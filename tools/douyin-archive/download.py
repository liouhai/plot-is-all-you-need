#!/usr/bin/env python3
"""下载单条抖音作品或一个主页的全部作品；不校准、不拆图。"""
import argparse
import asyncio
import csv
import json
import os
import plistlib
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHROME_INFO = Path("/Applications/Google Chrome.app/Contents/Info.plist")
CHROME_VERSION = plistlib.loads(CHROME_INFO.read_bytes())["CFBundleShortVersionString"] if CHROME_INFO.exists() else "154.0.0.0"
UA = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VERSION} Safari/537.36"


def save_json(path, value, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
    temporary.replace(path)
    if private:
        path.chmod(0o600)


def load_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_csv(path, rows, fields):
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def report(state, root):
    save_json(root / "state.json", state)
    rows = list(state["works"].values())
    write_csv(root / "manifest.csv", rows,
              ["id", "created", "title", "url", "kind", "download", "error"])
    write_csv(root / "report.csv", rows,
              ["id", "download", "extract", "images", "review", "error"])


def binary(name):
    found = shutil.which(name)
    if not found and Path("/opt/homebrew/bin", name).exists():
        found = str(Path("/opt/homebrew/bin", name))
    if not found:
        raise RuntimeError(f"缺少 {name}")
    return found


def run_ffmpeg(arguments):
    result = subprocess.run([binary("ffmpeg"), "-hide_banner", "-loglevel", "error",
                             "-nostdin", "-y", *map(str, arguments)],
                            capture_output=True, timeout=1800)
    if result.returncode:
        # FFmpeg errors can contain media URLs: do not echo them.
        raise RuntimeError("FFmpeg 处理失败")
    return result


def probe(path):
    result = subprocess.run([binary("ffprobe"), "-v", "error", "-show_streams",
                             "-show_format", "-of", "json", str(path)],
                            capture_output=True, timeout=60, check=True)
    info = json.loads(result.stdout)
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    return {"width": stream["width"], "height": stream["height"],
            "duration": float(info.get("format", {}).get("duration", 0))}


def validate_video(path):
    info = probe(path)
    if info["duration"] <= 0:
        raise RuntimeError("视频没有有效时长")
    run_ffmpeg(["-xerror", "-i", path, "-map", "0:v:0", "-f", "null", "-"])
    return info


def require_space(root, needed=0):
    if shutil.disk_usage(root).free < needed + 2 * 1024 ** 3:
        raise RuntimeError("磁盘空间不足：保留至少 2 GiB 余量，已完成文件已保存")


def chrome_cookie(browser, root):
    import browser_cookie3
    try:
        jar = getattr(browser_cookie3, browser)(domain_name=".douyin.com")
        cookies = {c.name: c.value for c in jar
                   if c.domain.lstrip(".") == "douyin.com" or c.domain.endswith(".douyin.com")}
    except Exception:
        raise RuntimeError(f"无法读取 {browser} 登录态；请检查钥匙串权限或在本机配置 secrets.json") from None
    if not cookies:
        raise RuntimeError("浏览器中没有抖音登录信息")
    value = "; ".join(f"{key}={value}" for key, value in cookies.items())
    save_json(root / "secrets.json", {"cookie": value}, private=True)
    print(f"已在本机保存 {browser} 登录态；未输出 Cookie")


def f2_client(root):
    # Prevent upstream log_setup from creating a file sink at import time.
    import logging
    logging.disable(logging.CRITICAL)
    logger = logging.getLogger("f2")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    from f2.apps.douyin.crawler import DouyinCrawler
    secret = load_json(root / "secrets.json", {})
    if not secret.get("cookie"):
        raise RuntimeError("缺少本机登录态，请先在浏览器登录抖音后重跑")
    kwargs = {"cookie": secret["cookie"], "headers": {"User-Agent": UA,
              "Referer": "https://www.douyin.com/"}, "timeout": 20,
              "max_retries": 2, "max_connections": 2}
    crawler = DouyinCrawler(kwargs)
    # F2's default transport disables TLS verification; use httpx's verified transport.
    import httpx
    async def audit_response(response):
        body = await response.aread()
        if response.status_code != 200 or not body.strip():
            print(f"接口 {response.request.url.path}：HTTP {response.status_code}，正文 {len(body)} 字节", flush=True)
        if response.status_code in (401, 403, 429):
            raise RuntimeError(f"接口返回 HTTP {response.status_code}，需要检查登录或验证，任务已暂停")
    crawler._aclient = httpx.AsyncClient(headers=crawler.headers, timeout=20,
                                        limits=httpx.Limits(max_connections=2),
                                        event_hooks={"response": [audit_response]})
    return crawler


def checked_response(data, key):
    if not isinstance(data, dict) or data.get("status_code") != 0 or key not in data:
        code = data.get("status_code") if isinstance(data, dict) else "empty"
        raise RuntimeError(f"抖音接口未返回有效数据（状态 {code}）；请检查登录或验证码")
    return data[key]


def add_work(state, item):
    ident = str(item["aweme_id"])
    if not ident.isdigit():
        raise RuntimeError("接口返回非法作品 ID")
    row = state["works"].setdefault(ident, {"id": ident, "download": "pending",
           "extract": "pending", "images": 0, "review": "", "error": ""})
    row.update(created=item.get("create_time", 0), title=item.get("desc", ""),
               url=f"https://www.douyin.com/video/{ident}",
               kind="gallery" if item.get("images") else "video")
    return row


async def enumerate_works(client, state, user_id, root):
    from f2.apps.douyin.model import UserPost
    cursor, seen, posts = 0, set(), {}
    state["listing_complete"] = False
    state["listing_user"] = user_id
    state["listed_ids"] = []
    while True:
        response = await client.fetch_user_post(UserPost(
            sec_user_id=user_id, max_cursor=cursor, count=20))
        items = checked_response(response, "aweme_list")
        if not isinstance(items, list) or "has_more" not in response:
            raise RuntimeError("主页分页数据不完整")
        if not items:
            raise RuntimeError("主页返回空列表，不能认定枚举成功")
        for item in items:
            if item.get("author", {}).get("sec_uid") != user_id:
                raise RuntimeError("作品作者与目标主页不一致")
            ident = add_work(state, item)["id"]
            posts[ident] = item
            if ident not in state["listed_ids"]:
                state["listed_ids"].append(ident)
        report(state, root)
        print(f"已枚举 {len(state['listed_ids'])} 条作品", flush=True)
        if not response["has_more"]:
            state["listing_complete"] = True
            report(state, root)
            return posts
        next_cursor = response.get("max_cursor")
        if not next_cursor or next_cursor == cursor or next_cursor in seen:
            raise RuntimeError("分页游标未前进，不能认定全量完成")
        seen.add(cursor)
        cursor = next_cursor
        await asyncio.sleep(1)


def media_sources(item, root):
    if item.get("images"):
        return [(root / "works" / str(item["aweme_id"]) / "originals" / f"{i:04d}.webp",
                 image.get("url_list", []) or image.get("download_url_list", []))
                for i, image in enumerate(item["images"], 1)]
    video = item.get("video", {})
    rates = sorted(video.get("bit_rate") or [], key=lambda x: x.get("bit_rate") or 0, reverse=True)
    addresses = [r.get("play_addr", {}) for r in rates] + [video.get("play_addr", {})]
    urls = list(dict.fromkeys(u for address in addresses for u in address.get("url_list", [])))
    return [(root / "works" / str(item["aweme_id"]) / "video.mp4", urls)]


def fetch_file(path, urls, root):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            validate_video(path) if path.suffix == ".mp4" else probe(path)
            return
        except Exception:
            path.replace(path.with_name(path.name + f".invalid-{time.time_ns()}"))
    part = path.with_name(path.name + ".part")
    for url in urls:
        if not url.startswith("https://"):
            continue
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": UA,
                                                 "Referer": "https://www.douyin.com/"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    length = int(response.headers.get("Content-Length", 0))
                    require_space(root, length)
                    count = 0
                    with part.open("wb") as f:
                        while chunk := response.read(1024 * 1024):
                            require_space(root, len(chunk))
                            f.write(chunk)
                            count += len(chunk)
                if not count or (length and count != length):
                    raise RuntimeError("媒体下载不完整")
                validate_video(part) if path.suffix == ".mp4" else probe(part)
                part.replace(path)
                return
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 429):
                    raise RuntimeError(f"媒体接口返回 HTTP {e.code}，任务已暂停，请检查登录或限流") from None
            except RuntimeError as e:
                if "空间" in str(e) or "接口" in str(e):
                    raise
            except Exception:
                pass
            time.sleep(attempt + 1)
    raise RuntimeError("媒体地址全部下载失败；保留未完成状态")


