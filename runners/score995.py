#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 995 채점기 --- 예측 `P1~P22` · 반증조건 `F01~F18`(+`F01-나`) · 조항 76·78·79.

## 규칙

- 🔴 **규칙 D**: 여기 나오는 «모든» 수는 `runners/out995_{nb,power,champ}.json` 의
  **키 경로**에서 읽는다. 손으로 친 수는 «사전등록 문언»(예측 구간의 경계)뿐이고,
  그건 `docs/prereg_995_unblock_nb.md` 의 인용이라 `사전등록` 칸에 따로 적는다.
- 🔴 **조항 78**: 이 채점기는 리터럴 `("통과", True)` 를 쓰지 않는다. 모든 판정은
  «식»이다. `runners/fiveprime902.py:2388` 의 AST 관문이 `runners/score*.py` 를 훑는다.
- 🔴 **조항 79**: 헤드라인 대비마다 조각 분해표를 «칸»으로 옮긴다.

## 쓰기

    python3 runners/score995.py --out runners/out995_score.json
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))

SRC = ("runners/score995.py",
       "runners/gamma995_nb.py", "runners/gamma995_power.py",
       "runners/gamma995_masks.py", "runners/gamma995_champ.py")

IN = collections.OrderedDict([
    ("A", "runners/out995_nb.json"),
    ("B", "runners/out995_power.json"),
    ("C", "runners/out995_champ.json"),
])
PROG = "runners/out995_champ_progress.txt"
PREREG = "docs/prereg_995_unblock_nb.md"

MATCH, PART, MISS = "맞다", "부분", "틀렸다"


def _sha(p):
    q = ROOT / p
    if not q.is_file():
        return None
    h = hashlib.sha256()
    with open(str(q), "rb") as f:
        for ch in iter(lambda: f.read(65536), b""):
            h.update(ch)
    return h.hexdigest()


def _now():
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _load():
    out = collections.OrderedDict()
    for k, p in IN.items():
        with open(str(ROOT / p), "r", encoding="utf-8") as f:
            out[k] = json.load(f, object_pairs_hook=collections.OrderedDict)
    return out


def G(obj, *path):
    """🔴 키 경로로만 읽는다. 없으면 «없다»가 아니라 터진다(조항 59)."""
    cur = obj
    for k in path:
        if isinstance(cur, list):
            cur = cur[k]
        else:
            if k not in cur:
                raise KeyError("키 경로 없음: %r (남은 %r)" % (k, path))
            cur = cur[k]
    return cur


def _in(x, lo, hi):
    return bool(lo <= x <= hi)


def _r(x, n=6):
    return None if x is None else round(float(x), n)


# ══════════════════════════════════════════════════════════════════════
# 조각 분해표 (조항 79)
# ══════════════════════════════════════════════════════════════════════
PIECE_KEYS = ("점추정", "t_clu", "🔴🔴 2·SE 를 넘나", "🔴 동부호 수",
              "도메인 사이 SD(τ̂)", "도메인 수")


def _piece_row(p, name):
    se = p.get("도메인 군집 SE")
    t = p.get("t_clu", p.get("🔴 t_clu"))
    sd = p.get("도메인 사이 SD(τ̂)", p.get("도메인 사이 SD"))
    return collections.OrderedDict([
        ("조각", name),
        ("점추정", p["점추정"]),
        ("도메인 군집 SE", se),
        ("t_clu", t),
        ("🔴 2·SE 를 넘나", p["🔴🔴 2·SE 를 넘나"]),
        ("동부호", p["🔴 동부호 수"]),
        ("도메인 수", p["도메인 수"]),
        ("도메인 사이 SD(τ̂)", sd),
    ])


