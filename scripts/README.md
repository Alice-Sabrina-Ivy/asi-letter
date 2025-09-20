# Scripts

This directory collects automation helpers that keep the published assets in
sync with the latest signed ASI Letter. The tools fall into two broad
categories:

* the **release pipeline**, which regenerates derived artifacts when a new
  letter is published; and
* **signing/timestamp utilities**, which assist with PGP clearsigning and
  OpenTimestamps management.

GitHub Actions workflows wire these scripts together so routine checks and
updates happen automatically—those automations are documented at the end of
this guide.

## Orchestrated release workflow

### `release.py`

```
python3 scripts/release.py [--check|--dry-run] [--skip-sync] [--skip-manifest] [--skip-metadata]
```

The orchestrator runs the individual Python helpers in sequence, stopping on
first failure so contributors do not need to remember the correct order. Use the
`--check` (or `--dry-run`) switch to verify that all generated files are already
up to date without applying changes. The optional `--skip-…` flags allow you to
rerun a single stage after making manual adjustments.

When regenerating assets for a new release you can simply run:

```
python3 scripts/release.py
```

If you prefer `make`, use the `release` target described below—`make release`
invokes the orchestrator with the default settings.

The pipeline executes the following stages:

#### `sync_docs_with_latest.py`

Discovers the newest `ASI-Letter-vYYYY.MM.DD.md` file under `letter/` (requiring
a matching `.asc` signature) and copies it to `docs/letter.md`. Passing
`--check` exits with status 1 instead of writing when the destination is stale.

#### `gen_releases_manifest.py`

Creates or refreshes `letter/RELEASES.json`. The script imports the trusted
public keys from `keys/`, hashes each published artifact (`.md`, `.asc`, and
`.ots`), records signer metadata reported by GnuPG, and timestamps the manifest.
With `--check` it only reports whether regeneration is required.

#### `update_version_metadata.py`

Reads the manifest to determine the most recent version and rewrites known
placeholders in `docs/index.html` (or any paths passed as positional arguments)
so titles, attributes, and comments always reference the latest release. When
run in `--check` mode the command merely reports files that would change.

## Signing and timestamp utilities

### `sign-and-export.sh`

Convenience wrapper around `gpg --clearsign`. Invoke it with a key ID or
fingerprint plus the path to a markdown file and it emits the corresponding
`*.asc` clearsigned file alongside the original content.

### `verify-clearsign.sh`

Continuous verification helper used in CI. It optionally imports a repository
copy of the public key, validates that the fingerprint declared in
`keys/FINGERPRINT` is present in the local keyring, and then runs
`gpg --verify` against every `letter/*.asc`. The script exits non-zero if any
verification fails.

### `find_latest_ots.py`

Utility for automation workflows that need to reference the newest
OpenTimestamps proof. It scans a directory (default: `letter/`) for `.ots`
files, selects the most recently modified proof, and prints useful key/value
pairs (`latest`, `basename`, `noext`, `version`) to standard output.

## Make integration

A convenience `release` target is provided so contributors can run the whole
pipeline via `make`:

```
make release
```

This is equivalent to invoking `python3 scripts/release.py` directly.

## Validation and automation workflows

Several GitHub Actions workflows exercise these scripts to keep the repository
healthy:

* **`verify-releases.yml`** — Runs on every push and pull request. Installs
  GnuPG and executes `scripts/verify-clearsign.sh` to ensure the committed
  signatures match the trusted fingerprint and validate successfully.
* **`releases-manifest.yml`** — Regenerates derived artifacts whenever the
  signed letters, keys, or manifest script change. The job runs
  `gen_releases_manifest.py`, `update_version_metadata.py`, and
  `sync_docs_with_latest.py` (including a `--check` verification pass) before
  committing updated `letter/RELEASES.json`, `docs/letter.md`, and
  `docs/index.html` back to the branch.
* **`ots-stamp-letter-asc.yml`** — Watches for new `letter/*.asc` files. When a
  clearsigned letter lacks a matching `.ots` proof, the workflow stamps it using
  the OpenTimestamps client and commits the generated proof.
* **`ots-upgrade.yml`** — Runs on a schedule, after successful manifest refresh
  jobs, and when key assets are updated. It stamps or upgrades the latest proof,
  attempts to extract the Bitcoin block height anchoring the proof, and rewrites
  the status footer in `docs/index.html` to reflect the attestation before
  committing any changes.
* **`ots-verify-upgrade.yml`** — Manually triggered utility for maintainers.
  Uses `find_latest_ots.py` to locate the newest proof, displays verification
  information, attempts an upgrade, and commits the improved proof if anything
  changes.
* **`sync-readme-fingerprint.yml`** — Keeps the fingerprint shown in the
  top-level `README.md` synchronized with `keys/FINGERPRINT`. When the latter
  changes, the workflow rewrites the README line and pushes a dedicated
  documentation commit.

Each workflow shares a `letter-artifacts-${{ github.ref }}` concurrency group so
only one automation mutates release assets per branch at a time, preventing
conflicting commits.
