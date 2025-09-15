#!/usr/bin/env bash
set -euo pipefail

: "${EXPECTED_FPR:?Set EXPECTED_FPR in workflow env}"
: "${RAW_KEY_URL:?Set RAW_KEY_URL in workflow env}"

# CI-safe keyring
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

echo "Downloading public key from: $RAW_KEY_URL"
TMP="$RUNNER_TEMP/key.asc"
curl -fsSL "$RAW_KEY_URL" -o "$TMP"

# Normalize the key: strip BOM/CR, convert UTF-16→UTF-8 if needed
python3 - <<PY
import codecs, sys, os
p = os.environ["TMP"]
b = open(p,"rb").read()
if b.startswith(codecs.BOM_UTF8): b = b[len(codecs.BOM_UTF8):]
def looks_utf16(x): 
    return x.startswith(codecs.BOM_UTF16_LE) or x.startswith(codecs.BOM_UTF16_BE) or (b"\x00" in x[:64])
try:
    if looks_utf16(b): b = b.decode("utf-16").encode("utf-8")
except Exception: pass
b = b.replace(b"\r", b"")
open(p,"wb").write(b)
PY

# Import and verify fingerprint
gpg --batch --import "$TMP"
DERIVED="$(gpg --list-keys --with-colons | awk -F: "/^fpr:/{print \$10; exit}")"
echo "Derived fingerprint: $DERIVED"
if [[ "$DERIVED" != "$EXPECTED_FPR" ]]; then
  echo "ERROR: Fingerprint mismatch. Expected $EXPECTED_FPR, got $DERIVED" >&2
  exit 3
fi

echo "$DERIVED:6:" | gpg --import-ownertrust >/dev/null

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