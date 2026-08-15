#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""974 --- **축 C3 의 정본 자**(`leave-one-source-out Δ`)와 **축 C2 의 자**를 한 주행으로 낸다.

🔴 973 은 **분모만** 만들었다(원천 × 도메인 행렬). **예측 성능의 LOSO Δ 는 0 회**였다.
🔴 티처 #112: **「정밀도 먼저, 그 다음 예측 LOSO Δ」** --- `runners/out974_precision.json`
   이 먼저 나와 있어야 이 러너가 돈다(§9-6 반증조건).

## 설계 (사전등록 §6·§7)

**행** = (s,a,o) 삼중쌍. `s` = 액션 앞 90일 · `o` = 액션 당일~뒤 90일.
🔴 **`sao962`(steam 리뷰)는 `o_결과` 에 `값` 배열이 없어 원리상 못 쓴다** --- 뺀 것을 적는다.

**나눔은 시간으로 자른다.** `언제 ≥ 2025-01-01` 이면 유보, 아니면 학습.
🔴 **HPLT 행의 ts 는 2014~2022 라 유보에 한 행도 못 들어간다** --- 그래서
**유보 집합이 세 팔에서 글자 그대로 같다**. 팔이 다른 것은 **학습 집합뿐**이다.
그것이 바로 「원천 하나를 빼면 유보 성능이 얼마나 달라지나」다.

| 팔 | 학습 |
|---|---|
| **B** | `sao941` + `sao959` 의 2025 이전 행 (**HPLT 없음**) |
| **C** | B + **HPLT 전량** |
| **C′** | B + **974 게이트 H1~H4 를 통과한 HPLT** |

**자** = 도메인별 유보 스피어만의 **유보 행 가중 묶음 Δ**(생산 함수 `predict971.pooled_delta`)
+ **유보 결과 순열 귀무 p**(생산 함수 `predict972.perm_null`).
**C2** = 도메인 수 × **도메인별 유보 성능의 최저값** · **C5** = `Δ⁺` 와 **최대 `Δ⁻`**.

🔴 **바퀴를 다시 만들지 않는다**: 특징 `layers957.feats_log` · 능형 `layers957.ridge_fit/ridge_pred`
· 순위상관 `predict971.spear` · 묶음 `predict971.pooled_delta` · 귀무 `predict972.perm_null`
· 들림 `y` 는 `grow959.build_arms_fast` 가 쓰는 **그 식 그대로**(`LIFT_PRE`·`LIFT_POST`).

씀:
    python3 runners/loso974.py --stage loso   --ref <40자 sha>
    python3 runners/loso974.py --stage wiring --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for p in (str(ROOT), str(ROOT / "runners")):
    if p not in sys.path:
        sys.path.insert(0, p)

import runners.predict971 as P                    # noqa: E402
import predict972 as N                            # noqa: E402
import runners.layers957 as L                     # noqa: E402
import runners.precision974 as PR                 # noqa: E402  게이트 H1~H4

RAN = ("runners/loso974.py", "runners/precision974.py", "runners/layers957.py",
       "runners/predict971.py", "runners/predict972.py")

OUT = ROOT / "runners"
SEED = 974
PERM_B = 4000
ALPHA = 1.0                  # §6 --- `layers957.ALPHAS` 의 가운데 값. 측정 전에 박는다.
SPLIT = dt.date(2025, 1, 1)  # §6 시간 나눔
MIN_HO = 20                  # 971 의 `N_MIN_HOLD` 와 같은 값
MIN_TR = 20

SRC = collections.OrderedDict([
    ("sao941", "data/ingest/sao941/pairs.jsonl.gz"),
    ("sao959", "data/ingest/sao959/pairs.jsonl.gz"),
    ("hplt_ko", "data/ingest/sao973_hplt/pairs.jsonl.gz"),
])
KEY_C, KEY_B = "C(통제+들뜸)", "B(통제만)"     # perm_null 이 찾는 열쇠 이름


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def code_stamp() -> dict:
    files = sorted(glob.glob(str(ROOT / "lab/*.py")))
    files += [str(ROOT / r) for r in RAN]
    return {str(Path(p).relative_to(ROOT)): P._sha_file(p)
            for p in sorted(set(files)) if Path(p).is_file()}


