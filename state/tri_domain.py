"""세 도메인 전이 --- 팝업 · 아이돌 · 게임.

노트 12가 병목을 지목했다. 두 도메인 세 축으로는 셀이 24개뿐이라 증폭 가설도
전이 일반성도 확정할 수 없었다. 게임 출시를 세 번째 도메인으로 넣어 셀을 늘린다.

네 도메인은 표면이 전혀 다르다.

    팝업   기획서 → 일평균 방문자 (게이트 계수)
    아이돌 데뷔 정보 → 초동 판매량 (한터 기준)
    게임   스토어 메타 → 리뷰 총계 (플레이어 수 대리)
    도서   상품 메타 → 판매지수 (알라딘 Sales Point)

라벨의 물리량이 다르므로 도메인 안에서 표준화한다. 검정하는 것은 절대값이 아니라
**축과 결과의 관계**다.

**시간 처리가 도메인마다 반대 방향이다.** 아이돌은 최근일수록 초동이 크고(버전
경쟁), 게임은 오래될수록 리뷰가 많다(누적). 노트 11에서 확립한 대로 각 도메인에서
선형 시간 추세를 뺀 뒤 비교한다. 빼지 않으면 두 추세가 서로 상쇄되거나 증폭돼
전이 성적이 의미를 잃는다.

측정:
  A 도메인 내부      각 도메인에서 축이 상수를 이기는가
  B 여섯 방향 전이   출처에서만 학습해 대상을 예측 (대상 라벨 미사용)
  C 계수 삼각비교    세 도메인이 각 축에 같은 부호를 주는가
  D 증폭 가설 재검정 셀이 늘어난 상태에서 노트 12의 미확정 가설을 다시 검정

사용: python3 -m state.tri_domain
"""
from __future__ import annotations

import json
from datetime import date
from itertools import permutations
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge

SEED = 20260728
ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
KO = {"target_breadth": "타깃 폭", "venue_prominence": "매장 노출도",
      "entry_friction": "입장 허들", "media_push": "미디어 투입", "goods_scale": "굿즈 규모"}


def z(v):
    v = np.asarray(v, float)
    return (v - v.mean()) / (v.std() + 1e-9)


def detrend(v, t):
    ok = np.isfinite(t)
    if ok.sum() < 10:
        return np.asarray(v, float)
    X = np.column_stack([np.ones(ok.sum()), t[ok]])
    out = np.asarray(v, float).copy()
    out[ok] = v[ok] - X @ np.linalg.lstsq(X, v[ok], rcond=None)[0]
    return out


# 탈추세 변수는 도메인마다 다르다. 무엇이 라벨을 밀어 올리는지가 다르기 때문이다.
#   팝업·아이돌 --- 달력 시간. 시장 자체가 커져 왔다.
#   게임        --- **출시 후 경과 시간**. 리뷰는 출시일부터 누적된다.
# 게임에 달력 연도를 쓰면 설명력이 34.0%인데, log10(경과일수)를 쓰면 47.5%다.
# 누적은 로그 곡선이므로 형태를 맞춰야 잔차가 공정한 비교 대상이 된다.
ASOF = date(2026, 7, 28)


def _from_axes_json(path: str, date_key: str, trend: str = "year"):
    d = json.loads(Path(path).read_text())
    rows = list(d.values())
    A = np.array([[r["axes"][a] for a in ALL5] for r in rows])
    M = np.array([[r["mask"][a] for a in ALL5] for r in rows])
    y = np.array([r["y"] for r in rows])
    if trend == "elapsed":
        t = []
        for r in rows:
            s0 = (r.get(date_key) or "")[:10]
            try:
                dd = (ASOF - date(*map(int, s0.split("-")))).days
                t.append(np.log10(max(dd, 1)))
            except (ValueError, TypeError):
                t.append(np.nan)
        t = np.array(t, float)
    else:
        t = np.array([int((r.get(date_key) or "0")[:4])
                      if (r.get(date_key) or "")[:4].isdigit() else np.nan
                      for r in rows], float)
    return A, M, y, t


