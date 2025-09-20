#!/usr/bin/env python3
"""Run all release preparation steps in sequence.

This helper orchestrates the individual scripts used to publish a new
release, providing a single entry point with convenient ``--check`` and
``--skip`` controls.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

SCRIPT_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Stage:
    """Represents a release step executed by this orchestrator."""

    key: str
    description: str
    script: Path
    check_flag: str | None = "--check"

    def build_command(self, check_mode: bool) -> List[str]:
        cmd: List[str] = [sys.executable, str(self.script)]
        if check_mode and self.check_flag:
            cmd.append(self.check_flag)
        return cmd


STAGES: Sequence[Stage] = (
    Stage(
        key="sync",
        description="Sync docs with latest release",
        script=SCRIPT_DIR / "sync_docs_with_latest.py",
    ),
    Stage(
        key="manifest",
        description="Generate releases manifest",
        script=SCRIPT_DIR / "gen_releases_manifest.py",
    ),
    Stage(
        key="metadata",
        description="Update version metadata",
        script=SCRIPT_DIR / "update_version_metadata.py",
    ),
)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        "--dry-run",
        dest="check",
        action="store_true",
        help="Run subordinate scripts in check mode when supported.",
    )
    parser.add_argument(
        "--skip-sync",
        action="store_true",
        help="Skip syncing docs with the latest release.",
    )
    parser.add_argument(
        "--skip-manifest",
        action="store_true",
        help="Skip generating the releases manifest.",
    )
    parser.add_argument(
        "--skip-metadata",
        action="store_true",
        help="Skip updating version metadata.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def run_stage(stage: Stage, check_mode: bool) -> None:
    description = stage.description
    cmd = stage.build_command(check_mode)
    check_suffix = " (check mode)" if check_mode and stage.check_flag else ""
    print(f"==> {description}{check_suffix}")
    subprocess.run(cmd, check=True)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    check_mode = bool(args.check)

    for stage in STAGES:
        skip = getattr(args, f"skip_{stage.key}")
        if skip:
            print(f"==> Skipping {stage.description}")
            continue
        try:
            run_stage(stage, check_mode)
        except subprocess.CalledProcessError as exc:
            print(
                f"Stage '{stage.description}' failed with exit code {exc.returncode}",
                file=sys.stderr,
            )
            return exc.returncode or 1

    print("All release steps completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
