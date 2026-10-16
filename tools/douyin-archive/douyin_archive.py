#!/usr/bin/env python3
"""Archive one Douyin homepage you are allowed to archive, and split flash-slideshow videos into still frames.

Credentials never appear in manifests or logs. See README.md for the workflow and its limits.
"""
import argparse
import bisect
import asyncio
import csv
import json
import math
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "douyin_archive"
CHROME_INFO = Path("/Applications/Google Chrome.app/Contents/Info.plist")
CHROME_VERSION = plistlib.loads(CHROME_INFO.read_bytes())["CFBundleShortVersionString"] if CHROME_INFO.exists() else "154.0.0.0"
UA = f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{CHROME_VERSION} Safari/537.36"
THRESHOLDS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3)


def sec_uid(text):
    """The homepage id from a URL like https://www.douyin.com/user/<id>, or from the bare id."""
    match = re.search(r"/user/([A-Za-z0-9_-]+)", text)
    ident = match[1] if match else text.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,}", ident):
        raise RuntimeError("无法从 --user 识别主页 ID，请粘贴完整的主页链接")
    return ident


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


def report(state):
    save_json(ROOT / "state.json", state)
    rows = list(state["works"].values())
    write_csv(ROOT / "manifest.csv", rows,
              ["id", "created", "title", "url", "kind", "download", "error"])
    write_csv(ROOT / "report.csv", rows,
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


def require_space(needed=0):
    if shutil.disk_usage(ROOT).free < needed + 2 * 1024 ** 3:
        raise RuntimeError("磁盘空间不足：保留至少 2 GiB 余量，已完成文件已保存")


def chrome_cookie(browser):
    import browser_cookie3
    try:
        jar = getattr(browser_cookie3, browser)(domain_name=".douyin.com")
        cookies = {c.name: c.value for c in jar
                   if c.domain.lstrip(".") == "douyin.com" or c.domain.endswith(".douyin.com")}
    except Exception as error:
        raise RuntimeError(f"无法读取 {browser} 登录态；请检查钥匙串权限或在本机配置 secrets.json") from None
    if not cookies:
        raise RuntimeError("浏览器中没有抖音登录信息")
    value = "; ".join(f"{key}={value}" for key, value in cookies.items())
    save_json(ROOT / "secrets.json", {"cookie": value}, private=True)
    print(f"已在本机保存 {browser} 登录态；未输出 Cookie")


def f2_client():
    # Prevent upstream log_setup from creating a file sink at import time.
    import logging
    logging.disable(logging.CRITICAL)
    logger = logging.getLogger("f2")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    from f2.apps.douyin.crawler import DouyinCrawler
    secret = load_json(ROOT / "secrets.json", {})
    if not secret.get("cookie"):
        raise RuntimeError("缺少本机登录态，请先运行 cookies")
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


async def enumerate_works(client, state):
    from f2.apps.douyin.model import UserPost
    cursor, seen, posts = 0, set(), {}
    state["listing_complete"] = False
    state["listed_ids"] = []
    while True:
        response = await client.fetch_user_post(UserPost(
            sec_user_id=state["sec_user_id"], max_cursor=cursor, count=20))
        items = checked_response(response, "aweme_list")
        if not isinstance(items, list) or "has_more" not in response:
            raise RuntimeError("主页分页数据不完整")
        for item in items:
            ident = add_work(state, item)["id"]
            posts[ident] = item
            if ident not in state["listed_ids"]:
                state["listed_ids"].append(ident)
        report(state)
        print(f"已枚举 {len(state['works'])} 条作品", flush=True)
        if not response["has_more"]:
            if not state["listed_ids"]:
                raise RuntimeError("主页返回空列表，不能认定枚举成功")
            state["listing_complete"] = True
            report(state)
            return posts
        next_cursor = response.get("max_cursor")
        if not next_cursor or next_cursor == cursor or next_cursor in seen:
            raise RuntimeError("分页游标未前进，不能认定全量完成")
        seen.add(cursor)
        cursor = next_cursor
        await asyncio.sleep(1)


def media_sources(item):
    if item.get("images"):
        return [(ROOT / "works" / str(item["aweme_id"]) / "originals" / f"{i:04d}.webp",
                 image.get("url_list", []) or image.get("download_url_list", []))
                for i, image in enumerate(item["images"], 1)]
    video = item.get("video", {})
    rates = sorted(video.get("bit_rate") or [], key=lambda x: x.get("bit_rate") or 0, reverse=True)
    addresses = [r.get("play_addr", {}) for r in rates] + [video.get("play_addr", {})]
    urls = list(dict.fromkeys(u for address in addresses for u in address.get("url_list", [])))
    return [(ROOT / "works" / str(item["aweme_id"]) / "video.mp4", urls)]


def fetch_file(path, urls):
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
                    require_space(length)
                    count = 0
                    with part.open("wb") as f:
                        while chunk := response.read(1024 * 1024):
                            require_space(len(chunk))
                            f.write(chunk)
                            count += len(chunk)
                if not count or (length and count != length):
                    raise RuntimeError("媒体下载不完整")
                validate_video(part) if path.suffix == ".mp4" else probe(part)
                part.replace(path)
                return
            except RuntimeError as e:
                if "空间" in str(e):
                    raise
            except Exception:
                pass
            time.sleep(attempt + 1)
    raise RuntimeError("媒体地址全部下载失败；保留未完成状态")


async def download_works(client, state, ids, posts=None):
    semaphore = asyncio.Semaphore(2)

    async def one(ident):
        if ident in state.get("skipped_ids", []):
            return
        async with semaphore:
            row = state["works"].get(ident)
            try:
                previous = load_json(ROOT / "works" / ident / "source.json", {})
                stamps = previous.get("stamps", {})
                if row and row["download"] == "complete" and stamps and all(
                    (ROOT / relative).exists() and
                    [(ROOT / relative).stat().st_size, (ROOT / relative).stat().st_mtime_ns] == stamp
                    for relative, stamp in stamps.items()
                ):
                    return
                item = (posts or {}).get(ident)
                if item is None:
                    from f2.apps.douyin.model import PostDetail
                    response = await client.fetch_post_detail(PostDetail(aweme_id=ident))
                    item = checked_response(response, "aweme_detail")
                if not item or str(item.get("aweme_id")) != ident:
                    raise RuntimeError("作品详情不完整")
                if item.get("author", {}).get("sec_uid") != state.get("sec_user_id"):
                    raise RuntimeError("作品作者与目标主页不一致")
                row = add_work(state, item)
                sources = media_sources(item)
                if not sources or any(not urls for _, urls in sources):
                    raise RuntimeError("作品没有可用媒体地址")
                for path, urls in sources:
                    await asyncio.to_thread(fetch_file, path, urls)
                save_json(ROOT / "works" / ident / "source.json",
                          {"id": ident, "kind": row["kind"], "files": [str(p.relative_to(ROOT)) for p, _ in sources],
                           "stamps": {str(p.relative_to(ROOT)): [p.stat().st_size, p.stat().st_mtime_ns] for p, _ in sources}})
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
                report(state)

    tasks = [asyncio.create_task(one(ident)) for ident in ids]
    try:
        await asyncio.gather(*tasks)
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def metrics(video):
    cached = video.parent / "metrics.json"
    signature = [video.stat().st_size, video.stat().st_mtime_ns, "luma-chroma-v1"]
    existing = load_json(cached, {})
    if existing.get("signature") == signature:
        return existing["frames"]
    with tempfile.TemporaryDirectory(dir=video.parent) as temporary:
        output = Path(temporary) / "metrics.txt"
        run_ffmpeg(["-i", video, "-an", "-vf",
                    f"select='gte(scene,0)',signalstats,metadata=print:file='{output}'",
                    "-f", "null", "-"])
        frames = []
        for line in output.read_text().splitlines():
            if line.startswith("frame:"):
                match = re.search(r"pts_time:([\d.eE+-]+)", line)
                if match:
                    frames.append({"t": float(match[1]), "scene": 0., "diff": 0.})
            elif frames and line.startswith("lavfi.scene_score="):
                frames[-1]["scene"] = float(line.split("=", 1)[1])
            elif frames and line.startswith(("lavfi.signalstats.YDIF=", "lavfi.signalstats.UDIF=", "lavfi.signalstats.VDIF=")):
                frames[-1]["diff"] = max(frames[-1]["diff"], float(line.split("=", 1)[1]))
    if not frames:
        raise RuntimeError("未能解析逐帧检测数据")
    save_json(cached, {"signature": signature, "frames": frames})
    return frames


def select_frames(frames, threshold):
    # Heuristic: scene and stability scores miss subtle edits; review flagged clips against the source.
    cuts = [0] + [i for i, f in enumerate(frames) if i and
                  max(f["scene"], f["diff"] / 100) >= threshold] + [len(frames)]
    selected = []
    for start, end in zip(cuts, cuts[1:]):
        # No minimum duration: even a one-frame content segment must survive.
        runs, active = [], []
        for i in range(start, end):
            if i > start and frames[i]["diff"] <= 1.0:
                active.append(i)
            else:
                if active:
                    runs.append(active)
                active = []
        if active:
            runs.append(active)
        stable = max(runs, key=len) if runs else []
        index = stable[len(stable) // 2] if stable else (start + end - 1) // 2
        review = "" if stable else "没有稳定区间，核对转场或短暂图片"
        if any(frames[i]["diff"] > 2.0 and max(frames[i]["scene"], frames[i]["diff"] / 100) < threshold
               for i in range(start + 1, end)):
            review = "段内存在未分段变化，核对漏图或动画"
        selected.append({"frame": index, "seconds": frames[index]["t"],
                         "start": frames[start]["t"], "review": review})
    return selected


def frame_expression(indices):
    terms = [f"eq(n,{index})" for index in indices]
    # Balanced sums avoid FFmpeg's expression recursion limit on long slideshows.
    while len(terms) > 1:
        terms = ["(" + "+".join(terms[i:i + 2]) + ")" for i in range(0, len(terms), 2)]
    return terms[0]


def reviewed_frames(frames, override):
    times = override.get("seconds", [])
    if not times or any(not isinstance(t, (int, float)) or not math.isfinite(t) for t in times):
        raise RuntimeError("人工选帧时间必须是非空的有限数值列表")
    if times != sorted(set(times)) or times[0] < frames[0]["t"] or times[-1] > frames[-1]["t"]:
        raise RuntimeError("人工选帧时间必须递增且处于视频范围内")
    stamps = [f["t"] for f in frames]
    selected = []
    for requested in times:
        right = bisect.bisect_left(stamps, requested)
        index = min((max(0, right - 1), min(len(frames) - 1, right)), key=lambda i: abs(stamps[i] - requested))
        selected.append({"frame": index, "seconds": stamps[index], "start": stamps[index],
                         "review": override.get("review_note", "")})
    if len({r["frame"] for r in selected}) != len(selected):
        raise RuntimeError("人工选帧时间映射到了重复视频帧")
    return selected


def preview(folder):
    images = sorted((folder / "images").glob("*.png"))
    if not images:
        raise RuntimeError("没有输出图片")
    from PIL import Image, ImageDraw          # previews only; the saved PNGs are never resized
    pages = []
    for page in range(0, len(images), 100):
        batch = images[page:page + 100]
        sheet = Image.new("RGB", (1000, ((len(batch) + 4) // 5) * 230), "white")
        draw = ImageDraw.Draw(sheet)
        for i, path in enumerate(batch):
            with Image.open(path) as picture:
                picture.thumbnail((190, 200))
                x, y = (i % 5) * 200, (i // 5) * 230
                sheet.paste(picture.convert("RGB"), (x + (200 - picture.width) // 2, y))
            draw.text((x + 5, y + 205), path.stem, fill="black")
        name = "preview.jpg" if page == 0 else f"preview-{page // 100 + 1:02d}.jpg"
        sheet.save(folder / name, quality=90)
        pages.append(name)
    return pages


def extract_work(ident, threshold, destination=None):
    work = ROOT / "works" / ident
    destination = destination or work
    override = load_json(ROOT / "frame_overrides.json", {}).get(ident)
    marker = load_json(destination / "extraction.json", {})
    if marker.get("threshold") == threshold and marker.get("override") == override and marker.get("complete"):
        expected = marker["count"]
        if all((destination / "images" / f"{i:04d}.png").exists() for i in range(1, expected + 1)):
            return marker
        raise RuntimeError("已完成图片缺失，保留原目录并要求核对")
    if (destination / "images").exists():
        if marker.get("complete"):
            raise RuntimeError("已有另一阈值的完成图片；请使用新目录，避免覆盖")
        backup = destination / f"incomplete-{time.time_ns()}"
        backup.mkdir()
        for path in list(destination.iterdir()):
            if path.name in ("images", "frames.csv", "extraction.json") or path.name.startswith("preview"):
                path.replace(backup / path.name)
    source = load_json(work / "source.json", {})
    require_space()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="extract-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        images = stage / "images"
        images.mkdir()
        if source.get("kind") == "gallery":
            rows = []
            for i, relative in enumerate(source["files"], 1):
                require_space()
                run_ffmpeg(["-i", ROOT / relative, "-frames:v", "1", images / f"{i:04d}.png"])
                rows.append({"image": f"{i:04d}.png", "frame": "", "seconds": "", "review": ""})
        else:
            video = work / "video.mp4"
            info = probe(video)
            data = metrics(video)
            selected = reviewed_frames(data, override) if override else select_frames(data, threshold)
            require_space(len(selected) * info["width"] * info["height"] * 4)
            rows = [dict(image=f"{i:04d}.png", **row) for i, row in enumerate(selected, 1)]
            expression = frame_expression(row["frame"] for row in selected)
            run_ffmpeg(["-i", video, "-an", "-vf", f"select='{expression}'", "-fps_mode", "vfr",
                        "-start_number", "1", images / "%04d.png"])
        if len(list(images.glob("*.png"))) != len(rows):
            raise RuntimeError("输出图片数量与选帧数量不一致")
        write_csv(stage / "frames.csv", rows, ["image", "frame", "seconds", "start", "review"])
        preview(stage)
        marker = {"complete": True, "threshold": threshold, "count": len(rows),
                  "review": any(row["review"] for row in rows), "override": override}
        save_json(stage / "extraction.json", marker)
        destination.mkdir(parents=True, exist_ok=True)
        for path in stage.iterdir():
            path.replace(destination / path.name)
    return marker


def estimate(state):
    sizes = []
    for ident in state.get("samples", []):
        work = ROOT / "works" / ident
        calibration = ROOT / "calibration" / ident / str(state["calibration"]["threshold"])
        sizes.append(sum(p.stat().st_size for folder in (work, calibration)
                         for p in folder.rglob("*") if p.is_file()))
    if sizes:
        total = int(sum(sizes) / len(sizes) * len(state["works"]) * 2)
        print(f"按样本估计总空间（含两倍余量）：{total / 1024 ** 3:.2f} GiB")
        require_space(total)


def safe_error(error):
    if isinstance(error, RuntimeError) and not re.search(r"https?://|cookie|token", str(error), re.I):
        return str(error)
    return type(error).__name__ + "：详情已隐藏以保护登录信息"


async def online(command, state, sample_id=None):
    async with f2_client() as client:
        if command == "sample":
            posts = await enumerate_works(client, state)
            # three calibration samples: the one you named (ideally your hardest flash video) plus the newest posts
            ids = ([sample_id] if sample_id else []) + [i for i in state["listed_ids"] if i != sample_id]
            ids = ids[:3]
            state["samples"] = ids
            report(state)
            await download_works(client, state, ids, posts)
            if not all(state["works"].get(i, {}).get("download") == "complete" for i in ids):
                raise RuntimeError("三条样本未全部下载成功，全量任务未启动")
            state["samples_downloaded"] = True
            report(state)
        else:
            if not state.get("samples_downloaded") or not state.get("calibration", {}).get("accepted"):
                raise RuntimeError("下载和拆图样本尚未验收，全量任务未启动")
            posts = await enumerate_works(client, state)
            estimate(state)
            await download_works(client, state, state["listed_ids"], posts)
            failed = sum(state["works"][ident]["download"] != "complete"
                         for ident in state["listed_ids"] if ident not in state.get("skipped_ids", []))
            if failed:
                raise RuntimeError(f"仍有 {failed} 条作品未下载成功，详情见 report.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["cookies", "sample", "calibrate", "accept", "download", "extract", "status"])
    parser.add_argument("--browser", choices=["chrome", "safari"], default="chrome")
    parser.add_argument("--user", help="主页链接或主页 ID；第一次运行 sample 时必须给，之后记在 state.json 里")
    parser.add_argument("--sample-id", help="sample 时指定一条作品 ID 作为校准样本（建议选最难拆的快闪视频）")
    parser.add_argument("--threshold", type=float, choices=THRESHOLDS)
    args = parser.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    state = load_json(ROOT / "state.json", {"works": {}})
    try:
        if args.command == "cookies":
            chrome_cookie(args.browser)
        elif args.command in ("sample", "download"):
            if args.user:
                ident = sec_uid(args.user)
                if state.get("sec_user_id") not in (None, ident):
                    raise RuntimeError("douyin_archive/ 里已有另一个主页的进度；换主页前请先把这个文件夹改名或移走")
                state["sec_user_id"] = ident
            if not state.get("sec_user_id"):
                raise RuntimeError("先用 --user 指定要归档的主页链接")
            if args.sample_id and not args.sample_id.isdigit():
                raise RuntimeError("--sample-id 应为纯数字的作品 ID")
            asyncio.run(online(args.command, state, args.sample_id))
        elif args.command == "calibrate":
            if not state.get("samples_downloaded"):
                raise RuntimeError("先下载并验证三条样本")
            for ident in state["samples"]:
                for threshold in THRESHOLDS:
                    marker = extract_work(ident, threshold, ROOT / "calibration" / ident / str(threshold))
                    print(f"样本 {ident} 阈值 {threshold}：{marker['count']} 张；待核对 {marker['review']}")
        elif args.command == "accept":
            if args.threshold is None:
                raise RuntimeError("人工核对预览与视频后，用 --threshold 明确记录通过的阈值")
            for ident in state.get("samples", []):
                path = ROOT / "calibration" / ident / str(args.threshold) / "extraction.json"
                if not load_json(path, {}).get("complete"):
                    raise RuntimeError("所选阈值的样本拆图尚未完成")
            if len(state.get("samples", [])) != 3:
                raise RuntimeError("缺少三条校准样本")
            state["calibration"] = {"accepted": True, "threshold": args.threshold}
            report(state)
        elif args.command == "extract":
            calibration = state.get("calibration", {})
            if not calibration.get("accepted"):
                raise RuntimeError("三条样本尚未验收，全量拆图未启动")
            for ident, row in state["works"].items():
                if row["download"] != "complete":
                    continue
                try:
                    result = extract_work(ident, calibration["threshold"])
                    review = (result.get("override") or {}).get("review_note", "")
                    row.update(extract="complete", images=result["count"],
                               review=review or ("需要核对" if result["review"] else "未发现自动检测异常"), error="")
                    print(f"拆图完成：{ident}，{result['count']} 张", flush=True)
                except Exception as e:
                    row.update(extract="failed", error=safe_error(e))
                    if isinstance(e, RuntimeError) and "空间" in str(e):
                        raise
                finally:
                    report(state)
            failed = sum(row["extract"] == "failed" for row in state["works"].values())
            if failed:
                raise RuntimeError(f"仍有 {failed} 条作品拆图失败，详情见 report.csv")
        else:
            rows = list(state["works"].values())
            print(json.dumps({"listing_complete": state.get("listing_complete", False),
                "works": len(rows), "downloaded": sum(r["download"] == "complete" for r in rows),
                "skipped": len(state.get("skipped_ids", [])),
                "extracted": sum(r["extract"] == "complete" for r in rows),
                "images": sum(r["images"] for r in rows), "calibration": state.get("calibration")}, ensure_ascii=False))
        return 0
    except KeyboardInterrupt:
        report(state)
        print("已中断，下载文件及进度已保留", flush=True)
        return 130
    except Exception as e:
        state["last_error"] = safe_error(e)
        report(state)
        print("停止：" + state["last_error"], flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
