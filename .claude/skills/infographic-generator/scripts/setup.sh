#!/usr/bin/env bash
# One-time setup for the infographic-generator skill: Python deps, headless
# Chromium, and local copies of the three OFL typefaces (so rendering never
# touches the network at carousel-render time).
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONTS_DIR="$SKILL_DIR/resources/fonts"
mkdir -p "$FONTS_DIR"

echo "==> Installing Python dependencies"
python3 -m pip install --quiet --upgrade playwright jinja2 pillow requests

echo "==> Installing headless Chromium for Playwright"
python3 -m playwright install chromium

echo "==> Fetching fonts from google/fonts (OFL)"
RAW="https://raw.githubusercontent.com/google/fonts/main/ofl"

curl -fsSL "$RAW/poppins/Poppins-ExtraBold.ttf" -o "$FONTS_DIR/Poppins-ExtraBold.ttf"
curl -fsSL "$RAW/poppins/Poppins-SemiBold.ttf"  -o "$FONTS_DIR/Poppins-SemiBold.ttf"
curl -fsSL "$RAW/poppins/Poppins-Medium.ttf"    -o "$FONTS_DIR/Poppins-Medium.ttf"

echo "==> Fonts installed:"
ls -la "$FONTS_DIR"

echo "==> Done."
