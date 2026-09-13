#!/usr/bin/env python3
"""
Render an Instagram carousel from output/<slug>/slides.json.

slides.json is the single source of truth. This script does not invent copy;
it validates, renders each slide from template/slide.html via Playwright +
Chromium, screenshots at 2x, and builds a contact sheet.

Usage:
    python3 render_carousel.py <slug> [--scale 2] [--slide N]

Paths are resolved relative to the project root (the current working
directory, which must contain output/<slug>/slides.json).
"""
import argparse
import html
import json
import random
import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from PIL import Image

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "template"
FONTS_DIR = SKILL_DIR / "resources" / "fonts"

FONT_FILES = {
    "extrabold": FONTS_DIR / "Poppins-ExtraBold.ttf",
    "semibold": FONTS_DIR / "Poppins-SemiBold.ttf",
    "medium": FONTS_DIR / "Poppins-Medium.ttf",
}

ACCENT_RE = re.compile(r"\*(.+?)\*")
VALID_ROLES = {"cover", "body", "closing"}

# Soft, muted wellness tones. Kept deliberately close in saturation/lightness
# so any pairing still feels like the same brand, just a different day.
BACKGROUND_PALETTE = [
    "#F6F1E7",  # warm cream
    "#E3E9DC",  # sage
    "#F1DFD6",  # blush
    "#DCE6EA",  # soft sky
    "#E7E0EC",  # lavender
    "#EFE1CE",  # sand
    "#E0E7E4",  # seafoam
    "#ECE0E5",  # dusty rose
]

# Curated two-tone pairs for the "duo" background style: a hard-edged split
# between two colors from the same warm/cool family, so it never clashes.
# No gradients — the edge stays sharp.
DUO_PALETTE = [
    ("#F6F1E7", "#EFE1CE"),  # cream / sand
    ("#E3E9DC", "#E0E7E4"),  # sage / seafoam
    ("#F1DFD6", "#ECE0E5"),  # blush / dusty rose
    ("#DCE6EA", "#E7E0EC"),  # soft sky / lavender
]

SPLIT_RATIOS = [34, 66]  # top-band height as % of page height, for "duo" style

# Muted accent tones, rotated the same way as backgrounds so no two posts in
# a row read identically. All dark/saturated enough to pop on every
# BACKGROUND_PALETTE / DUO_PALETTE tone.
ACCENT_PALETTE = [
    "#C1512E",  # terracotta (original brand accent)
    "#4A6B57",  # deep sage
    "#8B5E3C",  # warm umber
    "#5B6E8C",  # dusty indigo
    "#9C6B9E",  # muted plum
]

USED_TOPICS_PATH = Path("output") / "used_topics.json"


class ValidationError(Exception):
    pass


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_accents(raw_text, context):
    matches = ACCENT_RE.findall(raw_text)
    if len(matches) > 1:
        raise ValidationError(
            f"{context}: found {len(matches)} accent markers, at most 1 allowed: {raw_text!r}"
        )
    parts = []
    last = 0
    for m in ACCENT_RE.finditer(raw_text):
        parts.append(html.escape(raw_text[last:m.start()]))
        parts.append(f'<span class="accent">{html.escape(m.group(1))}</span>')
        last = m.end()
    parts.append(html.escape(raw_text[last:]))
    return "".join(parts), len(matches)


def validate_slides(data):
    slides = data.get("slides")
    if not slides or not isinstance(slides, list):
        raise ValidationError("slides.json must contain a non-empty 'slides' list")
    if not (4 <= len(slides) <= 9):
        raise ValidationError(f"slide count must be 4-9, got {len(slides)}")
    if slides[0].get("role") != "cover":
        raise ValidationError("slide 1 must have role 'cover'")
    if slides[-1].get("role") != "closing":
        raise ValidationError("last slide must have role 'closing'")
    for i, s in enumerate(slides[1:-1], start=2):
        if s.get("role") != "body":
            raise ValidationError(f"slide {i} must have role 'body' (only slide 1 is cover, only the last is closing)")

    prepared = []
    for idx, s in enumerate(slides, start=1):
        role = s.get("role")
        if role not in VALID_ROLES:
            raise ValidationError(f"slide {idx}: unknown role {role!r}")

        text = s.get("text")
        if not text:
            raise ValidationError(f"slide {idx} ({role}): missing 'text'")

        html_str, accents = parse_accents(text, f"slide {idx} text")
        entry = {"role": role, "index": idx, "statement_html": html_str, "accent_count": accents}

        if role == "closing":
            cta = s.get("cta")
            entry["cta"] = html.escape(cta) if cta else None
            entry["accent_count"] = accents + 1  # the end mark

        prepared.append(entry)

    return prepared


