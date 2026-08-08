# -*- coding: utf-8 -*-
"""노트 857 — 봉인 1호 수확 채점기(사전 동결 · 재량 제거).

정본 규칙(seal_2026-08-08.json 동결분)과 annex 1~5 의 보조 자를 **코드로**
조립한다 — 수확 시점에 사람이 절차를 재구성하지 않는다(재량 차단).

    python3 runners/harvest844.py --selftest    # 받아들임 시험(판-내 897 만 · 언제나 허용)
    python3 runners/harvest844.py --harvest     # 2026-09-28 이후에만 실행 허용

규율: 이 파일은 첫 봉인작 개봉(8/11) **전**에 커밋됐다. 이후 수정은
지문 사슬 위반(844 사고 · 티처 #11)이다 — 고치려면 harvest844b 로 새 파일 +
정오 사이드카.
"""
import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
ROOT = Path("/Users/ax/world_model")
KOBIS_DIR = ROOT / "cycle_log/forward/kobis"
HARVEST_NOT_BEFORE = dt.date(2026, 9, 28)
K_WINDOW = 20          # 개봉일 + 0..20 (836)
CENSOR_MIN = 14        # 마지막 관측 < 개봉+14 → 검열 제외 (봉인 동결)
THRESH = 0.2046        # 정본 문턱(불가침)
RHO_REF = 0.4858


def label_from_daily(rows_by_day, title, open_date):
    """836 라벨 규칙: (제목, 개봉일) 매칭 행의 누적관객(셀 5번째) — 창 내 마지막."""
    od = dt.date.fromisoformat(open_date)
    obs = {}
    for day, rows in rows_by_day.items():
        off = (dt.date.fromisoformat(day) - od).days
        if not (0 <= off <= K_WINDOW):
            continue
        for r in rows:
            if r["제목"].strip() == title.strip() and r.get("개봉일") == open_date:
                c = r["숫자 셀(원본 순서)"]
                if len(c) >= 5:
                    obs[off] = c[4]
    if not obs:
        return None, None
    last = max(obs)
    return float(np.log10(max(obs[last], 1))), last


def selftest():
    """받아들임 시험 — 판-내 897 아카이브에서 라벨 규칙 재현(봉인 라벨 무접촉)."""
    B1 = json.load(open(ROOT / "data/ingest/kobis/backfill_2023-01-01_full.json"))
    B2 = json.load(open(ROOT / "data/ingest/kobis/backfill_2026-05-04_90d.json"))
    daily = {**B1, **B2}
    KA = json.load(open(ROOT / "data/state/kobis_axes.json"))
    n_match = n_total = n_censor_calc = 0
    diffs = []
    for kid, row in KA.items():
        y_ref = row["y"]
        y_new, last = label_from_daily(daily, row["name"], row["release_date"])
        if y_new is None:
            continue
        n_total += 1
        if last < CENSOR_MIN:
            n_censor_calc += 1
        if abs(y_new - y_ref) < 1e-9:
            n_match += 1
        else:
            diffs.append((row["name"], y_ref, y_new))
    censor_ref = sum(1 for r in KA.values() if r.get("검열(개봉+14 미달)"))
    out = {"행": n_total, "라벨 일치": n_match, "일치율": round(n_match / max(n_total, 1), 4),
           "검열 재계산": n_censor_calc, "검열 기준(836)": censor_ref,
           "불일치 예": diffs[:5]}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


