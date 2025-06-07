# Standard Library Imports
import os
import uuid
from calendar import monthrange
from datetime import datetime, time, timedelta
from decimal import Decimal

# Third-party Imports
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
import pytz

# Local Application Imports
from .forms import (DateSelectionForm, KhachThueForm, MonthYearSelectionForm,
                    MonthlyTicketRuleForm, PerTurnTicketRuleForm, VehicleForm,
                    VehicleTypeForm)
from .image_processing import (save_entry_image_and_recognize_plate,
                               save_exit_image_and_recognize_plate)
from .models import (KhachThue, MonthlyTicketRules, ParkingHistory,
                     PerTurnTicketRules, Vehicle, VehicleTypes)

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
    # 1. Lấy danh sách các loại xe để hiển thị ra form
    vehicle_types = VehicleTypes.objects.all()

    # 2. Truyền danh sách loại xe vào context
    context = {
        'thong_bao_loi': None,
        'thong_bao_thanh_cong_text': None,
        'thong_bao_text': None,
        'thoi_gian_su_kien': None,
        'xe': None,
        'khach_thue': None,
        'bien_so_da_nhap': '',
        'vehicle_types': vehicle_types,
    }
    entry_vehicle_image_path_to_save = None
    entry_ocr_ready_image_path_to_save = None

    if request.method == 'POST':
        bien_so_nhap_tay = request.POST.get('bien_so', '').strip().upper()
        uploaded_image = request.FILES.get('image_upload')

        # 3. Lấy loại xe từ form, giá trị là ID của VehicleType
        vehicle_type_id = request.POST.get('vehicle_type')

        bien_so_final = ""
        recognized_plate_status = ""

        if uploaded_image:
            plate_text_from_ocr, saved_original_path, saved_ocr_input_path = save_entry_image_and_recognize_plate(uploaded_image)
            if saved_original_path:
                entry_vehicle_image_path_to_save = saved_original_path
            if saved_ocr_input_path:
                entry_ocr_ready_image_path_to_save = saved_ocr_input_path

            recognized_plate_status = plate_text_from_ocr

            if recognized_plate_status and "LOI" not in recognized_plate_status.upper() and "KHONG" not in recognized_plate_status.upper():
                bien_so_final = recognized_plate_status.upper()
                context['thong_bao_text'] = f"Ảnh đã được upload. Biển số nhận dạng: {bien_so_final}."
            else:
                context['thong_bao_loi'] = f"Xử lý ảnh: {recognized_plate_status}. "
                if bien_so_nhap_tay:
                    bien_so_final = bien_so_nhap_tay
                    context['thong_bao_loi'] += "Sử dụng biển số nhập tay."
        elif bien_so_nhap_tay:
            bien_so_final = bien_so_nhap_tay
        else:
            context['thong_bao_loi'] = "Vui lòng nhập biển số hoặc upload ảnh."
            return render(request, 'parking_management/kiem_tra_bien_so.html', context)

        context['bien_so_da_nhap'] = bien_so_final

        if not bien_so_final or "LOI" in bien_so_final.upper() or "KHONG" in bien_so_final.upper():
            if not context['thong_bao_loi']:
                context['thong_bao_loi'] = "Không xác định được biển số xe hợp lệ."
        else:
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
                            VehicleTypeID=xe_khach_thue_tim_thay.VehicleTypeID,
                            ProcessedLicensePlateEntry=bien_so_final,
                            EntryTime=timezone.now(), Status='IN_YARD',
                            EntryVehicleImagePath=entry_vehicle_image_path_to_save
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
                        selected_vehicle_type = None
                        if vehicle_type_id:
                            try:
                                selected_vehicle_type = VehicleTypes.objects.get(pk=vehicle_type_id)
                            except VehicleTypes.DoesNotExist:
                                context['thong_bao_loi'] = "Loại xe đã chọn không hợp lệ."

                        if not context['thong_bao_loi']:
                            lich_su_moi_vang_lai = ParkingHistory.objects.create(
                                VehicleID=None,
                                ProcessedLicensePlateEntry=bien_so_final,
                                EntryTime=timezone.now(),
                                Status='IN_YARD',
                                EntryVehicleImagePath=entry_vehicle_image_path_to_save,
                                VehicleTypeID=selected_vehicle_type
                            )
                            context[
                                'thong_bao_thanh_cong_text'] = f"Đã ghi nhận xe khách vãng lai (BS nhận dạng: {bien_so_final}) vào bãi lúc:"
                            context['thoi_gian_su_kien'] = lich_su_moi_vang_lai.EntryTime

            except Exception as e_view:
                print(f"Lỗi trong view kiem_tra_bien_so khi xử lý CSDL: {e_view}")
                context['thong_bao_loi'] = "Có lỗi xảy ra trong quá trình xử lý dữ liệu."

    # ---- DÒNG BỊ LỖI ĐÃ ĐƯỢC SỬA Ở ĐÂY ----
    return render(request, 'parking_management/kiem_tra_bien_so.html', context)


