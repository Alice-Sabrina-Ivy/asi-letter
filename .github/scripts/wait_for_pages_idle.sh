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
TARGET_WORKFLOW="${WAIT_FOR_PAGES_WORKFLOW:-pages build and deployment}"
TARGET_SHA="${WAIT_FOR_PAGES_COMMIT:-${GITHUB_SHA:-}}"
SLEEP_SECONDS="${WAIT_FOR_PAGES_SLEEP:-10}"
TIMEOUT_SECONDS="${WAIT_FOR_PAGES_TIMEOUT:-600}"
CREATION_TIMEOUT="${WAIT_FOR_PAGES_CREATION_TIMEOUT:-120}"
START_TIME="$(date +%s)"

api_request() {
  local url="$1"
  curl -fsSL \
    -H "Authorization: Bearer $GITHUB_TOKEN" \
    -H "Accept: application/vnd.github+json" \
    "$url"
}

TARGET_SEEN=0
TARGET_CREATION_START="$START_TIME"

while true; do
  NOW="$(date +%s)"
  if (( TIMEOUT_SECONDS > 0 )) && (( NOW - START_TIME >= TIMEOUT_SECONDS )); then
    echo "Timed out waiting for GitHub Pages workflow to finish" >&2
    exit 1
  fi

  RESPONSE="$(api_request "https://api.github.com/repos/${OWNER}/${REPO}/actions/runs?per_page=100&branch=${BRANCH}")"
  COUNT="$(echo "$RESPONSE" | jq --arg name "$TARGET_WORKFLOW" '[.workflow_runs[] | select(.name == $name and (.status == "in_progress" or .status == "queued"))] | length')"

  TARGET_DONE=1
  TARGET_STATUS=""
  TARGET_CONCLUSION=""

  if [[ -n "$TARGET_SHA" ]]; then
    TARGET_INFO="$(echo "$RESPONSE" | jq -c --arg name "$TARGET_WORKFLOW" --arg sha "$TARGET_SHA" '[.workflow_runs[] | select(.name == $name and .head_sha == $sha)] | first?')"
    if [[ "$TARGET_INFO" != "null" && -n "$TARGET_INFO" ]]; then
      TARGET_SEEN=1
      TARGET_STATUS="$(echo "$TARGET_INFO" | jq -r '.status')"
      TARGET_CONCLUSION="$(echo "$TARGET_INFO" | jq -r '.conclusion // ""')"
      if [[ "$TARGET_STATUS" != "completed" ]]; then
        TARGET_DONE=0
      fi
    else
      if (( TARGET_SEEN == 0 )); then
        if (( CREATION_TIMEOUT > 0 )) && (( NOW - TARGET_CREATION_START < CREATION_TIMEOUT )); then
          TARGET_DONE=0
        fi
      fi
    fi
  fi

  if [[ "$COUNT" == "0" && "$TARGET_DONE" == "1" ]]; then
    if (( TARGET_SEEN == 1 )) && [[ -n "$TARGET_CONCLUSION" ]]; then
      echo "GitHub Pages run for commit ${TARGET_SHA} finished with conclusion: ${TARGET_CONCLUSION}."
    fi
    echo "GitHub Pages is idle for ${BRANCH}."
    break
  fi

  if [[ "$TARGET_DONE" != "1" ]]; then
    if (( TARGET_SEEN == 1 )); then
      echo "Waiting for GitHub Pages run for commit ${TARGET_SHA} (status: ${TARGET_STATUS:-unknown}) to finish..."
    else
      echo "Waiting for GitHub Pages run for commit ${TARGET_SHA} to appear..."
    fi
  else
    echo "Waiting for ${COUNT} GitHub Pages run(s) targeting ${BRANCH} to complete before committing..."
  fi

  sleep "$SLEEP_SECONDS"
done

