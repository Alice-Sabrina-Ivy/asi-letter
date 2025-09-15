#!/usr/bin/env bash
set -euo pipefail

# Require fingerprint from workflow env
: "${EXPECTED_FPR:?Set EXPECTED_FPR in workflow env}"

# Isolated keyring (CI-safe)
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

echo "Fetching key from keyserver: $EXPECTED_FPR"
# Needs dirmngr; keyserver.ubuntu.com is reliable on GitHub runners
gpg --keyserver keyserver.ubuntu.com --recv-keys "$EXPECTED_FPR"

# Trust this key for verification
echo "$EXPECTED_FPR:6:" | gpg --import-ownertrust >/dev/null

# Files to verify (default to releases/*.asc)
shopt -s nullglob
FILES=(releases/*.asc)
if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No .asc files found to verify."
  exit 0
fi

for f in "${FILES[@]}"; do
  echo "Verifying $f"
  gpg --batch --verify "$f"
done

echo "All signatures verified."
