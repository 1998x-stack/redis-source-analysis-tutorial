#!/usr/bin/env python3
"""Validate the static Pages site, all article anchors, local assets, catalog and SVGs."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"


class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []
        self.ids = []
        self.fragments = []
        self.tags = []
        self.h1 = 0
        self.figures = 0
        self.figure_images = 0
        self.bad_image_alts = []
        self.final_demos = 0
        self.fifth_demos = 0
        self.scripts = []
        self.chapter_cards = []
        self.card_statuses = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "h1":
            self.h1 += 1
        if tag == "figure":
            self.figures += 1
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.fragments.append(unquote(urlparse(attrs["href"]).fragment))
        if tag in ("a", "link", "script", "img", "source"):
            uri = attrs.get("href") or attrs.get("src")
            if uri:
                self.refs.append((tag, uri))
        if tag == "img":
            if not attrs.get("alt", "").strip():
                self.bad_image_alts.append(attrs.get("src", "<unknown>"))
            if "diagram-pan" in attrs.get("class", ""):
                self.figure_images += 1
        if tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        if "data-final-demo" in attrs:
            self.final_demos += 1
        if "data-fifth-demo" in attrs:
            self.fifth_demos += 1
        if tag == "a" and "chapter-card" in attrs.get("class", "").split():
            self.chapter_cards.append(attrs.get("href", ""))
            self.card_statuses.append(attrs.get("data-status", ""))


def parse_html(path):
    parser = Tags()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def duplicate_values(values):
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def check_file(path, parser, errors, html_ids):
    if path.parent.name == "chapters" and path.stem.isdigit():
        chapter = int(path.stem)
        if parser.h1 != 1:
            errors.append(f"{path}: expected exactly one h1; got {parser.h1}")
        for required in ("main", "article", "section"):
            if required not in parser.tags:
                errors.append(f"{path}: missing semantic {required} element")
        duplicates = duplicate_values(parser.ids)
        if duplicates:
            errors.append(f"{path}: duplicate ids: {', '.join(duplicates)}")
        ids = set(parser.ids)
        for fragment in parser.fragments:
            if fragment and fragment not in ids:
                errors.append(f"{path}: unresolved in-page anchor #{fragment}")
        if parser.bad_image_alts:
            errors.append(f"{path}: images missing alt text: {parser.bad_image_alts}")

        if 21 <= chapter <= 25:
            if parser.figures != 3:
                errors.append(f"{path}: expected 3 fifth-batch diagrams; got {parser.figures}")
            if parser.fifth_demos != 1:
                errors.append(f"{path}: expected one fifth-batch interactive model")
            if "../assets/js/fifth-article.js" not in parser.scripts:
                errors.append(f"{path}: missing fifth-article enhancement")

        if 26 <= chapter <= 28:
            expected_demos = {26: 2, 27: 1, 28: 2}[chapter]
            if parser.figures != 3:
                errors.append(f"{path}: expected 3 standalone mechanism diagrams; got {parser.figures}")
            if parser.final_demos != expected_demos:
                errors.append(f"{path}: expected {expected_demos} final interactive models; got {parser.final_demos}")
            if "../assets/js/final-articles.js" not in parser.scripts:
                errors.append(f"{path}: missing final-articles.js enhancement")
            if len([tag for tag in parser.tags if tag == "section"]) < 8:
                errors.append(f"{path}: article has too few independent sections")

    for tag, uri in parser.refs:
        parsed = urlparse(uri)
        if parsed.scheme or parsed.netloc or uri.startswith(("mailto:", "tel:", "data:", "javascript:")):
            continue
        if parsed.path:
            candidate = (path.parent / unquote(parsed.path)).resolve()
        else:
            candidate = path.resolve()
        if not candidate.is_relative_to(SITE.resolve()):
            errors.append(f"{path}: unsafe link {uri}")
            continue
        if parsed.path and not candidate.exists():
            errors.append(f"{path}: broken local path {uri}")
            continue
        if parsed.fragment and candidate in html_ids:
            fragment = unquote(parsed.fragment)
            if fragment and fragment not in html_ids[candidate]:
                errors.append(f"{path}: broken fragment {uri}")


def main():
    errors = []
    manifest_path = SITE / "catalog.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    chapters = manifest.get("chapters", [])
    if manifest.get("chapterCount") != 28 or len(chapters) != 28:
        errors.append("catalog chapter count must be exactly 28")

    expected_files = []
    for chapter in chapters:
        target = SITE / chapter["file"]
        expected_files.append(chapter["file"])
        if not target.is_file():
            errors.append(f"chapter missing: {target}")
        if chapter.get("status") not in ("rewritten", "legacy"):
            errors.append(f"invalid status for chapter {chapter.get('num')}: {chapter.get('status')}")

    html_paths = sorted(SITE.rglob("*.html"))
    html_ids = {path.resolve(): set(parse_html(path).ids) for path in html_paths}
    parsers = {path: parse_html(path) for path in html_paths}
    for path, parser in parsers.items():
        check_file(path, parser, errors, html_ids)

    index_path = SITE / "index.html"
    index = parsers.get(index_path)
    if index is None:
        errors.append("docs/index.html is missing")
    else:
        if len(index.chapter_cards) != 28:
            errors.append(f"homepage must contain 28 chapter cards; got {len(index.chapter_cards)}")
        if any(status != "rewritten" for status in index.card_statuses):
            errors.append("homepage still contains a non-rewritten chapter card")
        if sorted(index.chapter_cards) != sorted(expected_files):
            errors.append("homepage chapter cards do not match docs/catalog.json")
        if "legacy" in index.card_statuses:
            errors.append("homepage retains legacy status cards")

    for path in SITE.rglob("*.svg"):
        try:
            root = ET.parse(path).getroot()
            if not root.tag.endswith("svg") or not root.attrib.get("viewBox"):
                errors.append(f"SVG lacks viewBox: {path}")
            # ElementTree expands xmlns into Clark notation and removes it from attrib.
            if not root.tag.startswith("{http://www.w3.org/2000/svg}"):
                errors.append(f"SVG lacks standard namespace: {path}")
            if not any(child.tag.endswith("title") for child in root):
                errors.append(f"SVG lacks title: {path}")
            if not any(child.tag.endswith("desc") for child in root):
                errors.append(f"SVG lacks desc: {path}")
        except ET.ParseError as exc:
            errors.append(f"invalid SVG {path}: {exc}")

    if errors:
        print(f"FAIL ({len(errors)})")
        print("\n".join(errors))
        sys.exit(1)

    print(
        f"PASS: {len(chapters)} catalog chapters, "
        f"{len(html_paths)} HTML files, "
        f"{len(list(SITE.rglob('*.svg')))} SVGs; "
        "unique IDs, internal anchors, local paths and catalog parity verified"
    )


if __name__ == "__main__":
    main()
