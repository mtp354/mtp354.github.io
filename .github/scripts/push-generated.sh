#!/usr/bin/env bash
set -euo pipefail

branch="${1:?Usage: push-generated.sh BRANCH}"
git check-ref-format "refs/heads/$branch"

for attempt in 1 2 3; do
  git fetch --no-tags origin "refs/heads/$branch"
  if ! git rebase FETCH_HEAD; then
    git rebase --abort
    echo "::error::Generated changes conflict with $branch. Regenerate from the latest branch."
    exit 1
  fi
  if git push origin "HEAD:refs/heads/$branch"; then
    exit 0
  fi
  if [ "$attempt" -lt 3 ]; then
    echo "::warning::Push failed; refreshing $branch before retry $((attempt + 1))."
    sleep "$((attempt * 2))"
  fi
done

echo "::error::Could not publish generated changes after three attempts."
exit 1
