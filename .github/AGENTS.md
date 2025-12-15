# .github/ — Codex Guide

## Directory purpose
- Continuous integration workflows and helper scripts that maintain release artifacts, verify signatures, stamp OpenTimestamps proofs, and coordinate with GitHub Pages deployments.

## Key workflows/commands
- Workflows live in `.github/workflows/`; helper scripts in `.github/scripts/` are invoked by those jobs.
- Common automation: release refresh (`releases-manifest`), OTS stamping/upgrading, signature verification, and README fingerprint sync.

## File map
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `scripts/` | Helper utilities used by workflows (see nested AGENTS). | Scripts expect GitHub Actions env vars (e.g., `GITHUB_TOKEN`) and may install deps. | Called from workflows for Pages coordination and artifact discovery. |
| `workflows/` | GitHub Actions definitions for release automation, OTS maintenance, and verification (see nested AGENTS). | Concurrency groups prevent overlapping artifact mutations; some jobs auto-commit changes. | Runs on pushes, dispatches, or dependent workflow completions. |

## Codex operating guidance
- Edit policy: Update workflows/scripts cautiously; preserve concurrency groups and permissions that gate auto-commits. Keep YAML formatting compatible with GitHub Actions.
- Validation: Use `act` locally if available or rely on GitHub Actions run results. For small edits, sanity-check referenced paths/commands exist.
- Common failure modes: breaking auto-commit permissions, removing waits for GitHub Pages (can cause canceled deployments), or misaligning workflow triggers with artifact locations.

