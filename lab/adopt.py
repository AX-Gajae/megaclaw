# -*- coding: utf-8 -*-
"""🔴 **층 채택 규칙** — 959 가 네 번째 조건 ㉣ 을 넣는다.

**왜.** 958 의 산출물이 `"🔴🔴 채택(㉠㉡㉢)": true` 를 찍었고 **원장에도 그대로 들어갔다**.
그런데 같은 산출물의 다른 칸이 *「도메인 지시자를 넣으면 그 위에서 층 ③ 은 **해롭다**(−0.0075 ·
「다 — 뺀다」)」* 를 이미 재 놓았다. 🔴 **즉 「채택한다」와 「빼야 한다」가 한 파일 안에 같이 있었고,
「빼야 한다」는 산문에만 있었다**(티처 #97 F3).

**뿌리는 규칙이다.** ㉠(합산 Δρ > T) · ㉡(부 표적 부호 유지) · ㉢(순열 null 밖) 셋은
**「이 층이 정보를 더하는가」**만 본다. **「더 싼 것으로 같은 정보를 얻을 수 있는가」를 원리상 안 본다.**
그래서 **대리변수를 층으로 채택하는 것을 막을 수 없다**.

    ㉣ **더 싼 대체물 검사** — 층을 대신할 후보(예: 도메인 지시자 9열)를 넣었을 때
       ㉮ 그 대체물이 **혼자서 든다**(Δρ_대체 > T_대체) **그리고**
       ㉯ 그 **위에서** 이 층의 Δρ 가 **T 를 못 넘거나 음수다**
       → 🔴 **㉠㉡㉢ 을 다 통과해도 채택하지 않는다.**

🔴 **조항 62**: 이 파일이 있다고 값이 옳아지지 않는다. **부르는 쪽이 이 함수의 답을 키로 내야** 한다.
"""
from __future__ import annotations


def adopt(sum_pass: bool, sub_sign_pass: bool, perm_pass: bool,
          alt_delta: float | None = None, alt_T: float | None = None,
          layer_on_alt_delta: float | None = None,
          layer_on_alt_T: float | None = None) -> dict:
    """네 조건을 다 보고 **하나의 불리언**을 낸다.

    대체물 정보가 **없으면** ㉣ 은 「모른다」다 — 🔴 **「통과」가 아니다**(조항 59).
    모르면 채택을 **보류**한다.
    """
    three = bool(sum_pass and sub_sign_pass and perm_pass)
    if alt_delta is None or alt_T is None or layer_on_alt_delta is None:
        return {
            "㉠ 합산 Δρ > T": bool(sum_pass),
            "㉡ 부 표적 부호 유지": bool(sub_sign_pass),
            "㉢ 순열 null 밖": bool(perm_pass),
            "🔴 ㉣ 더 싼 대체물": "모른다 — 안 쟀다",
            "🔴 ㉠㉡㉢ 만으로는": three,
            "🔴🔴 채택(㉠㉡㉢㉣)": False,
            "왜": "㉣ 을 안 쟀다. 「모른다」는 「통과」가 아니다(조항 59) — 채택을 보류한다",
        }
    alt_stands = bool(alt_delta > alt_T)
    lt = layer_on_alt_T if layer_on_alt_T is not None else 0.0
    layer_dies = bool(layer_on_alt_delta <= lt)
    cheaper = bool(alt_stands and layer_dies)
    return {
        "㉠ 합산 Δρ > T": bool(sum_pass),
        "㉡ 부 표적 부호 유지": bool(sub_sign_pass),
        "㉢ 순열 null 밖": bool(perm_pass),
        "㉣ 대체물이 혼자 드나": alt_stands,
        "㉣ 그 위에서 이 층이 죽나": layer_dies,
        "🔴 ㉣ 더 싼 대체물이 있나": cheaper,
        "🔴 ㉠㉡㉢ 만으로는": three,
        "🔴🔴 채택(㉠㉡㉢㉣)": bool(three and not cheaper),
        "왜": ("더 싼 대체물이 같은 정보를 주고 그 위에서 이 층이 해롭다 — 채택하지 않는다"
              if cheaper else
              ("네 조건을 다 통과했다" if three else "㉠㉡㉢ 중 하나가 불통과다")),
    }


