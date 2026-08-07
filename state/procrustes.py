"""도메인 간 인자 정렬 --- 부호 규약을 구조로 대체한다.

노트 18은 도메인마다 주성분을 따로 뽑아 전이했고, 성분 부호는 '출처 라벨과 양이
되도록' 뒤집었다. 누출은 아니지만(대상 라벨을 쓰지 않았다) 약점이 둘이다.

  · 부호만 맞추므로 두 인자가 서로 뒤바뀌어도 잡지 못한다.
  · 라벨이 전혀 없는 새 도메인에는 적용할 수 없다.

여기서는 **적재 패턴만으로** 정렬한다. 세 도메인이 공통으로 관측하는 축
(타깃 폭, 굿즈 규모)에서의 적재를 기준으로 회전 행렬을 찾는다 --- 직교
프로크루스테스 문제이고 해가 닫힌 형태로 있다(Schönemann 1966).

    최소화  ||L_src[C] R - L_ref[C]||_F   단, R'R = I
    해      R = UV',  단 L_src[C]' L_ref[C] = U S V'

라벨은 어디에도 들어가지 않는다. 회전은 순전히 '두 도메인이 같은 축을 어떻게
싣는가'로 정해진다.

사용: python3 -m state.procrustes
"""
from __future__ import annotations

import json
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

from .tri_domain import ALL5, detrend, load_all, z

SEED = 20260728
# 공통 축 둘. 노트 19는 셋으로 늘리라고 했고 실제로 게임의 미디어 투입을 100%
# 관측 가능하게 만들었는데, 전이가 나빠졌다(노트 20) --- 세 도메인의 '미디어 투입'
# 정의가 서로 다른 것을 재기 때문이다. 정렬 축은 개수가 아니라 정의의 정합성으로
# 고른다.
# 공통 축 --- 정렬에 참여하므로 도메인 간 같은 물리량이어야 한다.
# 노트 37에서 매장 노출도를 더해 둘에서 셋으로 늘렸다(유의 9→10, 이득
# +0.0480→+0.0529). 입장 허들까지 넷으로 늘리면 오히려 나빠진다(9/12,
# +0.0421) --- 가격은 도메인마다 다른 것을 재기 때문이다(노트 9·16).
# 노트 108에서 셋에서 **다섯**으로 늘렸다. 입장료(노트 105)와 미디어 홍보
# (노트 108)를 더한다 --- 둘 다 ALL5 에 있었으나 노트 20 · 22가 ``정의 불일치''를
# 이유로 정렬에서 뺐고 여든 노트 동안 재검토되지 않았다. 노트 103 · 104가 만든
# **정렬 잔차**로 다시 재니 정의가 아니라 **방향**이 문제였고(잔차 0.980 ->
# 0.875), 미디어 홍보는 덮개율이 문제였다(다섯 도메인 0%). 둘을 고치자
# 판정치가 +0.4038 -> +0.4270 으로 오르고 씨앗 넷 붓스트랩에서 **채택 4/4**
# (구간 [+0.0119, +0.0322])다. 방향 표는 data/state/axis_orient.json 에 있다.
COMMON = ["target_breadth", "goods_scale", "venue_prominence",
          "entry_friction", "media_push"]
K = 2


# 도메인 고유 축을 공유 공간에 섞는 비율. 1.0이면 공유 축과 동등하게 섞는다.
#
# 노트 28에서 게임에 축 하나를 더하자 인자 기하가 회전해 정렬이 깨졌다(유의 방향
# 6개→5개). 고유 축이 공유 공간을 과하게 지배한 탓이다. λ를 쓸어 보니 0.75에서
# 축을 켜든 끄든 여섯 방향이 유지된다(노트 29).
#
#   λ      축 끔            축 켬
#   0.00   5개 -0.0573     5개 -0.0573    (고유 축 미사용)
#   0.75   6개 -0.0691     6개 -0.0675    ← 채택
#   1.00   6개 -0.0762     5개 -0.0666    (축을 켜면 붕괴)
#
# λ=1.0이 축을 끈 상태에서는 가장 좋지만, 축을 늘릴 계획이라면 0.75가 안전하다.
# 고유 축 블록의 배율. 1.0 은 '축소하지 않는다'는 뜻이며 튜닝된 값이 아니다.
# 노트 29의 겹침 유도 규칙을 노트 48에서 폐기하고 이 값으로 왔다.
LAM_OWN = 1.0

