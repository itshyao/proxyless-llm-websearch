import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)

from dotenv import load_dotenv
load_dotenv()

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from typing import Any
from mcp.server.fastmcp import FastMCP, Context
from base.pools import BrowserPool, CrawlerPool
from base.engines import BingSearch
from base.reranker import Chunker, DashscopeReranker
from loguru import logger

@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[Any]:

    browser_pool = BrowserPool(pool_size=1)
    await browser_pool._create_browser_instance(headless=True)

    crawler_pool = CrawlerPool(pool_size=1)
    await crawler_pool._get_instance()
    print("✅ Browser pool initialized.")

    yield {"browser_pool": browser_pool, "crawler_pool": crawler_pool}

    # shutdown：清理资源
    await browser_pool.cleanup()
    # await crawler_pool.cleanup()
    print("✅ Browser pool cleaned up.")

mcp = FastMCP(name="websearch", port=8001, lifespan=lifespan)


async def split_and_reranker(query, contents):
    chunker = Chunker(chunk_size=512, chunk_overlap=128, separators=["\n\n", "\n"])
    reranker = DashscopeReranker(top_k=5)
    results, chunks, indexs, n = [], [], {}, 0
    for content in contents:
        final_splits = chunker.split_text(content["content"])
        chunks.extend([chunk for chunk in final_splits])
        for i in range(n, len(chunks) + n):
            indexs[i] = content["url"]
        n += len(chunks)

    reranked_chunks, reranked_indexs = await reranker.get_reranked_documents(query, chunks)
    results = [{indexs[reranked_indexs[i]]: reranked_chunks[i]} for i in range(len(reranked_chunks))]

    return results

@mcp.tool(description="搜索引擎工具，根据用户问题进行网页搜索。")
async def web_search(ctx: Context, questions: list) -> dict:
    """搜索引擎工具，根据用户问题进行网页搜索。"""
    logger.info(questions)
    browser_pool = ctx.request_context.lifespan_context["browser_pool"]

    search = BingSearch(browser_pool=browser_pool)
    result = await search.response(questions)
    logger.info(result)

    return result


@mcp.tool(description="URL解析工具，解析网页链接内容，支持查询功能。")
async def link_parser(ctx: Context, urls: list, query: str) -> list:
    """URL解析工具，解析网页链接内容，支持查询功能。"""
    logger.info(f"{query} | {urls}")
    crawler_pool = ctx.request_context.lifespan_context["crawler_pool"]

    async with crawler_pool.get_crawler() as crawler:
        results = await crawler.run(urls)
        logger.info(results)
        if query:
            results = await split_and_reranker(query, results)
    logger.info(results)
    # await crawler_pool.cleanup()
    return results


if __name__ == "__main__":
    mcp.run(transport="sse")