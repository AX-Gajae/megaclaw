#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""983 — 🔴🔴🔴 **「어느 유보에서 재나」를 잰다** — `docs/목표.md` 「정본 유보」 절의 유일한 출처.

사전등록 `docs/prereg_983_holdout_registry.md` §2-1 ⓐ.

🔴 **왜 이 러너가 있나 (티처 #121 1순위).** 982 가 낸 가장 큰 수(유보 정의를 바꿨을 때의
자 가중 L1 · 분기비 9.6579)는 **자 논의가 아니라 유보 논의를 가리키는데, 저장소에는
유보 정의를 적는 자리가 「없다」.** 자는 `docs/목표.md` 에 표로 등록돼 있고 개정 잠금까지
걸려 있는데, **그보다 «위»에 오는 선택인 「어느 유보에서 재나」는 아무 데도 없다.**

🔴 **그리고 977~981 의 결론은 전부 「개체 묶음 유보」에서 났다.** 982 가 「유보를 바꾸면
관문 판정이 뒤집힌다」를 증명해 놓고 그 사실을 그 결론들 옆에 안 적었다.

🔴 **손 전사 금지(규칙 D).** 「정본 유보」 절에 들어가는 모든 수는 이 산출물의 키에서 온다.

씀:
    python3 runners/holdout983.py --stage holdout --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402
import alpha977 as A                              # noqa: E402
import ruler979 as R9                             # noqa: E402
import pick981 as PK                              # noqa: E402
import tfwd982 as T2                              # noqa: E402

RAN = ("runners/holdout983.py", "runners/tfwd982.py", "runners/pick981.py",
       "runners/ruler979.py", "runners/alpha977.py", "runners/ledger.py",
       "runners/layers957.py", "runners/predict971.py")
OUT = ROOT / "runners"
RULERS = R9.RULERS

H_ENT = "㈎ 개체 묶음 유보 (976~981)"
H_TIME = "㈏ 시간 방향 유보 (982~)"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _r(x, n=6):
    if x is None:
        return None
    x = float(x)
    return None if not np.isfinite(x) else round(x, n)


def _iso(o):
    return dt.date.fromordinal(int(o)).isoformat()


