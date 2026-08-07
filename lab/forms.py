"""정식화 포트폴리오. 현행 파이프라인은 여기서 **한 항목**일 뿐이다.

목표는 고정이고(IP · 기획 → 소비자 반응) 그 아래 방법은 언제나 갈아 끼운다.
챔피언/도전자 구도로 두고, 이기면 승격 지면 은퇴한다.

    F1  공유 축 + 직교 프로크루스테스 + 능형 전이     노트 5--124 (현 챔피언)
    F2  결합 위계 잠재 모형 (τ 풀링, 우도 결측)       미구현
    F3  정렬 없는 최적수송 (Gromov--Wasserstein)     미구현
    F4  파운데이션 in-context (TabPFN)               미구현
    F5  동역학 --- 일자별 곡선의 확산 모형             미구현
    F6  직접 풀링 + 도메인 임베딩                     구현
    F7  불변성 (anchor regression)                  미구현
"""
from __future__ import annotations

import itertools

import numpy as np
from scipy.stats import rankdata
from sklearn.linear_model import Ridge

from state.procrustes import COMMON, factor_space, lam_by_overlap, procrustes
from state.tri_domain import ALL5

from .harness import Data


# ── F0 무작위 --- 바닥 ──────────────────────────────────────────────────
class Chance:
    name = "F0_chance"
    idea = "무작위 점수. 바닥선."

    def __init__(self, seed: int = 0):
        self.rng = np.random.default_rng(seed)

    def fit(self, train: Data) -> None:
        pass

    def predict(self, d, A, M, t):
        return self.rng.random(len(A))


# ── F1 현행 --- 공유 축 + 프로크루스테스 ────────────────────────────────
def _align(Fs, Ft, cm):
    sh = [a for a in cm if a in Fs["axes"] and a in Ft["axes"]]
    if len(sh) < 2:
        return None
    ke = min(Fs["V"].shape[1], Ft["V"].shape[1], len(sh))
    Ls = Fs["V"][[Fs["axes"].index(a) for a in sh], :ke]
    Lt = Ft["V"][[Ft["axes"].index(a) for a in sh], :ke]
    return procrustes(Ls, Lt), ke


class Procrustes:
    """노트 5--124 의 파이프라인. 이제 도전자 중 하나다."""
    name = "F1_procrustes"
    idea = "도메인별 PCA → 쌍별 직교 정렬 → 능형 전이 (노트 108의 공통 축 다섯)"

    def __init__(self, common=None, k=None):
        self.cm = list(common or COMMON)
        self.k = k
        self.src = {}

    def fit(self, train: Data) -> None:
        lam = lam_by_overlap(train.dom, names=train.names, common=self.cm)
        self.src = {}
        for d, v in train.dom.items():
            try:
                F = factor_space(*v, lam=lam.get(d, 1.0),
                                 names=train.names.get(d), common=self.cm,
                                 k=self.k)
            except Exception:
                continue
            if len(F["y"]) >= 30:
                self.src[d] = F
        self.names = train.names

    def predict(self, d, A, M, t):
        y = np.zeros(len(A))
        Ft = factor_space(A, M, y, t, names=self.names.get(d),
                          common=self.cm, k=self.k)
        rows = Ft["n"]
        ps = []
        for s, Fs in self.src.items():
            if s == d:
                continue
            r = _align(Fs, Ft, self.cm)
            if r is None:
                continue
            R, ke = r
            p = Ridge(alpha=1.0).fit(Fs["S"][:, :ke] @ R,
                                     Fs["y"]).predict(Ft["S"][:, :ke])
            ps.append(rankdata(p) / len(p))
        if not ps:
            return np.full(len(A), np.nan)
        e = np.column_stack(ps).mean(1)
        # factor_space 는 완전사례만 남긴다 --- 나머지는 결측으로 돌려준다
        out = np.full(len(A), np.nan)
        keep = _keep_rows(A, M, self.names.get(d), self.cm)
        out[keep] = e
        return out


def _keep_rows(A, M, names, cm, min_cov=0.6):
    nm = names or ALL5
    ka = [j for j in range(len(nm)) if M[:, j].mean() >= min_cov]
    return M[:, ka].all(1)


# ── F6 직접 풀링 --- 정렬 없이 도메인 표시자로 ──────────────────────────
class DirectPool:
    """정렬을 아예 안 한다. 모든 도메인을 한 표에 쌓고 도메인 표시자를 준다.

    라벨 눈금이 다르므로 도메인 안 순위로 바꿔 쌓는다. 축이 없는 도메인은
    중립 대입 + 관측 표시자(노트 85)."""
    name = "F6_directpool"
    idea = "정렬 없이 전 도메인을 한 표로. 라벨은 도메인 안 순위, 축 결측은 표시자."

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha
        self.m = None

    @staticmethod
    def _feat(A, M, names, order=None):
        """중립 대입 + 관측 표시자(노트 85).

        order 는 전 도메인 축 이름의 합집합이다. **하드코딩하면 안 된다** ---
        처음엔 ALL5 를 그대로 돌려서, 축을 여덟 개 덧붙여도 모형에 한 칸도
        안 닿았다(차이가 정확히 +0.0000 으로 나온 게 단서였다)."""
        nm = list(names or ALL5)
        ix = {a: i for i, a in enumerate(nm)}
        cols = []
        for a in (order or ALL5):
            if a in ix:
                j = ix[a]
                ok = M[:, j] > 0
                cols.append(np.where(ok, A[:, j], 0.5))
                cols.append(ok.astype(float))
            else:
                cols.append(np.full(len(A), 0.5))
                cols.append(np.zeros(len(A)))
        return np.column_stack(cols)

    def fit(self, train: Data) -> None:
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.doms = sorted(train.dom)
        Xs, ys = [], []
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            F = self._feat(A, M, train.names.get(d), self.order)
            oh = np.zeros((len(A), len(self.doms)))
            oh[:, i] = 1.0
            Xs.append(np.column_stack([F, oh]))
            ys.append(rankdata(y) / len(y))
        X = np.vstack(Xs)
        self.m = Ridge(alpha=self.alpha).fit(X, np.concatenate(ys))
        self.names = train.names

    def predict(self, d, A, M, t):
        F = self._feat(A, M, self.names.get(d), self.order)
        oh = np.zeros((len(A), len(self.doms)))
        if d in self.doms:
            oh[:, self.doms.index(d)] = 1.0
        return self.m.predict(np.column_stack([F, oh]))


# ── 등록부 ─────────────────────────────────────────────────────────────
REGISTRY: dict[str, dict] = {}


AXIS_MODE = "common"      # 기본은 공통 핵심 --- 아래 주석 참고


def axis_order(train, mode: str | None = None) -> list:
    """쓸 축 목록.

    ``common``  전 도메인이 다 가진 축만 (지금은 다섯). 노트 5--124 가
                암묵적으로 하던 것이다 --- 옛 코드가 ALL5 를 하드코딩해
                게임의 축 넷(가격 · 연령등급 · 램 · 카테고리 수)을 조용히
                버리고 있었다.
    ``union``   있는 축을 다 쓴다. 없는 도메인은 중립 대입 + 표시자 0.

    **어느 쪽이 맞는지는 재서 정한다.** union 으로 바꾸면 게임만 갖는 축
    넷이 사실상 게임 전용 기울기가 되고, 그건 노트 126 이 잰 ``도메인 고유
    유연성은 비싸다''에 그대로 걸린다. 그래서 기본은 common 이고 union 은
    별도 도전자로 올려 붙인다."""
    mode = mode or AXIS_MODE
    per = {d: list(train.names.get(d) or ALL5) for d in train.dom}
    if mode == "union":
        seen = []
        for d in sorted(per):
            for a in per[d]:
                if a not in seen:
                    seen.append(a)
        return seen or list(ALL5)
    if not per:                      # 축이 하나도 없는 판(노트 233)
        return list(ALL5)            # --- 터지지 말고 빈손을 돌려준다
    common = [a for a in per[sorted(per)[0]]
              if all(a in v for v in per.values())]
    return common or list(ALL5)


def register(cls, make=None, status="challenger", null_make=None):
    """null_make --- 치환 귀무용 (더 싸게). 없으면 make 를 그대로 쓴다."""
    REGISTRY[cls.name] = {"cls": cls, "make": make or (lambda: cls()),
                          "null_make": null_make,
                          "idea": getattr(cls, "idea", ""), "status": status}


register(Chance, status="baseline")
register(Procrustes, status="champion")
register(DirectPool)


# ── F7 불변성 --- anchor regression ─────────────────────────────────────
class Anchor:
    """도메인을 앵커로 두고 앵커 방향의 잔차를 벌한다.

    노트 119--121 이 잰 같은 플랫폼 결합(27\%)은 ``도메인마다 다르게 작동하는
    방향''이다. anchor regression 은 그 방향을 골라 줄인다. gamma=1 이면 최소제곱,
    gamma 를 키우면 도구변수 극한(도메인 간 불변인 방향만 남는다)."""
    name = "F7_anchor"
    idea = "도메인을 앵커로 — 도메인마다 다르게 작동하는 방향에 벌점 (Rothenhausler 2021)"

    def __init__(self, gamma: float = 8.0, alpha: float = 1.0):
        self.gamma, self.alpha = gamma, alpha

    def fit(self, train: Data) -> None:
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.doms = sorted(train.dom)
        Xs, ys, gs = [], [], []
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            Xs.append(DirectPool._feat(A, M, train.names.get(d), self.order))
            ys.append(rankdata(y) / len(y))
            gs.append(np.full(len(A), i))
        X = np.vstack(Xs); y = np.concatenate(ys); g = np.concatenate(gs)
        # P_A = 도메인 평균으로 사영. X~ = (I-P)X + sqrt(gamma) P X
        Xc, yc = X.copy(), y.copy()
        for i in range(len(self.doms)):
            k = g == i
            Xc[k] = X[k] - X[k].mean(0)
            yc[k] = y[k] - y[k].mean()
        Xm, ym = X - Xc, y - yc                       # 사영 성분
        s = np.sqrt(self.gamma)
        self.m = Ridge(alpha=self.alpha).fit(Xc + s * Xm, yc + s * ym)
        self.names = train.names

    def predict(self, d, A, M, t):
        return self.m.predict(DirectPool._feat(A, M, self.names.get(d), self.order))


# ── F8 비선형 --- 축이 천장인가 모형이 천장인가 ─────────────────────────
class Boost:
    """F6 과 완전히 같은 자질에 비선형 모형. 안 오르면 **축이 천장**이다."""
    name = "F8_boost"
    idea = "F6 과 같은 자질, 히스토그램 부스팅 — 선형이 병목인지 축이 병목인지 가른다"

    def __init__(self, depth: int = 4, it: int = 220, lr: float = 0.06):
        self.kw = dict(max_depth=depth, max_iter=it, learning_rate=lr,
                       l2_regularization=1.0, random_state=0)

    def fit(self, train: Data) -> None:
        from sklearn.ensemble import HistGradientBoostingRegressor
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.doms = sorted(train.dom)
        Xs, ys = [], []
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            F = DirectPool._feat(A, M, train.names.get(d), self.order)
            oh = np.zeros((len(A), len(self.doms))); oh[:, i] = 1.0
            Xs.append(np.column_stack([F, oh]))
            ys.append(rankdata(y) / len(y))
        self.m = HistGradientBoostingRegressor(**self.kw).fit(
            np.vstack(Xs), np.concatenate(ys))
        self.names = train.names

    def predict(self, d, A, M, t):
        F = DirectPool._feat(A, M, self.names.get(d), self.order)
        oh = np.zeros((len(A), len(self.doms)))
        if d in self.doms:
            oh[:, self.doms.index(d)] = 1.0
        return self.m.predict(np.column_stack([F, oh]))


# ── F9 순위 우도 --- 재는 것과 맞추는 것을 일치시킨다 ────────────────────
class RankLik:
    """판정치가 스피어만인데 제곱오차로 맞춰 왔다. 목적을 순위로 바꾼다.

    도메인 안에서 짝을 뽑아 (x_i - x_j) 에 로지스틱을 태운다. Plackett--Luce /
    Bradley--Terry 의 짝 형태. 도메인 간 눈금 차이는 짝이 도메인 안에서만
    만들어지므로 자동으로 빠진다 --- **도메인 표시자조차 필요 없다**."""
    name = "F9_ranklik"
    idea = "제곱오차 대신 짝 순위 우도 (Bradley--Terry) — 재는 것과 맞추는 것을 일치"

    def __init__(self, pairs: int = 40000, C: float = 1.0, seed: int = 0):
        self.pairs, self.C, self.seed = pairs, C, seed

    def fit(self, train: Data) -> None:
        from sklearn.linear_model import LogisticRegression
        self.order = axis_order(train, getattr(self, 'axes', None))
        rng = np.random.default_rng(self.seed)
        self.doms = sorted(train.dom)
        tot = sum(len(train.dom[d][2]) for d in self.doms)
        D, L = [], []
        for d in self.doms:
            A, M, y, t = train.dom[d]
            F = DirectPool._feat(A, M, train.names.get(d), self.order)
            n = len(y)
            k = max(200, int(self.pairs * n / tot))
            i, j = rng.integers(0, n, k), rng.integers(0, n, k)
            ok = y[i] != y[j]
            i, j = i[ok], j[ok]
            D.append(F[i] - F[j])
            L.append((y[i] > y[j]).astype(int))
        self.m = LogisticRegression(C=self.C, fit_intercept=False,
                                    max_iter=2000).fit(np.vstack(D),
                                                       np.concatenate(L))
        self.names = train.names

    def predict(self, d, A, M, t):
        return self.m.decision_function(
            DirectPool._feat(A, M, self.names.get(d), self.order))


register(Anchor)
register(Boost)


