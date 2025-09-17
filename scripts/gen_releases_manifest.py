#!/usr/bin/env python3
"""Generate ``letter/RELEASES.json`` using only cross-platform tooling."""

from __future__ import annotations

import argparse
import base64
import binascii
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union


RE_VERSION = re.compile(r"ASI-Letter-v(?P<ver>\d{4}\.\d{2}\.\d{2})\.md\Z")


class ManifestError(RuntimeError):
    """Raised when manifest generation fails."""


def _run_git_rev_parse(start: Path) -> Optional[Path]:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

    top = result.stdout.strip()
    if not top:
        return None
    return Path(top)


def repo_root(start: Path) -> Path:
    git_root = _run_git_rev_parse(start)
    if git_root is not None:
        return git_root.resolve()
    return start.resolve()


def read_fingerprint(path: Path) -> str:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ManifestError(f"Missing fingerprint file: {path}") from exc

    fingerprint = raw.strip()
    if fingerprint.startswith("\ufeff"):
        fingerprint = fingerprint.lstrip("\ufeff")
    fingerprint = fingerprint.upper()
    if not re.fullmatch(r"[0-9A-F]{40}", fingerprint):
        raise ManifestError(
            f"keys/FINGERPRINT must be exactly 40 hex chars (got: '{fingerprint}')"
        )
    return fingerprint


def relativize(path: Path, base: Path) -> str:
    base = base.resolve()
    absolute = path.resolve(strict=False)
    try:
        relative = absolute.relative_to(base)
    except ValueError:
        relative = Path(os.path.relpath(absolute, base))
    return PurePosixPath(relative).as_posix()


def file_info(path: Path, base: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None

    stat = path.stat()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "path": relativize(path, base),
        "size": int(stat.st_size),
        "sha256": digest,
    }


def ensure_gpg_keys(key_dir: Path) -> None:
    for key_file in sorted(key_dir.glob("*.asc")):
        try:
            subprocess.run(
                ["gpg", "--batch", "--import", str(key_file)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise ManifestError("gpg executable not found") from exc


SignatureMeta = Dict[str, Union[str, int, None]]


def parse_sig_metadata(asc_path: Path) -> Optional[SignatureMeta]:
    if not asc_path.exists():
        return None

    try:
        proc = subprocess.run(
            ["gpg", "--status-fd=1", "--verify", str(asc_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError as exc:
        raise ManifestError("gpg executable not found") from exc

    fingerprint: Optional[str] = None
    uid: Optional[str] = None
    timestamp: Optional[int] = None
    for line in proc.stdout.splitlines():
        if line.startswith("[GNUPG:]"):
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "VALIDSIG":
                fingerprint = parts[2].upper()
                if len(parts) >= 5:
                    try:
                        timestamp = int(parts[4])
                    except ValueError:
                        timestamp = None
            elif len(parts) >= 4 and parts[1] == "GOODSIG":
                uid = " ".join(parts[3:]).strip()
    if fingerprint:
        data: SignatureMeta = {
            "fingerprint": fingerprint,
            "uid": uid or None,
        }
        if timestamp is not None:
            data["timestamp"] = timestamp
        return data
    return None


def decode_base64(contents: str, description: str) -> bytes:
    normalized = re.sub(r"\s+", "", contents)
    try:
        return base64.b64decode(normalized, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ManifestError(f"Invalid base64 data in {description}: {exc}") from exc


def ots_metadata(ots_path: Path, base: Path) -> Optional[Dict[str, Any]]:
    if ots_path.exists():
        info = file_info(ots_path, base)
        if info is None:
            return None
        info = dict(info)
        info["encoding"] = "binary"
        return info

    base64_path = ots_path.with_name(ots_path.name + ".base64")
    if base64_path.exists():
        encoded_info = file_info(base64_path, base)
        if encoded_info is None:
            return None
        contents = base64_path.read_text(encoding="utf-8")
        raw_bytes = decode_base64(contents, encoded_info["path"])
        digest = hashlib.sha256(raw_bytes).hexdigest()
        return {
            "path": encoded_info["path"],
            "decoded_path": relativize(ots_path, base),
            "encoding": "base64",
            "size": len(raw_bytes),
            "sha256": digest,
            "encoded": encoded_info,
        }

    return None


def collect_releases(
    letter_dir: Path, base: Path, current_fp: str
) -> Tuple[List[Dict[str, Any]], List[int]]:
    releases: List[Dict[str, Any]] = []
    signature_epochs: List[int] = []
    for md_path in letter_dir.glob("ASI-Letter-v*.md"):
        match = RE_VERSION.fullmatch(md_path.name)
        if not match:
            continue
        version = match.group("ver")
        asc_path = md_path.with_name(md_path.name + ".asc")
        ots_path = asc_path.with_name(asc_path.name + ".ots")

        sig_meta = parse_sig_metadata(asc_path)
        signer = {
            "fingerprint": sig_meta["fingerprint"] if sig_meta else current_fp,
            "uid": sig_meta["uid"] if sig_meta else None,
        }
        if sig_meta and isinstance(sig_meta.get("timestamp"), int):
            signature_epochs.append(int(sig_meta["timestamp"]))

        releases.append(
            {
                "version": version,
                "signer": signer,
                "files": {
                    "md": file_info(md_path, base),
                    "asc": file_info(asc_path, base),
                    "ots": ots_metadata(ots_path, base),
                },
            }
        )

    releases.sort(key=lambda item: item["version"], reverse=True)
    return releases, signature_epochs


def build_manifest(base: Path) -> Dict[str, Any]:
    keys_dir = base / "keys"
    letter_dir = base / "letter"

    current_fp = read_fingerprint(keys_dir / "FINGERPRINT")
    ensure_gpg_keys(keys_dir)

    releases, signature_epochs = collect_releases(letter_dir, base, current_fp)

    pubkey_path = keys_dir / "alice-asi-publickey.asc"
    if signature_epochs:
        updated_dt = dt.datetime.fromtimestamp(
            max(signature_epochs), tz=dt.timezone.utc
        )
    else:
        updated_dt = dt.datetime.now(tz=dt.timezone.utc)
    updated = updated_dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "schema": "asi-letter/releases#2",
        "updated": updated,
        "key": {
            "fingerprint_current": current_fp,
            "path": relativize(pubkey_path, base),
        },
        "releases": releases,
    }

def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate letter release manifest")
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Only check if the generated manifest matches the existing file. "
            "Exit with status 1 if an update is required."
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("letter/RELEASES.json"),
        help="Path to the manifest file (defaults to letter/RELEASES.json).",
    )
    return parser.parse_args(list(argv))


def write_manifest_text(manifest: Dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2)


def resolve_output_path(base: Path, output: Path) -> Path:
    return output if output.is_absolute() else base / output


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(tuple(argv or []))

    base = repo_root(Path.cwd())
    try:
        manifest = build_manifest(base)
    except ManifestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = resolve_output_path(base, args.output)
    manifest_text = write_manifest_text(manifest)

    if args.check:
        try:
            current_text = output_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            print(
                f"Manifest not found at {output_path}. Run the generator to create it.",
                file=sys.stderr,
            )
            return 1

        try:
            rel = output_path.relative_to(base)
        except ValueError:
            rel = output_path

        if current_text == manifest_text:
            print(f"{rel} is up to date.")
            return 0

        print(
            f"{rel} is out of date. Run 'python3 scripts/gen_releases_manifest.py' and commit the updated file.",
            file=sys.stderr,
        )
        return 1

    output_path.write_text(manifest_text, encoding="utf-8")
    print(f"Wrote {relativize(output_path, base)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
