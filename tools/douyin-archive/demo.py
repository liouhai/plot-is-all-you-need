"""Offline demo of the frame splitter: no network, no account, no third-party content.

    python demo.py

It draws 24 made-up slides, cuts them into a flash video (some slides last one frame, one slide
comes back later, two neighbours differ only slightly), runs the same extraction the archive uses,
and writes demo/demo.png: the timeline of the video on top, the recovered stills underneath.
Needs FFmpeg and Pillow.
"""
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import douyin_archive as archive

OUT = Path(__file__).resolve().parent / "demo"
W, H, FPS, THRESHOLD = 540, 720, 30, 0.02
PASTEL = ["#f6d6d6", "#fde2c8", "#fff3c4", "#d9f0d3", "#cdeaf2", "#d6dcf7", "#ead7f5", "#f4d4e6"]
INK = ["#d1495b", "#edae49", "#00798c", "#30638e", "#6a4c93", "#2a9d8f"]


def font(size):
    for path in ("/System/Library/Fonts/Helvetica.ttc", "C:/Windows/Fonts/arialbd.ttf",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def slide(number, rng, base=None):
    """A stand-in for a figure: a tinted card with a number and a small bar chart."""
    im = base.copy() if base else Image.new("RGB", (W, H), rng.choice(PASTEL))
    d = ImageDraw.Draw(im)
    if not base:
        d.text((40, 30), f"{number:02d}", fill="#222222", font=font(110))
    d.rectangle((40, 200, W - 40, H - 60), fill="white")
    colour = rng.choice(INK)
    for k in range(7):
        top = rng.randint(260, H - 140)
        d.rectangle((70 + k * 60, top, 110 + k * 60, H - 90), fill=colour)
    return im


def build_video(rng):
    """Returns the segments as (slide number, first frame, frame count)."""
    slides = [slide(n, rng) for n in range(1, 25)]
    slides[11] = slide(12, rng, base=slides[10])                 # 12 keeps 11's card and number; only the bars change
    order = list(range(24)) + [4]                                # slide 05 flashes by again at the end
    lengths = [rng.choice((3, 4, 5, 6, 8)) for _ in order]
    lengths[7], lengths[16] = 1, 1                               # two slides are on screen for a single frame
    frames = OUT / "frames"
    frames.mkdir(parents=True)
    segments, n = [], 0
    for index, length in zip(order, lengths):
        segments.append((index + 1, n, length))
        for _ in range(length):
            n += 1
            slides[index].save(frames / f"{n:05d}.png")
    video = OUT / "works" / "demo" / "video.mp4"
    video.parent.mkdir(parents=True)
    archive.run_ffmpeg(["-framerate", FPS, "-i", frames / "%05d.png", "-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", video])
    shutil.rmtree(frames)
    archive.save_json(video.parent / "source.json", {"id": "demo", "kind": "video", "files": ["works/demo/video.mp4"]})
    return segments, video


def figure(segments, picked, counts):
    """Timeline of the flash video above the stills that came out of it."""
    stills = sorted((OUT / "works" / "demo" / "images").glob("*.png"))
    cols, tw, th, pad = 9, 150, 200, 14
    rows = -(-len(stills) // cols)
    width = pad + cols * (tw + pad)
    im = Image.new("RGB", (width, 300 + rows * (th + pad + 26)), "white")
    d = ImageDraw.Draw(im)
    total = sum(length for _, _, length in segments)
    d.text((pad, 14), f"Flash video: {len(segments)} segments in {total / FPS:.1f} s ({FPS} fps), shortest = 1 frame ({1000 / FPS:.0f} ms)",
           fill="#111111", font=font(26))
    x0, x1, y0, y1 = pad, width - pad, 70, 130
    scale = (x1 - x0) / total
    for k, (number, start, length) in enumerate(segments):
        d.rectangle((x0 + start * scale, y0, x0 + (start + length) * scale - 1, y1), fill=PASTEL[k % len(PASTEL)], outline="#888888")
        if length >= 3:
            d.text((x0 + start * scale + 4, y0 + 18), f"{number:02d}", fill="#333333", font=font(18))
    for row in picked:                                           # where the splitter took each still
        x = x0 + (row["frame"] + 0.5) * scale
        d.polygon([(x - 6, y1 + 16), (x + 6, y1 + 16), (x, y1 + 2)], fill="#d1495b")
    d.text((pad, y1 + 24), f"Recovered {len(stills)} stills at threshold {THRESHOLD}   (red marks = the frame taken from each segment)",
           fill="#111111", font=font(26))
    d.text((pad, y1 + 62), "Stills found at other thresholds: " + "   ".join(f"{t}: {c}" for t, c in counts.items()),
           fill="#666666", font=font(22))
    for i, path in enumerate(stills):
        x, y = pad + (i % cols) * (tw + pad), 290 + (i // cols) * (th + pad + 26)
        with Image.open(path) as picture:
            im.paste(picture.convert("RGB").resize((tw, th), Image.LANCZOS), (x, y))
        d.rectangle((x, y, x + tw, y + th), outline="#bbbbbb")
        d.text((x + 2, y + th + 3), path.stem, fill="#555555", font=font(16))
    im.save(OUT / "demo.png")


if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True)
    rng = random.Random(3)
    segments, video = build_video(rng)
    archive.ROOT = OUT                                            # run the real extraction on the made-up video
    data = archive.metrics(video)
    counts = {t: len(archive.select_frames(data, t)) for t in archive.THRESHOLDS}
    result = archive.extract_work("demo", THRESHOLD)
    picked = archive.select_frames(data, THRESHOLD)
    figure(segments, picked, counts)
    # every segment must yield exactly one still, taken from inside that segment
    assert result["count"] == len(segments), (result["count"], len(segments))
    assert all(start <= row["frame"] < start + length for row, (_, start, length) in zip(picked, segments))
    print(f"{len(segments)} segments -> {result['count']} stills; by threshold: {counts}")
    print(OUT / "demo.png")
