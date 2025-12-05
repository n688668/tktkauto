import os
import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import time
import random
import re # Dùng để làm sạch tên thư mục
import csv
from io import StringIO
import sys
import select

# --- Cho Google Drive ---
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# --- Cho AI ---
from google import genai
from google.genai import types

from dotenv import load_dotenv
# Tải các biến từ file .env vào môi trường
load_dotenv()

# ==========================================================
# --- KHAI BÁO CẤU HÌNH VÀ API KEYS (TỪ FILE .ENV) ---
# ==========================================================

# 1. API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# 2. Cấu hình Ứng dụng
# Lưu ý: os.getenv trả về chuỗi, nên cần chuyển đổi sang boolean và gán giá trị mặc định
ENABLE_TELEGRAM_NOTIFICATIONS = os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "False").lower() == "true"
GSHEET_ID = os.getenv("GSHEET_ID")

# 3. ID Thư mục Google Drive
BACKGROUND_IMAGES_FOLDER_ID = os.getenv("BACKGROUND_IMAGES_FOLDER_ID")
STORY_DRIVE_FOLDER_ID = os.getenv("STORY_DRIVE_FOLDER_ID")
PHONG_THUY_DRIVE_FOLDER_ID = os.getenv("PHONG_THUY_DRIVE_FOLDER_ID")
TU_VI_DRIVE_FOLDER_ID = os.getenv("TU_VI_DRIVE_FOLDER_ID")
TAROT_DRIVE_FOLDER_ID = os.getenv("TAROT_DRIVE_FOLDER_ID")
CUNG_HOANG_DAO_DRIVE_FOLDER_ID = os.getenv("CUNG_HOANG_DAO_DRIVE_FOLDER_ID")
FAIRY_TALE_DRIVE_FOLDER_ID = os.getenv("FAIRY_TALE_DRIVE_FOLDER_ID")
JOKE_DRIVE_FOLDER_ID = os.getenv("JOKE_DRIVE_FOLDER_ID")

# 4. Các đường dẫn cục bộ (Giữ nguyên hoặc chỉnh sửa theo nhu cầu)
FILE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(FILE_DIR, 'auto_creds.txt')
CLIENT_SECRETS_FILE = os.path.join(FILE_DIR, 'credentials.json')
FONT_PATH = os.path.join(FILE_DIR, 'font.ttf')

# Thiết lập Client Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

TIMEOUT_SECONDS = 3

# ==========================================================
# --- KHỐI HÀM PHỤ VÀ TẢI ẢNH (GIỮ NGUYÊN) ---
# ==========================================================

# HÀM Xử lý ngắt dòng tự động
def text_wrap(text, font, max_width):
    lines = []
    paragraphs = text.split('\n')
    for paragraph in paragraphs:
        if not paragraph:
            lines.append("")
            continue
        words = paragraph.split()
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            try:
                width = font.getlength(test_line)
            except AttributeError:
                width = len(test_line) * 20
            if width <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)
    return lines

# --- HÀM TẠO ẢNH NỀN VÀ CHÈN CHỮ (PILLOW) ---
def create_image_with_text(text_to_overlay, drive_service, slide_index, theme):
    filename_out = f"slide_{slide_index}_final.jpg"
    W, H = 1080, 1920
    temp_bg_path = None

    # CHUỖI ƯU TIÊN TẢI ẢNH: PEXELS -> UNSPLASH -> GOOGLE DRIVE
    temp_bg_path = get_random_pexels_image(theme, slide_index)
    if not temp_bg_path:
        temp_bg_path = get_random_unsplash_image(theme, slide_index)
        if not temp_bg_path:
            temp_bg_path = get_random_background_image(
                drive_service,
                BACKGROUND_IMAGES_FOLDER_ID,
                slide_index
            )

    if temp_bg_path:
        # ... (logic mở, crop ảnh) ...
        try:
            img = Image.open(temp_bg_path).convert('RGB')
        except Exception as e:
            img = Image.new('RGB', (W, H), color = (0, 0, 0))

        img_w, img_h = img.size
        target_w, target_h = W, H
        scale_ratio = max(target_w / img_w, target_h / img_h)
        new_w = int(img_w * scale_ratio)
        new_h = int(img_h * scale_ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - target_w) // 2
        right = left + target_w
        top = (new_h - target_h) // 2
        bottom = top + target_h
        img = img.crop((left, top, right, bottom))
    else:
        img = Image.new('RGB', (W, H), color = (0, 0, 0))

    draw = ImageDraw.Draw(img)
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 128))
    img.paste(overlay, (0, 0), overlay)

    # 3B: CHÈN CHỮ
    try:
        font_size = 72
        font = ImageFont.truetype(FONT_PATH, font_size)
    except IOError:
        font = ImageFont.load_default()

    MAX_TEXT_WIDTH = W - 240
    wrapped_lines = text_wrap(text_to_overlay, font, MAX_TEXT_WIDTH)

    # =======================================================
    # *** KHỐI SỬA CHỮA CĂN GIỮA DỌC ***
    # =======================================================
    # 1. Tính toán tổng chiều cao của khối văn bản
    total_text_height = 0
    line_spacing = 15

    # Phải tính toán chiều cao từng dòng một cách chính xác
    for line in wrapped_lines:
        if not line: continue
        try:
            text_bbox = draw.textbbox((0, 0), line, font=font)
            line_height = text_bbox[3] - text_bbox[1]
            total_text_height += line_height + line_spacing
        except Exception:
            # Fallback nếu lỗi tính toán BB
            total_text_height += font_size + 20

    # Bỏ đi khoảng cách dòng thừa cuối cùng
    if total_text_height > 0:
        total_text_height -= line_spacing

    # 2. Đặt điểm bắt đầu Y tại trung tâm khung hình
    y_start_center = (H // 2)
    y_current = y_start_center - (total_text_height // 2)
    # =======================================================

    for line in wrapped_lines:
        if not line: continue

        # Tính toán Bounding Box cho căn giữa ngang và nền
        try:
            text_bbox = draw.textbbox((0, 0), line, font=font)
            textwidth = text_bbox[2] - text_bbox[0]
            textheight = text_bbox[3] - text_bbox[1] # Chiều cao dòng
        except Exception:
            textwidth = font.getlength(line) if hasattr(font, 'getlength') else 500
            textheight = font_size + 5 # Chiều cao dòng (Fallback)

        # Căn giữa theo chiều ngang
        x = (W - textwidth) // 2

        # Vẽ nền đen mờ sau chữ
        draw.rectangle([(x - 20, y_current - 10), (x + textwidth + 20, y_current + textheight + 10)], fill=(0, 0, 0, 128))

        # Vẽ chữ
        draw.text((x, y_current), line, fill=(255, 255, 255), font=font)

        # Cập nhật vị trí Y cho dòng tiếp theo
        y_current += textheight + 15 # Dùng chiều cao dòng thực tế + 15px

    filename_out = f"slide_{slide_index}_final.jpg"
    img.save(filename_out, format='JPEG', quality=85)

    if temp_bg_path and os.path.exists(temp_bg_path):
        os.remove(temp_bg_path)

    return filename_out

# Hàm Tạo thư mục và tải lên Drive (ví dụ)
def create_drive_folder(folder_name, parent_folder_id, drive_service):
    """
    Tạo tên thư mục mới bằng cách thêm timestamp (số giây + mili giây)
    để đảm bảo tính duy nhất và tạo thư mục ngay lập tức.
    """
    try:
        # 1. Lấy timestamp chính xác (dạng số, bao gồm mili giây)
        # Ví dụ: 1733215914519
        timestamp_ms = int(time.time() * 1000)

        # 2. Tạo tên thư mục duy nhất
        # Tên mới sẽ có dạng: Tên_Gốc_1733215914519
        unique_folder_name = f"{folder_name} {timestamp_ms}"

        print(f"Bắt đầu: Tạo thư mục mới với Timestamp...")

        # 3. Tạo thư mục ngay lập tức
        folder_metadata = {
            'title': unique_folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [{'id': parent_folder_id}]
        }
        folder = drive_service.CreateFile(folder_metadata)
        folder.Upload()
        print(f"  - Đã tạo thư mục mới duy nhất: '{unique_folder_name}'. ID: {folder['id']}")
        return folder['id']

    except Exception as e:
        print(f"Lỗi khi tạo thư mục Google Drive: {e}")
        return None

# --- HÀM TẢI ẢNH LÊN GOOGLE DRIVE ---
# (Giữ nguyên như kịch bản trước)
def upload_to_drive(file_path, drive_service, folder_id):
    try:
        file_metadata = {'title': os.path.basename(file_path), 'parents': [{'id': folder_id}]}
        uploaded_file = drive_service.CreateFile(file_metadata)
        uploaded_file.SetContentFile(file_path)
        uploaded_file.Upload()
        print(f"  - Đã tải '{os.path.basename(file_path)}' lên Google Drive.")
        return uploaded_file['alternateLink']
    except Exception as e:
        print(f"Lỗi khi tải lên Google Drive: {e}")
        return None

# --- HÀM GỬI THÔNG BÁO KẾT QUẢ ĐẾN TELEGRAM ---
def send_telegram_notification(text_message, image_urls=None):
    # Kiểm tra cờ bật/tắt
    if not ENABLE_TELEGRAM_NOTIFICATIONS:
        print("⚠️ Thông báo Telegram đã bị tắt (ENABLE_TELEGRAM_NOTIFICATIONS = False). Bỏ qua.")
        return

    print("\n--- Đang gửi thông báo kết quả đến Telegram ---")
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    # Payload cho tin nhắn chính
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': text_message,
        'parse_mode': 'HTML'
    }

    try:
        # Gửi tin nhắn chính
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            print("Đã gửi tin nhắn thông báo thành công!")
        else:
            print(f"Lỗi Telegram (gửi tin nhắn): {response.status_code} - {response.text}") # IN CHI TIẾT LỖI

        # Gửi link ảnh nếu có
        if image_urls:
            img_message = "<b>Ảnh đã lưu trên Drive (tải xuống để đăng):</b>\n" + "\n".join(image_urls)
            payload_img = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': img_message,
                'parse_mode': 'HTML'
            }
            # Gửi tin nhắn thứ hai chứa link ảnh
            requests.post(url, data=payload_img)

    except Exception as e:
        print(f"Lỗi kết nối Telegram (notification): {e}")

