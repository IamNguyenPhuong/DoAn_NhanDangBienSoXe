# image_processing.py (PHIÊN BẢN NÂNG CẤP)

import os
import uuid
from django.conf import settings
# --- THAY ĐỔI 1: Import service mới ---
from services.ocr_service import recognize_license_plate
# --- HẾT THAY ĐỔI 1 ---


# --- THAY ĐỔI 2: Xóa toàn bộ hàm _recognize_plate_from_image cũ ---
# Code cũ dùng cv2 và pytesseract đã được xóa bỏ.
# --- HẾT THAY ĐỔI 2 ---


# --- HÀM WRAPPER CHO XE VÀO ---
def save_entry_image_and_recognize_plate(uploaded_file):
    """Lưu ảnh xe vào và gọi hàm nhận dạng của Gemini."""
    try:
        # 1. Lưu file vào thư mục 'vehicle_entries' (giữ nguyên logic cũ)
        filename_part, ext = os.path.splitext(uploaded_file.name)
        unique_filename = f"entry_{filename_part}_{uuid.uuid4().hex[:6]}{ext or '.jpg'}"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'vehicle_entries')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        full_path = os.path.join(save_dir, unique_filename)
        with open(full_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        relative_path = os.path.join('vehicle_entries', unique_filename)

        # --- THAY ĐỔI 3: Gọi service Gemini thay vì hàm OCR cũ ---
        # Đọc lại dữ liệu ảnh vừa lưu để gửi đi
        with open(full_path, 'rb') as f_read:
            image_data = f_read.read()
            mime_type = getattr(uploaded_file, 'content_type', 'image/jpeg')

        # Gọi service nhận dạng
        result = recognize_license_plate(image_data, mime_type)

        # Xử lý kết quả trả về từ service
        if result['status'] == 'success':
            plate_text = result['text']
        else:
            # Nếu có lỗi, trả về thông báo lỗi để view xử lý
            plate_text = f"Lỗi: {result['message']}"
        # --- HẾT THAY ĐỔI 3 ---

        # Trả về biển số và đường dẫn ảnh, giữ nguyên định dạng để views.py không bị lỗi
        return plate_text, relative_path, None

    except Exception as e:
        print(f"Lỗi khi lưu ảnh xe vào hoặc gọi OCR: {e}")
        return "LOI_LUU_ANH_VAO", None, None


# --- HÀM WRAPPER CHO XE RA ---
def save_exit_image_and_recognize_plate(uploaded_file):
    """Lưu ảnh xe ra và gọi hàm nhận dạng của Gemini."""
    try:
        # 1. Lưu file vào thư mục 'vehicle_exits' (giữ nguyên logic cũ)
        filename_part, ext = os.path.splitext(uploaded_file.name)
        unique_filename = f"exit_{filename_part}_{uuid.uuid4().hex[:6]}{ext or '.jpg'}"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'vehicle_exits')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        full_path = os.path.join(save_dir, unique_filename)
        with open(full_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        relative_path = os.path.join('vehicle_exits', unique_filename)

        # --- THAY ĐỔI 4: Gọi service Gemini cho xe ra ---
        with open(full_path, 'rb') as f_read:
            image_data = f_read.read()
            mime_type = getattr(uploaded_file, 'content_type', 'image/jpeg')

        result = recognize_license_plate(image_data, mime_type)

        if result['status'] == 'success':
            plate_text = result['text']
        else:
            plate_text = f"Lỗi: {result['message']}"
        # --- HẾT THAY ĐỔI 4 ---

        return plate_text, relative_path, None

    except Exception as e:
        print(f"Lỗi khi lưu ảnh xe ra hoặc gọi OCR: {e}")
        return "LOI_LUU_ANH_RA", None, None