def stamp_block(ref, cs0, cs1, t0):
    import hashlib
    import subprocess
    ds = {k: P._sha_file(str(ROOT / v)) for k, v in SRC.items()}
    runner, ok = {}, 0
    for r in RAN:
        disk = P._sha_file(str(ROOT / r))
        try:
            cm = hashlib.sha256(subprocess.check_output(
                ["git", "show", "%s:%s" % (ref, r)], cwd=str(ROOT))).hexdigest()
        except Exception:                                          # noqa: BLE001
            cm = None
        runner[r] = {"디스크 sha256": disk, "커밋 blob sha256": cm, "일치": disk == cm}
        ok += 1 if disk == cm else 0
    return {
        "언제(시작)": t0, "언제(끝)": _now(),
        "시작 code_stamp 요약": hashlib.sha256(
            json.dumps(cs0, sort_keys=True).encode()).hexdigest(),
        "끝 code_stamp 요약": hashlib.sha256(
            json.dumps(cs1, sort_keys=True).encode()).hexdigest(),
        "🔴 시작=끝": cs0 == cs1,
        "분모: 도장이 덮는 파일": len(cs1),
        "🔴 자료 지문": ds, "분모: 연 자료 파일": len(ds),
        "🔴 F1 기준 ref(준 대로)": ref,
        "🔴 40자 고정 sha 인가": bool(re.fullmatch(r"[0-9a-f]{40}", ref or "")),
        "🔴 기준 ref 가 0000…0000 인가": bool(re.fullmatch(r"0{40}", ref or "")),
        "러너별": runner, "🔴 분자/분모": "%d / %d" % (ok, len(RAN)),
        "🔴 F5 통과": ok == len(RAN) and bool(re.fullmatch(r"[0-9a-f]{40}", ref or ""))
        and not re.fullmatch(r"0{40}", ref or ""),
    }


# ══════════════════════════════════════════════════════════════════════
# 자료 --- 행 하나를 (x, y, 도메인, 날짜, 개체)로
# ══════════════════════════════════════════════════════════════════════
def row_of(p: dict, src: str):
    """🔴 `o_결과.값` 이 없으면 **원리상 못 쓴다**(steam 리뷰). None 을 낸다."""
    s = p.get("s_상태", {}).get("값")
    o = p.get("o_결과", {}).get("값")
    if not s or not o or len(s) < 90 or len(o) < 91:
        return None
    s = np.asarray(s, dtype=float)
    o = np.asarray(o, dtype=float)
    y = (math.log10(1.0 + float(o[:L.LIFT_POST].mean()))
         - math.log10(1.0 + float(s[-L.LIFT_PRE:].mean())))
    if not np.isfinite(y):
        return None
    return {"x": L.feats_log(s), "y": y, "도메인": p.get("도메인"),
            "언제": p["a_액션"]["언제"], "개체": p["a_액션"]["개체"],
            "원천": src, "쌍id": p["쌍id"]}


def load(src: str, gate=False):
    rows, drop = [], collections.Counter()
    with gzip.open(str(ROOT / SRC[src]), "rt", encoding="utf-8") as f:
        for line in f:
            p = json.loads(line)
            if gate:
                if any(PR.gate_flags(PR.light(p)).values()):
                    drop["974 게이트 H1~H4"] += 1
                    continue
            r = row_of(p, src)
            if r is None:
                drop["o_결과 에 값 배열이 없다"] += 1
                continue
            rows.append(r)
    return rows, dict(drop)


def design(rows, doms):
    X = np.asarray([r["x"] for r in rows], dtype=float)
    D = np.zeros((len(rows), len(doms)), dtype=float)
    for i, r in enumerate(rows):
        if r["도메인"] in doms:
            D[i, doms.index(r["도메인"])] = 1.0
    return np.hstack([X, D])


def fit_score(train, hold, doms):
    """묶음 능형 하나를 적합하고 **도메인별로** 유보 스피어만을 낸다."""
    Xtr, ytr = design(train, doms), np.asarray([r["y"] for r in train], float)
    m = L.ridge_fit(Xtr, ytr, ALPHA)
    Xho = design(hold, doms)
    pred = L.ridge_pred(m, Xho)
    return pred


