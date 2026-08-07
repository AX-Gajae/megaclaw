"""상시 가드 --- 모든 실행에 자동으로 붙는 검사.

노트 87 · 115 · 117 · 124 는 전부 **내가 낸 수치를 내가 뒤집은** 사건이었다.
공통 신호가 있었다.

    ``수치가 이상하다''가 아니라 ``수치가 너무 깔끔하다''

그때마다 사후에 손으로 확인했고, 그래서 세 번 다 논문을 내보낸 **뒤에**
잡았다. 여기서는 그 검사들을 실행 시점으로 옮긴다. 가드가 깨진 실행은
점수가 기록되되 **승격 대상에서 빠진다**(lab/loop.py::promote).

    엿보기   대상 라벨을 바꿔도 예측이 같아야 한다 (구조적 무결성)
    치환     출처 라벨을 섞으면 점수가 무너져야 한다 (라벨 누수)
    분모     대상 집합이 기준과 같아야 한다 (노트 82 · 90)
    재현     같은 입력이면 같은 점수 (또는 씨앗 넷의 폭을 기록)
    빈칸     축이 전부 상수인 레코드의 비중 (노트 124)
    양규약   배포와 전체가 둘 다 나와야 하고 낙관 편의를 기록 (노트 112)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

from . import harness as H
from .harness import PRIMARY, Data, board, evaluate

DEN = Path("data/lab/denominator.json")
PERMUTE_MAX = 0.15     # 라벨을 섞고도 이만큼 남으면 라벨 말고 딴 게 일한 것
SEEDS = [20260729, 19770101, 20250315, 20260101]


# ── 도구 ───────────────────────────────────────────────────────────────
def _split(data: Data, T: float):
    tr = {}
    for d in data.dom:
        # 라벨 결측을 **연도로 우연히** 거르고 있었다 --- 노트 273이
        # ``harness.evaluate`` 에서 고친 것과 같은 병의 세 번째 자리다
        # (``어느 행이 진짜 있는 행인가'' --- 노트 271이 셋, 273이 넷째).
        # 지금 판은 2025년 이전 결측이 0건이라 이 한 항이 아무것도 안
        # 바꾸지만, 게임처럼 창이 안 찬 라벨이 2025년 이전에 생기면 죽는다.
        # ``rank.predictions`` 가 이 함수를 쓰므로 짝 측정이 통째로 걸린다.
        k = (np.isfinite(data.yr[d]) & (data.yr[d] < T)
             & np.isfinite(data.dom[d][2]))
        if k.sum() >= H.MIN_TRAIN:      # 가드도 하네스와 같은 문턱을 쓴다
            tr[d] = (data.slice(d, k), k)
    return tr


def _fit_on(make, data: Data, T: float, ymap=None, seed=None):
    """T 이전으로 적합. ymap(d, y) 가 있으면 출처 라벨을 갈아 끼운다.

    seed 가 주어지면 **정식화 객체의 씨앗을 바꾼다**(노트 146). 예전 재현
    가드는 ``np.random.seed()'' 만 불렀는데, 이 판의 정식화는 전부
    ``np.random.default_rng(self.seed)'' 를 쓰므로 전역 씨앗이 아무것도 안
    바꿨다 --- 씨앗에 0.06 움직이는 정식화를 스무 노트 동안 ``폭 0.0000''
    으로 보고했다."""
    tr = {}
    yr = {}
    for d, (sl, k) in _split(data, T).items():
        A, M, y, t = sl
        if ymap is not None:
            y = ymap(d, y)
        tr[d] = (A, M, y, t)
        yr[d] = data.yr[d][k]
    f = make()
    if seed is not None:
        for a in ("seed", "random_state"):
            if hasattr(f, a):
                setattr(f, a, seed)
        kw = getattr(f, "kw", None)
        if isinstance(kw, dict) and "random_state" in kw:
            f.kw = {**kw, "random_state": seed}
    f.fit(Data(tr, data.names, yr))
    return f


def _predict_post(f, data: Data, tgt: str, T: float):
    post = np.isfinite(data.yr[tgt]) & (data.yr[tgt] >= T)
    if post.sum() < 20:
        return None, None
    A, M, y, t = data.slice(tgt, post)
    try:
        p = np.asarray(f.predict(tgt, A, M, t), float)
    except Exception:
        return None, None
    return p, y


def _rho(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 20:
        return float("nan")
    a, b = rankdata(p[ok]), rankdata(y[ok])
    return float(np.corrcoef(a, b)[0, 1])


# ── 가드들 ─────────────────────────────────────────────────────────────
def g_peek(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY) -> dict:
    """대상의 **후행** 라벨을 뒤섞고도 예측이 한 자리도 안 변해야 한다.

    변하면 채점할 라벨이 어떤 경로로든 적합에 들어간 것이다.

    처음엔 대상 라벨을 **통째로** 섞었다. 그러면 이력이 충분해서 학습 풀에
    정당하게 들어간 도메인은 무조건 실패한다 --- 그 도메인의 T 이전 라벨은
    써도 되는 것이다. 노트 133에서 팝업 이력을 16건에서 73건으로 넓히자마자
    이 가드가 걸렸고, 걸린 쪽이 자료가 아니라 가드였다. 섞는 것은 T 이후만."""
    f = _fit_on(make, data, T)
    p0, _ = _predict_post(f, data, tgt, T)
    if p0 is None:
        return {"name": "엿보기", "passed": True, "detail": "대상 표본 부족 — 건너뜀"}
    rng = np.random.default_rng(7)
    d2 = dict(data.dom)
    A, M, y, t = d2[tgt]
    post = np.isfinite(data.yr[tgt]) & (data.yr[tgt] >= T)
    y2 = np.array(y, copy=True)
    y2[post] = rng.permutation(y2[post])
    d2[tgt] = (A, M, y2, t)
    f2 = _fit_on(make, Data(d2, data.names, dict(data.yr)), T)
    p1, _ = _predict_post(f2, Data(d2, data.names, dict(data.yr)), tgt, T)
    if p1 is None:
        return {"name": "엿보기", "passed": False, "detail": "라벨 치환 후 예측 실패"}
    same = np.allclose(np.nan_to_num(p0, nan=-9), np.nan_to_num(p1, nan=-9),
                       atol=1e-9)
    return {"name": "엿보기", "passed": bool(same),
            "detail": "대상 라벨 치환에 예측 불변" if same else
                      f"예측이 움직임 — 최대 {np.nanmax(np.abs(p0-p1)):.3g}"}


def g_permute(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY,
              R: int = 99, budget: float = 150.0, null_make=None) -> dict:
    """출처 라벨을 도메인별로 섞고 **귀무 분포를 만든다**.

    처음엔 한 번만 섞어서 ``치환해도 +0.49 가 남는다''로 읽었는데, 그건
    귀무의 평균이 아니라 **폭**이었다. 팝업 후행 표본이 59건뿐이라 무작위
    방향도 |rho| 0.5 를 예사로 낸다. 한 번 뽑고 판정한 것 자체가 틀렸다.

    그래서 R 번 뽑아 실제값의 순위를 본다. 대표 수치는 대상 하나가 아니라
    **대상을 모은 판**(가중 평균)으로도 잰다 --- 팝업 하나로는 분해능이 없다."""
    import time as _t
    f0 = _fit_on(make, data, T)
    p0, y0 = _predict_post(f0, data, tgt, T)
    real_t = _rho(p0, y0) if p0 is not None else float("nan")
    real_b, w = _pooled(f0, data, T)
    nmk = null_make or make
    nt, nb = [], []
    t0 = _t.time()
    for s in range(R):
        # **해상도를 시간이 정한다.** 비싼 정식화는 R 을 못 채우므로 p 의
        # 최소 해상도가 1/(R+1) 로 커진다. 그 값을 detail 에 적어 둔다.
        if s >= 12 and _t.time() - t0 > budget:
            break
        rng = np.random.default_rng(1000 + s)
        try:
            f = _fit_on(nmk, data, T, ymap=lambda d, y: rng.permutation(y))
        except Exception:
            continue
        p, y = _predict_post(f, data, tgt, T)
        if p is not None:
            v = _rho(p, y)
            if np.isfinite(v):
                nt.append(v)
        b, _ = _pooled(f, data, T)
        if np.isfinite(b):
            nb.append(b)
    if len(nb) < 8:
        return {"name": "치환", "passed": True, "detail": "귀무 표본 부족 — 건너뜀",
                "z": float("nan")}
    nb = np.array(nb)
    pv = float((np.sum(np.abs(nb) >= abs(real_b)) + 1) / (len(nb) + 1))
    sd = float(nb.std())
    z = float((real_b - nb.mean()) / sd) if sd > 1e-9 else float("nan")
    d = (f"판 {real_b:+.4f} vs 귀무 {nb.mean():+.4f}±{sd:.4f} "
         f"→ z={z:+.2f} p={pv:.3f} (R={len(nb)})")
    if nt:
        nt = np.array(nt)
        d += f" · {tgt} {real_t:+.4f} vs 귀무 ±{nt.std():.3f}"
        if nt.std() > 0.15:
            d += f" — 표본 {int(w.get(tgt, 0))}건이라 분해능 없음"
    return {"name": "치환", "passed": bool(pv <= 0.05), "detail": d,
            "z": z, "p": pv, "pooled": float(real_b), "null_sd": sd}


def _pooled(f, data: Data, T: float) -> tuple:
    """대상별 rho 를 표본 수로 가중 평균. 팝업 하나보다 분해능이 크다."""
    num = den = 0.0
    w = {}
    for d in data.dom:
        p, y = _predict_post(f, data, d, T)
        if p is None:
            continue
        ok = np.isfinite(p) & np.isfinite(y)
        r = _rho(p, y)
        if not np.isfinite(r):
            continue
        n = int(ok.sum())
        w[d] = n
        num += r * n
        den += n
    return (num / den if den else float("nan")), w


def g_denominator(scores: dict) -> dict:
    """대상 집합이 기준과 같아야 비교가 성립한다(노트 82 · 90).

    처음 통과한 실행의 대상 집합을 기준으로 못 박고, 이후는 그것과 비교한다."""
    got = sorted(scores.get("deploy", {}))
    if not got:
        return {"name": "분모", "passed": False, "detail": "배포 규약 점수가 없다"}
    DEN.parent.mkdir(parents=True, exist_ok=True)
    if not DEN.exists():
        DEN.write_text(json.dumps({"targets": got}, ensure_ascii=False))
        return {"name": "분모", "passed": True,
                "detail": f"기준 확정 — {len(got)}개 {' '.join(got)}"}
    ref = json.loads(DEN.read_text())["targets"]
    miss = [t for t in ref if t not in got]
    extra = [t for t in got if t not in ref]
    ok = not miss and not extra
    d = f"기준 {len(ref)}개와 일치" if ok else \
        f"빠짐 {miss or '-'} · 추가 {extra or '-'} (기준 {len(ref)}개)"
    return {"name": "분모", "passed": bool(ok), "detail": d}


def g_repro(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY,
            budget: float = 150.0) -> dict:
    """씨앗 넷. 결정적이면 폭 0, 확률적이면 흔들림을 적는다.

    **노트 146에서 두 군데를 고쳤다.**

    ① 씨앗을 실제로 안 바꾸고 있었다. ``np.random.seed(s)'' 는 전역 legacy
    RNG 만 건드리는데 이 판의 정식화는 전부 생성자에서 받은 씨앗으로
    ``default_rng'' 를 만든다. 그래서 씨앗에 팝업 rho 가 0.060 움직이는
    F18 배깅도 ``폭 0.0000 · 결정적''으로 보고됐다. 이제 객체의 씨앗
    속성을 직접 갈아 끼운다.

    ② 판정을 **최대$-$최소에서 예측 자기상관으로** 바꿨다. 표본 k 개의
    범위는 기대값이 k 와 함께 커진다($d_2{=}1.13$, $d_4{=}2.06$) --- 예산
    안에서 두 번만 돈 비싼 정식화가 네 번 돈 싼 정식화보다 자동으로 잘
    나온다. 자기상관은 그 편향이 없고, 노트 145에서 본 대로 극값보다
    훨씬 안정적이며, 라벨을 안 본다.

    폭도 같이 적는다 --- 사람이 읽는 값이라서."""
    import time as _t
    ps, vs = [], []
    t0 = _t.time()
    for s in SEEDS:
        if len(ps) >= 2 and _t.time() - t0 > budget:
            break
        try:
            f = _fit_on(make, data, T, seed=int(s) % (2 ** 31))
            p, y = _predict_post(f, data, tgt, T)
            if p is not None and np.isfinite(p).sum() >= 20:
                ps.append(p)
                vs.append(_rho(p, y))
        except Exception:
            pass
    vs = [v for v in vs if np.isfinite(v)]
    if len(ps) < 2 or len(vs) < 2:
        return {"name": "재현", "passed": True, "detail": "표본 부족 — 건너뜀"}
    st = []
    for i in range(1, len(ps)):
        k = np.isfinite(ps[0]) & np.isfinite(ps[i])
        if k.sum() >= 20:
            v = _rho(ps[0][k], ps[i][k])
            if np.isfinite(v):
                st.append(float(v))
    if not st:
        return {"name": "재현", "passed": True, "detail": "비교 불가 — 건너뜀"}
    m = float(np.mean(st))
    sp = float(max(vs) - min(vs))
    det = m > 0.99999
    return {"name": "재현", "passed": bool(m >= 0.95), "stab": m, "span": sp,
            "detail": ("결정적" if det else f"씨앗 자기상관 {m:.3f}")
                      + f" · 씨앗 {len(vs)}개 rho 폭 {sp:.4f}"
                      f" · 평균 {np.mean(vs):+.4f}"}


def g_empty(data: Data, T: float = 2025.0, tgt: str = PRIMARY) -> dict:
    """축이 전부 관측됐는데 값이 하나로 붙어 있는 레코드(노트 124).

    태깅이 안 된 자리다. 라벨 품질이 아니라 **빈칸**을 재는 것이니, 비중이
    크면 그 실행의 점수는 실은 남은 소수만 말한다."""
    if tgt not in data.dom:
        return {"name": "빈칸", "passed": True, "detail": "대상 없음"}
    A, M, y, t = data.dom[tgt]
    post = np.isfinite(data.yr[tgt]) & (data.yr[tgt] >= T)
    A, M = A[post], M[post]
    if not len(A):
        return {"name": "빈칸", "passed": True, "detail": "대상 표본 없음"}
    deg = 0
    for i in range(len(A)):
        v = A[i][M[i] > 0]
        if len(v) >= 2 and np.nanstd(v) < 1e-9:
            deg += 1
    fr = deg / len(A)
    return {"name": "빈칸", "passed": bool(fr < 0.30),
            "detail": f"축 전부 상수 {deg}/{len(A)} = {fr:.1%}"}


def g_tie(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY) -> dict:
    """예측이 한 값에 뭉쳐 있는 레코드의 비중.

    축이 하나도 관측 안 된 레코드는 모형이 구별할 수가 없어서 전부 같은
    점수를 받는다. 그런데 스피어만은 그런 묶음이 있어도 숫자를 내놓는다 ---
    묶음만 떼어 재면 정의가 안 되는데(rho=nan) 전체로 재면 오히려 올라간다.
    팝업 표본을 넓히려다 이걸로 한 번 속았다: 축 없는 51건을 더했더니
    $+$0.3662가 $+$0.4459로 ``올랐다''. 올라간 게 아니라 잴 수 없는 것을
    센 것이었다."""
    f = _fit_on(make, data, T)
    p, y = _predict_post(f, data, tgt, T)
    if p is None:
        return {"name": "묶음", "passed": True, "detail": "대상 표본 부족 — 건너뜀"}
    ok = np.isfinite(p)
    if ok.sum() < 5:
        return {"name": "묶음", "passed": False, "detail": "유한한 예측이 거의 없다"}
    v = p[ok]
    _, cnt = np.unique(np.round(v, 10), return_counts=True)
    fr = float(cnt.max() / len(v))
    d = f"같은 값에 뭉친 최대 묶음 {int(cnt.max())}/{len(v)} = {fr:.1%}"
    if fr >= 0.15:
        d += " — 이만큼은 모형이 구별을 못 한 것이고 rho 에 섞여 있다"
    return {"name": "묶음", "passed": bool(fr < 0.15), "detail": d}


def g_flat(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY) -> dict:
    """예측이 **거의 상수**면 순위 상관은 잡음을 잰다.

    노트 131에서 한 번 속았다. 능형이 계수를 거의 0으로 수축시키면 예측이
    사실상 폴드 평균이 되고, 폴드별 예측을 모아서 스피어만을 재면 폴드 간
    평균 차이만 재게 된다 --- 원상관이 $+$0.114인 변수가 $-$0.400으로
    뒤집혀 나왔다. 묶음 가드(g\_tie)는 값이 완전히 같을 때만 잡으니
    ``조금씩만 다른'' 이 경우를 놓친다.

    그래서 예측의 퍼짐을 라벨의 퍼짐에 견준다. 예측 사분위폭이 라벨
    사분위폭의 2\%도 안 되면 그 순위는 믿을 것이 아니다."""
    f = _fit_on(make, data, T)
    p, y = _predict_post(f, data, tgt, T)
    if p is None:
        return {"name": "평탄", "passed": True, "detail": "대상 표본 부족 — 건너뜀"}
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 10:
        return {"name": "평탄", "passed": False, "detail": "유한한 예측이 거의 없다"}
    iq = lambda v: float(np.percentile(v, 75) - np.percentile(v, 25))
    pi, yi = iq(p[ok]), iq(y[ok])
    ratio = pi / yi if yi > 1e-12 else 0.0
    d = f"예측 사분위폭 / 라벨 사분위폭 = {ratio:.4f}"
    if ratio < 0.02:
        d += " — 예측이 거의 상수다. 순위가 잡음을 잰다"
    return {"name": "평탄", "passed": bool(ratio >= 0.02), "detail": d}


def g_when(data: Data) -> dict:
    """축이 **예측 시점에 알 수 있는 것**인가(노트 141).

    라벨 상관도 낮고 플랫폼도 다른데 쓰면 안 되는 축이 있다 --- 지금 긁은
    스냅샷이다. Kitsu 순위가 세계애니에서 두 기간 다 $+$0.41 이고 가드
    둘을 통과하는데, 작품이 나오기 전에는 존재하지 않는다."""
    from .provenance import audit_data
    nm = sorted({a for v in data.names.values() for a in v})
    # **이름이 붙은 것과 실제로 관측된 것은 다르다.** harness.load 가 축
    # 이름을 모든 도메인에 붙이고 없는 곳은 마스크 0 으로 둔다 --- 이름만
    # 보고 판정하면 값이 없는 도메인까지 걸린다(노트 142).
    obs = {}
    for d, names in data.names.items():
        if d not in data.dom:
            continue
        M = data.dom[d][1]
        obs[d] = [a for i, a in enumerate(list(names))
                  if i < M.shape[1] and M[:, i].mean() > 0.01]
    bad = audit_data(obs)
    if not bad:
        return {"name": "시점", "passed": True,
                "detail": f"축 {len(nm)}개 전부 사전/정적"}
    n = sum(len(v) for v in bad.values())
    first = next(iter(bad.items()))
    return {"name": "시점", "passed": False,
            "detail": f"사후 (도메인,축) {n}쌍 — {first[0]}: " +
                      " · ".join(list(first[1])[:3])}


def g_twoproto(scores: dict) -> dict:
    """배포와 전체가 둘 다 나와야 하고, 그 차이가 낙관 편의다(노트 112)."""
    dep, alz = scores.get("deploy", {}), scores.get("all", {})
    if not dep:
        return {"name": "양규약", "passed": False, "detail": "배포 규약 실패"}
    if not alz:
        return {"name": "양규약", "passed": True, "detail": "전체 규약 없음"}
    sh = [k for k in dep if k in alz]
    if not sh:
        return {"name": "양규약", "passed": True, "detail": "겹치는 대상 없음"}
    bias = float(np.mean([alz[k] - dep[k] for k in sh]))
    return {"name": "양규약", "passed": True,
            "detail": f"전체−배포 = {bias:+.4f} (대상 {len(sh)}개 평균) "
                      f"— 시간을 안 가르면 이만큼 낙관"}


def _expect_gap(r: float, n: int, reps: int = 300) -> tuple:
    """집단이 없을 때 중앙 분할이 상관을 얼마나 깎는지 --- 모의로 기준선.

    예측 중앙에서 가르면 X 분산이 반으로 줄어 상관이 **집단이 없어도** 준다.
    그 감쇠를 빼지 않으면 건강한 실행을 잡는다(챔피언 설정에서 실제로
    그랬다). 참 rho 0.5 · n 59 면 기대 차가 0.17 쯤이다."""
    rng = np.random.default_rng(int(1000 * abs(r)) + n)
    gs = []
    for _ in range(reps):
        x = rng.normal(size=n)
        y = r * x + np.sqrt(max(1e-9, 1 - r * r)) * rng.normal(size=n)
        rp = lambda a, b: float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])
        m = x <= np.median(x)
        hv = [rp(x[k], y[k]) for k in (m, ~m) if k.sum() >= 15]
        if len(hv) == 2:
            gs.append(rp(x, y) - float(np.mean(hv)))
    if len(gs) < 30:
        return float("nan"), float("nan")
    return float(np.mean(gs)), float(np.std(gs))


def g_group(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY,
            groups=None) -> dict:
    """합친 스피어만이 **집단 간 순서**를 재고 있지 않은가.

    같은 결함을 세 번 만났다. 묶음(노트 127) --- 축이 없는 레코드가 전부
    같은 점수를 받는데 스피어만은 숫자를 냈다. 폴드 평균(노트 131) --- 능형이
    수축해 예측이 폴드 평균이 되자 폴드 간 차이를 쟀다. 집단 수준(노트 136)
    --- 주장 라벨 무리가 검증 무리보다 라벨도 예측도 체계적으로 높아서,
    합친 rho +0.456 중 절반이 ``어느 무리인가''를 맞힌 것이었다.

    **집단 표지가 있으면 그것으로, 없으면 예측 중앙 분할로** 본다. 뒤쪽은
    검정력이 낮다 --- 무리 경계와 예측 중앙이 안 겹치면 못 잡는다. 그래서
    중앙 분할 쪽은 기대 감쇠를 모의로 빼고 2 표준편차를 넘을 때만 적는다."""
    f = _fit_on(make, data, T)
    p, y = _predict_post(f, data, tgt, T)
    if p is None:
        return {"name": "집단", "passed": True, "detail": "대상 표본 부족 — 건너뜀"}
    ok = np.isfinite(p) & np.isfinite(y)
    if ok.sum() < 40:
        return {"name": "집단", "passed": True, "detail": f"표본 {int(ok.sum())} — 건너뜀"}
    pv, yv = p[ok], y[ok]
    pooled = _rho(pv, yv)
    # 표지는 도메인 전체 행으로 들어오고 채점은 후행만 한다 --- 여기서 자른다
    if groups is not None:
        gv = np.asarray(groups)
        if len(gv) == len(data.dom[tgt][2]):
            post = np.isfinite(data.yr[tgt]) & (data.yr[tgt] >= T)
            gv = gv[post]
        groups = gv if len(gv) == len(p) else None
    if groups is not None:
        g = np.asarray(groups)[ok]
        pc, yc = np.array(pv, float), np.array(yv, float)
        big = [u for u in set(g.tolist()) if (g == u).sum() >= 15]
        if len(big) >= 2:
            for u in big:
                m = g == u
                pc[m] = rankdata(pv[m]) / m.sum()
                yc[m] = rankdata(yv[m]) / m.sum()
            keep = np.isin(g, big)
            within = _rho(pc[keep], yc[keep])
            gap = float(pooled - within)
            d = (f"합친 {pooled:+.3f} · 집단 안 순위로 {within:+.3f}"
                 f" · 차 {gap:+.3f} (집단 {len(big)}개)")
            if gap >= 0.15:
                d += " — 절반 가까이가 집단 간 순서다"
            return {"name": "집단", "passed": bool(gap < 0.15), "detail": d,
                    "pooled": float(pooled), "within": float(within), "gap": gap}
    med = np.median(pv)
    lo, hi = pv <= med, pv > med
    rs = [_rho(pv[m], yv[m]) for m in (lo, hi) if m.sum() >= 15]
    rs = [r for r in rs if np.isfinite(r)]
    if len(rs) < 2:
        return {"name": "집단", "passed": True, "detail": "반쪽 표본 부족 — 건너뜀"}
    within = float(np.mean(rs))
    gap = float(pooled - within)
    exp, sd = _expect_gap(float(pooled), int(ok.sum()))
    z = (gap - exp) / sd if sd and sd == sd and sd > 1e-9 else 0.0
    d = (f"합친 {pooled:+.3f} · 반쪽 안 {within:+.3f} · 차 {gap:+.3f}"
         f" (집단 없을 때 기대 {exp:.3f}±{sd:.3f} → {z:+.1f}σ)")
    if z >= 2.0:
        d += " — 집단 구조 의심"
    return {"name": "집단", "passed": bool(z < 2.0), "detail": d,
            "pooled": float(pooled), "within": within, "gap": gap, "z": float(z)}


def g_detect(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY,
             B: int = 400) -> dict:
    """이 대상에서 **얼마나 작은 차이까지 볼 수 있나**를 실행마다 적어 둔다.

    노트 135에서 일곱 편에 걸친 서술이 전부 탐지 한계 안이었다는 것을 알았다.
    팝업 후행 59건에서 짝지은 차의 반폭이 0.13이고 내가 ``내렸다''고 적은
    값들이 0.045~0.074였다. 수치를 적는 것과 그 수치로 이야기를 만드는 것은
    다르고, 후자에는 구간이 필요하다.

    그래서 판정을 하는 게 아니라 **한계를 기록한다.** 실행마다 이 줄이
    남으면 다음에 그 아래 차이를 서술하려 할 때 걸린다."""
    f = _fit_on(make, data, T)
    p, y = _predict_post(f, data, tgt, T)
    if p is None:
        return {"name": "분해능", "passed": True, "detail": "대상 표본 부족 — 건너뜀"}
    ok = np.isfinite(p) & np.isfinite(y)
    n = int(ok.sum())
    if n < 20:
        return {"name": "분해능", "passed": True, "detail": f"표본 {n} — 건너뜀"}
    pv, yv = p[ok], y[ok]
    rng = np.random.default_rng(20260730)
    vs = []
    for _ in range(B):
        i = rng.integers(0, n, n)
        a, b = rankdata(pv[i]), rankdata(yv[i])
        if a.std() > 0 and b.std() > 0:
            vs.append(float(np.corrcoef(a, b)[0, 1]))
    if len(vs) < 50:
        return {"name": "분해능", "passed": True, "detail": "붓스트랩 실패 — 건너뜀"}
    lo, hi = np.percentile(vs, [2.5, 97.5])
    hw = float((hi - lo) / 2)
    # 짝지은 차의 반폭은 단일 값 반폭보다 좁다(공통 분산이 상쇄된다).
    # 노트 135 실측: 팝업 n=59 에서 단일 0.232 · 짝지은 0.127 → 비 0.55.
    # 한 대상 한 쌍에서 잰 값이라 다른 대상에서는 다를 수 있다.
    paired = hw * 0.55
    return {"name": "분해능", "passed": True, "hw": hw, "paired": paired,
            "detail": f"{tgt} n={n} · 단일 반폭 {hw:.3f}"
                      f" · 짝지은 차 반폭 약 {paired:.3f}"
                      f" — 이보다 작은 차이는 서술하지 말 것"}


def g_attrib(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY,
             R: int = 4, seed: int = 20260730) -> dict:
    """**남의 축을 흔들면 내 예측이 얼마나 남아 있나**(노트 144 · 145).

    풀링 모형에서 도메인 X 의 자질을 바꾸면 X 와 무관한 도메인 Y 의 점수도
    움직인다. 그 자체는 정상이다 --- 풀에서 배우니까. 문제는 **크기**다.
    노트 144에서 F8 부스팅은 팝업의 입력이 한 비트도 안 바뀌었는데 다른
    도메인의 축을 하나 지우는 것만으로 팝업 예측 순위가 자기 자신과 0.895
    밖에 안 맞았다. 능형은 0.987 이다. 그 판에서 읽으려던 처치 효과는
    0.003 이었다.

    **재는 값은 rho 폭이 아니라 예측 자기상관이다**(노트 145에서 고쳤다).
    rho 폭은 n=59 에서 다섯 값의 최대-최소라 그 자체가 잡음이고, 그것으로
    깊이 1/2/4 를 견주다가 ``깊이는 무관하다''고 잘못 읽었다. 자기상관으로
    다시 재니 0.981 / 0.951 / 0.895 로 단조다. 게다가 자기상관은 라벨을
    아예 안 본다 --- 채점과 독립이라 엿보기 걱정이 없다.

    분해능 가드가 ``표본이 작아 못 보는 차이''를 적는다면 이것은 ``풀이
    흔들려 못 돌리는 차이''를 적는다. 판정이 아니라 **바닥을 기록한다** ---
    풀링 모형에서 이 값을 1로 만들 수는 없다. 만들면 풀링이 아니다."""
    rng = np.random.default_rng(seed)
    if len([d for d in data.dom if d != tgt]) == 0:
        return {"name": "귀착", "passed": True, "detail": "다른 도메인 없음 — 건너뜀"}
    try:
        p0, y0 = _predict_post(_fit_on(make, data, T), data, tgt, T)
    except Exception as e:
        return {"name": "귀착", "passed": True,
                "detail": f"적합 실패({type(e).__name__}) — 건너뜀"}
    if p0 is None:
        return {"name": "귀착", "passed": True, "detail": "대상 표본 부족 — 건너뜀"}
    ok = np.isfinite(p0) & np.isfinite(y0)
    if ok.sum() < 20:
        return {"name": "귀착", "passed": True, "detail": f"표본 {int(ok.sum())} — 건너뜀"}
    st, rh = [], [_rho(p0[ok], y0[ok])]
    for _ in range(R):
        dom = {}
        for d, (A, M, y, t) in data.dom.items():
            if d == tgt or not A.shape[1]:
                dom[d] = (A, M, y, t)
                continue
            A2, M2 = A.copy(), M.copy()
            j = rng.integers(0, A.shape[1])
            A2[:, j] = 0.5
            M2[:, j] = 0.0
            dom[d] = (A2, M2, y, t)
        d2 = Data(dom, dict(data.names), dict(data.yr))
        try:
            p, y = _predict_post(_fit_on(make, d2, T), d2, tgt, T)
        except Exception:
            continue
        if p is None:
            continue
        k = ok & np.isfinite(p)
        if k.sum() < 20:
            continue
        v = _rho(p0[k], p[k])
        if np.isfinite(v):
            st.append(float(v))
            rh.append(_rho(p[k], y[k]))
    if len(st) < 2:
        return {"name": "귀착", "passed": True, "detail": "섭동 적합 실패 — 건너뜀"}
    m = float(np.mean(st))
    return {"name": "귀착", "passed": True, "stab": m, "stabmin": float(min(st)),
            "floor": float(max(rh) - min(rh)),
            "detail": f"{tgt} — 남의 축 하나를 지우면 예측 자기상관 {m:.3f}"
                      f" (최저 {min(st):.3f}, {len(st)}회) · 그때 rho 폭"
                      f" {max(rh)-min(rh):.3f} — 이보다 작은 도메인별 차이는"
                      f" 귀착 불가"}


def g_bare(data: Data, T: float = 2025.0, tgt: str = PRIMARY) -> dict:
    """유보 레코드 중 **손 축이 하나도 없는** 것의 비중(노트 174).

    노트 173에서 학습 구간만 축을 채우고 유보를 비워 뒀더니 팝업 rho 가
    +0.275 에서 -0.018 로 무너졌다. 모형이 학습에서 손 축에 기대는 법을
    배웠는데 예측 시점에 그 축이 없었기 때문이다.

    그때 ``채움은 양쪽에 대칭이어야 한다''를 규약으로 적었는데 노트 174가
    그것을 좁혔다 --- 애니의 장소 노출은 학습 88.7\% 대 유보 19.6\% 로
    훨씬 더 비대칭인데도 빼면 판이 내려간다(F6 에서 +0.0070, t=2.0).
    유보 레코드에 다른 손 축이 두세 개씩 남아 있기 때문이다.

    **문제는 비대칭이 아니라 빈 레코드다.** 손 축이 0개인 유보 레코드는
    모형이 구별할 재료가 없다."""
    SH = ("target_breadth", "venue_prominence", "entry_friction",
          "media_push", "goods_scale")
    nm = list(data.names.get(tgt) or [])
    js = [nm.index(a) for a in SH if a in nm]
    if not js:
        return {"name": "맨몸", "passed": True, "detail": "손 축 없음 — 건너뜀"}
    post = np.isfinite(data.yr[tgt]) & (data.yr[tgt] >= T)
    if post.sum() < 20:
        return {"name": "맨몸", "passed": True, "detail": "표본 부족 — 건너뜀"}
    M = data.dom[tgt][1][post][:, js]
    k = (M > 0).sum(1)
    bare = float((k == 0).mean())
    return {"name": "맨몸", "passed": bool(bare < 0.10), "bare": bare,
            "detail": f"{tgt} 유보 {int(post.sum())}건 중 손 축 0개가 "
                      f"{bare:.1%} · 최소 {int(k.min())}축"
                      + (" — 학습에만 축이 있으면 예측이 무너진다"
                         if bare >= .10 else "")}


# ── 묶음 ───────────────────────────────────────────────────────────────
# 도메인별 집단 표지 --- 라벨 눈금이 기계적으로 갈리는 자리(노트 137)
DOMAIN_GROUP = {"웹툰": ("webtoon_records.json", "finished"),
                "모바일": ("mobile_records.json", "__free"),
                "애니": ("anime_records.json", "medium")}


def domain_groups(dom: str):
    """도메인의 집단 표지. 행 순서는 trendaxes._ids() 와 같다."""
    import json as _j
    from pathlib import Path as _P
    from . import trendaxes as _T
    spec = DOMAIN_GROUP.get(dom)
    if not spec:
        return None
    f, fld = spec
    p = _P("data/state") / f
    if not p.exists():
        return None
    j = _j.loads(p.read_text())
    ids = _T._ids().get(dom)
    if not ids:
        return None
    if fld == "__free":
        return np.array(["free" if (j.get(k) or {}).get("price") in (0, 0.0)
                         else "paid" for k in ids])
    return np.array([str((j.get(k) or {}).get(fld)) for k in ids])


def corrected_board(f, data: Data, T: float = 2025.0) -> tuple:
    """집단 간 순서를 뺀 판 rho.

    노트 137 --- 판 rho 의 4분의 1이 ``이게 연재 중인가'' ``이게 무료 앱인가''
    를 맞힌 몫이었다. 웹툰(후행 711)과 모바일(441)이 판 가중의 44\%이고 둘
    다 라벨 눈금이 집단으로 갈린다. 순위는 보정해도 거의 안 바뀌지만
    **수준은 0.07~0.11 낮다.** 그리고 축의 값어치는 보정하면 오히려 커진다
    --- 인공물이 축으로는 못 올리는 바닥이라서다."""
    num = numc = den = 0.0
    for d in data.dom:
        p, y = _predict_post(f, data, d, T)
        if p is None:
            continue
        r = _rho(p, y)
        if not np.isfinite(r):
            continue
        n = int((np.isfinite(p) & np.isfinite(y)).sum())
        num += r * n; den += n
        rc = r
        g = domain_groups(d)
        if g is not None:
            post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
            if len(g) == len(post):
                gv = g[post]
                if len(gv) == len(p):
                    big = [u for u in set(gv.tolist()) if (gv == u).sum() >= 15]
                    if len(big) >= 2:
                        pc, yc = np.array(p, float), np.array(y, float)
                        for u in big:
                            m = gv == u
                            pc[m] = rankdata(p[m]) / m.sum()
                            yc[m] = rankdata(y[m]) / m.sum()
                        k = np.isin(gv, big)
                        v = _rho(pc[k], yc[k])
                        if np.isfinite(v):
                            rc = v
        numc += rc * n
    if not den:
        return float("nan"), float("nan")
    return num / den, numc / den


def popup_groups(wide: bool = False):
    """팝업의 계수 방법 표지 --- 집단 가드가 쓴다. 없으면 None."""
    import json as _j
    from pathlib import Path as _P
    from . import trendaxes as _T
    pm = _P("data/state/popup_v2_meta.json")
    if not pm.exists():
        return None
    by = {m["id"]: m.get("counting") for m in _j.loads(pm.read_text())}
    prev = _T.WIDE
    _T.set_wide(wide)
    ids = _T._popup_ids()
    _T.set_wide(prev)
    return np.array([by.get(i) for i in ids])


def g_shade(make, data: Data, ref_data: Data | None = None,
            T: float = 2025.0, tgt: str = PRIMARY,
            floor: float = 0.10) -> dict:
    """**그늘** --- 판이 올라도 어느 도메인이 무너지면 막는다(노트 182).

    노트 182에서 시드는 축을 끄는 실험을 했더니 판이 +0.0084 올랐다.
    그런데 갈라 보니 팝업이 0.343에서 0.127로 반 토막 났다 --- 팝업은
    깃발에 한 번도 안 걸렸고, 손 축 다섯을 다 갖고 있어 **맨몸 가드도
    통과한다**. 무너진 까닭은 만화 · 세계애니가 손 축 셋씩 잃어 풀링 계수가
    얇아졌기 때문이다. 축을 끄는 것은 국소적이지 않다.

    **판이 그것을 숨긴다.** 판 rho 는 채점 표본 수로 가중한 평균이라
    유보 59건짜리 팝업이 0.22 내려가도 2,608건 분모에서 0.005 밖에 안
    움직인다. 큰 도메인이 조금 오르면 덮인다.

    ``ref_data`` 는 견줄 자료다 --- 대개 기본 축만 실은 ``load()`` 다.
    없으면 건너뛴다(가드가 참을 주장하지 않는다).
    """
    if ref_data is None:
        return {"name": "그늘", "passed": True, "detail": "견줄 자료 없음 — 건너뜀"}
    def per(dat):
        f = _fit_on(make, dat, T)
        out = {}
        for d in dat.dom:
            A, M, y, t = dat.dom[d]
            yr = dat.yr[d]
            m = np.isfinite(y) & np.isfinite(yr) & (yr >= T)
            if m.sum() < 20:
                continue
            p = f.predict(d, A[m], M[m], t[m])
            if not np.isfinite(p).all() or np.std(p) < 1e-12:
                continue
            out[d] = (float(spearmanr(p, y[m]).statistic), int(m.sum()))
        return out
    try:
        a, b = per(ref_data), per(data)
    except Exception as e:
        return {"name": "그늘", "passed": False,
                "detail": f"검사 자체가 터짐: {type(e).__name__} {e}"}
    drops = {d: round(b[d][0] - a[d][0], 4) for d in sorted(set(a) & set(b))}
    worst = min(drops, key=lambda d: drops[d]) if drops else None
    bad = worst is not None and drops[worst] < -floor
    return {"name": "그늘", "passed": not bad,
            "worst": worst, "drop": drops.get(worst),
            "drops": drops, "floor": floor,
            "detail": (f"{worst} 가 {drops[worst]:+.3f} — 문턱 {-floor}"
                       if worst else "견줄 도메인 없음")}



def g_accrual(data: Data, T: float = 2025.0, tgt: str = PRIMARY,
             yr_max: float = 0.30, ratio_min: float = 0.60,
             min_post: int = 30) -> dict:
    """**쌓임** --- 축을 채우는 원본 필드가 예측 시점 뒤에 자라나(노트 264).

    ``provenance.WHEN`` 은 축 **이름**에 뜻을 붙이는데, 손 축 다섯은 도메인마다
    다른 필드로 채워진다. 노트 262 · 263이 그 틈에서 둘을 찾았다 --- 웹툰
    ``entry_friction`` 이 ``daily_pass``(``finished`` 와 $+$0.841)였고
    ``goods_scale`` 이 ``n_episode``(연도와 $-$0.490, 유보/학습 45\%)였다.
    둘 다 가드 **시점**과 **한철**을 통과했다: 시점은 이름만 보고, 한철은
    지표만 보는데 두 축 다 덮음이 두 시기 100\% 였다.

    이 가드는 ``provenance.SOURCE`` 를 읽어 레코드에서 원본 필드를 꺼내
    **라벨을 안 보고** 둘을 잰다 --- 연도와의 순위 상관, 그리고 유보 평균 대
    학습 평균의 비. 쌓이는 양은 옛것일수록 크므로 연도와 음의 상관이 나고
    유보 평균이 작다.

    **유보 표본이 적으면 건너뛴다**(노트 263 --- 만화는 유보가 여섯 건이라
    ``학습 113 대 유보 44`` 가 여섯 건의 평균이었고, 하마터면 그 수로 축을
    막을 뻔했다).

    **관측된 행에서만 잰다**(노트 264). 첫 판에서 이것을 빼먹고 모바일
    ``media_push``(``n_shot``)를 걸었는데, 그 축은 ``n_shot`` 이 0 이면 축
    빌더가 이미 마스크 0 으로 내린다 --- 전체 행으로 재면 86\%의 0 이
    ``최근일수록 작다''는 가짜 무늬를 만든다. 마스크를 씌우고 다시 재니
    무늬가 사라졌다. 가드가 **자기가 안 보는 값으로 판정**하고 있었다."""
    import json as _json
    from pathlib import Path as _P
    from .provenance import SOURCE, RECORDS
    from .trendaxes import _ids
    try:
        ids_all = _ids()
    except Exception as e:
        return {"name": "쌓임", "passed": True, "detail": f"id 못 읽음: {e}"}
    bad, seen = [], 0
    for (dom, ax), fld in sorted(SOURCE.items(), key=lambda kv: kv[0]):
        if fld is None:
            continue
        if dom not in data.dom or dom not in RECORDS or dom not in ids_all:
            continue
        nm = list(data.names.get(dom) or [])
        if ax not in nm:
            continue
        M = data.dom[dom][1]
        if (M[:, nm.index(ax)] > 0).mean() < 0.01:
            continue                       # 이미 막힌 축은 안 본다
        p = _P("data/state") / RECORDS[dom]
        if not p.exists():
            continue
        try:
            rec = _json.loads(p.read_text())
        except Exception:
            continue
        byid = {v.get("record_id"): v for v in rec.values()}
        vals = []
        for i in ids_all[dom]:
            x = (byid.get(i) or {}).get(fld)
            if isinstance(x, bool):
                x = 1.0 if x else 0.0
            vals.append(float(x) if isinstance(x, (int, float)) else np.nan)
        v = np.asarray(vals, float)
        yr = data.yr[dom]
        if len(v) != len(yr):
            continue
        # **축이 실제로 관측된 행에서만 잰다**(노트 264 · 271).
        obs = data.rows(dom, axis=ax)
        ok = np.isfinite(v) & np.isfinite(yr) & obs
        pre, post = ok & (yr < T), ok & (yr >= T)
        if post.sum() < min_post or pre.sum() < min_post or v[ok].std() == 0:
            continue
        seen += 1
        r = spearmanr(v[ok], yr[ok]).correlation
        mp, mq = float(v[pre].mean()), float(v[post].mean())
        ratio = mq / mp if abs(mp) > 1e-9 else 1.0
        if np.isfinite(r) and r <= -yr_max and ratio < ratio_min:
            bad.append((dom, ax, fld, float(r), ratio))
    if not bad:
        return {"name": "쌓임", "passed": True,
                "detail": f"원본 필드 {seen}개 검사 · 쌓이는 무늬 없음"}
    d = " · ".join(f"{dm} {ax}({fl}) 연도 {r:+.2f} 비 {q:.0%}"
                   for dm, ax, fl, r, q in bad)
    return {"name": "쌓임", "passed": False, "detail": d + " — 예측 시점 뒤에 자란다"}



def _drop_mode(a, b, frac: float = 0.2):
    """결측 덩어리(최빈값)를 벗긴다 --- 겹말 가드용(노트 653).

    두 축이 같은 원천이면 ``zero_is_data=True`` 가 같은 행을 같은 상수로
    채운다. 백분위 변환은 동률에 같은 값을 주므로 그 덩어리가 두 축에서
    **완전히 일치**하고, 상관이 정보 겹침이 아니라 **결측 무늬**를 잰다.

    최빈값이 행의 ``frac`` 을 넘는 축이 하나라도 있으면 두 축에서 그 값을
    가진 행을 모두 뺀다. 남은 행이 50 미만이면 ``(None, None)``.
    """
    import numpy as _np
    u1, c1 = _np.unique(a, return_counts=True)
    u2, c2 = _np.unique(b, return_counts=True)
    if c1.max() / len(a) <= frac and c2.max() / len(b) <= frac:
        return a, b
    k = (a != u1[c1.argmax()]) & (b != u2[c2.argmax()])
    if k.sum() < 50:
        return None, None
    return a[k], b[k]

def g_dup(data: Data, T: float = 2025.0, tgt: str = PRIMARY,
          thr: float = 0.95) -> dict:
    """**겹말** --- 새 축이 이미 있는 축의 다시 쓰기인가(노트 240 · **653**).

    **노트 653 이 이 가드를 고쳤다.** 결측을 상수로 채운 덩어리가 두 축에서
    같은 행에 놓이면 백분위 변환이 그것을 똑같이 매핑해서, **정보가 겹치지
    않아도** rho 가 1 에 붙는다. 최빈값 덩어리를 벗기고 재도록 바꿨다.

    노트 239가 웹툰 레코드에서 ``태그 수''를 찾아 판을 $+$0.0038 올렸고,
    노트 240이 그것을 세 도메인으로 넓혀 $+$0.0105($t{=}3.07$)를 얻었다.
    그런데 ``target\\_breadth'' 가 **바로 그 태그 수**다 ---
    ``webtoon\\_axes.py'' 는 ``scale01(n\\_tag, 3, 14)'', 세계애니 · 만화는
    ``scale01(n\\_tag, 3, 30)'' 이고, 관측 행 안에서 순위 상관이 웹툰
    $+$0.985 · 세계애니 · 만화 $+$1.000 이다.

    **있는 열을 그대로 복사해도 이득이 똑같이 나온다**($+$0.0100 대
    $+$0.0106). 새 정보가 0 인 열이 같은 값을 낸다 --- 이득은 자료가 아니다.

    무엇이냐는 노트 241이 갈랐다. **벌점이 아니라 도메인별 기울기다.**
    복사본에 이름을 \\emph{하나만} 주고 전 도메인이 나눠 쓰게 하면 벌점은
    똑같이 반이 되는데 판이 꿈쩍도 안 한다($+$0.0005, $t{=}1.02$).
    도메인마다 제 이름을 줄 때만 이득이 난다($+$0.0102). 그리고 그 쌍을
    안쪽에서 고르면 판이 오히려 내려간다($-$0.0070) --- 그래서 노트 241은
    이 이득을 **거부**했다.

    그래서 이 가드는 **거부권이 아니라 이름표**다. 겹치는 축을 막지 않고,
    ``이것은 새 자료가 아니다''라고 적어 둔다. 이득이 났을 때 자료인지
    기울기 자유인지 가르는 법은 싸다 --- 같은 열에 **이름을 하나만 주고**
    다시 재면 된다. 사라지면 기울기였다(노트 241).

    라벨을 안 본다 --- 축들끼리의 순위 상관만 본다."""
    hits = []
    for d in sorted(data.dom):
        nm = list(data.names.get(d) or [])
        A, M, y, _ = data.dom[d]
        yr = data.yr[d]
        tr = np.isfinite(yr) & (yr < T)
        if tr.sum() < 50 or len(nm) < 2:
            continue
        for i in range(len(nm)):
            for k in range(i + 1, len(nm)):
                o = tr & (M[:, i] > 0) & (M[:, k] > 0)
                if o.sum() < 50:
                    continue
                a, b = A[o, i], A[o, k]
                if a.min() == a.max() or b.min() == b.max():
                    continue
                # **결측 덩어리를 벗기고 잰다**(노트 653). 두 축이 같은
                # 원천이면 `zero_is_data=True` 가 같은 행을 같은 상수로
                # 채우고, 백분위 변환이 그 동률 덩어리를 **똑같이** 매핑한다.
                # 그러면 정보가 겹치지 않아도 rho 가 1 에 붙는다 ---
                # `trend_level`~`trend_volatility` 가 만화에서 +0.998 이었는데
                # 덩어리(행의 93.7%)를 빼면 **−0.654** 로 부호가 뒤집힌다.
                # 옛 가드는 후보를 하나 냈고 고친 가드는 **0** 이다.
                a, b = _drop_mode(a, b)
                if a is None or len(np.unique(a)) < 3 or len(np.unique(b)) < 3:
                    continue
                r = spearmanr(a, b).correlation
                if np.isfinite(r) and abs(r) >= thr:
                    hits.append((abs(r), d, nm[i], nm[k]))
    hits.sort(reverse=True)
    d_ = (f"겹치는 축 쌍 {len(hits)}개 · 최대 "
          f"|rho|={hits[0][0]:.3f} ({hits[0][1]} {hits[0][2]}~{hits[0][3]})"
          if hits else "겹치는 축 쌍 없음")
    return {"name": "겹말", "passed": True, "dups": len(hits), "detail": d_
            + (" — 새 자료가 아니라 축별 가중 변경이다" if hits else "")}


def g_season(data: Data, T: float = 2025.0, tgt: str = PRIMARY,
             gap: float = 0.50) -> dict:
    """**한철** --- 지표가 유보에서 상수인데 학습에서만 변하는 열(노트 214).

    설계행렬은 축마다 값과 **관측 지표**를 나란히 싣는다
    (``forms._design`` 의 ``ok.astype(float)``). 지표가 유보에서 전부 1
    이고 학습에서만 0/1 을 오가면 그 열은 유보 순위를 못 매긴다 --- 대신
    **학습을 배포 시대와 그 이전으로 갈라 주는 스위치**로만 쓰인다.
    분할이 시간으로 정의되므로 그것은 분할 변수 자체다.

    노트 213이 공휴일 목록 밖을 결측으로 돌렸을 때 정확히 이것이 생겼다.
    목록이 2023년부터였고 유보가 2025년부터라 ``cal_holiday_gap`` 의 지표가
    **유보 100\% · 학습 14$\sim$41\%** 였다. 그 열 하나로 배깅 트리가
    $+$0.0158 을 얻었고, 목록을 2015년까지 채워 벌어짐을 지우니
    $+$0.4603 이 $+$0.4396 으로 내려앉았다($t{=}-4.74$). **점수가 아니라
    자료가 옳아진 것이다.**

    라벨을 안 본다 --- 날짜와 결측 무늬만 본다. 그래서 값싸고, 거부권으로
    쓰기에 안전하다."""
    bad, dead = [], []
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        yr = data.yr[d]
        h = np.isfinite(yr) & (yr >= T)
        tr = np.isfinite(yr) & (yr < T)
        if h.sum() < 20 or tr.sum() < 20:
            continue
        for j, nm in enumerate(data.names.get(d) or []):
            if j >= M.shape[1]:
                break
            oh = (M[h, j] > 0).astype(float)
            ot = (M[tr, j] > 0).astype(float)
            if oh.std() > 1e-9:
                continue          # 유보에서도 변하면 진짜 자질이다
            if ot.std() < 1e-9:
                continue          # 양쪽 다 상수면 그냥 빈 열(빈칸 가드 몫)
            if abs(float(oh.mean()) - float(ot.mean())) >= gap:
                bad.append((d, nm, round(float(oh.mean()), 2),
                            round(float(ot.mean()), 2)))
    # 값 쪽 --- 관측 행 안에서 유보 분산이 0 이면 그 열도 유보 순위를 못
    # 매긴다. 훑어 보니 129열 중 하나뿐이다(아이돌 ``cal_weekend'' ---
    # 유보 25건이 전부 같은 요일 구분이다). **지표 쪽이 진짜 문제였고 값
    # 쪽은 드물다** --- 그래도 같은 논리라 같은 가드에 둔다.
    for d in sorted(data.dom):
        A, M, y, t = data.dom[d]
        yr = data.yr[d]
        h = np.isfinite(yr) & (yr >= T)
        tr = np.isfinite(yr) & (yr < T)
        if h.sum() < 20 or tr.sum() < 20:
            continue
        for j, nm in enumerate(data.names.get(d) or []):
            if j >= M.shape[1]:
                break
            vh, vt = A[h, j][M[h, j] > 0], A[tr, j][M[tr, j] > 0]
            # **유보 50건 아래는 안 본다.** 아이돌은 유보가 25건이라
            # 이진 자질이 우연히 상수가 되는 것이 흔하다 --- 그건 구조가
            # 아니라 표본 사고다. 지표 쪽 벌어짐은 목록 경계와 분할 경계가
            # 어긋나서 생기므로 표본이 커져도 남지만, 값 쪽 상수는 안 남는다.
            if len(vh) < 50 or len(vt) < 10:
                continue
            if float(np.std(vh)) < 1e-9 and float(np.std(vt)) > 0.05:
                dead.append((d, nm))
    if not bad and not dead:
        return {"name": "한철", "passed": True,
                "detail": f"유보-학습 관측 벌어짐 {gap:.2f} 넘는 열 없음 · 유보 죽은 값 없음"}
    bits = []
    if bad:
        bits.append("학습에서만 변하는 지표 %d개 — %s" % (
            len(bad), "; ".join(f"{d}·{nm} 유보{a:.2f}/학습{b:.2f}"
                                for d, nm, a, b in bad[:4])))
    if dead:
        bits.append("유보에서 값이 상수인 열 %d개 — %s" % (
            len(dead), "; ".join(f"{d}·{nm}" for d, nm in dead[:4])))
    return {"name": "한철", "passed": False, "detail": " / ".join(bits)}



def g_alive(make, data: Data, T: float = 2025.0, tgt: str = PRIMARY,
            floor: float = 0.8) -> dict:
    """**살아있음** --- 판정치가 몇 도메인에서 나왔나(노트 231).

    ``rank.pooled`` 은 유한 표본이 20 미만이거나 예측 분산이 0 인 도메인을
    조용히 버린다. **그래서 여덟 도메인에서 죽은 정식화도 숫자를 받는다.**
    F1 프로크루스테스가 아홉 중 여덟에서 예측이 통째로 NaN 인데 $+$0.1472
    를 보고했고 그것은 펀딩 80건 하나만의 값이었다 --- 노트 5$\sim$124 의
    옛 파이프라인이자 포트폴리오의 기준선이 오래전부터 죽어 있었다.

    분모 가드가 대상 수를 보지만 그것은 \emph{점수가 있는} 대상을 센다 ---
    죽은 도메인은 애초에 점수가 안 만들어져 분모에서 빠진다. **여기서는
    자료에 있는 도메인 수를 분모로 놓는다.**"""
    from .rank import predictions, coverage
    try:
        # **T 를 넘긴다**(노트 671). 안 넘기면 `predictions` 가 기본 2025 로
        # 유보를 잘라, T=2026 으로 부른 가드가 2025 유보의 덮음을 본다 ---
        # 노트 668 이 `board()` 에서 잡은 것과 같은 종류다.
        pr = predictions(make, data, T=T)
    except Exception as e:
        return {"name": "살아있음", "passed": False,
                "detail": f"예측 자체가 터짐: {type(e).__name__} {e}"}
    cov = coverage(pr)
    able = sum(1 for d in data.dom
               if np.isfinite(data.dom[d][2]).sum() >= 20)
    if able == 0:
        return {"name": "살아있음", "passed": True, "detail": "잴 도메인 없음"}
    frac = cov["도메인"] / able
    if frac >= floor:
        return {"name": "살아있음", "passed": True,
                "detail": f"{cov['도메인']}/{able} 도메인 · 표본 {cov['표본']}"}
    return {"name": "살아있음", "passed": False,
            "detail": f"{cov['도메인']}/{able} 도메인에서만 점수가 난다 "
                      f"(표본 {cov['표본']}) — 죽은 곳: "
                      + " · ".join(cov["죽은"][:5])}


def g_source(data: Data, T: float = 2025.0, tgt: str = PRIMARY,
             rho_max: float = 0.25, min_post: int = 30,
             min_block: int = 3) -> dict:
    """**출처** --- 한 도메인에 자료원이 둘 섞였나(노트 288).

    ``forms._design`` 은 축마다 **(값, 관측 표시자)** 쌍을 낸다. 표시자는
    ``모르는 자리''를 알리라고 넣은 것인데, 한 도메인에 **출처가 둘** 섞이고
    출처마다 채워지는 축이 다르면 표시자 무늬가 곧 출처 표지가 되고 출처가
    라벨을 가른다.

    실제로 그랬다. 넓힌 팝업 판(``wide*``)은 189행 중 107행이 시장 레코드
    (``MKT-*``)인데 손 축 다섯의 마스크가 **내부 98.8\% 대 시장 0.0\%** 다.
    라벨은 시장이 2.05배 높고 **유보에서 표시자 하나로 |rho|=0.4157** ---
    같은 판의 실제 팝업 점수 0.3582 **보다 크다.** 표지 하나가 모형을 이긴다.

    **정보가 있는 결측과 구별해야 한다.** 게임의 ``media\_push`` 도 표시자가
    라벨과 $+$0.405 인데, 그건 ``자료가 있느냐''가 실제로 크기를 말하는 것이고
    예측 시점에 아는 정보라 정당하다. 가르는 표지는 **뭉치가 계열을
    가로지르나** 다 --- 넓힌 팝업은 한 뭉치가 공유 축 다섯과 검색을 함께
    묶고(계열 둘 이상), 게임은 검색끼리 · 위키끼리 따로 묶인다(계열 하나).
    한 자료원 안의 동시 결측은 정상이고, 계열을 가로지르는 동시 결측은
    **행의 출처가 다르다**는 뜻이다.

    한철(``g_season``)과 무늬가 정반대다 --- 한철은 지표가 **유보에서 상수**
    일 때(스위치)를 잡고 이것은 유보에서 **변하면서 라벨을 예측할** 때를 잡는다.

    라벨을 본다 --- **거부권으로만** 쓴다(노트 183).
    """
    from .forms import _family
    bad = []
    for d in sorted(data.dom):
        A, M, y, _t = data.dom[d]
        yr = data.yr.get(d)
        if yr is None:
            continue
        post = np.isfinite(yr) & (yr >= T) & np.isfinite(y)
        if post.sum() < min_post:
            continue
        nm = list(data.names.get(d) or [])
        I = (M[post] > 0).astype(float)
        var = [j for j in range(min(I.shape[1], len(nm)))
               if len(np.unique(I[:, j])) > 1
               and 0.05 <= I[:, j].mean() <= 0.95]
        if len(var) < min_block:
            continue
        C = np.corrcoef(I[:, var].T)
        seen, blocks = set(), []
        for a in range(len(var)):
            if a in seen:
                continue
            g = [a] + [b for b in range(a + 1, len(var))
                       if b not in seen and abs(C[a, b]) >= 0.95]
            seen.update(g)
            if len(g) >= min_block:
                blocks.append(g)
        for g in blocks:
            names = [nm[var[i]] for i in g]
            fams = {_family(x) for x in names}
            if len(fams) < 2:
                continue                       # 한 자료원 안의 동시 결측 --- 정상
            r = spearmanr(I[:, var[g[0]]], y[post]).correlation
            if r == r and abs(r) >= rho_max:
                bad.append((d, len(names), sorted(fams), float(r), names[:4]))
    bad.sort(key=lambda x: -abs(x[3]))
    if not bad:
        return {"name": "출처", "passed": True,
                "detail": "계열을 가로지르는 동시 결측 뭉치가 라벨을 예측하지 않는다"}
    return {"name": "출처", "passed": False,
            "detail": ("자료원이 섞인 것 같다 — "
                       + " · ".join(f"{d} 축 {n}개가 계열 {'/'.join(f)} 를 "
                                    f"가로질러 함께 결측, rho={r:+.3f}"
                                    for d, n, f, r, _ in bad[:2]))}


def quick(scores: dict, data: Data | None = None, T: float = 2025.0) -> str:
    """**손으로 돌리는 대본에서 부르는 한 줄짜리 가드**(노트 598).

    ``g_denominator`` 는 노트 82 · 90 이 ``분모가 조용히 바뀌면 비교가
    성립하지 않는다``로 세운 가드인데, **포트폴리오 루프에서만** 불렸다.
    그래서 손으로 돌린 실험 수백 번 동안 한 번도 안 울렸고, 그 사이
    기준 목록이 **만화 하나만큼 낡아 있었다**(유보 258행 = 분모의 7.7%).

    **가드는 불려야 가드다.** 이 함수는 적합 없이 도는 것만 골라 부르므로
    실험 대본 첫머리에 한 줄로 넣을 수 있다::

        print(guards.quick({"deploy": sc}, data))

    ``scores`` 는 ``{"deploy": {도메인: rho}}`` 꼴이다 --- 평범한 사전을
    넘기면 ``배포 규약 점수가 없다``로 떨어진다(내가 노트 597 에서 그랬다).
    """
    out = [g_denominator(scores), g_twoproto(scores)]
    if data is not None:
        out += [g_empty(data, T), g_when(data), g_bare(data, T),
                g_season(data, T), g_dup(data, T), g_accrual(data, T),
                g_source(data, T)]
    bad = [g for g in out if not g["passed"]]
    ln = ["  가드(적합 없이) %d/%d 통과" % (len(out) - len(bad), len(out))]
    for g in bad:
        ln.append("    **%s 실패** — %s" % (g["name"], str(g["detail"])[:120]))
    if not bad:
        ln.append("    전부 통과")
    return "\n".join(ln)


def check_all(make, data: Data, scores: dict, T: float = 2025.0,
              tgt: str = PRIMARY, heavy: bool = True, null_make=None,
              groups=None, ref_data: Data | None = None) -> list[dict]:
    out = [g_denominator(scores), g_twoproto(scores), g_empty(data, T, tgt),
           g_when(data), g_bare(data, T, tgt),
           g_season(data, T, tgt), g_alive(make, data, T, tgt),
           g_dup(data, T, tgt), g_accrual(data, T, tgt),
           g_source(data, T, tgt)]
    if ref_data is not None:
        try:
            out.append(g_shade(make, data, ref_data, T, tgt))
        except Exception as e:
            out.append({"name": "그늘", "passed": False,
                        "detail": f"검사 자체가 터짐: {type(e).__name__} {e}"})
    if heavy:
        for fn in (g_peek, g_permute, g_repro, g_tie, g_flat, g_detect,
                   g_group, g_attrib):
            try:
                if fn is g_permute:
                    out.append(fn(make, data, T, tgt, null_make=null_make))
                elif fn is g_group:
                    out.append(fn(make, data, T, tgt, groups=groups))
                else:
                    out.append(fn(make, data, T, tgt))
            except Exception as e:
                out.append({"name": fn.__name__[2:], "passed": False,
                            "detail": f"검사 자체가 터짐: {type(e).__name__} {e}"})
    return out
