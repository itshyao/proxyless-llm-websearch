from typing import List, Optional
from bs4 import BeautifulSoup
from pools import BrowserPool, BrowserPlaywright
import json
class BaiduSearch:

    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.base_url = "https://www.baidu.com/"

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

        await page.fill('input[name="wd"]', question)
        await page.wait_for_timeout(1000)
        await page.click('input#su')
        await page.wait_for_selector('div.c-container')  # 等待搜索结果加载完成
        await page.wait_for_timeout(1000)
        html = await page.content()
        await page.close()
        await context.close()
        return html

    def parsing(self, html: Optional[str]) -> Optional[List[dict]]:
        soup = BeautifulSoup(html, "lxml")
        items = soup.find_all("div", class_="c-container")
        results = []
        for item in items:
            title_tag = item.find('h3', class_='c-title t t tts-title')
            title = title_tag.get_text(strip=True) if title_tag else ''

            publisher_tag = item.find('a', class_='siteLink_9TPP3')
            publisher = publisher_tag.get_text(strip=True) if publisher_tag else ''

            url_tag = item.find('a', class_='siteLink_9TPP3')
            url = url_tag['href'] if url_tag else ''

            summary_tag = item.find('span', class_='content-right_2s-H4')
            summary = summary_tag.get_text(strip=True) if summary_tag else ''

            time_tag = item.find("span", class_="c-color-gray2")
            time = time_tag.get_text(strip=True) if time_tag else ''

            data = {
                "title": title,
                "publisher": publisher,
                "url": url,
                "summary": summary,
                "time": time
            }
            if url:
                results.append(data)
            results = [json.loads(x) for x in set(json.dumps(d, sort_keys=True) for d in results)]
        return results

