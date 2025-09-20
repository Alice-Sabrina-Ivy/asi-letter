# Scripts

This directory collects automation helpers that keep the published assets in
sync with the latest signed ASI Letter and its associated proofs. The tools fall
into three groups:

* the release automation pipeline that regenerates derived artifacts,
* helpers for signing and verifying the letter, and
* GitHub Actions workflows that continuously validate public releases.

## Release automation pipeline

### `release.py`

```sh
python3 scripts/release.py [--check|--dry-run] [--skip-sync] [--skip-manifest] [--skip-metadata]
```

`release.py` is the orchestrator that executes the release pipeline end-to-end.
It calls each stage in order, aborts on the first failure, and forwards
`--check`/`--dry-run` to request read-only mode from the underlying tools. Power
users can re-run individual steps by combining the `--skip-…` switches. 【F:scripts/release.py†L1-L97】

When regenerating assets for a new release you can simply run:

```sh
python3 scripts/release.py
```

If you prefer `make`, use the `release` target, which is equivalent to invoking
`python3 scripts/release.py` directly. 【F:Makefile†L4-L7】

### `sync_docs_with_latest.py`

Discovers the newest `ASI-Letter-v*.md` file in `letter/`, verifies that its
signature (`.asc`) exists, and copies the Markdown into `docs/letter.md`. The
script exits non-zero when `--check` is supplied and the docs are out of date. 【F:scripts/sync_docs_with_latest.py†L1-L94】

### `gen_releases_manifest.py`

Rebuilds `letter/RELEASES.json` using cross-platform tooling only. It imports the
maintainer public keys, calculates SHA-256 digests for each release asset, and
records signer metadata gleaned from the detached signatures. The `--check`
mode ensures CI can detect drift without rewriting the manifest. 【F:scripts/gen_releases_manifest.py†L1-L204】

### `update_version_metadata.py`

Parses the manifest to find the latest version and rewrites known placeholders in
`docs/index.html` (and any additional targets passed on the command line) so the
site banner, data attributes, and HTML comments all reference the current
release. In check mode it reports the files that would change. 【F:scripts/update_version_metadata.py†L1-L164】

## Signing and verification helpers

### `sign-and-export.sh`

Convenience wrapper around `gpg --clearsign` that produces `letter.md.asc` files
for a given key fingerprint or ID. The script aborts when required arguments are
missing. 【F:scripts/sign-and-export.sh†L1-L11】

### `verify-clearsign.sh`

CI-friendly verification routine that imports the in-repo public key (when
available), ensures the fingerprint recorded in `keys/FINGERPRINT` exists in the
local keyring, and then verifies every `letter/*.asc` signature. 【F:scripts/verify-clearsign.sh†L1-L36】

### `find_latest_ots.py`

Utility used by the timestamping workflows to locate the most recent
OpenTimestamps proof in `letter/`. It prints reusable key/value pairs describing
that proof (path, basename, version, etc.) for subsequent workflow steps. 【F:scripts/find_latest_ots.py†L1-L90】

## Validation workflows

Automated workflows in `.github/workflows/` ensure public artifacts remain
consistent with the authoritative signed letter. Concurrency groups guard against
races between jobs that update the same files.

### `verify-releases.yml`

Runs on every push and pull request. Installs GnuPG and executes
`verify-clearsign.sh` to confirm each published letter is still properly signed. 【F:.github/workflows/verify-releases.yml†L1-L13】

### `releases-manifest.yml`

Triggers when release materials, keys, or the manifest script change. It checks
out the repository with full history, regenerates `RELEASES.json`, refreshes
`docs/index.html` via `update_version_metadata.py`, synchronizes `docs/letter.md`
with the latest letter, and auto-commits the refreshed artifacts back to the
branch. 【F:.github/workflows/releases-manifest.yml†L1-L39】

### `ots-stamp-letter-asc.yml`

Watches for new `letter/*.asc` pushes. Any signatures lacking a corresponding
`.ots` proof are stamped in-place, rebased against the tip of the branch, and
committed automatically. Waiting for GitHub Pages ensures deployments are idle
before proofs change. 【F:.github/workflows/ots-stamp-letter-asc.yml†L1-L47】

### `ots-upgrade.yml`

Runs on a 30-minute cron schedule, after successful manifest refreshes, or when
letter HTML/signature assets change. It installs both the Python and Go
OpenTimestamps clients, upgrades the freshest proof (creating one if needed),
extracts the best-known Bitcoin block height, and rewrites the timestamp status
block in `docs/index.html` before committing the result. Scheduled runs skip the
upgrade when the site already advertises a block height. 【F:.github/workflows/ots-upgrade.yml†L1-L120】

### `ots-verify-upgrade.yml`

Manual workflow that operators can trigger to inspect the latest OpenTimestamps
proof. It finds the newest `.ots`, shows pre-upgrade status, runs an upgrade, and
verifies again. If the proof changed it commits the updated file. 【F:.github/workflows/ots-verify-upgrade.yml†L1-L45】

### `sync-readme-fingerprint.yml`

Keeps the fingerprint shown in `README.md` synchronized with `keys/FINGERPRINT`.
Whenever the fingerprint changes, the workflow re-formats it for readability and
commits the updated README. 【F:.github/workflows/sync-readme-fingerprint.yml†L1-L37】
