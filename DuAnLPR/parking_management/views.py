from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q  # Import Q để dùng cho tìm kiếm phức tạp

from decimal import Decimal
from datetime import datetime, time, timedelta
import pytz  # Nếu bạn còn dùng trong calculate_parking_fee_detailed

# Import models một lần ở đây
from .models import (
    KhachThue,
    VehicleTypes,
    Vehicle,
    MonthlyTicketRules,
    PerTurnTicketRules,
    ParkingHistory
)
# Import forms một lần ở đây
from .forms import (
    KhachThueForm,
    VehicleForm,
    VehicleTypeForm,
    MonthlyTicketRuleForm,
    PerTurnTicketRuleForm
)
# Import hàm xử lý ảnh
from .image_processing import save_uploaded_image_and_recognize_plate


# View cho Trang chủ người dùng cuối
@login_required
def user_dashboard_view(request):
    xe_trong_bai_count = ParkingHistory.objects.filter(Status='IN_YARD', ExitTime__isnull=True).count()
    context = {
        'so_xe_trong_bai': xe_trong_bai_count,
        'user': request.user
    }
    return render(request, 'parking_management/user_dashboard.html', context)


# View cho Đăng nhập
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('parking_management:user_dashboard')
            else:
                context = {'form': form, 'error_message': 'Tên đăng nhập hoặc mật khẩu không đúng.'}
                return render(request, 'parking_management/login.html', context)
        else:
            context = {'form': form, 'error_message': 'Dữ liệu form không hợp lệ.'}
            return render(request, 'parking_management/login.html', context)
    else:
        form = AuthenticationForm()
    return render(request, 'parking_management/login.html', {'form': form})


# View cho Đăng xuất
@login_required
def logout_view(request):
    logout(request)
    return redirect('parking_management:login_user')