# ==========================================================
# --- KHỐI HÀM AI ĐIỀU PHỐI ---
# ==========================================================

# --- HÀM TẢI ẢNH NỀN NGẪU NHIÊN TỪ DRIVE ---
def get_random_background_image(drive_service, folder_id, slide_index):
    try:
        # Lấy danh sách tất cả các file trong thư mục ảnh nền
        query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed=false"
        file_list = drive_service.ListFile({'q': query}).GetList()

        if not file_list:
            print("  - Cảnh báo: Thư mục ảnh nền trống hoặc không có ảnh. Sử dụng nền đen.")
            return None

        # Chọn ngẫu nhiên một file
        random_file = random.choice(file_list)

        # Tải file xuống
        temp_filename = f"temp_bg_{slide_index}.jpg"
        random_file.GetContentFile(temp_filename)

        print(f"  - Đã tải ảnh nền ngẫu nhiên: {random_file['title']}")
        return temp_filename

    except Exception as e:
        print(f"Lỗi khi tải ảnh nền từ Drive: {e}")
        return None

# --- HÀM TẢI ẢNH NGẪU NHIÊN TỪ PEXELS (Ưu tiên 1) ---
def get_random_pexels_image(query, slide_index):
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
        print("  - Cảnh báo: PEXELS_API_KEY chưa được cấu hình. Bỏ qua Pexels.")
        return None

    # DANH SÁCH CHỦ ĐỀ CỐ ĐỊNH (theo yêu cầu của người dùng)
    THEME_KEYWORDS = [
        "rain", "snow", "forest", "mountain", "sea beach",
        "sunset", "sunrise", "old books", "potted plant indoor"
    ]

    # CHỌN CHỦ ĐỀ NGẪU NHIÊN TỪ DANH SÁCH
    random_theme = random.choice(THEME_KEYWORDS)
    print(f"  - Đang thử lấy ảnh nền từ Pexels theo chủ đề ngẫu nhiên: '{random_theme}'")
    modified_query = f"{random_theme} natural aesthetic no people"

    pexels_url = "https://api.pexels.com/v1/search"
    headers = { "Authorization": PEXELS_API_KEY }
    params = {
        'query': modified_query,
        'orientation': 'portrait',
        'size': 'large',
        'per_page': 15,
        'page': 1
    }

    try:
        response = requests.get(pexels_url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"  - Lỗi Pexels (Search): Status code {response.status_code}. Vui lòng kiểm tra API Key hoặc Limit.")
            return None

        data = response.json()
        photos = data.get('photos', [])

        if not photos:
            print(f"  - Pexels: Không tìm thấy ảnh nào cho chủ đề '{random_theme}'.")
            return None

        random_photo = random.choice(photos)
        image_url = random_photo['src']['original']

        image_response = requests.get(image_url, allow_redirects=True, timeout=15)
        if image_response.status_code == 200:
            temp_filename = f"temp_pexels_bg_{slide_index}.jpg"
            with open(temp_filename, 'wb') as f:
                f.write(image_response.content)
            print(f"  - ✅ Đã tải ảnh nền từ Pexels thành công.")
            return temp_filename
        else:
            print(f"  - Lỗi Pexels (Download): Status code {image_response.status_code}.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  - Lỗi kết nối Pexels: {e}. Chuyển sang dùng Unsplash.")
        return None

