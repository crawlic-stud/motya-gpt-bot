import os

from dotenv import load_dotenv

from model import MotyaModel
from mongo import ConfigDb


load_dotenv()
motya = MotyaModel()
config_db = ConfigDb(os.getenv("MONGO_URL"), "motya_gpt", "config")


def test_getting_themes():
    themes = config_db.get_themes()
    assert themes is not None, "No themes for a new post"


def test_creates_random_post():
    themes = config_db.get_themes()
    assert isinstance(motya.create_random_post(
        themes), str), "Must be a string!"


if __name__ == "__main__":
    test_getting_themes()
    test_creates_random_post()