def load_used_topics():
    if USED_TOPICS_PATH.exists():
        return json.loads(USED_TOPICS_PATH.read_text(encoding="utf-8"))
    return {}


def save_used_topics(data):
    USED_TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USED_TOPICS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def pick_look(data):
    """Resolve this carousel's background style + accent color.

    Three independent rotations (style, background, accent) are tracked in
    used_topics.json and each avoids repeating its immediately-previous
    pick, so consecutive posts never look identical even when random draws
    would otherwise coincide. Any of "background" (solid), "background_top"
    + "background_bottom" (duo), or "accent" set explicitly in slides.json
    short-circuits that dimension's auto-pick.
    """
    used = load_used_topics()
    dirty = False

    if data.get("background_top") and data.get("background_bottom"):
        style, bg_top, bg_bottom = "duo", data["background_top"], data["background_bottom"]
        split_ratio = data.get("split_ratio", SPLIT_RATIOS[0])
    elif data.get("background"):
        style, bg_top, bg_bottom, split_ratio = "solid", None, data["background"], None
    else:
        last_style = used.get("style", {}).get("last")
        style = random.choice([s for s in ("solid", "duo") if s != last_style] or ["solid", "duo"])
        used.setdefault("style", {})["last"] = style
        dirty = True
        if style == "duo":
            last_pair = tuple(used.get("backgrounds", {}).get("last_duo", []))
            choices = [p for p in DUO_PALETTE if p != last_pair] or DUO_PALETTE
            bg_top, bg_bottom = random.choice(choices)
            split_ratio = random.choice(SPLIT_RATIOS)
            used.setdefault("backgrounds", {})["last_duo"] = [bg_top, bg_bottom]
        else:
            last_solid = used.get("backgrounds", {}).get("last")
            choices = [c for c in BACKGROUND_PALETTE if c != last_solid] or BACKGROUND_PALETTE
            bg_top, bg_bottom, split_ratio = None, random.choice(choices), None
            used.setdefault("backgrounds", {})["last"] = bg_bottom
        used.setdefault("backgrounds", {}).setdefault("history", []).append(
            bg_bottom if style == "solid" else f"{bg_top}/{bg_bottom}"
        )

    accent = data.get("accent")
    if not accent:
        last_accent = used.get("accents", {}).get("last")
        choices = [c for c in ACCENT_PALETTE if c != last_accent] or ACCENT_PALETTE
        accent = random.choice(choices)
        used.setdefault("accents", {})["last"] = accent
        used["accents"].setdefault("history", []).append(accent)
        dirty = True

    if dirty:
        save_used_topics(used)
    return {"style": style, "bg_top": bg_top, "bg_bottom": bg_bottom, "split_ratio": split_ratio, "accent": accent}


