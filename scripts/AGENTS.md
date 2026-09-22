# scripts/ — Codex Guide

## Directory purpose
- Automation and utility scripts for managing ASI Letter releases, verifying signatures, syncing docs, and working with OpenTimestamps proofs.

## Key workflows/commands
- `python3 scripts/release.py [--check|--dry-run] [--skip-*]` — orchestrates sync, manifest generation, and metadata updates.
- `bash scripts/verify-clearsign.sh` — verifies all `letter/*.asc` against `keys/FINGERPRINT` (imports `asi-public.asc` if present).
- `python3 scripts/sync_docs_with_latest.py [--check]` — sync `docs/letter.md` with newest signed Markdown.
- `python3 scripts/gen_releases_manifest.py [--check]` — regenerate `letter/RELEASES.json` with hashes/metadata.
- `python3 scripts/update_version_metadata.py [--check] [targets...]` — refresh release markers in site files.
- `python3 scripts/render_index_html.py [--check]` — pre-render `docs/index.html` with the latest Markdown content.
- `python3 scripts/find_latest_ots.py <dir>` — output latest `.ots` info for workflows.
- Signing helper: `bash scripts/sign-and-export.sh <key> <file>` wraps `gpg --clearsign`.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | Directory guide. | Keep in sync with script behaviors. | Contributor reference. |
| `README.md` | Describes each script and related workflows. | Update alongside script changes for accuracy. | Human-readable script index. |
| `release.py` | Orchestrates staged release tasks (sync docs → manifest → metadata → render → publish artifacts → discovery) with skip flags and `--check/--dry-run`. | Expects stage scripts present under `scripts/`; stops on first failure. | Entry point for release automation and `make release`. |
| `sync_docs_with_latest.py` | Copies newest `letter/ASI-Letter-v*.md` into `docs/letter.md`; supports `--check`. | Requires matching `.asc` for chosen release; errors if docs dir missing. | Used in release pipeline and CI doc sync. |
| `gen_releases_manifest.py` | Builds `letter/RELEASES.json` with file metadata/hashes and signer fingerprint validation. | Requires `keys/FINGERPRINT` to be 40 uppercase hex; fails if files/signatures missing. | Run during releases/checks; consumed by metadata updater and site. |
| `update_version_metadata.py` | Rewrites release markers in target files (default `docs/index.html`) based on latest manifest entry, and regenerates the schema.org JSON-LD block between `structured-data` markers. | Fails if markers absent unless `--allow-missing-markers`; expects valid manifest schema. | Keeps site metadata aligned with latest release. |
| `render_index_html.py` | Renders `docs/letter.md` into HTML and injects it into `docs/index.html`. | Requires the Python `markdown-it-py` package (CommonMark, as GitHub renders); fails if render markers are missing. | Produces static HTML so the site renders without JavaScript. |
| `publish_latest_artifacts.py` | Copies the newest release's `.asc`/`.ots`, the public key, fingerprint and manifest into `docs/` under stable names, and refreshes `scripts/asi-public.asc`. | Copies must stay byte-identical so published `.asc` matches the `sha256` in `RELEASES.json`; relies on `*.asc`/`*.ots` being `-text` in `.gitattributes`. | Makes the site self-sufficient for verification; no version-pinned URLs. |
| `gen_discovery.py` | Generates `docs/sitemap.xml`, `docs/llms.txt` and `docs/.nojekyll` from one table of canonical URLs. | Edit the `RESOURCES` table, never the generated files; `lastmod` comes from the newest manifest entry. | Crawler and agent discovery for the published site. |
| `find_latest_ots.py` | Locates newest `.ots` file in a directory and prints path/basename/noext/version outputs. | Scans depth-1; errors if no proofs present. | Utility for OTS workflows. |
| `sign-and-export.sh` | Wrapper around `gpg --clearsign` to sign a Markdown letter with a key ID/fingerprint. | Produces `<input>.asc`; assumes GPG available/unlocked. | Manual signing helper for release managers. |
| `check_signed_payload.py` | Verifies each `letter/*.md` is the text embedded in its `.md.asc`. | Comparison MUST stay canonicalized (per-line rstrip, normalized final newline) or 7 of 14 existing releases false-positive; the `.asc` is authoritative. | Run by `verify-clearsign.sh`; closes the gap where `gpg --verify` never reads the `.md`. |
| `verify-clearsign.sh` | Verifies all `letter/*.asc` against `keys/FINGERPRINT` by parsing gpg `--status-fd` output. | Requires an explicit `VALIDSIG` naming the trusted PRIMARY key (it used to accept any key in the keyring); rejects `EXPKEYSIG`/`REVKEYSIG`/`BADSIG`; fails on zero `.asc` files rather than passing vacuously; warns near key expiry. | CI and local verification entry point. |
| `asi-public.asc` | Convenience copy of the public key for verification. | **Generated** by `publish_latest_artifacts.py` from `keys/alice-asi-publickey.asc`; never edit by hand. It had drifted to an expired export, so CI was verifying against an expired key. | Imported by `verify-clearsign.sh` if present. |
| `ASI-Letter-v2025.09.17.md` | Copy of 2025.09.17 release stored alongside scripts. | Purpose unclear (needs human note); keep consistent with signed release if retained. | Reference/backup; not part of automation stages. |
| `ASI-Letter-v2025.09.17.md.asc` | Clear-signed copy of the above Markdown. | Should validate against trusted fingerprint; purpose unclear (needs human note). | Reference signature with archival copy. |

## Codex operating guidance
- Edit policy: Update scripts/docs as needed; avoid altering archival release copies unless maintaining consistency with canonical releases. Preserve executable bits on shell scripts.
- Validation: Run `python3 scripts/release.py --check` plus targeted `--check` modes; ensure `bash scripts/verify-clearsign.sh` passes after key/signature changes.
- Common failure modes: forgetting to update README when scripts change, modifying release artifacts directly, missing executable permissions on shell helpers, or breaking manifest/schema expectations.
