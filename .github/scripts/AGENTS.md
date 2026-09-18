# .github/scripts/ — Codex Guide

## Directory purpose
- Helper utilities invoked by GitHub Actions to coordinate Pages deployments, inspect OpenTimestamps proofs, and locate the latest release assets.

## Key workflows/commands
- `wait_for_pages_idle.sh` — called before auto-commits to avoid clashing with GitHub Pages deployments.
- `extract_block_height.py` — used in OTS workflows to report Bitcoin block height from `.ots` proofs.
- `get_latest_letter_asc.py` — resolves the latest `.asc` path from `letter/RELEASES.json` for stamping/upgrading steps.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | This guide. | Keep aligned with helper behavior. | Reference for workflow authors. |
| `generated_paths.sh` | Prints, on ONE line, every path written by `scripts/release.py`. | Single source of truth for workflow commit steps. Must stay one line: `git-auto-commit-action` parses `file_pattern` with `read -r -a` and stops at the first newline. Keep in sync with the stage list in `release.py`. | Used by `releases-manifest.yml` and `ots-upgrade.yml` to decide what to stage. |
| `assert_generated_paths.sh` | Fails CI if the pipeline wrote a path missing from `generated_paths.sh`. | Takes `--baseline <file>` (a pre-run `git status --porcelain` snapshot) so pre-existing dirt is ignored, plus extra allowed patterns. Without it, an uncovered new artifact is silently dropped at commit and `release.py --check` still passes. | Run right after `release.py` in any workflow that commits regenerated artifacts. |
| `wait_for_pages_idle.sh` | Polls GitHub Actions API until no Pages deployment runs for the branch, preventing cancellations when pushing new commits. | Requires `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, branch/ref vars; depends on `curl` + `jq`; keep executable. | Called from workflows before auto-committing regenerated assets/proofs. |
| `extract_block_height.py` | Parses an OpenTimestamps proof and prints the highest Bitcoin block height. | Exits silently if dependencies/parse fail; expects valid `.ots` input. | Used in OTS workflows to summarize proof anchoring. |
| `get_latest_letter_asc.py` | Reads `letter/RELEASES.json` to find the latest `.asc` signature path. | Assumes manifest has `releases[0].files.asc.path`; returns nothing if missing; resolves relative paths. | Helps OTS workflows select current signature for stamping/upgrade. |

## Codex operating guidance
- Edit policy: Preserve interfaces/output formats expected by workflows; keep shell script executable.
- Validation: Run with representative inputs or inspect workflow callers; ensure required env vars and dependencies remain unchanged.
- Common failure modes: missing `GITHUB_TOKEN` causing API failures, changing output formats consumed by workflows, or dropping executable permissions.
