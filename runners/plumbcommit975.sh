#!/bin/zsh
# 975 --- 규칙 A(배관만 · checkout 금지)로 가지에 커밋한다.
# 씀: plumbcommit975.sh <branch> <msgfile> <path> [<path> ...]
set -e
ROOT=/Users/ax/world_model
BR=$1; MSG=$2; shift 2
export GIT_INDEX_FILE=$(mktemp /tmp/wmidx975.XXXXXX)
rm -f "$GIT_INDEX_FILE"
git -C $ROOT read-tree "$BR"
for p in "$@"; do
  if [ -e "$ROOT/$p" ]; then
    git -C $ROOT -c core.quotePath=false update-index --add -- "$p"
  else
    git -C $ROOT -c core.quotePath=false update-index --force-remove -- "$p"
  fi
done
TREE=$(git -C $ROOT write-tree)
PAR=$(git -C $ROOT rev-parse "$BR")
NEW=$(git -C $ROOT commit-tree "$TREE" -p "$PAR" -F "$MSG")
git -C $ROOT update-ref "refs/heads/${BR#refs/heads/}" "$NEW" "$PAR"
rm -f "$GIT_INDEX_FILE"
echo "$NEW"
