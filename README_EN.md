# Plot Is All You Need

[中文](README.md) | **English**

[![Plot Is All You Need promo](media/promo.gif)](media/promo.mp4)

<sub>Click for the full 48-second version with sound (captions in Chinese)</sub>

Tired of having brilliant experimental data but no figure that makes people look twice?
Tired of having good taste and knowing what looks good, while AI keeps drawing plain, forgettable figures?
Tired of admiring good figures all the time and failing to recall them when you need one?
Tired of having a good reference in hand and struggling to describe it to an AI?
This skill is built for exactly these problems. Plot Is All You Need: you only look, pick what looks good, and leave everything behind the scenes to the agent. It is a skill that has the agent draw figures by **looking at figures** rather than by following rules.

Writing plotting prompts is tiring. You have to describe which chart, which style and which colours you want, and most people cannot put that into words; they only know whether they like something once they see it.
This skill works the other way round. It ships with a gallery, like the show homes you visit before renovating. You ask for a figure, and it lays out suitable examples on a sample sheet for you to choose from.
You can say "the layout of B with the colours of E". It draws that with your data, then puts the result next to the example for you to check.

**The gallery is the taste.** Delete the figures you dislike, add the ones you like, and what gets drawn changes with it.

The public gallery `gallery/` currently holds **95 figures**: 14 drawn in this repository, with plotting code, and 81 from open-access papers. They range from plain to flamboyant, and each has an appreciation card. Another 350 entries have a card but no image (`gallery/cards-only/`) and serve as a text reference.

> The skill's own files (`SKILL.md`, the stage guides, the gallery cards) are written in Chinese. This page is a translation of [README.md](README.md).

## What a session looks like

- **You have data**: the agent screens the gallery and looks at the candidates itself, then draws 4–6 draft versions directly with your data
  and puts them on one sample sheet for you to choose from. What you see are **drafts of your own data**, not the original gallery figures.
  Each draft notes which gallery figure it follows; ask if you want to see the original.
- **You have no data, or only want to browse**: the agent lays out original gallery figures on a sample sheet.
- You choose the same way in both cases: say "C", or combine, for example "the layout of B + the colours of E".
  Every round contains both figures close to your past taste and figures the agent recommends for this audience, each labelled as such.
- Once you have chosen, the agent produces the final PNG, PDF and plotting script, then shows the result next to the example for you to check.

## Four stages

| | |
|---|---|
| **Appreciation** | The agent studies every figure in the gallery and writes a card for it. You can edit the cards directly. |
| **Resonance** | Candidates are laid out on a sample sheet. Each round has figures close to your taste and figures the agent recommends for the audience; you decide. |
| **Rendition** | The chosen figure is drawn with your data. The agent handles the data wrangling. |
| **Appraisal** | The agent checks its work against the example, then shows you both side by side. Results you like can go back into the gallery. |

## Installation

### Claude Code

```bash
git clone https://github.com/liouhai/plot-is-all-you-need.git ~/.claude/skills/plot-is-all-you-need
pip install -r ~/.claude/skills/plot-is-all-you-need/requirements.txt
```

### Codex

```bash
git clone https://github.com/liouhai/plot-is-all-you-need.git ~/.agents/skills/plot-is-all-you-need
pip install -r ~/.agents/skills/plot-is-all-you-need/requirements.txt
```

Codex picks up newly installed skills automatically; restart Codex if it does not appear. Type `/skills` to list installed skills, or `$plot-is-all-you-need` to call this one by name.

### Both

Clone once and symlink the other side, so both share one gallery and one taste record:

```bash
ln -s ~/.claude/skills/plot-is-all-you-need ~/.agents/skills/plot-is-all-you-need
```

Once installed, tell the agent something like "turn this data into a figure".

### Consider disabling scipilot-figure-skill

If you also have `scipilot-figure-skill` installed, consider disabling it. It explicitly forbids some chart types, such as pie charts, 3D charts and dual y-axes,
and these can work very well in the right setting. When both skills trigger, they give conflicting advice.
This skill takes a different approach: every figure is shown as usual, with a one-line caution where needed, and you decide.

## Maintaining your own gallery

`gallery/` is published with the repository; `gallery-local/` stays on your machine and is never uploaded. Your gallery supplies the references for selecting and drawing figures with this skill.
Before adding someone else's figure to the public `gallery/`, read [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Remove figures**: delete the images in `gallery/`, then ask the agent to "tidy the gallery".
- **Add figures**: hand the images to the agent and say "add these to the gallery", or run `python scripts/ingest.py <image or folder>`.
  Duplicates are removed on the way in. A figure that only differs in colour is not stored again; its palette is recorded on the card of the figure already there.
