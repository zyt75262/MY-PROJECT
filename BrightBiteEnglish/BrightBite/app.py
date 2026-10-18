#!/usr/bin/env python3
"""Run BrightBite independently: python app.py.

AI-assisted starter implementation, 2026-10-18. Review AUTHORS_AND_AI.md before
describing this project in an application or portfolio.
"""

import argparse
import logging
import sqlite3
import sys
import threading
import socket
import webbrowser
from pathlib import Path


def main() -> int:
    if sys.version_info < (3, 11):
        print("Please install Python 3.11 or newer.")
        return 1
    from community.server import build_server

    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="BrightBite standalone Python app")
    parser.add_argument("--port", type=int, default=8766, help="Local port, default: 8766")
    parser.add_argument("--no-browser", action="store_true", help="Do not open a browser automatically")
    parser.add_argument("--share", action="store_true", help="Allow other devices to connect to this computer")
    parser.add_argument("--public-host", help="HTTPS domain used by an optional reverse proxy")
    parser.add_argument("--data-dir", type=Path, default=root / "local_data", help="Directory for the local SQLite database")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535")
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    try:
        if args.public_host and not args.share:
            parser.error("--public-host requires --share")
        server = build_server(root, args.data_dir.resolve() / "community.sqlite3", args.port,
                              host="0.0.0.0" if args.share else "127.0.0.1",
                              public_host=args.public_host)
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"Cannot start: {error}")
        print("If the port is busy: python app.py --port 8776")
        return 1
    url = f"http://127.0.0.1:{server.server_port}"
    print("\nBrightBite")
    print("Keep this window open. Connected devices use the database on this computer.")
    print(f"Open in your browser: {url}")
    if args.share:
        print("Other devices on the same network can use these addresses (do not use 127.0.0.1 on your phone):")
        try:
            addresses = sorted({row[4][0] for row in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)
                                if not row[4][0].startswith("127.")})
        except OSError:
            addresses = []
        for address in addresses:
            print(f"  http://{address}:{server.server_port}/")
        if not addresses:
            print(f"  No address was detected. Run ipconfig to find the computer IPv4 address, then open http://COMPUTER_IP:{server.server_port}")
        print("If the page does not open, check the network and allow Python through the private-network firewall.")
        if args.public_host:
            url = f"https://{args.public_host}/"
            print(f"Shared HTTPS address: {url}")
    print("Stop with Ctrl+C.\n", flush=True)
    if not args.no_browser:
        timer = threading.Timer(0.7, webbrowser.open, args=(url,))
        timer.daemon = True
        timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your local records are saved.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
