# -*- coding: utf-8 -*-
"""팔 937 — 사전등록의 **시각 증거**를 굳힌다. 🔴 `os.utime` 을 안 쓴다.

sha256 과 mtime 을 `runners/out937_prereg_stamp.json` 에 박는다. 측정 러너는 이 파일의
sha256 을 **다시 계산해서** 대조한다(손 전사 금지).

🔴 이 스탬프를 쓰는 시점에 **측정 러너(`runners/repair937_run.py`)는 아직 없다.**

사용: python3 runners/repair937_stamp.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out937_prereg_stamp.json"
FILES = [
    "docs/prereg_937_repair.md",
    "runners/repair937_stamp.py",
]
#: 🔴 A 가 「같은 코드로 다시 돌렸다」고 말할 수 있으려면 이 둘이 안 바뀌어야 한다
READ_ONLY = [
    "runners/interval918_build.py",
    "state/interval918.py",
    "runners/out918_build.json",
    "runners/out935_rawpanel.json",
    "runners/out933_calpanel.json",
    "runners/out936_teacher.json",
]


def _rec(f: str) -> dict:
    p = ROOT / f
    b = p.read_bytes()
    return {"sha256": hashlib.sha256(b).hexdigest(), "바이트": len(b),
            "mtime(UTC)": dt.datetime.fromtimestamp(
                p.stat().st_mtime, dt.timezone.utc).isoformat()}


def main() -> None:
    out = {
        "무엇": "937 사전등록의 시각 증거 — 🔴 측정 **전에** 굳힌다",
        "사전등록": "docs/prereg_937_repair.md",
        "파일별 sha256·mtime": {f: _rec(f) for f in FILES},
        "🔴 남의 파일(읽기만 · 측정 뒤 대조한다)": {f: _rec(f) for f in READ_ONLY},
        "🔴 대조할 daily.npz 의 sha256(사전등록 §3-A 가 박은 값)":
            "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2",
        "이 stamp 를 쓴 시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(),
        "🔴 os.utime 을 썼나": False,
        "🔴 이번에 새로 넘는 것": [
            "🔴 **사전등록 전용 커밋이 세 사이클 연속**이다(935 사전등록 → 935 판정 → 이것). "
            "이 커밋에는 측정 러너도 결과도 없다",
            "🔴 **남의 파일의 sha 도 함께 박는다** — 「같은 코드로 다시 돌렸다」를 "
            "측정 뒤에 **기계가** 대조할 수 있게(사전등록 §4-1)",
            "🔴 **판정 규칙이 「도피구 없이」 네 갈래로 미리 갈려 있다**(§3-A 의 A1·A2 표)",
        ],
        "🔴 그래도 못 넘는 것": [
            "커밋 시각도 손으로 고칠 수 있다 — 증언의 세기는 '위조 비용'이지 '불가능'이 아니다",
            "🔴 티처 #77 이 A·C·D 의 답의 상당 부분을 **이미 냈고 나는 그것을 읽고 썼다** "
            "(사전등록 §0-가). '결과를 모르는 사전등록'이 아니다",
            "🔴 A 의 도구 성질(numpy 가 zip mtime 을 1980-01-01 로 고정한다)을 "
            "**사전등록 전에** 확인했다(§0-나). 대상의 측정은 아니지만 순서는 이 사이클의 약점이다",
        ],
        "🔴 측정에 쓸 러너(이 시점에 아직 없다)": "runners/repair937_run.py",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
