from typing import Optional, NamedTuple
from dataclasses import dataclass

import aioschedule
from aiogram import types

from ..model.async_model import AsyncMotyaModel, Prompt, Post
from ..utils import create_media


MAX_CAPTION_SIZE = 1024


class TaskError(Exception):
    ...


class TelegramPost(NamedTuple):
    group: str
    time: str
    media: types.MediaGroup | None = None
    text: str | None = None


class Task:
    def __init__(
        self,
        model: AsyncMotyaModel,
        what_to_do: str,
        post_time: str,
        pictures_info: Optional[list[Prompt]] = None,
    ) -> None:
        self.model = model
        self.what_to_do = what_to_do
        self.post_time = post_time
        self.pic_info = pictures_info or []

    async def _get_text(self) -> str:
        answer = await self.model.answer(self.what_to_do)
        return answer

    async def _get_images(self) -> list[bytes]:
        images = await self.model.image_gen.get_images(self.pic_info)
        return images

    async def create_telegram_post(self, group: str) -> TelegramPost:
        text = await self._get_text()
        images = await self._get_images()

        if not images and not text:
            raise TaskError("No text or images were provided.")

        if not images:
            return TelegramPost(group, self.post_time, text=text)

        if not text:
            media = create_media(images)
            return TelegramPost(group, self.post_time, media=media)

        if len(text) < MAX_CAPTION_SIZE:
            media = create_media(images, text)
            return TelegramPost(group, self.post_time, media=media)

        media = create_media(images)
        return TelegramPost(group, self.post_time, media, text)