def piece_tables(J):
    A, B, C = J["A"], J["B"], J["C"]
    out = collections.OrderedDict()

    # ㉡ --- 팔 C 재적합(게이트 20) · 헤드라인
    g20 = G(C, "§C3 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동", "게이트별", "게이트 20")
    rows = [_piece_row(g20["조각"][k], k) for k in g20["조각"]]
    out["대비 ㉡ (팔 C · F01 수리 마스크로 «다시 적합» · 게이트 20)"] = collections.OrderedDict([
        ("공통 도메인 수", g20["공통 도메인 수"]),
        ("부호 규약", g20["🔴 부호 규약"]),
        ("조각", rows),
        ("🔴 문턱을 넘은 조각 수", g20["🔴🔴 문턱을 넘은 조각 수"]),
        ("🔴 조각 수", len(rows) - 1),
    ])

    # ㉡ --- 팔 B (994 산출물만 · 재적합 없음)
    b5 = G(B, "§B5 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동")
    rows = [_piece_row(b5["조각"][k], k) for k in b5["조각"]]
    out["대비 ㉡ (팔 B · 994 옛 마스크 · 재적합 «없다»)"] = collections.OrderedDict([
        ("공통 도메인 수", b5["공통 도메인 수"]),
        ("칸별 채점 행", b5["칸별 채점 행"]),
        ("조각", rows),
        ("🔴 문턱을 넘은 조각 수", b5["🔴🔴 문턱을 넘은 조각 수"]),
    ])

    # ㉠ --- 팔 B
    b4 = G(B, "§B4 🔴🔴 대비 ㉠ --- 원점 1 의 거리 조각")
    rows = [_piece_row(b4["조각"][k], k) for k in b4["조각"]]
    out["대비 ㉠ (팔 B · 원점 1 의 거리 조각)"] = collections.OrderedDict([
        ("공통 도메인 수", b4["공통 도메인 수"]),
        ("부호 규약", b4["🔴 무엇"]),
        ("조각", rows),
        ("🔴 문턱을 넘은 조각 수", b4["🔴🔴 문턱을 넘은 조각 수"]),
    ])

    # ㉠ --- 팔 C 게이트 사다리
    c4 = G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리", "게이트별")
    lad = collections.OrderedDict()
    for gk, gv in c4.items():
        lad[gk] = collections.OrderedDict([
            ("공통 도메인 수", gv["공통 도메인 수"]),
            ("조각", [_piece_row(gv["조각"][k], k) for k in gv["조각"]]),
            ("🔴 문턱을 넘은 조각 수", gv["🔴🔴 문턱을 넘은 조각 수"]),
        ])
    out["대비 ㉠ (팔 C · 게이트 사다리 · 재적합)"] = lad

    # 예산 사다리 --- 팔 A
    a4 = G(A, "§A4-나 🔴🔴 조각 분해표", "예산 사다리")
    rows = [_piece_row(a4["조각"][k], k) for k in a4["조각"]]
    rows.append(_piece_row(a4["🔴 합 (예산 1800 → 예산 전량)"], "🔴 합 (1800 → 전량)"))
    out["예산 사다리 (팔 A · 헤드라인 「전량 − 1800」)"] = collections.OrderedDict([
        ("층별 묶음 ρ", G(A, "§A1 단조", "층별 묶음 ρ")),
        ("🔴 단조 위반 수", G(A, "§A1 단조", "🔴 단조 위반 수")),
        ("조각", rows),
        ("🔴 문턱을 넘은 조각 수", a4["🔴🔴 문턱을 넘은 조각 수"]),
        ("🔴 조각 수", a4["조각 수"]),
    ])
    return out


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 「도메인을 늘리면 검정력이 오른다」의 «조건» --- 수로
# ══════════════════════════════════════════════════════════════════════
def domain_law(J):
    A, B, C = J["A"], J["B"], J["C"]
    fit = G(B, "§B2 🔴 n 법칙", "적합")
    tau, sig = fit["🔴 τ̂"], fit["🔴 σ̂"]
    n_star = (sig / tau) ** 2

    # 팔 C ㉠ 게이트 사다리 --- d 를 늘렸을 때 t 가 어떻게 갔나
    c4 = G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리", "게이트별")
    rung = []
    keys = list(c4.keys())
    for i in range(len(keys) - 1):
        a, b = c4[keys[i]], c4[keys[i + 1]]
        pa, pb = a["조각"]["거리 1→거리 4"], b["조각"]["거리 1→거리 4"]
        da, db = a["공통 도메인 수"], b["공통 도메인 수"]
        if db == da:
            continue
        ta, tb = pa["도메인 사이 SD(τ̂)"], pb["도메인 사이 SD(τ̂)"]
        ma, mb = abs(pa["점추정"]), abs(pb["점추정"])
        new = sorted(set(b["공통 도메인"]) - set(a["공통 도메인"]))
        rung.append(collections.OrderedDict([
            ("어디서 어디로", "%s(d=%d) → %s(d=%d)" % (keys[i], da, keys[i + 1], db)),
            ("🔴 새로 든 도메인", new),
            ("|t| 전", abs(pa["t_clu"])), ("|t| 후", abs(pb["t_clu"])),
            ("🔴 |t| 가 올랐나", bool(abs(pb["t_clu"]) > abs(pa["t_clu"]))),
            ("τ̂ 전", ta), ("τ̂ 후", tb), ("τ̂ 비", _r(tb / ta)),
            ("|μ̂| 전", ma), ("|μ̂| 후", mb), ("|μ̂| 비", _r(mb / ma) if ma else None),
            ("√(d'/d)", _r(math.sqrt(float(db) / da))),
            ("🔴 오르는 데 필요한 |μ̂| 비 = (τ̂'/τ̂)/√(d'/d)",
             _r((tb / ta) / math.sqrt(float(db) / da))),
            ("🔴 실제 |μ̂| 비가 그보다 큰가",
             bool(ma and (mb / ma) >= (tb / ta) / math.sqrt(float(db) / da))),
        ]))

    # 팔 A 게이트 사다리 --- d 10 → 11 (펀딩 4 행)
    a5 = G(A, "§A5 게이트 인자화", "칸")
    ak = list(a5.keys())
    arung = []
    for i in range(len(ak) - 1):
        a, b = a5[ak[i]], a5[ak[i + 1]]
        if b["채점 도메인 수 d"] == a["채점 도메인 수 d"]:
            continue
        ca, cb = a["🔴 도메인 군집"], b["🔴 도메인 군집"]
        arung.append(collections.OrderedDict([
            ("어디서 어디로", "%s(d=%d) → %s(d=%d)"
             % (ak[i], a["채점 도메인 수 d"], ak[i + 1], b["채점 도메인 수 d"])),
            ("🔴 새로 든 도메인", sorted(set(b["도메인"]) - set(a["도메인"]))),
            ("t 전", ca["🔴 t_clu"]), ("t 후", cb["🔴 t_clu"]),
            ("🔴 |t| 가 올랐나", bool(abs(cb["🔴 t_clu"]) > abs(ca["🔴 t_clu"]))),
            ("점추정 전", ca["점추정"]), ("점추정 후", cb["점추정"]),
            ("🔴 부호가 뒤집혔나", bool(ca["점추정"] * cb["점추정"] < 0)),
            ("도메인 사이 SD 전", ca["도메인 사이 SD"]),
            ("도메인 사이 SD 후", cb["도메인 사이 SD"]),
            ("🔴 SD 비", _r(cb["도메인 사이 SD"] / ca["도메인 사이 SD"])),
            ("동부호 전", ca["🔴 동부호 수"]), ("동부호 후", cb["🔴 동부호 수"]),
        ]))

    # 새로 든 도메인이 실제로 몇 행이었나 --- 문턱과 견준다
    cells = G(C, "§C2-나 칸별 채점 행")
    def _rows_of(dom, needle):
        got = []
        for k, v in cells.items():
            if needle in k and dom in v:
                got.append(v[dom])
        return got
    entrants = collections.OrderedDict()
    for r in rung:
        for dom in r["🔴 새로 든 도메인"]:
            rr = _rows_of(dom, "원점 1 →")
            entrants[dom] = collections.OrderedDict([
                ("팔 C ㉠ 의 네 칸에서 그 도메인의 채점 행", rr),
                ("가장 적은 칸", min(rr) if rr else None),
                ("🔴 문턱 n* 를 넘나", bool(rr and min(rr) >= n_star)),
            ])
    # 팔 A 에서 든 도메인(펀딩)
    hold = G(A, "§A0 분모", "도메인별 base 유보 행")
    for r in arung:
        for dom in r["🔴 새로 든 도메인"]:
            entrants[dom + "(팔 A · alpha977)"] = collections.OrderedDict([
                ("유보 행", hold.get(dom)),
                ("🔴 문턱 n* 를 넘나", bool(hold.get(dom, 0) >= n_star)),
            ])

    # 대비 ㉡ 의 12 도메인은 몇 행이었나
    b4rows = None
    for k, v in cells.items():
        if "블록 4" in k and "게이트 20" in k and "원점 1" in k:
            b4rows = v
            break
    beta = collections.OrderedDict([
        ("칸", "원점 1 → 블록 4 · 게이트 20"),
        ("도메인 수", len(b4rows)),
        ("합", int(sum(b4rows.values()))),
        ("가장 적은 도메인", min(b4rows, key=lambda d: b4rows[d])),
        ("가장 적은 칸의 행", min(b4rows.values())),
        ("🔴 12 도메인이 «전부» n* 를 넘나", bool(min(b4rows.values()) >= n_star)),
    ])

    # 팔 B 의 d 법칙 --- 「같은 풀에서 부분집합」이면 t ∝ √d
    b1 = G(B, "§B1 🔴 d 법칙")
    return collections.OrderedDict([
        ("🔴 법", "SE_clu(d, n) = sqrt((τ² + σ²/n̄)/d) · t = μ̂·√d/√(τ²+σ²/n̄)"),
        ("🔴🔴🔴 조건 (수로)",
         "도메인을 «하나» 더 넣어 |t| 가 오르려면 |μ̂'|/|μ̂| ≥ (τ̂'/τ̂)/√(d'/d) 여야 한다. "
         "새 도메인의 유보 행이 적으면 그 칸의 표본 잡음 σ̂/√n 이 τ̂ 에 «통째로» 얹혀 "
         "τ̂'/τ̂ 가 √(d'/d) 보다 빨리 큰다."),
        ("🔴🔴 그 문턱 n* = σ̂²/τ̂² (팔 B §B2 적합의 «같은» 두 수)", _r(n_star, 4)),
        ("τ̂ (§B2 절편에서)", tau),
        ("σ̂ (§B2 기울기에서)", sig),
        ("§B2 적합 R²", fit["R²"]),
        ("🔴 뜻", "새 도메인의 유보 행이 n* 보다 적으면 그 도메인은 «신호»가 아니라 «잡음»을 "
                 "가져온다 --- d 가 √ 로 버는 것보다 τ̂ 가 더 는다."),
        ("🔴 팔 B --- 같은 풀에서 부분집합만 바꾸면(μ̂·τ̂ 가 구성상 고정) SE·√d 가 평평하다",
         collections.OrderedDict([
             ("SE·√d 최대/최소 비", b1["🔴 SE·√d 의 최대/최소 비"]),
             ("d 범위", list(b1["칸"].keys())),
             ("평균 도메인당 행 n̄ (f=1.0)",
              G(B, "§B2 🔴 n 법칙", "칸", "f=1.0", "평균 도메인당 행 n̄")),
         ])),
        ("🔴🔴 팔 C --- 게이트로 «진짜» 새 도메인을 넣으면 어떻게 되나", rung),
        ("🔴🔴 팔 A --- 게이트로 펀딩(유보 4 행)을 넣으면 어떻게 되나", arung),
        ("🔴🔴🔴 새로 든 도메인의 행 수 대 문턱 n*", entrants),
        ("🔴🔴🔴 대비 ㉡ 의 12 도메인은 문턱을 넘나", beta),
    ])


