# scripts/ — Codex Guide

## Directory purpose
- Automation and utility scripts for managing ASI Letter releases, verifying signatures, syncing docs, and working with OpenTimestamps proofs.

## Key workflows/commands
- Run full release refresh (sync docs, manifest, metadata): `python3 scripts/release.py` (use `--check`/`--dry-run` to ensure cleanliness).
- Verify signatures: `bash scripts/verify-clearsign.sh` (imports key if available and checks all `letter/*.asc`).
- Sync docs with latest signed letter: `python3 scripts/sync_docs_with_latest.py [--check]`.
- Regenerate manifest: `python3 scripts/gen_releases_manifest.py [--check]`.
- Update site version markers: `python3 scripts/update_version_metadata.py [--check] [targets...]`.
- Stamp/upgrade proofs: GitHub workflows call `scripts/find_latest_ots.py` and external OTS client.

## File map
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `README.md` | Documents available scripts and related CI workflows. | Keep descriptions aligned with actual behavior when scripts change. | Contributor reference. |
| `release.py` | Orchestrates sync, manifest generation, and metadata updates as stages. Supports `--check/--dry-run` and skip flags. | Expects stage scripts to exist under `scripts/`; stops on first failure. | Entry point for release automation and `make release`. |
| `sync_docs_with_latest.py` | Copies newest `letter/ASI-Letter-v*.md` into `docs/letter.md`; supports `--check`. | Requires matching `.asc` for chosen release; treats missing docs dir as error. | Used in release pipeline and CI doc sync. |
| `gen_releases_manifest.py` | Builds `letter/RELEASES.json` with file metadata, signer details, and hashes; imports public keys. | Requires `keys/FINGERPRINT` formatted as 40 uppercase hex; errors if signatures mismatch fingerprint or files missing. | Run during releases and checks; consumed by metadata updater/site. |
| `update_version_metadata.py` | Rewrites version markers in target files (default `docs/index.html`) based on latest entry in `RELEASES.json`. | Fails if targets lack markers unless `--allow-missing-markers`; expects manifest schema to include `releases` array. | Keeps site metadata aligned with latest release; used in release pipeline. |
| `find_latest_ots.py` | Finds newest `.ots` file in a directory and prints path/basename/noext/version key-value pairs. | Only scans depth-1 files; raises if directory missing or no `.ots` present. | Utility for workflows upgrading proofs. |
| `sign-and-export.sh` | Wrapper around `gpg --clearsign` to sign a Markdown letter with provided key ID/fingerprint. | Produces `<input>.asc` beside source; assumes GPG available and key unlocked. | Manual signing helper for release managers. |
| `verify-clearsign.sh` | Verifies all `letter/*.asc` files against fingerprint in `keys/FINGERPRINT`, optionally importing `scripts/asi-public.asc`. | Exits non-zero on missing key or failed verification; uses `gpg --batch`. | CI and local verification entry point. |
| `asi-public.asc` | Convenience copy of the public key for local verification. | Should mirror `keys/alice-asi-publickey.asc`; do not edit manually. | Imported by `verify-clearsign.sh` if present. |
| `ASI-Letter-v2025.09.17.md` | Copy of a historical letter release stored alongside scripts. | Content mirrors dated release; purpose unclear (needs human note) — keep in sync with signed artifacts if used. | Reference/backup; not part of automated pipeline. |
| `ASI-Letter-v2025.09.17.md.asc` | Clear-signed version of the above dated letter. | Should verify against trusted fingerprint; purpose unclear (needs human note). | Reference signature alongside archival copy. |

## Codex operating guidance
- Edit policy: Update scripts and documentation as needed; avoid altering archival release copies unless maintaining consistency with canonical releases. Keep executable bits on shell scripts when editing.
- Validation: Prefer running `python3 scripts/release.py --check` plus targeted script `--check` modes; for shell scripts, lint manually or run in a safe environment. Ensure `verify-clearsign.sh` passes after key/signature-related changes.
- Common failure modes: forgetting to update README when scripts change; modifying release artifacts directly instead of using signing tools; missing executable permissions on shell helpers; breaking manifest schema expectations.

