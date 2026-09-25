#!/usr/bin/env python3
"""Verify each letter/*.asc.ots timestamps the exact bytes of its sibling .asc.

An OpenTimestamps proof opens with the SHA-256 of the file it was made for. The
release workflow stamps an .asc only when no .ots exists yet, so re-uploading a
corrected .asc under the same name silently keeps the proof of the earlier
upload. Nothing compared the two, and the proof then vouches for bytes that are
no longer in the repository.

That is not hypothetical. letter/ASI-Letter-v2026.03.14.md.asc (v1.3.0) was
uploaded three times on 2026-03-14; its proof covered the 22:09 UTC upload
(5a467c4), not the 22:51 UTC one that stayed (c22f043), which rewrote a
paragraph. The letter's own Verification section promises that each .asc.ots
covers "those exact .asc bytes".

A missing proof is not an error here: the release workflow runs this check
before it stamps, and a new release has no proof until then. A proof for
different bytes is an error, because restamping silently would move an old
release's timestamp to today without anyone deciding to.

Usage:
    python3 scripts/check_ots_digest.py [--letter-dir PATH]
Exit status 0 when every existing proof matches its file, 1 otherwise.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Iterable, Optional

# Serialized DetachedTimestampFile: magic, version (varuint 1), then the op that
# hashed the file and its digest (python-opentimestamps, core/timestamp.py).
HEADER_MAGIC = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
MAJOR_VERSION = 1
OP_SHA256 = 0x08


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--letter-dir", type=Path, default=Path("letter"))
    return parser.parse_args(list(argv))


def proof_digest(proof: bytes) -> Optional[str]:
    """Return the SHA-256 a proof commits to, or None if it isn't one we can read."""
    if not proof.startswith(HEADER_MAGIC):
        return None
    rest = proof[len(HEADER_MAGIC):]
    if len(rest) < 2 + 32 or rest[0] != MAJOR_VERSION or rest[1] != OP_SHA256:
        return None
    return rest[2:34].hex()


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    ascs = sorted(args.letter_dir.glob("*.asc"))
    if not ascs:
        print(f"No .asc files found under {args.letter_dir}/ -- nothing checked.", file=sys.stderr)
        return 1

    fail = 0
    for asc in ascs:
        ots = asc.with_name(asc.name + ".ots")
        if not ots.exists():
            print(f"note {asc}: no timestamp proof yet (the release workflow stamps it)")
            continue
        committed = proof_digest(ots.read_bytes())
        if committed is None:
            print(f"FAIL {ots}: not a SHA-256 OpenTimestamps proof this check can read")
            fail = 1
            continue
        actual = hashlib.sha256(asc.read_bytes()).hexdigest()
        if committed != actual:
            print(
                f"FAIL {ots}: proves {committed[:16]}..., but {asc.name} is {actual[:16]}... "
                "The proof timestamps different bytes (was the .asc re-uploaded?). "
                "Replace it with a proof of the current file, or restore the bytes it covers."
            )
            fail = 1
            continue
        print(f"ok   {ots} (sha256 {actual[:16]}...)")
    return fail


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
