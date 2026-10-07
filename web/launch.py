# -*- coding: utf-8 -*-
"""launch：工作台入口——双击即可运行，不需要手动命令行（r4 阶段 0，用户追加要求）。

用法：
    python web/launch.py [--port N] [--no-build] [--no-open] [--build-only]

行为：构建/复用站点 → http.server 绑 127.0.0.1（红线 1，永不绑 0.0.0.0）→
自动打开默认浏览器 → Ctrl+C 退出。Windows 下双击仓库根的 启动工作台.bat 即可。
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(ROOT / "scripts"))
import splib  # noqa: E402
import build_site  # noqa: E402


def preferred_port() -> int:
    """固定首选端口（8765 起）：localStorage 按 origin（含端口）隔离，
    端口稳定才能让判读进度跨重启续存；被占用则顺延，最后才随机。"""
    for p in range(8765, 8780):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return random_fallback_port()


def random_fallback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="StylePack 工作台入口（本地）")
    ap.add_argument("--port", type=int, default=0, help="端口，默认自动挑选")
    ap.add_argument("--site", default=str(ROOT / "web" / "site"),
                    help="站点目录（默认 web/site）")
    ap.add_argument("--no-build", action="store_true", help="跳过构建，直接用现有 site/")
    ap.add_argument("--no-open", action="store_true", help="不自动开浏览器")
    ap.add_argument("--build-only", action="store_true", help="只构建站点后退出")
    args = ap.parse_args()

    site = Path(args.site)
    if not args.no_build or not (site / "index.html").is_file():
        print("正在构建站点……")
        build_site.build(site)
    if args.build_only:
        print("构建完成（--build-only，不启动服务）。")
        return 0

    port = args.port or preferred_port()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(site))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"StylePack 工作台已启动：{url}")
    print("本服务只监听本机（127.0.0.1），数据不出机器；按 Ctrl+C 停止。")
    if not args.no_open:
        threading.Timer(0.6, webbrowser.open, (url,)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
