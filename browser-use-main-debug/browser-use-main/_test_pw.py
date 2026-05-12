import urllib.request, json, time

# Simple Playwright script to test
script = '''
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp("http://127.0.0.1:9222")
        page = await browser.contexts[0].new_page()
        await page.goto("https://www.bing.com", wait_until="domcontentloaded")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_selector("#sb_form_q", state="visible")
        await page.fill("#sb_form_q", "耳机")
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle")
        title = await page.title()
        print(f"Page title: {title}")
        await browser.close()

asyncio.run(main())
'''

task_id = f"pw-test-{time.strftime('%H%M%S')}"
body = json.dumps({"script": script, "task_id": task_id}).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:9242/run-playwright",
    data=body,
    headers={"Content-Type": "application/json"},
    method="POST"
)

print(f"task_id: {task_id}")
print("执行 Playwright 脚本...")
start = time.time()
try:
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read().decode())
        elapsed = time.time() - start
        d = result.get("data", {})
        print(f"success: {result.get('success')}")
        print(f"elapsed: {d.get('elapsed_ms')}ms (total: {elapsed:.1f}s)")
        print(f"stdout: {d.get('stdout','')[:200]}")
        if not result.get('success'):
            print(f"error: {d.get('error','')[:300]}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:200]}")
except Exception as e:
    print(f"ERR: {e}")
