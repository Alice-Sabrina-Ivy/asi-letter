# .github/ — Codex Guide

## Directory purpose
- GitHub Actions workflows and helper scripts that verify releases, regenerate artifacts, stamp/upgrade OpenTimestamps proofs, and coordinate with GitHub Pages deployments.

## Key workflows/commands
- Workflow definitions in `.github/workflows/` drive signature verification, manifest refresh, OTS stamping/upgrades, and README fingerprint sync.
- Helper scripts in `.github/scripts/` support those workflows (API polling, proof inspection, locating latest assets).

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | Directory guide (this file). | Keep aligned with workflow/script contents. | Contributor reference. |
| `scripts/` | Workflow helper utilities (see `.github/scripts/AGENTS.md`). | Scripts expect GH Actions env/permissions. | Called from workflows for Pages coordination and proof data. |
| `workflows/` | GitHub Actions workflow definitions (see `.github/workflows/AGENTS.md`). | Preserve concurrency groups and auto-commit settings. | Runs CI/release/OTS automation. |

## Codex operating guidance
- Edit policy: Modify workflows/scripts cautiously; keep concurrency groups, permissions, and Pages waiting logic intact to avoid CI races.
- Validation: Use `act` locally if available or rely on GitHub Actions results; sanity-check referenced paths and commands exist.
- Common failure modes: breaking auto-commit permissions, skipping Pages idle waits, or misaligning workflow triggers with artifact locations.
