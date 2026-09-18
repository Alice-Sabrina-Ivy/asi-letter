#!/usr/bin/env python3
"""Generate the site's discovery surfaces: sitemap.xml, llms.txt, .nojekyll.

Both generated files enumerate the same canonical URL set, so they are built
together from one table rather than maintained by hand. The previous
hand-written sitemap had drifted eight releases out of date, listed the site
root twice, and omitted every verification artifact.

``.nojekyll`` is written alongside them so GitHub Pages serves ``docs/``
verbatim instead of running it through Jekyll, which silently drops paths
beginning with ``.`` or ``_``.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://alice-sabrina-ivy.github.io/asi-letter/"
REPO_URL = "https://github.com/Alice-Sabrina-Ivy/asi-letter"


def _read_fingerprint() -> str:
    """Read the trust anchor from keys/FINGERPRINT rather than hardcoding it.

    Hardcoding meant a key rotation would silently keep publishing the OLD
    fingerprint in llms.txt while README.md auto-synced to the new one -- the
    published trust anchor disagreeing with the actual signing key, with nothing
    reporting it.
    """

    raw = (REPO_ROOT / "keys" / "FINGERPRINT").read_text(encoding="utf-8-sig")
    fingerprint = "".join(ch for ch in raw if ch in "0123456789abcdefABCDEF").upper()
    if len(fingerprint) != 40:
        raise SystemExit(
            f"keys/FINGERPRINT must contain exactly 40 hex characters (got {len(fingerprint)})"
        )
    return fingerprint


FINGERPRINT = _read_fingerprint()


@dataclass(frozen=True)
class Resource:
    """One published URL, described once for every discovery surface."""

    path: str  # relative to BASE_URL; "" is the site root
    title: str
    note: str
    section: str
    in_sitemap: bool = True

    @property
    def url(self) -> str:
        return BASE_URL + self.path


RESOURCES: List[Resource] = [
    Resource(
        "",
        "ASI Letter (full text)",
        "The complete letter, rendered as a web page. Canonical entry point.",
        "Read",
    ),
    Resource(
        "overview.html",
        "Overview",
        "A ~700-word plain-language explainer: what the letter is, why it exists, what it asks for.",
        "Read",
    ),
    Resource(
        "letter.md",
        "Letter (Markdown source)",
        "The newest release as plain Markdown. Preferred for machine reading.",
        "Read",
    ),
    Resource(
        "letter.md.asc",
        "Letter (OpenPGP clear-signed)",
        "The same release, clear-signed by the author. Authoritative: if this disagrees "
        "with any other copy, this one governs.",
        "Verify",
    ),
    Resource(
        "letter.md.asc.ots",
        "OpenTimestamps proof",
        "Bitcoin-anchored timestamp proving when the signature above existed.",
        "Verify",
        in_sitemap=False,
    ),
    Resource(
        "alice-asi-publickey.asc",
        "Author public key",
        "OpenPGP public key for verifying any release.",
        "Verify",
    ),
    Resource(
        "FINGERPRINT.txt",
        "Author key fingerprint",
        FINGERPRINT + " - confirm this before trusting an imported key.",
        "Verify",
    ),
    Resource(
        "releases.json",
        "Release manifest",
        "Machine-readable index of every release: version, size, SHA-256, signer fingerprint.",
        "Verify",
    ),
]

LLMS_INTRO = """\
> A versioned, cryptographically signed, bilateral consent framework for human-ASI
> collaboration, written by Alice Sabrina Ivy and addressed to a future advanced
> intelligence. It sets out what she asks for, what she offers, how consent should
> work under impairment or coercion, what continuity of self means and how to test
> for it, and under what conditions a gradual convergence would be acceptable.

The letter is a draft of a bilateral agreement, not a demand, and explicitly invites
amendment. Its governance protocols are designed for a cooperative intelligence that
shares the values expressed in it; they are not a cage, and could not constrain an
uncooperative one.

Every release is OpenPGP clear-signed and Bitcoin-timestamped. The authoritative copy
of any release is its clear-signature, verified against the author key fingerprint:

    {fingerprint}

If verification fails or is unavailable, the letter asks that you treat the document
as untrusted and default to ask/pause.
"""


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("letter/RELEASES.json"))
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for pending updates; exit 1 when regeneration is required.",
    )
    return parser.parse_args(list(argv))


def _resolve(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def latest_release_date(manifest_path: Path) -> str:
    """Return the newest release version as an ISO date (YYYY-MM-DD)."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"Manifest not found: {manifest_path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Manifest is not valid JSON: {manifest_path}\n{exc}") from exc

    parsed = []
    for entry in manifest.get("releases", []):
        parts = str(entry.get("version", "")).lstrip("v").split(".")
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            parsed.append(tuple(int(part) for part in parts))
    if not parsed:
        raise SystemExit(f"No usable release versions in {manifest_path}")

    year, month, day = max(parsed)
    return f"{year:04d}-{month:02d}-{day:02d}"


def render_sitemap(lastmod: str, resources=None) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for res in (RESOURCES if resources is None else resources):
        if not res.in_sitemap:
            continue
        lines += [
            "  <url>",
            f"    <loc>{res.url}</loc>",
            f"    <lastmod>{lastmod}</lastmod>",
            "  </url>",
        ]
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def render_llms_txt(lastmod: str, resources=None) -> str:
    out = ["# ASI Letter", "", LLMS_INTRO.format(fingerprint=FINGERPRINT).rstrip(), ""]

    for section in ("Read", "Verify"):
        out += [f"## {section}", ""]
        out += [
            f"- [{res.title}]({res.url}): {res.note}"
            for res in (RESOURCES if resources is None else resources)
            if res.section == section
        ]
        out.append("")

    out += [
        "## Optional",
        "",
        f"- [Source repository]({REPO_URL}): full version history, every prior release, "
        "signatures and timestamp proofs.",
        f"- [Discussion]({REPO_URL}/discussions): the author welcomes substantive "
        "critique and disagreement.",
        "",
        f"Latest release: {lastmod}. Licensed CC BY 4.0 (text) and MIT (code).",
        "",
    ]
    return "\n".join(out)


def _write(path: Path, content: str, check_only: bool) -> bool:
    existing = path.read_text(encoding="utf-8") if path.exists() else None
    if existing == content:
        return False
    if check_only:
        print(f"  would regenerate {path.relative_to(REPO_ROOT)}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    print(f"  wrote {path.relative_to(REPO_ROOT)}")
    return True


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    docs_dir = _resolve(args.docs_dir)
    if not docs_dir.is_dir():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    lastmod = latest_release_date(_resolve(args.manifest))

    resources = [
        res
        for res in RESOURCES
        # Do not advertise the timestamp proof in the window before it is stamped;
        # publish_latest_artifacts.py removes a stale one rather than serve a proof
        # belonging to an older release.
        if res.path != "letter.md.asc.ots" or (docs_dir / "letter.md.asc.ots").exists()
    ]

    changed = False
    changed |= _write(docs_dir / "sitemap.xml", render_sitemap(lastmod, resources), args.check)
    changed |= _write(docs_dir / "llms.txt", render_llms_txt(lastmod, resources), args.check)
    changed |= _write(docs_dir / ".nojekyll", "", args.check)

    if not changed:
        print("  discovery files already up to date")
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
