import requests
from config import ENABLE_TELEGRAM_NOTIFICATIONS, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

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