- **Edit cards**: the `.md` file next to each image is the agent's understanding of it. If it is wrong, edit it and set `edited` to `true`.
- **Have the agent collect in bulk**: just say "find 50 more figures from such-and-such field". The limits for collecting (kinds of figure, how many per paper, which words a card may use)
  are written in `stages/1-appreciation.md`; `build_index.py` checks every card and prints ⚠ for words outside the vocabulary.

## The taste record, taste.md

`taste.md` records what you have chosen before. The repository does not contain this file; the agent creates it in the skill directory after your first choice.
- **When it is written**: when you choose from a sample sheet or clearly reject a way of drawing, and again after the final figure is accepted, the agent appends one line.
- **What is written**: date, audience, what you chose, what you rejected, a one-sentence summary. For example:
  `2026-10-04 | journal main text | layout of <id> + colours of <id> | rejected 3D and large gradients | wants "quiet but not dull"`
- **How it is used**: on the next sample sheet, the agent uses it to pick the figures labelled "close to your taste". It is never used to exclude a figure, and the same sheet always also contains the agent's own recommendations for the audience.
- **You can edit it**: it is a plain text file. Correct it if it is wrong, or empty or delete it to start over.

## Measured cost

A record of one real session (Claude Opus 5.5, Claude Code desktop app), for reference only.
The task was to try several other forms for a 3×3 profile figure from a paper. Claude found the data and the original script on a remote server,
screened 12 candidates out of a gallery of 367 figures, drew 5 draft forms with the real data, and handed over a sample sheet.
The record ends when the sample sheet was delivered; it does not include the final polishing and checking.

| | |
|---|---|
| Time | 6 min 18 s |
| Model calls | 21 |
| Output | 21k tokens |
| Context | grew from 68k to 158k tokens, an increase of 90k |
| Pro plan 5-hour limit | about 3% |

Where the 90k added tokens went:

| Use | Tokens | Share |
|---|---|---|
| Looking at images (candidate sheet, original figure, 5 drafts; 8 images, about 4,500 each) | 36k | 40% |
| Claude's output (plotting script about 9k, the rest reasoning and replies) | 20k | 22% |
| Finding the data and reading the original plotting script | 18k | 20% |
| Skill documents and screening the index | 12k | 13% |
| Other | 4k | 5% |

## Layout

```
SKILL.md            entry point of the skill
stages/             detailed guide for each of the four stages
scripts/            ingesting, indexing, building sample sheets (see "Scripts" below)
gallery/            the public gallery (cards-only/ holds entries that have a card but no image)
gallery-local/      private local gallery, not uploaded
THIRD_PARTY_NOTICES.md  figure sources, copyright and licences (everything copyright-related lives here; in Chinese)
```

## Scripts

You normally do not run these yourself; the agent calls them when needed. To maintain the gallery by hand, run them from the skill directory.

| Script | What it does | When to use it |
|---|---|---|
| `ingest.py` | Adds figures to the gallery: scales the long side down to 2000 px, removes duplicates, records the palette of recoloured variants on the existing card, flags low-quality screenshots, creates an empty card | When adding figures |
| `build_index.py` | Rebuilds `INDEX.md` (one row per figure) from all cards and checks that each card's kind, purpose words and loudness are within the allowed values; with `--prune` it also removes cards whose image has been deleted | After adding or removing figures, or editing cards |
| `contact_sheet.py` | Puts figures together for viewing: `sheet` builds a sample sheet labelled A, B, C; `compare` puts an example and a result side by side; `swatches` lists all palettes recorded for a figure | When choosing and when checking results |
| `cards.py` | Shared functions for reading and writing cards, plus the lists of kinds and purpose words a card may use; used by the three scripts above, not run directly | — |

```bash
python scripts/ingest.py <image or folder>              # goes to gallery-local/ by default; add --gallery gallery for the public gallery
python scripts/build_index.py                           # rebuild the index; add --prune to remove orphan cards
python scripts/contact_sheet.py sheet --out sheet.png <id> <id> ...
python scripts/contact_sheet.py compare --out cmp.png --labels "example,result" <id> <result.png>
python scripts/contact_sheet.py swatches --out pal.png <id>
```

## Licence

[MIT](LICENSE). For the sources and licences of third-party figures in the gallery, see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
