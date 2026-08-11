# -*- coding: utf-8 -*-
"""팔 940 — 사전등록의 **시각 증거**를 굳힌다. 🔴 `os.utime` 을 안 쓴다.

sha256 과 mtime 을 `runners/out940_prereg_stamp.json` 에 박는다. 측정 러너는 이 파일의
sha256 을 **다시 계산해서** 대조한다(손 전사 금지).

🔴 이 스탬프를 쓰는 시점에 **측정 러너(`runners/ratio940_run.py`)도 `state/ratio940.py` 도
게이트(`runners/gate940_wiring.py`)도 아직 없다.**

사용: python3 runners/ratio940_stamp.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out940_prereg_stamp.json"
FILES = [
    "docs/prereg_940_ratio.md",
    "runners/ratio940_stamp.py",
]
#: 🔴 이 사이클은 **남의 산출물을 읽기만** 한다. 측정 뒤에 기계가 대조한다
READ_ONLY = [
    "runners/out922_permfix.json",
    "runners/out925_gapsplit.json",
    "runners/out933_calpanel.json",
    "runners/out935_rawpanel.json",
    "runners/out937_repair.json",
    "runners/out939_threshold.json",
    "state/perm922.py",
    "state/gap925.py",
    "state/gate939.py",
    "runners/perm922_run.py",
]


def _rec(f: str) -> dict:
    p = ROOT / f
    b = p.read_bytes()
    return {"sha256": hashlib.sha256(b).hexdigest(), "바이트": len(b),
            "mtime(UTC)": dt.datetime.fromtimestamp(
                p.stat().st_mtime, dt.timezone.utc).isoformat()}


def main() -> None:
    rev = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    out = {
        "무엇": "940 사전등록의 시각 증거 — 🔴 측정 **전에** 굳힌다",
        "사전등록": "docs/prereg_940_ratio.md",
        "🔴 이 stamp 를 쓸 때의 HEAD(계수의 기준 트리 후보)": rev,
        "파일별 sha256·mtime": {f: _rec(f) for f in FILES},
        "🔴 남의 파일(읽기만 · 측정 뒤 대조한다)": {f: _rec(f) for f in READ_ONLY},
        "이 stamp 를 쓴 시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(),
        "🔴 os.utime 을 썼나": False,
        "🔴 사전등록이 박은 공식(손 전사 금지 · 러너가 다시 계산한다)":
            "r = m · L_used · cr / G · m = max|기후값 MAE 상대차| · "
            "L_used = max(1.0, 전달률 BCa 상한) · G = min_i(R − y_i) · cr = 진짜 기준 팔 MAE",
        "🔴 사전등록이 박은 판정규칙(§4)":
            "배선이 붙었다 ⟺ ① 새 자를 쓰는 실행 경로가 있고 ② 그 경로에서 값을 바꾸면 "
            "산출물이 바뀌고 ③ 새 소비자가 생겼을 때 붉어지는 기계 검사가 있다 — 셋 다. "
            "하나라도 아니면 명문화하고 어느 조건이 왜 안 됐는지 적는다. "
            "둘 중 어느 쪽으로도 안 떨어지면 「못 정했다」로 적는다",
        "🔴 미리 박은 예측 여덟(§4)": {
            "P1": "COMPARABLE_REL 을 import 하는 .py 는 3~6개",
            "P2": "관문 결과로 실제로 분기하는 파일은 runners/perm922_run.py 하나뿐",
            "P3": "§B-ㄴ(상수만 주입)에서 판정문이 **안 바뀐다**(기본 인자 동결)",
            "P4": "§B-ㄴ 에서 산출물의 문턱 필드는 1e-9 로 바뀐다(적히는 수 ≠ 쓰이는 수)",
            "P5": "§B-ㄱ 이 옛 산출물의 상대차·판정문을 비트로 재현한다",
            "P6": "922 N1 의 상대차는 0.05 를 넘는다",
            "P7": "새 r 은 939 의 r 과 935 판① 에서만 같고 ②·진단③ 에서는 다르다",
            "P8": "k·p 는 한 팔도 안 바뀐다",
        },
        "🔴 이번에 새로 넘는 것": [
            "🔴 **사전등록 전용 커밋이 여섯 사이클 연속**(933 → 935 → 937 → 939 → 이것). "
            "이 커밋에는 측정 러너도 새 모듈도 결과도 없다",
            "🔴 **신고 양식 자체를 바꾸면서 「무엇을 잃는지」를 셋으로 미리 적었다**(§1) — "
            "규약을 바꾼 앞 사이클들(937·939)은 잃는 것을 안 적었다",
            "🔴 **「지울까 남길까」를 값 보기 전에 정했다**(§4 끝) — 남긴다 · 이유와 잃는 것까지",
            "🔴 **주입 시험을 사전등록에 표로 박았다**(§B ㄱ·ㄴ·ㄷ) — "
            "「배선이 붙었나」를 말로 답하지 않고 **값을 바꿔 넣어** 답한다",
        ],
        "🔴 그래도 못 넘는 것": [
            "🔴 나는 이미 `perm922_run.py:433` 의 `if not cmp_n2[\"🔴 통과\"]:` 를 **읽었다** — "
            "그래서 P2 는 「모르는 것을 맞히는 예측」이 아니라 **읽은 것을 전수로 확인하는 예측**이다. "
            "P2 가 값을 갖는 자리는 「다른 파일에는 없다」쪽이다",
            "🔴 나는 `perm922_run.py:461` 의 무조건문을 읽어서 **P6 을 거의 안다** — "
            "P6 은 예측이 아니라 **자기 대조**에 가깝다. 그렇게 적어 둔다",
            "🔴 방향의 출처가 또 **티처**다 — ⓪-다 의 자기 물음은 이번에도 0 이고, "
            "그래서 탐색 팔을 아예 안 띄웠다(그것도 0 이다)",
            "🔴 새 양식이 잃는 것 ㄱ(이분법)이 손해인지 이득인지는 **이 사이클이 판정 못 한다**",
        ],
        "🔴 측정에 쓸 것(이 시점에 아직 없다)": [
            "state/ratio940.py", "runners/ratio940_run.py",
            "runners/gate940_wiring.py", "runners/out940_ratio.json",
            "runners/out940_gate.json"],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
