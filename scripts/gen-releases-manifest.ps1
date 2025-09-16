Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-Fingerprint {
  $raw = (Get-Content -Raw -Path "keys/FINGERPRINT").Trim().ToUpper()
  if ($raw -notmatch '^[0-9A-F]{40}$') {
    throw "keys/FINGERPRINT must be exactly 40 hex chars (got: '$raw')."
  }
  return $raw
}

function FileInfoJson($path) {
  if (Test-Path $path) {
    $fi = Get-Item $path
    return [pscustomobject]@{
      path   = ($path -replace '\\','/')
      size   = [int64]$fi.Length
      sha256 = (Get-FileHash $path -Algorithm SHA256).Hash.ToLower()
    }
  } else { $null }
}

function Ensure-GpgKeys {
  $keyFiles = Get-ChildItem -Path "keys" -Filter "*.asc" -ErrorAction SilentlyContinue
  if ($keyFiles) {
    foreach ($k in $keyFiles) { & gpg --batch --import $k.FullName | Out-Null }
  }
}

function Get-SigMeta([string]$ascPath) {
  # Returns @{ fingerprint="<40hex>"; uid="<User ID>" } or $null
  $raw = & gpg --status-fd=1 --verify $ascPath 2>$null
  $lines = ($raw -split "`r?`n")
  $meta = @{}
  foreach ($line in $lines) {
    if ($line -match '^\[GNUPG:\]\s+VALIDSIG\s+([0-9A-F]{40})\b') { $meta.fingerprint = $matches[1].ToUpper() }
    if ($line -match '^\[GNUPG:\]\s+GOODSIG\s+[0-9A-F]+\s+(.+)$') { $meta.uid = $matches[1].Trim() }
  }
  if ($meta.fingerprint) { return $meta } else { return $null }
}

$currentFp = Read-Fingerprint
$pubkeyPath = "keys/alice-asi-publickey.asc"
Ensure-GpgKeys

$releases = @()
Get-ChildItem -Path "letter" -Filter "ASI-Letter-v*.md" | ForEach-Object {
  $md = $_
  if ($md.BaseName -match 'ASI-Letter-v(?<ver>\d{4}\.\d{2}\.\d{2})') { $ver = $matches['ver'] } else { return }
  $asc = Join-Path $md.DirectoryName ($md.BaseName + ".asc")
  $ots = Join-Path $md.DirectoryName ($md.BaseName + ".asc.ots")

  $sig = $null
  if (Test-Path $asc) { $sig = Get-SigMeta $asc }

  $releases += [pscustomobject]@{
    version = $ver
    signer  = if ($sig) {
      [pscustomobject]@{ fingerprint = $sig.fingerprint; uid = ($sig.uid ?? $null) }
    } else {
      # Fallback to current fingerprint if parsing fails (e.g., missing key locally)
      [pscustomobject]@{ fingerprint = $currentFp; uid = $null }
    }
    files = [pscustomobject]@{
      md  = FileInfoJson $md.FullName
      asc = FileInfoJson $asc
      ots = FileInfoJson $ots
    }
  }
}

$manifest = [pscustomobject]@{
  schema  = "asi-letter/releases#1"
  updated = (Get-Date).ToUniversalTime().ToString("s") + "Z"
  key     = [pscustomobject]@{
    fingerprint_current = $currentFp
    path = $pubkeyPath
  }
  releases = ($releases | Sort-Object -Property version -Descending)
}

$out = "letter/RELEASES.json"
$manifest | ConvertTo-Json -Depth 6 | Set-Content $out -NoNewline
Write-Host "Wrote $out"