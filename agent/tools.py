from engines import BingSearch, QuarkSearch, BaiduSearch, SougouSearch
from typing import List, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel


class WebSearchArgsSchema(BaseModel):
    questions: List[str]

class QuarkSearchArgsSchema(BaseModel):
    questions: List[str]

class LinkParserArgsSchema(BaseModel):
    urls: List[str]

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
