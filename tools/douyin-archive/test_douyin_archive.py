"""Run with: python test_douyin_archive.py (no test framework, no network)."""
import json
import asyncio
import shutil
import tempfile
from pathlib import Path
import douyin_archive as archive


def check():
    archive.binary("ffmpeg")
    archive.binary("ffprobe")
    frames = [{"t": i / 30, "scene": .8 if i in (10, 11, 20) else 0.,
               "diff": 200. if i in (10, 11, 20) else 0.} for i in range(30)]
    selected = archive.select_frames(frames, .3)
    assert len(selected) == 4, "must retain short and repeated content"
    assert selected[0]["frame"] < 10, "first content missing"
    assert selected[1]["frame"] == 10, "one-frame content missing"
    assert 11 <= selected[2]["frame"] < 20
    assert selected[-1]["frame"] >= 20, "last content missing"
    assert [r["seconds"] for r in selected] == sorted(r["seconds"] for r in selected)
    fade = [{"t": i / 30, "scene": .01, "diff": 10.} for i in range(20)]
    assert archive.select_frames(fade, .3)[0]["review"], "undetected fade must be flagged"
    assert archive.reviewed_frames(frames, {"seconds": [0.0, 10/30, 29/30]})[1]["frame"] == 10
    try:
        archive.reviewed_frames(frames, {"seconds": [0.0, 99.0]})
    except RuntimeError:
        pass
    else:
        raise AssertionError("out-of-range manual frames must be rejected")
    assert "https://" not in archive.safe_error(ValueError("https://private/ Cookie=secret"))
    assert "secret" not in archive.safe_error(RuntimeError("cookie=secret"))
    assert archive.sec_uid("https://www.douyin.com/user/" + "A" * 30 + "?from=x") == "A" * 30
    assert archive.sec_uid("B" * 30) == "B" * 30
    try:
        archive.sec_uid("https://www.douyin.com/")
    except RuntimeError:
        pass
    else:
        raise AssertionError("a link without a homepage id must be rejected")
    old_video = {"aweme_id": "123", "video": {"bit_rate": None,
                 "play_addr": {"url_list": ["https://example.invalid/video.mp4"]}}}
    assert archive.media_sources(old_video)[0][1] == ["https://example.invalid/video.mp4"]
    with tempfile.TemporaryDirectory() as temporary:
        old_root = archive.ROOT
        archive.ROOT = Path(temporary)
        try:
            archive.save_json(archive.ROOT / "secret.json", {"cookie": "test"}, private=True)
            assert (archive.ROOT / "secret.json").stat().st_mode & 0o777 == 0o600
            state = {"works": {}, "sec_user_id": "T" * 24}
            item = {"aweme_id": "123", "desc": "hello", "create_time": 1}
            archive.add_work(state, item)["download"] = "complete"
            archive.add_work(state, item)
            assert len(state["works"]) == 1
            assert state["works"]["123"]["download"] == "complete"
            asyncio.run(archive.download_works(None, {"works": {}, "skipped_ids": ["789"]}, ["789"], {}))
            if True:
                work = archive.ROOT / "works" / "123"
                work.mkdir(parents=True)
                video = work / "video.mp4"
                archive.run_ffmpeg(["-f", "lavfi", "-i", "color=red:s=128x96:r=30:d=0.4",
                    "-f", "lavfi", "-i", "color=blue:s=128x96:r=30:d=0.033333",
                    "-f", "lavfi", "-i", "color=green:s=128x96:r=30:d=0.4",
                    "-f", "lavfi", "-i", "color=red:s=128x96:r=30:d=0.4",
                    "-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]",
                    "-map", "[v]", "-c:v", "libx264", "-crf", "0", video])
                archive.validate_video(video)
                post = dict(item, author={"sec_uid": state["sec_user_id"]},
                            video={"play_addr": {"url_list": ["https://unused.invalid/test.mp4"]}})
                asyncio.run(archive.download_works(None, state, ["123"], {"123": post}))
                assert state["works"]["123"]["download"] == "complete"
                asyncio.run(archive.download_works(None, state, ["123"], {}))
                archive.run_ffmpeg(["-i", video, "-vf", "select='" + archive.frame_expression(range(300)) + "'",
                                    "-f", "null", "-"])
                metrics = archive.metrics(video)
                result = archive.extract_work("123", .05)
                assert result["count"] == 4, (result, metrics)
                assert archive.probe(work / "images" / "0001.png")["width"] == 128
                timestamps = [p.stat().st_mtime_ns for p in (work / "images").glob("*.png")]
                assert archive.extract_work("123", .05) == result
                assert timestamps == [p.stat().st_mtime_ns for p in (work / "images").glob("*.png")]
                assert (work / "preview.jpg").exists()
                assert len(json.loads((work / "metrics.json").read_text())["frames"]) == len(metrics)
                gallery = archive.ROOT / "works" / "456"
                originals = gallery / "originals"
                originals.mkdir(parents=True)
                shutil.copyfile(work / "images" / "0001.png", originals / "0001.png")
                archive.save_json(gallery / "source.json", {"kind": "gallery", "files": ["works/456/originals/0001.png"]})
                assert archive.extract_work("456", .05)["count"] == 1
                assert (originals / "0001.png").read_bytes() == (gallery / "images" / "0001.png").read_bytes()
        finally:
            archive.ROOT = old_root
    print("PASS: first/last, one-frame content, repeats, fade flag, credentials, resume, real FFmpeg extraction")


if __name__ == "__main__":
    check()
