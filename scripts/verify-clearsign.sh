#!/usr/bin/env bash
set -euo pipefail

# Require fingerprint from workflow env
: "${EXPECTED_FPR:?Set EXPECTED_FPR in workflow env}"

# Isolated keyring (CI-safe)
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

echo "Fetching key by fingerprint: $EXPECTED_FPR"

# Prefer hkps on port 443; if it flakes, fall back to HTTP fetch + import
if ! gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys "$EXPECTED_FPR"; then
  echo "Keyserver fetch failed; falling back to curl import"
  if ! curl -fsSL "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x$EXPECTED_FPR" | gpg --import; then
    echo "ERROR: could not obtain key $EXPECTED_FPR from keyserver.ubuntu.com" >&2
    exit 2
  fi
fi

# Trust this key for verification
echo "$EXPECTED_FPR:6:" | gpg --import-ownertrust >/dev/null

# Verify all clearsigned release files (if any)
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