import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from dotenv import load_dotenv
load_dotenv()

from base.ultis import QueryRequest, SplitRequest, RerankRequest
from base import WebTools, ToolsGraph
from base.pools import BrowserPool, CrawlerPool
from base.reranker import Chunker, DashscopeReranker
from base.ultis import QueryRequest
import asyncio

async def main():
    browser_pool = BrowserPool(pool_size=1)
    crawler_pool = CrawlerPool(pool_size=1)

    await browser_pool._create_browser_instance(headless=True)
    await crawler_pool._get_instance()
    
    params = QueryRequest(
        question="广州今日天气",
        engine="bing",
        split=SplitRequest(chunk_size=512, chunk_overlap=128, separators=["\n\n", "\n"]),
        rerank=RerankRequest(top_k=5)
    )

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

    await browser_pool.cleanup()
    await crawler_pool.cleanup()

    print(result)

if __name__ == "__main__":
    asyncio.run(main())