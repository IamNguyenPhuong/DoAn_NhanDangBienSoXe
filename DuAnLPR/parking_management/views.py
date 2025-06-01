from django.shortcuts import render, redirect
from django.utils import timezone
from django.contrib import messages
from .models import Vehicle, KhachThue, ParkingHistory, PerTurnTicketRules, VehicleTypes
from decimal import Decimal
from datetime import datetime, time, timedelta # Thêm datetime, time, timedelta
import pytz
from .image_processing import save_uploaded_image_and_recognize_plate

# Bỏ PerTurnTicketRules, VehicleTypes nếu chưa dùng đến trong view này
# from .models import Vehicle, KhachThue, ParkingHistory, PerTurnTicketRules, VehicleTypes

def kiem_tra_bien_so_view(request):
    context = {
        'thong_bao_loi': None,
        'thong_bao_thanh_cong_text': None,
        'thong_bao_text': None,
        'thoi_gian_su_kien': None,
        'xe': None,
        'khach_thue': None,
        'bien_so_da_nhap': ''
    }

    entry_vehicle_image_path_to_save = None  # Biến để lưu đường dẫn ảnh
    entry_cropped_plate_image_path_to_save = None  # Thêm biến này

    if request.method == 'POST':
        bien_so_nhap_tay = request.POST.get('bien_so', '').strip().upper()
        uploaded_image = request.FILES.get('image_upload')

        bien_so_final = ""

        if uploaded_image:
            # Hàm bây giờ trả về 3 giá trị
            recognized_plate, saved_original_path, saved_cropped_path = save_uploaded_image_and_recognize_plate(
                uploaded_image)

            if recognized_plate and saved_original_path:  # Chỉ cần recognized_plate và ảnh gốc là đủ để tiếp tục
                bien_so_final = recognized_plate.upper()
                entry_vehicle_image_path_to_save = saved_original_path
                if saved_cropped_path:  # Nếu có ảnh cắt
                    entry_cropped_plate_image_path_to_save = saved_cropped_path

                # Điều chỉnh thông báo để thân thiện hơn, không nhất thiết hiển thị biển số "giả"
                if "LOI" in bien_so_final:
                    context['thong_bao_loi'] = f"Xử lý ảnh: {bien_so_final}."
                elif bien_so_final == "CHUA_NHAN_DANG":
                    context['thong_bao_text'] = "Ảnh đã được upload, nhưng chưa nhận dạng được biển số từ ảnh."
                elif bien_so_final == "DA_TIM_THAY_VUNG_BIEN_SO":  # Hoặc DA_TIM_THAY_VUNG_4_CANH
                    context['thong_bao_text'] = f"Ảnh đã được upload, đã khoanh vùng được biển số (cần OCR)."
                    # Ở đây, vì chưa có OCR, chúng ta có thể yêu cầu người dùng nhập tay biển số nếu muốn
                    # hoặc dùng một giá trị tạm thời nếu không muốn chặn luồng.
                    # Ví dụ: yêu cầu nhập tay nếu OCR thất bại
                    # context['yeu_cau_nhap_tay_bien_so'] = True
                    # context['thong_bao_loi'] = "Đã khoanh vùng biển số, vui lòng nhập ký tự biển số để xác nhận."
                    # return render(request, 'parking_management/kiem_tra_bien_so.html', context)
                    # Hoặc tạm thời, để test luồng, chúng ta vẫn tiếp tục với một biển số "đã xử lý"
                    pass  # Để logic phía dưới tiếp tục với bien_so_final là "DA_TIM_THAY_VUNG_BIEN_SO"
                else:  # Trường hợp OCR thành công (sau này)
                    context['thong_bao_text'] = f"Ảnh đã được upload. Biển số nhận dạng: {bien_so_final}."

            else:  # recognized_plate là None hoặc saved_original_path là None
                context['thong_bao_loi'] = "Có lỗi nghiêm trọng khi xử lý hoặc lưu ảnh upload."
                return render(request, 'parking_management/kiem_tra_bien_so.html', context)

        elif bien_so_nhap_tay:
            bien_so_final = bien_so_nhap_tay
        else:
            context['thong_bao_loi'] = "Vui lòng nhập biển số hoặc upload ảnh."
            return render(request, 'parking_management/kiem_tra_bien_so.html', context)

        context['bien_so_da_nhap'] = bien_so_final

        if not bien_so_final or "LOI" in bien_so_final.upper():
            if not context['thong_bao_loi']:
                context['thong_bao_loi'] = "Không xác định được biển số xe hợp lệ từ ảnh hoặc nhập tay."
            return render(request, 'parking_management/kiem_tra_bien_so.html', context)

        # --- Phần logic kiểm tra xe và ghi nhận ---
        try:
            # Nếu bien_so_final là "DA_TIM_THAY_VUNG_BIEN_SO", có thể bạn muốn tìm theo một cách khác
            # hoặc yêu cầu nhập tay. Hiện tại, nó sẽ không tìm thấy trong Vehicle.objects.get
            # Trừ khi bạn có xe với biển số là "DA_TIM_THAY_VUNG_BIEN_SO"

            # Để đơn giản, nếu bien_so_final không phải là một biển số thực sự mà là thông báo,
            # ta sẽ coi như không tìm thấy xe khách thuê và xử lý như khách vãng lai với biển số này.

            xe_khach_thue_tim_thay = None
            if bien_so_final not in ["CHUA_NHAN_DANG", "DA_TIM_THAY_VUNG_BIEN_SO",
                                     "LOI_KICH_THUOC_CAT"]:  # Giả sử đây là các thông báo
                xe_khach_thue_tim_thay = Vehicle.objects.filter(BienSoXe__iexact=bien_so_final).first()

            if xe_khach_thue_tim_thay:
                xe_tim_thay = xe_khach_thue_tim_thay
                khach_thue = xe_tim_thay.KhachThueID
                context['xe'] = xe_tim_thay
                context['khach_thue'] = khach_thue
                # ... (logic kiểm tra xe khách thuê đang trong bãi và ghi nhận như cũ) ...
                # Khi tạo ParkingHistory, thêm:
                # EntryCroppedPlateImagePath=entry_cropped_plate_image_path_to_save (nếu có)
                lich_su_dang_gui = ParkingHistory.objects.filter(
                    VehicleID=xe_tim_thay, ExitTime__isnull=True, Status='IN_YARD'
                ).first()
                if lich_su_dang_gui:
                    # ... (thông báo xe đang trong bãi)
                    context['thong_bao_text'] = (f"Xe {xe_tim_thay.BienSoXe} của khách thuê {khach_thue.HoVaTen} "
                                                 f"đang ở trong bãi. Vào lúc:")
                    context['thoi_gian_su_kien'] = lich_su_dang_gui.EntryTime
                else:
                    lich_su_moi = ParkingHistory.objects.create(
                        VehicleID=xe_tim_thay,
                        ProcessedLicensePlateEntry=bien_so_final,
                        EntryTime=timezone.now(), Status='IN_YARD',
                        EntryVehicleImagePath=entry_vehicle_image_path_to_save,
                        EntryCroppedPlateImagePath=entry_cropped_plate_image_path_to_save  # Thêm dòng này
                    )
                    # ... (thông báo thành công)
                    context['thong_bao_thanh_cong_text'] = (f"Đã ghi nhận xe {xe_tim_thay.BienSoXe} của khách thuê "
                                                            f"{khach_thue.HoVaTen} vào bãi lúc:")
                    context['thoi_gian_su_kien'] = lich_su_moi.EntryTime

            else:  # Xử lý như khách vãng lai (hoặc xe khách thuê nhưng biển số từ ảnh chưa phải là biển số thật)
                lich_su_vang_lai_dang_gui = ParkingHistory.objects.filter(
                    ProcessedLicensePlateEntry__iexact=bien_so_final,
                    VehicleID__isnull=True, ExitTime__isnull=True, Status='IN_YARD'
                ).first()

                if lich_su_vang_lai_dang_gui:
                    # ... (thông báo xe vãng lai đang trong bãi)
                    context['thong_bao_text'] = f"Xe khách vãng lai {bien_so_final} đang ở trong bãi. Vào lúc:"
                    context['thoi_gian_su_kien'] = lich_su_vang_lai_dang_gui.EntryTime
                else:
                    lich_su_moi_vang_lai = ParkingHistory.objects.create(
                        VehicleID=None, ProcessedLicensePlateEntry=bien_so_final,
                        EntryTime=timezone.now(), Status='IN_YARD',
                        EntryVehicleImagePath=entry_vehicle_image_path_to_save,
                        EntryCroppedPlateImagePath=entry_cropped_plate_image_path_to_save  # Thêm dòng này
                    )
                    # ... (thông báo thành công)
                    context['thong_bao_thanh_cong_text'] = f"Đã ghi nhận xe khách vãng lai {bien_so_final} vào bãi lúc:"
                    context['thoi_gian_su_kien'] = lich_su_moi_vang_lai.EntryTime

        except Vehicle.DoesNotExist:  # Khối except này có thể không cần thiết nữa nếu dùng filter().first()
            # Xử lý như khách vãng lai (copy logic từ trên xuống nếu cần, nhưng đoạn code trên đã gộp)
            pass

    return render(request, 'parking_management/kiem_tra_bien_so.html', context)


