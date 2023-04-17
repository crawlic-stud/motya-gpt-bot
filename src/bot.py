import os
import asyncio
import io
import argparse
import random
import logging

from aiogram import types, Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter
from aiogram.utils.exceptions import BadRequest
import aioschedule

from async_model import AsyncMotyaModel
from model_middleware import ModelMiddleware
from mongo import BotConfigDb, UserConfigDb
from image_gen import ImageGenerator, ImageGenerationError
from models import Prompt, Resolution


THROTTLE_RATE = 5
MAX_IMAGE_SIZE = 2048
MAX_CAPTION_SIZE = 1024
GROUP_NAME = "@motya_blog"
DEFAULT_PROMPT = Prompt("")

TOKEN = os.getenv("TG_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = "motya_gpt"
bot_config_db = BotConfigDb(MONGO_URL, DB_NAME, "config")
user_config_db = UserConfigDb(MONGO_URL, DB_NAME, "user_config")
logger = logging.getLogger("bot")


def create_media(images: list[bytes], caption: str = None) -> types.MediaGroup:
    media = types.MediaGroup()
    media.attach_photo(types.InputFile(io.BytesIO((images[0])), "image.png"), caption)
    for image in images[1:]:
        media.attach_photo(types.InputFile(io.BytesIO(image), "image.png"))
    return media


async def send_post(model: AsyncMotyaModel, group: str | int = None):
    themes = bot_config_db.get_themes()
    images = random.choice([0, 1, 3])
    
    group = GROUP_NAME if not group else group

    post = await model.create_random_post_with_images(themes, images)
    if not images:
        await bot.send_message(group, post.text)
        return
        
    if len(post.text) < MAX_CAPTION_SIZE:
        media = create_media(post.images, post.text)
        await bot.send_media_group(group, media)
    else:
        media = create_media(post.images)
        await bot.send_media_group(group, media)
        await bot.send_message(group, post.text)


async def posts_loop(model: AsyncMotyaModel):
    for time in ["8:10", "11:50", "14:05", "16:45", "19:05"]:
        aioschedule.every().day.at(time).do(send_post, model, None)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp: Dispatcher):
    image_gen = ImageGenerator()
    motya = await AsyncMotyaModel.create(image_gen)
    dp.middleware.setup(ModelMiddleware(motya))
    asyncio.create_task(posts_loop(motya))
    basic_commands = [
        types.BotCommand("start", "Поприветствовать Мотю"),
        types.BotCommand("draw", "Нарисовать картинку по запросу"),
        types.BotCommand("style", "Поставить стандартный стиль картинок"),
        types.BotCommand("res", "Поставить стандартное разрешение картинок"),
    ] 
    await bot.set_my_commands(basic_commands)
    await bot.set_my_commands(
        [
            *basic_commands,
            types.BotCommand("prompt", "Поменять личность бота"),
            types.BotCommand("themes", "Добавить или посмотреть темы"),
            types.BotCommand("test", "Тестовая команда"),
        ],
        types.BotCommandScopeChat(chat_id=ADMIN_ID)
    )


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


def validate_resolution(res: list[str]) -> Resolution:
    if len(res) == 2 and all(isinstance(item, int) for item in res):
        return Resolution(*res)
    elif len(res) != 2 or not all(item.isdigit() for item in res):
        raise ImageGenerationError(f"нужно ввести ширину и высоту изображения двумя числами 🫣")

    w, h = [int(item) for item in res]
    if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
        raise ImageGenerationError(f"разрешение картинки не может быть больше чем {MAX_IMAGE_SIZE}x{MAX_IMAGE_SIZE} пикселей 🙄") 
    
    return Resolution(w, h)


def parse_args(args: str) -> Prompt | None:
    args = args.split()
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*")
    parser.add_argument(
        "-style", "-s", 
        nargs="*", 
        type=str, 
        help="style of image", 
        default=DEFAULT_PROMPT.style
    )
    parser.add_argument(
        "-res", "-r", 
        nargs="*", 
        help="image resolution", 
        default=DEFAULT_PROMPT.resolution
    )
    args, _ = parser.parse_known_args(args)

    if not args.text:
        return

    res = validate_resolution(args.res)
    return Prompt(" ".join(args.text), " ".join(args.style), res)


@dp.message_handler(commands=["style"])
async def set_style(message: types.Message):
    style = message.get_args()
    user_config_db.set_style(message.from_id, style)
    await message.reply("поменял стандартный стиль 🥰")


@dp.message_handler(commands=["res"])
async def set_style(message: types.Message):
    args = message.get_args()
    if not args:
        user_config_db.set_resolution(message.from_id, Resolution())
        await message.reply("поставил стандартное разрешение изображения ✅🥰")
        return
    res = validate_resolution(args.split())
    user_config_db.set_resolution(message.from_id, res)
    await message.reply("поменял стандартное разрешение изображения 🥰")


@dp.message_handler(commands=["draw"])
@dp.throttled(on_draw_spam ,rate=THROTTLE_RATE)
async def send_image(message: types.Message, model: AsyncMotyaModel):
    prompt = parse_args(message.get_args())
    if not prompt:
        msg = await message.answer("думаю 🐾 ...")
        answer = await model.answer(
            "напиши: чтобы нарисовать что-то, нужно отправить вместе с командой /draw то, что хочешь нарисовать"
        )
        await message.reply(answer)
        await msg.delete()
        return

    user_conf = user_config_db.get_user_config(message.from_id)
    if prompt.is_default():
        prompt = Prompt(prompt.text, user_conf.style, user_conf.resolution)

    msg = await message.answer("рисую ✏️🐾 ...")
    image_bytes = await model.image_gen.get_images([prompt])
    file_ = types.InputFile(io.BytesIO(image_bytes[0]), f"{prompt.text}.png")
    
    if prompt.resolution == DEFAULT_PROMPT.resolution:
        await message.reply_photo(file_, caption=f'готово 🎨🐾')
    else:
        await message.reply_document(file_, caption=f'готово 🎨🐾')
    
    await msg.delete()


@dp.message_handler(IDFilter(ADMIN_ID), commands=["prompt"])
async def prompt(message: types.Message, model: AsyncMotyaModel):
    current = bot_config_db.get_main_prompt()
    await message.reply(current)
    new = message.get_args()
    if not new:
        return
    bot_config_db.set_main_prompt(new)
    await model.reset_model(new)
    await message.reply("обновил 🤗")


@dp.message_handler(IDFilter(ADMIN_ID), commands=["themes"])
async def prompt(message: types.Message):
    current = "\n".join(bot_config_db.get_themes())
    new = message.get_args()
    await message.reply(current)
    if not new:
        return
    bot_config_db.add_themes(
        [theme.strip() for theme in new.split(",")])
    await message.reply("добавил темы 🤗")


@dp.message_handler(IDFilter(ADMIN_ID), commands=["test"])
async def test(message: types.Message, model: AsyncMotyaModel):
    await send_post(model, message.from_id)


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
async def generation_error(update: types.Update, error):
    try:
        await update.message.reply(f"ошибка 🥶 {error}")
    except Exception as e:
        pass
    finally:
        return True 


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    bot_config_db.add_themes()
