#!/bin/zsh
# 🔴🔴 981 수리 R1 — **문서·원장 커밋을 fail-closed 로 묶는다.**
#   씀: pipe981_docs.sh <메시지파일> <경로...>
# `note981_gen.py --stage verify` 가 0 이 아니면 **커밋을 안 한다.**
# 그러면 「치환표를 다시 지었는데 문서는 1 차판」(980 이 저지른 것)이 원리상 못 커밋된다.
set -e
ROOT=/Users/ax/world_model
cd "$ROOT"
echo "── 규칙 D 관문: 치환표 ↔ 문서·원장 대조 ──"
python3 runners/note981_gen.py --stage verify
echo "── 통과 · 커밋한다 ──"
zsh runners/pipe981.sh "$@"
