from typing import NamedTuple
from dataclasses import dataclass

DEFAULT_SIZE = 768


@dataclass
class Post:
    text: str
    images: list[str]

    def __post_init__(self):
        self.text = self.text.lower()


class Resolution(NamedTuple):
    width: int = DEFAULT_SIZE
    height: int = DEFAULT_SIZE


class Prompt(NamedTuple):
    text: str
    style: str = ""
    resolution: Resolution = Resolution()

    def is_default(self):
        return not self.style and self.resolution == Resolution()


class UserConfig(NamedTuple):
    resolution: Resolution = Resolution()
    style: str = ""
