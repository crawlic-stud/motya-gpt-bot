import os
import logging
from pathlib import Path

from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram import types, Bot, Dispatcher

from mongo import BotConfigDb, UserConfigDb, NewsHistoryDb
from models import Prompt


THROTTLE_RATE_IMAGE = 5
CHAT_HISTORY_SIZE = 10
THROTTLE_RATE_MESSAGE = 1
MAX_IMAGE_SIZE = 1024
MAX_CAPTION_SIZE = 1024
GIF_MAX_FRAMES = 24
MAX_GIF_SIZE = 1024
BLOG_ID = "Telegram"
GROUP_NAME = "@motya_blog"
DEFAULT_PROMPT = Prompt("")
IMAGE_CAPTION = "готово 🎨🐾"

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = "motya_gpt"
IMG_PATH = Path.cwd() / "images"
DRAW_HELP = "чтобы нарисовать что-то, нужно отправить вместе с командой {command} то, что хочешь нарисовать 😉"

bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MongoStorage(uri=MONGO_URL, db_name=DB_NAME))
bot_config_db = BotConfigDb(MONGO_URL, DB_NAME, "config")
user_config_db = UserConfigDb(MONGO_URL, DB_NAME, "user_config")
news_history_db = NewsHistoryDb(MONGO_URL, DB_NAME, "news_history")
logger = logging.getLogger("bot")
