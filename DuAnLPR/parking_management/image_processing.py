import cv2
import numpy as np
import os
from django.conf import settings
import uuid
import pytesseract


# --- HÀM XỬ LÝ ẢNH CỐT LÕI ---
# Hàm này sẽ được gọi bởi cả chức năng xe vào và xe ra
def _recognize_plate_from_image(image_path):
    """
    Hàm nội bộ để thực hiện tất cả các bước nhận dạng từ một đường dẫn ảnh.
    Trả về chuỗi ký tự đã nhận dạng.
    """
    try:
        img_original_cv = cv2.imread(image_path)
        if img_original_cv is None:
            return "LOI_DOC_ANH"

        # 1. Tiền xử lý ảnh (cho việc khoanh vùng)
        gray_img = cv2.cvtColor(img_original_cv, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced_gray = clahe.apply(gray_img)
        blurred_img = cv2.GaussianBlur(contrast_enhanced_gray, (5, 5), 0)
        edged_img = cv2.Canny(blurred_img, 50, 150)

        # 2. Phát hiện vùng 4 cạnh (biển số tiềm năng)
        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        license_plate_contour_final = None
        for contour_candidate in contours:
            perimeter = cv2.arcLength(contour_candidate, True)
            approx_polygon = cv2.approxPolyDP(contour_candidate, 0.02 * perimeter, True)
            if len(approx_polygon) == 4:
                (x_c, y_c, w_c, h_c) = cv2.boundingRect(approx_polygon)
                if (w_c >= 20 and h_c >= 10) and (
                        w_c < img_original_cv.shape[1] * 0.95 and h_c < img_original_cv.shape[0] * 0.95):
                    license_plate_contour_final = approx_polygon
                    break

        if license_plate_contour_final is None:
            return "KHONG_TIM_THAY_BIEN_SO"

        # 3. Cắt và xử lý ảnh cho OCR
        (x, y, w, h) = cv2.boundingRect(license_plate_contour_final)
        if not (w > 0 and h > 0):
            return "LOI_KICH_THUOC_CAT"

        cropped_plate_img = contrast_enhanced_gray[y:y + h, x:x + w]

        # 4. Tiền xử lý vùng ảnh đã cắt để tối ưu OCR
        # Resize để chuẩn hóa chiều cao, giúp Tesseract nhận dạng tốt hơn
        target_height_ocr = 60
        current_height_ocr, current_width_ocr = cropped_plate_img.shape[:2]
        if current_height_ocr > 0 and current_width_ocr > 0:
            scale_factor = float(target_height_ocr) / current_height_ocr
            new_width = int(current_width_ocr * scale_factor)
            if new_width > 0:
                resized_for_ocr = cv2.resize(cropped_plate_img, (new_width, target_height_ocr),
                                             interpolation=cv2.INTER_LANCZOS4)
            else:
                resized_for_ocr = cropped_plate_img
        else:
            resized_for_ocr = cropped_plate_img

        # Áp dụng ngưỡng nhị phân (Thresholding)
        (_, ocr_ready_img) = cv2.threshold(resized_for_ocr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 5. Thực hiện OCR
        char_whitelist = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-.'
        custom_config = f'--oem 3 --psm 7 -c tessedit_char_whitelist={char_whitelist}'

        ocr_text = pytesseract.image_to_string(ocr_ready_img, lang='eng', config=custom_config)

        cleaned_ocr_text = "".join(filter(lambda char: char in char_whitelist, ocr_text.upper()))
        recognized_plate_text = "".join(cleaned_ocr_text.split())

        if not recognized_plate_text:
            return "OCR_KHONG_RA_KY_TU"

        return recognized_plate_text

    except pytesseract.TesseractNotFoundError:
        return "LOI_TESSERACT_NOT_FOUND"
    except Exception as e:
        print(f"Lỗi trong hàm _recognize_plate_from_image: {e}")
        return "LOI_XU_LY_ANH"


# --- HÀM WRAPPER CHO XE VÀO ---
def save_entry_image_and_recognize_plate(uploaded_file):
    """Lưu ảnh xe vào và gọi hàm nhận dạng cốt lõi."""
    try:
        # 1. Lưu file vào thư mục 'vehicle_entries'
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

        # 2. Gọi hàm nhận dạng cốt lõi
        plate_text = _recognize_plate_from_image(full_path)

        # Hàm này trả về cả biển số nhận dạng và đường dẫn ảnh đã lưu
        return plate_text, relative_path, None

    except Exception as e:
        print(f"Lỗi khi lưu ảnh xe vào: {e}")
        return "LOI_LUU_ANH_VAO", None, None


# --- HÀM WRAPPER CHO XE RA ---
def save_exit_image_and_recognize_plate(uploaded_file):
    """Lưu ảnh xe ra và gọi hàm nhận dạng cốt lõi."""
    try:
        # 1. Lưu file vào thư mục 'vehicle_exits'
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

        # 2. Gọi hàm nhận dạng cốt lõi
        plate_text = _recognize_plate_from_image(full_path)

        return plate_text, relative_path, None

    except Exception as e:
        print(f"Lỗi khi lưu ảnh xe ra: {e}")
        return "LOI_LUU_ANH_RA", None, None