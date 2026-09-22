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


def require_markdown_it() -> "markdown_it":
    try:
        import markdown_it  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: install the 'markdown-it-py' package (pip install markdown-it-py)."
        ) from exc
    return markdown_it


def normalize(text: str) -> str:
    collapsed = (
        text.replace("\u00A0", " ")
        .replace("—", "-")
        .replace("–", "-")
    )
    collapsed = re.sub(r"\s+", " ", collapsed).strip().lower()
    return collapsed


def paragraph_text(element: ET.Element) -> str:
    return "".join(element.itertext()).strip()


def _is_bare_canonical_pointer(child: ET.Element) -> bool:
    """True only when the paragraph is *nothing but* a pointer at the repo.

    The CTA bar already carries a "Canonical source" button, so a paragraph that
    merely repeats that link is redundant and gets dropped. A paragraph that
    happens to *contain* the repo link among other prose is not redundant, and
    removing it loses signed content -- which is exactly what used to happen:
    the letter's closing block ("Version", "Core invariant", "Authenticity",
    "Verification failure", "Author key fingerprint", "Author key policy",
    "Canonical Source") is a single Markdown paragraph ending in a repo link, so
    matching on "contains a repo anchor" deleted the whole authenticity block
    from the rendered page while the signed .md kept it.
    """

    text = re.sub(r"\s+", " ", paragraph_text(child)).strip()
    anchors = [a for a in child.findall(".//a") if a.get("href") == REPO_URL]

    if not anchors:
        # A label-only paragraph such as "Canonical Source: <bare url>".
        return bool(re.fullmatch(r"canonical source\s*:?\s*\S*", text, flags=re.IGNORECASE))

    residue = text
    for anchor in anchors:
        anchor_text = re.sub(r"\s+", " ", "".join(anchor.itertext())).strip()
        if anchor_text:
            residue = residue.replace(anchor_text, " ")
    residue = re.sub(r"^\W*canonical source\W*:?", "", residue, flags=re.IGNORECASE)
    residue = re.sub(r"[\s:*_.,;—-]+", "", residue)
    return not residue


def remove_canonical_paragraphs(root: ET.Element) -> None:
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "p" and _is_bare_canonical_pointer(child):
                parent.remove(child)


def _wrap_in_signature_footer(parent: ET.Element, paragraphs: list) -> None:
    """Move `paragraphs` into a <footer class="signature"> in place.

    The paragraphs are re-parented verbatim. Nothing is rewritten, so the page
    can only ever display the sign-off exactly as it appears in the signed
    document.
    """

    index = list(parent).index(paragraphs[0])
    footer = ET.Element("footer", {"class": "signature"})
    for offset, paragraph in enumerate(paragraphs):
        parent.remove(paragraph)
        if offset == len(paragraphs) - 1 and len(paragraphs) > 1:
            paragraph.set("class", "pronouns")
        footer.append(paragraph)
    parent.insert(index, footer)


def ensure_signature(root: ET.Element) -> bool:
    """Style the letter's existing sign-off. Never invent one.

    This previously substituted a hardcoded footer for the real sign-off, and
    appended that same hardcoded text when it failed to find one -- so the page
    could show a closing that was not in the signed document at all. It now only
    wraps what is already there, and reports failure to the caller instead.
    """

    paragraph_items = []
    for parent in root.iter():
        for child in list(parent):
            if child.tag == "p":
                paragraph_items.append((parent, child))

    # Single-paragraph form: the sign-off, name and pronouns joined by soft breaks.
    for parent, paragraph in paragraph_items:
        text = normalize(paragraph_text(paragraph))
        if re.match(r"^until we meet.+alice sabrina ivy(\s+she/her)?$", text):
            _wrap_in_signature_footer(parent, [paragraph])
            return True

    # Three-paragraph form: separated by blank lines.
    for index in range(len(paragraph_items) - 2):
        parent, first = paragraph_items[index]
        if paragraph_items[index + 1][0] is not parent or paragraph_items[index + 2][0] is not parent:
            continue
        t0 = normalize(paragraph_text(first))
        t1 = normalize(paragraph_text(paragraph_items[index + 1][1]))
        t2 = normalize(paragraph_text(paragraph_items[index + 2][1]))
        if t0 in {"until we meet", "until we meet-"} and t1 == "alice sabrina ivy" and t2 in {
            "she/her",
            "she / her",
        }:
            _wrap_in_signature_footer(
                parent,
                [first, paragraph_items[index + 1][1], paragraph_items[index + 2][1]],
            )
            return True

    return False


def github_slug(text: str) -> str:
    """Slugify a heading the way GitHub does.

    Matching GitHub's rule is deliberate: the same anchor then resolves both on
    the published site and on GitHub's own rendering of letter/*.md, so a link
    someone saves keeps working in either place.

    Lowercase, drop everything that is not a word character, hyphen or space,
    then turn spaces into hyphens. (Punctuation vanishes rather than becoming a
    separator, so "Why I'm writing - and why" yields a doubled hyphen exactly as
    GitHub produces.)
    """

    slug = text.strip().lower()
    slug = re.sub(r"[^\w\- ]", "", slug, flags=re.UNICODE)
    return slug.replace(" ", "-")


