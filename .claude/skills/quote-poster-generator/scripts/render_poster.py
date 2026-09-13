#!/usr/bin/env python3
"""
Render a single-image illustrated quote poster from output/<slug>/poster.json.

poster.json is the single source of truth: {"topic", "slug", "quote",
"subline" (optional)}. This script validates it, resolves a background
illustration, renders one 1080x1350 JPEG via Playwright + Chromium (local
fonts, no network), and writes output/<slug>/01.jpg plus a slides.json
shaped so the infographic-generator skill's notion_publish.py can publish
it unmodified (see SKILL.md).

The background is normally a bespoke illustration generated via Canva for
this specific quote (Claude does that in conversation, then writes
"background_image" + "quote_zone" + "subline_zone" into poster.json before
calling this script — see "Where the illustrations come from" in SKILL.md).
"background": "<name>" instead reuses one of the small set of named,
pre-made illustrations in BACKGROUNDS below, rotating if omitted entirely.

Usage:
    python3 render_poster.py <slug> [--scale 2]
"""
import argparse
import json
import random
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "template"
FONTS_DIR = SKILL_DIR / "resources" / "fonts"
BACKGROUNDS_DIR = SKILL_DIR / "resources" / "backgrounds"

FONT_CAVEAT = FONTS_DIR / "Caveat-Variable.ttf"
FONT_POPPINS_SEMIBOLD = FONTS_DIR / "Poppins-SemiBold.ttf"

# A small set of named, reusable illustrations (the original two references
# the visual style was established from) plus the text-zone geometry that
# keeps the overlay clear of each one's artwork. Used only when poster.json
# asks for one of these by name, or omits background entirely (rotates,
# avoiding the immediately-previous pick) — the default path for a normal
# request is a bespoke "background_image" (see module docstring).
BACKGROUNDS = [
    {
        "name": "meditation-branch-sun",
        "file": "meditation-branch-sun.png",
        "ink": "#2A2118",
        "quote": {"top": 340, "left": 90, "width": 500},
        "subline_zone": {"top": 1120, "right": 90, "width": 420, "align": "right"},
    },
    {
        "name": "reaching-hills-sun",
        "file": "reaching-hills-sun.png",
        "ink": "#2A2118",
        "quote": {"top": 130, "left": 90, "width": 480},
        "subline_zone": {"top": 1120, "left": 90, "width": 480, "align": "left"},
    },
]

USED_TOPICS_PATH = Path("output") / "used_topics.json"


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_used_topics():
    if USED_TOPICS_PATH.exists():
        return json.loads(USED_TOPICS_PATH.read_text(encoding="utf-8"))
    return {}


