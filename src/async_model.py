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


logger = logging.getLogger("model")
MAX_FAILS = 10


def retry_policy(info: RetryInfo):
    exc = info.exception
    logger.warning(f"Retrying because of: {exc.__class__}. Total tries = {info.fails}")
    if isinstance(exc, ProgrammingError):
        return info.fails >= MAX_FAILS, 5000
    elif isinstance(exc, IndexError):
        return info.fails >= MAX_FAILS, 0
    return True, 0


@dataclass
class Post:
    text: str
    images: list[str]
    

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
    async def answer(self, text: str, model_name: str = "mindsdb.motya_model") -> str:
        result = await self._execute(f'SELECT response from {model_name} WHERE text="{text}";')
        return result[0]

    async def get_inspirations(self, theme: str) -> list[str]:
        inspirations = await self.answer(theme, "mindsdb.motya_helper")
        return inspirations.split(",")

    async def get_random_inspiration(self, themes: list[str]) -> str:
        theme = random.choice(themes)
        inspiration = random.choice(await self.get_inspirations(theme)).strip()
        return inspiration

    async def reset_model(self, prompt, model_name: str = "mindsdb.motya_model") -> None:
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

    async def create_random_post_with_images(self, themes: list[str], images_amount: int) -> Post:
        inspiration = await self.get_random_inspiration(themes)
        logger.info(f"GENERATING POST WITH IMAGES: {inspiration}")
        text = await self.answer(f"напиши короткий пост про: {inspiration}")
        if self.image_gen is None:
            return Post(text, [])

        inspiration_for_image = await self.answer(
            f"Какие картинки могут подойти к посту на тему: {inspiration}. "
            f"Напиши через запятую, без нумерации и лишнего текста. Делай максимально подробное описание картинок. " 
            f"Напиши на английском языке."
        )
        inspiration_for_image = random.choice(inspiration_for_image.split(",")).strip()
        logger.info(f"GENERATING IMAGE: {inspiration_for_image}")
        images = self.image_gen.get_images(inspiration_for_image, images_amount)
        
        return Post(text, images)


async def main():
    image_gen = ImageGenerator()
    motya = await AsyncMotyaModel.create(image_gen)
    # print(await motya.create_random_post_with_images(["детский труд"], 4))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
