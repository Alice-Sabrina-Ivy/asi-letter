#!/usr/bin/env bash
set -euo pipefail

# Location of your armored public key in the repo:
PUBKEY="scripts/asi-public.asc"

# Create an isolated GNUPG home (CI-safe)
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

# Import the public key
gpg --batch --import "$PUBKEY"

# Derive the key fingerprint from the armored key itself
FPR="$(gpg --import-options show-only --import --with-colons "$PUBKEY" \
  | awk -F: '/^fpr:/ {print $10; exit}')"
echo "Using fingerprint: $FPR"

# (Optional) pin to EXPECTED_FPR via workflow env if you want an extra check
if [[ -n "${EXPECTED_FPR:-}" && "$FPR" != "$EXPECTED_FPR" ]]; then
  echo "ERROR: expected $EXPECTED_FPR but key file has $FPR"
  exit 1
fi

# Trust this key enough for verification (or use --trusted-key later)
echo "$FPR:6:" | gpg --import-ownertrust >/dev/null

# What to verify: args or default glob (clearsigned files)
FILES=("$@")
if [[ ${#FILES[@]} -eq 0 ]]; then
  shopt -s nullglob
  FILES=(releases/*.asc)
fi

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No .asc files found to verify."
  exit 0
fi

# Verify each clearsigned file
for f in "${FILES[@]}"; do
  echo "Verifying $f"
  gpg --batch --verify "$f"
done

echo "All signatures verified."
