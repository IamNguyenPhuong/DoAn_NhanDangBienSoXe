import cv2
import numpy as np

# Tạo một ảnh đen đơn giản
img = np.zeros((100, 300, 3), dtype=np.uint8)
cv2.putText(img, "OpenCV GUI Test", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

try:
    cv2.imshow("Test Window", img)
    print("cv2.imshow() called. Press any key in the window to close.")
    key = cv2.waitKey(0) # Đợi nhấn phím
    print(f"Key pressed: {key}")
    cv2.destroyAllWindows()
    print("OpenCV GUI seems to be working!")
except cv2.error as e:
    print(f"OpenCV GUI Error: {e}")
    print("It seems OpenCV GUI support is still missing or not working correctly.")
    print("Please ensure you have installed 'opencv-contrib-python' and not 'opencv-python-headless'.")
    print("You might also need to install system libraries like GTK or other media packs if on a barebones system, though this is less common on typical Windows setups.")