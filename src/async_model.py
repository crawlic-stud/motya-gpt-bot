import aiomysql
from aiomysql.utils import _PoolContextManager
from pymysql.err import ProgrammingError
from retry import retry

import logging
import os
import random
import asyncio


logger = logging.getLogger("model")


async def test_example():
    pool = await aiomysql.create_pool(
        host="cloud.mindsdb.com",
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 42;")
            print(cur.description)
            (r,) = await cur.fetchone()
            assert r == 42
    pool.close()
    await pool.wait_closed()


class AsyncMotyaModel:
    """Class to connect to my Mindsdb model"""
    def __init__(self) -> None:
        self.pool: _PoolContextManager | None = None

    @classmethod
    async def create(cls):
        instance = cls()
        instance.pool = await aiomysql.create_pool(
            host="cloud.mindsdb.com",
            user=os.getenv("USER"),
            password=os.getenv("PASSWORD"),
        )
        return instance
    
    def __del__(self):
        self.pool.close()

    async def _execute(self, command: str) -> tuple[str]:
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(command)
                result = await cur.fetchone() or tuple()
                return result

    @retry(ProgrammingError, tries=2, delay=10, logger=logger)
    @retry(IndexError, tries=5, logger=logger)
    async def answer(self, text: str, model_name: str = "mindsdb.motya_model") -> str:
        result = await self._execute(f'SELECT response from {model_name} WHERE text="{text}";')
        return result[0]

    async def get_inspiration(self, theme: str) -> str:
        inspirations = await self.answer(theme, "mindsdb.motya_helper")
        return inspirations.split(",")

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
        theme = random.choice(themes)
        inspiration = random.choice(await self.get_inspiration(theme)).strip()
        logger.info(f"GENERATING POST: {inspiration}")
        return await self.answer(f"напиши короткий пост про: {inspiration}")


async def main():
    motya = await AsyncMotyaModel.create()
    print(await motya.create_random_post(["love"]))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    logging.basicConfig(level=logging.INFO)
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(test_example(loop))
    asyncio.run(main())