# Hàm tính phí chi tiết
def calculate_parking_fee_detailed(entry_dt_utc, exit_dt_utc, vehicle_type):
    # ... (Nội dung hàm này giữ nguyên như phiên bản bạn đã có và thấy ổn) ...
    total_fee = 0
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
    context = {
        'bien_so_da_nhap': '',
        'lich_su_gui_xe_hien_tai': None,
        'thong_bao_loi': None,
        'thong_bao_thanh_cong': None,
        'tien_phai_tra': None,
        'entry_time_display': None,
        'exit_time_display': None,
        'saved_exit_image_path': None,  # <--- THAY ĐỔI: Thêm vào context
    }

    if request.method == 'POST':
        bien_so_nhap_tay = request.POST.get('bien_so_ra', '').strip().upper()
        exit_image_file = request.FILES.get('exit_image_upload')
        # <--- THAY ĐỔI: Lấy lại đường dẫn ảnh đã lưu từ hidden input
        saved_path_from_hidden_input = request.POST.get('saved_exit_image_path')

        bien_so_final = ""
        exit_image_path_to_save = None

        if exit_image_file:
            # Ưu tiên xử lý nếu có file mới được upload
            plate_text_from_ocr, saved_original_path, _ = save_exit_image_and_recognize_plate(exit_image_file)

            if saved_original_path:
                exit_image_path_to_save = saved_original_path

            if plate_text_from_ocr and "LOI" not in plate_text_from_ocr.upper() and "KHONG" not in plate_text_from_ocr.upper():
                bien_so_final = plate_text_from_ocr.upper()
            else:
                if bien_so_nhap_tay:
                    bien_so_final = bien_so_nhap_tay
        elif bien_so_nhap_tay:
            bien_so_final = bien_so_nhap_tay

        # <--- THAY ĐỔI: Nếu không có ảnh mới, dùng lại đường dẫn đã lưu ở bước 1
        if not exit_image_path_to_save and saved_path_from_hidden_input:
            exit_image_path_to_save = saved_path_from_hidden_input

        if not bien_so_final and 'action_tim_xe' in request.POST:
            context['thong_bao_loi'] = "Vui lòng nhập biển số hoặc upload ảnh hợp lệ."
            return render(request, 'parking_management/xe_ra_khoi_bai.html', context)

        context['bien_so_da_nhap'] = bien_so_final
        # <--- THAY ĐỔI: Truyền đường dẫn ảnh đã lưu ra template để đưa vào hidden input
        context['saved_exit_image_path'] = exit_image_path_to_save

        lich_su_dang_xu_ly = ParkingHistory.objects.filter(
            (Q(VehicleID__BienSoXe__iexact=bien_so_final) | Q(
                ProcessedLicensePlateEntry__iexact=bien_so_final)),
            ExitTime__isnull=True,
            Status='IN_YARD'
        ).select_related('VehicleID', 'VehicleID__VehicleTypeID', 'VehicleID__KhachThueID', 'VehicleTypeID').first()

        context['lich_su_gui_xe_hien_tai'] = lich_su_dang_xu_ly

        if lich_su_dang_xu_ly:
            entry_time_cho_hien_thi = lich_su_dang_xu_ly.EntryTime

            if 'action_tinh_tien_va_cho_ra' in request.POST:
                lich_su_dang_xu_ly.ExitTime = timezone.now()

                # CẬP NHẬT ĐƯỜNG DẪN ẢNH VÀ BIỂN SỐ LÚC RA VÀO CSDL
                # Dòng này bây giờ sẽ nhận đúng giá trị từ biến exit_image_path_to_save
                lich_su_dang_xu_ly.ExitVehicleImagePath = exit_image_path_to_save
                lich_su_dang_xu_ly.ProcessedLicensePlateExit = bien_so_final

                phi_gui_xe = 0
                rules_applied_info = []

                if lich_su_dang_xu_ly.VehicleID and lich_su_dang_xu_ly.VehicleID.HasMonthlyTicket:
                    lich_su_dang_xu_ly.WasMonthlyTicketUsed = True
                    context['thong_bao_thanh_cong'] = f"Xe {bien_so_final} của khách thuê sử dụng vé tháng. Cho xe ra."
                else:
                    current_vehicle_type = lich_su_dang_xu_ly.VehicleTypeID
                    if not current_vehicle_type:
                        if lich_su_dang_xu_ly.VehicleID:
                            current_vehicle_type = lich_su_dang_xu_ly.VehicleID.VehicleTypeID
                        else:
                            try:
                                current_vehicle_type = VehicleTypes.objects.get(TypeName='Xe máy')
                            except VehicleTypes.DoesNotExist:
                                context['thong_bao_loi'] = "Lỗi: Không tìm thấy loại xe 'Xe máy' mặc định."
                                return render(request, 'parking_management/xe_ra_khoi_bai.html', context)

                    if current_vehicle_type:
                        phi_gui_xe, rules_applied_info = calculate_parking_fee_detailed(
                            entry_time_cho_hien_thi, lich_su_dang_xu_ly.ExitTime, current_vehicle_type
                        )
                        if rules_applied_info and not any("Không có quy tắc" in s for s in rules_applied_info):
                            context['thong_bao_thanh_cong'] = (f"Đã tính tiền cho xe {bien_so_final}. "
                                                               f"Tổng số tiền: {phi_gui_xe} VND. Cho xe ra.")
                        elif rules_applied_info and "Không có quy tắc" in rules_applied_info[0]:
                            context['thong_bao_thanh_cong'] = rules_applied_info[
                                                                  0] + f" Xe {bien_so_final} ra không tính phí."
                            phi_gui_xe = Decimal('0.00')
                        else:
                            context['thong_bao_thanh_cong'] = (
                                f"Không xác định được quy tắc tính phí cho xe {bien_so_final}. "
                                f"Cho xe ra không tính phí.")
                            phi_gui_xe = Decimal('0.00')
                    else:
                        context['thong_bao_loi'] = "Không thể xác định loại xe để tính phí."
                        phi_gui_xe = Decimal('0.00')

                lich_su_dang_xu_ly.CalculatedFee = phi_gui_xe
                lich_su_dang_xu_ly.Status = 'EXITED'
                lich_su_dang_xu_ly.save()

                context['tien_phai_tra'] = lich_su_dang_xu_ly.CalculatedFee
                context['entry_time_display'] = entry_time_cho_hien_thi
                context['exit_time_display'] = lich_su_dang_xu_ly.ExitTime
                context['lich_su_gui_xe_hien_tai'] = None
            else:  # Logic khi bấm nút "Tìm xe trong bãi"
                if lich_su_dang_xu_ly.VehicleID:
                    context['thong_bao_text'] = (
                        f"Tìm thấy xe {lich_su_dang_xu_ly.VehicleID.BienSoXe} của khách thuê "
                        f"{lich_su_dang_xu_ly.VehicleID.KhachThueID.HoVaTen} đang trong bãi.")
                else:
                    context['thong_bao_text'] = (f"Tìm thấy xe khách vãng lai {bien_so_final} đang trong bãi.")
                context[
                    'co_ve_thang'] = lich_su_dang_xu_ly.VehicleID.HasMonthlyTicket if lich_su_dang_xu_ly.VehicleID else False
                context['thoi_gian_vao'] = lich_su_dang_xu_ly.EntryTime
        else:
            context['thong_bao_loi'] = f"Không tìm thấy xe có biển số '{bien_so_final}' đang trong bãi."

    return render(request, 'parking_management/xe_ra_khoi_bai.html', context)


