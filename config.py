import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

FILE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(FILE_DIR, 'font.ttf')
CREDENTIALS_FILE = os.path.join(FILE_DIR, 'auto_creds.txt')
CLIENT_SECRETS_FILE = os.path.join(FILE_DIR, 'credentials.json')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")
ENABLE_TELEGRAM_NOTIFICATIONS = os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "False").lower() == "true"
GSHEET_ID = os.getenv("GSHEET_ID")

BACKGROUND_IMAGES_FOLDER_ID = os.getenv("BACKGROUND_IMAGES_FOLDER_ID")
STORY_DRIVE_FOLDER_ID = os.getenv("STORY_DRIVE_FOLDER_ID")
PHONG_THUY_DRIVE_FOLDER_ID = os.getenv("PHONG_THUY_DRIVE_FOLDER_ID")
TU_VI_DRIVE_FOLDER_ID = os.getenv("TU_VI_DRIVE_FOLDER_ID")
TAROT_DRIVE_FOLDER_ID = os.getenv("TAROT_DRIVE_FOLDER_ID")
CUNG_HOANG_DAO_DRIVE_FOLDER_ID = os.getenv("CUNG_HOANG_DAO_DRIVE_FOLDER_ID")
FAIRY_TALE_DRIVE_FOLDER_ID = os.getenv("FAIRY_TALE_DRIVE_FOLDER_ID")
JOKE_DRIVE_FOLDER_ID = os.getenv("JOKE_DRIVE_FOLDER_ID")

TIMEOUT_SECONDS = 3

# Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)