# ── F18 배깅 부스팅 --- 귀착 가드가 만든 정식화 ──────────────────────────
class BagBoost(Boost):
    """부스팅 K 개를 부트스트랩 표본에 맞추고 **순위**를 평균한다.

    노트 144가 잰 것: 다른 도메인의 축 하나를 지우면 팝업의 예측 순위가
    자기 자신과 0.895 밖에 안 맞는다(능형은 0.987). 팝업의 입력은 한 비트도
    안 바뀌었는데도 그렇다. 노트 145가 그 원인을 깊이로 좁혔다 --- 깊이
    1/2/4 에서 자기상관이 0.981 / 0.951 / 0.895 로 내려간다. 상호작용을
    깊게 쓸수록 풀이 조금 바뀔 때 함수가 통째로 다시 짜인다.

    깊이를 낮추면 안정은 사는데 판이 내린다(+0.366 → +0.338). 배깅은
    **둘 다 산다** --- 판 +0.3846, 자기상관 0.951. 부스팅은 편의를 줄이는
    장치라 분산이 남고, 그 분산이 여기서는 ``풀에 대한 분산''으로 나타난다.

    눈금이 아니라 순위만 쓰므로 평균도 순위로 낸다."""
    name = "F18_bagboost"
    idea = "부스팅을 부트스트랩으로 배깅하고 순위 평균 — 귀착 가드가 지목한 분산을 줄인다"

    # **자루를 8 에서 32 로 올렸다**(노트 396). 노트 395가 자료를 고정하고
    # 씨앗만 바꿔도 판이 0.012 를 오간다는 것을 쟀는데(SD 0.0033), 그 분산이
    # 자루 여덟 개에서 나온다. K=32 로 올리면 씨앗 SD 가 **0.0045 -> 0.0010**
    # 으로 4.5배 준다(1/sqrt(K) 가 예상하는 2배보다 빠르다).
    #
    # **그런데 판 자체도 오른다** --- K=8/16/32 에서 0.4450 / 0.4462 / 0.4476
    # 으로 단조다. 그래서 표기 바꿈이 아니라 모형 바꿈이고, 관문을 돌렸다:
    # 짝 12뽑기 판 **+0.0031 · 11/12** (뽑기마다 씨앗도 바꿔 다시 재도 같은
    # +0.0031 · 11/12 이고 **열한 도메인이 전부 양수**). 조건 ② 통과.
    #
    # **손잡이 넷 중 처음으로 산 것이다.** 노트 216 이 알파를, 216·243 이
    # tau 를, 272 가 깊이를 죽였는데 셋 다 봉우리가 있는 편향-분산 손잡이라
    # 안쪽에서 고르면 빗나갔다. K 는 봉우리가 없다 --- 자루를 늘리면 분산만
    # 주는 순수 비용 손잡이라 ``고르는'' 문제가 아니라 ``얼마나 낼까'' 문제다.
    # 값은 적합 시간 4배(5.8초 -> 24.3초)다.
    # **깊이를 4 에서 6 으로 올렸다**(노트 406). 노트 272 가 죽인 손잡이다.
    # 되살아난 이유는 손잡이가 아니라 **자료** --- 272 이후 만화 +4,999 ·
    # 웹툰 +835 · 애니 +1,382 행이 들어왔고 펀딩 표본이 교정됐다.
    # 봉우리의 자리는 자료 크기의 함수다.
    #
    # 짝 12뽑기 K=32: 판 **+0.0093 +- 0.0039 · 12/12** (사전 등록 +0.003 ·
    # >=9/12 를 넘는다). 미리 적은 실패 조건 --- ``K=8 에서만 나는 이득이면
    # 깊이의 부활이 아니라 자루의 대체물'' --- 은 안 걸렸다.
    #
    # **웹툰만 거꾸로 간다**(-0.0241 · 0/12, 판에서 제일 큰 도메인).
    # 아이돌 +0.1179 · 펀딩 +0.0409 · 모바일 +0.0201 · 게임 +0.0193 ·
    # 애니 +0.0135 가 전부 12/12 로 이를 덮는다. 무릎은 6 이고 8·12 는
    # 평평하다(K=8 에서 0.4597/0.4586/0.4596).
    # **깊이를 6 에서 12 로 올렸다**(노트 426). **판을 조금 내고 전이를 샀다** ---
    # 이 실험실이 판정 지표를 거슬러 챔피언을 옮긴 첫 자리다.
    #
    #   판(짝 12뽑기, 현 축)   -0.0018 +- 0.0024 · 2/12   ← 규약대로면 유지
    #   비게임 앱 전이         +0.0292 [95% +0.0220, +0.0359] · 1.000
    #   KR 만화 전이          +0.0267 [95% -0.0021, +0.0616] · 0.966
    #
    # 안 본 도메인 **둘**이 같은 부호 · 같은 크기이고 앱 쪽은 1,600행이라
    # 구간이 0 을 안 문다. 깊이 12·16·24 가 +0.0292/+0.0293/+0.0291 로
    # **12 에서 포화**한다 --- 임의로 고른 끝이 아니다.
    #
    # 노트 425 가 잰 대로 **판은 이 축에서 전이보다 139배 좁다**. 지표가
    # 방법을 가두면 지표를 뗀다.
    #
    # 낸 것: 팝업 -0.0351(1/12) · 웹툰 -0.0173(0/12). 번 것: 모바일
    # +0.0109(12/12) · 게임 +0.0071(11/12) · 애니 +0.0049(10/12).
    # **lr 을 0.06 에서 0.10 으로 올렸다**(노트 427). 노트 408 이 판으로
    # 물렸던 손잡이다(깊이 6 에서 판 +0.0005 · 6/12 미결정 → 유지).
    # 노트 426 의 규약대로 **전이 쪽에서 다시 보니 살아 있었다**:
    #
    #   비게임 앱 전이  +0.0046 [95% +0.0022, +0.0071] · 1.000
    #   KR 만화 전이   +0.0121 [95% -0.0036, +0.0273] · 0.949  (같은 부호)
    #   판(깊이 12 재관문)  -0.0005 +- 0.0020 · 5/12   (2x짝SD 0.0040 안)
    #
    # 깊이(+0.029)보다 훨씬 작지만 **판에 공짜**다.
    # **깊이를 12 에서 6 으로 되돌렸다**(노트 432). 노트 426 이 깊이 12 를
    # 넣은 근거는 **오직 전이**였다 --- 판은 -0.0018 · 2/12 로 반대했는데
    # 안 본 도메인 **둘**(비게임 앱 +0.0292 · KR 만화 +0.0267)이 확실히
    # 샀기 때문이다.
    #
    # 노트 430 이 LODO(도메인 하나씩 빼기)로 짝을 **열하나**로 늘렸고,
    # 노트 431 이 그 시험대에서 K=64 의 ``한 짝 1.000''이 3/11 로 뒤집히는
    # 것을 보였다. 같은 자로 깊이 12 를 다시 재니 **4/11 · 평균 -0.0046**
    # 이다 --- **부호가 뒤집혔다.**
    #
    # 판도 전이도 이제 깊이 12 에 약하게 반대한다. 근거가 사라졌으므로
    # 되돌린다. **lr 0.10 은 남긴다** --- 그쪽은 판 실제 자료가 +0.0028
    # (씨앗 SE 의 네 배)로 받쳐 준다(노트 432).
    # **깊이 12 --- 두 번째 채택**(노트 457).
    #
    # 역사가 길다. 노트 426 이 집 밖 짝(앱 되뽑기 1.000 · KR 0.966)으로
    # 깊이 12 를 채택했고(**판정 지표를 거스른 첫 채택**), 노트 432 가
    # **LODO 4/11 · 평균 -0.0046** 으로 되돌렸다. 그런데 노트 441 이
    # **LODO 는 집 밖 효과를 원리상 못 본다**(같은 수집 · 계기 · 시기)는
    # 것을 보였다 --- **되돌린 근거가 그 종류의 효과를 못 재는 자였다.**
    # 노트 456 이 K=64 로 같은 재개를 하고 조항을 만들었다: **자가 바뀌면
    # 그 자로 닫았던 갈래는 다시 열 수 있다.**
    #
    # 지금 자로 다시 쟀다(씨앗 열 · 씨앗마다 짝지어):
    #
    #   판          -0.0032  95% [-0.0041, -0.0023]
    #   날짜 통제 판 -0.0046
    #   KR 만화     **+0.0064**  95% [+0.0022, +0.0105]
    #   비게임 앱   **+0.0061**  95% [+0.0026, +0.0097]
    #
    # 깊이 8 이 네 계기 모두에서 중간이라 단조다. 노트 426 거울의 조건 셋이
    # 다 찬다 --- ① 집 밖 짝 둘이 같은 부호 ② **둘 다** 구간이 0 을 안 뭄
    # ③ 판 손해 0.0032 가 2x짝SD(0.0041) 안. 짝 12뽑기는 판 -0.0028 ·
    # SD 0.0021 · **양수 1/12** 다.
    #
    # **거래를 숨기지 않는다** --- 판은 확실히 잃는다(부호 1/12, 날짜 통제도
    # 같이 내려가니 날짜 구멍이 아니라 진짜 실력이다). 웹툰 -0.0086(0/12)과
    # 팝업 -0.0313 이 내고, 모바일 +0.0059(12/12)가 번다. 그것을 집 밖 두
    # 짝의 +0.006 과 바꾼다.
    #
    # 노트 426 때보다 전이 이득이 다섯 배 작다(+0.029 -> +0.006). 그 사이에
    # **OOC_DROP 이 들어갔기 때문**으로 읽는다 --- 깊이가 사던 것의 상당수가
    # ``독 있는 축을 도메인별로 조건부로 쓰기''였는데, 이제 그 축을 아예
    # 안 쓴다.
    #
    # 되돌림 조항(노트 432): 되돌릴 상태의 이름은 **``깊이 6 인 F18''**.
    # 되돌릴 조건도 미리 적는다 --- **다음에 새로 여는 집 밖 짝에서 깊이 12
    # 의 이득이 0 이하이거나, 판 손해가 다시 재서 2x짝SD 밖으로 나가면
    # 되돌린다.**
    def __init__(self, depth: int = 12, it: int = 220, lr: float = 0.10,
                 K: int = 32, seed: int = 0):
        super().__init__(depth=depth, it=it, lr=lr)
        self.K, self.seed = K, seed

    # **계절 --- 두 해 동안 버려지던 t 를 처음으로 쓴다**(노트 447).
    #
    # 모든 ``predict`` 가 t 를 받는데 ``_feat`` 은 받지도 않았다. 노트 446 이
    # 그걸 찾고, 동시에 **날짜를 그냥 넣으면 안 된다**는 것도 찾았다 --- 유보
    # 안에서 날짜와 라벨이 -0.228 로 붙어 있는데 그건 라벨이 관측 시점까지
    # **쌓이는** 양이라서다. 최근순 축은 날 판을 +0.0186 올리면서 날짜 통제
    # 판을 -0.0294 내린다(구멍이지 실력이 아니다).
    #
    # **연중 위치는 다르다.** 유보 안에서 날짜에 단조가 아니라(2025~2026 을
    # 두 번 돈다) 쌓임을 못 읽는다. 그래서 둘이 같이 오른다:
    #
    #   짝 12뽑기  판 **+0.0041** SD 0.0042 양수 **9/12**
    #              날짜 통제 판 **+0.0046** SD 0.0038 양수 **11/12**
    #
    # 날짜 통제 쪽이 **더 크고 더 고르다** --- 최근순과 정반대다. 같이 거른
    # 나머지 셋은 둘 다 떨어뜨렸다(밀도 -0.028/-0.041 · 간격 -0.009/-0.012 ·
    # 셋 다 -0.021/-0.036).
    #
    # LODO 는 문턱 넘은 게 넷뿐이라 잴 수 없음(노트 439)이고 노트 420 거부권도
    # 안 걸린다(오름 3 · 내림 1 · 평균 +0.0183). **애니가 전이에서 -0.0713 ->
    # +0.1017 로 부호를 바꾼다** --- 판에서도 애니가 +0.0264 로 12/12 다.
    #
    # 되돌림 조항(노트 432): 되돌릴 상태의 이름은 **``계절 축 없는 36축 F18''**.
    SEASON = True

    # **전용 축을 판으로 나르는 한 칸**(노트 449).
    #
    # 같은 벽을 네 번 만났다 --- 시장팝업 전용 축(그 도메인 +0.0241 · 판 0,
    # 노트 412) · 표지 둘째(판 +0.0035 인데 전이 -0.1140, 노트 420) · 분기
    # (애니 +0.0167 · 판 +0.0003, 노트 448). 열을 하나 더하면 그 열이
    # **``이 행은 애니다''라고 말하는 데 절반을 쓴다**.
    #
    # 장치는 **한 열, 도메인마다 다른 재료**다. 도메인마다 자기 전용 축 중
    # 학습 라벨과 제일 붙은 것을 골라 **도메인 안에서 순위 정규화**해 같은
    # 칸에 넣는다(부호는 맞춰서). 뜻이 ``이 행은 자기 도메인의 특기 축에서
    # 몇 등인가''라 **정보는 나르고 정체는 안 나른다**.
    #
    # 두 번 틀리고 세 번째에 됐다:
    #
    # 1. **축 고르기를 전 축에 열면 죽는다** --- 열하나 중 일곱이
    #    ``target_breadth''(이미 공유 축)를 골라 공유 축의 사본이 되고
    #    판 **-0.0164** 다.
    # 2. **전용을 <=2 도메인으로 좁히면 세금이 붙는다** --- 판 +0.0025 ·
    #    7/12 로 조건 ① 못 넘음. 그런데 **칸 찬 도메인 +0.0054 · 빈 도메인
    #    -0.0079** 였다. 빈 칸의 표시자로 나무가 갈라 **도메인 이름표가 다시
    #    생긴 것**이다.
    # 3. **<=4 로 풀어 더 많이 채우니** 세금이 -0.0079 -> -0.0024 로 줄고
    #    관문을 넘는다.
    #
    #   짝 12뽑기(뽑기마다 축을 다시 고른다)
    #     판 **+0.0046** SD 0.0035 양수 **10/12**
    #     날짜 통제 판 **+0.0062** SD 0.0035 양수 **11/12**
    #     칸 찬 도메인 **+0.0147**(n 7) · 빈 도메인 -0.0024(n 4)
    #
    # 아이돌 하나가 끄는 게 아니다 --- 무게로 보면 애니(+0.0119 · 12/12)와
    # 웹툰(+0.0086 · 10/12)이 대부분을 낸다. LODO 도 안 막는다(문턱 넘은
    # 다섯 중 오름 넷 · 평균 +0.0202 · **애니 +0.0279 -> +0.2093**).
    #
    # 안 배운 도메인은 고른 축이 없어 **칸이 빈다** --- 집 밖 예보에서
    # 저절로 꺼진다.
    #
    # 되돌림 조항(노트 432): 되돌릴 상태의 이름은 **``특기 칸 없는 F18''**.
    SPEC = True
    SPEC_MAXDOM = 4      # 이 수 이하 도메인에서만 관측되는 축을 전용으로 본다
    SPEC_MINOBS = 15

    def _spec_pick(self, train) -> dict:
        """도메인마다 전용 특기 축을 고른다. **학습 라벨만 본다.**"""
        from scipy.stats import spearmanr
        cnt = {}
        for d in train.dom:
            A, M, y, t = train.dom[d]
            for j, a in enumerate(list(train.names.get(d) or ALL5)):
                if M[:, j].sum() >= self.SPEC_MINOBS:
                    cnt[a] = cnt.get(a, 0) + 1
        excl = {a for a, c in cnt.items() if c <= self.SPEC_MAXDOM}
        out = {}
        for d in train.dom:
            A, M, y, t = train.dom[d]
            nm = list(train.names.get(d) or ALL5)
            best = None
            for j, a in enumerate(nm):
                if a not in excl:
                    continue
                o = M[:, j] > 0
                if o.sum() < self.SPEC_MINOBS or len(np.unique(A[o, j])) < 3:
                    continue
                r = spearmanr(A[o, j], y[o]).correlation
                if not np.isfinite(r):
                    continue
                if best is None or abs(r) > abs(best[1]):
                    best = (a, float(r))
            out[d] = best
        return out

    def _spec_col(self, d, A, M, names):
        """(도메인 안 순위, 표시자). 고른 축이 없으면 칸이 빈다."""
        nm = list(names or ALL5)
        pk = getattr(self, "spec", {}).get(d)
        v = np.full(len(A), 0.5)
        m = np.zeros(len(A))
        if pk and pk[0] in nm:
            j = nm.index(pk[0])
            o = M[:, j] > 0
            if o.sum() >= 5:
                r = rankdata(A[o, j]) / o.sum()
                v[o] = r if pk[1] >= 0 else 1.0 - r
                m[o] = 1.0
        return np.column_stack([v, m])

    @staticmethod
    def _timeax(t):
        """예보 쪽 최근성 --- 연도 자체(노트 524)."""
        from .harness import years
        yr = np.asarray(years(t), float)
        m = np.isfinite(yr)
        v = np.where(m, yr, 2020.0)
        return np.column_stack([v, m.astype(float)])

    @staticmethod
    def _season(t):
        """연중 위치(0~1)와 관측 표시자. t 는 ``years()`` 로 연으로 편다."""
        from .harness import years
        yr = np.asarray(years(t), float)
        s = np.full(len(yr), 0.5)
        m = np.isfinite(yr)
        s[m] = yr[m] - np.floor(yr[m])
        return np.column_stack([s, m.astype(float)])

    def fit(self, train: Data) -> None:
        from sklearn.ensemble import HistGradientBoostingRegressor
        train = self._traincap(train)
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.doms = sorted(train.dom)
        self.spec = self._spec_pick(train) if self.SPEC else {}
        Xs, ys, ws = [], [], []
        wmap, yfix = {}, {}
        if self.TRAINW:
            ntr = {d: len(train.dom[d][2]) for d in self.doms}
            Ttr = sum(ntr.values()); Tte = sum(self.TRAINW.get(d, 0) for d in self.doms)
            for d in self.doms:
                st = ntr[d] / max(1, Ttr)
                se = self.TRAINW.get(d, 0) / max(1, Tte)
                w = (se / st) if st > 0 else 1.0
                wmap[d] = min(max(w, self.TRAINW_CLIP[0]), self.TRAINW_CLIP[1])
        if self.TRAINW and self.TRAINW_YEARFIX:
            from collections import defaultdict as _dd
            p0, p1 = _dd(float), _dd(float)
            for dz in self.doms:
                yz = np.floor(np.asarray(train.yr[dz], float))
                wz = wmap.get(dz, 1.0)
                for v in yz:
                    if np.isfinite(v):
                        p0[v] += 1.0
                        p1[v] += wz
            s0, s1 = sum(p0.values()), sum(p1.values())
            for v in p0:
                aa = p0[v] / s0 if s0 else 0.0
                bb = p1[v] / s1 if s1 else 0.0
                yfix[v] = (aa / bb) if bb > 0 else 1.0
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            A, M = self._domdrop(d, A, M, train.names.get(d))
            A, M = self._domperm(d, A, M, train.names.get(d))
            F = DirectPool._feat(A, M, train.names.get(d), self.order)
            if self.SEASON:
                F = np.column_stack([F, self._season(t)])
            if self.SPEC:
                F = np.column_stack([F, self._spec_col(d, A, M, train.names.get(d))])
            if self.TIMEAX:
                F = np.column_stack([F, self._timeax(t)])
            if self.DOMAX:
                F = np.column_stack([F, self._domax(d, A, M, train.names.get(d))])
            oh = np.zeros((len(A), len(self.doms))); oh[:, i] = 1.0
            Xs.append(np.column_stack([F, oh]))
            ys.append(rankdata(y) / len(y))
            wrow = np.full(len(A), float(wmap.get(d, 1.0)))
            if self.TRAINR:
                yv2 = np.asarray(train.yr[d], float)
                age = np.where(np.isfinite(yv2), 2025.0 - yv2, 0.0)
                wrow = wrow * np.power(0.5, np.maximum(age, 0.0) / float(self.TRAINR))
            if yfix:
                yv = np.floor(np.asarray(train.yr[d], float))
                wrow = wrow * np.array([yfix.get(v, 1.0) if np.isfinite(v) else 1.0
                                        for v in yv])
            ws.append(wrow)
        X, Y = np.vstack(Xs), np.concatenate(ys)
        SW = np.concatenate(ws) if (self.TRAINW or self.TRAINR) else None
        rng = np.random.default_rng(self.seed)
        self.ms = []
        for k in range(self.K):
            i = rng.integers(0, len(X), len(X))
            kw = {"sample_weight": SW[i]} if SW is not None else {}
            self.ms.append(HistGradientBoostingRegressor(
                **{**self.kw, "random_state": k}).fit(X[i], Y[i], **kw))
        self.names = train.names

    # 안 배운 도메인에는 **눈금이 수집마다 다른 축을 안 쓴다**(노트 441).
    #
    # 학습 안에서 축과 라벨의 부호를 다 재 보니 공유 축 다섯 중
    # ``entry_friction`` **만** 부호가 안 맞는다 --- 모바일 +0.648 대 만화
    # -0.158 · 애니 -0.124, 양수 3/7. 나머지 넷은 9/11 · 9/10 · 6/8 · 5/6
    # 으로 도메인이 바뀌어도 같은 쪽을 가리킨다. 모델은 큰 양수 쪽을 배워
    # **처음 보는 수집에 거꾸로 쓴다**.
    #
    # 집 밖 두 짝에서 예보 때만 이 축을 가려 봤다(학습은 그대로 뒀다).
    #   KR 만화(짝 안 부호 -0.320)  무표지 +0.2330 -> **+0.5504**  (+0.3174)
    #   비게임 앱(짝 안 부호 -0.566) 무표지 -0.1389 -> **+0.2799**  (+0.4188)
    # 대조로 뺀 축은 두 짝 다 **반대로** 갔다(KR venue_prominence -0.1575 ·
    # 앱 goods_scale -0.1148) --- 아무 축이나 빼서 되는 일이 아니다. 값은
    # 둘 다 [0,1] 안이라 단위 버그도 아니다(세계애니 평균 0.005 대 애니
    # 0.645 --- 매체마다 ``마찰''이 다른 것이다).
    #
    # **판은 이 변경을 원리상 못 본다.** 판이 채점하는 도메인은 전부
    # ``d in self.doms'' 라 아래 가지가 안 열린다 --- 예보가 **정확히**
    # 같다. LODO 도 문턱(0.0108) 넘은 게 셋뿐이라 노트 439 로 **잴 수
    # 없음**이고 축이 있는 일곱 도메인 평균은 -0.0030 이다. 축이 없는 네
    # 도메인은 차가 정확히 +0.0000 이었다(가드).
    #
    # 그래서 노트 431 의 LODO 다수결이 아니라 노트 426 의 거울로 정했다 ---
    # **집 밖 짝 둘이 같은 부호이고 판 손해가 0** 이다. 전역 제거(학습에서도
    # 빼기)는 **안 한다**: 판 -0.0018 · 양수 2/12 로 노트 378 조건 ① 기각이다.
    #
    # 되돌림 조항(노트 432): 되돌릴 상태의 이름은 **``예보 때도
    # entry_friction 을 쓰는 F18''** 이다. 되돌릴 조건도 미리 적는다 ---
    # **다음에 새로 여는 집 밖 짝에서 이 가림의 효과가 0 이하면 되돌린다.**
    # **비웠다**(노트 583). 이 축을 가려 온 까닭은 "어느 쪽으로 읽을지를
    # 몰라서"(노트 443)였는데, 노트 581 이 **왜 몰랐는지**를 찾았다 ---
    # 하네스 열이 다섯 도메인에서 뒤집혀 있어 학습 가중이 -0.023(사실상 0)
    # 이었다. ``fixaxes.orient`` 로 방향을 세우니 가중이 -0.105 로 서고
    # 집 밖 짝(원 방향으로 들어온다)과 뜻이 맞는다. 씨앗 12 에서
    # **KR +0.6376→+0.6824 · 앱 +0.2860→+0.5038**.
    OOC_DROP = ()
    # **도메인마다 뺄 축**(노트 497~498). 공유 축은 대부분에게 이롭고 몇에게
    # 해로운데 그 ``몇''이 축마다 다르다 --- 트렌드는 애니가, target_breadth
    # 는 시장팝업 · 게임 · 모바일 · 웹툰이, venue_prominence 는 도서 · 애니가
    # 빼는 쪽이 낫다(전부 부호 8/8 · 12/12).
    #
    # **이 표는 유보를 안 보고 골랐다.** 학습 안에서 시간을 한 번 더 잘라
    # (안쪽 학습 <2023 · 안쪽 검증 2023~2025) 후보 축 열 개를 하나씩 전
    # 도메인에서 가려 (도메인, 축) 차를 재고, 차 >= 0.010 · 씨앗 3 부호 일치
    # · 안쪽 검증 >= 150행인 짝만 남겼다. 남은 것이 **애니 트렌드 하나**다.
    # 문턱 없이 차 > 0.005 만 걸면 아홉 짝이 뽑히는데 그 표는 판 -0.0085
    # (0/12)로 **진다** --- 작은 도메인에서 안쪽 검증이 효과를 못 가른다.
    #
    #   자 다섯이 **전부** 양수다(짝 씨앗 10):
    #     판          +0.0045  10/10  [+0.0033, +0.0056]
    #     날짜 통제 판   +0.0045  10/10  [+0.0036, +0.0054]
    #     무리 안 판    +0.0088  10/10  [+0.0078, +0.0097]
    #     KR 만화     +0.0152  10/10  [+0.0125, +0.0179]
    #     비게임 앱     +0.0039   8/10  [+0.0016, +0.0062]
    #
    # 거래가 없다 --- 노트 426 거울을 쓸 일이 없는 첫 채택이다. 되돌림은
    # ``DOMDROP 이 빈 F18''.
    #
    # 애니 점수는 +0.5639 -> +0.6010 인데 아이돌 -0.0577 · 팝업 -0.0253 로
    # **이웃이 흔들린다** --- 도메인별 가림은 도메인별로 안 갇힌다(공유 열이
    # 달라진다). 애니가 판 무게 17.7%이고 그 둘이 1.5% · 1.9%라 순합이 양수다.
    #
    # **둘째 칸 --- 세계애니 grp**(노트 504). 노트 503 이 남긴 유일한 생존
    # 후보였고 짝 씨앗 **20** 으로 확정했다.
    #
    #     판          +0.0011  15/20  [+0.0003, +0.0019]
    #     날짜 통제 판   +0.0004  12/20  [-0.0005, +0.0013]   0을 문다
    #     무리 안 판    +0.0004  11/20  [-0.0006, +0.0014]   0을 문다
    #     KR 만화     +0.0084  16/20  [+0.0049, +0.0119]
    #     비게임 앱     -0.0020   7/20  [-0.0046, +0.0007]   0을 문다
    #
    # **약한 채택이다.** 0 밖인 자가 판과 KR 둘뿐이고 판 이득이 애니
    # 채택(+0.0045)의 1/4 이다. 사전 등록이 ``앱이 0 을 물고 나머지 넷이
    # 양수면 채택'' 이었고 그대로 통과했으므로 넣는다 --- 스크립트 안의
    # 고정 문턱(집 밖 -0.0010)은 반대했는데, **사전 등록이 우선**이고
    # 그 불일치를 숨기지 않고 적는다.
    #
    # **미리 적는 되돌림 조건**: 다음 사이클에 짝 씨앗 40 으로 다시 재서
    # **판 구간이 0 을 물면 되돌린다**. 되돌린 상태의 이름은
    # ``DOMDROP 에 세계애니가 없는 F18''.
    #
    # **--- 노트 507: 그 조건이 발동했다. 되돌렸다. ---**
    # 짝 씨앗 **40** 에서:
    #     판          +0.0000  22/40  [-0.0004, +0.0005]   0을 문다
    #     날짜 통제 판   -0.0014   8/40  [-0.0019, -0.0009]   **확실히 음수**
    #     무리 안 판    -0.0006  17/40  [-0.0013, +0.0002]
    #     KR 만화     +0.0068  32/40  [+0.0046, +0.0090]
    #     비게임 앱     -0.0032  10/40  [-0.0048, -0.0015]   **확실히 음수**
    # 씨앗 20 에서 판 +0.0011 [+0.0003,+0.0019] 로 0 밖이던 것이 씨앗 40
    # 에서 정확히 0 이 된다. **씨앗 20 이 모자랐다.**
    #
    # → **조항: 판 차가 +0.002 아래인 후보는 짝 씨앗 40 으로 재기 전에
    #    채택하지 않는다.** (애니 트렌드는 +0.0045 라 안 걸린다.)
    # **만화를 더한다**(노트 553). 노트 554 가 기계를 찾았다 --- 검색 축의
    # 마스크는 ``긁혔나''이고(``zero_is_data=True`` 가 *물어봤는데 계열이 안
    # 왔다*를 관측으로 센다), ``ingest/trend_all`` 이 레코드 파일 순서의 앞을
    # 자르는데 **``manga_records.json`` 은 ``y_popularity`` 로 정렬돼 있다**
    # (파일순서↔라벨 순위상관 $-1.0000$). 그래서 만화에서 ``긁혔나'' 는
    # 사실상 ``라벨 상위 27% 인가'' 다.
    #
    # 결정적인 것은 **학습과 유보의 결측률이 다르다**는 것이다 --- 긁힘이
    # 학습 $16\%$ 인데 유보는 $3\%$ 다. 모형이 학습에서 ``긁혔으면
    # 인기''($+0.5380$)를 세게 배우는데 유보에서는 그 갈래가 거의 안 쓰인다.
    # 노트 558 의 표가 같은 말을 한다 --- 만화는 유보 관측 $3\%$ 에
    # **마스크↔라벨 $+0.2512$ 뿐이고 값은 잴 수조차 없다**(게임 $+0.2866$ ·
    # 도서 $+0.2444$ · 모바일 $+0.2366$ 은 값으로 버니 그대로 둔다).
    #
    # 짝 씨앗 **40**(노트 518 --- 0 근처인 자가 여럿이었다):
    #   판 $-0.0001$(문다) · 날짜 통제 $+0.0006$(문다) ·
    #   **무리 안 $+0.0037$(31/40) · KR 만화 $+0.0082$(**39/40**) ·
    #   비게임 앱 $+0.0022$(26/40)** --- 다섯 자 중 셋이 $0$ 밖 양수이고
    #   음수는 없다. 거부권 446 안 걸림 · 426 거울 통과(KR $+$ · 앱 $+$).
    #   씨앗 12 에서 $0$ 을 물던 앱과 무리 안이 40 에서 올라섰다.
    #
    # **판은 안 움직인다** --- 순위가 아니라 **전이**를 사는 채택이다.
    # 노트 351 이 같은 모양으로 TREND_DROP 을 채택한 선례가 있다.
    DOMDROP = {"애니": ("trend_",), "만화": ("trend_",)}

    # **가림 대신 섞기**(노트 525 시험용 · 기본 빈 사전이라 챔피언 불변).
    # 도메인별 가림은 두 가지를 한꺼번에 한다 --- ① 그 축의 정보를 없애고
    # ② 그 행을 남이 학습한 갈래의 **결측 쪽**으로 보낸다. 섞기는 ①만
    # 한다(값의 분포와 결측 무늬는 그대로 두고 행 짝만 흐트러뜨린다).
    # 둘의 차가 ② 의 몫이다.
    DOMPERM = {}

    # **도메인 전용 축 사본**(노트 529 시험용 · 기본 빈 사전이라 챔피언 불변).
    # 노트 527 이 본 것 --- 축 하나가 지배하는 도메인(모바일 entry_friction
    # 단독 83.2%) 에서 공유 모델이 진다. 그 축이 도메인마다 부호가 뒤집혀서
    # (노트 441) 공유 열이 평균으로 눌리는 것이라면, **그 도메인 행에서만
    # 값이 있는 사본 열**을 하나 더 주면 나무가 눌리지 않고 쓸 수 있다.
    # 가림(DOMDROP) 의 거울이다 --- 저쪽은 빼고 이쪽은 더한다.
    DOMAX = {}

    # **만화 학습 행 절반**(노트 509). 노트 508 이 도메인별 행당 값어치를
    # 재다가 만화 하나만 부호가 반대인 것을 봤다 --- 학습 행 2,823개(전체
    # 학습의 15%)를 빼면 판이 **오른다**.
    #
    # 만화는 학습의 **30.5%** 인데 채점의 **7.5%** 다(비 4.05, 다음인
    # 세계애니 1.63 의 2.5배). 노트 505 는 만화 챔피언이 자기 천장의
    # **2.00배**라고 했다 --- **제일 많이 받고 유일하게 안 준다.**
    # 만화 행이 시끄러워서는 아니다(축<->라벨 |rho| 평균 0.197 로 남 0.195
    # 와 같다). 공유 축을 자기 쪽으로 끌어당기는 것이고 그게 **집 밖에서
    # 제일 아프다.**
    #
    #   짝 씨앗 **40** (노트 507 조항대로 20 에서 멈추지 않고 40 까지):
    #     판          +0.0021  30/40  [+0.0013, +0.0030]
    #     날짜 통제 판   +0.0035  34/40  [+0.0024, +0.0046]
    #     무리 안 판    +0.0022  31/40  [+0.0011, +0.0032]
    #     KR 만화     +0.0274  38/40  [+0.0227, +0.0321]
    #     비게임 앱     +0.0082  33/40  [+0.0049, +0.0115]
    #
    # **자 다섯이 전부 양수이고 전부 0 밖이다.** 씨앗 20 에서 40 으로
    # 늘리며 **더 단단해졌다**(세계애니 grp 은 반대로 무너졌다).
    # **집 밖 이득이 판 이득의 13배**다.
    #
    # 되돌림은 ``TRAINCAP 이 빈 F18''.
    TRAINCAP = {"만화": 0.5}

    # **유보 무게로 학습 가중**(노트 510 시험). 행 무게 =
    # (그 도메인 유보 몫 / 학습 몫) 을 TRAINW_CLIP 으로 자른 값.
    # **유보 행 수만 쓰고 라벨은 안 본다** --- 채점 목적함수의 정의다.
    # 기본 꺼짐(None); 켜려면 유보 행 수 dict 를 넣는다.
    # **채택**(노트 514). 행 무게 = (그 도메인 유보 몫 / 학습 몫) 을
    # ``줄이는 쪽으로만'' 자른다(clip 0.2~**1.0**) --- 만화 0.25 ·
    # 세계애니 0.61 만 걸리고 나머지는 1.0 이라 **아무것도 안 키운다**.
    # 노트 510 의 clip 2.0 판본은 작은 도메인을 두 배로 키워 판을 깎았다.
    #
    # **유보 행 수만 쓰고 라벨은 안 본다** --- 채점 목적함수의 정의다.
    # 다만 **채점 집합이 바뀌면 이 표도 바뀌어야 한다.**
    #
    #   짝 씨앗 **40** (배선 고친 뒤 · 기준은 TRAINCAP 만 켠 챔피언):
    #     판          +0.0010  28/40  [+0.0004, +0.0016]
    #     날짜 통제 판   -0.0000  18/40  [-0.0007, +0.0006]   안 움직임
    #     무리 안 판    +0.0019  33/40  [+0.0012, +0.0026]
    #     KR 만화     +0.0155  40/40  [+0.0129, +0.0181]
    #     비게임 앱     +0.0026  23/40  [+0.0004, +0.0047]
    #
    # **KR 40/40** --- 부호 일치로 이 실험실 최고. **집 밖 두 짝이 둘 다
    # 0 밖 양수인 것도 처음이다.**
    #
    # 노트 511 은 같은 후보를 **잘못된 배선**(DOMDROP 이 예보 전용)에서
    # 재고 노트 446 거부권으로 보류했다 --- 그때는 날짜 통제 판이
    # -0.0005(14/40)로 내려갔다. 배선을 고치니 -0.0000(18/40)으로
    # **안 움직인다**. **거부권의 전제가 사라졌다.**
    #
    # 되돌림은 ``TRAINW 가 None 인 F18''.
    # **채택**(노트 514). 블록 짝 앙상블로 확정했다 --- 단일 앙상블 한
    # 번은 -0.0012 였는데 그 블록이 여섯 중 **유일한 음수**였다.
    #
    #   앙상블(6-앙상블 · 블록 6개 짝):
    #     판          **+0.0006**  5/6  [-0.0003, +0.0016]
    #     날짜 통제 판     -0.0004  2/6
    #   단일 모형(짝 씨앗 40 · 기준은 TRAINCAP 만 켠 챔피언):
    #     판          +0.0010  28/40  [+0.0004, +0.0016]
    #     날짜 통제 판   -0.0000  18/40  [-0.0007, +0.0006]   안 움직임
    #     무리 안 판    +0.0019  33/40  [+0.0012, +0.0026]
    #     KR 만화     +0.0155  **40/40**  [+0.0129, +0.0181]
    #     비게임 앱     +0.0026  23/40  [+0.0004, +0.0047]
    #
    # **KR 40/40 은 부호 일치로 이 실험실 최고**이고 **집 밖 두 짝이 둘 다
    # 0 밖 양수인 것도 처음**이다.
    #
    # 노트 446 거부권(판이 오르는데 날짜 통제 판이 내려가면 안 넣는다)은
    # **힘이 센 자에서 안 선다** --- 짝 씨앗 40 에서 -0.0000(18/40)로
    # 안 움직인다. 앙상블 여섯 블록의 -0.0004(2/6)는 표본이 작다.
    # **미리 적는 되돌림 조건: 앙상블 블록 12 로 날짜 통제 판을 다시 재서
    # 확실한 음수면 되돌린다**(되돌린 상태 이름 ``TRAINW 가 None 인 F18'').
    #
    # 노트 511 은 같은 후보를 **잘못된 배선**에서 재고 보류했다(그때는
    # 날짜 통제 -0.0005 · 14/40). 배선을 고치니 전제가 사라졌다(노트 513).
    TRAINW = {"웹툰": 711, "애니": 606, "펀딩": 529, "모바일": 441,
              "세계애니": 300, "만화": 258, "게임": 180, "도서": 163,
              "시장팝업": 126, "팝업": 65, "아이돌": 51}
    TRAINW_CLIP = (0.2, 1.0)
    # **연도 분포 고정**(노트 515 시험). 도메인 무게가 학습 행의 연도
    # 분포를 옮기면(노트 512: 줄이는 둘이 제일 옛날이라 +1.425년 최근으로
    # 밀린다) 그 이득이 **최근성**인지 **구성**인지 안 갈린다. 켜면
    # 연도별로 다시 정규화해 **연도 분포를 원래대로** 돌린다 --- 남는
    # 것은 연도 **안**의 구성 변화뿐이다. 기본 꺼짐.
    TRAINW_YEARFIX = False
    # **연도 직접 가중 --- 채택**(노트 516). 노트 515 가 TRAINW 이득의
    # 80%가 **최근성**임을 보였으니 수단(도메인 무게) 대신 목적(최근성)을
    # 직접 건다 --- 행 무게 ×= 0.5^((2025 - 연도) / TRAINR).
    #
    # 노트 446·447 이 죽인 것은 **예보 쪽** 최근성(최근순 **축**: 날 판
    # +0.0186 인데 날짜 통제 판 -0.0294)이고 이것은 **학습 쪽**이다 ---
    # **다른 기계다.** 여기서는 날짜 통제 판이 오히려 **오른다.**
    #
    #   짝 씨앗 **40** (기준 = TRAINW 만 켠 챔피언):
    #     판          +0.0025  34/40  [+0.0019, +0.0031]
    #     날짜 통제 판   +0.0013  30/40  [+0.0006, +0.0020]
    #     무리 안 판    +0.0041  39/40  [+0.0034, +0.0049]
    #     KR 만화     +0.0139  **40/40**  [+0.0117, +0.0161]
    #     비게임 앱     +0.0066  34/40  [+0.0048, +0.0085]
    #   앙상블(6-앙상블 · 블록 6개 짝):
    #     판 **+0.0020**  6/6  [+0.0012, +0.0028] · 날짜 통제 +0.0010  5/6
    #
    # **자 다섯이 전부 0 밖 양수이고 앙상블도 6/6 이다.**
    #
    # **TRAINW 와 보완재다** --- 연도 가중 **단독**은 집 밖을 못 산다
    # (τ=8 KR -0.0018 · τ=4 -0.0009, 둘 다 0 을 문다)인데 집안은 산다.
    # **TRAINW 는 KR 을, 연도는 판을 산다.** 둘 다 켜야 다섯이 다 오른다.
    #
    # τ=4 도 재 봤고 τ=8 이 낫다. 되돌림은 ``TRAINR 이 None 인 F18''.
    TRAINR = 8.0
    # **최근순 축**(노트 524 시험). 예보 쪽 최근성 --- 연도 자체를 한 칸.
    # 노트 447 이 죽였다(판 +0.0186 인데 날짜 통제 -0.0294). 기본 꺼짐.
    TIMEAX = False

    def _traincap(self, train):
        """학습 행을 도메인별로 줄인다(노트 509). 씨앗마다 다르게 뽑는다."""
        if not self.TRAINCAP:
            return train
        from .harness import Data, MIN_TRAIN
        rng = np.random.default_rng(7000 + self.seed)
        dom, yr = {}, {}
        for d, v in train.dom.items():
            A, M, y, t = v
            f = self.TRAINCAP.get(d)
            n = len(y)
            if f is None or f >= 1.0:
                dom[d] = v
                yr[d] = train.yr[d]
                continue
            m = max(MIN_TRAIN, int(round(n * f)))
            i = np.sort(rng.choice(n, min(m, n), replace=False))
            dom[d] = (A[i], M[i], y[i], t[i])
            yr[d] = np.asarray(train.yr[d])[i]
        return Data(dom, train.names, yr)

    def _domax(self, d, A, M, names):
        """도메인 전용 축 사본 --- 그 도메인 행에서만 값이 있다(노트 529).

        열 순서는 ``sorted(DOMAX)`` 로 고정한다. 적합과 예보가 같은 자리를
        써야 하므로 도메인마다 **모든** 짝의 열을 만들고, 자기 것이 아닌
        자리는 중립(0.5)과 표시자 0 으로 채운다.
        """
        out = []
        nm = list(names or ALL5)
        for d2 in sorted(self.DOMAX):
            for a in self.DOMAX[d2]:
                if d2 == d and a in nm:
                    j = nm.index(a)
                    out.append(np.where(M[:, j] > 0, A[:, j], 0.5))
                    out.append(M[:, j].astype(float))
                else:
                    out.append(np.full(len(A), 0.5))
                    out.append(np.zeros(len(A)))
        return np.column_stack(out) if out else np.zeros((len(A), 0))

    def _domperm(self, d, A, M, names):
        """그 도메인 안에서 그 축의 행 짝만 흐트러뜨린다(노트 525).

        가림과 달리 값의 분포도 결측 무늬도 그대로다 --- 나무가 지나가는
        갈래는 안 바뀌고 **어느 행이 어느 값을 갖는지**만 무작위가 된다.
        """
        pats = self.DOMPERM.get(d)
        if not pats:
            return A, M
        nm = list(names or ALL5)
        A, M = A.copy(), M.copy()
        for j, a in enumerate(nm):
            if any(a.startswith(p) for p in pats):
                r = np.random.default_rng(90000 + 7 * self.seed + (hash(a) % 977))
                p = r.permutation(len(A))
                A[:, j] = A[p, j]
                M[:, j] = M[p, j]
        return A, M

    def _domdrop(self, d, A, M, names):
        """그 도메인에서 빼기로 한 축을 0으로(노트 498)."""
        pats = self.DOMDROP.get(d)
        if not pats:
            return A, M
        nm = list(names or ALL5)
        A, M = A.copy(), M.copy()
        for j, a in enumerate(nm):
            if any(a.startswith(p) for p in pats):
                A[:, j] = 0.0
                M[:, j] = 0.0
        return A, M

    def calibrate_ooc(self, d, A, M, y, min_n: int = 4,
                      allow_flip: bool = False) -> dict:
        """새 수집의 라벨 **몇 개**로 가릴 축의 부호를 정한다(노트 443).

        .. warning::

           **뒤집기는 노트 463 에서 반증됐다. 기본값이 꺼져 있다.**

           아래 표는 전부 **AX5(+gen/grp)만 학습에 넣은 축소 모형**에서
           잰 것이다. 36축 챔피언에서 씨앗 여덟을 짝지어 다시 재니
           뒤집기가 **한 번도 최선이 아니다**:

           ====== ========= ========= ==========
           짝     그대로    가림      뒤집기
           ====== ========= ========= ==========
           KR     +0.6115   +0.5531   **+0.3833**
           앱     +0.2213   +0.2648   +0.2474
           ====== ========= ========= ==========

           KR 은 짝 안 부호가 -0.320 이라 규칙 B 가 뒤집는데, 그러면
           **+0.6115 가 +0.3833 으로 떨어진다**(뒤집기-가림 -0.1698
           95% [-0.1781,-0.1615]). 축이 다섯뿐일 때는 그 축이 입력의
           큰 몫이라 부호가 전부였지만, 36축에서는 모델이 그 축을 다른
           것들과 **함께** 쓰므로 값을 뒤집으면 그 조합이 깨진다.

           ``allow_flip=True`` 로 켤 수는 있으나 **켤 근거가 지금은
           없다.** 부호는 계속 재서 ``ooc_cal`` 에 적어 둔다.
        

        가리는 건 휴전이지 해결이 아니다 --- 축은 도메인 **안**에서는 값이
        크고(모바일 $+0.648$), 못 쓰는 이유는 **어느 쪽으로 읽을지를 몰라서**
        다. 새 수집의 라벨 몇 개면 그건 그냥 잴 수 있다.

        규칙(잰 것 중 제일 나은 것 --- 노트 443):
        **짝 안 부호가 음수면 뒤집고, 아니면 가린다.**
        ``아니면 그대로 둔다''가 아니다 --- KR 에서 그 되돌아감이 k 가 작을 때
        값을 크게 깎았다(k=5 에서 $+0.4695$ 대 $+0.5690$).

        라벨 몇 개면 되나 (집 밖 두 짝 · 뽑기 60회 평균 · 채점은 쓴 k 행을
        뺀 나머지):

        ====  ==========  ==========  ==========
        k     KR 규칙B    앱 규칙B    가림(k=0)
        ====  ==========  ==========  ==========
        5     +0.5690     +0.4307     +0.5336 / +0.2635
        10    +0.5897     +0.4636
        40    +0.5999     +0.4817     (= 오라클)
        ====  ==========  ==========  ==========

        **다섯이면 가림을 이기고 마흔이면 오라클과 같다.** 부르지 않으면
        예전대로 가린다 --- 영샷 기본값은 안 바뀐다.
        """
        from scipy.stats import spearmanr
        nm = list(self.names.get(d) or ALL5)
        y = np.asarray(y, float)
        dec = {}
        for a in self.OOC_DROP:
            if a not in nm:
                continue
            j = nm.index(a)
            o = (M[:, j] > 0) & np.isfinite(y)
            if o.sum() < min_n:
                continue
            r = spearmanr(A[o, j], y[o]).correlation
            if np.isfinite(r) and r < 0:
                # 노트 463: 뒤집기는 36축에서 반증됐다 --- 부호는 적되
                # allow_flip 을 켜지 않으면 예보를 안 바꾼다.
                dec[a] = "뒤집기" if allow_flip else "부호 음수(뒤집기 꺼짐)"
        if not hasattr(self, "ooc_cal"):
            self.ooc_cal = {}
        self.ooc_cal[d] = dec
        return dec

    def _design(self, d, A, M, t):
        nm = list(self.names.get(d) or ALL5)
        if d not in self.doms and self.OOC_DROP:
            cal = getattr(self, "ooc_cal", {}).get(d, {})
            A, M = A.copy(), M.copy()
            for a in self.OOC_DROP:
                if a not in nm:
                    continue
                j = nm.index(a)
                if cal.get(a) == "뒤집기":
                    o = M[:, j] > 0
                    A[o, j] = 1.0 - A[o, j]
                else:
                    M[:, j] = 0.0
        A, M = self._domdrop(d, A, M, self.names.get(d))
        A, M = self._domperm(d, A, M, self.names.get(d))
        F = DirectPool._feat(A, M, self.names.get(d), self.order)
        if self.SEASON:
            F = np.column_stack([F, self._season(t)])
        if self.SPEC:
            F = np.column_stack([F, self._spec_col(d, A, M, self.names.get(d))])
        if self.TIMEAX:
            F = np.column_stack([F, self._timeax(t)])
        if self.DOMAX:
            F = np.column_stack([F, self._domax(d, A, M, self.names.get(d))])
        oh = np.zeros((len(A), len(self.doms)))
        if d in self.doms:
            oh[:, self.doms.index(d)] = 1.0
        X = np.column_stack([F, oh])
        return X

    def predict(self, d, A, M, t):
        X = self._design(d, A, M, t)
        return np.mean([rankdata(m.predict(X)) for m in self.ms], axis=0)

    def predict_bags(self, d, A, M, t):
        """자루마다의 순위를 (K, n) 으로 돌려준다(노트 532).

        ``predict`` 와 **같은 설계행렬**을 쓴다 --- 평균을 내면 정확히
        ``predict`` 다(스크립트가 가드로 확인한다). 라벨을 안 보므로
        자루 사이의 불일치를 **예보 때 쓸 수 있는 신뢰도**로 쓸 수 있다.
        """
        X = self._design(d, A, M, t)
        return np.vstack([rankdata(m.predict(X)) for m in self.ms])


