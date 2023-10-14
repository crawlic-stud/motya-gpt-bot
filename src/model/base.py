from aioretry import retry, RetryInfo
from abc import ABC, abstractmethod


MAX_FAILS = 1
MAX_TOKENS = 8192
MAX_HISTORY_LENGTH = MAX_TOKENS // 2
MAIN_MODEL = "mindsdb.motya_model"
THEME_MODEL = "mindsdb.motya_helper"
PIC_MODEL = "mindsdb.pic_helper"
MODELS = [MAIN_MODEL, THEME_MODEL, PIC_MODEL]
CONN_ERR_MSG = (
    "не могу сейчас ответить, я в отпуске 😓 используй команду /draw, чтобы порисовать!"
)


class AsyncChatModel(ABC):
    @abstractmethod
    def answer(self, *args, **kwargs):
        ...

    @classmethod
    @abstractmethod
    async def create(self, *args, **kwargs):
        ...
