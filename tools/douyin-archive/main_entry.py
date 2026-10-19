#!/usr/bin/env python3
"""统一入口：download / extract / review / ingest / run。视觉判断由调用它的 agent 完成。"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from download import load_json, save_json, safe_error

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def ingest_selected(folder, images, gallery=None):
    folder = Path(folder).resolve()
    manifest = load_json(folder / "extraction.json", {})
    segments = manifest.get("segments", [])
    if not manifest.get("complete") or any(s["status"] == "pending" for s in segments):
        raise RuntimeError("先由 agent 处理所有待复核片段，再将选中的绘图作品入库")
    permitted = {(folder / image).resolve() for s in segments if s["status"] in ("auto", "kept")
                 for image in s["images"]}
    selected = [Path(image).resolve() for image in images]
    if not selected or any(image not in permitted for image in selected):
        raise RuntimeError("只能入库 agent 已检查并选中的正式输出图片")
    sys.path.insert(0, str(ROOT / "scripts"))
    import ingest
    gallery = Path(gallery) if gallery else ROOT / "gallery-local"
    gallery.mkdir(parents=True, exist_ok=True)
    results = manifest.setdefault("ingested", {})
    with tempfile.TemporaryDirectory(prefix="collect-") as temporary:
        for image in selected:
            relative = str(image.relative_to(folder))
            if relative in results:
                continue
            # Content names avoid leaking source account/work identifiers into future exports.
            ident = "collect-" + hashlib.sha256(image.read_bytes()).hexdigest()[:16]
            staged = Path(temporary) / (ident + ".png")
            shutil.copyfile(image, staged)
            status, name, other = ingest.register(staged, gallery)
            results[relative] = {"status": status, "id": name, "other": other}
            save_json(folder / "extraction.json", manifest)
    return results


def run_download(arguments):
    python = HERE / ".venv" / "bin" / "python"
    return subprocess.run([str(python) if python.is_file() else sys.executable,
                           str(HERE / "download.py"), *arguments]).returncode


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["download", "extract", "review", "ingest", "run"])
    if not arguments or arguments[0] in ("-h", "--help"):
        parser.print_help()
        return 0
    args, rest = parser.parse_args(arguments[:1]), arguments[1:]
    if args.command == "download":
        return run_download(rest)
    if args.command in ("extract", "review"):
        import extract
        return extract.main([args.command, *rest])
    command = argparse.ArgumentParser(prog=f"main_entry.py {args.command}")
    if args.command == "run":
        target = command.add_mutually_exclusive_group(required=True)
        target.add_argument("--video")
        target.add_argument("--user")
        command.add_argument("--output", type=Path, default=Path("douyin_archive"))
        command.add_argument("--browser", choices=["chrome", "safari"], default="chrome")
        command.add_argument("--threshold", type=float, default=0.02)
        options = command.parse_args(rest)
        target_args = ["--video", options.video] if options.video else ["--user", options.user]
        status = run_download([*target_args, "--output", str(options.output), "--browser", options.browser])
        if status:
            return status
        import extract
        return extract.main(["extract", str(options.output), "--threshold", str(options.threshold)])
    command.add_argument("output", type=Path)
    command.add_argument("--images", type=Path, nargs="+", required=True,
                         help="agent 目视确认属于绘图作品的正式输出图片")
    options = command.parse_args(rest)
    try:
        print(json.dumps(ingest_selected(options.output, options.images), ensure_ascii=False, indent=2))
        print("下一步：按 Appreciation 写新卡片，然后运行 scripts/build_index.py。")
        return 0
    except Exception as error:
        print("停止：" + safe_error(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