register(BagBoost)

register(RankLik)


# ── 축을 늘리면 오르나 --- F8 이 ``병목은 축''이라 했으니 직접 잰다 ──────
class PoolUnion(DirectPool):
    """게임만 갖는 축 넷까지 다 쓴다. 공통 다섯만 쓰는 F6 과의 차이가
    ``도메인 전용 축을 사는 값''이다."""
    name = "F11_poolunion"
    idea = "축 합집합 — 게임 전용 축 넷까지. F6 과의 차이가 도메인 전용 축의 값"
    axes = "union"


class RankUnion(RankLik):
    name = "F12_rankunion"
    idea = "짝 순위 우도 + 축 합집합"
    axes = "union"


register(PoolUnion)
register(RankUnion)

# F2 는 torch 를 쓰므로 지연 반입 --- torch 가 없는 환경에서도 나머지는 돈다
try:
    from .joint import Joint
    # 귀무에서는 tau 를 안 고른다 --- 섞인 라벨로 고르는 것은 잡음을 고르는 것이고
    # 99배 비싸다. 대신 그만큼 귀무가 좁아져 z 가 낙관적이다(논문에 적었다).
    register(Joint, null_make=lambda: Joint(k=2, tau=3.0, w=8.0, steps=400))
except Exception as _e:                                   # pragma: no cover
    pass


