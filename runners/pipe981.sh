#!/bin/zsh
# 981 배관 커밋기 — checkout 없이 가지에 쓴다 (루프.md 규칙 A).
#   씀: pipe981.sh <메시지파일> <경로1> [경로2 ...]
# 🔴 HEAD 는 언제나 main 에 남는다. 가지 ref 만 움직인다.
set -e
ROOT=/Users/ax/world_model
BR=refs/heads/note/981-ruler-mechanical-target-grid
MSGF="$1"; shift
cd "$ROOT"
PARENT=$(git rev-parse --verify -q "$BR" || git rev-parse --verify refs/heads/main)
TMPIDX=$(mktemp /tmp/981idx.XXXXXX)
rm -f "$TMPIDX"
export GIT_INDEX_FILE="$TMPIDX"
git read-tree "$PARENT"
for p in "$@"; do
  if [ -f "$p" ]; then
    BLOB=$(git hash-object -w -- "$p")
    MODE=$(test -x "$p" && echo 100755 || echo 100644)
    git update-index --add --cacheinfo $MODE,$BLOB,"$p"
  else
    git update-index --force-remove -- "$p" 2>/dev/null || true
  fi
done
TREE=$(git write-tree)
NEW=$(git commit-tree "$TREE" -p "$PARENT" -F "$MSGF")
git update-ref "$BR" "$NEW" "$PARENT" 2>/dev/null || git update-ref "$BR" "$NEW"
rm -f "$TMPIDX"
echo "$NEW"
