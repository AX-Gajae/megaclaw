"""노트 798 — **라벨이 넓은 도메인만은 절대값을 팔 수 있나.**

문턱은 **결과 무관 규칙**: 11개 도메인 유보 라벨 IQR 의 중앙값. 큰 쪽이
'넓은 무리'. 되돌림은 유보백분위(792 최선) 하나 · 기준선은 기후값(규약 43).
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
SEEDS = (0, 1, 2, 3)
T = 2025.0


def main():
    t0 = time.time()
    data = FF.shell(FF.base())

    #: ── 문턱 --- **라벨만 본다**(예보·오차를 안 본다) ────────────────
    fc0 = C.forecasts(lambda: CLS(seed=0), data, T=T, seed=0)
    iqr = {d: C.label_spread(yho)["IQR"] for d, (_, _, _, yho) in fc0.items()}
    med = float(np.median(list(iqr.values())))
    wide = sorted(d for d, v in iqr.items() if v > med)
    narrow = sorted(d for d, v in iqr.items() if v <= med)
    print(json.dumps({"도메인 IQR": {k: round(v, 4) for k, v in
                                  sorted(iqr.items(), key=lambda x: -x[1])},
                      "🔴 문턱(중앙값)": round(med, 4),
                      "넓은 무리": wide, "좁은 무리": narrow},
                     ensure_ascii=False), flush=True)

    runs = []
    for s in SEEDS:
        fc = C.forecasts(lambda s=s: CLS(seed=s), data, T=T, seed=s)
        per = {}
        for d, (ptr, ytr, pho, yho) in fc.items():
            yh, _ = C.inv_holdout_pct(ptr, ytr, pho)
            cm, cl, ch = C.climatology(ytr, len(yho))
            #: 구간 --- 기후값 구간(학습 10~90분위)을 **둘 다** 쓴다. 792 가
            #: 예보 구간의 설계 실수를 봤으므로 여기서는 점 추정만 가른다
            per[d] = {"진짜": C.rulers(yh, yho, cl, ch),
                      "기후값": C.rulers(cm, yho, cl, ch),
                      "행": len(yho)}
        runs.append(per)
        print(f"  씨앗 {s} 끝 · {round(time.time()-t0,1)}초", flush=True)

    doms = sorted(runs[0])
    wts = {d: runs[0][d]["행"] for d in doms}

    def pooled(group, arm, key):
        ks = [d for d in group if d in doms]
        w = np.array([wts[d] for d in ks], float)
        out = []
        for r in runs:
            v = np.array([r[d][arm][key] for d in ks], float)
            out.append(float((w * v).sum() / w.sum()))
        a = np.array(out)
        return {"씨앗별": [round(x, 4) for x in a],
                "평균": round(float(a.mean()), 4),
                "SD": round(float(a.std(ddof=1)), 5)}

    res = {}
    for gname, group in (("넓은 무리", wide), ("좁은 무리", narrow)):
        block = {"행 합": int(sum(wts[d] for d in group if d in doms))}
        for key in ("자릿수 오차 비율", "중앙절대오차", "구간 덮음"):
            t_ = pooled(group, "진짜", key)
            c_ = pooled(group, "기후값", key)
            d_ = t_["평균"] - c_["평균"]
            noise = max(t_["SD"], c_["SD"])
            block[key] = {"진짜": t_, "기후값": c_,
                          "**진짜−기후값**": round(d_, 4),
                          "잡음(씨앗 SD)": round(noise, 5),
                          "**3배 밖으로 이기나**": bool(d_ < -3 * noise)}
        res[gname] = block
        dg = block["자릿수 오차 비율"]
        print(f"[{gname}] 자릿수 진짜 {dg['진짜']['평균']:.4f} 대 기후값 "
              f"{dg['기후값']['평균']:.4f} · 차 {dg['**진짜−기후값**']:+.4f} · "
              f"3배밖 {dg['**3배 밖으로 이기나**']}", flush=True)

    perd = {d: {"IQR": round(iqr[d], 4),
                "무리": "넓" if d in wide else "좁",
                "자릿수 [진짜, 기후값]": [
                    round(float(np.mean([r[d]["진짜"]["자릿수 오차 비율"]
                                         for r in runs])), 3),
                    round(float(np.mean([r[d]["기후값"]["자릿수 오차 비율"]
                                         for r in runs])), 3)]}
            for d in doms}

    ga = res["넓은 무리"]["자릿수 오차 비율"]["**3배 밖으로 이기나**"]
    gd = res["좁은 무리"]["자릿수 오차 비율"]["**3배 밖으로 이기나**"]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "문턱(IQR 중앙값)": round(med, 4),
        "넓은 무리": wide, "좁은 무리": narrow,
        "무리별": res, "도메인별": perd,
        "**판정 (가) 넓은 무리 조건부 허용**": bool(ga and not gd),
        "**판정 (나) 조건부 능력 없음**": bool(not ga),
        "**판정 (다) 좁은 무리도 이김 --- 재사전등록**": bool(gd),
        "예측 ② (가) 발동": bool(ga and not gd),
        "예측 ④ 덮음은 넓은 무리에서도 기후값 승":
            res["넓은 무리"]["구간 덮음"]["**진짜−기후값**"],
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
