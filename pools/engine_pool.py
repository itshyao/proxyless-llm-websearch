from contextlib import asynccontextmanager
from asyncio import Queue, Semaphore
from playwright.async_api import async_playwright
import atexit
import asyncio

class BrowserPlaywright:
    def __init__(self, headless):
        self.playwright = None
        self.browser = None
        self.headless = headless

    async def __aenter__(self):
        # 启动 Playwright 只需启动一次
        if not self.playwright:
            self.playwright = await async_playwright().start()
        # 启动浏览器只需启动一次
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(headless=self.headless)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Only close the browser when we're done with all tasks
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def new_page(self):
        # 创建新页面
        context = await self.browser.new_context()
        return await context.new_page()


class BrowserPool:
    def __init__(self, pool_size: int):
        self.pool_size = pool_size
        self.pool = Queue(maxsize=pool_size)  # 设置队列的最大长度为 pool_size
        self.lock = Semaphore(pool_size)  # 控制并发
        self.browser_instances = []  # 用来保存浏览器实例
        # 注册退出时清理资源的函数
        atexit.register(lambda: asyncio.run(self.cleanup()))

    @asynccontextmanager
    async def get_browser(self):
        async with self.lock:
            browser_instance = await self._get_browser_instance()
            try:
                yield browser_instance
            finally:
                await self._release_browser_instance(browser_instance)

    async def _get_browser_instance(self):
        # 如果池为空，创建新实例
        if self.pool.empty():
            browser_instance = await self._create_browser_instance()
        else:
            browser_instance = await self.pool.get()
        return browser_instance

    async def _create_browser_instance(self, headless=True):
        # 创建一个新的浏览器实例并返回
        browser_instance = await BrowserPlaywright(headless).__aenter__()
        self.browser_instances.append(browser_instance)  # 保存实例
        return browser_instance

    async def _release_browser_instance(self, browser_instance: BrowserPlaywright):
        if self.pool.qsize() < self.pool_size:
            await self.pool.put(browser_instance)

    async def cleanup(self):
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        print("Cleaning up all browser instances.")

        # 并发清理所有实例
        await asyncio.gather(
            *(browser.__aexit__(None, None, None) for browser in self.browser_instances)
        )
