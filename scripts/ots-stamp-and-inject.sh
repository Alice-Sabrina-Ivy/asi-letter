#!/usr/bin/env bash
set -euo pipefail

FILE="$1"
PROOFS_DIR="proofs"
mkdir -p "$PROOFS_DIR"

command -v ots >/dev/null || { echo "Missing '\''ots'\'' CLI"; exit 1; }

BN="$(basename "$FILE")"
OTS_PATH="$PROOFS_DIR/$BN.ots"
B64_PATH="$PROOFS_DIR/$BN.ots.b64"
INFO_PATH="$PROOFS_DIR/$BN.info.txt"
APPENDIX_MD="$PROOFS_DIR/$BN.appendix.md"
APPENDIX_HTML="$PROOFS_DIR/$BN.appendix.html"

SHA="$(sha256sum "$FILE" | awk '\''{print tolower($1)}'\'')"
echo "$SHA  $BN" > "$PROOFS_DIR/$BN.sha256"

ots stamp "$FILE"
mv "$FILE.ots" "$OTS_PATH"

base64 -w0 "$OTS_PATH" > "$B64_PATH"

ots info "$OTS_PATH" > "$INFO_PATH" || true

# Markdown appendix
{
  echo "## Proof of Creation — Bitcoin anchored (OpenTimestamps)"
  echo
  echo "- Artifact: $BN"
  echo "- SHA-256: $SHA"
  echo "- OpenTimestamps proof: $OTS_PATH"
  echo "- Verify on any system:"
  echo "  1) \`pip install opentimestamps-client\`"
  echo "  2) \`ots verify $OTS_PATH \"$BN\"\`"
  echo "  3) \`ots info $OTS_PATH\`"
  echo
  echo "### Inline OTS proof (Base64)"
  echo
  echo '```'
  cat "$B64_PATH"
  echo
  echo '```'
} > "$APPENDIX_MD"

# HTML appendix (for index.html injection)
{
  cat <<HTML
<div class="proof-block">
  <h4 style="margin:0 0 .5rem 0;">Proof of Creation — Bitcoin anchored (OpenTimestamps)</h4>
  <ul style="margin:.25rem 0 1rem 1.25rem;">
    <li><strong>Artifact:</strong> $BN</li>
    <li><strong>SHA-256:</strong> <code>$SHA</code></li>
    <li><strong>OpenTimestamps proof:</strong> <code>$OTS_PATH</code></li>
  </ul>
  <p style="margin:.25rem 0 .5rem 0;"><strong>Verify on any system</strong></p>
  <ol style="margin:.25rem 0 1rem 1.25rem;">
    <li><code>pip install opentimestamps-client</code></li>
    <li><code>ots verify $OTS_PATH "$BN"</code></li>
    <li><code>ots info $OTS_PATH</code></li>
  </ol>
  <details>
    <summary>Inline OTS proof (Base64)</summary>
    <pre style="white-space:pre-wrap;word-break:break-all;"><code>$(cat "$B64_PATH")</code></pre>
  </details>
</div>
HTML
} > "$APPENDIX_HTML"

# Replace between markers if present
if grep -q "<!-- PROOF:BEGIN -->" "$FILE" && grep -q "<!-- PROOF:END -->" "$FILE"; then
  TMP_BLOCK="$(mktemp)"
  if [[ "$FILE" =~ \.html?$ ]]; then
    { echo "<!-- PROOF:BEGIN -->"; cat "$APPENDIX_HTML"; echo "<!-- PROOF:END -->"; } > "$TMP_BLOCK"
  else
    { echo "<!-- PROOF:BEGIN -->"; cat "$APPENDIX_MD"; echo "<!-- PROOF:END -->"; } > "$TMP_BLOCK"
  fi
  perl -0777 -pe 'BEGIN{undef $/} s/<!-- PROOF:BEGIN -->.*?<!-- PROOF:END -->/'"$(sed 's/[&/\]/\\&/g' "$TMP_BLOCK")"'/s' -i "$FILE"
  rm -f "$TMP_BLOCK"
fi

echo "Stamped and prepared appendix for $BN"
