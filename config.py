import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Admin ID larni xavfsiz o'qish
admin_env = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x) for x in admin_env.split(",") if x.strip().isdigit()]

MONGO_URL = os.getenv("MONGO_URL")
CARD_NUMBER = os.getenv("CARD_NUMBER", "Karta kiritilmagan")
