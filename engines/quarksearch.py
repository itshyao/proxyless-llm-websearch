from typing import Optional, List
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from pools import BrowserPool, BrowserPlaywright

class QuarkSearch:
    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.base_url = "https://ai.quark.cn/"

    async def response(self, questions: Optional[List[str]]) -> Optional[dict]:
        results = {}
        async with self.browser_pool.get_browser() as browser:
            for question in questions:
                html = await self.run(browser=browser, question=question)
                result = self.parsing(html)
                if result:
                    results[question] = result
        return results

    async def run(self, browser: BrowserPlaywright, question: Optional[str]):
        context = await browser.browser.new_context()
        page = await context.new_page()
        await page.goto(self.base_url)

        await page.fill('textarea[placeholder="搜资料、提问题、找答案"]', question)
        await page.wait_for_timeout(1000)
        await page.wait_for_selector("span.input-keywords-highlight", timeout=5000)
        await page.click("span.input-keywords-highlight")


        await page.wait_for_selector("section.sc.sc_structure_template_normal")

        await page.wait_for_function('document.body !== null')
        await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')

        # await page.screenshot(path="quark_weather.png")


        html = await page.content()
        await page.close()
        await context.close()
        return html

    def parsing(self, html):
        soup = BeautifulSoup(html, "lxml")
        items = soup.find_all("section", class_="sc sc_structure_template_normal")
        results = []
        for item in items:
            # 提取标题
            title_tag = item.find("div", class_="qk-title-text")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # 提取发布者
            tags = item.find_all("span", class_="qk-source-item qk-clamp-1")
            publisher = tags[0].get_text(strip=True) if tags else ""
            if len(tags) == 2:
                time = tags[1].get_text(strip=True)
            else:
                time = ""

            url_tag = item.find("a", class_="qk-link-wrapper")
            url = url_tag["href"] if url_tag else ""

            summary_tag = item.find("div", class_="qk-paragraph-text")
            summary = summary_tag.get_text(strip=True) if summary_tag else ""

            # 输出解析后的信息
            result = {
                "title": title,
                "publisher": publisher,
                "url": url,
                "summary": summary,
                "time": time
            }
            results.append(result)
        return results





