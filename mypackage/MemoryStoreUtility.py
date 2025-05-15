import json
import uuid
from langgraph.store.memory import InMemoryStore


class MemoryStoreUtility:
    """
    InMemoryStore から複数の名前空間の成果物を取得し、連結した文字列として返すユーティリティクラス。
    """

    # 名前空間対応表(storeで使用)
    store_name_space_converter = {
        "coreteam": ["coreteam"],
        "retrievalteam": ["coreteam", "retrievalteam"],
        "webscraper": ["coreteam", "retrievalteam", "webscraper"],
        "writingteam": ["coreteam", "writingteam"],
        "storyplanner": ["coreteam", "writingteam", "storyplanner"],
        "dialoguewriter": ["coreteam", "writingteam", "dialoguewriter"],
    }

    # 名前空間対応表(toosで使用)
    toosNameSpaceConverter = {
        "retrievalteam": ["retrievalteam"],
        "writingteam": ["coreteam"],
        "storyplanner": ["webscraper"],
        "dialoguewriter": ["storyplanner", "webscraper"],
        "coreteam": [
            "coreteam",
        ],
        "deliverablesmanager": [
            "coreteam",
        ],
    }

    def __init__(self):
        """InMemoryStore の初期化"""
        self.in_memory_store = InMemoryStore()
        self.memory_id = str(uuid.uuid4())  # 一意のIDを生成

    def get_combined_deliverables(self, namespaces, tojson=True):
        """
        指定された複数の名前空間に対応するすべての成果物を取得し、連結した文字列として返す。

        :param namespaces: 取得対象の名前空間リスト
        :return: すべての成果物を連結したJSON文字列
        :tojson: json型式に変換するか指定できます。(true:json変換,false:変換無し配列)
        """
        deliverables = []

        # 指定されたnamespaceのタプル構造を保って検索
        for namespace in namespaces:
            if namespace in self.store_name_space_converter:
                search_tuple = self.store_name_space_converter[namespace]
                memories = self.in_memory_store.search(tuple(search_tuple))
                deliverables.extend([x.value for x in memories])

        if tojson:

            # 取得した成果物をJSON文字列に変換
            return json.dumps(deliverables, ensure_ascii=False)
        else:
            return deliverables

    def store_deliverable(self, namespace, result):
        """
        指定された名前空間に成果物を格納する。

        :param namespace: 格納対象の名前空間 (store_name_space_converter に対応するキー)
        :param result: 格納するデータ（辞書形式）
        """

        # InMemoryStore に格納
        self.in_memory_store.put(namespace, self.memory_id, result)

    def get_namespace_store(self, key):
        """
        指定したキーに対応する名前空間のリストを返す。

        :param key: store_name_space_converter に登録されているキー
        :return: 名前空間のリスト（見つからない場合は None）
        """
        return self.store_name_space_converter.get(key, None)

    def get_namespace_tools(self, key):
        """
        指定したキーに対応する名前空間のリストを返す。

        :param key: toosNameSpaceConverter に登録されているキー
        :return: 名前空間のリスト（見つからない場合は None）
        """
        return self.toosNameSpaceConverter.get(key, None)


# 使用例
if __name__ == "__main__":
    utility = MemoryStoreUtility()
    namespaces_to_search = ["retrievalTeam", "writingTeam"]
    result = utility.get_combined_deliverables(namespaces_to_search)
    print(result)
