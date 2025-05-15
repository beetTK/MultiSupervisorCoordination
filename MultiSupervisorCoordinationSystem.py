from collections import defaultdict
from itertools import islice
import json
import os
import requests
from typing import (
    Annotated,
    Dict,
    List,
    Literal,
    Tuple,
    TypedDict,
    Union,
)

from duckduckgo_search import DDGS
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, Send

from mypackage.BedrockModelManager import BedrockModelManager
from mypackage.MemoryStoreUtility import MemoryStoreUtility
import mypackage.models as withStructuredOutputModels
from mypackage.prompts import *
from mypackage.WebScraperUtility import WebScraperUtility

deliverablesManager = "deliverablesManager"

CustomSearchAPIAPIKEY = os.environ["CustomSearchAPIAPIKEY"]
SEARCH_ENGINE_ID = os.environ["SEARCH_ENGINE_ID"]


# llmクラスをインスタンス化
model_manager = BedrockModelManager()

# 各モデルの取得
llm_claude35_Haiku = model_manager.get_llm("claude35_haiku")
llm_claude35sonne_v2 = model_manager.get_llm("claude35_sonnet_v2")
llm_nova_micro = model_manager.get_llm("nova_micro")

# 使用可能なモデル一覧を取得
available_models = model_manager.list_models()
print(available_models)


