# .github/scripts/ — Codex Guide

## Directory purpose
- Helper utilities used by `release.yml` to decide what a release commit contains and to prove nothing was left out.

## File map (every tracked item)
| filename | what it does | important invariants / gotchas | how it’s used |
| --- | --- | --- | --- |
| `AGENTS.md` | This guide. | Keep aligned with helper behavior. | Reference for workflow authors. |
| `generated_paths.sh` | Prints, on ONE line, every path written by `scripts/release.py`. | Single source of truth for the commit step. Must stay one line (`read -r -a` stops at the first newline). Keep in sync with the stage list in `release.py`. `--stageable` drops absent, untracked paths so `git add` can't abort. | `release.yml` build job. |
| `assert_generated_paths.sh` | Fails CI if the pipeline wrote a path missing from `generated_paths.sh`. | `--baseline <file>` is a pre-run `git status --porcelain` snapshot; a missing baseline file is now an error (it used to be skipped silently). Extra allowed patterns follow, e.g. `'letter/*.ots'`. | Right after `release.py` in `release.yml`. |

## Codex operating guidance
- Edit policy: preserve output formats and keep scripts executable.
- Validation: run `bash .github/scripts/assert_generated_paths.sh --baseline <snapshot>` after `python3 scripts/release.py`.