# 슬롯 다섯 개 밖의 **고유 축**. 도메인마다 개수도 종류도 다를 수 있다 ---
# 정렬에 쓰이지 않으므로 대응물이 필요 없다(노트 36).
#
# 게임만 넣는다. 관측 축이 둘(타깃 폭·굿즈 규모)뿐이라 인자 공간이 사실상
# 회전만 하고 있었는데, 넷을 더하니 서른 셀 평균 순위 상관이 +0.3440에서
# +0.3506으로 오르고 짝지은 95% 구간이 [+0.0014, +0.0110]로 0을 넘는다(노트 54).
# 팝업은 같은 처리로 -0.017, 아이돌 -0.005로 나빠져 넣지 않는다.
EXTRA_DOMAINS = ("게임",)


def load_all(with_names: bool = False):
    """도메인을 같은 형식으로 낸다. 팝업은 사람 태그, 나머지는 규칙 유도다.

    with_names=True 면 (도메인, 축 이름) 쌍을 낸다. 고유 축이 붙은 도메인은
    이름 목록이 다섯 개보다 길다."""
    from .slots import load_popup
    X, yp, w, Ap, Mp, gp, tp, cols = load_popup()
    tpv = np.array([int(s[:4]) if s and s[:4].isdigit() else np.nan for s in tp], float)
    out = {"팝업": (Ap, Mp, yp, tpv)}
    out["아이돌"] = _from_axes_json("data/state/idol_axes.json", "debut_date")
    out["게임"] = _from_axes_json("data/state/game_axes.json", "release_date",
                                trend="elapsed")
    # 네 번째 도메인. 판매지수는 누적이므로 게임 리뷰와 같은 경과시간 탈추세를 쓴다.
    bp = Path("data/state/book_axes.json")
    if bp.exists():
        out["도서"] = _from_axes_json(str(bp), "pub_date", trend="elapsed")
    # 다섯 번째 도메인 --- 크라우드펀딩(노트 40).
    #
    # 라벨이 **후원자 수**라 팝업 일평균 방문자와 같은 물리량이다. 캠페인 기간이
    # 대개 30일 안팎으로 고정이므로 누적 편향이 게임·도서만큼 크지 않다. 대신
    # 시장 자체가 커져 왔으므로 **시작 연도**로 탈추세한다(팝업·아이돌과 같음).
    fp = Path("data/state/funding_axes.json")
    if fp.exists():
        out["펀딩"] = _from_axes_json(str(fp), "start_date")
    # 여섯 번째 도메인 --- 웹툰 연재(노트 46).
    #
    # 라벨이 **관심 등록 수**라 팝업 방문자·펀딩 후원자와 같은 물리량이다.
    # 연재 시작부터 누적되므로 게임·도서와 같은 log 경과일 탈추세를 쓴다.
    wp = Path("data/state/webtoon_axes.json")
    if wp.exists():
        out["웹툰"] = _from_axes_json(str(wp), "start_date", trend="elapsed")
    # 일곱 번째 도메인 --- 애니메이션 스트리밍(노트 69).
    #
    # 노트 68이 남은 길을 하나로 좁혔다 --- 웹툰을 세 배로 키워도 구간이 안
    # 좁아졌고, 유효 표본은 셀 수가 아니라 도메인 수에 지배된다. 여섯이면 셀
    # 30개, 일곱이면 42개다.
    #
    # 라벨이 **한줄평 수**라 게임 리뷰·도서 판매지수와 같은 누적 물리량이다.
    # 1화가 플랫폼에 올라온 날 기준 log 경과일로 탈추세한다.
    ap_ = Path("data/state/anime_axes.json")
    if ap_.exists():
        out["애니"] = _from_axes_json(str(ap_), "start_date", trend="elapsed")
    # 여덟 번째 도메인 --- 모바일 게임(노트 74).
    #
    # 노트 73이 값을 계산했다 --- 셀 42→56, 게이트 유효 표본 6→7, 합의 투표자
    # 6→7. 라벨이 **평가 참여자 수**라 스팀 게임 리뷰 총계와 같은 누적 물리량이며
    # 출시일 기준 log 경과일로 탈추세한다. 축 배선을 스팀과 일부러 같게 맞춰
    # 두 도메인의 차이가 배선이 아니라 시장에서 오게 한다.
    mp = Path("data/state/mobile_axes.json")
    if mp.exists():
        out["모바일"] = _from_axes_json(str(mp), "release_date", trend="elapsed")
    # 아홉 번째 도메인 --- 일본 만화(노트 78).
    #
    # 노트 76이 배선을 닫았고 노트 77이 누출을 다 막았다. 남은 지렛대가
    # 도메인뿐이라 셀 54→72로 늘린다. 라벨이 **서재 등록 수**라 웹툰 관심
    # 등록 수와 같은 누적 물리량이며 연재 시작일 기준 log 경과일로 탈추세한다.
    # 축 배선을 웹툰과 같게 맞춰 두 도메인의 차이가 시장에서 오게 한다.
    gp = Path("data/state/manga_axes.json")
    if gp.exists():
        out["만화"] = _from_axes_json(str(gp), "start_date", trend="elapsed")
    # 열 번째 도메인 --- 세계 애니(AniList, 노트 81).
    #
    # 애니(라프텔)와 **같은 매체를 다른 플랫폼이 잰다** --- 한국 구독자의
    # 한줄평 수 대 세계 이용자의 서재 등록 수. 노트 79가 웹툰/만화에서 같은
    # 구조로 라벨 신뢰도를 쟀고 여기서 한 번 더 잰다.
    wp2 = Path("data/state/wanime_axes.json")
    if wp2.exists():
        out["세계애니"] = _from_axes_json(str(wp2), "start_date", trend="elapsed")
    # 열한 번째 도메인 --- **시장 팝업**(노트 283 · 284, `ingest/market_axes.py`).
    #
    # 기사가 된 팝업 205건이다. 내부 팝업(75행)과 **붙이지 않고 따로 연다** ---
    # 손 축 마스크가 내부 100% 대 시장 0% 라 붙이면 마스크 무늬가 곧 출처
    # 표지가 되고 출처가 라벨을 3.2배로 가른다(노트 266의 덫과 같은 자리).
    #
    # 라벨이 **일평균 방문**이라 내부 팝업과 같은 물리량이고 기간이 제각각이라
    # 시작 연도로 탈추세한다(팝업 · 펀딩 · 아이돌과 같음). 학습 101행이라
    # 청력 문턱(F18 의 22)을 넘는다 --- 내부 팝업 16행이 못 가진 조건이다.
    #
    # **읽을 때 조심할 것**: 이 도메인은 결과로 선택된 모집단이다(기사가 된
    # 것만 있다). 그 안에서의 순위 과제로만 읽고, 전체 팝업으로 일반화하지
    # 않는다. 라벨 신뢰등급도 C · D · E 가 절반이 넘는다.
    mk = Path("data/state/market_axes.json")
    if mk.exists():
        out["시장팝업"] = _from_axes_json(str(mk), "period_from")
    # **id 목록을 같이 넘긴다**(노트 368) --- 채움을 자리가 아니라 키로
    # 붙이기 위해서다. 축 파일의 키 순서가 곧 행 순서다(`_from_axes_json`).
    _ids = {}
    for _dom, _p in (("만화", gp), ("세계애니", wp2)):
        try:
            if _p.exists():
                _ids[_dom] = list(json.loads(_p.read_text()))
        except Exception:
            pass
    _apply_adopted(out, _ids)
    if not with_names:
        return out
    from .own_axes import extend
    return extend(out, set(EXTRA_DOMAINS))


