#!/usr/bin/env bash
# One-time setup for the quote-poster-generator skill: Python deps, headless
# Chromium, and a local copy of the Caveat variable font (so rendering never
# touches the network at poster-render time). Shares its Python deps and
# Chromium install with the infographic-generator skill — installing twice
# is harmless (pip/playwright no-op if already satisfied) and keeps this
# skill runnable standalone.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTS_DIR="$SKILL_DIR/resources/fonts"
mkdir -p "$FONTS_DIR"

echo "==> Installing Python dependencies"
python3 -m pip install --quiet --upgrade playwright jinja2 pillow requests

echo "==> Installing headless Chromium for Playwright"
python3 -m playwright install chromium

echo "==> Fetching Caveat (variable font, OFL) from google/fonts"
curl -fsSL "https://raw.githubusercontent.com/google/fonts/main/ofl/caveat/Caveat%5Bwght%5D.ttf" \
  -o "$FONTS_DIR/Caveat-Variable.ttf"

echo "==> Copying Poppins SemiBold from infographic-generator (handle text)"
cp "$SKILL_DIR/../infographic-generator/resources/fonts/Poppins-SemiBold.ttf" "$FONTS_DIR/"

echo "==> Fonts installed:"
ls -la "$FONTS_DIR"

echo "==> Done."
