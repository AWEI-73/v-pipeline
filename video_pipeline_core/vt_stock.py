"""vt_stock.py — 素材來源:Pexels stock(服務 curator/素材腿),從 video_tools 解耦。"""
import os
import sys
import json
from .vt_core import ToolError  # noqa: F401

# ── Pexels API（小編擴充：另一個免費素材來源）────────────────────────────

def _pexels_request(endpoint: str, params: dict) -> dict:
    """呼叫 Pexels API，回 JSON"""
    api_key = os.environ.get('PEXELS_API_KEY')
    if not api_key:
        raise ToolError("環境變數 PEXELS_API_KEY 未設定。註冊免費 key：https://www.pexels.com/api/")
    import urllib.request
    import urllib.parse
    qs = urllib.parse.urlencode(params)
    url = f"https://api.pexels.com{endpoint}?{qs}"
    # 加 User-Agent：urllib 預設的 Python-urllib/x.x 會被 Pexels 擋
    req = urllib.request.Request(url, headers={
        "Authorization": api_key,
        "User-Agent": "video_director/1.0 (curator skill)",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        raise ToolError(f"Pexels API failed: {str(e)[:300]}")


def _pexels_video_candidates(query, limit=10):
    """Return normalized Pexels video candidates."""
    has_cjk = any('一' <= ch <= '鿿' for ch in (query or ""))
    params = {"query": query, "per_page": limit, "orientation": "landscape"}
    if has_cjk:
        params["locale"] = "zh-TW"
    data = _pexels_request("/videos/search", params)
    candidates = []
    for v in data.get("videos", []):
        files = sorted(v.get("video_files", []), key=lambda x: -(x.get("width") or 0))
        best = next((f for f in files if f.get("file_type", "").startswith("video/mp4")
                     and (f.get("width") or 0) <= 1920), files[0] if files else None)
        if not best:
            continue
        candidates.append({
            "provider": "pexels",
            "download_url": best.get("link"),
            "duration": v.get("duration") or 0,
            "width": best.get("width"),
            "height": best.get("height"),
            "url": v.get("url"),
            "thumbnail_url": v.get("image"),
        })
    return candidates


def _pixabay_video_candidates(query, limit=10):
    """Return normalized Pixabay video candidates. Missing API key means no candidates."""
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        return []
    import urllib.request
    import urllib.parse
    q = urllib.parse.quote(query or "")
    per_page = min(max(limit, 3), 50)
    url = f"https://pixabay.com/api/videos/?key={key}&q={q}&per_page={per_page}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return []
    candidates = []
    for h in data.get("hits", []):
        vids = h.get("videos", {})
        v = vids.get("medium") or vids.get("large") or vids.get("small") or vids.get("tiny") or {}
        if not v.get("url"):
            continue
        candidates.append({
            "provider": "pixabay",
            "download_url": v.get("url"),
            "duration": h.get("duration") or 0,
            "width": v.get("width"),
            "height": v.get("height"),
            "url": h.get("pageURL"),
            "thumbnail_url": v.get("thumbnail"),
        })
    return candidates


def _download_url(url, out_path):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "video_director/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(out_path, "wb") as f:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            f.write(chunk)
    return True


def fetch_stock_video_with_provider(query, out_path, min_dur=0, providers=None):
    """(I/O) Stock video search/download → (out_path, provider).
    Default provider order is Pexels then Pixabay. Missing/failing providers are
    skipped so mv_cut can treat stock failure as a recoverable GAP."""
    providers = providers or ("pexels", "pixabay")
    searchers = {
        "pexels": _pexels_video_candidates,
        "pixabay": _pixabay_video_candidates,
    }
    for provider in providers:
        search = searchers.get(provider)
        if not search:
            continue
        try:
            candidates = search(query)
        except Exception:
            continue
        for cand in sorted(candidates, key=lambda c: -(c.get("duration") or 0)):
            if min_dur and (cand.get("duration") or 0) < min_dur:
                continue
            if not cand.get("download_url"):
                continue
            try:
                if _download_url(cand["download_url"], out_path):
                    return out_path, provider
            except Exception:
                continue
    return None, None


def fetch_stock_video(query, out_path, min_dur=0, providers=None):
    """(I/O) Stock video search/download → out_path.
    Default provider order is Pexels then Pixabay. Missing/failing providers are
    skipped so mv_cut can treat stock failure as a recoverable GAP."""
    path, _ = fetch_stock_video_with_provider(query, out_path, min_dur=min_dur, providers=providers)
    return path


def cmd_pexels_search(args):
    """搜 Pexels 照片或影片"""
    media_type = args.type
    if media_type not in ('photo', 'video'):
        raise ToolError("--type 必須是 photo 或 video")

    limit = args.limit or 10
    endpoint = "/v1/search" if media_type == 'photo' else "/videos/search"
    # 自動偵測中文 query → 加 zh-TW locale 拿在地化結果
    import unicodedata
    has_cjk = any(unicodedata.category(ch).startswith('Lo') and '一' <= ch <= '鿿' for ch in args.query)
    params = {
        "query": args.query,
        "per_page": limit,
        "orientation": "landscape",
    }
    if has_cjk:
        params["locale"] = "zh-TW"
    data = _pexels_request(endpoint, params)

    # 標準化輸出
    candidates = []
    if media_type == 'photo':
        for p in data.get('photos', []):
            candidates.append({
                "id": p['id'],
                "source": "pexels-photo",
                "url": p['url'],
                "download_url": p['src']['large2x'],
                "photographer": p.get('photographer'),
                "width": p.get('width'),
                "height": p.get('height'),
                "alt": p.get('alt', ''),
            })
    else:
        for v in data.get('videos', []):
            # 取最高品質 mp4
            files = sorted(v.get('video_files', []),
                           key=lambda x: -(x.get('width') or 0))
            best = next((f for f in files if f.get('file_type', '').startswith('video/mp4')
                         and f.get('width', 0) <= 1920), files[0] if files else None)
            if not best: continue
            candidates.append({
                "id": v['id'],
                "source": "pexels-video",
                "url": v['url'],
                "download_url": best['link'],
                "thumbnail_url": v.get('image'),  # 影片預覽圖
                "duration": v.get('duration'),
                "width": best.get('width'),
                "height": best.get('height'),
                "user": v.get('user', {}).get('name'),
            })

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "query": args.query,
        "type": media_type,
        "count": len(candidates),
        "candidates": candidates,
    }, ensure_ascii=False))


def cmd_pexels_download(args):
    """下載 Pexels 直連 URL（從 pexels-search 結果的 download_url）"""
    import urllib.request
    url = args.url
    out = args.out or os.path.basename(url.split('?')[0])
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "video_director/1.0 (curator skill)",
        })
        with urllib.request.urlopen(req, timeout=120) as resp:
            with open(out, 'wb') as f:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk: break
                    f.write(chunk)
        size = os.path.getsize(out)
        print(json.dumps({
            "status": "ok",
            "file": out,
            "size_bytes": size,
        }, ensure_ascii=False))
    except Exception as e:
        raise ToolError(f"download failed: {str(e)[:300]}")
