"""2단계 — **위험률의 기후값**을 먼저 잰다. 🔴 모형은 안 짓는다.

제품 출력 ③(*「언제 어떤 불특정 이벤트가 발생할지」*)의 **바닥**을 깐다.

    간격 분포        (도메인, 종류) 별 다음 이벤트까지의 일수 — 중앙·10~90분위
    기후값 기준선    규약 43 · 노트 792 — 「아무 조건 없이 그 **도메인**의 중앙값을 늘 말한다」
    조건부           「그 **(도메인, 종류)** 의 중앙값을 말한다」
    덮음             10~90분위 구간이 실제로 몇 %를 덮나 (도메인 층 · 종류 층)
    전이 표          종류 X 다음에 종류 Y 가 오는 경험적 표
    selectivity      🔴 시각을 개체 안에서 섞어도 같은 전이 표가 나오면 그 표는 자료와 무관하다

🔴 잡음 단위는 씨앗이 아니라 **개체**다(노트 897·899). 구간은 `lab/pairboot.cluster_boot`
(BCa · 규약 47)로 낸다. 못 부르면 **폴백 사유를 명기**한다.
🔴 첫 양수를 그대로 채택하지 않는다(노트 133) — 음성 대조 · 누설 점검 · 도메인 분해를 같이 낸다.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict

import numpy as np

from .sources import _parse_day


def _day(x):
    d = _parse_day(str(x)[:10])
    return d


def gaps_by_entity(events, *, only_material: bool | None = None):
    """(개체, 종류) 별 연속 이벤트 간격(일). 🔴 시간 게이트 통과 행만."""
    seq = defaultdict(list)
    for e in events:
        if e.get("사후_동일시각"):
            continue
        if only_material is not None and e.get("물질") is not None:
            if bool(e["물질"]) != only_material:
                continue
        d = _day(e["t_occur"])
        if d is None:
            continue
        seq[(e["개체"], e["도메인"], e["종류"])].append((d, e.get("일차")))
    out = []
    for (ent, dom, kind), ds in seq.items():
        ds.sort(key=lambda x: x[0])
        for i in range(1, len(ds)):
            g = (ds[i][0] - ds[i - 1][0]).days
            if g <= 0:
                continue
            out.append({"개체": ent, "도메인": dom, "종류": kind, "gap": g,
                        "t": ds[i - 1][0].isoformat(),
                        #: 🔴 예측 시점(t_k)에 이미 아는 값만 조건으로 쓴다
                        "일차": ds[i - 1][1]})
    return out


#: 🔴 진단용 구간 — 값을 보기 전에 정했다(개봉 주 · 2주 · 4주 · 8주 · 그 뒤)
NTH_BINS = [(None, "일차 모름"), (7, "0~6일"), (14, "7~13일"), (28, "14~27일"),
            (56, "28~55일"), (10 ** 9, "56일+")]


def nth_bin(n):
    if n is None:
        return "일차 모름"
    for hi, name in NTH_BINS[1:]:
        if n < hi:
            return name
    return "56일+"


def split(entities, frac=0.7, salt="910"):
    """🔴 개체 단위 홀드아웃. 행 단위로 나누면 같은 개체가 양쪽에 든다(누설)."""
    tr, ho = set(), set()
    for e in entities:
        h = int(hashlib.sha256((salt + str(e)).encode()).hexdigest()[:8], 16)
        (tr if (h % 100) < int(frac * 100) else ho).add(e)
    assert not (tr & ho), "🔴 W-G 누설 — 학습 개체와 홀드아웃 개체가 겹친다"
    return tr, ho


def _med(xs):
    return float(np.median(xs)) if len(xs) else float("nan")


def climate_vs_conditional(gaps, *, frac=0.7, salt="910", kind_shuffle_seed=None):
    """기후값(도메인 중앙값) 대 조건부((도메인,종류) 중앙값). 🔴 중앙값은 학습 쪽에서만."""
    rng = np.random.default_rng(0 if kind_shuffle_seed is None else kind_shuffle_seed)
    g = [dict(x) for x in gaps]
    if kind_shuffle_seed is not None:
        #: 🔴 음성 대조 — 종류 라벨을 섞는다. 이득이 「조건」이 아니라 분할 자유도에서 오나
        ks = [x["종류"] for x in g]
        rng.shuffle(ks)
        for x, k in zip(g, ks):
            x["종류"] = k
    ents = {x["개체"] for x in g}
    tr, ho = split(ents, frac, salt)
    trg = [x for x in g if x["개체"] in tr]
    hog = [x for x in g if x["개체"] in ho]
    if not trg or not hog:
        return {"상태": "🔴 못 잰다 — 학습 또는 홀드아웃이 비었다",
                "학습 간격": len(trg), "홀드아웃 간격": len(hog)}

    dom_med = {d: _med([x["gap"] for x in trg if x["도메인"] == d])
               for d in {x["도메인"] for x in trg}}
    kind_med = {}
    for x in trg:
        kind_med.setdefault((x["도메인"], x["종류"]), []).append(x["gap"])
    kind_med = {k: _med(v) for k, v in kind_med.items()}
    global_med = _med([x["gap"] for x in trg])

    rows, ents_ho = [], []
    n_backoff = 0
    for x in hog:
        pc = dom_med.get(x["도메인"], global_med)
        pk = kind_med.get((x["도메인"], x["종류"]))
        if pk is None or not np.isfinite(pk):
            pk = pc                       # 🔴 학습에 그 종류가 없으면 기후값으로 후퇴
            n_backoff += 1
        rows.append((abs(x["gap"] - pc), abs(x["gap"] - pk)))
        ents_ho.append(x["개체"])
    arr = np.asarray(rows, float)
    imp = arr[:, 0] - arr[:, 1]           # + 면 조건부가 이긴다

    res = {
        "학습 간격 수(분모)": len(trg), "홀드아웃 간격 수(분모)": len(hog),
        "학습 개체 수": len(tr), "홀드아웃 개체 수": len(ho),
        "🔴 W-G 누설 점검(학습∩홀드아웃)": 0,
        "기후값 규칙": "그 도메인의 학습 간격 중앙값을 늘 말한다(규약 43 · 노트 792)",
        "기후값 중앙값(학습)": dom_med,
        "조건부 규칙": "그 (도메인, 종류) 의 학습 간격 중앙값을 말한다",
        "🔴 학습에 그 종류가 없어 기후값으로 후퇴한 홀드아웃 행": n_backoff,
        "기후값 MAE": float(arr[:, 0].mean()), "조건부 MAE": float(arr[:, 1].mean()),
        "기후값 MedAE": float(np.median(arr[:, 0])),
        "조건부 MedAE": float(np.median(arr[:, 1])),
        "개선(MAE, 기후−조건부)": float(imp.mean()),
        "개선율": (float(imp.mean() / arr[:, 0].mean())
                if arr[:, 0].mean() > 0 else None),
    }
    res["_imp"] = imp
    res["_ents"] = ents_ho
    res["_hog"] = hog
    res["_dom_med"] = dom_med
    res["_kind_med"] = kind_med
    res["_trg"] = trg
    return res


def boot_improvement(imp, ents, *, B=2000, seed=910):
    """개체 군집 BCa(규약 47). 🔴 못 부르면 폴백 사유를 명기한다."""
    idx = defaultdict(list)
    for i, e in enumerate(ents):
        idx[e].append(i)
    clusters = [np.asarray(v, int) for v in idx.values()]
    vals = np.asarray(imp, float)
    try:
        from lab.pairboot import cluster_boot, verdict
        th, lo, hi, kind = cluster_boot(lambda ix: float(vals[ix].mean()),
                                        clusters, B=B, seed=seed)
        v = verdict(lo, hi)
        return {"점추정": float(th), "lo": float(lo), "hi": float(hi), "구간 종류": kind,
                "판정": v, "군집(개체) 수": len(clusters), "행": len(vals),
                "B": B, "🔴 폴백 사유": None}
    except Exception as ex:                                     # noqa: BLE001
        rng = np.random.default_rng(seed)
        nC = len(clusters)
        bs = np.empty(B)
        for b in range(B):
            pick = rng.integers(0, nC, nC)
            bs[b] = vals[np.concatenate([clusters[i] for i in pick])].mean()
        return {"점추정": float(vals.mean()),
                "lo": float(np.percentile(bs, 2.5)), "hi": float(np.percentile(bs, 97.5)),
                "구간 종류": "percentile(폴백)", "군집(개체) 수": nC, "행": len(vals),
                "B": B,
                "🔴 폴백 사유": f"lab.pairboot.cluster_boot 를 못 썼다 — {type(ex).__name__}: {ex}"}


def coverage(res, *, lo_q=10, hi_q=90):
    """10~90분위 구간의 **실측 덮음**. 두 층으로 낸다(노트 792 형)."""
    trg, hog = res["_trg"], res["_hog"]
    dom_iv, kind_iv = {}, {}
    for x in trg:
        dom_iv.setdefault(x["도메인"], []).append(x["gap"])
        kind_iv.setdefault((x["도메인"], x["종류"]), []).append(x["gap"])
    dom_iv = {k: (float(np.percentile(v, lo_q)), float(np.percentile(v, hi_q)), len(v))
              for k, v in dom_iv.items()}
    kind_iv = {k: (float(np.percentile(v, lo_q)), float(np.percentile(v, hi_q)), len(v))
               for k, v in kind_iv.items()}
    out = {"명목 덮음": (hi_q - lo_q) / 100.0, "분위": [lo_q, hi_q]}
    for name, table, keyf in (("도메인 구간", dom_iv, lambda x: x["도메인"]),
                              ("종류 구간", kind_iv, lambda x: (x["도메인"], x["종류"]))):
        hit = tot = miss_key = 0
        per = Counter()
        per_tot = Counter()
        for x in hog:
            iv = table.get(keyf(x))
            if iv is None:
                miss_key += 1
                continue
            tot += 1
            ok = iv[0] <= x["gap"] <= iv[1]
            hit += int(ok)
            per[(str(keyf(x)), "덮음")] += int(ok)
            per_tot[str(keyf(x))] += 1
        out[name] = {
            "실측 덮음": (hit / tot) if tot else None,
            "덮인 행": hit, "홀드아웃 행(분모)": tot,
            "🔴 학습에 그 열쇠가 없어 못 잰 행": miss_key,
            "🔴 합 == 홀드아웃 전체(assert)": (tot + miss_key) == len(hog),
            "구간(학습)": {str(k): {"lo": v[0], "hi": v[1], "학습 행": v[2]}
                       for k, v in table.items()},
            "열쇠별 덮음": {k: (per[(k, "덮음")] / v if v else None)
                       for k, v in per_tot.items()},
        }
        assert (tot + miss_key) == len(hog), f"{name}: 합 != 홀드아웃 전체"
    return out


# ---------------------------------------------------------------- 전이 표
def _count_trans(pairs):
    """🔴 (날짜, 종류) 로 **결정적으로** 정렬한다 — 같은 날 동시 발생의 순서가
    삽입 순서에 좌우되면 그 표는 자료가 아니라 파일 순서를 잰다."""
    lst = sorted(pairs, key=lambda x: (x[0], x[1]))
    tab, n, same = Counter(), 0, 0
    for i in range(1, len(lst)):
        tab[(lst[i - 1][1], lst[i][1])] += 1
        n += 1
        same += int(lst[i - 1][0] == lst[i][0])
    return tab, n, same


def transition_table(events):
    """개체 안에서 시각 순으로 종류 X → 종류 Y. 🔴 시간 게이트 통과 행만."""
    seq = defaultdict(list)
    for e in events:
        if e.get("사후_동일시각"):
            continue
        d = _day(e["t_occur"])
        if d is None:
            continue
        seq[e["개체"]].append((d, e["종류"]))
    tab, n, same = Counter(), 0, 0
    for ent, lst in seq.items():
        t, m, s = _count_trans(lst)
        tab.update(t)
        n += m
        same += s
    return tab, n, seq, same


def _tvd(tab, n):
    """실측 전이 표와 **주변곱**(독립) 표 사이의 총변동거리."""
    if n == 0:
        return float("nan")
    row = Counter()
    col = Counter()
    for (a, b), c in tab.items():
        row[a] += c
        col[b] += c
    s = 0.0
    keys = {(a, b) for a in row for b in col}
    for a, b in keys:
        p = tab.get((a, b), 0) / n
        q = (row[a] / n) * (col[b] / n)
        s += abs(p - q)
    return 0.5 * s


def permutation_selectivity(events, *, n_perm=1000, seed=910):
    """🔴 라벨 순열 selectivity — 개체 안에서 `t_occur` 을 무작위로 재배정한다.

    개체별 시각 다중집합은 보존하고 **종류-시각 짝만** 깬다. 전이 표의 총변동거리가
    귀무 분포의 어디에 있나. p ≥ 0.05 면 **그 표는 자료와 무관**하다.
    """
    tab, n, seq, same = transition_table(events)
    obs = _tvd(tab, n)
    rng = np.random.default_rng(seed)
    ents = [([d for d, _ in v], [k for _, k in v])
            for v in seq.values() if len(v) >= 2]
    null = np.empty(n_perm)
    for p in range(n_perm):
        t, m = Counter(), 0
        for days, kinds in ents:
            #: 🔴 개체 안에서 `t_occur` 을 무작위 재배정 — 시각 다중집합은 보존하고
            #: **종류-시각 짝만** 깬다(사전등록 §6.3)
            perm = rng.permutation(len(days))
            tt, mm, _ = _count_trans([(days[perm[i]], kinds[i]) for i in range(len(days))])
            t.update(tt)
            m += mm
        null[p] = _tvd(t, m)
    pval = float((1 + np.sum(null >= obs)) / (n_perm + 1))
    return {
        "전이 수(분모)": n, "전이 표 칸 수": len(tab),
        "같은 날 전이 수": same,
        "같은 날 전이 비율": (same / n) if n else None,
        "⚠ 같은 날 전이의 순서": "🔴 (날짜, 종류) 알파벳 순으로 결정적으로 정했다 — "
                        "같은 날 동시 발생의 진짜 순서는 저장소에 **없다**",
        "실측 총변동거리": obs,
        "귀무 평균": float(np.mean(null)), "귀무 SD": float(np.std(null)),
        "귀무 95분위": float(np.percentile(null, 95)),
        "순열 수": n_perm, "p": pval,
        "판정": ("🔴 발화 — 전이 표는 자료와 무관하지 않다" if pval < 0.05
               else "🔴 안 발화 — 전이 표를 「자료와 무관」 딱지를 달아 싣는다"),
        "전이 표(상위 40)": {f"{a} → {b}": c
                        for (a, b), c in sorted(tab.items(), key=lambda kv: -kv[1])[:40]},
        "전이 표 전량": {f"{a} → {b}": c for (a, b), c in sorted(tab.items())},
    }


# ------------------------------------------------- 🔴 진단 (판정 미사용)
def diag_nth_conditional(gaps, *, frac=0.7, salt="910"):
    """🔴 **판정에 안 쓴다**(사전등록에 없다). 「③ 을 0 에서 올리려면 무엇이 필요한가」의 답을
    수로 적기 위한 진단 하나 — (도메인, 종류) 에 **개봉 후 일차 구간**을 더하면 달라지나.

    조건은 **예측 시점 t_k 에 이미 아는 값**만 쓴다(누설 없음).
    """
    ents = {x["개체"] for x in gaps}
    tr, ho = split(ents, frac, salt)
    trg = [x for x in gaps if x["개체"] in tr]
    hog = [x for x in gaps if x["개체"] in ho]
    if not trg or not hog:
        return {"상태": "🔴 못 잰다 — 학습 또는 홀드아웃이 비었다"}
    dom_med, kd_med, kdn_med = {}, {}, {}
    for x in trg:
        dom_med.setdefault(x["도메인"], []).append(x["gap"])
        kd_med.setdefault((x["도메인"], x["종류"]), []).append(x["gap"])
        kdn_med.setdefault((x["도메인"], x["종류"], nth_bin(x.get("일차"))), []).append(x["gap"])
    dom_med = {k: _med(v) for k, v in dom_med.items()}
    kd_med = {k: _med(v) for k, v in kd_med.items()}
    kdn_n = {k: len(v) for k, v in kdn_med.items()}
    kdn_med = {k: _med(v) for k, v in kdn_med.items()}
    gm = _med([x["gap"] for x in trg])
    e0, e2, backoff = [], [], 0
    for x in hog:
        pc = dom_med.get(x["도메인"], gm)
        k3 = (x["도메인"], x["종류"], nth_bin(x.get("일차")))
        p3 = kdn_med.get(k3)
        if p3 is None or not np.isfinite(p3):
            p3 = kd_med.get((x["도메인"], x["종류"]), pc)
            backoff += 1
        e0.append(abs(x["gap"] - pc))
        e2.append(abs(x["gap"] - p3))
    e0, e2 = np.asarray(e0, float), np.asarray(e2, float)
    imp = e0 - e2
    out = {
        "🔴 이 절은 판정에 안 쓴다": "사전등록 §6 의 자가 아니다 — 진단이다",
        "조건": "(도메인, 종류, 개봉 후 일차 구간)",
        "홀드아웃 간격 수(분모)": int(e0.size),
        "기후값 MAE": float(e0.mean()), "진단 조건부 MAE": float(e2.mean()),
        "개선(MAE)": float(imp.mean()),
        "개선율": float(imp.mean() / e0.mean()) if e0.mean() > 0 else None,
        "🔴 학습에 그 칸이 없어 후퇴한 행": backoff,
        "일차 구간별 학습 행": {str(k): v for k, v in sorted(kdn_n.items(), key=lambda kv: str(kv[0]))},
        "일차 구간별 학습 중앙값": {str(k): v for k, v in sorted(kdn_med.items(), key=lambda kv: str(kv[0]))},
    }
    out["_imp"] = imp
    out["_ents"] = [x["개체"] for x in hog]
    return out


def transition_dayset(events, *, n_perm=200, seed=910):
    """🔴 보조 진단 — **순서 인공물이 없는** 전이 표.

    같은 날 동시 발생의 순서는 저장소에 **없다**. 그래서 「종류 → 종류」 표는
    (날짜, 종류) 정렬이 순서를 **만들어 낸다**(실측: 초판의 `다른 날 전이만` 표에서
    스크린수→상영횟수 80,070 대 반대 269 — 이건 자료가 아니라 정렬이다).

    그래서 단위를 **하루의 종류 집합**으로 올린다: 개체의 연속된 **이벤트 날** 사이의
    (집합 → 집합) 전이. 이것은 정렬에 안 흔들린다.
    """
    from collections import defaultdict as _dd
    per = _dd(lambda: _dd(set))
    for e in events:
        if e.get("사후_동일시각"):
            continue
        d = _day(e["t_occur"])
        if d is None:
            continue
        per[e["개체"]][d].add(e["종류"])

    def _tab(entday):
        t, m = Counter(), 0
        for days in entday:
            ks = [days[d] for d in sorted(days)]
            for i2 in range(1, len(ks)):
                t[(ks[i2 - 1], ks[i2])] += 1
                m += 1
        return t, m

    entday = [{d: "+".join(sorted(v)) for d, v in dd.items()} for dd in per.values()]
    tab, n = _tab(entday)
    obs = _tvd(tab, n)
    rng = np.random.default_rng(seed)
    null = np.empty(n_perm)
    movable = [dd for dd in entday if len(dd) >= 2]
    for p2 in range(n_perm):
        shuf = []
        for dd in movable:
            ds = list(dd)
            vs = [dd[d] for d in ds]
            perm = rng.permutation(len(ds))
            shuf.append({ds[i2]: vs[perm[i2]] for i2 in range(len(ds))})
        t, m = _tab(shuf)
        null[p2] = _tvd(t, m)
    pval = float((1 + np.sum(null >= obs)) / (n_perm + 1))
    return {
        "🔴 단위": "하루의 **종류 집합** — 같은 날 순서는 저장소에 없다",
        "전이 수(분모)": n, "칸 수": len(tab),
        "실측 총변동거리": obs, "귀무 평균": float(np.mean(null)),
        "귀무 95분위": float(np.percentile(null, 95)), "순열 수": n_perm, "p": pval,
        "판정": ("🔴 발화 — 자료와 무관하지 않다" if pval < 0.05
               else "🔴 안 발화 — 「자료와 무관」 딱지를 단다"),
        "전이 표(상위 30)": {f"{a} → {b}": c
                        for (a, b), c in sorted(tab.items(), key=lambda kv: -kv[1])[:30]},
    }
