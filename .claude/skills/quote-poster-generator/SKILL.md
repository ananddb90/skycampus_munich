---
name: quote-poster-generator
description: Turns a short single-line insight — a verified public quote from Sri Sri Ravi Shankar, or a randomly picked, not-yet-used chapter from the books in ./src — into one finished Instagram post for Skycampus Munich (posting under @skycampusmunich): a single 1080x1350 illustrated quote poster (not a carousel), rendered from a single HTML/CSS template in headless Chromium and screenshotted at 2x (2160x2700), plus a matching caption. Warm hand-drawn-mood look — a bespoke Canva-generated nature illustration matched to that specific quote (earthy cream/sage/terracotta tones, a meditating or reaching figure, botanical branches, sun) as the background, with a Caveat handwritten quote overlaid using the account's own font system (no Canva text layers used). Single-image, single-liner posts only — for a multi-slide carousel, use infographic-generator instead. Trigger on phrasings like "make a quote poster about X", "single-liner post with illustration", "one-image post like [reference]", "illustrated quote card", "quote from Sri Sri Ravi Shankar", or a bare request for a new poster with no quote given (in which case pick one per Step 0 below).
---

# Quote poster generator

Produces one illustrated quote poster: a short handwritten-style line over a
warm nature illustration generated to match that specific quote,
`@skycampusmunich` handle at the bottom. This is a **single image**, not a
carousel — it's the format for a single striking line, not a multi-slide
story. For multi-slide content use the
[infographic-generator](../infographic-generator/SKILL.md) skill instead;
don't mix the two up, and don't add multi-slide support here.

Copy first (`poster.json`), then illustration generation, then a
deterministic render pass (Playwright + Chromium, local fonts) — same
philosophy as infographic-generator: you write the copy, the script renders
it and refuses to ship anything that overflows.

## Two content modes — know which one you're in

- **Attributed quote** (his actual words): triggered by "quote from Sri Sri
  Ravi Shankar", "a Ravi Shankar quote", etc. See the sourcing rule below —
  this is the only case where the poster names an author.
- **Brand-voice single-liner** (our own paraphrase of a book insight): the
  default when the user just asks for "a poster about X" or a bare "make a
  poster" with no source named. Written in our own casual, curiosity-driven
  voice (see Step 0/1), no attribution line — same as infographic-generator's
  carousel copy voice.

Don't blend them: never present a paraphrase as if it were his literal
quote, and never attribute an invented line to him.

## Quote sourcing rule (attributed-quote mode only)

When the post is framed as "a quote from Sri Sri Ravi Shankar" (or similar),
the quote text must come from one of:

- https://www.goodreads.com/author/quotes/106453.Ravi_Shankar
- another clearly public, reputable source that explicitly attributes the
  exact wording to him (his own published books, his official site, etc.)

**Never** use a quote from any other public figure for this account's
attributed-quote format, and **never** fabricate or paraphrase wording and
present it as a direct quote — fetch the source, copy the exact wording,
attribute it as `— Sri Sri Ravi Shankar` in the `subline`. If a fetched
quote is long, pick a different, shorter one from the same source rather
than trimming/editing his wording.

This rule is specific to *this account's* attributed-quote posts — it has
no bearing on the brand-voice mode above, which was never attributed to him
in the first place.

## Where the illustrations come from

Early versions of this skill hand-drew the illustrations as simple SVG
silhouettes (looked bad), then moved to picking from a tiny fixed library of
2 pre-made Canva illustrations (felt repetitive — every post looked like one
of the same two images). **The current default is a bespoke illustration
generated fresh for every poster**, in the established visual style, matched
to that specific quote's imagery — done via the Canva MCP connector, with
you reviewing and picking the result, every time:

