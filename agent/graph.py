from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph, MessagesState
from langgraph.prebuilt import ToolNode
from typing import Literal
from datetime import datetime
from dotenv import load_dotenv
import os
from agent.tools import WebTools
from .prompt import prompts
load_dotenv()
def get_datetime_str():
    now = datetime.now()
    datetime_str = now.strftime("%Y-%m-%d %H:%M")
    return datetime_str

class ToolsGraph:

    def __init__(self, browser_pool, crawler_pool, engine):
        self.browser_pool = browser_pool
        self.crawler_pool = crawler_pool
        self.engine = engine
        self.ts_manage = WebTools(browser_pool=self.browser_pool, crawler_pool=crawler_pool, engine=self.engine)
        self.tools = [self.ts_manage.web_search, self.ts_manage.link_parser]
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
        print(messages)
        response = await self.llm.ainvoke(messages)
        return {"messages": [response]}

    async def run(self, question):
        inputs = {"messages": [SystemMessage(content=prompts["web_prompt"]),HumanMessage(content=question)]}
        final_state = await self.graph.ainvoke(inputs)
        for i in final_state["messages"]:
            print(i)
        return final_state["messages"][-1].content

