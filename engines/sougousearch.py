from typing import List, Optional
from bs4 import BeautifulSoup
from pools import BrowserPool, BrowserPlaywright

class SougouSearch:

    def __init__(self, browser_pool: BrowserPool):
        self.browser_pool = browser_pool
        self.base_url = "https://www.sogou.com"

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
        context = await browser.browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36")
        page = await context.new_page()
        await page.goto(self.base_url)
        await page.wait_for_timeout(1000)
        # await page.screenshot(path="sougou.png")
        await page.fill('input#query', question)
        await page.wait_for_timeout(1000)
        await page.click('input#stb')
        await page.wait_for_timeout(1000)
        await page.wait_for_selector('div.vrwrap')

        html = await page.content()
        await page.close()
        await context.close()
        return html

    def parsing(self, html: Optional[str]) -> Optional[List[dict]]:
        soup = BeautifulSoup(html, "lxml")
        items = soup.find_all("div", class_="vrwrap")

        results = []
        for item in items:
            title_tag = item.select_one("h3.vr-title a")
            title = title_tag.get_text(strip=True) if title_tag else ""
            url = title_tag.get("href", "") if title_tag else ""

            if url.startswith("/link?url="):
                url = f"{self.base_url}{url}"

            summary_tag = item.select_one("div.text-layout p.star-wiki")
            if summary_tag:
                summary = summary_tag.get_text(strip=True)
            else:
                alt_summary_tag = item.select_one("div.fz-mid.space-txt")
                summary = alt_summary_tag.get_text(strip=True) if alt_summary_tag else ""

            publisher_tag = item.find("div", class_="citeurl")
            publisher = publisher_tag.get_text(strip=True) if publisher_tag else ""

            time_tag = summary.split("-")
            if len(time_tag) == 2:
                time = time_tag[0]
            else:
                time = ""
            if title and url:
                data = {
                    "title": title,
                    "publisher": publisher,
                    "url": url,
                    "summary": summary,
                    "time": time
                }
                results.append(data)
        return results


