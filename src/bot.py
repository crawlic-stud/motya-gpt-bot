import os
import asyncio

from aiogram import types, Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import ChatTypeFilter, IsReplyFilter, IDFilter
import aioschedule

from model import MotyaModel


TOKEN = os.getenv("TG_TOKEN")
bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())


async def send_post(model: MotyaModel):
    group = "@motya_blog"
    await bot.send_message(group, model.create_random_post())


async def posts_loop(model: MotyaModel):
    for time in ["8:10", "11:50", "14:05", "17:30"]:
        aioschedule.every().day.at(time).do(send_post, model)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(model: MotyaModel, dp: Dispatcher):
    # await bot.send_message("@motya_blog", 
    # model.answer("напиши пост в котором ты приветствуешь подписчиков и рассказываешь им о том, что будет в этом блоге"))
    asyncio.create_task(posts_loop(model))


@dp.message_handler(commands=["start"])
async def send_start(message: types.Message, model: MotyaModel):
    await types.ChatActions.typing()
    answer = model.answer("привет!")
    await message.reply(answer)


@dp.message_handler(ChatTypeFilter(types.ChatType.PRIVATE))
async def reply_to_message_privately(message: types.Message, model: MotyaModel):
    msg = await message.answer("секундочку 🐾 ...")
    answer = model.answer(message.text)
    await message.reply(answer)
    await msg.delete()


@dp.message_handler(IsReplyFilter(True))
async def reply_to_message_in_chat(message: types.Message, model: MotyaModel):
    replied_id = message.reply_to_message.from_id
    if replied_id == bot.id or replied_id == -1001928224337:
        replied_text = message.reply_to_message.text
        await types.ChatActions.typing()
        answer = model.answer(f"Ты писал про: {replied_text}. Ответь на: {message.text}")
        await message.reply(answer)
