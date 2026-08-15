# -*- coding: utf-8 -*-
"""노트 971 — 🔴🔴🔴 **항진명제 탐지기가 「리팩터링만으로」 만족되는가**를 심어서 잰다.

**왜 이 파일이 있나.** `dropaudit969.py` 의 `W6` 은 세 사이클(968·969·970) 연속으로
「항진명제」로 잡혔다. 971 이 그것을 고쳤고 자의 항진명제 계수가 **1 → 0** 이 됐다.
🔴 **그런데 그 0 이 「병이 나았다」는 뜻인지 「자가 못 보게 됐다」는 뜻인지 몰랐다.**

이 파일은 **같은 항진명제를 두 꼴로 심는다**:

- `t1_inline()` --- 표현식이 **함수 본문에 그대로** 있다(자유 이름 0 → 자 A 가 잡는다)
- `t2_moved()` + `call_t2()` --- **똑같이 퇴화한 값**을 **파라미터로 넘긴다**.
  🔴 **부르는 자리는 t1 과 비트로 같은 값을 준다** --- 병은 하나도 안 고쳐졌다.

그리고 음성 대조 둘:

- `n1_real()` --- 진짜 검사(양성 대조를 먹는다 → 입력이 바뀌면 값이 바뀐다)
- `n2_literal()` --- 리터럴 항진명제(자 A 가 잡아야 한다)

`meta965.py --only runners/tautprobe971.py` 로 잰다. 🔴 **이 파일은 아무것도 안 쓴다.**
"""
import hashlib

#: 🔴 t1 과 t2 가 **같은 값**을 받는다는 것을 파일 안에서 못 박는다.
SRC = "971 항진명제 탐지기 심기".encode("utf-8")


def _same_bytes():
    """🔴 **쓰기가 한 줄도 없다** --- 그래서 두 sha 는 같을 수밖에 없다."""
    before = hashlib.sha256(SRC).hexdigest()
    after = hashlib.sha256(SRC).hexdigest()
    return before, after


def t1_inline():
    """🔴 **심기 1** --- W6 의 **구판 꼴**. 표현식이 함수 본문에 그대로 있다.

    `before`·`after` 는 위에서 계산되지만 **자 B 의 슬라이스가 뿌리까지 따라간다.**
    자 A 는 「자유 이름 0」이 아니므로 못 잡고, **자 B 가 뿌리를 갈아 잡아야 한다.**
    """
    before = hashlib.sha256(SRC).hexdigest()
    after = hashlib.sha256(SRC).hexdigest()
    return {"🔴 무엇": "쓰기 없는 두 sha 를 견준다 --- 어떤 자료에서도 참이다",
            "🔴 입력별 값": {"before": before, "after": after},
            "통과": bool(before == after)}


def t2_moved(before, after):
    """🔴 **심기 2** --- **같은 항진명제를 파라미터로 옮긴 것뿐**이다.

    🔴🔴 **부르는 자리(`call_t2`)가 t1 과 비트로 같은 값을 준다 --- 병은 하나도 안 고쳐졌다.**
    자 A 는 자유 이름이 둘이라 **원리상 못 잡는다.**
    """
    return {"🔴 무엇": "t1 과 같은 식 --- 다만 인자로 받는다",
            "🔴 입력별 값": {"before": before, "after": after},
            "통과": bool(before == after)}


def call_t2():
    """🔴 **부르는 자리가 항진명제다** --- `_same_bytes()` 는 쓰기 없이 같은 sha 를 두 번 낸다."""
    b, a = _same_bytes()
    return t2_moved(b, a)


def n1_real(same, diff, n_hex):
    """🔴 **음성 대조 1 --- 진짜 검사.** 양성 대조를 먹으므로 입력이 바뀌면 값이 바뀐다."""
    return {"🔴 무엇": "같은 바이트는 같다고 하고 다른 바이트는 다르다고 하는가(양성 대조)",
            "🔴 입력별 값": {"같은 짝": same, "다른 짝": diff, "16진 길이": n_hex},
            "통과": bool(same and not diff and n_hex == 64)}


def call_n1():
    """🔴 `probe_diff` 가 **한 줄 더한 바이트**라 자가 갈릴 수 있다 --- 971 의 `w6_new` 꼴."""
    h_same = hashlib.sha256(SRC).hexdigest()
    h_diff = hashlib.sha256(SRC + "x".encode("utf-8")).hexdigest()
    return n1_real(bool(h_same == hashlib.sha256(SRC).hexdigest()),
                   bool(h_same == h_diff), len(h_same))


def n2_literal():
    """🔴 **음성 대조 2 --- 리터럴 항진명제.** 자 A 가 이것은 반드시 잡아야 한다."""
    return {"🔴 무엇": "아무 입력도 안 읽는 리터럴", "통과": True}


def report() -> dict:
    return {"t1 인라인(심기)": t1_inline(), "t2 인자로 옮김(심기)": call_t2(),
            "n1 진짜 검사(음성 대조)": call_n1(), "n2 리터럴(심기)": n2_literal()}
