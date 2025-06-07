# services/ocr_service.py

import requests
import base64
import os
from dotenv import load_dotenv

# Tải các biến môi trường từ file .env
load_dotenv()

# Lấy API Key từ biến môi trường
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"

def recognize_license_plate(image_data: bytes, mime_type: str) -> dict:
    """
    Gửi dữ liệu ảnh đến Google Gemini API để nhận dạng biển số xe.
    Hàm này nhận dữ liệu ảnh dạng bytes, không đọc từ file.

    Args:
        image_data (bytes): Dữ liệu byte của file ảnh.
        mime_type (str): Loại MIME của ảnh (ví dụ: 'image/jpeg').

    Returns:
        dict: Một dictionary chứa trạng thái và kết quả.
              Thành công: {'status': 'success', 'text': '29A-123.45'}
              Thất bại:  {'status': 'error', 'message': 'Lý do lỗi...'}
    """
    if not API_KEY:
        return {'status': 'error', 'message': 'API Key của Gemini chưa được cấu hình.'}

    # Mã hóa ảnh sang Base64 để gửi đi
    encoded_string = base64.b64encode(image_data).decode('utf-8')

    headers = {"Content-Type": "application/json"}
    prompt = "Đọc ký tự trên biển số xe trong ảnh này. Chỉ trả về duy nhất chuỗi ký tự của biển số, không kèm theo bất kỳ giải thích nào khác."

    payload = {
        "contents": [{
            "parts": [
                {"inline_data": {"mime_type": mime_type, "data": encoded_string}},
                {"text": prompt}
            ]
        }]
    }

    try:
        # Gửi yêu cầu đến API, đặt timeout 10 giây
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # Báo lỗi nếu có lỗi HTTP (4xx, 5xx)

        result = response.json()
        # Trích xuất kết quả text từ JSON trả về
        text = result['candidates'][0]['content']['parts'][0]['text']
        cleaned_text = text.strip() # Dọn dẹp khoảng trắng hoặc ký tự xuống dòng

        return {'status': 'success', 'text': cleaned_text}

    except requests.exceptions.RequestException as e:
        # Lỗi mạng, kết nối, timeout
        return {'status': 'error', 'message': f'Lỗi kết nối đến Google API: {e}'}
    except (KeyError, IndexError):
        # Lỗi do JSON trả về không đúng cấu trúc mong đợi
        return {'status': 'error', 'message': 'Không thể phân tích kết quả từ API.'}