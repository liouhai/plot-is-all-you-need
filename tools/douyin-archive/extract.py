#!/usr/bin/env python3
"""本地拆图：可靠画面自动保存，不可靠片段交给调用本程序的 agent 判断。"""
import argparse
import hashlib
import json
import re
import shutil
import tempfile
from pathlib import Path

from download import load_json, save_json, write_csv, run_ffmpeg, probe, require_space, safe_error

THRESHOLDS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.3)


def metrics(video, cache=None):
    cached = cache or video.parent / "metrics.json"
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
                         "start": frames[start]["t"], "start_frame": start, "end_frame": end, "review": review})
    return selected

def frame_expression(indices):
    terms = [f"eq(n,{index})" for index in indices]
    # Balanced sums avoid FFmpeg's expression recursion limit on long slideshows.
    while len(terms) > 1:
        terms = ["(" + "+".join(terms[i:i + 2]) + ")" for i in range(0, len(terms), 2)]
    return terms[0]

def preview(folder):
    images = sorted((folder / "images").glob("*.png"))
    if not images:
        return []
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


def refresh(folder, manifest):
    rows = []
    for segment in manifest["segments"]:
        for image in segment.get("images", []):
            rows.append({"image": image, "segment": segment["id"], "status": segment["status"],
                         "frame": segment.get("frame", ""), "seconds": segment.get("seconds", ""),
                         "note": segment.get("note", "")})
    manifest["count"] = len(rows)
    manifest["pending"] = sum(s["status"] == "pending" for s in manifest["segments"])
    manifest["dropped"] = sum(s["status"] == "dropped" for s in manifest["segments"])
    write_csv(folder / "frames.csv", rows, ["image", "segment", "status", "frame", "seconds", "note"])
    preview(folder)
    save_json(folder / "extraction.json", manifest)
    return manifest


