import logging

from aiogram import executor
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    from model import MotyaModel
    from model_middleware import ModelMiddleware
    from bot import dp, on_startup

    motya = MotyaModel()
    dp.middleware.setup(ModelMiddleware(motya))
    executor.start_polling(
        dispatcher=dp,
        on_startup=lambda dp: on_startup(motya, dp),
        skip_updates=True
    )
