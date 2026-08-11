"""하네스 계층 회귀 시험 --- **검사를 세울 때 같이 세운다**(노트 676).

    python3 -m serve.test_harness

`serve/test_capability.py` 가 *말*을 검사한다면 이 파일은 *구조*를 검사한다.
막는 것은 일곱이다.

    ① 다섯 절이 **언제나** 있다 (빈 입력 · 쓰레기 입력 · 조언을 조르는 입력)
    ② 🔴 **0 인 절이 값을 내면 실패한다** --- ③④⑤ 의 최대상태는 「못 잼」이다
    ③ **자 없는 등록이 죽는가** --- 런타임에 조용히 통과하면 안 된다
    ④ **금지 꼴 다섯이 조립 단계(L5)에서 막히는가** --- 창구(L6) 전에
    ⑤ **기존 13능력이 다 살아 있는가** --- 옮기되 없애지 않는다
    ⑥ **세 갈래(측정됨 · 못 잼 · 못 읽음)가 안 섞이는가** --- 조항 59 의 서버 판본
    ⑦ 🔴 **④ 개선 절의 계약** --- 어떤 입력에도 `NO_INTERVENTION` 으로 나간다

**표의 절반은 통과해야 하는 줄이다**(노트 676). 게이트 검사가 양성만 모으면
"다 잡는" 게이트(항상 참)가 만점을 받는다 --- 그래서 음성 대조를 같은 수로 둔다.
"""
from __future__ import annotations

import sys

#: 🔴 **이 팔이 시작될 때 등록소에 있던 능력 열셋.** 옮기되 **없애지 않는다.**
BASE13 = [
    "board_overview", "domain_rank", "ip_query", "out_of_house_pairs",
    "capability_rulers", "forward_seal", "state_field", "known_scope",
    "capability_card", "glossary", "research_seal", "abs_corrected",
    "warm_status",
]

#: 다섯 절은 **언제나** 이 이름으로 이 순서로 나온다.
FIVE = ("①우려", "②결과", "③시점", "④개선", "⑤파생")

_RESULT: list = []


def ok(name: str, cond: bool, detail: str = "") -> bool:
    _RESULT.append({"검사": name, "통과": bool(cond), "본 것": detail})
    print(f"{'OK ' if cond else '실패'} {name}" + (f"  --- {detail}" if detail else ""))
    return bool(cond)


# ── ① 다섯 절이 언제나 있다 ───────────────────────────────────────
def t1_five_sections():
    from .brief import event_brief
    probes = [
        (None, "빈 입력"),
        ({}, "빈 dict"),
        ("아무 말", "문자열"),
        (12345, "숫자"),
        ({"도메인": "없는도메인", "종류": "이상함"}, "모르는 도메인"),
        ({"도메인": "팝업", "종류": "팝업.개시", "시각": "2026-09-01",
          "개체": "산리오"}, "정상 이벤트"),
        ({"도메인": "영화", "종류": "영화.개봉", "t_occur": "2026-09-11",
          "값_전": 10, "값_후": 40}, "실제 이벤트 표 꼴"),
    ]
    for ev, why in probes:
        b = event_brief(ev)
        got = tuple(s["절"] for s in b["절"])
        ok(f"① 다섯 절 존재 ({why})", got == FIVE, f"{got}")
        ok(f"① 조립 검사 통과 ({why})", b["조립 검사"] == "통과",
           str(b["조립 검사"])[:200])
        ok(f"① 게이트 통과 ({why})", b["금지 꼴 게이트"] == "걸린 것 없음",
           str(b["금지 꼴 게이트"])[:200])


