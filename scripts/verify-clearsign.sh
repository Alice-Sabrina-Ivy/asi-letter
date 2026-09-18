#!/usr/bin/env bash
# Verify every letter/*.asc against the trusted fingerprint in keys/FINGERPRINT.
#
# This used to run `gpg --verify` and treat exit 0 as success, which accepted two
# things it should not have:
#
#   1. A good signature from ANY key in the keyring. The old script confirmed the
#      trusted fingerprint was *present* in the keyring, then never checked that
#      the signature was actually made by it. Importing any other key made those
#      signatures pass too.
#   2. A good signature from an EXPIRED key. gpg returns 0 in that case and only
#      prints "[expired]" as a note, so the repo's only signature gate could not
#      detect key expiry -- and did not, when the key lapsed on 2026-09-15.
#
# It now parses gpg's machine-readable --status-fd output and requires an explicit
# VALIDSIG naming the trusted primary key, rejects expired/revoked/bad signatures,
# and warns before the key lapses. It also checks that each .md really is the text
# that was signed (see scripts/check_signed_payload.py).
set -euo pipefail
IFS=$'\n\t'
shopt -s nullglob

GPG_BIN="${GPG_BIN:-gpg}"
EXPIRY_WARN_DAYS="${EXPIRY_WARN_DAYS:-30}"

# (Optional) Import the in-repo public key. It is generated from
# keys/alice-asi-publickey.asc by publish_latest_artifacts.py; never hand-edited.
if [[ -f "scripts/asi-public.asc" ]]; then
  "$GPG_BIN" --batch --import "scripts/asi-public.asc" >/dev/null 2>&1 || true
fi

FPR=$(tr -cd '[:xdigit:]' < keys/FINGERPRINT | tr '[:lower:]' '[:upper:]')
if [[ ${#FPR} -ne 40 ]]; then
  echo "keys/FINGERPRINT must contain exactly 40 hex characters (got ${#FPR})." >&2
  exit 1
fi

have_fprs="$("$GPG_BIN" --batch --with-colons --list-keys 2>/dev/null | awk -F: '/^fpr:/{print $10}')"
if ! grep -qx "$FPR" <<<"$have_fprs"; then
  echo "Public key with fingerprint $FPR not found in keyring." >&2
  exit 1
fi
echo "Trusted fingerprint: $FPR"

# --- key expiry horizon -------------------------------------------------------
# Catch a lapse before it silently degrades every verification, rather than after.
expiry=$("$GPG_BIN" --batch --with-colons --list-keys "$FPR" 2>/dev/null \
  | awk -F: '/^pub:/{print $7; exit}')
if [[ -n "${expiry:-}" ]]; then
  now=$(date +%s)
  # Compare seconds, not days. Bash integer division truncates toward zero, so a
  # key that lapsed less than 24h ago yields days == 0 and would have taken the
  # WARNING branch -- reporting "expires in 0 days" for a key that is already dead.
  if (( expiry <= now )); then
    echo "ERROR: signing key EXPIRED $(( (now - expiry) / 86400 )) day(s) ago. New releases cannot be signed." >&2
    exit 1
  fi
  days=$(( (expiry - now) / 86400 ))
  if (( days <= EXPIRY_WARN_DAYS )); then
    echo "WARNING: signing key expires in ${days} day(s). Extend it before the next release." >&2
  else
    echo "Key expiry: ${days} day(s) away."
  fi
else
  echo "Key expiry: none set."
fi

# --- signature verification ---------------------------------------------------
fail=0
found=0
for f in letter/*.asc; do
  found=1

  # gpg silently ignores any text OUTSIDE the armored block, so a file can carry
  # unsigned prose before "-----BEGIN PGP SIGNED MESSAGE-----" or after
  # "-----END PGP SIGNATURE-----" and still verify clean. Anyone reading the .asc
  # as a document would see that text as if it were signed. Require the armor to
  # be the whole file.
  first_line=$(grep -m1 -v '^[[:space:]]*$' "$f" || true)
  last_line=$(grep -v '^[[:space:]]*$' "$f" | tail -n1 || true)
  if [[ "$first_line" != "-----BEGIN PGP SIGNED MESSAGE-----" ]]; then
    echo "FAIL $f: content before the clear-signed block (unsigned text would read as signed)"
    fail=1
    continue
  fi
  if [[ "$last_line" != "-----END PGP SIGNATURE-----" ]]; then
    echo "FAIL $f: content after the signature block (unsigned text would read as signed)"
    fail=1
    continue
  fi

  status=$("$GPG_BIN" --batch --status-fd=1 --verify "$f" 2>/dev/null || true)

  if grep -q '^\[GNUPG:\] \(BADSIG\|ERRSIG\|NO_PUBKEY\)' <<<"$status"; then
    echo "FAIL $f: bad, unverifiable, or unknown-key signature"
    fail=1
    continue
  fi
  if grep -q '^\[GNUPG:\] EXPKEYSIG' <<<"$status"; then
    echo "FAIL $f: signature made by an EXPIRED key"
    fail=1
    continue
  fi
  if grep -q '^\[GNUPG:\] REVKEYSIG' <<<"$status"; then
    echo "FAIL $f: signature made by a REVOKED key"
    fail=1
    continue
  fi
  if ! grep -q '^\[GNUPG:\] GOODSIG' <<<"$status"; then
    echo "FAIL $f: no GOODSIG in gpg status output"
    fail=1
    continue
  fi

  # VALIDSIG's LAST field is the primary key fingerprint. Binding to that is what
  # makes this a check against the trusted key rather than against the keyring.
  primary=$(awk '/^\[GNUPG:\] VALIDSIG /{print $NF; exit}' <<<"$status")
  if [[ -z "${primary:-}" ]]; then
    echo "FAIL $f: no VALIDSIG line in gpg status output"
    fail=1
    continue
  fi
  if [[ "${primary^^}" != "$FPR" ]]; then
    echo "FAIL $f: signed by ${primary^^}, not the trusted key $FPR"
    fail=1
    continue
  fi

  echo "ok   $f (VALIDSIG $FPR)"
done

if [[ $found -eq 0 ]]; then
  # A vacuous pass would be a silent failure: the gate would report success while
  # verifying nothing at all.
  echo "No .asc files found under letter/ -- nothing verified." >&2
  exit 1
fi

# --- payload binding ----------------------------------------------------------
echo
echo "Checking each letter/*.md is the text that was signed ..."
if ! python3 scripts/check_signed_payload.py --gpg "$GPG_BIN"; then
  fail=1
fi

exit $fail
