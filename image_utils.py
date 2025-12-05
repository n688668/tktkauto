import os, random, requests
from PIL import Image, ImageDraw, ImageFont
from config import FONT_PATH, PEXELS_API_KEY, UNSPLASH_ACCESS_KEY, BACKGROUND_IMAGES_FOLDER_ID
from drive_utils import get_random_background_image

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

# --- HÀM TẢI ẢNH NGẪU NHIÊN TỪ PEXELS (Ưu tiên 1) ---
def get_random_pexels_image(query, slide_index):
    if not PEXELS_API_KEY or PEXELS_API_KEY == "YOUR_PEXELS_API_KEY":
        print("  - Cảnh báo: PEXELS_API_KEY chưa được cấu hình. Bỏ qua Pexels.")
        return None

    THEME_KEYWORDS = [
        "rain", "snow", "forest", "mountain", "sea beach",
        "sunset", "sunrise", "old books", "potted plant indoor"
    ]
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
        # adjust font_size if fallback
        font_size = 24

    MAX_TEXT_WIDTH = W - 240
    wrapped_lines = text_wrap(text_to_overlay, font, MAX_TEXT_WIDTH)

    # =======================================================
    # *** TÍNH CHIỀU CAO DÒNG (LINE HEIGHT) CHÍNH XÁC VÀ KHOẢNG CÁCH DÒNG ***
    # =======================================================
    # cố gắng lấy ascent/descent từ font
    try:
        ascent, descent = font.getmetrics()
        default_line_height = ascent + descent
    except Exception:
        default_line_height = font_size + 10

    # line_spacing tỷ lệ theo font_size để tránh dính dòng
    line_spacing = max(12, int(font_size * 0.20))

    # Tính chiều cao thực tế cho từng dòng (dùng bounding box nếu cần)
    line_heights = []
    for line in wrapped_lines:
        if not line:
            # dùng 60% chiều cao mặc định cho dòng rỗng (tạo khoảng cách)
            line_heights.append(int(default_line_height * 0.6))
            continue
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            lh = bbox[3] - bbox[1]
            # đảm bảo không nhỏ hơn default
            if lh < default_line_height * 0.8:
                lh = int(default_line_height)
        except Exception:
            lh = int(default_line_height)
        line_heights.append(int(lh))

    # Tổng chiều cao của khối văn bản = sum dòng + spacing giữa các dòng
    total_text_height = sum(line_heights) + line_spacing * (max(0, len(line_heights) - 1))

    # 2. Đặt điểm bắt đầu Y tại trung tâm khung hình
    y_start_center = (H // 2)
    y_current = y_start_center - (total_text_height // 2)

    # =======================================================
    # VẼ CÁC DÒNG VỚI KHOẢNG CÁCH ĐÃ TÍNH
    # =======================================================
    for idx, line in enumerate(wrapped_lines):
        if not line:
            y_current += line_heights[idx] + line_spacing
            continue

        # Tính toán bounding box cho căn giữa ngang và lấy chiều rộng
        try:
            text_bbox = draw.textbbox((0, 0), line, font=font)
            textwidth = text_bbox[2] - text_bbox[0]
            textheight = text_bbox[3] - text_bbox[1]
        except Exception:
            textwidth = font.getlength(line) if hasattr(font, 'getlength') else 500
            textheight = line_heights[idx]

        # Căn giữa theo chiều ngang
        x = (W - textwidth) // 2

        # Vẽ nền đen mờ sau chữ (dùng alpha overlay đã paste phía trên)
        padding_x = 24
        padding_y = max(10, int(line_heights[idx] * 0.2))
        rect_top = y_current - padding_y
        rect_bottom = y_current + textheight + padding_y
        draw.rectangle([(x - padding_x, rect_top), (x + textwidth + padding_x, rect_bottom)], fill=(0, 0, 0))

        # Vẽ chữ
        draw.text((x, y_current), line, fill=(255, 255, 255), font=font)

        # Cập nhật vị trí Y cho dòng tiếp theo
        y_current += line_heights[idx] + line_spacing

    filename_out = f"slide_{slide_index}_final.jpg"
    img.save(filename_out, format='JPEG', quality=85)

    if temp_bg_path and os.path.exists(temp_bg_path):
        try:
            os.remove(temp_bg_path)
        except Exception:
            pass

    return filename_out
