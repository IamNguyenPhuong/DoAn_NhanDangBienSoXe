import cv2
import numpy as np
import os
from django.conf import settings
import uuid
import pytesseract

# --- QUAN TRỌNG: CẤU HÌNH TESSERACT ---
# Nếu Tesseract không nằm trong PATH của môi trường server,
# bạn PHẢI bỏ comment dòng dưới và SỬA ĐÚNG ĐƯỜNG DẪN.
# Ví dụ trên Windows Server:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Ví dụ trên Linux Server (nếu tesseract không nằm trong PATH mặc định):
# pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract' # Hoặc /usr/local/bin/tesseract

def save_uploaded_image_and_recognize_plate(uploaded_file):
    """
    Lưu ảnh được upload, thực hiện các bước xử lý ảnh để khoanh vùng biển số,
    tiền xử lý vùng cắt, và OCR ký tự.
    """
    try:
        # Tạo tên file duy nhất và đường dẫn lưu file gốc
        original_filename_part, original_extension = os.path.splitext(uploaded_file.name)
        if not original_extension:
            original_extension = ".jpg"  # Mặc định nếu không có phần mở rộng

        unique_id = uuid.uuid4().hex[:11]
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
            print(f"Lỗi Django (image_processing): Không thể đọc ảnh từ {original_image_full_path}")
            relative_original_image_path_on_error = os.path.join('vehicle_entries', filename_to_save)
            return "LOI_DOC_ANH", relative_original_image_path_on_error, None

        img_for_processing = img_original_cv.copy()

        # 1. Tiền xử lý ảnh (cho việc khoanh vùng)
        gray_img = cv2.cvtColor(img_for_processing, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced_gray = clahe.apply(gray_img)
        blurred_img = cv2.GaussianBlur(contrast_enhanced_gray, (5, 5), 0)
        edged_img = cv2.Canny(blurred_img, 50, 150)  # Ngưỡng Canny bạn đã thấy tương đối ổn

        # 2. Phát hiện vùng 4 cạnh (đơn giản hóa)
        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        license_plate_contour_final = None

        for contour_candidate in contours:
            perimeter = cv2.arcLength(contour_candidate, True)
            approx_polygon = cv2.approxPolyDP(contour_candidate, 0.02 * perimeter, True)
            if len(approx_polygon) == 4:
                (x_contour, y_contour, w_contour, h_contour) = cv2.boundingRect(approx_polygon)
                if (w_contour >= 20 and h_contour >= 10) and \
                        (w_contour < img_original_cv.shape[1] * 0.95 and h_contour < img_original_cv.shape[0] * 0.95):
                    license_plate_contour_final = approx_polygon
                    # print(f"DEBUG Django: Selected 4-sided contour: w={w_contour}, h={h_contour}")
                    break

        recognized_plate_text_result = "KHONG_TIM_THAY_VUNG_4_CANH"
        relative_original_image_path = os.path.join('vehicle_entries', filename_to_save)
        relative_cropped_ocr_ready_image_path = None

        if license_plate_contour_final is not None:
            (x, y, w, h) = cv2.boundingRect(license_plate_contour_final)
            if w > 0 and h > 0:
                cropped_plate_img = contrast_enhanced_gray[y:y + h, x:x + w]

                ocr_input_img_for_processing = cropped_plate_img.copy()
                target_height_ocr = 60
                current_height_ocr = ocr_input_img_for_processing.shape[0]
                current_width_ocr = ocr_input_img_for_processing.shape[1]
                if current_height_ocr > 0 and current_width_ocr > 0:
                    if current_height_ocr < target_height_ocr / 1.5 or current_height_ocr > target_height_ocr * 1.5:
                        scale_factor = float(target_height_ocr) / current_height_ocr
                        new_width = int(current_width_ocr * scale_factor)
                        if new_width > 0:
                            ocr_input_img_for_processing = cv2.resize(ocr_input_img_for_processing,
                                                                      (new_width, target_height_ocr),
                                                                      interpolation=cv2.INTER_LANCZOS4)

                (_, ocr_ready_img) = cv2.threshold(ocr_input_img_for_processing, 0, 255,
                                                   cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

                try:
                    char_whitelist = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-.'
                    custom_config = f'--oem 3 --psm 11 -c tessedit_char_whitelist={char_whitelist}'

                    ocr_text = pytesseract.image_to_string(ocr_ready_img, lang='eng', config=custom_config)

                    cleaned_ocr_text = "".join(filter(lambda char: char in char_whitelist, ocr_text.upper()))
                    recognized_plate_text_result = "".join(cleaned_ocr_text.split())

                    if not recognized_plate_text_result:
                        recognized_plate_text_result = "OCR_KHONG_RA_KY_TU"
                    else:
                        print(f"DEBUG Django: OCR Raw Text: '{ocr_text.strip()}'")
                        print(f"DEBUG Django: OCR Cleaned Text: '{recognized_plate_text_result}'")

                except pytesseract.TesseractNotFoundError:
                    print(
                        "LỖI PYTESSERACT Django: Tesseract không được tìm thấy hoặc chưa được cấu hình đúng 'tesseract_cmd'.")
                    recognized_plate_text_result = "LOI_TESSERACT_NOT_FOUND"
                except Exception as ocr_error:
                    print(f"Lỗi trong quá trình OCR Django: {ocr_error}")
                    recognized_plate_text_result = "LOI_OCR"

                # Lưu ảnh đã sẵn sàng cho OCR (ảnh đen trắng) để kiểm tra (nếu muốn)
                # cropped_filename_save = f"ocr_ready_{original_filename_part}_{unique_id}.png"
                # cropped_ocr_ready_image_full_path = os.path.join(save_dir, cropped_filename_save)
                # cv2.imwrite(cropped_ocr_ready_image_full_path, ocr_ready_img)
                # relative_cropped_ocr_ready_image_path = os.path.join('vehicle_entries', cropped_filename_save)
            else:
                recognized_plate_text_result = "LOI_KICH_THUOC_CAT"
        # else: # Không tìm thấy license_plate_contour_final
        # print("DEBUG Django: No 4-sided contour was selected. OCR will not be performed on cropped.")
        # Nếu bạn muốn OCR trên toàn ảnh khi không tìm thấy contour, thêm logic đó ở đây
        # Dựa trên fallback logic trong run_opencv_test.py

        return recognized_plate_text_result, relative_original_image_path, relative_cropped_ocr_ready_image_path

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi xử lý ảnh trong Django (image_processing.py): {e}")
        import traceback
        traceback.print_exc()
        if 'filename_to_save' in locals():  # Kiểm tra xem biến đã được định nghĩa chưa
            relative_original_image_path_on_error = os.path.join('vehicle_entries', filename_to_save)
            return "LOI_XU_LY_ANH", relative_original_image_path_on_error, None
        return "LOI_XU_LY_ANH", None, None