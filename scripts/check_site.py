#!/usr/bin/env python3
"""Check the finished site: the page must show exactly the signed words.

`release.py --check` proves only that each stage would regenerate its output
identically, which passes by construction in the job that just regenerated
everything. Nothing looked at the finished page. This does, read-only:

1. The letter on docs/index.html has exactly the words of docs/letter.md (the
   signed text), in order. The comparison strips Markdown syntax from the source
   and tags from the page and compares words. It deliberately does NOT use the
   Markdown library the renderer uses: a library change would alter both sides
   the same way and pass unnoticed.
2. Only one piece of site chrome lives inside the letter: the button bar after
   the sign-off. The sign-off itself is present.
3. The generated markers each appear exactly once and name the newest release.
4. Every in-page link (#...) points at an id that exists, and no id repeats.
5. Every Table of Contents entry is a link.
6. docs/overview.html still says what docs/overview.md says (it is maintained by
   hand and once drifted for weeks), and its JSON-LD fingerprint matches
   keys/FINGERPRINT.

Usage:
    python3 scripts/check_site.py [--check]
(--check is accepted so release.py can run every stage the same way; this
script never writes anything.) Exit status 0 when every check passes.
"""

from __future__ import annotations

import argparse
import difflib
import html
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS = REPO_ROOT / "docs"

RENDER_START = "<!-- render-letter:start -->"
RENDER_END = "<!-- render-letter:end -->"
SINGLE_MARKERS = (
    RENDER_START,
    RENDER_END,
    "<!-- structured-data:start -->",
    "<!-- structured-data:end -->",
    "<!-- OTS-START -->",
    "<!-- OTS-END -->",
)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Accepted for release.py; no effect.")
    return parser.parse_args(list(argv))


# --- words ---------------------------------------------------------------------

def tokens(text: str) -> List[str]:
    return re.findall(r"\w+|[^\w\s]", text)


def markdown_words(markdown: str) -> List[str]:
    """The words a reader sees in rendered Markdown, without rendering it."""

    text = re.sub(r"(?m)^[\s|:-]*-{3,}[\s|:-]*$", " ", markdown)    # table rule rows and --- breaks
    text = re.sub(r"\]\([^)]*\)", "]", text)                     # link targets
    text = re.sub(r"<(https?://[^>\s]+)>", r"\1", text)          # autolinks
    text = re.sub(r"(?m)^\s*(?:[-*_]\s*){3,}$", " ", text)       # thematic breaks
    text = re.sub(r"(?m)^\s*(#{1,6}|[-*+]|\d+\.|>)\s", " ", text)  # headings, list and quote markers
    text = re.sub(r"\\(.)", r"\1", text)                         # backslash escapes
    text = re.sub(r"[*_`\[\]|]", " ", text)                      # emphasis, code, brackets, table pipes
    return tokens(text)


def html_words(fragment: str) -> List[str]:
    fragment = re.sub(r"(?s)<script\b.*?</script>", " ", fragment)
    fragment = re.sub(r"<wbr\s*/?>", "", fragment)  # a line-break hint, not a space
    fragment = re.sub(r"<[^>]+>", " ", fragment)
    fragment = html.unescape(fragment)
    fragment = re.sub(r"[*_`\[\]|]", " ", fragment)
    return tokens(fragment)


def compare(name: str, page: List[str], source: List[str], errors: List[str]) -> None:
    if page == source:
        return
    shown = 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, page, source, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        errors.append(
            f"{name}: page and signed source differ ({op}): "
            f"page {' '.join(page[i1:i2])[:100]!r} vs source {' '.join(source[j1:j2])[:100]!r}"
        )
        shown += 1
        if shown == 5:
            errors.append(f"{name}: (further differences not shown)")
            break


# --- checks --------------------------------------------------------------------

def latest_release() -> dict:
    manifest = json.loads((REPO_ROOT / "letter" / "RELEASES.json").read_text(encoding="utf-8"))
    return max(manifest["releases"], key=lambda r: r["version"])