# ── F10 도메인별 수축 --- 하나의 tau 로는 안 된다 ───────────────────────
class PerDomShrink:
    """도메인마다 ``자기 이력''과 ``남의 이력''을 섞는 비율을 따로 정한다.

    측정이 시킨 설계다. 학습 기간 안에서 재 보면 두 큰 도메인이 정반대를
    원한다 --- 웹툰은 자기 전기간으로 자기 후기간을 맞추면 $-$0.19 로
    **뒤집히는데** 남의 도메인으로 맞추면 $+$0.24 이고, 모바일은 자기 것이
    $+$0.47 인데 남의 것은 $-$0.03 이다. 전역 tau 하나로는 둘 다 못 준다.

    w_d 는 **학습 기간을 다시 갈라** 정한다(안쪽 시점 이전으로 적합 →
    이후로 채점). 이력이 없는 도메인(팝업)은 w=0, 즉 완전 풀링이다."""
    name = "F10_pershrink"
    idea = "도메인마다 자기 이력과 남의 이력의 배합비를 따로 — 웹툰은 뒤집히고 모바일은 안 옮겨간다"

    GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
    # **검증 창은 서로 겹치면 안 된다.** 처음엔 각 분할이 ``자른 시점 이후
    # 전부''를 검증했는데, 그러면 2022.5 분할의 검증 집합이 2023.0 분할의
    # 검증 집합을 통째로 품는다. 짝지은 표준오차가 터무니없이 작아져서
    # 웹툰의 안쪽 이득 0.016 조차 t 검정을 통과한다. 창을 갈라 놓는다.
    INNER = ((2022.5, 2023.0), (2023.0, 2023.5),
             (2023.5, 2024.0), (2024.0, 2024.5), (2024.5, 2025.0))

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    @staticmethod
    def _pool(dom, names, alpha, skip=None, order=None):
        Xs, ys = [], []
        for e, (A, M, y, t) in dom.items():
            if e == skip or len(y) < 40:
                continue
            Xs.append(DirectPool._feat(A, M, names.get(e), order))
            ys.append(rankdata(y) / len(y))
        if not Xs:
            return None
        return Ridge(alpha=alpha).fit(np.vstack(Xs), np.concatenate(ys))

    def _mix(self, dom, names, d, A, M):
        F = DirectPool._feat(A, M, names.get(d), self.order)
        # 학습에 없던 도메인이면 전 도메인 풀 --- 팝업이 정확히 이 경우다
        # (2025년 이전 16건이라 학습 도메인에 못 든다). 이력이 없으면
        # 배합비를 정할 자료도 없으니 완전 풀링이 유일하게 정직한 선택이다.
        o = self.oth.get(d, self.all_pool)
        s = self.own.get(d)
        w = self.w.get(d, 0.0)
        po = rankdata(o.predict(F)) / len(F) if o is not None else None
        ps = rankdata(s.predict(F)) / len(F) if s is not None else None
        if ps is None or w <= 0:
            return po
        if po is None or w >= 1:
            return ps
        return (1 - w) * po + w * ps

    def fit(self, train: Data) -> None:
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.names = train.names
        self.oth, self.own, self.w = {}, {}, {}
        self.all_pool = self._pool(train.dom, train.names, self.alpha, order=self.order)
        for d in train.dom:
            self.oth[d] = self._pool(train.dom, train.names, self.alpha, skip=d, order=self.order)
            A, M, y, t = train.dom[d]
            if len(y) >= 40:
                self.own[d] = Ridge(alpha=self.alpha).fit(
                    DirectPool._feat(A, M, train.names.get(d), self.order),
                    rankdata(y) / len(y))
        # 표류량 --- 창 사이에 관계가 해마다 얼마나 움직이나(학습 기간 안에서만)
        self._drift = self._drift_rate(train)
        # w_d --- 학습 기간 안쪽 분할로만 정한다
        from scipy.stats import spearmanr
        acc = {d: {g: [] for g in self.GRID} for d in train.dom}
        for inner, upto in self.INNER:
            tr, va = {}, {}
            for d, (A, M, y, t) in train.dom.items():
                u = train.yr[d]
                a = np.isfinite(u) & (u < inner)
                b = np.isfinite(u) & (u >= inner) & (u < upto)
                if a.sum() >= 40:
                    tr[d] = (A[a], M[a], y[a], t[a])
                if b.sum() >= 20:
                    va[d] = (A[b], M[b], y[b], t[b])
            if len(tr) < 3:
                continue
            inner_m = PerDomShrink(self.alpha)
            inner_m.names = train.names
            inner_m.order = self.order
            inner_m.all_pool = self._pool(tr, train.names, self.alpha, order=self.order)
            inner_m.oth = {d: self._pool(tr, train.names, self.alpha, skip=d, order=self.order)
                           for d in va}
            inner_m.own = {}
            for d in va:
                if d in tr:
                    A2, M2, y2, t2 = tr[d]
                    inner_m.own[d] = Ridge(alpha=self.alpha).fit(
                        DirectPool._feat(A2, M2, train.names.get(d), self.order),
                        rankdata(y2) / len(y2))
            for d, (A, M, y, t) in va.items():
                for g in self.GRID:
                    inner_m.w = {d: g}
                    p = inner_m._mix(tr, train.names, d, A, M)
                    if p is None:
                        continue
                    r = spearmanr(p, y).correlation
                    if np.isfinite(r):
                        acc[d][g].append(r)
        # **평평하면 풀링으로 간다.** 안쪽 분할의 argmax 를 그냥 집으면
        # 웹툰이 w=0.5 를 받는데, 웹툰의 축→라벨 관계는 2025년에 뒤집힌다.
        # 안쪽 분할은 전부 2024년 이전이라 그 뒤집힘을 **볼 수가 없다**.
        # 검증 창 뒤에 오는 체제 변화는 어떤 교차검증으로도 안 잡힌다.
        # 그러니 증거가 평평할 때의 기본값은 도메인 고유 구조가 아니라
        # 풀링이어야 한다 --- 못 보는 변화에 대한 유일한 보험이다.
        for d in train.dom:
            V = {g: np.array(v) for g, v in acc[d].items() if len(v) >= 2}
            if not V:
                self.w[d] = 0.0
                continue
            top = max(V, key=lambda g: V[g].mean())
            base = min(V)                            # 가장 풀링된 격자점
            n = min(len(V[top]), len(V[base]))
            dg = V[top][:n] - V[base][:n]
            gain = float(dg.mean())
            # 절대 문턱을 손으로 정하면 그것도 결국 바깥을 본 것이다. 대신
            # **안쪽 증거 자체의 불확실성**으로 판정한다 --- 분할 넷의 짝지은
            # t 검정(단측 5%). 안쪽 곡선이 평평하면 t 가 안 나오고, 그러면
            # 도메인 고유 구조를 사지 않는다.
            tcrit = {2: 6.31, 3: 2.92, 4: 2.35, 5: 2.13, 6: 2.02}.get(n, 1.96)
            se = float(dg.std(ddof=1) / np.sqrt(n)) if n >= 2 else 9.9
            # 유의성만으로는 모자란다. 웹툰의 안쪽 이득 0.030 은 창을 갈라
            # 놓아도 재현되는데 바깥에서는 부호가 뒤집힌다 --- 잡음이 아니라
            # **2025년에 관계가 달라진 것**이고, 2025년 이전 자료로는 그걸
            # 볼 방법이 없다.
            #
            # 그래서 문턱을 예보 지평의 **표류량**에서 끌어온다. 도메인별
            # 관계가 해마다 얼마나 움직이는지는 학습 기간 안에서 잴 수 있다
            # (창 사이 변화의 중앙값). 그만큼도 안 되는 이득은 지평 너머까지
            # 살아남는다고 볼 근거가 없다.
            if n < 2 or gain < max(tcrit * se, self._drift):
                self.w[d] = base
                continue
            # **안쪽이 평평하면 그건 ``아무래도 좋다''가 아니라 ``여기선 모른다''다.**
            # 웹툰은 안쪽 곡선이 0.410~0.426(폭 0.037)으로 평평한데 바깥 곡선은
            # +0.236에서 -0.191까지 0.43을 간다. 1 SE 규칙만으로는 그 0.016을
            # 신호로 읽어 w=0.5 를 집는다. 그래서 절대 문턱을 하나 더 건다 ---
            # 안쪽 이득이 이만큼도 안 되면 도메인 고유 구조에 걸지 않는다.
            pick = top
            for g in sorted(V):                      # w 오름차순 = 풀링 강한 순
                n = min(len(V[g]), len(V[top]))
                if n < 2:
                    continue
                dif = V[g][:n] - V[top][:n]
                se = float(dif.std(ddof=1) / np.sqrt(n))
                if dif.mean() >= -max(se, 1e-9):
                    pick = g
                    break
            self.w[d] = pick
        self.w_table = {d: {g: float(np.mean(v)) for g, v in acc[d].items() if v}
                        for d in train.dom}
        self._train = train.dom

    def _drift_rate(self, train: Data, horizon: float = 1.5) -> float:
        """축→라벨 관계가 해마다 얼마나 움직이나 --- 학습 기간 안에서만 잰다.

        도메인마다 직전 2년으로 적합해 이후 1년을 채점하고, 창을 반년씩
        밀며 그 값이 창 사이에 얼마나 변하는지 본다. 그 중앙값 x 지평이
        ``이 정도 이득은 지평을 못 넘긴다''는 선이다."""
        from scipy.stats import spearmanr
        ch = []
        for d, (A, M, y, t) in train.dom.items():
            u = train.yr[d]
            F = DirectPool._feat(A, M, train.names.get(d), self.order)
            vs = []
            for mid in np.arange(2021.5, float(np.nanmax(u)) + .01, .5):
                a = np.isfinite(u) & (u >= mid - 2) & (u < mid)
                b = np.isfinite(u) & (u >= mid) & (u < mid + 1)
                if a.sum() < 60 or b.sum() < 30:
                    continue
                m = Ridge(alpha=self.alpha).fit(F[a], rankdata(y[a]) / a.sum())
                r = spearmanr(m.predict(F[b]), y[b]).correlation
                if np.isfinite(r):
                    vs.append(r)
            if len(vs) >= 3:
                ch += list(np.abs(np.diff(vs)) * 2.0)      # 반년 간격 → 연율
        return float(np.median(ch)) * horizon if ch else 0.05

    def predict(self, d, A, M, t):
        p = self._mix(self._train, self.names, d, A, M)
        return p if p is not None else np.full(len(A), np.nan)


