import logging
import random
import g4f
from aioretry import retry, RetryInfo

from .base import *
from image_gen import ImageGenerator
from news_parser import NewsParser
from models import Prompt, Post


logger = logging.getLogger("g4f_model")


def retry_policy(info: RetryInfo):
    exc = info.exception
    logger.warning(f"Retrying because of: {exc.__class__}. Total tries = {info.fails}")
    return info.fails >= MAX_FAILS, 1


class GPT4FreeModel(AsyncChatModel):
    def __init__(self) -> None:
        self.system_message: str | None = None
        self.helper_message: str | None = None
        self.model: str | None = None
        self.image_message: str | None = None
        self.image_gen: ImageGenerator | None = None
        self.news_parser: NewsParser | None = None

    @classmethod
    async def create(
        cls,
        system_message: str,
        helper_message: str,
        image_message: str,
        model: str = "gpt-3.5-turbo",
        image_gen: ImageGenerator | None = None,
        news_parser: NewsParser | None = None,
    ) -> "GPT4FreeModel":
        instance = cls()
        instance.system_message = system_message
        instance.helper_message = helper_message
        instance.image_message = image_message
        instance.model = model
        instance.image_gen = image_gen
        instance.news_parser = news_parser
        return instance

    def _create_messages(
        self,
        text: str,
        history: list[dict[str, str]] | None = None,
        system_message: str | None = None,
    ) -> list[dict[str, str]]:
        if history is None:
            history = []
        if system_message is None:
            system_message = self.system_message
        return [
            {"role": "system", "content": system_message},
            *history,
            {"role": "user", "content": text},
        ]

    async def _answer(self, messages: list[dict[str, str]]) -> str:
        message = await g4f.ChatCompletion.create_async(
            model=self.model, messages=messages
        )
        return message

    @retry(retry_policy=retry_policy)
    async def answer_with_history(
        self, text: str, history: list[dict[str, str]]
    ) -> str:
        messages = self._create_messages(text, history)
        return await self._answer(messages)

    @retry(retry_policy=retry_policy)
    async def answer(self, text: str) -> str:
        messages = self._create_messages(text)
        return await self._answer(messages)

    async def get_inspirations(self, theme: str) -> list[str]:
        messages = self._create_messages(theme, system_message=self.helper_message)
        answer = await self._answer(messages)
        return answer.split(",")

    async def get_image_inspirations(self, post_text: str) -> list[str]:
        messages = self._create_messages(post_text, system_message=self.helper_message)
        answer = await self._answer(messages)
        return answer.split(";")

    async def get_random_inspiration(self, themes: list[str]) -> str:
        theme = random.choice(themes)
        inspiration = random.choice(await self.get_inspirations(theme)).strip()
        return inspiration

    async def get_random_article_description(
        self, excluded_links: list[str]
    ) -> tuple[str, str]:
        logger.info(f"Getting article from {self.news_parser.BASE_URL}")
        link = await self.news_parser.get_latest_link(excluded_links)
        logger.info(f"Article URL: {link}")
        messages = self._create_messages(
            f"опиши новость в позитивной манере по ссылке: {link}. "
            f"в самом начале укажи заголовок статьи в формате: <b>заголовок</b>. "
            f"напиши что это ежедневная рубрика позитивная новость дня. "
            f"напиши 3 ключевых факта из статьи, которые тебя зацепили. "
            f"не надо писать ничего про себя, только про новость. "
            f"в конце добавь ссылку на новость в формате: <a href='ссылка'>тут</a>."
        )
        article_description = await self._answer(messages)
        return article_description, link

    async def reset_model(self, prompt: str) -> None:
        self.system_message = prompt

    async def create_random_post_with_images(
        self, themes: list[str], images_amount: int, image_styles: list[str]
    ) -> Post:
        inspiration = await self.get_random_inspiration(themes)
        logger.info(f"GENERATING POST WITH IMAGES: {inspiration}")
        text: str = await self.answer(f"напиши подробный пост про: {inspiration}")
        if self.image_gen is None or images_amount <= 0:
            logger.warning("Image weren't generated.")
            return Post(text, [])

        inspirations_for_image = await self.get_image_inspirations(text)
        random.shuffle(inspirations_for_image)
        inspirations_for_image = inspirations_for_image[:images_amount]
        style = random.choice([f"{item}, no text" for item in image_styles])
        prompts = [Prompt(insp, style) for insp in inspirations_for_image]

        logger.info(
            f"GENERATING IMAGES ({images_amount}): {', '.join(inspirations_for_image)}"
        )
        images = await self.image_gen.get_images(prompts)

        return Post(text, images)
