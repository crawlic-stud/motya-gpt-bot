import aiomysql
from aiomysql.utils import _PoolContextManager
from pymysql.err import ProgrammingError
from aioretry import retry, RetryInfo

import logging
import os
import random
import asyncio
from dataclasses import dataclass

from image_gen import ImageGenerator
from news_parser import NewsParser
from models import Prompt, Post


logger = logging.getLogger("model")
MAX_FAILS = 20
MAX_TOKENS = 8192
MAX_HISTORY_LENGTH = MAX_TOKENS // 2
MAIN_MODEL = "mindsdb.motya_model"
THEME_MODEL = "mindsdb.motya_helper"
PIC_MODEL = "mindsdb.pic_helper"


def retry_policy(info: RetryInfo):
    exc = info.exception
    logger.warning(f"Retrying because of: {exc.__class__}. Total tries = {info.fails}")
    if isinstance(exc, ProgrammingError):
        return info.fails >= MAX_FAILS, 1
    elif isinstance(exc, IndexError):
        return info.fails >= MAX_FAILS, 0
    return True, 0


class AsyncMotyaModel:
    """Class to connect to my Mindsdb model"""
    def __init__(self) -> None:
        self.pool: _PoolContextManager | None = None
        self.image_gen: ImageGenerator | None = None
        self.news_parser: NewsParser | None = None

    @classmethod
    async def create(
        cls, 
        image_gen: ImageGenerator | None = None,
        news_parser: NewsParser | None = None 
    ):
        instance = cls()
        instance.pool = await aiomysql.create_pool(
            host="cloud.mindsdb.com",
            user=os.getenv("USER"),
            password=os.getenv("PASSWORD"),
        )
        instance.image_gen = image_gen
        instance.news_parser = news_parser
        return instance
    
    def __del__(self):
        self.pool.close()

    async def _execute(self, command: str) -> tuple[str]:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(command)
                result = await cur.fetchone() or tuple()
                return result

    @retry(retry_policy=retry_policy)
    async def answer(self, text: str, model_name: str = MAIN_MODEL) -> str:
        text = text.replace('"', '')
        command = f'SELECT response from {model_name} WHERE text="{text}";'
        result = await self._execute(command)
        return result[0]

    def prepare_dialog(self, history: list[str], step: int, max_steps: int):
        dialog = "\n".join(f"-{line}" for line in history)
        logger.info(f"History length: {max_steps - step + 1}")
        if len(dialog) < MAX_HISTORY_LENGTH:
            return dialog
        if step >= max_steps:
           return "" 
        return self.prepare_dialog(history[step:], step + 1, max_steps)

    async def answer_with_history(self, text: str, history: list[str], model_name: str = MAIN_MODEL) -> str:
        dialog = self.prepare_dialog(history, 1, len(history))
        if dialog:
            prompt = f"Ответь на сообщение, учитывая историю диалога. Сообщение: {text}. Диалог:\n{dialog}"
            result = await self.answer(prompt, model_name)
        else:
            result = await self.answer(text, model_name)
        return result

    async def get_inspirations(self, theme: str) -> list[str]:
        inspirations = await self.answer(theme, THEME_MODEL)
        return inspirations.split(",")

    async def get_image_inspirations(self, post_text: str) -> list[str]:
        inspirations = await self.answer(post_text, PIC_MODEL)
        return inspirations.split(";")

    async def get_random_inspiration(self, themes: list[str]) -> str:
        theme = random.choice(themes)
        inspiration = random.choice(await self.get_inspirations(theme)).strip()
        return inspiration

    async def reset_model(self, prompt, model_name: str = MAIN_MODEL) -> None:
        try:
            await self._execute(f"DROP TABLE {model_name}")
            logger.info(f"Dropped table: {model_name}")
        except ProgrammingError as e:
            logger.error("Deletion failed:", e)
        
        try:
            await self._execute(f"""
                CREATE MODEL {model_name}
                PREDICT response
                USING
                engine = 'openai',
                max_tokens = 1000,
                model_name = 'gpt-4',
                prompt_template = 'From input message: {{{{text}}}}\
                {prompt}';""".strip()
            )
            logger.info(f"Created table: {model_name}")
        except ProgrammingError as e:
            logger.error("Creation failed:", e)

    async def create_random_post(self, themes: list[str]) -> str:
        inspiration = await self.get_random_inspiration(themes)
        logger.info(f"GENERATING POST: {inspiration}")
        return await self.answer(f"напиши короткий пост про: {inspiration}")

    async def create_random_post_with_images(
        self, 
        themes: list[str], 
        images_amount: int, 
        image_styles: list[str]
    ) -> Post:
        inspiration = await self.get_random_inspiration(themes)
        logger.info(f"GENERATING POST WITH IMAGES: {inspiration}")
        text: str = await self.answer(f"напиши короткий пост про: {inspiration}")
        if self.image_gen is None or images_amount <= 0:
            logger.warning("Image weren't generated.")
            return Post(text, [])

        inspirations_for_image = await self.get_image_inspirations(text)
        random.shuffle(inspirations_for_image)
        inspirations_for_image = inspirations_for_image[:images_amount]
        style = random.choice([f"{item}, no text" for item in image_styles])
        prompts = [Prompt(insp, style) for insp in inspirations_for_image]

        logger.info(f"GENERATING IMAGES ({images_amount}): {', '.join(inspirations_for_image)}")
        images = await self.image_gen.get_images(prompts)
        
        return Post(text, images)


async def main():
    motya = await AsyncMotyaModel.create()
    # print(await motya.create_random_post(["игрушки"]))
    history = [
      "write a 700 words essay on the second topic",
      "write a 1000 words essay on the second topic",
      "write it in english",
      "write some topics related to the theme: \"changing fashions\". make it related to it industry or computer science university. write in english",
      "hi! 😊 here are some topics related to \"changing fashions\" in the it industry and computer science university:\n\n1. the evolution of programming languages: from punch cards to artificial intelligence 🤖\n2. the rise of wearable technology: smartwatches, fitness trackers, and vr headsets 🕶️\n3. the impact of social media on the fashion industry: influencers, online shopping, and virtual fashion shows 💻\n4. the role of big data and analytics in predicting fashion trends 📊\n5. sustainable fashion and technology: eco-friendly materials and 3d printing 🌿\n\nhope you find these topics interesting! have fun learning and exploring new things at school! 🏫 don't forget to share your discoveries with your friends and family! 👨‍👩‍👧‍👦💕"
    ]
    dialog = motya.prepare_dialog(history, 1, len(history))
    prompt = f"Ответь на сообщение, учитывая историю диалога. Сообщение: мотя привет. Диалог: {dialog}"
    answer = await motya.answer(prompt)
    print(answer)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
