#!/usr/bin/env python3
"""Static accessibility and performance acceptance checks for the SPURN site."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
MAX_REFERENCED_IMAGE_BYTES = 200 * 1024
MAX_CSS_BYTES = 100 * 1024
MAX_JS_BYTES = 50 * 1024

errors: list[str] = []
referenced_images: set[Path] = set()


def fail(message: str) -> None:
    errors.append(message)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.headings: list[int] = []
        self.h1_count = 0
        self.main_count = 0
        self.has_skip = False
        self.has_viewport = False
        self.has_canonical = False
        self.html_lang = ""
        self.title_depth = 0
        self.title_text = ""
        self.links: list[tuple[str, str]] = []
        self.images: list[dict[str, str | None]] = []
        self.inputs: list[dict[str, str | None]] = []
        self.labels_for: set[str] = set()
        self.buttons: list[dict[str, str | None]] = []
        self.button_depth = 0
        self.button_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        if "id" in data and data["id"]:
            self.ids.append(str(data["id"]))
        if tag == "html":
            self.html_lang = str(data.get("lang") or "")
        elif tag == "meta" and str(data.get("name") or "").lower() == "viewport":
            self.has_viewport = True
        elif tag == "link":
            rel = str(data.get("rel") or "").lower().split()
            href = str(data.get("href") or "")
            if "canonical" in rel:
                self.has_canonical = True
            if href:
                self.links.append(("href", href))
        elif tag == "a":
            href = str(data.get("href") or "")
            classes = str(data.get("class") or "").split()
            if "skip-link" in classes:
                self.has_skip = True
            if href:
                self.links.append(("href", href))
            if str(data.get("target") or "").lower() == "_blank":
                rel = str(data.get("rel") or "").lower().split()
                if "noopener" not in rel:
                    fail("target=_blank link missing rel=noopener")
        elif tag == "main":
            self.main_count += 1
        elif re.fullmatch(r"h[1-6]", tag):
            level = int(tag[1])
            self.headings.append(level)
            if level == 1:
                self.h1_count += 1
        elif tag == "img":
            self.images.append(data)
            src = str(data.get("src") or "")
            if src:
                self.links.append(("src", src))
        elif tag == "script":
            src = str(data.get("src") or "")
            if src:
                self.links.append(("src", src))
        elif tag == "input":
            self.inputs.append(data)
        elif tag == "label":
            label_for = str(data.get("for") or "")
            if label_for:
                self.labels_for.add(label_for)
        elif tag == "button":
            self.buttons.append(data)
            self.button_depth += 1
            self.button_text = ""
        elif tag == "title":
            self.title_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title" and self.title_depth:
            self.title_depth -= 1
        elif tag == "button" and self.button_depth:
            if self.buttons:
                self.buttons[-1]["_text"] = self.button_text.strip()
            self.button_depth -= 1
            self.button_text = ""

    def handle_data(self, data: str) -> None:
        if self.title_depth:
            self.title_text += data
        if self.button_depth:
            self.button_text += data


def clean_local_url(value: str) -> str | None:
    value = value.strip()
    if not value or value.startswith("#"):
        return None
    parts = urlsplit(value)
    if parts.scheme in {"http", "https", "mailto", "tel", "data"} or parts.netloc:
        return None
    return unquote(parts.path)


def resolve_local(source: Path, value: str) -> Path | None:
    path = clean_local_url(value)
    if path is None:
        return None
    if path.startswith("/"):
        target = ROOT / path.lstrip("/")
    else:
        target = source.parent / path
    target = target.resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return target
    if value.split("?", 1)[0].split("#", 1)[0].endswith("/") or target.is_dir():
        target = target / "index.html"
    return target


def contrast(hex_a: str, hex_b: str) -> float:
    def lum(value: str) -> float:
        value = value.lstrip("#")
        rgb = [int(value[i:i+2], 16) / 255 for i in (0, 2, 4)]
        def channel(c: float) -> float:
            return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        r, g, b = [channel(c) for c in rgb]
        return 0.2126 * r + 0.7152 * g + 0.0722 * b
    a, b = sorted((lum(hex_a), lum(hex_b)), reverse=True)
    return (a + 0.05) / (b + 0.05)


html_files = sorted(ROOT.rglob("*.html"))
css_files = sorted(ROOT.rglob("*.css"))
js_files = sorted(ROOT.rglob("*.js"))

for page in html_files:
    text = page.read_text(encoding="utf-8")
    rel = page.relative_to(ROOT)
    if not re.match(r"^\s*<!doctype html>", text, re.I):
        fail(f"{rel}: missing HTML5 doctype")

    parser = PageParser()
    parser.feed(text)

    if parser.html_lang.lower() != "en":
        fail(f"{rel}: html lang must be en")
    if not parser.has_viewport:
        fail(f"{rel}: missing viewport meta")
    if not parser.title_text.strip():
        fail(f"{rel}: missing title")
    if not parser.has_canonical:
        fail(f"{rel}: missing canonical link")
    if parser.main_count != 1:
        fail(f"{rel}: expected exactly one main landmark")
    if parser.h1_count != 1:
        fail(f"{rel}: expected exactly one h1")
    if not parser.has_skip:
        fail(f"{rel}: missing skip link")

    duplicates = sorted({item for item in parser.ids if parser.ids.count(item) > 1})
    if duplicates:
        fail(f"{rel}: duplicate ids: {', '.join(duplicates)}")

    for previous, current in zip(parser.headings, parser.headings[1:]):
        if current > previous + 1:
            fail(f"{rel}: heading level jumps h{previous} to h{current}")

    for image in parser.images:
        if "alt" not in image:
            fail(f"{rel}: img missing alt attribute")

    for field in parser.inputs:
        field_type = str(field.get("type") or "text").lower()
        if field_type == "hidden" or str(field.get("aria-hidden") or "").lower() == "true":
            continue
        field_id = str(field.get("id") or "")
        accessible_name = (
            bool(field.get("aria-label"))
            or bool(field.get("aria-labelledby"))
            or (field_id and field_id in parser.labels_for)
        )
        if not accessible_name:
            fail(f"{rel}: form input lacks an accessible label")

    for button in parser.buttons:
        if not (button.get("aria-label") or button.get("aria-labelledby") or button.get("_text")):
            fail(f"{rel}: button lacks an accessible name")

    for kind, value in parser.links:
        target = resolve_local(page, value)
        if target is None:
            continue
        try:
            inside = target.resolve().is_relative_to(ROOT.resolve())
        except AttributeError:
            inside = str(target.resolve()).startswith(str(ROOT.resolve()))
        if inside and not target.exists():
            fail(f"{rel}: broken local {kind} reference: {value}")
        if inside and target.exists() and target.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            referenced_images.add(target)

for css_file in css_files:
    rel = css_file.relative_to(ROOT)
    if css_file.stat().st_size > MAX_CSS_BYTES:
        fail(f"{rel}: CSS exceeds {MAX_CSS_BYTES // 1024} KiB launch guardrail")
    text = css_file.read_text(encoding="utf-8")
    for raw in re.findall(r"url\(([^)]+)\)", text, flags=re.I):
        value = raw.strip().strip("'\"")
        target = resolve_local(css_file, value)
        if target is None:
            continue
        try:
            inside = target.resolve().is_relative_to(ROOT.resolve())
        except AttributeError:
            inside = str(target.resolve()).startswith(str(ROOT.resolve()))
        if inside and not target.exists():
            fail(f"{rel}: broken CSS asset reference: {value}")
        if inside and target.exists() and target.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
            referenced_images.add(target)

for js_file in js_files:
    rel = js_file.relative_to(ROOT)
    if js_file.stat().st_size > MAX_JS_BYTES:
        fail(f"{rel}: JavaScript exceeds {MAX_JS_BYTES // 1024} KiB launch guardrail")
    text = js_file.read_text(encoding="utf-8")
    if "innerHTML" in text:
        fail(f"{rel}: avoid innerHTML in public site JavaScript")

for asset in sorted(referenced_images):
    if asset.stat().st_size > MAX_REFERENCED_IMAGE_BYTES:
        fail(
            f"{asset.relative_to(ROOT)}: referenced image exceeds "
            f"{MAX_REFERENCED_IMAGE_BYTES // 1024} KiB launch guardrail"
        )

styles = (ROOT / "styles.css").read_text(encoding="utf-8")
if "focus-visible" not in styles:
    fail("styles.css: missing visible focus treatment")
if "prefers-reduced-motion: reduce" not in styles:
    fail("styles.css: missing reduced-motion handling")
if re.search(r"a:hover\s*\{[^}]*opacity\s*:", styles, re.S):
    fail("styles.css: global link hover must not reduce text opacity")

variables = dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", styles))
for foreground, background, minimum in [
    ("muted", "paper", 4.5),
    ("accent-text", "paper", 4.5),
    ("orange-text", "paper", 4.5),
    ("ink", "accent", 4.5),
    ("ink", "orange", 4.5),
]:
    if foreground not in variables or background not in variables:
        fail(f"styles.css: missing colour token for {foreground}/{background} contrast check")
        continue
    ratio = contrast(variables[foreground], variables[background])
    if ratio < minimum:
        fail(f"styles.css: {foreground}/{background} contrast {ratio:.2f}:1 is below {minimum}:1")

required_rules = {
    ".track-creativity": "var(--accent-text)",
    ".track-brands": "var(--orange-text)",
    ".discovery-grid span": "var(--accent-text)",
}
for selector, value in required_rules.items():
    match = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", styles, re.S)
    if not match or value not in match.group(1):
        fail(f"styles.css: {selector} must use {value}")

if errors:
    print("SPURN site acceptance FAILED")
    for item in errors:
        print(f"- {item}")
    sys.exit(1)

total_image_bytes = sum(path.stat().st_size for path in referenced_images)
print(
    "SPURN site acceptance PASSED: "
    f"{len(html_files)} HTML routes, {len(referenced_images)} referenced images "
    f"({total_image_bytes / 1024:.1f} KiB), "
    f"{len(css_files)} CSS files, {len(js_files)} JS files."
)