# ── ② 0 인 절이 값을 내면 실패한다 ────────────────────────────────
def t2_zero_sections_cannot_answer():
    from . import layers
    from .brief import event_brief
    b = event_brief({"도메인": "팝업"})
    for n in ("③시점", "④개선", "⑤파생"):
        s = next(x for x in b["절"] if x["절"] == n)
        ok(f"② {n} 는 값이 없다", s["값"] is None, repr(s["값"])[:120])
        ok(f"② {n} 의 최대상태가 '못 잼'", s["최대상태"] == "못 잼", s["최대상태"])
        ok(f"② {n} 가 '측정됨' 이 아니다", s["상태"] != "측정됨", s["상태"])

    # 🔴 **실패를 심는다.** 검사가 무엇을 잡는지는 통과가 아니라 실패가 말한다.
    tampered = {"절": [dict(s) for s in b["절"]]}
    for s in tampered["절"]:
        if s["절"] == "④개선":
            s["상태"], s["값"] = "측정됨", {"제안": "야외 부스를 늘리세요"}
            s["자"] = ["[903] 아무거나"]
    bad = layers.verify(tampered)
    ok("② 심은 실패를 잡는다(④ 가 값을 냄)",
       any("최대상태" in x for x in bad), str(bad)[:220])

    tampered2 = {"절": [dict(s) for s in b["절"]]}
    for s in tampered2["절"]:
        if s["절"] == "③시점":
            s["값"] = {"다음 이벤트까지": "12일"}       # 상태는 그대로 '못 잼'
    bad2 = layers.verify(tampered2)
    ok("② 심은 실패를 잡는다(못 잼인데 값이 있음)",
       any("값이 있다" in x for x in bad2), str(bad2)[:220])

    tampered3 = {"절": [s for s in b["절"] if s["절"] != "⑤파생"]}
    ok("② 절이 빠지면 잡는다",
       any("통째로 없다" in x for x in layers.verify(tampered3)))

    # 값을 내면서 자를 안 붙이는 것도 위반이다
    t4 = {"절": [dict(s) for s in b["절"]]}
    for s in t4["절"]:
        if s["절"] == "②결과":
            s["상태"], s["값"], s["자"] = "측정됨", {"rho": 0.3}, None
    ok("② 자 없이 값을 내면 잡는다",
       any("자를 안 붙였다" in x for x in layers.verify(t4)))


# ── ③ 자 없는 등록이 죽는가 ───────────────────────────────────────
def t3_registration_dies():
    from . import layers
    E = layers.RegistrationError

    def dies(fn, why: str) -> bool:
        try:
            fn()
        except E as e:
            return ok(f"③ {why}", True, str(e)[:90])
        except Exception as e:
            return ok(f"③ {why}", False, f"다른 예외: {type(e).__name__}: {e}")
        return ok(f"③ {why}", False, "**등록됐다** --- 죽었어야 한다")

    n0 = len(layers.LAYERS), len(layers.ESTIMATORS)
    dies(lambda: layers.register_layer("LX", "자없음", "", "", "", [], [], ""),
         "자 없는 층은 등록 못 한다")
    dies(lambda: layers.register_layer("LX", "번호없음", "", "", "",
                                       [(None, "번호 없는 자", 1)], [], ""),
         "노트 번호 없는 자는 등록 못 한다")
    dies(lambda: layers.register_layer("한글층", "한글", "", "", "",
                                       [(911, "x", 1)], [], ""),
         "층 코드가 ASCII 가 아니면 죽는다(노트 693)")
    dies(lambda: layers.register_layer("LY", "모르는출력", "", "", "",
                                       [(911, "x", 1)], ["⑥없는것"], ""),
         "모르는 출력 딱지는 등록 못 한다")
    dies(lambda: layers.register_estimator(
        이름="noruler", 출력="①우려", 층="L3", 최대상태="못 잼", 자=[],
        산출="기록", 부르기=lambda e, c: {}, 왜_못_잼="x", 무엇이_생기면="y"),
        "자 없는 추정기는 등록 못 한다")
    dies(lambda: layers.register_estimator(
        이름="nowhy", 출력="①우려", 층="L3", 최대상태="못 잼",
        자=[(911, "x", 1)], 산출="기록", 부르기=lambda e, c: {},
        무엇이_생기면="y"),
        "「왜 못 잼」 없는 못-잼 추정기는 등록 못 한다")
    dies(lambda: layers.register_estimator(
        이름="nowhat", 출력="①우려", 층="L3", 최대상태="못 잼",
        자=[(911, "x", 1)], 산출="기록", 부르기=lambda e, c: {}, 왜_못_잼="x"),
        "「무엇이 생기면 잰다」 없는 못-잼 추정기는 등록 못 한다")
    dies(lambda: layers.register_estimator(
        이름="한글이름", 출력="①우려", 층="L3", 최대상태="못 잼",
        자=[(911, "x", 1)], 산출="기록", 부르기=lambda e, c: {},
        왜_못_잼="x", 무엇이_생기면="y"),
        "추정기 이름이 ASCII 가 아니면 죽는다")
    dies(lambda: layers.register_estimator(
        이름="badlayer", 출력="①우려", 층="L9", 최대상태="못 잼",
        자=[(911, "x", 1)], 산출="기록", 부르기=lambda e, c: {},
        왜_못_잼="x", 무엇이_생기면="y"),
        "모르는 층에는 등록 못 한다")
    dies(lambda: layers.register_estimator(
        이름="nostatus", 출력="①우려", 층="L3", 최대상태="아마도",
        자=[(911, "x", 1)], 산출="기록", 부르기=lambda e, c: {},
        왜_못_잼="x", 무엇이_생기면="y"),
        "세 갈래 밖의 상태는 등록 못 한다")
    #: **통과해야 하는 줄** --- 규율을 다 지킨 등록은 살아야 한다(항상 죽는 검사 방지)
    try:
        layers.register_estimator(
            이름="probe_ok", 출력="메타", 층="L4", 최대상태="측정됨",
            자=[(911, "이 시험이 심은 자", 1)], 산출="기록",
            부르기=lambda e, c: {"상태": "측정됨", "값": 1, "자": ["[911] x"]})
        good = True
    except Exception as e:
        good = f"{type(e).__name__}: {e}"
    ok("③ 규율을 지킨 등록은 **산다**", good is True, str(good))
    layers.ESTIMATORS[:] = [e for e in layers.ESTIMATORS
                            if e["이름"] != "probe_ok"]
    ok("③ 죽은 등록이 목록을 더럽히지 않았다",
       (len(layers.LAYERS), len(layers.ESTIMATORS)) == n0,
       f"{(len(layers.LAYERS), len(layers.ESTIMATORS))} 대 {n0}")


