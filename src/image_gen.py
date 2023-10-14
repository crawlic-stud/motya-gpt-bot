import base64
import asyncio
import json
import logging
import os
from typing import Any

import aiohttp

from models import Prompt, Resolution


logger = logging.getLogger("image_gen")
BEARER_TOKEN = os.getenv("FUSION_AI_TOKEN")


def create_headers():
    headers = {}
    headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
    )
    headers.update({"Referer": "https://fusionbrain.ai/diffusion"})
    headers.update({"Origin": "https://fusionbrain.ai"})
    headers.update({"Authorization": f"Bearer {BEARER_TOKEN}"})
    return headers


class ImageGenerationError(Exception):
    ...


class ImageGenerator:
    REQUEST_STATUS_DELAY_S = 10
    MAX_RETRIES = 50
    RUN_URL = "https://api.fusionbrain.ai/web/api/v1/text2image/run?model_id=1"
    STATUS_URL = "https://api.fusionbrain.ai/web/api/v1/text2image/status/{pocket_id}"

    def __init__(self) -> None:
        self.headers = create_headers()

    @staticmethod
    async def _process_response(
        response: aiohttp.ClientResponse, required_code: int = 200
    ):
        if not response.status == required_code:
            raise ImageGenerationError(f"Details: {await response.text()}")

    async def _get_pocket_id(
        self,
        session: aiohttp.ClientSession,
        prompt: Prompt,
    ) -> str:
        data = {
            "type": "GENERATE",
            "style": "DEFAULT",
            "width": prompt.resolution.width,
            "height": prompt.resolution.height,
            "generateParams": {"query": f"{prompt.text}, {prompt.style}"},
        }
        form_data = aiohttp.FormData()
        form_data.add_field(
            "params", json.dumps(data), content_type="application/json", filename="blob"
        )
        async with session.post(self.RUN_URL, data=form_data) as response:
            await self._process_response(response, 201)
            data = await response.json()
            pocket_id = data["uuid"]
            logger.info(f"Got {pocket_id=}")
            return pocket_id

    async def _check_images(
        self, session: aiohttp.ClientSession, pocket_id: str
    ) -> list[str] | None:
        url = self.STATUS_URL.format(pocket_id=pocket_id)
        async with session.get(
            url,
        ) as response:
            await self._process_response(response)
            data = await response.json()
            status_str = data["status"]
            logger.info(
                f"WAITING: status = {status_str}, delay = {self.REQUEST_STATUS_DELAY_S} s"
            )
            return data["images"]

    async def _get_image_bytes(self, base64_string: str) -> bytes:
        image_bytes = base64.b64decode(base64_string)
        logger.info("Got image bytes")
        return image_bytes

    async def _get_image(
        self,
        session: aiohttp.ClientSession,
        prompt: Prompt,
    ) -> bytes:
        pocket_id = await self._get_pocket_id(session, prompt)
        images = await self._check_images(session, pocket_id)
        retries = 0
        while not images and retries <= self.MAX_RETRIES:
            await asyncio.sleep(self.REQUEST_STATUS_DELAY_S)
            retries += 1
            images = await self._check_images(session, pocket_id)
        if not images or retries > self.MAX_RETRIES:
            raise ImageGenerationError("Server is not responding.")
        image_bytes = await self._get_image_bytes(images[0])
        return image_bytes

    async def get_images(self, prompts: list[Prompt]) -> list[bytes]:
        images = []
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for prompt in prompts:
                image_bytes = await self._get_image(session, prompt)
                images.append(image_bytes)
        return images


async def main():
    image_gen = ImageGenerator()
    logging.basicConfig(level=logging.INFO)
    async with aiohttp.ClientSession(headers=image_gen.headers) as session:
        prompt = "собачка"
        for i in range(1):
            image_bytes = await image_gen._get_image(
                session,
                Prompt(
                    prompt, "нарисовано цветными карандашами", Resolution(1024, 1024)
                ),
            )
            with open(f"test.png", "wb") as f:
                f.write(image_bytes)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    asyncio.run(main())