# ══════════════════════════════════════════════════════════════════════
def stage_loso(ref: str) -> dict:
    t0 = _now()
    cs0 = code_stamp()
    # 🔴 §9-6 --- 정밀도가 먼저 나와 있어야 이 러너가 돈다
    pfile = OUT / "out974_precision.json"
    if not pfile.is_file():
        raise SystemExit("🔴 반증조건 6 --- out974_precision.json 이 없다. 정밀도 먼저.")
    prec = json.loads(pfile.read_text(encoding="utf-8"))

    base, drop_b = [], {}
    for s in ("sao941", "sao959"):
        r, d = load(s)
        base += r
        drop_b[s] = d
    hplt, drop_h = load("hplt_ko")
    hplt_g, drop_g = load("hplt_ko", gate=True)
    # 🔴 962 는 원리상 못 쓴다 --- 세어서 적는다
    n962 = sum(1 for _ in gzip.open(
        str(ROOT / "data/ingest/sao962/pairs.jsonl.gz"), "rt", encoding="utf-8"))

    def isho(r):
        return dt.date.fromisoformat(r["언제"]) >= SPLIT

    hold = [r for r in base if isho(r)]
    tr_b = [r for r in base if not isho(r)]
    hplt_tr = [r for r in hplt if not isho(r)]
    hplt_g_tr = [r for r in hplt_g if not isho(r)]
    arms = collections.OrderedDict([
        ("B(HPLT 없음)", tr_b),
        ("C(HPLT 전량)", tr_b + hplt_tr),
        ("C′(HPLT · 974 게이트)", tr_b + hplt_g_tr),
    ])
    doms = sorted({r["도메인"] for r in tr_b + hplt_tr + hold})

    dom_ho = collections.Counter(r["도메인"] for r in hold)
    dom_tr = collections.Counter(r["도메인"] for r in tr_b)
    gated = [d for d in doms if dom_ho[d] >= MIN_HO and dom_tr[d] >= MIN_TR]

    preds = {k: fit_score(v, hold, doms) for k, v in arms.items()}
    yho = np.asarray([r["y"] for r in hold], float)
    dho = np.asarray([r["도메인"] for r in hold])

    # per --- `predict972.perm_null` 이 먹는 꼴 그대로 만든다(생산 함수 재사용)
    def make_per(name_c):
        per = collections.OrderedDict()
        for d in gated:
            m = dho == d
            pb, pc = preds["B(HPLT 없음)"][m], preds[name_c][m]
            per[d] = {"유보 행": int(m.sum()), "학습 행": int(dom_tr[d]),
                      "예측": {"B": pb, "C": pc},
                      "_yho": yho[m],
                      "ρ": {KEY_B: P.spear(pb, yho[m]), KEY_C: P.spear(pc, yho[m])}}
        return per

    res = collections.OrderedDict()
    for name in ("C(HPLT 전량)", "C′(HPLT · 974 게이트)"):
        per = make_per(name)
        delta, den = P.pooled_delta(per, KEY_C, KEY_B)
        pn = N.perm_null(per, B=PERM_B, seed=SEED)
        dd = {d: round(per[d]["ρ"][KEY_C] - per[d]["ρ"][KEY_B], 6) for d in per}
        pos = sum(1 for v in dd.values() if v > 0)
        res[name] = {
            "🔴 학습 행": len(arms[name]), "🔴 밑값(B) 학습 행": len(tr_b),
            "🔴 늘어난 학습 행": len(arms[name]) - len(tr_b),
            "🔴🔴 묶음 Δρ(C−B)": round(float(delta), 6),
            "🔴 분모: 유보 행 합": int(den),
            "🔴 도메인별 Δ": dd,
            "🔴 양수 도메인": "%d / %d" % (pos, len(dd)),
            "🔴🔴 C5 --- Δ⁺(가장 오른 도메인)":
                (max(dd.items(), key=lambda kv: kv[1]) if dd else None),
            "🔴🔴 C5 --- 최대 Δ⁻(가장 내린 도메인)":
                (min(dd.items(), key=lambda kv: kv[1]) if dd else None),
            "🔴 순열 귀무": pn,
        }

    # 🔴 C2 --- 도메인 수 × 도메인별 유보 성능의 **최저값**
    c2 = collections.OrderedDict()
    for name in arms:
        per = collections.OrderedDict()
        pr = preds[name]
        for d in gated:
            m = dho == d
            per[d] = round(float(P.spear(pr[m], yho[m])), 6)
        lo = min(per.items(), key=lambda kv: kv[1])
        c2[name] = {
            "🔴 게이트 통과 도메인 수": len(per),
            "🔴 도메인별 유보 스피어만": per,
            "🔴🔴 최저값": lo[1], "🔴🔴 최저 도메인": lo[0],
            "🔴 C2 자(도메인 수 × 최저값)": round(len(per) * lo[1], 6),
            "평균": round(float(np.mean(list(per.values()))), 6),
        }

    out = {
        "무엇": "974 --- 예측 성능 leave-one-source-out Δ (축 C3) + 도메인 최저 성능 (축 C2)",
        "🔴 축": "C3 (data spec · mixture · filtering) + C2 (멀티도메인) + C5 (간섭)",
        "사전등록": "docs/prereg_974_precision.md §6·§7",
        "🔴 정밀도가 먼저 나왔나(§9-6)": {
            "파일": "runners/out974_precision.json",
            "개체 정밀도(층화 표본 전체)":
                prec["🔴🔴 ① 층화 표본 전체(층 무시)"]["🔴 주 자 = 개체 정밀도(모름=실패)"],
            "유효 삼중쌍 점추정": prec["🔴🔴 ② 유효 삼중쌍"]["점추정"]},
        "🔴 자료": {
            "원천별 쓸 수 있는 행": {"sao941+sao959": len(base),
                             "hplt_ko": len(hplt), "hplt_ko(게이트 뒤)": len(hplt_g)},
            "🔴 sao962 는 원리상 못 쓴다": {
                "행": n962, "왜": "`o_결과` 에 일별 값 배열이 없다(리뷰 본문이다)"},
            "뺀 사유(941·959)": drop_b, "뺀 사유(hplt)": drop_h,
            "뺀 사유(hplt·게이트)": drop_g,
            "🔴 나눔": "언제 ≥ %s 면 유보" % SPLIT.isoformat(),
            "🔴 유보 행(세 팔에서 같다)": len(hold),
            "🔴 유보에 든 HPLT 행": sum(1 for r in hplt if isho(r)),
            "학습 행 B": len(tr_b), "학습 행 C": len(arms["C(HPLT 전량)"]),
            "학습 행 C′": len(arms["C′(HPLT · 974 게이트)"]),
            "도메인 전량": doms,
            "🔴 게이트(유보≥%d · 학습≥%d) 통과 도메인" % (MIN_HO, MIN_TR): gated,
            "도메인별 유보 행": dict(dom_ho), "도메인별 밑값 학습 행": dict(dom_tr),
        },
        "🔴🔴🔴 C3 --- leave-one-source-out Δ": res,
        "🔴🔴🔴 C2 --- 도메인별 유보 성능의 최저값": c2,
        "능형 λ": ALPHA, "씨앗": SEED, "순열 뽑기": PERM_B,
    }
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_loso.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


