"""Add figures to a gallery: downscale, drop near-duplicates, record palette variants, create stub cards.

    python scripts/ingest.py <image or folder> ...     # add new figures to gallery-local
    python scripts/ingest.py                           # sync: register images dropped straight into a gallery
    python scripts/ingest.py --gallery gallery <...>   # add to the public gallery

A figure whose structure matches one already in the library is treated as a recolouring of it:
the image is not added, its colours are appended to the existing card's `palettes`.
New figures get a stub card (`appreciated: false`) for the Appreciation stage to fill in.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards

Image.MAX_IMAGE_PIXELS = None
MAX_SIDE, G = 2000, 96
SAME, MAYBE = 0.85, 0.55  # structure similarity: >= SAME is a recolouring, >= MAYBE is worth a look
# ponytail: one global threshold on a layout signature; cropped screenshots of the same figure can slip
# under it. Upgrade path: the pixel-precise matcher in _archive/dedup-scripts/match.py.


def _content(im):
    """RGB array with black letterbox and blank margins removed, plus letterbox fraction."""
    im = im.convert("RGB").copy()
    im.thumbnail((640, 640), Image.BOX)
    a = np.asarray(im).astype(np.int16)
    g = a.mean(2)
    r, c = np.where(g.mean(1) >= 35)[0], np.where(g.mean(0) >= 35)[0]
    box = 0.0
    if len(r) and len(c):
        b = a[r[0]:r[-1] + 1, c[0]:c[-1] + 1]
        box = 1 - b.size / a.size
        a = b
    corners = np.concatenate([a[:4, :4].reshape(-1, 3), a[:4, -4:].reshape(-1, 3),
                              a[-4:, :4].reshape(-1, 3), a[-4:, -4:].reshape(-1, 3)])
    ink = np.abs(a - np.median(corners, 0)).max(2) > 22
    r, c = np.where(ink.any(1))[0], np.where(ink.any(0))[0]
    if len(r) > 4 and len(c) > 4:
        a, ink = a[r[0]:r[-1] + 1, c[0]:c[-1] + 1], ink[r[0]:r[-1] + 1, c[0]:c[-1] + 1]
    return a, ink, box


def signature(a):
    """Colour-blind layout signature: edges are taken per channel, so a palette swap keeps them."""
    gx = np.abs(np.diff(a, axis=1, append=a[:, -1:])).max(2)
    gy = np.abs(np.diff(a, axis=0, append=a[-1:])).max(2)
    edge = ((np.maximum(gx, gy) > 18) * 255).astype(np.uint8)
    e = Image.fromarray(edge).resize((G, G), Image.BOX).filter(ImageFilter.GaussianBlur(1))
    s = np.asarray(e, np.float32).ravel()
    s -= s.mean()
    return s / (np.linalg.norm(s) + 1e-9)


def merge_colours(rgb, share, maxn=8, min_share=0.03):
    """Fold near-identical colours together, keep the most common ones. Tints are kept: they are a gradient's steps."""
    rgb, share = np.asarray(rgb, float), np.asarray(share, float).copy()
    alive = np.ones(len(rgb), bool)
    for i in np.argsort(-share):
        if alive[i]:
            for j in range(len(rgb)):
                if j != i and alive[j] and np.linalg.norm(rgb[i] - rgb[j]) < 24:
                    alive[j] = False
                    share[i] += share[j]
    keep = [i for i in np.argsort(-share) if alive[i] and share[i] >= min_share][:maxn]
    return " ".join("#%02x%02x%02x" % tuple(int(v) for v in rgb[i]) for i in keep)


def palette(a, ink):
    """Most common chromatic colours of the figure (greys, near-white and near-black left out)."""
    px = a[ink].reshape(-1, 3)
    px = px[px.max(1) > 45]
    if len(px) < 50:
        return ""
    sat = (px.max(1) - px.min(1)) / np.maximum(px.max(1), 1)
    chrom = px[sat > 0.18]
    if len(chrom) < 0.03 * len(px):
        chrom = px  # greyscale figure
    sub = chrom[np.random.default_rng(0).choice(len(chrom), min(len(chrom), 40000), replace=False)].astype(np.uint8)
    q = Image.fromarray(sub[None]).quantize(16, method=Image.Quantize.MEDIANCUT)
    rgb = np.array(q.getpalette()[:48], float).reshape(-1, 3)  # fewer than 16 entries for flat-colour figures
    return merge_colours(rgb, np.bincount(np.asarray(q).ravel(), minlength=len(rgb)) / sub.shape[0])


