import os

from dotenv import load_dotenv
import pytest

from async_model import AsyncMotyaModel
from mongo import BotConfigDb


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


if __name__ == "__main__":
    test_getting_themes()
    test_creates_random_post()
