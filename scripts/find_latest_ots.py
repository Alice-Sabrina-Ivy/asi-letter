#!/usr/bin/env python3
"""Utilities for locating the newest OpenTimestamps proof in a directory."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


@dataclass(frozen=True)
class LatestOts:
    """Details about the newest OpenTimestamps proof discovered."""

    path: Path
    basename: str
    noext: str
    version: str


def _candidate_files(directory: Path) -> Iterable[Path]:
    for entry in directory.iterdir():
        if entry.is_file() and entry.suffix == ".ots":
            yield entry


def _sort_key(path: Path) -> tuple[float, str]:
    stat = path.stat()
    return stat.st_mtime, path.name


def _derive_version_components(path: Path) -> tuple[str, str, str]:
    basename = path.name
    noext = basename[: -len(path.suffix)] if path.suffix else basename
    version = noext
    if noext.endswith(".md.asc"):
        version = noext[: -len(".md.asc")]
    return basename, noext, version


def find_latest_ots(directory: Path) -> LatestOts:
    """Return information about the newest ``.ots`` file in *directory*.

    Parameters
    ----------
    directory:
        Directory that will be searched. Only files directly inside this
        directory (i.e. depth 1) are considered.
    """

    if not directory.is_dir():
        raise FileNotFoundError(f"{directory} is not a directory")

    candidates: List[Path] = list(_candidate_files(directory))
    if not candidates:
        raise FileNotFoundError("No .ots files found in directory")

    latest = max(candidates, key=_sort_key)
    basename, noext, version = _derive_version_components(latest)
    return LatestOts(path=latest.resolve(), basename=basename, noext=noext, version=version)


def _format_outputs(latest: LatestOts, *, base_dir: Path | None = None) -> List[str]:
    cwd = base_dir or Path.cwd()
    try:
        rel_path = latest.path.relative_to(cwd)
    except ValueError:
        rel_path = Path(os.path.relpath(latest.path, cwd))

    return [
        f"latest={rel_path.as_posix()}",
        f"basename={latest.basename}",
        f"noext={latest.noext}",
        f"version={latest.version}",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory",
        type=Path,
        nargs="?",
        default=Path("letter"),
        help="Directory containing .ots files (default: letter)",
    )
    args = parser.parse_args(argv)

    try:
        latest = find_latest_ots(args.directory)
    except FileNotFoundError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1

    for line in _format_outputs(latest):
        print(line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
