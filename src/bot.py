import os
import asyncio

from aiogram import types, Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter
import aioschedule

from async_model import AsyncMotyaModel
from model_middleware import ModelMiddleware
from mongo import ConfigDb


TOKEN = os.getenv("TG_TOKEN")
bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
MONGO_URL = os.getenv("MONGO_URL")
config_db = ConfigDb(MONGO_URL, "motya_gpt", "config")


async def send_post(model: AsyncMotyaModel):
    group = "@motya_blog"
    themes = config_db.get_themes()
    await bot.send_message(group, await model.create_random_post(themes))


async def posts_loop(model: AsyncMotyaModel):
    for time in ["8:10", "11:50", "14:05", "16:45", "19:05"]:
        aioschedule.every().day.at(time).do(send_post, model)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp: Dispatcher):
    motya = await AsyncMotyaModel.create()
    dp.middleware.setup(ModelMiddleware(motya))
    asyncio.create_task(posts_loop(motya))


@dp.message_handler(commands=["start"])
async def send_start(message: types.Message, model: AsyncMotyaModel):
    await types.ChatActions.typing()
    answer = "привет! " \
        "я бот мотя на основе GPT-4, можешь смело задавать мне любые вопросы! " \
        "только помни, что я еще совсем маленький и только учусь 😇 " \
        '\n\nкстати! подпишись на мой <a href="https://t.me/motya_blog">блог</a>!'
    await message.reply(answer)


@dp.message_handler(ChatTypeFilter(types.ChatType.PRIVATE))
async def reply_to_message_privately(message: types.Message, model: AsyncMotyaModel):
    msg = await message.answer("секундочку 🐾 ...")
    answer = await model.answer(message.text)
    await message.reply(answer)
    await msg.delete()


@dp.message_handler(IsReplyFilter(True))
async def reply_to_message_in_chat(message: types.Message, model: AsyncMotyaModel):
    replied_id = message.reply_to_message.from_id
    if replied_id == bot.id or replied_id == -1001928224337:
        replied_text = message.reply_to_message.text
        await types.ChatActions.typing()
        answer = await model.answer(f"Ты писал про: {replied_text}. Ответь на: {message.text}")
        await message.reply(answer)
