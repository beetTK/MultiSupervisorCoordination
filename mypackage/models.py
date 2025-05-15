from langgraph.graph import MessagesState
from os import name
from typing import List, TypedDict, Annotated
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.pydantic_v1 import Field, BaseModel
from pydantic import create_model
from pydantic import BaseModel as pydanticBaseModel
from enum import Enum
from typing import List, Literal, Type
from pydantic import create_model, Field
from langchain_core.tools import tool
from mypackage.MemoryStoreUtility import MemoryStoreUtility
from langchain_core.language_models.chat_models import BaseChatModel
from collections import defaultdict
from mypackage.prompts import *


class AgentState(MessagesState):
    exeNum: Annotated[defaultdict, "executions Number"]


class Dialogue(pydanticBaseModel):
    """A dialogue entry containing a speaker and their spoken text."""

    speaker: str = Field(..., description="The name of the speaker")
    text: str = Field(..., description="The content of the dialogue")


class Chapter(pydanticBaseModel):
    """A structured representation of a chapter containing dialogues."""

    title: str = Field(..., description="The title of the chapter")
    dialogue: List[Dialogue] = Field(
        ..., description="A list of dialogues in the chapter"
    )


class Story(pydanticBaseModel):
    """A structured representation of a story composed of multiple chapters."""

    chapters: List[Chapter] = Field(..., description="A list of chapters in the story")


def update_router_types(new_options, docstring: str) -> Type[pydanticBaseModel]:
    """新しい Router モデルを動的に作成し、docstring を設定する"""
    model = create_model(
        "Router",
        next=(
            Literal[tuple(new_options)],
            Field(..., description="Specify the next process"),
        ),
        __base__=pydanticBaseModel,
    )

    # 動的に docstring を設定
    model.__doc__ = docstring
    return model


# 動的に deliverableSearch 関数を作成する関数
def makedeliverableSearch(
    namespace_options: list[str], utilityMemoryStore: MemoryStoreUtility
):
    """指定された namespace_options に基づいて deliverableSearch を動的に作成する"""

    # 動的に Pydantic モデルを作成
    NamespaceModel = create_model(
        "NamespaceRouter",
        namespace=(
            Literal[tuple(namespace_options)],  # `Literal` に候補を制限
            Field(..., description="Select a namespace from predefined options"),
        ),
        __base__=pydanticBaseModel,
    )

    # deliverableSearch 関数を動的に定義
    @tool(args_schema=NamespaceModel)  # 動的に作成したスキーマを適用
    def deliverableSearch(namespace: str) -> str:
        """This tool can reference accessible artifacts by receiving your namespace."""

        deliverable = utilityMemoryStore.get_combined_deliverables(
            utilityMemoryStore.get_namespace_tools(namespace)
        )

        return deliverable

    return deliverableSearch  # 作成した関数を返す


def route(new_options, docstring: str) -> Type[pydanticBaseModel]:
    """新しい Router モデルを動的に作成し、docstring を設定する"""
    model = create_model(
        "Router",
        next=(
            Literal[tuple(new_options)],
            Field(..., description="Specify the next process"),
        ),
        __base__=pydanticBaseModel,
    )

    # 動的に docstring を設定
    model.__doc__ = docstring
    return model
