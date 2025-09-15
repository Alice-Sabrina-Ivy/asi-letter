#!/usr/bin/env bash
set -euo pipefail

PUBKEY="scripts/asi-public.asc"

# Isolated keyring for CI
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

# Import public key from repo
gpg --batch --import "$PUBKEY"

# Derive fingerprint from the key itself
FPR="$(gpg --import-options show-only --import --with-colons "$PUBKEY" \
  | awk -F: "/^fpr:/ {print \$10; exit}")"
echo "Using fingerprint: $FPR"

# Optional pin (set EXPECTED_FPR in workflow env to enforce)
if [[ -n "${EXPECTED_FPR:-}" && "$FPR" != "$EXPECTED_FPR" ]]; then
  echo "ERROR: expected $EXPECTED_FPR but key file has $FPR"
  exit 1
fi

# Trust this key for verification
echo "$FPR:6:" | gpg --import-ownertrust >/dev/null

# Files to verify
FILES=("$@")
if [[ ${#FILES[@]} -eq 0 ]]; then
  shopt -s nullglob
  FILES=(releases/*.asc)
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No .asc files found to verify."
  exit 0
fi

for f in "${FILES[@]}"; do
  echo "Verifying $f"
  gpg --batch --verify "$f"
done

echo "All signatures verified."
