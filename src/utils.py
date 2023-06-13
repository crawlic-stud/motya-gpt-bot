import io

from aiogram import types


def create_media(images: list[bytes], caption: str = None) -> types.MediaGroup:
    media = types.MediaGroup()
    media.attach_photo(types.InputFile(
        io.BytesIO((images[0])), "image.png"), caption)
    for image in images[1:]:
        media.attach_photo(types.InputFile(io.BytesIO(image), "image.png"))
    return media
