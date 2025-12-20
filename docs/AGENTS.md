# docs/ — Codex Guide

## Directory purpose
- Static site assets for the published ASI Letter page. `index.html` renders the site; `letter.md` mirrors the latest signed Markdown release.

## Key workflows/commands
- `python3 scripts/sync_docs_with_latest.py [--check]` — copies newest `letter/ASI-Letter-v*.md` into `docs/letter.md`.
- `python3 scripts/update_version_metadata.py [--check] [targets...]` — refreshes release markers (title/data attributes/comment) in `index.html`.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | This directory guide. | Keep aligned with site asset roles; defer to root policy. | Contributor reference. |
| `index.html` | Static HTML for the public site with release-version markers, CTA links, styling, and Markdown rendering hook. | Markers (`<!-- release-version -->`, `data-release-version`, title) must match latest release; `update_version_metadata.py` rewrites them. Footer status is updated by OTS workflows. Avoid manual drift from automation expectations. | Served as site entrypoint; updated by release/OTS workflows and metadata script. |
| `letter.md` | Markdown copy of the latest signed letter. | Generated/overwritten by `sync_docs_with_latest.py`; keep consistent with `letter/` sources. | Displayed on site; checked by release pipeline for freshness. |

## Codex operating guidance
- Edit policy: Avoid manual edits to generated `letter.md` or release markers in `index.html`; layout/content changes should respect placeholders used by automation.
- Validation: Run `python3 scripts/sync_docs_with_latest.py --check` to detect stale Markdown and `python3 scripts/update_version_metadata.py --check` to confirm version markers.
- Common failure modes: stale version markers after new manifest, editing `letter.md` directly, or altering HTML in ways that break release/OTS automation.
