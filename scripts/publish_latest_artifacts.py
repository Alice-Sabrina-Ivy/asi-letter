#!/usr/bin/env python3
"""Publish the newest release's verification artifacts under stable docs/ names.

The signed releases in ``letter/`` are version-pinned and live outside the
GitHub Pages root, so nothing that crawls the site ever reaches a signature,
an OpenTimestamps proof, or the public key. This stage copies the newest
release's artifacts into ``docs/`` under names that never change, giving both
humans and automated agents a permanent URL to fetch:

    docs/letter.md              (written by sync_docs_with_latest.py)
    docs/letter.md.asc          clear-signed newest release
    docs/letter.md.asc.ots      OpenTimestamps proof for that signature
    docs/alice-asi-publickey.asc  author public key
    docs/FINGERPRINT.txt        author key fingerprint
    docs/releases.json          machine-readable release manifest

``.asc``/``.ots`` files in ``letter/`` remain the authoritative originals;
these are byte-identical copies, so verification succeeds against either path.
(``.asc`` and ``.ots`` are marked ``-text`` in .gitattributes so they survive
check-in byte for byte and keep matching the hashes in RELEASES.json.)

This stage also refreshes ``scripts/asi-public.asc``, the convenience copy of
the public key that ``verify-clearsign.sh`` imports. It is a hand-maintained
duplicate that had already drifted: it still carried the key export that
expired 2026-09-15, so CI was importing an expired key and verifying every
release against it. Deriving it here means it cannot drift again.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--letter-dir", type=Path, default=Path("letter"))
    parser.add_argument("--keys-dir", type=Path, default=Path("keys"))
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if updates are needed; exit 1 when publishing is required.",
    )
    return parser.parse_args(list(argv))


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def _parse_version(path: Path) -> Optional[Tuple[int, int, int]]:
    """Mirror sync_docs_with_latest.py's version parsing."""
    name = path.name
    if not name.startswith("ASI-Letter-v") or not name.endswith(".md"):
        return None
    parts = name[len("ASI-Letter-v") : -len(".md")].split(".")
    if len(parts) != 3:
        return None
    try:
        return tuple(int(part) for part in parts)  # type: ignore[return-value]
    except ValueError:
        return None


def discover_latest_md(letter_dir: Path) -> Path:
    candidates = []
    for md_path in letter_dir.glob("ASI-Letter-v*.md"):
        version = _parse_version(md_path)
        if version is not None:
            candidates.append((version, md_path))
    if not candidates:
        raise SystemExit(f"No ASI-Letter markdown files found in {letter_dir}")
    return max(candidates, key=lambda item: item[0])[1]


def plan_copies(letter_dir: Path, keys_dir: Path, docs_dir: Path) -> List[Tuple[Path, Path]]:
    latest_md = discover_latest_md(letter_dir)
    asc = latest_md.with_name(latest_md.name + ".asc")
    ots = asc.with_name(asc.name + ".ots")

    public_key = keys_dir / "alice-asi-publickey.asc"

    pairs: List[Tuple[Path, Path]] = [
        (asc, docs_dir / "letter.md.asc"),
        (public_key, docs_dir / "alice-asi-publickey.asc"),
        (keys_dir / "FINGERPRINT", docs_dir / "FINGERPRINT.txt"),
        (letter_dir / "RELEASES.json", docs_dir / "releases.json"),
        # Convenience copy imported by verify-clearsign.sh; derived, not edited.
        (public_key, REPO_ROOT / "scripts" / "asi-public.asc"),
    ]

    missing = [str(src) for src, _ in pairs if not src.exists()]
    if missing:
        raise SystemExit("Missing required source artifact(s):\n  " + "\n  ".join(missing))

    # The OTS proof is deliberately OPTIONAL. There is a real window -- between a
    # new .asc being pushed and ots-stamp-letter-asc.yml producing its proof --
    # where the newest release has no .ots yet. gen_releases_manifest.py already
    # tolerates this and records "ots": null; treating it as fatal here made this
    # stage stricter than the rest of the pipeline and turned that ordinary race
    # into a red build.
    if ots.exists():
        pairs.append((ots, docs_dir / "letter.md.asc.ots"))
    return pairs


def prune_stale_ots(letter_dir: Path, docs_dir: Path, check_only: bool) -> bool:
    """Drop a published proof that belongs to an older release.

    Serving the previous release's .ots beside the current .asc would be worse
    than serving none: it looks like a valid timestamp for a document it does not
    attest. Once the proof is stamped, the next run republishes it.
    """

    latest_md = discover_latest_md(letter_dir)
    ots = latest_md.with_name(latest_md.name + ".asc.ots")
    published = docs_dir / "letter.md.asc.ots"
    if ots.exists() or not published.exists():
        return False
    if check_only:
        print(f"  would remove {published.relative_to(REPO_ROOT)} (no proof for newest release yet)")
        return True
    published.unlink()
    print(f"  removed {published.relative_to(REPO_ROOT)} (no proof for newest release yet)")
    return True


def publish(letter_dir: Path, keys_dir: Path, docs_dir: Path, check_only: bool) -> bool:
    changed = False
    for src, dest in plan_copies(letter_dir, keys_dir, docs_dir):
        payload = src.read_bytes()
        if dest.exists() and dest.read_bytes() == payload:
            continue
        changed = True
        if check_only:
            print(f"  would publish {dest.relative_to(REPO_ROOT)} <- {src.relative_to(REPO_ROOT)}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        print(f"  published {dest.relative_to(REPO_ROOT)} <- {src.relative_to(REPO_ROOT)}")
    changed |= prune_stale_ots(letter_dir, docs_dir, check_only)

    if not changed:
        print("  stable artifacts already up to date")
    return changed


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    letter_dir = _resolve(args.letter_dir)
    keys_dir = _resolve(args.keys_dir)
    docs_dir = _resolve(args.docs_dir)

    for label, path in (("Letter", letter_dir), ("Keys", keys_dir), ("Docs", docs_dir)):
        if not path.is_dir():
            raise SystemExit(f"{label} directory not found: {path}")

    needs_update = publish(letter_dir, keys_dir, docs_dir, args.check)
    return 1 if (args.check and needs_update) else 0


if __name__ == "__main__":
    raise SystemExit(main())