def calculate_parking_fee_detailed(entry_dt_utc, exit_dt_utc, vehicle_type):
    """
    Tính phí gửi xe chi tiết dựa trên các ca đã định nghĩa.
    entry_dt_utc và exit_dt_utc được giả định là aware datetime objects ở múi giờ UTC.
    """
    total_fee = Decimal('0.00')
    applied_rules_descriptions = []

    # Chuyển đổi sang múi giờ địa phương (Asia/Ho_Chi_Minh)
    local_tz = pytz.timezone(timezone.get_current_timezone_name())  # Lấy TIME_ZONE từ settings
    entry_dt = entry_dt_utc.astimezone(local_tz)
    exit_dt = exit_dt_utc.astimezone(local_tz)

    print(f"CALC_FEE DEBUG: Localized entry_dt: {entry_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    print(f"CALC_FEE DEBUG: Localized exit_dt: {exit_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    if exit_dt <= entry_dt:
        return total_fee, ["Thời gian ra không hợp lệ."]

    all_rules = PerTurnTicketRules.objects.filter(VehicleTypeID=vehicle_type).order_by('TimeFrom')
    if not all_rules.exists():
        return total_fee, [f"Không có quy tắc vé lượt cho loại xe {vehicle_type.TypeName}."]

    current_day = entry_dt.date()
    end_day = exit_dt.date()

    temp_entry_time_for_day_iteration = entry_dt

    while current_day <= end_day:
        is_entry_day = (current_day == entry_dt.date())
        is_exit_day = (current_day == exit_dt.date())

        day_start_dt_local = local_tz.localize(datetime.combine(current_day, time.min))
        day_end_dt_local = local_tz.localize(datetime.combine(current_day, time.max))

        actual_start_for_day = max(temp_entry_time_for_day_iteration,
                                   day_start_dt_local) if is_entry_day else day_start_dt_local
        actual_end_for_day = min(exit_dt, day_end_dt_local) if is_exit_day else day_end_dt_local

        if actual_start_for_day >= actual_end_for_day:
            current_day += timedelta(days=1)
            if current_day <= end_day:  # Chỉ cập nhật nếu vòng lặp sẽ tiếp tục
                temp_entry_time_for_day_iteration = local_tz.localize(datetime.combine(current_day, time.min))
            continue

        for rule in all_rules:
            if rule.TimeFrom is None or rule.TimeTo is None:
                continue

            # Tạo datetime cho TimeFrom và TimeTo của rule trong ngày hiện tại (current_day) VỚI MÚI GIỜ ĐỊA PHƯƠNG
            rule_start_dt_current_day_local = local_tz.localize(datetime.combine(current_day, rule.TimeFrom))
            rule_end_dt_current_day_local = local_tz.localize(datetime.combine(current_day, rule.TimeTo))

            # Xử lý ca qua đêm
            if rule_end_dt_current_day_local < rule_start_dt_current_day_local:
                # Phần 1 của ca: từ rule.TimeFrom đến cuối ngày current_day
                rule_part1_end_dt_local = day_end_dt_local

                overlap_start1 = max(actual_start_for_day, rule_start_dt_current_day_local)
                overlap_end1 = min(actual_end_for_day, rule_part1_end_dt_local)

                if overlap_start1 < overlap_end1:
                    total_fee += rule.Price
                    applied_rules_descriptions.append(
                        f"{rule.ShiftName or rule.PerTurnRuleID} (ngày {current_day.strftime('%d/%m')})")

                # Phần 2 của ca: từ đầu ngày (current_day + 1) đến rule.TimeTo
                next_processing_day = current_day + timedelta(days=1)
                if next_processing_day <= end_day:  # Chỉ xét nếu ngày xử lý tiếp theo vẫn trong khoảng gửi xe
                    rule_part2_start_dt_local = local_tz.localize(datetime.combine(next_processing_day, time.min))
                    rule_part2_end_dt_local = local_tz.localize(datetime.combine(next_processing_day, rule.TimeTo))

                    # Xác định khoảng thời gian xe gửi trong ngày next_processing_day
                    next_day_entry_for_calc = local_tz.localize(datetime.combine(next_processing_day, time.min))
                    next_day_exit_for_calc = min(exit_dt,
                                                 local_tz.localize(datetime.combine(next_processing_day, time.max)))

                    overlap_start2 = max(next_day_entry_for_calc, rule_part2_start_dt_local)
                    overlap_end2 = min(next_day_exit_for_calc, rule_part2_end_dt_local)

                    if overlap_start2 < overlap_end2:
                        desc_part2 = f"{rule.ShiftName or rule.PerTurnRuleID} (phần qua đêm ngày {next_processing_day.strftime('%d/%m')})"
                        if desc_part2 not in applied_rules_descriptions:
                            total_fee += rule.Price
                            applied_rules_descriptions.append(desc_part2)
            else:  # Ca trong ngày
                overlap_start = max(actual_start_for_day, rule_start_dt_current_day_local)
                overlap_end = min(actual_end_for_day, rule_end_dt_current_day_local)

                if overlap_start < overlap_end:
                    total_fee += rule.Price
                    applied_rules_descriptions.append(
                        f"{rule.ShiftName or rule.PerTurnRuleID} (ngày {current_day.strftime('%d/%m')})")

        current_day += timedelta(days=1)
        if current_day <= end_day:  # Chỉ cập nhật nếu vòng lặp sẽ tiếp tục
            temp_entry_time_for_day_iteration = local_tz.localize(datetime.combine(current_day, time.min))

    return total_fee, applied_rules_descriptions

def xe_ra_khoi_bai_view(request):
    context = {
        'bien_so_da_nhap': '',
        'lich_su_gui_xe': None,
        'thong_bao_loi': None,
        'thong_bao_thanh_cong': None,
        'tien_phai_tra': None,
    }

    if request.method == 'POST':
        bien_so_nhap_ra = request.POST.get('bien_so_ra', '').strip().upper()
        context['bien_so_da_nhap'] = bien_so_nhap_ra

        if not bien_so_nhap_ra:
            context['thong_bao_loi'] = "Vui lòng nhập biển số xe muốn ra."
        else:
            lich_su_gui_xe = ParkingHistory.objects.filter(
                VehicleID__BienSoXe__iexact=bien_so_nhap_ra,
                ExitTime__isnull=True,
                Status='IN_YARD'
            ).first()

            if not lich_su_gui_xe:
                lich_su_gui_xe = ParkingHistory.objects.filter(
                    ProcessedLicensePlateEntry__iexact=bien_so_nhap_ra,
                    VehicleID__isnull=True,
                    ExitTime__isnull=True,
                    Status='IN_YARD'
                ).first()

            context['lich_su_gui_xe'] = lich_su_gui_xe

            if lich_su_gui_xe:
                if 'action_tinh_tien_va_cho_ra' in request.POST:
                    lich_su_gui_xe.ExitTime = timezone.now()

                    phi_gui_xe = Decimal('0.00')
                    rules_applied_info = []  # Để lưu thông tin các rule đã áp dụng

                    if lich_su_gui_xe.VehicleID and lich_su_gui_xe.VehicleID.HasMonthlyTicket:
                        lich_su_gui_xe.WasMonthlyTicketUsed = True
                        context[
                            'thong_bao_thanh_cong'] = f"Xe {bien_so_nhap_ra} của khách thuê sử dụng vé tháng. Cho xe ra."
                    else:
                        current_vehicle_type = None
                        if lich_su_gui_xe.VehicleID:
                            current_vehicle_type = lich_su_gui_xe.VehicleID.VehicleTypeID
                        else:
                            try:
                                current_vehicle_type = VehicleTypes.objects.get(TypeName='Xe máy')
                            except VehicleTypes.DoesNotExist:
                                context['thong_bao_loi'] = "Lỗi: Không tìm thấy loại xe 'Xe máy' mặc định."
                                lich_su_gui_xe.CalculatedFee = phi_gui_xe
                                lich_su_gui_xe.Status = 'EXITED_WITH_ERROR_NO_TYPE'
                                lich_su_gui_xe.save()
                                return render(request, 'parking_management/xe_ra_khoi_bai.html', context)

                        phi_gui_xe, rules_applied_info = calculate_parking_fee_detailed(
                            lich_su_gui_xe.EntryTime,
                            lich_su_gui_xe.ExitTime,
                            current_vehicle_type
                        )

                        if rules_applied_info and not any("Không có quy tắc" in s for s in
                                                          rules_applied_info):  # Kiểm tra nếu có rule được áp dụng
                            lich_su_gui_xe.PerTurnRuleAppliedID = PerTurnTicketRules.objects.filter(
                                VehicleTypeID=current_vehicle_type).first()  # Tạm gán rule đầu tiên
                            context['thong_bao_thanh_cong'] = (f"Đã tính tiền cho xe {bien_so_nhap_ra}. "
                                                               f"Các ca áp dụng: {'; '.join(rules_applied_info)}. "
                                                               f"Tổng số tiền: {phi_gui_xe} VND. Cho xe ra.")
                        elif "Không có quy tắc" in rules_applied_info[0]:
                            context['thong_bao_loi'] = rules_applied_info[
                                                           0] + f" Cho xe {bien_so_nhap_ra} ra không tính phí."
                            phi_gui_xe = Decimal('0.00')
                        else:  # Không có rule nào khớp
                            context['thong_bao_loi'] = (
                                f"Không xác định được quy tắc tính phí cho xe {bien_so_nhap_ra}. "
                                f"Tạm thời cho xe ra không tính phí.")
                            phi_gui_xe = Decimal('0.00')

                    lich_su_gui_xe.CalculatedFee = phi_gui_xe
                    lich_su_gui_xe.Status = 'EXITED'
                    lich_su_gui_xe.save()

                    context['tien_phai_tra'] = lich_su_gui_xe.CalculatedFee
                    context['lich_su_gui_xe'] = None
                else:
                    if lich_su_gui_xe.VehicleID:
                        khach_thue = lich_su_gui_xe.VehicleID.KhachThueID
                        context['thong_bao_text'] = (f"Tìm thấy xe {lich_su_gui_xe.VehicleID.BienSoXe} của khách thuê "
                                                     f"{khach_thue.HoVaTen} đang trong bãi.")
                        context['thoi_gian_vao'] = lich_su_gui_xe.EntryTime
                        context['co_ve_thang'] = lich_su_gui_xe.VehicleID.HasMonthlyTicket
                    else:
                        context['thong_bao_text'] = (
                            f"Tìm thấy xe khách vãng lai {lich_su_gui_xe.ProcessedLicensePlateEntry} "
                            f"đang trong bãi.")
                        context['thoi_gian_vao'] = lich_su_gui_xe.EntryTime
                        context['co_ve_thang'] = False
            else:
                context['thong_bao_loi'] = f"Không tìm thấy xe có biển số {bien_so_nhap_ra} đang trong bãi."

    return render(request, 'parking_management/xe_ra_khoi_bai.html', context)