def review_bundle(video, folder, segment, frames):
    review = folder / "review" / segment["id"]
    images = review / "images"
    images.mkdir(parents=True)
    start, end = segment["start_frame"], segment["end_frame"]
    # shortcut: 每段预览最多 24 帧；有遗漏时 agent 从原视频提取其余帧，或舍弃难以恢复的片段。
    count = min(24, end - start)
    indices = sorted({start + i * (end - start - 1) // max(1, count - 1) for i in range(count)})
    run_ffmpeg(["-i", video, "-an", "-vf", f"select='{frame_expression(indices)}'", "-fps_mode", "vfr",
                "-start_number", "0", images / "%04d.png"])
    candidates = [{"image": f"images/{i:04d}.png", "frame": index, "seconds": frames[index]["t"]}
                  for i, index in enumerate(indices)]
    if len(list(images.glob("*.png"))) != len(candidates):
        raise RuntimeError("复核候选帧数量不一致")
    run_ffmpeg(["-i", video, "-an", "-vf", f"trim=start_frame={start}:end_frame={end},setpts=PTS-STARTPTS",
                "-c:v", "libx264", "-crf", "18", review / "clip.mp4"])
    preview(review)
    save_json(review / "segment.json", {**segment, "source": str(video), "candidates": candidates})
    segment["bundle"] = str(review.relative_to(folder))


def existing_result(folder, signature, threshold):
    marker = load_json(folder / "extraction.json", {})
    if not marker:
        if folder.exists() and any(folder.iterdir()):
            raise RuntimeError("输出目录已有未完成或其他内容，请使用新目录，避免覆盖")
        return None
    if marker.get("signature") != signature or marker.get("threshold") != threshold:
        raise RuntimeError("源文件或阈值已改变，请使用新输出目录，保留已有结果")
    for segment in marker["segments"]:
        if any(not (folder / image).is_file() for image in segment.get("images", [])):
            raise RuntimeError("已完成图片缺失，请保留原目录并核对")
        if segment["status"] == "pending":
            bundle = folder / segment["bundle"]
            details = load_json(bundle / "segment.json", {})
            if not details or not (bundle / "clip.mp4").is_file() or any(
                    not (bundle / row["image"]).is_file() for row in details["candidates"]):
                raise RuntimeError("待复核片段缺失，请保留原目录并核对")
    return marker


def extract_video(video, destination=None, threshold=0.02):
    video = Path(video).resolve()
    folder = Path(destination).resolve() if destination else video.parent / (video.stem + "-extracted")
    if not 0 < threshold <= 1:
        raise RuntimeError("拆图阈值必须大于 0 且不超过 1")
    signature = [video.stat().st_size, video.stat().st_mtime_ns]
    previous = existing_result(folder, signature, threshold)
    if previous:
        return previous
    info = probe(video)
    folder.parent.mkdir(parents=True, exist_ok=True)
    require_space(folder.parent)
    with tempfile.TemporaryDirectory(prefix="extract-", dir=folder.parent) as temporary:
        stage = Path(temporary)
        (stage / "images").mkdir()
        data = metrics(video, stage / "metrics.json")
        segments = []
        for segment in select_frames(data, threshold):
            if segment["review"] and segments and segments[-1]["review"]:
                segments[-1]["end_frame"] = segment["end_frame"]
                segments[-1]["review"] = "连续不可靠变化，检查整段是否能取得完整图"
            else:
                segments.append(segment)
        require_space(folder.parent, len(segments) * info["width"] * info["height"] * 4)
        automatic = []
        for i, segment in enumerate(segments, 1):
            segment.update(id=f"s{i:04d}", status="pending" if segment["review"] else "auto", images=[])
            if segment["review"]:
                require_space(folder.parent, min(24, segment["end_frame"] - segment["start_frame"]) *
                              info["width"] * info["height"] * 4)
                review_bundle(video, stage, segment, data)
            else:
                automatic.append(segment)
        if automatic:
            candidates = stage / "candidates"
            candidates.mkdir()
            expression = frame_expression(s["frame"] for s in automatic)
            run_ffmpeg(["-i", video, "-an", "-vf", f"select='{expression}'", "-fps_mode", "vfr",
                        "-start_number", "1", candidates / "%04d.png"])
            if len(list(candidates.glob("*.png"))) != len(automatic):
                raise RuntimeError("自动选帧与输出图片数量不一致")
            for i, segment in enumerate(automatic, 1):
                name = f"images/{segment['id']}-01.png"
                shutil.copyfile(candidates / f"{i:04d}.png", stage / name)
                segment["images"] = [name]
        manifest = {"complete": True, "source": str(video), "signature": signature,
                    "threshold": threshold, "segments": segments}
        refresh(stage, manifest)
        # The temporary directory is published only after all artifacts have been verified.
        if folder.exists():
            if any(folder.iterdir()):
                raise RuntimeError("输出目录在拆图期间出现内容，停止以避免覆盖")
            for path in stage.iterdir():
                path.replace(folder / path.name)
        else:
            stage.rename(folder)
    return manifest


def extract_gallery(work, root, destination):
    source = load_json(work / "source.json", {})
    files = [(root / name).resolve() for name in source.get("files", [])]
    if not files or any(not path.is_relative_to(root.resolve()) for path in files):
        raise RuntimeError("图集来源缺失或超出下载目录")
    signature = [[str(path), path.stat().st_size, path.stat().st_mtime_ns] for path in files]
    previous = existing_result(destination, signature, None)
    if previous:
        return previous
    destination.parent.mkdir(parents=True, exist_ok=True)
    require_space(destination.parent)
    with tempfile.TemporaryDirectory(prefix="gallery-", dir=destination.parent) as temporary:
        stage = Path(temporary)
        (stage / "images").mkdir()
        segments = []
        for i, path in enumerate(files, 1):
            ident = f"s{i:04d}"
            image = f"images/{ident}-01.png"
            run_ffmpeg(["-xerror", "-i", path, "-frames:v", "1", stage / image])
            segments.append({"id": ident, "status": "auto", "images": [image], "review": ""})
        result = refresh(stage, {"complete": True, "source": str(work), "signature": signature,
                                 "threshold": None, "segments": segments})
        if destination.exists():
            for path in stage.iterdir():
                path.replace(destination / path.name)
        else:
            stage.rename(destination)
    return result


def apply_review(folder, segment_id, images=(), drop=False, note=""):
    folder = Path(folder).resolve()
    if not note.strip() or (bool(images) == bool(drop)):
        raise RuntimeError("agent 必须说明判断理由，并选择提供图片或舍弃片段其中一种")
    manifest = load_json(folder / "extraction.json", {})
    segment = next((s for s in manifest.get("segments", []) if s["id"] == segment_id), None)
    if segment is None:
        raise RuntimeError("找不到待复核片段")
    files = [Path(path).resolve() for path in images]
    decision = {"status": "dropped" if drop else "kept", "note": note,
                "inputs": [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                           for path in files]}
    if segment.get("decision") == decision:
        return manifest
    if segment["status"] != "pending":
        raise RuntimeError("该片段已经处理；修改判断请从新输出目录开始")
    require_space(folder)
    with tempfile.TemporaryDirectory(prefix="review-", dir=folder) as temporary:
        stage = Path(temporary)
        from PIL import Image
        names = []
        for i, path in enumerate(files, 1):
            name = f"images/{segment_id}-{i:02d}.png"
            target = stage / Path(name).name
            with Image.open(path) as image:
                image.load()
                require_space(folder, image.width * image.height * 4)
                image.convert("RGB").save(target)
            final = folder / name
            if final.exists() and final.read_bytes() != target.read_bytes():
                raise RuntimeError("agent 图片与已有文件冲突，保留原文件")
            names.append(name)
        for name in names:
            target = stage / Path(name).name
            final = folder / name
            if not final.exists():
                target.replace(final)
    segment.update(status=decision["status"], note=note, images=names, decision=decision)
    # Agent-supplied images may be crops or multiple recovered figures, so the automatic frame is not their provenance.
    segment.pop("frame", None)
    segment.pop("seconds", None)
    return refresh(folder, manifest)


def extract_input(source, destination=None, threshold=0.02):
    source = Path(source).resolve()
    if source.is_file():
        result = extract_video(source, destination, threshold)
        folder = Path(destination).resolve() if destination else source.parent / (source.stem + "-extracted")
        return [{"output": str(folder), "count": result["count"], "pending": result["pending"]}]
    works = source / "works"
    if not works.is_dir():
        raise RuntimeError("请输入本地视频文件或含 works/ 的下载目录")
    results, failed = [], False
    for work in sorted(works.iterdir()):
        if not work.is_dir():
            continue
        folder = Path(destination).resolve() / work.name if destination else work / "extraction"
        try:
            if load_json(work / "source.json", {}).get("kind") == "gallery":
                result = extract_gallery(work, source, folder)
            elif (work / "video.mp4").is_file():
                result = extract_video(work / "video.mp4", folder, threshold)
            else:
                continue
            results.append({"work": work.name, "output": str(folder), "count": result["count"], "pending": result["pending"]})
        except Exception as error:
            failed = True
            results.append({"work": work.name, "error": safe_error(error)})
    save_json(source / "collection.json", {"works": results})
    if failed:
        raise RuntimeError("部分作品拆图失败，详见 collection.json；其他结果已保留")
    if not results:
        raise RuntimeError("下载目录中没有可拆图的完整媒体")
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    split = commands.add_parser("extract", help="拆本地视频或整个下载目录")
    split.add_argument("input", type=Path)
    split.add_argument("--output", type=Path)
    split.add_argument("--threshold", type=float, default=0.02)
    review = commands.add_parser("review", help="由 agent 提交片段判断，不接受人工时间表")
    review.add_argument("output", type=Path)
    review.add_argument("--segment", required=True)
    choice = review.add_mutually_exclusive_group(required=True)
    choice.add_argument("--images", type=Path, nargs="+")
    choice.add_argument("--drop", action="store_true")
    review.add_argument("--note", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "extract":
            results = extract_input(args.input, args.output, args.threshold)
            print(json.dumps(results, ensure_ascii=False, indent=2))
        else:
            result = apply_review(args.output, args.segment, args.images or (), args.drop, args.note)
            print(f"已保存 agent 判断：可用 {result['count']} 张，待判断 {result['pending']} 段，舍弃 {result['dropped']} 段")
        return 0
    except Exception as error:
        print("停止：" + safe_error(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
