"""**우리 쪽 사정이 축에 실렸나** --- 노트 546 · 552 · 554 를 한 감사로 묶는다.

세 노트가 사흘 사이에 같은 뿌리에서 나왔다.

    노트 546   플랫폼 운영(매일$+$ 전환)이 ``days`` 를 바꾼다 ---
               ``meta_c3_웹툰`` 이 사실상 ``월요일이냐''였고 그것은 완결 표지였다
    노트 552   같은 전환이 ``start_date`` 도 옮긴다 --- 옛 작품 $61$ 개가
               $2025$ 년 이후 유보에 신작인 척 들어와 있었다(판 $0.0149$)
    노트 554   **우리 수집 순서**가 마스크에 실린다 --- 레코드 파일이 인기순으로
               정렬돼 있고 수집기가 앞에서부터 자른다

셋 다 ``작품의 성질''이 아니라 **작품 바깥의 사정**(플랫폼 운영 · 우리 수집)이
축에 들어온 것이다. 노트 117 의 가드 둘(라벨 상관 · 같은 플랫폼)과 노트 141 의
시점 가드는 이것을 못 잡는다 --- 상관도 낮고, 플랫폼도 다르고, 시점도 사전이다.

**그래서 검사 셋을 여기 모은다.** 문턱은 이번 사이클의 관측에서 잡았고
(아래 각 함수의 독스트링), **판정이 아니라 순위**로 낸다 --- 세 검사 다
``이 값을 넘으면 나쁘다''가 아니라 ``여기부터 보라''다.

사용:
    python3 -m lab.sideaudit            전체 표
    from lab.sideaudit import audit ; audit()
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

import numpy as np
from math import comb as _comb
from scipy.stats import rankdata, spearmanr

D = Path("data/state")
T = 2025.0

# ── 검사 ① 사후 상태 (노트 546 · 549) ────────────────────────────────────
# 도메인 → 그 도메인의 **사후 플래그** 칸들. 결과가 나온 뒤에야 갈리는 상태.
POST_FLAG = {"웹툰": ("finished", "daily_pass"),
             "만화": ("status",), "세계애니": ("status",), "애니": ("is_ending",)}
POST_HIT = 0.25          # |축 ↔ 사후 플래그| 가 이보다 크면 본다
# 노트 546 에서 meta_c3 가 +0.3303 · 노트 552 에서 cal_dow_cos 가 +0.3297
# 이었고, 같은 도메인의 나머지 축은 전부 $|0.20|$ 아래였다. 0.25 는 그 사이다.

# ── 검사 ② 날짜가 맞나 (노트 552) ────────────────────────────────────────
# 도메인 → (쌓이는 수 칸, 주당 상한 칸, 문턱). 자세한 근거는 lab/datehygiene.
RATE = {"웹툰": ("n_episode", "n_day", 2.0),
        # **연재중 행은 셈이 다르다**(노트 592). ``세계애니``·``만화`` 의
        # ``n_episode``/``n_chapter`` 는 완결작에서는 *나온 수* 인데
        # 연재중에서는 *편성된 총수* 다 --- 3주 전 시작한 24부작이 규칙에
        # 걸린다. 태거도 그것을 알고 ``status == "FINISHED"`` 일 때만
        # ``goods_scale`` 을 관측한다(``ingest/wanime_axes.py``, 노트 21).
        # **축이 안 쓰는 행을 감사가 물면 상시 거짓 양성이 되고, 그러면
        # 사람이 감사를 안 본다.** 네 번째 칸은 (필드, 값) 거르개다.
        # ``만화`` 는 **문을 안 단다** --- ``n_chapter`` 가 완결(5,823)·중단
        # (61) 행에만 있고 연재중에는 아예 없다. 문을 달면 중단 행만
        # 가려지는데 그 행들은 축을 먹인다(``ingest/manga_axes.py`` 는
        # 상태를 안 본다). **거르개는 태거가 안 쓰는 행에만 건다.**
        "만화": ("n_chapter", None, 2.0),
        "애니": ("n_episode", None, 2.0),
        "세계애니": ("n_episode", None, 2.0, ("status", "FINISHED"))}
RATE_HIT = 0.010         # 위반 비율이 1% 를 넘으면 본다
# 웹툰이 1.8% 로 걸렸고 세계애니 1.1% · 애니 0.5% · 만화 0.1% 는 정당한
# 일괄 공개였다. **비율만으로는 못 가른다** --- 걸린 것들이 한 플래그와
# 한 요일에 몰리는지(웹툰은 매일+ 95% · 월요일 84%)를 같이 본다.

# ── 검사 ③ 수집 순서 (노트 554) ─────────────────────────────────────────
GAP_HIT = 0.10           # |학습 결측률 − 유보 결측률| 가 이보다 크면 본다

# **곱에 문턱이 있다**(노트 593). 이 검사가 낸 후보를 실제로 세 번 돌렸다 ---
# 애니(곱 0.200) 채택 · 만화(0.072) 채택 · **웹툰(0.043) 기각**. 웹툰은
# 팔 둘(축 통째 가림 · 관측-0 을 결측으로)이 **판을 -0.009 내리고 그 도메인을
# -0.026 깎았다.** 마스크가 수집 순서를 나르는 것은 맞지만 **축이 주는 것이
# 더 크다** --- 웹툰은 학습에서도 70% 가 관측되므로 축이 실제로 정보를 준다.
#
# 남은 미처리(모바일 0.031 · 세계애니 0.010 · 도서 0.003)는 **전부 웹툰
# 아래**다. 그래서 이 아래는 안 쫓는다.
#
# **표본이 셋뿐이라 문턱 자체는 약하다** --- 0.043 과 0.072 사이 어디인지는
# 모른다. 새 후보가 그 사이에 오면 그때 다시 본다.
CHASE_HIT = 0.05         # 곱이 이보다 작으면 **안 쫓는다**(노트 593)
# 곱(차 × |마스크↔라벨|)으로 줄 세운다. 애니 trend 0.199(이미 가림) ·
# 만화 trend 0.070 · 웹툰 0.043 · 모바일 0.032 · 도서 0.003.

TODAY = datetime.date(2026, 8, 4)


def _part(a, b, c):
    ra, rb, rc = rankdata(a), rankdata(b), rankdata(c)
    r = lambda u, v: spearmanr(u, v).correlation      # noqa: E731
    ab, ac, bc = r(ra, rb), r(ra, rc), r(rb, rc)
    den = np.sqrt((1 - ac ** 2) * (1 - bc ** 2))
    return (ab - ac * bc) / den if den > 0 else np.nan


def _records(rf: str) -> dict:
    p = D / rf
    if not p.exists():
        return {}
    j = json.loads(p.read_text())
    return {v["record_id"]: v for v in j.values()
            if isinstance(v, dict) and "record_id" in v}


def post_state(data, ids_all, recmap) -> list:
    """검사 ① --- 축이 **사후 플래그**를 읽고 있나(연도 통제).

    노트 546 이 찾은 무늬. 상태가 라벨과 붙는 것 자체는 누출이 아니다 ---
    **축이 그 상태를 읽을 때**가 누출이다(노트 549 가 KR 짝에서 확인했다:
    상태↔라벨이 $-0.345$ 인데 ALL5 축은 최대 $|0.14|$ 라 깨끗하다).
    """
    out = []
    for dom, flags in POST_FLAG.items():
        if dom not in data.dom or dom not in ids_all:
            continue
        ids = ids_all[dom]
        if len(ids) != len(data.dom[dom][2]):
            continue
        by = recmap.get(dom) or {}
        yr, y = data.yr[dom], data.dom[dom][2]
        ho = np.isfinite(yr) & (yr >= T) & np.isfinite(y)
        if ho.sum() < 60:
            continue
        nm = list(data.names[dom])
        A, M = data.dom[dom][0], data.dom[dom][1]
        for fl in flags:
            v = np.array([1.0 if (by.get(i) or {}).get(fl) else 0.0
                          for i in ids])
            if not (0 < v[ho].mean() < 1):
                continue
            for jx, a in enumerate(nm):
                q = ho & (M[:, jx] > 0) & np.isfinite(A[:, jx])
                if q.sum() < 60 or len(np.unique(A[q, jx])) < 3:
                    continue
                r = _part(A[q, jx], v[q], yr[q])
                if np.isfinite(r) and abs(r) >= POST_HIT:
                    out.append((abs(r), dom, a, fl, r))
    out.sort(reverse=True)
    return out


def bad_date(recmap) -> list:
    """검사 ② --- 쌓이는 수가 흐른 시간보다 많나(**라벨을 안 본다**).

    걸린 비율만으로는 못 가른다 --- 웹툰 $1.8\\%$ 는 결함이었고 세계애니
    $1.1\\%$ 는 일괄 공개였다. 그래서 **걸린 것들이 한 플래그에 몰리는지**를
    함께 낸다(웹툰은 매일$+$ $95\\%$).
    """
    out = []
    for dom, spec in RATE.items():
        cf, nd, k = spec[0], spec[1], spec[2]
        gate = spec[3] if len(spec) > 3 else None
        rf = {"웹툰": "webtoon_records.json", "만화": "manga_records.json",
              "애니": "anime_records.json", "세계애니": "wanime_records.json"}[dom]
        by = recmap.get(dom) or _records(rf)
        if not by:
            continue
        tot = n = 0
        flags = {f: 0 for f in POST_FLAG.get(dom, ())}
        for v in by.values():
            if gate and str(v.get(gate[0])) != gate[1]:
                continue
            c = v.get(cf)
            if not isinstance(c, (int, float)) or c < 10:
                continue
            try:
                dt = datetime.date.fromisoformat(str(v.get("start_date"))[:10])
            except Exception:
                continue
            tot += 1
            cap = max(float(v.get(nd) or 1), 1.0) if nd else 1.0
            if c / max((TODAY - dt).days / 7.0, 1.0) > k * cap:
                n += 1
                for f in flags:
                    if v.get(f):
                        flags[f] += 1
        if tot and n / tot >= RATE_HIT:
            # **쏠림은 바탕 비율과 견뎌야 뜻이 있다.** 세계애니 ``status`` 는
            # 98% 가 FINISHED 라 걸린 것의 100% 가 FINISHED 여도 아무 뜻이
            # 없다. 웹툰 ``daily_pass`` 는 바탕 54% 인데 걸린 것의 95% 다.
            base = {f: np.mean([1.0 if v.get(f) else 0.0
                                for v in by.values()]) for f in flags}
            lift = {f: (round(c / n / base[f], 2) if n and base[f] > 0 else None)
                    for f, c in flags.items()}
            out.append((n / tot, dom, n, tot, lift, _hygiened(dom, n)))
    out.sort(reverse=True)
    return out


def _hygiened(dom: str, n: int) -> str:
    """이 도메인이 **이미 `datehygiene` 로 처리됐는지** 본다(노트 615).

    노트 561 이 ``_handled()`` 를 만들었는데 **감사 ③ 에만 달았다.**
    ② 는 두 달 동안 웹툰 $64$ 행을 다시 보고해 왔고, 그 $64$ 행은
    노트 $552$ 가 이미 라벨을 ``NaN`` 으로 만든 바로 그 행들이다
    (``datehygiene.bad()`` 와 같은 규칙 · 같은 수).

    **이 판에서 여덟 번째로 같은 무늬다** --- 546(빈 축) · 549(provenance) ·
    581(방향) · 598(가드가 안 불림) · 603(가드가 한 도메인만) ·
    607(조항이 한 함수에만) · 614(감도를 안 찍음) · **615(고침 표시가
    한 검사에만)**. 전부 ``적어는 뒀는데 거기까지만`` 이다.
    """
    try:
        from .datehygiene import bad as _bad
        m = (_bad().get(dom))
        if m is None or not m.any():
            return ""
        return ("**노트 552 에서 처리됨** — `datehygiene` 가 이 %d 행의 라벨을 "
                "NaN 으로 둔다(축 결합은 유지)" % int(m.sum()))
    except Exception as e:  # 조용히 넘기지 않는다(노트 133)
        return "⚠ `datehygiene` 확인 실패 — %s" % e


def collect_order(data) -> list:
    """검사 ③ --- 학습과 유보의 **결측률이 다른가**, 그 마스크가 라벨과 붙나.

    곱(차 $\\times$ $|$마스크$\\leftrightarrow$라벨$|$)으로 줄 세운다. 차 하나로는
    안 된다 --- 도서 trend 는 차가 $30$\\%p 인데 마스크가 라벨과 무관해서
    결측 갈래가 실어 나를 것이 없다.

    **이미 처리된 칸은 표시한다**(노트 561). 처음엔 자료만 보고 순위를 냈는데,
    그러면 만화 trend 가 채택(노트 553) 뒤에도 $2$ 위로 남는다 --- 감사가
    ``고칠 것''과 ``이미 고친 것''을 못 가르면 매번 같은 줄을 다시 읽게 된다.
    노트 $546 \\cdot 549$ 의 뿌리(장부와 코드가 따로 자란다)와 같은 자리다.
    """
    FAM = ("trend_", "wiki_", "cal_", "tag_", "meta_", "gen", "grp",
           "mkt_", "fund_", "mob_", "wt_", "ani_", "wa_")
    handled = _handled()
    out = []
    for dom in data.dom:
        yr, y = data.yr[dom], data.dom[dom][2]
        tr = np.isfinite(yr) & (yr < T) & np.isfinite(y)
        ho = np.isfinite(yr) & (yr >= T) & np.isfinite(y)
        if tr.sum() < 60 or ho.sum() < 20:
            continue
        nm = list(data.names[dom])
        M = data.dom[dom][1]
        byf: dict = {}
        for jx, a in enumerate(nm):
            for p in FAM:
                if a.startswith(p):
                    byf.setdefault(p.rstrip("_"), []).append(jx)
                    break
        for f, js in byf.items():
            ct = float(np.mean([M[tr, i].mean() for i in js]))
            ch = float(np.mean([M[ho, i].mean() for i in js]))
            if max(ct, ch) < 0.02 or not (0 < ct < 1):
                continue
            gap = abs(ct - ch)
            if gap < GAP_HIT:
                continue
            r = _part(M[tr, js[0]].astype(float), y[tr], yr[tr])
            if not np.isfinite(r):
                continue
            out.append((gap * abs(r), dom, f, ct, ch, r,
                        handled.get((dom, f), "")))
    out.sort(reverse=True)
    return out


def _handled() -> dict:
    """{(도메인, 무리): 처리한 손잡이} --- 세 곳을 한꺼번에 읽는다.

    같은 일을 하는 손잡이가 셋이다(노트 555 의 남은 것):
    ``forms.DOMDROP``(모형층) · ``fixaxes.BLOCK``(자료층) ·
    ``loop.TREND_DROP`` / ``WIKI_DROP``(축을 아예 안 붙임).
    감사가 셋을 다 읽어야 ``이미 고친 것''을 안 세운다.
    """
    out = {}
    try:
        from .forms import REGISTRY
        for d, pats in REGISTRY["F18_bagboost"]["cls"].DOMDROP.items():
            for p in pats:
                out[(d, p.rstrip("_"))] = "DOMDROP"
    except Exception:
        pass
    try:
        from .fixaxes import BLOCK
        for (d, ax) in BLOCK:
            f = ax.split("_")[0] if "_" in ax else ax
            out.setdefault((d, f), "BLOCK")
    except Exception:
        pass
    try:
        from .loop import TREND_DROP, WIKI_DROP
        for d in TREND_DROP:
            out.setdefault((d, "trend"), "TREND_DROP")
        for d in WIKI_DROP:
            out.setdefault((d, "wiki"), "WIKI_DROP")
    except Exception:
        pass
    return out


def champion_data():
    """챔피언이 실제로 쓰는 축까지 붙인 자료.

    맨 ``harness.load()`` 는 고유 축 다섯뿐이라 ①③ 이 통째로 빈다 ---
    처음에 그렇게 돌려서 ``없음''이 나왔다. 검사 대상이 확장 축이므로
    여기서 같이 짓는다.
    """
    from . import loop as L, grpaxes, genaxes

    def ex():
        e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
             **L._tag(), **L._fund(), **L._rawsub(), **genaxes.build()}
        e.update(grpaxes.build())
        return e
    return L._idol(lambda: ex(), mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")


# 유보 행수(노트 552 정정 후 · 분모 3,369). ``domain_deltas`` 가 잡음
# 지배 도메인을 표시하는 데 쓴다.
POST_N = {"웹툰": 650, "애니": 606, "펀딩": 529, "모바일": 441, "세계애니": 300,
          "만화": 258, "게임": 180, "도서": 163, "시장팝업": 126, "팝업": 65,
          "아이돌": 51}
NOISY_N = 200            # 유보가 이보다 적으면 도메인 하나의 차는 잡음이다


def domain_deltas(deltas: dict, kind: str = "전역 제거",
                  cov: dict | None = None) -> str:
    """**전역 변경의 도메인별 차로 후보를 세우지 말라**(노트 551 · 560).

    조항은 노트 551 이 세웠다 --- ``전역으로 끄면 오른다''를 ``거기서 가리면
    오른다''로 읽지 않는다. 전역 제거의 도메인별 차에는 \\emph{이웃 효과}가
    섞여 있다. 그 도메인의 예보가 바뀌는 경로가 둘이기 때문이다.

        ① 자기 축이 없어져서
        ② **남들이 그 축으로 배운 것이 없어져서** --- 공유 모형이 바뀐다

    \\textbf{그런데 하루 만에 내가 그 조항을 어겼다.} 노트 559 의 도메인별
    표에서 도서만 $+0.0459$ 인 것을 보고 후보를 세웠는데, 도서만 바꾸니
    $\\mathbf{-0.0820}$ 으로 \\textbf{부호가 뒤집혔다}. 노트 551 의 팝업
    ($+0.0374 \\to +0.0018$)과 같은 무늬다 --- **두 번**.

    사람이 기억하는 조항은 하루를 못 갔다. 그래서 **표를 낼 때 경고를
    같이 낸다** --- 이 함수를 거치지 않고 도메인별 차를 인쇄하지 않는다.
    """
    ln = ["  %-8s %11s %7s %7s  %s"
          % ("도메인", "차", "유보", "덮음", "")]
    for d, v in sorted(deltas.items(), key=lambda kv: -abs(kv[1])):
        n = POST_N.get(d)
        tag = ("  ← **유보 %d행 · 잡음**" % n) if (n and n < NOISY_N) else ""
        c = None if cov is None else cov.get(d)
        if c is not None and c < 0.02:
            tag = "  ← **덮음 0% — 전부 이웃 효과**" + tag
        ln.append("  %-8s %+11.4f %7s %7s%s"
                  % (d, v, n if n else "?",
                     "?" if c is None else "%.0f%%" % (100 * c), tag))
    ln.append("")
    thin = [d for d in deltas
            if POST_N.get(d, 10 ** 9) < NOISY_N]
    if thin:
        ln.append("  ⚠ **유보 %d행 미만 도메인은 |차| 로 정렬하면 위로 뜬다**"
                  "(노트 562 · 591) --- %s." % (NOISY_N, " · ".join(sorted(thin))))
        ln.append("    효과 0.05 를 고르려면 (2/e)^2 = 1,600행이 필요하다. "
                  "**이 줄들은 순서에서 빼고 읽는다.**")
    if cov is None:
        ln.append("  ⚠ **덮음을 안 넘겼다** --- `cov={도메인: 그 축 덮음}` 을 "
                  "주면 **덮음 0% 인 줄**(차가 전부 이웃 효과)을 표시한다(노트 525).")
    ln.append("  ⚠ **이 표로 가림 후보를 세우지 않는다**(노트 551 · 560). "
              "%s 의 도메인별 차에는" % kind)
    ln.append("    **이웃 효과**가 섞여 있다 --- 그 도메인만 바꾸면 부호가 "
              "뒤집힐 수 있다")
    ln.append("    (팝업 +0.0374→+0.0018 · 도서 +0.0459→**-0.0820**). "
              "화면을 좁히는 데만 쓴다.")
    ln.append("    **크기는 미리 못 잰다**(노트 599 · 600) --- 짝 **일곱**에서 "
              "이웃 차가 -0.028 ~ +0.128 이고 **부호가 넷에서 뒤집힌다**.")
    ln.append("    덮음과의 순위상관이 **+0.107**(|차| 기준 +0.036) --- "
              "**덮음은 이웃 효과를 예측하지 못한다.** 덮음 0% 만 정의상 안다.")
    return "\n".join(ln)


def holdout_baseline(rho: float, dom: str, feat: str = "단일 특성") -> str:
    """**유보에서 잰 단일 특성의 rho 는 모형의 상한이 아니다**(노트 568).

    노트 $567$ 이 도서 라벨(``sales_point``)이 누적임을 찾고, 유보에서
    ``$-$출판일'' 하나가 $\\rho = +0.5615$ 인데 챔피언이 $+0.4023$ 인 것을
    ``$+0.008$ 을 안 가져가고 있다''로 읽었다. 달력을 주니 판이
    $\\mathbf{-0.0024}$ 이고 **도서 자신이 $-0.0454$** 로 내려갔다.

    이유는 하나다 --- \\textbf{유보 $\\rho$ 는 *그 자리에서 아는 것*이고
    모형은 *학습에서 배운 것*이다.} 라벨이 시간에 따라 이동하면(누적이 바로
    그것이다) 학습에서 배운 관계가 유보에서 안 맞고 오히려 해롭다.

    **같은 함정을 세 번 밟았다.**

        노트 $548$   검색 축 전체의 값(상한)을 $\\to$ 펀딩 수집의 *기대값*으로
        노트 $560$   전역 변경의 도메인별 차를 $\\to$ 그 도메인만 바꿨을 때의 *이득*으로
        노트 $568$   단일 특성의 유보 $\\rho$ 를 $\\to$ 모형이 벌 *양*으로

    셋 다 **유보에서 잰 값을 모형이 가져갈 수 있는 것으로 읽었다**. 사람이
    기억하는 조항은 세 번을 못 갔으므로 --- 노트 $561$ 이 이웃 효과 표에
    한 것과 같이 --- **수치를 낼 때 경고를 같이 낸다.**
    """
    return ("  %s 유보 rho = %+.4f (%s)\n"
            "  ⚠ **이것은 모형의 상한이 아니다**(노트 568). 유보 rho 는 *그 자리에서\n"
            "    아는 것*이고 모형은 *학습에서 배운 것*이다 --- 라벨이 시간에 따라\n"
            "    이동하면 둘이 갈린다(도서: 기준선 +0.5615 인데 달력을 주니 -0.0454).\n"
            "    상한을 말하려면 **학습에서 적합해 유보에서 채점**한다."
            % (dom, rho, feat))


BARE_HIT = 0.02          # 손 축 0 행이 이보다 많으면 표시한다(노트 603)


def trim_small(vals: dict, what: str = "구간") -> str:
    """**구간의 끝을 작은 도메인이 정하면 그 끝은 못 쓴다**(노트 591 · 607).

    노트 606 이 축을 하나씩 빼서 도메인별 손해를 내고 그 **구간**으로
    ``없는 축의 값``을 말했다. 그런데 구간의 **음수 끝**이
    아이돌(유보 51)의 -0.1235 였다 --- ``media\_push 는 해로울 수 있다``가
    **51행짜리 수치** 위에 서 있었다. 유보 200 이상만 쓰면 하단이
    -0.00001 로 올라온다.

    축-도메인 짝 42 개에서 유보 크기 ↔ $|$손해$|$ 순위상관이 **-0.364**,
    200 미만 중앙이 200 이상의 **1.67 배**다. **작은 도메인이 구간 끝을
    독차지한다.**
    """
    big = {d: v for d, v in vals.items() if POST_N.get(d, 0) >= NOISY_N}
    small = {d: v for d, v in vals.items() if d not in big}
    ln = ["  %s 전체 n=%d  [%+.4f, %+.4f]"
          % (what, len(vals), min(vals.values()), max(vals.values()))]
    if big:
        ln.append("  %s 유보 %d 이상 n=%d  [%+.4f, %+.4f]"
                  % (what, NOISY_N, len(big), min(big.values()), max(big.values())))
    if small:
        ln.append("  ⚠ **뺀 도메인**(유보 %d 미만) — %s" % (NOISY_N, " · ".join(
            "%s %+.4f(%d행)" % (d, v, POST_N.get(d, 0))
            for d, v in sorted(small.items(), key=lambda kv: -abs(kv[1])))))
        ln.append("    **구간의 끝을 작은 도메인이 정하면 그 끝은 못 쓴다**"
                  "(노트 607) --- 짝 42개에서 크기↔|값| 순위상관 -0.364.")
    ln.append("  ⚠ **행수는 대용물이다 --- 되면 `ci_keep` 을 쓴다**(노트 608): "
              "이 문턱은 42짝에서 **위양성 15개를 통과시키고 진짜 2개를 버렸다**.")
    return "\n".join(ln)


CI_B = 2000

#: 팔이 **짝지어졌을 때** 씨앗 SE 가 얼마나 작아지는지(노트 610, 판 수준).
#: 같은 적합에서 열만 가리는 팔 0.00047 대 두 번 적합하는 팔 0.00235.
PAIR_GAIN = 5.0


#: **무리 안 판의 무리 최소 행수**(노트 617 채택 · 옛 값 8).
#: 문턱을 올리면 잡음↓ 표본↓ 로 반대로 움직인다. 훑어 보니
#: 표본 SD 가 8→0.0112 · 12→0.0089 · 20→0.0058 · **30→0.0049** · 50→0.0051 로
#: 30 까지 단조로 내려가고 평평해진다(**2.3 배**). 도메인은 **일곱 그대로**라
#: 자의 뜻이 안 바뀌고(노트 598 분모 교훈) 행은 2,840→2,578 로 9% 만 준다.
#: 판과의 표본 상관은 +0.14 → **+0.31** 로 오르지만 여전히 독립이다(노트 614).
#:
#: **효과 칸으로 고르지 않았다** --- 다섯 문턱의 |차| 중 최대를 고르면
#: **유의성 위 선택**이다(노트 608). 근거는 **정밀도 곡선** 하나다.
GRP_MIN = 30

#: 자마다의 **차 표본 SD** (노트 613, 채택 팔에서 실측 · 씨앗 6~8).
#: 값은 ``(유보 행수, 순수 표본 SD)``. 문턱은 그 두 배로 읽는다.
#:
#: .. warning::
#:
#:    **이 표는 읽을 수 있지만 그 자들을 돌릴 수는 없다**(노트 683).
#:    저장소에서 재현 가능한 자는 **판 하나**다. 날짜 통제 판 · 무리 안 판 ·
#:    KR 만화 · 비게임 앱 · CN 만화의 **채점기가 저장소에 없다** ---
#:    ``manga_kr`` 를 참조하는 ``.py`` 가 0개이고 ``git log -S`` 도 0건이다.
#:    노트 583/586 채택 커밋(``bc0b19860``)이 KR 0.638→0.684 · 앱 0.290→0.505 를
#:    적었는데 건드린 파일은 ``forms.py``·``loop.py`` 뿐이다 --- **그 숫자는
#:    커밋되지 않은 스크래치 스크립트가 냈다.**
#:
#:    자료는 있다: ``data/state/manga_kr.json``(KR 명부 1,250) ·
#:    ``ingest/app_domain.py``(앱 ``_genre``). **채점기를 다시 짤 때는 노트 683 의
#:    받아들임 시험 셋을 먼저 통과시킨다** --- 행 수(1,716·1,600·352) ·
#:    챔피언 기준선(+0.6841·+0.5053·+0.3094) · 표본 SD. 안 맞으면 **새 자로
#:    취급하고 기록된 숫자와 견주지 않는다**(노트 579·580 분모 조항).
SENS = {
    "판": (3369, 0.0021),
    "날짜 통제 판": (3369, 0.0026),
    "무리 안 판": (3369, 0.0049),   # 노트 617 — 문턱 30 채택 전 0.0114
    "KR 만화": (1716, 0.0123),
    "비게임 앱": (1600, 0.0122),
    "CN 만화": (352, 0.0109),
}

#: 표본 성분에서 **유효 독립 자 수**(노트 614). 이름상 여섯인데 넷 반이다.
EFF_RULERS = 4.73


def sensitivity(effects: dict) -> str:
    """후보의 예상 효과를 받아 **어느 자가 그것을 잴 수 있는지** 찍는다(노트 614).

    ``effects`` 는 ``{자 이름: 예상 |효과|}`` 다. 자마다 차 잡음이 **5.5 배까지
    다르므로**(판 $0.0021$ 대 무리 안 판 $0.0114$) **문턱 하나를 여섯에
    같이 쓸 수 없다.**

    **관문의 힘은 자 수가 아니라 (독립 × 감도)다.** 이 판의 여섯 자는
    표본 성분에서 유효 독립이 ``EFF_RULERS`` = $4.73$ 인데(중복은
    판↔날짜 통제 판 한 쌍뿐), 노트 $586$ 채택에서는 **판 계열 셋이 다
    감도가 없어**($t=0.7 \\cdot 1.3 \\cdot 0.2$) 실제로 결정한 자가
    **둘**이었다. CN 만화는 독립성이 완벽한데 감도가 없어 관문에서 빠졌다.
    """
    ln = ["  %-13s %9s %9s %8s"% ("자", "예상 효과", "2 SD 문턱", "t")]
    can = []
    for nm, (n, sd) in SENS.items():
        e = effects.get(nm)
        if e is None:
            ln.append("  %-13s %9s %9.4f  %6s  — 안 잼" % (nm, "—", 2 * sd, "—"))
            continue
        t = abs(e) / sd
        ok = abs(e) >= 2 * sd
        if ok:
            can.append(nm)
        ln.append("  %-13s %+9.4f %9.4f %8.1f%s"
                  % (nm, e, 2 * sd, t, "  **잴 수 있다**" if ok else "  못 잰다"))
    ln.append("  → **잴 수 있는 자 %d 개** — %s" % (len(can), " · ".join(can) or "없다"))
    if not can:
        ln.append("    ⚠ **어느 자도 이 크기를 못 잰다.** 유보를 늘리거나 후보를 키운다.")
    return "\n".join(ln)


def arm_ci(diffs, 자: str = "판", paired=None, boot=None, tol: float = 0.0) -> str:
    """A/B 팔의 씨앗 차에서 구간을 내고 **그 구간이 무엇인지 적는다**(노트 610).

    이 판이 $460$ 개 노트 동안 찍어 온 ``95% 구간``은 전부 **씨앗
    스프레드**였고, 그 인쇄가 노트별 스크립트에 복제돼 있어 규약을 한
    곳에서 못 바꿨다. 여기가 그 한 곳이다.

    ``paired`` 를 **반드시 적는다.**

    * ``True`` --- 두 팔이 **같은 적합**을 쓰고 예측 때만 열을 가린다.
      씨앗 잡음이 상쇄돼 씨앗 SE 가 **약 5 배 작다**(위키 가림 팔
      $0.00047$). **좁은 구간이 효과의 확실함이 아니라 짝지어짐이다.**
    * ``False`` --- 두 팔을 **따로 적합**한다. **채택은 언제나 이쪽이다.**
      노트 $586$ 채택이 씨앗 SE $0.00235$ 로, 씨앗 기준으로도 $0$ 을 물었다.

    ``boot`` 에 행 부트스트랩 배열을 주면 **표본 구간**도 같이 찍는다 ---
    표본 성분은 **씨앗을 늘려도 안 줄어든다**(노트 $609$).
    """
    import numpy as _np
    v = _np.asarray([x for x in diffs if _np.isfinite(x)], float)
    if len(v) < 3:
        return "  ⚠ **씨앗이 %d 개뿐 --- 구간을 안 찍는다**" % len(v)
    m = float(v.mean())
    pos = int((v > tol).sum())
    lo, hi = _np.percentile(v, [2.5, 97.5])
    ln = ["  %-10s %+.5f  부호 %d/%d  **씨앗** 95%% [%+.5f, %+.5f] 폭 %.5f"
          % (자, m, pos, len(v), lo, hi, hi - lo)]
    if boot is not None:
        b = _np.asarray(boot, float)
        blo, bhi = _np.percentile(b, [2.5, 97.5])
        pure = float(max(b.std(ddof=1) ** 2 - v.std(ddof=1) ** 2, 0.0)) ** 0.5
        ln.append("  %-10s %s  **표본** 95%% [%+.5f, %+.5f] 폭 %.5f  순수 표본 SD %.5f"
                  % ("", " " * 8, blo, bhi, bhi - blo, pure))
        ln.append("    %s (표본) — **표본 성분은 씨앗을 늘려도 안 줄어든다**"
                  % ("**0 을 문다**" if blo < 0 < bhi else "**0 밖**"))
    if paired is None:
        ln.append("    ⚠ **`paired` 를 안 적었다** --- 씨앗 폭은 팔 설계가 정한다"
                  "(짝지으면 약 %.0f배 좁다, 노트 610). 무엇을 잰 구간인지 못 읽는다."
                  % PAIR_GAIN)
    elif paired:
        ln.append("    ⚠ **짝지은 팔이다**(같은 적합·예측 때만 가림) --- 씨앗 구간이"
                  " 약 %.0f배 좁다. **좁은 것이 확실함이 아니다.**" % PAIR_GAIN)
    else:
        ln.append("    **따로 적합한 팔이다** --- 씨앗 잡음이 상쇄되지 않는다."
                  " 채택은 언제나 이쪽이다(노트 610).")
    if boot is None:
        ln.append("    ⚠ **표본 구간을 안 냈다** --- 이 구간은 '다시 적합하면 같은 답'"
                  "(재현성)이지 '다른 표본이었어도 같은 답'(일반화)이 아니다(노트 608).")
    return "\n".join(ln)


def boot_ci(p1, p2, y, B: int = CI_B, seed: int = 7):
    """**유보 행을 다시 뽑았을 때의 구간**을 낸다(노트 608).

    ``p1`` 은 원 예보, ``p2`` 는 축을 가린 예보, ``y`` 는 라벨이다.
    돌려주는 것은 ``(평균, 표본 SE, lo, hi)`` --- ρ 차의 부트스트랩
    분포다.

    **씨앗 스프레드와 다른 것을 잰다.** 씨앗은 ``다시 적합하면 같은 답이
    나오나``(재현성)이고 이것은 ``다른 표본이었어도 같은 답이 나왔나``
    (일반화)다. 도메인 수준에서 **표본 SE 가 씨앗 SE 의 12.6 배**(중앙,
    축-도메인 42짝)라, 씨앗 스프레드를 신뢰구간으로 읽으면 **열두 배
    과신한다**.
    """
    import numpy as _np
    from scipy.stats import spearmanr as _sp
    p1 = _np.asarray(p1, float); p2 = _np.asarray(p2, float)
    y = _np.asarray(y, float)
    ok = _np.isfinite(y) & _np.isfinite(p1) & _np.isfinite(p2)
    p1, p2, y = p1[ok], p2[ok], y[ok]
    n = len(y)
    if n < 20:
        return (float("nan"),) * 4
    idx = _np.random.default_rng(seed).integers(0, n, size=(B, n))
    bs = _np.empty(B)
    for b in range(B):
        i = idx[b]
        bs[b] = _sp(p1[i], y[i]).correlation - _sp(p2[i], y[i]).correlation
    lo, hi = _np.percentile(bs, [2.5, 97.5])
    return float(bs.mean()), float(bs.std(ddof=1)), float(lo), float(hi)


def ci_keep(cis: dict, what: str = "구간") -> str:
    """**구간으로 자른다** --- 행수 문턱(`trim_small`)을 대신한다(노트 608).

    ``cis`` 는 ``{도메인: (평균, lo, hi)}`` 다. **0 을 무는 도메인을 빼고**
    남은 것으로 구간을 낸다.

    노트 607 이 만든 `trim_small` 은 **행수**로 잘랐다. 42짝에서 그 자를
    실제 부트스트랩 구간과 견주니

    * 유보 200 **이상** 24짝 중 구간이 0 밖인 것은 **9** --- **15개가
      위양성**이다(웹툰 650행 `target_breadth` +0.0282 가 0 을 문다).
    * 유보 200 **미만** 18짝 중 **2개가 진짜**다(아이돌 51행
      `venue_prominence` +0.280 [+0.103,+0.482] · 게임 180행 `media_push`).

    표본 SE 는 $0.70/\\sqrt{n}$ 을 잘 따르지만(크기↔SE 순위상관 -0.749)
    **효과 크기는 행수와 무관**하므로 비가 뒤집힌다. **행수는 SE 를
    통해서만 판정에 닿는다.**

    미리 적는 한계: 남은 값은 **유의성 위 선택**이라 위로 부푼다. 그리고
    부트스트랩이 행을 독립으로 보므로 같은 IP 가 여러 행이면 구간이
    실제보다 좁다.
    """
    keep = {d: v for d, v in cis.items() if not (v[1] < 0 < v[2])}
    drop = {d: v for d, v in cis.items() if d in cis and d not in keep}
    mu = [v[0] for v in cis.values()]
    ln = ["  %s 전체 n=%d  [%+.4f, %+.4f]" % (what, len(cis), min(mu), max(mu))]
    if keep:
        k = [v[0] for v in keep.values()]
        ln.append("  %s **구간이 0 밖** n=%d  [%+.4f, %+.4f]"
                  % (what, len(keep), min(k), max(k)))
    else:
        ln.append("  ⚠ **0 밖인 도메인이 없다 --- 구간을 못 낸다**")
    if drop:
        ln.append("  ⚠ **0 을 무는 도메인**(뺐다) — %s" % " · ".join(
            "%s %+.4f[%+.4f,%+.4f](%d행)" % (d, v[0], v[1], v[2], POST_N.get(d, 0))
            for d, v in sorted(drop.items(), key=lambda kv: -abs(kv[1][0]))))
    ln.append("    남은 값은 **유의성 위 선택**이라 위로 부푼다(노트 608).")
    return "\n".join(ln)


def bare_rows(data=None, T: float = 2025.0) -> list:
    """⑤ **손 축이 하나도 없는 유보 행**을 **전 도메인**에서 센다(노트 603).

    ``guards.g_bare`` 가 이미 있는데 그것은 ``tgt=PRIMARY``(팝업) **한
    도메인만** 본다 --- 노트 174 가 팝업에서 겪은 사고를 막으려고 만든
    것이라 그렇다. 전 도메인으로 돌리니 **아이돌에도 2행이 있었다**
    (유보 51 중 3.9%). 아홉 도메인은 정확히 0 이다.

    그 행들은 **예보가 도메인 상수**라 채점에서 서로 동점이고, 그만큼
    ``rho`` 를 깎는다. 노트 602 가 팝업 7행의 값을 쟀다 --- 그 7행에
    완벽 예보를 주면 팝업이 $+0.3831 \to +0.5274$ 이고 판으로 $+0.00278$
    이다(이 판이 이번 세션에 채택한 것보다 크다).

    **가드가 한 도메인만 보면 나머지 열은 안 보인다.** 노트 598 의
    ``가드는 불려야 가드다`` 에 하나 더 --- **가드는 전부를 봐야 가드다.**
    """
    from . import forms
    if data is None:
        data = champion_data()
    out = []
    for dom in sorted(data.dom):
        names = list(data.names[dom])
        js = [names.index(a) for a in forms.ALL5 if a in names]
        if not js:
            continue
        k = (np.isfinite(data.yr[dom]) & (data.yr[dom] >= T)
             & np.isfinite(data.dom[dom][2]))
        if k.sum() < 20:
            continue
        _A, M, y, _t = data.slice(dom, k)
        ok = np.isfinite(y)
        n0 = int(((M[ok][:, js] > 0).sum(axis=1) == 0).sum())
        out.append((n0 / max(int(ok.sum()), 1), dom, n0, int(ok.sum())))
    return sorted(out, reverse=True)


AGREE_HIT = 0.70         # 부호 일치율이 이보다 낮으면 **공유 축이 아니다**

# **이름표 열은 채점하지 않는다**(노트 589). ``grp`` 는 도메인마다 *다른
# 것*을 담는다 --- 웹툰은 연령등급 · 모바일은 무료 여부 · 애니는 매체 ·
# 만화는 국가 · 펀딩은 카테고리(``grpaxes.SPEC``). 공유 눈금이 아니라
# **행을 집단으로 묶는 통로**이므로(노트 138 바닥선), 도메인 사이에서
# 부호가 같아야 할 이유가 없다. 이 자를 걸면 일치율 71% · 가중 -0.1625 로
# ``강한데 갈린다'' 처럼 보이는데 **범주 오류다.**
#
# ``gen`` 은 반대다 --- 노트 419 가 **도메인 사이에서 눈금을 공유하는**
# 범주로 설계했고, 실제로 일치율 100%(5/5 음수)다. 그래서 채점한다.
NOMINAL = ("grp", "SPEC", "SEASON")

# **도메인이 여섯 미만이면 다수결이 아니다**(노트 439 · 590). 노트 439 가
# LODO 에서 "문턱 통과 도메인이 여섯 미만이면 다수결이 성립하지 않는다 ---
# `잴 수 없음' 이다" 를 세웠는데, 이 자에는 안 붙어 있었다. 달력은 도메인이
# **셋뿐**이라 일치율 67% 가 **2 대 1** 이고, 셋 중 하나가 부호가 다를
# 우연 확률은 0.75 다 --- 갈렸다고 부를 수 없다.
#
# 도메인 n 개에서 소수 부호가 m 개일 때 "동전이라면" 확률은 이항분포다.
# ``p_split`` 로 같이 적고, ``MIN_DOMS`` 아래면 **판정을 보류**한다.
MIN_DOMS = 6


def shared_sign(data=None, axes=None, oriented=None) -> list:
    """④ **공유 축의 부호가 도메인마다 같은가**(노트 581).

    노트 544 가 "공유 축은 도메인 사이에서 뜻이 같아야 한다" 를 세웠는데
    그것을 재는 검사가 없었다. 넣는다.

    .. warning::

       **하네스 열을 원 축으로 읽지 않는다.** ``data/state/axis_orient.json``
       이 ``값 -> 1-값`` 으로 뒤집힌 (축, 도메인) 을 적어 두고 있고
       (노트 108 채택 · 노트 160 기록), 그것을 안 보면 부호가 **가짜로**
       갈려 보인다. ``entry_friction`` 이 하네스 열에서 일치율 50% 인데
       되돌리면 88% 다 --- **노트 155~159 가 다섯 번, 노트 581 이 여섯
       번째로 밟았다.** 그래서 이 함수는 **두 줄을 다 낸다.**
    """
    import json as _j
    from pathlib import Path as _P
    if data is None:
        data = champion_data()
    from . import forms, fixaxes
    op = _P("data/state/axis_orient.json")
    orient = _j.loads(op.read_text()) if op.exists() else {}
    # **되돌린 자료면 두 줄의 이름이 바뀐다**(노트 583). ``axis_orient.json``
    # 은 *원 자료*가 뒤집혀 있다는 기록이라 영원히 참이지만, ``fixaxes.orient``
    # 를 거친 자료에서는 **하네스 열이 곧 원 방향**이다. 그것을 안 적으면
    # 다음 사람이 두 줄을 거꾸로 읽는다 --- 노트 160 이 파일을 만들어 두고도
    # 여섯 번 밟힌 것과 같은 자리다.
    if oriented is None:
        oriented = bool(getattr(fixaxes, "ORIENT_HITS", None))
    applied = set(getattr(fixaxes, "ORIENT_FIX", ())) if oriented else set()
    out = []
    for ax in (axes if axes is not None else forms.ALL5):
        if ax in NOMINAL:
            continue
        flipped = set(orient.get(ax) or [])
        rows = []
        for dom in sorted(data.dom):
            k = (np.isfinite(data.yr[dom]) & (data.yr[dom] < 2025.0)
                 & np.isfinite(data.dom[dom][2]))
            if k.sum() < 20:
                continue
            names = list(data.names[dom])
            if ax not in names:
                continue
            j = names.index(ax)
            A, M, y, _t = data.slice(dom, k)
            yr = data.yr[dom][k]
            ok = (M[:, j] > 0) & np.isfinite(y)
            if ok.mean() < 0.05 or ok.sum() < 20:
                continue
            r = _part(A[ok, j], y[ok], yr[ok])
            if not np.isfinite(r):
                continue
            rows.append((dom, float(r), int(k.sum()), dom in flipped))
        if len(rows) < 3:
            continue
        lab_now, lab_raw = (("하네스 열(=원 방향)", "뒤집힌 원자료")
                            if ax in applied else ("하네스 열", "원 방향"))
        # 첫 줄은 **자료를 있는 그대로**(모형이 보는 것) 채점하고, 둘째 줄은
        # 뒤집기 표를 적용해 채점한다. ``applied`` 는 **이름만** 바꾼다.
        for label, orig in ((lab_now, False), (lab_raw, True)):
            vals = [(-r if (orig and f) else r) for _d, r, _n, f in rows]
            pos = sum(1 for v in vals if v > 0)
            agree = max(pos, len(vals) - pos) / len(vals)
            w = np.array([n for _d, _r, n, _f in rows], float)
            w /= w.sum()
            # 동전이라면 이만큼 갈릴 확률(양측). 도메인이 적으면 크다.
            n_, k_ = len(vals), min(pos, len(vals) - pos)
            p_split = sum(_comb(n_, i) for i in range(k_ + 1)) / (2.0 ** n_) * 2
            out.append((agree, ax, label, n_, pos, n_ - pos,
                        float((w * np.array(vals)).sum()),
                        sorted(flipped), min(p_split, 1.0), n_ < MIN_DOMS))
    return sorted(out)


def baseline_ratio(ratio: float, name: str, n_candidates: int,
                   n_holdout: int | None = None) -> str:
    """**기준선 대비 비를 낼 때 경고를 같이 낸다**(노트 584).

    노트 580 이 '통합 / 전용 = 1.67배' 를 내고 **덱에 실었다**. 전용 쪽
    손잡이 후보가 **넷**이었다. 스물여덟로 넓히니 시장팝업이 13.85 -> 1.07,
    아이돌이 1.36 -> 0.92 로 뒤집혔다 --- **비를 정한 것은 모형이 아니라
    기준선에 준 노력이었다.**

    같은 함정을 이 판에서 네 번째로 만난다(548 상한->기대값 · 560 전역
    표->단일 이득 · 568 유보 기준선->상한 · **584 인색한 기준선->비**).
    앞의 셋과 달리 이번 것은 **밖으로 나간 문서**에 실렸다.

    쓰는 법::

        print(sideaudit.baseline_ratio(1.67, "통합 / 전용", 4, 3369))

    ``n_candidates`` 가 여덟 아래면 **비를 적지 말고 차를 적으라**고 한다 ---
    작은 기준선이 0 근처면 비가 발산한다(시장팝업 전용 +0.0113 이 13.85 배를
    만들었다).
    """
    msg = ["  ⚠ **비는 기준선에 준 노력이 정한다**(노트 584) — "
           "%s = %.2f배, 기준선 후보 %d개." % (name, ratio, n_candidates)]
    if n_candidates < 8:
        msg.append("    후보가 여덟 아래다. **넓히면 비가 뒤집힐 수 있다** — "
                   "노트 580 은 넷으로 1.67배를 냈고 스물여덟에서 무너졌다.")
    if ratio > 3.0:
        msg.append("    비가 3 을 넘는다. 기준선이 0 근처면 발산한다 — "
                   "**비 대신 차를 적는다.**")
    if n_holdout is not None and n_holdout < 200:
        msg.append("    유보 %d행. 도메인 하나의 비는 이 크기에서 씨앗 잡음과 "
                   "구별이 안 된다(노트 562)." % n_holdout)
    msg.append("    적을 때 **기준선의 후보 수와 고른 방법을 같이 적는다.**")
    return "\n".join(msg)


def audit(data=None) -> dict:
    if data is None:
        data = champion_data()
    from .trendaxes import _ids
    ids_all = _ids()
    RF = {"웹툰": "webtoon_records.json", "만화": "manga_records.json",
          "애니": "anime_records.json", "세계애니": "wanime_records.json"}
    recmap = {d: _records(f) for d, f in RF.items()}
    return {"사후 상태": post_state(data, ids_all, recmap),
            "틀린 날짜": bad_date(recmap),
            "수집 순서": collect_order(data),
            "공유 축 부호": shared_sign(data),
            "맨몸 행": bare_rows(data)}


def _main() -> None:
    import warnings
    warnings.filterwarnings("ignore")
    a = audit()
    print("=== ① 사후 상태를 읽는 축 (|상관| >= %.2f, 연도 통제) ==="
          % POST_HIT)
    if not a["사후 상태"]:
        print("  없음")
    for _, dom, ax, fl, r in a["사후 상태"][:10]:
        print("  %-8s %-18s ↔ %-12s %+.4f" % (dom, ax, fl, r))
    print("\n=== ② 시작일이 물리적으로 불가능한 행 (>= %.1f%%) ==="
          % (100 * RATE_HIT))
    if not a["틀린 날짜"]:
        print("  없음")
    for row in a["틀린 날짜"]:
        p, dom, n, tot, fl = row[:5]
        done = row[5] if len(row) > 5 else ""
        print("  %-8s %4d/%5d (%.1f%%)  플래그 배수 %s" % (dom, n, tot, 100 * p, fl))
        if done:
            print("    %s" % done)
    if a["틀린 날짜"] and all((len(r) > 5 and r[5].startswith("**"))
                            for r in a["틀린 날짜"]):
        print("  ⚠ **걸린 것이 전부 이미 처리된 것이다 — 새것 없음**(노트 615).")
    print("\n=== ③ 수집 순서가 마스크에 실린 축 (차 >= %.0f%%p) ==="
          % (100 * GAP_HIT))
    if not a["수집 순서"]:
        print("  없음")
    print("  %-8s %-6s %8s %8s %11s %8s  %s" % ("도메인", "무리", "학습", "유보",
                                                "마스크↔라벨", "곱", "처리"))
    for sc, dom, f, ct, ch, r, hd in a["수집 순서"][:10]:
        print("  %-8s %-6s %7.0f%% %7.0f%% %+11.4f %8.3f  %s"
              % (dom, f, 100 * ct, 100 * ch, r, sc,
                 ("**%s 로 처리됨**" % hd) if hd else ""))
    live = [x for x in a["수집 순서"] if not x[6]]
    chase = [x for x in live if x[0] >= CHASE_HIT]
    print("\n  **아직 안 고친 것 %d개** (그중 곱 >= %.2f 인 것 **%d개**)%s"
          % (len(live), CHASE_HIT, len(chase),
             ("" if not chase else " — 제일 큰 것: %s %s (곱 %.3f)"
              % (chase[0][1], chase[0][2], chase[0][0]))))
    if live and not chase:
        print("  ⚠ **남은 것이 전부 곱 %.2f 아래다 — 안 쫓는다**(노트 593). "
              "웹툰 0.043 을 실제로 돌려 **기각**했다" % CHASE_HIT)
        print("    (판 -0.0087~-0.0105 · 웹툰 -0.026~-0.028, 팔 둘 다 0/12). "
              "애니 0.200 · 만화 0.072 는 채택이었다.")

    print("\n=== ④ 공유 축의 부호가 도메인마다 같은가 (일치율 < %.0f%% 면 걸림) ==="
          % (100 * AGREE_HIT))
    print("  ⚠ **하네스 열을 원 축으로 읽지 않는다**(노트 581) — "
          "axis_orient.json 이 뒤집어 둔 곳이 있다. 두 줄을 다 본다.")
    print("  %-18s %-10s %5s %5s %5s %9s %9s %7s  %s"
          % ("축", "읽는 법", "도메인", "양", "음", "일치율", "가중평균",
             "동전확률", "판정"))
    for row in a["공유 축 부호"]:
        agree, ax, label, n, pos, neg, wm, flipped = row[:8]
        ps, thin = (row[8], row[9]) if len(row) > 9 else (float("nan"), False)
        verdict = ("**도메인 %d개 — 잴 수 없음**" % n if thin
                   else ("**갈린다**" if agree < AGREE_HIT else ""))
        print("  %-18s %-10s %5d %5d %5d %8.0f%% %+9.4f %6.2f  %s"
              % (ax, label, n, pos, neg, 100 * agree, wm, ps, verdict))
    bad = [x for x in a["공유 축 부호"]
           if x[0] < AGREE_HIT and not (len(x) > 9 and x[9])
           and x[2].startswith("원 방향")]
    print("\n  **원 방향에서도 갈리는 축 %d개**%s" % (len(bad),
          "" if not bad else " — " + ", ".join(
              "%s(%.0f%%)" % (x[1], 100 * x[0]) for x in bad)))

    print("\n=== ⑤ 손 축이 하나도 없는 유보 행 (전 도메인 · >= %.0f%%) ==="
          % (100 * BARE_HIT))
    br = a.get("맨몸 행") or []
    hit = [x for x in br if x[0] >= BARE_HIT]
    if not hit:
        print("  없음")
    for p_, dom, n0, tot in hit:
        print("  %-8s %3d/%4d (%.1f%%)  ← 예보가 상수라 채점에서 동점"
              % (dom, n0, tot, 100 * p_))
    if hit:
        print("  ⚠ `guards.g_bare` 는 **팝업 한 도메인만** 본다(노트 603). "
              "여기는 전 도메인이다.")
        print("    노트 602: 팝업 7행에 완벽 예보를 주면 "
              "+0.3831 -> +0.5274, 판 +0.00278.")


if __name__ == "__main__":
    _main()
