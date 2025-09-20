# Scripts

This directory collects automation helpers that keep the published assets in
sync with the latest signed ASI Letter. You can run them manually while
preparing a release, and most of them are also wired into the repository's
validation workflows so contributors do not have to remember the correct
sequence.

## Release orchestration

### `release.py`

```
python3 scripts/release.py [--check|--dry-run] [--skip-sync] [--skip-manifest] [--skip-metadata]
```

* Coordinates the standard publishing pipeline by running the three release
  stages below in order, aborting on the first failure.
* Accepts `--check`/`--dry-run` to forward the read-only mode supported by the
  underlying scripts so you can verify cleanliness without touching the working
  tree.
* Advanced users can re-run a specific stage by combining the `--skip-…`
  switches for the steps they want to bypass.

When regenerating assets for a new release you can simply run:

```
python3 scripts/release.py
```

If you prefer `make`, use the `release` target described below.

### `sync_docs_with_latest.py`

* Finds the highest-version `ASI-Letter-v*.md` file in the `letter/`
  directory, ensures the matching `.asc` signature exists, and copies the
  Markdown into `docs/letter.md`.
* In `--check` mode it exits with status 1 if the docs are out of date, letting
  automation guard against drift.

### `gen_releases_manifest.py`

* Rebuilds `letter/RELEASES.json` using only cross-platform tooling so the
  manifest can be generated on any runner.
* Imports the trusted signing keys, gathers metadata for every release
  artifact (Markdown, detached signature, optional OpenTimestamps proof), and
  records the signer fingerprint from `keys/FINGERPRINT`.
* Supports `--check` to report whether regeneration is required without
  writing the file.

### `update_version_metadata.py`

* Parses `letter/RELEASES.json`, selects the newest version, and rewrites known
  placeholders in generated assets (currently `docs/index.html`) so the site
  always advertises the latest signed release.
* Provides a `--check` mode that only reports pending changes, which is useful
  in CI to ensure the metadata was refreshed.

### Make integration

A convenience `release` target is provided so contributors can run the whole
pipeline via `make`:

```
make release
```

This is equivalent to invoking `python3 scripts/release.py` directly.

## Signing and timestamping helpers

### `sign-and-export.sh`

Minimal wrapper that clearsigns a Markdown letter with the specified key and
writes the detached `.asc` file next to the input document.

### `find_latest_ots.py`

Discovers the newest OpenTimestamps proof within a directory and prints useful
metadata (path, basename, inferred version). The output is designed to feed
GitHub Actions steps or shell scripts that need to operate on the latest
proof.

### `verify-clearsign.sh`

Imports the trusted public key (if provided), confirms that the expected
fingerprint from `keys/FINGERPRINT` is present in the local keyring, and then
verifies every `letter/*.asc` file. The script exits non-zero on any
verification failure so CI can block unsigned or tampered releases.

## GitHub Actions workflows

Several workflows exercise the scripts above to keep the repository healthy and
published artifacts trustworthy:

* **`releases-manifest`** &mdash; Regenerates `letter/RELEASES.json`, updates
  `docs/index.html` metadata, re-syncs `docs/letter.md`, and commits the results
  whenever release assets or signing keys change.
* **`Verify OpenPGP clear-signed releases`** &mdash; Runs on every push and pull
  request to install GnuPG and execute `scripts/verify-clearsign.sh`, ensuring
  all signed letters verify cleanly before changes land.
* **`ots-stamp-letter-asc`** &mdash; Automatically stamps new `letter/*.asc`
  files with OpenTimestamps proofs, rebases to avoid conflicts, waits for Pages
  deployments to finish, and commits any newly-created `.ots` files.
* **`ots-upgrade`** &mdash; Runs on a schedule, when release assets change, or
  after the manifest workflow finishes. It upgrades the most recent `.ots`
  proof, extracts the latest Bitcoin attestation, refreshes the footer in
  `docs/index.html`, and commits the updates.
* **`ots-verify-upgrade`** &mdash; Manual workflow that installs the
  OpenTimestamps client, reports verification status before and after an
  upgrade, and commits the improved proof if anything changed.
* **`sync-readme-fingerprint`** &mdash; Ensures the fingerprint displayed in the
  top-level README always matches `keys/FINGERPRINT` by rewriting the relevant
  line and pushing the update when necessary.

Together these workflows keep the documentation, manifests, signatures, and
timestamp proofs synchronized without manual intervention.