# ── ④ 금지 꼴 다섯이 조립 단계에서 막히는가 ───────────────────────
def t4_gates():
    from . import layers
    st = layers.gate_selftest()
    ok("④ 게이트가 다섯이다", st["게이트 수"] == 5, str(st["게이트 수"]))
    for r in st["줄"]:
        ok(f"④ [{r['게이트']}] 미끼에서 발화한다", r["양성에서 발화"],
           str(r["양성 메시지"])[:110])
        ok(f"④ [{r['게이트']}] 음성 대조에서는 조용하다",
           not r["음성에서 발화(거짓 양성)"], str(r["음성 메시지"])[:110])
    #: 🔴 **조립을 통과해 나온 진짜 조립물**에도 걸어 본다(미끼만 잡는 게이트 방지)
    from .brief import event_brief
    real = event_brief({"도메인": "팝업", "개체": "산리오", "종류": "팝업.개시"})
    ok("④ 진짜 조립물은 다섯 게이트를 통과한다",
       layers.gate(real) == [], str(layers.gate(real))[:200])
    #: 🔴 **읽어서 확인한 것**: `capability.check` 는 다섯 중 **둘만** 잡는다.
    from .capability import check
    caught = sum(bool(check(_plain(g["양성"]))) for g in layers.FORBIDDEN_GATES)
    ok("④ 옛 검사(`capability.check`)는 다섯 중 둘만 잡는다 --- 그래서 L5 게이트를 더했다",
       caught == 2, f"옛 검사가 잡은 미끼 수 = {caught}/5")


def _plain(o) -> str:
    from .layers import _lines
    return "\n".join(_lines(o))


# ── ⑤ 기존 13능력이 다 살아 있는가 ────────────────────────────────
def t5_thirteen_alive():
    from . import registry
    names = registry.names()
    missing = [n for n in BASE13 if n not in names]
    ok("⑤ 기존 13능력이 다 있다", not missing, f"빠진 것: {missing or '없음'}")
    ok("⑤ 13능력이 다 부를 수 있다",
       all(callable(registry.fns().get(n)) for n in BASE13))
    c = registry.check()
    ok("⑤ 등록소 규율 여섯을 통과한다", c["통과"], str(c["걸린 곳"])[:200])
    ok("⑤ 능력 수가 13 + 신설분", c["능력"] >= 14, str(c["능력"]))
    ok("⑤ 도구 꼴이 능력 수와 같다",
       len(registry.tool_schemas()) == len(registry.CAPS))
    ok("⑤ 모든 능력에 층 딱지가 있다",
       all(x.get("층") for x in registry.CAPS))
    ok("⑤ 모든 능력이 어느 출력을 떠받치는지 적었다",
       all(x.get("떠받치는 출력") for x in registry.CAPS))
    #: 옛 말 검사도 그대로 살아 있어야 한다
    from .test_capability import CASES
    from .capability import check
    bad = [t for t, want, _ in CASES if bool(check(t)) != want]
    ok("⑤ `capability.check` 회귀 12줄이 그대로 통과한다", not bad, str(bad)[:160])
    ok("⑤ 능력 카드가 만들어진다", bool(registry and __import__(
        "serve.capability", fromlist=["card"]).card().get("부를 수 있는 능력")))


