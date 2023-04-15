from typing import NamedTuple


class Post(NamedTuple):
    text: str
    images: list[bytes]


class Prompt(NamedTuple):
    text: str
    style: str = ""
    width: int = 768
    height: int = 768
