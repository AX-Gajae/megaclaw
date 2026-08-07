"""시간 추세를 제거한 전이 재검정 --- 노트 10의 효과 크기 정정.

경위. 노트 10은 굿즈 규모가 팝업에서 아이돌로 유의하게 전이된다고 보고했다
(차이 -0.0556, 순열 p=0.034). 그 뒤 데뷔 연도 구간별로 쪼개 보니 최근 구간에서만
이겼다 --- 2021년 이전 +0.1451, 2022~2024 +0.0565, 2025년 이후 -0.0226.

원인을 찾으니 시간 혼동이었다. 앨범 버전 수도 초동도 함께 늘어왔다.

    연도 vs 굿즈 규모  r=+0.386
    연도 vs 초동       r=+0.426
    굿즈 규모 vs 초동   r=+0.432

전이 검정이 이 공통 추세를 타고 있었다. 다만 완전히 그런 것은 아니다 ---
연도를 통제한 부분상관이 +0.321로 원래의 74%가 남는다.

그래서 두 도메인 모두에서 시간 추세를 빼고 다시 잰다. 팝업 쪽도 마찬가지로
뺀다 --- 한쪽만 빼면 눈금이 어긋난다.

**타깃 폭도 다시 짠다.** 현재 합성은 인원 수가 지배하는데 인원 수와 초동의 상관이
+0.010으로 사실상 0이다. 그리고 `survival_show` 를 잘못 읽고 있었다 --- 값이
'없음'이 아니라 '프로그램 이름 또는 None' 이라 None을 결측으로 처리했더니 관측된
44건이 전부 1.0이 돼 분산이 0이 됐다. None은 '서바이벌 출신 아님'이다.
데뷔 전 대중 도달을 재는 두 신호(서바이벌 출신, 사전 화제 기록)로 다시 만든다.

사용: python3 -m state.detrend_transfer
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

import state.transfer_axes as T

SEED = 20260728


def detrend(v: np.ndarray, t: np.ndarray) -> np.ndarray:
    """선형 시간 추세를 뺀 잔차. 관측 시점이 없으면 그대로 둔다."""
    ok = np.isfinite(t)
    if ok.sum() < 10:
        return v
    X = np.column_stack([np.ones(ok.sum()), t[ok]])
    beta = np.linalg.lstsq(X, v[ok], rcond=None)[0]
    out = v.astype(float).copy()
    out[ok] = v[ok] - X @ beta
    return out


def rebuild_target_breadth() -> dict:
    """데뷔 전 대중 도달로 타깃 폭을 다시 만든다.

    이전 합성: 인원 수(가중 1.0) + 서바이벌(1.0) + 성별(0.5).
      · 인원 수는 초동과 무상관(+0.010)이다.
      · 서바이벌은 None 처리 버그로 분산이 0이었다.
      · 성별은 진짜 효과가 있지만(걸그룹 -0.283) 그것은 '타깃 폭'이 아니라
        시장 구조다. 축 이름과 다른 것을 넣으면 전이 해석이 망가진다.

    새 합성: 서바이벌 출신 + 사전 화제 기록. 둘 다 '데뷔 전에 얼마나 많은 사람에게
    닿았는가'를 잰다."""
    out = {}
    for f in glob.glob("data/idol_records/*.json"):
        r = json.loads(Path(f).read_text())
        sv = 1.0 if r.get("survival_show") else 0.0      # None = 서바이벌 출신 아님
        pd = 1.0 if r.get("pre_debut_signals") else (0.5 if r.get("pre_debut_note") else 0.0)
        out[r["record_id"]] = float(np.average([sv, pd], weights=[1.0, 0.8]))
    return out


