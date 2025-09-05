import sys
import os
# 设置项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from langchain_mcp_adapters.client import MultiServerMCPClient
from base import ToolsGraph
from base.ultis import QueryRequest



# FastAPI应用初始化
app = FastAPI()

# 请求模型
class QuestionRequest(BaseModel):
    question: str

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

async def get_answer_from_tools(question: str):
    """获取工具的回答"""
    tools = await load_mcp_tools()
    graph = ToolsGraph(tools=tools)
    result = await graph.run(question)
    return result

@app.get("/healthy")
async def healthy():
    return "ok"

# FastAPI 路由，接收问题并返回答案
@app.post("/search")
async def ask_question(params: QuestionRequest):
    result = await get_answer_from_tools(params.question)
    return {"data": result}

if __name__ == "__main__":
    # 启动FastAPI应用
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8800)
