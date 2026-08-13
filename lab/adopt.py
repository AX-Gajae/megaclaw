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
