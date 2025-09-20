#!/usr/bin/env python3
"""Generate ``letter/RELEASES.json`` using only cross-platform tooling."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Optional, Tuple


RE_VERSION = re.compile(r"ASI-Letter-v(?P<ver>\d{4}\.\d{2}\.\d{2})\.md\Z")


class ManifestError(RuntimeError):
    """Raised when manifest generation fails."""


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only verify whether RELEASES.json is current; exit 1 if regeneration is needed.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("letter/RELEASES.json"),
        help="Destination manifest path (default: letter/RELEASES.json).",
    )
    return parser.parse_args(list(argv))


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


def parse_sig_metadata(asc_path: Path) -> Optional[Dict[str, Optional[str]]]:
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
    for line in proc.stdout.splitlines():
        if line.startswith("[GNUPG:]"):
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "VALIDSIG":
                fingerprint = parts[2].upper()
            elif len(parts) >= 4 and parts[1] == "GOODSIG":
                uid = " ".join(parts[3:]).strip()
    if fingerprint:
        return {"fingerprint": fingerprint, "uid": uid or None}
    return None


def ots_metadata(ots_path: Path, base: Path) -> Optional[Dict[str, Any]]:
    if ots_path.exists():
        info = file_info(ots_path, base)
        if info is None:
            return None
        info = dict(info)
        info["encoding"] = "binary"
        return info

    return None


def collect_releases(letter_dir: Path, base: Path, current_fp: str) -> List[Dict[str, Any]]:
    releases: List[Dict[str, Any]] = []
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
    return releases


def build_manifest(base: Path) -> Dict[str, Any]:
    keys_dir = base / "keys"
    letter_dir = base / "letter"

    current_fp = read_fingerprint(keys_dir / "FINGERPRINT")
    ensure_gpg_keys(keys_dir)

    releases = collect_releases(letter_dir, base, current_fp)

    pubkey_path = keys_dir / "alice-asi-publickey.asc"
    updated = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    return {
        "schema": "asi-letter/releases#2",
        "updated": updated,
        "key": {
            "fingerprint_current": current_fp,
            "path": relativize(pubkey_path, base),
        },
        "releases": releases,
    }


def serialize_manifest(manifest: Dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2)


def write_manifest(manifest: Dict[str, Any], output_path: Path) -> None:
    json_text = serialize_manifest(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json_text, encoding="utf-8")


def load_existing_manifest(path: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"Existing manifest is invalid JSON: {path}\n{exc}") from exc
    return data, text


def _equivalent_without_updated(
    proposed: Dict[str, Any],
    existing: Dict[str, Any],
) -> bool:
    proposed_copy = dict(proposed)
    existing_copy = dict(existing)
    proposed_copy.pop("updated", None)
    existing_copy.pop("updated", None)
    return proposed_copy == existing_copy


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    base = repo_root(Path.cwd())
    try:
        manifest = build_manifest(base)
    except ManifestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = args.output
    if not output_path.is_absolute():
        output_path = base / output_path

    try:
        existing_manifest, existing_text = load_existing_manifest(output_path)
    except ManifestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if existing_manifest is not None and _equivalent_without_updated(manifest, existing_manifest):
        manifest["updated"] = existing_manifest.get("updated", manifest["updated"])

    new_text = serialize_manifest(manifest)
    rel_path = relativize(output_path, base)

    if args.check:
        if existing_text is None:
            print(f"{rel_path} is missing and must be generated", file=sys.stderr)
            return 1
        if existing_text != new_text:
            print(f"{rel_path} is out of date", file=sys.stderr)
            return 1
        print(f"{rel_path} is up to date")
        return 0

    if existing_text == new_text:
        print(f"{rel_path} is already current")
        return 0

    write_manifest(manifest, output_path)
    print(f"Wrote {rel_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
