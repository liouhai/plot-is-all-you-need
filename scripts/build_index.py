"""Rebuild INDEX.md in each gallery from the cards. One row per figure; read this before opening images.

    python scripts/build_index.py            # rebuild, report orphans and cards waiting for appreciation
    python scripts/build_index.py --prune    # also delete cards whose image was removed
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards


def row(img, meta):
    flags = []
    if meta.get("kind") and meta["kind"] != "数据图":
        flags.append(meta["kind"])
    if meta.get("low_quality"):
        flags.append("低质量")
    if meta.get("code"):
        flags.append("有代码")
    if meta.get("caveat"):
        flags.append("有提醒")
    n = len(meta.get("palettes", []))
    if n > 1:
        flags.append(f"{n}套配色")
    cell = lambda v: str(v).replace("|", "/").replace("\n", " ")
    return (f"| {img.stem} | {cell(meta.get('title', ''))} | {cell('、'.join(meta.get('purpose', [])))} | "
            f"{cell(meta.get('data', ''))} | {cell(meta.get('loudness', ''))} | {cell(' '.join(flags))} |")


def build(gallery, prune=False):
    imgs = {p.stem: p for p in cards.images(gallery)}
    for card in sorted(gallery.glob("*.md")):
        if card.name != "INDEX.md" and card.stem not in imgs:
            print(f"孤儿卡片（图已删除）: {card.relative_to(cards.ROOT)}" + ("  → 已清理" if prune else ""))
            if prune:
                card.unlink()
    done, pending, nocard = [], [], []
    for stem, img in imgs.items():
        card = img.with_suffix(".md")
        if not card.exists():
            nocard.append(stem)
            continue
        meta, _ = cards.read(card)
        (done if meta.get("appreciated") else pending).append((img, meta))
    bad = [(i.stem, msg) for i, m in done for msg in cards.problems(m)]
    for stem, msg in bad:
        print(f"⚠ {gallery.name}/{stem}: {msg}")
    done.sort(key=lambda x: (x[1].get("kind", ""), (x[1].get("purpose") or [""])[0], str(x[1].get("loudness", ""))))
    tally = Counter(w for _, m in done for w in m.get("purpose") or [])
    lines = [f"# {gallery.name} 索引", "",
             f"共 {len(imgs)} 张，已鉴赏 {len(done)} 张。张扬度 1=平铺直叙，3=中规中矩，5=花里胡哨。",
             "先按「用途」「需要的数据」筛出候选，再打开图片和卡片确认。",
             "用途词：" + "、".join(f"{w} {n}" for w, n in tally.most_common()), "",
             "| id | 标题 | 用途 | 需要的数据 | 张扬度 | 标记 |", "|---|---|---|---|---|---|"]
    lines += [row(i, m) for i, m in done]
    if pending:
        lines += ["", f"## 待鉴赏（{len(pending)} 张，卡片还是空的）", "", ", ".join(i.stem for i, _ in pending)]
    (gallery / "INDEX.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{gallery.name}: {len(imgs)} 张图，已鉴赏 {len(done)}，待鉴赏 {len(pending)}"
          + (f"，无卡片 {len(nocard)}（运行 ingest.py 同步）" if nocard else "")
          + (f"，⚠ {len(bad)} 处字段不合词表，请按上面的提示改卡片" if bad else ""))


if __name__ == "__main__":
    for g in cards.GALLERIES:
        if g.exists():
            build(g, prune="--prune" in sys.argv)
