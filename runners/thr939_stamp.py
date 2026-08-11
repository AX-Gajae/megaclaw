# -*- coding: utf-8 -*-
"""팔 939 — 사전등록의 **시각 증거**를 굳힌다. 🔴 `os.utime` 을 안 쓴다.

sha256 과 mtime 을 `runners/out939_prereg_stamp.json` 에 박는다. 측정 러너는 이 파일의
sha256 을 **다시 계산해서** 대조한다(손 전사 금지).

🔴 이 스탬프를 쓰는 시점에 **측정 러너(`runners/thr939_run.py`)도 `state/gate939.py` 도 아직 없다.**

사용: python3 runners/thr939_stamp.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out939_prereg_stamp.json"
FILES = [
    "docs/prereg_939_threshold.md",
    "runners/thr939_stamp.py",
]
#: 🔴 이 사이클은 **남의 산출물을 읽기만** 한다. 측정 뒤에 기계가 대조한다
READ_ONLY = [
    "runners/out925_gapsplit.json",
    "runners/out933_calpanel.json",
    "runners/out935_rawpanel.json",
    "runners/out935_addendum.json",
    "runners/out937_repair.json",
    "runners/out938_teacher.json",
    "state/perm922.py",
    "state/gap925.py",
]


def _rec(f: str) -> dict:
    p = ROOT / f
    b = p.read_bytes()
    return {"sha256": hashlib.sha256(b).hexdigest(), "바이트": len(b),
            "mtime(UTC)": dt.datetime.fromtimestamp(
                p.stat().st_mtime, dt.timezone.utc).isoformat()}


def main() -> None:
    out = {
        "무엇": "939 사전등록의 시각 증거 — 🔴 측정 **전에** 굳힌다",
        "사전등록": "docs/prereg_939_threshold.md",
        "파일별 sha256·mtime": {f: _rec(f) for f in FILES},
        "🔴 남의 파일(읽기만 · 측정 뒤 대조한다)": {f: _rec(f) for f in READ_ONLY},
        "이 stamp 를 쓴 시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(),
        "🔴 os.utime 을 썼나": False,
        "🔴 사전등록이 박은 공식(손 전사 금지 · 러너가 다시 계산한다)":
            "T = G / (L_used × cr) · G = min_i(R − y_i) · L_used = max(1.0, BCa 상한) · 정본 팔 = 판①",
        "🔴 이번에 새로 넘는 것": [
            "🔴 **사전등록 전용 커밋이 다섯 사이클 연속**이다(933 → 935 → 937 → 이것). "
            "이 커밋에는 측정 러너도 결과도 없다",
            "🔴 **문턱을 정하는 공식을 값 보기 전에 박았다** — 문턱은 이 저장소가 "
            "「결과 보고 안 고친다」고만 말하고 **한 번도 자료에서 세운 적이 없는** 상수다",
            "🔴 **「못 정했다」로 끝나는 경우를 셋으로 미리 한정했다**(§A-4-2)",
            "🔴 **새 분류 규칙이 동어반복인지를 규칙과 함께 미리 물었다**(§C-2) — "
            "규약 48 이 앓은 병(티처 #78 C1)을 되풀이 안 하려고",
        ],
        "🔴 그래도 못 넘는 것": [
            "🔴 나는 출처 추적 중에 이슈 #175 에서 **진짜 기후값 MAE 12.1284일**을 봤다 — "
            "그래서 T 의 자릿수를 짐작한다(사전등록 §0-2). 막는 것은 공식을 먼저 박는 것뿐이다",
            "🔴 §A 의 자는 **판정 통계량에서 나온다** — 관문이 판정과 독립이 아니다(§E-1)",
            "🔴 G 는 **관측된** 최소 빈틈이라 뽑기 수에 의존한다(§E-2)",
            "방향의 출처가 또 **티처**다 — ⓪ 의 자기 물음은 이번에도 0 이다(§E-4)",
        ],
        "🔴 측정에 쓸 것(이 시점에 아직 없다)": [
            "state/gate939.py", "runners/thr939_run.py", "runners/out939_threshold.json"],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
