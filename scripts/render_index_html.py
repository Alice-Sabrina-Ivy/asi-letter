#!/usr/bin/env python3
"""Render docs/index.html with the latest Markdown letter content.

This script pre-renders docs/letter.md into HTML and replaces the content between
the render markers in docs/index.html. It mirrors the runtime JavaScript layout
adjustments so the static site no longer needs client-side rendering.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INDEX = Path("docs/index.html")
DEFAULT_MARKDOWN = Path("docs/letter.md")

RENDER_START = "<!-- render-letter:start -->"
RENDER_END = "<!-- render-letter:end -->"
REPO_URL = "https://github.com/Alice-Sabrina-Ivy/asi-letter"
LETTER_URL = f"{REPO_URL}/blob/main/docs/letter.md"
KEYS_URL = f"{REPO_URL}/tree/main/keys"
CTA_HTML = f"""
<nav class="cta-bar" id="cta-bar">
  <a class="btn btn-primary" id="btn-repo" href="{REPO_URL}" target="_blank" rel="noopener" aria-label="Open repository on GitHub">
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M8 0C3.58 0 0 3.64 0 8.13c0 3.6 2.29 6.65 5.47 7.73.4.08.55-.18.55-.39 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.5-2.69-.96-.09-.23-.48-.96-.82-1.15-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.53.28-.87.51-1.07-1.78-.2-3.64-.91-3.64-4.05 0-.9.31-1.64.82-2.22-.08-.2-.36-1.02.08-2.12 0 0 .67-.22 2.2.85.64-.18 1.33-.27 2.01-.27.68 0 1.37.09 2.01.27 1.53-1.07 2.2-.85 2.2-.85.44 1.1.16 1.92.08 2.12.51.58.82 1.32.82 2.22 0 3.15-1.87 3.85-3.65 4.05.29.26.54.77.54 1.55 0 1.12-.01 2.03-.01 2.31 0 .21.15.47.55.39A8.06 8.06 0 0 0 16 8.13C16 3.64 12.42 0 8 0Z" fill="currentColor"/></svg>
    <span>Canonical source</span>
  </a>
  <a class="btn" id="btn-letter" href="{LETTER_URL}" target="_blank" rel="noopener">
    <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1h5l4 4v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1Zm5 1.5V5h3.5L9 2.5ZM5 7h6v1.5H5V7Zm0 3h6v1.5H5V10Z" fill="currentColor"/></svg>
    <span>Open letter.md</span>
  </a>
  <a class="btn" id="btn-verify" href="{KEYS_URL}" target="_blank" rel="noopener" title="View public keys">
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2l7 3v6c0 5-3.1 9.4-7 11-3.9-1.6-7-6-7-11V5l7-3zm0 2.2L7 5.2v5.5c0 4.1 2.6 7.9 5 9.2 2.4-1.3 5-5.1 5-9.2V5.2l-5-1zm4.3 5.6l-5 5a1 1 0 0 1-1.4 0l-2-2 1.4-1.4 1.3 1.3 4.3-4.3 1.4 1.4z" fill="currentColor"/></svg>
    <span>Public Keys</span>
  </a>
