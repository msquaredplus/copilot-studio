#!/usr/bin/env bash
# Run the Copilot Studio pipeline locally.
# Prerequisites: `claude` (logged in) + `gh` (logged in)
# Usage: ./run-local.sh <issue-number>

set -euo pipefail

ISSUE_NUMBER="${1:?Usage: ./run-local.sh <issue-number>}"
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

echo "[local] Fetching issue #$ISSUE_NUMBER from $REPO..."

ISSUE_JSON=$(gh issue view "$ISSUE_NUMBER" --json number,title,body,comments)
ISSUE_TITLE=$(echo "$ISSUE_JSON" | jq -r '.title')
ISSUE_BODY=$(echo "$ISSUE_JSON" | jq -r '.body')
ISSUE_COMMENTS=$(echo "$ISSUE_JSON" | jq -r \
  '[.comments[] | select(.author.login != "github-actions[bot]") | .body] | join("\n---\n")')

echo "[local] Issue: $ISSUE_TITLE"
echo "[local] Starting pipeline..."

cd "$(dirname "$0")"
npm install --prefix scripts --silent

ISSUE_NUMBER="$ISSUE_NUMBER" \
ISSUE_TITLE="$ISSUE_TITLE" \
ISSUE_BODY="$ISSUE_BODY" \
ISSUE_COMMENTS="$ISSUE_COMMENTS" \
GITHUB_TOKEN="$(gh auth token)" \
REPO="$REPO" \
CLAUDE_BIN="claude" \
  node scripts/run-pipeline.js
