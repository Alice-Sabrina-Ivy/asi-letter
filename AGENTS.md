# ASI Letter — Codex Guide

## Repository purpose
- Canonical source for Alice Sabrina Ivy's signed "Letter to ASI" releases, accompanying OpenPGP signatures, OpenTimestamps proofs, and the static site that publishes them.
- Primary goals: publish and verify signed releases, keep docs synchronized with the latest letter, and automate integrity checks.
- Where to start: read `README.md` for verification steps; inspect `letter/RELEASES.json` for release metadata; use `scripts/release.py --check` to confirm artifacts are current.

## Run/test/build entrypoints
- Release/consistency check: `python3 scripts/release.py --check` (runs docs sync, manifest generation, metadata update in dry-run mode).
- Signature verification: `bash scripts/verify-clearsign.sh` (ensures `letter/*.asc` files validate against `keys/FINGERPRINT`).
- Other automated checks are driven by GitHub Actions workflows in `.github/workflows/`.

## Top-level directory map
- `docs/` — Static site assets (HTML + Markdown) updated to the latest signed letter.
- `keys/` — Public key material and canonical fingerprint for signature verification.
- `letter/` — Versioned letter releases with signatures, proofs, and manifest.
- `scripts/` — Automation helpers for syncing docs, generating manifests, stamping signatures, and signing/verification utilities.
- `.github/` — CI workflows and helper scripts for stamping, verification, and site coordination.
- `Makefile` — Convenience `release` target to run `scripts/release.py`.
- `README.md` — User-facing verification and timestamping instructions.

## Project conventions
- Release filenames follow `ASI-Letter-vYYYY.MM.DD.md` with matching `.asc` and `.asc.ots` proofs.
- The trusted fingerprint is stored in `keys/FINGERPRINT` and must match signatures in `letter/` artifacts.
- Regenerate derived artifacts (docs, manifest, metadata) via `scripts/release.py` rather than manual edits.

## Codex operating guidance
- Edit policy: AGENTS files and documentation may be updated; avoid modifying signed letter artifacts, manifest outputs, or keys unless performing an intentional release/update.
- Validation: prefer `python3 scripts/release.py --check` and `bash scripts/verify-clearsign.sh` before committing doc changes.
- Common pitfalls: manual edits to generated assets (`docs/letter.md`, `letter/RELEASES.json`, `.asc/.ots` files) will be overwritten or break signature checks; keep fingerprint formatting intact (uppercase hex, no spaces in raw file).

