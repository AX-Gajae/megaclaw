# -*- coding: utf-8 -*-
"""팔 935 **자기 적발** — 정본을 다시 읽어 관문의 **도달 가능 폭 ÷ 문턱**을 낸다 (이슈 #178).

🔴 왜 붙이나
  정본은 관문의 검정력을 **「기준 팔 MAE 의 가짓수」**로만 신고한다(티처 #76 M1 이 요구한 형태).
  그런데 #178 의 `gap925.gate_report` 는 검정력을 **「도달 가능 폭 ÷ 문턱」**으로 잰다.
  🔴 **가짓수가 많아도 폭이 문턱에 못 닿으면 관문은 못 걸린다.** 두 눈금이 다른 답을 낼 수 있으므로
  둘 다 신고한다. 🔴 **정본을 한 자도 안 고친다** — 이 파일은 별도 산출물이다(933 의 addendum 과 같은 형식).

산출물: runners/out935_addendum.json
사용:   python3 runners/rawpanel935_addendum.py
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))

from state.gap925 import gate_report  # noqa: E402
from state.perm922 import COMPARABLE_REL  # noqa: E402
from state.interval918 import sha256_text  # noqa: E402

SRC = ROOT / "runners/out935_rawpanel.json"
OUT = ROOT / "runners/out935_addendum.json"
PANELS = ("① 원판 전량", "② 원판 − b_prv=−1 칸", "진단 b_prv=−1 칸만")


def main() -> None:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    recs = d["⑤ 뽑기 원자료 — 🔴 뽑기마다 전량 싣는다"]["기록"]
    out = {
        "무엇": "935 자기 적발 — 관문의 검정력을 **두 눈금**으로 잰다(가짓수 · 도달 가능 폭 ÷ 문턱)",
        "정본": str(SRC.relative_to(ROOT)),
        "정본 sha256": sha256_text(SRC),
        "🔴 정본을 고쳤나": False,
        "뽑기 수(분모)": len(recs),
        "문턱(perm922.COMPARABLE_REL)": COMPARABLE_REL,
    }
    per = {}
    for p in PANELS:
        rel = np.asarray([r[p]["비교가능성 상대차"] for r in recs], float)
        base = np.asarray([r[p]["기준 팔 MAE"] for r in recs], float)
        gr = gate_report("비교가능성(기후값 MAE 상대차) · %s" % p,
                         axis="상대차 = (귀무 − 진짜)/진짜",
                         threshold=COMPARABLE_REL,
                         reach_lo=0.0, reach_hi=float(np.abs(rel).max()),
                         observed={"평균": float(rel.mean()), "최소": float(rel.min()),
                                   "최대": float(rel.max())},
                         note="reach 는 0 에서 |상대차| 의 최댓값까지 — 「귀무 뽑기가 문턱에 닿을 수 있나」")
        per[p] = {
            "🔴 눈금 A — 기준 팔 MAE 가짓수(티처 #76 M1)": {
                "가짓수": int(np.unique(base).size), "분모": int(base.size),
                "🔴 검정력이 있나(≥2)": bool(np.unique(base).size >= 2)},
            "🔴 눈금 B — 도달 가능 폭 ÷ 문턱(이슈 #178 · gap925.gate_report)": gr,
            "🔴 문턱까지 남은 여유(문턱 − |상대차| 최대)": float(COMPARABLE_REL - np.abs(rel).max()),
            "🔴 문턱의 몇 %까지 갔나": float(100.0 * np.abs(rel).max() / COMPARABLE_REL),
            "통과한 뽑기": int(sum(r[p]["🔴 비교가능성 통과"] for r in recs)),
            "🔴 두 눈금이 같은 답인가": bool(
                (np.unique(base).size >= 2) == (not gr["🔴 검정력 0 인가(비 < 1 이면 자동)"])),
        }
    out["판별"] = per
    out["🔴🔴 자기 적발"] = [
        "🔴 **판 ① 에서 두 눈금이 다른 답을 낸다.** 가짓수는 %d 가지(검정력 있음)인데 "
        "도달 가능 폭은 문턱의 **%.1f%%** 밖에 안 된다 — 즉 **관문은 발화 가능한 물건이지만 "
        "이 귀무들로는 못 걸린다.** 정본의 「관문에 검정력이 있다」는 **눈금 A 의 문장**이고, "
        "눈금 B 로는 여전히 「이 뽑기 범위에서는 못 걸린다」다. 🔴 933 의 「가짓수 1 = 원리상 발화 불가」와는 "
        "**다른 종류의 못 걸림**이다(그건 항등이고 이건 폭 부족이다)"
        % (per[PANELS[0]]["🔴 눈금 A — 기준 팔 MAE 가짓수(티처 #76 M1)"]["가짓수"],
           per[PANELS[0]]["🔴 문턱의 몇 %까지 갔나"]),
        "🔴 **판 ② 는 문턱의 %.1f%% 까지 갔다**(최대 상대차 %.6f 대 문턱 %.2f) — 통과했지만 "
        "**여유가 %.6f 뿐**이다. 「200/200 통과」를 안심의 근거로 쓰면 안 된다"
        % (per[PANELS[1]]["🔴 문턱의 몇 %까지 갔나"],
           per[PANELS[1]]["🔴 눈금 B — 도달 가능 폭 ÷ 문턱(이슈 #178 · gap925.gate_report)"]["🔴 도달 가능 폭"],
           COMPARABLE_REL, per[PANELS[1]]["🔴 문턱까지 남은 여유(문턱 − |상대차| 최대)"]),
        "🔴 **진단 ③ 은 관문이 실제로 걸렸다**(통과 0/%d) — 사전등록 §4-다 가 「원리상 걸린다」고 "
        "미리 적은 그대로다. **걸린 대로 신고한다.**" % len(recs),
    ]
    # ── 🔴 칸 분해 — **원판의 수로** 다시 낸다 (조항 60 · 티처 #76 M4 형식판) ──
    vv = d["⑥ 🔴 판정용 순열"]
    rows = {p: d["② 항등 검사 (사전등록 §7-2·§7-4)"]
            ["W3 b_prv=−1 이 prevmed 결측과 같은 행인가 · 행 회계"]["행"][k]
            for p, k in zip(PANELS, ("판 ①", "판 ②", "진단 ③"))}
    n1 = rows[PANELS[0]]
    eff = {p: vv[p]["🔴 효과(진짜 − 귀무평균 · 일)"] for p in PANELS}
    imp = {p: vv[p]["진짜"] for p in PANELS}
    share_eff = eff[PANELS[2]] * rows[PANELS[2]] / n1 / eff[PANELS[0]]
    share_imp = imp[PANELS[2]] * rows[PANELS[2]] / n1 / imp[PANELS[0]]
    out["🔴🔴 칸 분해 — 원판의 수로 (🔴 티처 #76 의 87.5% 는 [달력제거] 판의 수다)"] = {
        "행": rows,
        "b_prv=−1 칸이 홀드아웃 행의 몇 %": 100.0 * rows[PANELS[2]] / n1,
        "🔴 그 칸이 나르는 **효과**의 몫(원판)": share_eff,
        "🔴 그 칸이 나르는 **개선**의 몫(원판)": share_imp,
        "합 검사(효과)": {"칸 밖 + 칸": eff[PANELS[1]] * rows[PANELS[1]] / n1
                                + eff[PANELS[2]] * rows[PANELS[2]] / n1,
                      "전량": eff[PANELS[0]],
                      "🔴 맞나": bool(abs(eff[PANELS[1]] * rows[PANELS[1]] / n1
                                       + eff[PANELS[2]] * rows[PANELS[2]] / n1
                                       - eff[PANELS[0]]) < 1e-12)},
        "합 검사(개선)": {"칸 밖 + 칸": imp[PANELS[1]] * rows[PANELS[1]] / n1
                                + imp[PANELS[2]] * rows[PANELS[2]] / n1,
                      "전량": imp[PANELS[0]],
                      "🔴 맞나": bool(abs(imp[PANELS[1]] * rows[PANELS[1]] / n1
                                       + imp[PANELS[2]] * rows[PANELS[2]] / n1
                                       - imp[PANELS[0]]) < 1e-12)},
        "🔴🔴 자기 적발": "판정 커밋 0be729569 의 메시지와 원장 첫 판이 **티처의 87.5%% 를 그대로 옮겼다.** "
                    "그 수는 **[달력제거] 판**의 칸 분해(#76 M8)이고, **원판에서는 효과의 %.1f%% · "
                    "개선의 %.1f%%** 다. 🔴 **한 문단에 두 판의 수를 섞는 것**(조항 60 · #76 M4 가 933 "
                    "논문에서 잡은 바로 그 형식판)이라 여기서 정정한다. **판정은 안 바뀐다** — "
                    "p·k·Z 는 이 수를 한 번도 안 쓴다" % (100 * share_eff, 100 * share_imp),
        "🔴 그래도 남는 문장": "그 칸은 홀드아웃 행의 **4.15%** 인데 효과의 **약 절반**을 나른다 — "
                       "「한 칸이 헤드라인을 나른다」는 우려 자체는 원판에서도 참이다. "
                       "그래서 판 ② 가 필요했고, 그 칸을 빼도 k=0 이다",
    }
    out["🔴 판정이 바뀌나"] = ("아니다 — 순열 p 는 관문 통과·불통과로 부분집합을 안 만든다(전량으로 냈다). "
                       "바뀌는 것은 **「관문이 검정력을 가졌다」의 뜻**이다: 눈금 A 로는 참, 눈금 B 로는 거짓")
    out["쓴 시각(UTC)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
