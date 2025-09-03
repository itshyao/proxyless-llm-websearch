from dotenv import load_dotenv
load_dotenv()

from pools import BrowserPool, CrawlerPool
from ultis import QueryRequest, SplitRequest, RerankRequest
from agent import ToolsGraph
from reranker import OpenAIEmbeddingReranker, Chunker, DashscopeReranker
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
    
    graph = ToolsGraph(browser_pool, crawler_pool, engine=params.engine, chunker=chunker, reranker=reranker)
    result = await graph.run(params.question)

    await browser_pool.cleanup()
    await crawler_pool.cleanup()

    print(result)

if __name__ == "__main__":
    asyncio.run(main())