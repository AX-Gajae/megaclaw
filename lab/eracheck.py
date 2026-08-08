# -*- coding: utf-8 -*-
# era manifest comparator(노트 871 · 티처 #36 P1) — '다음 시대 단절은 5분 진단'의 소비 주체.
# 사용: from lab.eracheck import compare; compare(data)  ← 적합류 러너가 적합 전에 부른다.
# 정본: data/lab/era_manifest.json (단일 필자 runners/eramanifest871.py 계열 · 시대 교체 시 새 동결)
import hashlib
import json
from pathlib import Path

import numpy as np

CANON = Path("/Users/ax/world_model/data/lab/era_manifest.json")


def fingerprint(data) -> dict:
    """도메인별 학습측 재료 지문: 행 · y/A/M 해시. dom[d] = (A, M, y, t)."""
    out = {}
    for dom in sorted(data.dom):
        A, M, y, _t = data.dom[dom]
        h = lambda a: hashlib.sha256(np.round(np.asarray(a, float), 6).tobytes()).hexdigest()[:12]
        out[dom] = {"행": int(len(np.asarray(y))), "y": h(y), "A": h(A), "M": h(M)}
    return out


def compare(data, verbose: bool = True):
    """현 세계 지문 대 정본 — (일치 여부, 불일치 도메인 목록)을 낸다."""
    canon = json.loads(CANON.read_text())["지문"]
    now = fingerprint(data)
    bad = sorted(set(canon) ^ set(now)
                 | {d for d in set(canon) & set(now) if canon[d] != now[d]})
    if verbose:
        print(f"era 대조: {'일치 ' + str(len(now)) + '/' + str(len(canon)) if not bad else '단절 — ' + str(bad)}",
              flush=True)
    return (not bad), bad
