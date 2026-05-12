import asyncio
import sys
import os
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# 禁用系统代理（避免 VPN/代理干扰）
for _k in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
    os.environ.pop(_k, None)

async def stable_goto(page, url, timeout=30000):
    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

async def wait_nav(page, timeout=12000):
    try:
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except PlaywrightTimeoutError:
            pass

async def main():
    async with async_playwright() as p:
        trace_dir = r"traces/task-181757"
        os.makedirs(trace_dir, exist_ok=True)
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-proxy-server"])
        ctx = await browser.new_context()
        page = await ctx.new_page()
        _frame = None
        await stable_goto(page, 'https://httpbin.org/html')
        await wait_nav(page)
        await page.screenshot(path=r'traces/task-181757/screenshot_1.png')
        print('[screenshot] 截图已保存: traces/task-181757/screenshot_1.png')
        print('[done] DSL 执行完成')

asyncio.run(main())