def main():
    # メモリストア
    utilityMemoryStore = MemoryStoreUtility()

    # -------------------------------------------------------------------------------------------------
    # ----------------------------------retrievalTeam_graph_create_START--------------------------------------
    # -------------------------------------------------------------------------------------------------

    # 検索エージェント
    webScrapter_agent = create_react_agent(
        llm_nova_micro,
        tools=[tool_Search, tool_scrape_webpages],
        state_modifier=SystemPromptReactAgent.format(suffix=WebScrapterInstruction),
    )

    webScrapter_agent.step_timeout = 60

    # 検索ノード(webScrapter)
    def webScrapter_node(
        state: withStructuredOutputModels.AgentState,
    ) -> withStructuredOutputModels.AgentState:

        result = webScrapter_agent.invoke({"messages": state["messages"][-1].content})

        # storeに成果物を格納
        namespace_for_memory = tuple(
            utilityMemoryStore.get_namespace_store("webscraper")
            + [str(state["exeNum"].get("webScrapter", 0))]
        )
        memory = {"webScrapterDeliverable": result["messages"][-1].content}
        utilityMemoryStore.store_deliverable(namespace_for_memory, memory)

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=result["messages"][-1].content,
                        name="webScrapter",
                    )
                ]
            },
            goto="supervisor",
        )

    webScrapter_workers = [
        {
            "name": "webScrapter",
            "role": "The URL content is summarized, and keyword search is performed to return the results.",  # URL内容の要約、キーワード検索を行い結果を返却します。
        }
    ]

    retrievalTeam_supervisor_node = make_supervisor_node(
        llm=llm_claude35_Haiku,
        workers=webScrapter_workers,
        actions=default_action,
        finalAnswer="FINISH",
        visorName="retrievalteam",
        MemoryStore=utilityMemoryStore,
    )

    # グラフの構築
    retrievalTeam_workflow = StateGraph(withStructuredOutputModels.AgentState)

    retrievalTeam_workflow.add_node("webScrapter", webScrapter_node)
    retrievalTeam_workflow.add_node("supervisor", retrievalTeam_supervisor_node)
    retrievalTeam_workflow.add_edge(START, "supervisor")

    memory = MemorySaver()
    retrievalTeam_graph = retrievalTeam_workflow.compile(
        checkpointer=memory, debug=True
    )

    # -------------------------------------------------------------------------------------------------
    # ----------------------------------retrievalTeam_graph_create_END----------------------------------------
    # -------------------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------------------
    # ----------------------------------writingTeam_graph_create_START----------------------------------------
    # -------------------------------------------------------------------------------------------------

    namespace_options = ["storyplanner"]

    # メモリストア検索ツールを生成
    custom_tool_Planner = withStructuredOutputModels.makedeliverableSearch(
        namespace_options=namespace_options,
        utilityMemoryStore=utilityMemoryStore,
    )

    # 物語設計者エージェント
    storyPlanner_agent = create_react_agent(
        llm_claude35_Haiku,
        tools=[custom_tool_Planner],
        state_modifier=SystemPromptReactAgent.format(suffix=StoryPlannerInstruction),
    )

    storyPlanner_agent.step_timeout = 60

    # 物語設計者ノード
    def storyPlanner_node(
        state: withStructuredOutputModels.AgentState,
    ) -> withStructuredOutputModels.AgentState:

        # storeを検索して成果物を取得
        jsDeliverable = utilityMemoryStore.get_combined_deliverables(
            utilityMemoryStore.get_namespace_tools("storyplanner")
        )

        result = llm_claude35_Haiku.invoke(
            (
                [SystemMessage(content=StoryPlannerInstruction)]
                + state["messages"]
                + [
                    HumanMessage(
                        content=HumanPromptMemoryStore.format(
                            jsDeliverable=jsDeliverable
                        ),
                        name=deliverablesManager,
                    )
                ]
            )
        )

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=result.content,
                        name="storyplanner",
                    )
                ]
            },
            goto="dialogueWriter",
        )

    # 台詞ライターノード
    def dialogueWriter_node(
        state: withStructuredOutputModels.AgentState,
    ) -> withStructuredOutputModels.AgentState:

        # storeを検索して成果物を取得
        jsDeliverable = utilityMemoryStore.get_combined_deliverables(
            utilityMemoryStore.get_namespace_tools("dialoguewriter")
        )

        result = llm_claude35_Haiku.invoke(
            (
                [SystemMessage(content=DialogueWriterInstruction)]
                + state["messages"]
                + [
                    HumanMessage(
                        content=HumanPromptMemoryStore.format(
                            jsDeliverable=jsDeliverable
                        ),
                        name=deliverablesManager,
                    )
                ]
            )
        )

        # storeに成果物を格納
        namespace_for_memory = tuple(
            utilityMemoryStore.get_namespace_store("dialoguewriter")
            + [str(state["exeNum"].get("dialoguewrite", 0))]
        )
        memory = {"dialogueWriterDeliverable": result.content}
        utilityMemoryStore.store_deliverable(namespace_for_memory, memory)

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=result.content,
                        name="dialogueWriter",
                    )
                ]
            },
            goto="supervisor",
        )

    writingTeam_workers = [
        {
            "name": "storyPlanner",
            "role": """The Story Planner creates the story and structures it into chapters. 
            Next, based on the chapter information prepared by the Story Planner, the Dialogue Writer creates conversations between characters.""",
        }
    ]

    writingTeam_supervisor_node = make_supervisor_node(
        llm=llm_claude35_Haiku,
        workers=writingTeam_workers,
        actions=default_action,
        finalAnswer="FINISH",
        visorName="writingteam",
        MemoryStore=utilityMemoryStore,
    )

    # ライティングチームのグラフの構築
    writingTeam_workflow = StateGraph(withStructuredOutputModels.AgentState)
    writingTeam_workflow.add_node("supervisor", writingTeam_supervisor_node)
    writingTeam_workflow.add_node("dialogueWriter", dialogueWriter_node)
    writingTeam_workflow.add_node("storyPlanner", storyPlanner_node)
    writingTeam_workflow.add_edge(START, "supervisor")

    memory = MemorySaver()
    writingTeam_graph = writingTeam_workflow.compile(checkpointer=memory)
    # -------------------------------------------------------------------------------------------------
    # ----------------------------------writingTeam_graph_create_END-----------------------------------
    # -------------------------------------------------------------------------------------------------

    # -------------------------------------------------------------------------------------------------
    # ----------------------------------coreTeam_graph_create_START------------------------------------
    # -------------------------------------------------------------------------------------------------

    # SVに各チームの特色を設定
    coreTeam_workers = [
        {
            "name": "retrievalTeam",
            # URLの要約やキーワード検索を通じて、必要な情報を迅速かつ的確に取得するチームです。
            "role": """We are a team that quickly and accurately retrieves the necessary information through URL summaries and keyword searches.""",
        },
        {
            "name": "writingTeam",
            # Story PlannerとDialogue Writerが協力し、魅力的な物語構成と自然な対話を創り出すチームです。
            "role": """The Story Planner and Dialogue Writer collaborate to create compelling story structures and natural conversations as a team.""",
        },
    ]

    mainSVname = "coreteam"

    coreTeam_supervisor_node = make_supervisor_node(
        llm=llm_claude35_Haiku,
        workers=coreTeam_workers,
        actions=[
            {
                "actionName": "GIVEUP",
                # 「作業を続けることは不可能であると判断しました。」
                "actioDetail": "I have determined that it is impossible to continue the work.",
            },
        ],
        finalAnswer="COMPLETE",
        visorName=mainSVname,
        MemoryStore=utilityMemoryStore,
    )

    def call_retrievalTeam(
        state: withStructuredOutputModels.AgentState,
    ) -> withStructuredOutputModels.AgentState:

        response = retrievalTeam_graph.invoke(
            {
                "messages": state["messages"][-1],
                "exeNum": state["exeNum"],
            },
            config={"configurable": {"thread_id": "retrievalTeam_graph"}},
        )

        return Command(update={"messages": response["messages"][-1]}, goto="supervisor")

    def call_writingTeam(
        state: withStructuredOutputModels.AgentState,
    ) -> withStructuredOutputModels.AgentState:

        response = writingTeam_graph.invoke(
            {
                "messages": state["messages"][-1],
                "exeNum": state["exeNum"],
            },
            config={"configurable": {"thread_id": "writingTeam_graph"}},
        )

        return Command(update={"messages": response["messages"][-1]}, goto="supervisor")

    # Requirement Definition（要件定義）ノード
    def call_requirementDefinition(
        state: withStructuredOutputModels.AgentState,
    ) -> withStructuredOutputModels.AgentState:

        Response = llm_claude35sonne_v2.invoke(
            [
                SystemMessage(
                    content=SystemPromptRequirementDefinition.format(
                        workers=json.dumps(coreTeam_workers, ensure_ascii=False)
                    )
                ),
                state["messages"][-1],
            ]
        )

        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=Response.content,
                        name="PM",
                    )
                ]
            },
            goto="supervisor",
        )

    coreTeam_builder = StateGraph(withStructuredOutputModels.AgentState)
    coreTeam_builder.add_node("supervisor", coreTeam_supervisor_node)
    coreTeam_builder.add_node("retrievalTeam", call_retrievalTeam)
    coreTeam_builder.add_node("writingTeam", call_writingTeam)
    coreTeam_builder.add_node("requirementDefinition", call_requirementDefinition)
    coreTeam_builder.add_edge(START, "requirementDefinition")

    memory = MemorySaver()
    coreTeam_graph = coreTeam_builder.compile(checkpointer=memory)
    # -------------------------------------------------------------------------------------------------
    # ----------------------------------superviso_graph__create_END------------------------------------
    # -------------------------------------------------------------------------------------------------

    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!GRAPH__START!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    dic = defaultdict(dict)
    dic[mainSVname] = 0

    final_response = None

    for s in coreTeam_graph.stream(
        {
            "messages": [
                HumanMessage(
                    content="""blenderのジオメトリノードの最新情報を検索し、その内容を解説する文を会話形式で作成してください。""",
                    name="user",
                )
            ],
            "exeNum": dic,
        },
        subgraphs=True,
        config={"configurable": {"thread_id": "coreTeam_graph"}},
    ):
        final_response = s
        print(s)
        print("----")

    print("----")
    print("Final Response:", final_response)


