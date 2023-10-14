from aiogram import types
from aiogram.dispatcher.storage import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter

from ..config import dp, bot, logger, THROTTLE_RATE_MESSAGE, BLOG_ID
from ..utils import save_history, create_history_chunk, on_message_spam
from ..replies import reply_to_one_message, reply_to_question_in_chat, reply_to_drawing
from model.g4f_model import GPT4FreeModel


@dp.message_handler(commands=["clear"])
async def reset_history(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["history"] = []
    await message.reply("отчистил историю сообщений 🫡")


@dp.message_handler(ChatTypeFilter(types.ChatType.PRIVATE))
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def reply_to_message_privately(
    message: types.Message, model: GPT4FreeModel, state: FSMContext
):
    logger.info(f"Answering to {message.from_id} in chat {message.chat.id}")
    await types.ChatActions.typing()
    msg = await message.answer("секундочку 🐾 ...")
    async with state.proxy() as data:
        history = data.get("history", [])
        answer = await model.answer_with_history(message.text, history)
        await message.reply(answer)
        await save_history(data, create_history_chunk(message.text, answer))
        await msg.delete()


@dp.message_handler(IsReplyFilter(True))
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def handle_reply_in_chat(
    message: types.Message, model: GPT4FreeModel, state: FSMContext
):
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
async def handle_ask_command_in_chat(
    message: types.Message, model: GPT4FreeModel, state: FSMContext
):
    if message.get_command():
        message.text = message.get_args()
        if not message.text:
            await message.reply("на что вы хотите чтобы я ответил? 🤓")
            return
    await reply_to_question_in_chat(message, model, state)
