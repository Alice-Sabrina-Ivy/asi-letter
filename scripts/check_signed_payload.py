#!/usr/bin/env python3
"""Verify each letter/*.md is the text that its sibling *.md.asc actually signed.

`gpg --verify` on a clear-signed file validates the text embedded *inside* the
.asc. It never looks at the sibling .md, so the signature check passes no matter
what the .md contains. Nothing else in the pipeline closed that gap either, yet
every downstream stage trusts the .md: it becomes docs/letter.md, it is rendered
into docs/index.html, it is uploaded as a GitHub Release asset, and its sha256 is
recorded in RELEASES.json beside a verified signer block.

That is not hypothetical. letter/ASI-Letter-v2025.09.14.md diverged from its
signed payload on 18 lines -- the signed text has horizontal rules (`---`) while
the file on disk kept the clearsign dash-escaping (`- ---`), i.e. the .md was a
transcript copied out of the .asc rather than the signed document.

CANONICALIZATION (important -- a naive byte compare is wrong here)
RFC 4880 clear-signing legitimately normalizes the text it hashes: trailing
whitespace on each line is stripped and the final newline is normalized. This
letter uses trailing double-spaces as Markdown hard breaks, so a raw `cmp`
reports a difference for 7 of the 14 existing releases that are in fact correct.
Only a canonicalized comparison distinguishes benign normalization from a real
divergence.

Usage:
    python3 scripts/check_signed_payload.py [--letter-dir PATH] [--gpg BINARY]
Exit status 0 when every .md matches its signed payload, 1 otherwise.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--letter-dir", type=Path, default=Path("letter"))
    parser.add_argument(
        "--fingerprint-file",
        type=Path,
        default=Path("keys/FINGERPRINT"),
        help="Trust anchor to require in VALIDSIG (default: keys/FINGERPRINT).",
    )
    parser.add_argument(
        "--no-fingerprint-check",
        action="store_true",
        help="Only require a good signature, without binding it to the trusted key.",
    )
    parser.add_argument(
        "--gpg",
        default="gpg",
        help="gpg binary to use for extracting the signed payload (default: gpg).",
    )
    return parser.parse_args(list(argv))


def canonical_lines(text: str) -> List[str]:
    """Reduce text to the form the clear-signature actually covers.

    RFC 4880 s7.1 ignores exactly two things: trailing SPACE and TAB on each
    line, and the line ending of the final line. Nothing else.

    Both bounds matter. Using str.rstrip() would also strip Unicode whitespace
    (NBSP, U+2028, ...) that IS signed, letting a real modification pass. And
    dropping every trailing blank line would hide added or removed blank lines
    at EOF, which are likewise signed -- only the one final line terminator is
    not.
    """

    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    # Undo the split artefact from the final line terminator only.
    if lines and lines[-1] == "":
        lines.pop()
    return [line.rstrip(" \t") for line in lines]


def extract_payload(gpg: str, asc_path: Path, fingerprint: Optional[str]) -> Optional[str]:
    """Return the signed text, or None if the signature is not good.

    gpg writes the cleartext of a clear-signed file BEFORE it evaluates the
    signature, so the output file exists even for a forged signature or an
    absent public key. Testing only "did a file appear" therefore verified
    nothing: an attacker who edited both the .md and the cleartext inside the
    .asc would be reported as matching. The signature must be checked here too,
    because this script is documented as a standalone verification command.
    """

    with tempfile.TemporaryDirectory(prefix="asi-payload-") as tmp:
        out = Path(tmp) / "payload.txt"
        result = subprocess.run(
            [
                gpg,
                "--batch",
                "--yes",
                "--status-fd=1",
                "--decrypt",
                "--output",
                str(out),
                str(asc_path),
            ],
            capture_output=True,
        )
        status = result.stdout.decode("utf-8", "replace")
        stderr = result.stderr.decode("utf-8", "replace").strip()

        if result.returncode != 0:
            sys.stderr.write(f"  gpg failed on {asc_path.name} (exit {result.returncode}): {stderr}\n")
            return None
        for bad in ("BADSIG", "ERRSIG", "NO_PUBKEY", "EXPKEYSIG", "REVKEYSIG"):
            if f"[GNUPG:] {bad}" in status:
                sys.stderr.write(f"  {asc_path.name}: gpg reported {bad}\n")
                return None
        if "[GNUPG:] VALIDSIG " not in status:
            sys.stderr.write(f"  {asc_path.name}: no VALIDSIG in gpg status output\n")
            return None

        if fingerprint:
            primary = ""
            for line in status.splitlines():
                if line.startswith("[GNUPG:] VALIDSIG "):
                    primary = line.split()[-1].upper()
                    break
            if primary != fingerprint:
                sys.stderr.write(
                    f"  {asc_path.name}: signed by {primary or '?'}, not the trusted key {fingerprint}\n"
                )
                return None

        if not out.exists():
            sys.stderr.write(f"  could not extract payload from {asc_path.name}: {stderr}\n")
            return None
        return out.read_text(encoding="utf-8", errors="replace")


def diff_summary(signed: List[str], on_disk: List[str], limit: int = 3) -> List[str]:
    notes: List[str] = []
    for index, (a, b) in enumerate(zip(signed, on_disk), start=1):
        if a != b:
            notes.append(f"    line {index}: signed {a!r} != on disk {b!r}")
            if len(notes) >= limit:
                break
    if len(signed) != len(on_disk):
        notes.append(f"    line count: signed {len(signed)} != on disk {len(on_disk)}")
    return notes


def read_fingerprint(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8-sig")
    fingerprint = "".join(ch for ch in raw if ch in "0123456789abcdefABCDEF").upper()
    if len(fingerprint) != 40:
        raise SystemExit(
            f"{path} must contain exactly 40 hex characters (got {len(fingerprint)})"
        )
    return fingerprint


def check_release(
    gpg: str, md_path: Path, asc_path: Path, fingerprint: Optional[str] = None
) -> Tuple[bool, List[str]]:
    payload = extract_payload(gpg, asc_path, fingerprint)
    if payload is None:
        return False, ["    signature not good, or payload could not be extracted"]

    signed = canonical_lines(payload)
    on_disk = canonical_lines(md_path.read_text(encoding="utf-8", errors="replace"))
    if signed == on_disk:
        return True, []
    return False, diff_summary(signed, on_disk)


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    letter_dir = args.letter_dir
    if not letter_dir.is_absolute():
        letter_dir = REPO_ROOT / letter_dir
    if not letter_dir.is_dir():
        raise SystemExit(f"Letter directory not found: {letter_dir}")

    fingerprint = None
    if not args.no_fingerprint_check:
        fp_path = args.fingerprint_file
        if not fp_path.is_absolute():
            fp_path = REPO_ROOT / fp_path
        fingerprint = read_fingerprint(fp_path)
        if fingerprint:
            print(f"Requiring signatures from {fingerprint}")

    asc_paths = sorted(letter_dir.glob("ASI-Letter-v*.md.asc"))
    if not asc_paths:
        # Vacuous success would be a silent pass; treat it as a failure.
        sys.stderr.write(f"No clear-signed letters found in {letter_dir}\n")
        return 1

    failures = 0
    for asc_path in asc_paths:
        md_path = asc_path.with_suffix("")  # strip ".asc"
        if not md_path.exists():
            print(f"MISSING  {md_path.name} (referenced by {asc_path.name})")
            failures += 1
            continue

        ok, notes = check_release(args.gpg, md_path, asc_path, fingerprint)
        if ok:
            print(f"ok       {md_path.name} matches its signed payload")
        else:
            failures += 1
            print(f"MISMATCH {md_path.name} is NOT the text signed in {asc_path.name}")
            for note in notes:
                print(note)

    print()
    if failures:
        print(f"{failures} of {len(asc_paths)} release(s) do not match their signed payload.")
        print("The .asc is authoritative: correct the .md to match it, never the reverse.")
        return 1

    print(f"All {len(asc_paths)} releases match the text that was signed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
