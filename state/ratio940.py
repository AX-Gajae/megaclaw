# -*- coding: utf-8 -*-
"""팔 940-ㄱ — **관문을 「문턱」에서 「민감도 비 r」로 강등한다.** 그리고 소비자 명부를 든다.

사전등록: `docs/prereg_940_ratio.md` (스탬프 `runners/out940_prereg_stamp.json`).

🔴 이 모듈이 지키는 것
  · `state/perm922.py` · `state/gap925.py` · `state/gate939.py` 를 **한 글자도 안 고친다**.
    셋 다 옛 산출물이 `코드 sha256` 으로 가리키는 증거물이다.
  · 신고에서 **`k` 를 기본에서 뺀다**. 기본은 `r` 이고, `k` 는 「이 k 로 무엇을 갈랐나」를
    같이 적을 때만 쓴다(사전등록 §1 「바꾸지 않는 것」).
  · 🔴 **`1 − (1−u)^B` 는 안 낸다** — `k=0` 이면 정의상 `≡ 0.95` 인 항등식이다(티처 #79 치명 3).
  · 결론 문장에서 **「통과」·「검정력 0」은 금지어**다 — 함수가 자기 출력에서 직접 검사한다.

용어(사전등록 §2)
    m       뽑기들의 |기후값 MAE 상대차| **최댓값**
    cr      진짜 기준 팔 MAE (일)
    L_used  max(1, 전달률 BCa 상한)   — 기준 팔 왜곡이 개선으로 새는 비율
    G       min_i(R − y_i)            — 진짜 개선과 가장 가까운 귀무 개선의 빈틈 (일)
    🔴 r    m · L_used · cr / G       — 「관문 축 최댓값이 판정을 뒤집는 크기의 몇 배인가」
"""
from __future__ import annotations

import math

#: 결론 문장에서 쓰면 안 되는 낱말 (규약 48 재개정판을 이어받는다)
FORBIDDEN = ("통과", "검정력 0")

#: 🔴 신고에서 **폐기한** 것 — 왜 폐기했는지를 코드가 들고 있는다
RETIRED = {
    "1 − (1−u)^B (「이 B뽑기에서 한 번이라도 걸릴 확률의 95% 상한」)":
        "🔴 **항등식이다.** k=0 이면 Clopper–Pearson 상한 정의상 (1−u)^B = 1−conf 이므로 "
        "1−(1−u)^B ≡ conf. B=10·50·200·1000·5000 전부 0.950000000 — 자료가 아니라 "
        "「95%를 골랐다」의 되풀이다(티처 #79 치명 3 · 러너 §E 가 다시 센다)",
    "문턱 T 를 상수 하나로 신고하기":
        "🔴 **상수가 아니다.** 팔별 0.015122/0.019429/0.077105 로 5.0989배 갈리고, "
        "L_used 의 바닥 1.0 이 세 팔 중 둘의 T 를 전적으로 정한다(티처 #79 치명 2)",
    "k 를 기본 신고로 쓰기":
        "🔴 **폐기가 아니라 강등이다.** k 는 「이 k 로 무엇을 갈랐나」를 같이 적을 때만 쓴다. "
        "아무것도 안 갈랐으면 k 는 관문이 한 일을 과장한다(939 가 그랬다)",
}


def five_number(vals) -> dict:
    """분포의 5수 요약 — 🔴 `r` 이 최댓값 하나만 보는 것의 **대체물**(사전등록 §1 잃는 것 ㄴ)."""
    v = sorted(abs(float(x)) for x in vals)
    n = len(v)
    if n == 0:
        return {"🔴 못 잰다": "뽑기가 0개다"}

    def q(p: float) -> float:
        if n == 1:
            return v[0]
        h = p * (n - 1)
        lo = int(math.floor(h))
        hi = min(lo + 1, n - 1)
        return v[lo] + (h - lo) * (v[hi] - v[lo])

    return {"최소": v[0], "1사분위": q(0.25), "중앙값": q(0.5),
            "3사분위": q(0.75), "최대": v[-1], "뽑기 수 B": n}


