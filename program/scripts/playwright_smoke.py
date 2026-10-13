from __future__ import annotations
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True)
        page=await browser.new_page()
        await page.set_content("<title>CKH</title><h1>网络回退</h1>")
        print(await page.title(),await page.locator("h1").inner_text())
        await browser.close()

asyncio.run(main())
