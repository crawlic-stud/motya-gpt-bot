from aiogram import types

from ..config import dp, logger
from image_gen import ImageGenerationError
from aiohttp.client_exceptions import ClientConnectionError


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