async def download_works(state, ids, posts, root, expected_author=None):
    semaphore = asyncio.Semaphore(2)

    async def one(ident):
        if ident in state.get("skipped_ids", []):
            return
        async with semaphore:
            row = state["works"].get(ident)
            try:
                previous = load_json(root / "works" / ident / "source.json", {})
                stamps = previous.get("stamps", {})
                if row and row["download"] == "complete" and stamps and all(
                    (root / relative).exists() and
                    [(root / relative).stat().st_size, (root / relative).stat().st_mtime_ns] == stamp
                    for relative, stamp in stamps.items()
                ):
                    return
                item = (posts or {}).get(ident)
                if item is None:
                    raise RuntimeError("作品详情缺失，请重新运行下载以刷新媒体地址")
                if not item or str(item.get("aweme_id")) != ident:
                    raise RuntimeError("作品详情不完整")
                if expected_author and item.get("author", {}).get("sec_uid") != expected_author:
                    raise RuntimeError("作品作者与目标主页不一致")
                row = add_work(state, item)
                sources = media_sources(item, root)
                if not sources or any(not urls for _, urls in sources):
                    raise RuntimeError("作品没有可用媒体地址")
                for path, urls in sources:
                    await asyncio.to_thread(fetch_file, path, urls, root)
                save_json(root / "works" / ident / "source.json",
                          {"id": ident, "kind": row["kind"], "files": [str(p.relative_to(root)) for p, _ in sources],
                           "stamps": {str(p.relative_to(root)): [p.stat().st_size, p.stat().st_mtime_ns] for p, _ in sources}})
                row.update(download="complete", error="")
                print(f"下载验证成功：{ident}", flush=True)
            except Exception as e:
                if row:
                    row.update(download="failed", error=safe_error(e))
                if isinstance(e, RuntimeError) and ("接口" in str(e) or "空间" in str(e)):
                    raise
                if type(e).__name__ in ("APIUnauthorizedError", "APIRateLimitError", "APIRetryExhaustedError"):
                    raise RuntimeError("接口验证或限流失败，任务已暂停，请检查浏览器登录状态") from None
                print(f"下载失败：{ident}（{type(e).__name__}）", flush=True)
            finally:
                report(state, root)

    tasks = [asyncio.create_task(one(ident)) for ident in ids]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def safe_error(error):
    if isinstance(error, RuntimeError) and not re.search(r"https?://|cookie|token", str(error), re.I):
        return str(error)
    return type(error).__name__ + "：详情已隐藏以保护登录信息"


