"""노트 792(791 의 진단에서 나왔다) — **되돌림이 문제였나.** 능력 자를 세 방식으로 다시 잰다.

노트 691 은 되돌림을 **등백분위 하나**로만 했고 결론이 *"등백분위 사상에서"*
로 한정돼 있었다. 여기서 셋을 나란히 두고 **위약에도 같은 되돌림을 적용**한다.
재는 코드는 `lab/calib.py` 에 있다(규약 41).
"""
import json
import sys
import time

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/"
                   "ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import calib as C, forms

CLS = forms.REGISTRY["F18_bagboost"]["cls"]
SEEDS = (0, 1, 2, 3)          # 자 자신의 잡음(노트 691 과 같은 넷)
T = 2025.0
INVS = ("유보백분위", "기후값")


def one_seed(data, seed):
    """씨앗 하나 · 되돌림 셋 × (진짜 · 위약) 의 도메인별 자."""
    fc = C.forecasts(lambda: CLS(seed=seed), data, T=T, seed=seed)
    rng = np.random.default_rng(1000 + seed)
    out = {inv: {"진짜": {}, "위약": {}} for inv in INVS}
    spread = {}
    for d, (ptr, ytr, pho, yho) in fc.items():
        spread[d] = C.label_spread(yho)
        for arm in ("진짜", "위약"):
            #: 🔴 위약은 **학습 예보도** 섞는다 --- 되돌림까지 위약이어야
            #: 되돌림의 효과와 예보의 효과가 안 섞인다
            if arm == "진짜":
                a_tr, a_ho = ptr, pho
            else:
                a_tr = C.shuffle_in_domain(ptr, rng)
                a_ho = C.shuffle_in_domain(pho, rng)
            # (4) 🔴 유보 안 백분위 --- 드리프트 상쇄(전이적)
            yh, _ = C.inv_holdout_pct(a_tr, ytr, a_ho)
            #: 구간은 학습 라벨 분위를 예보 백분위에 따라 좁힌다(±0.10 창)
            lo, hi = _pct_interval(ytr, a_ho)
            out["유보백분위"][arm][d] = C.rulers(yh, yho, lo, hi)
            # 기후값 --- **이름 붙인 기준선**(791 이 위약 = 기후값임을 확인)
            cm, cl, ch = C.climatology(ytr, len(yho))
            out["기후값"][arm][d] = C.rulers(cm, yho, cl, ch)
        for inv in INVS:
            for arm in ("진짜", "위약"):
                out[inv][arm][d].update(spread[d])
    return out, spread, C.wiring(fc, data, T=T)


def _pct_interval(ytr, pho, w=0.10):
    """유보 예보 백분위 ±w 창에 해당하는 **학습 라벨** 분위를 구간으로."""
    u = (np.argsort(np.argsort(pho)) + 0.5) / len(pho)
    lo = np.percentile(ytr, np.clip((u - w) * 100, 0, 100))
    hi = np.percentile(ytr, np.clip((u + w) * 100, 0, 100))
    return lo, hi


def _win_interval(ptr, ytr, pho, w=0.05):
    """노트 691 의 구간 --- 같은 예보 백분위 창(±0.05)의 학습 라벨 10~90분위."""
    srt = np.sort(ptr)
    pct_tr = (np.searchsorted(srt, ptr, side="left") / max(len(srt) - 1, 1))
    pct_ho = (np.searchsorted(srt, pho, side="left") / max(len(srt) - 1, 1))
    lo = np.empty(len(pho))
    hi = np.empty(len(pho))
    for i, u in enumerate(pct_ho):
        m = np.abs(pct_tr - u) <= w
        v = ytr[m] if m.sum() >= 10 else ytr
        lo[i], hi[i] = np.percentile(v, 10), np.percentile(v, 90)
    return lo, hi


