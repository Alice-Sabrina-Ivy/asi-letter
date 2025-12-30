#!/usr/bin/env python3
"""Run release automation helpers in sequence.

This orchestrator coordinates the existing scripts that keep the project
artifacts in sync with the most recent signed letter. It runs each stage in
order, stopping on the first failure and providing a convenient ``--check`` mode
that ensures no files would be modified.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class Stage:
    """Definition of a single release stage."""

    name: str
    script: str
    skip_flag: str
    help_text: str

    @property
    def cli_option(self) -> str:
        return f"--{self.skip_flag.replace('_', '-')}"


STAGES: List[Stage] = [
    Stage(
        name="Sync docs with latest release",
        script="sync_docs_with_latest.py",
        skip_flag="skip_sync",
        help_text="the documentation sync step",
    ),
    Stage(
        name="Generate releases manifest",
        script="gen_releases_manifest.py",
        skip_flag="skip_manifest",
        help_text="manifest generation",
    ),
    Stage(
        name="Update version metadata",
        script="update_version_metadata.py",
        skip_flag="skip_metadata",
        help_text="metadata updates",
    ),
    Stage(
        name="Render index HTML",
        script="render_index_html.py",
        skip_flag="skip_render",
        help_text="index rendering",
    ),
]


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify whether all stages are clean without applying changes.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias for --check for contributors that prefer the term.",
    )
    for stage in STAGES:
        parser.add_argument(
            stage.cli_option,
            action="store_true",
            dest=stage.skip_flag,
            help=f"Skip {stage.help_text}.",
        )
    return parser.parse_args(list(argv))


def run_stage(stage: Stage, base_dir: Path, check_mode: bool) -> None:
    script_path = base_dir / "scripts" / stage.script
    if not script_path.exists():
        raise SystemExit(f"Script not found: {script_path}")

    cmd = [sys.executable, str(script_path)]
    if check_mode:
        cmd.append("--check")

    mode_label = " (check mode)" if check_mode else ""
    print(f"  → Running {stage.name}{mode_label}...")
    subprocess.run(cmd, check=True, cwd=base_dir)


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)
    check_mode = bool(args.check or args.dry_run)

    repo_root = Path(__file__).resolve().parents[1]

    selected: List[Stage] = []
    for stage in STAGES:
        if getattr(args, stage.skip_flag):
            print(f"Skipping {stage.name} ({stage.cli_option})")
        else:
            selected.append(stage)

    if not selected:
        print("All stages skipped; nothing to do.")
        return 0

    total = len(selected)
    for index, stage in enumerate(selected, start=1):
        print(f"[{index}/{total}] {stage.name}")
        run_stage(stage, repo_root, check_mode)

    print("All release stages completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