# View cho Kiểm tra biển số / Ghi nhận xe vào
@login_required
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
    entry_vehicle_image_path_to_save = None
    entry_ocr_ready_image_path_to_save = None  # Nếu bạn định lưu ảnh này

    if request.method == 'POST':
        bien_so_nhap_tay = request.POST.get('bien_so', '').strip().upper()
        uploaded_image = request.FILES.get('image_upload')
        bien_so_final = ""
        recognized_plate_status = ""

        if uploaded_image:
            plate_text_from_ocr, saved_original_path, saved_ocr_input_path = save_uploaded_image_and_recognize_plate(
                uploaded_image)
            if saved_original_path:
                entry_vehicle_image_path_to_save = saved_original_path
            if saved_ocr_input_path:
                entry_ocr_ready_image_path_to_save = saved_ocr_input_path

            recognized_plate_status = plate_text_from_ocr

            if recognized_plate_status and recognized_plate_status not in [
                "LOI_DOC_ANH", "LOI_XU_LY_ANH", "LOI_TESSERACT_NOT_FOUND", "LOI_OCR",
                "KHONG_TIM_THAY_VUNG_4_CANH", "OCR_KHONG_RA_KY_TU", "LOI_KICH_THUOC_CAT"
            ]:
                bien_so_final = recognized_plate_status.upper()
                context['thong_bao_text'] = f"Ảnh đã được upload. Biển số nhận dạng: {bien_so_final}."
            else:
                context['thong_bao_loi'] = f"Xử lý ảnh: {recognized_plate_status}. "
                if bien_so_nhap_tay:
                    bien_so_final = bien_so_nhap_tay
                    context['thong_bao_loi'] += "Sử dụng biển số nhập tay."
                # Bỏ return ở đây để form có thể hiển thị lại với lỗi
        elif bien_so_nhap_tay:
            bien_so_final = bien_so_nhap_tay
        else:
            context['thong_bao_loi'] = "Vui lòng nhập biển số hoặc upload ảnh."
            return render(request, 'parking_management/kiem_tra_bien_so.html', context)

        context['bien_so_da_nhap'] = bien_so_final

        if not bien_so_final or "LOI" in bien_so_final.upper() or \
                bien_so_final in ["KHONG_TIM_THAY_VUNG_4_CANH", "OCR_KHONG_RA_KY_TU"]:
            if not context['thong_bao_loi']:
                context['thong_bao_loi'] = "Không xác định được biển số xe hợp lệ."
            # Không return ở đây, để hiển thị lỗi trên form
        else:  # Chỉ xử lý ghi nhận nếu có bien_so_final hợp lệ
            try:
                xe_khach_thue_tim_thay = Vehicle.objects.filter(BienSoXe__iexact=bien_so_final).first()
                if xe_khach_thue_tim_thay:
                    khach_thue = xe_khach_thue_tim_thay.KhachThueID
                    context['xe'] = xe_khach_thue_tim_thay
                    context['khach_thue'] = khach_thue
                    lich_su_dang_gui = ParkingHistory.objects.filter(VehicleID=xe_khach_thue_tim_thay,
                                                                     ExitTime__isnull=True, Status='IN_YARD').first()
                    if lich_su_dang_gui:
                        context['thong_bao_text'] = (
                            f"Xe {xe_khach_thue_tim_thay.BienSoXe} của khách thuê {khach_thue.HoVaTen} "
                            f"đang ở trong bãi. Vào lúc:")
                        context['thoi_gian_su_kien'] = lich_su_dang_gui.EntryTime
                    else:
                        lich_su_moi = ParkingHistory.objects.create(
                            VehicleID=xe_khach_thue_tim_thay,
                            ProcessedLicensePlateEntry=bien_so_final,
                            EntryTime=timezone.now(), Status='IN_YARD',
                            EntryVehicleImagePath=entry_vehicle_image_path_to_save
                            # , EntryOcrReadyImagePath=entry_ocr_ready_image_path_to_save # Nếu bạn có trường này
                        )
                        context['thong_bao_thanh_cong_text'] = (
                            f"Đã ghi nhận xe {xe_khach_thue_tim_thay.BienSoXe} (BS nhận dạng: {bien_so_final}) của khách thuê "
                            f"{khach_thue.HoVaTen} vào bãi lúc:")
                        context['thoi_gian_su_kien'] = lich_su_moi.EntryTime
                else:
                    lich_su_vang_lai_dang_gui = ParkingHistory.objects.filter(
                        ProcessedLicensePlateEntry__iexact=bien_so_final,
                        VehicleID__isnull=True, ExitTime__isnull=True, Status='IN_YARD'
                    ).first()
                    if lich_su_vang_lai_dang_gui:
                        context['thong_bao_text'] = f"Xe khách vãng lai {bien_so_final} đang ở trong bãi. Vào lúc:"
                        context['thoi_gian_su_kien'] = lich_su_vang_lai_dang_gui.EntryTime
                    else:
                        lich_su_moi_vang_lai = ParkingHistory.objects.create(
                            VehicleID=None, ProcessedLicensePlateEntry=bien_so_final,
                            EntryTime=timezone.now(), Status='IN_YARD',
                            EntryVehicleImagePath=entry_vehicle_image_path_to_save
                            # , EntryOcrReadyImagePath=entry_ocr_ready_image_path_to_save # Nếu có
                        )
                        context[
                            'thong_bao_thanh_cong_text'] = f"Đã ghi nhận xe khách vãng lai (BS nhận dạng: {bien_so_final}) vào bãi lúc:"
                        context['thoi_gian_su_kien'] = lich_su_moi_vang_lai.EntryTime
            except Exception as e_view:
                print(f"Lỗi trong view kiem_tra_bien_so khi xử lý CSDL: {e_view}")
                context['thong_bao_loi'] = "Có lỗi xảy ra trong quá trình xử lý dữ liệu."

    return render(request, 'parking_management/kiem_tra_bien_so.html', context)


