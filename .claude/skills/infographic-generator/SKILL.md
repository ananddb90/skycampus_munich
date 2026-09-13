---
name: infographic-generator
description: Turns a topic — or a randomly picked, not-yet-used chapter from the books in ./src — into a finished Instagram carousel for Skycampus Munich (an AI automation agency, posting under @skycampusmunich): 4-9 slides at 1080x1350, rendered from a single HTML/CSS template in headless Chromium and screenshotted at 2x (2160x2700), plus a matching caption. Light, warm wellness/yoga-quote-card look — a curiosity-hook cover, a short story-like answer, a soft close — with a rotating pastel background style (solid or two-tone) and accent color per post. No image-generation model, no external API, no key. Multi-slide carousels only — for a single-image illustrated quote post, use quote-poster-generator instead. Trigger on phrasings like "make a carousel about X", "infographic for X", "turn this into an Instagram carousel", "carousel slides on X", "carousel it" after a pasted topic, or a bare request for a new carousel/infographic with no topic given (in which case pick one per Step 0 below).
---

# Infographic generator

Produces a light, wellness-quote-card style Instagram carousel: bold
statement per slide on a soft pastel background, `@skycampusmunich` handle
on every slide. Copy first (`slides.json`), then a deterministic render pass
(Playwright + Chromium, local fonts, no network). You write the copy; the
script renders it and refuses to ship anything that doesn't fit or breaks
the one-accent-per-slide rule.

## One-time setup (only if not already done)

```bash
bash .claude/skills/infographic-generator/scripts/setup.sh
```

Installs `playwright`, `jinja2`, `pillow`, `requests`, installs headless
Chromium, and downloads the Poppins weight files into `resources/fonts/`.

Also requires `NOTION_TOKEN` and `NOTION_DATABASE_ID` (a Notion internal
integration secret, and the id of the Instagram Content Calendar database,
shared with that integration) — either exported in the environment or set in
a `.env` file at the project root:

```
NOTION_TOKEN=ntn_...
NOTION_DATABASE_ID=...
```

Used by Step 4 to publish each finished carousel to Notion.

## Step 0 — pick a topic (only when the user didn't give one)

