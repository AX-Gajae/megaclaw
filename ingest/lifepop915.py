# -*- coding: utf-8 -*-
"""팔 915-ㅋ · 0단계 — **서울 생활인구 250m zip 19개를 압축을 풀지 않고 전량 흘려 읽는다.**

🔴 규율(사전등록 `docs/prereg_915_grid.md` §2)
  · 압축을 **안 푼다**. `zipfile` 스트리밍만. 디스크에 9GB 를 풀지 않는다.
  · 행 수를 **추정하지 않고 센다**. 표본 하루로 곱하지 않는다(조항 60).
  · 필드는 큰따옴표로 싸여 있고 `행정동코드` 는 오른쪽 공백 패딩(13자)이다. 인코딩 **CP949**.
  · 마스킹 `*` 는 **결측이 아니라 「≤3」**. 0 으로 접되 **건수를 따로 센다**.
  · 🔴 행의 단위는 격자가 아니라 **(행정동, 격자) 쌍**이다(899 §2.2).
    격자 단위 값은 **행정동을 넘어 합산**한다 — 합산했다고 산출물에 적는다.

한 번의 흘려읽기로 **계수**와 **값 추출**을 같이 한다(두 번 읽으면 예산을 넘는다).

산출물(전부 **스크래치패드** · 저장소 밖)
  <scratch>/g915/<zip이름>.json    달별 계수 요약
  <scratch>/g915/<zip이름>.npz     격자 × (날짜,시각) 생활인구합계 · float32

사용: python3 -m ingest.lifepop915 --zip 250_LOCAL_RESD_202601.zip
      python3 runners/grid915_count.py          (19개를 워커로 나눠 돌린다)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
SRC = ROOT / "data/ingest/seoul_lifepop"
SCRATCH = Path(os.environ.get(
    "G915_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "g915"

Q = b'" \t\r\n'          # 큰따옴표 + 공백 패딩을 한 번에 벗긴다
STAR = b"*"


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def scan_zip(zp: Path, want_values: bool = True) -> dict:
    """CSV 를 풀지 않고 읽는다. 필드 0~4(일자·시간·행정동코드·250M격자·생활인구합계)."""
    t0 = dt.datetime.now(dt.timezone.utc)
    rows = 0
    bad = 0
    masked = 0                      # 🔴 `*` = 「≤3 이라 가렸다」 ≠ 「0 이었다」
    nonfinite = 0
    days: dict[bytes, int] = {}
    hours: set[bytes] = set()
    dongs: set[bytes] = set()
    grids: set[bytes] = set()
    pairs: set[tuple[bytes, bytes]] = set()
    headers: set[str] = set()
    agg: dict[bytes, list] = {}
    day_ix: dict[bytes, int] = {}
    vsum = 0.0

    with zipfile.ZipFile(zp) as z:
        members = sorted(n for n in z.namelist() if n.lower().endswith(".csv"))
        for n in members:
            with z.open(n) as f:
                first = True
                for raw in f:
                    if first:
                        first = False
                        headers.add(raw.decode("cp949", "replace").strip().replace('"', ""))
                        continue
                    if not raw.strip():
                        continue
                    p = raw.split(b",", 5)
                    if len(p) < 5:
                        bad += 1
                        continue
                    rows += 1
                    d = p[0].strip(Q)
                    h = p[1].strip(Q)
                    dg = p[2].strip(Q)
                    gd = p[3].strip(Q)
                    days[d] = days.get(d, 0) + 1
                    hours.add(h)
                    dongs.add(dg)
                    grids.add(gd)
                    pairs.add((dg, gd))
                    if not want_values:
                        continue
                    di = day_ix.get(d)
                    if di is None:
                        di = day_ix[d] = len(day_ix)
                    v = p[4].strip(Q)
                    if v == STAR:
                        masked += 1
                        continue                      # 0 으로 접는다(값은 ≤3)
                    try:
                        fv = float(v)
                    except ValueError:
                        nonfinite += 1
                        continue
                    a = agg.get(gd)
                    if a is None:
                        a = agg[gd] = [0.0] * (31 * 24)
                    a[di * 24 + int(h)] += fv
                    vsum += fv

    dayk = sorted(day_ix, key=lambda k: day_ix[k])
    nd = len(dayk)
    gkeys = sorted(grids)
    if want_values:
        M = np.zeros((len(gkeys), nd, 24), np.float32)
        for i, g in enumerate(gkeys):
            a = agg.get(g)
            if a is None:
                continue
            for j, dk in enumerate(dayk):
                di = day_ix[dk]
                M[i, j, :] = a[di * 24:di * 24 + 24]
        SCRATCH.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(SCRATCH / (zp.stem + ".npz"),
                            V=M,
                            grids=np.array([g.decode("cp949") for g in gkeys]),
                            days=np.array([d.decode("ascii") for d in dayk]))

    dd = {k.decode("ascii"): v for k, v in days.items()}
    out = {
        "파일": zp.name, "바이트": zp.stat().st_size, "sha256": sha256(zp),
        "CSV 수": len(members),
        "포장": ("폴더" if any("/" in m for m in members) else "평면"),
        "헤더 가짓수": len(headers),
        "열 수": len(sorted(headers)[0].split(",")) if headers else 0,
        "헤더": sorted(headers)[0].split(",") if headers else [],
        "행수(직접 셌다)": rows, "쪼개기 실패 행": bad,
        "일수": nd, "기간": [min(dd), max(dd)] if dd else None,
        "날짜별 행수": dict(sorted(dd.items())),
        "하루 행수 최소/최대": [min(dd.values()), max(dd.values())] if dd else None,
        "시간 칸": sorted(x.decode("ascii") for x in hours),
        "서로 다른 행정동코드": len(dongs),
        "서로 다른 250M격자": len(grids),
        "서로 다른 (행정동,격자) 쌍": len(pairs),
        "🔴 마스킹(`*`=≤3) 행": masked,
        "마스킹 비율": round(masked / rows, 6) if rows else None,
        "수로 못 읽은 값": nonfinite,
        "합계 총합": vsum,
        "격자 목록(앞 3)": [g.decode("cp949") for g in gkeys[:3]],
        "🔴 격자 단위 값은 행정동을 넘어 합산했다": True,
        "시작 UTC": t0.isoformat(timespec="seconds"),
        "끝 UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "초": round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 1),
    }
    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / (zp.stem + ".json")).write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", required=True)
    ap.add_argument("--novalues", action="store_true")
    a = ap.parse_args()
    r = scan_zip(SRC / a.zip, want_values=not a.novalues)
    print(json.dumps({k: r[k] for k in ("파일", "행수(직접 셌다)", "일수",
                                        "서로 다른 250M격자", "초")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
