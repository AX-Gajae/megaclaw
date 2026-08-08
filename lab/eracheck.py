# -*- coding: utf-8 -*-
# era manifest comparator(노트 871·872) — '다음 시대 단절은 5분 진단'의 소비 주체.
# 층이 둘이다(노트 872 · 함정 명기): **compare(전층 A/M/y)** 는 챔피언 축 구성 전용 —
# A/M 해시가 extra 축 구성에 종속이라 전역 훅에 쓰면 거짓 단절. **compare_labels(행+y)** 가
# 전역 훅(harness.load 기저 빌드 직후 · 경고형)이고 833 병(도메인 합류·라벨 드리프트)을 잡는다.
# 정본: data/lab/era_manifest.json. **재동결 규약(872)**: 구 정본을 data/lab/eras/era_<시대id>.json
# 으로 이동한 뒤 새 정본을 'x' 로 쓴다(덮어쓰기 금지 — git 과 이중 보존).
import hashlib
import json
from pathlib import Path

import numpy as np

CANON = Path("/Users/ax/world_model/data/lab/era_manifest.json")          # 챔피언 구성 전층(A/M/y)
CANON_BASE = Path("/Users/ax/world_model/data/lab/era_manifest_base.json")  # 기저 라벨 층(훅 전용 — 872)


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


def fingerprint_labels(data) -> dict:
    """라벨 층만(행 + y 해시) — extra 축 구성에 불변."""
    out = {}
    for dom in sorted(data.dom):
        y = np.asarray(data.dom[dom][2], float)
        out[dom] = {"행": int(len(y)),
                    "y": hashlib.sha256(np.round(y, 6).tobytes()).hexdigest()[:12]}
    return out


def compare_labels(data, verbose: bool = False):
    """전역 훅용 — 정본은 **기저 라벨 manifest**(872 반증: 라벨 층도 구성 종속 —
    챔피언 wide/cut 변형이 게임·아이돌·팝업의 행·라벨을 바꾼다. 챔피언 manifest 로
    기저를 대조하면 거짓 단절 3건). 정본 부재 시 무음. 불일치만 출력(경고형)."""
    if not CANON_BASE.exists():
        return True, []
    canon = json.loads(CANON_BASE.read_text())["지문"]
    now = fingerprint_labels(data)
    bad = sorted({d for d in set(canon) ^ set(now)}
                 | {d for d in set(canon) & set(now)
                    if canon[d]["행"] != now[d]["행"] or canon[d]["y"] != now[d]["y"]})
    if bad:
        print(f"⚠ era 라벨 단절 — {bad} (정본 {CANON.name})", flush=True)
    elif verbose:
        print(f"era 라벨 대조: 일치 {len(now)}/{len(canon)}", flush=True)
    return (not bad), bad
