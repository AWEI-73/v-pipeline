"""vt_dashboard.py — dashboard(監控:state.json/serve/self-contained 產生器),
從 video_tools 解耦(= dashboard skill)。共用原語取自 vt_core。"""
import os
import sys
import json
import subprocess
from .vt_core import FFMPEG, FFPROBE, run, ToolError, _audio_duration  # noqa: F401

# ── dashboard: 監控介面 ──────────────────────────────────────────────────

def cmd_state(args):
    """掃 workdir → 產 state.json，給 dashboard.html 用"""
    workdir = args.workdir
    if not os.path.isdir(workdir):
        raise ToolError(f"workdir not found: {workdir}")

    from .dashboard_state import load_dashboard_state
    state = load_dashboard_state(workdir)

    import copy
    final_state = copy.deepcopy(state)
    final_state["dashboard"] = state

    out = args.out or os.path.join(workdir, "state.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(final_state, f, ensure_ascii=False, indent=2)

    nodes = state["nodes"]
    print(json.dumps({
        "status": "ok",
        "file": out,
        "project": state["run"]["project"],
        "done": sum(1 for n in nodes if n["status"] == "done"),
        "total": len(nodes),
    }, ensure_ascii=False))


def cmd_serve(args):
    """本地 HTTP server 服務 dashboard.html + workspace 檔案"""
    workdir = args.workdir
    port = args.port or 8765
    if not os.path.isdir(workdir):
        raise ToolError(f"workdir not found: {workdir}")

    # 複製 dashboard.html 到 workdir 根目錄（如沒有）
    dashboard_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
    dashboard_dst = os.path.join(workdir, "dashboard.html")
    if os.path.exists(dashboard_src) and not os.path.exists(dashboard_dst):
        import shutil
        shutil.copy(dashboard_src, dashboard_dst)

    # 複製 story_map.html 到 workdir 根目錄（如沒有）
    story_map_src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "story_map.html")
    story_map_dst = os.path.join(workdir, "story_map.html")
    if os.path.exists(story_map_src) and not os.path.exists(story_map_dst):
        import shutil
        shutil.copy(story_map_src, story_map_dst)

    # 首先更新一次 state.json
    args_state = type('A', (), {'workdir': workdir, 'project': None, 'out': None})()
    try:
        cmd_state(args_state)
    except SystemExit:
        pass  # state 失敗也照樣 serve

    print(json.dumps({
        "status": "starting",
        "url": f"http://localhost:{port}/dashboard.html",
        "workdir": os.path.abspath(workdir),
    }, ensure_ascii=False))

    import http.server
    import socketserver
    os.chdir(workdir)
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        print(f"Serving at http://localhost:{port}/dashboard.html (Ctrl+C to stop)",
              file=sys.stderr)
        httpd.serve_forever()


def cmd_dashboard(args):
    """產生 self-contained dashboard HTML（route state 內嵌）。
    免 server：直接用瀏覽器開檔（含 \\\\wsl.localhost\\... file://）即可看，不需 serve。
    auto-refresh 在內嵌模式關閉（靜態快照）；要即時刷新請改用 `serve`。"""
    workdir = args.workdir
    from .dashboard_state import load_dashboard_state
    state = load_dashboard_state(workdir)
    tmpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard.html")
    if not os.path.exists(tmpl):
        raise ToolError(f"找不到 dashboard 範本：{tmpl}")
    with open(tmpl, encoding="utf-8") as f:
        html = f.read()
    # 內嵌 state；跳脫 </script> 避免提早結束標籤
    blob = json.dumps(state, ensure_ascii=False).replace("</", "<\\/")
    inject = f"<script>window.__STATE__ = {blob};</script>\n"
    if "</head>" in html:
        html = html.replace("</head>", inject + "</head>", 1)
    else:
        html = inject + html
    out = args.out or os.path.join(workdir, "dashboard_view.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(json.dumps({"status": "ok", "file": out, "self_contained": True,
                      "next_action": state.get("next_action"),
                      "segments": len(state.get("segments", []))}, ensure_ascii=False))


def cmd_story_map(args):
    """產生 self-contained story map HTML（route state 內嵌）。
    免 server：直接用瀏覽器開檔即可看，不需 serve。"""
    workdir = args.workdir
    from .dashboard_state import load_dashboard_state
    state = load_dashboard_state(workdir)
    tmpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "story_map.html")
    if not os.path.exists(tmpl):
        raise ToolError(f"找不到 story_map 範本：{tmpl}")
    with open(tmpl, encoding="utf-8") as f:
        html = f.read()
    # 內嵌 state；跳脫 </script> 避免提早結束標籤
    blob = json.dumps(state, ensure_ascii=False).replace("</", "<\\/")
    inject = f"<script>window.__STATE__ = {blob};</script>\n"
    if "</head>" in html:
        html = html.replace("</head>", inject + "</head>", 1)
    else:
        html = inject + html
    out = args.out or os.path.join(workdir, "story_map_view.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(json.dumps({"status": "ok", "file": out, "self_contained": True,
                      "next_action": state.get("next_action"),
                      "segments": len(state.get("segments", []))}, ensure_ascii=False))
