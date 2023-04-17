from typing import NamedTuple


DEFAULT_SIZE = 768


class Post(NamedTuple):
    text: str
    images: list[bytes]


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
