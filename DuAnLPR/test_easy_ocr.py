import cv2
import numpy as np
import pytesseract
from typing import Tuple, List


def preprocess_image(image: np.ndarray) -> np.ndarray:
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Apply CLAHE for contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)

    # Reduce noise with bilateral filter
    denoised = cv2.bilateralFilter(contrast, 9, 75, 75)

    # Adaptive thresholding to binarize
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )
    return binary


def detect_plate(image: np.ndarray) -> Tuple[np.ndarray, List[int]]:
    # Convert to HSV for color segmentation
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower_white = np.array([0, 0, 200])
    upper_white = np.array([255, 50, 255])
    mask = cv2.inRange(hsv, lower_white, upper_white)

    # Edge detection
    edges = cv2.Canny(mask, 100, 200)

    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter for plate-like rectangles
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / h
        area = w * h
        if 2 < aspect_ratio < 5 and 0.01 < area / (image.shape[0] * image.shape[1]) < 0.1:
            plate = image[y:y + h, x:x + w]
            return plate, [x, y, w, h]
    return image, [0, 0, image.shape[1], image.shape[0]]


def split_rows(plate_binary: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    # Compute histogram along y-axis
    hist = np.sum(plate_binary, axis=1)
    mid = len(hist) // 2

    # Find split point (minimum intensity between rows)
    split_point = mid + np.argmin(hist[mid - 10:mid + 10]) - 10
    top_row = plate_binary[:split_point, :]
    bottom_row = plate_binary[split_point:, :]
    return top_row, bottom_row


def recognize_text(image: np.ndarray) -> str:
    # Tesseract configuration
    config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHJKLMNPQRSTUVWXYZ-.'
    text = pytesseract.image_to_string(image, config=config)
    return text.strip()


def process_license_plate(image_path: str) -> str:
    # Load image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("Không thể tải ảnh!")

    # Detect plate region
    plate, _ = detect_plate(image)

    # Preprocess plate
    plate_binary = preprocess_image(plate)

    # Split into two rows
    top_row, bottom_row = split_rows(plate_binary)

    # Recognize text from each row
    top_text = recognize_text(top_row)
    bottom_text = recognize_text(bottom)

    # Combine and format result
    result = f"{top_text} {bottom_text}"
    return result


# Example usage

if __name__ == "__main__":
    image_path = "path_to_your_image.jpg"  # Thay bằng đường dẫn đến ảnh của bạn
    try:
        plate_number = process_license_plate(image_path)
        print(f"Biển số nhận diện: {plate_number}")
    except Exception as e:
        print(f"Lỗi: {e}")