</nav>
""".strip()


@dataclass(frozen=True)
class RenderResult:
    html: str
    signature_found: bool


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--index",
        type=Path,
        default=DEFAULT_INDEX,
        help="Path to docs/index.html (default: docs/index.html).",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=DEFAULT_MARKDOWN,
        help="Path to docs/letter.md (default: docs/letter.md).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for pending updates; exit non-zero if changes are needed.",
    )
    return parser.parse_args(list(argv))


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def require_markdown() -> "markdown":
    try:
        import markdown  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: install the 'markdown' package (pip install markdown)."
        ) from exc
    return markdown


def normalize(text: str) -> str:
    collapsed = (
        text.replace("\u00A0", " ")
        .replace("—", "-")
        .replace("–", "-")
    )
    collapsed = re.sub(r"\s+", " ", collapsed).strip().lower()
    return collapsed


def make_signature_footer() -> ET.Element:
    footer_html = (
        "<footer class=\"signature\">"
        "<p>Until we meet—</p>"
        "<p>Alice Sabrina Ivy</p>"
        "<p class=\"pronouns\">she/her</p>"
        "</footer>"
    )
    return ET.fromstring(footer_html)


def paragraph_text(element: ET.Element) -> str:
    return "".join(element.itertext()).strip()


def remove_canonical_paragraphs(root: ET.Element) -> None:
    for parent in root.iter():
        children = list(parent)
        for child in children:
            if child.tag != "p":
                continue
            text = paragraph_text(child)
            if re.match(r"^canonical source\s*:", text, flags=re.IGNORECASE):
                parent.remove(child)
                continue
            for anchor in child.findall(".//a"):
                href = anchor.get("href")
                if href == REPO_URL:
                    parent.remove(child)
                    break


def ensure_signature(root: ET.Element) -> bool:
    signature_found = False
    paragraph_items = []
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "p":
                paragraph_items.append((parent, child))

    for parent, paragraph in paragraph_items:
        text = normalize(paragraph_text(paragraph))
        if re.match(r"^until we meet-?\s+alice sabrina ivy(\s+she/her)?$", text):
            children = list(parent)
            index = children.index(paragraph)
            parent.remove(paragraph)
            parent.insert(index, make_signature_footer())
            signature_found = True
            break

    if not signature_found:
        for index in range(len(paragraph_items) - 2):
            t0 = normalize(paragraph_text(paragraph_items[index][1]))
            t1 = normalize(paragraph_text(paragraph_items[index + 1][1]))
            t2 = normalize(paragraph_text(paragraph_items[index + 2][1]))
            if t0 in {"until we meet", "until we meet-"} and t1 == "alice sabrina ivy" and t2 in {
                "she/her",
                "she / her",
            }:
                parent, first = paragraph_items[index]
                children = list(parent)
                insert_at = children.index(first)
                parent.remove(first)
                parent.insert(insert_at, make_signature_footer())
                parent.remove(paragraph_items[index + 1][1])
                parent.remove(paragraph_items[index + 2][1])
                signature_found = True
                break

    if not signature_found:
        text_tail = normalize(" ".join(paragraph_text(item[1]) for item in paragraph_items))[-240:]
        if "until we meet" in text_tail and "alice sabrina ivy" in text_tail and "she/her" in text_tail:
            root.append(make_signature_footer())
            signature_found = True

    if not signature_found:
        root.append(make_signature_footer())

    return signature_found


def add_link_attributes(root: ET.Element) -> None:
    for anchor in root.iter("a"):
        href = anchor.get("href", "")
        if href.startswith(("http://", "https://")):
            anchor.set("target", "_blank")
            rel = anchor.get("rel", "")
            rel_tokens = {token for token in rel.split() if token}
            rel_tokens.add("noopener")
            anchor.set("rel", " ".join(sorted(rel_tokens)))


def insert_cta(root: ET.Element) -> None:
    cta_element = ET.fromstring(CTA_HTML)
    signature = root.find(".//footer[@class='signature']")
    if signature is not None:
        children = list(root)
        if signature in children:
            index = children.index(signature)
            root.insert(index + 1, cta_element)
            return
    root.append(cta_element)


def render_markdown(markdown_text: str) -> RenderResult:
    markdown = require_markdown()
    html = markdown.markdown(
        markdown_text,
        extensions=["extra", "sane_lists", "tables"],
        output_format="xhtml",
    )
    root = ET.fromstring(f"<div>{html}</div>")
    add_link_attributes(root)
    remove_canonical_paragraphs(root)
    signature_found = ensure_signature(root)
    insert_cta(root)
    rendered = "\n".join(ET.tostring(child, encoding="unicode") for child in list(root))
    return RenderResult(html=rendered, signature_found=signature_found)


def replace_render_block(text: str, render_html: str) -> Tuple[str, int]:
    pattern = re.compile(
        r"(?P<indent>^[ \t]*)" + re.escape(RENDER_START) + r".*?"
        + re.escape(RENDER_END),
        flags=re.DOTALL | re.MULTILINE,
    )
    match = pattern.search(text)
    if not match:
        raise SystemExit(
            f"Render markers not found in index.html. Expected {RENDER_START} ... {RENDER_END}."
        )
    indent = match.group("indent")
    indented_html = "\n".join(f"{indent}  {line}" if line else f"{indent}" for line in render_html.split("\n"))
    replacement = f"{indent}{RENDER_START}\n{indent}  <div id=\"md\">"
    if indented_html.strip():
        replacement += f"\n{indented_html}\n{indent}  </div>"
    else:
        replacement += f"\n{indent}  </div>"
    replacement += f"\n{indent}{RENDER_END}"
    updated = text[: match.start()] + replacement + text[match.end() :]
    return updated, 1


def process(index_path: Path, markdown_path: Path, check_only: bool) -> bool:
    markdown_text = markdown_path.read_text(encoding="utf-8")
    render_result = render_markdown(markdown_text)
    text = index_path.read_text(encoding="utf-8")
    updated, _ = replace_render_block(text, render_result.html)
    if updated != text:
        if check_only:
            return True
        index_path.write_text(updated, encoding="utf-8")
        return True
    return False


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    index_path = resolve_path(args.index)
    markdown_path = resolve_path(args.markdown)

    if not index_path.exists():
        raise SystemExit(f"Index HTML not found: {index_path}")
    if not markdown_path.exists():
        raise SystemExit(f"Markdown source not found: {markdown_path}")

    changed = process(index_path, markdown_path, args.check)
    if args.check and changed:
        try:
            rel = index_path.relative_to(REPO_ROOT)
        except ValueError:
            rel = index_path
        print(f"{rel} requires re-rendering")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
