"""절대량 복원 --- 순위 예측을 실제 숫자로 되돌린다.

노트 19가 라벨 0개 파이프라인을 완성했지만 한계를 하나 남겼다.

    이 파이프라인은 순위를 맞히지 절대량을 맞히지 못한다. 도메인 안에서
    표준화한 눈금이므로, 실제 방문자 수를 얻으려면 그 도메인의 분포를 알아야 한다.

실무에서는 숫자가 필요하다. '이 팝업이 상위 30%'가 아니라 '하루 1,200명'이어야
기획이 선다. 그런데 분포를 알려면 그 도메인의 라벨이 있어야 한다.

**여기서 두 가지가 분리된다.**

    순위  --- 라벨 0개. 프로크루스테스 정렬 + 전이 계수 (노트 19).
    눈금  --- 중심과 폭 두 모수. 라벨 몇 개면 추정된다.

몇 개인지가 이 노트의 질문이다. 노트 16의 소수 예시 실험과 다르다 --- 거기서는
기울기와 절편을 자유롭게 맞춰 순위 자체를 바꾸려 했고 실패했다. 여기서는 순위를
그대로 두고 눈금만 옮긴다. 모수가 둘뿐이므로 훨씬 적게 든다.

비교 대상:
    상수      k개의 중앙값만 쓴다. 순위 정보 없음.
    파이프라인 k개로 눈금을 잡고 라벨 0개 순위를 얹는다.
    전량      참 중심·폭을 안다고 가정. 폭 추정에 MAD를 쓴 쪽이 실제 상한이다.

성적은 **배수 오차**로 낸다 --- log10 공간의 MAE를 10의 거듭제곱으로 되돌리면
'평균 몇 배 틀리는가'가 된다. 실무자가 읽을 수 있는 단위다.

사용: python3 -m state.absolute
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

import state.procrustes as P
from .tri_domain import ALL5, detrend, load_all, z

SEED = 20260728
KS = [3, 5, 8, 12, 20, 30, 50]


def raw_labels(dom: str):
    """도메인의 원 라벨(log10)과 탈추세 성분을 함께 낸다.

    파이프라인은 탈추세·표준화 눈금에서 순위를 내므로, 절대량으로 되돌리려면
    추세를 다시 더해야 한다. 추세는 관측 시점만 있으면 알 수 있고 라벨이
    필요 없다 --- 그래서 이 부분은 k에 들어가지 않는다."""
    doms = load_all()
    A, M, y, t = doms[dom]
    ka = [j for j in range(len(ALL5)) if M[:, j].mean() >= 0.6]
    rows = M[:, ka].all(1)
    y0, t0 = y[rows], t[rows]
    res = detrend(y0, t0)
    return y0, res, t0, rows


def run(reps: int = 200) -> dict:
    doms = load_all()
    F = {k: P.factor_space(*v) for k, v in doms.items()}
    P.COMMON = ["target_breadth", "goods_scale"]
    G = P.align(F, "팝업")

    out = {"ks": KS, "결과": {}}
    print("절대량 복원 --- 배수 오차(평균 몇 배 틀리는가)")
    for tgt in G:
        # 순위 예측 --- 대상 라벨 0개. 다른 두 도메인에서 각각 배워 평균낸다.
        preds = []
        for s in G:
            if s == tgt:
                continue
            m = Ridge(alpha=1.0).fit(G[s]["S"], G[s]["y"])
            preds.append(m.predict(G[tgt]["S"]))
        zhat = np.mean(preds, axis=0)
        zhat = (zhat - zhat.mean()) / (zhat.std() + 1e-9)

        y0, res, t0, _ = raw_labels(tgt)
        trend = y0 - res                     # 라벨 없이 알 수 있는 성분
        n = len(y0)

        row = {}
        for k in KS:
            if k >= n - 5:
                continue
            e_pipe, e_const = [], []
            for r in range(reps):
                rng = np.random.default_rng(SEED + 100 * r + k)
                idx = rng.choice(n, k, replace=False)
                hold = np.setdiff1d(np.arange(n), idx)
                # 눈금 --- 잔차의 중심과 폭 두 모수만 k개로 추정
                c = float(np.median(res[idx]))
                s_ = float(np.median(np.abs(res[idx] - c)) * 1.4826) or float(res[idx].std())
                pred = trend[hold] + c + s_ * zhat[hold]
                e_pipe.append(float(np.abs(pred - y0[hold]).mean()))
                e_const.append(float(np.abs(trend[hold] + c - y0[hold]).mean()))
            row[k] = {"pipe_fold": round(float(10 ** np.mean(e_pipe)), 3),
                      "const_fold": round(float(10 ** np.mean(e_const)), 3),
                      "win_rate": round(float(np.mean(np.array(e_pipe) < np.array(e_const))), 3)}
        # 참 분포를 안다고 가정한 경우. **상한이 아니다** --- 여기서는 폭에
        # 표준편차를 쓰는데 k-표본 쪽은 MAD를 쓰고, 평균절대오차 최소화에는
        # MAD가 낫다. 그래서 k가 커지면 이 값을 넘어선다(아이돌 k=20에서
        # 3.956배 대 4.312배). 참고선으로만 읽는다.
        c, s_ = float(np.median(res)), float(res.std())
        e = float(np.abs(trend + c + s_ * zhat - y0).mean())
        row["full_sd"] = {"pipe_fold": round(float(10 ** e), 3)}
        # MAD 로 폭을 잡은 참 분포 --- 이쪽이 실제 상한이다
        s2 = float(np.median(np.abs(res - c)) * 1.4826)
        row["full_mad"] = {"pipe_fold": round(
            float(10 ** float(np.abs(trend + c + s2 * zhat - y0).mean())), 3)}
        out["결과"][tgt] = row

        print(f"\n[{tgt}]  n={n}")
        print(f"  {'k':>4}{'파이프라인':>11}{'상수':>9}{'승률':>8}")
        for k in KS:
            if k not in row:
                continue
            v = row[k]
            print(f"  {k:>4}{v['pipe_fold']:>11.3f}배{v['const_fold']:>8.3f}배"
                  f"{v['win_rate']:>8.2f}")
        print(f"  전량 MAD{row['full_mad']['pipe_fold']:>9.3f}배   "
              f"(전량 SD {row['full_sd']['pipe_fold']:.3f}배)")

    Path("data/state/absolute.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
