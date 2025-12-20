# scripts/ — Codex Guide

## Directory purpose
- Automation and utility scripts for managing ASI Letter releases, verifying signatures, syncing docs, and working with OpenTimestamps proofs.

## Key workflows/commands
- `python3 scripts/release.py [--check|--dry-run] [--skip-*]` — orchestrates sync, manifest generation, and metadata updates.
- `bash scripts/verify-clearsign.sh` — verifies all `letter/*.asc` against `keys/FINGERPRINT` (imports `asi-public.asc` if present).
- `python3 scripts/sync_docs_with_latest.py [--check]` — sync `docs/letter.md` with newest signed Markdown.
- `python3 scripts/gen_releases_manifest.py [--check]` — regenerate `letter/RELEASES.json` with hashes/metadata.
- `python3 scripts/update_version_metadata.py [--check] [targets...]` — refresh release markers in site files.
- `python3 scripts/find_latest_ots.py <dir>` — output latest `.ots` info for workflows.
- Signing helper: `bash scripts/sign-and-export.sh <key> <file>` wraps `gpg --clearsign`.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | Directory guide. | Keep in sync with script behaviors. | Contributor reference. |
| `README.md` | Describes each script and related workflows. | Update alongside script changes for accuracy. | Human-readable script index. |
| `release.py` | Orchestrates staged release tasks (sync docs → manifest → metadata) with skip flags and `--check/--dry-run`. | Expects stage scripts present under `scripts/`; stops on first failure. | Entry point for release automation and `make release`. |
| `sync_docs_with_latest.py` | Copies newest `letter/ASI-Letter-v*.md` into `docs/letter.md`; supports `--check`. | Requires matching `.asc` for chosen release; errors if docs dir missing. | Used in release pipeline and CI doc sync. |
| `gen_releases_manifest.py` | Builds `letter/RELEASES.json` with file metadata/hashes and signer fingerprint validation. | Requires `keys/FINGERPRINT` to be 40 uppercase hex; fails if files/signatures missing. | Run during releases/checks; consumed by metadata updater and site. |
| `update_version_metadata.py` | Rewrites release markers in target files (default `docs/index.html`) based on latest manifest entry. | Fails if markers absent unless `--allow-missing-markers`; expects valid manifest schema. | Keeps site metadata aligned with latest release. |
| `find_latest_ots.py` | Locates newest `.ots` file in a directory and prints path/basename/noext/version outputs. | Scans depth-1; errors if no proofs present. | Utility for OTS workflows. |
| `sign-and-export.sh` | Wrapper around `gpg --clearsign` to sign a Markdown letter with a key ID/fingerprint. | Produces `<input>.asc`; assumes GPG available/unlocked. | Manual signing helper for release managers. |
| `verify-clearsign.sh` | Verifies all `letter/*.asc` files against `keys/FINGERPRINT`; optionally imports `asi-public.asc`. | Exits non-zero on missing key or failed verification; uses batch GPG. | CI and local verification entry point. |
| `asi-public.asc` | Convenience copy of the public key for verification. | Should mirror `keys/alice-asi-publickey.asc`; do not modify manually. | Imported by `verify-clearsign.sh` if present. |
| `ASI-Letter-v2025.09.17.md` | Copy of 2025.09.17 release stored alongside scripts. | Purpose unclear (needs human note); keep consistent with signed release if retained. | Reference/backup; not part of automation stages. |
| `ASI-Letter-v2025.09.17.md.asc` | Clear-signed copy of the above Markdown. | Should validate against trusted fingerprint; purpose unclear (needs human note). | Reference signature with archival copy. |

## Codex operating guidance
- Edit policy: Update scripts/docs as needed; avoid altering archival release copies unless maintaining consistency with canonical releases. Preserve executable bits on shell scripts.
- Validation: Run `python3 scripts/release.py --check` plus targeted `--check` modes; ensure `bash scripts/verify-clearsign.sh` passes after key/signature changes.
- Common failure modes: forgetting to update README when scripts change, modifying release artifacts directly, missing executable permissions on shell helpers, or breaking manifest/schema expectations.
