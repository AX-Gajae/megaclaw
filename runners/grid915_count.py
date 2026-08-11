# -*- coding: utf-8 -*-
"""팔 915-ㅋ · 0단계 러너 — zip **19개 전량**을 워커로 나눠 **직접 센다**.

🔴 추정이 아니다. 909 의 「약 1억 4,769만 행」은 **하루 표본 × 577** 이라 조항 60 에 걸린다.
여기서는 19개 zip 을 **전량 흘려 읽어** 센 수만 적는다.

산출물: runners/out915_count.json (저장소) · <scratch>/g915/*.{json,npz} (저장소 밖)
사용: python3 runners/grid915_count.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
from ingest.lifepop915 import SCRATCH, SRC, scan_zip  # noqa: E402

OUT = ROOT / "runners/out915_count.json"
WORKERS = int(os.environ.get("G915_WORKERS", "6"))
LIMIT_SEC = float(os.environ.get("G915_LIMIT_SEC", "2100"))   # 🔴 사전등록 예산 35분


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "🔴 파일 없음"


def one(name: str) -> dict:
    return scan_zip(SRC / name, want_values=True)


def main() -> None:
    t0 = time.time()
    zips = sorted(p.name for p in SRC.glob("250_LOCAL_RESD_*.zip"))
    res: dict[str, dict] = {}
    fail: dict[str, str] = {}
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(one, n): n for n in zips}
        for f in as_completed(futs):
            n = futs[f]
            try:
                res[n] = f.result()
            except Exception as e:                     # noqa: BLE001
                fail[n] = f"{type(e).__name__}: {e}"
            print(f"[{time.time()-t0:7.1f}s] {n} done={len(res)} fail={len(fail)}", flush=True)
            if time.time() - t0 > LIMIT_SEC:
                fail["🔴 예산 초과"] = f"{LIMIT_SEC}s 를 넘겨서 남은 것을 못 셌다"
                break

    grids: set[str] = set()
    days: set[str] = set()
    pairs_sum = 0
    rows = 0
    masked = 0
    per = {}
    for n, r in sorted(res.items()):
        rows += r["행수(직접 셌다)"]
        masked += r["🔴 마스킹(`*`=≤3) 행"]
        pairs_sum += r["서로 다른 (행정동,격자) 쌍"]
        days |= set(r["날짜별 행수"])
        import numpy as np
        z = np.load(SCRATCH / (Path(n).stem + ".npz"), allow_pickle=False)
        grids |= set(z["grids"].tolist())
        per[n] = {k: r[k] for k in ("바이트", "sha256", "CSV 수", "포장", "열 수",
                                    "행수(직접 셌다)", "일수", "기간",
                                    "하루 행수 최소/최대", "서로 다른 행정동코드",
                                    "서로 다른 250M격자", "서로 다른 (행정동,격자) 쌍",
                                    "🔴 마스킹(`*`=≤3) 행", "마스킹 비율", "초")}

    out = {
        "팔": "915-ㅋ", "단계": "0 — 계수(직접 셌다 · 추정 아님)",
        "🔴 자": "뗐다 — 계수만. 판정도 효과도 없다",
        "사전등록": "docs/prereg_915_grid.md",
        "코드 sha256": {c: sha16(ROOT / c) for c in
                       ("ingest/lifepop915.py", "runners/grid915_count.py")},
        "🔴 분모 딱지 — 다섯이 전부 다른 분모다": {
            "zip 파일 수": len(zips),
            "zip 바이트 합": sum((SRC / n).stat().st_size for n in zips),
            "① 서로 다른 250m 격자(19개월 합집합)": len(grids),
            "② 서로 다른 날짜": len(days),
            "③ (행정동,격자) 쌍 — 달별 합(합집합 아님)": pairs_sum,
            "④ 행 = (행정동,격자,날짜,시각) — 🔴 직접 센 전량": rows,
            "⑤ 팝업이 붙는 격자 수": "🔴 1단계(runners/grid915_link.py)가 센다 — 여기 수와 섞지 마라",
        },
        "🔴 마스킹": {"행": masked, "비율": round(masked / rows, 6) if rows else None,
                   "뜻": "`*` = 집계 3명 이하라 가렸다 — 「0 이었다」가 아니다. 값 추출에서 0 으로 접었다"},
        "🔴 909 의 추정과 대조": {
            "909 추정": 147_690_000,
            "내가 센 수": rows,
            "차이": rows - 147_690_000 if rows else None,
            "왜 대조하나": "909 는 하루 표본 255,967 × 577 이라 조항 60 에 걸린다. 위 수는 전량 계수다"},
        "달별": per,
        "못 센 것": fail or "없다(19개 전량 셌다)",
        "초": round(time.time() - t0, 1),
        "끝 UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "값 텐서 둔 곳(저장소 밖)": str(SCRATCH),
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["🔴 분모 딱지 — 다섯이 전부 다른 분모다"], ensure_ascii=False))


if __name__ == "__main__":
    main()
