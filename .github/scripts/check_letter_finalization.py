#!/usr/bin/env python3
"""Utility to determine whether the current letter's OTS proof has finalized."""

from __future__ import annotations

import argparse
import io
import json
import re
import subprocess
import sys
from typing import Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def log(message: str) -> None:
    print(message)


def determine_branch(ref_name: Optional[str], ref: Optional[str], default: Optional[str]) -> str:
    branch = (ref_name or "").strip()
    ref_value = (ref or "").strip()
    default_value = (default or "").strip()

    if not branch and ref_value.startswith("refs/heads/"):
        branch = ref_value.split("/", 2)[-1]
    if not branch and default_value:
        branch = default_value
    if not branch:
        branch = "main"
    return branch


def fetch_text(url: str) -> Optional[str]:
    log(f"Fetching {url} ...")
    try:
        with urlopen(url) as response:  # nosec: B310 - controlled URLs
            return response.read().decode("utf-8", "replace")
    except (URLError, HTTPError) as exc:
        log(f"Failed to fetch {url}: {exc}")
        return None


def fetch_bytes(url: str) -> Optional[bytes]:
    log(f"Fetching {url} (binary) ...")
    try:
        with urlopen(url) as response:  # nosec: B310 - controlled URLs
            return response.read()
    except (URLError, HTTPError) as exc:
        log(f"Failed to fetch {url}: {exc}")
        return None


def ensure_opentimestamps() -> bool:
    try:
        import opentimestamps  # type: ignore  # noqa: F401
        return True
    except ImportError:
        log("Installing opentimestamps-client for block height extraction ...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", "opentimestamps-client"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as exc:  # pragma: no cover - best effort
            log(f"pip install failed: {exc}")
            return False

    try:
        import opentimestamps  # type: ignore  # noqa: F401
        return True
    except ImportError:
        log("Unable to import opentimestamps after installation attempt.")
        return False


def extract_ots_height(data: Optional[bytes]) -> str:
    if not data:
        return ""
    if not ensure_opentimestamps():
        return ""

    try:
        from opentimestamps.core.serialize import StreamDeserializationContext
        from opentimestamps.core.timestamp import DetachedTimestampFile
        from opentimestamps.core.notary import BitcoinBlockHeaderAttestation
    except Exception as exc:  # pragma: no cover - depends on package internals
        log(f"Unable to import OpenTimestamps parser: {exc}")
        return ""

    try:
        ctx = StreamDeserializationContext(io.BytesIO(data))
        timestamp = DetachedTimestampFile.deserialize(ctx).timestamp
    except Exception as exc:  # pragma: no cover - invalid proof
        log(f"Failed to parse OTS proof: {exc}")
        return ""

    heights = sorted(
        {
            att.height
            for _path, att in timestamp.all_attestations()
            if isinstance(att, BitcoinBlockHeaderAttestation)
        }
    )
    if not heights:
        return ""
    return str(heights[-1])


def write_outputs(
    path: Optional[str],
    should_run: bool,
    index_height: str,
    proof_height: str,
    cron_state: str,
) -> None:
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"should_run={'true' if should_run else 'false'}\n")
        if index_height:
            handle.write(f"index_height={index_height}\n")
        if proof_height:
            handle.write(f"proof_height={proof_height}\n")
        if cron_state:
            handle.write(f"cron_state={cron_state}\n")


def evaluate(
    event_name: str,
    repository: str,
    branch: str,
    force: bool = False,
) -> Tuple[bool, str, str, str]:
    cron_state = "none"
    if event_name in {"push", "workflow_run"}:
        cron_state = "enable"

    if force:
        log("Force flag supplied; allowing workflow to proceed regardless of finalization status.")
        return True, "", "", cron_state

    base = f"https://raw.githubusercontent.com/{repository}/{branch}"

    index_html = fetch_text(f"{base}/docs/index.html")
    if index_html is None:
        log("Unable to inspect docs/index.html; allowing workflow to proceed.")
        return True, "", "", cron_state

    version_match = re.search(r"<!--\s*release-version:\s*v?([0-9][0-9.]+)\s*-->", index_html)
    index_version = version_match.group(1) if version_match else ""
    height_match = re.search(r"Bitcoin block <strong>([0-9]+)</strong>", index_html)
    index_height = height_match.group(1) if height_match else ""

    releases_raw = fetch_text(f"{base}/letter/RELEASES.json")
    if releases_raw is None:
        log("Unable to inspect RELEASES.json; allowing workflow to proceed.")
        return True, index_height, "", cron_state

    try:
        releases = json.loads(releases_raw)
    except json.JSONDecodeError as exc:
        log(f"Failed to parse RELEASES.json: {exc}")
        return True, index_height, "", cron_state

    release_entry = None
    releases_list = releases.get("releases") or []
    if index_version:
        for candidate in releases_list:
            if candidate.get("version") == index_version:
                release_entry = candidate
                break
    if release_entry is None and releases_list:
        release_entry = releases_list[0]

    if release_entry is None:
        log("No releases found; allowing workflow to proceed.")
        return True, index_height, "", cron_state

    ots_path = (
        release_entry.get("files", {})
        .get("ots", {})
        .get("path")
    )
    if not ots_path:
        log("Latest release lacks an OTS proof path; allowing workflow to proceed.")
        return True, index_height, "", cron_state

    ots_bytes = fetch_bytes(f"{base}/{ots_path}")
    ots_height = extract_ots_height(ots_bytes)

    if ots_height and index_height == ots_height:
        log(
            "Detected finalized Bitcoin block %s for current letter; skipping further runs." % index_height
        )
        if event_name == "schedule":
            cron_state = "disable"
        return False, index_height, ots_height, cron_state

    log(
        "Proof not yet finalized for current letter (index height: %s, proof height: %s); proceeding."
        % (
            index_height or "n/a",
            ots_height or "n/a",
        )
    )
    return True, index_height, ots_height, cron_state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--event-name", default="", help="GitHub event name")
    parser.add_argument("--repository", required=True, help="owner/repo slug")
    parser.add_argument("--ref-name", default="", help="Git ref name")
    parser.add_argument("--ref", default="", help="Full Git ref")
    parser.add_argument("--default-branch", default="", help="Default branch name")
    parser.add_argument("--github-output", default="", help="Path to GITHUB_OUTPUT")
    parser.add_argument(
        "--force",
        choices={"true", "false"},
        default="false",
        help="Override the finalization guard (true/false)",
    )

    args = parser.parse_args()

    branch = determine_branch(args.ref_name, args.ref, args.default_branch)

    should_run, index_height, proof_height, cron_state = evaluate(
        args.event_name,
        args.repository,
        branch,
        force=args.force == "true",
    )
    write_outputs(args.github_output, should_run, index_height, proof_height, cron_state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