# Hàm tính phí chi tiết
def calculate_parking_fee_detailed(entry_dt_utc, exit_dt_utc, vehicle_type):
    # ... (Nội dung hàm này giữ nguyên như phiên bản bạn đã có và thấy ổn) ...
    total_fee = Decimal('0.00')
    applied_rules_descriptions = []

    local_tz = pytz.timezone(timezone.get_current_timezone_name())
    entry_dt = entry_dt_utc.astimezone(local_tz)
    exit_dt = exit_dt_utc.astimezone(local_tz)

    # print(f"CALC_FEE DEBUG: Localized entry_dt: {entry_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")
    # print(f"CALC_FEE DEBUG: Localized exit_dt: {exit_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}")

    if exit_dt <= entry_dt:
        return total_fee, ["Thời gian ra không hợp lệ."]

    all_rules = PerTurnTicketRules.objects.filter(VehicleTypeID=vehicle_type).order_by('TimeFrom')
    if not all_rules.exists():
        return total_fee, [
            f"Không có quy tắc vé lượt cho loại xe {vehicle_type.TypeName if vehicle_type else 'Không xác định'}."]  # Kiểm tra vehicle_type

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
            if current_day <= end_day:
                temp_entry_time_for_day_iteration = local_tz.localize(datetime.combine(current_day, time.min))
            continue

        for rule in all_rules:
            if rule.TimeFrom is None or rule.TimeTo is None:
                continue

            rule_start_dt_current_day_local = local_tz.localize(datetime.combine(current_day, rule.TimeFrom))
            rule_end_dt_current_day_local = local_tz.localize(datetime.combine(current_day, rule.TimeTo))

            is_overnight_shift_defined_by_times = rule.TimeFrom > rule.TimeTo

            if is_overnight_shift_defined_by_times:
                rule_part1_end_dt_local = day_end_dt_local

                overlap_start1 = max(actual_start_for_day, rule_start_dt_current_day_local)
                overlap_end1 = min(actual_end_for_day, rule_part1_end_dt_local)

                if overlap_start1 < overlap_end1:
                    total_fee += rule.Price
                    applied_rules_descriptions.append(
                        f"{rule.ShiftName or rule.PerTurnRuleID} (ngày {current_day.strftime('%d/%m')})")

                next_processing_day = current_day + timedelta(days=1)
                if next_processing_day <= end_day:
                    rule_part2_start_dt_next_day_local = local_tz.localize(
                        datetime.combine(next_processing_day, time.min))
                    rule_part2_end_dt_next_day_local = local_tz.localize(
                        datetime.combine(next_processing_day, rule.TimeTo))

                    next_day_entry_for_calc = local_tz.localize(datetime.combine(next_processing_day, time.min))
                    next_day_exit_for_calc = min(exit_dt,
                                                 local_tz.localize(datetime.combine(next_processing_day, time.max)))

                    overlap_start2 = max(next_day_entry_for_calc, rule_part2_start_dt_next_day_local)
                    overlap_end2 = min(next_day_exit_for_calc, rule_part2_end_dt_next_day_local)

                    if overlap_start2 < overlap_end2:
                        desc_part2 = f"{rule.ShiftName or rule.PerTurnRuleID} (phần qua đêm ngày {next_processing_day.strftime('%d/%m')})"
                        if desc_part2 not in applied_rules_descriptions:
                            total_fee += rule.Price
                            applied_rules_descriptions.append(desc_part2)
            else:
                overlap_start = max(actual_start_for_day, rule_start_dt_current_day_local)
                overlap_end = min(actual_end_for_day, rule_end_dt_current_day_local)

                if overlap_start < overlap_end:
                    total_fee += rule.Price
                    applied_rules_descriptions.append(
                        f"{rule.ShiftName or rule.PerTurnRuleID} (ngày {current_day.strftime('%d/%m')})")

        current_day += timedelta(days=1)
        if current_day <= end_day:
            temp_entry_time_for_day_iteration = local_tz.localize(datetime.combine(current_day, time.min))
    return total_fee, applied_rules_descriptions


