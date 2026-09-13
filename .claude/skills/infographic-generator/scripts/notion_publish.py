#!/usr/bin/env python3
"""
Publish a rendered carousel to the Instagram Content Calendar Notion database.

Reads output/<slug>/slides.json (topic, slide count) and output/<slug>/caption.md
(caption text), uploads output/<slug>/01.jpg..NN.jpg to Notion in slide order,
and creates one database page: Name/Topic/Caption/Slide count filled in, Slides
holding the images in order, Status set to "Ready for review". The same
uploads are also inserted as full-size image blocks in the page body (in
slide order) — the Slides *property* only ever renders as small thumbnail
chips in Notion's UI (including in side peek), so the body is what makes a
big, scrollable slide-by-slide view when the page is opened or peeked.

This script never sets Status to "Approved" — that transition is a human
decision made in Notion. Any future poster automation must only ever act on
rows already marked "Approved"; it must not be the thing that sets it.

Usage:
    python3 notion_publish.py <slug>

Requires NOTION_TOKEN and NOTION_DATABASE_ID, either exported in the
environment or set in a .env file at the project root (KEY=VALUE, one per
line). Paths are resolved relative to the project root (the current working
directory, which must contain output/<slug>/).
"""
import json
import os
import sys
from pathlib import Path

import requests

NOTION_VERSION = "2022-06-28"
API_BASE = "https://api.notion.com/v1"


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def load_dotenv(project_root):
    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def notion_request(method, path, token, **kwargs):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
    }
    headers.update(kwargs.pop("headers", {}))
    resp = requests.request(method, f"{API_BASE}{path}", headers=headers, **kwargs)
    if resp.status_code >= 300:
        die(f"Notion API {method} {path} failed ({resp.status_code}): {resp.text}")
    return resp.json()


def rich_text(text):
    # Notion caps each rich_text object's content at 2000 chars; chunk if needed.
    chunks = [text[i:i + 2000] for i in range(0, len(text), 2000)] or [""]
    return [{"text": {"content": c}} for c in chunks]


def upload_file(token, image_path):
    created = notion_request(
        "POST", "/file_uploads", token,
        json={"filename": image_path.name},
    )
    with open(image_path, "rb") as f:
        notion_request(
            "POST", f"/file_uploads/{created['id']}/send", token,
            files={"file": (image_path.name, f, "image/jpeg")},
        )
    return created["id"]


def main():
    if len(sys.argv) != 2:
        die("usage: notion_publish.py <slug>")
    slug = sys.argv[1]

    project_root = Path.cwd()
    load_dotenv(project_root)

    token = os.environ.get("NOTION_TOKEN")
    database_id = os.environ.get("NOTION_DATABASE_ID")
    if not token or not database_id:
        die(
            "NOTION_TOKEN and NOTION_DATABASE_ID must be set (env vars or "
            f"{project_root / '.env'})."
        )

    out_dir = project_root / "output" / slug
    slides_json_path = out_dir / "slides.json"
    caption_path = out_dir / "caption.md"
    if not slides_json_path.exists():
        die(f"{slides_json_path} not found. Render the carousel first.")
    if not caption_path.exists():
        die(f"{caption_path} not found. Write the caption first.")

    data = json.loads(slides_json_path.read_text(encoding="utf-8"))
    topic = data.get("topic", slug)
    slide_count = len(data.get("slides", []))
    caption = caption_path.read_text(encoding="utf-8").strip()

    images = sorted(out_dir.glob("[0-9][0-9].jpg"))
    if not images:
        die(f"no rendered slides (NN.jpg) found in {out_dir}")
    if len(images) != slide_count:
        die(f"slides.json declares {slide_count} slides but {len(images)} images found in {out_dir}")

    page = notion_request(
        "POST", "/pages", token,
        json={
            "parent": {"type": "database_id", "database_id": database_id},
            "properties": {
                "Name": {"title": [{"text": {"content": topic}}]},
                "Topic": {"rich_text": rich_text(topic)},
                "Status": {"select": {"name": "Draft"}},
            },
        },
    )
    page_id = page["id"]
    print(f"[notion] created page {page_id} ({page['url']})")

    slide_files = []
    for image_path in images:
        upload_id = upload_file(token, image_path)
        slide_files.append({
            "type": "file_upload",
            "file_upload": {"id": upload_id},
            "name": image_path.name,
        })
        print(f"[notion] uploaded {image_path.name}")

    notion_request(
        "PATCH", f"/blocks/{page_id}/children", token,
        json={
            "children": [
                {"object": "block", "type": "image", "image": {"type": "file_upload", "file_upload": {"id": f["file_upload"]["id"]}}}
                for f in slide_files
            ]
        },
    )
    print(f"[notion] {slide_count} slides added to page body")

    notion_request(
        "PATCH", f"/pages/{page_id}", token,
        json={
            "properties": {
                "Caption": {"rich_text": rich_text(caption)},
                "Slide count": {"number": slide_count},
                "Slides": {"files": slide_files},
                "Status": {"select": {"name": "Ready for review"}},
            }
        },
    )
    print(f"[notion] {slide_count} slides attached, status set to Ready for review")
    print(f"\nDone. {page['url']}")


if __name__ == "__main__":
    main()