class SearchDDGInput(BaseModel):
    queries: List[str] = Field(
        description="Please enter a list of keywords you want to search for"
    )


# DuckDuckGo検索
@tool(args_schema=SearchDDGInput)
def tool_Search(
    queries: Annotated[List[str], "List of query strings for searching"],
    max_result_num: Annotated[int, "Maximum number of results returned per query"] = 1,
) -> Annotated[
    Dict[str, List[Dict[str, str]]], "List of search results for each query"
]:
    """
    A tool for performing DuckDuckGo searches.
    Performs web searches using DuckDuckGo with the specified multiple queries and returns the results.
    The returned information includes page title, summary (snippet), and URL.

    Parameters
    ----------
    queries : List[str]
        List of query strings for searching.
    max_result_num : int
        Maximum number of results returned per query.

    Returns
    -------
    Dict[str, List[Dict[str, str]]]:
        Dictionary containing search results for each query.
        For each query, returns a list of dictionaries containing:
        - title: Title
        - snippet: Page summary
        - url: Page URL

    This function recommends searching in the most appropriate language for specific questions, such as programming-related queries.
    Also, if search results alone are not sufficient, it is recommended to use additional tools to retrieve actual page content.
    """
    all_results = {}

    for query in queries:
        try:
            # まずDDGSで試行
            results = DDGS().text(
                query,
                region="wt-wt",
                safesearch="off",
                backend="lite",
                max_results=max_result_num,
            )
            query_results = [
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                }
                for r in islice(results, max_result_num)
            ]

            # 結果が空の場合はGoogle検索にフォールバック
            if not query_results:
                raise Exception("No results from DDGS")

        except Exception as e:
            # DDGSが失敗した場合、Google検索を使用
            try:
                query_results = gSearch(query, max_result_num)
            except Exception as ge:
                # 両方の検索が失敗した場合
                print(
                    f"Both DDGS and Google Search failed for query '{query}': {str(ge)}"
                )
                query_results = []

        all_results[query] = query_results

    return all_results


