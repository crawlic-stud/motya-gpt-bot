import asyncio

from aiogram.types import InputFile
from dotenv import load_dotenv

from bot import bot, bot_config_db
from model.async_model import AsyncMotyaModel, THEME_MODEL, PIC_MODEL 



async def recreate():
    motya = await AsyncMotyaModel.create()
    helper_p = bot_config_db.get_helper_prompt()
    await motya._execute(f"""
                CREATE MODEL {THEME_MODEL}
                PREDICT response
                USING
                engine = 'openai',
                max_tokens = 1000,
                model_name = 'gpt-4',
                prompt_template = 'From input message: {{{{text}}}}\
                {helper_p}';""".strip()
            )


if __name__ == "__main__":
    load_dotenv()
    # asyncio.run(recreate())
    
