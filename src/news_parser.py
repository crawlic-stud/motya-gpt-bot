from typing import NamedTuple
import asyncio

import aiohttp
from bs4 import BeautifulSoup


class NewsParserError(Exception):
    ...


class NewsParser:
    BASE_URL = "https://positivnews.ru/"

    def __init__(self) -> None:
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }

    # NOTE: might be reasonable to get news from different pages
    async def get_latest_link(self, excluded_links: list[str]) -> str:
        async with aiohttp.ClientSession(headers=self.headers) as session:
            async with session.get(self.BASE_URL) as response:
                if response.status != 200:
                    raise NewsParserError(
                        f"Can not connect to {self.BASE_URL}")

                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                a_tags = soup.select(".post-title > a")
                hrefs = [a["href"] for a in a_tags]

                latest_link = hrefs.pop(0) if hrefs else None
                while latest_link in excluded_links and hrefs:
                    latest_link = hrefs.pop(0)

                return latest_link


if __name__ == "__main__":
    print(
        asyncio.run(NewsParser().get_latest_link([]))
    )