def add_heading_anchors(root: ET.Element) -> dict:
    """Give every heading an id and return {normalized heading text: slug}.

    Ids are derived from the heading text on every build, never stored, so
    sections can be added, removed, reordered or reworded and the anchors simply
    follow. Collisions get GitHub's -1/-2 suffix.
    """

    seen: dict = {}
    index: dict = {}
    for element in root.iter():
        if element.tag not in {"h1", "h2", "h3", "h4"}:
            continue
        text = "".join(element.itertext()).strip()
        if not text:
            continue
        base = github_slug(text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        slug = base if count == 0 else f"{base}-{count}"
        element.set("id", slug)
        index.setdefault(normalize(text), slug)
    return index


def link_table_of_contents(root: ET.Element, headings: dict) -> None:
    """Turn the letter's Table of Contents entries into working links.

    The TOC is hand-written prose inside the signed document, so it is matched
    against the real headings at build time rather than assumed correct. An entry
    that matches nothing raises instead of quietly rendering as plain text: a
    silently half-linked contents page is exactly the kind of invisible
    degradation this pipeline keeps getting bitten by.
    """

    children = list(root)
    start = None
    for position, child in enumerate(children):
        if child.tag in {"h1", "h2", "h3"} and normalize("".join(child.itertext())) == "table of contents":
            start = position
            break
    if start is None:
        return

    unmatched = []
    for child in children[start + 1:]:
        if child.tag in {"h1", "h2"}:
            break  # end of the contents section
        for item in child.iter("li"):
            label = "".join(item.itertext()).strip()
            if not label:
                continue
            key = normalize(label)
            slug = headings.get(key)
            if slug is None:
                # The TOC often abbreviates a longer heading, e.g. the entry
                # "On the Alice-after predictive model" for the heading
                # "... (construction & validation)".
                matches = [s for k, s in headings.items() if k.startswith(key)]
                slug = matches[0] if len(matches) >= 1 else None
            if slug is None:
                unmatched.append(label)
                continue

            anchor = ET.Element("a", {"href": f"#{slug}"})
            anchor.text = item.text
            for sub in list(item):
                item.remove(sub)
                anchor.append(sub)
            item.text = None
            item.insert(0, anchor)

    if unmatched:
        raise SystemExit(
            "Table of Contents entries do not match any heading:\n  "
            + "\n  ".join(unmatched)
            + "\n\nThe contents list is part of the signed letter. Either the entry or the "
            "heading was reworded; make them agree in the next release."
        )


def add_link_attributes(root: ET.Element) -> None:
    for anchor in root.iter("a"):
        href = anchor.get("href", "")
        if href.startswith(("http://", "https://")):
            anchor.set("target", "_blank")
            rel = anchor.get("rel", "")
            rel_tokens = {token for token in rel.split() if token}
            rel_tokens.add("noopener")
            anchor.set("rel", " ".join(sorted(rel_tokens)))


def remove_existing_cta(root: ET.Element) -> None:
    for parent in root.iter():
        for child in list(parent):
            if child.tag != "nav":
                continue
            classes = (child.get("class") or "").split()
            if "cta-bar" in classes:
                parent.remove(child)


def insert_cta(root: ET.Element) -> None:
    """Insert the CTA bar after the signature footer.

    Two definitions of this function used to exist; the second silently shadowed
    the first, which meant remove_existing_cta() was never called and the
    nested-parent search was lost. This keeps both behaviours.
    """

    remove_existing_cta(root)
    cta_element = ET.fromstring(CTA_HTML)
    for parent in root.iter():
        for index, child in enumerate(list(parent)):
            if child.tag == "footer" and child.get("class") == "signature":
                parent.insert(index + 1, cta_element)
                return
    root.append(cta_element)

def render_markdown(markdown_text: str) -> RenderResult:
    """Render with CommonMark (plus GFM tables), the dialect GitHub uses.

    This used Python-Markdown, which only nests a list under 4-space indentation.
    The letter nests with 2-3 spaces, which CommonMark and GitHub accept, so the
    site silently flattened nested lists: axiom precedence tiers 2 and 3 rendered
    as stray text inside a bullet, and Phase 5's conditions fell out of Phase 5.
    Using the same dialect as GitHub keeps the page structurally identical to the
    signed Markdown as GitHub displays it.
    """

    markdown_it = require_markdown_it()
    renderer = markdown_it.MarkdownIt("commonmark", {"xhtmlOut": True}).enable("table")
    html = renderer.render(markdown_text)
    root = ET.fromstring(f"<div>{html}</div>")
    headings = add_heading_anchors(root)
    link_table_of_contents(root, headings)
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

    # Previously this flag was discarded and a hardcoded sign-off was appended in
    # its place, so a letter whose closing no longer matched would silently
    # publish a footer that was not in the signed document. Fail instead: the
    # rendered page must not contain words the author did not sign.
    if not render_result.signature_found:
        raise SystemExit(
            f"Could not locate the letter's sign-off in {markdown_path}.\n"
            "ensure_signature() only styles an existing sign-off; it never invents one.\n"
            "If the closing wording changed, update the patterns in ensure_signature()."
        )

    text = index_path.read_text(encoding="utf-8")
    updated, _ = replace_render_block(text, render_result.html)
    if updated != text:
        if check_only:
            return True
        index_path.write_text(updated, encoding="utf-8", newline="\n")
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
