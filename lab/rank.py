"""순위표를 **부분 순서**로 읽는다(노트 147).

노트 146이 순위표에 씨앗 띠를 얹고 ``위 여섯은 순위가 없다''고 적었다.
그 잣대가 틀렸다. 두 정식화를 견줄 때 표본 잡음은 **같은 레코드**에 걸리므로
대부분 상쇄된다. 그래서 순위를 가르는 데 드는 값은 주변 sd 가 아니라
**짝 sd** 이고, 그것은 두 정식화가 얼마나 닮았느냐에 따라 열네 배까지
차이 난다.

    주변 sd      어느 정식화든 0.018 언저리
    짝 sd        F6 대 F9 는 0.0010, F8 대 F10 은 0.0144

그러니 판 하나에 ``탐지 한계'' 숫자 하나를 붙이는 것은 두 방향으로 틀린다
--- 닮은 짝에는 너무 엄하고 안 닮은 짝에는 너무 무르다. 한계는 **행렬**이다.

쓰는 법::

    from lab import rank
    r = rank.resolve({"F8": pr8, "F18": pr18, ...})
    print(r["order"])      # 부분 순서
    print(r["pairs"])      # 짝마다 격차 · 짝 sd · t
"""
from __future__ import annotations

import numpy as np
from scipy.stats import rankdata, spearmanr

from .guards import _fit_on, _predict_post


def predictions(make, data, T: float = 2025.0, seeds=(0, 1, 2)) -> dict:
    """씨앗을 갈아 끼워 적합하고 **예측 순위를 평균한다**.

    씨앗은 성가신 모수다 --- 판정치에 남겨 둘 이유가 없다. 노트 146에서
    F18 이 씨앗에 팝업 rho 0.059 움직이는 것을 봤다. 점수를 평균하는 것보다
    예측을 평균하는 편이 낫다(그쪽이 분산을 실제로 줄인다)."""
    per = []
    for s in seeds:
        def m(s=s):
            f = make()
            for a in ("seed", "random_state"):
                if hasattr(f, a):
                    setattr(f, a, s)
            kw = getattr(f, "kw", None)
            if isinstance(kw, dict) and "random_state" in kw:
                f.kw = {**kw, "random_state": s}
            return f
        f = _fit_on(m, data, T)
        o = {}
        for d in sorted(data.dom):
            p, y = _predict_post(f, data, d, T)
            if p is not None:
                o[d] = (p, y)
        per.append(o)
    keys = set(per[0])
    for o in per[1:]:
        keys &= set(o)
    return {d: (np.mean([_rank_nan(o[d][0]) for o in per], axis=0),
                per[0][d][1]) for d in sorted(keys)}


