#!/usr/bin/env bash
set -euo pipefail

PUBKEY="scripts/asi-public.asc"

# Isolated keyring (CI-safe)
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

# --- Normalize key file on runner (strip BOM, CR; convert UTF-16 → UTF-8 if needed) ---
python3 - <<PY
import codecs, sys
p = r"${PUBKEY}"
b = open(p,"rb").read()
# strip UTF-8 BOM
if b.startswith(codecs.BOM_UTF8):
    b = b[len(codecs.BOM_UTF8):]
# convert if looks like UTF-16 (BOM or lots of NULs)
def looks_utf16(x): 
    return x.startswith(codecs.BOM_UTF16_LE) or x.startswith(codecs.BOM_UTF16_BE) or (b"\x00" in x[:64])
if looks_utf16(b):
    try:
        b = b.decode("utf-16").encode("utf-8")
    except Exception:
        pass
# drop CRs
b = b.replace(b"\r", b"")
open(p,"wb").write(b)
PY
# ---------------------------------------------------------------------

# Import, derive fingerprint, trust it for this verify
gpg --batch --import "$PUBKEY"
FPR="$(gpg --import-options show-only --import --with-colons "$PUBKEY" | awk -F: '/^fpr:/{print $10; exit}')"
echo "Using fingerprint: $FPR"
echo "$FPR:6:" | gpg --import-ownertrust >/dev/null

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