def sensitivity_ratio(name: str, *, rel_values, G, cr, L_used, L_bca_hi=None,
                      used_for: str, note: str = "") -> dict:
    """🔴 **규약 61 신고** — 「이 팔의 관문 축 최댓값은 판정을 뒤집는 크기의 몇 배인가 = r」.

    `used_for` 는 **필수**다. 이 관문이 무엇을 갈랐는지 — 아무것도 안 갈랐으면
    `"아무것도 안 갈랐다"` 를 그대로 적는다(939 의 병: 관문을 신고하면서 그것이 판정에
    쓰였는지를 안 적었다).

    입력이 없으면 **「못 잰다」**로 돌려준다 — 🔴 「없다」가 아니다(조항 59).
    """
    v = [abs(float(x)) for x in rel_values]
    B = len(v)
    out: dict = {
        "팔": name,
        "축": "기후값 MAE 상대차(|귀무 − 진짜| ÷ 진짜)",
        "🔴 이 r 로 무엇을 갈랐나": used_for,
        "🔴 뽑기 수 B": B,
        "상대차 분포 5수 요약": five_number(v),
    }
    if B == 0:
        out["🔴 못 잰다"] = "뽑기가 0개다"
        return _selfcheck(out)

    m = max(v)
    out["m 관측 최대 |상대차|"] = m

    missing = [k for k, x in (("G", G), ("cr", cr), ("L_used", L_used)) if x is None]
    if missing:
        out["🔴 못 잰다"] = (f"{'·'.join(missing)} 를 이 팔의 산출물에서 못 읽었다 — "
                        "🔴 **「없다」가 아니라 「못 읽었다」다**(조항 59)")
        out["비고"] = note
        return _selfcheck(out)

    G, cr, L_used = float(G), float(cr), float(L_used)
    out.update({
        "cr 진짜 기준 팔 MAE(일)": cr,
        "L_used = max(1, 전달률 BCa 상한)": L_used,
        "G 빈틈 = min(R − y_i)(일)": G,
        "🔴 왜곡(일) = m · L_used · cr": m * L_used * cr,
    })
    if G <= 0:
        out["🔴 못 잰다"] = ("G ≤ 0 — 진짜를 이긴 귀무가 있다. 비를 낼 분모가 없다"
                        f"(G = {G})")
        out["비고"] = note
        return _selfcheck(out)

    out["🔴🔴 r = m · L_used · cr / G"] = m * L_used * cr / G
    out["🔴 L_used 의 바닥(1.0)이 정했나"] = (
        None if L_bca_hi is None else bool(float(L_bca_hi) < 1.0))
    out["전달률 BCa 상한(바닥 적용 전)"] = (
        None if L_bca_hi is None else float(L_bca_hi))
    out["🔴 G 는 뽑기 수에 의존한다"] = (
        f"B 를 늘리면 G 는 **단조 비증가**이므로 r 은 **단조 비감소**다. "
        f"그러므로 이 r={m * L_used * cr / G:.6f} 은 **B={B} 을 같이 적지 않으면 뜻이 없다**")
    out["🔴 r 을 어떻게 읽나"] = (
        "r < 1 이면 이 팔의 관문 축 최댓값은 **판정을 뒤집을 크기에 못 미친다**. "
        "r ≥ 1 이면 **기준 팔 차이 하나만으로 순위가 뒤집힐 수 있다**. "
        "🔴 **r 은 이분법을 안 준다** — 어느 쪽이든 「무엇을 갈랐나」는 사람이 적는다")
    out["비고"] = note
    return _selfcheck(out)


def _selfcheck(out: dict) -> dict:
    blob = " ".join(f"{a} {b}" for a, b in out.items())
    bad = [w for w in FORBIDDEN if w in blob]
    out["🔴 금지어 자가검사(「통과」·「검정력 0」)"] = "없다" if not bad else bad
    out["🔴 폐기한 신고를 안 넣었나"] = {
        "1 − (1−u)^B 를 냈나": any("(1−u)" in k for k in out),
        "k 를 기본으로 냈나": any(k.strip().startswith("k") or "걸린 뽑기" in k for k in out),
    }
    return out


