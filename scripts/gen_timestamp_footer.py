#!/usr/bin/env python3
"""Generate the Bitcoin timestamp footer in docs/index.html.

The footer used to be assembled with printf inside ots-upgrade.yml, from a block
height read out of a SECOND, independent `ots upgrade` run on a /tmp copy rather
than from the proof actually committed. That is two sources of truth for one
claim. This reads the heights from the committed letter/*.asc.ots files, so the
number on the page is the number in the published proof.

It also gives the reader somewhere to go. A bare "Bitcoin block 959472" is not
checkable by anyone who does not already know what to do with it, so the height
links to a block explorer and the proof itself is offered for download beside
the instructions for verifying it.

NO NEW DEPENDENCIES
An OpenTimestamps proof stores a Bitcoin attestation as a fixed 8-byte tag
followed by two varints (payload length, then block height), so the heights are
read directly from the bytes. Verified to agree exactly with the opentimestamps
library on every proof in this repository. The pipeline therefore does not need
the opentimestamps client installed to render a correct footer.

EARLIEST ATTESTATION, NOT LATEST
A proof can carry attestations from several calendar servers; the first release
has four (915041, 915042, 915046, 915128). The claim is "existed prior to this
block", so the EARLIEST attestation is the tightest true statement. The older
helper (.github/scripts/extract_block_height.py) reports the highest, which is
still true but weaker.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
START = "<!-- OTS-START -->"
END = "<!-- OTS-END -->"

# Bitcoin block header attestation tag from the OpenTimestamps format.
ATTESTATION_TAG = bytes([0x05, 0x88, 0x96, 0x0D, 0x73, 0xD7, 0x19, 0x01])

EXPLORER = "https://mempool.space/block/"
VERIFY_ANCHOR = "https://github.com/Alice-Sabrina-Ivy/asi-letter#verify-bitcoin-timestamp-opentimestamps"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--letter-dir", type=Path, default=Path("letter"))
    parser.add_argument("--index", type=Path, default=Path("docs/index.html"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for pending updates; exit 1 when regeneration is required.",
    )
    return parser.parse_args(list(argv))


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def _read_varint(data: bytes, index: int) -> Tuple[int, int]:
    value = 0
    shift = 0
    while index < len(data):
        byte = data[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index
        shift += 7
    raise ValueError("truncated varint")


def block_heights(ots_path: Path) -> List[int]:
    """Every Bitcoin block height attested by this proof."""

    try:
        data = ots_path.read_bytes()
    except OSError:
        return []

    heights: List[int] = []
    cursor = 0
    while True:
        found = data.find(ATTESTATION_TAG, cursor)
        if found < 0:
            break
        try:
            _payload_len, after = _read_varint(data, found + len(ATTESTATION_TAG))
            height, _ = _read_varint(data, after)
            heights.append(height)
        except (ValueError, IndexError):
            pass
        cursor = found + 1
    return sorted(set(heights))


def _version(path: Path) -> Optional[Tuple[int, int, int]]:
    name = path.name
    if not name.startswith("ASI-Letter-v") or not name.endswith(".md.asc.ots"):
        return None
    parts = name[len("ASI-Letter-v") : -len(".md.asc.ots")].split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)  # type: ignore[return-value]


def discover(letter_dir: Path):
    proofs = []
    for path in letter_dir.glob("ASI-Letter-v*.md.asc.ots"):
        version = _version(path)
        if version is not None:
            proofs.append((version, path))
    if not proofs:
        return None, None
    proofs.sort()
    return proofs[0], proofs[-1]


def _fmt(version: Tuple[int, int, int]) -> str:
    return f"{version[0]:04d}-{version[1]:02d}-{version[2]:02d}"


def render_footer(letter_dir: Path) -> str:
    first, latest = discover(letter_dir)

    if latest is None:
        line = "Bitcoin anchoring pending. Proof will update automatically."
    else:
        heights = block_heights(latest[1])
        if heights:
            height = heights[0]  # earliest attestation = tightest true claim
            line = (
                f'This version is anchored in Bitcoin block '
                f'<a href="{EXPLORER}{height}" rel="noopener" target="_blank">'
                f"<strong>{height}</strong></a>, attesting that it existed prior to that block."
            )
        else:
            line = "Bitcoin anchoring pending. Proof will update automatically."

    extra = ""
    if first is not None and latest is not None and first[0] != latest[0]:
        first_heights = block_heights(first[1])
        if first_heights:
            extra = (
                f'\n  <p id="ots-first">The first release ({_fmt(first[0])}) is anchored in block '
                f'<a href="{EXPLORER}{first_heights[0]}" rel="noopener" target="_blank">'
                f"{first_heights[0]}</a>.</p>"
            )

    return (
        f"{START}\n"
        '<section id="timestamp-proof" style="max-width:48rem;margin:2rem auto 0 auto;'
        'padding-top:1rem;border-top:1px solid #e5e7eb;text-align:center;font-size:0.95rem;'
        'line-height:1.5;">\n'
        '  <h3 style="margin:0 0 .5rem 0;font-size:1.05rem;">Timestamp proof (Bitcoin)</h3>\n'
        f'  <p id="ots-line">{line}</p>'
        f"{extra}\n"
        '  <p id="ots-verify" style="font-size:0.9rem;">'
        '<a href="letter.md.asc.ots">Download the proof</a> &middot; '
        f'<a href="{VERIFY_ANCHOR}" rel="noopener" target="_blank">How to verify it</a></p>\n'
        "</section>\n"
        f"{END}"
    )


def apply(index_path: Path, footer: str, check_only: bool) -> bool:
    text = index_path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)

    if pattern.search(text):
        updated = pattern.sub(lambda _m: footer, text, count=1)
    elif "</body>" in text:
        updated = text.replace("</body>", f"{footer}\n</body>", 1)
    else:
        raise SystemExit(f"No OTS markers and no </body> in {index_path}")

    if updated == text:
        return False
    if check_only:
        print(f"  would regenerate the timestamp footer in {index_path.relative_to(REPO_ROOT)}")
        return True
    index_path.write_text(updated, encoding="utf-8", newline="\n")
    print(f"  wrote timestamp footer in {index_path.relative_to(REPO_ROOT)}")
    return True


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    letter_dir = _resolve(args.letter_dir)
    index_path = _resolve(args.index)
    if not letter_dir.is_dir():
        raise SystemExit(f"Letter directory not found: {letter_dir}")
    if not index_path.is_file():
        raise SystemExit(f"Index not found: {index_path}")

    changed = apply(index_path, render_footer(letter_dir), args.check)
    if not changed:
        print("  timestamp footer already up to date")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