# Custom Search APIによる検索処理
def gSearch(
    word: Annotated[str, "Search text"], num: Annotated[int, "Number of results"] = 1
) -> Annotated[
    List[Dict[str, str]], "List of search results containing title, snippet, and URL"
]:
    url = "https://www.googleapis.com/customsearch/v1"

    # 複数のAPIキーをリストとして管理
    CustomSearchAPIAPIKEYS = [
        CustomSearchAPIAPIKEY,
    ]

    for api_key in CustomSearchAPIAPIKEYS:
        try:
            params = {
                "q": word,
                "key": api_key,
                "cx": SEARCH_ENGINE_ID,
                "num": num,
            }

            response = requests.get(url, params=params)

            if response.status_code == 200:
                results = response.json()
                filtered_results = [
                    {
                        "title": item["title"],
                        "snippet": item["snippet"],
                        "url": item["link"],
                    }
                    for item in results.get("items", [])
                ]
                return filtered_results

            elif response.status_code == 403 or response.status_code == 429:
                print(f"API key {api_key} exceeded limit. Trying next key...")
                continue  # 次のAPIキーに切り替え
            else:
                raise Exception(f"Error: {response.status_code}, {response.text}")

        except Exception as e:
            print(f"Error with API key {api_key}: {e}")
            continue  # 次のAPIキーを試す

    raise Exception("All API keys have exceeded their limits or are invalid.")


class ScrapeWebpages(BaseModel):
    urls: List[str] = Field(description="The target URL for search")


# # URLからweb情報を取得し文字列として返す
@tool(args_schema=ScrapeWebpages)
def tool_scrape_webpages(urls: List[str]) -> str:
    """Use requests and bs4 to scrape the provided web pages for detailed information."""

    scraper = WebScraperUtility()

    URLS = []

    for URL in urls:
        url = URL
        result = scraper.get_full_visible_text(url)
        URLS.append({"URL": URL, "document": result})

    return json.dumps(URLS)


class WorkerProfile(TypedDict):
    name: str
    role: str


class action(TypedDict):
    actionName: str
    actionDetail: str