# View cho Xử lý xe ra
@login_required
def xe_ra_khoi_bai_view(request):
    # ... (Nội dung hàm này giữ nguyên như phiên bản bạn đã có và thấy ổn) ...
    # Đảm bảo rằng khi gọi calculate_parking_fee_detailed, bạn truyền đúng:
    # lich_su_gui_xe.EntryTime (đang là UTC)
    # lich_su_gui_xe.ExitTime (đang là UTC, vừa được gán timezone.now())
    # current_vehicle_type (đối tượng VehicleTypes)
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
            ).select_related('VehicleID', 'VehicleID__VehicleTypeID').first()  # Thêm select_related

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
                    lich_su_gui_xe.ExitTime = timezone.now()  # Đây là aware datetime (UTC nếu USE_TZ=True)

                    phi_gui_xe = Decimal('0.00')
                    rules_applied_info = []

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

                        # `lich_su_gui_xe.EntryTime` và `lich_su_gui_xe.ExitTime` được truyền vào đây
                        # Chúng là aware datetime objects (thường là UTC)
                        phi_gui_xe, rules_applied_info = calculate_parking_fee_detailed(
                            lich_su_gui_xe.EntryTime,
                            lich_su_gui_xe.ExitTime,
                            current_vehicle_type
                        )

                        if rules_applied_info and not any("Không có quy tắc" in s for s in rules_applied_info):
                            # Gán PerTurnRuleAppliedID nếu muốn (ví dụ rule đầu tiên, hoặc dựa trên logic khác)
                            # lich_su_gui_xe.PerTurnRuleAppliedID = PerTurnTicketRules.objects.filter(VehicleTypeID=current_vehicle_type).first()
                            context['thong_bao_thanh_cong'] = (f"Đã tính tiền cho xe {bien_so_nhap_ra}. "
                                                               f"Các ca áp dụng: {'; '.join(rules_applied_info)}. "
                                                               f"Tổng số tiền: {phi_gui_xe} VND. Cho xe ra.")
                        elif rules_applied_info and "Không có quy tắc" in rules_applied_info[
                            0]:  # Kiểm tra lỗi trả về từ hàm tính
                            context['thong_bao_loi'] = rules_applied_info[
                                                           0] + f" Cho xe {bien_so_nhap_ra} ra không tính phí."
                            phi_gui_xe = Decimal('0.00')
                        else:
                            context['thong_bao_loi'] = (
                                f"Không xác định được quy tắc tính phí cho xe {bien_so_nhap_ra}. "
                                f"Tạm thời cho xe ra không tính phí.")
                            phi_gui_xe = Decimal('0.00')

                    lich_su_gui_xe.CalculatedFee = phi_gui_xe
                    lich_su_gui_xe.Status = 'EXITED'
                    lich_su_gui_xe.save()

                    context['tien_phai_tra'] = lich_su_gui_xe.CalculatedFee
                    context['lich_su_gui_xe'] = None
                else:  # Hiển thị thông tin xe để xác nhận
                    if lich_su_gui_xe.VehicleID:
                        khach_thue = lich_su_gui_xe.VehicleID.KhachThueID
                        context['thong_bao_text'] = (f"Tìm thấy xe {lich_su_gui_xe.VehicleID.BienSoXe} của khách thuê "
                                                     f"{khach_thue.HoVaTen} đang trong bãi.")
                        context['thoi_gian_vao'] = lich_su_gui_xe.EntryTime  # Sẽ được localize trong template
                        context['co_ve_thang'] = lich_su_gui_xe.VehicleID.HasMonthlyTicket
                    else:
                        context['thong_bao_text'] = (
                            f"Tìm thấy xe khách vãng lai {lich_su_gui_xe.ProcessedLicensePlateEntry} "
                            f"đang trong bãi.")
                        context['thoi_gian_vao'] = lich_su_gui_xe.EntryTime  # Sẽ được localize trong template
                        context['co_ve_thang'] = False
            else:
                context['thong_bao_loi'] = f"Không tìm thấy xe có biển số {bien_so_nhap_ra} đang trong bãi."

    return render(request, 'parking_management/xe_ra_khoi_bai.html', context)


# --- Các View CRUD cho KhachThue ---
@login_required
def khachthue_list_view(request):
    danh_sach_khach_thue = KhachThue.objects.all().order_by('HoVaTen')
    context = {'danh_sach_khach_thue': danh_sach_khach_thue}
    return render(request, 'parking_management/khachthue_list.html', context)


