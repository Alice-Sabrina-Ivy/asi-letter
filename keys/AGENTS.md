# keys/ — Codex Guide

## Directory purpose
- Trusted cryptographic material for verifying ASI Letter signatures.

## Key workflows/commands
- Fingerprint normalization and README sync handled by `.github/workflows/sync-readme-fingerprint.yml`.
- Verification scripts (`scripts/verify-clearsign.sh`, `scripts/gen_releases_manifest.py`) read `keys/FINGERPRINT` and import the public key in this directory.

## File map
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `FINGERPRINT` | Canonical 40-hex-character fingerprint (uppercase) for the signing key. | Keep uppercase hex only; trailing whitespace/newlines are significant to some tooling. Used as source of truth for verification/manifest scripts and README updates. | Read by verification scripts and CI to ensure signatures match the trusted key; propagated into docs. |
| `alice-asi-publickey.asc` | Exported OpenPGP public key for verifying signatures. | Should match the fingerprint above; do not edit contents manually. | Imported by users and scripts to validate `letter/*.asc` signatures. |

## Codex operating guidance
- Edit policy: Do not modify these files except when rotating keys or updating the canonical fingerprint. Avoid reformatting `FINGERPRINT` (no spaces, uppercase hex only).
- Validation: Run `bash scripts/verify-clearsign.sh` after any key/fingerprint change; regenerate manifests with `python3 scripts/gen_releases_manifest.py --check`.
- Common failure modes: changing fingerprint formatting so automated sync fails; mismatched public key vs fingerprint; forgetting to update README via workflow after key changes.

