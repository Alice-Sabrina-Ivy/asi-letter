#!/usr/bin/env python3
"""Coordinate the release workflow by chaining the helper scripts."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    """Represents a release stage orchestrated by this helper."""

    key: str
    script: Path
    description: str
    supports_check: bool
    skip_attr: str

    def command(self, check_mode: bool) -> Sequence[str]:
        cmd = [sys.executable, str(self.script)]
        if check_mode and self.supports_check:
            cmd.append("--check")
        return cmd


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run each stage in validation mode without writing changes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias for --check to match common tooling expectations.",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip syncing docs/letter.md from the latest signed release.",
    )
    parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Skip regenerating letter/RELEASES.json.",
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="Skip updating docs/index.html metadata to the newest version.",
    )
    return parser.parse_args(list(argv))


def stage_definitions() -> Sequence[Stage]:
    base = Path(__file__).resolve().parent
    return (
        Stage(
            key="sync",
            script=base / "sync_docs_with_latest.py",
            description="Synchronize docs/letter.md with the latest release",
            supports_check=True,
            skip_attr="skip_sync",
        ),
        Stage(
            key="manifest",
            script=base / "gen_releases_manifest.py",
            description="Regenerate letter/RELEASES.json",
            supports_check=True,
            skip_attr="skip_manifest",
        ),
        Stage(
            key="metadata",
            script=base / "update_version_metadata.py",
            description="Update version metadata in generated assets",
            supports_check=True,
            skip_attr="skip_metadata",
        ),
    )


def run_stage(stage: Stage, check_mode: bool) -> None:
    cmd = stage.command(check_mode)
    mode_note = " (check mode)" if check_mode and stage.supports_check else ""
    print(f"\n[release] {stage.description}{mode_note}")
    print(f"[release] $ {shlex.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=REPO_ROOT)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    check_mode = args.check or args.dry_run

    for stage in stage_definitions():
        if getattr(args, stage.skip_attr):
            print(f"[release] Skipping {stage.description} (--skip-{stage.key}).")
            continue
        try:
            run_stage(stage, check_mode)
        except subprocess.CalledProcessError as exc:
            print(
                f"[release] Stage '{stage.key}' failed with exit code {exc.returncode}.",
                file=sys.stderr,
            )
            return exc.returncode or 1

    print("\n[release] All stages completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
