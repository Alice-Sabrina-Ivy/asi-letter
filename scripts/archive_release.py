#!/usr/bin/env python3
"""Submit the repository and site to public archives, so releases outlive this host.

The letter states it is designed to outlive its author. That claim needs archives
that do not depend on this GitHub account continuing to exist, and archives only
help if they are refreshed -- a snapshot of a retired release is worse than
useless, because it looks current.

Two archives, with different requirements:

  Software Heritage  Archives the full git history, permanently. Anonymous
                     submissions are accepted (rate limit 10/hour), so this
                     needs no credentials and always runs.

  Wayback Machine    Archives the rendered pages. Save Page Now REFUSES
                     anonymous requests (HTTP 500 even from a real browser), so
                     it needs archive.org S3-style keys. Set IA_ACCESS_KEY and
                     IA_SECRET_KEY to enable it; without them this step is
                     skipped with a note rather than failing.

archive.today is deliberately not attempted: it is behind an interactive bot
wall that cannot be solved from CI.

Nothing here fails the build. An archive being slow, rate-limited or down is not
a reason to fail a release; the next run will try again.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/Alice-Sabrina-Ivy/asi-letter"
BASE_URL = "https://alice-sabrina-ivy.github.io/asi-letter/"
SWH_SAVE = "https://archive.softwareheritage.org/api/1/origin/save/git/url/"
WAYBACK_SAVE = "https://web.archive.org/save"

# Save Page Now limits in-flight captures per account. 4 of 7 URLs came back
# HTTP 429 when submitted back to back, so requests are paced and retried.
WAYBACK_DELAY_SECONDS = 8.0
RETRIES = 3


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument(
        "--wayback-delay",
        type=float,
        default=WAYBACK_DELAY_SECONDS,
        help="Seconds between Save Page Now submissions (avoids HTTP 429).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be submitted without contacting any archive.",
    )
    return parser.parse_args(list(argv))


def sitemap_urls(docs_dir: Path) -> List[str]:
    """Archive exactly what the sitemap publishes, so the two cannot disagree."""

    sitemap = docs_dir / "sitemap.xml"
    if not sitemap.exists():
        return [BASE_URL]
    urls = []
    for chunk in sitemap.read_text(encoding="utf-8").split("<loc>")[1:]:
        url = chunk.split("</loc>")[0].strip()
        if url.startswith(BASE_URL):
            urls.append(url)
    return urls or [BASE_URL]


def archive_software_heritage(timeout: float, dry_run: bool) -> None:
    print("Software Heritage (full git history)")
    target = f"{SWH_SAVE}{REPO_URL}/"
    if dry_run:
        print(f"  would POST {target}")
        return

    request = urllib.request.Request(
        target, data=b"", headers={"Accept": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", "replace"))
        print(
            f"  accepted: request {payload.get('id')} "
            f"({payload.get('save_request_status')}/{payload.get('save_task_status')})"
        )
        remaining = response.headers.get("X-Ratelimit-Remaining")
        if remaining is not None:
            print(f"  rate limit remaining this hour: {remaining}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace").strip()[:200]
        print(f"  not archived: HTTP {exc.code} {body}", file=sys.stderr)
    except Exception as exc:  # network, timeout, malformed JSON
        print(f"  not archived: {exc}", file=sys.stderr)


def archive_wayback(urls: List[str], timeout: float, dry_run: bool, delay: float = WAYBACK_DELAY_SECONDS) -> None:
    print("\nWayback Machine (rendered pages)")
    access = os.environ.get("IA_ACCESS_KEY", "").strip()
    secret = os.environ.get("IA_SECRET_KEY", "").strip()

    if not (access and secret):
        print("  skipped: IA_ACCESS_KEY / IA_SECRET_KEY not set.")
        print("  Save Page Now refuses anonymous requests; generate keys at")
        print("  https://archive.org/account/s3.php and add them as repository secrets.")
        return

    # Save Page Now caps how many captures an account may have in flight.
    # Submitting the whole sitemap back to back returned HTTP 429 for 4 of 7
    # URLs, so pace the requests and back off when told to.
    for position, url in enumerate(urls):
        if dry_run:
            print(f"  would submit {url}")
            continue

        if position:
            time.sleep(delay)

        data = urllib.parse.urlencode({"url": url, "capture_all": "1"}).encode()
        request = urllib.request.Request(
            WAYBACK_SAVE,
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"LOW {access}:{secret}",
            },
            method="POST",
        )

        for attempt in range(1, RETRIES + 1):
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read().decode("utf-8", "replace")
                try:
                    job = json.loads(body).get("job_id", "queued")
                except json.JSONDecodeError:
                    job = "queued"
                print(f"  submitted {url} ({job})")
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and attempt < RETRIES:
                    backoff = delay * (2 ** attempt)
                    print(f"  rate limited on {url}; retrying in {backoff:.0f}s")
                    time.sleep(backoff)
                    continue
                if exc.code in (401, 403):
                    # Wrong or revoked keys: worth saying plainly rather than
                    # burying it among transient failures.
                    print(
                        f"  rejected {url}: HTTP {exc.code} -- check IA_ACCESS_KEY / IA_SECRET_KEY",
                        file=sys.stderr,
                    )
                    return
                print(f"  failed {url}: HTTP {exc.code}", file=sys.stderr)
                break
            except Exception as exc:
                print(f"  failed {url}: {exc}", file=sys.stderr)
                break


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    docs_dir = args.docs_dir
    if not docs_dir.is_absolute():
        docs_dir = REPO_ROOT / docs_dir

    archive_software_heritage(args.timeout, args.dry_run)
    archive_wayback(sitemap_urls(docs_dir), args.timeout, args.dry_run, args.wayback_delay)

    # Always succeed: an archive being unavailable is not a release failure.
    print("\nDone (archive failures never fail the build).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