def save_used_topics(data):
    USED_TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USED_TOPICS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def resolve_background(data, project_root):
    # Bespoke illustration generated for this specific quote (the normal
    # path — see module docstring). Claude writes these three fields into
    # poster.json after the Canva generate/pick/export workflow.
    custom_path = data.get("background_image")
    if custom_path:
        quote_zone = data.get("quote_zone")
        subline_zone = data.get("subline_zone")
        if not quote_zone or not subline_zone:
            die("'background_image' is set but 'quote_zone' and/or 'subline_zone' is missing from poster.json")
        img_path = Path(custom_path)
        if not img_path.is_absolute():
            img_path = project_root / img_path
        return {
            "name": img_path.stem,
            "path": img_path,
            "ink": data.get("ink", "#2A2118"),
            "quote": quote_zone,
            "subline_zone": subline_zone,
        }

    # Otherwise, reuse one of the small set of named illustrations.
    explicit = data.get("background")
    if explicit:
        match = next((b for b in BACKGROUNDS if b["name"] == explicit), None)
        if not match:
            die(f"unknown background {explicit!r}; choices: {[b['name'] for b in BACKGROUNDS]}")
        chosen = match
    else:
        used = load_used_topics()
        last = used.get("poster", {}).get("last_background")
        choices = [b for b in BACKGROUNDS if b["name"] != last] or BACKGROUNDS
        chosen = random.choice(choices)
        used.setdefault("poster", {})["last_background"] = chosen["name"]
        used["poster"].setdefault("history", []).append(chosen["name"])
        save_used_topics(used)

    return {**chosen, "path": BACKGROUNDS_DIR / chosen["file"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug")
    parser.add_argument("--scale", type=int, default=2)
    args = parser.parse_args()

    project_root = Path.cwd()
    poster_json_path = project_root / "output" / args.slug / "poster.json"
    if not poster_json_path.exists():
        die(f"{poster_json_path} not found. Write the copy first.")

    data = json.loads(poster_json_path.read_text(encoding="utf-8"))
    quote = data.get("quote")
    if not quote:
        die("poster.json must have a non-empty 'quote'")
    subline = data.get("subline")

    for f in (FONT_CAVEAT, FONT_POPPINS_SEMIBOLD):
        if not f.exists():
            die(f"missing font file {f}. Run scripts/setup.sh first.")

    bg = resolve_background(data, project_root)
    bg_path = bg["path"]
    if not bg_path.exists():
        die(f"missing background image {bg_path}")
    if not data.get("background_image") and "background" not in data:
        data["background"] = bg["name"]
        poster_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[background] {bg['name']}")

    out_dir = project_root / "output" / args.slug
    out_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("poster.html")

    html_out = template.render(
        quote=quote,
        subline=subline,
        ink=bg["ink"],
        background_uri=bg_path.resolve().as_uri(),
        quote_zone=bg["quote"],
        subline_zone=bg["subline_zone"],
        font_caveat=FONT_CAVEAT.resolve().as_uri(),
        font_poppins_semibold=FONT_POPPINS_SEMIBOLD.resolve().as_uri(),
    )
    html_path = out_dir / "poster.html"
    html_path.write_text(html_out, encoding="utf-8")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--force-color-profile=srgb",
                "--font-render-hinting=none",
                "--disable-lcd-text",
                "--allow-file-access-from-files",
            ]
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=args.scale)

        def block_network(route):
            if route.request.url.startswith(("http://", "https://")):
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_network)
        page.goto(html_path.resolve().as_uri())
        page.evaluate("document.fonts.ready")

        loaded = page.evaluate(
            """(specs) => specs.map(([weight, family]) => ({
                spec: weight + ' ' + family,
                loaded: document.fonts.check(weight + ' 16px \\'' + family + '\\'')
            }))""",
            [["700", "Caveat"], ["600", "Poppins"]],
        )
        missing = [f["spec"] for f in loaded if not f["loaded"]]
        if missing:
            browser.close()
            die(f"fonts failed to load locally: {missing} (would fall back over network). Run scripts/setup.sh.")

        fit_results = page.evaluate("window.__fit()")
        overflowed = [r for r in fit_results if r["overflow"]]
        if overflowed:
            browser.close()
            for r in overflowed:
                print(
                    f"'{r['block']}' overflows at floor size {r['floor']}px "
                    f"({r['lines']} lines, max {r['maxLines']}). Shorten the copy.",
                    file=sys.stderr,
                )
            sys.exit(1)
        for r in fit_results:
            print(f"[{r['block']}] {r['finalSize']}px, {r['lines']} line(s)")

        img_path = out_dir / "01.jpg"
        page.screenshot(
            path=str(img_path),
            type="jpeg",
            quality=92,
            clip={"x": 0, "y": 0, "width": 1080, "height": 1350},
        )
        browser.close()
        print(f"-> {img_path}")

    # slides.json shaped so infographic-generator's notion_publish.py works
    # unmodified against this output directory too (see SKILL.md).
    slides_json_path = out_dir / "slides.json"
    slides_json_path.write_text(
        json.dumps(
            {
                "topic": data.get("topic", args.slug),
                "slug": args.slug,
                "slides": [{"role": "single", "text": quote}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nDone. Output in {out_dir}")


if __name__ == "__main__":
    main()
