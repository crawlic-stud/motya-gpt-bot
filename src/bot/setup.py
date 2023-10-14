import asyncio

import aioschedule
from aiogram import types, Dispatcher

from .jobs import send_news, send_post
from .config import bot_config_db, bot, ADMIN_ID
from model.g4f_model import GPT4FreeModel
from image_gen import ImageGenerator
from news_parser import NewsParser
from model_middleware import ModelMiddleware


async def posts_loop(model: GPT4FreeModel):
    for time in ["11:50", "14:05", "16:45", "19:05"]:
        aioschedule.every().day.at(time).do(send_post, model, None)
    aioschedule.every().day.at("8:10").do(send_news, model, None)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


async def on_startup(dp: Dispatcher):
    image_gen = ImageGenerator()
    news_parser = NewsParser()
    motya = await GPT4FreeModel.create(
        system_message=bot_config_db.get_main_prompt(),
        helper_message=bot_config_db.get_helper_prompt(),
        image_message="придумай какие картинки подойдут к посту. перечисли их через точку с запятой. без нумерации."
        " например вот так: поля; тополя; радуга",
        model="gpt-3.5-turbo",
        image_gen=image_gen,
        news_parser=news_parser,
    )
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
        types.BotCommandScopeChat(chat_id=ADMIN_ID),
    )
