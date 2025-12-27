# .github/workflows/ — Codex Guide

## Directory purpose
- GitHub Actions definitions that verify signatures, regenerate release artifacts, maintain OpenTimestamps proofs, and keep documentation in sync.

## Key workflows/commands
- Workflows trigger on pushes, manual dispatch, schedules, or dependent workflow completions. Several jobs auto-commit regenerated artifacts after rebasing and waiting for GitHub Pages to be idle.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | Directory guide. | Keep aligned with workflow behavior. | Reference for CI edits. |
| `verify-releases.yml` | On push/PR installs GnuPG and runs `bash scripts/verify-clearsign.sh` to validate all `letter/*.asc`. | Requires `keys/FINGERPRINT` and scripts path; uses ubuntu runner. | Safety net for signature integrity. |
| `releases-manifest.yml` | On pushes to release paths or after OTS stamping, runs `python3 scripts/release.py`, rebases, waits for Pages idle, and auto-commits updates to manifest/docs. | Concurrency group `letter-artifacts-...`; skip auto-run when commit contains `[manifest-auto]`; needs GPG + Python. | Keeps `letter/RELEASES.json`, `docs/letter.md`, `docs/index.html` current. |
| `auto-release-latest-letter.yml` | On pushes to release metadata/assets, reads latest entry in `letter/RELEASES.json`, ensures `.ots` proof exists, and publishes a GitHub Release marked as latest if missing. | Requires `jq` and GitHub CLI; only runs when all paths exist; avoids duplicate releases by checking tag. | Publishes the “latest recommended” release snapshot with attachments and verification notes. |
| `ots-stamp-letter-asc.yml` | On push to `letter/*.asc`, stamps missing `.ots` proofs with OpenTimestamps and commits new proofs after rebasing/Pages wait. | Uses concurrency group; commit only when new proofs (`touched=1`). | Ensures each signature gains timestamp proof. |
| `ots-verify-upgrade.yml` | Manual workflow to find latest proof via `scripts/find_latest_ots.py`, show `ots info/verify`, attempt upgrade, then commit changed proof. | Requires Python + OTS client; waits for Pages idle before commit. | Ad-hoc proof upgrade/inspection. |
| `ots-upgrade.yml` | Scheduled/push/workflow_run workflow that prechecks whether upgrade is needed, stamps/upgrades proofs, updates footer status, regenerates artifacts, and auto-commits. | Relies on embedded Python logic, GH API access, env vars (`GITHUB_TOKEN`, optional `OTS_UPGRADE_FINALIZED_VERSION`), and concurrency guard. Keep Pages wait and commit patterns intact. | Automated OTS upgrade/metadata refresh pipeline. |
| `sync-readme-fingerprint.yml` | On `keys/FINGERPRINT` changes (or manual), normalizes fingerprint formatting and patches README line, committing if updates occur. | Needs `GITHUB_TOKEN`; sed commands expect uppercase fingerprint. | Keeps README trust anchor aligned with canonical fingerprint. |

## Codex operating guidance
- Edit policy: Preserve concurrency groups, permissions, Pages waits, and commit gating to avoid race conditions or canceled deployments.
- Validation: Dry-run with `act` if available or review syntax; confirm referenced scripts/paths exist.
- Common failure modes: misconfigured permissions blocking auto-commits, removing waits that cause Pages cancellations, or altering expected outputs consumed by later steps.