# --- Các View CRUD cho KhachThue ---
@login_required
def khachthue_list_view(request):
    # Sắp xếp theo KhachThueID tăng dần
    danh_sach_khach_thue = KhachThue.objects.all().order_by('KhachThueID')
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
    danh_sach_xe = Vehicle.objects.select_related('KhachThueID', 'VehicleTypeID').all().order_by('VehicleID')
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
    danh_sach_loai_xe = VehicleTypes.objects.all().order_by('VehicleTypeID')
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
    danh_sach_quy_tac = MonthlyTicketRules.objects.select_related('VehicleTypeID').all().order_by('MonthlyRuleID')
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
        'PerTurnRuleID') # Sửa ở đây: sắp xếp theo ID của VehicleTypeID trước
    context = {
        'danh_sach_quy_tac': danh_sach_quy_tac,
        'page_title': 'Danh Sách Quy Tắc Giá Vé Lượt' # Thêm page_title nếu template của bạn dùng
    }
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
        'VehicleID__VehicleTypeID'
    ).order_by('-RecordID')

    # --- THÊM DÒNG NÀY ---
    # Đếm số xe hiện đang ở trong bãi
    xe_trong_bai_count = ParkingHistory.objects.filter(Status='IN_YARD').count()

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
        'page_title': 'Lịch Sử Xe Ra/Vào Bãi',
        'xe_trong_bai_count': xe_trong_bai_count, # --- THÊM VÀO CONTEXT ---
    }
    return render(request, 'parking_management/parkinghistory_list.html', context)