def render_slides(slug, project_root, prepared, scale, look, only_slide=None):
    from playwright.sync_api import sync_playwright

    out_dir = project_root / "output" / slug
    html_dir = out_dir / "html"
    html_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("slide.html")

    n = len(prepared)
    font_uris = {k: v.resolve().as_uri() for k, v in FONT_FILES.items()}

    targets = [prepared[only_slide - 1]] if only_slide else prepared
    reference_furniture = None

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=[
                "--force-color-profile=srgb",
                "--font-render-hinting=none",
                "--disable-lcd-text",
                "--allow-file-access-from-files",
            ]
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=scale)

        def block_network(route):
            if route.request.url.startswith(("http://", "https://")):
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_network)

        if only_slide and only_slide != 1:
            existing_cover = html_dir / "01.html"
            if existing_cover.exists():
                page.goto(existing_cover.resolve().as_uri())
                page.evaluate("document.fonts.ready")
                reference_furniture = page.evaluate("window.__furniture()")

        for entry in targets:
            idx = entry["index"]
            folio = f"{idx:02d} / {n:02d}"
            html_out = template.render(
                role=entry["role"],
                statement_html=entry["statement_html"],
                cta=entry.get("cta"),
                folio=folio,
                bg_style=look["style"],
                bg_top=look.get("bg_top"),
                bg_bottom=look["bg_bottom"],
                split_ratio=look.get("split_ratio"),
                accent_color=look["accent"],
                font_extrabold=font_uris["extrabold"],
                font_semibold=font_uris["semibold"],
                font_medium=font_uris["medium"],
            )
            html_path = html_dir / f"{idx:02d}.html"
            html_path.write_text(html_out, encoding="utf-8")

            page.goto(html_path.resolve().as_uri())
            page.evaluate("document.fonts.ready")
            loaded = page.evaluate(
                """(weights) => weights.map(w => ({weight: w, loaded: document.fonts.check(w + " 16px 'Poppins'")}))""",
                ["800", "600"] + (["500"] if entry.get("cta") else []),
            )
            missing = [f["weight"] for f in loaded if not f["loaded"]]
            if missing:
                browser.close()
                die(f"slide {idx:02d}: Poppins weights failed to load locally: {missing} (would fall back over network)")

            fit_results = page.evaluate("window.__fit()")
            overflowed = [r for r in fit_results if r["overflow"]]
            if overflowed:
                browser.close()
                for r in overflowed:
                    print(
                        f"slide {idx:02d}: '{r['block']}' overflows at floor size "
                        f"{r['floor']}px ({r['lines']} lines, max {r['maxLines']}). "
                        f"Fix the copy, not the type.",
                        file=sys.stderr,
                    )
                sys.exit(1)

            accent_count = page.evaluate("window.__accentCount()")
            if accent_count > 1:
                browser.close()
                die(f"slide {idx:02d}: renderer counted {accent_count} accents on the page, max 1")

            furniture = page.evaluate("window.__furniture()")
            if idx == 1 and reference_furniture is None:
                reference_furniture = furniture
            elif reference_furniture:
                for key, rect in furniture.items():
                    ref = reference_furniture.get(key)
                    if ref is None or rect is None:
                        continue
                    if abs(rect["x"] - ref["x"]) > 0.5 or abs(rect["y"] - ref["y"]) > 0.5:
                        browser.close()
                        die(
                            f"slide {idx:02d}: furniture '{key}' drifted from slide 01 "
                            f"(01={ref}, {idx:02d}={rect})"
                        )

            for r in fit_results:
                print(f"[slide {idx:02d}] {r['block']}: {r['finalSize']}px, {r['lines']} line(s)")

            img_path = out_dir / f"{idx:02d}.jpg"
            page.screenshot(
                path=str(img_path),
                type="jpeg",
                quality=92,
                clip={"x": 0, "y": 0, "width": 1080, "height": 1350},
            )
            print(f"[slide {idx:02d}] -> {img_path}")

        browser.close()

    return out_dir


def build_contact_sheet(out_dir, n_slides):
    thumbs = []
    for i in range(1, n_slides + 1):
        p = out_dir / f"{i:02d}.jpg"
        if p.exists():
            thumbs.append(p)
    if not thumbs:
        return
    images = [Image.open(p) for p in thumbs]
    w = 360
    resized = []
    for im in images:
        h = int(im.height * (w / im.width))
        resized.append(im.resize((w, h)))
        im.close()
    total_w = sum(r.width for r in resized)
    max_h = max(r.height for r in resized)
    sheet = Image.new("RGB", (total_w, max_h), (255, 255, 255))
    x = 0
    for r in resized:
        sheet.paste(r, (x, 0))
        x += r.width
    sheet_path = out_dir / "contact-sheet.jpg"
    sheet.save(sheet_path, quality=90)
    print(f"[contact sheet] -> {sheet_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="slug of output/<slug>/slides.json")
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--slide", type=int, default=None, help="re-render only slide N")
    args = parser.parse_args()

    project_root = Path.cwd()
    slides_json_path = project_root / "output" / args.slug / "slides.json"
    if not slides_json_path.exists():
        die(f"{slides_json_path} not found. Write the copy first.")

    data = json.loads(slides_json_path.read_text(encoding="utf-8"))

    try:
        prepared = validate_slides(data)
    except ValidationError as e:
        die(str(e))

    for f in FONT_FILES.values():
        if not f.exists():
            die(f"missing font file {f}. Run scripts/setup.sh first.")

    look = pick_look(data)
    data["style"] = look["style"]
    data["accent"] = look["accent"]
    if look["style"] == "duo":
        data["background_top"] = look["bg_top"]
        data["background_bottom"] = look["bg_bottom"]
        data["split_ratio"] = look["split_ratio"]
        data.pop("background", None)
        print(f"[look] duo {look['bg_top']} / {look['bg_bottom']} (split {look['split_ratio']}%), accent {look['accent']}")
    else:
        data["background"] = look["bg_bottom"]
        data.pop("background_top", None)
        data.pop("background_bottom", None)
        data.pop("split_ratio", None)
        print(f"[look] solid {look['bg_bottom']}, accent {look['accent']}")
    slides_json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    out_dir = render_slides(args.slug, project_root, prepared, args.scale, look, only_slide=args.slide)

    if args.slide is None:
        build_contact_sheet(out_dir, len(prepared))

    print(f"\nDone. Output in {out_dir}")


if __name__ == "__main__":
    main()
