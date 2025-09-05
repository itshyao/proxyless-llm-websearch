import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from dotenv import load_dotenv
load_dotenv()

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from base import ToolsGraph

async def load_mcp_tools():
    """加载 MCP 工具"""
    client = MultiServerMCPClient(
        {
            "websearch": {
                "url": f"http://localhost:8001/sse",
                "transport": "sse",
            }
        }
    )
    tools = await client.get_tools()
    return tools

async def main(question):

    tools = await load_mcp_tools()  

    graph = ToolsGraph(tools=tools)
    result = await graph.run(question)
    print(result)


if __name__ == "__main__":
    result = asyncio.run(main(question="这个网页讲了什么：https://zhuanlan.zhihu.com/p/440982337"))