def rulers(sum_delta: float, sum_T: float,
           sub_delta: float, sub_T: float,
           perm_obs: float, perm_p95: float,
           card_T: float) -> dict:
    """🔴 **자들이 서로 독립된 증거인가** — 962 가 다시 썼다.

    **왜 다시 썼나.** 961 이 만든 판은 문턱만 견줬다::

        def implies(a_thr, b_thr): return a_thr >= b_thr
        ... implies(sum_T, 0.0)          # ← 「㉡ ⊂ ㉠」

    ㉡ 의 실효 문턱을 **하드코딩 0.0** 으로 두었으므로 이것은 ``sum_T >= 0`` 과 같다 —
    🔴 **어떤 자료에서도 참인 항진명제**이고, 🔴 **함수가 관측 ``sub_delta`` 를 아예 안 읽는다.**
    티처 #100 이 ``sub_delta = -0.9``(부호 완전 반전)를 심었는데 ``True`` 가 그대로 나왔다.

    **두 번째 병.** 세 자는 **같은 양을 안 잰다** — ㉠ 은 층 ③ 의 Δρ, ㉡ 은 **다른 표적**
    ``y_수준`` 의 Δρ, ㉢ 의 관측은 **씨앗 하나**인데 ㉠ 은 씨앗 평균이다.
    🔴 **분모가 다른 세 수의 문턱을 한 줄에 이었다**(조항 60).

    **그래서 무엇으로 바꿨나.** 문턱 대신 **관측된 통과/불통과**를 낸다. 그리고
    🔴 **「한 점으로는 포함관계를 판정할 수 없다」를 산출물에 명시로 적는다** — 한 점에서
    두 자가 같은 답을 낸 것은 **포함관계가 아니라 일치**다. 낼 수 있는 것은
    **「이 점에서 ㉠ 통과가 ㉡ 통과를 함의했는가」**라는 **반례로 깨질 수 있는** 문장뿐이다.

    🔴 **조항 62**: 부르는 쪽이 이 함수의 답을 **키로** 내야 한다.
    """
    a_pass = bool(sum_delta > sum_T)
    b_pass = bool(sub_delta > 0.0)          # 🔴 관측을 실제로 읽는다
    c_pass = bool(perm_obs > perm_p95)      # 🔴 관측을 실제로 읽는다

    def holds(x: bool, y: bool) -> bool:
        """이 **한 점**에서 `x 통과 ⟹ y 통과` 가 성립했는가. 반례가 있으면 False."""
        return (not x) or y

    b_ind = a_pass != b_pass
    c_ind = a_pass != c_pass
    return {
        "🔴 무엇": ("자마다 **관측된 통과/불통과**를 낸다. 🔴 **문턱만 견주지 않는다** — "
                 "961 판은 관측을 안 읽어 항진명제였다(티처 #100 치-1)"),
        "자별 관측": {
            "㉠ 합산": {"자": "Δρ > T", "관측": sum_delta, "문턱": sum_T, "통과": a_pass},
            "㉡ 부 표적": {"자": "부호가 안 뒤집혔나", "관측": sub_delta, "문턱": 0.0,
                       "통과": b_pass, "곁 · 그 표적의 T": sub_T,
                       "🔴 분모 경고": "이것은 **다른 표적** `y_수준` 의 Δρ 다 — ㉠ 과 한 문장에 잇지 마라(조항 60)"},
            "㉢ 순열 null": {"자": "관측 > 상위 5%", "관측": perm_obs, "문턱": perm_p95,
                          "통과": c_pass,
                          "🔴 분모 경고": "이 관측은 **씨앗 하나**다 — ㉠ 의 씨앗 평균과 다른 수다(조항 60)"},
        },
        "㉠ 통과": a_pass,
        "㉡ 통과(관측을 실제로 읽었다)": b_pass,
        "㉢ 통과(관측을 실제로 읽었다)": c_pass,
        "🔴 ㉡ ⊂ ㉠ (관측 기준)": holds(a_pass, b_pass),
        "🔴 ㉢ ⊂ ㉠ (관측 기준)": holds(a_pass, c_pass),
        "🔴 ㉢ 의 문턱이 사실상 0 인가": bool(abs(perm_p95) < card_T),
        "🔴 ㉢ 문턱 / 카드 문턱": float(perm_p95 / card_T) if card_T else None,
        "🔴 독립된 자의 수(관측 기준)": 1 + int(b_ind) + int(c_ind),
        "🔴🔴 한 점으로는 포함관계를 판정할 수 없다": (
            "이 키들은 **이 한 점에서의 함의**다. 한 점에서 두 자가 같은 답을 낸 것은 "
            "**포함관계가 아니라 일치**다. 「독립된 자의 수」를 **자의 성질**로 읽지 마라 — "
            "🔴 그렇게 읽은 문장이 논문 504 claims[7] 이었고 962 가 철회했다(원장 1016)"),
        "🔴 무엇이면 이 답이 바뀌나": (
            "㉡ 은 `sub_delta` 의 부호가, ㉢ 은 `perm_obs > perm_p95` 가 바뀌면 바뀐다. "
            "🔴 **961 판은 둘 다 안 읽어서 아무것도 이 답을 못 바꿨다**"),
    }
