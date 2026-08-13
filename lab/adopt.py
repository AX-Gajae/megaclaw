# -*- coding: utf-8 -*-
"""🔴 **층 채택 규칙** — 959 가 ㉣ 을 넣었고 **961 이 그것을 3값으로 고친다**.

**왜(959).** 958 의 산출물이 `"🔴🔴 채택(㉠㉡㉢)": true` 를 찍었고 **원장에도 그대로 들어갔다**.
그런데 같은 산출물의 다른 칸이 *「도메인 지시자를 넣으면 그 위에서 층 ③ 은 **해롭다**(−0.0075 ·
「다 — 뺀다」)」* 를 이미 재 놓았다. 🔴 **즉 「채택한다」와 「빼야 한다」가 한 파일 안에 같이 있었고,
「빼야 한다」는 산문에만 있었다**(티처 #97 F3).

    ㉣ **더 싼 대체물 검사** — 층을 대신할 후보(예: 도메인 지시자)를 넣었을 때
       ㉮ 그 대체물이 **혼자서 든다** **그리고**
       ㉯ 그 **위에서** 이 층이 **죽는다**
       → 🔴 **㉠㉡㉢ 을 다 통과해도 채택하지 않는다.**

**🔴🔴 왜 961 이 고치나 — 이 파일이 자기 조항 59 를 어기고 있었다.**
959 판의 ㉮ 는 `alt_delta > alt_T` 하나로 **참/거짓 둘**만 냈다. 그래서 `Δρ` 가
**문턱 띠 안**(= 「못 가른다」)일 때 ㉮ 가 조용히 `거짓` 이 되고, ㉯ 는 `layer_delta <= T` 라
띠 안이면 조용히 `참` 이 됐다. 🔴 **960 의 도메인 군집 판에서 두 하위검사가 「둘 다 못 가른다」인데
`채택 = true` 가 나왔다**(960 이 자진 신고했고 티처 #99 M3 가 확인했다).

**🔴 조항 59**: 「없다」와 「못 봤다」와 「못 읽었다」는 셋이다.
**「못 가른다」는 「아니다」가 아니다.** 그래서 961 부터 두 하위검사는 **참 / 거짓 / 모른다** 셋을 낸다.

    ㉮ 대체물이 혼자 드나 :  Δρ >  T  → 참 ·  Δρ < −T → 거짓 ·  그 사이 → 🔴 **모른다**
    ㉯ 그 위에서 층이 죽나 :  Δρ < −T  → 참 ·  Δρ >  T → 거짓 ·  그 사이 → 🔴 **모른다**

그리고 **클레이니 3값 논리**로 잇는다(`모른다` 는 전염되되 결정적 `거짓` 은 이긴다):

    더싼대체물있나 = ㉮ ∧ ㉯      (둘 다 참이면 참 · 하나라도 거짓이면 거짓 · 아니면 모른다)
    ㉣ 통과        = ¬더싼대체물있나
    채택           = ㉠ ∧ ㉡ ∧ ㉢ ∧ ㉣통과   —  🔴 **`모른다` 는 통과가 아니다 → 보류(False)**

🔴 **조항 62**: 이 파일이 있다고 값이 옳아지지 않는다. **부르는 쪽이 이 함수의 답을 키로 내야** 한다.
🔴 **그리고 961 이 `rulers()` 를 더한다** — **자마다 문턱과 「자들 사이의 논리적 포함관계」를
산출물 키로 낸다**. 안 그러면 **「자 넷이 다 같은 답」은 하나의 답을 넷으로 센 것**이다
(티처 #99 M1: ㉢ 의 통과 조건이 사실상 `Δρ > 0` 이라 **㉢ ⊂ ㉠**).
"""
from __future__ import annotations

T3_TRUE = "참"
T3_FALSE = "거짓"
T3_UNK = "모른다"


