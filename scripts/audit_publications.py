#!/usr/bin/env python3
"""Verify public SPURN indexing hygiene. This is NOT editorial approval."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FORMATS = {"The Latest": "latest", "Discovery": "discovery", "Intelligence": "intelligence", "Editorial": "editorial"}
ARTICLE = re.compile(r"^/(latest|discovery|intelligence|editorial)/[a-z0-9]+(?:-[a-z0-9]+)*\.html$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ORIGIN = "https://spurnmedia.com"


def audit(root: Path) -> list[str]:
    root = root.resolve()
    errors: list[str] = []
    try:
        records = json.loads((root / "search/search-index.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"Cannot read public index: {exc}"]
    if not isinstance(records, list) or not records:
        return ["Public index must be a nonempty list"]
    try:
        tree = ET.parse(root / "sitemap.xml")
        sitemap = {n.text.strip() for n in tree.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if n.text}
    except (OSError, ET.ParseError) as exc:
        return [f"Cannot read sitemap: {exc}"]

    indexed: set[str] = set()
    for i, item in enumerate(records):
        if not isinstance(item, dict):
            errors.append(f"Record {i}: not an object")
            continue
        title, desc, fmt, url, date = (item.get(k) for k in ("title", "description", "format", "url", "date"))
        if not isinstance(title, str) or not title.strip():
            errors.append(f"Record {i}: missing title")
        if not isinstance(desc, str) or not desc.strip():
            errors.append(f"Record {i}: missing description")
        if fmt not in FORMATS:
            errors.append(f"Record {i}: invalid format")
        if not isinstance(url, str) or not ARTICLE.fullmatch(url):
            errors.append(f"Record {i}: invalid public article URL")
            continue
        if fmt in FORMATS and not url.startswith("/" + FORMATS[fmt] + "/"):
            errors.append(f"Record {i}: format/URL mismatch")
        if not isinstance(date, str) or (date and not DATE.fullmatch(date)):
            errors.append(f"Record {i}: invalid ISO date")
        if url in indexed:
            errors.append(f"Record {i}: duplicate URL {url}")
        indexed.add(url)
        file = (root / url.lstrip("/")).resolve()
        if not file.is_relative_to(root) or not file.is_file() or file.is_symlink():
            errors.append(f"Record {i}: missing/symlinked article {url}")
            continue
        html = file.read_text(encoding="utf-8")
        if f'<link rel="canonical" href="{ORIGIN}{url}">' not in html:
            errors.append(f"Record {i}: canonical mismatch {url}")
        if ORIGIN + url not in sitemap:
            errors.append(f"Record {i}: missing sitemap entry {url}")
        if re.search(r'<meta\s+name=["\']robots["\'][^>]*\bnoindex\b', html, re.I):
            errors.append(f"Record {i}: noindex on public article {url}")

    public_files = {"/" + p.relative_to(root).as_posix()
                    for folder in FORMATS.values()
                    for p in (root / folder).glob("*.html")
                    if p.is_file() and p.name != "index.html"}
    for missing in sorted(public_files - indexed):
        errors.append(f"Public article absent from index: {missing}")
    for extra in sorted(indexed - public_files):
        errors.append(f"Public index points to missing article: {extra}")
    homepage = (root / "index.html").read_text(encoding="utf-8")
    for link in re.findall(r'class="latest-wire-row"\s+href="([^"]+)"', homepage):
        if "/" + link.lstrip("/") not in indexed:
            errors.append(f"Homepage Latest link absent from index: {link}")
    return errors


if __name__ == "__main__":
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    problems = audit(directory)
    if problems:
        for problem in problems:
            print("FAIL:", problem)
        sys.exit(1)
    print("PASS: public index, article paths, canonicals, sitemap and homepage references")
