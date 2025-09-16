Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-Fingerprint {
  $raw = (Get-Content -Raw -Path "keys/FINGERPRINT").Trim().ToUpper()
  if ($raw -notmatch '^[0-9A-F]{40}$') { throw "keys/FINGERPRINT must be exactly 40 hex chars (got: '$raw')." }
  $raw
}

# Repo root (for relative path calc)
function Get-RepoRoot {
  $top = (& git rev-parse --show-toplevel 2>$null)
  if ([string]::IsNullOrWhiteSpace($top)) { $top = (Get-Location).Path }
  # Normalize slashes and trim trailing slash
  return (($top -replace '\\','/').TrimEnd('/'))
}
$RepoRoot = Get-RepoRoot

function To-Rel([string]$path) {
  if (-not $path) { return $null }
  $full = (Resolve-Path -LiteralPath $path).Path
  $full = ($full -replace '\\','/')
  if ($full.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    $rel = $full.Substring($RepoRoot.Length).TrimStart('/','\')
    return $rel
  }
  return $full
}

function FileInfoJson($path) {
  if (Test-Path $path) {
    $fi = Get-Item $path
    [pscustomobject]@{
      path   = (To-Rel $fi.FullName)
      size   = [int64]$fi.Length
      sha256 = (Get-FileHash $fi.FullName -Algorithm SHA256).Hash.ToLower()
    }
  } else { $null }
}

function Get-OtsMetadata([string]$otsBinaryPath) {
  if (Test-Path $otsBinaryPath) {
    $info = FileInfoJson $otsBinaryPath
    if ($info) { $info | Add-Member -NotePropertyName encoding -NotePropertyValue "binary" }
    return $info
  }

  $base64Path = "$otsBinaryPath.base64"
  if (Test-Path $base64Path) {
    $encoded = FileInfoJson $base64Path
    $raw = (Get-Content -Raw -Path $base64Path)
    $rawStripped = ($raw -replace '\s','')
    try {
      $bytes = [System.Convert]::FromBase64String($rawStripped)
    } catch {
      throw "Invalid base64 data in $($encoded.path): $_"
    }

    $tmp = [System.IO.Path]::GetTempFileName()
    try {
      [System.IO.File]::WriteAllBytes($tmp, $bytes)
      $binaryHash = (Get-FileHash $tmp -Algorithm SHA256).Hash.ToLower()
    } finally {
      Remove-Item $tmp -ErrorAction SilentlyContinue
    }

    return [pscustomobject]@{
      path          = $encoded.path
      decoded_path  = (To-Rel $otsBinaryPath)
      encoding      = "base64"
      size          = [int64]$bytes.Length
      sha256        = $binaryHash
      encoded       = [pscustomobject]@{
        path   = $encoded.path
        size   = $encoded.size
        sha256 = $encoded.sha256
      }
    }
  }

  return $null
}

function Ensure-GpgKeys {
  $keyFiles = Get-ChildItem -Path "keys" -Filter "*.asc" -ErrorAction SilentlyContinue
  if ($keyFiles) { foreach ($k in $keyFiles) { & gpg --batch --import $k.FullName | Out-Null } }
}

function Get-SigMeta([string]$ascPath) {
  # Returns @{ fingerprint="<40hex>"; uid="<User ID>" } or $null
  $out = & gpg --status-fd=1 --verify $ascPath 2>$null
  if (-not $out) { return $null }
  $fp = $null; $uid = $null
  foreach ($line in $out) {
    if ($line -match '^\[GNUPG:\]\s+VALIDSIG\s+([0-9A-Fa-f]{40})\b') { $fp = $matches[1].ToUpper() }
    elseif ($line -match '^\[GNUPG:\]\s+GOODSIG\s+[0-9A-Fa-f]+\s+(.+)$') { $uid = $matches[1].Trim() }
  }
  if ($fp) { return @{ fingerprint = $fp; uid = $uid } } else { return $null }
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

  $signerObj = if ($sig) {
    [pscustomobject]@{ fingerprint = $sig.fingerprint; uid = $sig.uid }
  } else {
    [pscustomobject]@{ fingerprint = $currentFp; uid = $null }
  }

  $releases += [pscustomobject]@{
    version = $ver
    signer  = $signerObj
    files   = [pscustomobject]@{
      md  = FileInfoJson $md.FullName
      asc = FileInfoJson $asc
      ots = Get-OtsMetadata $ots
    }
  }
}

# Force array even when it has one item using the unary comma operator
$releasesSorted = ,($releases | Sort-Object -Property version -Descending)

$manifest = [pscustomobject]@{
  schema  = "asi-letter/releases#2"
  updated = (Get-Date).ToUniversalTime().ToString("s") + "Z"
key     = [pscustomobject]@{
    fingerprint_current = $currentFp
    path = $pubkeyPath
  }
  releases = $releasesSorted
}

$manifest | ConvertTo-Json -Depth 6 | Set-Content "letter/RELEASES.json" -NoNewline
Write-Host "Wrote letter/RELEASES.json"
