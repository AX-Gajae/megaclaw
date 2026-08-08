"""방법과 무관한 평가 하네스.

**노트 124까지의 구조적 함정** --- ``앙상블 판정치''는 *쌍별 정렬 후 전이*가
있다고 전제한 정의였다. 그래서 TabPFN 이든 최적수송이든 확산 모형이든 **점수를
매길 수가 없었고**, 대안이 경쟁에 못 들어오니 자연히 현행만 손보게 됐다.
지표가 방법을 가둔 것이다.

여기서는 정식화에 요구하는 것이 하나뿐이다.

    (도메인, 축, 마스크, 시간) → 점수 벡터    (순위만 의미 있다)

그러면 무엇이든 붙는다. 현행 파이프라인도 이 인터페이스의 한 구현일 뿐이다.

**규약**(노트 77 · 106 · 112)

    엄격   출처는 T 이전, 대상은 T 이후. 설계 결정도 과거로 내린다
    배포   설계는 고정하고 출처만 자른다
    전체   시간을 안 가른다(참고용, 낙관적)
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import numpy as np
from scipy.stats import rankdata

from state.audit import domains
from state.rank_test import spearman

ASOF = 2026.57
PRIMARY = "팝업"
# 도메인이 학습 풀에 들어가려면 T 이전에 몇 건이 있어야 하나.
# 40 은 노트 5의 편의값이었다. 노트 133에서 재 보니 이 값이 팝업 하나만
# 가르고(나머지 아홉은 이미 40 이상) 15 로 낮추면 짝 순위 우도가 팝업에서
# +0.3698 에서 +0.4300 으로 오른다.
MIN_TRAIN = 15   # 40 → 15 (노트 402)
# 문턱은 **학습만** 거른다 --- 아래 도메인은 train 에서 빠지고도 **채점은
# 그대로 된다**. 그래서 문턱 40 은 팝업(학습 24행)을 원핫이 전부 0 인
# **안 본 도메인 상태**로 만들고 있었다. 노트 398~401 이 잰 바로 그 좌표다.
# 짝 12뽑기: 판 -0.0018 · 2/12, 움직인 도메인은 **팝업 하나뿐**
# (-0.0525 · 1/12). 두 팔이 같은 열한 도메인을 채점하므로 잴 수 있다.
_WARNED = set()


def fingerprint(data) -> dict:
    """축 자료의 **내용** 지문.

    노트 274 · 275가 같은 병에 세 번 걸렸다 --- 저장소에 남는 것은 축 세트
    ``이름``(``trendcalwiki``)인데 그 이름이 가리키는 열은 변한다. 노트 262 ·
    263이 웹툰 두 열을 막은 뒤에도 이름은 그대로였고, 그래서 07-30 의 값과
    07-31 의 값을 뺀 $-$0.067 이 나왔다(실제로는 $+$0.0071).

    노트 134가 ``무엇과 무엇을 견줬는지 기록하라''고 적었는데 그때 기록한
    것이 이름이었다. 여기서는 열 자체를 해싱한다. **지문이 다르면 두 실행의
    도메인 점수는 못 뺀다.**
    """
    import hashlib
    out = {}
    for d in sorted(data.dom):
        A, M, y, _t = data.dom[d]
        h = hashlib.sha256()
        for arr in (A, M, y, data.yr[d]):
            a = np.ascontiguousarray(np.asarray(arr, dtype=np.float64))
            # NaN 은 바이트가 여러 가지라 하나로 몰아 준다.
            h.update(np.nan_to_num(a, nan=-9.87e18).tobytes())
        h.update(("|".join(data.names.get(d) or [])).encode())
        out[d] = h.hexdigest()[:12]
    everything = hashlib.sha256(
        "".join(f"{k}:{v}" for k, v in sorted(out.items())).encode())
    out["_전체"] = everything.hexdigest()[:12]
    return out


def _warn(msg: str) -> None:
    """같은 경고를 한 번만 낸다 --- 라운드마다 수백 번 부르므로."""
    if msg in _WARNED:
        return
    _WARNED.add(msg)
    print(f"[하네스 경고] {msg}", flush=True)
    try:
        from . import store
        store.event(f"하네스 경고 — {msg}", "warn")
    except Exception:
        pass


def years(t) -> np.ndarray:
    t = np.asarray(t, float)
    fin = t[np.isfinite(t)]
    if len(fin) and np.nanmax(fin) > 1000:
        return t
    return ASOF - (10.0 ** t) / 365.25


@dataclass
class Data:
    """도메인 → (A, M, y, t). 하네스가 잘라서 정식화에 준다."""
    dom: dict
    names: dict
    yr: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.yr:
            self.yr = {d: years(self.dom[d][3]) for d in self.dom}

    def slice(self, d: str, keep) -> tuple:
        A, M, y, t = self.dom[d]
        return A[keep], M[keep], y[keep], t[keep]

    def rows(self, d: str, *, post: bool | None = None,
             labeled: bool = False, axis: str | None = None,
             T: float = 2025.0):
        """**어느 행이 진짜 있는 행인가**를 이름으로 묻는다(노트 271).

        이 판에는 서로 다른 행 집합이 셋 있고, 그것을 헷갈려 **세 번**
        조용히 틀렸다.

            post=True      유보 행 --- ``rank.predictions`` 가 돌려주는 길이
            labeled=True   라벨이 유한한 행 --- ``rank.pooled`` 가 채점하는 것
            axis="..."     그 축의 마스크가 선 행 --- 모형이 그 축을 보는 것

        셋이 다르다. 게임은 30일 창이 안 찬 43건 때문에 ``유보 행''이
        223 이고 ``라벨 있는 행''이 180 이다. 모바일 ``media\_push`` 는
        유보 100\% 인데 축 마스크는 13.6\% 다.

        틀린 자리 셋 --- 노트 264(가드가 축 마스크를 안 보고 원본 필드를
        전 행에서 읽었다) · 노트 266(후보 SVD 를 토큰 없는 행까지 넣고
        적합해 ``기록됐나'' 성분을 만들었다) · 노트 270(유보 행 수와 라벨
        있는 행 수를 같게 보고 길이를 견줘 게임이 조용히 표에서 빠졌다).
        셋 다 예외가 안 나고 숫자만 이상했다.

        기본은 전부 참(``rows(d)`` 는 모든 행)."""
        A, M, y, t = self.dom[d]
        k = np.ones(len(y), bool)
        if post is not None:
            yr = self.yr[d]
            k &= np.isfinite(yr) & ((yr >= T) if post else (yr < T))
        if labeled:
            k &= np.isfinite(y)
        if axis is not None:
            nm = list(self.names.get(d) or [])
            if axis not in nm:
                return np.zeros(len(y), bool)
            k &= M[:, nm.index(axis)] > 0
        return k

    def weights(self, T: float = 2025.0, min_rows: int = 20) -> dict:
        """도메인 → 채점되는 유보 행 수. **판 가중은 이걸로만 만든다**(노트 329).

        `dom[d][3]` 은 이름이 ``t`` 지만 일곱 도메인에서 **연도가 아니라
        로그 경과시간**이다(0.8~4.1). 그걸로 ``>= 2025`` 를 걸면 그 일곱이
        전부 유보 0 이 되고, 판이 2,675행 열 도메인에서 **268행 네 도메인**
        으로 조용히 줄어든다. 노트 328이 그렇게 판 학습SE 를 0.0163 대신
        0.0308 로 재고 미결정 폭을 넓히자고 했다.

        같은 오해가 재추출 함수에도 복사돼 있었다 --- 학습 행을
        ``t < 2025`` 로 고르니 그 일곱은 **유보까지 재추출**됐다.
        **한 번 잘못 이해하면 그 이해가 여러 군데로 간다.**
        """
        return {d: int(self.rows(d, post=True, labeled=True, T=T).sum())
                for d in self.dom
                if self.rows(d, post=True, labeled=True, T=T).sum() >= min_rows}

    def pooled(self, scores: dict, T: float = 2025.0) -> float:
        """도메인 점수 → 판 rho. `rank.pooled` 와 같은 가중(채점 표본 수)."""
        w = self.weights(T)
        num = den = 0.0
        for d, v in scores.items():
            if d in w and np.isfinite(v):
                num += float(v) * w[d]
                den += w[d]
        return num / den if den else float("nan")


class Formulation(Protocol):
    """정식화가 지켜야 할 전부."""
    name: str

    def fit(self, train: Data) -> None: ...

    def predict(self, d: str, A, M, t) -> np.ndarray:
        """높을수록 반응이 크다고 보는 점수. 눈금은 상관없다(순위만 쓴다)."""
        ...


# 마지막 load 에서 날짜 위생으로 라벨을 지운 행 수(노트 552). 가드가 조용히
# 안 도는 것을 막는다 --- 축 파일이 갈리면 마스크가 통째로 안 붙을 수 있다.
LOAD_HYGIENE: dict = {}


def load(extra: dict | None = None, quiet: set | None = None) -> Data:
    """extra 는 {축이름: {도메인: (값, 표시자)}} --- 있으면 축에 덧붙인다.

    행 순서는 domains() 와 같아야 한다(state/candidates.py 규약).
    행 수가 안 맞으면 중립으로 채우고 **경고한다**(노트 133) --- 그 조용한
    대체 때문에 넓힌 팝업에 축이 안 붙은 것을 한참 못 봤다. quiet 에 든
    도메인은 경고를 안 낸다(부르는 쪽이 뒤에 통째로 교체할 때).

    **시작일을 못 믿는 행은 여기서 라벨이 NaN 이 된다**(노트 552,
    ``lab/datehygiene``). 행을 지우지 않고 라벨만 지우므로 축 결합이
    안 깨지고, 학습과 채점이 둘 다 ``np.isfinite(y)`` 로 갈리므로 그것으로
    충분하다. 몇 행을 뺐는지는 ``LOAD_HYGIENE`` 에 남는다."""
    dom, names = domains()
    from .datehygiene import apply as _hyg
    dom, hits = _hyg(dict(dom))
    LOAD_HYGIENE.clear()
    LOAD_HYGIENE.update(hits)
    #: (노트 872) 시대 단절 조기 경보 — **라벨 층만**(행+y · A/M 은 축 구성 종속이라
    #: 여기서 대조하면 extra 실험마다 거짓 단절 — lab/eracheck 문서). print 전용이라
    #: 적합·채점에 무영향(씨앗 0 on/off 비트 동일로 실증 — out872). ERA_HOOK=0 이면 끔.
    import os as _os
    if _os.environ.get("ERA_HOOK") != "0":
        try:
            from .eracheck import compare_labels as _cl
            _cl(Data(dom, names))
        except Exception as _e:                          # 가드가 본선을 죽이면 안 된다
            print(f"era 가드 자체 오류(무시): {_e}", flush=True)
    if not extra:
        return Data(dom, names)
    dom2, nm2 = {}, {}
    for d, (A, M, y, t) in dom.items():
        cols, msk = [A], [M]
        nl = list(names.get(d) or [])
        for c, byd in extra.items():
            if d in byd and len(byd[d][0]) == len(A):
                v, o = byd[d]
                cols.append(np.asarray(v, float).reshape(-1, 1))
                msk.append(np.asarray(o, float).reshape(-1, 1))
            else:
                # **조용한 대체는 조용한 버그가 된다**(노트 133). 축이
                # 도메인에 아예 없는 것과 행 수가 안 맞는 것은 다르다 ---
                # 뒤쪽은 거의 늘 실수다. 넓힌 팝업에 축을 안 붙인 채로
                # 한참 재고 있었다.
                if d in byd and not (quiet and d in quiet):
                    _warn(f"{c}: {d} 행 수 {len(byd[d][0])} != {len(A)}"
                          f" — 중립으로 채운다")
                cols.append(np.full((len(A), 1), 0.5))
                msk.append(np.zeros((len(A), 1)))
            nl.append(c)
        dom2[d] = (np.hstack(cols), np.hstack(msk), y, t)
        nm2[d] = nl
    return Data(dom2, nm2)


# ── 채점 ───────────────────────────────────────────────────────────────
def _score_one(f: Formulation, data: Data, tgt: str, keep) -> float | None:
    A, M, y, t = data.slice(tgt, keep)
    if len(y) < 20:
        return None
    try:
        p = np.asarray(f.predict(tgt, A, M, t), float)
    except Exception:
        return None
    if p.shape[0] != len(y) or not np.isfinite(p).any():
        return None
    # **라벨도 유한해야 한다**(노트 273). 예측만 걸렀더니 게임의 결측 라벨
    # 43건(노트 210의 30일 창이 안 찬 것)이 순위에 들어가 게임 점수가
    # +0.62 대신 **+0.19** 로 나오고 있었다. 노트 271이 ``오래된 코드는
    # 이 자리에서 안 틀린다''고 적었는데 여기가 반례다 --- 네 번째다.
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 20:
        return None
    return float(spearman(p[ok], y[ok]))


def evaluate(make: Callable[[], Formulation], data: Data | None = None,
             protocol: str = "deploy", T: float = 2025.0,
             targets: list[str] | None = None) -> dict:
    """정식화 하나를 채점한다. make() 는 매번 새 인스턴스를 낸다."""
    data = data or load()
    tg = targets or list(data.dom)
    out = {}
    if protocol == "all":
        # **라벨이 없는 행은 학습에 못 넣는다**(노트 273). 노트 210이 게임
        # 라벨을 30일 창으로 바꾸면서 창이 안 찬 43건을 결측으로 뒀는데,
        # 이 갈래가 그것을 거르지 않아 ``Input y contains NaN'' 으로 죽었다.
        # ``deploy'' 갈래는 연도로 자르다가 우연히 같이 걸러서 멀쩡했다 ---
        # 그 43건이 전부 2025년 이후라서다. 우연히 안 죽은 것이지 옳았던 게
        # 아니다.
        #
        # 죽어도 실행은 이어졌고 가드 **양규약**은 ``전체 규약 없음''으로
        # 통과했다. 그래서 승격은 안 막혔지만 노트 112가 보라고 만든
        # **낙관 편의**(전체 − 배포)를 그동안 못 재고 있었다.
        keep = {d: np.isfinite(data.dom[d][2]) for d in data.dom}
        sub = {d: data.slice(d, keep[d]) for d in data.dom
               if keep[d].sum() >= MIN_TRAIN}
        if len(sub) < 3:
            return {}
        f = make()
        f.fit(Data(sub, data.names,
                   {d: data.yr[d][keep[d]] for d in sub}))
        for d in tg:
            if d not in keep:
                continue
            v = _score_one(f, data, d, keep[d])
            if v is not None:
                out[d] = v
        return out
    # 시간 분할 --- 출처는 T 이전만
    train, tmask = {}, {}
    for d in data.dom:
        # 라벨 결측을 **연도로 우연히** 거르고 있었다(노트 273 · 274). 지금은
        # 2025년 이전 결측이 0건이라 이 한 항이 아무것도 안 바꾸지만, 게임처럼
        # 창이 안 찬 라벨이 다음에 2025년 이전에 생기면 그때는 죽는다.
        k = (np.isfinite(data.yr[d]) & (data.yr[d] < T)
             & np.isfinite(data.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = data.slice(d, k)
            tmask[d] = k
    if len(train) < 3:
        return {}
    f = make()
    # yr 는 **같은 마스크**로 잘라야 한다 --- 다른 마스크로 자르면 행 수가
    # 어긋난다(오늘은 두 마스크가 같아서 안 어긋났을 뿐이다).
    f.fit(Data(train, data.names, {d: data.yr[d][tmask[d]] for d in train}))
    for d in tg:
        post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
        if post.sum() < 20:
            continue
        v = _score_one(f, data, d, post)
        if v is not None:
            out[d] = v
    return out


def headline(scores: dict) -> float:
    """대표 수치 --- 제품이 묻는 것은 팝업이다."""
    return float(scores.get(PRIMARY, np.nan))


def board(scores: dict) -> float:
    """연구 수치 --- 대상 평균."""
    v = [x for x in scores.values() if np.isfinite(x)]
    return float(np.mean(v)) if v else float("nan")


def bootstrap_ci(make: Callable[[], Formulation], data: Data | None = None,
                 target: str = PRIMARY, protocol: str = "deploy",
                 T: float = 2025.0, B: int = 60, seed: int = 20260729,
                 on_step=None) -> tuple[float, float, float]:
    """대상 하나의 점수에 붓스트랩 구간. 대상만 재표집한다."""
    data = data or load()
    rng = np.random.default_rng(seed)
    base = evaluate(make, data, protocol, T, [target]).get(target, float("nan"))
    vs = []
    A, M, y, t = data.dom[target]
    n = len(y)
    for i in range(B):
        b = rng.integers(0, n, n)
        d2 = dict(data.dom)
        d2[target] = (A[b], M[b], y[b], t[b])
        yr2 = dict(data.yr)
        yr2[target] = data.yr[target][b]
        try:
            v = evaluate(make, Data(d2, data.names, yr2), protocol, T,
                         [target]).get(target)
        except Exception:
            v = None
        if v is not None and np.isfinite(v):
            vs.append(v)
        if on_step and (i + 1) % 10 == 0:
            on_step(i + 1, float(np.mean(vs)) if vs else float("nan"))
    if len(vs) < 10:
        return base, float("nan"), float("nan")
    lo, hi = np.percentile(vs, [2.5, 97.5])
    return base, float(lo), float(hi)
