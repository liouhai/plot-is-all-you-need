"""Put figures side by side so the user can choose by looking.

    # 样板册：每张图标 A、B、C…，可在 id 后用 :: 加一行标记
    python scripts/contact_sheet.py sheet --out sheet.png "id1::贴近你的口味" "id2::我的推荐" path/to/draft.png

    # 并排对照：样例 | 成品
    python scripts/contact_sheet.py compare --out cmp.png --labels "样例 A,成品" id1 figures/result.png

    # 色卡：一张卡片记录的所有配色，编号 1、2、3…
    python scripts/contact_sheet.py swatches --out pal.png id1
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards

Image.MAX_IMAGE_PIXELS = None
FONTS = ["/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
         "/System/Library/Fonts/Hiragino Sans GB.ttc", "C:/Windows/Fonts/msyh.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"]


def font(size):
    for f in FONTS:
        if Path(f).exists():
            return ImageFont.truetype(f, size)
    return ImageFont.load_default(size=size)


def fit(path, w, h):
    im = Image.open(path).convert("RGB")
    im.thumbnail((w, h), Image.LANCZOS)
    return im


def grid(items, out, cell, cols, head=64):
    """items: [(image path, big label, small tag)]"""
    rows = (len(items) + cols - 1) // cols
    pad = 16
    ims = [fit(path, cell, cell) for path, _, _ in items]
    ch = max(im.height for im in ims)  # cell height follows the tallest figure, so wide figures are not lost in white
    sheet = Image.new("RGB", (cols * (cell + pad) + pad, rows * (ch + head + pad) + pad), "white")
    d = ImageDraw.Draw(sheet)
    for k, ((path, label, tag), im) in enumerate(zip(items, ims)):
        x, y = pad + (k % cols) * (cell + pad), pad + (k // cols) * (ch + head + pad)
        d.rectangle([x, y, x + cell, y + head - 8], fill="#f1f1f1")
        d.text((x + 10, y + 6), label, fill="#111111", font=font(34))
        if tag:
            d.text((x + 16 + d.textlength(label, font=font(34)) + 10, y + 18), tag, fill="#b0461e", font=font(22))
        sheet.paste(im, (x + (cell - im.width) // 2, y + head + (ch - im.height) // 2))
        d.rectangle([x, y + head, x + cell, y + head + ch], outline="#dddddd")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sheet")
    s.add_argument("items", nargs="+")
    s.add_argument("--out", required=True)
    s.add_argument("--cols", type=int)
    c = sub.add_parser("compare")
    c.add_argument("items", nargs="+")
    c.add_argument("--out", required=True)
    c.add_argument("--labels", default="")
    w = sub.add_parser("swatches")
    w.add_argument("item")
    w.add_argument("--out", required=True)
    a = ap.parse_args()

    if a.cmd == "sheet":
        items = []
        for k, it in enumerate(a.items):
            ident, _, tag = it.partition("::")
            items.append((cards.find(ident), chr(65 + k), tag))
        grid(items, a.out, 560, a.cols or (2 if len(items) <= 4 else 3))
    elif a.cmd == "compare":
        labels = [x.strip() for x in a.labels.split(",")] if a.labels else []
        items = [(cards.find(it), labels[k] if k < len(labels) else "", "") for k, it in enumerate(a.items)]
        grid(items, a.out, 900, len(items))
    else:
        meta, _ = cards.read(cards.find(a.item).with_suffix(".md"))
        pals = [p.split() for p in meta.get("palettes", [])]
        sw, rh = 56, 64
        im = Image.new("RGB", (90 + sw * max(len(p) for p in pals) + 20, rh * len(pals) + 20), "white")
        d = ImageDraw.Draw(im)
        for i, p in enumerate(pals):
            d.text((14, 20 + i * rh), str(i + 1), fill="#111111", font=font(28))
            for j, h in enumerate(p):
                d.rectangle([90 + j * sw, 14 + i * rh, 90 + j * sw + sw - 6, 14 + i * rh + rh - 16], fill=h)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        im.save(a.out)
        print(a.out)


if __name__ == "__main__":
    main()
