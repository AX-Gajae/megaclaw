# -*- coding: utf-8 -*-
# 아이돌 엔티티 키 v3 — entity862.ent_key_v3 의 동결 사본 이식(티처 #33 P1ⓓ · 노트 868).
# entity862.py 는 main 가드가 없어 import = 측정 재실행 — 이 모듈이 유일한 임포트 지점이다.
import json
import re
from pathlib import Path

V3 = json.load(open(Path("/Users/ax/world_model") / "data/lab/idol_group_alias_v3.json"))
ROMA = V3["그룹 로마자 별칭"]


def norm_flat(s):
    return re.sub(r"[^0-9a-z가-힣]+", "", str(s or "").casefold())


def ent_key_v3(g):
    """v3 매처(동결): ①괄호 안 한글 우선 ②전체 정규형 ③로마자 별칭."""
    s = str(g or "").strip()
    if not s:
        return None
    m = re.search(r"[\(（]([^)）]*[가-힣][^)）]*)[\)）]", s)
    if m:
        return norm_flat(m.group(1))
    n = norm_flat(s)
    return ROMA.get(n, n)
