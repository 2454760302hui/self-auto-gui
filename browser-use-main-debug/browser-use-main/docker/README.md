# Docker Setup for Browser-Use

This directory contains the optimized Docker build system for browser-use, achieving < 30 second builds.

## Quick Start

```bash
# Build base images (only needed once or when dependencies change)
./docker/build-base-images.sh

# Build browser-use (recommended)
docker build -f Dockerfile.fast -t browseruse .

# Start the HTTP service
# Then open http://127.0.0.1:9242/ in your browser to use the web console.
docker run --rm -p 9242:9242 browseruse

# Health check
curl http://127.0.0.1:9242/health

# Connect a browser session
curl -X POST http://127.0.0.1:9242/connect

# Open a page
curl -X POST http://127.0.0.1:9242/open -H 'content-type: application/json' -d '{"url":"https://example.com"}'

# Inspect state
curl http://127.0.0.1:9242/state

# Basic runtime checks (CLI still available by overriding the default command)
docker run --rm browseruse doctor
docker run --rm --entrypoint python browseruse -c "import browser_use; print('import ok')"

# Verified BrowserSession smoke test
docker run --rm --entrypoint bash browseruse -lc "/app/.venv/bin/python - <<'PY'
import asyncio
from browser_use import BrowserSession

async def main():
    browser = BrowserSession(headless=True)
    try:
        await browser.start()
        page = await browser.get_current_page()
        await page.goto('data:text/html,<title>ok</title><h1>Hello</h1>')
        state = await browser.get_browser_state_summary()
        print(state.tabs[0].url)
        print(state.tabs[0].title)
    finally:
        await browser.stop()

asyncio.run(main())
PY"

# Or use the standard Dockerfile (slower and depends on external Debian chromium downloads)
docker build -t browseruse .
```

## Web Console

Open `http://127.0.0.1:9242/` after starting the container.

The root page now provides a lightweight browser-use control console with:
- service health check
- browser connect and close actions
- URL open action
- current state inspection
- typing into the focused element
- clicking by element index or x/y coordinates
- response and activity log panels in the page
- browser target selection: visible Chrome via CDP, visible Chrome profile, or Docker virtual browser

### Real visible browser vs Docker virtual browser

Important:
- `Docker virtual browser` runs inside the container's Xvfb display. It is useful for automation fallback, but it does **not** open a browser window you can see on the host.
- To make `Open URL` open a **real visible browser**, use one of these modes in the web console before clicking Connect:
  - `Visible Chrome via CDP` (recommended)
  - `Visible Chrome profile`
- The web console now blocks `Open URL` when the current target is only the Docker virtual browser.

### Recommended: Visible Chrome via CDP

This is the primary Docker workflow.

1. Start Chrome on the host with remote debugging enabled.
2. Open the Docker web console at `http://127.0.0.1:9242/`.
3. Select `Visible Chrome via CDP`.
4. Prefer entering a container-reachable CDP URL manually, such as `http://host.docker.internal:9222`.
5. Click Connect, then click Open URL.

Important notes for Docker:
- Auto-discovery works best when Chrome is reachable from the same environment as the HTTP service.
- Inside Docker, `127.0.0.1` is the container itself, not the Windows host.
- If auto-discovery fails, do not switch to virtual mode if you need a real visible browser. Start host Chrome with remote debugging and enter a reachable host CDP URL.

Example Chrome launch on the Windows host:

```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

### Alternative: Visible Chrome profile

If CDP is not available:
1. Select `Visible Chrome profile`.
2. Enter a Chrome profile such as `Default`.
3. Click Connect, then click Open URL.

This starts a real system Chrome profile instead of the container-only virtual browser.

Notes:
- `Dockerfile.fast` is the validated path for reliable startup and browser automation in this environment.
- Docker now starts an HTTP service by default on `http://127.0.0.1:9242` when you publish port 9242.
- The exposed URL is the browser-use control service, not the visited webpage itself.
- The standard `Dockerfile` can still fail if the Debian mirror cannot download `chromium` during build.
- Docker images now set `IN_DOCKER=True` and disable default browser extensions by default for more stable container startup.

## Files

- `Dockerfile` - Standard self-contained build (~2 min)
- `Dockerfile.fast` - Fast build using pre-built base images (~30 sec)
- `docker/` - Base image definitions and build script
  - `base-images/system/` - Python + minimal system deps
  - `base-images/chromium/` - Adds Chromium browser
  - `base-images/python-deps/` - Adds Python dependencies
  - `build-base-images.sh` - Script to build all base images

## Performance

| Build Type | Time |
|------------|------|
| Standard Dockerfile | ~2 minutes |
| Fast build (with base images) | ~30 seconds |
| Rebuild after code change | ~16 seconds |
