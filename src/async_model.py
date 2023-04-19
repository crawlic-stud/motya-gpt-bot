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
from models import Prompt, Post


logger = logging.getLogger("model")
MAX_FAILS = 20
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

    @classmethod
    async def create(cls, image_gen: ImageGenerator | None = None):
        instance = cls()
        instance.pool = await aiomysql.create_pool(
            host="cloud.mindsdb.com",
            user=os.getenv("USER"),
            password=os.getenv("PASSWORD"),
        )
        instance.image_gen = image_gen
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
        # logger.info("Answering...")
        result = await self._execute(f"SELECT response from {model_name} WHERE text='{text}';")
        return result[0]

    async def answer_with_history(self, text: str, history: list[str], model_name: str = MAIN_MODEL) -> str:
        # logger.info("Answering with history...")
        dialog = "\n".join([
            f" - {line}" for line in history
        ])
        prompt = f"Ответь на сообщение, учитывая историю диалога. Сообщение: {text}. Диалог: \n{dialog}"
        result = await self.answer(prompt)
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

        # inspirations_for_image = await self.answer(
        #     f"Какие картинки больше всего подойдут к посту: {text}. "
        #     f"Напиши максимально кратко, напиши через точку с запятой, не используй эмодзи."
        # )
        inspirations_for_image = await self.get_image_inspirations(text)
        # inspirations_for_image = inspirations_for_image.split(";")
        random.shuffle(inspirations_for_image)
        inspirations_for_image = inspirations_for_image[:images_amount]
        style = random.choice([f"{item}, no text" for item in image_styles])
        prompts = [Prompt(insp, style) for insp in inspirations_for_image]

        logger.info(f"GENERATING IMAGES ({images_amount}): {', '.join(inspirations_for_image)}")
        images = await self.image_gen.get_images(prompts)
        
        return Post(text, images)


async def main():
    motya = await AsyncMotyaModel.create()
    print(await motya.create_random_post(["игрушки"]))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