def pooled(per_dom, key, wts):
    """판 가중 --- 유보 채점 행수로 가중(노트 691 과 같은 방식)."""
    ks = [d for d in per_dom if per_dom[d].get(key) is not None]
    if not ks:
        return None
    w = np.array([wts[d] for d in ks], float)
    v = np.array([per_dom[d][key] for d in ks], float)
    return float((w * v).sum() / w.sum())


def main():
    t0 = time.time()
    data = FF.shell(FF.base())
    runs, spread, wire = [], None, None
    for s in SEEDS:
        o, sp, w = one_seed(data, s)
        runs.append(o)
        spread = spread or sp
        wire = wire or w
        print(f"  씨앗 {s} 끝 · {round(time.time()-t0,1)}초", flush=True)

    doms = sorted(runs[0][INVS[0]]["진짜"])
    wts = {d: runs[0][INVS[0]]["진짜"][d]["행"] for d in doms}
    print(json.dumps({"배선": wire, "유보 채점 행": wts,
                      "합": sum(wts.values())}, ensure_ascii=False), flush=True)

    res = {}
    for inv in INVS:
        block = {}
        for key in ("자릿수 오차 비율", "중앙절대오차", "구간 덮음"):
            arms = {}
            for arm in ("진짜", "위약"):
                vals = [pooled(r[inv][arm], key, wts) for r in runs]
                arms[arm] = {"씨앗별": [round(v, 4) for v in vals],
                             "평균": round(float(np.mean(vals)), 4),
                             "**씨앗 SD**": round(float(np.std(vals, ddof=1)), 5)}
            d = arms["진짜"]["평균"] - arms["위약"]["평균"]
            noise = max(arms["진짜"]["**씨앗 SD**"], arms["위약"]["**씨앗 SD**"])
            block[key] = {**arms, "**진짜−위약**": round(d, 4),
                          "자 잡음(씨앗 SD)": round(noise, 5),
                          "**잡음 3배 밖**": bool(abs(d) > 3 * noise)}
        #: 기울기는 **도메인별 부호 일치**로만(판 평균은 발산 · 노트 691)
        agree = 0
        det = {}
        for d in doms:
            rt = np.mean([r[inv]["진짜"][d]["기울기"] for r in runs
                          if r[inv]["진짜"][d]["기울기"] is not None])
            rp = np.mean([r[inv]["위약"][d]["기울기"] for r in runs
                          if r[inv]["위약"][d]["기울기"] is not None])
            det[d] = [round(float(rt), 3), round(float(rp), 3)]
            agree += int(abs(rt - 1) < abs(rp - 1))
        block["기울기(1 에 더 가까운 도메인 수)"] = {
            "진짜가 가까움": f"{agree}/{len(doms)}", "도메인별 [진짜, 위약]": det}
        res[inv] = block
        dg = block["자릿수 오차 비율"]
        print(f"[{inv}] 자릿수 진짜 {dg['진짜']['평균']:.4f} 대 위약 "
              f"{dg['위약']['평균']:.4f} · 차 {dg['**진짜−위약**']:+.4f} · "
              f"잡음3배밖 {dg['**잡음 3배 밖**']} · 덮음 진짜 "
              f"{block['구간 덮음']['진짜']['평균']:.4f} 대 위약 "
              f"{block['구간 덮음']['위약']['평균']:.4f}", flush=True)

    # ── IQR 가설 --- 진짜와 위약이 **같이** 정렬해야 라벨 분포의 자다 ──
    iqr = {}
    for inv in INVS:
        row = {}
        for arm in ("진짜", "위약"):
            per = {d: {k: float(np.mean([r[inv][arm][d][k] for r in runs]))
                       for k in ("자릿수 오차 비율",)} for d in doms}
            for d in doms:
                per[d].update(spread[d])
            for sk in ("IQR", "자리폭", "SD"):
                rho, n = C.align(per, "자릿수 오차 비율", sk)
                row[f"{arm}·{sk}"] = None if rho is None else round(rho, 3)
        iqr[inv] = row
    ok_iqr = {}
    for inv in INVS:
        a, b = iqr[inv]["진짜·IQR"], iqr[inv]["위약·IQR"]
        ok_iqr[inv] = bool(a is not None and b is not None
                           and a >= 0.7 and b >= 0.7 and abs(a - b) <= 0.15)

    # ── 판정 --- 🔴 기준선은 위약이 아니라 **기후값**(사전등록 792) ─────
    def val(inv, key):
        return res[inv][key]["진짜"]["평균"]

    def sd(inv, key):
        return max(res[inv][key]["진짜"]["**씨앗 SD**"],
                   res[inv][key]["위약"]["**씨앗 SD**"])
    dg_new, dg_clim = val("유보백분위", "자릿수 오차 비율"), val("기후값", "자릿수 오차 비율")
    cv_new, cv_clim = val("유보백분위", "구간 덮음"), val("기후값", "구간 덮음")
    noise = max(sd("유보백분위", "자릿수 오차 비율"), sd("기후값", "자릿수 오차 비율"))
    diff = dg_new - dg_clim
    ga = bool(diff < -3 * noise)
    gb = bool(abs(diff) <= 3 * noise)
    gc = bool(diff > 3 * noise)
    wid_new = float(np.mean([np.mean([r["유보백분위"]["진짜"][d]["구간 폭 중앙값"]
                                      for r in runs]) for d in doms]))
    wid_clim = float(np.mean([np.mean([r["기후값"]["진짜"][d]["구간 폭 중앙값"]
                                       for r in runs]) for d in doms]))

    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "도메인": doms, "유보 합": sum(wts.values()),
        "판정선(T6 이 미리 못박음)": C.DIGIT_LINE,
        "되돌림별": res,
        "IQR 가설 (진짜·위약이 같이 정렬해야 라벨 분포의 자)": iqr,
        "**IQR 판정(둘 다 ≥0.7 이고 0.15 안)**": ok_iqr,
        "🔴 자릿수 유보백분위 대 기후값": [round(dg_new, 4), round(dg_clim, 4),
                                  "차 " + f"{diff:+.4f}", "잡음3배 " + f"{3*noise:.4f}"],
        "🔴 덮음 유보백분위 대 기후값": [round(cv_new, 4), round(cv_clim, 4)],
        "구간 폭 중앙값 유보백분위 대 기후값": [round(wid_new, 4), round(wid_clim, 4)],
        "**판정 (가) 드리프트가 원인 --- 기후값보다 3배 낮다**": ga,
        "**판정 (나) 정보 부족 --- 기후값과 붙는다**": gb,
        "**판정 (다) 더 나쁘다 --- 드리프트를 없애도 해롭다**": gc,
        "예측 ① (나) 이고 자릿수 0.16~0.30": [gb, round(dg_new, 4)],
        "예측 ② 덮음 0.70~0.85": [bool(0.70 <= cv_new <= 0.85), round(cv_new, 4)],
        "예측 ③ 구간 폭이 기후값과 비슷":
            [bool(abs(wid_new - wid_clim) / max(wid_clim, 1e-9) < 0.2),
             round(wid_new, 4), round(wid_clim, 4)],
        "🔴 도메인별 자릿수 [유보백분위, 기후값]":
            {d: [round(float(np.mean([r["유보백분위"]["진짜"][d]["자릿수 오차 비율"]
                                      for r in runs])), 3),
                 round(float(np.mean([r["기후값"]["진짜"][d]["자릿수 오차 비율"]
                                      for r in runs])), 3)] for d in doms},
        "🔴 도메인별 덮음 [유보백분위, 기후값]":
            {d: [round(float(np.mean([r["유보백분위"]["진짜"][d]["구간 덮음"]
                                      for r in runs])), 3),
                 round(float(np.mean([r["기후값"]["진짜"][d]["구간 덮음"]
                                      for r in runs])), 3)] for d in doms},
        "IQR 판정(참고)": ok_iqr,
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
