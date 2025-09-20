# Release helpers

The `scripts/` directory contains utilities that automate common release
maintenance tasks. The preferred entry point is `release.py`, which orchestrates
the individual helpers in a safe, repeatable order.

## `release.py`

```bash
python3 scripts/release.py
```

Running the script without arguments will:

1. Sync `docs/letter.md` with the newest signed Markdown in `letter/`.
2. Regenerate `letter/RELEASES.json`.
3. Update version metadata in generated assets such as `docs/index.html`.

Progress is printed for each stage and the helper stops immediately if a step
fails.

### Validation / dry runs

Pass `--check` (or the alias `--dry-run`) to verify whether any updates are
required without modifying files:

```bash
python3 scripts/release.py --check
```

Each underlying helper exposes a compatible `--check` mode so that running the
orchestrator leaves the working tree untouched unless a change is necessary.

### Skipping stages

Advanced workflows can re-run individual stages by skipping the others:

```bash
python3 scripts/release.py --skip-sync --skip-manifest
```

Available switches are `--skip-sync`, `--skip-manifest`, and `--skip-metadata`.

These options are helpful when iterating on a single step but the unified entry
point should remain the default interface for contributors.
