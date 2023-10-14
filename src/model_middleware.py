from aiogram.dispatcher.handler import ctx_data
from aiogram import types
from aiogram.dispatcher.middlewares import BaseMiddleware

from model.g4f_model import GPT4FreeModel


class ModelMiddleware(BaseMiddleware):
    def __init__(self, model: GPT4FreeModel) -> None:
        super().__init__()
        self.model = model

    async def on_pre_process_message(self, _: types.Message, data: dict):
        data["model"] = self.model