# ── 노트 108에서 채택한 것 ─────────────────────────────────────────────
#
# 두 가지다. 둘 다 씨앗 넷 붓스트랩에서 채택(4/4, 판정치 +0.0232,
# 구간 [+0.0119, +0.0322])이고 시간 분할 네 시점 모두 양수다(+0.0309).
#
# ① **미디어 홍보 채우기.** 만화 · 세계애니는 이 축이 덮개율 0%였다. AniList
#    에서 공식 외부 채널 수와 예고편 유무를 4,737건 받아 채웠다(둘 다 100%).
#    개념을 하나로 고정한 것이 핵심이다 --- ``얼마나 밀었나''를 공식 채널
#    개수로 잰다. 채우고 방향을 맞추면 정렬 잔차가 0.510으로 **현행 공통 축
#    셋(0.556)보다 낫다.**
#
# ② **방향 맞춤.** 입장료와 미디어 홍보는 도메인마다 라벨과의 부호가 갈린다
#    (입장료: 팝업 -0.251 대 세계애니 +0.587). 프로크루스테스는 고유 축의
#    부호는 흡수하지만 **공통 축의 부호는 흡수하지 못한다** --- 같은 방향
#    뒤집기를 하고 정렬에 안 넣으면 판정치 변화가 정확히 0이다(노트 105).
#    부호는 보정 표본 50%면 전체와 9.4/10 일치한다.
#
# 두 축은 `procrustes.COMMON` 에 들어간다(노트 108). 팝업은 전체 자료에서
# +0.4501 -> +0.4601 이지만 씨앗 넷 보류이고 시간 분할에서는 음수다 ---
# **도구 쪽 검증은 아직 남았다.**
# **자리가 아니라 id 로 붙인다**(노트 368). 옛 코드는 ``value``/``mask`` 를
# 행 순서 그대로 얹고 길이가 다르면 ``continue`` 로 넘어갔다 --- 파일에
# ``ids`` 가 들어 있는데도 안 썼다. 만화 행이 1,789 에서 2,041 로 늘자
# 축 하나가 예외도 경고도 없이 사라졌고(노트 365) 그것이 아홉 번째
# 갈라진 목록이다.
#
# ``media_push_fill2.json`` 이 있으면 그쪽을 먼저 쓴다 --- 만화는 노트
# 368 이 ``ingest/manga_push`` 로 다시 만들었다(개념은 노트 108 그대로,
# 눈금은 저장소 안에 근거가 있는 것으로).
MPUSH_ID = "USE_ID"


