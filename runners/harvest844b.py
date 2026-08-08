# -*- coding: utf-8 -*-
"""노트 858 — 수확 진단 사이드카(harvest844 의 b — **정본 판정 권한 없음**).

동결된 harvest844.py 의 구멍 넷(티처 #23)을 판정 권한 없이 봉합한다:
  ① 정규화 조인 + 편집거리 후보 — 조인 실패를 '검열'과 가른다
  ② 연기 감지 — 개봉일 무시 제목 매치로 실제 개봉일 보고
  ③ annex2 등화 m-표 조립(비단조 원표 수리본) · 합성 표 올림 조회 문서화
  ④ 합성 라벨 드라이런(--dryrun) — 사다리→밴드→판정문 전 경로를 라벨 무접촉으로

    python3 runners/harvest844b.py --dryrun     # 합성 라벨 전 경로 시험(상시 허용)
    python3 runners/harvest844b.py --normtest   # 제목 정규화 합성 시험(상시 허용)
    python3 runners/harvest844b.py --diagnose   # 9/28 이후에만(수확과 함께 1회)

부호 시험은 annex3 본문의 '≥' 로 낙착한다(갈래 기록의 '>' 와 어긋남 — 문서화).
합성 표 조회는 **올림**(엄격 쪽 · annex3 에 미문서였음을 여기 명기).
"""
import argparse
import datetime as dt
import difflib
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
ROOT = Path("/Users/ax/world_model")
KOBIS_DIR = ROOT / "cycle_log/forward/kobis"
HARVEST_NOT_BEFORE = dt.date(2026, 9, 28)


def norm_title(s):
    """공백·콜론·중점·특수부호 무시 정규화(조인 위생 — 판정 아님)."""
    s = str(s or "")
    s = re.sub(r"[\s:·・;,!?'\"“”‘’\-–—~]+", "", s)
    return s.lower()


def load_annexes():
    a1 = json.load(open(KOBIS_DIR / "annex_2026-08-08.json"))
    a2 = json.load(open(KOBIS_DIR / "annex2_2026-08-08.json"))
    a3 = json.load(open(KOBIS_DIR / "annex3_2026-08-08.json"))
    a4 = json.load(open(KOBIS_DIR / "annex4_2026-08-09.json"))
    a5 = json.load(open(KOBIS_DIR / "annex5_2026-08-08.json"))
    return a1, a2, a3, a4, a5


def band_lookup(m_eff):
    """등화 m-표(annex2 — 비단조 원표의 수리본)와 합성 표(annex3 · 올림) 병기."""
    _, a2, a3, _, _ = load_annexes()
    iso = a2["m-표 등화(단조 강제 · 합산 σ 조회는 이것)"]
    m_c = str(max(10, min(m_eff, 30)))
    comp = a3["합산 σ̄ 조회 표(단조 강제 · annex1 규칙의 σᵢ 는 이제 이 표)"]
    keys = sorted(int(k) for k in comp)
    up = next((k for k in keys if k >= min(m_eff, 30)), keys[-1])   # 올림(엄격)
    return {"annex2 등화 2σ": iso.get(m_c), "annex3 합성 2σ(올림)": comp[str(up)]}


def ladder(labels, films, a3, a4, a5):
    arms = {
        "v1(정본)": {m["code"]: m["예측 순위"] for m in films},
        "v2(재척도)": {r["code"]: r["v2 순위"] for r in a3["봉인 30편 v2 보조 팔"]["예측(자루 평균 순위·v2 축)"]},
        "격리(+3)": {r["code"]: r["격리"] for r in a4["격리 팔(v1 척도 + 회복 3편만)"]["순위"]},
        "v3(+5)": {r["code"]: r["v3 순위"] for r in a5["예측 팔(자루 평균 순위)"]},
    }
    rhos = {}
    for arm, ranks in arms.items():
        codes = [c for c in labels if c in ranks]
        if len(codes) >= 3:
            rhos[arm] = round(float(spearmanr([-ranks[c] for c in codes],
                                              [labels[c] for c in codes])[0]), 4)
    return rhos