def make_supervisor_node(
    llm: BaseChatModel,
    workers: list[WorkerProfile],
    actions: list[action],
    finalAnswer: str,
    visorName: str,
    MemoryStore: MemoryStoreUtility,
) -> str:
    options = (
        [finalAnswer]
        + [w["name"] for w in workers]
        + [a["actionName"] for a in actions]
    )

    WorkerLiteral = Union[Literal["__end__"], str]  # workersの名前も含める

    def supervisor_node(state: withStructuredOutputModels.AgentState) -> Literal[WorkerLiteral]:  # type: ignore
        """An LLM-based router."""

        # 現在のSV名
        Name = visorName

        # storeを検索して成果物を取得
        jsDeliverable = MemoryStore.get_combined_deliverables(
            MemoryStore.get_namespace_tools(Name)
        )

        # ルーティング用システムプロンプトを作成
        system_prompt = SystemPrompSupervisor.format(
            teamName=Name,
            worker=json.dumps(workers, ensure_ascii=False),
            action=json.dumps(actions, ensure_ascii=False),
        )

        messages = (
            [SystemMessage(content=system_prompt)]
            + state["messages"]
            + [
                HumanMessage(
                    content=HumanPromptMemoryStore.format(jsDeliverable=jsDeliverable),
                    name=deliverablesManager,
                )
            ]
        )

        Router = withStructuredOutputModels.update_router_types(
            options,
            f"Worker to route to next. If no workers needed, route to {finalAnswer}.",
        )
        # ルーティングllmを実行
        response = llm.with_structured_output(Router).invoke(messages)

        goto = response.next

        if goto == "FINISH":
            goto = END

            return Command(
                update={
                    "messages": [
                        HumanMessage(
                            # 依頼された作業が終了しました。成果物は{deliverablesManager}からご確認ください。
                            content=f"The requested work is complete. Please check the deliverables with {deliverablesManager}.",
                            name=Name,
                        )
                    ]
                },
                goto=goto,
            )

        elif goto == "COMPLETE":
            goto = END

            Extractresultsfromdata = llm.invoke(
                (
                    [SystemMessage(content=SystemPromptExtractresultsfromdata.format())]
                    # ユーザの依頼内容
                    + [state["messages"][0]]
                    # 依頼内容から要件定義した内容
                    + [state["messages"][1]]
                    + [
                        HumanMessage(
                            content=HumanPromptMemoryStore.format(
                                jsDeliverable=jsDeliverable
                            ),
                            name=deliverablesManager,
                        ),
                    ]
                )
            )

            return Command(
                update={
                    "messages": [
                        HumanMessage(
                            content=Extractresultsfromdata.content,
                            name=Name,
                            additional_kwargs={"result": "SUCCESS"},
                        )
                    ]
                },
                goto=goto,
            )

        elif goto == "ASK":
            goto = END

            askResponse = llm.invoke(
                (
                    [
                        SystemMessage(
                            #         あなたは{Name}の監督者です。以下のワーカー指示を行う前に、直前の指揮命令者からの指示に不明点を感じました。
                            # 不明点を直前の指揮命令者へ問い合わせを行ってください。
                            content=f"""You are the supervisor of {Name}. Before carrying out the following worker instructions, 
                            you felt there were unclear points in the instructions from your immediate superior. 
                            Please inquire with your immediate superior to clarify these unclear points.。
                    {json.dumps(workers, ensure_ascii=False)}"""
                        )
                    ]
                    + state["messages"]
                    + [
                        HumanMessage(
                            content=HumanPromptMemoryStore.format(
                                jsDeliverable=jsDeliverable
                            ),
                            name=deliverablesManager,
                        )
                    ]
                )
            )

            return Command(
                update={
                    "messages": [
                        HumanMessage(
                            content=askResponse.content,
                            name=Name,
                        )
                    ]
                },
                goto=goto,
            )
        elif goto == "REQUEST":
            goto = END

            requestResponse = llm.invoke(
                (
                    [
                        SystemMessage(
                            # あなたは{Name}の監督者です。以下のワーカーに指示を行う前に、直前の指揮命令者から受けた指示に達成困難な点を見つけました。
                            #     改善要求、改善案を直前の指揮命令者へ提言してください。
                            content=f"""You are the supervisor of {Name}. Before giving instructions to the workers below, you have identified some unachievable points in the instructions you received from your immediate superior. 
                            Please propose improvements and suggestions for improvement to your immediate superior.
                                {json.dumps(workers, ensure_ascii=False)}"""
                        )
                    ]
                    + state["messages"]
                    + [
                        HumanMessage(
                            content=HumanPromptMemoryStore.format(
                                jsDeliverable=jsDeliverable
                            ),
                            name=deliverablesManager,
                        )
                    ]
                )
            )

            return Command(
                update={
                    "messages": [
                        HumanMessage(
                            content=requestResponse.content,
                            name=Name,
                        )
                    ]
                },
                goto=goto,
            )

        else:
            # SVごとの実行回数を記録する
            state["exeNum"][goto] = state["exeNum"].get(goto, 0) + 1

            # 次へのワーカへの指示をllmで作成
            instructionResponse = llm.invoke(
                [
                    SystemMessage(
                        content=SystemPromptInstruction.format(
                            teamName=Name,
                            workers=json.dumps(workers, ensure_ascii=False),
                        )
                    )
                ]
                + state["messages"]
                + [
                    HumanMessage(
                        content=HumanPromptMemoryStore.format(
                            jsDeliverable=jsDeliverable
                        ),
                        name=deliverablesManager,
                    ),
                    HumanMessage(
                        # 次のワーカーへ指示を行ってください。ワーカ名:{goto}
                        content=f"Please give the following instructions to the worker. Worker name: {goto}",
                        name="supervisor",
                    ),
                ]
            )

            return Command(
                update={
                    "messages": [
                        HumanMessage(
                            content=instructionResponse.content,
                            name=Name,
                        )
                    ]
                },
                goto=goto,
            )

    return supervisor_node


if __name__ == "__main__":
    main()