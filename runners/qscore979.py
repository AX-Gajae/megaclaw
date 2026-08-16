#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""979 — 🔴 **자기 예측 Q1~Q10 을 전부 채점한다**(사전등록 §5 · 반증조건 2).

노트 978 은 자기 예측 여덟 중 **둘만** 채점했다. 🔴 **979 가 같은 병을 안 앓으려면
자기 열 개도 하나도 안 빼고 채점해야 한다** — 값이 무엇이든 적는다.

씀:
    python3 runners/qscore979.py --stage q --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ledger as LG                               # noqa: E402

RAN = ("runners/qscore979.py", "runners/ledger.py", "runners/predict971.py")
OUT = ROOT / "runners"


def _l(n):
    p = OUT / n
    if not p.is_file():
        raise SystemExit("🔴 산출물이 없다(fail-closed): %s" % n)
    return json.loads(p.read_text(encoding="utf-8"))


def stage_q(ref):
    t0 = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cs0 = LG.code_stamp(RAN)
    sd = _l("out979_sd.json")
    rs = _l("out979_rescore.json")
    gt = _l("out979_gate.json")
    sm = _l("out979_srcmix.json")
    ap = _l("out979_alphapair.json")
    sc = _l("out979_score978.json")

    WT = "🔴🔴🔴 자 여섯의 가중"
    IDN = "🔴🔴🔴 항등식 — R_iv* 는 R_pool 인가"
    DEC = "🔴🔴🔴 v2.2 채택 판정 (D4)"
    QQ = "🔴🔴 예측 Q2·Q5·Q6"
    MIX = "🔴🔴🔴 학습 혼합 대 유보 혼합"
    FLD = "🔴🔴 select() 가 hplt 쪽에서 겹에 의존하나"
    PRD = "🔴🔴🔴 예측 P1~P8 채점표"

    Q = collections.OrderedDict()

    def rec(k, txt, ok, ev):
        Q[k] = collections.OrderedDict([("등록 문언", txt), ("🔴🔴 채점", bool(ok)),
                                        ("근거", ev)])

    q1 = rs["🔴🔴 예측 Q1 — 벌 수를 맞추면 SE 가 좁아지나"]
    rec("Q1", "벌 수를 맞추면 SE 가 좁아진다 — SE_25벌 < SE_구판 인 칸이 48/48",
        bool(q1["🔴 예측 Q1(48/48 이 좁아진다)"]),
        {"분자/분모": q1["🔴🔴 SE_25벌 < SE_구판 인 칸 분자/분모"],
         "🔴 넓어진 칸": q1["🔴 넓어진 칸"]})

    r2 = gt[DEC]["자별"]["R_eq 균등"]["🔴 통과한 λ 칸"]
    rec("Q2", "R_eq 균등은 맞춘 SE 에서도 §2 를 0/2 통과한다",
        bool(gt[QQ]["Q2 — R_eq 균등이 정합 SE 에서도 0/2 인가"]),
        {"🔴 실측": r2,
         "🔴🔴 예측이 틀렸으면 무엇이 바뀌나":
             "🔴 **결정(승격을 되돌린다)은 살아남는다** — v2.2 는 λ 둘 다를 요구한다. "
             "바뀌는 것은 노트 978 이 적은 「0/8」·「0/2」라는 **문장**이다",
         "🔴 v2.2 통과": gt[DEC]["자별"]["R_eq 균등"]["🔴🔴🔴 v2.2 등록 규칙 통과 (λ 둘 다)"]})

    rel = sd[WT]["🔴🔴🔴 최대 상대오차"]
    rec("Q3", "s_d 의 뽑기 추정과 닫힌 꼴의 최대 상대오차 < 0.05",
        bool(rel is not None and rel < 0.05),
        {"🔴 최대 상대오차": rel,
         "🔴 몬테카를로 이론값": sd[WT]["🔴 몬테카를로 오차의 이론값 1/√(2(n_perm−1))"],
         "🔴 그 몇 배": sd[WT]["🔴🔴 최대 상대오차가 이론 잡음의 몇 배인가"]})

    dif = sd[IDN]["🔴🔴🔴 그 둘의 차"]
    rec("Q4", "R_iv* 닫힌꼴과 R_pool 묶음의 가장 큰 도메인 몫 차 < 0.01",
        bool(dif is not None and dif < 0.01),
        {"🔴 몫 차": dif,
         "🔴 가중 벡터의 최대 차": sd[IDN]["🔴🔴 두 가중의 최대 차"]})

    rec("Q5", "검정력이 가장 큰 자는 R_z 가 아니다 — 978 의 정본 선택이 뒤집힌다",
        bool(gt[QQ]["Q5 — 검정력 최대 자가 R_z 가 아닌가"]),
        {"🔴 979 가 고른 자": gt[DEC]["🔴🔴🔴 정본으로 고른 자"],
         "🔴 978 이 고른 자": gt[DEC]["🔴🔴 978 이 고른 자"],
         "🔴 뒤집히나": gt[DEC]["🔴🔴🔴 978 의 정본 선택이 뒤집히나"]})

    rec("Q6", "벌 수를 맞추면 여덟 칸 통과 수가 늘어나는 자가 하나 이상 있다",
        bool(gt[QQ]["Q6 — 벌 수를 맞추니 여덟 칸 통과가 늘어난 자가 있나"]),
        {"🔴 자별 — 정합 대 978 판": gt[QQ]["🔴 자별 여덟 칸 — 정합 대 978 판"]})

    r = sm[MIX]["🔴🔴🔴 피어슨 r (hplt 학습 1,710 행 몫 대 유보 몫)"]
    rec("Q7", "hplt 학습 몫과 유보 몫의 피어슨 r 이 음수이고 |r| < 0.5",
        bool(r is not None and r < 0 and abs(r) < 0.5),
        {"🔴 피어슨 r": r,
         "🔴 스피어만": sm[MIX]["🔴 스피어만 (같은 짝)"],
         "🔴 hplt 전량 층의 r": sm[MIX][
             "🔴 피어슨 r (hplt 전량 몫 대 유보 몫 · 978 이 잰 층)"]})

    rec("Q8", "다섯 겹의 hplt 선택 행이 바이트로 같다",
        bool(sm[FLD]["🔴🔴 다섯 겹의 hplt 선택 행이 바이트로 같은가"]),
        {"🔴 base 쪽은 같은가": sm[FLD]["🔴 다섯 겹의 base 선택 행이 바이트로 같은가"]})

    p6 = sc[PRD]["P6"]
    rec("Q9", "노트 978 의 예측 P6 은 정본 자에서 거짓이다",
        bool(not p6["🔴🔴🔴 979 판(정합 SE · 정본 자) 채점"]),
        {"🔴 정본 자에서 분자/분모": p6["근거"]["🔴🔴🔴 정본 자에서 분자/분모"],
         "🔴 978 판 채점": p6["🔴🔴 978 판(1 벌 SE · 자 넷) 채점"]})

    rec("Q10", "α 이득을 짝 SE 로 재면 u=3 에서 2 SE 를 넘는 칸이 하나 이상 나온다",
        bool(ap["🔴🔴 예측 Q10(u=3 에서 2 짝SE 를 넘는 칸이 하나 이상)"]),
        {"🔴 u=3 에서 넘는 칸": ap["🔴🔴🔴 이득이 2 짝SE 를 넘는 칸(u=3)"],
         "🔴 전체에서 넘는 칸": ap["🔴🔴🔴 이득이 2 짝SE 를 넘는 칸(전체)"],
         "🔴 978 잣대(수준 SD)로는": ap["🔴 978 잣대(수준 SD)로 「잡음을 넘는」 칸"]})

    n_true = sum(1 for v in Q.values() if v["🔴🔴 채점"])
    out = collections.OrderedDict()
    out["무엇"] = ("979 §5 — 🔴 **자기 예측 Q1~Q10 을 전부 채점한다.** "
                 "노트 978 은 자기 여덟 중 둘만 채점했다")
    out["🔴 축"] = "자기 자(수리 레인)"
    out["사전등록"] = "docs/prereg_979_denominator.md §5"
    out["🔴 이 stage 는 자 값을 안 낸다(반증조건 4 분모 밖 · 측정 전에 적었다)"] = True
    out["🔴🔴🔴 예측 Q1~Q10 채점표"] = Q
    out["🔴🔴🔴 참인 예측 분자/분모"] = "%d / %d" % (n_true, len(Q))
    out["🔴🔴 거짓인 예측"] = [k for k, v in Q.items() if not v["🔴🔴 채점"]]
    out["🔴🔴 채점한 예측 분자/분모"] = "%d / %d" % (len(Q), 10)
    out["🔴 등록물 전량 분모(Q 열 + 978 의 P 여덟 + 978 의 반증조건 여덟)"] = 26
    out["통과"] = bool(len(Q) == 10)
    out["🔴 이 절의 `통과` 가 뜻하는 것"] = (
        "🔴 **등록한 예측 열을 하나도 안 빼고 채점했다**(값이 무엇이든 적는다). "
        "🔴 참인 수가 아니라 **채점한 수**가 이 절의 통과 조건이다")
    out["🔴 도장"] = LG.stamp_block(ref, cs0, LG.code_stamp(RAN), t0, RAN, LG.DATA)
    (OUT / "out979_qscore.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["q"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    r = stage_q(a.ref)
    print(json.dumps({k: v for k, v in r.items()
                      if not str(k).startswith("🔴🔴🔴")},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
