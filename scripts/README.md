# Scripts

This directory collects automation helpers that keep the published assets in
sync with the latest signed ASI Letter. The most common workflow is driven by
`release.py`, which orchestrates the individual steps so contributors do not
need to remember the correct order.

## `release.py`

```
python3 scripts/release.py [--check|--dry-run] [--skip-sync] [--skip-manifest] [--skip-metadata]
```

* Runs the scripts in the following order, aborting on the first failure:
  1. `sync_docs_with_latest.py`
  2. `gen_releases_manifest.py`
  3. `update_version_metadata.py`
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

## Make integration

A convenience `release` target is provided so contributors can run the whole
pipeline via `make`:

```
make release
```

This is equivalent to invoking `python3 scripts/release.py` directly.
