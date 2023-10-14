from typing import NamedTuple
from dataclasses import dataclass

DEFAULT_SIZE = 1024


@dataclass
class Post:
    text: str
    images: list[str]

    def __post_init__(self):
        self.text = self.text.lower()


class Resolution(NamedTuple):
    width: int = DEFAULT_SIZE
    height: int = DEFAULT_SIZE

    @property
    def ratio(self):
        return self.width / self.height

    def __max__(self):
        return self.width if self.width > self.height else self.height

    def get_scaled(self, size: int) -> "Resolution":
        if self.width == max(self):
            return Resolution(width=size, height=int(self.height * size / self.width))
        elif self.height == max(self):
            return Resolution(height=size, width=int(self.width * size / self.height))
        return self


@dataclass
class Prompt:
    text: str
    style: str = ""
    resolution: Resolution = Resolution()
    frames_count: int = 12

    def is_default(self):
        return not self.style and self.resolution == Resolution()

    @property
    def description(self):
        return f"{self.text} {self.style}"


class UserConfig(NamedTuple):
    resolution: Resolution = Resolution()
    style: str = ""
    last_image: str = ""


class CappedList(list):
    def __init__(self, messages: list[str] = None, max_store: int = 5):
        super().__init__()
        self.max_store = max_store

        messages = messages if messages is not None else []
        for msg in messages:
            self.add_message(msg)

    def add_message(self, message: str):
        if len(self) >= self.max_store:
            self.pop(0)
        self.append(message)
