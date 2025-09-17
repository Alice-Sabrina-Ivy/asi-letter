#!/usr/bin/env python3
"""Copy the newest signed letter's Markdown into the ``docs`` directory."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple


@dataclass(frozen=True)
class LetterRelease:
    """Simple representation of a published letter release."""

    version: Tuple[int, int, int]
    source_md: Path


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--letter-dir",
        type=Path,
        default=Path("letter"),
        help="Directory containing ASI-Letter-v*.md files (default: letter)",
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Destination docs directory (default: docs)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if updates are needed; exit 1 when sync is required.",
    )
    return parser.parse_args(list(argv))


def _parse_version(path: Path) -> Tuple[int, int, int] | None:
    name = path.name
    if not name.startswith("ASI-Letter-v") or not name.endswith(".md"):
        return None
    version_str = name[len("ASI-Letter-v") : -len(".md")]
    parts = version_str.split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def discover_latest(letter_dir: Path) -> LetterRelease:
    candidates: list[LetterRelease] = []
    for md_path in letter_dir.glob("ASI-Letter-v*.md"):
        version = _parse_version(md_path)
        if version is None:
            continue
        asc_path = md_path.with_name(md_path.name + ".asc")
        if not asc_path.exists():
            raise SystemExit(f"Missing signature for {md_path.name}: {asc_path} not found")
        candidates.append(LetterRelease(version=version, source_md=md_path))

    if not candidates:
        raise SystemExit(f"No ASI-Letter markdown files found in {letter_dir}")

    return max(candidates, key=lambda item: item.version)


def _needs_update(src: Path, dest: Path) -> bool:
    if not dest.exists():
        return True
    return src.read_bytes() != dest.read_bytes()


def _sync(src: Path, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not _needs_update(src, dest):
        return False
    dest.write_bytes(src.read_bytes())
    return True


def sync_latest(letter_dir: Path, docs_dir: Path, check_only: bool) -> bool:
    release = discover_latest(letter_dir)
    md_dest = docs_dir / "letter.md"

    md_changed = _needs_update(release.source_md, md_dest)

    if check_only:
        return md_changed

    return _sync(release.source_md, md_dest)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    letter_dir = args.letter_dir.resolve()
    docs_dir = args.docs_dir.resolve()

    if not letter_dir.is_dir():
        raise SystemExit(f"Letter directory not found: {letter_dir}")
    if not docs_dir.exists():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    needs_sync = sync_latest(letter_dir, docs_dir, args.check)
    if args.check and needs_sync:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
