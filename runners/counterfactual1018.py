# -*- coding: utf-8 -*-
"""사이클 1018 — L3 반사실 추정기 (합성통제 · 위약=MDE · 이중 기준선 · 환율).

사전등록: docs/탐색/1018.md (커밋 be7941132 — 실측 «전») §1~§8 을 그대로 집행한다.
정본 명세: docs/아키텍처_결정기.md §L3 + v1.1. 규칙 변경 0 — 어긋나면 그 수는 「미판정」.

씀:  python3 runners/counterfactual1018.py
산출: /Users/ax/wm_harvest/foundation/l3_counterfactual/
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import datetime as dt
import glob
import gzip
import hashlib
import json
import math
import os
import random
import time
import warnings

import numpy as np

warnings.filterwarnings("ignore", message="Mean of empty slice")

from pretrain.leak_guard import assert_no_leak, LeakDetected
from pretrain.mde_guard import assert_mde, mde_of, MdeUnderpowered

REPO = "/Users/ax/world_model"
LEDGER = "/Users/ax/wm_harvest/foundation/ledger_interventions/ledger.jsonl"
OUT = "/Users/ax/wm_harvest/foundation/l3_counterfactual"
WD_DIR = os.path.join(REPO, "data/ingest/wiki_daily")
WV_DIR = os.path.join(REPO, "data/state/wiki_views")
WA_DIR = os.path.join(REPO, "data/state/wiki_after")
TRI = "/Users/ax/wm_harvest/foundation/triples"

K_DONOR = 25          # §3 공여 상한
MIN_DONOR = 5         # §3 공여 하한
FW_ITERS = 500        # §3 Frank-Wolfe
RMSE_ABS = 0.30       # §3 품질 관문
RMSE_REL = 0.75       # §3 품질 관문 (×SD_pre)
GUARD_DAYS = 14       # §1 T0 가드밴드
AIM = math.log(1.5)   # §4 겨냥 효과 = 0.4055
SEEDS = (1018, 2019)  # §4 위약 시드 쌍
B_BOOT = 2000         # §7 ⓐ 붓스트랩

# §2 route ② 도메인 사전 (record_id 접두 → 도메인)
PREFIX_DOM = {"AN": "애니", "WA": "세계애니", "GAME": "게임", "WT": "웹툰", "MG": "만화",
              "MB": "모바일", "BOOK": "도서", "IDOL": "아이돌", "FUND": "펀딩",
              "MKT": "시장팝업", "MKT2": "시장팝업"}


def dom_of_rid(rid):
    p = rid.split("-")[0]
    if p in PREFIX_DOM:
        return PREFIX_DOM[p]
    return "팝업"  # 내부층 접두(RCPU·RTPU·RIPU·RXPU·RCCP·ROPU …)


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


LOG_FH = None


def say(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    if LOG_FH:
        LOG_FH.write(line + "\n")
        LOG_FH.flush()


def d2i(d):
    return d.year * 10000 + d.month * 100 + d.day


def days_range(d0, n):
    return [d0 + dt.timedelta(days=k) for k in range(n)]


def parse_iso(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


def cover_n(curve, days):
    return sum(1 for d in days if d2i(d) in curve)


def vec_fill0(curve, days):
    """§2 — 커버 관문 뒤 결측일 = 0 (원천의 영일 생략 의미론 역적용) · 채운 수 병기."""
    v = np.zeros(len(days), dtype=np.float64)
    filled = 0
    for i, d in enumerate(days):
        k = d2i(d)
        if k in curve:
            v[i] = curve[k]
        else:
            filled += 1
    return v, filled


# ── 게이트 함수 + v5.3-2 방향 탐침 (측정 «전») ─────────────────────────
def gate_zero_center(median, se_med):
    """§4 위약 0 중심 — |med| ≤ 2×SE_med 면 참(통과). 부호: 양쪽."""
    return abs(median) <= 2.0 * se_med


def direction_probe():
    t = 0.1  # 합성 문턱 t>0 — 2×SE_med = t 가 되게 SE_med = t/2
    se = t / 2.0
    bad = []
    if gate_zero_center(+2 * t, se):
        bad.append("+2t 에서 참(악화 쪽이 통과)")
    if gate_zero_center(-2 * t, se):
        bad.append("-2t 에서 참(악화 쪽이 통과)")
    if not gate_zero_center(0.0, se):
        bad.append("0 에서 거짓")
    if bad:
        raise RuntimeError("🔴 방향 탐침 실패(v5.3-2) — 측정 없이 중단: %s" % "; ".join(bad))
    return {"합성 t": t, "±2t": "거짓·거짓", "0": "참", "판정": "통과"}


# ── Frank-Wolfe 합성통제 (§3 — 결정론) ────────────────────────────────
def fit_scm(X, y):
    """min ‖Xw−y‖² · w≥0 · Σw=1 — FW 500회 · 초기 균등 · argmin 동률 낮은 인덱스."""
    K = X.shape[1]
    w = np.full(K, 1.0 / K)
    for t in range(1, FW_ITERS + 1):
        g = X.T @ (X @ w - y)
        s = int(np.argmin(g))
        gam = 2.0 / (t + 2.0)
        w *= (1.0 - gam)
        w[s] += gam
    return w


def scm_one(unit_curve, T0, opened, donors, tag):
    """§3 절차 한 건. donors = [(키, curve)] (이미 자기·같은 문서·원장 제외 · 도메인 일치).
    반환 dict — 단계별 탈락은 {"탈락": 사유}."""
    pre_days = days_range(T0 - dt.timedelta(days=90), 90)
    post_days = days_range(opened, 91)
    if cover_n(unit_curve, pre_days) < 85 or cover_n(unit_curve, post_days) < 86:
        return {"탈락": "커버 미달"}
    y_pre_raw, f_pre = vec_fill0(unit_curve, pre_days)
    y_post_raw, f_post = vec_fill0(unit_curve, post_days)
    y_pre = np.log1p(y_pre_raw)
    y_post = np.log1p(y_post_raw)

    elig = []
    for key, cv in donors:
        if cover_n(cv, pre_days) >= 85 and cover_n(cv, post_days) >= 86:
            elig.append((key, cv))
    if len(elig) < MIN_DONOR:
        return {"탈락": "공여 부족", "공여 후보": len(elig)}
    # 상관 상위 K (동률 키 사전순 — 정렬 키 (−corr, 키))
    scored = []
    for key, cv in elig:
        v, _ = vec_fill0(cv, pre_days)
        lv = np.log1p(v)
        sd = lv.std()
        corr = float(np.corrcoef(lv, y_pre)[0, 1]) if (sd > 0 and y_pre.std() > 0) else -2.0
        if math.isnan(corr):
            corr = -2.0
        scored.append((-corr, key, cv))
    scored.sort(key=lambda z: (z[0], z[1]))
    picked = scored[:K_DONOR]
    Xp = np.stack([np.log1p(vec_fill0(cv, pre_days)[0]) for _, _, cv in picked], axis=1)
    Xo = np.stack([np.log1p(vec_fill0(cv, post_days)[0]) for _, _, cv in picked], axis=1)
    w = fit_scm(Xp, y_pre)
    resid = Xp @ w - y_pre
    rmse = float(np.sqrt((resid ** 2).mean()))
    sd_pre = float(y_pre.std())
    if not (rmse <= RMSE_ABS or rmse <= RMSE_REL * sd_pre):
        return {"탈락": "적합 불가", "RMSE_pre": round(rmse, 4), "SD_pre": round(sd_pre, 4)}
    synth_post_log = Xo @ w
    eff_log = float((y_post - synth_post_log).mean())
    eff_raw = float((y_post_raw - np.expm1(synth_post_log)).sum())
    return {"T0": T0.isoformat(), "opened": opened.isoformat(),
            "효과_log": eff_log, "효과_원눈금": eff_raw,
            "RMSE_pre": round(rmse, 4), "SD_pre": round(sd_pre, 4),
            "공여 후보": len(elig), "공여 사용": len(picked),
            "결측채움(전/후)": [f_pre, f_post],
            "일별차_log": [round(float(x), 4) for x in (y_post - synth_post_log)],
            "_w": w, "_picked": [k for _, k, _ in picked],
            "_pre_days_obs": [d for d in pre_days if d2i(d) in unit_curve],
            "_Xw_fn": (picked, w), "_synth_post_log": synth_post_log,
            "_y_post_log": y_post}


# ── 자료 적재 ─────────────────────────────────────────────────────────
def load_wiki_daily():
    rows = []
    shas = {}
    for fp in sorted(glob.glob(os.path.join(WD_DIR, "*.jsonl.gz"))):
        shas[os.path.basename(fp)] = sha16(fp)
        with gzip.open(fp, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if not r.get("날짜"):
                    continue
                curve = {int(a): int(b) for a, b in zip(r["날짜"], r["조회수"])}
                rows.append({"키": r["키"], "도메인": r["도메인"], "문서": r["문서"],
                             "n일": len(curve), "curve": curve})
    return rows, shas


def route2_curve(rid, which):
    fp = os.path.join(WV_DIR if which == "pre" else WA_DIR, rid + ".json")
    if not os.path.exists(fp):
        return None
    with open(fp) as fh:
        v = json.load(fh)
    if not v.get("days") or (which == "pre" and not v.get("page")):
        return None  # page 요건은 wiki_views 쪽만 — 1016 triple_ok 과 동형
    return {int(x[0]): int(x[1]) for x in v["days"]}


def main():
    global LOG_FH
    os.makedirs(OUT, exist_ok=True)
    LOG_FH = open(os.path.join(OUT, "run1018.out"), "w", encoding="utf-8")
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S")
    say("시작 %s · load1=%.2f" % (t_start, os.getloadavg()[0]))
    probe = direction_probe()
    say("방향 탐침(v5.3-2): %s" % json.dumps(probe, ensure_ascii=False))

    # 원장
    ledger = [json.loads(l) for l in open(LEDGER, encoding="utf-8")]
    ledger_ids = {r["record_id"] for r in ledger}
    resolved_pages = {r["source"]["wiki_resolution"]["page"] for r in ledger
                      if r["source"].get("wiki_resolution")}
    say("원장 %d · 해소 문서 %d" % (len(ledger), len(resolved_pages)))

    wrows, wd_shas = load_wiki_daily()
    say("wiki_daily 행 %d" % len(wrows))
    by_doc = {}
    for r in wrows:
        by_doc.setdefault(r["문서"], []).append(r)
    by_dom = {}
    for r in wrows:
        by_dom.setdefault(r["도메인"], []).append(r)

    # 공여 적격(§3 ⓐⓑ) — 도메인별
    donor_by_dom = {}
    n_donor_elig = 0
    for dom, rs in by_dom.items():
        lst = [r for r in rs if r["키"] not in ledger_ids and r["문서"] not in resolved_pages]
        donor_by_dom[dom] = lst
        n_donor_elig += len(lst)
    say("공여 적격(원장 밖) 합 %d · 도메인별 %s" %
        (n_donor_elig, {d: len(v) for d, v in sorted(donor_by_dom.items())}))

    # ── R1: 1016 §7-5 «후» 삼중 조건 재계수 ──
    def triple_ok_1016(rec, f):
        pre = days_range(f - dt.timedelta(days=90), 90)
        post = days_range(f, 91)
        wr = rec["source"].get("wiki_resolution")
        pg = wr["page"] if wr else None
        if pg:
            for row in by_doc.get(pg, []):
                if cover_n(row["curve"], pre) >= 85 and cover_n(row["curve"], post) >= 86:
                    return True
        cv, ca = route2_curve(rec["record_id"], "pre"), route2_curve(rec["record_id"], "post")
        if cv is not None and ca is not None:
            if cover_n(cv, pre) >= 85 and cover_n(ca, post) >= 86:
                return True
        return False

    R1 = []
    for rec in ledger:
        w = rec["A"]["when"]
        if w.get("date_precision") != "day":
            continue
        f = parse_iso(w.get("opened_at"))
        if f and triple_ok_1016(rec, f):
            R1.append(rec)
    say("R1 삼중 조건(1016 «후» 재계수): %d [목표 재현 139]" % len(R1))

    # ── R2: T0 규칙 적용 가능 + 곡선 채택 (§1·§2) ──
    def pick_curve(rec, T0, opened):
        pre = days_range(T0 - dt.timedelta(days=90), 90)
        post = days_range(opened, 91)
        wr = rec["source"].get("wiki_resolution")
        pg = wr["page"] if wr else None
        cands = list(by_doc.get(pg, [])) if pg else []
        for row in wrows:
            if row["키"] == rec["record_id"] and row not in cands:
                cands.append(row)
        best = None
        for row in cands:
            sc = cover_n(row["curve"], pre) + cover_n(row["curve"], post)
            key = (-sc, row["도메인"], row["키"])
            if best is None or key < best[0]:
                best = (key, row, sc)
        if best is not None:
            row = best[1]
            if cover_n(row["curve"], pre) >= 85 and cover_n(row["curve"], post) >= 86:
                doc = row["문서"]
                return {**{d2i_k: v for d2i_k, v in row["curve"].items()}}, row["도메인"], doc, row["키"], "wiki_daily"
        cv, ca = route2_curve(rec["record_id"], "pre"), route2_curve(rec["record_id"], "post")
        if cv is not None and ca is not None:
            if cover_n(cv, pre) >= 85 and cover_n(ca, post) >= 86:
                merged = dict(cv)
                merged.update(ca)
                return merged, dom_of_rid(rec["record_id"]), (pg or rec["record_id"]), rec["record_id"], "route2"
        return None, None, None, None, None

    treated = []   # 각 원소: rec + 곡선 + 도메인
    drop_R2 = 0
    for rec in R1:
        w = rec["A"]["when"]
        opened = parse_iso(w["opened_at"])
        ann = parse_iso(w.get("announced_at"))
        T0 = ann if ann else opened - dt.timedelta(days=GUARD_DAYS)
        curve, dom, doc, ckey, route = pick_curve(rec, T0, opened)
        if curve is None:
            drop_R2 += 1
            continue
        treated.append({"rec": rec, "rid": rec["record_id"], "T0": T0, "opened": opened,
                        "ann": ann, "curve": curve, "dom": dom, "doc": doc,
                        "ckey": ckey, "route": route})
    say("R2 T0 적용 가능: %d (탈락 %d)" % (len(treated), drop_R2))

    # ── 누수 관문 (§3 · L0-3) — 건별 사전 창 관측일 as_of=T0 ──
    stamps_ok, min_margin, first_stamp, leak_fail = 0, None, None, []
    for u in treated:
        pre = days_range(u["T0"] - dt.timedelta(days=90), 90)
        rows_in = [{"id": "%s:%s" % (u["rid"], d.isoformat()), "published_at": d.isoformat()}
                   for d in pre if d2i(d) in u["curve"]]
        try:
            st = assert_no_leak(rows_in, u["T0"].isoformat(), tag="1018 사전창 rid=%s" % u["rid"])
            stamps_ok += 1
            if first_stamp is None:
                first_stamp = st
            if st["여유일"] is not None and (min_margin is None or st["여유일"] < min_margin):
                min_margin = st["여유일"]
        except LeakDetected as e:
            leak_fail.append(u["rid"])
            say("🔴 누수 — %s «측정 없이 중단» 신고: %s" % (u["rid"], str(e)[:160]))
    treated = [u for u in treated if u["rid"] not in set(leak_fail)]
    say("누수 관문: 통과 %d · 위반 %d · 최소 여유일 %s" % (stamps_ok, len(leak_fail), min_margin))

    # ── R3·R4: 합성통제 (§3) ──
    R4 = []
    drop = {"공여 부족": 0, "적합 불가": 0, "커버 미달": 0}
    for u in treated:
        donors = [(r["키"], r["curve"]) for r in donor_by_dom.get(u["dom"], [])
                  if r["문서"] != u["doc"] and r["키"] != u["ckey"]]
        donors.sort(key=lambda z: z[0])
        res = scm_one(u["curve"], u["T0"], u["opened"], donors, u["rid"])
        if "탈락" in res:
            drop[res["탈락"]] = drop.get(res["탈락"], 0) + 1
            u["탈락"] = res
            continue
        u["scm"] = res
        R4.append(u)
    say("R3/R4: 최종 처치 분모 %d (공여 부족 %d · 적합 불가 %d · 커버 미달 %d)"
        % (len(R4), drop["공여 부족"], drop["적합 불가"], drop["커버 미달"]))

    # ── 위약 (§4) — 두 시드 ──
    pool = {}
    for r in wrows:
        if r["키"] in ledger_ids or r["문서"] in resolved_pages:
            continue
        prev = pool.get(r["문서"])
        if prev is None or (-r["n일"], r["키"]) < (-prev["n일"], prev["키"]):
            pool[r["문서"]] = r
    punits = sorted(pool.values(), key=lambda r: r["키"])
    say("위약 풀(문서 중복 접음): %d" % len(punits))
    pairs = sorted([(u["T0"], u["opened"]) for u in R4])

    def run_placebo(seed):
        rng = random.Random(seed)
        effects, meta_rows = [], []
        n_cov_fail, n_donor_short, n_fit_fail = 0, 0, 0
        for r in punits:
            got = None
            for _ in range(5):
                T0, opened = pairs[rng.randrange(len(pairs))]
                pre = days_range(T0 - dt.timedelta(days=90), 90)
                post = days_range(opened, 91)
                if cover_n(r["curve"], pre) >= 85 and cover_n(r["curve"], post) >= 86:
                    got = (T0, opened)
                    break
            if got is None:
                n_cov_fail += 1
                continue
            donors = [(z["키"], z["curve"]) for z in donor_by_dom.get(r["도메인"], [])
                      if z["키"] != r["키"] and z["문서"] != r["문서"]]
            donors.sort(key=lambda z: z[0])
            res = scm_one(r["curve"], got[0], got[1], donors, r["키"])
            if "탈락" in res:
                if res["탈락"] == "공여 부족":
                    n_donor_short += 1
                elif res["탈락"] == "적합 불가":
                    n_fit_fail += 1
                else:
                    n_cov_fail += 1
                continue
            effects.append(res["효과_log"])
            meta_rows.append({"키": r["키"], "문서": r["문서"], "도메인": r["도메인"],
                              "T0": res["T0"], "opened": res["opened"],
                              "효과_log": round(res["효과_log"], 4),
                              "RMSE_pre": res["RMSE_pre"]})
        e = np.array(effects)
        stats = {"시드": seed, "N": int(len(e)),
                 "평균": float(e.mean()) if len(e) else None,
                 "중앙값": float(np.median(e)) if len(e) else None,
                 "SD": float(e.std(ddof=1)) if len(e) > 1 else None,
                 "q2.5": float(np.percentile(e, 2.5)) if len(e) else None,
                 "q97.5": float(np.percentile(e, 97.5)) if len(e) else None,
                 "SE_med(1.2533·SD/√N)": float(1.2533 * e.std(ddof=1) / math.sqrt(len(e))) if len(e) > 1 else None,
                 "탈락": {"커버(5회 재추출 포함)": n_cov_fail, "공여 부족": n_donor_short,
                          "적합 불가": n_fit_fail},
                 "도메인 분해": {}}
        for m in meta_rows:
            d = stats["도메인 분해"].setdefault(m["도메인"], [])
            d.append(m["효과_log"])
        stats["도메인 분해"] = {d: {"n": len(v), "중앙값": float(np.median(v)),
                                    "q2.5": float(np.percentile(v, 2.5)) if len(v) >= 50 else None,
                                    "q97.5": float(np.percentile(v, 97.5)) if len(v) >= 50 else None}
                                for d, v in sorted(stats["도메인 분해"].items())}
        return stats, meta_rows, e

    st1, rows1, e1 = run_placebo(SEEDS[0])
    say("위약 시드 %d: N=%d · med=%.4f · SD=%.4f" % (SEEDS[0], st1["N"], st1["중앙값"], st1["SD"]))
    st2, rows2, e2 = run_placebo(SEEDS[1])
    say("위약 시드 %d: N=%d · med=%.4f · SD=%.4f" % (SEEDS[1], st2["N"], st2["중앙값"], st2["SD"]))
    p1 = os.path.join(OUT, "placebo_seed1018.json")
    json.dump({"통계": st1, "건별": rows1}, open(p1, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump({"통계": st2, "건별": rows2},
              open(os.path.join(OUT, "placebo_seed2019.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    p1_sha = sha16(p1)

    # 0 중심 게이트 (§4 — 양쪽)
    zero_ok = gate_zero_center(st1["중앙값"], st1["SE_med(1.2533·SD/√N)"])
    zero_gate = {"중앙값": st1["중앙값"], "2×SE_med": 2 * st1["SE_med(1.2533·SD/√N)"],
                 "여유(2SE−|med|)": 2 * st1["SE_med(1.2533·SD/√N)"] - abs(st1["중앙값"]),
                 "판정": "통과(0 중심)" if zero_ok else "🔴 설계 결함 — 측정 중단"}
    say("0 중심 게이트: %s" % json.dumps(zero_gate, ensure_ascii=False))

    # MDE (§4 · 부칙 6)
    J = abs(st1["SD"] - st2["SD"]) / math.sqrt(2.0)
    mde = mde_of(st1["SD"], J)
    mde_stamp, demote = None, False
    try:
        mde_stamp = assert_mde(mde, AIM, p1_sha)
        say("MDE 관문: 통과 — %s" % json.dumps(mde_stamp, ensure_ascii=False))
    except MdeUnderpowered as e:
        demote = True
        mde_stamp = {"MDE": mde, "겨냥 효과": AIM, "판정": "MdeUnderpowered — 유의 칸 [관찰] 강등",
                     "메시지": str(e)[:300], "눈금 출처 sha": p1_sha}
        say("MDE 관문: %s" % mde_stamp["판정"])

    # ── 처치 효과 표 + 유의 (§4 분위 · §7 ⓒ) ──
    if not zero_ok:
        say("🔴 설계 결함 — 처치 효과 표·유의·환율 게재 중단 (§4). 위약 진단만 저장.")
        finish(t_start, wd_shas, st1, st2, zero_gate, mde_stamp, J, mde, None, None, None,
               None, len(ledger), len(R1), len(treated) + len(leak_fail), len(treated), drop,
               len(R4), stamps_ok, min_margin, first_stamp, leak_fail, len(punits), demote, probe)
        return

    q_lo = st1["q2.5"]
    q_hi = st1["q97.5"]
    for u in R4:
        eff = u["scm"]["효과_log"]
        u["유의"] = bool(eff < q_lo or eff > q_hi)

    # ── 이중 기준선 (§5) ──
    import torch
    torch.set_num_threads(4)
    from pretrain.transition import load_ensemble, load_conformal, ConformalWrap
    ens, man, member_shas = load_ensemble()
    conf = load_conformal()
    delta, conf_meta = conf
    model = ConformalWrap(ens, delta).eval()
    doms10 = json.load(open(os.path.join(TRI, "domains.json"), encoding="utf-8"))
    ent_rows = {}
    for i, l in enumerate(open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")):
        m = json.loads(l)
        ent_rows.setdefault(m["개체"], []).append(i)
    E_all = np.load(man["text_emb"])["E"].astype(np.float32)
    fc_skip = {"도메인 밖": 0, "임베딩 없음": 0, "지평 밖": 0}
    n_sign_agree, n_fc = 0, 0
    scm_effs, fc_effs = [], []
    for u in R4:
        u["예보기"] = None
        if u["dom"] not in doms10:
            fc_skip["도메인 밖"] += 1
            continue
        if u["ckey"] not in ent_rows:
            fc_skip["임베딩 없음"] += 1
            continue
        ov0 = u["opened"]
        ov1 = min(u["opened"] + dt.timedelta(days=90), u["T0"] + dt.timedelta(days=90))
        if ov1 < ov0:
            fc_skip["지평 밖"] += 1
            continue
        pre = days_range(u["T0"] - dt.timedelta(days=90), 90)
        S_raw, _ = vec_fill0(u["curve"], pre)
        logS = np.log1p(S_raw)
        base = float(logS.mean())
        Sc = (logS - base).astype(np.float32)
        dom1 = np.zeros(len(doms10), dtype=np.float32)
        dom1[doms10.index(u["dom"])] = 1.0
        doy = u["T0"].month * 30.4 + u["T0"].day
        yearf = u["T0"].year + (u["T0"].month - 0.5) / 12.0
        Ee = E_all[ent_rows[u["ckey"]]].mean(axis=0)
        x = np.concatenate([Sc, dom1,
                            np.array([math.sin(2 * math.pi * doy / 365.0),
                                      math.cos(2 * math.pi * doy / 365.0),
                                      (yearf - 2013.0) / 10.0, base], dtype=np.float32),
                            Ee]).astype(np.float32)[None, :]
        with torch.no_grad():
            q = model(torch.from_numpy(x))[0].numpy()  # (91,5) 잔차 눈금(등각 적용)
        n_ov = (ov1 - ov0).days + 1
        diffs, in_band = [], 0
        for k in range(n_ov):
            day = ov0 + dt.timedelta(days=k)
            fi = (day - u["T0"]).days
            pi = (day - u["opened"]).days
            act_log = u["scm"]["_y_post_log"][pi]
            syn_log = u["scm"]["_synth_post_log"][pi]
            diffs.append(act_log - (q[fi, 2] + base))
            if (q[fi, 0] + base) <= syn_log <= (q[fi, 4] + base):
                in_band += 1
        fc_eff = float(np.mean(diffs))
        scm_ov = float(np.mean([u["scm"]["_y_post_log"][(ov0 + dt.timedelta(days=k) - u["opened"]).days]
                                - u["scm"]["_synth_post_log"][(ov0 + dt.timedelta(days=k) - u["opened"]).days]
                                for k in range(n_ov)]))
        u["예보기"] = {"효과_log": round(fc_eff, 4), "비교창 일수": n_ov,
                       "합성이 등각 띠 안(일 비율)": round(in_band / n_ov, 4),
                       "SCM 효과(비교창)": round(scm_ov, 4)}
        n_fc += 1
        if (fc_eff > 0) == (u["scm"]["효과_log"] > 0):
            n_sign_agree += 1
        scm_effs.append(u["scm"]["효과_log"])
        fc_effs.append(fc_eff)
    fc_corr = float(np.corrcoef(scm_effs, fc_effs)[0, 1]) if len(scm_effs) >= 3 else None
    band_rates = [u["예보기"]["합성이 등각 띠 안(일 비율)"] for u in R4 if u["예보기"]]
    dual = {"분모": n_fc, "탈락": fc_skip, "부호 일치": n_sign_agree,
            "피어슨 상관": round(fc_corr, 4) if fc_corr is not None else None,
            "합성이 등각 띠 안(평균 일 비율)": round(float(np.mean(band_rates)), 4) if band_rates else None,
            "manifest sha256/16": sha16(os.path.join(TRI, "..", "transition", "ensemble_manifest.json")),
            "δ(log)": delta}
    say("이중 기준선: %s" % json.dumps(dual, ensure_ascii=False))

    # ── 백도어 v1 + E-value (§6) ──
    big_doms = sorted({u["dom"] for u in R4
                       if sum(1 for z in R4 if z["dom"] == u["dom"]) >= 5})
    cols, names = [], []
    yv = np.array([u["scm"]["효과_log"] for u in R4])
    base_pre = []
    for u in R4:
        pre = days_range(u["T0"] - dt.timedelta(days=90), 90)
        v, _ = vec_fill0(u["curve"], pre)
        base_pre.append(float(np.log1p(v).mean()))
    cols.append(np.array(base_pre)); names.append("base(사전 log 평균)")
    for d in big_doms:
        cols.append(np.array([1.0 if u["dom"] == d else 0.0 for u in R4])); names.append("dom:" + d)
    prior, prior_miss = [], []
    for u in R4:
        ih = u["rec"]["C"].get("ip_history") or {}
        pc = ih.get("prior_count")
        prior.append(1.0 if (pc is not None and pc > 0) else 0.0)
        prior_miss.append(1.0 if pc is None else 0.0)
    cols.append(np.array(prior)); names.append("prior_count>0")
    cols.append(np.array(prior_miss)); names.append("prior 결측 지시자")
    comp, comp_miss = [], []
    for u in R4:
        c = u["rec"]["C"].get("comp_density_any")
        comp.append(float(c) if c is not None else 0.0)
        comp_miss.append(1.0 if c is None else 0.0)
    cols.append(np.array(comp)); names.append("comp_density_any")
    cols.append(np.array(comp_miss)); names.append("comp 결측 지시자")
    Xc = np.stack(cols, axis=1)
    Xc = Xc - Xc.mean(axis=0, keepdims=True)   # 중심화 → 절편 = 조정 평균
    A = np.concatenate([np.ones((len(R4), 1)), Xc], axis=1)
    beta, _, _, _ = np.linalg.lstsq(A, yv, rcond=None)
    adj_mean = float(beta[0])
    raw_mean = float(yv.mean())
    d_std = adj_mean / st1["SD"]
    RR = math.exp(0.91 * abs(d_std))
    evalue = RR + math.sqrt(RR * (RR - 1.0)) if RR > 1 else 1.0
    backdoor = {"무조정 평균 효과_log": round(raw_mean, 4),
                "조정 평균 효과_log(절편)": round(adj_mean, 4),
                "계수": {n: round(float(b), 4) for n, b in zip(names, beta[1:])},
                "d(=조정평균/SD_위약)": round(d_std, 4),
                "E-value": round(evalue, 3),
                "해석": "미관측 혼란이 처치·결과 양쪽과 RR≈%.2f 이상으로 결합해야 조정 평균 효과가 0 으로 뒤집힌다 (VanderWeele 근사 RR=exp(0.91·d))" % RR,
                "s_disc 조정": "L1 후 자리(원장 전건 L1_pending) — 본 판은 미조정",
                "인과 화법": "무작위 아님 — 관측 조정 + 위약 눈금 하의 추정"}
    say("백도어 v1: %s" % json.dumps(backdoor, ensure_ascii=False))

    # ── 사건 반응 함수 v0 (§7 ⓐ) — 상대일 −14..+90 (opened 기준) ──
    rel_days = list(range(-14, 91))
    M = np.full((len(R4), len(rel_days)), np.nan)
    for i, u in enumerate(R4):
        picked, w = u["scm"]["_Xw_fn"]
        for j, d in enumerate(rel_days):
            day = u["opened"] + dt.timedelta(days=d)
            if d >= 0:
                M[i, j] = u["scm"]["_y_post_log"][d] - u["scm"]["_synth_post_log"][d]
            else:
                if day < u["T0"]:
                    continue  # T0 이전은 사전 창 몫 — IRF 밖
                yv_ = math.log1p(u["curve"].get(d2i(day), 0))
                sv = 0.0
                for (_, _, cv), wk in zip(picked, w):
                    sv += wk * math.log1p(cv.get(d2i(day), 0))
                M[i, j] = yv_ - sv
    rng = np.random.default_rng(1018)
    n_units = len(R4)
    boot_lo, boot_hi = [], []
    means, ns = [], []
    for j in range(len(rel_days)):
        col = M[:, j]
        ok = ~np.isnan(col)
        ns.append(int(ok.sum()))
        means.append(float(np.nanmean(col)) if ok.any() else None)
    idx_boot = rng.integers(0, n_units, size=(B_BOOT, n_units))
    for j in range(len(rel_days)):
        col = M[:, j]
        if ns[j] == 0:
            boot_lo.append(None); boot_hi.append(None)
            continue
        samp = col[idx_boot]                      # (B, n)
        bm = np.nanmean(samp, axis=1)
        bm = bm[~np.isnan(bm)]
        boot_lo.append(float(np.percentile(bm, 5)))
        boot_hi.append(float(np.percentile(bm, 95)))
    irf = {"유형": "팝업개최", "눈금": "log1p 차(실제−합성)", "기준일": "opened_at",
           "붓스트랩": {"B": B_BOOT, "시드": 1018, "구간": "90%(개체 재표집)"},
           "상대일": rel_days, "평균": [round(m, 4) if m is not None else None for m in means],
           "n": ns, "q05": [round(x, 4) if x is not None else None for x in boot_lo],
           "q95": [round(x, 4) if x is not None else None for x in boot_hi]}
    json.dump(irf, open(os.path.join(OUT, "irf_v0.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ── 환율 (§7 ⓑ) ──
    ex_rows = []
    for u in R4:
        vis = u["rec"]["Y"].get("visitors_total")
        effr = u["scm"]["효과_원눈금"]
        if vis is None or effr is None or effr <= 0:
            continue
        ex_rows.append({"rid": u["rid"], "도메인": u["dom"], "방문자": vis,
                        "관심증분(사후91)": round(effr, 1),
                        "환율(방문자/관심1)": round(vis / effr, 4),
                        "유의": u["유의"]})
    ex_dom = {}
    for r in ex_rows:
        ex_dom.setdefault(r["도메인"], []).append(r["환율(방문자/관심1)"])
    def qstat(v):
        return {"n": len(v), "중앙값": float(np.median(v)),
                "q25": float(np.percentile(v, 25)), "q75": float(np.percentile(v, 75))}
    ex_sig = [r["환율(방문자/관심1)"] for r in ex_rows if r["유의"]]
    exchange = {"분모(visitors∧증분>0)": len(ex_rows),
                "도메인별": {d: qstat(v) for d, v in sorted(ex_dom.items())},
                "전체": qstat([r["환율(방문자/관심1)"] for r in ex_rows]) if ex_rows else None,
                "유의 건 한정": qstat(ex_sig) if ex_sig else {"n": 0},
                "눈금 주석": "분자=행사 전체 방문자 · 분모=사후 91일 창 관심 증분(원 눈금 합) — 창 불일치는 v0 한계"}
    json.dump({"집계": exchange, "건별": ex_rows},
              open(os.path.join(OUT, "exchange.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    # ── 처치 건별 표 (§7 ⓒ — 실명은 파일 안에만) ──
    with open(os.path.join(OUT, "effects.jsonl"), "w", encoding="utf-8") as fh:
        for u in R4:
            s = u["scm"]
            rec = {"record_id": u["rid"], "층": u["rec"]["layer"], "도메인": u["dom"],
                   "문서": u["doc"], "곡선키": u["ckey"], "route": u["route"],
                   "T0": u["T0"].isoformat(), "opened": u["opened"].isoformat(),
                   "announced_at": u["ann"].isoformat() if u["ann"] else None,
                   "lead_days": (u["opened"] - u["T0"]).days,
                   "효과_log": round(s["효과_log"], 4), "효과_원눈금": round(s["효과_원눈금"], 1),
                   "유의(위약 양측 5%)": u["유의"],
                   "RMSE_pre": s["RMSE_pre"], "SD_pre": s["SD_pre"],
                   "공여 후보": s["공여 후보"], "공여 사용": s["공여 사용"],
                   "결측채움(전/후)": s["결측채움(전/후)"],
                   "예보기": u["예보기"],
                   "visitors_total": u["rec"]["Y"].get("visitors_total"),
                   "일별차_log": s["일별차_log"]}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    n_sig = sum(1 for u in R4 if u["유의"])
    n_sig_pos = sum(1 for u in R4 if u["유의"] and u["scm"]["효과_log"] > 0)
    say("처치 효과: 유의 %d/%d (양(+) %d · 음(−) %d) · 평균 %.4f · 중앙값 %.4f"
        % (n_sig, len(R4), n_sig_pos, n_sig - n_sig_pos, raw_mean,
           float(np.median([u["scm"]["효과_log"] for u in R4]))))
    finish(t_start, wd_shas, st1, st2, zero_gate, mde_stamp, J, mde, dual, backdoor, irf,
           exchange, len(ledger), len(R1), len(treated) + len(leak_fail), len(treated), drop,
           len(R4), stamps_ok, min_margin, first_stamp, leak_fail, len(punits), demote, probe,
           n_sig=n_sig, n_sig_pos=n_sig_pos)


def finish(t_start, wd_shas, st1, st2, zero_gate, mde_stamp, J, mde, dual, backdoor, irf,
           exchange, n0, n1, n2_in, n2, drop, n4, stamps_ok, min_margin, first_stamp,
           leak_fail, n_pool, demote, probe, n_sig=None, n_sig_pos=None):
    meta = {
        "사전등록": {"문서": "docs/탐색/1018.md", "커밋": "be7941132"},
        "잰 소스(조항 66)": {
            "러너 sha256": hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest(),
            "ledger.jsonl sha256/16": sha16(LEDGER),
            "wiki_daily sha256/16": wd_shas,
            "시작": t_start, "끝": time.strftime("%Y-%m-%dT%H:%M:%S")},
        "방향 탐침(v5.3-2)": probe,
        "분모 사다리": {"R0 원장": n0, "R1 삼중(1016 «후» 재계수)": n1,
                        "R2 T0 적용 가능": n2, "누수 위반 제외": len(leak_fail),
                        "R3/R4 탈락": drop, "R4 최종 처치 분모": n4},
        "누수 관문(L0-3)": {"통과": stamps_ok, "위반": leak_fail,
                            "최소 여유일": min_margin, "대표 스탬프": first_stamp},
        "위약(§4)": {"풀": n_pool, "시드1018": st1, "시드2019": {k: st2[k] for k in
                     ("N", "평균", "중앙값", "SD")},
                     "0 중심 게이트": zero_gate,
                     "MDE": {"J(시드 지터)": J, "MDE=2×max(SD,J)": mde,
                             "겨냥 효과": AIM, "스탬프": mde_stamp,
                             "유의 칸 강등": bool(demote)}},
        "처치 유의": ({"유의": n_sig, "전체": n4, "양(+)": n_sig_pos}
                      if n_sig is not None else "게재 중단(0 중심 결함)"),
        "이중 기준선(§5)": dual,
        "백도어 v1(§6)": backdoor,
        "환율(§7ⓑ)": exchange["집계"] if isinstance(exchange, dict) and "집계" in exchange else exchange,
    }
    json.dump(meta, open(os.path.join(OUT, "meta1018.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1, default=str)
    say("완료 — meta1018.json 기록")


if __name__ == "__main__":
    main()
