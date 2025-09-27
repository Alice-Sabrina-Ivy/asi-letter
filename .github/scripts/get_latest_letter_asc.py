#!/usr/bin/env python3
"""Select the most recent letter .asc path from RELEASES.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterable, Optional


def iter_candidates(path_value: str, manifest_path: Path) -> Iterable[Path]:
    """Yield likely filesystem locations for the manifest-provided path."""

    raw = Path(path_value)
    if raw.is_absolute():
        yield raw
        return

    # Prefer interpreting the value relative to the current working directory.
    yield raw

    # Some manifests may use paths relative to the manifest's own directory.
    yield manifest_path.parent / raw


def find_latest_letter_asc(manifest_path: Path) -> Optional[Path]:
    if not manifest_path.is_file():
        return None

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    releases = payload.get("releases") or []
    if not releases:
        return None

    latest = releases[0] or {}
    asc_info = (latest.get("files") or {}).get("asc") or {}
    path_value = asc_info.get("path")
    if not path_value:
        return None

    for candidate in iter_candidates(path_value, manifest_path):
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError:
            continue
        if resolved.is_file():
            return resolved
    return None


def main() -> int:
    manifest_arg = sys.argv[1] if len(sys.argv) > 1 else "letter/RELEASES.json"
    manifest_path = Path(manifest_arg)

    result = find_latest_letter_asc(manifest_path)
    if result is None:
        return 0

    cwd = Path.cwd().resolve()
    try:
        display = result.relative_to(cwd)
    except ValueError:
        display = result

    sys.stdout.write(display.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