1. List the books under `./src` (currently PDFs — extract with the `pdf`
   skill, e.g. `pypdf`: read `reader.outline` for the chapter list, and
   `reader.get_destination_page_number(item)` to get each chapter's start
   page so you can extract just that chapter's text).
2. Read `output/used_topics.json` at the project root (create it with `{}`
   if absent — note it also stores background-rotation state, see below,
   so don't blow away the `"backgrounds"` key). It maps each book's path →
   list of `{topic, slug, date}` already produced.
3. Pick one chapter/topic at random from that book that isn't already in
   its list. If a chapter was picked yesterday and today's random draw
   lands on it again, re-roll — never reuse a chapter until every other
   chapter in that book has been used at least once.
4. Read the full text of that chapter and get the gist: what's the single
   idea worth carrying into a carousel? Ignore incidental content (dated
   news bulletins, unrelated addenda) that sometimes trails a chapter in
   these books.
5. After Step 1 below (copy written and rendered), append
   `{topic, slug, date}` to that book's list in `output/used_topics.json`.

If the user gave you a topic directly, skip topic selection — just slugify
it and go straight to Step 1.

## Step 1 — write the copy (`output/<slug>/slides.json`)

This file is the single source of truth. The renderer reads nothing else.
Render immediately after writing it — rendering is free, there's no
approval gate before that. Show the user the copy and the contact sheet
together and expect edits to either one.

Structure — every slide is one bold statement, closing adds a `cta`:

```json
{
  "topic": "Human readable topic",
  "slug": "kebab-case-slug",
  "slides": [
    { "role": "cover", "text": "Have you ever wondered why testing feels safer than trusting?" },
    { "role": "body", "text": "Testing is just doubt wearing a *disguise*." },
    { "role": "body", "text": "You only question what you haven't fully *trusted* yet." },
    { "role": "closing", "text": "So stop testing. Start trusting", "cta": "That's the whole secret." }
  ]
}
```

Background style and accent color are optional — omit them and the renderer
auto-picks (and writes its choice back into this file):

- **Style**: `"solid"` (one flat pastel) or `"duo"` (a hard-edged two-tone
  split, no gradient) — alternated so you don't get the same style twice in
  a row.
- **Background color(s)**: for solid, one tone from `BACKGROUND_PALETTE`;
  for duo, a harmonious pair from `DUO_PALETTE` plus a split ratio. Never
  repeats the immediately-previous pick.
- **Accent**: one tone from `ACCENT_PALETTE`, also rotated. It's still one
  accent color for the *whole* carousel — every slide in one post shares it.

Only set these yourself to force a specific look: `"background": "#hex"`
for solid, or `"background_top"` + `"background_bottom"` (+ optional
`"split_ratio"`, default 34) for duo, and/or `"accent": "#hex"`.

**Content shape — question, then story, then resolution:**

- **Cover**: raises curiosity. A direct question ("Have you ever
  wondered...", "What if...", "Why does...") or a provocative claim that
  makes someone want to swipe. Never the answer itself.
- **Body slides**: unfold the answer like a short story, one beat per
  slide — not fragmented aphorisms, not a heading-plus-caption information
  card. Each slide's `text` should read like the next sentence in a train
  of thought that started on the cover. 2-7 body slides. **Vary the total
  slide count post to post** (4, 5, 6, 7, 8, 9 — don't default to 5 every
  time); let the idea's natural length decide, not habit.
- **Closing**: resolves the question in one line, plus a soft `cta` —
  an invitation, not a pitch ("Something to sit with today.", "Notice it
  next time it happens."). No "DM me" / "link in bio" unless the user asks.

**Rules the renderer enforces** (don't fight them — fix the copy instead):

- **Slide count**: 4-9. Slide 1 is always `"role": "cover"`, the last slide
  is always `"role": "closing"`, everything between is `"role": "body"`.
  Don't pad to hit a number.
- **Length per slide**: `text` can wrap up to ~7 lines at the shrink floor,
  but aim for 1-4 — this is a quote card, not a paragraph. If an idea needs
  more room, split it into two slides.
- **Accent markup**: wrap at most one word or short phrase per slide in
  `*asterisks*` to color it — optional, not required on every slide. Two
  in one slide gets refused. On the closing slide, don't add one: the
  small dot after the line is already that slide's accent.

## Step 2 — render

```bash
python3 .claude/skills/infographic-generator/scripts/render_carousel.py <slug>
```

This validates `slides.json`, renders every slide to
`output/<slug>/html/NN.html`, screenshots each to `output/<slug>/NN.jpg`
(2160x2700 JPEG, quality 92), and builds `output/<slug>/contact-sheet.jpg`.
It prints the final font size and line count per slide, and stops with the
specific slide if the text still overflows its line limit at the minimum
font size — the fix is always the copy, never a smaller font floor.

To re-render one slide after a copy tweak: add `--slide N` (this keeps the
same background the first render picked). To render at a different scale:
`--scale 1` (default `2`).

**Before showing the user anything**, open `contact-sheet.jpg` yourself
(Read tool) and sanity-check it: nothing clipped, at most one accent per
slide, the question-then-story flow actually reads as a sequence, the
handle sits in the same spot on every slide. Fix and re-render if not.

## Step 3 — caption

Write `output/<slug>/caption.md`: the Instagram caption in a warm,
plain-spoken voice, then a blank line, then hashtags.

- Opening line should be the same hook as the cover question — it's what
  Instagram shows in the truncated preview before "...more".
- Roughly 60-120 words total.
- 8-15 hashtags, mixed reach (a few broad wellness tags, a few
  niche/branded), no hashtag walls, no emoji anywhere.
- **Always include 2-3 Munich/local-community hashtags** in the mix (not on
  top of the 8-15 — they count toward that total), e.g. `#MunichYoga`
  `#MünchenYoga` `#MunichMeditation` `#MunichWellness` `#MunichCommunity`.
  Vary which ones post to post rather than always using the same three;
  this is a Munich-based studio/agency account, and local discovery matters
  as much as broad wellness reach.

## Step 4 — publish to the Notion content calendar

```bash
python3 .claude/skills/infographic-generator/scripts/notion_publish.py <slug>
```

Creates one page in the **Instagram Content Calendar** Notion database,
uploads `output/<slug>/01.jpg` … `NN.jpg` to it as file attachments in slide
order, and fills in Caption (from `caption.md`) and Slide count. It also
inserts the same images as full-size image blocks in the page body, in
order — the **Slides** property only ever shows small thumbnail chips in
Notion (in the database table, and in the properties section of side peek),
so the body is what gives you a big, scrollable view slide-by-slide when you
open or side-peek the page. Only after all slides upload successfully does
it set **Status** to `Ready for review`.

**Never set Status to `Approved` from this skill, or from any script it
calls.** Approval is a human decision made by reviewing the row in Notion.
`Approved` is the only status a future posting automation is ever allowed to
act on — this skill's job ends at `Ready for review`.

## Design system (for template edits only — don't touch this per-carousel)

The layout (type, margins, folio/handle placement) is fixed on purpose so
every carousel reads as the same account. What's *meant* to vary post to
post, on purpose, so the feed doesn't look repetitive: background style,
background color(s), and accent color — see Step 1 above. Three independent
rotations, each tracked in `output/used_topics.json` and each avoiding its
own immediately-previous pick, so consecutive posts essentially never look
identical even before the copy differs.

- Background: either `"solid"` (one flat color, `BACKGROUND_PALETTE`) or
  `"duo"` (two flat colors with a hard-edged split, `DUO_PALETTE` +
  `SPLIT_RATIOS`, both in `scripts/render_carousel.py`). Never a gradient —
  duo is a sharp edge between two flat fills, not a blend.
- Ink: near-black `#1C1A17` for the statement text; the same color at
  reduced opacity for the folio and the soft CTA line. Accent: one tone
  from `ACCENT_PALETTE` (muted terracotta, sage, umber, indigo, plum) per
  carousel — every slide *within* a post shares the same accent; it's the
  accent that rotates *between* posts, not the ink or the layout.
- Type: Poppins ExtraBold, uppercase, for every slide's main statement
  (76px, shrinking to a 52px floor, line-height 1.1). Poppins Medium,
  sentence case, for the closing slide's soft CTA (27px). Poppins
  Medium/SemiBold for the folio (`NN / NN`, top right) and the
  `— @skycampusmunich` handle (bottom right). Never swap families.
- Layout: the statement block is vertically centered on the page (text
  itself stays left-aligned, only the block as a whole is centered).
  Margins: 72px sides, 88px top, 96px bottom. No grid columns, no
  hairlines, no cards.
- Forbidden anywhere: emoji, drop shadows, glows, gradients, boxes/cards/
  panels, icons, watermarks, illustrations, animation, and any text beyond
  the copy plus the folio/handle. (Illustrated single-image posts are a
  different format — see [quote-poster-generator](../quote-poster-generator/SKILL.md).)

## Files

- `template/slide.html` — the only template, all CSS inline, `@font-face`
  pointing at local files in `resources/fonts/`.
- `scripts/render_carousel.py` — validate → pick background → render →
  screenshot → contact sheet. Reads `output/<slug>/slides.json`, writes
  into `output/<slug>/`, and reads/writes `output/used_topics.json` for
  both chapter history and background rotation.
- `scripts/notion_publish.py` — creates the Notion database page, uploads
  `output/<slug>/NN.jpg` in order, fills in Caption/Slide count, sets Status
  to `Ready for review`. Reads `NOTION_TOKEN`/`NOTION_DATABASE_ID` from the
  environment or the project root's `.env`.
- `scripts/setup.sh` — one-time dependency/font install.
- `resources/fonts/` — Poppins ExtraBold/SemiBold/Medium, OFL, fetched by
  `setup.sh`.
