# Scripts

This directory collects automation helpers that keep the published assets in
sync with the latest signed ASI Letter and provide tooling for
cryptographic/OTS maintenance. The most common workflow is driven by
`release.py`, which orchestrates the individual steps so contributors do not
need to remember the correct order. The sections below describe each script and
the related continuous validation jobs in more detail.

## Release orchestration

### `release.py`

```
python3 scripts/release.py [--check|--dry-run] [--skip-sync] [--skip-manifest] [--skip-metadata] [--skip-render]
```

* Runs the scripts in the following order, aborting on the first failure:
  1. `sync_docs_with_latest.py`
  2. `gen_releases_manifest.py`
  3. `update_version_metadata.py`
  4. `render_index_html.py`
* Pass `--check` or `--dry-run` to forward the read-only mode supported by the
  underlying tools. This is useful in CI or when verifying that the working tree
  is already up to date.
* Advanced users can re-run a specific stage by combining the `--skip-…`
  switches shown above.

When regenerating assets for a new release you can simply run:

```
python3 scripts/release.py
```

If you prefer `make`, use the `release` target described below.

### `sync_docs_with_latest.py`

Copies the newest signed Markdown file in `letter/` to `docs/letter.md`. The
script discovers the most recent `ASI-Letter-vYYYY.MM.DD.md`, ensures the
matching `.asc` signature exists, and writes the Markdown into the docs tree.

```
python3 scripts/sync_docs_with_latest.py [--letter-dir PATH] [--docs-dir PATH] [--check]
```

`--check` exits with status 1 when the docs need to be refreshed, which is how
CI detects out-of-sync content.

### `gen_releases_manifest.py`

Builds `letter/RELEASES.json` using standard Python tooling so the manifest can
be regenerated anywhere. It imports trusted keys from `keys/`, validates the
`keys/FINGERPRINT` file, collects metadata for every markdown/signature/proof
triple, and serializes the result in a stable order. The script keeps the
existing `updated` timestamp when only that field would change.

```
python3 scripts/gen_releases_manifest.py [--output PATH] [--check]
```

### `update_version_metadata.py`

Reads `letter/RELEASES.json`, selects the newest release, and rewrites known
version placeholders (page title, data attributes, and HTML comments) in site
artifacts such as `docs/index.html`.

```
python3 scripts/update_version_metadata.py [--manifest PATH] [--check] [targets...]
```

`targets` defaults to `docs/index.html`. Passing `--check` reports files that
require updates without modifying them.

### `render_index_html.py`

Pre-renders `docs/letter.md` into HTML and replaces the content between the
render markers in `docs/index.html`. This keeps the site layout identical while
removing the need for client-side JavaScript rendering. Requires the Python
`markdown` package.

```
python3 scripts/render_index_html.py [--index PATH] [--markdown PATH] [--check]
```

## Signing and verification helpers

### `sign-and-export.sh`

Minimal wrapper around `gpg --clearsign` that accepts a key ID/fingerprint and a
Markdown letter, producing `<letter>.asc` beside the input. Intended for release
managers who prefer not to remember the exact GnuPG flags.

### `verify-clearsign.sh`

Verifies every `letter/*.asc` file against the fingerprint stored in
`keys/FINGERPRINT`. The script optionally imports `scripts/asi-public.asc`,
checks that the key is present locally, and fails the build if any signature
verification fails. This is the same entrypoint the CI job uses.

## OpenTimestamps utilities

### `find_latest_ots.py`

Locates the newest `.ots` proof in a directory and prints several helpful
outputs (`latest`, `basename`, `noext`, and `version`). The automation workflows
use these values to verify and upgrade proofs idempotently.

## Make integration

A convenience `release` target is provided so contributors can run the whole
pipeline via `make`:

```
make release
```

This is equivalent to invoking `python3 scripts/release.py` directly.

## Validation and automation workflows

Multiple GitHub Actions workflows keep the repository healthy and the published
assets reproducible:

* **`verify-releases.yml`** (push/PR): installs GnuPG and runs
  `scripts/verify-clearsign.sh` to ensure every committed clear-signed letter
  validates against the trusted fingerprint.
* **`releases-manifest.yml`** (push to `letter/**`, `keys/**`, or manual):
  executes the full release pipeline (manifest generation, metadata refresh, and
  docs sync) and auto-commits the results. It rebases onto the tip of the target
  branch and waits for GitHub Pages deployments to finish before pushing.
* **`ots-stamp-letter-asc.yml`** (push to `letter/*.asc`): installs the
  OpenTimestamps client, stamps any new signatures to produce matching `.ots`
  proofs, waits for GitHub Pages to be idle, and commits the generated proofs.
* **`ots-verify-upgrade.yml`** (manual): finds the freshest proof via
  `find_latest_ots.py`, shows `ots info/verify` output, attempts an upgrade, and
  commits the updated proof when changes are detected.
* **`sync-readme-fingerprint.yml`** (push to `keys/FINGERPRINT` or manual):
  normalizes the fingerprint string and patches `README.md` so the published
  trust anchor always mirrors the canonical value.

These workflows share a concurrency group (`letter-artifacts-${{ github.ref }}`)
so that only one automation run mutates release artifacts for a given branch at
a time. Several jobs call `.github/scripts/wait_for_pages_idle.sh` to avoid
interrupting GitHub Pages deployments when they push their commits.
