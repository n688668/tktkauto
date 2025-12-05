import json
from config import client
from google.genai import types

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
    1. Câu chuyện phải là một truyện cổ tích ngẫu nhiên có tính giáo dục hoặc truyền cảm hứng.
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
    print("Bắt đầu: Yêu cầu Gemini tạo một câu chuyện cười ngắn...")

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
