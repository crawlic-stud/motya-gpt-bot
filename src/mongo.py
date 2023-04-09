import pymongo


class MongoDatabase:
    def __init__(self, url, db_name, collection_name):
        self.client = pymongo.MongoClient(url)[db_name][collection_name]

    def get_all(self) -> list:
        return [r for r in self.client.find()]

    def count(self) -> int:
        return self.client.count_documents({})


class ConfigDb(MongoDatabase):
    def get_themes(self) -> None | list[str]:
        result = self.client.find_one({"_id": "themes"}) or {}
        return result.get("themes")

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
