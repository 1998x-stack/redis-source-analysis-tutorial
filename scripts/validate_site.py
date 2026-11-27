#!/usr/bin/env python3
"""Verify static GitHub Pages structure without third-party dependencies."""
from __future__ import annotations
from html.parser import HTMLParser
from pathlib import Path
import json
import re
import sys
import xml.etree.ElementTree as ET
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs"
class Tags(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs=[]; self.headings=[]; self.tags=[]; self.title=False;self.h1=0
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs); self.tags.append(tag)
        if tag=="h1": self.h1+=1
        if tag in ("a","link","script","img","source") and (u:=attrs.get("href") or attrs.get("src")): self.refs.append((tag,u))
def check_file(path, errors):
    text=path.read_text(encoding="utf-8")
    parser=Tags();parser.feed(text)
    if path.name != "index.html" and path.parent.name == "chapters" and int(path.stem)<=25:
        if parser.h1!=1:errors.append(f"{path}: expected exactly one h1; got {parser.h1}")
        for required in ("<main","<article","<section","<figure"):
            if required not in text: errors.append(f"{path}: missing {required}")
    if path.parent.name == "chapters" and path.stem in ("21", "22", "23", "24", "25"):
        if text.count('<figure class="figure diagram-pan">') != 3:
            errors.append(f"{path}: fifth-batch page needs exactly 3 narrative diagrams")
        if text.count('data-fifth-demo=') != 1:
            errors.append(f"{path}: fifth-batch page needs one interactive model")
        if text.count('<section id=') < 8:
            errors.append(f"{path}: insufficient independent article sections")
        if text.count("https://github.com/redis/redis/blob/7.2.4/") < 3:
            errors.append(f"{path}: missing pinned upstream source references")
        if '<script src="../assets/js/fifth-article.js"' not in text:
            errors.append(f"{path}: missing fifth-article enhancement")
    for tag,uri in parser.refs:
        parsed=urlparse(uri)
        if parsed.scheme or parsed.netloc or uri.startswith(("#","mailto:","tel:","data:","javascript:")): continue
        candidate=(path.parent / unquote(parsed.path)).resolve()
        if not candidate.is_relative_to(SITE.resolve()):errors.append(f"{path}: unsafe link {uri}")
        elif parsed.path and not candidate.exists():errors.append(f"{path}: broken {uri}")
    return parser
def main():
    errors=[]
    manifest=json.loads((SITE/"catalog.json").read_text(encoding="utf-8"))
    chapters=manifest["chapters"]
    if len(chapters)!=28:errors.append("catalog chapter count not 28")
    for chapter in chapters:
        target=SITE/chapter["file"]
        if not target.is_file():errors.append(f"chapter missing: {target}")
    for path in SITE.rglob("*.html"):check_file(path,errors)
    for path in SITE.rglob("*.svg"):
        try:
            root=ET.parse(path).getroot()
            if not root.tag.endswith("svg") or not root.attrib.get("viewBox"):errors.append(f"SVG lacks viewBox {path}")
            if not any(child.tag.endswith("title") for child in root):errors.append(f"SVG lacks title {path}")
            if not any(child.tag.endswith("desc") for child in root):errors.append(f"SVG lacks desc {path}")
        except ET.ParseError as exc:errors.append(f"invalid SVG {path}: {exc}")
    if errors:
        print("FAIL ("+str(len(errors))+")");print("\n".join(errors));sys.exit(1)
    print(f"PASS: {len(chapters)} chapters, {len(list(SITE.rglob('*.html')))} HTML files, {len(list(SITE.rglob('*.svg')))} SVGs; relative paths valid")
if __name__=="__main__":main()