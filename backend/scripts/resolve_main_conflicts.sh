#!/usr/bin/env bash
set -euo pipefail

# Resolves conflicts by keeping current branch (feature/work) changes.
# Usage:
#   bash backend/scripts/resolve_main_conflicts.sh origin/main
# Default target is origin/main.

TARGET_BRANCH="${1:-origin/main}"

CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "Current branch: ${CURRENT_BRANCH}"
echo "Target branch : ${TARGET_BRANCH}"

git fetch --all --prune

echo "Merging ${TARGET_BRANCH} into ${CURRENT_BRANCH} with preference for current branch changes..."
if git merge -X ours "${TARGET_BRANCH}"; then
  echo "Merge completed without unresolved conflicts."
else
  echo "Auto-merge reported conflicts; forcing keep-current-branch versions..."
  git checkout --ours .
  git add -A
  git commit -m "Resolve merge conflicts with ${TARGET_BRANCH} by keeping ${CURRENT_BRANCH} changes"
fi

echo "Done. Review with: git status && git log --oneline -n 5"
