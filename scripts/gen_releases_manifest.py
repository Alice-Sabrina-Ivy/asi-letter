#!/usr/bin/env python3
"""Generate the letter release manifest."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


RELEASE_PATTERN = re.compile(r"ASI-Letter-v(?P<version>\d{4}\.\d{2}\.\d{2})\.md$")
FINGERPRINT_RE = re.compile(r"^[0-9A-F]{40}$")
VALIDSIG_RE = re.compile(r"^\[GNUPG:\]\s+VALIDSIG\s+([0-9A-Fa-f]{40})\b")
GOODSIG_RE = re.compile(r"^\[GNUPG:\]\s+GOODSIG\s+[0-9A-Fa-f]+\s+(.+)$")


@dataclass
class Args:
    letter_dir: Path
    keys_dir: Path
    public_key: Path
    output: Path


def parse_args(argv: Optional[List[str]] = None) -> Args:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--letter-dir",
        type=Path,
        default=Path("letter"),
        help="Directory containing ASI letter releases (default: letter)",
    )
    parser.add_argument(
        "--keys-dir",
        type=Path,
        default=Path("keys"),
        help="Directory containing signing keys (default: keys)",
    )
    parser.add_argument(
        "--public-key",
        type=Path,
        default=Path("keys/alice-asi-publickey.asc"),
        help="Path to the current public key (default: keys/alice-asi-publickey.asc)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("letter/RELEASES.json"),
        help="Output manifest path (default: letter/RELEASES.json)",
    )

    namespace = parser.parse_args(argv)
    return Args(
        letter_dir=namespace.letter_dir,
        keys_dir=namespace.keys_dir,
        public_key=namespace.public_key,
        output=namespace.output,
    )


def detect_repo_root() -> Path:
    try:
        output = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path(__file__).resolve().parent.parent
    return Path(output.decode().strip()).resolve()


def to_rel(path: Path, repo_root: Path) -> str:
    resolved = path.resolve(strict=False)
    try:
        rel = resolved.relative_to(repo_root)
    except ValueError:
        return resolved.as_posix()
    return rel.as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_info(path: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    stat = path.stat()
    return {
        "path": to_rel(path, repo_root),
        "size": int(stat.st_size),
        "sha256": sha256_file(path),
    }


def read_fingerprint(path: Path) -> str:
    raw = path.read_text(encoding="utf-8-sig").strip().upper()
    if not FINGERPRINT_RE.fullmatch(raw):
        raise ValueError(
            f"{path} must be exactly 40 hex chars (got: '{raw}')."
        )
    return raw


def import_gpg_keys(keys_dir: Path) -> None:
    for asc in keys_dir.glob("*.asc"):
        try:
            subprocess.run(
                ["gpg", "--batch", "--import", str(asc)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except FileNotFoundError:
            return


def parse_sig_metadata(asc_path: Path) -> Optional[Dict[str, Optional[str]]]:
    try:
        result = subprocess.run(
            ["gpg", "--status-fd=1", "--verify", str(asc_path)],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None

    stdout = result.stdout.splitlines()
    fingerprint: Optional[str] = None
    uid: Optional[str] = None
    for line in stdout:
        if fingerprint is None:
            match = VALIDSIG_RE.match(line)
            if match:
                fingerprint = match.group(1).upper()
                continue
        if uid is None:
            match = GOODSIG_RE.match(line)
            if match:
                uid = match.group(1).strip()
    if fingerprint:
        return {"fingerprint": fingerprint, "uid": uid}
    return None


def ots_metadata(ots_path: Path, repo_root: Path) -> Optional[Dict[str, Any]]:
    if ots_path.exists():
        info = file_info(ots_path, repo_root)
        if info is None:
            return None
        info = dict(info)
        info["encoding"] = "binary"
        return info

    base64_path = ots_path.with_name(ots_path.name + ".base64")
    if not base64_path.exists():
        return None

    encoded_info = file_info(base64_path, repo_root)
    if encoded_info is None:
        return None

    raw = base64_path.read_text(encoding="utf-8")
    stripped = "".join(raw.split())
    try:
        decoded = base64.b64decode(stripped, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RuntimeError(f"Invalid base64 data in {base64_path}: {exc}") from exc

    sha256 = hashlib.sha256(decoded).hexdigest()
    return {
        "path": encoded_info["path"],
        "decoded_path": to_rel(ots_path, repo_root),
        "encoding": "base64",
        "size": int(len(decoded)),
        "sha256": sha256,
        "encoded": encoded_info,
    }


def collect_releases(
    letter_dir: Path, repo_root: Path, default_fingerprint: str
) -> List[Dict[str, Any]]:
    releases: List[Dict[str, Any]] = []
    for md_path in sorted(letter_dir.glob("ASI-Letter-v*.md")):
        match = RELEASE_PATTERN.search(md_path.name)
        if not match:
            continue
        version = match.group("version")
        asc_path = md_path.with_suffix(md_path.suffix + ".asc")
        ots_path = asc_path.with_suffix(asc_path.suffix + ".ots")

        sig_meta = parse_sig_metadata(asc_path) if asc_path.exists() else None
        if sig_meta:
            signer = {
                "fingerprint": sig_meta["fingerprint"],
                "uid": sig_meta.get("uid"),
            }
        else:
            signer = {"fingerprint": default_fingerprint, "uid": None}

        releases.append(
            {
                "version": version,
                "signer": signer,
                "files": {
                    "md": file_info(md_path, repo_root),
                    "asc": file_info(asc_path, repo_root),
                    "ots": ots_metadata(ots_path, repo_root),
                },
            }
        )

    releases.sort(key=lambda item: item["version"], reverse=True)
    return releases


def resolve_under(base: Path, candidate: Path) -> Path:
    if candidate.is_absolute():
        return candidate.resolve(strict=False)
    return (base / candidate).resolve(strict=False)


def generate_manifest(
    repo_root: Path,
    letter_dir: Path,
    keys_dir: Path,
    public_key: Path,
) -> Dict[str, Any]:
    fingerprint = read_fingerprint(keys_dir / "FINGERPRINT")
    import_gpg_keys(keys_dir)

    releases = collect_releases(letter_dir, repo_root, fingerprint)

    updated = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    return {
        "schema": "asi-letter/releases#2",
        "updated": updated,
        "key": {
            "fingerprint_current": fingerprint,
            "path": to_rel(public_key, repo_root),
        },
        "releases": releases,
    }


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    repo_root = detect_repo_root()
    letter_dir = resolve_under(repo_root, args.letter_dir)
    keys_dir = resolve_under(repo_root, args.keys_dir)
    public_key = resolve_under(repo_root, args.public_key)
    output_path = resolve_under(repo_root, args.output)
    try:
        manifest = generate_manifest(repo_root, letter_dir, keys_dir, public_key)
    except Exception as exc:  # pragma: no cover - CLI entry point
        print(f"Error: {exc}", file=os.sys.stderr)
        return 1

    json_text = json.dumps(manifest, indent=2)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json_text, encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