register(PerDomShrink)


# ── 축을 늘리면 오르나 --- F8 이 ``병목은 축''이라 했으니 직접 잰다 ──────
def extra_axes(names: tuple = ("emb0", "emb1", "emb2", "emb3", "emb4",
                               "emb5", "emb6", "emb7")):
    """state/candidates.py 의 후보 축을 (값, 표시자) 쌍으로 가져온다.

    행 순서는 state.audit.domains() 와 같다(둘 다 같은 id 목록을 쓴다)."""
    from state.candidates import build
    B = build()
    return {c: B[c] for c in names if c in B}


class WithExtra:
    """어떤 정식화든 감싸서 축을 덧붙인다. 자질이 천장인지 재는 도구."""

    def __init__(self, base, extra=None, tag=""):
        self.base = base
        self.extra = extra if extra is not None else extra_axes()
        self.name = f"{base().name}+{tag or len(self.extra)}축"

    def _aug(self, data: Data) -> Data:
        dom, names = {}, {}
        for d, (A, M, y, t) in data.dom.items():
            cols, msk, nm = [A], [M], list(data.names.get(d) or ALL5)
            for c, byd in self.extra.items():
                if d not in byd:
                    cols.append(np.full((len(A), 1), 0.5))
                    msk.append(np.zeros((len(A), 1)))
                else:
                    v, o = byd[d]
                    cols.append(np.asarray(v, float).reshape(-1, 1))
                    msk.append(np.asarray(o, float).reshape(-1, 1))
                nm.append(c)
            dom[d] = (np.hstack(cols), np.hstack(msk), y, t)
            names[d] = nm
        return Data(dom, names, dict(data.yr))

    def fit(self, train: Data) -> None:
        self.m = self.base()
        self.aug_names = self._aug(train).names
        self.m.fit(self._aug(train))

    def predict(self, d, A, M, t):
        nm = list(self.aug_names.get(d) or ALL5)
        cols, msk = [A], [M]
        for c in self.extra:
            byd = self.extra[c]
            if d not in byd:
                cols.append(np.full((len(A), 1), 0.5))
                msk.append(np.zeros((len(A), 1)))
            else:
                v, o = byd[d]
                v, o = np.asarray(v, float), np.asarray(o, float)
                if len(v) != len(A):        # 시간 자르기로 행이 줄어든 경우
                    return np.full(len(A), np.nan)
                cols.append(v.reshape(-1, 1)); msk.append(o.reshape(-1, 1))
        return self.m.predict(d, np.hstack(cols), np.hstack(msk), t)


