#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 — **챔피언 판**(12 도메인 · 유보 3,775 · 씨앗 0~11).

사전등록 `docs/prereg_990_arms_rulers.md` §1-2 · §1-3 · §1-5 ㉢ 을 그대로 따른다.

🔴🔴🔴 **이 러너는 세계 자료를 «실제로» 연다** --- `ff753.shell(ff753.base())`.
  🔴 **연 경로를 `sys.addaudithook` 으로 «런타임에» 기록한다**(`조항 73-나`).

🔴 **공표값 `0.47034` 를 손으로 안 적는다** --- 정본 출처
  `runners/text680.py` 의 `BOARD_RHO` 를 «임포트»해서 읽는다
  (`ingest/audit.py:2218` 의 `CANON_SRC` 가 그 자리를 정본으로 등기했다).

씀:
    python3 runners/champ990.py --stage weights --ref <40자 sha>   # 빠르다
    python3 runners/champ990.py --stage board   --ref <40자 sha>   # 🔴 12 씨앗 · 느리다
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── 🔴 런타임 자: 연 `data/` 경로를 «전부» 기록한다 ──────────────────────
_OPENED = collections.OrderedDict()


def _audit(event, args):
    if event != "open":
        return
    try:
        p = args[0]
    except Exception:                                              # noqa: BLE001
        return
    if not isinstance(p, str):
        try:
            p = os.fspath(p)
        except Exception:                                          # noqa: BLE001
            return
    if not isinstance(p, str):
        return
    try:
        rel = os.path.relpath(os.path.abspath(p), str(ROOT))
    except Exception:                                              # noqa: BLE001
        return
    if rel.startswith("data" + os.sep):
        _OPENED[rel] = _OPENED.get(rel, 0) + 1


sys.addaudithook(_audit)

from scipy.stats import spearmanr                  # noqa: E402
import ff753 as FF                                 # noqa: E402
from lab.harness import Data, MIN_TRAIN            # noqa: E402
from text680 import BOARD_RHO                      # noqa: E402  🔴 정본 출처
import runners.alpha977 as A                       # noqa: E402

RAN = ("runners/champ990.py", "runners/ff753.py", "runners/text680.py",
       "runners/alpha977.py")
OUT = ROOT / "runners"
PROG = OUT / "out990_progress.txt"

# ══ 사전등록 상수 (§7 · 측정 전에 박았다) ══════════════════════════════
T_SPLIT = 2025.0
CHAMP_SEEDS = list(FF.RULER_SEEDS)          # 🔴 (0..11) --- 손으로 안 적는다
TOL_REPRO = 5e-4                            # §3 P5 의 등록 문턱
MIN_ROWS = 20                               # 챔피언 판의 도메인 게이트


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prog(msg):
    with open(str(PROG), "a", encoding="utf-8") as f:
        f.write("%s  [champ] %s\n" % (_now(), msg))
    sys.stderr.write("%s  [champ] %s\n" % (_now(), msg))
    sys.stderr.flush()


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def _stamp(ref, cs0, t0):
    return collections.OrderedDict([
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", ref),
            ("🔴 코드 sha256(시작)", cs0),
            ("🔴 코드 sha256(끝)", code_stamp()),
            ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
        ("🔴🔴🔴 이 러너가 «연» `data/` 경로",
         collections.OrderedDict([
             ("경로별 연 횟수", collections.OrderedDict(_OPENED)),
             ("🔴 연 `data/` 경로 수", len(_OPENED))])),
    ])


def _shell():
    return FF.shell(FF.base())


