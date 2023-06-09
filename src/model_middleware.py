from aiogram.dispatcher.handler import ctx_data
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware

from async_model import AsyncMotyaModel


class ModelMiddleware(BaseMiddleware):
    def __init__(self, model: AsyncMotyaModel) -> None:
        super().__init__()
        self.model = model

    async def on_pre_process_message(self, message: types.Message, data: dict):
        data["model"] = self.model
