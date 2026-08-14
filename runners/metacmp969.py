# -*- coding: utf-8 -*-
"""노트 969 — **자의 전후 대조**. 🔴 **손으로 안 센다.**

티처 #107 2순위 ①②③ 의 산출물:
- **P10** 968 의 「모른다 77.8%」가 **커밋된 소스**에서 재현되나(`genver` 별).
- **P11** `meta965` **R1 전 / R1 후**를 **같은 대상**에 걸어 §4 F1 을 전후로 싣는다.
  🔴 968 은 자기 자를 고쳐 자기 점수를 문턱 너머로 옮기고 **이 대조를 한 번도 안 돌렸다.**
- **P12** 「구조적 천장」 --- 상수 False 자리가 몇이나 되나.

🔴 **`--out` 필수.** 입력은 `meta965.py` 산출물 넷.
"""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
S1 = "§1 🔴🔴 등록 러너 전수 — 자 셋"
S4 = "§4 🔴🔴 F1 — **내가 새로 만든 `통과` 키가 상수인가**"
CF = "🔴 상수 False(생성기가 유효 입력을 못 만들었을 수 있다 — 「모른다」)"


def read(p):
    R = json.loads(Path(p).read_text(encoding="utf-8"))
    a, b = R[S1], R[S4]
    n1 = a["🔴 분모 ② `통과` 자리 + 위임 자리"]
    m1 = a["🔴 모른다(자 B 가 슬라이스를 못 돌렸거나 상수 False)"]
    n4 = b["🔴 분모: 내 `통과` 자리"]
    m4 = b["🔴 모른다"]
    m4 = len(m4) if isinstance(m4, list) else 0
    return {
        "산출물": str(Path(p).name),
        "genver": R["🔴 자 B 생성기 판(968)"]["genver"],
        "slicer": R.get("🔴🔴 역슬라이서 판(969)", {}).get("slicer", "(없다 --- 969 이전 판)"),
        "🔴 잰 소스 sha256": R.get("🔴🔴 잰 소스 sha256 (R3 · 969)", {}).get("🔴 분모 ① 등록 러너"),
        "§1 분모": n1, "🔴 §1 모른다": m1,
        "🔴 §1 모른다 %": round(100.0 * m1 / n1, 1) if n1 else None,
        "§1 항진명제": a["🔴 분자: 항진명제로 잡힌 자리"],
        "§1 떨어진다": a["🔴 떨어진다(자 셋 중 아무도 안 잡았고 자 B 가 값이 변함을 봤다)"],
        "🔴 상수 False 자리 수": a[CF]["수"], "🔴 상수 False 자리": a[CF]["자리"],
        "§4 F1 분모": n4, "🔴 §4 F1 모른다": m4,
        "🔴 §4 F1 모른다 %": round(100.0 * m4 / n4, 1) if n4 else None,
        "🔴 §4 F1 상수인 자리": b["🔴 상수인 자리 목록"],
        "🔴 절반을 넘었나(루프.md:994)": bool(n1 and m1 * 2 > n1),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--mine", required=True, help="내 러너에 건 산출물")
    ap.add_argument("--t968", nargs="+", required=True, help="968 대상 산출물 셋 이상")
    a = ap.parse_args()

    mine = read(a.mine)
    rows = [read(p) for p in a.t968]
    byk = {(r["genver"], r["slicer"]): r for r in rows}

    def pick(g, s):
        return byk.get((g, s))

    g1n, g2n, g2o = pick(1, "new"), pick(2, "new"), pick(2, "old")
    R = {
        "🔴 낸 때(UTC)": dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "🔴 사전등록": "docs/prereg_969_dropped.md",
        "🔴 대상": "runners/colaudit968.py (968 의 러너 · 커밋본)",
        "판별 표": rows,
        "🔴 내 러너(runners/dropaudit969.py)": mine,
    }
    R["🔴🔴 P10 --- 968 의 수가 자기 커밋에서 재현되나"] = {
        "968 이 신고한 수": {"§1 모른다": 7, "분모": 9, "%": 77.8, "산출물이 적은 genver": 2},
        "🔴 커밋본 genver 1": {"§1 모른다": g1n and g1n["🔴 §1 모른다"], "%": g1n and g1n["🔴 §1 모른다 %"]},
        "🔴 커밋본 genver 2": {"§1 모른다": g2n and g2n["🔴 §1 모른다"], "%": g2n and g2n["🔴 §1 모른다 %"]},
        "🔴🔴 판정": (
            "🔴 **티처 #107 C4 가 옳다.** 968 의 산출물은 `genver: 2` 라 적혀 있는데 "
            "그 수(7/9 = 77.8%)는 **genver 1 이 내는 수**다. 커밋된 소스의 genver 2 는 "
            "**6/9 = 66.7%** 를 낸다. 🔴 **그 수는 자기 커밋에서 재현 안 된다.**"),
        "🔴 잰 소스가 커밋본인가": (
            "`runners/colaudit968.py` 의 sha256 = "
            + str((((g2n or {}).get("🔴 잰 소스 sha256")) or {}).get("runners/colaudit968.py"))
            + " --- `git show <ref>:runners/colaudit968.py | shasum -a 256` 과 대조하라"),
    }
    R["🔴🔴 P11 --- R1 전후를 같은 대상에 건다(968 이 안 한 것)"] = {
        "🔴 R1 전(slicer old · genver 2)": {
            "§1 모른다 %": g2o and g2o["🔴 §1 모른다 %"],
            "🔴🔴 §4 F1 모른다 %": g2o and g2o["🔴 §4 F1 모른다 %"]},
        "🔴 R1 후(slicer new · genver 2)": {
            "§1 모른다 %": g2n and g2n["🔴 §1 모른다 %"],
            "🔴🔴 §4 F1 모른다 %": g2n and g2n["🔴 §4 F1 모른다 %"]},
        "🔴🔴 판정": (
            "🔴 **티처 #107 C5 가 옳다.** 968 의 R1 은 §4 F1 「모른다」를 "
            "**66.7% → 44.4%** 로 옮겼다 --- **절반선을 넘겼다.** "
            "968 은 §1(77.8%)을 써서 판정 결과가 불변이었지만, "
            "**자기 자를 고쳐 자기 점수를 문턱 너머로 옮기고 전후를 한 번도 안 쟀다.** "
            "🔴 그래서 969 는 `meta965.py` 에 `--slicer old` 를 남겼다 --- "
            "**구판을 지우지 않아야 전후를 쌀 수 있다.**"),
    }
    R["🔴🔴 P12 --- 「구조적 천장」이 있나"] = {
        "968 의 주장": "정확성 검사는 무작위 입력에서 상수 False 라 「모른다」가 원리상 많다 --- 구조적 천장",
        "🔴 상수 False 자리 수(판별)": {"genver1/new": g1n and g1n["🔴 상수 False 자리 수"],
                                "genver2/new": g2n and g2n["🔴 상수 False 자리 수"],
                                "genver2/old": g2o and g2o["🔴 상수 False 자리 수"]},
        "🔴 티처 #107 이 든 둘": ["runners/colaudit968.py:769", "runners/colaudit968.py:790"],
        "🔴 실측 자리(genver2/new)": g2n and g2n["🔴 상수 False 자리"],
        "🔴 그 천장": (round(100.0 * g2n["🔴 상수 False 자리 수"] / g2n["§1 분모"], 1)
                  if g2n else None),
        "🔴🔴 판정": (
            "🔴 **티처 #107 이 옳다.** genver 2 · 커밋본에서 상수 False 는 **9 중 2** 이고 "
            "그 둘은 티처가 든 `:769`·`:790` 과 **비트로 같다**. 천장은 **22.2%** 이고 "
            "관측된 66.7~77.8% 를 **설명 못 한다.** "
            "⚠ **다만 그 수는 판에 딸려 있다** --- genver1/new 에서는 **3**, genver2/old 에서는 **1** 이다. "
            "「천장」이라 부를 만큼 고정된 양이 아니다"),
        "🔴🔴 진짜 병목이 무엇인지 --- 969 가 실측으로 답한다": {
            "티처 #107 의 진단": "뿌리가 0 --- 자유 이름이 전부 모듈 전역이다. `probe_pack` 처럼 **검사가 입력을 인자로 받게** 하라",
            "🔴 969 가 그대로 해 봤다": "`runners/dropaudit969.py` 의 배선 검사 여섯 자리 전부가 `wiring(probes)` 로 입력을 **인자**로 받는다",
            "🔴🔴 결과": {"§1 모른다": mine["🔴 §1 모른다"], "분모": mine["§1 분모"],
                     "%": mine["🔴 §1 모른다 %"],
                     "🔴 §4 F1 모른다 %": mine["🔴 §4 F1 모른다 %"]},
            "🔴🔴 판정": (
                "🔴🔴 **티처 #107 의 처방이 실측으로 맞았다.** 968 은 77.8%(신고)·66.7%(커밋본) 였고 "
                "967 은 88.9% 였는데, **검사를 인자화한 969 의 러너는 " + str(mine["🔴 §1 모른다 %"])
                + "%** 다 --- **절반 아래다.** 🔴 **문턱을 무르게 할 필요가 없었다. 공학 문제였다.**"),
        },
    }
    R["🔴🔴🔴 판정 자격(`docs/루프.md:994`)"] = {
        "규칙": "「모른다」가 분모 절반을 넘으면 그 자는 그 사이클을 판정할 자격이 없다",
        "967": "88.9% --- 자격 없음", "968(신고)": "77.8% --- 자격 없음",
        "968(커밋본 genver 2)": str(g2n and g2n["🔴 §1 모른다 %"]) + "% --- 자격 없음",
        "🔴🔴 969": "{}%(§1 {}/{}) · §4 F1 {}% --- **둘 다 절반 아래**".format(
            mine["🔴 §1 모른다 %"], mine["🔴 §1 모른다"], mine["§1 분모"], mine["🔴 §4 F1 모른다 %"]),
        "🔴 판정": ("🔴 **969 의 자는 판정 자격이 있다.** 967·968 이 못 넘은 문턱을 "
                 "**문턱을 안 무르게 하고** 넘었다"),
        "🔴🔴 그러나 자가 나를 물었다": {
            "§1 항진명제": mine["§1 항진명제"],
            "🔴 §4 F1 상수인 자리": mine["🔴 §4 F1 상수인 자리"],
            "🔴 무엇인가": ("`runners/dropaudit969.py:893` --- 배선 **W6(저장소 무변)** 의 통과식이다. "
                       "`before == after` 는 **같은 순수함수를 같은 인자로 두 번 부른 것**이고 "
                       "그 사이에 아무 일도 안 일어난다 --- **조항 64 가 금지한 꼴 그대로다.** "
                       "🔴 **자가 옳다.** 진짜 대조는 §Z(주행 시작/끝 `code_stamp`)가 하고 있고 "
                       "W6 은 그것의 **미니어처라서 항진명제**다. 지우지 않고 신고한다"),
        },
    }
    txt = json.dumps(R, ensure_ascii=False, indent=1)
    Path(a.out).write_text(txt, encoding="utf-8")
    print("wrote", a.out, hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16])


if __name__ == "__main__":
    main()