def _fill_by_id(A, M, ids_now, d, col):
    """id 로 맞춰 붙인다. 못 찾은 행은 **건드리지 않는다**."""
    ids = d.get("ids")
    if not ids:
        return None
    look = {k: (v, m) for k, v, m in zip(ids, d["value"], d["mask"])}
    hit = sum(1 for k in ids_now if k in look)
    if hit < 0.5 * len(ids_now):
        return None
    A, M = A.copy(), M.copy()
    for i, k in enumerate(ids_now):
        vm = look.get(k)
        if vm is not None:
            A[i, col], M[i, col] = vm
    return A, M, hit


def _apply_adopted(out, ids_by_dom=None) -> None:
    op = Path("data/state/axis_orient.json")
    ix = {a: i for i, a in enumerate(ALL5)}
    fills = [Path("data/state/media_push_fill2.json"),
             Path("data/state/media_push_fill.json")]
    seen = set()
    for fp in fills:
        if not fp.exists():
            continue
        fill = json.loads(fp.read_text())
        for dom, d in fill.items():
            if dom not in out or dom in seen:
                continue
            A, M, y, t = out[dom]
            ids_now = (ids_by_dom or {}).get(dom)
            got = None
            if ids_now is not None and len(ids_now) == len(y):
                got = _fill_by_id(A, M, ids_now, d, ix["media_push"])
            if got is not None:
                A, M, _hit = got
                out[dom] = (A, M, y, t); seen.add(dom); continue
            # id 를 못 쓰면 옛 방식(자리) --- 다만 **길이가 맞을 때만**
            v = np.asarray(d["value"], float)
            mk = np.asarray(d["mask"], float)
            if len(v) != len(y):
                import warnings
                warnings.warn("media_push 채움 길이 불일치: %s %d 대 %d --- 축이 빠진다"
                              % (dom, len(v), len(y)))
                continue
            A, M = A.copy(), M.copy()
            A[:, ix["media_push"]] = v
            M[:, ix["media_push"]] = mk
            out[dom] = (A, M, y, t); seen.add(dom)
    if op.exists():
        neg = json.loads(op.read_text())
        for ax, doms in neg.items():
            for dom in doms:
                if dom not in out:
                    continue
                A, M, y, t = out[dom]
                A = A.copy()
                A[:, ix[ax]] = 1.0 - A[:, ix[ax]]
                out[dom] = (A, M, y, t)


