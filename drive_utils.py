import os, time, random
from pydrive2.drive import GoogleDrive

# Hàm Tạo thư mục và tải lên Drive
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