# ══════════════════════════════════════════════ 🔴 소비자 명부 (게이트가 쓴다)
#: 🔴 `state/perm922.COMPARABLE_REL` 을 **import 하는** 파일과 그 갈래.
#: 게이트(`runners/gate940_wiring.py`)가 이 명부와 저장소 실측을 대조해서,
#: **명부에 없는 새 소비자가 생기면 붉어진다.** 이것이 「배선」의 ③ 조건이다.
CONSUMERS = {
    "runners/perm922_run.py": {
        "갈래": "🔴 관문 갈래로 **분기한다**",
        "증거": "perm922_run.py 의 `if not cmp_n2[\"🔴 통과\"]:` 한 줄이 판정문을 §6-4"
              "(**판정 불능**)로 보낸다 — 저장소에서 관문이 판정을 실제로 고른 유일한 자리",
        "이 사이클이 하는 일": "🔴 **주입 시험의 대상**(사전등록 §B) — 값을 바꿔 넣고 판정문이 바뀌나",
    },
    "runners/calpanel933_run.py": {
        "갈래": "산출물에 적기만 한다(판정에 안 쓴다)",
        "증거": "`\"비교가능성 통과분만의 p(병기 · 판정에 안 쓴다)\"` — 러너가 자기 입으로 적는다",
        "이 사이클이 하는 일": "새 양식으로 다시 신고(§C) · 코드 수정 0",
    },
    "runners/rawpanel935_run.py": {
        "갈래": "산출물에 적기만 한다(판정에 안 쓴다)",
        "증거": "`\"🔴 비교가능성 통과분만의 p(병기 · 판정에 안 쓴다)\"`",
        "이 사이클이 하는 일": "새 양식으로 다시 신고(§C) · 코드 수정 0",
    },
    "runners/rawpanel935_addendum.py": {
        "갈래": "산출물에 적기만 한다(판정에 안 쓴다)",
        "증거": "935 산출물의 상대차를 읽어 `gap925.gate_report` 로 다시 신고할 뿐이다",
        "이 사이클이 하는 일": "새 양식으로 다시 신고(§C) · 코드 수정 0",
    },
}

#: 🔴 **남기기로 정한 옛 상수**와 그 이유(사전등록 §4 · 값 보기 전에 정했다)
OLD_CONSTANT = {
    "무엇": "state/perm922.py:28 `COMPARABLE_REL = 0.05`",
    "🔴 지웠나": "**안 지웠다 · 남긴다**",
    "왜 남기나": "위 네 러너가 import 한다. 지우면 **옛 산출물의 재현이 원리상 깨진다** — "
             "증거물은 「다시 돌려서 같은 수가 나오는가」로 검증되는데, 상수를 지우면 "
             "그 검증 자체가 불가능해진다",
    "🔴 왜 파일을 아예 안 여나": "`state/perm922.py` 의 sha256 이 "
                        "`runners/out939_threshold.json:코드 sha256` 과 "
                        "`runners/out939_prereg_stamp.json` 에 박혀 있다. 한 글자만 고쳐도 "
                        "939 의 「남의 파일이 안 바뀌었나」 대조가 붉어진다 — "
                        "**옛 산출물의 재현성과 새 규약을 둘 다 지키는 유일한 길은 안 여는 것**이다",
    "🔴 그래서 무엇을 잃나": "저장소에 「쓰면 안 되는 상수」가 주석 없이 계속 남는다. "
                     "다음 세션이 위에서 아래로 읽다가 만난다. "
                     "🔴 **그 손해는 게이트로만 막는다** — `runners/gate940_wiring.py` 가 "
                     "명부 밖의 새 소비자를 붉게 낸다",
}
