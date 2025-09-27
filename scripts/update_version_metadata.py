#!/usr/bin/env python3
"""Synchronize version metadata in generated assets with the latest release.

This script reads ``letter/RELEASES.json`` to locate the most recent release
and then updates known metadata placeholders (page title, data attributes,
comments, etc.) so they always reflect the latest signed version. Run this
before publishing the static site to avoid drift between the manifest and the
rendered HTML.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path("letter/RELEASES.json")
DEFAULT_TARGETS = (Path("docs/index.html"),)

_VERSION_RX = re.compile(r"\d{4}\.\d{2}\.\d{2}")


@dataclass
class VersionInfo:
    """Represents the parsed latest release information."""

    raw: str

    @property
    def tagged(self) -> str:
        """Return the display form (prefixed with ``v``)."""

        return f"v{self.raw}" if not self.raw.startswith("v") else self.raw


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help="Path to RELEASES.json (defaults to letter/RELEASES.json).",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check for pending updates; exit non-zero if changes are needed.",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        type=Path,
        default=list(DEFAULT_TARGETS),
        help="Files to rewrite (defaults to docs/index.html).",
    )
    return parser.parse_args(list(argv))


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else (REPO_ROOT / path)


def load_manifest(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError as exc:
        raise SystemExit(f"Manifest not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Manifest is not valid JSON: {path}\n{exc}") from exc


def select_latest_version(manifest: dict) -> VersionInfo:
    releases = manifest.get("releases")
    if not releases:
        raise SystemExit("No releases listed in manifest.")

    def key(entry: dict) -> Tuple[int, int, int]:
        version = entry.get("version")
        if not isinstance(version, str) or not _VERSION_RX.fullmatch(version):
            raise SystemExit(f"Unexpected version format: {version!r}")
        parts = version.split(".")
        return tuple(int(part) for part in parts)  # type: ignore[return-value]

    latest = max(releases, key=key)
    version = latest.get("version")
    if not isinstance(version, str):  # defensive, should not happen
        raise SystemExit("Latest release entry missing version string")
    return VersionInfo(raw=version)


def substitute_version_markers(text: str, version: VersionInfo) -> Tuple[str, int]:
    """Replace known placeholders with the latest version.

    Returns the updated text and the total number of substitutions performed.
    """

    replacements: List[Tuple[re.Pattern[str], str]] = [
        # Page title ("ASI Letter — vYYYY.MM.DD").
        (
            re.compile(r"(<title>\s*ASI Letter\s+—\s*)v" + _VERSION_RX.pattern + r"(\s*</title>)"),
            rf"\1{version.tagged}\2",
        ),
        # Attributes whose value is the tagged version (double quotes).
        (
            re.compile(r"(data-release-version\s*=\s*\")v?" + _VERSION_RX.pattern + r"(\")"),
            rf"\1{version.tagged}\2",
        ),
        # Attributes whose value is the tagged version (single quotes).
        (
            re.compile(r"(data-release-version\s*=\s*')v?" + _VERSION_RX.pattern + r"(')"),
            rf"\1{version.tagged}\2",
        ),
        # Boolean-style markers where the text node itself stores the version.
        (
            re.compile(r"(data-release-version[^>]*>)v?" + _VERSION_RX.pattern),
            rf"\1{version.tagged}",
        ),
        # Comment marker for debugging / downstream tooling.
        (
            re.compile(r"(<!--\s*release-version\s*:\s*)v?" + _VERSION_RX.pattern + r"(\s*-->)", re.IGNORECASE),
            rf"\1{version.tagged}\2",
        ),
    ]

    updated = text
    total = 0
    for pattern, replacement in replacements:
        updated, count = pattern.subn(replacement, updated)
        total += count
    return updated, total


def process_file(path: Path, version: VersionInfo, check_only: bool) -> bool:
    text = path.read_text(encoding="utf-8")
    updated, matches = substitute_version_markers(text, version)
    if matches == 0:
        raise SystemExit(f"No version markers found in {path}")

    if updated != text:
        if check_only:
            return True
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    manifest_path = resolve_path(args.manifest)
    manifest = load_manifest(manifest_path)
    version = select_latest_version(manifest)

    any_changes = False
    for target in args.targets:
        target_path = resolve_path(target)
        if not target_path.exists():
            raise SystemExit(f"Target not found: {target_path}")
        changed = process_file(target_path, version, args.check)
        any_changes = any_changes or changed
        if args.check and changed:
            try:
                rel = target_path.relative_to(REPO_ROOT)
            except ValueError:
                rel = target_path
            print(f"{rel} requires version update to {version.tagged}")

    if args.check and any_changes:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
