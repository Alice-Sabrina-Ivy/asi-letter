# docs/ — Codex Guide

## Directory purpose
- Static site assets for the published ASI Letter page. `index.html` is the rendered site; `letter.md` is a synced copy of the latest signed letter.

## Key workflows/commands
- Refresh content from the newest signed letter: `python3 scripts/sync_docs_with_latest.py` (use `--check` for dry-run).
- Update version markers (title/data attributes/comments) after a new release: `python3 scripts/update_version_metadata.py --check` or without `--check` to rewrite.

## File map
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `index.html` | Static HTML for https://alice-sabrina-ivy.github.io/asi-letter/. Contains styling, CTA links, and release-version markers. | Version markers (`release-version` comment, `data-release-version` attributes, title) must reflect latest release; edited by `update_version_metadata.py`. Avoid manual changes to signed/embedded content without regenerating. | Served as main site; updated via release automation and metadata script. |
| `letter.md` | Markdown copy of the latest signed letter release. | Overwritten by `sync_docs_with_latest.py` from `letter/ASI-Letter-v*.md`; do not hand-edit. | Displayed in docs and used for site content; kept in sync with `letter/` artifacts. |

## Codex operating guidance
- Edit policy: Avoid manual edits to `letter.md` or release markers in `index.html`; prefer running sync/metadata scripts. Layout tweaks in `index.html` are possible but be mindful of version placeholders.
- Validation: `python3 scripts/sync_docs_with_latest.py --check` to detect stale Markdown; `python3 scripts/update_version_metadata.py --check` to confirm markers match `letter/RELEASES.json`.
- Common failure modes: forgetting to update release markers after new manifest; editing `letter.md` directly so it diverges from signed source; breaking CSS/HTML that release automation expects. 