@login_required
def khachthue_create_view(request):
    if request.method == 'POST':
        form = KhachThueForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm khách thuê thành công!')
            return redirect('parking_management:khachthue_list')
    else:
        form = KhachThueForm()
    context = {'form': form, 'page_title': 'Thêm Khách Thuê Mới'}
    return render(request, 'parking_management/khachthue_form.html', context)


@login_required
def khachthue_update_view(request, khachthue_id):
    khach_thue_obj = get_object_or_404(KhachThue, KhachThueID=khachthue_id)
    if request.method == 'POST':
        form = KhachThueForm(request.POST, instance=khach_thue_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã cập nhật thông tin khách thuê thành công!')
            return redirect('parking_management:khachthue_list')
    else:
        form = KhachThueForm(instance=khach_thue_obj)
    context = {'form': form, 'page_title': f'Cập nhật Khách Thuê: {khach_thue_obj.HoVaTen}',
               'khach_thue': khach_thue_obj}
    return render(request, 'parking_management/khachthue_form.html', context)


@login_required
def khachthue_delete_view(request, khachthue_id):
    khach_thue_obj = get_object_or_404(KhachThue, KhachThueID=khachthue_id)
    if request.method == 'POST':
        ten_da_xoa = khach_thue_obj.HoVaTen
        khach_thue_obj.delete()
        messages.success(request, f'Đã xóa khách thuê {ten_da_xoa} thành công!')
        return redirect('parking_management:khachthue_list')
    context = {'khach_thue': khach_thue_obj, 'page_title': f'Xác nhận xóa Khách Thuê: {khach_thue_obj.HoVaTen}'}
    return render(request, 'parking_management/khachthue_confirm_delete.html', context)


# --- Các View CRUD cho Vehicle ---
@login_required
def vehicle_list_view(request):
    danh_sach_xe = Vehicle.objects.select_related('KhachThueID', 'VehicleTypeID').all().order_by('BienSoXe')
    context = {'danh_sach_xe': danh_sach_xe}
    return render(request, 'parking_management/vehicle_list.html', context)


@login_required
def vehicle_create_view(request):
    if request.method == 'POST':
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm xe mới thành công!')
            return redirect('parking_management:vehicle_list')
    else:
        form = VehicleForm()
    context = {'form': form, 'page_title': 'Thêm Xe Mới'}
    return render(request, 'parking_management/vehicle_form.html', context)


@login_required
def vehicle_update_view(request, vehicle_id):
    vehicle_obj = get_object_or_404(Vehicle, VehicleID=vehicle_id)
    if request.method == 'POST':
        form = VehicleForm(request.POST, instance=vehicle_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật thông tin xe {vehicle_obj.BienSoXe} thành công!')
            return redirect('parking_management:vehicle_list')
    else:
        form = VehicleForm(instance=vehicle_obj)
    context = {'form': form, 'page_title': f'Cập nhật Xe: {vehicle_obj.BienSoXe}', 'vehicle': vehicle_obj}
    return render(request, 'parking_management/vehicle_form.html', context)


@login_required
def vehicle_delete_view(request, vehicle_id):
    vehicle_obj = get_object_or_404(Vehicle, VehicleID=vehicle_id)
    if request.method == 'POST':
        bien_so_da_xoa = vehicle_obj.BienSoXe
        vehicle_obj.delete()
        messages.success(request, f'Đã xóa xe {bien_so_da_xoa} thành công!')
        return redirect('parking_management:vehicle_list')
    context = {'vehicle': vehicle_obj, 'page_title': f'Xác nhận xóa Xe: {vehicle_obj.BienSoXe}'}
    return render(request, 'parking_management/vehicle_confirm_delete.html', context)


# --- Các View CRUD cho VehicleTypes ---
@login_required
def vehicletype_list_view(request):
    danh_sach_loai_xe = VehicleTypes.objects.all().order_by('TypeName')
    context = {'danh_sach_loai_xe': danh_sach_loai_xe}
    return render(request, 'parking_management/vehicletype_list.html', context)


@login_required
def vehicletype_create_view(request):
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm loại xe mới thành công!')
            return redirect('parking_management:vehicletype_list')
    else:
        form = VehicleTypeForm()
    context = {'form': form, 'page_title': 'Thêm Loại Xe Mới'}
    return render(request, 'parking_management/vehicletype_form.html', context)


@login_required
def vehicletype_update_view(request, vehicletype_id):
    vehicletype_obj = get_object_or_404(VehicleTypes, VehicleTypeID=vehicletype_id)
    if request.method == 'POST':
        form = VehicleTypeForm(request.POST, instance=vehicletype_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật loại xe {vehicletype_obj.TypeName} thành công!')
            return redirect('parking_management:vehicletype_list')
    else:
        form = VehicleTypeForm(instance=vehicletype_obj)
    context = {'form': form, 'page_title': f'Cập nhật Loại Xe: {vehicletype_obj.TypeName}', 'object': vehicletype_obj}
    return render(request, 'parking_management/vehicletype_form.html', context)


@login_required
def vehicletype_delete_view(request, vehicletype_id):
    vehicletype_obj = get_object_or_404(VehicleTypes, VehicleTypeID=vehicletype_id)
    if request.method == 'POST':
        try:
            type_name_da_xoa = vehicletype_obj.TypeName
            vehicletype_obj.delete()
            messages.success(request, f'Đã xóa loại xe {type_name_da_xoa} thành công!')
        except Exception as e:
            messages.error(request,
                           f'Không thể xóa loại xe "{vehicletype_obj.TypeName}" vì đang có xe hoặc quy tắc giá sử dụng loại xe này.')
        return redirect('parking_management:vehicletype_list')
    context = {'object_to_delete': vehicletype_obj, 'page_title': f'Xác nhận xóa Loại Xe: {vehicletype_obj.TypeName}'}
    return render(request, 'parking_management/vehicletype_confirm_delete.html', context)


# --- Các View CRUD cho MonthlyTicketRules ---
@login_required
def monthlyticketrule_list_view(request):
    danh_sach_quy_tac = MonthlyTicketRules.objects.select_related('VehicleTypeID').all().order_by(
        'VehicleTypeID__TypeName', 'PricePerMonth')
    context = {'danh_sach_quy_tac': danh_sach_quy_tac}
    return render(request, 'parking_management/monthlyticketrule_list.html', context)


@login_required
def monthlyticketrule_create_view(request):
    if request.method == 'POST':
        form = MonthlyTicketRuleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm quy tắc giá vé tháng mới thành công!')
            return redirect('parking_management:monthlyticketrule_list')
    else:
        form = MonthlyTicketRuleForm()
    context = {'form': form, 'page_title': 'Thêm Quy Tắc Giá Vé Tháng Mới'}
    return render(request, 'parking_management/monthlyticketrule_form.html', context)


@login_required
def monthlyticketrule_update_view(request, rule_id):
    rule_obj = get_object_or_404(MonthlyTicketRules, MonthlyRuleID=rule_id)
    if request.method == 'POST':
        form = MonthlyTicketRuleForm(request.POST, instance=rule_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật quy tắc giá vé tháng thành công!')
            return redirect('parking_management:monthlyticketrule_list')
    else:
        form = MonthlyTicketRuleForm(instance=rule_obj)
    context = {'form': form, 'page_title': f'Cập nhật Quy Tắc Giá Vé Tháng (ID: {rule_obj.MonthlyRuleID})',
               'object': rule_obj}
    return render(request, 'parking_management/monthlyticketrule_form.html', context)


@login_required
def monthlyticketrule_delete_view(request, rule_id):
    rule_obj = get_object_or_404(MonthlyTicketRules, MonthlyRuleID=rule_id)
    if request.method == 'POST':
        try:
            rule_desc = f"Quy tắc cho {rule_obj.VehicleTypeID.TypeName} - {rule_obj.PricePerMonth} VND"
            rule_obj.delete()
            messages.success(request, f'Đã xóa quy tắc giá vé tháng "{rule_desc}" thành công!')
        except Exception as e:
            messages.error(request, f'Không thể xóa quy tắc giá vé tháng. Lỗi: {e}')
        return redirect('parking_management:monthlyticketrule_list')
    context = {'object_to_delete': rule_obj,
               'page_title': f'Xác nhận xóa Quy Tắc Giá Vé Tháng (ID: {rule_obj.MonthlyRuleID})'}
    return render(request, 'parking_management/monthlyticketrule_confirm_delete.html', context)


# --- Các View CRUD cho PerTurnTicketRules ---
@login_required
def perturnticketrule_list_view(request):
    danh_sach_quy_tac = PerTurnTicketRules.objects.select_related('VehicleTypeID').all().order_by(
        'VehicleTypeID__TypeName', 'TimeFrom')
    context = {'danh_sach_quy_tac': danh_sach_quy_tac}
    return render(request, 'parking_management/perturnticketrule_list.html', context)


@login_required
def perturnticketrule_create_view(request):
    if request.method == 'POST':
        form = PerTurnTicketRuleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Đã thêm quy tắc giá vé lượt mới thành công!')
            return redirect('parking_management:perturnticketrule_list')
    else:
        form = PerTurnTicketRuleForm()
    context = {'form': form, 'page_title': 'Thêm Quy Tắc Giá Vé Lượt Mới'}
    return render(request, 'parking_management/perturnticketrule_form.html', context)


@login_required
def perturnticketrule_update_view(request, rule_id):
    rule_obj = get_object_or_404(PerTurnTicketRules, PerTurnRuleID=rule_id)
    if request.method == 'POST':
        form = PerTurnTicketRuleForm(request.POST, instance=rule_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Đã cập nhật quy tắc giá vé lượt thành công!')
            return redirect('parking_management:perturnticketrule_list')
    else:
        form = PerTurnTicketRuleForm(instance=rule_obj)
    context = {'form': form, 'page_title': f'Cập nhật Quy Tắc Giá Vé Lượt (ID: {rule_obj.PerTurnRuleID})',
               'object': rule_obj}
    return render(request, 'parking_management/perturnticketrule_form.html', context)


@login_required
def perturnticketrule_delete_view(request, rule_id):
    rule_obj = get_object_or_404(PerTurnTicketRules, PerTurnRuleID=rule_id)
    if request.method == 'POST':
        try:
            rule_info = f"Quy tắc cho {rule_obj.VehicleTypeID.TypeName} ({rule_obj.ShiftName if rule_obj.ShiftName else 'Cả ngày'}) - {rule_obj.Price} VND"
            rule_obj.delete()
            messages.success(request, f'Đã xóa quy tắc giá vé lượt "{rule_info}" thành công!')
        except Exception as e:
            messages.error(request, f'Không thể xóa quy tắc giá vé lượt. Có thể đang được sử dụng. Lỗi: {e}')
        return redirect('parking_management:perturnticketrule_list')
    context = {'object_to_delete': rule_obj,
               'page_title': f'Xác nhận xóa Quy Tắc Giá Vé Lượt (ID: {rule_obj.PerTurnRuleID})'}
    return render(request, 'parking_management/perturnticketrule_confirm_delete.html', context)


# --- View cho Lịch Sử Ra Vào ---
@login_required
def parkinghistory_list_view(request):
    lich_su_list_full = ParkingHistory.objects.select_related(
        'VehicleID',
        'VehicleID__KhachThueID',
        'VehicleID__VehicleTypeID',
        'PerTurnRuleAppliedID',
        'PerTurnRuleAppliedID__VehicleTypeID'
    ).order_by('-EntryTime')

    query = request.GET.get('q', '')
    if query:
        lich_su_list_full = lich_su_list_full.filter(
            Q(ProcessedLicensePlateEntry__icontains=query) |
            Q(ProcessedLicensePlateExit__icontains=query) |
            Q(VehicleID__BienSoXe__icontains=query)
        ).distinct()

    paginator = Paginator(lich_su_list_full, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'page_title': 'Lịch Sử Xe Ra/Vào Bãi'
    }
    return render(request, 'parking_management/parkinghistory_list.html', context)