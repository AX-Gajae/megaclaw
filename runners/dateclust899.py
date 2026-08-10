# -*- coding: utf-8 -*-
"""노트 899 · 갈래 ㄴ — **판 자신의 날짜 군집**. ICC · DEFF · n_eff, 그리고 문턱 재산정.

사전등록: `docs/prereg_899_axesdie.md` (커밋 `ee2436a43` · 2026-08-10T23:22:56+09:00)

판의 ② 구간(`out898_board.json`)은 **3,774개 단독 군집** = 행 독립 가정이다.
897 이 *"잡음의 단위는 날짜"* 라고 잰 **뒤**다(⚠ 897 의 분모는 3,710행/11도메인 ---
조항 60 대로 **그 수를 여기에 붙이지 않는다**. 판 자신의 분모로 다시 잰다).

🔴 이 사이클은 자를 뗐다 --- 채택/기각 없음. 새 문턱은 **후보**이고 정본을 안 바꾼다.

산출물: `runners/out899_dateclust.json`
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import rankdata

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                    # noqa: E402
import ruler890 as R890                               # noqa: E402
from lab import idolset, pairboot as PB               # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out899_dateclust.json"
T = 2025.0
SEEDS = FF.RULER_SEEDS
ARMS = (1, 2)
B = 10_000
B_CHK = 2_000
RNG_890 = 8900
HALF_A, HALF_B = SEEDS[:6], SEEDS[6:]
SEED_COMP = 0.00099          # thresh891 씨앗 성분 --- 읽어서 검증한다
OLD_R5 = 0.00353

#: 도메인 → (축 json, 날짜 키). `state/tri_domain.py:load_all` 에서 읽어서 옮겼다.
SRC = {
    "게임":     ("data/state/game_axes.json",    "release_date"),
    "도서":     ("data/state/book_axes.json",    "pub_date"),
    "펀딩":     ("data/state/funding_axes.json", "start_date"),
    "웹툰":     ("data/state/webtoon_axes.json", "start_date"),
    "애니":     ("data/state/anime_axes.json",   "start_date"),
    "모바일":   ("data/state/mobile_axes.json",  "release_date"),
    "만화":     ("data/state/manga_axes.json",   "start_date"),
    "세계애니": ("data/state/wanime_axes.json",  "start_date"),
    "영화":     ("data/state/kobis_axes.json",   "release_date"),
    "시장팝업": ("data/state/market_axes.json",  "period_from"),
}


def sha(p):
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def dates_for(d, n_rows, yr):
    """도메인 d 의 **전 행** 날짜 문자열. (배열, 출처, W4통과) 를 낸다."""
    if d == "아이돌":
        rows = idolset._rows(wide_post=True)
        if len(rows) == n_rows:
            return (np.array([str(r.get("debut_date") or "")[:10] for r in rows]),
                    "idolset._rows/debut_date", True)
        return None, f"idolset._rows 행 {len(rows)} != {n_rows}", False
    if d in SRC:
        p, k = SRC[d]
        rows = list(json.loads((ROOT / p).read_text()).values())
        if len(rows) == n_rows:
            return (np.array([str(r.get(k) or "")[:10] for r in rows]),
                    f"{p}/{k}", True)
        return None, f"{p} 행 {len(rows)} != {n_rows}", False
    # 팝업 --- 하네스 `yr` 이 이미 **일 해상도 분수연도**다(`popupset._frac`).
    # `_frac(s) = y + (m-1)/12 + (d-1)/365.25` 를 되돌려 YYYY-MM-DD 를 만든다.
    # 되돌리기가 단사(injective)라 군집은 원래 날짜와 정확히 같다.
    if d == "팝업":
        v = np.asarray(yr, float)
        out = []
        for x in v:
            if not np.isfinite(x):
                out.append(""); continue
            y_ = int(np.floor(x + 1e-9))
            rem = x - y_
            mo = int(np.floor(rem * 12 + 1e-6)) + 1
            dy = int(np.rint((rem - (mo - 1) / 12) * 365.25)) + 1
            mo = min(max(mo, 1), 12); dy = min(max(dy, 1), 31)
            out.append(f"{y_:04d}-{mo:02d}-{dy:02d}")
        return (np.array(out),
                "popupset._frac(meta.date) 역산 → YYYY-MM-DD(일 해상도)", True)
    return None, "원천 미확인", False


def icc_oneway(vals, groups):
    """일원 변량효과 ICC. (ICC, m̄, m0, K, N, MSB, MSW) --- 못 재면 None."""
    v = np.asarray(vals, float)
    ok = np.isfinite(v)
    v, g = v[ok], np.asarray(groups)[ok]
    N = len(v)
    uq, inv = np.unique(g, return_inverse=True)
    K = len(uq)
    if N < 3 or K < 2 or K >= N:
        return None
    m = np.bincount(inv)
    gm = v.mean()
    means = np.bincount(inv, weights=v) / m
    SSB = float((m * (means - gm) ** 2).sum())
    SSW = float(((v - means[inv]) ** 2).sum())
    MSB, MSW = SSB / (K - 1), SSW / (N - K)
    m0 = (N - float((m ** 2).sum()) / N) / (K - 1)
    den = MSB + (m0 - 1) * MSW
    icc = float((MSB - MSW) / den) if den > 0 else float("nan")
    return {"ICC": icc, "m̄(N/K)": N / K, "m0": m0, "K": K, "N": N,
            "MSB": MSB, "MSW": MSW,
            "DEFF(공식 · m̄)": 1 + (N / K - 1) * icc,
            "DEFF(공식 · m0)": 1 + (m0 - 1) * icc,
            "n_eff(m̄)": N / (1 + (N / K - 1) * icc) if (1 + (N / K - 1) * icc) > 0
                         else float("nan")}


def cl_from(keys):
    """군집 키 배열 → 인덱스 리스트."""
    uq, inv = np.unique(np.asarray(keys), return_inverse=True)
    return [np.where(inv == i)[0] for i in range(len(uq))]


def main():
    t0 = time.time()
    log = open(ROOT / "runners/out899_dateclust.log", "w", buffering=1)

    def say(s):
        print(s, flush=True); log.write(str(s) + "\n")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    res = {"노트": 899, "갈래": "ㄴ · 판 자신의 날짜 군집",
           "사전등록": {"파일": "docs/prereg_899_axesdie.md",
                        "커밋": "ee2436a43b35b06a2ae4156afaf346f55efa599d",
                        "시각": "2026-08-10T23:22:56+09:00"},
           "HEAD": head, "시각": dt.datetime.now().isoformat(timespec="seconds"),
           "코드 sha": {f: sha(ROOT / f) for f in
                        ("runners/dateclust899.py", "runners/thresh891.py",
                         "runners/ruler890.py", "lab/pairboot.py",
                         "state/rank_test.py", "runners/ff753.py")},
           "🔴 자": "뗐다 — 채택/기각 없음. 새 문턱은 **후보**이고 정본을 안 바꾼다",
           "⚠ 조항 60": "897 은 3,710행/11도메인이다. 그 540 을 여기 붙이지 않는다"}

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    W = d0.weights(T); tot = sum(W.values())
    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}
    yh = {d: np.asarray(d0.dom[d][2], float)[post[d]] for d in doms}
    ns = {d: int(post[d].sum()) for d in doms}

    ref = json.load(open(ROOT / "runners/out890_ruler.json", encoding="utf-8"))
    th = json.load(open(ROOT / "runners/out891_thresh.json", encoding="utf-8"))
    dig = R890.digest_data(d0)
    wire = {"W1 자료 sha256": dig,
            "W1 890 과 동일": dig == ref["배선"]["ㄱ 자료 sha256"],
            "W2 가중 합": tot, "W2 도메인": len(W),
            "🔴 thresh891 에서 읽은 값": {
                "R5(옛 문턱)": th["자 다섯"]["🔴 R5 합성 2σ = 채택 문턱"],
                "씨앗 성분": th["자 다섯"]["성분"]["씨앗(12대12 환산)"],
                "행 짝 성분": th["자 다섯"]["성분"]["행 짝(널)"],
                "칸2 통과(R5)": th["판정"]["칸2 통과(R5)"]}}
    assert wire["W1 890 과 동일"] and tot == 3775, "🔴 배선 중단"
    seed_comp = wire["🔴 thresh891 에서 읽은 값"]["씨앗 성분"]
    old_row = wire["🔴 thresh891 에서 읽은 값"]["행 짝 성분"]
    say(json.dumps(wire, ensure_ascii=False))

    # ── 적합 캐시(예측) ────────────────────────────────────────────────
    CACHE = ROOT / "runners/out891_fits.npz"
    assert CACHE.exists(), "🔴 out891_fits.npz 가 없다 --- W5 불가"
    z = np.load(CACHE, allow_pickle=True)
    PR = {k: {d: [z[f"p{k}_{d}_{i}"] for i in range(len(SEEDS))] for d in doms}
          for k in ARMS}
    for k in ARMS:
        for d in doms:
            assert len(PR[k][d][0]) == ns[d], f"🔴 {d} 예측 길이 != post 행수"
    RK = {k: {d: [rankdata(PR[k][d][i]) for i in range(len(SEEDS))] for d in doms}
          for k in ARMS}

    def ens(rk, seeds):
        return np.mean([rk[s] for s in seeds], axis=0)

    E = {(k, "full"): {d: ens(RK[k][d], SEEDS) for d in doms} for k in ARMS}
    for k in ARMS:
        E[(k, "A")] = {d: ens(RK[k][d], HALF_A) for d in doms}
        E[(k, "B")] = {d: ens(RK[k][d], HALF_B) for d in doms}
    sp = R890.sp
    NAMES = ["REAL(K2full−K1full)", "NULL_K1(A−B)", "NULL_K2(A−B)", "LVL_K1full"]

    def stats_on(idx_by_dom):
        num = {n: 0.0 for n in NAMES}; den = {n: 0.0 for n in NAMES}
        for d in doms:
            i = idx_by_dom[d]; y = yh[d][i]
            v = {"REAL(K2full−K1full)": sp(E[(2, "full")][d][i], y) - sp(E[(1, "full")][d][i], y),
                 "NULL_K1(A−B)": sp(E[(1, "A")][d][i], y) - sp(E[(1, "B")][d][i], y),
                 "NULL_K2(A−B)": sp(E[(2, "A")][d][i], y) - sp(E[(2, "B")][d][i], y),
                 "LVL_K1full": sp(E[(1, "full")][d][i], y)}
            for n in NAMES:
                if np.isfinite(v[n]):
                    num[n] += v[n] * W[d]; den[n] += W[d]
        return {n: (num[n] / den[n] if den[n] else np.nan) for n in NAMES}

    # ── 날짜 ───────────────────────────────────────────────────────────
    rows_idol = idolset._rows(wide_post=True)
    grp_idol = np.array([str(r.get("group_name") or "") for r in rows_idol])
    DATE, meaning, w4 = {}, {}, {}
    for d in doms:
        arr, src, ok = dates_for(d, len(d0.dom[d][2]), d0.yr[d])
        w4[d] = ok
        meaning[d] = src
        DATE[d] = None if not ok else arr[post[d]]

    # ── 군집 세기 ──────────────────────────────────────────────────────
    per = {}
    for d in doms:
        n = ns[d]
        if DATE[d] is None:
            per[d] = {"채점 후보행(post)": n, "🔴 날짜": "모른다 — " + meaning[d]}
            continue
        day = np.array([s if s and s[:4].isdigit() else f"미상#{i}"
                        for i, s in enumerate(DATE[d])])
        mon = np.array([s[:7] if s and s[:4].isdigit() else f"미상#{i}"
                        for i, s in enumerate(DATE[d])])
        unk = int(sum(1 for s in DATE[d] if not (s and s[:4].isdigit())))
        Kd, Km = len(np.unique(day)), len(np.unique(mon))
        sz = np.bincount(np.unique(day, return_inverse=True)[1])
        per[d] = {"채점 후보행(post)": n, "판 가중(라벨 유한)": int(W.get(d, 0)),
                  "날짜 출처": meaning[d],
                  "날짜 미상 행": unk,
                  "일 군집 수": Kd, "일 m̄": round(n / Kd, 3),
                  "일 최대 군집": int(sz.max()), "단독 군집 비율": round(float((sz == 1).mean()), 3),
                  "월 군집 수": Km, "월 m̄": round(n / Km, 3)}
        say(f"  {d}: n={n} 일군집 {Kd} (m̄ {n/Kd:.2f} · 최대 {sz.max()}) · "
            f"월군집 {Km} (m̄ {n/Km:.2f}) · 미상 {unk} · {meaning[d]}")

    res["🔴 날짜의 뜻이 도메인마다 다르다"] = {d: meaning[d] for d in doms}
    res["날짜 군집"] = per

    # ── ICC ────────────────────────────────────────────────────────────
    icc = {}
    for d in doms:
        if DATE[d] is None:
            icc[d] = "모른다 — 날짜 없음"; continue
        y = yh[d]; p = PR[1][d][0]           # 챔피언(K=1) 씨앗 0
        ok = np.isfinite(y) & np.isfinite(p)
        if ok.sum() < 20:
            icc[d] = "모른다 — 유한행 20 미만"; continue
        day = np.array([s if s and s[:4].isdigit() else f"미상#{i}"
                        for i, s in enumerate(DATE[d])])[ok]
        mon = np.array([s[:7] if s and s[:4].isdigit() else f"미상#{i}"
                        for i, s in enumerate(DATE[d])])[ok]
        yy, pp = y[ok], p[ok]
        r = rankdata(yy) / len(yy) - rankdata(pp) / len(pp)
        a_day, a_mon = icc_oneway(r, day), icc_oneway(r, mon)
        lab = icc_oneway(rankdata(yy) / len(yy), day)
        icc[d] = {
            "잔차 ICC(일)": a_day or "잴 수 없다(전부 단독 군집)",
            "잔차 ICC(월)": a_mon or "잴 수 없다",
            "라벨 ICC(일 · 병기)": (lab["ICC"] if lab else "잴 수 없다"),
        }
        if a_day:
            say(f"  ICC {d}: 일 {a_day['ICC']:+.4f} m̄ {a_day['m̄(N/K)']:.2f} "
                f"m0 {a_day['m0']:.2f} DEFF {a_day['DEFF(공식 · m̄)']:.3f} "
                f"n_eff {a_day['n_eff(m̄)']:.1f}"
                + (f" · 월 {a_mon['ICC']:+.4f} DEFF {a_mon['DEFF(공식 · m̄)']:.3f}"
                   if a_mon else ""))
        else:
            say(f"  ICC {d}: 일 잴 수 없다(전부 단독)")
    res["ICC · DEFF · n_eff"] = icc

    # ── 부트: 행 / 일 군집 / 월 군집 ───────────────────────────────────
    cl_day, cl_mon = {}, {}
    for d in doms:
        if DATE[d] is None:
            cl_day[d] = cl_mon[d] = [np.array([i]) for i in range(ns[d])]
            continue
        day = np.array([s if s and s[:4].isdigit() else f"미상#{i}"
                        for i, s in enumerate(DATE[d])])
        mon = np.array([s[:7] if s and s[:4].isdigit() else f"미상#{i}"
                        for i, s in enumerate(DATE[d])])
        cl_day[d] = cl_from(day); cl_mon[d] = cl_from(mon)
    # 아이돌 프랜차이즈 ∪ 날짜(합집합 군집) --- 병기
    cl_idol_fr, _wc = PB.clusters_of(list(grp_idol[post["아이돌"]]))

    def boot(mode, Bn, seed):
        rng = np.random.default_rng(seed)
        draws = {n: np.empty(Bn) for n in NAMES}
        for b in range(Bn):
            idx = {}
            for d in doms:
                if mode == "row":
                    if d == "아이돌":
                        cl = cl_idol_fr
                        idx[d] = np.concatenate([cl[i] for i in
                                                 rng.integers(0, len(cl), len(cl))])
                    else:
                        idx[d] = rng.integers(0, ns[d], ns[d])
                else:
                    cl = (cl_day if mode == "day" else cl_mon)[d]
                    idx[d] = np.concatenate([cl[i] for i in
                                             rng.integers(0, len(cl), len(cl))])
            v = stats_on(idx)
            for n in NAMES:
                draws[n][b] = v[n]
            if (b + 1) % 2500 == 0:
                say(f"    부트[{mode}] {b+1}/{Bn} ({time.time()-t0:.0f}s)")
        return draws

    def summ(a):
        a = a[np.isfinite(a)]
        return {"SD": round(float(a.std(ddof=1)), 5),
                "2σ": round(2 * float(a.std(ddof=1)), 5),
                "lo(2.5%)": round(float(np.percentile(a, 2.5)), 5),
                "hi(97.5%)": round(float(np.percentile(a, 97.5)), 5)}

    say("부트 ① 행 단위(thresh891 재현 · W5) ...")
    d_row = boot("row", B, RNG_890)
    say("부트 ② 일 군집 ...")
    d_day = boot("day", B, RNG_890)
    say("부트 ③ 월 군집 ...")
    d_mon = boot("mon", B, RNG_890)

    S = {"행": {n: summ(d_row[n]) for n in NAMES},
         "일 군집": {n: summ(d_day[n]) for n in NAMES},
         "월 군집": {n: summ(d_mon[n]) for n in NAMES}}
    res["부트 재표집 단위별"] = S

    w5 = {"내 NULL_K1 SD": S["행"]["NULL_K1(A−B)"]["SD"],
          "891 NULL_K1 SD": th["부트"]["NULL_K1(A−B)"]["SD"],
          "내 NULL_K2 SD": S["행"]["NULL_K2(A−B)"]["SD"],
          "891 NULL_K2 SD": th["부트"]["NULL_K2(A−B)"]["SD"],
          "내 LVL_K1full SD": S["행"]["LVL_K1full"]["SD"],
          "891 LVL_K1full SD": th["부트"]["LVL_K1full"]["SD"]}
    w5["W5 통과"] = (w5["내 NULL_K1 SD"] == w5["891 NULL_K1 SD"]
                     and w5["내 NULL_K2 SD"] == w5["891 NULL_K2 SD"])
    wire["W5 thresh891 행 부트 재현"] = w5
    say(json.dumps(w5, ensure_ascii=False))

    # ── 판 수준 DEFF (실측) ────────────────────────────────────────────
    deff_emp = {}
    for lvl, dd in (("일 군집", S["일 군집"]), ("월 군집", S["월 군집"])):
        deff_emp[lvl] = {n: round((dd[n]["SD"] / S["행"][n]["SD"]) ** 2, 3)
                         for n in NAMES}
    res["🔴 판 수준 실측 DEFF = (SD_군집/SD_행)²"] = deff_emp

    # ── 새 문턱 후보 ───────────────────────────────────────────────────
    def r5(row_sd):
        return 2 * float(np.hypot(seed_comp, row_sd))

    new = {}
    for lvl, dd in (("행(옛 · 891)", S["행"]), ("일 군집", S["일 군집"]),
                    ("월 군집", S["월 군집"])):
        rn = max(dd["NULL_K1(A−B)"]["SD"], dd["NULL_K2(A−B)"]["SD"])
        arm = "K=1" if dd["NULL_K1(A−B)"]["SD"] >= dd["NULL_K2(A−B)"]["SD"] else "K=2"
        new[lvl] = {"행 짝 성분(SD)": rn, "고른 팔": arm,
                    "씨앗 성분(891 에서 읽음)": seed_comp,
                    "R5 = 2·hypot": round(r5(rn), 5),
                    "옛 R5 대비 배수": round(r5(rn) / OLD_R5, 3)}
    new["🔴 대조"] = {"891 행 짝 성분": old_row,
                      "내 행 짝 성분": new["행(옛 · 891)"]["행 짝 성분(SD)"],
                      "일치": abs(new["행(옛 · 891)"]["행 짝 성분(SD)"] - old_row) < 1e-9}
    res["🔴 문턱 후보(제안 · 정본 안 바꾼다)"] = new

    # ── 새 문턱으로 12도메인 재판정(참고 · 채택 아님) ──────────────────
    tbl891 = th["도메인별 새 자 적용"] if "도메인별 새 자 적용" in th else None
    b898 = json.load(open(ROOT / "runners/out898_board.json", encoding="utf-8"))
    contrib = {d: abs(b898["도메인별"][d]["판 기여 Δ"]) for d in doms
               if d in b898.get("도메인별", {})}
    pass_tbl = {}
    for lvl in ("행(옛 · 891)", "일 군집", "월 군집"):
        R = new[lvl]["R5 = 2·hypot"]
        pass_tbl[lvl] = {"R5": R,
                         "통과 도메인": [d for d, c in contrib.items() if c >= R],
                         "통과 수": sum(1 for c in contrib.values() if c >= R)}
    res["참고 — 898 짝Δ 기여가 각 문턱을 넘는 도메인(🔴 채택 아님)"] = pass_tbl
    res["898 도메인 기여(읽어서 옮김)"] = contrib
    res["배선"] = wire
    res["_tbl891_있음"] = tbl891 is not None

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    say(f"→ {OUT} ({time.time()-t0:.0f}s)")


if __name__ == "__main__":
    main()