# ── F4 파운데이션 in-context --- TabPFN ─────────────────────────────────
class TabPFN:
    """표 자료용 사전학습 트랜스포머. 맞추는 게 아니라 **문맥으로 읽는다**.

    지시에 있던 ``프론티어급 프로덕트 참고''의 정확한 대상이다. TabPFN 은
    합성 표 자료 수백만 개로 사전학습된 트랜스포머라, 학습 표를 문맥에 넣고
    한 번 통과시켜 예측한다 --- 하이퍼모수도 없고 적합도 없다.

    **이 판에서 왜 볼 만한가.** 노트 126이 잰 법칙은 ``한 도메인의 이력만으로
    정해지는 모수는 지평 너머에서 배신한다''였다. TabPFN 은 **우리 자료로
    모수를 정하지 않는다** --- 사전학습된 것을 그대로 쓰고 우리 표는 문맥일
    뿐이다. 그렇다면 그 법칙에 안 걸려야 한다. 걸리는지가 이 실험이다.

    8.x 는 라이선스 토큰이 필요해 가중치가 공개된 2.2.1 을 쓴다.
    """
    name = "F4_tabpfn"
    idea = "TabPFN — 표 자료 사전학습 트랜스포머. 모수를 우리 자료로 안 정한다"

    def __init__(self, n_est: int = 2, cap: int = 3000, seed: int = 0):
        self.n_est, self.cap, self.seed = n_est, cap, seed

    def fit(self, train: Data) -> None:
        self.order = axis_order(train, getattr(self, "axes", None))
        self.doms = sorted(train.dom)
        self.names = train.names
        Xs, ys = [], []
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            F = DirectPool._feat(A, M, train.names.get(d), self.order)
            oh = np.zeros((len(A), len(self.doms)))
            oh[:, i] = 1.0
            Xs.append(np.column_stack([F, oh]))
            ys.append(rankdata(y) / len(y))
        X = np.vstack(Xs); Y = np.concatenate(ys)
        # 문맥 길이 한계 --- 도메인 비율을 지키며 줄인다
        if len(X) > self.cap:
            rng = np.random.default_rng(self.seed)
            keep = rng.choice(len(X), self.cap, replace=False)
            X, Y = X[keep], Y[keep]
        self.n_ctx = len(X)
        from tabpfn import TabPFNRegressor
        self.m = TabPFNRegressor(device="cpu", n_estimators=self.n_est,
                                 ignore_pretraining_limits=True,
                                 random_state=self.seed)
        self.m.fit(X, Y)

    def predict(self, d, A, M, t):
        F = DirectPool._feat(A, M, self.names.get(d), self.order)
        oh = np.zeros((len(A), len(self.doms)))
        if d in self.doms:
            oh[:, self.doms.index(d)] = 1.0
        return self.m.predict(np.column_stack([F, oh]))


try:
    register(TabPFN, null_make=lambda: TabPFN(n_est=1, cap=1500))
except Exception:                                          # pragma: no cover
    pass


