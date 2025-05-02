import asyncio
import atexit
from asyncio import Queue, Semaphore
from contextlib import asynccontextmanager
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode


class CrawlerInstance:
    def __init__(self):
        self.browser_config = BrowserConfig(headless=True, verbose=False)
        self.run_config = CrawlerRunConfig(cache_mode=CacheMode.ENABLED, stream=False)
        self.crawler = None

    async def __aenter__(self):
        self.crawler = AsyncWebCrawler(config=self.browser_config)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.crawler:
            await self.crawler.close()

    async def run(self, urls: list[str]) -> list[dict]:
        responses = await self.crawler.arun_many(urls=urls, config=self.run_config)

        results = []
        for r in responses:
            if r.success:
                results.append({"url": r.url, "content": r.markdown})
        return results

class CrawlerPool:
    def __init__(self, pool_size):
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)
        self.lock = Semaphore(pool_size)
        self.instances = []
        atexit.register(lambda: asyncio.run(self.cleanup()))

    @asynccontextmanager
    async def get_crawler(self):
        async with self.lock:
            crawler = await self._get_instance()
            try:
                yield crawler
            finally:
                await self._release_instance(crawler)

    async def _get_instance(self):
        if self.pool.empty():
            crawler = await CrawlerInstance().__aenter__()
            self.instances.append(crawler)
        else:
            crawler = await self.pool.get()
        return crawler

    async def _release_instance(self, crawler: CrawlerInstance):
        if self.pool.qsize() < self.pool_size:
            await self.pool.put(crawler)

    async def cleanup(self):
        await asyncio.gather(*[
            crawler.__aexit__(None, None, None)
            for crawler in self.instances
        ])