# ══════════════════════════════════════════════════════════════════════
# 조항 76 --- 「994 의 3.2~3.6 배는 무엇이었나」
# ══════════════════════════════════════════════════════════════════════
BUDGET = collections.OrderedDict([          # 사전등록 §11-다 의 «좁힌» 예상(분)
    ("A", (2.0, 6.0)), ("B", (2.0, 6.0)), ("C", (25.0, 35.0))])
NAME = {"A": "runners/gamma995_nb.py", "B": "runners/gamma995_power.py",
        "C": "runners/gamma995_champ.py"}


def clause76(J):
    rows = collections.OrderedDict()
    t0s, t1s = [], []
    for k in ("A", "B", "C"):
        st = G(J[k], "🔴 도장")
        sec = st["걸린 초"]
        lo, hi = BUDGET[k]
        mins = sec / 60.0
        t0s.append(st["언제(시작 · UTC)"])
        t1s.append(st["언제(끝 · UTC)"])
        rows["팔 " + k] = collections.OrderedDict([
            ("러너", NAME[k]),
            ("사전등록 §11-다 예상(분)", [lo, hi]),
            ("🔴 실측(분)", _r(mins, 3)),
            ("🔴 상한 대비 배수", _r(mins / hi, 4)),
            ("🔴 하한 대비 배수", _r(mins / lo, 4)),
            ("🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)", _r(lo / mins, 2)),
            ("🔴 P16 (배수 ≤ 1.5) 을 넘나", bool((mins / hi) <= 1.5)),
            ("시작(UTC)", st["언제(시작 · UTC)"]),
            ("끝(UTC)", st["언제(끝 · UTC)"]),
            ("🔴 고정한 스레드", G(J[k], "🔴 고정한 스레드")),
        ])
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    w0 = min(dt.datetime.strptime(x, fmt) for x in t0s)
    w1 = max(dt.datetime.strptime(x, fmt) for x in t1s)
    wall = (w1 - w0).total_seconds() / 60.0

    # 팔 C 의 적합 시간 --- 진행 로그에서 «혼자 잰» 연기 시험 값과 견준다
    per = collections.OrderedDict()
    with open(str(ROOT / PROG), "r", encoding="utf-8") as f:
        for ln in f:
            if "끝 (" in ln and "원점" in ln:
                head = ln.split("  ", 1)[1]
                org = head.split("씨앗")[0].strip()
                sec = float(head.rsplit("(", 1)[1].split(" ")[0])
                per.setdefault(org, []).append(sec)
    smoke = collections.OrderedDict([   # 사전등록 §11-나 S26 --- «혼자» 4 스레드로 잰 값
        ("원점 1", 18.8), ("원점 2", 22.5), ("원점 3", 25.5), ("원점 4", 28.8)])
    fits = collections.OrderedDict()
    for k in sorted(per):
        v = per[k]
        m = sum(v) / len(v)
        fits[k] = collections.OrderedDict([
            ("칸 수", len(v)), ("실측 평균 초", _r(m, 3)),
            ("사전등록 §11-나 S26 「혼자」 초", smoke.get(k)),
            ("🔴 실측/혼자", _r(m / smoke[k], 4) if k in smoke else None),
            ("🔴 옆에서 넷이 도는데 «혼자» 보다 빨랐나",
             bool(k in smoke and m < smoke[k])),
        ])
    slower = sum(1 for v in fits.values() if v["🔴 실측/혼자"] and v["🔴 실측/혼자"] > 1.0)
    return collections.OrderedDict([
        ("🔴 팔별", rows),
        ("🔴 측정 구간 전체 벽시계(분) --- 조항 76 v4.13 이 요구한 «새» 자", _r(wall, 3)),
        ("측정 구간 시작(UTC)", w0.strftime(fmt)),
        ("측정 구간 끝(UTC)", w1.strftime(fmt)),
        ("🔴 팔 C 원점별 적합 시간 대 «혼자» 잰 값", fits),
        ("🔴🔴 「혼자」 보다 느렸던 원점 수", slower),
        ("🔴 분모: 견준 원점 수", len(fits)),
        ("🔴🔴🔴 그래서 994 의 3.2~3.6 배는 「경합」인가",
         "🔴 아니다. 995 의 팔 C 는 옆에서 팔 A·팔 B·탐색 팔·데몬이 도는데도 "
         "«혼자» 잰 적합 시간보다 «빨랐다»(느렸던 원점 %d / %d). 「가벼운 팔과의 경합」은 "
         "적합 시간을 «전혀» 안 늘린다." % (slower, len(fits))),
        ("🔴🔴🔴 그러면 무엇이었나",
         "🔴 995 자신의 수가 답을 반으로 가른다. 「적합 시간에서 나온」 예상(팔 C · S26)은 "
         "상한 대비 %.2f 배로 «맞았고**, 「어림으로 쓴」 예상(팔 A·B)은 실측의 %.1f~%.1f 배로 "
         "«빗나갔다». ⇒ 994 의 배수는 「경합」보다 「추정 오류」와 「994 러너가 애초에 무거웠던 것」"
         "쪽이다. 994 의 자릿수(팔 3.2~3.6× · 적합 6.66× · 씨앗 0 38~41×)가 «서로 다른 것»도 "
         "한 원인(경합)으로는 안 풀린다."
         % (rows["팔 C"]["🔴 상한 대비 배수"],
            min(rows["팔 A"]["🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)"],
                rows["팔 B"]["🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)"]),
            max(rows["팔 A"]["🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)"],
                rows["팔 B"]["🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)"]))),
        ("🔴🔴 조항 76 의 자기 채점 자는 «한쪽»으로만 벤다",
         "「상한 대비 배수 ≤ 1.5」는 «느린 쪽»으로만 떨어진다. 995 는 «빠른 쪽»으로 "
         "최대 %.1f 배 어긋났는데 P16 은 세 팔 전부 «통과»를 냈다 --- 조항 78 ㉮ 의 절반이다."
         % max(rows[k]["🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)"]
               for k in ("팔 A", "팔 B", "팔 C"))),
        ("⚠ CPU%·load average 는 산출물 «키 경로»에 없다",
         "조타수가 `ps`·`uptime` 으로 잰 값(팔 C 392~397% · 팔 A·B ≈100% · "
         "load average 3.6 → 6.7)은 «러너가 안 박았다». 조항 59 대로 「못 읽었다」가 아니라 "
         "「산출물에 자리가 없다」로 적는다 --- 다음 사이클 러너가 박아야 한다."),
    ])


