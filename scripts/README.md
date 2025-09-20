# Scripts

## `release.py`

`release.py` orchestrates the release preparation workflow that keeps
`docs/` and `letter/` in sync with the latest signed publication. Run it
from the repository root:

```sh
python3 scripts/release.py
```

Alternatively, `make release` runs the same command for convenience.

The helper sequentially runs:

1. `scripts/sync_docs_with_latest.py`
2. `scripts/gen_releases_manifest.py`
3. `scripts/update_version_metadata.py`

If any step fails the process stops immediately.

### Check / dry-run mode

Use `--check` (or the `--dry-run` alias) to forward the corresponding flag
to the downstream scripts. This verifies whether updates are needed without
modifying files. The command exits non-zero if a regeneration is required.

```sh
python3 scripts/release.py --check
```

### Skipping individual stages

Advanced users can skip specific stages with the `--skip-sync`,
`--skip-manifest`, and `--skip-metadata` options. This is helpful when you
want to rerun a single step without leaving the unified entry point.

```sh
python3 scripts/release.py --skip-manifest
```