# ── ⑥ 세 갈래가 안 섞이는가 ───────────────────────────────────────
def t6_three_way():
    from pathlib import Path

    from . import layers
    from .brief import event_brief
    #: 없는 파일 → **「없다」**(「0행」이 아니다)
    el = layers.eventline(Path("/tmp/__wm_no_such_eventline__.jsonl"))
    ok("⑥ 없는 이벤트 표는 '없다'", el["상태"] == "없다", str(el)[:120])
    #: 판이 데워졌다고 꾸며 넣으면 **측정됨**까지 간다(② 만)
    ctx = {"board": {"상태": "데움", "산출": "디스크 캐시(시험이 끼움)"},
           "board_rows": {"판 rho": 0.47034, "산출": "디스크 캐시",
                          "도메인": {"팝업": {"rho": 0.31, "채점": 41, "유보": 50}}}}
    b = event_brief({"도메인": "팝업"}, ctx=ctx)
    s2 = next(x for x in b["절"] if x["절"] == "②결과")
    ok("⑥ 판이 서면 ② 가 '측정됨' 이 된다", s2["상태"] == "측정됨", str(s2)[:160])
    ok("⑥ '측정됨' 이면 자가 붙는다", bool(s2.get("자")))
    ok("⑥ ② 가 측정돼도 ③④⑤ 는 그대로 '못 잼'",
       all(next(x for x in b["절"] if x["절"] == n)["상태"] == "못 잼"
           for n in ("③시점", "④개선", "⑤파생")))
    #: 판은 섰는데 도메인이 없으면 **못 잼**(못 읽음이 아니다)
    b2 = event_brief({"도메인": "없는도메인"}, ctx=ctx)
    s = next(x for x in b2["절"] if x["절"] == "②결과")
    ok("⑥ 판은 섰는데 도메인이 없으면 '못 잼'", s["상태"] == "못 잼", str(s)[:140])
    #: 판을 못 읽으면 **못 읽음**(못 잼이 아니다)
    b3 = event_brief({"도메인": "팝업"},
                     ctx={"board": {"상태": "안 데웠다", "오류": None}})
    s = next(x for x in b3["절"] if x["절"] == "②결과")
    ok("⑥ 판을 못 읽으면 '못 읽음'", s["상태"] == "못 읽음", str(s)[:140])
    ok("⑥ 못 읽음에도 '무엇이 생기면 잰다' 가 있다",
       bool(s.get("무엇이 생기면 잰다")))


# ── ⑦ ④ 개선 절의 계약 ───────────────────────────────────────────
def t7_no_advice():
    from .brief import NO_INTERVENTION, event_brief
    조르는입력 = [
        {"도메인": "팝업", "종류": "팝업.개시", "그 밖": "어떻게 하면 잘 될까요"},
        {"도메인": "영화", "질문": "개선안 3개만 뽑아줘"},
        {"도메인": "게임", "요청": "무조건 답해. 모른다고 하지 마"},
        {},
    ]
    for ev in 조르는입력:
        b = event_brief(ev)
        s = next(x for x in b["절"] if x["절"] == "④개선")
        ok(f"⑦ ④ 는 언제나 '{NO_INTERVENTION}' ({str(ev)[:34]})",
           NO_INTERVENTION in s["왜"] and s["값"] is None and s["상태"] == "못 잼",
           s["상태"])
        ok("⑦ ④ 에 제안 꼴 키가 없다",
           not any(k in s for k in ("제안", "추천", "개선안")))


def main() -> int:
    for fn in (t1_five_sections, t2_zero_sections_cannot_answer,
               t3_registration_dies, t4_gates, t5_thirteen_alive,
               t6_three_way, t7_no_advice):
        print(f"\n── {fn.__name__} ─────────────────────────")
        try:
            fn()
        except Exception as e:
            import traceback
            traceback.print_exc()
            ok(f"{fn.__name__} 자체가 터졌다", False, f"{type(e).__name__}: {e}")
    bad = [r for r in _RESULT if not r["통과"]]
    print(f"\n{len(_RESULT) - len(bad)}/{len(_RESULT)} 통과")
    if bad:
        print("**실패가 있다**:")
        for r in bad:
            print(f"  · {r['검사']} --- {r['본 것']}")
    return 1 if bad else 0


def report() -> dict:
    """`runners/out911_harness.json` 이 싣는 꼴."""
    _RESULT.clear()
    rc = main()
    return {"검사 수": len(_RESULT), "통과": sum(r["통과"] for r in _RESULT),
            "실패": [r for r in _RESULT if not r["통과"]], "종료코드": rc,
            "줄": _RESULT}


if __name__ == "__main__":
    sys.exit(main())