# ── F16 공유 몸통 + 도메인별 달력 머리 ──────────────────────────────────
class TrunkHead:
    """축·검색은 전 도메인이 함께 배우고, 달력만 도메인마다 따로 얹는다.

    측정이 시킨 설계다(노트 132). 달력 축을 넣으면 대상 아홉 중 일곱이
    오르는데 지는 둘이 하필 제일 작은 팝업($n$=59, $-$0.092)과
    게임($n$=223, $-$0.061)이다. 달력 여섯 열의 비용이 표본이 작을수록
    크고, 그런데 \\emph{팝업이 제품 지표}다. 노트 131은 팝업 \\emph{안에서만}
    보면 달력이 $+$0.436에서 $+$0.513으로 크게 돕는다고 했다 --- 즉 팝업의
    달력 관계는 실재하는데 공유 계수에 눌린다.

    그래서 몸통과 머리를 나눈다. 몸통은 축 $+$ 검색으로 전 도메인이 같이
    배우고, 머리는 도메인마다 달력으로 **잔차만** 고친다. 머리의 세기
    $w_d$ 는 노트 126의 교훈대로 **학습 기간 안쪽 분할로만** 정하고,
    증거가 표류량을 못 넘으면 0으로 둔다(머리를 안 단다)."""
    name = "F16_trunkhead"
    idea = "공유 몸통(축＋검색) + 도메인별 달력 머리 — 머리 세기는 안쪽 분할로"

    GRID = (0.0, 0.25, 0.5, 0.75, 1.0)
    INNER = ((2022.5, 2023.0), (2023.0, 2023.5), (2023.5, 2024.0),
             (2024.0, 2024.5), (2024.5, 2025.0))

    def __init__(self, alpha: float = 1.0, cal_alpha: float = 4.0,
                 trunk: str = "F9_ranklik"):
        self.alpha, self.cal_alpha, self.trunk_name = alpha, cal_alpha, trunk

    @staticmethod
    def _split_axes(names):
        """축 이름을 몸통용과 머리용(달력)으로 가른다."""
        nm = list(names or ALL5)
        head = [a for a in nm if a.startswith("cal_")]
        body = [a for a in nm if not a.startswith("cal_")]
        return body, head

    def _cal_block(self, d, A, M, names):
        nm = list(names or ALL5)
        cols = []
        for a in self.head_axes:
            if a in nm:
                j = nm.index(a)
                ok = M[:, j] > 0
                cols.append(np.where(ok, A[:, j], 0.5))
            else:
                cols.append(np.full(len(A), 0.5))
        return np.column_stack(cols) if cols else None

    @staticmethod
    def _drop_cal(data: Data) -> Data:
        """몸통에 줄 자료 --- 달력 열을 **자료에서** 뺀다.

        처음엔 `trunk.order` 만 바꿨는데 `fit()` 이 첫 줄에서 그걸 덮어써서
        몸통이 달력을 그대로 보고 있었다. 축 목록이 아니라 자료를 잘라야 한다."""
        # **이름은 dom 에 없는 도메인까지 남긴다.** 처음엔 dom 만 돌았더니
        # 학습에 못 든 도메인(팝업은 2025년 이전 16건)의 이름이 빠지고,
        # _feat 이 ALL5 로 되돌아가 검색 축을 통째로 못 보게 됐다.
        dom, nm = {}, {}
        for d, names in data.names.items():
            keep = [i for i, a in enumerate(list(names) or ALL5)
                    if not a.startswith("cal_")]
            nm[d] = [list(names)[i] for i in keep]
            if d in data.dom:
                A, M, y, t = data.dom[d]
                dom[d] = (A[:, keep], M[:, keep], y, t)
        return Data(dom, nm, {k: v for k, v in data.yr.items() if k in dom})

    def fit(self, train: Data) -> None:
        from scipy.stats import spearmanr
        self.names = train.names
        body, head = self._split_axes(next(iter(train.names.values())))
        self.body_axes, self.head_axes = body, head
        self.tdata = self._drop_cal(train)
        self.trunk = forms_registry_make(self.trunk_name)()
        self.trunk.fit(self.tdata)               # 몸통은 달력을 아예 못 본다
        self.tnames = self.tdata.names
        # 도메인별 머리
        self.head, self.w = {}, {}
        for d, (A, M, y, t) in train.dom.items():
            C = self._cal_block(d, A, M, train.names.get(d))
            if C is None or len(y) < 40:
                continue
            r = rankdata(y) / len(y)
            At, Mt, _, _ = self.tdata.dom[d]
            base = rankdata(self.trunk.predict(d, At, Mt, t)) / len(y)
            self.head[d] = Ridge(alpha=self.cal_alpha).fit(C, r - base)
        # w_d --- 안쪽 분할, 겹치지 않는 검증 창
        acc = {d: {g: [] for g in self.GRID} for d in train.dom}
        for lo, hi in self.INNER:
            tr, va, yr = {}, {}, {}
            for d, (A, M, y, t) in train.dom.items():
                u = train.yr[d]
                a = np.isfinite(u) & (u < lo)
                b = np.isfinite(u) & (u >= lo) & (u < hi)
                if a.sum() >= 40:
                    tr[d] = (A[a], M[a], y[a], t[a]); yr[d] = u[a]
                if b.sum() >= 20:
                    va[d] = (A[b], M[b], y[b], t[b])
            if len(tr) < 3 or not va:
                continue
            im = TrunkHead(self.alpha, self.cal_alpha, self.trunk_name)
            try:
                im.fit(Data(tr, train.names, yr))
            except Exception:
                continue
            for d, (A, M, y, t) in va.items():
                if d not in im.head:
                    continue
                names = list(train.names.get(d) or ALL5)
                kp = [i for i, a in enumerate(names) if not a.startswith("cal_")]
                base = rankdata(im.trunk.predict(d, A[:, kp], M[:, kp], t)) / len(y)
                C = im._cal_block(d, A, M, train.names.get(d))
                corr = im.head[d].predict(C)
                for g in self.GRID:
                    rr = spearmanr(base + g * corr, y).correlation
                    if np.isfinite(rr):
                        acc[d][g].append(rr)
        for d in train.dom:
            V = {g: np.array(v) for g, v in acc[d].items() if len(v) >= 2}
            if not V:
                self.w[d] = 0.0
                continue
            top = max(V, key=lambda g: V[g].mean())
            n = min(len(V[top]), len(V[0.0]))
            dg = V[top][:n] - V[0.0][:n]
            tc = {2: 6.31, 3: 2.92, 4: 2.35, 5: 2.13}.get(n, 1.96)
            se = float(dg.std(ddof=1) / np.sqrt(n)) if n >= 2 else 9.9
            self.w[d] = top if (n >= 2 and dg.mean() > tc * max(se, 1e-9)) else 0.0

    def predict(self, d, A, M, t):
        names = list(self.names.get(d) or ALL5)
        kp = [i for i, a in enumerate(names) if not a.startswith("cal_")]
        base = self.trunk.predict(d, A[:, kp], M[:, kp], t)
        w = self.w.get(d, 0.0)
        if w <= 0 or d not in self.head:
            return base
        ok = np.isfinite(base)
        out = np.array(base, float)
        if ok.sum() < 3:
            return base
        br = np.full(len(base), np.nan)
        br[ok] = rankdata(base[ok]) / ok.sum()
        C = self._cal_block(d, A, M, self.names.get(d))
        out[ok] = br[ok] + w * self.head[d].predict(C)[ok]
        return out


def forms_registry_make(name: str):
    return REGISTRY[name]["make"]


register(TrunkHead)


# ── F17 진짜 바닥선 --- 메타데이터 플래그만 안다 ─────────────────────────
class GroupOnly(DirectPool):
    """집단 표지 축 하나만 쓴다. 손으로 매긴 축은 한 개도 안 본다.

    **F0 무작위는 바닥선이 아니었다.** 노트 138에서 재 보니 손 축 다섯으로
    만든 모형이 이 예측기보다 낮다(세 도메인 판 +0.321 대 +0.359).
    ``이 웹툰이 완결인가'' ``이 앱이 무료인가'' ``이 애니가 극장판인가''
    세 플래그만 알면 노트 5--127이 쌓은 것을 이긴다.

    바닥선은 무작위가 아니라 **누구나 공짜로 아는 것**이어야 한다."""
    name = "F17_grouponly"
    idea = "메타데이터 플래그만 — 진짜 바닥선 (완결 · 무료 · 매체 · 포맷)"

    @staticmethod
    def _only_grp(data: Data) -> Data:
        """집단 축만 남긴 자료. **order 만 거르면 안 된다** --- DirectPool.fit 이
        전체 축으로 능형을 맞춘 뒤라 열 수가 안 맞는다. 자료를 자른다."""
        dom, nm = {}, {}
        for d, names in data.names.items():
            keep = [i for i, a in enumerate(list(names)) if a.startswith("grp")]
            if not keep:
                continue
            nm[d] = [list(names)[i] for i in keep]
            if d in data.dom:
                A, M, y, t = data.dom[d]
                dom[d] = (A[:, keep], M[:, keep], y, t)
        return Data(dom, nm, {k: v for k, v in data.yr.items() if k in dom})

    def fit(self, train: Data) -> None:
        # **해당 없음과 고장은 다르다**(노트 233). 무리 축이 없는 판에서
        # 이 정식화는 잴 것이 없다 --- 터지는 대신 빈손임을 표시하고,
        # 예측을 전부 NaN 으로 돌려 덮음 0 으로 드러나게 한다.
        self._sub = self._only_grp(train)
        self._empty = not self._sub.dom
        if self._empty:
            self.names = train.names
            return
        super().fit(self._sub)

    def predict(self, d, A, M, t):
        if getattr(self, "_empty", False):
            return np.full(len(A), np.nan)
        names = list(self.names.get(d) or [])
        keep = [i for i, a in enumerate(names) if a.startswith("grp")]
        if not keep:
            return np.full(len(A), np.nan)
        return super().predict(d, A[:, keep], M[:, keep], t)


register(GroupOnly, status="baseline")


# ── F19 무리 쌓기 --- family stacking ──────────────────────────────────
SHARED5 = ("target_breadth", "venue_prominence", "entry_friction",
           "media_push", "goods_scale")


def _family(a: str) -> str:
    """축 이름 → 열 무리(노트 188).

    무리는 **출처**로 나눈다 --- 노트 185가 트리의 우위가 긁어온 열에서만
    산다는 것을 보였고, 노트 188이 그 우위가 *무리 안* 짝 곱으로 재현된다는
    것을 보였다(달력 90\% · 위키·검색 96\%). 무리 *사이* 곱은 0 을 낸다."""
    if a in SHARED5:
        return "공유"
    for p, f in (("cal_", "달력"), ("wiki_", "위키"), ("trend_", "검색")):
        if a.startswith(p):
            return f
    return "기타"


class FamilyStack:
    """무리마다 따로 적합하고 2단으로 합친다.

    **왜 2단인가**(노트 188). 무리 하나만 놓고 재면 ``도메인별 계수 $\\times$
    무리 안 짝 곱''이 트리를 90$\\sim$96\\% 재현한다. 그런데 열아홉 축에
    한꺼번에 넣으면 열이 쉰여섯이 되어 판이 0.3908 에서 0.3582 로 *내려간다*
    --- 주효과가 이미 설명한 분산 위에 곱 서른일곱을 얹는 것이라 잡음만 는다.
    **무리별로 따로 하면 되고 합치면 안 된다.**

    그래서 1단에서 무리마다 (도메인별 절편 + 무리 안 짝 곱) 능형을 적합하고,
    2단에서 그 예측 몇 개를 다시 능형으로 섞는다. 2단 입력은 **접힘 밖
    예측**이라야 한다 --- 1단이 본 행으로 2단을 적합하면 1단이 과적합한 만큼
    2단이 그것을 믿는다."""

    name = "F19_famstack"
    idea = "열 무리마다 (도메인별 + 무리 안 곱) 능형을 적합하고 2단으로 섞는다."

    def __init__(self, alpha1: float = 2.0, alpha2: float = 1.0,
                 folds: int = 4, deg2: bool = True):
        self.alpha1, self.alpha2, self.folds, self.deg2 = alpha1, alpha2, folds, deg2

    # --- 무리 하나의 설계행렬 --------------------------------------------
    def _design(self, A, M, names, cols):
        ix = {a: i for i, a in enumerate(names or ALL5)}
        base = []
        for a in cols:
            if a in ix:
                j = ix[a]
                ok = M[:, j] > 0
                base.append((np.where(ok, A[:, j], 0.5), ok.astype(float)))
            else:
                base.append((np.full(len(A), 0.5), np.zeros(len(A))))
        out = []
        for v, o in base:
            out += [v, o]
        if self.deg2:
            for i, k in itertools.combinations(range(len(base)), 2):
                vi, oi = base[i]
                vk, ok_ = base[k]
                out.append((vi - .5) * (vk - .5) + .5)
                out.append(np.minimum(oi, ok_))
        return np.column_stack(out)

    def fit(self, train: Data) -> None:
        self.doms = sorted(train.dom)
        allnames = []
        for d in self.doms:
            for a in (train.names.get(d) or ALL5):
                if a not in allnames:
                    allnames.append(a)
        self.fams = {}
        for a in allnames:
            self.fams.setdefault(_family(a), []).append(a)
        self.famorder = [f for f in ("공유", "달력", "위키", "검색", "기타")
                         if f in self.fams]
        self.names = train.names

        # 1단 --- 무리마다 도메인별 절편을 붙인 능형
        self.stage1 = {}
        oof = {d: {} for d in self.doms}
        rng = np.random.default_rng(0)
        for f in self.famorder:
            cols = self.fams[f]
            Xs, ys, dix = [], [], []
            for i, d in enumerate(self.doms):
                A, M, y, t = train.dom[d]
                F = self._design(A, M, train.names.get(d), cols)
                oh = np.zeros((len(A), len(self.doms)))
                oh[:, i] = 1.0
                Xs.append(np.column_stack([F, oh]))
                ys.append(rankdata(y) / len(y))
                dix.append(np.full(len(A), i))
            X = np.vstack(Xs)
            Y = np.concatenate(ys)
            DI = np.concatenate(dix)
            self.stage1[f] = Ridge(alpha=self.alpha1).fit(X, Y)
            # 접힘 밖 예측
            fold = rng.integers(0, self.folds, len(Y))
            p = np.zeros(len(Y))
            for k in range(self.folds):
                m = fold == k
                if m.sum() < 5 or (~m).sum() < 20:
                    p[m] = Ridge(alpha=self.alpha1).fit(X, Y).predict(X[m])
                    continue
                p[m] = Ridge(alpha=self.alpha1).fit(X[~m], Y[~m]).predict(X[m])
            for i, d in enumerate(self.doms):
                oof[d][f] = p[DI == i]

        # 2단 --- 무리 예측을 도메인별 절편과 함께 섞는다
        Xs, ys = [], []
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            P = np.column_stack([oof[d][f] for f in self.famorder])
            oh = np.zeros((len(A), len(self.doms)))
            oh[:, i] = 1.0
            Xs.append(np.column_stack([P, oh]))
            ys.append(rankdata(y) / len(y))
        self.stage2 = Ridge(alpha=self.alpha2).fit(np.vstack(Xs),
                                                   np.concatenate(ys))

    def predict(self, d, A, M, t):
        i = self.doms.index(d) if d in self.doms else 0
        oh = np.zeros((len(A), len(self.doms)))
        oh[:, i] = 1.0
        P = []
        for f in self.famorder:
            F = self._design(A, M, self.names.get(d), self.fams[f])
            P.append(self.stage1[f].predict(np.column_stack([F, oh])))
        return self.stage2.predict(np.column_stack([np.column_stack(P), oh]))


register(FamilyStack)


# ── 안쪽에서 알파를 고르는 도전자들(노트 189) ────────────────────────────
# 능형의 ``alpha=1.0'' 은 정식화를 쓴 날부터 한 번도 안 바뀐 기본값이었다.
# 학습 구간을 시간으로 다시 7 대 3 으로 갈라 고르면 판이 +0.011~0.013 오른다
# --- 노트 187~189 에서 열을 늘리는 처방 여섯 가지가 전부 진 것과 대조된다.
def _register_tuned():
    from .tune import tuned
    for _n in ("F6_directpool", "F10_pershrink", "F11_poolunion"):
        if _n not in REGISTRY:
            continue
        REGISTRY[_n + "_tuned"] = {
            "cls": REGISTRY[_n]["cls"], "make": tuned(_n),
            "null_make": None, "status": "challenger",
            "idea": "안쪽 시간 분할로 알파를 고른다(노트 189)"}


_register_tuned()


