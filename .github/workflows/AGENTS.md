# .github/workflows/ — Codex Guide

## Directory purpose
- GitHub Actions definitions that verify signatures, timestamp and regenerate release artifacts, deploy the site, publish the GitHub Release, and archive.

## Key workflows/commands
- `release.yml` is the single pass from change to live site. It is the only workflow that commits generated artifacts. See CLAUDE.md, "Release workflow".

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | Directory guide. | Keep aligned with workflow behavior. | Reference for CI edits. |
| `release.yml` | `build`: stamp new `.asc`, upgrade the newest proof, `release.py` + `--check` + `assert_generated_paths.sh`, ONE commit `[release-auto]`, package `docs/`. `deploy`: GitHub Pages (Actions source). Then `github-release`, `announce` (IndexNow), `archive`, after the deploy. | `build` holds the job-level group `letter-artifacts-main` (shared with `sync-readme-fingerprint.yml`), with `queue: max` so pending runs are never replaced. No `schedule:` here (see `scheduled.yml`). Commit paths come from `generated_paths.sh` plus `letter/*.ots`. Bot pushes use `GITHUB_TOKEN`, so nothing is re-triggered; that's why this workflow deploys and calls the others itself. Hourly schedule exits early once the newest proof is Bitcoin-attested. | Every release, proof upgrade, script or docs change. |
| `verify-releases.yml` | On push/PR runs `bash scripts/verify-clearsign.sh`. | gnupg is preinstalled on the runner. | Safety net for signature integrity. |
| `auto-release-latest-letter.yml` | Publishes the GitHub Release marked Latest (called by `release.yml`; push to README/licenses; manual). | Publishes only when the manifest's newest entry matches the newest letter on disk and has md/asc/ots files; otherwise skips (green). Job-level group `auto-release-main`. Checks out `main`, not the event SHA. | Release snapshot with attachments. |
| `scheduled.yml` | The repo's only schedule: hourly proof check (calls `release.yml`) and weekly archive (calls `archive-release.yml`). | Kept apart from `release.yml` so a 60-day inactivity disable can never stop publishing; `release.yml` re-enables it on every push. | Proof upgrades, archive safety net. |
| `archive-release.yml` | Software Heritage + (with `IA_*` secrets) Wayback (called by `release.yml` after deploy; weekly via `scheduled.yml`; manual). | Never fails the build; failures surface as `::warning::` annotations. Job-level group `archive-release-main`. | Keeps public archives current. |
| `sync-readme-fingerprint.yml` | On `keys/FINGERPRINT` changes (or manual), patches the README fingerprint line and commits `[skip ci]`. | Shares `letter-artifacts-main`; fails if the anchor line is missing. | Keeps README trust anchor aligned. |

## Codex operating guidance
- Edit policy: keep one committing job (`release.yml` build), the generated-paths commit list and guard, the `[release-auto]` guard, and the Pages permissions (`pages: write`, `id-token: write`, environment `github-pages`).
- Validation: `actionlint` if available; confirm referenced scripts/paths exist.
- Common failure modes: splitting the commit back across workflows (multiple commits and deploys per release), hardcoding a commit path list, or expecting a bot push to trigger another workflow.
