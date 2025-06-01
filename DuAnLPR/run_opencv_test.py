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
SAVE_DIR_TEST = os.path.join(MEDIA_ROOT_TEST, 'vehicle_entries_opencv_test')
if not os.path.exists(SAVE_DIR_TEST):
    os.makedirs(SAVE_DIR_TEST)


# --- QUAN TRỌNG: CẤU HÌNH TESSERACT ---
# Nếu bạn KHÔNG thêm thư mục cài đặt Tesseract vào PATH hệ thống,
# hãy bỏ comment dòng dưới và SỬA LẠI ĐƯỜNG DẪN cho đúng với máy của bạn.
# Ví dụ trên Windows:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
# Ví dụ trên Linux (nếu tesseract không nằm trong PATH mặc định):
# pytesseract.pytesseract.tesseract_cmd = r'/usr/local/bin/tesseract' # Đường dẫn có thể khác

def process_image_for_plate_ocr(image_file_path):
    """
    1. Tìm và cắt một vùng 4 cạnh tiềm năng (đơn giản hóa).
    2. Tiền xử lý vùng cắt.
    3. Cố gắng OCR ký tự trên vùng đã cắt.
    """
    try:
        img_original = cv2.imread(image_file_path)
        if img_original is None:
            print(f"Lỗi: Không thể đọc ảnh từ {image_file_path}")
            return "LOI_DOC_ANH", None, None

        img_for_processing = img_original.copy()

        # --- Hiển thị ảnh gốc ---
        cv2.imshow("0 - Original Image", img_original)
        cv2.waitKey(0)

        # 1. Tiền xử lý ảnh (cho việc khoanh vùng)
        gray_img = cv2.cvtColor(img_for_processing, cv2.COLOR_BGR2GRAY)
        # cv2.imshow("1 - Grayscale Image", gray_img)
        # cv2.waitKey(0)

        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast_enhanced_gray = clahe.apply(gray_img)
        # cv2.imshow("1.1 - Contrast Enhanced Gray", contrast_enhanced_gray)
        # cv2.waitKey(0)

        blurred_img = cv2.GaussianBlur(contrast_enhanced_gray, (5, 5), 0)
        # cv2.imshow("2 - Blurred Image", blurred_img)
        # cv2.waitKey(0)

        # Ngưỡng Canny (Bạn có thể cần tinh chỉnh dựa trên ảnh test)
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
            print("DEBUG: No 4-sided contour selected as potential plate.")

        recognized_plate_text_result = "KHONG_TIM_THAY_VUNG_4_CANH"
        path_to_cropped_image_result = None
        # Tạo đường dẫn cho ảnh gốc upload lên để trả về (nếu cần thiết cho Django)
        original_image_basename = os.path.basename(image_file_path)
        original_image_relative_path = os.path.join(os.path.basename(SAVE_DIR_TEST),
                                                    "original_for_django_" + original_image_basename)

        if license_plate_contour_final is not None:
            (x, y, w, h) = cv2.boundingRect(license_plate_contour_final)
            if w > 0 and h > 0:
                # Cắt từ ảnh xám đã tăng tương phản để OCR tốt hơn
                cropped_plate_img = contrast_enhanced_gray[y:y + h, x:x + w]

                cv2.imshow("5 - Cropped Region for OCR", cropped_plate_img)
                cv2.waitKey(0)

                # --- TIỀN XỬ LÝ ẢNH CẮT CHO OCR (QUAN TRỌNG) ---
                # 1. Thay đổi kích thước nếu cần (Tesseract thích chiều cao ký tự nhất định)
                # Ví dụ: đưa chiều cao về khoảng 40-60px
                target_height_ocr = 50
                current_height_ocr = cropped_plate_img.shape[0]
                if current_height_ocr > 0 and (
                        current_height_ocr < 30 or current_height_ocr > 100):  # Chỉ resize nếu quá nhỏ hoặc quá lớn
                    scale_factor = float(target_height_ocr) / current_height_ocr
                    width_new = int(cropped_plate_img.shape[1] * scale_factor)
                    height_new = target_height_ocr
                    if width_new > 0 and height_new > 0:
                        cropped_plate_img_resized = cv2.resize(cropped_plate_img, (width_new, height_new),
                                                               interpolation=cv2.INTER_CUBIC)
                        cv2.imshow("5.1 - Resized Cropped for OCR", cropped_plate_img_resized)
                        cv2.waitKey(0)
                        ocr_input_img = cropped_plate_img_resized
                    else:
                        ocr_input_img = cropped_plate_img  # Dùng ảnh gốc nếu resize lỗi
                else:
                    ocr_input_img = cropped_plate_img  # Dùng ảnh gốc nếu kích thước đã ổn

                # 2. Phân ngưỡng nhị phân (Thresholding)
                # Thử THRESH_BINARY + THRESH_OTSU trước
                (_, ocr_ready_img) = cv2.threshold(ocr_input_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                # Nếu OTSU không tốt, thử giá trị ngưỡng cố định, ví dụ 127, hoặc adaptiveThreshold
                # ocr_ready_img = cv2.adaptiveThreshold(ocr_input_img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                #                                       cv2.THRESH_BINARY, 11, 2)
                cv2.imshow("5.2 - OCR Ready Image (Thresholded)", ocr_ready_img)
                cv2.waitKey(0)

                # (Tùy chọn) Thêm các bước lọc nhiễu trên ocr_ready_img nếu cần (ví dụ: medianBlur)
                # ocr_ready_img = cv2.medianBlur(ocr_ready_img, 3) # Thử kernel size 3 hoặc 5
                # cv2.imshow("5.3 - OCR Ready Denoised", ocr_ready_img)
                # cv2.waitKey(0)

                # --- THỰC HIỆN OCR ---
                try:
                    # whitelist chỉ chứa các ký tự bạn mong đợi trên biển số Việt Nam
                    char_whitelist = 'ABCDEFGHJKLMNPQRSTUVWXYZ0123456789-'
                    # Thử các giá trị psm: 6, 7, 8, 11, 13. Psm 7 hoặc 8 thường tốt cho một dòng text.
                    custom_config = f'--oem 3 --psm 7 -c tessedit_char_whitelist={char_whitelist}'

                    ocr_text = pytesseract.image_to_string(ocr_ready_img, lang='eng', config=custom_config)

                    # Làm sạch kết quả OCR
                    cleaned_ocr_text = "".join(filter(lambda char: char in char_whitelist, ocr_text.upper()))
                    recognized_plate_text_result = cleaned_ocr_text.strip().replace(" ",
                                                                                    "")  # Loại bỏ thêm khoảng trắng bên trong

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

                # Lưu ảnh đã sẵn sàng cho OCR (ảnh đen trắng)
                base_name_orig = os.path.basename(image_file_path)
                name_part_orig, _ = os.path.splitext(base_name_orig)
                # Sử dụng uuid để tên file không bị trùng lặp khi test nhiều lần với cùng ảnh gốc
                cropped_filename_save = f"ocr_ready_{name_part_orig}_{uuid.uuid4().hex[:6]}.jpg"
                path_to_cropped_image_full = os.path.join(SAVE_DIR_TEST, cropped_filename_save)
                cv2.imwrite(path_to_cropped_image_full, ocr_ready_img)
                path_to_cropped_image_result = os.path.join(os.path.basename(SAVE_DIR_TEST), cropped_filename_save)
            else:
                print("DEBUG: Selected contour has invalid dimensions for cropping (w or h is 0).")
                recognized_plate_text_result = "LOI_KICH_THUOC_CAT"
        else:
            print("DEBUG (test script): No 4-sided contour was selected (or found after basic filtering).")

        cv2.destroyAllWindows()
        return recognized_plate_text_result, original_image_relative_path, path_to_cropped_image_result

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi xử lý ảnh trong test script: {e}")
        import traceback
        traceback.print_exc()
        cv2.destroyAllWindows()
        return "LOI_XU_LY_ANH_TRONG_TEST", None, None


# Khối if __name__ == '__main__' để chạy script
if __name__ == '__main__':
    # === THAY ĐỔI ĐƯỜNG DẪN ĐẾN ẢNH TEST CỦA BẠN Ở ĐÂY ===
    test_data_dir = os.path.join(str(BASE_DIR), "TestData")
    # Đặt tên file ảnh bạn muốn test ở đây
    image_name_to_test = "bienso_test_1.jpg"  # Ví dụ: ảnh image_f726d8.jpg

    test_image_file = os.path.join(test_data_dir, image_name_to_test)

    if not os.path.isfile(test_image_file):
        print(f"LỖI: File ảnh thử nghiệm không tồn tại: {test_image_file}")
    else:
        print(f"Đang xử lý ảnh: {test_image_file}")
        # Gọi hàm đã đổi tên
        plate_text, original_path_for_django, cropped_ocr_ready_path = process_image_for_plate_ocr(test_image_file)

        print("-" * 30)
        print(f"Kết quả nhận dạng biển số: {plate_text}")
        if original_path_for_django:  # Thực ra biến này chưa được dùng đúng cách trong script test
            print(
                f"Đường dẫn ảnh gốc (dùng cho Django sau này, không phải file đã lưu khi test): {original_path_for_django}")
        if cropped_ocr_ready_path:
            print(f"Ảnh đã xử lý cho OCR được lưu tại (tương đối): {cropped_ocr_ready_path}")
            print(
                f"Đường dẫn đầy đủ có thể là: {os.path.join(SAVE_DIR_TEST, os.path.basename(cropped_ocr_ready_path))}")
        # ... (các thông báo khác) ...