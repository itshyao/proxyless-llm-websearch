from engines import BingSearch, QuarkSearch, BaiduSearch, SougouSearch
from reranker import OpenAIEmbeddingReranker, Chunker
from typing import List, Optional
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

reranker = OpenAIEmbeddingReranker()


class WebSearchArgsSchema(BaseModel):
    questions: List[str]

class QuarkSearchArgsSchema(BaseModel):
    questions: List[str]

class LinkParserArgsSchema(BaseModel):
    urls: List[str]

class WebTools():

    def __init__(self, browser_pool, crawler_pool, engine):
        self.browser_pool = browser_pool
        self.crawler_pool = crawler_pool
        self.engine = engine
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

    async def link_parser_function(self, urls: list, query: Optional[str] = None) -> list:
        try:
            async with self.crawler_pool.get_crawler() as crawler:
                results = await crawler.run(urls)
                if query:
                    results = await split_and_reranker(query, results)
                    print(results)
                    return results
                else:
                    return results
        except:
            return results

async def split_and_reranker(query, contents):
    results = []
    for content in contents:
        splitter = Chunker()
        final_splits = splitter.split_text(content["content"])
        final_splits = [chunk for chunk in final_splits]
        reranker_results = await reranker.get_reranked_documents(query, final_splits, top_k=10)
        content["content"] = "\n".join(reranker_results)
        if content["content"]:
            results.append(content)
    return results