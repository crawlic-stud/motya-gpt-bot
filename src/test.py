import os
import random
from string import ascii_letters

from dotenv import load_dotenv
import pytest

from model.async_model import AsyncMotyaModel
from mongo import BotConfigDb
from models import CappedList


load_dotenv()
config_db = BotConfigDb(os.getenv("MONGO_URL"), "motya_gpt", "config")


def test_getting_themes():
    themes = config_db.get_themes()
    assert themes is not None, "No themes for a new post"


@pytest.mark.asyncio
async def test_creates_random_post():
    motya = await AsyncMotyaModel.create()
    themes = config_db.get_themes()
    post = await motya.create_random_post(themes)
    assert isinstance(post, str), "Must be a string!"


def test_chat_queue():
    max_store = 10
    queue = CappedList(max_store)
    for _ in range(10000):
        msg = "".join(random.choices(ascii_letters, k=10))
        queue.add_message(msg)
        print(queue)
        assert len(
            queue) <= max_store, f"Queue size must not exceed {max_store} elements"


if __name__ == "__main__":
    # test_getting_themes()
    # asyncio.run(test_creates_random_post())
    test_chat_queue()