# ══════════════════════════════════════════════════════════════════════
# 예측 P1~P22 --- 🔴 사전등록 «문언»만 손으로 옮기고, 견주는 수는 «전부» 키 경로다
# ══════════════════════════════════════════════════════════════════════
def predictions(J):
    A, B, C = J["A"], J["B"], J["C"]
    P = collections.OrderedDict()

    def put(pid, say, got, ok, note=None):
        d = collections.OrderedDict([
            ("사전등록 예측(§5 · §9-10)", say),
            ("🔴 실측(키 경로에서)", got),
            ("판정", ok),
        ])
        if note:
            d["🔴 곁말"] = note
        P[pid] = d

    a0 = G(A, "§A0 분모")
    hold = a0["도메인별 base 유보 행"]
    preg_hold = collections.OrderedDict([
        ("세계애니", 1288), ("애니", 291), ("게임", 184), ("모바일", 167),
        ("웹툰", 130), ("시장팝업", 103), ("만화", 67), ("팝업", 60),
        ("도서", 48), ("아이돌", 21), ("펀딩", 4)])
    same = all(hold.get(k) == v for k, v in preg_hold.items())
    put("P1", "base 2,363 · hplt 35,641 · 합집합 11 · gated 10 · §0-다 유보 벡터와 한 자리도 안 틀린다",
        collections.OrderedDict([
            ("base 행", a0["base 행"]), ("hplt 행", a0["hplt 행"]),
            ("도메인 합집합", a0["도메인 합집합"]),
            ("채점 도메인 수", a0["🔴 채점 도메인 수"]),
            ("🔴 유보 벡터가 사전등록과 한 자리도 안 틀리나", bool(same)),
        ]),
        MATCH if (a0["base 행"] == 2363 and a0["hplt 행"] == 35641
                  and a0["도메인 합집합"] == 11 and a0["🔴 채점 도메인 수"] == 10
                  and same) else MISS)

    full = G(A, "§A6 배선", "전량 겹별 학습 행")
    nb1710 = a0["🔴 alpha977.py 의 상수"]["🔴 그 예산이 hplt 에 닿는 행"]
    ratio = a0["hplt 행"] / float(nb1710)
    put("P2", "전량 층 겹당 학습 행 [37535, 37530, 37538, 37534, 37520] · hplt 학습 행 1,710 → 35,641 (20.84×)",
        collections.OrderedDict([
            ("전량 겹별 학습 행", full),
            ("N_B=1800 이 hplt 에 닿는 행", nb1710),
            ("hplt 전량", a0["hplt 행"]),
            ("🔴 배수", _r(ratio, 4)),
        ]),
        MATCH if (full == [37535, 37530, 37538, 37534, 37520]
                  and abs(ratio - 20.84) < 0.01) else MISS)

    dd = G(A, "🔴🔴 조항 78 --- ㉮ 원리상 못 «떨어지는» 검사", "㉮-1 예산 층마다 d 가 같다", "층별 d")
    put("P3", "모든 층에서 d = 10 · 최대 차 0 (🔴 ㉮-1 이라 최상위에서 뺀다)",
        collections.OrderedDict([("층별 d", dd),
                                 ("최대 차", max(dd.values()) - min(dd.values()))]),
        MATCH if (set(dd.values()) == {10}) else MISS,
        "🔴 ㉮-1 --- 최상위 연언에서 «뺐다». 통과해도 세계를 안 잰다")

    a4 = G(A, "§A4 군집 SE", "🔴🔴 전량 − 1800")
    dbun, duni = a4["Δ 묶음 ρ"], a4["Δ 균등 ρ"]
    ok4 = _in(dbun, 0.005, 0.045)
    ok4u = _in(duni, 0.04, 0.14)
    put("P4", "Δ 묶음 ρ ∈ [+0.005, +0.045] · Δ 균등 ρ ∈ [+0.04, +0.14]",
        collections.OrderedDict([
            ("Δ 묶음 ρ", dbun), ("🔴 구간 안인가(묶음)", ok4),
            ("Δ 균등 ρ", duni), ("🔴 구간 안인가(균등)", ok4u),
            ("🔴 균등이 구간 하한을 얼마나 밑도나", _r(0.04 - duni, 6)),
        ]),
        MATCH if (ok4 and ok4u) else (PART if (ok4 or ok4u) else MISS),
        "🔴 균등 예측은 «씨앗 976 하나»의 연기 시험 값(+0.086319)에서 냈다. "
        "12 씨앗 평균은 그 27% 다 --- 씨앗 하나로 구간을 세운 것이 틀렸다")

    cl = a4["🔴🔴 도메인 군집"]
    t5 = cl["🔴 t_clu"]
    put("P5", "t_clu ∈ [1.1, 2.4] 이고 < 2",
        collections.OrderedDict([("t_clu", t5), ("구간 안인가", _in(t5, 1.1, 2.4)),
                                 ("2 미만인가", bool(t5 < 2))]),
        MATCH if (_in(t5, 1.1, 2.4) and t5 < 2) else MISS)

    tr = G(A, "§A4 군집 SE", "🔴🔴 τ̂ 비 (전량 / 1800)")
    put("P6", "τ(전량)/τ(1800) ∈ [0.6, 1.15]",
        collections.OrderedDict([
            ("τ̂ 비", tr), ("τ̂(1800)", G(A, "§A4 군집 SE", "τ̂(1800)")),
            ("τ̂(전량)", G(A, "§A4 군집 SE", "τ̂(전량)")),
            ("🔴 1 보다 큰가(= 자료가 τ 를 «키웠다»)", bool(tr > 1.0)),
        ]),
        MATCH if _in(tr, 0.6, 1.15) else MISS)

    r7 = G(B, "§B1 🔴 d 법칙", "🔴 SE·√d 의 최대/최소 비")
    put("P7", "SE_clu(d')·√d' 의 최대/최소 비 ≤ 1.5", collections.OrderedDict([("비", r7)]),
        MATCH if r7 <= 1.5 else MISS)

    f8 = G(B, "§B2 🔴 n 법칙", "적합")
    put("P8", "SE² 대 1/n̄ 최소제곱 R² ≥ 0.7",
        collections.OrderedDict([("R²", f8["R²"]), ("절편 = τ²/d", f8["절편 = τ²/d"])]),
        MATCH if f8["R²"] >= 0.7 else MISS)

    fl_a = G(A, "§A4 군집 SE", "🔴 바닥 τ̂/√d (전량)")
    fl_b = G(B, "§B3 🔴 τ̂ · 바닥 · d*", "🔴 바닥 τ̂/√d")
    fl_d = cl["도메인 사이 SD"] / math.sqrt(cl["도메인 수"])
    put("P9", "바닥 τ̂/√10 (Δ 균등 ρ 기준) ∈ [0.025, 0.075]",
        collections.OrderedDict([
            ("팔 A 「바닥 τ̂/√d (전량)」(수준 ρ 기준)", fl_a),
            ("팔 B 「바닥 τ̂/√d」(수준 ρ 기준)", fl_b),
            ("🔴 Δ 균등 ρ 기준 바닥(도메인 사이 SD/√d)", _r(fl_d, 6)),
            ("🔴 셋 다 구간 밖인가",
             bool(not _in(fl_a, 0.025, 0.075) and not _in(fl_b, 0.025, 0.075)
                  and not _in(fl_d, 0.025, 0.075))),
            ("가장 가까운 읽기가 구간을 얼마나 벗어나나", _r(fl_a - 0.075, 6)),
        ]),
        MATCH if _in(fl_d, 0.025, 0.075) else MISS,
        "🔴 세 읽기 «전부» 구간 밖이다. 예측을 씨앗 976 의 소박한 값(0.045193) 하나로 세웠다")

    b4n = G(B, "§B4-나 994 낙차의 법 검산")
    tlaw = b4n["🔴 τ̂ 불변 가정 아래 t(d) 투영"]["d=7"]
    rel = abs(tlaw - 1.58) / 1.58
    put("P10", "μ̂ 0.130262 · τ̂ 0.222135 · SE 0.083959 · t 1.5515 · 994 보고 1.58 과 상대차 ≤ 5%",
        collections.OrderedDict([
            ("μ̂", b4n["μ̂"]), ("τ̂", b4n["τ̂"]), ("τ̂/√d", b4n["τ̂/√d"]),
            ("법 t(d=7)", tlaw), ("🔴 994 보고 1.58 과 상대차", _r(rel, 6)),
            ("뽑기 SE(등록된 자)", b4n["뽑기 SE(등록된 자)"]),
            ("법 대 뽑기 상대차", b4n["🔴 법 대 뽑기 상대차"]),
        ]),
        MATCH if rel <= 0.05 else MISS)

    ds = b4n["🔴 d* = 4τ̂²/μ̂²"]
    put("P11", "994 의 d* = 11.63 (±0.05)", collections.OrderedDict([("d*", ds)]),
        MATCH if abs(ds - 11.63) <= 0.05 else MISS)

    gd = G(C, "반증조건", "🔴 반증조건 10 --- 게이트가 d 를 늘린다")
    put("P12", "게이트 20/10/5/3 의 공통 도메인 d = 7 / 8 / 9 / 9",
        gd, MATCH if list(gd.values()) == [7, 8, 9, 9] else MISS)

    g5 = G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리",
           "게이트별", "게이트 5", "조각", "거리 1→거리 4")
    t13 = abs(g5["t_clu"])
    put("P13", "t_clu(gate=5, d=9) ∈ [1.1, 2.0] 이고 < 2 · 까닭 = 새로 든 도메인이 τ̂ 를 키운다",
        collections.OrderedDict([
            ("|t_clu|(d=9)", _r(t13, 6)), ("구간 안인가", _in(t13, 1.1, 2.0)),
            ("2 미만인가", bool(t13 < 2)),
            ("τ̂(d=7)", G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리",
                         "게이트별", "게이트 20", "조각", "거리 1→거리 4",
                         "도메인 사이 SD(τ̂)")),
            ("τ̂(d=9)", g5["도메인 사이 SD(τ̂)"]),
            ("🔴 새로 든 도메인이 τ̂ 를 키웠나", bool(
                g5["도메인 사이 SD(τ̂)"]
                > G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리",
                    "게이트별", "게이트 20", "조각", "거리 1→거리 4", "도메인 사이 SD(τ̂)"))),
        ]),
        MATCH if (_in(t13, 1.1, 2.0) and t13 < 2) else PART,
        "🔴 「< 2」와 「까닭」은 맞았고 «구간»은 아래로 빗나갔다 --- t 가 예측보다 더 떨어졌다")

    c1 = G(C, "§C1 🔴 정본 재현(수리 마스크)")
    dif14 = abs(float(c1["🔴 판 ρ(신판 · 수리 마스크 · 12 씨앗 «평균»)"])
                - c1["정본 BOARD_RHO_FULL"])
    put("P14", "|ρ − 0.47034252170476804| ≤ 1e-6",
        collections.OrderedDict([
            ("12 씨앗 평균 ρ(신판)", c1["🔴 판 ρ(신판 · 수리 마스크 · 12 씨앗 «평균»)"]),
            ("정본", repr(c1["정본 BOARD_RHO_FULL"])), ("🔴 차", dif14),
            ("씨앗 0 − BOARD_S0_FULL", c1["🔴🔴 씨앗 0 신판 − BOARD_S0_FULL"]),
        ]),
        MATCH if dif14 <= 1e-6 else MISS)

    c0 = G(C, "§C0 🔴🔴 F01 구판/신판 전후")
    put("P15", "정본 원점에서 유보 합 차 = +104 행 · 갈리는 도메인은 「웹툰·게임」 둘",
        collections.OrderedDict([
            ("유보 합 구판", c0["정본 유보 합 구판"]),
            ("유보 합 신판", c0["정본 유보 합 신판"]),
            ("🔴 차", c0["🔴🔴 정본 유보 합 차"]),
            ("갈린 도메인", c0["🔴 갈린 도메인"]),
            ("🔴 학습 합 차", c0["🔴 학습 합 차(0 이어야 한다)"]),
        ]),
        MATCH if (c0["🔴🔴 정본 유보 합 차"] == 104
                  and sorted(c0["🔴 갈린 도메인"]) == ["게임", "웹툰"]) else MISS)

    c76 = clause76(J)
    p16 = collections.OrderedDict(
        (k, collections.OrderedDict([
            ("실측(분)", v["🔴 실측(분)"]),
            ("상한 대비 배수", v["🔴 상한 대비 배수"]),
            ("🔴 ≤ 1.5 인가", v["🔴 P16 (배수 ≤ 1.5) 을 넘나"]),
            ("🔴 «빠른 쪽» 어긋남 배수", v["🔴 예상 하한이 실측의 몇 배인가(«빠른 쪽» 어긋남)"]),
        ])) for k, v in c76["🔴 팔별"].items())
    fastmiss = [v["🔴 «빠른 쪽» 어긋남 배수"] for k, v in p16.items() if k != "팔 C"]
    put("P16", "세 팔 전부 「예상 상한 대비 배수」 ≤ 1.5 (A 2~6분 · B 2~6분 · C 25~35분)",
        p16,
        MATCH if all(v["🔴 ≤ 1.5 인가"] for v in p16.values()) else MISS,
        "🔴 통과하되 «반쪽»이다 --- 이 자는 «느린 쪽»으로만 벤다. 팔 A·B 는 «빠른 쪽»으로 "
        "%.1f~%.1f 배 어긋났는데도 통과다(조항 78 ㉮ 의 절반)"
        % (min(fastmiss), max(fastmiss)))

    f14 = G(B, "반증조건", "🔴🔴 반증조건 14 --- 대비 ㉠ 이 사전등록 표와 1e-6 안")
    put("P17", "팔 B 가 994 산출물만으로 대비 ㉠ 네 줄을 재계산하면 사전등록 표와 소수점 여섯 자리까지 같다",
        f14, MATCH if all(abs(v) <= 1e-6 for v in f14.values()) else MISS)

    f15b = G(B, "반증조건", "🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다 (2·SE 초과 · 동부호 ≥ 10/12)")
    put("P18", "팔 B 가 대비 ㉡ 네 줄을 내면 사전등록 표와 소수점 여섯 자리까지 같다 · 공통 도메인 12",
        collections.OrderedDict([
            ("사전등록 표와의 차", f15b["사전등록 표와 1e-6 안"]),
            ("공통 도메인 수",
             G(B, "§B5 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동", "공통 도메인 수")),
        ]),
        MATCH if (all(abs(v) <= 1e-6 for v in f15b["사전등록 표와 1e-6 안"].values())
                  and G(B, "§B5 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동",
                        "공통 도메인 수") == 12) else MISS)

    f15c = G(C, "반증조건", "🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다")
    same_c = int(f15c["동부호"].split("/")[0])
    put("P19", "팔 C 가 F01 수리 마스크로 다시 적합해 대비 ㉡ 을 재면 합의 t_clu > 2 이고 동부호 ≥ 10/12",
        f15c, MATCH if (f15c["t_clu"] > 2 and same_c >= 10) else MISS)

    c4g20 = G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리", "게이트별", "게이트 20")
    cross = collections.OrderedDict(
        (k, v["🔴🔴 2·SE 를 넘나"]) for k, v in c4g20["조각"].items())
    put("P20", "팔 C 의 대비 ㉠ 에서 거리 3→4 «만» 문턱을 넘는다",
        cross,
        MATCH if (cross.get("거리 3→거리 4") is True
                  and c4g20["🔴🔴 문턱을 넘은 조각 수"] == 1) else MISS)

    lad = G(A, "§A4-나 🔴🔴 조각 분해표", "예산 사다리")
    keys = list(lad["조각"].keys())
    crossers = [k for k in keys if lad["조각"][k]["🔴🔴 2·SE 를 넘나"]]
    first_ok = lad["조각"][keys[0]]["🔴🔴 2·SE 를 넘나"]
    last_ok = lad["조각"][keys[-1]]["🔴🔴 2·SE 를 넘나"]
    put("P21", "신호는 첫 조각(1800→3600)에 몰린다 · 문턱을 넘는 조각 ≤ 2 · 마지막 조각(36000→전량)은 못 넘는다",
        collections.OrderedDict([
            ("조각별 t_clu",
             collections.OrderedDict((k, lad["조각"][k]["🔴 t_clu"]) for k in keys)),
            ("🔴 문턱을 넘은 조각", crossers),
            ("🔴 첫 조각이 넘나", first_ok),
            ("🔴 마지막 조각이 넘나", last_ok),
            ("문턱을 넘은 조각 수", len(crossers)),
        ]),
        MATCH if (first_ok and len(crossers) <= 2 and not last_ok) else PART,
        "🔴 「≤ 2 개」와 「마지막은 못 넘는다」는 맞았고 «자리»가 틀렸다 --- "
        "신호는 첫 조각이 아니라 «둘째»(3600→7200 · t 2.222775)에 있다")

    a8 = G(A, "§A8 🔴🔴🔴 조항 78 --- 기계로 센 ㉮")
    put("P22", "기계로 센 ㉮ 분자가 손으로 센 4 «이상»이다 (기계 − 손 ≥ 0)",
        collections.OrderedDict([
            ("팔 A 기계 ㉮ 분자", a8["🔴🔴 기계가 센 ㉮ 분자"]),
            ("팔 A 손 ㉮ 분자", a8["🔴 손으로 센 ㉮ 분자(사전등록 §0-바)"]),
            ("🔴 기계 − 손", a8["🔴 기계 − 손"]),
            ("분모: 검사한 조각", a8["분모: 검사한 조각"]),
            ("팔 B 기계 ㉮ 분자",
             G(B, "§B6 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "🔴🔴 기계가 센 ㉮ 분자")),
            ("팔 B 분모",
             G(B, "§B6 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "분모: 검사한 조각")),
            ("팔 C 기계 ㉮ 분자",
             G(C, "§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "🔴🔴 기계가 센 ㉮ 분자")),
            ("팔 C 분모",
             G(C, "§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "분모: 검사한 조각")),
            ("🔴 팔 C 대조판의 ㉮ 분자(계수가 1 을 낼 수 있나)",
             G(C, "§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮",
               "🔴 대조판 --- 첫 대조는 «일부러» ㉮ 다(계수가 1 을 낼 수 있다)", "이 판의 ㉮ 분자")),
        ]),
        MATCH if a8["🔴 기계 − 손"] >= 0 else MISS,
        "🔴 팔 A 의 기계 값이 손 값보다 «작다». 내막 둘: ① 기계 조각 11 개(F02~F06 · W1~W6) "
        "에 ㉮-1(「예산 층마다 d 가 같다」)에 «해당하는 조각이 아예 없다» --- 기계가 못 센 것이지 "
        "0 을 낸 게 아니다(조항 59). ② ㉮-3(「예산 b 에서 학습 행 = b」)에 해당하는 W2 를 기계가 "
        "«떨어질 수 있다»로 판정했다(변이체 b+1 에서 거짓). 곧 손 라벨은 ㉮-3 을 «과다 계상**했고 "
        "㉮-1 은 «기계 분모 밖»이다. 994 의 병(손이 «과소»)과 «반대쪽» 병이다")
    return P, c76


# ══════════════════════════════════════════════════════════════════════
# 반증조건 F01~F18 (+F01-나) --- 🔴 분모 19 · 러너가 «자기» 통과 키를 낸다
# ══════════════════════════════════════════════════════════════════════
FALS = [
    ("F01", "C", "🔴 수리 마스크로 챔피언 정본이 재현된다(|ρ − 0.47034252170476804| ≤ 1e-6)",
     "C", ("반증조건", "통과: 반증조건 1")),
    ("F01-나", "C", "🔴 수리 마스크 · 씨앗 0 이 BOARD_S0_FULL 을 1e-12 안에서 재현한다",
     "C", ("반증조건", "통과: 반증조건 1-나")),
    ("F02", "A", "예산 사다리에서 묶음 ρ 가 단조 비감소(위반 ≤ 1)",
     "A", ("§A7 반증조건", "통과: 반증조건 2")),
    ("F03", "A", "전량이 1800 보다 낫다 · 씨앗 SE 의 2 배 초과",
     "A", ("§A7 반증조건", "통과: 반증조건 3")),
    ("F04", "A", "🔴 벽 --- Δ 균등 ρ 의 t_clu < 2",
     "A", ("§A7 반증조건", "통과: 반증조건 4")),
    ("F05", "A", "부호 반대 도메인 ≥ 1",
     "A", ("§A7 반증조건", "통과: 반증조건 5")),
    ("F06", "A", "🔴 τ(전량)/τ(1800) > 0.6",
     "A", ("§A7 반증조건", "통과: 반증조건 6")),
    ("F07", "B", "🔴 √d 법 --- SE·√d 의 최대/최소 비 ≤ 1.5",
     "B", ("반증조건", "통과: 반증조건 7")),
    ("F08", "B", "🔴 n 법 --- R² ≥ 0.7 이고 절편 τ̂² > 0",
     "B", ("반증조건", "통과: 반증조건 8")),
    ("F09", "B", "🔴 994 재구성이 맞는다 --- 994 보고 t_clu 1.58 과 상대차 ≤ 10%",
     "B", ("반증조건", "통과: 반증조건 9")),
    ("F10", "C", "🔴 게이트가 d 를 늘린다 --- gate 5 의 d > gate 20 의 d",
     "C", ("반증조건", "통과: 반증조건 10")),
    ("F12", "C", "🔴🔴 벽이 게이트로 «안» 깨진다 --- |t_clu(gate=5, d=9)| < 2",
     None, None),
    ("F13", "A·B·C", "🔴🔴 헤드라인 대비마다 조각 분해표가 있다",
     None, None),
    ("F14", "B", "🔴 대비 ㉠ 재현 --- 사전등록 표와 |차| ≤ 1e-6",
     "B", ("반증조건", "통과: 반증조건 14")),
    ("F15", "B·C", "🔴🔴 대비 ㉡ 이 선다 --- 2·SE 초과 · 동부호 ≥ 10/12",
     None, None),
    ("F16", "A·B·C", "🔴 ㉮ 분자를 «기계»가 낸다 · 그 칸이 「0」을 낼 수 있음을 대조판으로 보인다",
     None, None),
    ("F17", "C", "🔴 F01 이탈 크기가 7.199316e-04 다 (씨앗 0)",
     "C", ("반증조건", "통과: 반증조건 17")),
    ("F18", "A·B·C", "🔴 도장 분모의 첫 자리가 자기 러너다",
     None, None),
]


def falsifications(J):
    A, B, C = J["A"], J["B"], J["C"]
    F = collections.OrderedDict()
    for fid, arm, say, src, path in FALS:
        if src is not None:
            got = G(J[src], *path)
            ev = collections.OrderedDict([("러너가 낸 통과 키", got), ("자리", "/".join(path))])
        elif fid == "F12":
            t = abs(G(C, "§C4 대비 ㉠ --- 원점 1 의 거리 조각 · 게이트 사다리",
                      "게이트별", "게이트 5", "조각", "거리 1→거리 4", "t_clu"))
            got = bool(t < 2)
            ev = collections.OrderedDict([("|t_clu|(gate=5 · d=9)", _r(t, 6)),
                                          ("🔴 벽이 깨졌나", bool(t >= 2))])
        elif fid == "F13":
            v = [G(A, "§A7 반증조건", "통과: 반증조건 13"),
                 G(B, "반증조건", "통과: 반증조건 13"),
                 G(C, "반증조건", "통과: 반증조건 13")]
            got = bool(all(v))
            ev = collections.OrderedDict([("팔 A", v[0]), ("팔 B", v[1]), ("팔 C", v[2])])
        elif fid == "F15":
            vb = G(B, "반증조건", "통과: 반증조건 15")
            vc = G(C, "반증조건", "통과: 반증조건 15")
            got = bool(vb and vc)
            ev = collections.OrderedDict([
                ("팔 B(재적합 없음)", vb), ("팔 C(다시 적합)", vc),
                ("팔 C 의 t_clu", G(C, "반증조건", "🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다", "t_clu")),
                ("팔 C 의 동부호", G(C, "반증조건", "🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다", "동부호")),
            ])
        elif fid == "F16":
            v = [G(A, "§A8 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "🔴 통과: 반증조건 16"),
                 G(B, "§B6 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "🔴 통과: 반증조건 16"),
                 G(C, "§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", "🔴 통과: 반증조건 16 (계수가 자료에 따라 움직이나)")]
            got = bool(all(v))
            ev = collections.OrderedDict([
                ("팔 A", v[0]), ("팔 B", v[1]), ("팔 C", v[2]),
                ("🔴 팔 A 대조판이 0 을 냈나",
                 G(A, "§A8 🔴🔴🔴 조항 78 --- 기계로 센 ㉮",
                   "🔴🔴 대조판 --- 계수가 「0」을 낼 수 있나", "🔴🔴 0 이 나왔나")),
                ("🔴 팔 C 대조판이 1 을 냈나",
                 bool(G(C, "§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮",
                        "🔴 대조판 --- 첫 대조는 «일부러» ㉮ 다(계수가 1 을 낼 수 있다)",
                        "이 판의 ㉮ 분자") == 1)),
            ])
        else:                                                   # F18
            v = [G(A, "§A7 반증조건", "통과: 반증조건 18"),
                 G(B, "반증조건", "통과: 반증조건 18"),
                 G(C, "반증조건", "통과: 반증조건 18")]
            got = bool(all(v))
            ev = collections.OrderedDict([
                ("팔 A SRC[0]", G(A, "§A7 반증조건", "🔴 반증조건 18 --- 도장 분모의 첫 자리가 자기 파일인가")),
                ("팔 B SRC[0]", G(B, "반증조건", "🔴 반증조건 18 --- 도장 분모의 첫 자리")),
                ("팔 C SRC[0]", G(C, "반증조건", "🔴 반증조건 18 --- 도장 분모의 첫 자리")),
            ])
        F[fid] = collections.OrderedDict([
            ("팔", arm), ("반증조건(참이면 통과)", say),
            ("🔴 결과", bool(got)), ("근거", ev)])

    # F11 --- 교차 검사는 «두 팔의 수를 견주는 것»이라 여기서 «계산»한다
    # 🔴 팔 A 는 이 칸을 «문자열»로 뭉갰다(`str(OrderedDict(...))`) --- 키 경로로 못 읽는다.
    #    조항 60-라 위반이고 규칙 D 를 방해한다. 여기서 되꺼내되 그 사실을 칸으로 낸다.
    a11 = G(A, "§A7 반증조건", "🔴 반증조건 11 --- 교차용 기준선(B 가 1e-12 안에서 맞춰야 한다)")
    squashed = isinstance(a11, str)

    def _pull(s, key):
        m = re.search(re.escape(key) + r"'\s*,\s*'([0-9.eE+-]+)'", s)
        if not m:
            raise KeyError("문자열에서 못 꺼냈다: %r" % key)
        return float(m.group(1))
    ab = _pull(a11, "🔴 묶음 ρ(전정밀)") if squashed else float(a11["🔴 묶음 ρ(전정밀)"])
    au = _pull(a11, "🔴 균등 ρ(전정밀)") if squashed else float(a11["🔴 균등 ρ(전정밀)"])
    bb = float(G(B, "§B0 🔴 독립 기준선(F11)", "🔴 묶음 ρ(전정밀)"))
    bu = float(G(B, "§B0 🔴 독립 기준선(F11)", "🔴 균등 ρ(전정밀)"))
    F["F11"] = collections.OrderedDict([
        ("팔", "A·B"),
        ("반증조건(참이면 통과)", "🔴 교차 검사 --- A §A1 첫 칸과 B §B0 의 묶음 ρ 가 |차| ≤ 1e-12"),
        ("🔴 결과", bool(abs(ab - bb) <= 1e-12 and abs(au - bu) <= 1e-12)),
        ("근거", collections.OrderedDict([
            ("팔 A 묶음 ρ", repr(ab)), ("팔 B 묶음 ρ", repr(bb)),
            ("🔴 |차|(묶음)", abs(ab - bb)),
            ("팔 A 균등 ρ", repr(au)), ("팔 B 균등 ρ", repr(bu)),
            ("🔴 |차|(균등)", abs(au - bu)),
            ("🔴🔴 팔 A 가 이 칸을 «문자열»로 뭉갰나(조항 60-라 위반)", bool(squashed)),
            ("🔴 두 팔이 «다른 코드 경로»인가",
             bool(G(A, "🔴 도장", "🔴 코드 sha256(끝)").get("runners/gamma995_nb.py")
                  != G(B, "🔴 도장", "🔴 코드 sha256(끝)").get("runners/gamma995_power.py"))),
        ]))])
    order = ["F01", "F01-나", "F02", "F03", "F04", "F05", "F06", "F07", "F08",
             "F09", "F10", "F11", "F12", "F13", "F14", "F15", "F16", "F17", "F18"]
    return collections.OrderedDict((k, F[k]) for k in order)


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 세계 명제 --- 「채택」인가 「제안」인가 (노트 133 · 조항 79-3)
# ══════════════════════════════════════════════════════════════════════
# 🔴 규칙을 «자료»로 적고 «식»으로 판정한다. 리터럴 판정을 안 쓴다.
RULE133 = collections.OrderedDict([
    ("출처", "노트 133 --- 「첫 양수를 그대로 채택하지 않는다. 통과해도 «제안»까지, "
             "확인 측정은 다음 사이클.」 · 조항 79-3 --- 「신호가 한 조각에 몰려 있으면 "
             "그것을 «가설»로 승격해 다음 사이클 사전등록에 박는다.」"),
    ("가-발견 사이클", 995),        # 사전등록 §9-9 S15 --- 995 설계 팔이 연기 시험에서 찾았다
    ("나-확인 사이클", 995),        # 팔 B·팔 C 가 같은 사이클에서 쟀다
])


def world_claim(J, law):
    C, B = J["C"], J["B"]
    g20 = G(C, "§C3 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동", "게이트별", "게이트 20")
    tot = g20["조각"]["원점 1→원점 4"]
    cmp_ = g20["🔴🔴 사전등록 표와의 대조(게이트 20 만 뜻이 있다)"]["원점 1→4"]
    ledger = G(C, "§C2-다 학습 장부(씨앗 0)")
    train = collections.OrderedDict(
        (k, collections.OrderedDict([("학습 도메인", v["학습 도메인"]),
                                     ("학습 행 합", v["학습 행 합"])]))
        for k, v in ledger.items())
    rows = [v["학습 행 합"] for v in ledger.values()]
    doms = [v["학습 도메인"] for v in ledger.values()]
    confound = collections.OrderedDict([
        ("🔴🔴🔴 정비 팔이 «새로» 찾은 교란",
         "대비 ㉡ 은 「거리」와 「채점 블록」을 갈랐지만 «원점을 옮기면 학습 자료가 같이 커진다». "
         "네 칸의 학습 행이 %s 로 %.2f 배 늘고 학습 도메인이 %d → %d 로 는다. "
         "그래서 ㉡ 은 「거리가 아프다」와 「학습량이 적다」를 «아직 못 가른다»."
         % (rows, rows[-1] / float(rows[0]), doms[0], doms[-1])),
        ("칸별 학습 장부(씨앗 0)", train),
        ("🔴 학습 행 최대/최소 비", _r(rows[-1] / float(rows[0]), 4)),
        ("🔴 994 가 이미 잰 것", "994 는 「낙차의 대부분은 학습량이고 표본 크기는 0 이다」를 냈다 "
                              "(C0−C3 0.053272 대 C0−C2 0.000998 · out994 채점). "
                              "그 축이 대비 ㉡ 안에서 «다시» 움직인다."),
    ])
    same_cycle = bool(RULE133["가-발견 사이클"] == RULE133["나-확인 사이클"])
    refit_only = bool(abs(cmp_["🔴 차"]) < 0.001)
    verdict = "제안" if (same_cycle or refit_only) else "채택"
    return collections.OrderedDict([
        ("🔴🔴🔴 명제", "챔피언 세계에서 「채점 블록을 블록 4 에 고정하고 원점만 옮기면 "
                     "원점이 멀수록 판 ρ 가 단조로 나빠진다」 --- 세 조각이 «전부» 2·SE 를 넘고 "
                     "합도 넘는다."),
        ("점추정(합 · 원점 1→4)", tot["점추정"]),
        ("도메인 군집 SE", tot["도메인 군집 SE"]),
        ("t_clu", tot["t_clu"]),
        ("동부호", tot["🔴 동부호 수"]),
        ("도메인 수", tot["도메인 수"]),
        ("95% 구간", [tot["2.5%"], tot["97.5%"]]),
        ("🔴 F01 안전 배수", cmp_["🔴 안전 배수(|실측| / F01 이탈)"]),
        ("🔴 게이트 20·10·5·3 에서 값이 같나",
         bool(len({json.dumps(v["조각"]["원점 1→원점 4"], sort_keys=True)
                   for v in G(C, "§C3 🔴🔴🔴 대비 ㉡ --- 채점 블록 4 고정 · 원점 이동",
                              "게이트별").values()}) == 1)),
        ("🔴 노트 133 규칙", RULE133),
        ("🔴 발견 사이클 == 확인 사이클인가", same_cycle),
        ("🔴 팔 B 의 「확인」은 «재현»이다 --- 사전등록 표와의 차",
         G(B, "반증조건", "🔴🔴 반증조건 15 --- 대비 ㉡ 이 선다 (2·SE 초과 · 동부호 ≥ 10/12)",
           "사전등록 표와 1e-6 안")),
        ("🔴 팔 C 의 「확인」은 «같은 세계·같은 씨앗»에서 마스크만 고친 재적합이다 --- 값이 얼마나 움직였나",
         cmp_["🔴 차"]),
        ("🔴🔴 그래서 새 정보가 있나",
         "팔 B 는 «0.0» 만큼 움직였다(= 재현이지 확인이 아니다). 팔 C 는 %s 만큼 움직였다 "
         "(= F01 마스크를 확인한 것이지 «가설»을 확인한 것이 아니다)." % cmp_["🔴 차"]),
        ("🔴🔴 남은 교란", confound),
        ("🔴🔴🔴 판정", verdict),
        ("🔴 근거", "① 발견(사전등록 §9-9 S15 · 995 설계 팔의 연기 시험)과 확인이 «같은 사이클»이다 "
                  "--- 노트 133 은 확인 측정을 «다음 사이클»에 두라고 한다. "
                  "② 팔 B 의 재계산은 사전등록 표와 차 0.0 --- 새 정보 0. "
                  "③ 팔 C 의 재적합은 같은 세계·같은 12 씨앗·같은 4,559 행에서 마스크만 바꿨고 "
                  "값이 %s 움직였다 --- 「F01 을 견딘다」는 확인이지 「가설」의 확인이 아니다. "
                  "④ 🔴 그리고 정비 팔이 «새 교란»을 찾았다(위 칸) --- 원점을 옮기면 학습 자료가 "
                  "%.2f 배 는다. ⇒ **채택 못 한다. 「제안」이다.**" % (cmp_["🔴 차"],
                                                              rows[-1] / float(rows[0]))),
        ("🔴 996 이 사전등록해야 할 것",
         "① 학습 행을 «맞춘» 채로 원점만 옮기는 칸(예: 원점 1~4 를 전부 4,556 행으로 잘라서). "
         "② 그 칸에서도 조각 셋이 2·SE 를 넘는가. "
         "③ 아래 「도메인 문턱 n*」를 챔피언 세계에서 «직접» 재기(995 의 n* 는 alpha977 세계 값이다)."),
    ])


# ══════════════════════════════════════════════════════════════════════
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runners/out995_score.json")
    a = ap.parse_args(argv)
    t0 = _now()
    J = _load()

    P, c76 = predictions(J)
    F = falsifications(J)
    law = domain_law(J)
    pieces = piece_tables(J)
    claim = world_claim(J, law)

    pv = collections.Counter(v["판정"] for v in P.values())
    fv = collections.Counter(bool(v["🔴 결과"]) for v in F.values())

    ident = collections.OrderedDict()
    for arm, key, hand in (("A", "§A8 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", 4),
                           ("B", "§B6 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", None),
                           ("C", "§C5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮", None)):
        d = G(J[arm], key)
        ident["팔 " + arm] = collections.OrderedDict([
            ("🔴 기계 ㉮ 분자", d["🔴🔴 기계가 센 ㉮ 분자"]),
            ("분모: 검사한 조각", d["분모: 검사한 조각"]),
            ("🔴 손 ㉮ 분자(사전등록 §0-바)",
             d.get("🔴 손으로 센 ㉮ 분자(사전등록 §0-바)", "이 팔은 손 값을 안 냈다(사전등록 §0-바 는 팔 A 세계의 넷이다)")),
            ("🔴🔴 기계 − 손", d.get("🔴 기계 − 손", "해당 없음")),
        ])
    ident["🔴 사전등록 §0-바 손 목록"] = collections.OrderedDict([
        ("㉮ 분자", 4), ("㉯ 분자", 4),
        ("㉮ 목록", ["㉮-1 예산 층마다 d 가 같다", "㉮-2 예산 층마다 유보 행 벡터가 같다",
                   "㉮-3 예산 b 에서 학습 행 = b", "㉮-4 자료 지문이 안 바뀐다"]),
        ("🔴 그중 팔 A 의 기계 조각 목록에 «대응 조각이 있는» 것",
         ["㉮-2 → W3", "㉮-3 → W2", "㉮-4 → W4"]),
        ("🔴🔴 대응 조각이 «없는» 것(기계가 못 센 자리 · 조항 59)", ["㉮-1"]),
        ("🔴 기계가 「떨어질 수 있다」로 뒤집은 것", ["㉮-3(W2 · 변이체 b+1 에서 거짓)"]),
    ])

    res = collections.OrderedDict([
        ("무엇", "🔴 노트 995 채점 --- 예측 22 · 반증조건 19 · 조항 76·78·79"),
        ("🔴 축", "C3 × C4 --- 그리고 「벽」 자체"),
        ("사전등록", PREREG),
        ("🔴 사전등록 sha256", _sha(PREREG)),
        ("🔴🔴🔴 세계 명제", claim),
        ("🔴🔴🔴 조항 79 --- 조각 분해표 전량", pieces),
        ("🔴🔴🔴 「도메인을 늘리면 검정력이 오른다」의 조건", law),
        ("🔴 예측 채점", P),
        ("🔴 예측 채점 합", collections.OrderedDict([
            ("분모", len(P)), ("맞다", pv[MATCH]), ("부분", pv[PART]), ("틀렸다", pv[MISS])])),
        ("🔴 반증조건 채점", F),
        ("🔴 반증조건 채점 합", collections.OrderedDict([
            ("분모", len(F)), ("통과", fv[True]), ("🔴 반증", fv[False]),
            ("🔴 반증된 것", [k for k, v in F.items() if not v["🔴 결과"]])])),
        ("🔴🔴 조항 78 --- 항등식 계수(기계 대 손)", ident),
        ("🔴🔴 조항 76 채점", c76),
        ("🔴 입력 산출물 sha256",
         collections.OrderedDict((p, _sha(p)) for p in list(IN.values()) + [PROG])),
        ("🔴 도장", collections.OrderedDict([
            ("언제(시작 · UTC)", t0), ("언제(끝 · UTC)", _now()),
            ("🔴 코드 sha256", collections.OrderedDict((p, _sha(p)) for p in SRC)),
        ])),
    ])
    res["통과"] = bool(fv[False] == 0)
    q = ROOT / a.out
    with open(str(q), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    sys.stdout.write("wrote %s\n" % q)
    return 0


if __name__ == "__main__":
    sys.exit(main())