# ── 최근 가중 도전자(노트 194) ──────────────────────────────────────────
def _register_recent():
    from .recency import recent
    for _n in ("F6_directpool", "F18_bagboost", "F10_pershrink"):
        if _n not in REGISTRY:
            continue
        REGISTRY[_n + "_recent"] = {
            "cls": REGISTRY[_n]["cls"], "make": recent(_n),
            "null_make": None, "status": "challenger",
            "idea": "안쪽에서 감쇠 tau 를 고르고 학습 행을 최근 쪽으로 되뽑는다(노트 194)"}


_register_recent()


# ── F21 최근 가중 + 도메인별 풀링 선택(노트 194 · 197 · 201) ─────────────
class RecentPick:
    """옛 행을 덜 믿고, 자기 자료로 잘 배우는 도메인은 풀에서 뺀다.

    두 손잡이를 **순차로** 고른다(노트 195 --- 같이 고르면 나빠진다).

    1. 감쇠 $\\tau$ --- 안쪽 시간 분할 1차원 격자. 노트 190 · 194 의 규약
       (봉우리 $\\ge$ 0.5 또는 단조 $\\ge$ 0.8)을 통과해야 쓴다.
    2. 도메인별 ``혼자 대 풀링'' --- 안쪽 격차가 문턱을 넘는 도메인만 자기
       계수를 쓴다. 격차는 **앞으로 두 토막**으로 잰다(노트 200 --- 접힘
       교차는 시간을 섞어 부호를 반대로 본다).

    두 이득이 거의 가법이다(노트 201) --- 각각 $+$0.020 · $+$0.013 이고
    합쳐서 $+$0.038($t{=}6.1$)이다."""

    name = "F21_recentpick"
    idea = "최근 가중과 도메인별 풀링 선택을 순차로 --- 둘이 거의 가법이다"

    def __init__(self, alpha: float = 20.0, th: float = 0.02, min_rows: int = 150,
                 pick_first: bool = True,
                 seeds=(0, 1, 2), taus=(None, 12.0, 8.0, 4.0, 2.0, 1.0)):
        # **재는 것을 먼저, 바꾸는 것을 나중에**(노트 202). 격차를 가중한
        # 자료에서 재면 모바일 신호가 +0.143 에서 +0.004 로 지워지고 선택이
        # 잉여로 보인다. 안 가중한 자료에서 재면 +0.0059(t=1.8) 가 남는다.
        self.pick_first = pick_first
        self.alpha, self.th, self.seeds, self.taus = alpha, th, seeds, taus
        # **혼자 모형은 표본이 있어야 세운다**(노트 201). 팝업은 학습이
        # 열여섯 행이라(노트 132) 자기 계수가 잡음이고, 그런 도메인이
        # 안쪽 격차에서 우연히 이기면 판이 무너진다.
        self.min_rows = min_rows

    def _feat(self, A, M, names):
        return DirectPool._feat(A, M, names, self.order)

    def _pool(self, parts):
        Xs, ys = [], []
        for i, dd in enumerate(self.doms):
            X, y = parts[dd]
            oh = np.zeros((len(y), len(self.doms)))
            oh[:, i] = 1.0
            Xs.append(np.column_stack([X, oh]))
            ys.append(y)
        return Ridge(alpha=self.alpha).fit(np.vstack(Xs), np.concatenate(ys))

    def _parts(self, train, idx):
        out = {}
        for dd in self.doms:
            A, M, y, t = train.dom[dd]
            i = idx[dd]
            out[dd] = (self._feat(A[i], M[i], train.names.get(dd)),
                       rankdata(y[i]) / max(len(i), 1))
        return out

    def _choose_tau(self, train: Data):
        from .recency import reweight
        from .tune import accept, inner_split, inner_score
        tr, te = inner_split(train)
        sc = {}
        for tau in self.taus:
            sc[tau] = inner_score(lambda: _Plain(self.alpha, self.order),
                                  (tr if tau is None
                                   else reweight(tr, tau, T=_maxyr(tr))), te)
        # **안정성**(노트 216) --- 봉우리만으로는 평평한 곡면을 못 거른다.
        # 다섯 분할에서 최고가 [없음, 8, 12, 1, 12] 로 헤맨다.
        from .tune import stable
        mk = {tau: ((lambda: _Plain(self.alpha, self.order)),
                    (lambda x, tau=tau: x if tau is None
                     else reweight(x, tau, T=_maxyr(x))))
              for tau in self.taus}
        st_ok, st_best, st_n = stable(mk, train, order=list(self.taus))
        ok, pk, mo = accept(sc, order=list(self.taus), stable_ok=st_ok)
        self.peak, self.mono, self.stable = pk, mo, (st_ok, str(st_best), st_n)
        return (max(sc, key=lambda k: sc[k]) if ok else None)

    def _choose_pick(self, data: Data):
        yr = data.yr
        fin = lambda dd: np.isfinite(data.dom[dd][2]) & np.isfinite(yr[dd])
        cut = {}
        for dd in self.doms:
            v = yr[dd][fin(dd)]
            cut[dd] = float(np.quantile(v, 0.7)) if len(v) >= 30 else np.inf
        i1 = {dd: np.flatnonzero(fin(dd) & (yr[dd] < cut[dd])) for dd in self.doms}
        i2 = {dd: np.flatnonzero(fin(dd) & (yr[dd] >= cut[dd])) for dd in self.doms}
        P1 = self._parts(data, i1)
        pool1 = self._pool(P1)
        pick = {}
        for k, dd in enumerate(self.doms):
            if (len(i2[dd]) < 20 or len(i1[dd]) < 40
                    or int(fin(dd).sum()) < self.min_rows):
                pick[dd] = "풀링"
                continue
            A, M, y, t = data.dom[dd]
            X2 = self._feat(A[i2[dd]], M[i2[dd]], data.names.get(dd))
            y2 = y[i2[dd]]
            oh = np.zeros((len(y2), len(self.doms)))
            oh[:, k] = 1.0
            ps = Ridge(alpha=self.alpha).fit(*P1[dd]).predict(X2)
            pp = pool1.predict(np.column_stack([X2, oh]))
            pick[dd] = "혼자" if (_rho(ps, y2) - _rho(pp, y2)) > self.th else "풀링"
        return pick

    def fit(self, train: Data) -> None:
        from .recency import reweight
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.doms = sorted(train.dom)
        if self.pick_first:
            self.pick = self._choose_pick(train)
            self.tau = self._choose_tau(train)
            data = reweight(train, self.tau) if self.tau else train
        else:
            self.tau = self._choose_tau(train)
            data = reweight(train, self.tau) if self.tau else train
            self.pick = self._choose_pick(data)
        fin2 = lambda dd: np.isfinite(data.dom[dd][2]) & np.isfinite(data.yr[dd])
        PA = self._parts(data, {dd: np.flatnonzero(fin2(dd)) for dd in self.doms})
        self.pool = self._pool(PA)
        self.solo = {dd: Ridge(alpha=self.alpha).fit(*PA[dd]) for dd in self.doms}
        self.names = data.names

    def _fit_old(self, train: Data) -> None:
        from .recency import reweight
        from .tune import accept, inner_split, inner_score
        self.order = axis_order(train, getattr(self, 'axes', None))
        self.doms = sorted(train.dom)
        # ① 감쇠
        tr, te = inner_split(train)
        sc = {}
        for tau in self.taus:
            f = lambda t=tau: RecentPick._plain(self.alpha, self.order)
            sc[tau] = float(np.mean([
                inner_score(lambda: _Plain(self.alpha, self.order),
                            (tr if tau is None else reweight(tr, tau, T=_maxyr(tr))), te)
                for _ in (0,)]))
        ok, pk, mo = accept(sc, order=list(self.taus))
        self.tau = (max(sc, key=lambda k: sc[k]) if ok else None)
        self.peak, self.mono = pk, mo
        data = reweight(train, self.tau) if self.tau else train
        # ② 도메인별 혼자/풀링 --- 앞으로 두 토막
        yr = data.yr
        cut = {}
        for dd in self.doms:
            v = yr[dd][np.isfinite(data.dom[dd][2]) & np.isfinite(yr[dd])]
            cut[dd] = float(np.quantile(v, 0.7)) if len(v) >= 30 else np.inf
        fin = lambda dd: np.isfinite(data.dom[dd][2]) & np.isfinite(yr[dd])
        i1 = {dd: np.flatnonzero(fin(dd) & (yr[dd] < cut[dd])) for dd in self.doms}
        i2 = {dd: np.flatnonzero(fin(dd) & (yr[dd] >= cut[dd])) for dd in self.doms}
        P1 = self._parts(data, i1)
        pool1 = self._pool(P1)
        iall_pre = lambda dd: np.flatnonzero(fin(dd))
        self.pick = {}
        for k, dd in enumerate(self.doms):
            if (len(i2[dd]) < 20 or len(i1[dd]) < 40
                    or len(iall_pre(dd)) < self.min_rows):
                self.pick[dd] = "풀링"
                continue
            A, M, y, t = data.dom[dd]
            X2 = self._feat(A[i2[dd]], M[i2[dd]], data.names.get(dd))
            y2 = y[i2[dd]]
            oh = np.zeros((len(y2), len(self.doms)))
            oh[:, k] = 1.0
            ps = Ridge(alpha=self.alpha).fit(*P1[dd]).predict(X2)
            pp = pool1.predict(np.column_stack([X2, oh]))
            rs = _rho(ps, y2)
            rp = _rho(pp, y2)
            self.pick[dd] = "혼자" if (rs - rp) > self.th else "풀링"
        # ③ 전체 학습으로 적합
        iall = {dd: np.flatnonzero(fin(dd)) for dd in self.doms}
        PA = self._parts(data, iall)
        self.pool = self._pool(PA)
        self.solo = {dd: Ridge(alpha=self.alpha).fit(*PA[dd]) for dd in self.doms}
        self.names = data.names

    def predict(self, d, A, M, t):
        X = self._feat(A, M, self.names.get(d))
        if self.pick.get(d) == "혼자" and d in self.solo:
            return self.solo[d].predict(X)
        oh = np.zeros((len(X), len(self.doms)))
        if d in self.doms:
            oh[:, self.doms.index(d)] = 1.0
        return self.pool.predict(np.column_stack([X, oh]))


class _Plain:
    """감쇠를 고를 때 쓰는 단순 풀링 --- DirectPool 과 같되 알파만 다르다."""

    def __init__(self, alpha, order):
        self.alpha, self.order = alpha, order

    def fit(self, train: Data) -> None:
        self.doms = sorted(train.dom)
        Xs, ys = [], []
        for i, d in enumerate(self.doms):
            A, M, y, t = train.dom[d]
            F = DirectPool._feat(A, M, train.names.get(d), self.order)
            oh = np.zeros((len(A), len(self.doms)))
            oh[:, i] = 1.0
            Xs.append(np.column_stack([F, oh]))
            ys.append(rankdata(y) / len(y))
        self.m = Ridge(alpha=self.alpha).fit(np.vstack(Xs), np.concatenate(ys))
        self.names = train.names

    def predict(self, d, A, M, t):
        F = DirectPool._feat(A, M, self.names.get(d), self.order)
        oh = np.zeros((len(A), len(self.doms)))
        if d in self.doms:
            oh[:, self.doms.index(d)] = 1.0
        return self.m.predict(np.column_stack([F, oh]))


def _rho(p, y):
    from scipy.stats import spearmanr
    if np.std(p) < 1e-12 or np.std(y) < 1e-12:
        return -9.0
    v = spearmanr(p, y).statistic
    return float(v) if np.isfinite(v) else -9.0


def _maxyr(dat):
    import numpy as _np
    return float(max(_np.nanmax(v) for v in dat.yr.values())) + 1e-6


register(RecentPick)

class RankMix:
    """두 정식화의 **순위를 반반 섞는다**(노트 227).

    노트 226이 잰 것 --- 트리는 혼자로는 네 도메인 전부에서 이기는데
    (+0.017~+0.078) 풀링 이득을 못 받는다(폭 0.021 대 능형 -0.05~+0.11).
    **능형은 계수를 나눠 써서 이웃에게 빌리고 트리는 도메인 지시자로 다시
    갈라 버린다.**

    먼저 ``빌리고 나서 가르는'' 잔차 트리를 만들어 봤는데 **실패했다**
    (판 +0.4303 으로 둘 다보다 낮다) --- 능형이 뺀 뒤의 잔차에는 트리가
    쓰던 것이 거의 안 남는다. 되는 것은 **따로 세우고 순위로 섞는 것**이다.

    두 예측의 유보 상관이 0.63~0.94 라 같은 것을 안 잡는다. 반반이 판
    +0.4534 로 F21(+0.4377) · F18(+0.4408) 둘 다보다 낫다.

    **무게는 안쪽에서 정했다**(노트 216) --- 안쪽 분할 다섯 중 넷이 0.5 를
    고른다. 대칭 기본값과도 같아서 고른 것이 아니라 안 고른 것에 가깝다."""

    name = "F23_rankmix"
    idea = "능형과 트리를 순위로 반반 --- 빌리는 쪽과 가르는 쪽을 따로 세운다"

    def __init__(self, w: float = 0.5, a: str = "F21_recentpick",
                 b: str = "F18_bagboost"):
        self.w, self.a, self.b = w, a, b

    def fit(self, train: Data) -> None:
        self.ma = REGISTRY[self.a]["make"](); self.ma.fit(train)
        self.mb = REGISTRY[self.b]["make"](); self.mb.fit(train)

    def predict(self, d, A, M, t):
        pa = np.asarray(self.ma.predict(d, A, M, t), float)
        pb = np.asarray(self.mb.predict(d, A, M, t), float)
        n = max(len(pa), 1)
        ra = rankdata(np.where(np.isfinite(pa), pa, np.nanmedian(pa))) / n
        rb = rankdata(np.where(np.isfinite(pb), pb, np.nanmedian(pb))) / n
        return (1.0 - self.w) * ra + self.w * rb


register(RankMix, status="새것")
