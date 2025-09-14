#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'
shopt -s nullglob

# (Optional) Import public key if you keep it in-repo as scripts/asi-public.asc
if [[ -f "scripts/asi-public.asc" ]]; then
  gpg --batch --import "scripts/asi-public.asc" >/dev/null 2>&1 || true
fi

# Ensure expected key is present (set your full fingerprint here)
FPR="2C101FA0F24E93...REPLACE_WITH_FULL_FINGERPRINT"
have_fprs="$(gpg --batch --with-colons --list-keys | awk -F: '/^fpr:/{print $10}')"
if ! grep -q "$FPR" <<<"$have_fprs"; then
  echo "Public key with fingerprint $FPR not found in keyring."
  gpg --batch --list-keys
  exit 1
fi
echo "Fingerprint OK: $FPR"

fail=0
found=0
for f in letter/*.asc; do
  found=1
  echo "Verifying $f"
  if ! gpg --batch --verbose --verify "$f" 2>&1; then
    echo "PGP verification failed for $f"
    fail=1
  fi
done

if [[ $found -eq 0 ]]; then
  echo "No .asc files found under letter/ — skipping."
  exit 0
fi

exit $fail
