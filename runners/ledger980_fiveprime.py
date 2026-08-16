#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""980 — 🔴 `⑤′` 결과를 **원장 1급 항목**으로 적는다.

🔴 `docs/루프.md:682` · 선례 965·967 — **⑤′ 불통과 결정은 원장 1급 항목이다.**
979 는 ⑤′ 를 돌리고도 그것을 원장에 1급으로 안 적었다(티처 #118 C6).

🔴 손 전사 금지(규칙 D) — 수는 전부 `runners/fiveprime_980.json` 의 키에서 온다.
"""
import collections
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
FP = ROOT / "runners/fiveprime_980.json"
DEN = ROOT / "data/lab/denominator.json"
GATE_NEW = "⓪ 관문(가지의 커밋된 트리 · 🔴 정본)"
GATE_OLD = "⓪ 관문(작업 트리 · 🔴 980 부터 진단 · 절 분모 밖)"


def main():
    r = json.loads(FP.read_text(encoding="utf-8"))
    secs = {k: v for k, v in r.items() if isinstance(v, dict) and "통과" in v}
    fail = sorted(k for k, v in secs.items() if not v["통과"])
    g = r.get(GATE_NEW, {})
    o = r.get(GATE_OLD, {})
    d = json.loads(DEN.read_text(encoding="utf-8"),
                   object_pairs_hook=collections.OrderedDict)
    d["🔴🔴🔴 노트 980 ⑤′ 취합 검사 — 원장 1급 항목(루프.md:682 · 선례 965·967)"] = \
        collections.OrderedDict([
            ("🔴 산출물", "runners/fiveprime_980.json"),
            ("🔴 절 수(분모)", r.get("🔴 절 수(분모)")),
            ("🔴🔴 실패한 절", fail or "없음"),
            ("🔴🔴 전체 통과", bool(r.get("통과"))),
            ("🔴🔴🔴 ⓪ 관문(정본 · 가지의 커밋된 트리) 통과", g.get("통과")),
            ("🔴 견준 가지", g.get("🔴 견준 가지")),
            ("🔴 가지 sha", g.get("🔴 가지 sha")),
            ("🔴 갈린 경로 전량(분모)", g.get("🔴 분모: 갈린 경로 전량")),
            ("🔴 데몬(규칙 B) 면제 경로 수", g.get("🔴 데몬(규칙 B) 면제 경로 수")),
            ("🔴🔴 면제 밖에서 갈린 경로", g.get("🔴🔴 분자: 면제 밖에서 갈린 경로")),
            ("🔴 그 경로", g.get("🔴 그 경로")),
            ("🔴 옛 작업 트리 관문의 날 실측(진단 · 절 분모 밖)",
             o.get("🔴 이 절이 잰 날 것")),
            ("🔴 왜 옛 관문을 내렸나",
             "🔴 규칙 A 가 checkout 을 금지하므로 HEAD 는 main 이고 사이클 커밋은 "
             "가지에만 있다 — 작업 트리 대 HEAD 를 물으면 규칙 A·B 가 서로를 막는다. "
             "967 이 12 사이클 전에 물었고 980 이 답을 docs/루프.md 4-나 에 썼다"),
            ("🔴 979 가 적은 실패 이유는 틀렸다",
             "더러운 28 중 데몬은 1 줄이고 27 이 979 자기 미커밋물 — 기전은 규칙 B 가 "
             "아니라 규칙 A 다(⑤′ 가 979 커밋이 하나도 없는 main 에서 돌았다)"),
            ("날짜", dt.date.today().isoformat()),
        ])
    DEN.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"🔴 원장 항목 수": len(d), "🔴 실패한 절": fail or "없음",
                      "🔴 ⓪ 관문(정본) 통과": g.get("통과"),
                      "🔴 전체 통과": bool(r.get("통과"))},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
