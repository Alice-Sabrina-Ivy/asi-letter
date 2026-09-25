#!/usr/bin/env bash
# Guard: every path the release pipeline dirtied must appear in the canonical
# generated-paths list.
#
# Run this straight after `scripts/release.py` in any workflow that commits
# regenerated artifacts. If a pipeline stage starts writing a new file and
# nobody adds it to generated_paths.sh, the commit step would silently drop it
# and the published copy would freeze at an old release while the rest moved on.
# That failure is invisible -- `release.py --check` passes, because the pipeline
# just regenerated everything in the same job. This turns it into a loud one.
#
# Usage: assert_generated_paths.sh [--baseline FILE] [extra-allowed-pattern ...]
#
# --baseline takes a snapshot of `git status --porcelain --untracked-files=all`
# captured BEFORE the pipeline ran. Paths already dirty then were not written by
# the pipeline (a new letter/*.md the author added, say) and are ignored, so the
# check reflects only what the pipeline itself produced.
#
# Extra patterns cover paths a workflow legitimately dirties outside the
# pipeline -- release.yml, for instance, has already stamped or upgraded a
# letter/*.ots proof by the time this runs.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

baseline_file=""
if [[ "${1:-}" == "--baseline" ]]; then
  baseline_file="${2:?--baseline requires a file path}"
  shift 2
  # A missing baseline used to be skipped silently, so a workflow that lost its
  # snapshot step kept "passing" this guard while the pipeline no longer ran.
  if [[ ! -f "$baseline_file" ]]; then
    echo "ERROR: baseline snapshot '$baseline_file' does not exist; the snapshot step must run before release.py." >&2
    exit 1
  fi
fi

known_raw="$("${repo_root}/.github/scripts/generated_paths.sh")"
read -r -a known <<< "$known_raw"
# Caller-supplied allowances are appended to the canonical list.
known+=("$@")

# Paths already dirty before the pipeline ran are not the pipeline's doing.
declare -A preexisting=()
if [[ -n "$baseline_file" && -f "$baseline_file" ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    preexisting["${line:3}"]=1
  done < "$baseline_file"
fi

# Collect dirty paths (modified, added, deleted, untracked). -z keeps paths with
# spaces or non-ASCII intact; porcelain v1 status codes are the first 3 columns.
dirty=()
while IFS= read -r -d '' entry; do
  path="${entry:3}"
  [[ -n "${preexisting[$path]:-}" ]] && continue
  dirty+=("$path")
done < <(git status --porcelain -z --untracked-files=all)

if [[ ${#dirty[@]} -eq 0 ]]; then
  echo "No files changed by the release pipeline."
  exit 0
fi

unexpected=()
for path in "${dirty[@]}"; do
  covered=0
  for candidate in "${known[@]}"; do
    if [[ "$path" == "$candidate" ]]; then
      covered=1
      break
    fi
    # Workflows may also pass globs (e.g. letter/*.ots) through this list.
    # shellcheck disable=SC2053
    if [[ "$path" == $candidate ]]; then
      covered=1
      break
    fi
  done
  if [[ $covered -eq 0 ]]; then
    unexpected+=("$path")
  fi
done

echo "Paths changed by the release pipeline:"
printf '  %s\n' "${dirty[@]}"

if [[ ${#unexpected[@]} -gt 0 ]]; then
  echo
  echo "ERROR: the release pipeline wrote path(s) missing from the canonical list:" >&2
  printf '  %s\n' "${unexpected[@]}" >&2
  echo >&2
  echo "Add them to .github/scripts/generated_paths.sh, or the commit step will" >&2
  echo "silently drop them and the published copies will go stale." >&2
  exit 1
fi

echo
echo "All changed paths are covered by generated_paths.sh."
