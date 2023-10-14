import random

from .config import (
    bot_config_db,
    news_history_db,
    bot,
    GROUP_NAME,
    MAX_CAPTION_SIZE,
)
from .utils import create_media
from model.g4f_model import GPT4FreeModel


async def send_post(model: GPT4FreeModel, group: str | int = None):
    themes = bot_config_db.get_themes()
    styles = bot_config_db.get_image_styles()
    images = random.choice([1, 3])

    group = GROUP_NAME if not group else group

    post = await model.create_random_post_with_images(themes, images, styles)
    if not images:
        await bot.send_message(group, post.text)

    if len(post.text) < MAX_CAPTION_SIZE:
        media = create_media(post.images, post.text)
        await bot.send_media_group(group, media)
    else:
        media = create_media(post.images)
        await bot.send_media_group(group, media)
        await bot.send_message(group, post.text)


async def send_news(model: GPT4FreeModel, group: str | int = None):
    excluded_urls = news_history_db.get_excluded_urls()
    post_text, url = await model.get_random_article_description(excluded_urls)
    post_text = f"{post_text}\n\n#новостиотмоти"

    group = GROUP_NAME if not group else group

    await bot.send_message(group, post_text)
    news_history_db.add_article_url(url)
