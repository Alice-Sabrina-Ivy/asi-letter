#!/usr/bin/env bash
set -euo pipefail
EXPECTED_FPR="$(tr -d ' \n\r' < keys/FINGERPRINT)"
ACTUAL_FPR="$(gpg --with-colons --import-options show-only --import --fingerprint keys/alice-asi-publickey.asc 2>/dev/null | awk -F: '/^fpr:/ {print $10; exit}')"
if [[ -z "$ACTUAL_FPR" ]]; then
  echo "Could not parse fingerprint from keys/alice-asi-publickey.asc" >&2; exit 1
fi
if [[ "$EXPECTED_FPR" != "$ACTUAL_FPR" ]]; then
  echo "Fingerprint mismatch! Expected $EXPECTED_FPR but got $ACTUAL_FPR" >&2; exit 1
fi
echo "Fingerprint OK: $ACTUAL_FPR"
shopt -s nullglob
for f in letter/*.asc; do
  echo "Verifying $f"
  gpg --verify "$f" >/dev/null 2>&1 || (echo "PGP verification failed for $f" >&2; exit 1)
done
echo "All .asc files verified."
