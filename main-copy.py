import os, time, random, select, sys

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from sheet_utils import load_app_modes_from_sheet
from apps import (
    run_story_app, run_phong_thuy, run_la_so_tu_vi,
    run_tarot, run_cung_hoang_dao, run_fairy_tale_app, run_joke_app
)
from config import (
    CLIENT_SECRETS_FILE, CREDENTIALS_FILE, TIMEOUT_SECONDS,
    FONT_PATH, GEMINI_API_KEY, GSHEET_ID
)
from notifier import send_telegram_notification

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
