import argparse
import io
from pathlib import Path

from aiogram import types
from PIL import Image

from models import CappedList, Prompt, Resolution

from .config import (
    MAX_IMAGE_SIZE,
    THROTTLE_RATE_IMAGE,
    DEFAULT_PROMPT,
    CHAT_HISTORY_SIZE,
)
from image_gen import ImageGenerationError


def create_media(images: list[bytes], caption: str = None) -> types.MediaGroup:
    media = types.MediaGroup()
    media.attach_photo(types.InputFile(io.BytesIO((images[0])), "image.png"), caption)
    for image in images[1:]:
        media.attach_photo(types.InputFile(io.BytesIO(image), "image.png"))
    return media


def create_gif(path: Path, img_extension: str = ".png", duration: int = 100) -> bytes:
    gif_frames: list[Image.Image] = []
    for image in path.glob(f"*{img_extension}"):
        frame = Image.open(image)
        gif_frames.append(frame)
    buffer = io.BytesIO()
    gif_frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=gif_frames[1:],
        duration=duration,
        loop=0,
    )
    return buffer.getvalue()


def create_history_chunk(
    user_message: str, assistant_message: str
) -> list[dict[str, str]]:
    return [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message},
    ]


async def on_draw_spam(message, *args, **kwargs):
    await message.reply(
        f"ой 🙄 команду /draw можно нажимать не чаще чем раз в {THROTTLE_RATE_IMAGE} секунд 😝"
    )


async def on_message_spam(message, *args, **kwargs):
    await message.reply("ой 🙄 пожалуйста, не пишите мне так часто, я не успеваю 😣")


def validate_resolution(res: list[str]) -> Resolution:
    if len(res) == 2 and all(isinstance(item, int) for item in res):
        return Resolution(*res)
    elif len(res) != 2 or not all(item.isdigit() for item in res):
        raise ImageGenerationError(
            f"нужно ввести ширину и высоту изображения двумя числами 🫣"
        )

    w, h = [int(item) for item in res]
    if w > MAX_IMAGE_SIZE or h > MAX_IMAGE_SIZE:
        raise ImageGenerationError(
            f"разрешение картинки не может быть больше чем {MAX_IMAGE_SIZE}x{MAX_IMAGE_SIZE} пикселей 🙄"
        )

    return Resolution(w, h)


def parse_args(args: str) -> Prompt | None:
    args = args.split()
    parser = argparse.ArgumentParser()
    parser.add_argument("text", nargs="*")
    parser.add_argument(
        "-style",
        "-s",
        nargs="*",
        type=str,
        help="style of image",
        default=DEFAULT_PROMPT.style,
    )
    parser.add_argument(
        "-res",
        "-r",
        nargs="*",
        help="image resolution",
        default=DEFAULT_PROMPT.resolution,
    )
    args, _ = parser.parse_known_args(args)

    if not args.text:
        return

    res = validate_resolution(args.res)
    return Prompt(" ".join(args.text), " ".join(args.style), res)


async def save_history(data, messages: list[str]):
    new_entries = [*data.get("history", []), *messages]
    history = CappedList(new_entries, max_store=CHAT_HISTORY_SIZE)
    data["history"] = history