def target_id(url, kind):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc not in ("www.douyin.com", "douyin.com"):
        raise RuntimeError("请提供 https://www.douyin.com 的完整作品或主页链接")
    if kind == "video":
        match = re.fullmatch(r"/(?:video|note)/([0-9]+)/?", parsed.path)
        modal = urllib.parse.parse_qs(parsed.query).get("modal_id", [])
        ident = match[1] if match else modal[0] if len(modal) == 1 else ""
        if re.fullmatch(r"[0-9]+", ident):
            return ident
        raise RuntimeError("--video 需要作品链接，或带 modal_id 的抖音链接")
    match = re.fullmatch(r"/user/([A-Za-z0-9_-]{20,})/?", parsed.path)
    if not match:
        raise RuntimeError("--user 需要完整的抖音主页链接")
    return match[1]


async def download(state, root, video_id=None, user_id=None):
    async with f2_client(root) as client:
        if video_id:
            from f2.apps.douyin.model import PostDetail
            response = await client.fetch_post_detail(PostDetail(aweme_id=video_id))
            item = checked_response(response, "aweme_detail")
            if not isinstance(item, dict) or str(item.get("aweme_id")) != video_id:
                raise RuntimeError("作品详情与目标作品不一致")
            add_work(state, item)
            posts = {video_id: item}
            ids = [video_id]
        else:
            posts = await enumerate_works(client, state, user_id, root)
            ids = state["listed_ids"]
        report(state, root)
        await download_works(state, ids, posts, root, expected_author=user_id)
        failed = sum(state["works"][ident]["download"] != "complete"
                     for ident in ids if ident not in state.get("skipped_ids", []))
        if failed:
            raise RuntimeError(f"仍有 {failed} 条作品未下载成功，详情见 report.csv")
        state.pop("last_error", None)
        report(state, root)
        completed = sum(state["works"][ident]["download"] == "complete" for ident in ids)
        print(f"本次目标 {len(ids)} 条，已完成 {completed} 条；保存到 {root}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--video", help="单条作品完整链接，也支持链接中的 modal_id")
    target.add_argument("--user", help="主页完整链接，下载该主页的全部作品")
    parser.add_argument("--output", type=Path, default=Path("douyin_archive"),
                        help="输出目录，默认当前目录下的 douyin_archive/")
    parser.add_argument("--browser", choices=["chrome", "safari"], default="chrome",
                        help="首次读取登录态的浏览器，默认 chrome")
    args = parser.parse_args(argv)
    root = args.output.expanduser().resolve()
    state = None
    try:
        ident = target_id(args.video or args.user, "video" if args.video else "user")
        root.mkdir(parents=True, exist_ok=True)
        state = load_json(root / "state.json", {"works": {}})
        binary("ffmpeg")
        binary("ffprobe")
        require_space(root)
        if not load_json(root / "secrets.json", {}).get("cookie"):
            chrome_cookie(args.browser, root)
        else:
            (root / "secrets.json").chmod(0o600)
        asyncio.run(download(state, root, video_id=ident if args.video else None,
                             user_id=ident if args.user else None))
        return 0
    except KeyboardInterrupt:
        if state is not None:
            report(state, root)
        print("已中断，下载文件及进度已保留", flush=True)
        return 130
    except Exception as error:
        message = safe_error(error)
        if state is not None:
            state["last_error"] = message
            report(state, root)
        print("停止：" + message, flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
