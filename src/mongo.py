import pymongo

from models import UserConfig, Resolution


class MongoDatabase:
    def __init__(self, url, db_name, collection_name):
        self.client = pymongo.MongoClient(url)[db_name][collection_name]

    def get_all(self) -> list:
        return [r for r in self.client.find()]

    def count(self) -> int:
        return self.client.count_documents({})


class BotConfigDb(MongoDatabase):
    def get_themes(self) -> None | list[str]:
        result = self.client.find_one({"_id": "themes"}) or {}
        return result.get("themes")

    def add_themes(self, themes: list[str]) -> None:
        self.client.update_one(
            {"_id": "themes"},
            {"$addToSet": {"themes": {"$each": themes}}}
        )

    def get_image_styles(self) -> None | list[str]:
        result = self.client.find_one({"_id": "styles"}) or {}
        return result.get("styles")

    def add_image_styles(self, styles: list[str]) -> None:
        self.client.update_one(
            {"_id": "styles"},
            {"$addToSet": {"styles": {"$each": styles}}}
        )

    def get_main_prompt(self) -> None | str:
        result = self.client.find_one({"_id": "main_prompt"}) or {}
        return result.get("prompt")

    def get_helper_prompt(self) -> None | str:
        result = self.client.find_one({"_id": "helper_prompt"}) or {}
        return result.get("prompt")

    def set_main_prompt(self, prompt: str) -> None:
        self.client.update_one({"_id": "main_prompt"}, {
                               "$set": {"prompt": prompt}}, upsert=True)

    def set_helper_prompt(self, prompt: str) -> None:
        self.client.update_one({"_id": "helper_prompt"}, {
                               "$set": {"prompt": prompt}}, upsert=True)


class UserConfigDb(MongoDatabase):
    def set_resolution(self, user_id: int, resolution: Resolution) -> None:
        self.client.update_one(
            {"user_id": user_id},
            {"$set": {
                "resolution": list(resolution),
            }},
            upsert=True
        )

    def set_style(self, user_id: int, style: str) -> None:
        self.client.update_one(
            {"user_id": user_id},
            {"$set": {
                "style": style,
            }},
            upsert=True
        )

    def get_user_config(self, user_id: int) -> UserConfig:
        default_config = UserConfig()
        conf = self.client.find_one({"user_id": user_id}) or {}
        return UserConfig(
            resolution=Resolution(*conf.get("resolution", [])),
            style=conf.get("style", default_config.style),
        )
