#!/usr/bin/env bash
set -euo pipefail

PUBKEY="scripts/asi-public.asc"

# Isolated keyring (CI-safe)
export GNUPGHOME="${GNUPGHOME:-$RUNNER_TEMP/gnupg}"
mkdir -p "$GNUPGHOME"; chmod 700 "$GNUPGHOME"

# --- Normalize key file on runner (handles BOM/CR/UTF-16 accidents) ---
# Strip UTF-8 BOM if present
if head -c3 "$PUBKEY" | od -An -t x1 | tr -d " \n" | grep -qi '^efbbbf$'; then
  tail -c +4 "$PUBKEY" > "$PUBKEY.tmp" && mv "$PUBKEY.tmp" "$PUBKEY"
fi
# If UTF-16, convert to UTF-8
ENC="$(file -bi "$PUBKEY" | sed 's/.*charset=//')"
if [[ "$ENC" == "utf-16le" || "$ENC" == "utf-16be" ]]; then
  iconv -f "$ENC" -t utf-8 "$PUBKEY" > "$PUBKEY.tmp" && mv "$PUBKEY.tmp" "$PUBKEY"
fi
# Drop CRs (Windows line endings)
tr -d '\r' < "$PUBKEY" > "$PUBKEY.tmp" && mv "$PUBKEY.tmp" "$PUBKEY"
# ---------------------------------------------------------------------

# Import, derive fingerprint, trust it for this verify
gpg --batch --import "$PUBKEY"
FPR="$(gpg --import-options show-only --import --with-colons "$PUBKEY" | awk -F: "/^fpr:/{print \$10; exit}")"
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
