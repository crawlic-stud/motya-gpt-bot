import os
import asyncio
import io
import argparse
from pathlib import Path
import random
import logging
import shutil

from aiogram import types, Bot, Dispatcher
from aiogram.contrib.fsm_storage.mongo import MongoStorage
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter
from aiogram.dispatcher.storage import FSMContext
from aiohttp.client_exceptions import ClientConnectionError
from pymysql.err import ProgrammingError
import aioschedule

from model.async_model import AsyncMotyaModel
from model_middleware import ModelMiddleware
from mongo import BotConfigDb, UserConfigDb, NewsHistoryDb
from image_gen import ImageGenerator, ImageGenerationError
from news_parser import NewsParser
from models import Prompt, Resolution, CappedList
from utils import create_media, create_gif


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


async def send_post(model: AsyncMotyaModel, group: str | int = None):
    themes = bot_config_db.get_themes()
    styles = bot_config_db.get_image_styles()
    images = random.choice([1, 3])

    group = GROUP_NAME if not group else group

    post = await model.create_random_post_with_images(themes, images, styles)
    if not images:
        await bot.send_message(group, post.text)

    if len(post.text) < MAX_CAPTION_SIZE:
        media = create_media(post.images, post.text)
        await bot.send_media_group(group, media)
    else:
        media = create_media(post.images)
        await bot.send_media_group(group, media)
        await bot.send_message(group, post.text)


async def send_news(model: AsyncMotyaModel, group: str | int = None):
    excluded_urls = news_history_db.get_excluded_urls()
    post_text, url = await model.get_random_article_description(excluded_urls)
    post_text = f"{post_text}\n\n#новостиотмоти"

    group = GROUP_NAME if not group else group

    await bot.send_message(group, post_text)
    news_history_db.add_article_url(url)


