# -*- coding: utf-8 -*-
"""팔 939-ㄱ — **관문 신고(규약 48 재개정판)** 와 **배선 분류(값으로)** 의 자.

사전등록: `docs/prereg_939_threshold.md` (2026-08-11 KST · 스탬프 `runners/out939_prereg_stamp.json`).

🔴 이 모듈이 지키는 것
  · `state/gap925.py:gate_report` 를 **한 줄도 안 고친다**. 그 함수의 필드 이름
    (`🔴 검정력 0 인가`)은 규약 48 재개정판이 **거짓이라 판정한 딱지**지만, 이름을 고치면
    그것을 읽는 933·935·937 러너가 재실행 때 깨진다 → **새 함수를 여기 둔다**(사전등록 §B-2).
  · 관문 신고에서 **「통과」·「검정력 0」은 금지어**다 — 함수가 자기 출력에서 **직접 검사한다**.
  · 배선 분류는 **이름이나 접두어가 아니라 값**으로 한다(티처 #78 C4 · m4).
"""
from __future__ import annotations

import math

FORBIDDEN = ("통과", "검정력 0")


# ══════════════════════════════════════════════ 이항 상한 (근사 없음)
def _log_binom_cdf(k: int, n: int, p: float) -> float:
    """log P(X ≤ k) — 곱을 로그로 쌓는다(scipy 없이)."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return -math.inf if k < n else 0.0
    terms = []
    for i in range(0, k + 1):
        lc = (math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1))
        terms.append(lc + i * math.log(p) + (n - i) * math.log1p(-p))
    m = max(terms)
    return m + math.log(sum(math.exp(t - m) for t in terms))


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """🔴 Clopper–Pearson **정확** 95% 상한 — `P(X ≤ k; n, u) = 1 − conf` 를 푼다.

    k=0 이면 닫힌 꼴 `1 − (1−conf)^(1/n)` 과 같다(러너가 대조한다).
    """
    if k >= n:
        return 1.0
    alpha = 1.0 - conf
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if math.exp(_log_binom_cdf(k, n, mid)) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def cp_lower(k: int, n: int, conf: float = 0.95) -> float:
    """대칭 상한의 짝 — `P(X ≥ k; n, l) = 1 − conf`."""
    if k <= 0:
        return 0.0
    alpha = 1.0 - conf
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        # P(X ≥ k) = 1 − P(X ≤ k−1)
        if 1.0 - math.exp(_log_binom_cdf(k - 1, n, mid)) < alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ══════════════════════════════════════════════ 관문 신고 (규약 48 재개정판)
def gate_report_939(name: str, *, axis: str, threshold: float, values,
                    note: str = "") -> dict:
    """🔴 **「이 B뽑기에서 k번 걸렸다 · 뽑기당 초과확률 95% 상한 u · 관측 최댓값 ÷ 문턱 = r」**.

    `values` = 뽑기별 관문 축 값(부호 있어도 된다 — 절댓값으로 잰다).
    🔴 「통과」·「검정력 0」은 **안 쓴다**(출력에서 직접 검사한다).
    """
    v = [abs(float(x)) for x in values]
    B = len(v)
    if B == 0:
        raise ValueError("뽑기가 0개다")
    k = sum(1 for x in v if x >= threshold)
    mx = max(v)
    out = {
        "관문": name, "축": axis, "문턱": float(threshold),
        "🔴 뽑기 수 B": B,
        "🔴 걸린 뽑기 k": k,
        "🔴 뽑기당 초과확률 95% 상한 u(Clopper–Pearson · 근사 없음)": cp_upper(k, B),
        "뽑기당 초과확률 95% 하한": cp_lower(k, B),
        "🔴 관측 최댓값 ÷ 문턱 = r": mx / threshold if threshold else float("inf"),
        "관측 최댓값": mx,
        "관측 최솟값": min(v),
        "🔴 이 B뽑기에서 한 번이라도 걸릴 확률의 95% 상한":
            1.0 - (1.0 - cp_upper(k, B)) ** B,
        "🔴 「원리상 못 걸린다」라고 쓸 수 있나":
            "🔴 안 된다 — 받침이 문턱 아래로 유계임을 보인 적이 없다",
        "비고": note,
    }
    blob = " ".join([str(a) + " " + str(b) for a, b in out.items()])
    bad = [w for w in FORBIDDEN if w in blob]
    out["🔴 금지어 자가검사(「통과」·「검정력 0」)"] = "없다" if not bad else bad
    return out


# ══════════════════════════════════════════════ 배선 분류 — 🔴 값으로 한다
#: 값이 아닌 서술 필드 — 짝 찾기에서 뺀다
_SKIP_KEYS = ("심은 결함", "심었나", "씨앗", "비고", "종류")
_NO_MARKS = ("안 심", "안 함")
_YES_MARKS = ("심은", "심음", "강제")


def _is_value(v) -> bool:
    return isinstance(v, (int, float, bool, dict, list))


def _norm(name: str) -> str:
    """부정어를 떼어 짝의 이름을 맞춘다 — 🔴 **짝 찾기에만** 쓴다(분류는 값이 한다)."""
    return (name.replace("안 심은", "심은").replace("안 심음", "심음")
                .replace("안 함", "").replace(" ", ""))


def _same(a, b) -> bool:
    """비트로 같은가 — dict 는 공통 키의 잎만 본다."""
    if isinstance(a, dict) and isinstance(b, dict):
        common = [k for k in a if k in b]
        if not common:
            return False
        return all(_same(a[k], b[k]) for k in common)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(_same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        try:
            return repr(float(a)) == repr(float(b))
        except (TypeError, ValueError):
            return a == b
    return a == b


def find_pairs(w: dict) -> list:
    """검사 dict 안에서 **(주입 없음, 주입 있음)** 값 짝을 찾는다."""
    no, yes = [], []
    for k, v in w.items():
        if any(s in k for s in _SKIP_KEYS) or k.startswith("🔴 발화") or not _is_value(v):
            continue
        if any(m in k for m in _NO_MARKS):
            no.append(k)
        elif any(m in k for m in _YES_MARKS):
            yes.append(k)
    pairs, how = [], None
    used = set()
    for a in no:                                    # ① 이름 정규화로 맞춘다
        for b in yes:
            if b in used:
                continue
            if _norm(a) == _norm(b):
                pairs.append((a, b))
                used.add(b)
                how = "이름 정규화"
                break
    if not pairs and no and yes:                    # ② 못 맞추면 순서로
        for a, b in zip(no, yes):
            pairs.append((a, b))
        how = "순서"
    return [{"주입 없음": a, "주입 있음": b,
             "값 없음": w[a], "값 있음": w[b], "🔴 같은가": _same(w[a], w[b])}
            for a, b in pairs] + ([] if not pairs else [{"짝 찾기 방법": how}])


def fired_field(w: dict):
    """검사가 스스로 신고한 발화 필드 — 🔴 **접두어 `🔴 발화했나` 에 안 매인다**."""
    for k, v in w.items():
        if "발화" in k and isinstance(v, bool):
            return k, bool(v)
    return None, None


def classify_check(name: str, w: dict) -> dict:
    """🔴 사전등록 §C-1 — **이름·접두어를 안 보고 값으로** 심음/음성 대조를 가른다."""
    raw = find_pairs(w)
    pairs = [p for p in raw if "🔴 같은가" in p]
    how = next((p["짝 찾기 방법"] for p in raw if "짝 찾기 방법" in p), None)
    fk, fv = fired_field(w)
    if not pairs:
        kind, why = "음성 대조", "값 짝이 없다 — 주입 자체를 안 했다"
    elif all(p["🔴 같은가"] for p in pairs):
        kind, why = "음성 대조", "값 짝이 **전부 같다** — 항등 검사(무해한 것을 넣으면 안 움직이나)"
    else:
        kind, why = "심음", "값 짝이 다르다 — 주입이 값을 바꿨다"
    differs = bool(pairs) and not all(p["🔴 같은가"] for p in pairs)
    return {
        "검사": name, "🔴 종류": kind, "근거": why,
        "값 짝": pairs, "짝 찾기 방법": how,
        "발화 필드": fk, "발화값": fv,
        "🔴 값 짝이 다른가": differs,
        "🔴 발화 필드가 값 짝과 같은 답인가(동어반복 검사 · 사전등록 §C-2)":
            (None if fk is None or not pairs else bool(fv) == differs),
        "⚠ 옛 규칙(937 `is_planted`)은 뭐라 했나":
            bool(isinstance(w.get("심은 결함"), str)
                 and not w["심은 결함"].startswith("(대조)")),
        "⚠ `심었나` 필드": w.get("심었나"),
    }


def account_939(wires: dict, unplantable: list) -> dict:
    """🔴 분모 **세 눈금**을 전부 낸다. 정본은 ㄴ(가장 보수적).

    `unplantable` = [{"무엇": str, "갈래": "㉮"|"㉯", "증거": str|None}, ...]
    """
    cls = {k: classify_check(k, v) for k, v in wires.items()}
    planted = [k for k, c in cls.items() if c["🔴 종류"] == "심음"]
    neg = [k for k, c in cls.items() if c["🔴 종류"] == "음성 대조"]
    # 🔴 발화 = 검사가 신고한 발화 필드가 있으면 **그것**, 없으면 「값이 달라졌다」(사전등록 §C-1)
    fired = [k for k in planted
             if (cls[k]["발화값"] if cls[k]["발화값"] is not None
                 else cls[k]["🔴 값 짝이 다른가"])]
    miss = [k for k in planted if k not in fired]
    yes_could = [u for u in unplantable if u["갈래"] == "㉯"]
    n_p, n_f, n_u, n_y = len(planted), len(fired), len(unplantable), len(yes_could)
    tk = "🔴 발화 필드가 값 짝과 같은 답인가(동어반복 검사 · 사전등록 §C-2)"
    taut = [k for k in planted if cls[k][tk] is True]
    return {
        "🔴 분류 규칙": "값 짝이 없다 → 음성 대조 · 값 짝이 전부 같다 → 음성 대조(항등) · "
                  "하나라도 다르다 → 심음. 🔴 **이름도 접두어도 `심었나` 도 안 본다**",
        "검사별": cls,
        "심음": sorted(planted), "음성 대조": sorted(neg),
        "심은 수": n_p, "발화한 수": n_f, "🔴 놓친 수": n_p - n_f, "놓친 것": miss,
        "음성 대조 수": len(neg),
        "못 심은 것": unplantable,
        "못 심은 수(전량)": n_u, "그중 ㉯ 심을 수 있었는데 안 심었다": n_y,
        "🔴 눈금 ㄱ — 심은 것 기준": f"{n_f}/{n_p} = {n_f/n_p:.3f}" if n_p else "분모 0",
        "🔴🔴 눈금 ㄴ(정본) — 못 심은 것 **전량**까지 분모에":
            f"{n_f}/{n_p+n_u} = {n_f/(n_p+n_u):.3f}" if n_p + n_u else "분모 0",
        "눈금 ㄷ — ㉯ 만 분모에":
            f"{n_f}/{n_p+n_y} = {n_f/(n_p+n_y):.3f}" if n_p + n_y else "분모 0",
        "🔴 눈금 ㄱ 이 동어반복인가(사전등록 §C-2)": {
            "심음 중 발화 필드가 값 짝과 같은 답을 낸 수": len(taut),
            "심음 수": n_p,
            "🔴 뜻": ("**전부 같다 — 이 자료에서 눈금 ㄱ 은 정보를 거의 안 담는다**"
                   if n_p and len(taut) == n_p else "일부만 같다 — 눈금 ㄱ 이 독립인 자리가 있다"),
        },
    }
