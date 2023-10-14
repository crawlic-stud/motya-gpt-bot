from aiogram import types
from aiogram.dispatcher.filters import IDFilter

from ..config import dp, bot_config_db, ADMIN_ID
from model.g4f_model import GPT4FreeModel
from ..jobs import send_post, send_news


@dp.message_handler(IDFilter(ADMIN_ID), commands=["prompt"])
async def prompt(message: types.Message, model: GPT4FreeModel):
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
    bot_config_db.add_themes([theme.strip() for theme in new.split(",")])
    await message.reply("добавил темы 🤗")


@dp.message_handler(IDFilter(ADMIN_ID), commands=["test"])
async def test(message: types.Message, model: GPT4FreeModel):
    await message.answer("тестирую...")
    await send_post(model, message.from_id)
    await send_news(model, message.from_id)
