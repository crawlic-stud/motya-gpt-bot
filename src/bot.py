import os
import asyncio
import io
import argparse

from aiogram import types, Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter
import aioschedule

from async_model import AsyncMotyaModel
from model_middleware import ModelMiddleware
from mongo import ConfigDb
from image_gen import ImageGenerator, ImageGenerationError
from models import Prompt


THROTTLE_RATE = 5
MAX_IMAGE_SIZE = 2048
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


def parse_args(args: str) -> Prompt | None:
    args = args.split()
    default_prompt = Prompt("")
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*")
    parser.add_argument(
        "-style", "-s", 
        nargs="*", 
        type=str, 
        help="style of image", 
        default=default_prompt.style
    )
    parser.add_argument(
        "-res", "-r", 
        nargs="*", 
        help="image resolution", 
        default=[default_prompt.width, default_prompt.height]
    )
    args, _ = parser.parse_known_args(args)

    if not args.text:
        return

    try:
        args.res = [int(item) for item in args.res]
    except ValueError:
        args.res = [default_prompt.width, default_prompt.height]

    if not len(args.res) == 2:
        raise ImageGenerationError(f"после -r нужно ввести ширину и высоту изображения 🫣")

    w, h = args.res
    if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
        raise ImageGenerationError(f"изображение не может быть больше чем {MAX_IMAGE_SIZE}x{MAX_IMAGE_SIZE} пикселей 🙄") 

    return Prompt(" ".join(args.text), " ".join(args.style), w, h)


@dp.message_handler(commands=["draw"])
@dp.throttled(on_draw_spam ,rate=THROTTLE_RATE)
async def send_image(message: types.Message, model: AsyncMotyaModel):
    prompt = parse_args(message.get_args())
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
    await message.reply_photo(file_, caption=f'готово 🎨🐾')
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


@dp.errors_handler(exception=ImageGenerationError)
async def flood_error(update: types.Update, error):
    try:
        await update.message.reply(f"ошибка 🥶 {error}")
    except Exception as e:
        pass
    finally:
        return True 


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    test_args = "милый тушканчик мотя -res test test"
    print(parse_args(test_args))