def check_index(errors: List[str]) -> None:
    page = (DOCS / "index.html").read_text(encoding="utf-8")

    for marker in SINGLE_MARKERS:
        count = page.count(marker)
        if count != 1:
            errors.append(f"index.html: marker {marker} appears {count} times (expected 1)")
    if page.count(RENDER_START) != 1 or page.count(RENDER_END) != 1:
        return  # nothing below is meaningful without the letter block

    latest = latest_release()
    tag = "v" + latest["version"]
    if f'data-release-version="{tag}"' not in page:
        errors.append(f"index.html: data-release-version does not name the newest release {tag}")
    if not re.search(r"<!--\s*release-version:\s*" + re.escape(tag) + r"\s*-->", page):
        errors.append(f"index.html: release-version comment does not name {tag}")
    title = re.search(r"<title>([^<]*)</title>", page)
    expected = latest.get("label") or tag
    if not title or expected not in title.group(1):
        errors.append(f"index.html: <title> does not name {expected}")

    letter = page.split(RENDER_START, 1)[1].split(RENDER_END, 1)[0]

    navs = re.findall(r"<nav\b[^>]*>", letter)
    if len(navs) != 1 or 'id="cta-bar"' not in navs[0]:
        errors.append(f"index.html: expected exactly one <nav> (the button bar) inside the letter, found {len(navs)}")
    if letter.count('<footer class="signature">') != 1:
        errors.append("index.html: the sign-off footer is missing or repeated")

    # The button bar is site chrome; everything else inside the markers is the letter.
    words_only = re.sub(r'(?s)<nav class="cta-bar".*?</nav>', " ", letter)
    source = (DOCS / "letter.md").read_text(encoding="utf-8")
    compare("index.html", html_words(words_only), markdown_words(source), errors)

    ids = re.findall(r'\bid="([^"]+)"', page)
    seen, repeated = set(), set()
    for element_id in ids:
        (repeated if element_id in seen else seen).add(element_id)
    for element_id in sorted(repeated):
        errors.append(f"index.html: id {element_id!r} is used more than once")
    for target in sorted(set(re.findall(r'href="#([^"]*)"', page))):
        if target and html.unescape(target) not in seen:
            errors.append(f"index.html: link to #{target} has no target")

    toc = re.search(r'(?s)<h2 id="table-of-contents">.*?(?=<h2 )', letter)
    if not toc:
        errors.append("index.html: Table of Contents not found")
    else:
        for item in re.findall(r"(?s)<li>(.*?)</li>", toc.group(0)):
            if '<a href="#' not in item:
                errors.append(f"index.html: Table of Contents entry is not a link: {html_words(item)[:8]}")


def check_overview(errors: List[str]) -> None:
    page = (DOCS / "overview.html").read_text(encoding="utf-8")
    source = (DOCS / "overview.md").read_text(encoding="utf-8")

    heading = re.search(r"(?s)<h1>(.*?)</h1>", page)
    content = re.search(r'(?s)<div class="content">(.*?)</div>\s*<nav class="footer-nav">', page)
    if not heading or not content:
        errors.append("overview.html: expected an <h1> and <div class=\"content\"> followed by the footer nav")
        return
    compare("overview.html", html_words(heading.group(1) + " " + content.group(1)), markdown_words(source), errors)

    fingerprint = "".join(
        ch for ch in (REPO_ROOT / "keys" / "FINGERPRINT").read_text(encoding="utf-8-sig") if ch in "0123456789abcdefABCDEF"
    ).upper()
    declared = re.findall(r"openpgp4fpr:([0-9A-Fa-f]{40})", page)
    if not declared or any(value.upper() != fingerprint for value in declared):
        errors.append(f"overview.html: JSON-LD fingerprint {declared} does not match keys/FINGERPRINT {fingerprint}")


def main(argv: Iterable[str]) -> int:
    parse_args(argv)
    errors: List[str] = []
    check_index(errors)
    check_overview(errors)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print("  site shows exactly the signed text; markers, links and contents check out")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
