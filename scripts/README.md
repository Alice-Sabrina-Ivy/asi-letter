# Scripts

This directory collects automation helpers that keep the published assets in
sync with the latest signed ASI Letter and provide tooling for
cryptographic/OTS maintenance. The most common workflow is driven by
`release.py`, which orchestrates the individual steps so contributors do not
need to remember the correct order. The sections below describe each script and
the related continuous validation jobs in more detail.

## Release orchestration

### `release.py`

```
python3 scripts/release.py [--check|--dry-run] [--skip-sync] [--skip-manifest] [--skip-metadata] [--skip-render] [--skip-artifacts] [--skip-discovery]
```

* Runs the scripts in the following order, aborting on the first failure:
  1. `sync_docs_with_latest.py`
  2. `gen_releases_manifest.py`
  3. `update_version_metadata.py`
  4. `render_index_html.py`
  5. `publish_latest_artifacts.py`
  6. `gen_discovery.py`
* Pass `--check` or `--dry-run` to forward the read-only mode supported by the
  underlying tools. This is useful in CI or when verifying that the working tree
  is already up to date.
* Advanced users can re-run a specific stage by combining the `--skip-…`
  switches shown above.

When regenerating assets for a new release you can simply run:

```
python3 scripts/release.py
```

If you prefer `make`, use the `release` target described below.

### `sync_docs_with_latest.py`

Copies the newest signed Markdown file in `letter/` to `docs/letter.md`. The
script discovers the most recent `ASI-Letter-vYYYY.MM.DD.md`, ensures the
matching `.asc` signature exists, and writes the Markdown into the docs tree.

```
python3 scripts/sync_docs_with_latest.py [--letter-dir PATH] [--docs-dir PATH] [--check]
```

`--check` exits with status 1 when the docs need to be refreshed, which is how
CI detects out-of-sync content.

### `gen_releases_manifest.py`

Builds `letter/RELEASES.json` using standard Python tooling so the manifest can
be regenerated anywhere. It imports trusted keys from `keys/`, validates the
`keys/FINGERPRINT` file, collects metadata for every markdown/signature/proof
triple, and serializes the result in a stable order. The script keeps the
existing `updated` timestamp when only that field would change.

```
python3 scripts/gen_releases_manifest.py [--output PATH] [--check]
```

### `update_version_metadata.py`

Reads `letter/RELEASES.json`, selects the newest release, and rewrites known
version placeholders (page title, data attributes, and HTML comments) in site
artifacts such as `docs/index.html`.

It also regenerates the schema.org JSON-LD block between the
`<!-- structured-data:start -->` / `<!-- structured-data:end -->` markers in
`docs/index.html`. That block carries `version` and `dateModified`, so it is
rebuilt wholesale on every run rather than hand-maintained. `datePublished` is
derived from the *oldest* manifest entry, `version`/`dateModified` from the
newest. The payload is serialized with `json.dumps` (not string-built) so values
are escaped correctly inside the `<script>` element.

The Open Graph and Twitter tags in `<head>` deliberately contain no version
string, so they need no automation and cannot go stale.

```
python3 scripts/update_version_metadata.py [--manifest PATH] [--check] [targets...]
```

`targets` defaults to `docs/index.html`. Passing `--check` reports files that
require updates without modifying them.

### `render_index_html.py`

Pre-renders `docs/letter.md` into HTML and replaces the content between the
render markers in `docs/index.html`. This keeps the site layout identical while
removing the need for client-side JavaScript rendering. Requires the Python
`markdown` package.

It also gives every heading an `id` and turns the letter's Table of Contents
into working links, so each section has a shareable URL
(`.../asi-letter/#paradox-clause`). Slugs follow GitHub's algorithm, so the same
anchor resolves on the site and on GitHub's rendering of `letter/*.md`.

Both are derived from the letter on every build and never stored, so the links
follow the document as it evolves -- no anchor map to maintain. Measured across
the existing 14 releases, 98% of anchors survive any given release unchanged. A
Table of Contents entry that matches no heading raises instead of rendering as
plain text, so a half-linked contents page cannot ship silently.

```
python3 scripts/render_index_html.py [--index PATH] [--markdown PATH] [--check]
```

### `publish_latest_artifacts.py`

Copies the newest release's verification artifacts into `docs/` under names
that never change, so the published site is self-sufficient for verification
and no URL is version-pinned:

| stable path | source |
| --- | --- |
| `docs/letter.md.asc` | newest `letter/ASI-Letter-v*.md.asc` |
| `docs/letter.md.asc.ots` | matching `.asc.ots` proof |
| `docs/alice-asi-publickey.asc` | `keys/alice-asi-publickey.asc` |
| `docs/FINGERPRINT.txt` | `keys/FINGERPRINT` |
| `docs/releases.json` | `letter/RELEASES.json` |
| `scripts/asi-public.asc` | `keys/alice-asi-publickey.asc` |

Copies are byte-identical, so a published `.asc` hashes to exactly the
`sha256` recorded in the manifest. `*.asc` and `*.ots` are marked `-text` in
`.gitattributes` to keep that true through check-in.

The last row matters: `scripts/asi-public.asc` is the copy
`verify-clearsign.sh` imports. It was previously hand-maintained and had
drifted to an expired key export, so deriving it here prevents recurrence.

```
python3 scripts/publish_latest_artifacts.py [--letter-dir PATH] [--keys-dir PATH] [--docs-dir PATH] [--check]
```

### `gen_discovery.py`

Generates the site's discovery surfaces from a single table of canonical URLs,
so they cannot drift apart or go stale:

