#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <KEYID-or-FPR> <path/to/letter.md>" >&2
  exit 1
fi
KEYID="$1"; INPUT="$2"
OUT="${INPUT}.asc"
gpg --clearsign --local-user "$KEYID" --output "$OUT" "$INPUT"
echo "Created: $OUT"