async def posts_loop(model: AsyncMotyaModel):
    for time in ["11:50", "14:05", "16:45", "19:05"]:
        aioschedule.every().day.at(time).do(send_post, model, None)
    aioschedule.every().day.at("8:10").do(send_news, model, None)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp: Dispatcher):
    image_gen = ImageGenerator()
    news_parser = NewsParser()
    motya = await AsyncMotyaModel.create(image_gen, news_parser)
    dp.middleware.setup(ModelMiddleware(motya))
    asyncio.create_task(posts_loop(motya))
    basic_commands = [
        types.BotCommand("start", "Поприветствовать Мотю"),
        types.BotCommand("draw", "Нарисовать картинку по запросу"),
        types.BotCommand("ask", "Задать вопрос боту (для чатов)"),
        types.BotCommand("gif", "Нарисовать анимацию по запросу"),
        types.BotCommand("clear", "Очистить историю сообщений с ботом"),
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
    await message.reply(f"ой 🙄 команду /draw можно нажимать не чаще чем раз в {THROTTLE_RATE_IMAGE} секунд 😝")


async def on_message_spam(message, *args, **kwargs):
    await message.reply("ой 🙄 пожалуйста, не пишите мне так часто, я не успеваю 😣")


@dp.message_handler(commands=["start"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
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
        raise ImageGenerationError(
            f"нужно ввести ширину и высоту изображения двумя числами 🫣")

    w, h = [int(item) for item in res]
    if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
        raise ImageGenerationError(
            f"разрешение картинки не может быть больше чем {MAX_IMAGE_SIZE}x{MAX_IMAGE_SIZE} пикселей 🙄")

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
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def set_style(message: types.Message):
    style = message.get_args()
    user_config_db.set_style(message.from_id, style)
    await message.reply("поменял стандартный стиль 🥰")


@dp.message_handler(commands=["gif"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def get_gif(message: types.Message, model: AsyncMotyaModel):
    prompt = parse_args(message.get_args())
    if not prompt:
        await message.reply(DRAW_HELP.format(command="/gif"))
        return

    user_conf = user_config_db.get_user_config(message.from_id)
    if prompt.is_default():
        prompt = Prompt(prompt.text, user_conf.style, user_conf.resolution)

    if prompt.frames_count > GIF_MAX_FRAMES:
        await message.reply(f"нельзя больше {GIF_MAX_FRAMES} кадров!")
    prompt.resolution = prompt.resolution.get_scaled(MAX_GIF_SIZE)

    user_config_db.set_last_image(message.from_id, prompt.description)
    temp_msg = await message.answer("рисую картинки ✏️🐾 ... займет 5-7 минуток")

    save_path = IMG_PATH / str(message.from_id) / str(message.message_id)
    try:
        for i in range(prompt.frames_count):
            image_bytes = await model.image_gen.get_images([prompt])
            save_path.mkdir(exist_ok=True, parents=True)
            file_path = save_path / f"{message.from_id}_{str(i)}.png"
            file_path.write_bytes(image_bytes[0])

        gif_bytes = create_gif(save_path, img_extension=".png", duration=250)
        file_ = types.InputFile(io.BytesIO(gif_bytes), f"{prompt.text}.gif")
        await message.reply_animation(file_, caption=IMAGE_CAPTION,
                                      width=prompt.resolution.width,
                                      height=prompt.resolution.height)
    finally:
        shutil.rmtree(save_path)

    await temp_msg.delete()


@dp.message_handler(commands=["res"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
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
@dp.throttled(on_draw_spam, rate=THROTTLE_RATE_IMAGE)
async def send_image(message: types.Message, model: AsyncMotyaModel):
    prompt = parse_args(message.get_args())
    if not prompt:
        msg = await message.reply(DRAW_HELP.format(command="/draw"))
        return

    user_conf = user_config_db.get_user_config(message.from_id)
    if prompt.is_default():
        prompt = Prompt(prompt.text, user_conf.style, user_conf.resolution)

    user_config_db.set_last_image(message.from_id, prompt.description)
    msg = await message.answer("рисую ✏️🐾 ...")
    image_bytes = await model.image_gen.get_images([prompt])
    file_ = types.InputFile(io.BytesIO(image_bytes[0]), f"{prompt.text}.png")

    if prompt.resolution == DEFAULT_PROMPT.resolution:
        await message.reply_photo(file_, caption=IMAGE_CAPTION)
    else:
        await message.reply_document(file_, caption=IMAGE_CAPTION)

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
    # await send_post(model, message.from_id)
    await send_news(model, message.from_id)


async def save_history(data, messages: list[str]):
    history = CappedList(
        [*data.get("history", []), *messages], max_store=CHAT_HISTORY_SIZE)
    data["history"] = history


@dp.message_handler(commands=["clear"])
async def reset_history(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["history"] = []
    await message.reply("отчистил историю сообщений 🫡")


@dp.message_handler(ChatTypeFilter(types.ChatType.PRIVATE))
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def reply_to_message_privately(message: types.Message, model: AsyncMotyaModel, state: FSMContext):
    logger.info(f"Answering to {message.from_id} in chat {message.chat.id}")
    await types.ChatActions.typing()
    msg = await message.answer("секундочку 🐾 ...")
    async with state.proxy() as data:
        history = data.get("history", [])
        answer = await model.answer_with_history(message.text, history)
        await message.reply(answer)
        await save_history(data, [message.text, answer])
        await msg.delete()


async def reply_to_question_in_chat(message: types.Message, model: AsyncMotyaModel, state: FSMContext):
    logger.info(f"Answering to {message.from_id} in chat {message.chat.id}")
    await types.ChatActions.typing()
    async with state.proxy() as data:
        history = data.get("history", [])
        answer = await model.answer_with_history(message.text, history)
        await message.reply(answer)
        await save_history(data, [message.text, answer])


async def reply_to_one_message(message: types.Message, model: AsyncMotyaModel, state: FSMContext):
    logger.info(
        f"Answering to one message from {message.from_id} in chat {message.chat.id}")
    await types.ChatActions.typing()
    answer = await model.answer(f"ты писал про: {message.reply_to_message.text}, ответь на: {message.text}")
    await message.reply(answer)
    async with state.proxy() as data:
        await save_history(data, [message.text, answer])


async def reply_to_drawing(message: types.Message, model: AsyncMotyaModel, state: FSMContext):
    logger.info(
        f"Answering to drawing from {message.from_id} in chat {message.chat.id}")
    await types.ChatActions.typing()
    config = user_config_db.get_user_config(message.from_id)
    answer = await model.answer(f"ты нарисовал рисунок по запросу: '{config.last_image}', ответь на: {message.text}")
    await message.reply(answer)
    async with state.proxy() as data:
        await save_history(data, [message.text, answer])


@dp.message_handler(IsReplyFilter(True))
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def handle_reply_in_chat(message: types.Message, model: AsyncMotyaModel, state: FSMContext):
    reply_from_user = message.reply_to_message.from_user
    if reply_from_user.id != bot.id and reply_from_user.full_name != BLOG_ID:
        return
    elif reply_from_user.full_name == BLOG_ID:
        await reply_to_one_message(message, model, message.reply_to_message)
        return
    elif message.reply_to_message.caption is not None:
        await reply_to_drawing(message, model, message.reply_to_message)
        return
    await reply_to_question_in_chat(message, model, state)


@dp.message_handler(commands=["ask"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def handle_ask_command_in_chat(message: types.Message, model: AsyncMotyaModel, state: FSMContext):
    if message.get_command():
        message.text = message.get_args()
        if not message.text:
            await message.reply("на что вы хотите чтобы я ответил? 🤓")
            return
    await reply_to_question_in_chat(message, model, state)


async def basic_error(update: types.Update, error_msg: str):
    try:
        await update.message.reply(error_msg)
    except Exception as e:
        logger.error(e)
    finally:
        return True


@dp.errors_handler(exception=ImageGenerationError)
async def generation_error(update: types.Update, error):
    await basic_error(update, f"ошибка 🥶 {error}")


@dp.errors_handler(exception=ClientConnectionError)
async def connection_error(update: types.Update, error):
    await basic_error(update, f"не могу найти свой карандаш и краски 😭")


@dp.errors_handler(exception=ProgrammingError)
async def retry_limit_error(update: types.Update, error):
    # await basic_error(update, f"ошибка 😖 пожалуйста, очистите историю сообщений с помощью команды /clear 🥺")
    await basic_error(update, f"у меня пока что болит горло, не могу отвечать, лечусь 🥺\nно могу порисовать по команде /draw 🎨")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    bot_config_db.add_themes()
