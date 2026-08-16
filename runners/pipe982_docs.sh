#!/bin/zsh
# 🔴🔴 982 — **문서·원장·인계카드 커밋을 fail-closed 로 묶는다**(981 R1 을 잇는다).
#   씀: pipe982_docs.sh <메시지파일> <경로...>
# `note982_gen.py --stage verify` 가 0 이 아니면 **커밋을 안 한다.**
set -e
ROOT=/Users/ax/world_model
cd "$ROOT"
echo "── 규칙 D 관문: 치환표 ↔ 판정문·카드·인계카드·원장 대조 ──"
python3 runners/note982_gen.py --stage verify
echo "── 통과 · 커밋한다 ──"
zsh runners/pipe982.sh "$@"
