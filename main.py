from dotenv import load_dotenv
import mysql.connector
from mysql.connector.errors import DatabaseError
from retry import retry

import logging
import os
from pathlib import Path
import random


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")
load_dotenv()


class MotyaModel:
    """Class to connect to my Mindsdb model"""
    def __init__(self) -> None:
        self.db = mysql.connector.connect(
            host="cloud.mindsdb.com",
            user=os.getenv("USER"),
            password=os.getenv("PASSWORD"),
            port="3306"
        )
        self.cursor = self.db.cursor(buffered=True)

    @retry(DatabaseError, tries=2, delay=10, logger=logger)
    @retry(IndexError, tries=5, logger=logger)
    def answer(self, text: str, model_name: str = "mindsdb.motya_model") -> str:
        self.cursor.execute(f'SELECT response from {model_name} WHERE text="{text}";')
        result = self.cursor.fetchone() or []
        return result[0]

    def get_inspiration(self, theme: str) -> str:
        inspirations = self.answer(theme, "mindsdb.motya_helper")
        return inspirations.split(",")

    def reset_model(self, prompt_path, model_name: str = "mindsdb.motya_model") -> None:
        prompt = Path(prompt_path).read_text(encoding="utf-8")
        
        try:
            self.cursor.execute(f"DROP TABLE {model_name}")
        except DatabaseError as e:
            logger.error("Deletion failed:", e)
        
        try:
            self.cursor.execute(f"""
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


if __name__ == "__main__":
    motya = MotyaModel()
    motya.reset_model("motya_prompt.txt", "mindsdb.motya_model")
    motya.reset_model("helper_prompt.txt", "mindsdb.motya_helper")
    inspiration = random.choice(motya.get_inspiration("программирование")).strip()
    print(inspiration)
    print(motya.answer(f"напиши короткий пост про: {inspiration}"))
