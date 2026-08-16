#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""981 — 🔴🔴🔴 **`v2.2` 를 기계로 돌린다** (축 C3).

사전등록 `docs/prereg_981_pick.md` §2 를 그대로 따른다.

🔴 **왜 이 파일이 있나.** 977·978·979 는 **규칙을 고쳐** 자를 갈았고 980 은 **규칙을 덜
적용해** 갈았다. 규칙 개정은 `git diff` 에 남지만 **규칙 미적용은 안 남는다.**
그래서 선택을 **산문에서 러너로 내린다** — `pick()` 이 유일한 선택자다.

🔴 **이 사이클은 `v2.2` 의 문언을 한 글자도 안 고친다**(반증조건 5).

씀:
    python3 runners/pick981.py --stage pick --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import loso974 as LO                              # noqa: E402
import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler979 as R9                             # noqa: E402

RAN = ("runners/pick981.py", "runners/ruler979.py", "runners/ruler978.py",
       "runners/alpha977.py", "runners/ledger.py", "runners/layers957.py",
       "runners/predict971.py", "runners/loso974.py")
OUT = ROOT / "runners"
PROG = OUT / "out981_progress.txt"

R1, R2, R3, R4, R5, R6 = R9.R1, R9.R2, R9.R3, R9.R4, R9.R5, R9.R6
RULERS = R9.RULERS
U_REG = A.U_REG