# --- HÀM TẢI ẢNH NGẪU NHIÊN TỪ UNSPLASH (Ưu tiên 2, Dùng API Chính thức) ---
def get_random_unsplash_image(query, slide_index):
    if not UNSPLASH_ACCESS_KEY or UNSPLASH_ACCESS_KEY == "YOUR_UNSPLASH_ACCESS_KEY":
        print("  - Cảnh báo: UNSPLASH_ACCESS_KEY chưa được cấu hình. Bỏ qua Unsplash.")
        return None

    # DANH SÁCH CHỦ ĐỀ CỐ ĐỊNH (theo yêu cầu của người dùng)
    THEME_KEYWORDS = [
        "rain", "snow", "forest", "mountain", "sea beach",
        "sunset", "sunrise", "old books", "potted plant indoor"
    ]
    random_theme = random.choice(THEME_KEYWORDS)
    print(f"  - Đang thử lấy ảnh nền từ Unsplash API theo chủ đề ngẫu nhiên: '{random_theme}'")

    negative_keywords = "-person -people -face -human -portrait"
    modified_query = f"{random_theme} backgrounds cover {negative_keywords}"

    unsplash_url = "https://api.unsplash.com/photos/random"

    headers = { "Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}" }

    params = {
        'query': modified_query,
        'orientation': 'portrait',
        'count': 1
    }

    try:
        response = requests.get(unsplash_url, headers=headers, params=params, timeout=10)
        if response.status_code != 200:
            print(f"  - Lỗi Unsplash (Search): Status code {response.status_code}. Chi tiết: {response.text}")
            return None

        data = response.json()

        if isinstance(data, list) and len(data) > 0:
            photo = data[0]
        elif isinstance(data, dict):
            photo = data
        else:
            print(f"  - Unsplash: Không tìm thấy ảnh nào cho chủ đề '{random_theme}'.")
            return None

        image_url = photo['urls']['full']

        image_response = requests.get(image_url, allow_redirects=True, timeout=15)

        if image_response.status_code == 200:
            temp_filename = f"temp_unsplash_bg_{slide_index}.jpg"
            with open(temp_filename, 'wb') as f:
                f.write(image_response.content)
            print(f"  - ✅ Đã tải ảnh nền từ Unsplash thành công.")
            return temp_filename
        else:
            print(f"  - Lỗi Unsplash (Download): Status code {image_response.status_code}.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"  - Lỗi kết nối Unsplash: {e}. Chuyển sang nguồn dự phòng.")
        return None

# --- HÀM ĐỀ XUẤT CHỦ ĐỀ HẤP DẪN (GEMINI) ---
def propose_random_theme(domains_list):
    print("Bắt đầu: Yêu cầu Gemini đề xuất một chủ đề hấp dẫn ngẫu nhiên, độc đáo...")

    system_prompt = f"""
    Bạn là một chuyên gia sáng tạo nội dung trên cách nền tảng số như TikTok, X, Youtube. Nhiệm vụ của bạn là đề xuất MỘT chủ đề câu chuyện ngắn (duy nhất) cực kỳ hấp dẫn, gây tò mò, hoặc chạm đến cảm xúc sâu sắc của người xem Việt Nam.

    QUY TẮC ĐỘC ĐÁO:
    1. Chủ đề phải **CỰC KỲ ngẫu nhiên** và **chưa từng được thấy** trong các đề xuất gần đây. Tránh các chủ đề chung chung.
    2. Tập trung vào một **tình huống gần gũi với mọi người, tính chất éo le, khó xử, nút thắt bất ngờ, hoặc một góc khuất** cụ thể theo chủ đề được chọn.

    LĨNH VỰC: Chủ đề nên xoay quanh {domains_list}.

    ĐỊNH DẠNG: Chỉ trả về **Tên Chủ Đề**, không có bất kỳ giải thích nào khác.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[system_prompt]
        )
        theme = response.text.strip()
        print(f"✅ Đã đề xuất chủ đề: {theme}")
        return theme
    except Exception as e:
        print(f"Lỗi khi gọi Gemini đề xuất chủ đề: {e}")
        return "Áp lực phải giỏi giang của con cái" # Chủ đề dự phòng

# --- HÀM TẠO KỊCH BẢN (GEMINI) ---
def generate_story_and_prompts(theme):
    print(f"Bắt đầu: Tạo kịch bản cho chủ đề '{theme}' bằng Gemini...")

    system_prompt = f"""
    Bạn là một nhà biên kịch nội dung TikTok chuyên nghiệp. Nhiệm vụ của bạn là chuyển chủ đề được cung cấp thành một kịch bản hấp dẫn, gây tò mò, và có một nút thắt bất ngờ ở cuối.
    QUY TẮC:
    1. Kịch bản phải dài từ **4 đến 10 slides**. Mỗi slide phải là một đoạn văn ngắn (tối đa 30 từ).
    2. Slide cuối cùng phải là **nút thắt/kết luận** gây sốc.
    3. Output BẮT BUỘC phải là một đối tượng JSON (array of objects) với các khóa sau:
       - 'text': Nội dung ngắn gọn cho slide.
       - 'caption': Phần caption cuối cùng cho toàn bộ video TikTok (chứa cả hashtag).
    """
    user_prompt = f"Viết một câu chuyện 4 đến 10 slides về chủ đề: {theme}."

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[system_prompt, user_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        data = json.loads(response.text)
        caption = "Câu chuyện đời thường." # Caption mặc định

        # XỬ LÝ LINH HOẠT TỪ ĐIỂN HOẶC DANH SÁCH
        if isinstance(data, dict):
            story_slides = data.get('slides', [])
            caption = data.get('caption', caption)
        elif isinstance(data, list):
            story_slides = data
            if story_slides and 'caption' in story_slides[0]:
                caption = story_slides[0]['caption']
        else:
            story_slides = []

        if not story_slides or not isinstance(story_slides, list):
            print("Lỗi: Gemini không trả về dữ liệu slides hợp lệ.")
            return None, None

        print("✅ Đã tạo kịch bản thành công.")
        return story_slides, caption

    except Exception as e:
        print(f"Lỗi khi gọi Gemini tạo kịch bản: {e}")
        return None, None

# HÀM PHỤ: TẠO NỘI DUNG VÀ PROMPT TÌM ẢNH CHUNG (Cho các App tâm linh)
def propose_content_and_image_query(app_name, user_input, num_slides=4):
    print(f"Đang yêu cầu Gemini tạo nội dung {app_name} cho: {user_input}...")

    # Định nghĩa các System Prompt và Image Query dựa trên App
    prompts_map = {
        'phong_thuy': {
            'system': f"Bạn là chuyên gia Phong Thủy, hãy viết {num_slides} đoạn văn ngắn (mỗi đoạn 30-50 từ) để tạo thành một lời khuyên chuyên sâu về chủ đề '{user_input}'. Trả về JSON array: [{{'text': 'Đoạn 1'}}, {{'text': 'Đoạn 2'}}, ...].",
            'image_query': f"minimalist feng shui background {user_input}",
            'caption': f"#phongthuy #{user_input.replace(' ', '')}"
        },
        'tu_vi': {
            'system': f"Bạn là chuyên gia Tử Vi. Hãy viết {num_slides} đoạn luận giải ngắn (mỗi đoạn 30-50 từ) về '{user_input}' theo phong cách cổ điển, bí ẩn. Trả về JSON array: [{{'text': 'Đoạn 1'}}, {{'text': 'Đoạn 2'}}, ...].",
            'image_query': "ancient chinese astrology chart dark background",
            'caption': f"#lasotuvi #luangiaituvi"
        },
        'tarot': {
            'system': f"Bạn là một Reader Tarot chuyên nghiệp. Hãy viết {num_slides} đoạn giải mã lá bài (mỗi đoạn 30-50 từ) về tình huống '{user_input}' (ví dụ: 'What is blocking my success?'). Trả về JSON array: [{{'text': 'Đoạn 1'}}, {{'text': 'Đoạn 2'}}, ...].",
            'image_query': "tarot card mystical background golden light",
            'caption': f"#tarotdaily #readingtarot"
        },
        'cung_hoang_dao': {
            'system': f"Bạn là chuyên gia Chiêm Tinh. Hãy viết {num_slides} dự đoán ngắn (mỗi đoạn 30-50 từ) cho cung '{user_input}' (ví dụ: 'Song Tử') về tình yêu, sự nghiệp, sức khỏe. Trả về JSON array: [{{'text': 'Đoạn 1'}}, {{'text': 'Đoạn 2'}}, ...].",
            'image_query': "zodiac sign galaxy background minimal",
            'caption': f"#{user_input.replace(' ', '')} #cung_hoang_dao"
        }
    }

    config = prompts_map.get(app_name)
    if not config:
        return None, None, None

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[config['system']],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        # Thử tải JSON
        slides_data = json.loads(response.text)
        if not isinstance(slides_data, list) or not slides_data:
            print("Lỗi: Gemini không trả về dữ liệu slides hợp lệ (JSON Array).")
            return None, None, None

        return slides_data, config['image_query'], config['caption']

    except Exception as e:
        print(f"Lỗi khi gọi Gemini tạo nội dung {app_name}: {e}")
        return None, None, None

# --- HÀM TẠO TRUYỆN CỔ TÍCH (GEMINI) ---
def generate_fairy_tale():
    print("Bắt đầu: Yêu cầu Gemini tạo một câu chuyện cổ tích ngẫu nhiên...")

    # System Prompt cho Truyện Cổ Tích
    system_prompt = """
    Bạn là một nhà kể chuyện cổ tích chuyên nghiệp. Nhiệm vụ của bạn là chọn MỘT câu chuyện cổ tích kinh điển/phổ biến từ bất kỳ nền văn hóa nào trên thế giới (ví dụ: Grimms, Andersen, Việt Nam, Trung Quốc, v.v.), sau đó tóm tắt nó thành một kịch bản hấp dẫn.
    QUY TẮC:
    1. Câu chuyện phải là một truyện cổ tích có tính giáo dục hoặc truyền cảm hứng.
    2. Kịch bản phải dài từ **4 đến 10 slides**. Mỗi slide phải là một đoạn văn ngắn (tối đa 40 từ).
    3. Output BẮT BUỘC phải là một đối tượng JSON (array of objects) với các khóa sau:
       - 'text': Nội dung ngắn gọn cho slide.
       - 'image_query': Một từ khóa tiếng Anh ngắn gọn (2-5 từ) để tìm ảnh minh họa cho slide này (Ví dụ: 'magical castle', 'brave prince', 'evil witch').
       - 'caption': Phần caption cuối cùng cho toàn bộ video (chứa cả hashtag).
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[system_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        data = json.loads(response.text)
        caption = "Câu chuyện cổ tích." # Caption mặc định

        # XỬ LÝ LINH HOẠT TỪ ĐIỂN HOẶC DANH SÁCH (Tương tự hàm generate_story_and_prompts)
        if isinstance(data, dict):
             # Trường hợp Gemini trả về object { "slides": [{}], "caption": "..." }
            story_slides = data.get('slides', data.get('story', []))
            caption = data.get('caption', caption)
        elif isinstance(data, list):
            # Trường hợp Gemini trả về array trực tiếp [{}, {}]
            story_slides = data
            if story_slides and 'caption' in story_slides[-1]:
                caption = story_slides[-1]['caption'] # Lấy caption từ slide cuối nếu có
        else:
            story_slides = []

        if not story_slides or not isinstance(story_slides, list):
            print("Lỗi: Gemini không trả về dữ liệu slides hợp lệ cho Cổ Tích.")
            return None, None

        print("✅ Đã tạo kịch bản Truyện Cổ Tích thành công.")
        return story_slides, caption

    except Exception as e:
        print(f"Lỗi khi gọi Gemini tạo kịch bản Truyện Cổ Tích: {e}")
        return None, None

# --- HÀM TẠO TRUYỆN CƯỜI (GEMINI) ---
def generate_joke():
    print("Bắt đầu: Yêu cầu Gemini tạo một câu chuyện cười ngắn, mạnh...")

    # System Prompt cho Truyện Cười
    system_prompt = """
    Bạn là một diễn viên hài độc thoại chuyên nghiệp. Nhiệm vụ của bạn là tạo MỘT câu chuyện cười/tình huống hài hước ngắn gọn.
    QUY TẮC:
    1. Câu chuyện phải cực kỳ ngắn gọn, có **tác động gây cười mạnh mẽ và bất ngờ** ở slide cuối cùng.
    2. Kịch bản phải dài **3 đến 5 slides** (tình huống, diễn biến, punchline). Mỗi slide TỐI ĐA 30 từ.
    3. Output BẮT BUỘC phải là một đối tượng JSON (array of objects) với các khóa sau:
       - 'text': Nội dung ngắn gọn cho slide.
       - 'image_query': Một từ khóa tiếng Anh hài hước/độc đáo (3-5 từ) để tìm ảnh nền cho slide này (Ví dụ: 'surprised face meme', 'funny cartoon dog', 'awkward situation').
       - 'caption': Phần caption cuối cùng cho toàn bộ video (chứa cả hashtag).
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[system_prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )

        data = json.loads(response.text)
        caption = "Truyện cười hài hước." # Caption mặc định

        # XỬ LÝ LINH HOẠT (Tương tự hàm generate_fairy_tale)
        if isinstance(data, dict):
            story_slides = data.get('slides', data.get('joke', []))
            caption = data.get('caption', caption)
        elif isinstance(data, list):
            story_slides = data
            if story_slides and 'caption' in story_slides[-1]:
                caption = story_slides[-1]['caption']
        else:
            story_slides = []

        if not story_slides or not isinstance(story_slides, list) or len(story_slides) < 3:
            print("Lỗi: Gemini không trả về dữ liệu slides hợp lệ cho Truyện Cười (Cần ít nhất 3 slides).")
            return None, None

        print("✅ Đã tạo kịch bản Truyện Cười thành công.")
        return story_slides, caption

    except Exception as e:
        print(f"Lỗi khi gọi Gemini tạo kịch bản Truyện Cười: {e}")
        return None, None

# ==========================================================
# --- KHỐI HÀM APP CON ---
# ==========================================================

# 1. HÀM APP CÂU CHUYỆN
def run_story_app(drive_service, theme_domain):
    print("\n--- 📝 App Câu Chuyện Khởi Động ---")
    print(f"-> Sử dụng lĩnh vực: {theme_domain}")

    # 1. AI TỰ ĐỀ XUẤT CHỦ ĐỀ
    # Sử dụng lĩnh vực đã chọn ngẫu nhiên để đề xuất chủ đề cụ thể
    chosen_theme = propose_random_theme(theme_domain)
    if not chosen_theme:
        send_telegram_notification("❌ Lỗi: Không thể đề xuất chủ đề từ AI.")
        return

    # 2. TẠO KỊCH BẢN
    story_slides, final_caption = generate_story_and_prompts(chosen_theme)
    if not story_slides:
        send_telegram_notification(f"❌ Lỗi: Không thể tạo kịch bản cho chủ đề '{chosen_theme}'.")
        return

    # 3. TẠO THƯ MỤC MỚI
    safe_folder_name = re.sub(r'[^\w\s-]', '', chosen_theme).strip()[:50] # bỏ .replace(' ', '-')
    new_folder_id = create_drive_folder(safe_folder_name, STORY_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id:
        send_telegram_notification(f"❌ Lỗi: Không thể tạo thư mục Drive cho chủ đề '{chosen_theme}'.")
        return

    # 4. LẶP QUA CÁC SLIDE & TẢI LÊN DRIVE (Logic giữ nguyên)
    drive_file_links = []
    print(f"\n--- Bắt đầu xử lý {len(story_slides)} slides cho chủ đề: '{chosen_theme}' ---")

    for i, slide in enumerate(story_slides):
        final_image_file = create_image_with_text(
            slide['text'],
            drive_service,
            i + 1,
            chosen_theme # Theme dùng làm query dự phòng cho ảnh
        )

        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link:
                drive_file_links.append(drive_link)
            if os.path.exists(final_image_file):
                os.remove(final_image_file)

    # 5. GỬI THÔNG BÁO CUỐI CÙNG
    if drive_file_links:
        full_message = (
            f"✅ <b>Quy trình CÂU CHUYỆN HOÀN TẤT!</b>\n"
            f"<b>Chủ đề:</b> {chosen_theme}\n"
            f"<b>Caption gợi ý:</b> {final_caption}\n\n"
        )
        send_telegram_notification(full_message, image_urls=drive_file_links)
    else:
        send_telegram_notification(f"❌ Quy trình Câu chuyện thất bại cho chủ đề '{chosen_theme}'.")

# 2. HÀM APP PHONG THỦY
def run_phong_thuy(drive_service, topic):
    print(f"--- 🔮 App Phong Thủy Khởi Động cho chủ đề: {topic} ---")

    # 1. TẠO NỘI DUNG & PROMPT ẢNH
    story_slides, image_query, final_caption = propose_content_and_image_query('phong_thuy', topic, num_slides=4)
    if not story_slides: return

    # 2. TẠO THƯ MỤC VÀ UPLOAD
    safe_folder_name = f"PT {topic}" # bỏ .replace(' ', '-')
    new_folder_id = create_drive_folder(safe_folder_name, PHONG_THUY_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id:
        send_telegram_notification(f"❌ Lỗi: Không thể tạo thư mục Drive cho Phong Thủy.")
        return

    drive_file_links = []
    for i, slide in enumerate(story_slides):
        # TẠO ẢNH: Sử dụng image_query cố định cho Phong Thủy
        final_image_file = create_image_with_text(
            slide['text'],
            drive_service,
            i + 1,
            image_query # Dùng query cố định cho chủ đề này
        )
        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link: drive_file_links.append(drive_link)
            if os.path.exists(final_image_file): os.remove(final_image_file)

    if drive_file_links:
        full_message = (f"✅ <b>Quy trình PHONG THỦY HOÀN TẤT!</b>\n<b>Chủ đề:</b> {topic}\n<b>Caption gợi ý:</b> {final_caption}")
        send_telegram_notification(full_message, image_urls=drive_file_links)

# 3. HÀM APP TỬ VI
def run_la_so_tu_vi(drive_service, topic):
    print(f"--- 🌌 App Tử Vi Khởi Động cho chủ đề: {topic} ---")

    story_slides, image_query, final_caption = propose_content_and_image_query('tu_vi', topic, num_slides=5)
    if not story_slides: return

    safe_folder_name = f"TV {topic}" # bỏ .replace(' ', '-')
    new_folder_id = create_drive_folder(safe_folder_name, TU_VI_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id:
        send_telegram_notification(f"❌ Lỗi: Không thể tạo thư mục Drive cho Tử Vi.")
        return

    drive_file_links = []
    for i, slide in enumerate(story_slides):
        final_image_file = create_image_with_text(
            slide['text'],
            drive_service,
            i + 1,
            image_query
        )
        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link: drive_file_links.append(drive_link)
            if os.path.exists(final_image_file): os.remove(final_image_file)

    if drive_file_links:
        full_message = (f"✅ <b>Quy trình TỬ VI HOÀN TẤT!</b>\n<b>Chủ đề:</b> {topic}\n<b>Caption gợi ý:</b> {final_caption}")
        send_telegram_notification(full_message, image_urls=drive_file_links)

# 4. HÀM APP TAROT
def run_tarot(drive_service, topic):
    print(f"--- 🃏 App Tarot Khởi Động cho chủ đề: {topic} ---")

    story_slides, image_query, final_caption = propose_content_and_image_query('tarot', topic, num_slides=3)
    if not story_slides: return

    safe_folder_name = f"Tarot {topic}" # bỏ .replace(' ', '-')
    new_folder_id = create_drive_folder(safe_folder_name, TAROT_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id: return

    # Lặp và upload ảnh
    drive_file_links = []
    for i, slide in enumerate(story_slides):
        final_image_file = create_image_with_text(slide['text'], drive_service, i + 1, image_query)
        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link: drive_file_links.append(drive_link)
            if os.path.exists(final_image_file): os.remove(final_image_file)

    if drive_file_links:
        full_message = (f"✅ <b>Quy trình TAROT HOÀN TẤT!</b>\n<b>Chủ đề:</b> {topic}\n<b>Caption gợi ý:</b> {final_caption}")
        send_telegram_notification(full_message, image_urls=drive_file_links)

# 5. HÀM APP CUNG HOÀNG ĐẠO
def run_cung_hoang_dao(drive_service, topic):
    print(f"--- 🌟 App Cung Hoàng Đạo Khởi Động cho chủ đề: {topic} ---")

    story_slides, image_query, final_caption = propose_content_and_image_query('cung_hoang_dao', topic, num_slides=5)
    if not story_slides: return

    safe_folder_name = f"CHĐ {topic}" # bỏ .replace(' ', '-')
    new_folder_id = create_drive_folder(safe_folder_name, CUNG_HOANG_DAO_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id: return

    # Lặp và upload ảnh
    drive_file_links = []
    for i, slide in enumerate(story_slides):
        final_image_file = create_image_with_text(slide['text'], drive_service, i + 1, image_query)
        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link: drive_file_links.append(drive_link)
            if os.path.exists(final_image_file): os.remove(final_image_file)

    if drive_file_links:
        full_message = (f"✅ <b>Quy trình CUNG HOÀNG ĐẠO HOÀN TẤT!</b>\n<b>Chủ đề:</b> {topic}\n<b>Caption gợi ý:</b> {final_caption}")
        send_telegram_notification(full_message, image_urls=drive_file_links)

# --- HÀM APP TRUYỆN CỔ TÍCH ---
def run_fairy_tale_app(drive_service, topic=None): # Giữ topic để phù hợp với hàm main, nhưng không dùng
    print("--- ✨ App TRUYỆN CỔ TÍCH Khởi Động ---")

    # 1. TẠO NỘI DUNG & PROMPT ẢNH (Không cần chủ đề)
    # Hàm generate_fairy_tale sẽ trả về story_slides (gồm text và image_query) và final_caption
    story_slides, final_caption = generate_fairy_tale()
    if not story_slides: return

    # 2. TẠO THƯ MỤC VÀ UPLOAD
    # Tên thư mục sẽ lấy một phần nội dung slide đầu tiên
    first_text = story_slides[0]['text'].split('.')[0].strip()
    safe_folder_name = f"CT {first_text}"
    new_folder_id = create_drive_folder(safe_folder_name, FAIRY_TALE_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id:
        send_telegram_notification(f"❌ Lỗi: Không thể tạo thư mục Drive cho Truyện Cổ Tích.")
        return

    drive_file_links = []
    for i, slide in enumerate(story_slides):
        # TẠO ẢNH: Sử dụng image_query của từng slide
        image_query = slide.get('image_query', 'magical fairy tale forest') # Image query dự phòng
        final_image_file = create_image_with_text(
            slide['text'],
            drive_service,
            i + 1,
            image_query
        )
        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link: drive_file_links.append(drive_link)
            if os.path.exists(final_image_file): os.remove(final_image_file)

    if drive_file_links:
        full_message = (f"✅ <b>Quy trình TRUYỆN CỔ TÍCH HOÀN TẤT!</b>\n<b>Chủ đề:</b> {first_text}...\n<b>Caption gợi ý:</b> {final_caption}")
        send_telegram_notification(full_message, image_urls=drive_file_links)

# --- HÀM APP TRUYỆN CƯỜI ---
def run_joke_app(drive_service, topic=None): # Giữ topic để phù hợp với hàm main, nhưng không dùng
    print("--- 😂 App TRUYỆN CƯỜI Khởi Động ---")

    # 1. TẠO NỘI DUNG & PROMPT ẢNH (Không cần chủ đề)
    story_slides, final_caption = generate_joke()
    if not story_slides: return

    # 2. TẠO THƯ MỤC VÀ UPLOAD
    # Tên thư mục sẽ lấy một phần nội dung slide đầu tiên
    first_text = story_slides[0]['text'].split('.')[0].strip()
    safe_folder_name = f"TC {first_text}"
    new_folder_id = create_drive_folder(safe_folder_name, JOKE_DRIVE_FOLDER_ID, drive_service)

    if not new_folder_id:
        send_telegram_notification(f"❌ Lỗi: Không thể tạo thư mục Drive cho Truyện Cười.")
        return

    drive_file_links = []
    for i, slide in enumerate(story_slides):
        # TẠO ẢNH: Sử dụng image_query của từng slide
        image_query = slide.get('image_query', 'funny unexpected moment') # Image query dự phòng
        final_image_file = create_image_with_text(
            slide['text'],
            drive_service,
            i + 1,
            image_query
        )
        if final_image_file:
            drive_link = upload_to_drive(final_image_file, drive_service, new_folder_id)
            if drive_link: drive_file_links.append(drive_link)
            if os.path.exists(final_image_file): os.remove(final_image_file)

    if drive_file_links:
        full_message = (f"✅ <b>Quy trình TRUYỆN CƯỜI HOÀN TẤT!</b>\n<b>Chủ đề:</b> {first_text}...\n<b>Caption gợi ý:</b> {final_caption}")
        send_telegram_notification(full_message, image_urls=drive_file_links)

# ==========================================================
# --- KHỐI CẤU HÌNH TỰ ĐỘNG CHỌN (MỚI) ---
# ==========================================================
# LƯU Ý: PHẢI CHẮC CHẮN CÁC HÀM run_story_app, run_phong_thuy, v.v. ĐƯỢC ĐỊNH NGHĨA TRƯỚC HÀM MAIN

# Cần giữ cố định để script biết thứ tự các cột
APP_COLUMN_MAPPING = {
    "CAUCHUYEN": 1,
    "PHONGTHUY": 2,
    "TUVI": 3,
    "TAROT": 4,
    "CUNGHOANGDAO": 5,
    "FAIRYTALE": 6,
    "JOKE": 7
}

# ==========================================================
# --- HÀM TẢI CẤU HÌNH TỪ GOOGLE SHEET (SỬA LẠI THEO CỘT) ---
# ==========================================================
def load_app_modes_from_sheet(gsheet_id):
    EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{gsheet_id}/export?format=csv&gid=0"

    try:
        print(f"Đang tải cấu hình ứng dụng từ Google Sheet ID: {gsheet_id}...")
        response = requests.get(EXPORT_URL, timeout=10)

        if response.status_code != 200:
            print(f"❌ Lỗi tải Sheet (Status {response.status_code}). Đảm bảo Sheet Public và ID chính xác.")
            return None

        csv_data = response.content.decode('utf-8')
        reader = csv.reader(StringIO(csv_data))

        # 1. Đọc dòng tiêu đề (HEADER)
        try:
            headers = next(reader)
            if not headers: raise StopIteration
        except StopIteration:
            print("❌ Sheet trống hoặc không có dòng tiêu đề.")
            return None

        dynamic_app_modes_raw = {}

        # 2. Xử lý tiêu đề và tạo cấu hình ban đầu
        for col_index, header in enumerate(headers):
            # Chuẩn hóa tên tiêu đề để so khớp với APP_COLUMN_MAPPING
            normalized_header = header.strip().upper().replace(' ', '')

            # Lấy ID và tên chính xác dựa trên tiêu đề cột
            app_id = APP_COLUMN_MAPPING.get(normalized_header)

            if app_id:
                dynamic_app_modes_raw[app_id] = {
                    "name": header.strip(), # Giữ nguyên tên gốc có dấu
                    "domains": [], # Khởi tạo danh sách domains trống
                    "col_index": col_index # Lưu chỉ mục cột để quét domain sau này
                }

        if not dynamic_app_modes_raw:
            print("❌ Không tìm thấy tiêu đề cột hợp lệ (Câu chuyện, Phong thủy,...) trong Sheet.")
            return None

        # 3. Quét các dòng còn lại để thu thập Domains (chủ đề)
        for row in reader:
            for app_id, config in dynamic_app_modes_raw.items():
                col_index = config["col_index"]

                if col_index < len(row):
                    domain = row[col_index].strip()
                    if domain:
                        # Thêm domain (chủ đề) vào danh sách ứng dụng tương ứng
                        config["domains"].append(domain)

        # 4. Loại bỏ chỉ mục cột trước khi trả về
        for config in dynamic_app_modes_raw.values():
            del config["col_index"]

        print(f"✅ Đã tải thành công {len(dynamic_app_modes_raw)} cấu hình ứng dụng theo cột.")
        return dynamic_app_modes_raw

    except requests.exceptions.RequestException as e:
        print(f"❌ Lỗi kết nối khi tải Google Sheet: {e}")
        return None
    except Exception as e:
        print(f"❌ Lỗi xử lý dữ liệu từ Google Sheet: {e}")
        return None

# ==========================================================
# --- HÀM CHÍNH (MAIN) - ĐÃ THÊM TỰ ĐỘNG HÓA VÀ VÒNG LẶP ---
# ==========================================================

if __name__ == "__main__":
    # 1. KIỂM TRA CẤU HÌNH VÀ BẮT ĐẦU XÁC THỰC DRIVE
    if not os.path.exists(FONT_PATH):
        error_msg = f"⚠️ LỖI: Không tìm thấy file font '{FONT_PATH}'. Vui lòng tải một file font (.ttf) và đặt tên file là 'font.ttf'."
        print(error_msg)
        send_telegram_notification(f"LỖI KHỞI ĐỘNG: {error_msg}")
        exit()
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY":
        error_msg = "⚠️ LỖI: GEMINI_API_KEY chưa được thiết lập."
        print(error_msg)
        send_telegram_notification(f"LỖI KHỞI ĐỘNG: {error_msg}")
        exit()
    if not os.path.exists(CLIENT_SECRETS_FILE):
        error_msg = f"⚠️ LỖI: Không tìm thấy file cấu hình ứng dụng: {CLIENT_SECRETS_FILE}"
        print(error_msg)
        send_telegram_notification(f"LỖI KHỞI ĐỘNG: {error_msg}")
        exit()

    # 2. XÁC THỰC GOOGLE DRIVE
    print("Đang xác thực Google Drive...")
    gauth = GoogleAuth()
    gauth.settings['client_config_file'] = CLIENT_SECRETS_FILE
    gauth.settings['save_credentials_file'] = CREDENTIALS_FILE

    # --- KHỐI THỬ TẢI TOKEN CŨ VÀ XỬ LÝ LỖI ---
    try:
        # 1. Thử tải token cũ
        gauth.LoadCredentialsFile(CREDENTIALS_FILE)

        # 2. Kiểm tra nếu token tải lên bị lỗi hoặc hết hạn
        if gauth.credentials is None or gauth.credentials.access_token_expired:
            raise Exception("Token không hợp lệ hoặc đã hết hạn.")

        print("✅ Đã tải mã token thành công.")

    except Exception as e:
        # Bất kỳ lỗi nào khi tải token hoặc token hết hạn đều nhảy vào đây
        error_msg_token = f"⚠️ LỖI TOKEN GẶP PHẢI: {e}. Bắt buộc phải xác thực lại."
        print(error_msg_token)
        # GỬI THÔNG BÁO CẦN XÁC THỰC LẠI
        send_telegram_notification(f"CẦN XÁC THỰC DRIVE: {error_msg_token}")

        # --- LOGIC QUAN TRỌNG: XÓA FILE HỎNG ---
        if os.path.exists(CREDENTIALS_FILE):
            os.remove(CREDENTIALS_FILE)
            print(f"-> Đã xóa file token hỏng: {CREDENTIALS_FILE}")

        # --- BẮT ĐẦU QUÁ TRÌNH XÁC THỰC LẠI QUA WEB ---
        print("Mã token chưa tồn tại hoặc đã hết hạn. Đang xác thực qua Web...")
        try:
            gauth.LocalWebserverAuth()
            if gauth.credentials:
                gauth.SaveCredentialsFile(CREDENTIALS_FILE)
                print("✅ Đã xác thực thành công và lưu mã token mới.")
                # GỬI THÔNG BÁO XÁC THỰC THÀNH CÔNG
                send_telegram_notification("✅ XÁC THỰC DRIVE: Đã xác thực lại Google Drive thành công.")
            else:
                error_msg_auth_fail = "❌ Xác thực Drive thất bại."
                print(error_msg_auth_fail)
                send_telegram_notification(f"LỖI DRIVE: {error_msg_auth_fail}")
                exit()
        except Exception as e:
            error_msg_critical_auth = f"❌ Lỗi nghiêm trọng khi xác thực Drive: {e}"
            print(error_msg_critical_auth)
            send_telegram_notification(f"LỖI NGHIÊM TRỌNG DRIVE: {error_msg_critical_auth}")
            exit()

    drive_service = GoogleDrive(gauth)
    print("✅ Đã kết nối Google Drive thành công.")

    # ==========================================================
    # --- 4. VÒNG LẶP TỰ ĐỘNG HÓA CHÍNH (ĐÃ SỬA THEO YÊU CẦU) ---
    # ==========================================================
    while True:
        print("\n" + "="*70)
        print("BẮT ĐẦU VÒNG LẶP MỚI: ĐANG CẬP NHẬT CẤU HÌNH TỪ GOOGLE SHEET")
        print("="*70)

        # --- TẢI CẤU HÌNH ---
        try:
            dynamic_app_modes_raw = load_app_modes_from_sheet(GSHEET_ID)
        except Exception as e:
            error_msg_load_sheet = f"❌ Lỗi nghiêm trọng khi tải cấu hình từ Google Sheet: {e}"
            print(error_msg_load_sheet)
            send_telegram_notification(f"LỖI SHEET NGHIÊM TRỌNG: {error_msg_load_sheet}")
            # Không exit() ở đây mà chỉ time.sleep(TIMEOUT_SECONDS) và continue như logic cũ

        if dynamic_app_modes_raw is None:
            print("\n❌ KHÔNG THỂ TẢI CẤU HÌNH TỪ GOOGLE SHEET. Chương trình sẽ thử lại sau 5 giây.")
            time.sleep(TIMEOUT_SECONDS)
            continue

        APP_MODES = {}
        APP_FUNCTION_MAP = {
            1: run_story_app,
            2: run_phong_thuy,
            3: run_la_so_tu_vi,
            4: run_tarot,
            5: run_cung_hoang_dao,
            6: run_fairy_tale_app,
            7: run_joke_app
        }

        # 1. TẠO APP_MODES TỪ SHEET (cho các app cũ)
        for app_id, config in dynamic_app_modes_raw.items():
            if app_id in APP_FUNCTION_MAP:
                config["function"] = APP_FUNCTION_MAP[app_id]
                APP_MODES[app_id] = config
            else:
                print(f"Cảnh báo: Không tìm thấy hàm thực thi cho ID ứng dụng {app_id}. Bỏ qua.")

        # 2. THÊM CÁC APP KHÔNG CẦN SHEET VÀO APP_MODES (Cho các app mới)
        # Thêm Truyện Cổ Tích
        if 6 not in APP_MODES:
            APP_MODES[6] = {
                "name": "Truyện Cổ Tích (AI)",
                "domains": ["AI_GENERATED_FAIRY_TALE"], # Dùng một chủ đề giả để logic check không bị lỗi
                "function": run_fairy_tale_app,
                "mode": "auto" # Thiết lập mặc định
            }

        # Thêm Truyện Cười
        if 7 not in APP_MODES:
            APP_MODES[7] = {
                "name": "Truyện Cười (AI)",
                "domains": ["AI_GENERATED_JOKE"], # Dùng một chủ đề giả để logic check không bị lỗi
                "function": run_joke_app,
                "mode": "auto" # Thiết lập mặc định
            }

        if not APP_MODES:
            print("\n❌ Lỗi: Không có ứng dụng nào được cấu hình hợp lệ sau khi tải Sheet. Chương trình sẽ thử lại sau 5 giây.")
            time.sleep(TIMEOUT_SECONDS)
            continue

        print(f"✅ Đã tải và cấu hình thành công {len(APP_MODES)} ứng dụng.")
        # --- KẾT THÚC LOGIC TẢI CẤU HÌNH ---

        # A. Tự động ngẫu nhiên chọn Ứng dụng
        available_apps = list(APP_MODES.keys())

        if not available_apps:
            print("❌ Lỗi: Không có ứng dụng nào được cấu hình hợp lệ để chạy.")
            time.sleep(TIMEOUT_SECONDS) # Thêm sleep để tránh vòng lặp nhanh
            continue

        random.shuffle(available_apps)
        app_id = available_apps[0]

        chosen_app = APP_MODES[app_id]
        app_name = chosen_app["name"]
        app_func = chosen_app["function"]
        app_domains = chosen_app["domains"]

        print(f"🤖 Đang chọn ứng dụng...")
        print(f"✅ Đã chọn Ứng dụng {app_id}: {app_name}")

        # B. Kiểm tra chủ đề và THỰC THI
        if app_domains:
            # --- LOGIC CHỌN DOMAIN DỰA TRÊN APP_ID ---
            chosen_domain = None
            if app_id == 1: # CAUCHUYEN
                # Rule 1: Chọn ngẫu nhiên từ domains
                chosen_domain = random.choice(app_domains)
                print("Lựa chọn: Ngẫu nhiên (CAUCHUYEN)")
            elif app_id in [6, 7]: # FAIRYTALE hoặc JOKE
                # Rule 3: KHÔNG CẦN DOMAIN TỪ SHEET, AI TỰ TẠO
                chosen_domain = f"AI_Generated_{app_name}"
                print(f"Lựa chọn: Chủ đề tự động tạo bởi AI ({app_name})")
            elif app_domains:
                # Rule 2: Chọn chủ đề ĐẦU TIÊN (Cho các app còn lại)
                chosen_domain = app_domains[0]
                print("Lựa chọn: Chủ đề đầu tiên của cột (B->E)")

            if chosen_domain:
                print(f"✅ Đã chọn Chủ đề: **{chosen_domain}**")

                try:
                    print(f"\n--- BẮT ĐẦU THỰC THI: {app_name.upper()} ---")
                    app_func(drive_service, chosen_domain)
                    print(f"\n--- KẾT THÚC THỰC THI: {app_name.upper()} ---\n")
                except Exception as e:
                    # GỬI THÔNG BÁO LỖI CHẠY ỨNG DỤNG
                    error_msg_run_app = f"❌ Lỗi nghiêm trọng trong quá trình chạy ứng dụng {app_name}: {e}"
                    print(error_msg_run_app)
                    send_telegram_notification(f"LỖI CHẠY APP: {error_msg_run_app}")

            # D. Tùy chọn tiếp tục hoặc dừng hẳn (CHỈ HỎI KHI CHẠY THÀNH CÔNG/GẶP LỖI SAU KHI CHỌN DOMAIN)
            while True:
                try:
                    # Cố gắng thực hiện Input có Timeout (sẽ lỗi trên Windows)
                    prompt = f"Bạn có muốn tiếp tục chạy một vòng lặp ngẫu nhiên nữa không? (y/n) (Tự động tiếp tục sau {TIMEOUT_SECONDS}s): "
                    print(prompt, end='', flush=True)

                    # Sử dụng select.select để chờ input trong x giây
                    # Lỗi WinError 10038 sẽ xảy ra tại đây trên Windows
                    i, _, _ = select.select([sys.stdin], [], [], TIMEOUT_SECONDS)

                    if i:
                        # Có input, đọc input từ stdin
                        choice = sys.stdin.readline().strip().lower()
                    else:
                        # Timeout, tự động chọn 'y'
                        choice = 'y'
                        print("\n⏰ Hết giờ! Tự động chọn 'y' (chạy tiếp).")

                except OSError as e:
                    # Bắt lỗi Windows (WinError 10038) hoặc lỗi khác của select
                    if 'not a socket' in str(e):
                        # Lỗi Windows đặc trưng -> Chuyển sang chế độ Tự động
                        print(f"\n⚠️ Cảnh báo Windows: Không thể dùng select.select() với stdin. Chuyển sang chế độ Tự động chạy tiếp sau {TIMEOUT_SECONDS} giây.")
                        choice = 'y'
                        time.sleep(TIMEOUT_SECONDS) # Chờ một khoảng thời gian trước khi tự động chạy tiếp
                    else:
                        # Xử lý các lỗi OSError khác (Nếu có)
                        print(f"\n❌ Lỗi OSError nghiêm trọng: {e}. Tự động chạy tiếp.")
                        choice = 'y'
                        time.sleep(TIMEOUT_SECONDS)


                if choice == 'n':
                    print("Chương trình đã dừng. Tạm biệt!")
                    exit()
                elif choice == 'y':
                    # Đảm bảo bạn chỉ ngủ 3 giây hoặc dùng biến TIMEOUT_SECONDS để làm chậm vòng lặp
                    print("Tiếp tục chạy vòng lặp mới sau 3 giây...")
                    # LƯU Ý: time.sleep(3) hoặc time.sleep(TIMEOUT_SECONDS) tùy ý bạn
                    time.sleep(TIMEOUT_SECONDS)
                    break # Quay lại đầu vòng lặp while True để tải lại cấu hình
                else:
                    print("Lựa chọn không hợp lệ. Vui lòng nhập 'y' hoặc 'n'.")

        else:
            # XỬ LÝ LỖI: Ứng dụng không có lĩnh vực/chủ đề
            error_msg_no_domain = f"❌ Lỗi: Ứng dụng '{app_name}' không có danh sách lĩnh vực/chủ đề được định nghĩa. Tự động chuyển sang vòng lặp mới sau 2 giây."
            print(error_msg_no_domain)
            send_telegram_notification(f"LỖI CẤU HÌNH: {error_msg_no_domain}")
            time.sleep(TIMEOUT_SECONDS)
            continue # Tự động bắt đầu vòng lặp mới mà KHÔNG cần hỏi
