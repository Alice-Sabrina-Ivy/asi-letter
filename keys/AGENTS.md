# keys/ — Codex Guide

## Directory purpose
- Trusted cryptographic material (fingerprint + public key) used to verify ASI Letter signatures.

## Key workflows/commands
- Fingerprint normalization + README sync: `.github/workflows/sync-readme-fingerprint.yml` updates `README.md` from `FINGERPRINT`.
- Verification scripts read these files: `bash scripts/verify-clearsign.sh`, `python3 scripts/gen_releases_manifest.py`.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | Directory guide. | Keep aligned with actual key material. | Contributor reference. |
| `FINGERPRINT` | Canonical 40-hex fingerprint (uppercase) for the signing key. | Preserve uppercase hex with no spaces; workflow updates README based on this value. | Read by verification scripts/CI and manifest generator. |
| `alice-asi-publickey.asc` | Exported OpenPGP public key. | Must match `FINGERPRINT`; do not hand-edit contents. | Imported by users/scripts to validate `letter/*.asc`. |

## Codex operating guidance
- Edit policy: Only change when rotating keys; avoid altering formatting of `FINGERPRINT` or contents of the public key.
- Validation: After key updates, run `bash scripts/verify-clearsign.sh` and `python3 scripts/gen_releases_manifest.py --check`; ensure README sync workflow reflects new fingerprint.
- Common failure modes: fingerprint formatting drift, mismatched key vs fingerprint, or skipping manifest/regeneration after key changes.
