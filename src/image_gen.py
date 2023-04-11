import asyncio
import os

import replicate


class ImageGenerator:
    MODEL = "stability-ai/stable-diffusion:db21e45d3f7023abc2a46ee38a23973f6dce16bb082a930b0c49861f96d1e5bf"

    def __init__(self) -> None:
        self.client = replicate.Client(api_token=os.getenv("REPLICATE_KEY"))

    def get_images(self, prompts: str) -> list[str]:
        result = []
        for prompt in prompts:
            output = self.client.run(
                self.MODEL,
                input={"prompt": prompt}
            )
            result.append(output[0])
        return result


async def main():
    image_gen = ImageGenerator()
    print(image_gen.get_images(
        ["kids with toys", "fluffy friends", "love and happiness"]))


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(main())