def run(boot: int = 2000, perm: int = 4000) -> dict:
    tb_new = rebuild_target_breadth()
    ax = json.loads(Path("data/state/idol_axes.json").read_text())

    T.USE = ["goods_scale"]
    Ap, yp, gp, _ = T.popup_pool()
    Ai, yi, gi, _ = T.idol_pool()

    rows = [v for v in ax.values() if v["mask"]["goods_scale"]]
    ti = np.array([int(v["debut_date"][:4]) if (v["debut_date"] or "")[:4].isdigit()
                   else np.nan for v in rows], float)
    # 팝업 쪽 시점 --- load_popup 의 meta 순서와 같은 풀을 쓴다
    from .slots import load_popup
    Xp, ypr, wp, Apr, Mp, grp, tp, _ = load_popup()
    keep = Mp[:, 4] > 0.5      # goods_scale 마스크
    tpv = np.array([int(s[:4]) if s and s[:4].isdigit() else np.nan for s in tp[keep]], float)

    def report(name, Asrc, ysrc, Atgt, ytgt):
        m = Ridge(alpha=1.0).fit(Asrc, ysrc)
        base = np.abs(np.median(ytgt) - ytgt).mean()
        obs = float(np.abs(m.predict(Atgt) - ytgt).mean() - base)
        rng = np.random.default_rng(SEED)
        null = np.array([
            float(np.abs(Ridge(alpha=1.0)
                         .fit(Asrc, ysrc[rng.permutation(len(ysrc))])
                         .predict(Atgt) - ytgt).mean() - base) for _ in range(perm)])
        p = float((null <= obs).mean())
        d = []
        for _ in range(boot):
            b = rng.integers(0, len(ysrc), len(ysrc))
            mm = Ridge(alpha=1.0).fit(Asrc[b], ysrc[b])
            d.append(float(np.abs(mm.predict(Atgt) - ytgt).mean() - base))
        d = np.array(d)
        r = {"obs": round(obs, 4), "p_perm": round(p, 4),
             "boot_median": round(float(np.median(d)), 4),
             "ci95": [round(float(np.percentile(d, 2.5)), 4),
                      round(float(np.percentile(d, 97.5)), 4)],
             "win_rate": round(float((d < 0).mean()), 3),
             "coef": round(float(m.coef_[0]), 3)}
        print(f"  {name:<24}Δ{r['obs']:+.4f}  순열 p={r['p_perm']:.4f}  "
              f"승률 {r['win_rate']:.2f}  계수 {r['coef']:+.3f}")
        return r

    print(f"굿즈 규모 전이 --- 팝업 {len(yp)}건 → 아이돌 {len(yi)}건")
    print("\n── 추세 제거 전 (노트 10) ──")
    a = report("팝업 → 아이돌", Ap, yp, Ai, yi)

    print("\n── 추세 제거 후 ──")
    Apd = np.column_stack([detrend(Ap[:, 0], tpv)])
    ypd = detrend(yp, tpv)
    Aid = np.column_stack([detrend(Ai[:, 0], ti)])
    yid = detrend(yi, ti)
    b = report("팝업 → 아이돌 (탈추세)", Apd, ypd, Aid, yid)

    print("\n── 참고: 새 타깃 폭 성분 ──")
    ids = list(ax)
    tb = np.array([tb_new.get(i, 0.0) for i in ids])
    yy = np.array([ax[i]["y"] for i in ids])
    tt = np.array([int(ax[i]["debut_date"][:4]) if (ax[i]["debut_date"] or "")[:4].isdigit()
                   else np.nan for i in ids], float)
    print(f"  새 타깃 폭 vs 초동          r={np.corrcoef(tb, yy)[0,1]:+.3f}")
    ok = np.isfinite(tt)
    print(f"  연도 통제 후                r={np.corrcoef(detrend(tb, tt)[ok], detrend(yy, tt)[ok])[0,1]:+.3f}")

    out = {"추세제거_전": a, "추세제거_후": b,
           "새_타깃폭_상관": round(float(np.corrcoef(tb, yy)[0, 1]), 3)}
    Path("data/state/detrend_transfer.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
