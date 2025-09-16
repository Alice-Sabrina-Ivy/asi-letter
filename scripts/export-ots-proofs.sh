#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

force=0
if [[ "${1:-}" == "--force" ]]; then
  force=1
fi

shopt -s nullglob
proofs=(letter/*.asc.ots.base64)
if [[ ${#proofs[@]} -eq 0 ]]; then
  echo "No base64-encoded OpenTimestamps proofs found under letter/." >&2
  exit 1
fi

for proof in "${proofs[@]}"; do
  decoded="${proof%.base64}"
  if [[ -e "$decoded" && $force -eq 0 ]]; then
    echo "Skipping $decoded (already exists). Use --force to overwrite." >&2
    continue
  fi
  base64 --decode "$proof" > "$decoded"
  echo "Decoded $proof → $decoded"
done