# 도메인별 λ. 균일 0.75보다 낫다 --- 축을 켠 상태에서 -0.0675 대 -0.0736 (노트 30).
#
#   방식                  매장축 끔        매장축 켬
#   균일 0.75            6개 -0.0691     6개 -0.0675
#   균일 1.00            6개 -0.0762     5개 -0.0666  (켜면 붕괴)
#   팝업 0.75·아이돌 1.0   6개 -0.0743     6개 -0.0736  ← 채택
#   고유축수 역비례        6개 -0.0664     5개 -0.0528  (단순 공식은 나쁘다)
#
# 팝업만 줄이는 이유는 고유 축 수가 아니라 그 축들의 내부 상관이다.
# **튜닝하지 않고 유도한다.** 격자 탐색으로 팝업 0.75·아이돌 1.0을 찾은 뒤,
# 왜 팝업만 줄여야 하는지 확인했다. 고유 축 수(3 대 2)도 내부 상관(0.147 대 0.124)도
# 아니고 **고유 축이 공유 축과 겹치는 정도**였다(0.318 대 0.244).
#
#   λ_d = min_d(겹침) / 겹침_d
#
# 이 규칙이 팝업 0.768, 아이돌 1.0을 주고 격자 최적(-0.0736)을 미세하게 넘는다
# (-0.0738, 매장축 켠 상태). 새 도메인이 와도 격자 탐색 없이 계산된다.
def lam_by_overlap(doms, min_cov: float = 0.6, names: dict | None = None,
                   common: list | None = None, derive: bool = False) -> dict:
    """**노트 48에서 폐기했다. 기본으로 1.0을 낸다.**

    겹침 유도 규칙(노트 29)은 전역 최소로 정규화한다 --- `λ_d = min_d(겹침) / 겹침_d`.
    그래서 **도메인 하나가 들어오면 다른 모든 도메인의 λ가 바뀐다.** 웹툰을
    여섯째로 넣자 나머지 λ가 0.73~1.0에서 0.24~0.33으로 내려갔고, 웹툰과 무관한
    스무 셀의 평균 순위 상관이 +0.3516에서 +0.3166으로 떨어졌다.

    노트 40에서 정렬을 쌍별로 바꾼 이유가 '도메인별 관측 차이를 그대로 안고
    간다'였는데, λ가 전역이면 그 취지가 깨진다. **성능 문제가 아니라 정의의
    결함이다** --- 한 도메인의 전이 성적이 표본에 어떤 다른 도메인이 들어 있는지에
    달리면 안 된다.

    성능으로도 1.0 고정이 낫다(6도메인 30셀 +0.3189 → +0.3506). 다만 짝지은
    95% 구간이 [-0.0003, +0.0590]으로 0을 아슬아슬하게 포함하므로 성능을 근거로
    삼지 않는다. **불변성이 근거다.**

    derive=True 로 부르면 옛 규칙을 그대로 계산한다(비교용).

    ---- 아래는 폐기된 규칙의 원 설명 ----
    고유 축과 공유 축의 평균 절대 상관에 반비례하는 λ.

    names --- 도메인별 축 이름. 도메인마다 고유 축 수가 다를 수 있으므로
    ALL5로 고정하지 않는다(노트 36). 주지 않으면 네 도메인 공통 다섯 축이다."""
    if not derive:
        return {k: 1.0 for k in doms}
    ov = {}
    for k, (A, M, y, t) in doms.items():
        nm = (names or {}).get(k, ALL5)
        cm = common or COMMON
        ka = [j for j in range(len(nm)) if M[:, j].mean() >= min_cov]
        rows = M[:, ka].all(1)
        sh = [nm.index(a) for a in cm if a in nm and nm.index(a) in ka]
        own = [j for j in ka if j not in sh]
        if not own:
            continue
        O = np.column_stack([z(detrend(A[rows][:, j], t[rows])) for j in own])
        S = np.column_stack([z(detrend(A[rows][:, j], t[rows])) for j in sh])
        C = np.abs(np.corrcoef(np.column_stack([O, S]), rowvar=False))
        ov[k] = float(C[:len(own), len(own):].mean())
    if not ov:
        return {}
    lo = min(ov.values())
    return {k: lo / v for k, v in ov.items()}