def stage_holdout(ref):
    t0 = _now()
    cs0 = LG.code_stamp(RAN)
    ep, tp = A.Pool(), T2.TPool()
    ER, TR = R9.Rulers6(ep), R9.Rulers6(tp)

    ent = collections.OrderedDict([
        ("🔴 이름", H_ENT),
        ("🔴 정의", "개체(entity) 를 겹에 배정한 **5 겹 OOF** — 유보는 «같은 시대의 다른 개체»다"),
        ("🔴 무엇이 겹을 정하나", "🔴 **씨앗**(`alpha977.SEEDS` 다섯 벌 평균)"),
        ("🔴 겹 수", int(len(set(ep.fi.tolist())))),
        ("🔴 유보 행 수(게이트 도메인 합)",
         int(sum(int(ep.ho_mask[d].sum()) for d in ep.gated))),
        ("🔴 base 행 전량", int(len(ep.yb))),
        ("🔴 게이트 도메인 수", len(ep.gated)),
        ("🔴 게이트 도메인", list(ep.gated)),
        ("🔴 도메인별 유보 행", collections.OrderedDict(
            [(d, int(ep.ho_mask[d].sum())) for d in ep.gated])),
        ("🔴🔴 예측인가 보간인가",
         "🔴 **보간이다** — 학습과 유보가 같은 시대를 나눠 가진다"),
        ("🔴 누가 썼나", "노트 976~981 의 모든 결론 · 🔴 저장소 판 ρ"),
    ])
    time_ = collections.OrderedDict([
        ("🔴 이름", H_TIME),
        ("🔴 정의",
         "시간 분위(20/40/60/80)로 블록 다섯을 자르고, 원점 `j = 1..4` 마다 "
         "**블록 `<j` 로 학습하고 블록 `j` 를 맞힌다**"),
        ("🔴 무엇이 겹을 정하나", "🔴 **시간**(씨앗은 뽑기 차례만 흔든다)"),
        ("🔴 블록 수", int(tp.nblock)),
        ("🔴 원점 수", len(tp.origins)),
        ("🔴 절단 날짜", [_iso(c) for c in tp.cuts]),
        ("🔴 유보 행 수(블록 1~4)", int(tp.ho_all.sum())),
        ("🔴 base 행 전량", int(len(tp.yb))),
        ("🔴 게이트 도메인 수", len(tp.gated)),
        ("🔴 게이트 도메인", list(tp.gated)),
        ("🔴 도메인별 유보 행", collections.OrderedDict(
            [(d, int(tp.ho_mask[d].sum())) for d in tp.gated])),
        ("🔴🔴 예측인가 보간인가",
         "🔴 **예측이다** — 학습의 마지막 시각이 유보의 첫 시각보다 앞이다"),
        ("🔴 누가 썼나", "노트 982(한 예산 칸) · 노트 983(예산 격자 전량)"),
    ])

    doms = [d for d in tp.gated if d in ep.gated]
    l1 = collections.OrderedDict()
    for nm in RULERS:
        a = PK._nor({d: TR.all_w()[nm][d] for d in doms}, doms)
        b = PK._nor({d: ER.all_w()[nm][d] for d in doms}, doms)
        l1[nm] = _r(PK.l1(a, b, doms))

    out = collections.OrderedDict()
    out["무엇"] = ("983 §2-1 ⓐ — 🔴🔴🔴 **「어느 유보에서 재나」를 잰다.** "
                 "`docs/목표.md` 「정본 유보」 절의 **유일한 출처**다(규칙 D)")
    out["🔴 축"] = "C1 상태→예측"
    out["사전등록"] = "docs/prereg_983_holdout_registry.md §2-1 ⓐ"
    out["🔴 티처"] = ("🔴 티처 #121 1순위 — 「982 가 낸 가장 큰 수는 자 논의가 아니라 유보 "
                    "논의를 가리키는데, 저장소에는 유보 정의를 적는 자리가 「없다」」")
    out["🔴🔴 유보 둘"] = collections.OrderedDict([(H_ENT, ent), (H_TIME, time_)])
    out["🔴🔴🔴 유보를 바꿨을 때 자 가중이 움직인 L1"] = collections.OrderedDict([
        ("🔴 견준 도메인(두 유보의 게이트 교집합)", doms),
        ("🔴 도메인 수", len(doms)),
        ("🔴 자별 L1", l1),
        ("🔴 최대", _r(max(l1.values()))),
        ("🔴 최소", _r(min(l1.values()))),
        ("🔴 정본 자(`R_pool 묶음`)", l1["R_pool 묶음"]),
    ])
    out["🔴🔴🔴 977~981 의 결론에 붙는 유보 종속 단서"] = collections.OrderedDict([
        ("🔴 누가 어느 유보에서 났나", collections.OrderedDict([
            ("노트 977~981 의 모든 자 판정", H_ENT),
            ("🔴 982 의 2순위 전체(이득 소멸 · 대조 포화 · MDE)", H_ENT),
            ("🔴 저장소 판 ρ", H_ENT),
            ("노트 982 §2(자가 갈리나)", "%s · 🔴 예산 한 칸(`N_B=1800`)" % H_TIME),
            ("노트 983 §2(예산 격자 전량)", H_TIME),
        ])),
        ("🔴🔴🔴 982 가 안 적은 문장 — 983 이 적는다",
         "🔴 **977~981 은 「예측」이 아니라 「보간」 위에서 자를 골랐고, 그 선택이 예측 "
         "위에서도 같은지는 982 가 처음 물었다.**"),
        ("🔴🔴 그래서 982 의 2순위 헤드라인에 붙는 단서",
         "🔴 **「이득 소멸」·「대조 포화」·「MDE 미달」은 «개체 묶음 유보에서» 참이다.** "
         "982 자신이 「유보를 바꾸면 관문 판정이 뒤집힌다」를 증명해 놓고 그 단서를 "
         "안 붙였다(티처 #121 물음 ① 의 답 1)"),
        ("🔴 판 ρ 옆에 붙는 단서",
         "🔴 **저장소 판 ρ 도 «개체 묶음 유보» 의 값이다** — 아무도 그 사실을 판 옆에 "
         "안 적었다(티처 #121 물음 ① 의 답 3)"),
    ])
    out["통과"] = bool(len(doms) > 0 and len(l1) == len(RULERS))
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **두 유보를 자료에서 실제로 지어 행 수·게이트·도메인별 행·자 가중 L1 을 냈다.** "
        "`통과` 는 「어느 유보가 옳다」가 **아니다** — 그 선택을 «등록하는 것»이 이 사이클의 일이다")
    LG.write_stamped(str(OUT / "out983_holdout.json"), out, ref, cs0, t0, RAN, LG.DATA)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["holdout"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_holdout(a.ref)
    print(json.dumps({"stage": a.stage, "통과": r.get("통과")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
