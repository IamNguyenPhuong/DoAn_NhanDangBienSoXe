# services/ocr_service.py (PHIÊN BẢN CUỐI CÙNG - SỬA ĐÚNG TÊN MODEL)

import requests
import base64
import os

def recognize_license_plate(image_data: bytes, mime_type: str) -> dict:
    """
    Gửi dữ liệu ảnh đến Google Gemini API để nhận dạng biển số xe.
    """
    api_key = os.getenv("API_KEY")

    if not api_key:
        return {'status': 'error', 'message': 'API Key của Gemini chưa được cấu hình.'}

    # --- ĐÂY LÀ DÒNG SỬA QUAN TRỌNG NHẤT ---
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"

    # Các phần còn lại giữ nguyên
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
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text']
        cleaned_text = text.strip()
        return {'status': 'success', 'text': cleaned_text}
    except requests.exceptions.HTTPError as http_err:
        error_details = response.json()
        print(f"LỖI HTTP TỪ GOOGLE API: {error_details}")
        return {'status': 'error', 'message': 'Lỗi từ Google API. Vui lòng kiểm tra Terminal.'}
    except Exception as e:
        return {'status': 'error', 'message': f'Lỗi không xác định: {e}'}