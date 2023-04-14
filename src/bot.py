import os
import asyncio
import io

from aiogram import types, Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter
import aioschedule

from async_model import AsyncMotyaModel
from model_middleware import ModelMiddleware
from mongo import ConfigDb
from image_gen import ImageGenerator


THROTTLE_RATE = 5
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
    image_gen = ImageGenerator()
    motya = await AsyncMotyaModel.create(image_gen)
    dp.middleware.setup(ModelMiddleware(motya))
    asyncio.create_task(posts_loop(motya))
    await bot.set_my_commands([
        types.BotCommand("start", "Поприветствовать Мотю"),
        types.BotCommand("draw", "Нарисовать картинку по запросу")
    ])


async def on_draw_spam(message, *args, **kwargs):
    await message.reply(f"ой 🙄 команду /draw можно нажимать не чаще чем раз в {THROTTLE_RATE} секунд 😝")


@dp.message_handler(commands=["start"])
async def send_start(message: types.Message, model: AsyncMotyaModel):
    await types.ChatActions.typing()
    answer =  \
        "приветик, новый друг! 🐾 меня зовут мотя, я маленький тушканчик 🐹 и только начинаю узнавать этот большой мир 🌍" \
        "можешь смело задавать мне любые вопросы! " \
        '\n\nкстати! подпишись на мой <a href="https://t.me/motya_blog">блог</a>! 😇'
    await message.reply(answer)


@dp.message_handler(commands=["draw"])
@dp.throttled(on_draw_spam ,rate=THROTTLE_RATE)
async def send_image(message: types.Message, model: AsyncMotyaModel):
    prompt = message.get_args()
    if not prompt:
        msg = await message.answer("думаю 🐾 ...")
        answer = await model.answer(
            "напиши чтобы пользователь отправил вместе с командой /draw то, что он хочет нарисовать"
        )
        await message.reply(answer)
        await msg.delete()
        return
    msg = await message.answer("рисую ✏️🐾 ...")
    image_bytes = await model.image_gen.get_images([prompt])
    file_ = types.InputFile(io.BytesIO(image_bytes[0])) 
    await message.reply_photo(file_, caption="готово 🎨🐾")
    await msg.delete()


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
