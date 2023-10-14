import io
import shutil

from aiogram import types

from models import Prompt
from ..utils import on_message_spam, parse_args, create_gif
from ..config import (
    dp,
    user_config_db,
    THROTTLE_RATE_MESSAGE,
    DRAW_HELP,
    GIF_MAX_FRAMES,
    MAX_GIF_SIZE,
    IMG_PATH,
    IMAGE_CAPTION,
)
from model.g4f_model import GPT4FreeModel


@dp.message_handler(commands=["gif"])
@dp.throttled(on_message_spam, rate=THROTTLE_RATE_MESSAGE)
async def get_gif(message: types.Message, model: GPT4FreeModel):
    prompt = parse_args(message.get_args())
    if not prompt:
        await message.reply(DRAW_HELP.format(command="/gif"))
        return

    user_conf = user_config_db.get_user_config(message.from_id)
    if prompt.is_default():
        prompt = Prompt(prompt.text, user_conf.style, user_conf.resolution)

    if prompt.frames_count > GIF_MAX_FRAMES:
        await message.reply(f"нельзя больше {GIF_MAX_FRAMES} кадров!")
    prompt.resolution = prompt.resolution.get_scaled(MAX_GIF_SIZE)

    user_config_db.set_last_image(message.from_id, prompt.description)
    temp_msg = await message.answer("рисую картинки ✏️🐾 ... займет 5-7 минуток")

    save_path = IMG_PATH / str(message.from_id) / str(message.message_id)
    try:
        for i in range(prompt.frames_count):
            image_bytes = await model.image_gen.get_images([prompt])
            save_path.mkdir(exist_ok=True, parents=True)
            file_path = save_path / f"{message.from_id}_{str(i)}.png"
            file_path.write_bytes(image_bytes[0])

        gif_bytes = create_gif(save_path, img_extension=".png", duration=250)
        file_ = types.InputFile(io.BytesIO(gif_bytes), f"{prompt.text}.gif")
        await message.reply_animation(
            file_,
            caption=IMAGE_CAPTION,
            width=prompt.resolution.width,
            height=prompt.resolution.height,
        )
    finally:
        shutil.rmtree(save_path)

    await temp_msg.delete()
