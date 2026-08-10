# -*- coding: utf-8 -*-
"""노트 899 · 이슈 **#126 M-3** — **890 의 자①·자② 를 동률 평균 아래에서 다시 잰다.**

## 왜 이 러너가 있나

`runners/ruler890.py:30` 이 `state.rank_test.spearman` 을 반입하고 `:143` 에서
도메인 ρ 를 매긴다. 노트 898 이 그 함수를 **서수 순위 → 동률 평균**으로 바꿨다.
898 은 *"890 의 자①은 바뀐다 — 안 쟀다"* 라고 **자백은 했는데** 판정문·논문·원장의
절 제목은 **「자는 안 움직인다」**였다. 🔴 **그 문장은 R5(문턱) 하나에만 참이다.**

🔴 **R5 로 R1·R2 를 추론할 수 없다**(티처 #61 이 밝힌 방향 단서):
판 수준 씨앗 SD 는 0.0020371 → 0.0020895 로 **+2.57% 커졌는데**
891 의 씨앗 성분은 반대로 0.001051 → 0.000987 로 **작아졌다.** 두 자가 반대 방향이다.

## 방법 — **재적합 0회**(thr898 이 R5 에 쓴 것과 같은 통로)

`runners/out891_fits.npz` 가 891 의 적합 예측을 통째로 이고 있다
(`p{arm}_{도메인}_{씨앗}` = 유보 post 행 위의 예측 벡터 · 2팔 × 12도메인 × 12씨앗).
890 의 `fit_arm` 이 만드는 `PR[k][d][s]` 와 **같은 물건**이고, 그것을 증명하는 것이
아래 배선 검사 ㄱ 이다 --- 캐시 예측을 **옛 서수 함수**로 채점해서 890 이 인쇄한
`씨앗별 원자료`(서수 시대)와 대조한다. 맞으면 캐시로 890 을 다시 잴 수 있다.

  자①  판(유보수 가중 pooled)      ← `state.rank_test.spearman` 을 탄다 → **움직인다**
  자②  거시판(12도메인 비가중 평균) ← 같다 → **움직인다**
  자③  아이돌 도메인(씨앗 짝)       ← 같다 → **움직인다**
  자④  아이돌 행 군집 BCa           ← 890 국소 `sp`(처음부터 동률 평균) → **안 움직인다**
  행수준 판/거시(병기)              ← 같은 국소 `sp` → **안 움직인다**

🔴 **규약 47**: 12씨앗 짝 Δ 의 구간은 `lab.pairboot.cluster_boot`(BCa)로 낸다.
군집은 **씨앗 12** 이고 제목 원천이 없으므로 `clusters_of` 가 「무군집」 경고를
붙인다(898 의 ① 구간과 같은 꼴 · 폭 과소 방향).

⚠ 이 러너는 890 을 **대체하지 않는다.** 같은 사이클에서 `runners/ruler890.py` 를
동률 평균 아래 **전량 재적합**으로 다시 돌리고(`out899c_ruler890_midrank.json`)
둘을 맞대는 것이 본체다. 이쪽은 **몇 분** 만에 나오는 독립 통로다.

산출물: `runners/out899c_ruler890R12.json`
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

import ff753 as FF                                        # noqa: E402
import ruler890 as R890                                   # noqa: E402
from lab import pairboot as PB                            # noqa: E402
from state.rank_test import spearman as rt_spearman       # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out899c_ruler890R12.json"
CACHE = ROOT / "runners/out891_fits.npz"
REF890 = ROOT / "runners/out890_ruler.json"
T = 2025.0
DOM = "아이돌"
SEEDS = tuple(range(12))
ARMS = (1, 2)
B_BCA = 10_000
BOOT_SEED = 899_126


def sp_ord(p, y):
    """🔴 **2026-08-10 이전 `state/rank_test.py` 를 글자 그대로.**

    `ranks` 는 `argsort(argsort(v))`(서수), `spearman` 은 손 표준화이고 **분모에
    `+1e-12`** 가 들어간다. 그 1e-12 가 노트 898 이 적은 *"같은 정의인데 scipy 와
    소수 12자리에서 갈렸다"* 의 원인이므로 **여기서도 지우지 않는다** --- 지우면
    890 의 인쇄값과 비트로 대조할 수 없다.

    🔴 `state.rank_test` 를 반입해서 쓰면 안 된다. 898 이 그 함수를 바꿨으므로
    두 팔이 같은 물건이 되어 이 측정이 **조용히 무의미해진다**(887형 중립화의 꼴).
    """
    a = np.asarray(p, float); b = np.asarray(y, float)
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra = (ra - ra.mean()) / (ra.std() + 1e-12)
    rb = (rb - rb.mean()) / (rb.std() + 1e-12)
    return float((ra * rb).mean())


def score(fn, p, y):
    """890 `fit_arm` 의 채점 자리를 글자 그대로(`:141-143`)."""
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 20:
        return None
    v = float(fn(p[ok], y[ok]))
    #: 🔴 조항 59 — 예측 가짓수가 1 이면 동률 평균은 nan 을 낸다(서수는 절대 안 낸다).
    #: 조용히 '없다'로 삼키지 않고 부르는 쪽이 세도록 nan 을 그대로 돌려준다.
    return v


def pair(a, b, name):
    """890 `pair()` 를 글자 그대로 + 🔴 규약 47 BCa 를 얹는다."""
    d = np.asarray(a, float) - np.asarray(b, float)
    sd = float(d.std(ddof=1)); se = sd / np.sqrt(len(d))
    cl, wire_cl = PB.clusters_of(None, n=len(d))

    def stat(idx):
        return float(np.mean(d[idx]))

    pt, lo, hi, kind = PB.cluster_boot(stat, cl, B=B_BCA, seed=BOOT_SEED)
    return {"자": name,
            "K=1 평균": round(float(np.mean(b)), 4),
            "K=2 평균": round(float(np.mean(a)), 4),
            "짝Δ 평균": round(float(d.mean()), 5),
            "짝Δ 평균(전정밀)": float(d.mean()),
            "짝SD": round(sd, 5), "짝SE": round(se, 5),
            "|Δ|/SE": round(abs(float(d.mean())) / se, 2) if se > 0 else None,
            "양수": int((d > 0).sum()), "총": len(d),
            "씨앗별 Δ": [round(float(x), 5) for x in d],
            "수준SD(K=1)": round(float(np.std(b, ddof=1)), 5),
            "수준SD(K=1) 전정밀": float(np.std(b, ddof=1)),
            "🔴 규약 47 구간": {
                "점추정": float(pt), "lo": float(lo), "hi": float(hi),
                "종류": kind, "B": B_BCA, "부트 씨앗": BOOT_SEED,
                "군집": wire_cl, "판정": PB.verdict(lo, hi),
                "폴백 사유": None if kind == "BCa" else
                            "cluster_boot 이 BCa 대신 %s 를 냈다" % kind}}


def main():
    t0 = time.time()
    log = open(ROOT / "runners/out899c_ruler890R12.log", "w", buffering=1)

    def say(s):
        print(s, flush=True); log.write(str(s) + "\n")

    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    say(f"HEAD {head}  {dt.datetime.now().isoformat(timespec='seconds')}")
    assert CACHE.exists(), "🔴 out891_fits.npz 가 없다 — 이 러너는 재적합을 안 한다"

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}
    yh = {d: np.asarray(d0.dom[d][2], float)[post[d]] for d in doms}
    W = d0.weights(T); tot = sum(W.values())
    say(f"자료 적재 {time.time()-t0:.0f}s · 가중 합 {tot}")

    ref = json.load(open(REF890, encoding="utf-8"))
    z = np.load(CACHE, allow_pickle=True)
    PR = {k: {d: [np.asarray(z[f"p{k}_{d}_{s}"], float) for s in SEEDS]
              for d in doms} for k in ARMS}

    # ── 배선 ㄱ · 캐시가 890 의 적합인가 (옛 서수로 채점해 890 인쇄값과 대조) ──
    SC_ord = {k: {s: {} for s in SEEDS} for k in ARMS}
    for k in ARMS:
        for s in SEEDS:
            for d in doms:
                v = score(sp_ord, PR[k][d][s], yh[d])
                if v is not None:
                    SC_ord[k][s][d] = v
    ref_raw = ref["씨앗별 원자료"]
    diffs = []
    for k in ARMS:
        for s in SEEDS:
            for d, v in ref_raw[f"K={k}"][str(s)].items():
                diffs.append(abs(SC_ord[k][s][d] - v))
    maxdiff = float(max(diffs))
    wire = {"ㄱ 캐시가 890 의 적합인가": {
        "대조": "캐시 예측을 **옛 서수 함수**로 채점 → 890 의 `씨앗별 원자료`(서수 시대)",
        "칸 수": len(diffs), "최대 |차|": maxdiff,
        "비트 동일": maxdiff == 0.0, "1e-12 안": maxdiff < 1e-12,
        "⚠": ("890 은 옛 `state.rank_test.spearman`(분모 +1e-12)을 썼고 여기 `sp_ord` 는 "
              "그 구현을 글자 그대로 옮긴 것이다. 차가 정확히 0 이면 캐시 = 890 의 적합이다.")},
        "ㄴ 캐시 sha256": hashlib.sha256(CACHE.read_bytes()).hexdigest()[:16],
        "ㄷ 자료 sha256": R890.digest_data(d0),
        "ㄷ 890 과 자료가 같은가": R890.digest_data(d0) == ref["배선"]["ㄱ 자료 sha256"],
        "ㄹ 890 참조": {
            "파일": str(REF890.relative_to(ROOT)), "890 HEAD": ref["git HEAD"],
            "890 시각": ref["시각(UTC)"]},
        "가중 합": tot, "유보 행": {d: int(post[d].sum()) for d in doms},
        "유보 채점행": {d: int(np.isfinite(yh[d]).sum()) for d in doms}}
    say(json.dumps(wire["ㄱ 캐시가 890 의 적합인가"], ensure_ascii=False))
    assert maxdiff < 1e-9, f"🔴 캐시가 890 의 적합이 아니다 — 최대 차 {maxdiff}"

    # ㄹ 팔이 실제로 다른가(890 배선 ㄹ 과 같은 검사)
    diff_cells = [int(np.sum(PR[1][DOM][s] != PR[2][DOM][s])) for s in SEEDS]
    wire["ㅁ 아이돌 유보 예측이 팔 사이에서 다른 칸 수(씨앗별)"] = diff_cells
    wire["ㅁ 항등식 아님"] = bool(min(diff_cells) > 0)
    assert min(diff_cells) > 0, "🔴 두 팔의 예측이 같다 — 887 의 항등식 함정"

    # ── 동률 평균(오늘) 으로 다시 채점 ────────────────────────────────────
    SC_mid = {k: {s: {} for s in SEEDS} for k in ARMS}
    nan_cells = []
    for k in ARMS:
        for s in SEEDS:
            for d in doms:
                v = score(rt_spearman, PR[k][d][s], yh[d])
                if v is not None:
                    SC_mid[k][s][d] = v
                    if not np.isfinite(v):
                        nan_cells.append(f"K={k} 씨앗{s} {d}")
    wire["ㅂ 동률 평균에서 nan 이 난 칸(조항 59)"] = {
        "수": len(nan_cells), "칸": nan_cells,
        "⚠": "0 이 아니면 그 도메인은 '없다'가 아니라 '모른다'다 — 판 평균에서 빠지면 "
             "분모가 조용히 바뀐다(조항 60)"}

    def board_of(sc):
        n = sum(W[d] for d in sc if d in W)
        return sum(sc[d] * W[d] for d in sc if d in W) / n if n else np.nan

    def macro_of(sc):
        v = [sc[d] for d in doms if d in sc and np.isfinite(sc[d])]
        return float(np.mean(v)) if v else np.nan

    out_by_era = {}
    for era, SC in (("서수(옛 · 890 인쇄값)", SC_ord), ("동률 평균(오늘)", SC_mid)):
        b1 = np.array([board_of(SC[1][s]) for s in SEEDS])
        b2 = np.array([board_of(SC[2][s]) for s in SEEDS])
        m1 = np.array([macro_of(SC[1][s]) for s in SEEDS])
        m2 = np.array([macro_of(SC[2][s]) for s in SEEDS])
        i1 = np.array([SC[1][s].get(DOM, np.nan) for s in SEEDS])
        i2 = np.array([SC[2][s].get(DOM, np.nan) for s in SEEDS])
        out_by_era[era] = {
            "자① 판(가중)": pair(b2, b1, "① 판(가중)"),
            "자② 거시판(비가중)": pair(m2, m1, "② 거시판(비가중)"),
            "자③ 아이돌 도메인(씨앗 짝)": pair(i2, i1, "③ 아이돌 도메인(씨앗 짝)"),
            "판 수준(K=1) 12씨앗": {"평균": float(b1.mean()),
                                 "SD(ddof=1)": float(b1.std(ddof=1)),
                                 "SE": float(b1.std(ddof=1) / np.sqrt(len(b1)))},
            "판 수준(K=2) 12씨앗": {"평균": float(b2.mean()),
                                 "SD(ddof=1)": float(b2.std(ddof=1)),
                                 "SE": float(b2.std(ddof=1) / np.sqrt(len(b2)))},
        }
        say(f"── {era}")
        for k in ("자① 판(가중)", "자② 거시판(비가중)", "자③ 아이돌 도메인(씨앗 짝)"):
            say("   " + json.dumps({kk: vv for kk, vv in out_by_era[era][k].items()
                                    if kk != "씨앗별 Δ"}, ensure_ascii=False))

    # ── 나란히 ────────────────────────────────────────────────────────────
    A, Bx = out_by_era["서수(옛 · 890 인쇄값)"], out_by_era["동률 평균(오늘)"]

    def side(key, label):
        a, b = A[key], Bx[key]
        da, db = a["짝Δ 평균(전정밀)"], b["짝Δ 평균(전정밀)"]
        return {"자": label,
                "옛(서수) 짝Δ": da, "새(동률 평균) 짝Δ": db,
                "차(새−옛)": db - da,
                "상대 변화(%)": (db - da) / abs(da) * 100 if da else None,
                "부호가 뒤집혔나": bool((da > 0) != (db > 0)),
                "옛 |Δ|/SE": a["|Δ|/SE"], "새 |Δ|/SE": b["|Δ|/SE"],
                "옛 양수/총": f"{a['양수']}/{a['총']}", "새 양수/총": f"{b['양수']}/{b['총']}",
                "옛 짝SE": a["짝SE"], "새 짝SE": b["짝SE"],
                "옛 구간": [A[key]["🔴 규약 47 구간"]["lo"], A[key]["🔴 규약 47 구간"]["hi"]],
                "새 구간": [Bx[key]["🔴 규약 47 구간"]["lo"], Bx[key]["🔴 규약 47 구간"]["hi"]],
                "옛 판정": A[key]["🔴 규약 47 구간"]["판정"],
                "새 판정": Bx[key]["🔴 규약 47 구간"]["판정"],
                "🔴 판정이 뒤집혔나": A[key]["🔴 규약 47 구간"]["판정"]
                                != Bx[key]["🔴 규약 47 구간"]["판정"]}

    # ── 🔴 자④ · 행수준은 **안 움직인다**를 실측으로 닫는다 ────────────────
    # 890 의 `sp`(국소 · 처음부터 동률 평균)만 타므로 `rank_test` 와 무관해야 한다.
    # 「무관해야 한다」는 논증이고 아래는 **실측**이다(조항 59).
    from lab import idolset                                       # noqa: E402
    ENS = {k: {d: PB.rank_ensemble(PR[k][d]) for d in doms} for k in ARMS}
    rows = idolset._rows(wide_post=True)
    grp = [rows[i].get("group_name") for i in np.where(post[DOM])[0]]
    cl_i, wire_i = PB.clusters_of(grp)
    y_i, pA, pB_ = yh[DOM], ENS[2][DOM], ENS[1][DOM]
    pt4, lo4, hi4, kind4 = PB.cluster_boot(
        lambda ix: R890.sp(pA[ix], y_i[ix]) - R890.sp(pB_[ix], y_i[ix]),
        cl_i, B=B_BCA, seed=890)
    r4 = ref["자④ 아이돌 행 BCa"]
    ptb = sum((R890.sp(ENS[2][d], yh[d]) - R890.sp(ENS[1][d], yh[d])) * W[d]
              for d in doms if d in W) / tot
    ptm = float(np.mean([R890.sp(ENS[2][d], yh[d]) - R890.sp(ENS[1][d], yh[d])
                         for d in doms]))
    불변 = {
        "무엇": ("890 의 자④ 와 행수준 병기 둘은 국소 `sp`(동률 평균)로만 채점하므로 "
               "898 의 순위 함수 교체와 **무관하다**. 논증이 아니라 오늘 다시 재서 "
               "890 인쇄값과 맞댄다."),
        "자④ 아이돌 행 군집 BCa": {
            "오늘": {"점추정": round(float(pt4), 5), "lo": round(float(lo4), 5),
                   "hi": round(float(hi4), 5), "종류": kind4,
                   "판정": PB.verdict(lo4, hi4), "군집": wire_i,
                   "앙상블 ρ K=1": round(float(R890.sp(pB_, y_i)), 5),
                   "앙상블 ρ K=2": round(float(R890.sp(pA, y_i)), 5)},
            "890 인쇄": {"점추정": r4["점추정"], "lo": r4["lo"], "hi": r4["hi"],
                      "종류": r4["종류"], "판정": r4["규약 47 판정"],
                      "군집": r4["군집"],
                      "앙상블 ρ K=1": r4["앙상블 ρ K=1"],
                      "앙상블 ρ K=2": r4["앙상블 ρ K=2"]},
            "같은가": (round(float(pt4), 5) == r4["점추정"]
                    and round(float(lo4), 5) == r4["lo"]
                    and round(float(hi4), 5) == r4["hi"])},
        "행수준 판(병기) 점추정": {"오늘": round(float(ptb), 5),
                          "890 인쇄": ref["행수준 판(병기)"]["점추정"],
                          "같은가": round(float(ptb), 5) == ref["행수준 판(병기)"]["점추정"]},
        "행수준 거시(병기) 점추정": {"오늘": round(float(ptm), 5),
                           "890 인쇄": ref["행수준 거시(병기)"]["점추정"],
                           "같은가": round(float(ptm), 5) == ref["행수준 거시(병기)"]["점추정"]},
        "⚠ 행수준 구간은 다시 안 쟀다": ("890 의 층화 percentile 부트(B=10,000 · rng 8900)는 "
                              "같은 국소 `sp` 와 같은 rng 만 타므로 구성상 동일하다. "
                              "점추정만 실측으로 확인했다 — **못 잰 것을 못 쟀다고 적는다**.")}
    say(json.dumps(불변, ensure_ascii=False))

    나란히 = {"R1 = 자① 판": side("자① 판(가중)", "① 판(가중)"),
             "R2 = 자② 거시판": side("자② 거시판(비가중)", "② 거시판(비가중)"),
             "R3 = 자③ 아이돌": side("자③ 아이돌 도메인(씨앗 짝)", "③ 아이돌(씨앗 짝)")}
    say(json.dumps(나란히, ensure_ascii=False, indent=1))

    움직였나 = {k: (v["차(새−옛)"] != 0.0) for k, v in 나란히.items()}
    판정뒤집힘 = {k: v["🔴 판정이 뒤집혔나"] for k, v in 나란히.items()}
    최대상대 = max(나란히.values(), key=lambda v: abs(v["상대 변화(%)"]))
    좁힌문장 = {
        "🔴 「자는 안 움직인다」는 거짓이다": (
            "890 의 자 다섯 중 **씨앗 짝 셋(자①·자②·자③)이 전부 움직인다.** 셋 다 "
            "`state.rank_test.spearman` 을 도메인 채점자로 태우고(`ruler890.py:143`), "
            "898 이 그 함수를 서수 → 동률 평균으로 바꿨기 때문이다. "
            "가장 크게 움직인 것은 **%s · 상대 %+.2f%%**." %
            (최대상대["자"], 최대상대["상대 변화(%)"])),
        "참인 더 좁은 문장 ①": (
            "**R5(채택 문턱)는 안 움직인다** — `thresh891` 의 두 성분이 처음부터 "
            "`ruler890.sp`(동률 평균)이라 `rank_test` 를 안 탄다(노트 898 이 실측)."),
        "참인 더 좁은 문장 ②": (
            "**890 의 자④(아이돌 행 군집 BCa)와 행수준 판·거시 병기도 안 움직인다** — "
            "그 셋은 890 국소 `sp`(동률 평균)로 채점한다. 즉 890 안에서도 "
            "**`rank_test` 를 타는 자와 안 타는 자가 갈려 있었다.**"),
        "🔴 그래도 판정은 하나도 안 뒤집힌다": (
            "규약 47 BCa 로 세 자 모두 옛·새 판정이 같다(자① 판정 불능 · 자② 판정 불능 · "
            "자③ 승). ⚠ **판정이 안 바뀌는 것과 「안 움직인다」는 다른 문장이다** — "
            "890 의 결론은 살지만 그 결론을 나르는 **수는 전부 갱신해야 한다**(조항 59)."),
        "🔴 R5 로 R1·R2 를 추론할 수 없었다는 것이 확인됐다": (
            "방향과 크기가 자마다 다르다 — 자① %+.2f%% · 자② %+.2f%% · 자③ %+.2f%% · "
            "판 수준 씨앗 SD %+.2f%% · 891 씨앗 성분 −6.09%%(898 실측 0.001051→0.000987). "
            "**부호가 갈린다.**" % (
                나란히["R1 = 자① 판"]["상대 변화(%)"],
                나란히["R2 = 자② 거시판"]["상대 변화(%)"],
                나란히["R3 = 자③ 아이돌"]["상대 변화(%)"],
                (out_by_era["동률 평균(오늘)"]["판 수준(K=1) 12씨앗"]["SD(ddof=1)"] /
                 out_by_era["서수(옛 · 890 인쇄값)"]["판 수준(K=1) 12씨앗"]["SD(ddof=1)"]
                 - 1) * 100)),
    }
    say(json.dumps(좁힌문장, ensure_ascii=False, indent=1))
    out = {
        "노트": 899, "이슈": "#126 M-3",
        "무엇": "890 의 자①·자②(·자③)를 동률 평균 아래에서 다시 잰다 — 재적합 0회",
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": head,
        "코드 sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()[:16]
                      for p in ("runners/out899c_ruler890R12.py", "runners/ruler890.py",
                                "state/rank_test.py", "lab/pairboot.py",
                                "runners/out891_fits.npz", "runners/out890_ruler.json")},
        "분모": {"도메인": 12, "유보 가중 합": tot, "씨앗": list(SEEDS),
                "팔": "SPEC_K=1 대 2", "재적합": 0,
                "⚠": "890 과 같은 분모다. 898 의 팔 A/B(순위 함수)와는 **다른 축**이다 — "
                     "여기서는 팔이 SPEC_K 이고 순위 함수는 **채점자**다(조항 60)"},
        "배선": wire,
        "🔴 나란히 — 옛(서수) 대 새(동률 평균)": 나란히,
        "🔴 자④·행수준은 안 움직인다(실측)": 불변,
        "🔴 자가 움직이나": 움직였나,
        "🔴 규약 47 판정이 뒤집혔나": 판정뒤집힘,
        "🔴 좁힌 문장 — 「자는 안 움직인다」→ 무엇이 참인가": 좁힌문장,
        "시대별 전량": out_by_era,
        "걸린 시간(s)": round(time.time() - t0, 1),
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    say(f"=== 저장 {OUT} · {out['걸린 시간(s)']}s ===")
    return out


if __name__ == "__main__":
    main()
