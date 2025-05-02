from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from agent import ToolsGraph
from pools import BrowserPool, CrawlerPool

browser_pool = BrowserPool(pool_size=1)
crawler_pool = CrawlerPool(pool_size=1)
graph = ToolsGraph(browser_pool, crawler_pool, engine="sougou")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str


@app.post("/search")
async def search(query: QueryRequest):
    result = await graph.run(query.question)
    return {"data": result}

if __name__ == "__main__":
    import uvicorn
    port = 8000
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
