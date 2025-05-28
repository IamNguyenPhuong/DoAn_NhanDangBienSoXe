import cv2
import numpy as np
import os
from django.conf import settings
import uuid


def save_uploaded_image_and_recognize_plate(uploaded_file):
    """
    Lưu ảnh được upload, xử lý để tìm biển số (đơn giản hóa, chỉ tìm contour 4 cạnh).
    """
    try:
        filename = str(uuid.uuid4()) + "_" + os.path.splitext(uploaded_file.name)[0] + ".jpg"
        save_dir = os.path.join(settings.MEDIA_ROOT, 'vehicle_entries')
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        file_path = os.path.join(save_dir, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        img = cv2.imread(file_path)

        if img is None:
            print(f"Lỗi: Không thể đọc ảnh từ {file_path}")
            return None, None

        # 1. Tiền xử lý ảnh
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blurred_img = cv2.GaussianBlur(gray_img, (5, 5), 0)
        edged_img = cv2.Canny(blurred_img, 75, 200)

        # 2. Phát hiện vùng chứa biển số (Tìm các đường viền - contours)
        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]

        license_plate_contour = None

        for contour in contours:
            perimeter = cv2.arcLength(contour, True)
            approx_polygon = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

            if len(approx_polygon) == 4:  # Chỉ kiểm tra có 4 cạnh
                license_plate_contour = approx_polygon
                print(f"DEBUG: Found a 4-sided contour.")
                break

        recognized_plate_text = "CHUA_NHAN_DANG"
        relative_image_path = os.path.join('vehicle_entries', filename)
        cropped_plate_image_path_relative = None

        if license_plate_contour is not None:
            (x, y, w, h) = cv2.boundingRect(license_plate_contour)
            # Kiểm tra cơ bản để tránh cắt ảnh quá lớn nếu w, h quá lớn so với kích thước ảnh
            img_height, img_width = img.shape[:2]
            if w < img_width * 0.9 and h < img_height * 0.9:  # Tránh lấy gần như toàn bộ ảnh
                cropped_plate_img = gray_img[y:y + h, x:x + w]

                # Chỉ lưu và thay đổi text nếu việc cắt ảnh hợp lệ
                if cropped_plate_img.size > 0:  # Đảm bảo ảnh cắt không rỗng
                    cropped_filename = "cropped_" + filename
                    cropped_plate_image_path_full = os.path.join(save_dir, cropped_filename)
                    cv2.imwrite(cropped_plate_image_path_full, cropped_plate_img)
                    cropped_plate_image_path_relative = os.path.join('vehicle_entries', cropped_filename)
                    recognized_plate_text = "DA_TIM_THAY_VUNG_BIEN_SO"  # Hoặc "VUNG_4_CANH"
                else:
                    print("DEBUG: Cropped image is empty, possibly due to invalid contour.")
                    recognized_plate_text = "LOI_CAT_ANH"
            else:
                print("DEBUG: Detected 4-sided contour is too large, likely not a plate.")
                recognized_plate_text = "CONTOUR_QUA_LON"

        return recognized_plate_text, relative_image_path  # Bạn có thể muốn trả về cả cropped_plate_image_path_relative

    except Exception as e:
        print(f"Lỗi nghiêm trọng khi xử lý ảnh: {e}")
        import traceback
        traceback.print_exc()
        return None, None