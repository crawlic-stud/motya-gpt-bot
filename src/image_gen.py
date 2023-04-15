import base64
import asyncio
import logging
import os

import aiohttp

from models import Prompt


logger = logging.getLogger("image_gen")
PROXY_IP_PORT = os.getenv("PROXY_IP_PORT")
PROXY_USER = os.getenv("PROXY_USER")
PROXY_PASSWORD = os.getenv("PROXY_PASSWORD")
# PROXY = f"https://{PROXY_USER}:{PROXY_PASSWORD}@{PROXY_IP_PORT}"
PROXY = None


def create_headers():
    headers = {}
    headers.update(
        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"})
    headers.update({"Referer": "https://fusionbrain.ai/diffusion"})
    headers.update({"Origin": "https://fusionbrain.ai"})
    return headers


class ImageGenerationError(Exception):
    ...


class ImageGenerator:
    REQUEST_STATUS_DELAY_S = 2
    MAX_RETRIES = 50
    RUN_URL = "https://fusionbrain.ai/api/v1/text2image/run"
    STATUS_URL = "https://fusionbrain.ai/api/v1/text2image/inpainting/pockets/{pocket_id}/status"
    ENTITIES_URL = "https://fusionbrain.ai/api/v1/text2image/inpainting/pockets/{pocket_id}/entities"

    def __init__(self) -> None:
        self.headers = create_headers()

    @staticmethod
    async def _process_response(response: aiohttp.ClientResponse, required_code: int = 200):
        if not response.status == required_code:
            raise ImageGenerationError(f"Details: {await response.text()}")

    async def _get_pocket_id(
        self,
        session: aiohttp.ClientSession,
        prompt: Prompt,
    ) -> str:
        async with session.post(
            self.RUN_URL,
            json={
                "queueType": "generate",
                "query": prompt.text,
                "preset": 1,
                "style": prompt.style,
                "width": prompt.width,
                "height": prompt.height,
            },
            # proxy=PROXY
        ) as response:
            await self._process_response(response, 201)
            data = await response.json()
            pocket_id = data["result"]["pocketId"]
            logger.info(f"Got {pocket_id=}")
            return pocket_id

    async def _check_status(self, session: aiohttp.ClientSession, pocket_id: str) -> bool:
        url = self.STATUS_URL.format(pocket_id=pocket_id)
        async with session.get(
            url,
            # proxy=PROXY
        ) as response:
            await self._process_response(response)
            data = await response.json()
            status_str = data["result"]
            logger.info(
                f"WAITING: status = {status_str}, delay = {self.REQUEST_STATUS_DELAY_S} s")
            return status_str == "SUCCESS"

    async def _get_image_bytes(self, session: aiohttp.ClientSession, pocket_id: str) -> bytes:
        url = self.ENTITIES_URL.format(pocket_id=pocket_id)
        async with session.get(
            url,
            # proxy=PROXY
        ) as response:
            await self._process_response(response)
            data = await response.json()
            image_bytes = data["result"][0]["response"][0]
            image_bytes = base64.b64decode(image_bytes)
            logger.info("Got image bytes")
            return image_bytes

    async def _get_image(
        self,
        session: aiohttp.ClientSession,
        prompt: Prompt,
    ) -> bytes:
        pocket_id = await self._get_pocket_id(session, prompt)
        status = await self._check_status(session, pocket_id)
        retries = 0
        while not status and retries <= self.MAX_RETRIES:
            await asyncio.sleep(self.REQUEST_STATUS_DELAY_S)
            retries += 1
            status = await self._check_status(session, pocket_id)
        if not status or retries > self.MAX_RETRIES:
            raise ImageGenerationError("Server is not responding.")
        image_bytes = await self._get_image_bytes(session, pocket_id)
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
        prompt = "милая девушка татарка с узкими зелеными глазами и широким лицом, маленьким носиком, глазами с макияжем, оранжевые светлые волосы, с букетом азалии в руках"
        image_bytes = await image_gen._get_image(
            session, Prompt(
                prompt, 
                # "20 years old, realistic, true light, beautiful, beautiful face, dream-like, sigma 85mm f/1.4, 15mm, 35mm, 4k, high resolution, 4k, 8k, hd, full color", 
                "A portrait of a 20 years old woman with green eyes in a white, flowy dress, standing in a field of wildflowers with the sun setting behind her",
                768, 1024
            )
        )
        with open(f"pics/{prompt}.png", "wb") as f:
            f.write(image_bytes)


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
