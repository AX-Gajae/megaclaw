# -*- coding: utf-8 -*-
"""팔 918-ㅌ · 0단계 — zip 19개를 **내 파서로 다시** 흘려 읽어 (격자 × 577일) 판을 만든다.

🔴 915 의 `ingest/lifepop915.py` 를 **안 쓴다.** 다른 파서로 세서 같은 수가 나오면
그것이 독립 재계산이다(티처 #71 이 915 에 해 준 것과 같은 형태).

산출물
  runners/out918_build.json                     (저장소 · 계수와 대조만)
  <scratch>/g918/daily.npz                      (저장소 밖 · 값 판)

사용: python3 runners/interval918_build.py
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
from state.interval918 import (DAY0, NDAY, SRC, scan_zip_daily,  # noqa: E402
                               sha256_text)

SCRATCH = Path(os.environ.get(
    "G918_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "g918"
OUT = ROOT / "runners/out918_build.json"
WORKERS = int(os.environ.get("G918_WORKERS", "6"))


def one(name: str) -> dict:
    r = scan_zip_daily(SRC / name)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(SCRATCH / (Path(name).stem + ".month.npz"),
                        V=r.pop("V"), C=r.pop("C"), M=r.pop("M"),
                        grids=np.array(r["격자"]), days=np.array(r["날짜"]))
    r.pop("격자")
    return r


def main() -> None:
    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    zips = sorted(p.name for p in SRC.glob("250_LOCAL_RESD_*.zip"))
    res, fail = {}, {}
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(one, n): n for n in zips}
        for f in as_completed(futs):
            n = futs[f]
            try:
                res[n] = f.result()
            except Exception as e:                       # noqa: BLE001
                fail[n] = f"{type(e).__name__}: {e}"
            print(f"[{time.time()-t0:7.1f}s] {n} done={len(res)} fail={len(fail)}",
                  flush=True)

    # ── 합치기: 8,880 격자 × 577일 ──────────────────────────────────────
    gset: set[str] = set()
    dset: set[str] = set()
    for n in sorted(res):
        z = np.load(SCRATCH / (Path(n).stem + ".month.npz"), allow_pickle=False)
        gset |= set(z["grids"].tolist())
        dset |= set(z["days"].tolist())
    grids = sorted(gset)
    gidx = {g: i for i, g in enumerate(grids)}
    V = np.zeros((len(grids), NDAY), np.float64)
    C = np.zeros((len(grids), NDAY), np.int32)
    M = np.zeros((len(grids), NDAY), np.int32)
    out_of_range = 0
    for n in sorted(res):
        z = np.load(SCRATCH / (Path(n).stem + ".month.npz"), allow_pickle=False)
        gi = np.asarray([gidx[g] for g in z["grids"].tolist()], int)
        for j, ds in enumerate(z["days"].tolist()):
            d = dt.date(int(ds[:4]), int(ds[4:6]), int(ds[6:8]))
            k = (d - DAY0).days
            if not (0 <= k < NDAY):
                out_of_range += 1
                continue
            V[gi, k] += z["V"][:, j]
            C[gi, k] += z["C"][:, j]
            M[gi, k] += z["M"][:, j]
    OBS = C > 0
    np.savez_compressed(SCRATCH / "daily.npz", V=V.astype(np.float64),
                        C=C, M=M, grids=np.array(grids))

    rows = sum(r["행수(직접 셌다)"] for r in res.values())
    masked = sum(r["🔴 마스킹(`*`=≤3) 행"] for r in res.values())
    pairs = sum(r["서로 다른 (행정동,격자) 쌍"] for r in res.values())

    # ── 915 산출물과의 **비트 대조**(같은 zip 을 봤나) ────────────────────
    p915 = ROOT / "runners/out915_count.json"
    cmp915 = {"🔴 못 읽었다": None}
    if p915.exists():
        d915 = json.loads(p915.read_text(encoding="utf-8"))
        per = d915.get("달별", {})
        same = diff = missing = 0
        bad = {}
        for n, r in sorted(res.items()):
            o = per.get(n)
            if o is None:
                missing += 1
                continue
            if o.get("sha256") == r["sha256"]:
                same += 1
            else:
                diff += 1
                bad[n] = {"918": r["sha256"], "915": o.get("sha256")}
        head = d915.get("🔴 분모 딱지 — 다섯이 전부 다른 분모다", {})
        cmp915 = {
            "🔴 zip sha256 비트 대조": {"같다": same, "다르다": diff,
                                 "915 에 없다": missing, "분모(zip)": len(res),
                                 "다른 것": bad or "없다"},
            "행 — 918 이 센 값": rows,
            "행 — 915 가 센 값": head.get("④ 행 = (행정동,격자,날짜,시각) — 🔴 직접 센 전량"),
            "행 일치": rows == head.get("④ 행 = (행정동,격자,날짜,시각) — 🔴 직접 센 전량"),
            "격자 — 918": len(grids),
            "격자 — 915": head.get("① 서로 다른 250m 격자(19개월 합집합)"),
            "격자 일치": len(grids) == head.get("① 서로 다른 250m 격자(19개월 합집합)"),
            "날짜 — 918": len(dset), "날짜 — 915": head.get("② 서로 다른 날짜"),
            "날짜 일치": len(dset) == head.get("② 서로 다른 날짜"),
            "쌍(달별 합) — 918": pairs,
            "쌍(달별 합) — 915": head.get("③ (행정동,격자) 쌍 — 달별 합(합집합 아님)"),
            "쌍 일치": pairs == head.get("③ (행정동,격자) 쌍 — 달별 합(합집합 아님)"),
            "마스킹 — 918": masked,
            "마스킹 — 915": (d915.get("🔴 마스킹") or {}).get("행"),
            "마스킹 일치": masked == (d915.get("🔴 마스킹") or {}).get("행"),
        }

    obs_frac = OBS.mean(axis=1)
    out = {
        "팔": "918-ㅌ", "단계": "0 — 판 만들기(계수와 대조뿐 · 판정 없다)",
        "사전등록": "docs/prereg_918_interval.md",
        "사전등록 mtime(UTC)": dt.datetime.fromtimestamp(
            (ROOT / "docs/prereg_918_interval.md").stat().st_mtime,
            dt.timezone.utc).isoformat(timespec="seconds"),
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                       ("state/interval918.py", "runners/interval918_build.py")},
        "코드 mtime(UTC)": {c: dt.datetime.fromtimestamp(
            (ROOT / c).stat().st_mtime, dt.timezone.utc).isoformat(timespec="seconds")
            for c in ("state/interval918.py", "runners/interval918_build.py")},
        "🔴 분모 딱지(전부 다른 분모다)": {
            "zip 파일 수": len(zips),
            "① 행 = (행정동,격자,날짜,시각)": rows,
            "② 서로 다른 250m 격자": len(grids),
            "③ 서로 다른 날짜(원자료)": len(dset),
            "④ 판의 날짜 축(2025-01-01~2026-07-31)": NDAY,
            "⑤ 칸 = 격자 × 날짜": len(grids) * NDAY,
            "⑥ 행이 있는 칸(관측)": int(OBS.sum()),
            "⑦ 마스킹 행(`*`=≤3)": masked,
            "⑧ (행정동,격자) 쌍 — 달별 합": pairs,
            "🔴 ① 과 ⑤ 는 다르다": "행 단위는 (행정동,격자) 쌍이라 행 > 칸이다",
        },
        "관측률": {
            "칸 관측 비율": float(OBS.mean()),
            "🔴 합이 0 인 관측 칸": int(((C > 0) & (V <= 0)).sum()),
            "🔴 915 식(sum>0) 관측 칸": int((V > 0).sum()),
            "🔴 둘의 차": int(OBS.sum() - (V > 0).sum()),
            "격자 관측률 ≥0.95 인 격자": int((obs_frac >= 0.95).sum()),
            "격자 관측률 중앙값": float(np.median(obs_frac)),
            "격자 관측률 최소": float(obs_frac.min()),
        },
        "🔴 915 와의 대조": cmp915,
        "달별": {n: {k: v for k, v in r.items() if k != "날짜"}
               for n, r in sorted(res.items())},
        "못 센 것": fail or "없다(19개 전량 셌다)",
        "시작 UTC": tstart.isoformat(timespec="seconds"),
        "끝 UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "초": round(time.time() - t0, 1),
        "판 둔 곳(저장소 밖)": str(SCRATCH / "daily.npz"),
        "축 밖 날짜": out_of_range,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out["🔴 분모 딱지(전부 다른 분모다)"], ensure_ascii=False))
    print(json.dumps(cmp915.get("🔴 zip sha256 비트 대조", cmp915), ensure_ascii=False))


if __name__ == "__main__":
    main()
