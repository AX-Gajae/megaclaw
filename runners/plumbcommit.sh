#!/bin/zsh
# 🔴 **공유** 배관 커밋기 — 규칙 A(배관만 · checkout 금지).
#
# 975 까지는 사이클마다 `plumbcommit9NN.sh` 를 새로 만들었다(일회용 파일).
# 976 이 **하나로 합친다** — `runners/ledger.py` 와 같은 이유다.
#
# 씀:  runners/plumbcommit.sh <branch> <msgfile> <path> [<path> ...]
set -e
ROOT=${WM_ROOT:-/Users/ax/world_model}
BR=$1; MSG=$2; shift 2
export GIT_INDEX_FILE=$(mktemp /tmp/wmidx.XXXXXX)
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
