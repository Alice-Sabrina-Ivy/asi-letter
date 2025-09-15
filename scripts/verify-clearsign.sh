#!/usr/bin/env bash
set -euo pipefail

PUBKEY="scripts/asi-public.asc"
FPR="${EXPECTED_FPR:-}"   # optional, but recommended

# Isolated keyring (CI-safe)
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

# --- Normalize key file on runner (strip BOM/CR; convert UTF-16 → UTF-8 if needed) ---
python3 - <<PY
import codecs
p = r"${PUBKEY}"
b = open(p, "rb").read()
# strip UTF-8 BOM
if b.startswith(codecs.BOM_UTF8): b = b[len(codecs.BOM_UTF8):]
# convert if looks like UTF-16 (BOM or lots of NULs)
def looks_utf16(x): 
    return x.startswith(codecs.BOM_UTF16_LE) or x.startswith(codecs.BOM_UTF16_BE) or b"\x00" in x[:64]
try:
    if looks_utf16(b): b = b.decode("utf-16").encode("utf-8")
except Exception: pass
# drop CRs (Windows)
b = b.replace(b"\r", b"")
open(p, "wb").write(b)
PY
# ---------------------------------------------------------------------

# Try local file import first; if it fails, fetch by fingerprint
if gpg --batch --import "$PUBKEY" 2>/dev/null; then
  echo "Imported public key from $PUBKEY"
else
  if [[ -z "$FPR" ]]; then
    echo "ERROR: local import failed and EXPECTED_FPR not set; cannot fetch key." >&2
    exit 2
  fi
  echo "Local import failed; fetching key by fingerprint: $FPR"
  # keyserver import (requires network)
  gpg --keyserver keyserver.ubuntu.com --recv-keys "$FPR"
fi

# Derive/confirm fingerprint
DERIVED="$(gpg --list-keys --with-colons | awk -F: "/^fpr:/{print \$10; exit}")"
echo "Using fingerprint: $DERIVED"
if [[ -n "$FPR" && "$DERIVED" != "$FPR" ]]; then
  echo "ERROR: Fingerprint mismatch. Expected $FPR, got $DERIVED" >&2
  exit 3
fi

# Trust it for verification
echo "$DERIVED:6:" | gpg --import-ownertrust >/dev/null

# Files to verify (default to releases/*.asc)
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