def dryrun():
    """합성 라벨로 전 경로(사다리·밴드·판정문·부호시험 ≥) 시험 — 라벨 무접촉."""
    seal = json.load(open(KOBIS_DIR / "seal_2026-08-08.json"))
    films = seal["작품"]
    _, _, a3, a4, a5 = load_annexes()
    rng = np.random.default_rng(858)
    fake = {m["code"]: float(31 - m["예측 순위"]) + rng.normal(0, 5) for m in films}
    # 검열 셋 임의 제외해 m<30 경로도 시험
    for m in films[:3]:
        fake.pop(m["code"], None)
    rhos = ladder(fake, films, a3, a4, a5)
    m_eff = len(fake)
    bands = band_lookup(m_eff)
    sign = (None if not {"v1(정본)", "v2(재척도)"} <= set(rhos)
            else bool(rhos["v2(재척도)"] >= rhos["v1(정본)"]))     # ≥ 낙착(annex3 본문)
    ok = (len(rhos) == 4 and all(np.isfinite(v) for v in rhos.values())
          and all(bands.values()) and sign is not None)
    out = {"합성 사다리": rhos, "m_eff": m_eff, "밴드": bands, "부호(≥)": sign,
           "전 경로 통과": bool(ok)}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not ok:
        raise SystemExit("⛔ 드라이런 실패")
    return out


def normtest():
    """897 제목에 콜론/공백/중점 섭동을 넣고 정규화 매치율(합성 시험)."""
    KA = json.load(open(ROOT / "data/state/kobis_axes.json"))
    titles = [r["name"] for r in KA.values()]
    idx = {norm_title(t): t for t in titles}
    rng = np.random.default_rng(8582)
    n_ok = 0
    n = len(titles)
    for t in titles:
        v = t
        if ":" in v:
            v = v.replace(":", " : ")
        if rng.random() < 0.5:
            v = v.replace(" ", "  ")
        if rng.random() < 0.3:
            v = v + " "
        if norm_title(v) in idx:
            n_ok += 1
    rate = n_ok / n
    print(json.dumps({"행": n, "정규화 매치": n_ok, "율": round(rate, 4)}, ensure_ascii=False))
    if rate < 0.99:
        raise SystemExit("⛔ 정규화 매치율 미달")
    return rate


def diagnose():
    """수확일 진단(9/28+ · 판정 권한 없음): 조인 실패/연기/진짜 검열 3분류."""
    if dt.date.today() < HARVEST_NOT_BEFORE:
        raise SystemExit(f"⛔ 진단은 {HARVEST_NOT_BEFORE} 이후(라벨 접촉 차단)")
    from ingest.kobis import fetch_daily
    import time as _t
    seal = json.load(open(KOBIS_DIR / "seal_2026-08-08.json"))
    films = seal["작품"]
    start = min(m["개봉일"] for m in films)
    days = []
    dcur = dt.date.fromisoformat(start)
    while dcur <= dt.date.today() - dt.timedelta(days=1):
        days.append(dcur.isoformat())
        dcur += dt.timedelta(days=1)
    cache = ROOT / "data/ingest/kobis"
    daily = {}
    for day in days:
        p = cache / f"{day}.json"
        if p.exists():
            daily[day] = json.loads(p.read_text())["rows"]
        else:
            daily[day] = fetch_daily(day)
            p.write_text(json.dumps({"date": day, "rows": daily[day]}, ensure_ascii=False, indent=1))
            _t.sleep(1.5)
    all_titles = {}
    for day, rows in daily.items():
        for r in rows:
            all_titles.setdefault(norm_title(r["제목"]), set()).add(r.get("개봉일"))
    report = []
    for m in films:
        nt = norm_title(m["제목"])
        exact_days = sum(1 for day, rows in daily.items()
                         for r in rows if r["제목"].strip() == m["제목"].strip()
                         and r.get("개봉일") == m["개봉일"])
        if exact_days > 0:
            cls = f"정상 매치({exact_days}일)"
        elif nt in all_titles:
            ods = all_titles[nt]
            cls = ("연기 후보 — 실제 개봉일 " + str(sorted(x for x in ods if x)) if m["개봉일"] not in ods
                   else "정규화로만 매치(제목 표기 차)")
        else:
            near = difflib.get_close_matches(nt, list(all_titles), n=2, cutoff=0.85)
            cls = "미출현(진짜 검열 후보)" + (f" · 근접 {near}" if near else "")
        report.append({"제목": m["제목"], "봉인 개봉일": m["개봉일"], "분류": cls})
    out = {"진단(판정 권한 없음)": report}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    with open(KOBIS_DIR / f"harvest_diag_{dt.date.today().isoformat()}.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dryrun", action="store_true")
    ap.add_argument("--normtest", action="store_true")
    ap.add_argument("--diagnose", action="store_true")
    a = ap.parse_args()
    if a.dryrun:
        dryrun()
    elif a.normtest:
        normtest()
    elif a.diagnose:
        diagnose()
    else:
        print("사용: --dryrun | --normtest (상시) · --diagnose (9/28+)")