def band(delta: float | None, T: float | None, *, positive_is_true: bool = True) -> str:
    """🔴 **3값 판정** — 문턱 띠 안이면 `모른다`.

    `positive_is_true=True`  : Δρ >  T → 참 · Δρ < −T → 거짓   (「드나」)
    `positive_is_true=False` : Δρ < −T → 참 · Δρ >  T → 거짓   (「죽나」)
    """
    if delta is None:
        return T3_UNK
    t = abs(T) if T is not None else 0.0
    if delta > t:
        return T3_TRUE if positive_is_true else T3_FALSE
    if delta < -t:
        return T3_FALSE if positive_is_true else T3_TRUE
    return T3_UNK


def and3(a: str, b: str) -> str:
    """클레이니 ∧ — 하나라도 `거짓` 이면 `거짓`, 둘 다 `참` 이면 `참`, 아니면 `모른다`."""
    if a == T3_FALSE or b == T3_FALSE:
        return T3_FALSE
    if a == T3_TRUE and b == T3_TRUE:
        return T3_TRUE
    return T3_UNK


def not3(a: str) -> str:
    return {T3_TRUE: T3_FALSE, T3_FALSE: T3_TRUE}.get(a, T3_UNK)


def adopt(sum_pass: bool, sub_sign_pass: bool, perm_pass: bool,
          alt_delta: float | None = None, alt_T: float | None = None,
          layer_on_alt_delta: float | None = None,
          layer_on_alt_T: float | None = None) -> dict:
    """네 조건을 다 보고 **하나의 불리언**을 낸다.

    🔴 **961 개정**: ㉣ 의 두 하위검사가 **참/거짓/모른다** 셋을 낸다.
    대체물 정보가 **없어도**, 있는데 **띠 안이어도** ㉣ 은 「모른다」다 —
    🔴 **「통과」가 아니다**(조항 59). 모르면 채택을 **보류**한다.
    """
    three = bool(sum_pass and sub_sign_pass and perm_pass)
    base = {
        "㉠ 합산 Δρ > T": bool(sum_pass),
        "㉡ 부 표적 부호 유지": bool(sub_sign_pass),
        "㉢ 순열 null 밖": bool(perm_pass),
    }
    if alt_delta is None or layer_on_alt_delta is None:
        return {
            **base,
            "🔴 ㉣ 더 싼 대체물": T3_UNK,
            "㉣ 대체물이 혼자 드나(3값)": T3_UNK,
            "㉣ 그 위에서 이 층이 죽나(3값)": T3_UNK,
            "🔴 ㉠㉡㉢ 만으로는": three,
            "🔴🔴 채택(㉠㉡㉢㉣)": False,
            "왜": "㉣ 을 안 쟀다. 「모른다」는 「통과」가 아니다(조항 59) — 채택을 보류한다",
            "🔴 3값 규약": "참/거짓/모른다 — 문턱 띠 안(|Δρ| ≤ T)은 「모른다」다",
        }
    if alt_T is None or layer_on_alt_T is None:
        # 🔴 문턱을 안 주면 띠가 0 폭이다 — 그 사실을 신고한다(조항 59: 「없다」와 「못 봤다」는 둘이다)
        warn = "⚠ 문턱(T)을 안 줬다 — 띠 폭 0 으로 쟀다. 「못 가른다」가 원리상 안 나온다"
    else:
        warn = None
    alt_stands = band(alt_delta, alt_T, positive_is_true=True)
    layer_dies = band(layer_on_alt_delta, layer_on_alt_T, positive_is_true=False)
    cheaper = and3(alt_stands, layer_dies)
    gate4 = not3(cheaper)
    adopted = bool(three and gate4 == T3_TRUE)
    if cheaper == T3_TRUE:
        why = "더 싼 대체물이 같은 정보를 주고 그 위에서 이 층이 해롭다 — 채택하지 않는다"
    elif cheaper == T3_UNK:
        why = ("🔴 ㉣ 이 「모른다」다 — 하위검사 하나 이상이 문턱 띠 안이다. "
               "「모른다」는 「통과」가 아니다(조항 59) — 채택을 보류한다")
    elif not three:
        why = "㉠㉡㉢ 중 하나가 불통과다"
    else:
        why = "네 조건을 다 통과했다(㉣ 은 「더 싼 대체물이 없다」로 결정됐다)"
    out = {
        **base,
        "㉣ 대체물이 혼자 드나(3값)": alt_stands,
        "㉣ 그 위에서 이 층이 죽나(3값)": layer_dies,
        "🔴 ㉣ 더 싼 대체물이 있나(3값)": cheaper,
        "🔴 ㉣ 통과(3값)": gate4,
        "🔴 ㉠㉡㉢ 만으로는": three,
        "🔴🔴 채택(㉠㉡㉢㉣)": adopted,
        "왜": why,
        "🔴 3값 규약": "참/거짓/모른다 — 문턱 띠 안(|Δρ| ≤ T)은 「모른다」이고 「통과」가 아니다",
        "쓴 문턱": {"alt_T": alt_T, "layer_on_alt_T": layer_on_alt_T},
    }
    if warn:
        out["⚠ 신고"] = warn
    return out


