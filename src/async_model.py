import aiomysql
from aiomysql.utils import _ConnectionContextManager
from mysql.connector.errors import DatabaseError
from retry import retry

import logging
import os
import random
import asyncio


logger = logging.getLogger("model")


async def test_example(loop):
    pool = await aiomysql.create_pool(
        host="cloud.mindsdb.com",
        user=os.getenv("USER"),
        password=os.getenv("PASSWORD"),
        port="3306",
        loop=loop
    )
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 42;")
            print(cur.description)
            (r,) = await cur.fetchone()
            assert r == 42
    pool.close()
    await pool.wait_closed()


class MotyaModel:
    """Class to connect to my Mindsdb model"""
    def __init__(self) -> None:
        self.connection: _ConnectionContextManager | None = None 
        self.cursor = None 

    @classmethod
    async def create(cls):
        conn = await aiomysql.connection.connect(
            host="cloud.mindsdb.com",
            user=os.getenv("USER"),
            password=os.getenv("PASSWORD"),
            port="3306"
        )
        instance = cls()
        instance.connection = conn
        instance.cursor = await conn.cursor
        return instance
    
    def __del__(self):
        self.connection.close()

    @retry(DatabaseError, tries=2, delay=10, logger=logger)
    @retry(IndexError, tries=5, logger=logger)
    async def answer(self, text: str, model_name: str = "mindsdb.motya_model") -> str:
        await self.cursor.execute(f'SELECT response from {model_name} WHERE text="{text}";')
        result = await self.cursor.fetchone() or []
        return result[0]

    async def get_inspiration(self, theme: str) -> str:
        inspirations = await self.answer(theme, "mindsdb.motya_helper")
        return inspirations.split(",")

    async def reset_model(self, prompt, model_name: str = "mindsdb.motya_model") -> None:
        try:
            await self.cursor.execute(f"DROP TABLE {model_name}")
        except DatabaseError as e:
            logger.error("Deletion failed:", e)
        
        try:
            await self.cursor.execute(f"""
                CREATE MODEL {model_name}
                PREDICT response
                USING
                engine = 'openai',
                max_tokens = 1000,
                model_name = 'gpt-4',
                prompt_template = 'From input message: {{{{text}}}}\
                {prompt}';""".strip()
            )
        except DatabaseError as e:
            logger.error("Creation failed:", e)

    async def create_random_post(self, themes: list[str]) -> str:
        theme = random.choice(themes)
        inspiration = random.choice(self.get_inspiration(theme)).strip()
        logger.info(f"GENERATING POST: {inspiration}")
        return await self.answer(f"напиши короткий пост про: {inspiration}")


async def main():
    motya = await MotyaModel.create()
    print(motya.create_random_post())



if __name__ == "__main__":
    asyncio.run(test_example(asyncio.get_event_loop()))