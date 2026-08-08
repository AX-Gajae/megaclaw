# -*- coding: utf-8 -*-
# 노트 877 — 겹침의 눈금(IP 단위·행 기준) 전행 재판정 + R/S(사전등록 '877' · 티처 #42 제안 1)
import datetime as dt
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402
from lab.decay import AXD, AX  # noqa: E402
from lab.titlekey import norm, keys_of  # noqa: E402
from lab.pairboot import franchise_key  # noqa: E402

ROOT = Path("/Users/ax/world_model")


def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0]) if ok.sum() >= 5 else np.nan


def main():
    t0 = time.time()
    data = sideaudit.champion_data()
    gold = json.loads((ROOT / "data/state/anime_match.json").read_text())
    rrec = json.loads((ROOT / "data/state/wanime_records.json").read_text())
    al2w = {}
    for k, v in rrec.items():
        al2w.setdefault(str(v.get("media_id")), k)
    al_cnt = Counter(str(g.get("al_id")) for g in gold.values())

    r_an = json.loads((AXD / f"{AX['애니']}.json").read_text())
    an_items = list(r_an.items())
    tl = [norm(v.get("name") or v.get("title") or "") for _k, v in an_items]
    yr = np.asarray(data.yr["애니"], float)
    y_all = np.asarray(data.dom["애니"][2], float)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)

    # 파트너 학습 키 → (도메인, 제목) 역맵
    src_map = {}
    for dkey in ("세계애니", "만화", "웹툰"):
        rr = json.loads((AXD / f"{AX[dkey]}.json").read_text())
        yrx = np.asarray(data.yr[dkey], float); yx = np.asarray(data.dom[dkey][2], float)
        ktrx = np.isfinite(yrx) & (yrx < 2025.0) & np.isfinite(yx)
        for (rid, rec), k in zip(rr.items(), ktrx):
            if not k:
                continue
            t = rec.get("name") or rec.get("title") or ""
            keys = ({norm(t)} - {""})
            if dkey == "세계애니" and rid in rrec:
                keys |= keys_of(rrec[rid])
            for kk in keys:
                src_map.setdefault(kk, []).append((dkey, t, rid))

    # 876 합집합 21 + 행 70(#42 복원)
    base = json.load(open(ROOT / "runners/out876_goldaudit.json"))
    rows_876 = set(base["합집합 행"]) | {70}
    o876 = base["O"]
    # 행별 레인·상대 근거 조립
    gold_row_map = {}
    for an_id, g in gold.items():
        wid = al2w.get(str(g.get("al_id")))
        i = {a: j for j, (a, _v) in enumerate(an_items)}.get(an_id)
        if wid and i is not None and kho[i]:
            gold_row_map.setdefault(int(i), []).append(
                {"wid": wid, "AniList": rrec.get(wid, {}).get("title"),
                 "sd": rrec.get(wid, {}).get("start_date"), "al_cnt": al_cnt[str(g.get("al_id"))]})
    v2_eye = {e["행"]: e for e in o876["v2 신규(눈 검증 대상)"]}

    table = []
    for i in sorted(rows_876):
        lanes, mates = [], []
        if tl[i] and tl[i] in src_map:
            lanes.append("v1")
            mates += [{"도메인": d, "제목": t} for d, t, _r in src_map[tl[i]][:4]]
        if i in gold_row_map:
            lanes.append("골드")
            mates += gold_row_map[i]
        if i in v2_eye:
            lanes.append("v2")
            mates.append({"AniList": v2_eye[i]["AniList"], "wid": v2_eye[i]["wid"]})
        table.append({"행": i, "라프텔": an_items[i][1].get("title"),
                      "레인": lanes, "상대": mates, "IP 판정": None})

    # ── IP 눈 검증(내 판정을 코드 밖에서 채워 넣지 않는다 — 규칙 기반 + 예외 목록) ──
    # 규칙: 같은 norm 키(v1) = 같은 IP(titlekey 가 시즌을 접음) · 골드/v2 는 상대 제목의
    # franchise_key(제목 도메인 자) 가 라프텔 franchise_key 와 일치하면 같은 IP.
    # 규칙이 못 가르는 행은 '수동' 필드로 남겨 노트에서 눈 판정을 병기한다.
    manual = {}
    for row in table:
        i = row["행"]
        lf_fk = franchise_key(row["라프텔"] or "")
        if "v1" in row["레인"]:
            row["IP 판정"] = "통과(v1 — 동일 정규 키)"
            continue
        mate_fks = [franchise_key(m.get("AniList") or "") for m in row["상대"] if m.get("AniList")]
        same = any(fk and fk == lf_fk for fk in mate_fks)
        if same:
            row["IP 판정"] = "통과(franchise_key 일치)"
        else:
            row["IP 판정"] = "수동(로마자/한글 자 불일치 — 눈 판정 필요)"
            manual[i] = {"라프텔": row["라프텔"], "상대": row["상대"]}

    n_pass_auto = sum(1 for r in table if r["IP 판정"].startswith("통과"))
    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
           "눈금": "IP 단위 · 행 기준(사전등록 877 — 이후 불변)",
           "전행 표": table, "자동 통과": n_pass_auto, "수동 대상": manual,
           "골드 교정 목록(사람 게이트)": {
               "중복 al_id": {al: c for al, c in al_cnt.items() if c > 1},
               "단일 부챗살(시즌 오매칭 · cnt=1)": [
                   {"an": "AN-44283", "lf": "【최애의 아이】 3기", "골드 al": "150672(1기)",
                    "올바른 후보": "WA-182587(3rd Season · 2026-01-14 · 유보측)"},
                   {"an": "AN-43450", "lf": "불멸의 그대에게 Season 3", "골드 al": "114535(1기)",
                    "올바른 후보": "WA-162669(S3 · 2025-10-04 · 유보측)"}]}}
    with open(ROOT / "runners/out877_ipmap.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({"자동 통과": n_pass_auto, "수동": list(manual)}, ensure_ascii=False), flush=True)
    print(f"수동 대상 상세: {json.dumps(manual, ensure_ascii=False)[:1500]}", flush=True)


if __name__ == "__main__":
    main()