def _rank_nan(p):
    """유한한 것만 순위 매기고 나머지는 NaN 으로 둔다(노트 232).

    옛 판은 ``rankdata(p)`` 였는데 **scipy 의 기본 정책이 NaN 전파**라
    한 행이 NaN 이면 벡터 전체가 NaN 이 된다. 그래서 못 매기는 행을
    정직하게 NaN 으로 돌려주는 정식화가 \emph{도메인 전체}를 잃었다 ---
    F1 프로크루스테스는 웹툰 711건 중 7건을 못 매겨서 711건을 다 잃었고,
    아홉 도메인 중 여덟이 그렇게 사라졌다(노트 231).

    부분 결측은 부분으로 남겨야 한다. 그래야 ``coverage`` 가 무엇이
    빠졌는지 적을 수 있다."""
    p = np.asarray(p, float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    if ok.sum():
        out[ok] = rankdata(p[ok]) / ok.sum()
    return out


def pooled(pr: dict, boot: dict | None = None) -> float:
    """대상별 스피어만을 채점 표본 수로 가중 평균 --- 이 판의 판정치."""
    num = den = 0.0
    for d, (p, y) in pr.items():
        if boot is not None:
            i = boot[d]
            p, y = p[i], y[i]
        ok = np.isfinite(p) & np.isfinite(y)
        if ok.sum() < 20:
            continue
        a, b = rankdata(p[ok]), rankdata(y[ok])
        if a.std() < 1e-12 or b.std() < 1e-12:
            continue
        num += float(np.corrcoef(a, b)[0, 1]) * ok.sum()
        den += ok.sum()
    return num / den if den else float("nan")


def resolve(preds: dict, B: int = 400, seed: int = 7, k: float = 2.0,
            seed_pooled: dict | None = None, k_seeds: int = 3) -> dict:
    """{이름: 예측} → 부분 순서.

    같은 재추출을 모든 정식화에 쓴다 --- 그래야 짝 차이에서 표본 잡음이
    상쇄된다. ``갈린다''는 격차가 짝 sd 의 k 배를 넘는 것으로 본다.

    seed_pooled 로 {이름: [씨앗별 판 rho]} 를 주면 **잔여 씨앗 분산을 더한다.**
    예측을 k_seeds 개 씨앗으로 평균해도 씨앗 분산이 0 이 되지는 않고 √k 로
    줄 뿐이다. 노트 147에서 F18 대 F8 이 그 항 때문에 갈렸다 안 갈렸다 한다
    --- 표본 짝 sd 0.0036 에 씨앗 항 0.0050 을 더해야 t 가 1.4 에서 0.8 로
    내려간다."""
    names = list(preds)
    if len(names) < 2:
        return {"point": {n: pooled(preds[n]) for n in names},
                "pairs": {}, "order": [names]}
    common = set(preds[names[0]])
    for n in names[1:]:
        common &= set(preds[n])
    pr = {n: {d: preds[n][d] for d in sorted(common)} for n in names}
    rng = np.random.default_rng(seed)
    sz = {d: len(pr[names[0]][d][1]) for d in common}
    boots = [{d: rng.integers(0, sz[d], sz[d]) for d in sz} for _ in range(B)]
    draws = {n: np.array([pooled(pr[n], bt) for bt in boots]) for n in names}
    point = {n: pooled(pr[n]) for n in names}
    order = sorted(names, key=lambda n: -point[n])
    pairs, beats = {}, {}
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            d = draws[a] - draws[b]
            sd = float(d.std(ddof=1))
            if seed_pooled and a in seed_pooled and b in seed_pooled:
                va = np.asarray(seed_pooled[a], float)
                vb = np.asarray(seed_pooled[b], float)
                if len(va) == len(vb) and len(va) > 1:
                    ss = float(np.std(va - vb, ddof=1)) / np.sqrt(k_seeds)
                    sd = float(np.hypot(sd, ss))
            gap = point[a] - point[b]
            t = gap / sd if sd > 0 else float("inf")
            pairs[f"{a}>{b}"] = {"gap": gap, "sd": sd, "t": t,
                                 "split": bool(abs(gap) > k * sd)}
            if abs(gap) > k * sd:
                beats.setdefault(a, set()).add(b)
    # 부분 순서 --- 서로 안 갈리는 것끼리 한 칸에 묶는다
    tiers, rest = [], list(order)
    while rest:
        cur = [rest[0]]
        for n in rest[1:]:
            if all(not pairs.get(f"{m}>{n}", pairs.get(f"{n}>{m}", {}))
                   .get("split", False) for m in cur):
                cur.append(n)
            else:
                break
        tiers.append(cur)
        rest = rest[len(cur):]
    return {"point": point, "pairs": pairs, "order": tiers,
            "marg_sd": {n: float(draws[n].std(ddof=1)) for n in names}}


def text(r: dict) -> str:
    """사람이 읽는 한 덩어리."""
    out = []
    for i, tier in enumerate(r["order"], 1):
        out.append(f"{i}칸  " + " ≈ ".join(
            f"{n} {r['point'][n]:+.4f}" for n in tier))
    for k, v in r["pairs"].items():
        if v["split"]:
            out.append(f"  {k}  {v['gap']:+.4f} ± {v['sd']:.4f}  t={v['t']:.1f}")
    return "\n".join(out)

# 라벨의 성질(노트 224). **판 rho 는 두 과제의 가중 평균이다.**
# 선호형은 ``얼마나 좋아하나''(즐겨찾기 · popularity)이고 양형은 ``얼마나
# 닿았나''(리뷰 수 · 평점 수 · 방문자 · 후원자 · 초동)다. 평가 점수 축이
# 선호형 셋에서 +0.36~+0.51 이고 양형 둘에서 -0.04~+0.06 으로 겹침 없이
# 갈린다 --- 같은 축이 한쪽만 맞힌다. 선호형이 몫 39.4% 에 가중 rho
# 0.4132, 양형이 60.6% 에 0.4883 으로 **선호형이 0.075 더 어렵다.**
KIND = {"웹툰": "선호", "세계애니": "선호", "만화": "선호",
        "애니": "양", "모바일": "양", "게임": "양", "도서": "양",
        "펀딩": "양", "팝업": "양", "아이돌": "양"}


def by_kind(pr: dict, boot: dict | None = None) -> dict:
    """판을 라벨 성질로 갈라 적는다 --- **순위에 안 쓴다.**

    노트 211이 도메인별 달력 몫을 판 옆에 적자고 하고 안 했다. 이번에는
    판정치를 바꾸는 것이 아니라 **둘로 적는** 것이라 순위 규칙을 안
    건드린다 --- 어느 쪽이 나아졌는지 보려면 이것이 있어야 한다."""
    out = {}
    for k in ("선호", "양"):
        sub = {d: v for d, v in pr.items() if KIND.get(d) == k}
        if not sub:
            continue
        b = {d: boot[d] for d in sub} if boot is not None else None
        n = sum(int(np.isfinite(v[1]).sum()) for v in sub.values())
        out[k] = {"rho": round(float(pooled(sub, b)), 4), "n": n,
                  "도메인": sorted(sub)}
    tot = sum(v["n"] for v in out.values()) or 1
    for k in out:
        out[k]["몫"] = round(out[k]["n"] / tot, 4)
    return out

def clock(pr: dict, data, T: float = 2025.0) -> dict:
    """**얼마가 시계인가** --- 도메인마다 ``-시작일'' 하나와 견준다(노트 270).

    라벨이 출시 시점부터 쌓이면 ``언제 나왔나''가 곧 라벨이 된다(노트 209).
    노트 269가 도서에서 그 극단을 봤다 --- 유보 163건 **안에서만** 반년
    코호트별 sales point 중앙값이 39,209에서 4,485로 **8.7배** 떨어진다.

    쓸 만한 눈금은 라벨의 쇠퇴 자체가 아니라 **달력 대 모형의 비**다. 게임은
    쇠퇴비가 34.5 로 제일 큰데 날짜 상관은 0.182 뿐이다(고정 창 라벨이라
    순위가 날짜에 안 붙는다). 반대로 도서는 쇠퇴비 10.5 에 날짜 상관 0.562 로
    **달력이 모형을 이긴다.**

        도서 1.61 · 웹툰 0.79 · 모바일 0.38 · 게임 0.29 · 애니 0.27 ·
        세계애니 0.19

    1 을 넘으면 그 도메인 점수는 능력이 아니라 시계다. 라벨을 안 고치면
    못 낫는다(노트 269 --- 고정 창은 새 수집이고 코호트 재정의는 과제 변경).
    **순위에 안 쓴다. 도메인 수를 읽는 눈금이다.**"""
    out = {}
    for d, (p, y) in pr.items():
        yr = data.yr.get(d)
        if yr is None:
            continue
        # ``predictions`` 는 **유보 행 전부**를 돌려준다(라벨이 NaN 인 것 포함).
        # 게임은 30일 창이 안 찬 43건이 NaN 이라 길이가 안 맞았다(노트 270).
        # ``Data.rows`` 로 이름 붙여 묻는다(노트 271).
        post = data.rows(d, post=True, T=T)
        if post.sum() != len(p) or post.sum() < 40:
            continue
        m = np.isfinite(p) & np.isfinite(y)
        if m.sum() < 40:
            continue
        mod = float(spearmanr(p[m], y[m]).correlation)
        cal = float(spearmanr(-yr[post][m], y[m]).correlation)
        if not (np.isfinite(mod) and np.isfinite(cal)) or abs(mod) < 1e-9:
            continue
        out[d] = {"모형": round(mod, 4), "달력": round(cal, 4),
                  "시계몫": round(cal / mod, 2)}
    worst = max(out, key=lambda k: out[k]["시계몫"]) if out else None
    return {"도메인별": out, "제일 큰": worst,
            "제일 큰 값": out[worst]["시계몫"] if worst else None,
            "1 넘는 곳": sorted(k for k, v in out.items() if v["시계몫"] > 1.0)}


def _norm_ppf(q: float) -> float:
    """표준정규 분위 --- 본페로니 문턱용(노트 282)."""
    from scipy.stats import norm
    return float(norm.ppf(q))


def spread(a: dict, b: dict, B: int = 800, seed: int = 0,
           t_min: float | None = None) -> dict:
    """**판이 0 인데 아무 일도 안 난 건가**(노트 247 · 248).

    판 rho 는 도메인 rho 의 가중 평균이라 **자리바꿈에 눈이 없다.** 웹툰이
    얻은 것을 게임이 내놓으면 ``아무 변화 없음''으로 보고한다.

    **도메인 차는 반드시 짝 SE 와 함께 읽는다**(노트 248). 도메인별 rho 의
    SE 가 웹툰 0.034(711건)에서 아이돌 0.207(25건)까지 **여섯 배** 벌어져
    있어서, 큰 수가 곧 큰 효과가 아니다. 노트 247이 아이돌 $+$0.131 을
    제일 큰 움직임으로 보고했는데 짝 SE 가 0.212 라 $t{=}0.62$ --- 잡음이다.
    (짝 SE 가 주변 SE 보다 **큰** 유일한 도메인이기도 하다. 두 예측이 거의
    무상관이라는 뜻이다.)

    잡음을 걷어내면 상쇄가 오히려 **더 뚜렷하다** --- 노트 247의 실험에서
    $|t| \\ge 2$ 인 둘(웹툰 $+$0.024 · 게임 $-$0.084)만 남기면 총량 0.0136에
    순 $-$0.0007, 4배가 아니라 **19배**다.

    ``순''은 판 차, ``총량''은 부호를 지운 것, ``진짜 총량''은 $|t| \\ge$
    ``t_min`` 인 도메인만 더한 것이다. 진짜 총량이 순의 세 배를 넘으면
    효과가 없는 게 아니라 **상쇄**이고, 판정은 못 하더라도(노트 245) 보고는
    해야 한다."""
    rng = np.random.default_rng(seed)
    ks = sorted(set(a) & set(b))
    # **문턱은 도메인 수에 맞춘다**(노트 282). ``t_min=2`` 는 한 도메인을
    # 볼 때의 값인데 여기서는 K 개를 동시에 본다 --- K=9 면 귀무 아래서도
    # |t|>2 가 적어도 하나 나올 확률이 **34%** 다(기대 0.41개). 노트 275의
    # 규칙 ②가 그 문턱을 그대로 써서 우연만으로 세 번에 한 번 닫혔다.
    # 본페로니: z(0.05 / 2K). K=9 -> 2.77.
    if t_min is None:
        t_min = float(_norm_ppf(1.0 - 0.05 / (2 * max(len(ks), 1))))
    tot = sum(len(a[k][0]) for k in ks) or 1
    per, net, mov, real_mov, real_net = {}, 0.0, 0.0, 0.0, 0.0
    for k in ks:
        n = len(a[k][0])
        w = n / tot
        d = float(pooled({k: b[k]})) - float(pooled({k: a[k]}))
        ds = []
        for _ in range(B):
            ix = {k: rng.integers(0, n, n)}
            va, vb = pooled({k: a[k]}, ix), pooled({k: b[k]}, ix)
            if np.isfinite(va) and np.isfinite(vb):
                ds.append(vb - va)
        se = float(np.std(ds)) if ds else float("nan")
        t = d / se if se == se and se > 1e-9 else float("nan")
        per[k] = {"차": round(d, 4), "짝SE": round(se, 4),
                  "t": round(t, 2) if t == t else None, "n": n}
        net += w * d
        mov += w * abs(d)
        if t == t and abs(t) >= t_min:
            real_mov += w * abs(d)
            real_net += w * d
    sig = {k: v for k, v in per.items() if v["t"] and abs(v["t"]) >= t_min}
    worst = max(sig, key=lambda k: abs(per[k]["차"])) if sig else None
    # **순서를 주장해도 되나**(노트 315). 노트 310 이 여기서 나온 도메인 차를
    # 크기 순으로 늘어놓고 그 순서 위에 결론을 세웠는데, 하루 뒤 잡음이 작은
    # 자로 다시 재니 두 순서의 상관이 -0.048 이었다. **못 가르는 값들의
    # 순서도 못 가른다.** 차와 짝SE 가 여기 다 있으므로 짝짝이 확률을 셀 수
    # 있다 --- 거부권이 아니라 이름표다.
    try:
        from .ordering import report as _ord
        ordr = _ord({k: (v["차"], v["짝SE"]) for k, v in per.items()
                     if v["짝SE"] == v["짝SE"]})
    except Exception as e:
        ordr = {"한 줄": f"순위 검사 실패: {type(e).__name__} {e}"}
    return {"순": round(net, 4), "총량": round(mov, 4), "순위": ordr,
            "t문턱": round(float(t_min), 2), "도메인 수": len(ks),
            "진짜 총량": round(real_mov, 4), "진짜 순": round(real_net, 4),
            "상쇄배": round(real_mov / abs(real_net), 1)
                      if abs(real_net) > 1e-9 else None,
            "제일 큰 도메인": worst,
            "제일 큰 값": per[worst]["차"] if worst else None,
            "진짜 몇": len(sig), "도메인별": per}


def coverage(pr: dict) -> dict:
    """**판정치가 몇 도메인에서 나왔나**(노트 231).

    ``pooled`` 은 유한 표본이 20 미만이거나 예측 분산이 0 인 도메인을
    조용히 버린다. 그래서 **여덟 도메인에서 죽은 정식화도 숫자를 받는다**
    --- F1 프로크루스테스가 아홉 중 여덟에서 예측이 통째로 NaN 인데
    $+$0.1472 를 보고했고, 그것은 펀딩 80건 하나만의 값이었다. 노트 5~124 의
    옛 파이프라인이자 포트폴리오의 기준선이 오래전부터 죽어 있었고 판이
    그것을 숨겼다.

    노트 220이 같은 모양을 축 무리 쪽에서 봤다(``기타 단독 +0.5037'' 이
    게임 혼자 값이었다). 이건 정식화 쪽이다. **판 옆에 늘 적는다.**"""
    live, dead = {}, []
    for d, (p, y) in pr.items():
        ok = np.isfinite(p) & np.isfinite(y)
        if ok.sum() >= 20 and np.std(p[ok]) > 1e-12:
            live[d] = int(ok.sum())
        else:
            dead.append(d)
    return {"도메인": len(live), "표본": sum(live.values()),
            "죽은": sorted(dead), "도메인별": live}


def pooled_cov(pr: dict) -> tuple:
    """(판 rho, 덮음) --- 둘을 떼어 놓지 않는다."""
    return float(pooled(pr)), coverage(pr)

def by_obs(pr: dict, data, T: float = 2025.0, cut: float = 0.7) -> dict:
    """판을 **관측률**로 갈라 적는다 --- 대입된 행과 관측된 행(노트 234).

    노트 85의 중립 대입은 축이 없는 도메인도 채점하려고 넣은 것이고 맞는
    결정이었다. 다만 **대입한 것과 관측한 것을 판정치가 구분하지 않는다.**
    유보 행의 관측률 중앙이 도메인마다 0.53$\sim$0.79 라 **모든 행에서
    축의 4분의 1에서 절반이 대입값**이다.

    갈라 보면 차이가 크다 --- 모바일에서 관측 많은 절반이 적은 절반보다
    $\rho$ 가 **$+$0.21** 높다(팝업 $+$0.11$\sim$0.12). 다만 애니는
    $-$0.05 로 반대다. **보편 법칙이 아니라 도메인마다 다르고, 그래서
    더더욱 하나로 평균하면 안 된다.**

    ``by_kind`` 와 같은 성질이다 --- 순위에 안 쓰고 옆에 적기만 한다."""
    import numpy as _np
    hi, lo = {}, {}
    for d, (p, y) in pr.items():
        if d not in data.dom:
            continue
        M = data.dom[d][1]
        yr = data.yr[d]
        h = _np.isfinite(data.dom[d][2]) & _np.isfinite(yr) & (yr >= T)
        obs = (M[h] > 0).mean(1)
        n = min(len(p), len(obs))
        m = obs[:n] >= cut
        if m.sum() >= 20:
            hi[d] = (p[:n][m], y[:n][m])
        if (~m).sum() >= 20:
            lo[d] = (p[:n][~m], y[:n][~m])
    out = {}
    for k, sub in (("관측", hi), ("대입", lo)):
        if not sub:
            continue
        n = sum(int(_np.isfinite(v[1]).sum()) for v in sub.values())
        out[k] = {"rho": round(float(pooled(sub)), 4), "n": n,
                  "도메인": sorted(sub)}
    return out
