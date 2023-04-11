import logging
import asyncio

from aiogram import executor
from dotenv import load_dotenv


async def main():
    from async_model import AsyncMotyaModel
    from model_middleware import ModelMiddleware
    from bot import dp, on_startup

    motya = AsyncMotyaModel.create()
    dp.middleware.setup(ModelMiddleware(motya))
    executor.start_polling(
        dispatcher=dp,
        on_startup=lambda dp: on_startup(motya, dp),
        skip_updates=True
    )


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
