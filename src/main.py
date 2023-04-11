import logging

from aiogram import executor
from dotenv import load_dotenv


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(level=logging.INFO)

    from bot import dp, on_startup

    executor.start_polling(
        dispatcher=dp,
        on_startup=on_startup,
        skip_updates=True
    )