#: 🔴 `v2.2` 문언 그대로 — 동률 밴드 폭. 사전등록 §8 에 박았다.
BAND = 0.05
D4KEY = "u=%d|D4 학습 y 전량(둘 다)"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (_now(), msg))
    sys.stderr.write("%s  %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    return None if x is None else round(float(x), n)


def _load(name):
    p = OUT / name
    if not p.is_file():
        raise SystemExit("🔴 %s 가 없다 — fail-closed" % name)
    return json.loads(p.read_text(encoding="utf-8"))


# ══════════════════════════════════════════════════════════════════════
# 🔴🔴🔴 §A `pick()` — **유일한 선택자**. 산문은 이 함수를 인용만 한다.
# ══════════════════════════════════════════════════════════════════════
def pick(rows, band=BAND):
    """🔴 `v2.2` 를 **문언 그대로** 실행한다.

    `rows` = OrderedDict[자 이름] -> {"통과": bool, "검정력": float, "몫": float}

    단계
      1. 통과자   = 조건 둘을 λ 둘 다에서 통과한 자
      2. 검정력   = min over λ |Δ(D4)| / SE_이중        (호출자가 이미 계산해 넣는다)
      3. 최고     = max 검정력
      4. 동률 밴드 = {자 : 검정력 ≥ 최고 × (1 − band)}
      5. 정본     = 밴드 안에서 「가장 큰 도메인의 몫」이 최소인 자

    🔴 **밴드 구성원 목록을 반드시 낸다**(반증조건 3).
    🔴 사람이 끼어들 자리가 없다 — 「규칙을 덜 적용」이 원리상 불가능하다.
    """
    ok = [nm for nm in rows if rows[nm]["통과"]]
    out = collections.OrderedDict()
    out["1 · 통과자 목록"] = ok or "없음"
    out["1 · 통과자 수"] = len(ok)
    out["2 · 검정력 표"] = collections.OrderedDict(
        [(nm, _r(rows[nm]["검정력"], 4)) for nm in rows])
    if not ok:
        out["3 · 최고 검정력"] = None
        out["4 · 동률 밴드 하한"] = None
        out["🔴🔴 4 · 동률 밴드 구성원"] = "없음"
        out["4 · 동률 밴드 크기"] = 0
        out["5 · 밴드 안 「가장 큰 도메인의 몫」"] = {}
        out["🔴🔴🔴 고른 자"] = "🔴 없다 — 정본 자를 바꾸지 않는다"
        out["🔴 고른 단계"] = "1 (통과자 0)"
        return out
    pw = {nm: float(rows[nm]["검정력"]) for nm in ok}
    top = max(pw.values())
    lo = top * (1.0 - band)
    near = [nm for nm in ok if pw[nm] >= lo]
    share = {nm: float(rows[nm]["몫"]) for nm in near}
    chosen = near[0] if len(near) == 1 else min(near, key=lambda nm: (share[nm], nm))
    out["3 · 최고 검정력"] = _r(top, 4)
    out["3 · 최고를 낸 자"] = max(ok, key=lambda nm: pw[nm])
    out["4 · 동률 밴드 하한 = 최고 × (1 − %.2f)" % band] = _r(lo, 4)
    out["🔴🔴 4 · 동률 밴드 구성원"] = near
    out["4 · 동률 밴드 크기"] = len(near)
    out["5 · 밴드 안 「가장 큰 도메인의 몫」"] = collections.OrderedDict(
        [(nm, _r(share[nm])) for nm in sorted(near, key=lambda x: share[x])])
    out["🔴🔴🔴 고른 자"] = chosen
    out["🔴 고른 단계"] = ("4 (밴드가 하나라 검정력 최대가 곧 답)" if len(near) == 1
                       else "5 (동률 밴드 %d 자 중 몫 최소)" % len(near))
    out["🔴 밴드 안 최고 검정력 자와 고른 자가 다른가"] = bool(
        chosen != out["3 · 최고를 낸 자"])
    return out


# ══════════════════════════════════════════════════════════════════════
# §B L1 결산 — 🔴 가중 벡터의 이동을 러너가 **다시 잰다**(손 전사 금지)
# ══════════════════════════════════════════════════════════════════════
def _nor(w, doms):
    s = sum(w[d] for d in doms)
    return {d: w[d] / s for d in doms}


def l1(wa, wb, doms):
    return float(sum(abs(wa[d] - wb[d]) for d in doms))


# ══════════════════════════════════════════════════════════════════════
def stage_pick(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    _prog("pick 시작")
    pool = A.Pool()
    h0 = R9.ho_stamp(pool)
    R = R9.Rulers6(pool)
    tab = R.table()
    doms = list(R.doms)

    rs = _load("out979_rescore.json")
    gy = rs["🔴🔴🔴 48 + 48 칸"]["라벨 파괴 D1~D4"]

    # ── §1 입력: D4 두 칸 (자 여섯) ────────────────────────────────
    cells = collections.OrderedDict()
    power = collections.OrderedDict()
    passed = collections.OrderedDict()
    for nm in RULERS:
        per = collections.OrderedDict()
        ratios, nok = [], 0
        for u in U_REG:
            k = D4KEY % u
            rr = gy[nm]["칸별"][k]
            per[k] = collections.OrderedDict([
                ("Δ", rr["Δ"]),
                ("SE_이중(정합 25 벌)", rr["🔴🔴 SE_25벌(정합)"]),
                ("|Δ|/SE", rr["🔴🔴 |Δ|/SE (정합)"]),
                ("① 부호 Δ<0", rr["🔴 조건 ① 부호 Δ < 0"]),
                ("② |Δ| ≥ 2·SE", rr["🔴🔴 조건 ② |Δ| ≥ 2·SE(정합)"]),
                ("v2.2 통과", rr["🔴🔴 둘 다 (v2.2 통과)"]),
            ])
            ratios.append(rr["🔴🔴 |Δ|/SE (정합)"] or 0.0)
            nok += 1 if rr["🔴🔴 둘 다 (v2.2 통과)"] else 0
        cells[nm] = per
        power[nm] = min(ratios)
        passed[nm] = bool(nok == len(U_REG))

    # ── §2 몫 두 벌: 뽑기판 · 닫힌꼴판 ─────────────────────────────
    wt = tab["자별 가중"]
    share_raw = collections.OrderedDict(
        [(nm, wt[nm]["🔴🔴 가장 큰 도메인의 몫"]) for nm in RULERS])
    #: 🔴 뽑기판(`R_z`·`R_iv`)의 **참값** = 닫힌 꼴 짝의 몫
    twin = {R3: R5, R4: R6}
    share_true = collections.OrderedDict(
        [(nm, share_raw[twin.get(nm, nm)]) for nm in RULERS])

    def rows_of(names, share):
        return collections.OrderedDict(
            [(nm, {"통과": passed[nm], "검정력": power[nm], "몫": share[nm]})
             for nm in names])

    # ── §3 체제 셋 ─────────────────────────────────────────────────
    regimes = collections.OrderedDict()
    regimes["체제 A · 979 판 (여섯을 서로 다른 자로 본다 · 몫은 각자 것)"] = pick(
        rows_of(RULERS, share_raw))
    FOLD = (R1, R2, R5, R6)
    regimes["체제 B · 980 선언판 (R_iv≡R_iv* · R_z≡R_z* 로 접는다 · 닫힌꼴 몫)"] = pick(
        rows_of(FOLD, share_true))
    regimes["체제 C · 잡음 제거판 (여섯을 다 두되 몫을 전부 참값으로)"] = pick(
        rows_of(RULERS, share_true))

    KB = "체제 B · 980 선언판 (R_iv≡R_iv* · R_z≡R_z* 로 접는다 · 닫힌꼴 몫)"
    KA = "체제 A · 979 판 (여섯을 서로 다른 자로 본다 · 몫은 각자 것)"
    KC = "체제 C · 잡음 제거판 (여섯을 다 두되 몫을 전부 참값으로)"
    canon = regimes[KB]["🔴🔴🔴 고른 자"]

    # ── §4 L1 결산 ─────────────────────────────────────────────────
    W = collections.OrderedDict()
    W["976 `R_pool 묶음` (w ∝ n_d)"] = _nor({d: float(R.n[d]) for d in doms}, doms)
    W["977 `R_eq 균등` (w ∝ 1)"] = _nor({d: 1.0 for d in doms}, doms)
    W["978 `R_z 순열SE 역가중` (w ∝ 1/s_d)"] = _nor(
        {d: 1.0 / R.sd[d] for d in doms}, doms)
    W["979 `R_iv SE² 역가중` (w ∝ 1/s_d²)"] = _nor(
        {d: 1.0 / R.sd[d] ** 2 for d in doms}, doms)
    W["980 `R_iv* 닫힌꼴` (w ∝ n_d − 1)"] = _nor(
        {d: float(R.n[d] - 1) for d in doms}, doms)
    ks = list(W.keys())
    steps = collections.OrderedDict()
    for i in range(len(ks) - 1):
        steps["%s → %s" % (ks[i].split()[0], ks[i + 1].split()[0])] = _r(
            l1(W[ks[i]], W[ks[i + 1]], doms))
    steps["🔴🔴 980 `R_iv*` 대 976 `R_pool`"] = _r(l1(W[ks[4]], W[ks[0]], doms))
    net = l1(W[ks[4]], W[ks[0]], doms)
    first = l1(W[ks[0]], W[ks[1]], doms)

    # ── §5 예측 채점 ───────────────────────────────────────────────
    pred = collections.OrderedDict([
        ("P1 — 체제 B 가 `R_pool 묶음` 을 고른다",
         bool(regimes[KB]["🔴🔴🔴 고른 자"] == R1)),
        ("P2 — 체제 A 가 `R_iv SE² 역가중` 을 고른다",
         bool(regimes[KA]["🔴🔴🔴 고른 자"] == R4)),
        ("P3 — 🔴 어느 체제에서도 `R_iv* 닫힌꼴` 이 안 나온다",
         bool(all(regimes[k]["🔴🔴🔴 고른 자"] != R6 for k in regimes))),
        ("P8 — `R_iv*` 대 `R_pool` L1 이 `976→977` 의 1% 미만",
         bool(net < 0.01 * first)),
    ])

    out = collections.OrderedDict()
    out["무엇"] = ("981 §2 — 🔴🔴🔴 **`v2.2` 를 기계로 돌린다.** "
                 "선택을 산문에서 러너로 내렸다 — `pick()` 이 유일한 선택자다")
    out["🔴 축"] = "C3 (곁 C2)"
    out["사전등록"] = "docs/prereg_981_pick.md §2"
    out["🔴 `v2.2` 문언을 이 사이클이 고쳤나"] = False
    out["🔴 동률 밴드 폭(등록 상수)"] = BAND
    out["🔴🔴 §1 입력 — D4 두 칸(출처 `out979_rescore.json`)"] = cells
    out["🔴 §1 검정력 = min over λ |Δ(D4)|/SE_이중"] = collections.OrderedDict(
        [(nm, _r(power[nm], 4)) for nm in RULERS])
    out["🔴 §1 v2.2 통과 여부"] = passed
    out["🔴🔴 §2 자별 가중 표"] = tab
    out["🔴 §2 가장 큰 도메인의 몫 — 뽑기판(979 가 쓴 값)"] = share_raw
    out["🔴🔴 §2 가장 큰 도메인의 몫 — 참값(닫힌 꼴)"] = share_true
    out["🔴 §2 뽑기판과 참값의 차"] = collections.OrderedDict(
        [(nm, _r(share_true[nm] - share_raw[nm])) for nm in RULERS])
    out["🔴🔴🔴 §3 체제 셋의 `pick()` 산출물"] = regimes
    out["🔴🔴🔴 §3 정본 자 (등록 판정 = 체제 B)"] = canon
    out["🔴🔴 §3 980 이 실은 자"] = R6
    out["🔴🔴🔴 §3 980 의 선택이 어느 체제에서 재현되나"] = [
        k for k in regimes if regimes[k]["🔴🔴🔴 고른 자"] == R6] or "🔴 없다"
    out["🔴 §3 세 체제가 고른 자"] = collections.OrderedDict(
        [(k, regimes[k]["🔴🔴🔴 고른 자"]) for k in regimes])
    out["🔴🔴 §4 자 전쟁 L1 결산"] = steps
    out["🔴🔴🔴 §4 977~980 네 사이클의 순 이동이 977 이탈폭의 몇 %"] = _r(
        100.0 * net / first, 4)
    out["🔴 §4 정규화 가중 벡터"] = collections.OrderedDict(
        [(k, {d: _r(W[k][d]) for d in doms}) for k in W])
    out["🔴 §5 예측 채점"] = pred
    out["통과"] = bool(len(regimes) == 3
                     and all("🔴🔴 4 · 동률 밴드 구성원" in regimes[k] for k in regimes))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "체제 셋 전부에서 `pick()` 이 돌았고 셋 다 동률 밴드 «구성원 목록»을 냈다 "
        "(반증조건 3). 🔴 이 값은 어느 자가 뽑혔는지와 무관하다")
    out["🔴 유보 지문"] = R9.ho_verdict(h0, R9.ho_stamp(pool))
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LO.SRC)
    (OUT / "out981_pick.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("pick 끝 — 정본 자 = %s" % canon)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["pick"])
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    r = {"pick": stage_pick}[a.stage](a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
