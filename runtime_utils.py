import os
import sys
import time
import threading
import queue
import signal
import logging

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

logger = logging.getLogger(__name__)

def authenticate_drive(client_secrets_file, credentials_file):
    gauth = GoogleAuth()
    gauth.settings['client_config_file'] = client_secrets_file
    gauth.settings['save_credentials_file'] = credentials_file
    try:
        gauth.LoadCredentialsFile(credentials_file)
        if gauth.credentials is None or getattr(gauth.credentials, "access_token_expired", True):
            raise Exception("Token không hợp lệ hoặc đã hết hạn.")
        logger.info("Loaded existing Drive credentials.")
    except Exception as e:
        logger.warning(f"Need re-auth: {e}")
        if os.path.exists(credentials_file):
            try:
                os.remove(credentials_file)
                logger.info("Removed invalid credentials file.")
            except Exception:
                pass
        try:
            gauth.LocalWebserverAuth()
            if gauth.credentials:
                gauth.SaveCredentialsFile(credentials_file)
                logger.info("Saved new Drive credentials.")
            else:
                raise Exception("LocalWebserverAuth failed to produce credentials.")
        except Exception as ee:
            raise RuntimeError(f"Drive authentication failed: {ee}")
    return GoogleDrive(gauth)

def input_with_timeout(prompt, timeout, default='y'):
    q = queue.Queue()
    def _reader():
        try:
            s = sys.stdin.readline()
            q.put(s)
        except Exception:
            q.put(None)
    print(prompt, end='', flush=True)
    t = threading.Thread(target=_reader, daemon=True)
    t.start()
    try:
        s = q.get(timeout=timeout)
        if s is None:
            return default
        return s.strip().lower() or default
    except queue.Empty:
        print(f"\n⏰ Hết giờ! Tự động chọn '{default}'.")
        return default

def _signal_handler(sig, frame):
    print("\nĐã nhận tín hiệu dừng. Thoát...")
    sys.exit(0)

# Đăng ký handler khi module được import
signal.signal(signal.SIGINT, _signal_handler)