# ══════════════════════════════════════════════════════════════════════
def stage_weights(ref):
    """🔴 §1-5 ㉢ — **`R_champ` 자의 도메인 가중을 «런타임에» 읽는다.**"""
    t0 = _now()
    cs0 = code_stamp()
    d0 = _shell()
    W = d0.weights(T_SPLIT)
    champ = collections.OrderedDict((d, int(W[d])) for d in sorted(W))
    tot = int(sum(champ.values()))

    pool = A.Pool()
    a977 = collections.OrderedDict(
        (d, int(pool.dom_ho[d])) for d in pool.gated)
    tot977 = int(sum(a977.values()))

    shared = [d for d in pool.gated if d in champ]
    only977 = [d for d in pool.gated if d not in champ]
    onlych = [d for d in champ if d not in set(pool.gated)]

    sub = collections.OrderedDict((d, champ[d]) for d in shared)
    subtot = int(sum(sub.values()))

    def _share(dd, tt):
        return collections.OrderedDict(
            (k, _r(v / float(tt))) for k, v in dd.items())

    big977 = max(a977, key=lambda d: a977[d])
    checks = collections.OrderedDict([
        ("C1 챔피언 판 유보 합이 3,775 인가", bool(tot == 3775)),
        ("C2 챔피언 판 도메인이 12 인가", bool(len(champ) == 12)),
        ("C3 alpha977 판 유보 합이 2,359 인가", bool(tot977 == 2359)),
        ("C4 alpha977 판 게이트 도메인이 10 인가", bool(len(a977) == 10)),
        ("C5 alpha977 의 10 이 챔피언 12 에 «전부» 든다",
         bool(len(only977) == 0)),
    ])

    res = collections.OrderedDict([
        ("무엇", "990 §1-5 ㉢ — 🔴 **`R_champ` 자의 도메인 가중을 런타임에 읽는다**"),
        ("🔴 축", "C2 (도메인 가중)"),
        ("사전등록", "docs/prereg_990_arms_rulers.md §1-5"),
        ("§1 🔴🔴🔴 챔피언 판(898)", collections.OrderedDict([
            ("도메인 수", len(champ)),
            ("도메인별 유보 행", champ),
            ("유보 행 합", tot),
            ("도메인별 몫", _share(champ, tot)),
            ("🔴 `세계애니` 의 몫", _r(champ.get("세계애니", 0) / float(tot))),
            ("씨앗", CHAMP_SEEDS),
            ("🔴 출처", "ff753.shell(ff753.base()).weights(%.1f)" % T_SPLIT),
        ])),
        ("§2 🔴🔴🔴 alpha977 판(977·989)", collections.OrderedDict([
            ("게이트 도메인 수", len(a977)),
            ("도메인별 유보 행", a977),
            ("유보 행 합", tot977),
            ("도메인별 몫", _share(a977, tot977)),
            ("🔴🔴🔴 가장 큰 도메인", big977),
            ("🔴🔴🔴 그 도메인의 몫", _r(a977[big977] / float(tot977))),
            ("🔴 게이트 밖 base 행", int(len(pool.yb)) - tot977),
            ("🔴 base 행 전량", int(len(pool.yb))),
            ("🔴 hplt 행 전량", int(len(pool.yh))),
        ])),
        ("§3 🔴🔴🔴 두 판의 대조 — **이 사이클의 세계 명제 `W2`**",
         collections.OrderedDict([
             ("공유 도메인", shared),
             ("공유 도메인 수", len(shared)),
             ("alpha977 에만 있는 도메인", only977 or "없음"),
             ("챔피언에만 있는 도메인", onlych or "없음"),
             ("🔴🔴🔴 `R_champ` 가중(공유 도메인으로 제한)", sub),
             ("🔴🔴🔴 `R_champ` 가중 합", subtot),
             ("🔴🔴🔴 `R_champ` 의 도메인별 몫", _share(sub, subtot)),
             ("🔴🔴🔴 `세계애니` 의 몫 — alpha977 판",
              _r(a977["세계애니"] / float(tot977))),
             ("🔴🔴🔴 `세계애니` 의 몫 — 챔피언 판",
              _r(champ["세계애니"] / float(tot))),
             ("🔴🔴🔴 `세계애니` 의 몫 — `R_champ`(공유 제한)",
              _r(sub["세계애니"] / float(subtot))),
             ("🔴🔴 몫의 배수(alpha977 ÷ 챔피언)",
              _r((a977["세계애니"] / float(tot977))
                 / (champ["세계애니"] / float(tot)), 3)),
         ])),
        ("§4 🔴🔴 HPLT 의 도메인 구성 — **자료 쪽 반쪽**",
         collections.OrderedDict([
             ("hplt 도메인별 행",
              collections.OrderedDict(
                  (d, int((pool.dh == d).sum()))
                  for d in sorted(set(pool.dh.tolist())))),
             ("hplt 행 합", int(len(pool.yh))),
             ("🔴 hplt 도메인별 몫",
              collections.OrderedDict(
                  (d, _r(int((pool.dh == d).sum()) / float(len(pool.yh))))
                  for d in sorted(set(pool.dh.tolist())))),
             ("🔴🔴🔴 `세계애니` 의 hplt 몫",
              _r(int((pool.dh == "세계애니").sum()) / float(len(pool.yh)))),
             ("🔴🔴🔴 hplt 에서 가장 큰 도메인",
              max(set(pool.dh.tolist()), key=lambda d: int((pool.dh == d).sum()))),
             ("🔴🔴🔴 그 도메인의 hplt 몫",
              _r(max(int((pool.dh == d).sum())
                     for d in set(pool.dh.tolist())) / float(len(pool.yh)))),
         ])),
        ("§5 🔴 배선 검사", checks),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", len(checks)),
        ("통과", bool(all(checks.values()))),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 두 판의 도메인 가중을 «런타임에» 읽었고 alpha977 의 10 이 챔피언 12 의 부분집합이다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


# ══════════════════════════════════════════════════════════════════════
def stage_board(ref):
    """🔴 §1-3 `W3` — **챔피언 판 `ρ` 를 씨앗 열둘로 다시 낸다**(예측 `P5`)."""
    t0 = _now()
    cs0 = code_stamp()
    d0 = _shell()
    doms = sorted(d0.dom)
    W = d0.weights(T_SPLIT)
    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T_SPLIT)) for d in doms}
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T_SPLIT)
             & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k)
            tmask[d] = k

    per = {d: [] for d in doms}
    pooled, eq = [], []
    t_start = time.time()
    for si, s in enumerate(CHAMP_SEEDS):
        f = FF.CLS(seed=s)
        f.fit(Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train}))
        num = den = 0.0
        vals = []
        for d in doms:
            A_, M_, y_, t_ = d0.slice(d, post[d])
            p = np.asarray(f.predict(d, A_, M_, t_), float)
            ok = np.isfinite(p) & np.isfinite(y_)
            if ok.sum() < MIN_ROWS:
                continue
            rho = float(spearmanr(p[ok], y_[ok])[0])
            per[d].append(rho)
            vals.append(rho)
            if d in W:
                num += rho * W[d]
                den += W[d]
        pooled.append(num / den)
        eq.append(float(np.mean(vals)))
        _prog("씨앗 %d/%d (%d) — 묶음 %.6f · %.1fs"
              % (si + 1, len(CHAMP_SEEDS), s, pooled[-1], time.time() - t_start))

    pv = np.asarray(pooled, float)
    ev = np.asarray(eq, float)
    got = float(pv.mean())
    diff = abs(got - float(BOARD_RHO))

    repro = collections.OrderedDict([
        ("🔴 공표값(출처 = `runners/text680.py` 의 `BOARD_RHO` · 손으로 안 적었다)",
         float(BOARD_RHO)),
        ("🔴 990 이 다시 낸 값(묶음 · 씨앗 %d 평균)" % len(CHAMP_SEEDS), _r(got)),
        ("🔴 공표값과의 차이", _r(diff, 8)),
        ("🔴 등록 문턱", TOL_REPRO),
        ("🔴🔴🔴 문턱 안인가", bool(diff <= TOL_REPRO)),
        ("🔴 씨앗 SD", _r(float(np.std(pv, ddof=1)))),
        ("🔴 씨앗 SE", _r(float(np.std(pv, ddof=1) / math.sqrt(len(pv))), 8)),
        ("🔴 씨앗별 묶음 ρ", [_r(x) for x in pv.tolist()]),
        ("🔴 균등 ρ(씨앗 평균)", _r(float(ev.mean()))),
        ("🔴 씨앗별 균등 ρ", [_r(x) for x in ev.tolist()]),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", int(len(CHAMP_SEEDS))),
    ])

    res = collections.OrderedDict([
        ("무엇", "990 §1-3 `W3` — 🔴 **챔피언 판 ρ 를 씨앗 열둘로 다시 낸다**"),
        ("🔴 축", "C2"),
        ("사전등록", "docs/prereg_990_arms_rulers.md §1-3"),
        ("§1 🔴 판", collections.OrderedDict([
            ("도메인 수", len(W)), ("유보 행 합", int(sum(W.values()))),
            ("씨앗", CHAMP_SEEDS), ("모형", str(FF.CLS)),
            ("상관", "scipy.stats.spearmanr(동률 평균)"),
            ("나눔", "언제 >= %.1f 이면 유보" % T_SPLIT),
        ])),
        ("§2 🔴 재현", repro),
        ("§3 🔴 도메인별 ρ(씨앗 평균)",
         collections.OrderedDict(
             (d, _r(float(np.mean(per[d])))) for d in doms if per[d])),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", int(len(CHAMP_SEEDS) * len(doms))),
        ("통과", bool(repro["🔴🔴🔴 문턱 안인가"])),
        ("🔴 이 절의 통과가 뜻하는 것",
         "🔴 챔피언 판이 이 사이클에서도 «그 자리에» 있다 — 989 가 「판이 움직였다」고 부른 것은 이 판이 아니다"),
    ])
    res.update(_stamp(ref, cs0, t0))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=("weights", "board"))
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    fn = {"weights": stage_weights, "board": stage_board}[a.stage]
    _prog("시작 %s" % a.stage)
    res = fn(a.ref)
    p = OUT / ("out990_champw.json" if a.stage == "weights"
               else "out990_champ.json")
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    _prog("끝 %s → %s" % (a.stage, p.name))
    return 0


if __name__ == "__main__":
    sys.exit(main())
