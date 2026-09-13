# infographic-generator

Claude Code skill: topic → Instagram carousel, rendered from HTML/CSS in
headless Chromium. No image model, no external API, no key.

## Setup

```bash
bash .claude/skills/infographic-generator/scripts/setup.sh
```

Installs `playwright` + `jinja2` + `pillow`, installs headless Chromium, and
downloads the Poppins font weights into `resources/fonts/`.

## Use

Ask Claude for a carousel ("make a carousel about X", "carousel it", or just
"make a carousel" to have it pick an unused topic from `./src`). Claude writes
`output/<slug>/slides.json`, then runs:

```bash
python3 .claude/skills/infographic-generator/scripts/render_carousel.py <slug>
```

Output lands in `output/<slug>/`: `01.jpg` … `NN.jpg` (2160x2700),
`contact-sheet.jpg`, and `caption.md`. Re-render one slide after an edit with
`--slide N`.

Then publish it to the Instagram Content Calendar in Notion:

```bash
python3 .claude/skills/infographic-generator/scripts/notion_publish.py <slug>
```

Requires `NOTION_TOKEN` and `NOTION_DATABASE_ID` (env vars or a `.env` file
at the project root). This creates a database page, uploads the slides as
attachments in order, fills in the caption and slide count, and sets Status
to `Ready for review` — never `Approved`, which stays a human decision.
