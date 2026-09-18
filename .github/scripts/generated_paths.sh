#!/usr/bin/env bash
# Canonical list of every path written by scripts/release.py.
#
# Workflows that regenerate artifacts and commit them MUST use this list rather
# than hardcoding their own. Two workflows previously hardcoded a short list and
# silently dropped everything else the pipeline produced: the files were
# regenerated in CI and then discarded at the commit step, so the published
# signature, manifest, sitemap and llms.txt stayed frozen at an old release
# while docs/letter.md moved forward.
#
# Prints the paths space-separated on ONE line. That matters for
# git-auto-commit-action, whose file_pattern parser reads with
# `read -r -a ... <<< "$INPUT_FILE_PATTERN"` and stops at the first newline.
#
# Keep in sync with the stage list in scripts/release.py. The
# assert_generated_paths.sh guard fails CI if a stage starts writing a path that
# is missing here, so this cannot drift unnoticed.
set -euo pipefail

GENERATED_PATHS=(
  # stage 1 — sync_docs_with_latest.py
  docs/letter.md
  # stage 2 — gen_releases_manifest.py
  letter/RELEASES.json
  # stages 3 & 4 — update_version_metadata.py, render_index_html.py
  docs/index.html
  # stage 5 — publish_latest_artifacts.py
  docs/letter.md.asc
  docs/letter.md.asc.ots
  docs/alice-asi-publickey.asc
  docs/FINGERPRINT.txt
  docs/releases.json
  scripts/asi-public.asc
  # stage 6 — gen_discovery.py
  docs/sitemap.xml
  docs/llms.txt
  docs/.nojekyll
)

printf '%s\n' "${GENERATED_PATHS[*]}"
