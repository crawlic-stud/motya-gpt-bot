import io
from pathlib import Path

from aiogram import types
from PIL import Image


def create_media(images: list[bytes], caption: str = None) -> types.MediaGroup:
    media = types.MediaGroup()
    media.attach_photo(types.InputFile(
        io.BytesIO((images[0])), "image.png"), caption)
    for image in images[1:]:
        media.attach_photo(types.InputFile(io.BytesIO(image), "image.png"))
    return media


def create_gif(path: Path, img_extension: str = ".png", duration: int = 100) -> bytes:
    gif_frames: list[Image.Image] = []
    for image in path.glob(f"*{img_extension}"):
        frame = Image.open(image)
        gif_frames.append(frame)
    buffer = io.BytesIO()
    gif_frames[0].save(buffer, format="GIF", save_all=True,
                       append_images=gif_frames[1:], duration=duration,
                       loop=0)
    return buffer.getvalue()


if __name__ == "__main__":
    buffer = create_gif(Path.cwd() / "images" / "361944343")
    values = buffer.getvalue()
    ...
