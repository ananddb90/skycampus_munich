# quote-poster-generator

Claude Code skill: one-line quote → single illustrated Instagram poster.
The illustration is a bespoke Canva-generated background, matched to each
specific quote in an established visual style (via the Canva MCP connector,
with a human picking the result every time — see SKILL.md); the quote text
is always overlaid separately in the account's own fonts (Caveat +
Poppins), rendered in headless Chromium. Two original illustrations remain
in `resources/backgrounds/` as a fast fallback when a bespoke generation
isn't wanted. Single image only — for multi-slide carousels, see the
sibling [infographic-generator](../infographic-generator/README.md) skill.

Quotes attributed to Sri Sri Ravi Shankar must come from
[his Goodreads quotes page](https://www.goodreads.com/author/quotes/106453.Ravi_Shankar)
or another clearly public, reputable source — never fabricated, and never
attributed to anyone else.

## Setup

```bash
bash .claude/skills/quote-poster-generator/scripts/setup.sh
```

Installs `playwright` + `jinja2` + `pillow` + `requests`, installs headless
Chromium, and downloads the Caveat font plus a copy of Poppins SemiBold into
`resources/fonts/`.

## Use

Ask Claude for a poster ("make a quote poster about X", "single-liner post
with illustration", or just "make a poster" to have it pick an unused topic
from `./src`). Claude writes `output/<slug>/poster.json`, then runs:

```bash
python3 .claude/skills/quote-poster-generator/scripts/render_poster.py <slug>
```

Output lands in `output/<slug>/`: `01.jpg` (2160x2700), `poster.html`,
`slides.json` (for the publish step), and `caption.md`.

Then publish it to the Instagram Content Calendar in Notion — this reuses
infographic-generator's script directly (no separate copy of that logic):

```bash
python3 .claude/skills/infographic-generator/scripts/notion_publish.py <slug>
```

Requires `NOTION_TOKEN` and `NOTION_DATABASE_ID` (env vars or the project
root's `.env` — same ones infographic-generator uses). Sets Status to
`Ready for review` — never `Approved`, which stays a human decision.
