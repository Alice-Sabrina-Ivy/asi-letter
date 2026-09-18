#!/usr/bin/env python3
"""Tell search engines a new release is published, without waiting to be crawled.

Why this exists: a search for this project's own name returned only GitHub, and
the one indexed copy of the site was four months stale -- it still showed the
opening line of a retired release. Organic recrawl of a small static site is slow
and unpredictable, so the release pipeline announces changes instead.

IndexNow is a small open protocol (Bing, Yandex, Seznam, Naver; Google does not
participate). Ownership is proved by hosting a file whose NAME is the key and
whose CONTENTS are the same key. That is the only credential, and it is public by
design, so nothing here is a secret.

This script finds that key file by looking for a docs/*.txt whose stem equals its
own contents -- self-validating, so there is no second copy to drift out of sync.

Usage:
    python3 scripts/ping_indexnow.py [--docs-dir docs] [--dry-run]

Exit status is 0 unless the submission is rejected for a reason worth fixing
(a bad key, or a malformed URL list). A search engine being unreachable is not
treated as a release failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://alice-sabrina-ivy.github.io/asi-letter/"
HOST = "alice-sabrina-ivy.github.io"
ENDPOINT = "https://api.indexnow.org/indexnow"


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"))
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be submitted without contacting the endpoint.",
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args(list(argv))


def find_key(docs_dir: Path) -> str:
    """Locate the IndexNow key file: name without .txt must equal its contents."""

    candidates = []
    for path in sorted(docs_dir.glob("*.txt")):
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if content and content == path.stem:
            candidates.append(content)

    if not candidates:
        raise SystemExit(
            f"No IndexNow key file in {docs_dir}.\n"
            "Expected a file whose name (without .txt) is identical to its contents, "
            "e.g. docs/<key>.txt containing <key>."
        )
    if len(candidates) > 1:
        raise SystemExit(f"Multiple IndexNow key files found: {candidates}")
    return candidates[0]


def collect_urls(docs_dir: Path) -> List[str]:
    """Submit exactly what the sitemap advertises, so the two cannot disagree."""

    sitemap = docs_dir / "sitemap.xml"
    if not sitemap.exists():
        raise SystemExit(f"Sitemap not found: {sitemap} (run scripts/gen_discovery.py first)")

    text = sitemap.read_text(encoding="utf-8")
    urls = []
    for chunk in text.split("<loc>")[1:]:
        url = chunk.split("</loc>")[0].strip()
        if url.startswith(BASE_URL):
            urls.append(url)
    if not urls:
        raise SystemExit(f"No URLs found in {sitemap}")
    return urls


def submit(key: str, urls: List[str], timeout: float, dry_run: bool) -> int:
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{BASE_URL}{key}.txt",
        "urlList": urls,
    }

    print(f"  host        : {payload['host']}")
    print(f"  keyLocation : {payload['keyLocation']}")
    print(f"  urls        : {len(urls)}")
    for url in urls:
        print(f"    {url}")

    if dry_run:
        print("\n  --dry-run: nothing submitted.")
        return 0

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            print(f"\n  submitted: HTTP {status}")
    except urllib.error.HTTPError as exc:
        # 400 = malformed request, 403 = key not valid for this host,
        # 422 = URLs do not belong to the host. All are our bug, so fail.
        detail = exc.read().decode("utf-8", "replace").strip()
        print(f"\n  rejected: HTTP {exc.code} {detail}", file=sys.stderr)
        if exc.code in (400, 403, 422):
            return 1
        print("  (treating as transient; not failing the release)", file=sys.stderr)
        return 0
    except (urllib.error.URLError, TimeoutError) as exc:
        # The search engine being unreachable is not a reason to fail a release.
        print(f"\n  could not reach endpoint ({exc}); not failing the release", file=sys.stderr)
        return 0

    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_args(argv)

    docs_dir = args.docs_dir
    if not docs_dir.is_absolute():
        docs_dir = REPO_ROOT / docs_dir
    if not docs_dir.is_dir():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    key = find_key(docs_dir)
    urls = collect_urls(docs_dir)
    return submit(key, urls, args.timeout, args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
