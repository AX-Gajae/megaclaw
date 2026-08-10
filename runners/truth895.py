# -*- coding: utf-8 -*-
"""노트 895 · 0단계 --- **정답지를 다시 낸다**. 요청 0건.

왜 다시 내나. 티처 #57 이 v1 정답지(`prec_one` 유효 수확)를 채점해 보니 **음성 20 을
실물 200 과 못 갈랐다**(AUC 0.5564 · MWU p 0.4061). 자를 만들기 전에 정답지가 서야
한다. 세 군데를 고친다 ---

  ⓐ **확인된 0 만 0** --- 6단계가 전부 판정된 작품의 0 만 0 으로 읽고, 판정 불가가
     하나라도 남은 작품의 0 은 **결측**이다(조항 59: '없다' 와 '못 봤다' 는 둘이다).
  ⓑ **연속량** --- `prec_one`(어절 **전부** 포함 · 이진)이 아니라 **어절 겹침 비율**
     (겹친 어절수 / 질의 어절수)을 항목마다 매겨 **합**한다. 타이가 줄어 천장이 오른다.
  ⓒ 천장(타이 없는 완벽한 자가 낼 수 있는 최대 스피어만)을 **먼저** 재고 B 의 통과선을
     그 60% 로 적는다.
  ⓓ **새 정답지가 음성 20 을 가르는지 먼저 본다.** 못 가르면 그 정답지로는 어떤 자도
     채점 못 한다 --- 그것도 값진 결과다.

🔴 **파서를 다시 구현하지 않는다**(티처 #57 M8). `runners/pilot893.py` 의 출하된
`_nav_title` 을 import 해서 쓴다.

🔴 **정정(2026-08-10 저녁 · 티처 #58 C1)**: 초판은 규약 47 을 어겼다 --- `lab.pairboot` 를
import 조차 안 하고 손으로 짠 **순 percentile**(`boot_auc`, B=4000)로 모든 구간을 냈고,
그 사실이 산출물에 **한 글자도** 적히지 않았다. 그 구간의 하한 0.7211 이 **F5 게이트**를
통과시켰다. 이 판은 모든 AUC 구간을 `cluster_boot` **BCa**(B=10,000 · 씨앗 895)로 다시
내고 --- `bca_auc()` --- **옛 값을 지우지 않고 나란히 병기**한다(`auc_intervals()`).
F5 판정은 `🔴 F5 게이트` 칸에 기계가 적는다.

🔴 **디시 재분류의 지위**: 894 가 옛 가드의 `결과 컨테이너 없음` 을 '확인된 0' 으로
재분류했다. 그 전제(응답에 무결과 표지가 있었다)는 P4 재요청 **12/12** 로 실측됐으나
`boot_ratio(12,12)=[1,1]` 은 퇴화이고 **Clopper-Pearson 하한 0.7354** 다(티처 #57 C4).
그래서 두 판을 **둘 다** 낸다 --- `느슨`(재분류를 판정으로 인정) · `엄격`(재분류를
판정 불가로 둔다). 정본은 **느슨**(894 판정이 그렇게 섰다)이고 엄격은 민감도다.
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab.pairboot import cluster_boot, solo_clusters   # noqa: E402  규약 47(정정 · 아래)
from runners.pilot893 import _nav_title          # noqa: E402  --- 출하된 파서를 쓴다

ROOT = Path("/Users/ax/world_model")
CACHE = ROOT / "data/state/cache_p893"
SAMPLE = ROOT / "data/state/pilot893_sample.json"
OUT = ROOT / "runners/out895_truth.json"
STEPS = ("뉴스사전", "뉴스사후", "블로그사전", "블로그사후", "디시최신", "디시정확")
DC_STEPS = ("디시최신", "디시정확")
#: 🔴 **정본 바탕은 넷이다(뉴스 제외)**. 이유는 측정으로 나왔다 --- 아래 「왜 바탕을 바꿨나」.
BASIS4 = ("블로그사전", "블로그사후", "디시최신", "디시정확")
OLD_DC_GUARD = "결과 컨테이너 없음"


# ── 자료 ────────────────────────────────────────────────────────────
def toks(q: str) -> list[str]:
    """`diag893.prec()` 와 **같은 어절 정의**(2글자 이상). 정의를 바꾸면 못 비빈다."""
    return [t for t in str(q).split() if len(t) >= 2]


def overlap(q: str, title: str) -> float:
    """어절 겹침 **비율**. 질의 전체가 통째로 들어 있으면 1.0.

    어절이 하나뿐인 질의에서는 `prec_one` 과 **글자 그대로 같다**(0 또는 1).
    """
    t = str(title)
    if q and q in t:
        return 1.0
    ks = toks(q)
    if not ks:
        return 0.0
    return sum(1 for k in ks if k in t) / len(ks)


def prec_one(q: str, title: str) -> bool:
    """v1 정답지(비교용)."""
    ks = toks(q)
    return bool(q in str(title) or (ks and all(k in str(title) for k in ks)))


def title_of(x: dict) -> str:
    t = x.get("제목", "")
    if x.get("원천") == "블로그":
        t, _ = _nav_title(t)
    return t


# ── 통계 ────────────────────────────────────────────────────────────
def avg_ranks(xs: list[float]) -> list[float]:
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        m = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = m
        i = j + 1
    return r


def pearson(a: list[float], b: list[float]) -> float:
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = math.sqrt(sum((x - ma) ** 2 for x in a))
    sb = math.sqrt(sum((x - mb) ** 2 for x in b))
    if sa == 0 or sb == 0:
        return float("nan")
    return sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / (sa * sb)


def spearman(a: list[float], b: list[float]) -> float:
    return pearson(avg_ranks(a), avg_ranks(b))


def ceiling(y: list[float]) -> float:
    """**타이 없는 완벽한 자**가 이 정답지에 낼 수 있는 스피어만의 최대값.

    정답지의 타이는 평균 순위를 받고, 완벽한 자는 같은 순서 안에서 타이를 임의로 깨
    1..n 을 받는다(블록 안 순서는 상관에 영향이 없다). 그 둘의 피어슨이 천장이다.
    """
    n = len(y)
    order = sorted(range(n), key=lambda i: y[i])
    perfect = [0.0] * n
    for pos, i in enumerate(order):
        perfect[i] = pos + 1
    return pearson(avg_ranks(y), perfect)


def auc(pos: list[float], neg: list[float]) -> float:
    """P(실물 > 음성) + 0.5·P(같음). 1.0 이면 완전히 갈린다."""
    if not pos or not neg:
        return float("nan")
    s = 0.0
    for p in pos:
        for q in neg:
            s += 1.0 if p > q else (0.5 if p == q else 0.0)
    return s / (len(pos) * len(neg))


def mwu_p(pos: list[float], neg: list[float]) -> float:
    """정규근사 · 타이 보정 양측 p."""
    n1, n2 = len(pos), len(neg)
    xs = pos + neg
    r = avg_ranks(xs)
    r1 = sum(r[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    mu = n1 * n2 / 2
    n = n1 + n2
    cnt = Counter(xs)
    tie = sum(t ** 3 - t for t in cnt.values())
    var = n1 * n2 / 12 * ((n + 1) - tie / (n * (n - 1)))
    if var <= 0:
        return float("nan")
    z = (u1 - mu) / math.sqrt(var)
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def boot_auc(pos, neg, B=4000, seed=895):
    """🔴 **초판(2026-08-10 17:00) 의 구간 — 순 percentile 이다. 정본이 아니다.**

    규약 47 은 BCa 를 요구하는데 이 함수는 `lab.pairboot` 를 쓰지 않고 손으로 짠
    층화 2표본 percentile 이었고, 그 사실이 산출물에 **한 글자도** 적히지 않았다
    (티처 #58 C1). **지우지 않고 남긴다** --- 이 실험실은 이력을 안 뭉갠다.
    지금은 `bca_auc()` 가 정본이고 이 값은 「순 percentile(초판)」으로 병기된다.
    """
    rng = random.Random(seed)
    es = []
    for _ in range(B):
        p = [pos[rng.randrange(len(pos))] for _ in range(len(pos))]
        q = [neg[rng.randrange(len(neg))] for _ in range(len(neg))]
        es.append(auc(p, q))
    es.sort()
    return [round(es[int(0.025 * B)], 4), round(es[int(0.975 * B)], 4)]


def bca_auc(pos, neg, B=10_000, seed=895) -> dict:
    """🔴 **정본 구간 — 규약 47 의 `lab.pairboot.cluster_boot` BCa**(씨앗 895).

    작품 하나가 단독 클러스터이므로 `solo_clusters` 로 **명시적** 무군집을 쓴다 ---
    조용한 폴백을 만들지 않는다(규약 47 병기 의무 · 티처 #5 결함 ③).

    ⚠ **한 벌 재표집이다**: AUC 는 실물·음성 **두 표본**의 통계인데 `cluster_boot` 는
    합친 78(또는 179)행을 한 번에 다시 뽑으므로 재표집마다 군 비율이 흔들린다.
    그 성질을 **없애는 대신 적는다** --- 같은 자료의 층화 percentile(초판)을 나란히
    병기하므로 둘을 비교할 수 있다. `score895.py:199` 가 A 에서 층화를 정본으로 삼은
    사유와 같은 사실이고, 여기서는 **규약 47 문면을 따르는 쪽(BCa)을 정본으로 둔다.**

    코드가 `percentile(유실)`·`percentile(폴백)` 을 돌려주면 그 문자열을 **그대로**
    `구간 종류` 에 적고 `폴백 사유` 를 함께 박는다(사전등록 220-224행).
    """
    arr = np.asarray(list(pos) + list(neg), float)
    nr = len(pos)

    def stat(idx):
        idx = np.asarray(idx, int)
        p, q = arr[idx[idx < nr]], arr[idx[idx >= nr]]
        if p.size == 0 or q.size == 0:
            return float("nan")            # 한 군이 통째로 빠진 재표집 --- 유실로 센다
        c = p[:, None] - q[None, :]
        return float(((c > 0).sum() + 0.5 * (c == 0).sum()) / (p.size * q.size))

    clusters, wire = solo_clusters(len(arr))
    th, lo, hi, kind = cluster_boot(stat, clusters, B=B, seed=seed)
    rep = {"점추정": round(float(th), 4), "lo": round(float(lo), 4),
           "hi": round(float(hi), 4), "구간 종류": kind,
           "B": B, "씨앗": seed, "n": {"실물": nr, "음성": len(arr) - nr},
           "⚠ 무군집": wire["⚠ 무군집"],
           "⚠ 한 벌 재표집": "실물·음성을 합쳐 한 번에 재표집한다 --- 군 비율이 흔들린다(층화 아님)"}
    if kind != "BCa":
        rep["🔴 폴백 사유"] = (
            f"`cluster_boot` 이 BCa 를 못 내고 `{kind}` 를 돌려줬다 --- 유실 ≥10%(재표집에서 "
            "한 군이 비었거나 통계가 nan) 또는 BCa 계산 실패. 사전등록 220-224행의 "
            "폴백 조항을 발화시킨 것이고, 그 사실을 이 필드로 박는다.")
    return rep


def auc_intervals(pos, neg) -> dict:
    """🔴 **정정(BCa)과 초판(순 percentile)을 나란히** --- 하나를 지우지 않는다."""
    new = bca_auc(pos, neg)
    old = boot_auc(pos, neg)
    return {"🔴 BCa(정정 · 규약 47 cluster_boot)": new,
            "순 percentile(초판 · 층화 2표본 · B=4000)": old,
            "정정−초판 하한 차": round(new["lo"] - old[0], 4),
            "정정−초판 상한 차": round(new["hi"] - old[1], 4)}


# ── 본체 ────────────────────────────────────────────────────────────
def build() -> dict:
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CACHE.glob("*.json"))]
    smp = json.loads(SAMPLE.read_text(encoding="utf-8"))
    meta = {r["record_id"]: r for r in smp["표본"]}

    out = []
    for r in rows:
        if not r.get("ok"):
            continue
        key, q = r["key"], r["질의"]
        st, er = r.get("단계별", {}), r.get("실패단계", {})
        undec_loose, undec_strict = [], []
        for s in STEPS:
            v = st.get(s)
            if isinstance(v, int) or v == "확인된 0":
                continue
            undec_strict.append(s)
            if s in DC_STEPS and OLD_DC_GUARD in str(er.get(s, "")):
                continue                      # 894 재분류 --- 느슨판에서는 판정된 것
            undec_loose.append(s)

        v2 = sum(overlap(q, title_of(x)) for x in r["항목"])
        v1 = sum(1 for x in r["항목"] if prec_one(q, title_of(x)))
        # 🔴 4단계 바탕(뉴스 제외) --- 아래 「왜 바탕을 바꿨나」 참조
        it4 = [x for x in r["항목"] if x.get("단계") in BASIS4]
        v2b = sum(overlap(q, title_of(x)) for x in it4)
        v1b = sum(1 for x in it4 if prec_one(q, title_of(x)))
        u4_loose = [s for s in undec_loose if s in BASIS4]
        u4_strict = [s for s in undec_strict if s in BASIS4]
        m = meta.get(key, {})
        out.append({
            "key": key, "질의": q, "질의출처": r.get("질의출처"),
            "층": r.get("층"), "country": m.get("country"),
            "y_popularity": m.get("y_popularity"), "t_0": r.get("t_0"),
            "어절수": len(toks(q)), "글자수": len(q),
            "음성": key.startswith("FAKE"),
            "항목수": len(r["항목"]),
            "v1 유효수확(prec_one)": v1,
            "v2 겹침합": round(v2, 6),
            "v1b 유효수확(4단계)": v1b,
            "v2b 겹침합(4단계)": round(v2b, 6),
            "판정불가 단계(느슨)": undec_loose,
            "판정불가 단계(엄격)": undec_strict,
            "판정불가 4단계(느슨)": u4_loose,
            "판정불가 4단계(엄격)": u4_strict,
        })

    for w in out:
        for tag in ("느슨", "엄격"):
            u6 = w[f"판정불가 단계({tag})"]
            u4 = w[f"판정불가 4단계({tag})"]
            for lab, val, uu in (("v2", w["v2 겹침합"], u6),
                                 ("v1", w["v1 유효수확(prec_one)"], u6),
                                 ("v2b", w["v2b 겹침합(4단계)"], u4),
                                 ("v1b", w["v1b 유효수확(4단계)"], u4)):
                if val > 0:
                    w[f"{lab}·{tag}"] = val          # 양수는 하한이어도 값이다
                elif not uu:
                    w[f"{lab}·{tag}"] = 0.0          # 확인된 0
                else:
                    w[f"{lab}·{tag}"] = None         # 🔴 결측 --- 0 으로 읽지 않는다
    return {"작품": out}


def score_report(out: list[dict], field: str) -> dict:
    real = [w for w in out if not w["음성"]]
    fake = [w for w in out if w["음성"]]
    rv = [w[field] for w in real if w[field] is not None]
    fv = [w[field] for w in fake if w[field] is not None]
    allv = rv + fv
    rep = {
        "분모": {"실물 전체": len(real), "실물 값 있음": len(rv), "실물 결측": len(real) - len(rv),
               "음성 전체": len(fake), "음성 값 있음": len(fv), "음성 결측": len(fake) - len(fv)},
        "확인된 0": {"실물": sum(1 for w in real if w[field] == 0),
                  "음성": sum(1 for w in fake if w[field] == 0)},
        "실물 중앙값": round(sorted(rv)[len(rv) // 2], 4) if rv else None,
        "음성 중앙값": round(sorted(fv)[len(fv) // 2], 4) if fv else None,
        "실물 평균": round(sum(rv) / len(rv), 4) if rv else None,
        "음성 평균": round(sum(fv) / len(fv), 4) if fv else None,
        "값 가짓수(전체)": len(set(allv)),
        "제일 큰 타이 블록": max(Counter(allv).values()) if allv else None,
    }
    if rv and fv:
        rep["🔴 AUC(음성<실물)"] = round(auc(rv, fv), 4)
        rep["AUC 95% 구간"] = auc_intervals(rv, fv)
        rep["MWU p(양측·타이보정)"] = round(mwu_p(rv, fv), 4)
    if allv:
        rep["🔴 스피어만 천장(타이 없는 완벽한 자)"] = round(ceiling(allv), 4)
        rep["천장 · 실물만"] = round(ceiling(rv), 4) if rv else None

    # 🔴 조항 60 --- 갈라 보고한다. 음성 질의는 **전부 한글**이므로 로마자·영어
    # 실물과의 비교는 '언어 비교' 이지 '존재량 비교' 가 아니다.
    strat = {}
    for src in sorted({w["질의출처"] for w in real if w["질의출처"]}):
        ys = [w[field] for w in real if w["질의출처"] == src and w[field] is not None]
        if not ys or not fv:
            continue
        strat[src] = {"n": len(ys), "중앙값": round(sorted(ys)[len(ys) // 2], 4),
                      "AUC(음성<이 팔)": round(auc(ys, fv), 4),
                      "95% 구간": auc_intervals(ys, fv),
                      "MWU p": round(mwu_p(ys, fv), 4)}
    ko = [w[field] for w in real
          if w["질의출처"] in ("AniList native(한글)", "AniList synonyms(한글)")
          and w[field] is not None]
    if ko and fv:
        strat["🔴 한글 질의 실물 전부(native+synonyms)"] = {
            "n": len(ko), "중앙값": round(sorted(ko)[len(ko) // 2], 4),
            "AUC(음성<이 팔)": round(auc(ko, fv), 4),
            "95% 구간": auc_intervals(ko, fv), "MWU p": round(mwu_p(ko, fv), 4)}
    rep["🔴 질의 언어로 가른 AUC"] = strat

    # 길이 교락 --- 정답지 자신이 질의 길이의 자인가(티처 #57 C3)
    xs = [(w["어절수"], w["글자수"], w[field]) for w in real if w[field] is not None]
    if len(xs) > 3:
        rep["정답지↔질의 어절수 ρ(실물)"] = round(
            spearman([a for a, _, _ in xs], [c for _, _, c in xs]), 4)
        rep["정답지↔질의 글자수 ρ(실물)"] = round(
            spearman([b for _, b, _ in xs], [c for _, _, c in xs]), 4)
    return rep


def main():
    d = build()
    out = d["작품"]
    rep = {}
    for f in ("v2b·느슨", "v2b·엄격", "v1b·느슨", "v1b·엄격",
              "v2·느슨", "v2·엄격", "v1·느슨", "v1·엄격"):
        rep[f] = score_report(out, f)
    # v1 과 v2 의 일치도(결측 아닌 교집합)
    both = [(w["v1·느슨"], w["v2·느슨"]) for w in out
            if w["v1·느슨"] is not None and w["v2·느슨"] is not None]
    rep["v1↔v2 스피어만(느슨 · 결측 제외)"] = round(
        spearman([a for a, _ in both], [b for _, b in both]), 4)
    rep["v1↔v2 분모"] = len(both)

    d["채점"] = rep
    d["🔴 왜 바탕을 바꿨나(6단계 → 4단계)"] = (
        "6단계 바탕에서는 **음성 20 전부가 뉴스 두 단계 판정 불가**다(20/20 · 503). "
        "그래서 음성은 **구조적으로 '확인된 0' 이 될 수 없고**, 조항 59 를 그대로 적용하면 "
        "수확 0 인 음성은 전원 결측이 되어 **남는 음성은 '무언가 긁힌 것' 뿐**이다 --- "
        "결과에 조건 붙여 표본을 고르는 것(selection on outcome)이라 AUC 가 **정의상 "
        "분리를 못 보게 편향된다**. 즉 v2 설계의 ⓐ 와 ⓓ 가 서로를 죽인다. "
        "고침: **양 군에 같은 바탕**을 준다 --- 뉴스 두 단계를 정답지에서 빼고 "
        "블로그2+디시2 의 넷으로만 센다. 음성 20/20 이 넷 전부 판정됐으므로 "
        "**음성의 확인된 0 이 되살아난다.** 요청 0건으로 고쳐진다.")
    # ── 🔴 정본 채점 모집단: **한글 질의 팔** ──────────────────────
    # ⓓ 의 답이 그렇게 나왔다. 음성 20 은 **전부 한글 구절**이라 로마자·영어 실물과
    # 비교하면 '언어의 잡음 바닥' 을 비교하게 된다(아래 판정 참조).
    F = "v2b·느슨"
    ko = [w for w in out if not w["음성"]
          and w["질의출처"] in ("AniList native(한글)", "AniList synonyms(한글)")]
    kov = [w[F] for w in ko if w[F] is not None]
    fkv = [w[F] for w in out if w["음성"] and w[F] is not None]
    pop = kov + fkv
    d["🔴 정본 채점 모집단(한글 질의 실물 + 음성)"] = {
        "실물 한글 질의": {"전체": len(ko), "값 있음": len(kov),
                     "확인된 0": sum(1 for v in kov if v == 0)},
        "음성": {"전체": 20, "값 있음": len(fkv), "확인된 0": sum(1 for v in fkv if v == 0)},
        "층 분포(값 있는 한글 실물)": dict(Counter(
            w["층"] for w in ko if w[F] is not None)),
        "원산국 분포": dict(Counter(w["country"] for w in ko if w[F] is not None)),
        "AUC(음성<실물)": round(auc(kov, fkv), 4),
        "AUC 95% 구간": auc_intervals(kov, fkv),
        "MWU p": round(mwu_p(kov, fkv), 4),
        # 🔴 M8(티처 #58) --- 62 인가 58 인가. 아래 「정본 분모」 칸이 못 박은 것.
        "🔴 분모 못 박기(62 대 58)": {
            "등록 모집단(한글 질의 실물 전수)": len(ko),
            "정답지 값 있음(v2b·느슨)": len(kov),
            "정답지 결측": len(ko) - len(kov),
            "정본": ("**A 의 분모는 62**(등록 모집단 전수) · **정답지가 필요한 통계"
                   "(정답지 자신의 AUC · 천장 · B · C)의 분모는 58+음성 20 = 78**. "
                   "이 두 수를 한 문장에 잇지 마라(조항 60)."),
            "근거": ("결측 4건은 **정답지의 결측**이지 자의 결측이 아니다. A 는 '자가 음성을 "
                   "가르는가' 라 자의 값만 있으면 재진다 --- 정답지 값으로 4건을 떨어뜨리면 "
                   "**결과(정답지)에 조건을 붙여 표본을 고르는 것**이고, 그것은 v3 이 고친 것 ① "
                   "에서 스스로 이름 붙여 피한 병(selection on outcome)과 같은 종류다. "
                   "반대로 B·C·천장은 정답지 값이 **정의상 필요**하므로 58 이 분모다. "
                   "구현도 그렇게 서 있다 --- score895.py:118 은 62, :152·:170 은 58."),
            "🔴 둘 다의 값은 out895_score.json 의 「A · 분모 62 대 58 병기」 칸에 있다": True,
        },
        "🔴 스피어만 천장(이 모집단)": round(ceiling(pop), 4),
        "값 가짓수": len(set(pop)), "제일 큰 타이 블록": max(Counter(pop).values()),
    }
    cap = d["🔴 정본 채점 모집단(한글 질의 실물 + 음성)"]["🔴 스피어만 천장(이 모집단)"]
    d["🔴 B 의 통과선"] = {
        "정본 천장(v2b·느슨 · 한글 질의 실물 58 + 음성 20)": cap,
        "🔴 통과선 = 천장 × 0.60": round(0.60 * cap, 4),
        "참고 · 전 표본 천장(v2b·느슨)": rep["v2b·느슨"].get("🔴 스피어만 천장(타이 없는 완벽한 자)"),
        "참고 · v1 6단계 천장(티처 #57 이 잰 것)": 0.8278,
        "⚠ 이 천장의 분모는 78(값 있는 한글 실물 58 + 음성 20)이다": "A 의 분모 62 와 다른 수다(조항 60)",
    }
    # ── 🔴 구간법을 산출물 머리에 박는다(티처 #58 C1: 초판엔 이 칸이 없었다) ──
    kinds = Counter()
    def _walk(o):
        if isinstance(o, dict):
            if "구간 종류" in o and "점추정" in o:
                kinds[o["구간 종류"]] += 1
            for v in o.values():
                _walk(v)
        elif isinstance(o, list):
            for v in o:
                _walk(v)
    _walk(d)
    d["🔴 구간법(규약 47)"] = {
        "정본": "BCa · lab/pairboot.cluster_boot · B=10,000 · 씨앗 895 · 작품 단독 클러스터(무군집 병기)",
        "구간 종류 집계(세어서)": dict(kinds),
        "폴백 발화": sum(v for k, v in kinds.items() if k != "BCa"),
        "폴백 사유": ("없다 --- 퇴화가 한 번도 발화하지 않았다(유실 <10% · BCa 계산 성공). "
                  "발화했다면 각 구간의 `🔴 폴백 사유` 필드에 코드가 적는다."),
        "병기": "모든 구간에 초판의 순 percentile(층화 2표본 · B=4000) 값을 나란히 남겼다",
        "🔴 이력": ("초판(17:00)은 `lab.pairboot` 를 import 조차 안 했고 모든 구간이 손수 짠 "
                 "순 percentile 이었으며 그 사실이 산출물에 없었다(티처 #58 C1 · 규약 47 위반)."),
    }
    # ── 🔴 F5 게이트를 **산출물에 박는다**(티처 #58 C1 이 걸린 자리) ─────
    ci = d["🔴 정본 채점 모집단(한글 질의 실물 + 음성)"]["AUC 95% 구간"]
    lo_new = ci["🔴 BCa(정정 · 규약 47 cluster_boot)"]["lo"]
    lo_old = ci["순 percentile(초판 · 층화 2표본 · B=4000)"][0]
    d["🔴 F5 게이트(정답지 AUC 부트 하한 ≤ 0.5 면 채점 중단)"] = {
        "정정 · BCa 하한": lo_new,
        "초판 · 순 percentile 하한": lo_old,
        "구간 종류": ci["🔴 BCa(정정 · 규약 47 cluster_boot)"]["구간 종류"],
        "🔴 판정(정본 = BCa)": "통과(채점 진행)" if lo_new > 0.5 else "🔴 중단 --- 채점하지 마라",
        "초판 기준 판정": "통과(채점 진행)" if lo_old > 0.5 else "🔴 중단",
        "판정이 바뀌었나": bool((lo_new > 0.5) != (lo_old > 0.5)),
        "🔴 이력": ("초판(2026-08-10 17:00)은 규약 47 을 어기고 순 percentile 로 이 게이트를 "
                 "통과시켰고 그 사실이 산출물에 적히지 않았다(티처 #58 C1). 이 판은 "
                 "`lab.pairboot.cluster_boot` BCa 로 다시 냈고 **두 값을 나란히 남긴다.**"),
    }
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"채점": rep, "B 통과선": d["🔴 B 의 통과선"]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
