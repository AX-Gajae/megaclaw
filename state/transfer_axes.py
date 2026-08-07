"""파운데이션 가설의 첫 직접 시험 --- 팝업에서 배운 축이 아이돌에서도 통하는가.

이 프로젝트의 전제는 하나다. IP가 대중과 만나는 접점들은 표면이 달라도 같은 잠재 축
위에 놓인다. 팝업스토어와 아이돌 데뷔는 파는 것도 세는 것도 다르지만, '대상이
얼마나 넓은가 · 닿기 얼마나 쉬운가 · 닿으면 무엇을 얻는가'는 같은 질문이다.

지금까지 이 전제를 시험할 수 없었다. 아이돌 쪽에 축이 매겨져 있지 않았기 때문이다.
노트 8이 그것을 수집 과제로 지정했고, 알라딘 상품 데이터로 두 축(입장 허들·굿즈
규모)을 81건 중 69건 채웠다. 이제 시험할 수 있다.

**설계.** 두 도메인의 라벨은 물리량이 다르다(팝업 일평균 방문자 vs 아이돌 초동 장수).
그래서 도메인 안에서 y를 표준화하고 축도 각각 표준화한다. 그러면 검정하는 것은
'절대값이 옮겨지는가'가 아니라 **'축과 결과의 관계 방향과 세기가 옮겨지는가'** 가
된다. 후자가 파운데이션 가설이 실제로 주장하는 바다.

    A 도메인 내부      같은 도메인에서 학습·검정 (IP 그룹 교차검증). 상한.
    B 아이돌 → 팝업    아이돌에서만 학습해 팝업을 예측. **팝업 라벨을 한 번도 안 본다.**
    C 팝업 → 아이돌    반대 방향.
    D 계수 비교        두 도메인이 각 축에 같은 부호·비슷한 크기를 주는가.

매장 노출도는 아이돌 쪽 태깅률이 32%뿐이라 뺀다. 네 축으로 한다.

사용: python3 -m state.transfer_axes
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .slots import load_popup

SEED = 20260728
# 매장 노출도 제외 --- 아이돌 태깅률 32%.
# 입장 허들 제외 --- 노트 9에서 앨범 가격을 굿즈 규모로 재배치한 뒤 대응물이 없다.
USE = ["target_breadth", "media_push", "goods_scale"]
KO = {"target_breadth": "타깃 폭", "entry_friction": "입장 허들",
      "media_push": "미디어 투입", "goods_scale": "굿즈 규모"}
ALL_AXES = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]


def z(v):
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-9)


def popup_pool():
    X, y, w, A, M, groups, times, cols = load_popup()
    idx = [ALL_AXES.index(a) for a in USE]
    keep = M[:, idx].all(1)
    return (np.column_stack([z(A[keep][:, j]) for j in idx]), z(y[keep]),
            groups[keep], "팝업")


def idol_pool():
    d = json.loads(Path("data/state/idol_axes.json").read_text())
    rows = list(d.values())
    A = np.array([[r["axes"][a] for a in USE] for r in rows])
    M = np.array([[r["mask"][a] for a in USE] for r in rows])
    y = np.array([r["y"] for r in rows])
    g = np.array([r.get("agency_norm") or r["group"] for r in rows])
    keep = M.all(1)
    return (np.column_stack([z(A[keep][:, j]) for j in range(len(USE))]), z(y[keep]),
            g[keep], "아이돌")


def cv_within(A, y, g, reps=40):
    """도메인 내부 성능. 그룹 교차검증 반복."""
    uniq = np.unique(g)
    diffs = []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        perm = rng.permutation(len(uniq))
        b = {u: perm[i] % 5 for i, u in enumerate(uniq)}
        gb = np.array([b[u] for u in g])
        ec, em = [], []
        for k in range(5):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            m = Ridge(alpha=1.0).fit(A[tr], y[tr])
            em.append(np.abs(m.predict(A[te]) - y[te]))
        diffs.append(float(np.concatenate(em).mean() - np.concatenate(ec).mean()))
    v = np.array(diffs)
    return {"median": round(float(np.median(v)), 4), "sd": round(float(v.std()), 4),
            "win_rate": round(float((v < 0).mean()), 3)}


def cross_ci(Asrc, ysrc, Atgt, ytgt, boot=400):
    """교차 성능에 신뢰구간을 붙인다.

    단일 적합의 점추정만으로는 주장할 수 없다 --- 아이돌→팝업이 -0.0041 로
    아슬아슬하게 이겼는데, 이 정도 크기는 출처 표본을 다시 뽑는 것만으로
    부호가 바뀔 수 있다. 출처를 부트스트랩해 계수의 표집 분산을 반영한다.
    대상 라벨은 여전히 학습에 쓰지 않는다."""
    rng = np.random.default_rng(SEED)
    base = np.abs(np.median(ytgt) - ytgt).mean()
    d = []
    for _ in range(boot):
        b = rng.integers(0, len(ysrc), len(ysrc))
        if np.unique(b).size < 5:
            continue
        m = Ridge(alpha=1.0).fit(Asrc[b], ysrc[b])
        d.append(float(np.abs(m.predict(Atgt) - ytgt).mean() - base))
    v = np.array(d)
    return {"median": round(float(np.median(v)), 4),
            "ci95": [round(float(np.percentile(v, 2.5)), 4),
                     round(float(np.percentile(v, 97.5)), 4)],
            "win_rate": round(float((v < 0).mean()), 3),
            "wins": bool(np.percentile(v, 97.5) < 0)}


def cross(Asrc, ysrc, Atgt, ytgt):
    """출처 도메인에서만 학습해 대상 도메인을 예측한다. 대상 라벨은 보지 않는다."""
    m = Ridge(alpha=1.0).fit(Asrc, ysrc)
    e_model = np.abs(m.predict(Atgt) - ytgt).mean()
    e_const = np.abs(np.median(ysrc) - ytgt).mean()      # 출처의 중앙값을 그대로 옮긴 것
    e_tgt_const = np.abs(np.median(ytgt) - ytgt).mean()  # 대상 자신의 중앙값(더 강한 기준)
    return {"모델": round(float(e_model), 4),
            "출처_상수": round(float(e_const), 4),
            "대상_상수": round(float(e_tgt_const), 4),
            "vs_대상상수": round(float(e_model - e_tgt_const), 4),
            "coef": {k: round(float(c), 3) for k, c in zip(USE, m.coef_)}}


def run() -> dict:
    Ap, yp, gp, _ = popup_pool()
    Ai, yi, gi, _ = idol_pool()
    print(f"팝업 완전케이스 {len(yp)}건 · 아이돌 완전케이스 {len(yi)}건 · 축 {len(USE)}개\n")

    out = {"n_popup": int(len(yp)), "n_idol": int(len(yi)), "axes": USE}
    print("── A. 도메인 내부 (상한) ──")
    for nm, (A, y, g) in (("팝업", (Ap, yp, gp)), ("아이돌", (Ai, yi, gi))):
        r = cv_within(A, y, g)
        out[f"내부_{nm}"] = r
        print(f"  {nm:<6}Δ중앙 {r['median']:+.4f}  SD {r['sd']:.4f}  승률 {r['win_rate']:.2f}")

    print("\n── B/C. 교차 도메인 (대상 라벨 미사용) ──")
    for nm, args in (("아이돌 → 팝업", (Ai, yi, Ap, yp)), ("팝업 → 아이돌", (Ap, yp, Ai, yi))):
        r = cross(*args)
        ci = cross_ci(*args)
        r["부트스트랩"] = ci
        out[f"교차_{nm}"] = r
        mark = "✅ 유의" if ci["wins"] else ("△ 이기나 CI가 0을 포함" if ci["median"] < 0 else "✗ 짐")
        print(f"  {nm:<14}Δ{r['vs_대상상수']:+.4f}  부트 중앙 {ci['median']:+.4f}  "
              f"CI[{ci['ci95'][0]:+.4f},{ci['ci95'][1]:+.4f}]  승률 {ci['win_rate']:.2f}  {mark}")

    print("\n── D. 계수 비교 (도메인 전체 적합) ──")
    mp = Ridge(alpha=1.0).fit(Ap, yp)
    mi = Ridge(alpha=1.0).fit(Ai, yi)
    out["계수"] = {"팝업": {k: round(float(c), 3) for k, c in zip(USE, mp.coef_)},
                 "아이돌": {k: round(float(c), 3) for k, c in zip(USE, mi.coef_)}}
    agree = 0
    print(f"  {'축':<12}{'팝업':>9}{'아이돌':>9}   부호")
    for k, cp, ci in zip(USE, mp.coef_, mi.coef_):
        same = (cp > 0) == (ci > 0)
        agree += same
        print(f"  {KO[k]:<12}{cp:>+9.3f}{ci:>+9.3f}   {'일치' if same else '불일치'}")
    out["부호일치"] = f"{agree}/{len(USE)}"
    rho = float(np.corrcoef(mp.coef_, mi.coef_)[0, 1])
    out["계수상관"] = round(rho, 3)
    print(f"\n  부호 일치 {agree}/{len(USE)}   계수 상관 r={rho:+.3f}")

    Path("data/state/transfer_axes.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
