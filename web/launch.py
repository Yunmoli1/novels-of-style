# -*- coding: utf-8 -*-
"""launch：工作台入口——双击即可运行，不需要手动命令行。

用法：
    python web/launch.py [--port N] [--site DIR] [--no-build] [--no-open]
                         [--build-only] [--static-only]

行为：
- 首次运行自动安装 Web 依赖（fastapi/uvicorn/httpx/jinja2，requirements-web.txt）
- 构建/复用站点 → 默认**全模式**：FastAPI（/app 配置与创作环）+ 静态站点同源
  挂载，仅绑 127.0.0.1（红线 1），自动打开浏览器 → Ctrl+C 退出
- --static-only：退回阶段 0 纯静态服务（无 /app，依赖缺失时的兜底）
- Windows 下双击仓库根的 启动工作台.bat 即可
"""
from __future__ import annotations

import argparse
import functools
import http.server
import socket
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = Path(__file__).resolve().parent
sys.path.insert(0, str(WEB))
sys.path.insert(0, str(ROOT / "scripts"))
import splib  # noqa: E402
import build_site  # noqa: E402


def random_fallback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


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


def deps_ready() -> bool:
    try:
        import fastapi  # noqa
        import httpx  # noqa
        import jinja2  # noqa
        import uvicorn  # noqa
        return True
    except ImportError:
        return False


def ensure_deps() -> bool:
    if deps_ready():
        return True
    print("首次运行：安装工作台依赖（fastapi / uvicorn / httpx / jinja2）……")
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "-r", str(WEB / "requirements-web.txt")])
    if r.returncode == 0 and deps_ready():
        print("依赖安装完成 ✓")
        return True
    print("依赖自动安装失败——本次以纯静态模式启动（判读/浏览可用，无创作环）。"
          "可手动执行：pip install -r web/requirements-web.txt")
    return False


def serve_static(site: Path, port: int) -> None:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(site))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    print(f"静态站点已启动：http://127.0.0.1:{port}/（纯静态模式）")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
    finally:
        httpd.server_close()


def main() -> int:
    splib.force_utf8_stdio()
    ap = argparse.ArgumentParser(description="StylePack 工作台入口（本地）")
    ap.add_argument("--port", type=int, default=0, help="端口，默认自动挑选（首选 8765）")
    ap.add_argument("--site", default=str(ROOT / "web" / "site"),
                    help="站点目录（默认 web/site）")
    ap.add_argument("--no-build", action="store_true", help="跳过构建，直接用现有 site/")
    ap.add_argument("--no-open", action="store_true", help="不自动开浏览器")
    ap.add_argument("--build-only", action="store_true", help="只构建站点后退出")
    ap.add_argument("--static-only", action="store_true", help="纯静态模式（无创作环）")
    args = ap.parse_args()

    site = Path(args.site)
    if not args.no_build or not (site / "index.html").is_file():
        print("正在构建站点……")
        build_site.build(site)
    if args.build_only:
        print("构建完成（--build-only，不启动服务）。")
        return 0

    port = args.port or preferred_port()
    url = f"http://127.0.0.1:{port}/"
    full_mode = (not args.static_only) and ensure_deps()
    if full_mode:
        from server import create_app
        app = create_app(site_dir=site)
        try:
            import appstate
            ver = appstate.workbench_version()
        except Exception:
            ver = "?"
        print(f"StylePack 工作台 v{ver} 已启动：{url}")
        print(f"（若浏览器没自动打开，手动访问该地址；端口被占用时会自动顺延，"
              f"以本行显示为准——页脚也标了版本，两处对不上=旧实例没关干净）")
        print("全模式：判读/浏览/canon + 模型配置 + 创作环。"
              "仅监听本机（127.0.0.1），数据不出机器；按 Ctrl+C 停止。")
        if not args.no_open:
            threading.Timer(0.8, webbrowser.open, (url,)).start()
        try:
            import uvicorn
            uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
        except KeyboardInterrupt:
            print("\n已停止。")
    else:
        if not args.no_open:
            threading.Timer(0.6, webbrowser.open, (url,)).start()
        serve_static(site, port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
