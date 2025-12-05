import requests, csv
from io import StringIO
from config import GSHEET_ID, TIMEOUT_SECONDS

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
