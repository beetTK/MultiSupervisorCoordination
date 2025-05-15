import os
import boto3
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_aws import ChatBedrockConverse


class BedrockModelManager:
    def __init__(self):
        # 環境変数からリージョンを取得
        self.regions = {
            "TOKYO": os.environ["regionName_TOKYO"],
            "US": os.environ["regionName_US"],
        }

        # Bedrockクライアントをリージョンごとに作成
        self.bedrock_clients = {
            region: boto3.client("bedrock-runtime", region_name=self.regions[region])
            for region in self.regions
        }

        # モデル設定
        self.model_configs = {
            "claude35_haiku": {
                "model_id": "us.anthropic.claude-3-5-haiku-20241022-v1:0",
                "temperature": 0,
                "max_tokens": 7000,
                "rate_limiter": InMemoryRateLimiter(
                    requests_per_second=1 / 3,
                    check_every_n_seconds=0.1,
                    max_bucket_size=20,
                ),
                "region": "US",
            },
            "claude35_sonnet_v2": {
                "model_id": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
                "temperature": 0,
                "max_tokens": 4000,
                "rate_limiter": InMemoryRateLimiter(
                    requests_per_second=1 / 60,
                    check_every_n_seconds=1,
                    max_bucket_size=1,
                ),
                "region": "TOKYO",
            },
            "nova_micro": {
                "model_id": "us.amazon.nova-micro-v1:0",
                "temperature": 0,
                "max_tokens": 5120,
                "rate_limiter": InMemoryRateLimiter(
                    requests_per_second=5, check_every_n_seconds=0.1, max_bucket_size=10
                ),
                "region": "US",
            },
        }

        # モデルインスタンスを作成
        self.llms = {
            name: self._create_llm(config)
            for name, config in self.model_configs.items()
        }

    def _create_llm(self, config):
        """指定された設定から LLM インスタンスを作成"""
        return ChatBedrockConverse(
            model_id=config["model_id"],
            temperature=config["temperature"],
            max_tokens=config["max_tokens"],
            rate_limiter=config["rate_limiter"],
            client=self.bedrock_clients[config["region"]],
        )

    def get_llm(self, model_name):
        """モデル名を指定して LLM インスタンスを取得"""
        return self.llms.get(model_name, None)

    def list_models(self):
        """登録されているモデル一覧を取得"""
        return list(self.llms.keys())


# クラスをインスタンス化
model_manager = BedrockModelManager()

# モデルの取得
llm_claude35_Haiku = model_manager.get_llm("claude35_haiku")
llm_claude35sonne_v2 = model_manager.get_llm("claude35_sonnet_v2")
llm_nova_micro = model_manager.get_llm("nova_micro")

# 使用可能なモデル一覧を取得
available_models = model_manager.list_models()
print(available_models)  # ["claude35_haiku", "claude35_sonnet_v2", "nova_micro"]