def rulers(sum_delta: float, sum_T: float,
           sub_delta: float, sub_T: float,
           perm_obs: float, perm_p95: float,
           card_T: float) -> dict:
    """🔴 **자마다 문턱과 「자들 사이의 논리적 포함관계」를 낸다**(티처 #99 M1).

    **왜.** 960 은 「자 넷이 다 같은 답을 냈다」고 적었다. 그런데 ㉢ 의 통과 조건이
    `관측 > 상위5%` 이고 상위5% 가 **−0.000493**(사실상 0)이면 ㉢ 은 `Δρ > 0` 과 같고,
    ㉠ 은 `Δρ > 0.020060` 이다. **㉠ 이 참이면 ㉢ 은 자동으로 참이다 — ㉢ ⊂ ㉠.**
    🔴 **그러면 「넷이 다 같은 답」은 하나의 답을 넷으로 센 것이다.**
    """
    def implies(a_thr: float, b_thr: float) -> bool:
        """`Δρ > a_thr` 이면 항상 `Δρ > b_thr` 인가 — 즉 a 의 통과 집합 ⊂ b 의 통과 집합."""
        return a_thr >= b_thr

    thr = {
        "㉠ 합산": {"자": "Δρ > T", "실효 문턱": sum_T, "관측": sum_delta,
                 "🔴 문턱이 어디서 왔나": f"max(CARD_T={card_T}, 2·SE_부트)"},
        "㉡ 부 표적": {"자": "부호가 안 뒤집혔나", "실효 문턱": 0.0, "관측": sub_delta,
                   "🔴 문턱이 어디서 왔나": "부호만 본다 — 크기 문턱이 없다",
                   "곁 · 그 표적의 T": sub_T},
        "㉢ 순열 null": {"자": "관측 > 상위 5%", "실효 문턱": perm_p95, "관측": perm_obs,
                      "🔴 문턱이 어디서 왔나": "열 순열 200회의 95분위"},
    }
    a_thr, c_thr, b_thr = sum_T, perm_p95, 0.0
    return {
        "🔴 무엇": ("자마다 **실효 문턱**을 한 자리에 놓고, 자들 사이의 **논리적 포함관계**를 낸다. "
                 "🔴 포함되는 자는 **독립된 증거가 아니다**"),
        "자별 문턱": thr,
        "🔴🔴 ㉢ ⊂ ㉠ (㉠ 통과 ⟹ ㉢ 통과)": bool(implies(a_thr, c_thr)),
        "🔴 ㉡ ⊂ ㉠ (㉠ 통과 ⟹ ㉡ 부호 +)": bool(implies(a_thr, b_thr)),
        "🔴 ㉢ 의 문턱이 사실상 0 인가": bool(abs(perm_p95) < card_T),
        "🔴 ㉢ 문턱 / 카드 문턱": float(perm_p95 / card_T) if card_T else None,
        "🔴 독립된 자의 수(포함되는 것을 빼고)": 1 + int(not implies(a_thr, c_thr)) + int(not implies(a_thr, b_thr)),
        "⚠ 이것이 뜻하는 것": ("포함관계가 참이면 그 자들은 **한 자의 되풀이**다. "
                       "「자 셋이 다 같은 답」이라고 쓰면 하나의 답을 셋으로 센 것이다"),
    }