def prep(A, M, y, t, use):
    """공통 축만 남기고, 도메인 안에서 탈추세 + 표준화."""
    idx = [ALL5.index(a) for a in use]
    keep = M[:, idx].all(1)
    a = A[keep][:, idx]
    yy = detrend(y[keep], t[keep])
    aa = np.column_stack([z(detrend(a[:, j], t[keep])) for j in range(len(idx))])
    return aa, z(yy), int(keep.sum())


def cv_within(A, y, reps=40, folds=5):
    n = len(y)
    if n < 25:
        return {"median": None, "win_rate": None, "note": f"표본 부족(n={n})"}
    diffs = []
    for r in range(reps):
        rng = np.random.default_rng(SEED + r)
        gb = rng.permutation(n) % folds
        ec, em = [], []
        for k in range(folds):
            te, tr = np.where(gb == k)[0], np.where(gb != k)[0]
            if len(te) == 0 or len(tr) < 10:
                continue
            ec.append(np.abs(np.median(y[tr]) - y[te]))
            em.append(np.abs(Ridge(alpha=1.0).fit(A[tr], y[tr]).predict(A[te]) - y[te]))
        if not ec:
            continue
        diffs.append(float(np.concatenate(em).mean() - np.concatenate(ec).mean()))
    if not diffs:
        return {"median": None, "win_rate": None, "note": "폴드 구성 실패"}
    v = np.array(diffs)
    return {"median": round(float(np.median(v)), 4), "win_rate": round(float((v < 0).mean()), 3)}


def cross(Asrc, ysrc, Atgt, ytgt, perm=3000):
    m = Ridge(alpha=1.0).fit(Asrc, ysrc)
    base = np.abs(np.median(ytgt) - ytgt).mean()
    obs = float(np.abs(m.predict(Atgt) - ytgt).mean() - base)
    rng = np.random.default_rng(SEED)
    null = np.array([float(np.abs(Ridge(alpha=1.0)
                                  .fit(Asrc, ysrc[rng.permutation(len(ysrc))])
                                  .predict(Atgt) - ytgt).mean() - base) for _ in range(perm)])
    return {"obs": round(obs, 4), "p": round(float((null <= obs).mean()), 4),
            "coef": [round(float(c), 3) for c in m.coef_]}


def coverage(doms) -> dict:
    """도메인별 축 태깅률. 공통 축은 여기서 데이터로 정한다 --- 미리 정하면
    한 도메인에 없는 축을 넣어 완전 케이스가 0이 된다(실제로 그랬다)."""
    out = {}
    for k, (A, M, y, t) in doms.items():
        out[k] = {a: float(M[:, ALL5.index(a)].mean()) for a in ALL5}
    return out


