import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from contextlib import asynccontextmanager
from base import WebTools, ToolsGraph
from base.pools import BrowserPool, CrawlerPool
from base.reranker import Chunker, DashscopeReranker
from base.ultis import QueryRequest

browser_pool = BrowserPool(pool_size=1)
crawler_pool = CrawlerPool(pool_size=1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup：可选预热
    await browser_pool._create_browser_instance(headless=True)
    await crawler_pool._get_instance()
    print("✅ Browser pool initialized.")

    yield  # 应用运行中，等待请求

    # shutdown：清理资源
    await browser_pool.cleanup()
    await crawler_pool.cleanup()
    print("✅ Browser pool cleaned up.")

app = FastAPI(lifespan=lifespan)

@app.get("/healthy")
async def healthy():
    return "ok"

@app.post("/search")
async def search(params: QueryRequest):
    chunker = Chunker(chunk_size=params.split.chunk_size, chunk_overlap=params.split.chunk_overlap, separators=params.split.separators)
    reranker = DashscopeReranker(top_k=params.rerank.top_k)
    ts_manage = WebTools(
        browser_pool=browser_pool,
        crawler_pool=crawler_pool,
        engine=params.engine,
        chunker=chunker,
        reranker=reranker)
    tools = [ts_manage.web_search, ts_manage.link_parser]
    graph = ToolsGraph(tools=tools)
    result = await graph.run(params.question)
    return {"data": result}

if __name__ == "__main__":
    import uvicorn
    port = 8800
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
