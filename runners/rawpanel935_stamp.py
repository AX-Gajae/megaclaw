# -*- coding: utf-8 -*-
"""팔 935 — 사전등록의 **시각 증거**를 굳힌다. 🔴 `os.utime` 을 안 쓴다.

sha256 과 mtime 을 `runners/out935_prereg_stamp.json` 에 박는다. 측정 러너는 이 파일의
sha256 을 **다시 계산해서** 대조한다(손 전사 금지 · 배선 W11).

사용: python3 runners/rawpanel935_stamp.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out935_prereg_stamp.json"
FILES = [
    "docs/prereg_935_rawpanel.md",
    "state/rawpanel935.py",
    "runners/rawpanel935_oracle.py",
    "runners/rawpanel935_stamp.py",
    "runners/out935_oracle.json",
]


def main() -> None:
    rec = {}
    for f in FILES:
        p = ROOT / f
        b = p.read_bytes()
        rec[f] = {
            "sha256": hashlib.sha256(b).hexdigest(),
            "바이트": len(b),
            "mtime(UTC)": dt.datetime.fromtimestamp(
                p.stat().st_mtime, dt.timezone.utc).isoformat(),
        }
    out = {
        "무엇": "935 사전등록의 시각 증거 — 🔴 200뽑기 측정 **전에** 굳힌다",
        "사전등록": "docs/prereg_935_rawpanel.md",
        "파일별 sha256·mtime": rec,
        "이 stamp 를 쓴 시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(),
        "🔴 os.utime 을 썼나": False,
        "🔴 이번에 새로 넘는 것": [
            "🔴 **커밋을 둘로 갈랐다** — 오라클 부속(out935_oracle.json)은 **앞선 커밋**에, "
            "사전등록·스탬프·원장만 담은 커밋은 그 뒤에. 933 의 경미 m8(「사전등록만 담은 커밋」이라 "
            "적고 결과 파일을 같이 넣었다)을 안 되풀이한다",
            "🔴 판정 문턱의 k 동치 조건을 **러너가 계산한다**(933 자기적발 ① — 손으로 적어 틀렸다)",
        ],
        "🔴 그래도 못 넘는 것": [
            "커밋 시각도 손으로 고칠 수 있다 — 증언의 세기는 '위조 비용'이지 '불가능'이 아니다",
            "🔴 오라클 부속 러너는 사전등록보다 **먼저** 돌았다(사전등록 §0-나). 귀무를 한 번도 안 "
            "만들지만 순서 자체는 이 사이클의 약점이다",
            "🔴 티처 #76 C5 가 원판의 진짜 개선 0.7545204330866538 · 40뽑기 k=0 · 효과 648분을 "
            "이미 냈고 나는 그것을 읽고 이 사전등록을 썼다 — '결과를 모르는 사전등록'이 아니다(§0-가)",
            "daily.npz 를 만드는 러너가 저장소에 없다 — sha 대조는 자기 자신하고만 된다(4사이클 연속)",
        ],
        "🔴 측정에 쓸 러너(이 시점에 아직 없다)": "runners/rawpanel935_run.py",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