def same_palette(p, q, tol=18):
    """Two colour lists are the same palette if every colour of each has a close partner in the other."""
    A, B = (np.array([[int(h[k:k + 2], 16) for k in (1, 3, 5)] for h in x.split()], float) for x in (p, q))
    d = np.linalg.norm(A[:, None] - B[None], axis=2)
    return max(d.min(1).mean(), d.min(0).mean()) < tol


def low_quality(im, box):
    w, h = im.size
    return bool(box > 0.05 or abs(w / h - 9 / 16) < 0.01 or max(w, h) < 1000)


def library():
    """ids, image paths and signatures of everything already in both galleries (cached per gallery)."""
    ids, paths, sigs = [], [], []
    for g in cards.GALLERIES:
        if not g.exists():
            continue
        cache = g / ".cache.npz"
        old = dict(zip(*[np.load(cache, allow_pickle=False)[k] for k in ("ids", "sig")])) if cache.exists() else {}
        gi, gs = [], []
        for p in cards.images(g):
            s = old.get(p.stem)
            if s is None:
                s = signature(_content(Image.open(p))[0])
            gi.append(p.stem)
            gs.append(s)
            paths.append(p)
        if gi:
            np.savez(cache, ids=np.array(gi), sig=np.stack(gs))
        ids += gi
        sigs += gs
    return ids, paths, (np.stack(sigs) if sigs else np.zeros((0, G * G), np.float32))


def add_palette(card, colours):
    if not colours or not card.exists():
        return
    meta, body = cards.read(card)
    if not any(same_palette(colours, p) for p in meta.get("palettes", [])):
        meta.setdefault("palettes", []).append(colours)
        cards.write(card, meta, body)


def register(src, gallery, dedup=True):
    """Returns (status, id, other_id): added / variant / exists."""
    src, gallery = Path(src), Path(gallery)
    ident = src.stem
    dest = gallery / f"{ident}.png"
    in_place = src.parent.resolve() == gallery.resolve()
    if in_place:
        dest = src
    elif dest.exists():
        return "exists", ident, None
    im = Image.open(src)
    a, ink, box = _content(im)
    sig, colours = signature(a), palette(a, ink)
    maybe = None
    if dedup:
        ids, _, sigs = library()
        if len(ids):
            sim = sigs @ sig
            sim[[i for i, x in enumerate(ids) if x == ident]] = -1
            k = int(sim.argmax())
            if sim[k] >= SAME:
                add_palette(cards.find(ids[k]).with_suffix(".md"), colours)
                return "variant", ident, ids[k]
            if sim[k] >= MAYBE:
                maybe = ids[k]
    if not in_place:
        im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(dest, optimize=True)
    card = dest.with_suffix(".md")
    if not card.exists():
        cards.write(card, {"title": "", "kind": "", "purpose": [], "data": "", "loudness": "", "caveat": "",
                           "low_quality": low_quality(Image.open(src), box), "code": "",
                           "appreciated": False, "edited": False, "palettes": [colours] if colours else []})
    return "added", ident, maybe


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--gallery", default="gallery-local")
    ap.add_argument("--no-dedup", action="store_true")
    args = ap.parse_args()
    gallery = cards.ROOT / args.gallery
    gallery.mkdir(exist_ok=True)
    if args.paths:
        todo = [f for p in map(Path, args.paths)
                for f in (sorted(p.iterdir()) if p.is_dir() else [p]) if f.suffix.lower() in cards.IMG_EXT]
    else:  # sync: images dropped straight into the gallery without a card
        todo = [p for p in cards.images(gallery) if not p.with_suffix(".md").exists()]
    added = variants = 0
    for f in todo:
        status, ident, other = register(f, gallery, dedup=not args.no_dedup)
        if status == "variant":
            variants += 1
            print(f"换色变体  {ident} ≈ {other}（未入库，配色已记到 {other} 的卡片）")
        elif status == "added":
            added += 1
            print(f"入库      {ident}" + (f"   ⚠ 可能与 {other} 重复，请对照看一眼" if other else ""))
        else:
            print(f"已存在    {ident}")
    print(f"\n新入库 {added} 张，换色变体 {variants} 张。下一步：给 appreciated: false 的卡片做鉴赏，然后运行 build_index.py")


if __name__ == "__main__":
    main()
