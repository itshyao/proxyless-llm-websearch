from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from typing import List, Optional, Literal
from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from datetime import datetime
import os

from .prompt import prompts
from base.engines import BingSearch, QuarkSearch, BaiduSearch, SougouSearch

class WebSearchArgsSchema(BaseModel):
    questions: List[str]

class LinkParserArgsSchema(BaseModel):
    urls: List[str]

def get_datetime_str():
    now = datetime.now()
    datetime_str = now.strftime("%Y-%m-%d %H:%M")
    return datetime_str

class WebTools():

    def __init__(self, browser_pool, crawler_pool, engine, chunker, reranker):
        self.browser_pool = browser_pool
        self.crawler_pool = crawler_pool
        self.engine = engine
        self.chunker=chunker
        self.reranker=reranker

        self.web_search = StructuredTool(
            name='web_search',
            description='网络搜索功能，模拟搜索引擎，专门解决实时类问题的查询。',
            args_schema=WebSearchArgsSchema,
            coroutine=self.web_search_function  # 协程函数
        )

        self.link_parser = StructuredTool(
            name='link_parser',
            description='用于解析url，获取网页链接的内容，其中urls为链接，query为用户在工具‘web_search’输入的查询。',
            args_schema=LinkParserArgsSchema,
            coroutine=self.link_parser_function
        )

    async def web_search_function(self, questions: list) -> dict:
        if self.engine == "bing":
            search = BingSearch(browser_pool=self.browser_pool)
        elif self.engine == "quark":
            search = QuarkSearch(browser_pool=self.browser_pool)
        elif self.engine == "baidu":
            search = BaiduSearch(browser_pool=self.browser_pool)
        elif self.engine == "sougou":
            search = SougouSearch(browser_pool=self.browser_pool)
        else:
            raise "engine输入错误"
        result = await search.response(questions)
        return result

    async def split_and_reranker(self, query, contents):
        results, chunks, indexs, n = [], [], {}, 0
        for content in contents:
            final_splits = self.chunker.split_text(content["content"])
            chunks.extend([chunk for chunk in final_splits])
            for i in range(n, len(chunks)+n):
                indexs[i] = content["url"]
            n += len(chunks)

        reranked_chunks, reranked_indexs = await self.reranker.get_reranked_documents(query, chunks)
        results = [{indexs[reranked_indexs[i]]: reranked_chunks[i]} for i in range(len(reranked_chunks))]

        return results

    async def link_parser_function(self, urls: list, query: Optional[str] = None) -> list:
        try:
            async with self.crawler_pool.get_crawler() as crawler:
                results = await crawler.run(urls)
                if query:
                    results = await self.split_and_reranker(query, results)
                    return results
                else:
                    return results
        except:
            return results


class ToolsGraph:

    def __init__(self, tools):

        self.tools = tools

        self.tool_node = ToolNode(self.tools)
        self.llm = ChatOpenAI(
            model=os.getenv("MODEL_NAME"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            streaming=False,
            temperature=0,
        ).bind_tools(self.tools)

        workflow = StateGraph(MessagesState)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("tools",  self.tool_node)
        # 设定入口为 agent
        workflow.add_edge(START, "agent")
        # 条件边：决定是否继续调用工具
        workflow.add_conditional_edges("agent",  self.should_continue)
        # 设置普通边：agent 到 agent
        workflow.add_edge("tools", "agent")
        self.graph = workflow.compile()


    def should_continue(self, state: MessagesState) -> Literal["tools", END]:
        messages = state['messages']
        last = messages[-1]
        return "tools" if last.tool_calls else END

    async def call_model(self, state: MessagesState):
        messages = state["messages"]
        response = await self.llm.ainvoke(messages)
        return {"messages": [response]}

    async def run(self, question):
        inputs = {"messages": [SystemMessage(content=prompts["web_prompt"] + f"\n当前时间：{get_datetime_str()}"),HumanMessage(content=question)]}
        final_state = await self.graph.ainvoke(inputs)
        print(final_state)
        for i in final_state["messages"]:
            print(i)
        return final_state["messages"][-1].content