**The `generate-design` tool has no seed/style/variety parameter — the
`query` text is the only lever that controls how different one poster
looks from the last.** Early runs of this step reused a style anchor that
named two specific past compositions ("a seated meditating figure beside a
branch", "a standing figure reaching toward the sun over rolling hills")
nearly verbatim on every call. That pins the model to imitate those same
two poses forever, which is exactly why posts started looking repetitive
and uncreative even though the prompt was technically "per quote." Fixed
by separating **palette/medium** (stays constant, for brand consistency)
from **composition** (must actively rotate, for variety):

1. Build the `query` from three parts:
   - **The fixed palette/medium anchor** (copy this verbatim — this is what
     makes posts recognizably the same account): "Minimalist nature-
     inspired illustration in a warm, hand-drawn folk-art style. Soft
     cream/sage pastel background, earthy terracotta figure, sage green
     botanical branch line art, small soft-gold sun accent. Gentle, warm,
     minimalist line art."
   - **A composition rolled from the motif bank, not invented fresh and not
     defaulted to the same pose every time.** Read
     `output/used_topics.json` → `"poster_motifs"` (a `{last_pose,
     last_setting, history}` object, same rotation pattern as
     infographic-generator's backgrounds/accents — create it with `{}` if
     absent). Pick one **pose** and one **setting/secondary-element** below
     that together (a) fit the quote's imagery and (b) aren't the pair used
     last time:
     - Pose family: seated in meditation, standing reaching upward, walking
       forward, kneeling, cupped open hands, lying back looking up,
       releasing something to the wind, planting/tending something, a
       distant walking silhouette, two small figures side by side.
     - Setting/secondary element: a single botanical branch, tall grass,
       a lone flower, falling leaves, rolling hills, a still pond, a
       mountain silhouette, a night sky with moon and stars (instead of the
       sun), soft rain lines, birds in flight.
     Translate the quote's core image into which pose+setting pair fits
     best, then write a one-sentence scene description from that pair —
     don't just paste the pair names in, make it read as a scene.
     Afterward, write the chosen pose+setting back to `"last_pose"` /
     `"last_setting"` and append to `"history"`.
   - Always end with: "Absolutely no text, no words, no letters anywhere in
     the image — illustration and background only."
2. It returns 4 candidates as thumbnail URLs. Show all 4 to the user as
   markdown images and let them pick — don't choose alone, this ships on
   the account every time, not just when building a library. When picking
   (or suggesting a pick), favor the candidate that best executes *this
   post's* scene over one that happens to most resemble an older post —
   palette consistency is already locked in by the fixed anchor, so leaning
   into the new composition is safe and is the whole point of this fix.
3. `create-design-from-candidate` (needs the `job_id` from step 1 and the
   chosen `candidate_id`).
4. `read-design` with `filter.fields: ["design_content"]` and confirm it's
   empty (no text snuck in despite the prompt) before proceeding.
5. `get-export-formats` then `export-design` as `png` at `width: 1080,
   height: 1350, lossless: true`. Download the returned S3 URL with `curl`
   into `output/<slug>/background.png` (this is a one-off asset for this
   post, not a shared library file).
6. Open the downloaded PNG yourself (Read tool) and find its empty space,
   then set in `poster.json`: `"background_image": "output/<slug>/background.png"`,
   `"quote_zone": {"top", "left"|"right", "width"}`, and
   `"subline_zone": {"top", "left"|"right", "width", "align"}` (px,
   1080x1350 canvas) — placed to sit in that empty space. Render (Step 2)
   and open the JPG to confirm nothing collides with the artwork; adjust the
   zone coordinates and re-render if it does.

**Fallback / quick-reuse option:** `resources/backgrounds/*.png` still holds
the original two illustrations the style was established from
(`meditation-branch-sun`, `reaching-hills-sun`). Set
`"background": "meditation-branch-sun"` (or the other name) in `poster.json`
to reuse one directly and skip the generation step — useful if the user
wants something fast, or Canva is unavailable. Omitting `background`
entirely (and not setting `background_image`) auto-rotates between just
these two named ones, same as before — but that's the fallback, not the
default; default to generating a bespoke illustration unless the user asks
for speed over freshness.

## One-time setup (only if not already done)

```bash
bash .claude/skills/quote-poster-generator/scripts/setup.sh
```

Installs `playwright`, `jinja2`, `pillow`, `requests` (shared with
infographic-generator — installing twice is harmless), installs headless
Chromium, and downloads the Caveat variable font plus a copy of Poppins
SemiBold into `resources/fonts/`. The Canva MCP connector is used for every
normal post now (see above), not just for occasional library-building.

Publishing to Notion reuses infographic-generator's script and its
`NOTION_TOKEN` / `NOTION_DATABASE_ID` setup — see Step 4 below. Nothing
poster-specific to configure there.

## Step 0 — pick a quote (only when the user didn't give one)

If the user asked for an **attributed quote** from him with no specific line
given: fetch https://www.goodreads.com/author/quotes/106453.Ravi_Shankar,
read the listed quotes, and pick one that's short (under ~90 characters,
6-14 words), stands alone without context, and isn't already in
`output/used_topics.json` → `"attributed_quotes"` (a flat list of
`{quote, source, slug, date}` — append to it after publishing, same spirit
as the chapter ledger below, so the account doesn't repeat the same quote).

Otherwise (**brand-voice** mode), this shares its source material and
"already used" ledger with infographic-generator, so the account never
turns the same chapter into a carousel *and* a poster:

1. List the books under `./src` (PDFs — extract with the `pdf` skill, e.g.
   `pypdf`: `reader.outline` for the chapter list,
   `reader.get_destination_page_number(item)` for each chapter's start page).
2. Read `output/used_topics.json` at the project root (create it with `{}`
   if absent — it also holds infographic-generator's background/accent
   rotation and this skill's background rotation, so don't blow those keys
   away). It maps each book's path → list of `{topic, slug, date}` already
   produced, regardless of which of the two skills produced it.
3. Pick one chapter/topic at random from that book that isn't already in
   its list. Never reuse a chapter until every other chapter in that book
   has been used at least once.
4. Read the chapter and pull out the single sharpest line or insight in
   it — not the whole arc, just the one sentence worth putting on a poster
   by itself. Paraphrase it in our own voice; this is not a literal quote,
   so no attribution line.
5. After Step 1 below (copy written and rendered), append
   `{topic, slug, date}` to that book's list in `output/used_topics.json`,
   same as infographic-generator does.

If the user gave you a quote or topic directly, skip topic selection —
slugify it and go straight to Step 1.

## Step 1 — write the copy (`output/<slug>/poster.json`)

```json
{
  "topic": "Human readable topic",
  "slug": "kebab-case-slug",
  "quote": "You don't have to have it all figured out right now.",
  "subline": "You're still growing, and that is enough."
}
```

- **`quote`** (required): the one line the whole post is built around. Aim
  for 6-14 words / under ~90 characters — this is a single-liner format, not
  a paragraph. It can wrap to 2-3 lines on the poster, but if it's running
  past that, it's not a one-liner anymore — cut it or move it to a carousel
  instead. In attributed-quote mode this must be his exact wording (see
  sourcing rule); in brand-voice mode it's our own paraphrase.
- **`subline`** (optional): in attributed-quote mode, use this for
  `"— Sri Sri Ravi Shankar"`. In brand-voice mode, a second, smaller
  resolving thought underneath — an echo or soft landing, not a
  restatement; skip it if the quote already stands on its own.

Illustration fields (`background_image`/`quote_zone`/`subline_zone`, or
`background`) get added after Step 1.5 below — don't set them yet.

## Step 1.5 — generate the illustration

See "Where the illustrations come from" above. Do this for every poster
before rendering, unless the user explicitly asks to reuse one of the two
named fallback illustrations or skip straight to a fast render.

## Step 2 — render

```bash
python3 .claude/skills/quote-poster-generator/scripts/render_poster.py <slug>
```

Validates `poster.json`, resolves the background (the `background_image` +
zones from Step 1.5, a named fallback, or auto-rotated fallback), renders
`output/<slug>/01.jpg` (2160x2700 JPEG, quality 92) and
`output/<slug>/poster.html`, and writes `output/<slug>/slides.json` in the
shape infographic-generator's publish script expects (see Step 4). It
prints the final quote/subline font sizes and stops if either overflows its
line limit at the minimum size — the fix is always shortening the copy,
never a smaller font floor.

**Before showing the user anything**, open `01.jpg` yourself (Read tool) and
sanity-check it: nothing clipped or overlapping the illustration, the text
sits in the illustration's empty space with good contrast, the handle sits
in its usual spot. Fix and re-render if not.

## Step 3 — caption

Write `output/<slug>/caption.md`: same voice and shape as
infographic-generator's captions — warm, plain-spoken, opening line matches
the poster's hook, blank line, then 8-15 mixed-reach hashtags, no emoji. A
single-liner post usually wants a *shorter* caption than a carousel's,
since the image already carries most of the thought — 40-90 words is
plenty. In attributed-quote mode, it's fine (good, even) for the caption to
name him again and add a hashtag like `#srisriravishankar`.

Same as infographic-generator: always fold in 2-3 Munich/local-community
hashtags (`#MunichYoga`, `#MünchenYoga`, `#MunichMeditation`,
`#MunichWellness`, `#MunichCommunity`, ...), varied post to post, counted
within the 8-15 total.

## Step 4 — publish to the Notion content calendar

Reuses infographic-generator's publish script as-is — this skill doesn't
have (and shouldn't get) its own copy of that logic:

```bash
python3 .claude/skills/infographic-generator/scripts/notion_publish.py <slug>
```

It reads `output/<slug>/slides.json` (for topic + slide count — written by
`render_poster.py` as a 1-element `slides` array so this just works),
`output/<slug>/caption.md`, and `output/<slug>/01.jpg`, then creates one
**Instagram Content Calendar** page with the image attached (as both the
Slides property and a full-size body block) and Status set to
`Ready for review`.

**Never set Status to `Approved`** — same rule as infographic-generator.
`Approved` is a human decision, and the only status a future posting
automation may ever act on.

## Design system (for template/style-anchor edits only — don't touch this per-poster)

- Background: one bespoke full-bleed illustration per poster (see "Where
  the illustrations come from"), always generated to match the fixed style
  anchor so the account reads as one consistent set — cream/sage/terracotta,
  warm, hand-drawn folk-art, one figure + botanical branch + sun as the
  recurring visual vocabulary. Don't drift the palette or style without the
  user explicitly asking for a change.
- Text overlay: always ours, never Canva's. Caveat (handwritten, variable
  weight 400-700) for the quote and subline; Poppins SemiBold for the
  handle, tying it back visually to infographic-generator's carousels.
  Never swap either font, and never let a Canva-generated design's own text
  layer ship — always export text-free art and overlay separately, exactly
  so this typography stays identical across every post regardless of
  illustration.
- Each poster's background has its own text-zone geometry
  (`quote_zone`/`subline_zone`), tuned per-illustration to sit in that
  image's empty space — this is inherently per-post now, not a fixed table.
- Forbidden: multiple slides (this format is one image, always), emoji,
  drop shadows, glows, added text baked into a background image, watermarks,
  animation, quotes attributed to anyone other than Sri Sri Ravi Shankar.

## Files

- `template/poster.html` — the only template, all CSS inline, `@font-face`
  pointing at local files in `resources/fonts/`, background image referenced
  via a local file URI passed in by `render_poster.py`.
- `resources/backgrounds/*.png` — the two original illustrations the visual
  style was established from; kept as a fallback/quick-reuse option, not
  the primary path anymore.
- `scripts/render_poster.py` — validate → resolve background
  (`background_image`+zones, a named fallback, or auto-rotated fallback) →
  render → screenshot → write `slides.json`. Reads `output/<slug>/poster.json`,
  writes into `output/<slug>/`, and reads/writes `output/used_topics.json`
  for the shared chapter ledger and the fallback rotation.
- `scripts/setup.sh` — one-time dependency/font install.
- `resources/fonts/` — Caveat (OFL, fetched by `setup.sh`) and a copy of
  Poppins SemiBold (OFL, copied from infographic-generator's fonts).