@login_required
def thong_ke_doanh_thu_ngay_view(request):
    form = DateSelectionForm(request.GET or None)
    selected_date_obj = None
    tong_doanh_thu_ngay = 0 # Đã sửa ở lần trước
    danh_sach_luot_gui = None

    if form.is_valid():
        selected_date_obj = form.cleaned_data['selected_date']

        current_project_tz = timezone.get_current_timezone()

        start_of_day_local_naive = datetime.combine(selected_date_obj, time.min)
        start_of_day_local_aware = timezone.make_aware(start_of_day_local_naive, current_project_tz)

        end_of_day_local_naive = datetime.combine(selected_date_obj, time.max)
        end_of_day_local_aware = timezone.make_aware(end_of_day_local_naive, current_project_tz)

        start_of_day_utc = start_of_day_local_aware.astimezone(pytz.utc)
        end_of_day_utc = end_of_day_local_aware.astimezone(pytz.utc)

        danh_sach_luot_gui = ParkingHistory.objects.filter(
            ExitTime__gte=start_of_day_utc,
            ExitTime__lte=end_of_day_utc,
            Status='EXITED',
            WasMonthlyTicketUsed=False,
            CalculatedFee__isnull=False
        ).select_related(
            # --- THAY ĐỔI Ở CÁC DÒNG DƯỚI ĐÂY ---
            'VehicleID',
            'VehicleID__VehicleTypeID',
            'VehicleID__KhachThueID'
            # Đã xóa 'PerTurnRuleAppliedID' khỏi đây
        ).order_by('ExitTime')

        aggregation = danh_sach_luot_gui.aggregate(total_revenue=Sum('CalculatedFee'))
        tong_doanh_thu_ngay = aggregation['total_revenue'] if aggregation['total_revenue'] is not None else 0 # Đã sửa ở lần trước

    context = {
        'form': form,
        'selected_date': selected_date_obj,
        'tong_doanh_thu_ngay': tong_doanh_thu_ngay,
        'danh_sach_luot_gui': danh_sach_luot_gui,
        'page_title': 'Thống Kê Doanh Thu Vé Lượt Theo Ngày'
    }
    return render(request, 'parking_management/thong_ke_doanh_thu_ngay.html', context)


