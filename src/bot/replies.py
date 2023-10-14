from aiogram import types
from aiogram.dispatcher.storage import FSMContext

from model.g4f_model import GPT4FreeModel
from .utils import save_history, create_history_chunk
from .config import logger, user_config_db


async def reply_to_question_in_chat(
    message: types.Message, model: GPT4FreeModel, state: FSMContext
):
    logger.info(f"Answering to {message.from_id} in chat {message.chat.id}")
    await types.ChatActions.typing()
    async with state.proxy() as data:
        history = data.get("history", [])
        answer = await model.answer_with_history(message.text, history)
        await message.reply(answer)
        await save_history(data, create_history_chunk(message.text, answer))


async def reply_to_one_message(
    message: types.Message, model: GPT4FreeModel, state: FSMContext
):
    logger.info(
        f"Answering to one message from {message.from_id} in chat {message.chat.id}"
    )
    await types.ChatActions.typing()
    answer = await model.answer(
        f"ты писал про: {message.reply_to_message.text}, ответь на: {message.text}"
    )
    await message.reply(answer)
    async with state.proxy() as data:
        await save_history(data, create_history_chunk(message.text, answer))


async def reply_to_drawing(
    message: types.Message, model: GPT4FreeModel, state: FSMContext
):
    logger.info(
        f"Answering to drawing from {message.from_id} in chat {message.chat.id}"
    )
    await types.ChatActions.typing()
    config = user_config_db.get_user_config(message.from_id)
    answer = await model.answer(
        f"ты нарисовал рисунок по запросу: '{config.last_image}', ответь на: {message.text}"
    )
    await message.reply(answer)
    async with state.proxy() as data:
        await save_history(data, create_history_chunk(message.text, answer))
