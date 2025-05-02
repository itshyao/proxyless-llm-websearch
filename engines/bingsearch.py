from typing import List, Optional
import unicodedata
from bs4 import BeautifulSoup
from pools import BrowserPool, BrowserPlaywright

class BingSearch:

    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.base_url = "https://cn.bing.com"

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

        # 输入搜索内容并执行搜索
        await page.fill('input#sb_form_q', question)
        await page.wait_for_timeout(500)
        await page.keyboard.press('Enter')
        await page.wait_for_selector('li.b_algo')  # 等待搜索结果加载完成
        await page.wait_for_timeout(2000)
        html = await page.content()
        await page.close()
        await context.close()
        return html

    def parsing(self, html: Optional[str]) -> Optional[List[dict]]:
        soup = BeautifulSoup(html, "lxml")
        items = soup.find_all("li", class_=lambda x: x and "b_algo" in x)
        results = []
        for item in items:
            publisher_tag = item.find("a", class_="tilk")
            publisher = publisher_tag.get("aria-label")
            url = publisher_tag.get("href")

            if item.find("p"):
                content = unicodedata.normalize("NFKC", item.find("p").get_text(strip=True))
                content_list = content.split(" · ")
                if len(content_list) == 2:
                    time = content_list[0]
                    summary = content_list[1]
                else:
                    time = "UNKNOW"
                    summary = content_list[0]
            else:
                time = ""
                summary = ""

            title_tag = item.find("h2")
            title = title_tag.get_text(strip=True)

            data = {
                "title": title,
                "publisher": publisher,
                "url": url,
                "summary": summary,
                "time": time
            }
            results.append(data)

        return results