@login_required
def thong_ke_doanh_thu_thang_view(request):
    form = MonthYearSelectionForm(request.GET or None)
    selected_month_num = None
    selected_year_num = None
    tong_doanh_thu_ve_luot_thang = 0
    danh_sach_luot_gui_thang = None
    # Thêm phần thống kê vé tháng (sẽ phức tạp hơn)
    # so_luong_ve_thang_ban_duoc = 0
    # doanh_thu_tu_ve_thang = Decimal('0.00')

    if form.is_valid():
        selected_month_num = int(form.cleaned_data['selected_month'])
        selected_year_num = int(form.cleaned_data['selected_year'])

        # Xác định ngày đầu và ngày cuối của tháng đã chọn
        _, num_days_in_month = monthrange(selected_year_num, selected_month_num)
        start_date_of_month = datetime(selected_year_num, selected_month_num, 1)
        end_date_of_month = datetime(selected_year_num, selected_month_num, num_days_in_month)

        current_project_tz = timezone.get_current_timezone()

        start_of_month_local_aware = timezone.make_aware(datetime.combine(start_date_of_month, time.min),
                                                         current_project_tz)
        end_of_month_local_aware = timezone.make_aware(datetime.combine(end_date_of_month, time.max),
                                                       current_project_tz)

        start_of_month_utc = start_of_month_local_aware.astimezone(pytz.utc)
        end_of_month_utc = end_of_month_local_aware.astimezone(pytz.utc)

        # 1. Thống kê doanh thu vé lượt trong tháng
        danh_sach_luot_gui_thang = ParkingHistory.objects.filter(
            ExitTime__gte=start_of_month_utc,
            ExitTime__lte=end_of_month_utc,
            Status='EXITED',
            WasMonthlyTicketUsed=False,
            CalculatedFee__isnull=False
        ).select_related('VehicleID',
                         'VehicleID__VehicleTypeID')  # Bỏ PerTurnRuleAppliedID nếu không hiển thị chi tiết rule

        aggregation_luot = danh_sach_luot_gui_thang.aggregate(total_revenue_luot=Sum('CalculatedFee'))
        tong_doanh_thu_ve_luot_thang = aggregation_luot['total_revenue_luot'] if aggregation_luot[
                                                                                     'total_revenue_luot'] is not None else 0

        # 2. Thống kê vé tháng (Phần này cần logic phức tạp hơn dựa trên cách bạn quản lý việc thu tiền vé tháng)
        # Ví dụ đơn giản: Đếm số xe đang có HasMonthlyTicket=True trong tháng đó
        # (Cách này không phản ánh đúng doanh thu nếu không có bảng ghi nhận giao dịch vé tháng)
        #
        # Hoặc, nếu bạn có một cách để xác định xe nào đã "mua" vé tháng trong tháng đó:
        # vehicles_with_monthly_ticket_in_month = Vehicle.objects.filter(
        #     HasMonthlyTicket=True,
        #     # Thêm điều kiện để lọc theo tháng/năm mà vé được kích hoạt/mua
        #     # Ví dụ: nếu bạn có trường `ngay_kich_hoat_ve_thang` trong model Vehicle:
        #     # ngay_kich_hoat_ve_thang__year=selected_year_num,
        #     # ngay_kich_hoat_ve_thang__month=selected_month_num
        # ).select_related('VehicleTypeID', 'VehicleTypeID__monthlyticketrules')
        # # Giả sử MonthlyTicketRules có related_name là 'monthlyticketrules' từ VehicleType
        # # Hoặc query trực tiếp MonthlyTicketRules
        #
        # for vehicle_ve_thang in vehicles_with_monthly_ticket_in_month:
        #     try:
        #         # Tìm quy tắc giá vé tháng cho loại xe này
        #         rule_ve_thang = MonthlyTicketRules.objects.get(VehicleTypeID=vehicle_ve_thang.VehicleTypeID)
        #         doanh_thu_tu_ve_thang += rule_ve_thang.PricePerMonth
        #         so_luong_ve_thang_ban_duoc += 1
        #     except MonthlyTicketRules.DoesNotExist:
        #         pass # Bỏ qua nếu không có rule giá cho loại xe này
        #     except MonthlyTicketRules.MultipleObjectsReturned:
        #         # Xử lý nếu có nhiều rule cho cùng 1 loại xe (nên tránh trong thiết kế)
        #         rule_ve_thang = MonthlyTicketRules.objects.filter(VehicleTypeID=vehicle_ve_thang.VehicleTypeID).first()
        #         if rule_ve_thang:
        #             doanh_thu_tu_ve_thang += rule_ve_thang.PricePerMonth
        #             so_luong_ve_thang_ban_duoc += 1

        # Tạm thời, chúng ta sẽ chỉ tập trung vào doanh thu vé lượt
        # Doanh thu vé tháng sẽ cần một cơ chế ghi nhận giao dịch cụ thể hơn.
        # Bạn có thể hiển thị số lượng xe đang được đánh dấu HasMonthlyTicket (nhưng không phải là doanh thu tháng đó)

    context = {
        'form': form,
        'selected_month': datetime(2000, selected_month_num, 1) if selected_month_num else None,  # Để lấy tên tháng
        'selected_year': selected_year_num,
        'tong_doanh_thu_ve_luot_thang': tong_doanh_thu_ve_luot_thang,
        'danh_sach_luot_gui_thang': danh_sach_luot_gui_thang,  # Để có thể hiển thị chi tiết nếu muốn
        # 'so_luong_ve_thang_ban_duoc': so_luong_ve_thang_ban_duoc,
        # 'doanh_thu_tu_ve_thang': doanh_thu_tu_ve_thang,
        # 'tong_doanh_thu_thang': tong_doanh_thu_ve_luot_thang + doanh_thu_tu_ve_thang,
        'page_title': 'Thống Kê Doanh Thu Theo Tháng'
    }
    return render(request, 'parking_management/thong_ke_doanh_thu_thang.html', context)