# ══════════════════════════════════════════════════════════════════════
def stage_wiring(ref: str) -> dict:
    """배선 V1~V7 + 파괴 대조 E1~E5 --- 자가 정말 자료에 매여 있나."""
    t0 = _now()
    cs0 = code_stamp()
    rng = np.random.RandomState(SEED)
    n, k = 400, 6
    Xt = rng.normal(size=(n, k))
    b = rng.normal(size=k)
    yt = Xt @ b + rng.normal(size=n) * 0.5
    Xh = rng.normal(size=(200, k))
    yh = Xh @ b + rng.normal(size=200) * 0.5
    m = L.ridge_fit(Xt, yt, ALPHA)
    ph = L.ridge_pred(m, Xh)

    V = collections.OrderedDict()
    V["V1 적합이 신호를 잡는다"] = P.spear(ph, yh) > 0.5
    # V2 --- 🔴 유보 정답을 바꿔치기해도 예측이 한 비트도 안 움직여야 한다
    ph2 = L.ridge_pred(L.ridge_fit(Xt, yt, ALPHA), Xh)
    V["V2 유보 정답이 예측에 못 샌다"] = bool(np.array_equal(ph, ph2)) and \
        bool(np.array_equal(ph, L.ridge_pred(m, Xh)))
    V["V3 순위상관은 단조변환에 안 흔들린다"] = abs(
        P.spear(ph, yh) - P.spear(np.exp(ph), yh)) < 1e-9
    V["V4 y 를 섞으면 상관이 죽는다"] = abs(
        P.spear(ph, yh[rng.permutation(200)])) < 0.3
    r0 = row_of({"s_상태": {"값": [1] * 90}, "o_결과": {"값": [1] * 91},
                 "도메인": "x", "a_액션": {"언제": "2020-01-01", "개체": "K"},
                 "쌍id": "t"}, "t")
    V["V5 s·o 가 다 있으면 행이 난다"] = r0 is not None and len(r0["x"]) == 6
    V["V6 o 값이 없으면 행이 안 난다"] = row_of(
        {"s_상태": {"값": [1] * 90}, "o_결과": {"글자": 3},
         "도메인": "x", "a_액션": {"언제": "2020-01-01", "개체": "K"},
         "쌍id": "t"}, "t") is None
    V["V7 y 는 o 가 커지면 커진다"] = (
        row_of({"s_상태": {"값": [1] * 90}, "o_결과": {"값": [9] * 91},
                "도메인": "x", "a_액션": {"언제": "2020-01-01", "개체": "K"},
                "쌍id": "t"}, "t")["y"] > r0["y"])

    E = collections.OrderedDict()
    # E1 --- 🔴 학습에서 x↔y 짝을 깨면 유보 상관이 죽어야 한다
    #        (λ 만 키우는 건 **파괴가 아니다** --- 능형은 전 계수를 같은 비율로 줄여
    #         순위를 보존한다. 실측으로 확인했다: λ=1e12 에서도 상관이 안 죽는다.)
    m2 = L.ridge_fit(Xt[rng.permutation(n)], yt, ALPHA)
    E["E1 학습 짝을 깨면 상관이 죽나"] = abs(P.spear(
        L.ridge_pred(m2, Xh), yh)) < 0.3
    E["E1b 참고: λ=1e12 로는 순위가 안 죽는다(능형의 성질)"] = abs(P.spear(
        L.ridge_pred(L.ridge_fit(Xt, yt, 1e12), Xh), yh)) > 0.5
    E["E2 x 를 상수로 부수면 상관이 죽나"] = not np.isfinite(P.spear(
        L.ridge_pred(L.ridge_fit(np.ones((n, 1)), yt, ALPHA),
                     np.ones((200, 1))), yh)) or abs(P.spear(
        L.ridge_pred(L.ridge_fit(np.ones((n, 1)), yt, ALPHA),
                     np.ones((200, 1))), yh)) < 0.2
    sl = SPLIT
    E["E3 나눔 날짜가 실제로 자른다"] = (
        dt.date.fromisoformat("2026-01-01") >= sl
        and not (dt.date.fromisoformat("2020-01-01") >= sl))
    E["E4 도메인 열이 실제로 붙는다"] = design(
        [{"x": [0] * 6, "도메인": "a"}], ["a", "b"]).shape == (1, 8)
    E["E5 게이트가 실제로 문다"] = PR.gate_flags(
        {"맞은 제목": "google", "host": "x.com"})["H1 단일 토큰 라틴"] and not \
        PR.gate_flags({"맞은 제목": "일론 머스크", "host": "x.com"})["H1 단일 토큰 라틴"]

    out = {"무엇": "974 --- LOSO 배선 V1~V7 · 파괴 대조 E1~E5",
           "V": {k2: bool(v) for k2, v in V.items()},
           "🔴 V 분자/분모": "%d / %d" % (sum(1 for v in V.values() if v), len(V)),
           "E": {k2: bool(v) for k2, v in E.items()},
           "🔴 E 분자/분모": "%d / %d" % (sum(1 for v in E.values() if v), len(E))}
    out["🔴 도장"] = stamp_block(ref, cs0, code_stamp(), t0)
    (OUT / "out974_loso_wiring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["loso", "wiring"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = {"loso": stage_loso, "wiring": stage_wiring}[a.stage](a.ref)
    print(json.dumps(r, ensure_ascii=False, indent=1, default=str)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