def harvest(fetch=True):
    if dt.date.today() < HARVEST_NOT_BEFORE:
        raise SystemExit(f"⛔ 수확은 {HARVEST_NOT_BEFORE} 이후 — 오늘 실행 거부(청정 창 보호)")
    from ingest.kobis import fetch_daily

    seal = json.load(open(KOBIS_DIR / "seal_2026-08-08.json"))
    films = seal["작품"]
    # 수확 창 일별 표 수집(소급 fetch — 이미 저장된 날은 재사용)
    days_needed = set()
    for m in films:
        od = dt.date.fromisoformat(m["개봉일"])
        for k in range(0, K_WINDOW + 1):
            days_needed.add((od + dt.timedelta(days=k)).isoformat())
    daily = {}
    cache = ROOT / "data/ingest/kobis"
    for day in sorted(days_needed):
        p = cache / f"{day}.json"
        if p.exists():
            daily[day] = json.loads(p.read_text())["rows"]
        elif fetch:
            daily[day] = fetch_daily(day)
            p.write_text(json.dumps({"date": day, "rows": daily[day]}, ensure_ascii=False, indent=1))
            time.sleep(1.5)

    # 라벨·검열
    labels, censored = {}, []
    for m in films:
        y, last = label_from_daily(daily, m["제목"], m["개봉일"])
        if y is None or last < CENSOR_MIN:
            censored.append(m["제목"])
        else:
            labels[m["code"]] = y
    m_eff = len(labels)

    # 사다리 4팔 + 보조(검열=공동최하위)
    a3 = json.load(open(KOBIS_DIR / "annex3_2026-08-08.json"))
    a4 = json.load(open(KOBIS_DIR / "annex4_2026-08-09.json"))
    a5 = json.load(open(KOBIS_DIR / "annex5_2026-08-08.json"))
    arms = {
        "v1(정본)": {m["code"]: m["예측 순위"] for m in films},
        "v2(재척도)": {r["code"]: r["v2 순위"] for r in a3["봉인 30편 v2 보조 팔"]["예측(자루 평균 순위·v2 축)"]},
        "격리(+3)": {r["code"]: r["격리"] for r in a4["격리 팔(v1 척도 + 회복 3편만)"]["순위"]},
        "v3(+5)": {r["code"]: r["v3 순위"] for r in a5["예측 팔(자루 평균 순위)"]},
    }
    rhos, rhos_aux = {}, {}
    y_min = min(labels.values()) - 1.0 if labels else 0.0
    for arm, ranks in arms.items():
        codes = [c for c in labels if c in ranks]
        if len(codes) >= 3:
            rhos[arm] = round(float(spearmanr([-ranks[c] for c in codes],
                                              [labels[c] for c in codes])[0]), 4)
        codes_all = [m["code"] for m in films if m["code"] in ranks]
        y_aux = [labels.get(c, y_min) for c in codes_all]
        rhos_aux[arm] = round(float(spearmanr([-ranks[c] for c in codes_all], y_aux)[0]), 4)

    # m-적응 밴드 조회(annex1 원 m-표 · annex3 합성 등화 표 — 보조 병기)
    a1 = json.load(open(KOBIS_DIR / "annex_2026-08-08.json"))
    band_m = a1["m-적응 밴드 2σ(부트 B=2000)"].get(str(min(m_eff, 30)))
    comp_iso = a3["합산 σ̄ 조회 표(단조 강제 · annex1 규칙의 σᵢ 는 이제 이 표)"]
    band_comp = comp_iso.get(str(min((k for k in map(int, comp_iso) if k >= min(m_eff, 30)),
                                     default=30)))

    rho_v1 = rhos.get("v1(정본)")
    if m_eff < 10:
        verdict = f"보류 — 유효 {m_eff} < 10(동결 규칙)"
    elif rho_v1 is not None and rho_v1 >= THRESH:
        verdict = (f"총붕괴 아님 — ρ_v1 {rho_v1} ≥ 문턱 {THRESH}(정본). "
                   f"'전향 재현' 상표는 누적 유효 ≥60 부터(annex1 합산 규칙)")
    else:
        verdict = (f"결측 조정 후 재판정 — ρ_v1 {rho_v1} < {THRESH}. "
                   f"annex4 정합 기준 0.2101±0.045 대비·사다리 몫 분해로 원인 귀속(드리프트 선언은 그 후)")

    out = {"유효": m_eff, "검열": censored, "사다리 ρ(검열 제외)": rhos,
           "사다리 ρ(검열=공동최하위 보조)": rhos_aux,
           "m-적응 밴드(보조)": {"annex1 원표 2σ": band_m, "annex3 합성 2σ": band_comp},
           "부호 시험(847)": (None if not {"v1(정본)", "v2(재척도)"} <= set(rhos) else
                             bool(rhos["v2(재척도)"] >= rhos["v1(정본)"])),
           "판정(동결 문면)": verdict}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    outp = KOBIS_DIR / f"harvest_{dt.date.today().isoformat()}.json"
    with open(outp, "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--harvest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.harvest:
        harvest()
    else:
        print("사용: --selftest(언제나) 또는 --harvest(9/28 이후)")
