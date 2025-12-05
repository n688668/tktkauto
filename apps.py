from ai_utils import propose_random_theme, generate_story_and_prompts, propose_content_and_image_query, generate_fairy_tale, generate_joke
from drive_utils import create_drive_folder, upload_to_drive
from image_utils import create_image_with_text
from notifier import send_telegram_notification
from config import STORY_DRIVE_FOLDER_ID, PHONG_THUY_DRIVE_FOLDER_ID, TU_VI_DRIVE_FOLDER_ID, TAROT_DRIVE_FOLDER_ID, CUNG_HOANG_DAO_DRIVE_FOLDER_ID, FAIRY_TALE_DRIVE_FOLDER_ID, JOKE_DRIVE_FOLDER_ID
import os, re

# HÀM APP CÂU CHUYỆN
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

# HÀM APP PHONG THỦY
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

# HÀM APP TỬ VI
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

# HÀM APP TAROT
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

# HÀM APP CUNG HOÀNG ĐẠO
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

# HÀM APP TRUYỆN CỔ TÍCH
def run_fairy_tale_app(drive_service, topic=None):
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

# HÀM APP TRUYỆN CƯỜI
def run_joke_app(drive_service, topic=None):
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
