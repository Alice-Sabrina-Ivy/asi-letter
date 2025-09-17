#!/usr/bin/env bash
# Wait until no GitHub Pages deployment workflow is running for the target branch.
# This avoids the built-in GitHub Pages workflow cancelling in-progress runs when
# a new commit is pushed in quick succession.

set -euo pipefail

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "GITHUB_TOKEN must be provided" >&2
  exit 1
fi

OWNER_REPO="${GITHUB_REPOSITORY:-}"
if [[ -z "$OWNER_REPO" ]]; then
  echo "GITHUB_REPOSITORY is not set" >&2
  exit 1
fi

OWNER="${OWNER_REPO%%/*}"
REPO="${OWNER_REPO##*/}"
BRANCH="${WAIT_FOR_PAGES_BRANCH:-${GITHUB_REF_NAME:-main}}"
SLEEP_SECONDS="${WAIT_FOR_PAGES_SLEEP:-10}"
TIMEOUT_SECONDS="${WAIT_FOR_PAGES_TIMEOUT:-600}"
START_TIME="$(date +%s)"

api_request() {
  local url="$1"
  curl -fsSL \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "$url"
}

while true; do
  NOW="$(date +%s)"
  if (( TIMEOUT_SECONDS > 0 )) && (( NOW - START_TIME >= TIMEOUT_SECONDS )); then
    echo "Timed out waiting for GitHub Pages workflow to finish" >&2
    exit 1
  fi

  RESPONSE="$(api_request "https://api.github.com/repos/${OWNER}/${REPO}/actions/runs?per_page=100&branch=${BRANCH}")"
  COUNT="$(echo "$RESPONSE" | jq '[.workflow_runs[] | select(.name == "pages build and deployment" and (.status == "in_progress" or .status == "queued"))] | length')"

  if [[ "$COUNT" == "0" ]]; then
    echo "GitHub Pages is idle for ${BRANCH}."
    break
  fi

  echo "Waiting for ${COUNT} GitHub Pages run(s) targeting ${BRANCH} to complete before committing..."
  sleep "$SLEEP_SECONDS"
done

