"""Read/write appreciation cards: `<id>.md` next to `<id>.png`, frontmatter + free text.

Frontmatter is a tiny YAML subset (scalars, inline [a, b] lists, and one dash-list) so the
scripts need no YAML dependency and humans can edit cards in any text editor.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GALLERIES = [ROOT / "gallery", ROOT / "gallery-local"]
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ORDER = ["title", "kind", "purpose", "data", "loudness", "caveat", "low_quality",
         "source", "code", "appreciated", "edited", "palettes"]
KINDS = ["数据图", "流程图", "示意图", "组合图"]
PURPOSES = ["分布", "组间比较", "相关关系", "趋势变化", "构成占比", "排序", "特征重要性", "模型解释", "模型性能",
            "空间分布", "网络与流向", "多指标综合", "层次结构", "集合关系", "流程示意", "不确定性"]
BODY = """**评价**：（待鉴赏）

**部件亮点**
- 结构布局：
- 图形元素：
- 配色：
- 文字与标注：
- 装饰细节：
- 图例与色条：
"""


def _scalar(v):
    v = v.strip()
    if v.startswith("[") and v.endswith("]"):
        return [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
    if v in ("true", "false"):
        return v == "true"
    if v.lstrip("-").isdigit():
        return int(v)
    return v.strip("\"'")


def read(path):
    text = Path(path).read_text(encoding="utf-8")
    meta, body = {}, text
    if text.startswith("---"):
        head, _, body = text[3:].partition("\n---")
        key = None
        for line in head.splitlines():
            if line.startswith("  - ") and key:
                meta.setdefault(key, [])
                if not isinstance(meta[key], list):
                    meta[key] = []
                meta[key].append(line[4:].strip().strip("\"'"))
            elif ":" in line:
                key, _, v = line.partition(":")
                key = key.strip()
                meta[key] = _scalar(v) if v.strip() else ""
    return meta, body.lstrip("\n")


def problems(meta):
    """What is outside the card's fixed vocabulary; an empty list means the card is fine."""
    out = []
    if meta.get("kind") not in KINDS:
        out.append(f"kind「{meta.get('kind')}」不在 {'/'.join(KINDS)} 之内")
    bad = [t for t in meta.get("purpose") or [] if t not in PURPOSES]
    if bad or not meta.get("purpose"):
        out.append(f"purpose {bad or '为空'} 不在词表内（词表见 scripts/cards.py 的 PURPOSES）")
    if meta.get("loudness") not in (1, 2, 3, 4, 5):
        out.append(f"loudness「{meta.get('loudness')}」应为 1–5 的整数")
    return out


def write(path, meta, body=BODY):
    out = ["---"]
    for k in ORDER + [k for k in meta if k not in ORDER]:
        if k not in meta:
            continue
        v = meta[k]
        if k == "palettes":
            out.append("palettes:")
            out += [f'  - "{p}"' for p in v]
        elif isinstance(v, list):
            out.append(f"{k}: [{', '.join(v)}]")
        elif isinstance(v, bool):
            out.append(f"{k}: {'true' if v else 'false'}")
        else:
            out.append(f"{k}: {v}")
    Path(path).write_text("\n".join(out) + "\n---\n\n" + body.strip() + "\n", encoding="utf-8")


def images(gallery):
    return sorted(p for p in Path(gallery).iterdir() if p.suffix.lower() in IMG_EXT and not p.name.startswith("."))


def find(ident):
    """Resolve an id (or path) to its image in either gallery."""
    p = Path(ident)
    if p.exists():
        return p
    for g in GALLERIES:
        for ext in IMG_EXT:
            if (g / f"{p.stem}{ext}").exists():
                return g / f"{p.stem}{ext}"
    raise FileNotFoundError(ident)


if __name__ == "__main__":  # self-check: round trip
    import tempfile
    m = {"title": "环形柱状图: 测试", "kind": "数据图", "purpose": ["比较", "构成"], "loudness": 4,
         "low_quality": False, "code": "", "palettes": ["#aa0000 #00bb00", "#123456 #abcdef"]}
    with tempfile.TemporaryDirectory() as d:
        write(Path(d) / "x.md", m, "正文")
        m2, b = read(Path(d) / "x.md")
    assert m2 == m and b.strip() == "正文", (m2, b)
    print("cards ok")
