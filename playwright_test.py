from playwright.async_api import async_playwright
import asyncio

async def do_login(page):
    await page.goto("https://example.com")
    print("Page title:", await page.title())
    return page

async def do_something_else(page):
    print("Page URL:", page.url)
    await page.click("h1")

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Try passing page between functions
        page = await do_login(page)
        await do_something_else(page)
        
        await context.close()
        await browser.close()

asyncio.run(main())
