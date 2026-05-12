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

async def _get_browser_and_page(p):
    """直接启动本地 Chromium（跳过 CDP 连接以避免依赖外部浏览器）"""
    print("🚀 启动本地 Chromium...")
    browser = await p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-proxy-server"])
    ctx = await browser.new_context()
    page = await ctx.new_page()
    print("✅ Chromium 已启动")
    return browser, ctx, page

async def main():
    async with async_playwright() as p:
        browser, ctx, page = await _get_browser_and_page(p)
        _frame = None
        # 未识别指令: test https://bing.com
        print('✅ DSL 执行完成')

asyncio.run(main())
