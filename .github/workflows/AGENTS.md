# .github/workflows/ — Codex Guide

## Directory purpose
- GitHub Actions definitions that verify signatures, regenerate release artifacts, maintain OpenTimestamps proofs, and keep documentation in sync.

## Key workflows/commands
- Workflows are triggered by pushes to release-related paths, manual dispatch, or completion of dependent runs. Many jobs auto-commit regenerated artifacts after rebasing and waiting for GitHub Pages to be idle.

## File map
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `verify-releases.yml` | On push/PR, installs GnuPG and runs `scripts/verify-clearsign.sh` to ensure all `letter/*.asc` signatures validate. | Requires `keys/FINGERPRINT` to match bundled keys; depends on `scripts/verify-clearsign.sh`. | Safety net for signature integrity in CI. |
| `releases-manifest.yml` | On relevant pushes or after OTS stamping, regenerates docs/manifest/metadata via `python3 scripts/release.py`, rebases, waits for Pages idle, and auto-commits changes. | Concurrency group `letter-artifacts-…` prevents overlapping runs; skips auto-run when commit message contains `[manifest-auto]`. Needs GPG and Python setup. | Keeps `letter/RELEASES.json`, `docs/letter.md`, and `docs/index.html` current. |
| `ots-stamp-letter-asc.yml` | On push to `letter/*.asc`, stamps missing `.ots` proofs using OpenTimestamps client and auto-commits new proofs after rebasing and waiting for Pages. | Uses concurrency group `letter-artifacts-…`; only runs commit step when new proofs created (`touched=1`). | Ensures every new signature gains a timestamp proof. |
| `ots-verify-upgrade.yml` | Manual workflow to inspect and upgrade the newest `.ots` proof using `find_latest_ots.py`, showing info/verify before and after, then committing upgraded proof. | Requires Python/OpenTimestamps; waits for Pages idle before committing. Output format consumed by auto-commit message. | For ad-hoc proof upgrades/verification. |
| `ots-upgrade.yml` | More complex workflow triggered by upstream runs/pushes to docs/signatures; performs precheck, fetches/validates manifests and proofs, and auto-commits upgrades when appropriate. | Relies on embedded Python logic, GitHub API access, and environment vars (including `GITHUB_TOKEN`). Maintain concurrency/perms to avoid interrupting Pages deployments. | Coordinates automated OTS proof upgrades tied to site artifacts. |
| `sync-readme-fingerprint.yml` | On fingerprint changes, normalizes `keys/FINGERPRINT` formatting and patches README fingerprint line; commits/pushes if updates occur. | Requires `GITHUB_TOKEN` for push; sed commands expect fingerprint formatting. | Keeps README trust anchor aligned with canonical fingerprint. |

## Codex operating guidance
- Edit policy: When modifying workflow triggers or steps, keep concurrency groups, permissions, and gating conditions intact to avoid race conditions or unintended auto-commits.
- Validation: Dry-run with `act` if available or review workflow syntax via GitHub Actions linter; confirm referenced scripts/paths exist.
- Common failure modes: misconfigured permissions preventing auto-commit, removing waits for Pages leading to canceled deployments, breaking expected outputs consumed by subsequent steps.

