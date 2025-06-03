import cv2
import numpy as np
import os
import sys
from pathlib import Path
import uuid
import pytesseract

# --- Cấu hình cho script test ---
BASE_DIR = Path(__file__).resolve().parent
MEDIA_ROOT_TEST = os.path.join(str(BASE_DIR), 'media_test_opencv_inside_project')
SAVE_DIR_TEST = os.path.join(MEDIA_ROOT_TEST, 'vehicle_entries_ocr_test')
if not os.path.exists(SAVE_DIR_TEST):
    os.makedirs(SAVE_DIR_TEST)


# --- QUAN TRỌNG: CẤU HÌNH TESSERACT ---
# Nếu Tesseract không nằm trong PATH, bỏ comment và SỬA ĐÚNG ĐƯỜNG DẪN dưới đây
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def process_image_for_plate_ocr(image_file_path):
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
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced_gray = clahe.apply(gray_img)  # Sẽ dùng lại ảnh này nếu khoanh vùng thất bại
        blurred_img = cv2.GaussianBlur(contrast_enhanced_gray, (5, 5), 0)
        edged_img = cv2.Canny(blurred_img, 50, 150)
        cv2.imshow("3 - Edged Image", edged_img)
        cv2.waitKey(0)

        # 2. Phát hiện vùng 4 cạnh (đơn giản hóa)
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
            print("DEBUG: No 4-sided contour selected as potential plate. Will attempt OCR on full preprocessed image.")

        recognized_plate_text_result = "KHONG_THE_NHAN_DANG"  # Mặc định nếu mọi thứ thất bại
        path_to_ocr_input_image_saved = None  # Đường dẫn ảnh đã được chuẩn bị cho OCR và lưu lại
        original_image_basename = os.path.basename(image_file_path)
        original_image_relative_path_for_django = os.path.join('vehicle_entries_test',
                                                               "original_for_django_" + original_image_basename)

        ocr_target_image = None  # Ảnh sẽ được đưa vào Tesseract

        if license_plate_contour_final is not None:
            (x, y, w, h) = cv2.boundingRect(license_plate_contour_final)
            if w > 0 and h > 0:
                # Cắt từ ảnh xám đã tăng tương phản
                cropped_plate_img = contrast_enhanced_gray[y:y + h, x:x + w]
                cv2.imshow("5.0 - Cropped Region (Input for OCR Preprocessing)", cropped_plate_img)
                cv2.waitKey(0)
                ocr_target_image = cropped_plate_img.copy()
                print("DEBUG: Processing OCR on CROPPED image.")
            else:
                print("DEBUG: Selected contour has invalid dimensions. Fallback to full image OCR.")
                # Fallback nếu cắt lỗi, dùng ảnh đã tăng tương phản toàn bộ
                ocr_target_image = contrast_enhanced_gray.copy()
        else:
            # Fallback nếu không tìm thấy contour, dùng ảnh đã tăng tương phản toàn bộ
            print("DEBUG: No specific plate region found. Attempting OCR on full preprocessed image.")
            ocr_target_image = contrast_enhanced_gray.copy()
            cv2.imshow("Fallback - Full Image for OCR Preprocessing", ocr_target_image)
            cv2.waitKey(0)

        # --- TIỀN XỬ LÝ ẢNH `ocr_target_image` CHO OCR ---
        # 1. Resize (Tùy chọn, nhưng thường hữu ích)
        target_height_ocr = 80
        current_height_ocr = ocr_target_image.shape[0]
        current_width_ocr = ocr_target_image.shape[1]
        if current_height_ocr > 0 and current_width_ocr > 0:
            if current_height_ocr < target_height_ocr / 2 or current_height_ocr > target_height_ocr * 2:  # Resize nếu chênh lệch nhiều
                scale_factor = float(target_height_ocr) / current_height_ocr
                new_width = int(current_width_ocr * scale_factor)
                if new_width > 0:
                    ocr_target_image_resized = cv2.resize(ocr_target_image, (new_width, target_height_ocr),
                                                          interpolation=cv2.INTER_LANCZOS4)
                    cv2.imshow("5.1 - Resized for OCR", ocr_target_image_resized)
                    cv2.waitKey(0)
                    ocr_input_for_thresholding = ocr_target_image_resized
                else:
                    ocr_input_for_thresholding = ocr_target_image  # Dùng ảnh gốc nếu resize lỗi
            else:
                ocr_input_for_thresholding = ocr_target_image  # Dùng ảnh gốc nếu kích thước đã tương đối ổn
        else:
            print("Lỗi: Ảnh đầu vào cho resize không hợp lệ (chiều cao hoặc rộng bằng 0).")
            cv2.destroyAllWindows()
            return "LOI_ANH_RESIZE_OCR", original_image_relative_path_for_django, None

        # 2. Phân ngưỡng nhị phân (Thresholding)
        # THỬ NGHIỆM CÁC PHƯƠNG PHÁP VÀ THAM SỐ Ở ĐÂY
        # (_, ocr_ready_img) = cv2.threshold(ocr_input_for_thresholding, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        ocr_ready_img = cv2.adaptiveThreshold(ocr_input_for_thresholding, 255,
                                              cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                              cv2.THRESH_BINARY_INV,
                                              15,  # blockSize
                                              7)  # C
        cv2.imshow("5.2 - OCR Ready (Thresholded)", ocr_ready_img)
        cv2.waitKey(0)

        # --- THỰC HIỆN OCR ---
        try:
            char_whitelist = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-'
            # THỬ NGHIỆM CÁC GIÁ TRỊ --psm. Nếu OCR trên toàn ảnh, psm 6 hoặc 11 có thể tốt hơn.
            # Nếu OCR trên vùng cắt nhỏ (hy vọng là biển số), psm 7 hoặc 8.
            psm_mode = '11' if license_plate_contour_final is not None else '7'  # Chọn psm tùy theo có khoanh vùng được không
            custom_config = f'--oem 3 --psm {psm_mode} -c tessedit_char_whitelist={char_whitelist}'

            print(f"DEBUG: Using Tesseract config: {custom_config}")
            ocr_text = pytesseract.image_to_string(ocr_ready_img, lang='eng', config=custom_config)

            cleaned_ocr_text = "".join(filter(lambda char: char in char_whitelist, ocr_text.upper()))
            recognized_plate_text_result = "".join(cleaned_ocr_text.split())

            if not recognized_plate_text_result:
                recognized_plate_text_result = "OCR_KHONG_RA_KY_TU"
            else:
                print(f"DEBUG: OCR Raw Text: '{ocr_text.strip()}'")
                print(f"DEBUG: OCR Cleaned Text: '{recognized_plate_text_result}'")

        except pytesseract.TesseractNotFoundError:
            print("LỖI PYTESSERACT: Tesseract không được tìm thấy...")
            recognized_plate_text_result = "LOI_TESSERACT_NOT_FOUND"
        except Exception as ocr_error:
            print(f"Lỗi trong quá trình OCR: {ocr_error}")
            recognized_plate_text_result = "LOI_OCR"

        # Lưu ảnh đã sẵn sàng cho OCR để kiểm tra
        name_part_orig, _ = os.path.splitext(os.path.basename(image_file_path))
        ocr_ready_filename_save = f"ocr_input_{name_part_orig}_{uuid.uuid4().hex[:6]}.png"
        path_to_ocr_input_image_full_saved = os.path.join(SAVE_DIR_TEST, ocr_ready_filename_save)
        cv2.imwrite(path_to_ocr_input_image_full_saved, ocr_ready_img)
        path_to_ocr_input_image_result = os.path.join(os.path.basename(SAVE_DIR_TEST), ocr_ready_filename_save)

        cv2.destroyAllWindows()
        return recognized_plate_text_result, original_image_relative_path_for_django, path_to_ocr_input_image_result

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi xử lý ảnh trong test script: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        return "LOI_XU_LY_ANH_TRONG_TEST", None, None


# Khối if __name__ == '__main__' để chạy script
if __name__ == '__main__':
    test_data_dir = os.path.join(str(BASE_DIR), "TestData")
    image_name_to_test = "bienso3.jpg"  # <<--- THAY TÊN FILE ẢNH CỦA BẠN Ở ĐÂY

    test_image_file = os.path.join(test_data_dir, image_name_to_test)

    if not os.path.isfile(test_image_file):
        print(f"LỖI: File ảnh thử nghiệm không tồn tại: {test_image_file}")
    else:
        print(f"Đang xử lý ảnh: {test_image_file}")
        plate_text, _, ocr_input_saved_path = process_image_for_plate_ocr(test_image_file)

        print("-" * 30)
        print(f"KẾT QUẢ NHẬN DẠNG BIỂN SỐ CUỐI CÙNG: {plate_text}")
        if ocr_input_saved_path:
            print(f"Ảnh đã được chuẩn bị cho OCR và lưu tại (tương đối): {ocr_input_saved_path}")
            print(f"Đường dẫn đầy đủ có thể là: {os.path.join(SAVE_DIR_TEST, os.path.basename(ocr_input_saved_path))}")