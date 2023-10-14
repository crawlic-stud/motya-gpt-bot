import io
from aiogram import types

from model.g4f_model import GPT4FreeModel
from models import Prompt, Resolution
from ..config import (
    dp,
    user_config_db,
    THROTTLE_RATE_MESSAGE,
    THROTTLE_RATE_IMAGE,
    DRAW_HELP,
    IMAGE_CAPTION,
    DEFAULT_PROMPT,
)
from ..utils import on_message_spam, validate_resolution, parse_args, on_draw_spam


@dp.message_handler(commands=["style"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def set_style(message: types.Message):
    style = message.get_args()
    user_config_db.set_style(message.from_id, style)
    await message.reply("поменял стандартный стиль 🥰")


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
async def send_image(message: types.Message, model: GPT4FreeModel):
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