def factor_space(A, M, y, t, min_cov: float = 0.6, lam: float = LAM_OWN,
                 names: list | None = None, block_norm: bool = False,
                 common: list | None = None, k: int | None = None):
    """관측 축으로 주성분을 뽑되 고유 축은 lam 배로 축소해 섞는다.
    부호는 손대지 않는다 --- 정렬은 프로크루스테스가 맡는다.

    names --- 이 도메인의 축 이름. 고유 축은 정렬에 쓰이지 않으므로 도메인마다
    개수와 종류가 달라도 된다(노트 36)."""
    nm = names or ALL5
    cm = common or COMMON
    kk = k or K
    ka = [j for j in range(len(nm)) if M[:, j].mean() >= min_cov]
    rows = M[:, ka].all(1)
    sh = [nm.index(a) for a in cm if a in nm and nm.index(a) in ka]
    own = [j for j in ka if j not in sh]
    cols = [np.column_stack([z(detrend(A[rows][:, j], t[rows])) for j in sh])]
    if own and lam > 1e-9:
        O = np.column_stack([z(detrend(A[rows][:, j], t[rows])) for j in own])
        # 고유 축 **블록 전체**의 분산을 공유 블록에 맞춘 뒤 lam 을 건다.
        #
        # 그러지 않으면 lam 이 겹침만 보정하고 개수는 보정하지 못한다. 고유 축이
        # 다섯 개면 블록 분산이 lam^2*5 로 공유 블록(2)을 압도해 주성분이 고유
        # 축 쪽으로 끌려가고, 정렬에 쓰는 공통 축 적재가 희석된다. 실제로 팝업에
        # 고유 축 다섯을 더하자 2차원 R 이 0.385 에서 0.349 로 떨어졌다(노트 36).
        #
        # **기본값은 끔이다.** 현행 다섯 축 구조에서는 유의 9/12로 같고 평균
        # 이득이 +0.0480에서 +0.0469로 미세하게 나빠진다. 고유 축을 크게 늘리는
        # 설계를 다시 시도할 때 켜라 --- 그때는 손실을 절반쯤 회복한다.
        if block_norm and len(own) > len(sh) > 0:
            O = O * np.sqrt(len(sh) / len(own))
        cols.append(lam * O)
    Z = np.column_stack(cols)
    # 상관이 아니라 공분산을 쓴다 --- 상관으로 표준화하면 lam 축소가 지워진다
    C = np.cov(Z, rowvar=False)
    ev, V = np.linalg.eigh(C)
    V = V[:, ::-1][:, :kk]
    # y_raw/t_raw --- **탈추세 전** 라벨과 시간. 보정 표본 안에서만 탈추세해야
    # 하는 절차(노트 70의 방향 결정)가 이것을 필요로 한다. 전표본으로 탈추세한
    # y 를 k건만 잘라 쓰면 나머지 n-k건의 정보가 새어 든다.
    return {"Z": Z, "V": V, "S": Z @ V, "y": z(detrend(y[rows], t[rows])),
            "y_raw": np.asarray(y, float)[rows], "t_raw": np.asarray(t, float)[rows],
            "axes": [nm[j] for j in sh] + [nm[j] for j in own],
            "n": int(rows.sum())}


def procrustes(Lsrc: np.ndarray, Lref: np.ndarray) -> np.ndarray:
    """L_src R ≈ L_ref 를 만드는 직교 R. 반사도 허용한다 --- 성분 부호가
    임의이므로 회전만으로는 맞출 수 없는 경우가 있다."""
    U, _, Vt = np.linalg.svd(Lsrc.T @ Lref)
    return U @ Vt


def align(F: dict, ref: str, common: list | None = None, k: int | None = None) -> dict:
    """공통 축 적재로 각 도메인의 인자 공간을 기준 도메인에 맞춘다.

    공통 축이 c개이고 성분이 k개이면 프로크루스테스는 c×k 적재를 맞춘다.
    **c < k 이면 회전이 과소결정된다** --- 그래서 공통 축을 늘리지 않고 k만
    늘리는 것은 의미가 없다(노트 37)."""
    cm = common or COMMON
    kk = k or K

    def loading(d):
        idx = [F[d]["axes"].index(a) for a in cm if a in F[d]["axes"]]
        return F[d]["V"][idx, :]          # (공통 축 수) × k

    Lref = loading(ref)
    out = {}
    for d in F:
        R = np.eye(kk) if d == ref else procrustes(loading(d), Lref)
        out[d] = {"S": F[d]["S"] @ R, "y": F[d]["y"], "R": R,
                  "L": loading(d) @ R, "n": F[d]["n"]}
    return out


