# parking_management/image_processing.py

import cv2
import numpy as np
import os
from django.conf import settings
import uuid


def save_uploaded_image_and_recognize_plate(uploaded_file):
    """
    Lưu ảnh được upload, xử lý để tìm biển số.
    Phiên bản này đơn giản hóa: tìm contour 4 cạnh đầu tiên (không quá nhỏ)
    và bỏ qua các bộ lọc chi tiết về tỷ lệ, diện tích.
    """
    try:
        # Tạo tên file duy nhất và đường dẫn lưu file gốc
        original_filename_part, original_extension = os.path.splitext(uploaded_file.name)
        if not original_extension:  # Nếu không có phần mở rộng, mặc định là .jpg
            original_extension = ".jpg"

        unique_id = uuid.uuid4().hex[:8]
        filename_to_save = f"{original_filename_part}_{unique_id}{original_extension}"

        save_dir = os.path.join(settings.MEDIA_ROOT, 'vehicle_entries')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        original_image_full_path = os.path.join(save_dir, filename_to_save)

        # Lưu file ảnh gốc được upload
        with open(original_image_full_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Bắt đầu xử lý ảnh bằng OpenCV từ file đã lưu
        img_original_cv = cv2.imread(original_image_full_path)
        if img_original_cv is None:
            print(f"Lỗi: Không thể đọc ảnh từ {original_image_full_path} bằng OpenCV")
            return "LOI_DOC_ANH", None, None

        img_for_processing = img_original_cv.copy()

        # 1. Tiền xử lý ảnh
        gray_img = cv2.cvtColor(img_for_processing, cv2.COLOR_BGR2GRAY)

        # Tăng độ tương phản (ví dụ dùng CLAHE) - Bạn có thể giữ lại hoặc bỏ nếu thấy không hiệu quả
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced_gray = clahe.apply(gray_img)

        # Làm mờ để giảm nhiễu
        blurred_img = cv2.GaussianBlur(contrast_enhanced_gray, (5, 5), 0)

        # Phát hiện cạnh bằng Canny (Ngưỡng này bạn có thể đã tìm được giá trị tương đối ổn)
        edged_img = cv2.Canny(blurred_img, 50, 150)  # Ví dụ: (50,150) hoặc (30,100)

        # 2. Phát hiện vùng chứa biển số
        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]  # Lấy 10 contour lớn nhất

        license_plate_contour_final = None

        for contour_candidate in contours:
            perimeter = cv2.arcLength(contour_candidate, True)
            approx_polygon = cv2.approxPolyDP(contour_candidate, 0.02 * perimeter, True)

            if len(approx_polygon) == 4:  # Điều kiện chính: là hình 4 cạnh
                (x, y, w, h) = cv2.boundingRect(approx_polygon)

                # Bộ lọc cơ bản: không quá nhỏ và không quá lớn (chiếm gần hết ảnh)
                if (w >= 20 and h >= 10) and \
                        (w < img_original_cv.shape[1] * 0.95 and h < img_original_cv.shape[0] * 0.95):
                    license_plate_contour_final = approx_polygon
                    print(f"DEBUG: Found and selected first valid 4-sided contour: w={w}, h={h}")
                    break  # Lấy contour 4 cạnh hợp lệ đầu tiên tìm được

        recognized_plate_text_result = "CHUA_NHAN_DANG"
        relative_original_image_path = os.path.join('vehicle_entries', filename_to_save)
        relative_cropped_image_path = None

        if license_plate_contour_final is not None:
            (x, y, w, h) = cv2.boundingRect(license_plate_contour_final)
            if w > 0 and h > 0:
                cropped_plate_img = contrast_enhanced_gray[y:y + h, x:x + w]

                cropped_filename_base = f"cropped_{original_filename_part}_{unique_id}.jpg"
                cropped_image_full_path = os.path.join(save_dir, cropped_filename_base)
                cv2.imwrite(cropped_image_full_path, cropped_plate_img)
                relative_cropped_image_path = os.path.join('vehicle_entries', cropped_filename_base)

                recognized_plate_text_result = "DA_TIM_THAY_VUNG_4_CANH"
                # SAU NÀY: recognized_plate_text_result = perform_ocr(cropped_plate_img)
            else:
                recognized_plate_text_result = "LOI_KICH_THUOC_CAT"

        return recognized_plate_text_result, relative_original_image_path, relative_cropped_image_path

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi xử lý ảnh trong Django: {e}")
        import traceback
        traceback.print_exc()
        if 'original_image_full_path' in locals() and os.path.exists(original_image_full_path):
            relative_original_image_path = os.path.join('vehicle_entries', os.path.basename(original_image_full_path))
            return "LOI_XU_LY_ANH", relative_original_image_path, None
        return "LOI_XU_LY_ANH", None, None