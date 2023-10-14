from aiogram import types

from ..config import dp, THROTTLE_RATE_MESSAGE
from ..utils import on_message_spam
from model.g4f_model import GPT4FreeModel


@dp.message_handler(commands=["start"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def send_start(message: types.Message, model: GPT4FreeModel):
    await types.ChatActions.typing()
    answer = (
        "приветик, новый друг! 🐾 меня зовут мотя, я маленький тушканчик 🐹 и только начинаю узнавать этот большой мир 🌍"
        "можешь смело задавать мне любые вопросы! "
        '\n\nкстати! подпишись на мой <a href="https://t.me/motya_blog">блог</a>! 😇'
    )
    await message.reply(answer)