# 출처 역할의 고유 축 비중. **노트 42에서 철회하고 유도값으로 되돌렸다.**
#
# 노트 41은 이 값을 1.5로 키워 19/20을 얻고 '정보량 손잡이'라고 설명했다.
# 노트 42가 그 설명의 반증 조건을 검정하다가 더 나쁜 것을 찾았다 --- λ를 0.5에서
# 3.0까지 훑어도 **전이 상관이 움직이지 않는다**(20셀 평균 0.381~0.387, 셀별
# 표준편차 평균 0.004). 움직인 것은 예측의 퍼짐이다(SD 0.67→0.38). λ를 키우면
# 인자 공간 분산이 커져 능형 계수가 작아지고, 그래서 우연히 축소가 걸렸다.
# 순위는 그대로인데 눈금만 맞은 것이며, 순열 검정이 MAE 기준이라 그것을 개선으로
# 읽었다.
#
# None 이면 겹침 유도값(노트 29)을 쓴다.
SRC_LAM = None


def align_pair(Fs: dict, Ft: dict, common: list | None = None):
    """출처를 대상에 직접 맞춘다 --- 쌍마다 **둘이 함께 관측한** 공통 축만 쓴다.

    지금까지는 네 도메인을 모두 기준 도메인(팝업)에 맞췄다. 그러면 공통 축
    집합이 전역으로 하나여야 하고, 어느 한 도메인이 그중 하나를 관측하지 못하면
    그 축을 전부에서 빼야 했다. 전이는 어차피 쌍 단위이므로 쌍마다 맞추면
    도메인별 관측 차이를 그대로 안고 갈 수 있다(노트 40).

    반환은 회전된 출처 점수다. 대상은 자기 좌표계 그대로 둔다."""
    cm = common or COMMON
    shared = [a for a in cm if a in Fs["axes"] and a in Ft["axes"]]
    if len(shared) < 2:
        return None
    Ls = Fs["V"][[Fs["axes"].index(a) for a in shared], :]
    Lt = Ft["V"][[Ft["axes"].index(a) for a in shared], :]
    return Fs["S"] @ procrustes(Ls, Lt), shared


def cross(As, ys, At, yt, perm=3000):
    base = np.abs(np.median(yt) - yt).mean()
    m = Ridge(alpha=1.0).fit(As, ys)
    obs = float(np.abs(m.predict(At) - yt).mean() - base)
    rng = np.random.default_rng(SEED)
    null = np.array([float(np.abs(Ridge(alpha=1.0)
                                  .fit(As, ys[rng.permutation(len(ys))])
                                  .predict(At) - yt).mean() - base) for _ in range(perm)])
    return round(obs, 4), round(float((null <= obs).mean()), 4)


def run(ref: str = "팝업", derive_lam: bool = True) -> dict:
    doms = load_all()
    lam = lam_by_overlap(doms) if derive_lam else {}
    if lam:
        print("겹침에서 유도한 λ: " +
              "  ".join(f"{k} {v:.3f}" for k, v in lam.items()))
    F = {k: factor_space(*v, lam=lam.get(k, LAM_OWN)) for k, v in doms.items()}
    for k, v in F.items():
        print(f"{k:<6} n={v['n']:>3}  관측 축 {len(v['axes'])}개")
    G = align(F, ref)

    print(f"\n=== 정렬 후 공통 축 적재 (기준: {ref}) ===")
    print(f"  {'도메인':<7}" + "".join(f"{a:>16}" for a in ("타깃 폭 PC1/PC2", "굿즈 규모 PC1/PC2")))
    for d, v in G.items():
        L = v["L"]
        print(f"  {d:<7}{L[0,0]:>+8.2f}{L[0,1]:>+8.2f}{L[1,0]:>+8.2f}{L[1,1]:>+8.2f}")

    print("\n=== 정렬 후 전이 (라벨 없는 정렬) ===")
    out = {"ref": ref, "n": {k: v["n"] for k, v in G.items()},
           "loadings": {d: [[round(float(x), 3) for x in r] for r in v["L"]]
                        for d, v in G.items()}, "교차": {}}
    for s, t in permutations(G, 2):
        o, p = cross(G[s]["S"], G[s]["y"], G[t]["S"], G[t]["y"])
        out["교차"][f"{s}→{t}"] = {"obs": o, "p": p}
        mark = "✅" if p < 0.05 else ("△" if o < 0 else "✗")
        print(f"  {s:<5}→ {t:<6}Δ{o:+.4f}  순열 p={p:.4f}  {mark}")

    Path("data/state/procrustes.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()