* `docs/sitemap.xml` — every published URL, with `lastmod` taken from the
  newest release in the manifest.
* `docs/llms.txt` — a structured index for automated readers, describing what
  the letter is, which file is authoritative, and how to verify it. It also
  points at the FIRST release and its Bitcoin anchor: the current release's
  timestamp only dates the current revision, so the original is what establishes
  when the work existed. Those two entries are absolute `raw.githubusercontent`
  URLs because Pages serves only `docs/`; a sitemap may list only URLs on its own
  host, so they are `llms.txt`-only by construction.
* `docs/.nojekyll` — makes Pages serve `docs/` verbatim rather than running it
  through Jekyll, which silently drops paths beginning with `.` or `_`.

```
python3 scripts/gen_discovery.py [--manifest PATH] [--docs-dir PATH] [--check]
```

## Signing and verification helpers

### `sign-and-export.sh`

Minimal wrapper around `gpg --clearsign` that accepts a key ID/fingerprint and a
Markdown letter, producing `<letter>.asc` beside the input. Intended for release
managers who prefer not to remember the exact GnuPG flags.

### `verify-clearsign.sh`

Verifies every `letter/*.asc` against the fingerprint in `keys/FINGERPRINT`, by
parsing GnuPG's machine-readable `--status-fd` output rather than trusting its
exit status. This is the same entrypoint the CI job uses. It fails when:

* the signature is `BADSIG`, `ERRSIG`, `NO_PUBKEY`, `EXPKEYSIG` or `REVKEYSIG`;
* there is no `VALIDSIG` naming the trusted **primary** key — it previously
  checked only that the fingerprint *existed* in the keyring, so a good signature
  from any other imported key passed;
* the `.asc` carries text outside the armored block, which GnuPG ignores but a
  human reader would see as though it were signed;
* no `.asc` files were found at all, which used to pass vacuously;
* the signing key has expired. `gpg --verify` returns 0 for a good signature from
  an expired key and only prints `[expired]`, which is why the key lapsing on
  2026-09-15 went unnoticed. The script also warns within `EXPIRY_WARN_DAYS`
  (default 30) of expiry.

It then runs `check_signed_payload.py` to confirm each `.md` really is the text
its `.asc` signed.

`scripts/asi-public.asc` is generated by `publish_latest_artifacts.py` from
`keys/alice-asi-publickey.asc`. Do not edit it by hand: this script imports it,
so a stale copy makes CI verify every release against an outdated key export.

### `check_signed_payload.py`

Confirms each `letter/*.md` is the text embedded in its `letter/*.md.asc`.

```
python3 scripts/check_signed_payload.py [--letter-dir PATH] [--gpg BIN] [--no-fingerprint-check]
```

`gpg --verify` validates only the text *inside* the clear-signature and never
reads the sibling `.md`, so a `.md` could drift from the document it is paired
with while every signature check still passed — and
`letter/ASI-Letter-v2025.09.14.md` had already drifted on 18 lines.

Two details matter if you change this:

* **The comparison must stay canonicalized.** RFC 4880 ignores exactly trailing
  SPACE/TAB per line and the final line terminator. Nothing else. A raw `cmp`
  false-positives on 7 of the 14 existing releases (this letter uses trailing
  double-spaces as Markdown hard breaks); `str.rstrip()` would over-normalize and
  strip Unicode whitespace that *is* signed.
* **The signature must be checked here too.** GnuPG writes the cleartext before
  it evaluates the signature, so a forged signature still produces output. The
  script requires a good `VALIDSIG` bound to `keys/FINGERPRINT`.

## OpenTimestamps utilities

### `find_latest_ots.py`

Locates the newest `.ots` proof in a directory and prints several helpful
outputs (`latest`, `basename`, `noext`, and `version`). The automation workflows
use these values to verify and upgrade proofs idempotently.

## Make integration

A convenience `release` target is provided so contributors can run the whole
pipeline via `make`:

```
make release
```

This is equivalent to invoking `python3 scripts/release.py` directly.

## Validation and automation workflows

Multiple GitHub Actions workflows keep the repository healthy and the published
assets reproducible:

* **`verify-releases.yml`** (push/PR): installs GnuPG and runs
  `scripts/verify-clearsign.sh` to ensure every committed clear-signed letter
  validates against the trusted fingerprint.
* **`releases-manifest.yml`** (push to `letter/**`, `keys/**`, or manual):
  executes the full release pipeline (manifest generation, metadata refresh, and
  docs sync) and auto-commits the results. It rebases onto the tip of the target
  branch and waits for GitHub Pages deployments to finish before pushing.
* **`ots-stamp-letter-asc.yml`** (push to `letter/*.asc`): installs the
  OpenTimestamps client, stamps any new signatures to produce matching `.ots`
  proofs, waits for GitHub Pages to be idle, and commits the generated proofs.
* **`ots-verify-upgrade.yml`** (manual): finds the freshest proof via
  `find_latest_ots.py`, shows `ots info/verify` output, attempts an upgrade, and
  commits the updated proof when changes are detected.
* **`sync-readme-fingerprint.yml`** (push to `keys/FINGERPRINT` or manual):
  normalizes the fingerprint string and patches `README.md` so the published
  trust anchor always mirrors the canonical value.

These workflows share a concurrency group (`letter-artifacts-${{ github.ref }}`)
so that only one automation run mutates release artifacts for a given branch at
a time. Several jobs call `.github/scripts/wait_for_pages_idle.sh` to avoid
interrupting GitHub Pages deployments when they push their commits.
