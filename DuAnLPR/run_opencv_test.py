import cv2
import numpy as np
import os
import sys
from pathlib import Path
import uuid
import pytesseract  # Đảm bảo đã import

# --- Cấu hình cho script test ---
BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT_TEST = os.path.join(str(BASE_DIR), 'media_test_opencv_inside_project')
SAVE_DIR_TEST = os.path.join(MEDIA_ROOT_TEST, 'vehicle_entries_ocr_test')
if not os.path.exists(SAVE_DIR_TEST):
    os.makedirs(SAVE_DIR_TEST)


# --- QUAN TRỌNG: CẤU HÌNH TESSERACT ---
# Nếu Tesseract không nằm trong PATH, bỏ comment và SỬA ĐÚNG ĐƯỜNG DẪN dưới đây
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def process_image_for_plate_ocr(image_file_path):  # Tên hàm đã được sửa ở đây
    """
    1. Đọc ảnh.
    2. Tiền xử lý ảnh (đơn giản).
    3. Tìm và cắt một vùng 4 cạnh tiềm năng (đơn giản hóa).
    4. Tiền xử lý vùng cắt cho OCR.
    5. Cố gắng OCR ký tự trên vùng đã cắt.
    """
    try:
        img_original = cv2.imread(image_file_path)
        if img_original is None:
            print(f"Lỗi: Không thể đọc ảnh từ {image_file_path}")
            return "LOI_DOC_ANH", None, None

        img_for_processing = img_original.copy()

        cv2.imshow("0 - Original Image", img_original)
        cv2.waitKey(0)

        # 1. Tiền xử lý ảnh (cho việc khoanh vùng)
        gray_img = cv2.cvtColor(img_for_processing, cv2.COLOR_BGR2GRAY)
        # cv2.imshow("1 - Grayscale Image", gray_img)
        # cv2.waitKey(0)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced_gray = clahe.apply(gray_img)  # BIẾN NÀY ĐÃ ĐƯỢC ĐỊNH NGHĨA Ở ĐÂY
        # cv2.imshow("1.1 - Contrast Enhanced Gray", contrast_enhanced_gray)
        # cv2.waitKey(0)

        blurred_img = cv2.GaussianBlur(contrast_enhanced_gray, (5, 5), 0)
        # cv2.imshow("2 - Blurred Image", blurred_img)
        # cv2.waitKey(0)

        edged_img = cv2.Canny(blurred_img, 50, 150)
        cv2.imshow("3 - Edged Image", edged_img)
        cv2.waitKey(0)

        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        license_plate_contour_final = None
        img_with_selected_contour = img_original.copy()

        for contour_candidate in contours:
            perimeter = cv2.arcLength(contour_candidate, True)
            approx_polygon = cv2.approxPolyDP(contour_candidate, 0.02 * perimeter, True)
            if len(approx_polygon) == 4:
                (x_contour, y_contour, w_contour, h_contour) = cv2.boundingRect(approx_polygon)
                if (w_contour >= 20 and h_contour >= 10) and \
                        (w_contour < img_original.shape[1] * 0.95 and h_contour < img_original.shape[0] * 0.95):
                    license_plate_contour_final = approx_polygon
                    print(f"DEBUG: Selected 4-sided contour: w={w_contour}, h={h_contour}")
                    cv2.drawContours(img_with_selected_contour, [license_plate_contour_final], -1, (0, 0, 255), 3)
                    break

        if license_plate_contour_final is not None:
            cv2.imshow("4 - Selected Contour (Potential Plate)", img_with_selected_contour)
            cv2.waitKey(0)
        else:
            print("DEBUG: No 4-sided contour selected as potential plate.")

        recognized_plate_text_result = "KHONG_TIM_THAY_VUNG_4_CANH"
        path_to_cropped_ocr_ready_image_result = None
        original_image_basename = os.path.basename(image_file_path)
        # ĐỊNH NGHĨA BIẾN NÀY Ở ĐÂY
        original_image_relative_path = os.path.join(os.path.basename(SAVE_DIR_TEST),
                                                    "original_for_django_" + original_image_basename)

        if license_plate_contour_final is not None:
            (x, y, w, h) = cv2.boundingRect(license_plate_contour_final)
            if w > 0 and h > 0:
                # Cắt từ ảnh xám đã tăng tương phản (contrast_enhanced_gray)
                cropped_plate_img = contrast_enhanced_gray[y:y + h, x:x + w]

                cv2.imshow("5.0 - Cropped Region (Input for OCR Preprocessing)", cropped_plate_img)
                cv2.waitKey(0)

                ocr_input_img_for_processing = cropped_plate_img.copy()
                target_height_ocr = 500
                current_height_ocr = ocr_input_img_for_processing.shape[0]
                current_width_ocr = ocr_input_img_for_processing.shape[1]  # Thêm dòng này
                if current_height_ocr > 0 and current_width_ocr > 0:
                    if current_height_ocr < target_height_ocr / 1.5 or current_height_ocr > target_height_ocr * 1.5:
                        scale_factor = float(target_height_ocr) / current_height_ocr
                        new_width = int(current_width_ocr * scale_factor)
                        if new_width > 0:
                            ocr_input_img_for_processing = cv2.resize(ocr_input_img_for_processing,
                                                                      (new_width, target_height_ocr),
                                                                      interpolation=cv2.INTER_LANCZOS4)
                            cv2.imshow("5.1 - Resized for OCR", ocr_input_img_for_processing)
                            cv2.waitKey(0)

                (_, ocr_ready_img) = cv2.threshold(ocr_input_img_for_processing, 0, 255,
                                                   cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                cv2.imshow("5.2 - OCR Ready (Thresholded)", ocr_ready_img)
                cv2.waitKey(0)

                try:
                    char_whitelist = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-.'
                    custom_config = f'--oem 3 --psm 11 -c tessedit_char_whitelist={char_whitelist}'
                    ocr_text = pytesseract.image_to_string(ocr_ready_img, lang='eng', config=custom_config)
                    cleaned_ocr_text = "".join(filter(lambda char: char in char_whitelist, ocr_text.upper()))
                    recognized_plate_text_result = "".join(cleaned_ocr_text.split())
                    if not recognized_plate_text_result:
                        recognized_plate_text_result = "OCR_KHONG_RA_KY_TU"
                    else:
                        print(f"DEBUG: OCR Raw Text: '{ocr_text.strip()}'")
                        print(f"DEBUG: OCR Cleaned Text: '{recognized_plate_text_result}'")
                except pytesseract.TesseractNotFoundError:
                    print(
                        "LỖI PYTESSERACT: Tesseract không được tìm thấy hoặc chưa được cấu hình đúng 'tesseract_cmd'.")
                    recognized_plate_text_result = "LOI_TESSERACT_NOT_FOUND"
                except Exception as ocr_error:
                    print(f"Lỗi trong quá trình OCR: {ocr_error}")
                    recognized_plate_text_result = "LOI_OCR"

                name_part_orig, _ = os.path.splitext(os.path.basename(image_file_path))
                cropped_filename_save = f"ocr_ready_{name_part_orig}_{uuid.uuid4().hex[:6]}.png"
                path_to_cropped_ocr_ready_image_full = os.path.join(SAVE_DIR_TEST, cropped_filename_save)
                cv2.imwrite(path_to_cropped_ocr_ready_image_full, ocr_ready_img)
                path_to_cropped_ocr_ready_image_result = os.path.join(os.path.basename(SAVE_DIR_TEST),
                                                                      cropped_filename_save)
            else:
                recognized_plate_text_result = "LOI_KICH_THUOC_CAT"
        else:
            print("DEBUG (test script): No 4-sided contour was selected.")

        cv2.destroyAllWindows()
        # Trả về: (chuỗi biển số nhận dạng, đường dẫn ảnh gốc (tạm), đường dẫn ảnh đã cắt và xử lý cho OCR)
        return recognized_plate_text_result, original_image_relative_path, path_to_cropped_ocr_ready_image_result

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi xử lý ảnh trong test script: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        return "LOI_XU_LY_ANH_TRONG_TEST", None, None


# Khối if __name__ == '__main__' để chạy script
if __name__ == '__main__':
    test_data_dir = os.path.join(str(BASE_DIR), "TestData")
    image_name_to_test = "bienso_test_4.jpg"

    test_image_file = os.path.join(test_data_dir, image_name_to_test)

    if not os.path.isfile(test_image_file):
        print(f"LỖI: File ảnh thử nghiệm không tồn tại: {test_image_file}")
    else:
        print(f"Đang xử lý ảnh: {test_image_file}")
        # Gọi hàm đã có tên đúng
        plate_text, original_path_django, cropped_ocr_path = process_image_for_plate_ocr(test_image_file)

        print("-" * 30)
        print(f"Kết quả nhận dạng biển số: {plate_text}")
        if original_path_django:
            print(f"Đường dẫn ảnh gốc (tham khảo cho Django): {original_path_django}")
        if cropped_ocr_path:
            print(f"Ảnh đã xử lý cho OCR được lưu tại (tương đối): {cropped_ocr_path}")