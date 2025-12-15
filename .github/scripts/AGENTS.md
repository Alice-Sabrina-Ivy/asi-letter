# .github/scripts/ — Codex Guide

## Directory purpose
- Helper utilities invoked by GitHub Actions to coordinate Pages deployments, inspect OpenTimestamps data, and locate the latest release assets.

## Key workflows/commands
- `wait_for_pages_idle.sh` is called by workflows before auto-committing to avoid interfering with Pages deployments.
- `extract_block_height.py` and `get_latest_letter_asc.py` are used inside OTS-related workflows to enrich proofs and select current artifacts.

## File map
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `wait_for_pages_idle.sh` | Polls GitHub Actions API until no Pages deployment is running for the branch, preventing canceled deployments when pushing commits. | Requires `GITHUB_TOKEN`, `GITHUB_REPOSITORY`, and branch/ref environment variables; depends on `curl` and `jq`. | Called in auto-commit workflows before pushing regenerated artifacts or upgraded proofs. |
| `extract_block_height.py` | Parses an OpenTimestamps proof and prints the highest Bitcoin block height present. | Gracefully exits if dependencies unavailable; expects valid `.ots` file input. | Used in OTS workflows to report proof anchoring status. |
| `get_latest_letter_asc.py` | Reads `letter/RELEASES.json` to resolve the path to the latest `.asc` signature. | Assumes manifest JSON with `releases[0].files.asc.path`; returns nothing if missing. | Helps workflows locate the newest signature for stamping/upgrading. |

## Codex operating guidance
- Edit policy: Preserve script interfaces expected by workflows (stdout formats, required env vars). Keep executable bit on shell script.
- Validation: Spot-check by running scripts locally with representative inputs; ensure API calls and JSON parsing remain stable.
- Common failure modes: missing `GITHUB_TOKEN` causing API failures, changing output format consumed by workflows, or dropping executable permissions.