def run(use=None, min_cov: float = 0.6) -> dict:
    doms = load_all()
    cov = coverage(doms)
    print("=== 축별 태깅률 (도메인 × 축) ===")
    print(f"  {'축':<12}" + "".join(f"{k:>9}" for k in doms))
    for a in ALL5:
        print(f"  {KO[a]:<12}" + "".join(f"{cov[k][a]:>9.0%}" for k in doms))
    if use is None:
        use = [a for a in ALL5 if all(cov[k][a] >= min_cov for k in doms)]
        dropped = [a for a in ALL5 if a not in use]
        print(f"\n공통 축(태깅률 {min_cov:.0%} 이상): {[KO[a] for a in use]}")
        print(f"제외: {[KO[a] for a in dropped]}")
    if len(use) < 1:
        print("공통 축이 없어 전이 검정 불가")
        return {"cov": cov, "axes": list(use)}

    P = {}
    for k, (A, M, y, t) in doms.items():
        a, yy, n = prep(A, M, y, t, use)
        P[k] = (a, yy, n)
        print(f"{k:<6} 완전 케이스 {n}건")
    print()

    out = {"axes": list(use), "cov": cov, "n": {k: v[2] for k, v in P.items()}}
    print("── A. 도메인 내부 ──")
    for k, (a, yy, n) in P.items():
        r = cv_within(a, yy)
        out[f"내부_{k}"] = r
        if r["median"] is None:
            print(f"  {k:<6}{r['note']}")
        else:
            print(f"  {k:<6}n={n:>3}  Δ중앙 {r['median']:+.4f}  승률 {r['win_rate']:.2f}")

    print("\n── B. 여섯 방향 전이 (대상 라벨 미사용, 탈추세) ──")
    out["교차"] = {}
    for s, tg in permutations(P, 2):
        r = cross(P[s][0], P[s][1], P[tg][0], P[tg][1])
        out["교차"][f"{s}→{tg}"] = r
        mark = "✅" if r["p"] < 0.05 else ("△" if r["obs"] < 0 else "✗")
        print(f"  {s:<5}→ {tg:<6}Δ{r['obs']:+.4f}  순열 p={r['p']:.4f}  {mark}")

    print("\n── C. 계수 삼각비교 ──")
    co = {k: [round(float(c), 3) for c in Ridge(alpha=1.0).fit(v[0], v[1]).coef_]
          for k, v in P.items()}
    out["계수"] = co
    print(f"  {'축':<12}" + "".join(f"{k:>10}" for k in P))
    for j, ax in enumerate(use):
        vals = [co[k][j] for k in P]
        same = len({v > 0 for v in vals}) == 1
        print(f"  {KO[ax]:<12}" + "".join(f"{v:>+10.3f}" for v in vals) +
              ("   전원 일치" if same else ""))
    Path("data/state/tri_domain.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    return out


if __name__ == "__main__":
    run()


# ── 표본 크기 교란 배제 ─────────────────────────────────────────────────
def balanced(use=None, n_cap: int = 63, reps: int = 200, min_cov: float = 0.6) -> dict:
    """게임 도메인만 n이 세 배 이상 크다. 전이 성적의 차이가 축의 성질이 아니라
    계수 추정 정밀도(=표본 크기) 때문일 수 있다.

    세 도메인을 같은 n으로 맞춰 반복 부분표집한다. 순서가 유지되면 표본 크기
    설명은 기각되고, 뒤집히면 노트 10의 비대칭이 단순히 n 이야기였던 것이다."""
    doms = load_all()
    cov = coverage(doms)
    if use is None:
        use = [a for a in ALL5 if all(cov[k][a] >= min_cov for k in doms)]
    P = {k: prep(A, M, y, t, use)[:2] for k, (A, M, y, t) in doms.items()}
    print(f"표본 균형 검정 --- 도메인마다 n={n_cap}으로 맞춰 {reps}회 반복")

    res = {}
    for s, tg in permutations(P, 2):
        wins, ds = 0, []
        for r in range(reps):
            rng = np.random.default_rng(SEED + r)
            As, ys = P[s]
            At, yt = P[tg]
            i = rng.choice(len(ys), min(n_cap, len(ys)), replace=False)
            j = rng.choice(len(yt), min(n_cap, len(yt)), replace=False)
            m = Ridge(alpha=1.0).fit(As[i], ys[i])
            base = np.abs(np.median(yt[j]) - yt[j]).mean()
            d = float(np.abs(m.predict(At[j]) - yt[j]).mean() - base)
            ds.append(d)
            wins += d < 0
        res[f"{s}→{tg}"] = {"median": round(float(np.median(ds)), 4),
                            "win_rate": round(wins / reps, 3)}
        print(f"  {s:<5}→ {tg:<6}Δ중앙 {res[f'{s}→{tg}']['median']:+.4f}  "
              f"승률 {res[f'{s}→{tg}']['win_rate']:.2f}")
    Path("data/state/tri_balanced.json").write_text(
        json.dumps({"n_cap": n_cap, "reps": reps, "axes": list(use), "res": res},
                   ensure_ascii=False, indent=1))
    return res
