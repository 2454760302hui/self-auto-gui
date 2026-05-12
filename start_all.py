"""Unified startup script for all NextAgent services.

This script starts:
  1. Main AutoGLM-GUI backend (port 8000) — mobile device control + frontend
  2. Browser Automation service (port 9242) — browser-use
  3. API Interface Testing service (port 9243) — httprunner
  4. Security Testing service (port 9244) — Xray + Rad

Usage:
  python start_all.py
  python start_all.py --no-browser    # Don't auto-open browser
  python start_all.py --port 8000     # Custom main port
  python start_all.py --host 0.0.0.0  # Bind to all interfaces
"""

import argparse
import multiprocessing
import os
import sys
import time
import webbrowser


def start_main_server(host: str, port: int, no_browser: bool, log_level: str, log_file: str | None, no_log_file: bool):
    """Start the main FastAPI server."""
    os.environ["AUTOGLM_SERVER_HOST"] = host
    os.environ["AUTOGLM_LOG_LEVEL"] = log_level
    if no_log_file:
        os.environ["AUTOGLM_NO_LOG_FILE"] = "1"
    else:
        os.environ["AUTOGLM_LOG_FILE"] = log_file or "logs/autoglm_{time:YYYY-MM-DD}.log"

    import uvicorn
    from AutoGLM_GUI.api import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level=log_level.lower())


def start_browser_service(host: str, port: int = 9242):
    """Start the browser automation service."""
    from AutoGLM_GUI.api.browser_service import app_browser
    import uvicorn
    uvicorn.run(app_browser, host=host, port=port, log_level="info", access_log=None)


def start_interface_service(host: str, port: int = 9243):
    """Start the API interface testing service."""
    from AutoGLM_GUI.api.interface_service import app_interface
    import uvicorn
    uvicorn.run(app_interface, host=host, port=port, log_level="info", access_log=None)


def start_security_service(host: str, port: int = 9244):
    """Start the security testing service."""
    from AutoGLM_GUI.api.security_service import app_security
    import uvicorn
    uvicorn.run(app_security, host=host, port=port, log_level="info", access_log=None)


def open_browser_window(host: str, port: int, delay: float = 2.0):
    """Open the browser after a delay."""
    time.sleep(delay)
    url = f"http://{host}:{port}"
    try:
        webbrowser.open(url)
    except Exception:
        print(f"Could not open browser. Please visit: {url}")


def find_available_port(start_port: int, host: str = "127.0.0.1") -> int:
    """Find an available port starting from start_port."""
    import socket
    for port in range(start_port, start_port + 100):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((host, port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No available port found in range {start_port}-{start_port + 99}")


def main():
    parser = argparse.ArgumentParser(description="NextAgent AI Automation Platform - All Services")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=None, help="Main server port (default: auto)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Log level (default: INFO)")
    parser.add_argument("--log-file", default="logs/autoglm_{time:YYYY-MM-DD}.log",
                        help="Log file path")
    parser.add_argument("--no-log-file", action="store_true", help="Disable file logging")
    parser.add_argument("--services-only", action="store_true",
                        help="Start only the three module services (no main app)")
    args = parser.parse_args()

    host = args.host
    main_port = args.port if args.port is not None else 9527

    # Fixed ports for module services
    browser_port = 9242
    interface_port = 9243
    security_port = 9244

    print()
    print("=" * 60)
    print("  NextAgent AI Automation Platform")
    print("=" * 60)
    print()
    print(f"  Main Server:   http://{host}:{main_port}")
    if not args.services_only:
        print(f"  Browser API:    http://{host}:{browser_port}")
        print(f"  Interface API:  http://{host}:{interface_port}")
        print(f"  Security API:   http://{host}:{security_port}")
    print()
    print(f"  Log Level:      {args.log_level}")
    print(f"  Log File:      ", end="")
    if args.no_log_file:
        print("disabled")
    else:
        print(args.log_file)
    print()
    print("=" * 60)
    print()

    ctx = multiprocessing.get_context("spawn")

    # Start module services
    print("[1/3] Starting Browser Automation Service (port 9242)...")
    p_browser = ctx.Process(target=start_browser_service, args=(host, browser_port), daemon=True)
    p_browser.start()

    print("[2/3] Starting API Interface Testing Service (port 9243)...")
    p_interface = ctx.Process(target=start_interface_service, args=(host, interface_port), daemon=True)
    p_interface.start()

    print("[3/3] Starting Security Testing Service (port 9244)...")
    p_security = ctx.Process(target=start_security_service, args=(host, security_port), daemon=True)
    p_security.start()

    time.sleep(1)
    print()

    if not args.services_only:
        # Start main server
        print(f"[4/4] Starting Main Server (port {main_port})...")
        p_main = ctx.Process(
            target=start_main_server,
            args=(host, main_port, args.no_browser, args.log_level, args.log_file, args.no_log_file),
        )
        p_main.start()

        # Open browser
        if not args.no_browser:
            browser_thread = ctx.Process(
                target=open_browser_window,
                args=(host, main_port, 2.0),
            )
            browser_thread.start()
    else:
        print("Services started. Press Ctrl+C to stop all.")
        print()

    try:
        # Wait for all processes
        while True:
            alive = [p_browser.is_alive(), p_interface.is_alive(), p_security.is_alive()]
            if not args.services_only:
                alive.append(p_main.is_alive())

            if not any(alive):
                print("All processes have exited.")
                break

            time.sleep(2)
    except KeyboardInterrupt:
        print("\nShutting down...")
        for p in [p_browser, p_interface, p_security]:
            if not args.services_only:
                p_main.terminate()
            p.terminate()


if __name__ == "__main__":
    main()
