# -*- coding: utf-8 -*-
"""노트 950 — **사전등록 채점기**(`docs/prereg_950_rulers.md` §2·§3).

🔴 **채점 규칙은 측정 전에 사전등록 §3 에 적혔다.** 이 파일은 그 규칙의 구현이다:

1. 채점은 **사전등록 본문 상수**로만 한다(아래 `PRED` 가 그 상수다)
2. 값은 **산출물 키에서 읽어** 견준다(손 전사 0)
3. 🔴 **「맞았다 / 빗맞혔다 / 못 쟀다」 셋**(조항 59). 키가 없으면 **「못 쟀다」**이고
   **절대 「맞았다」로 안 센다**
4. 범위 예측은 **그 부등식으로만** 채점한다
5. 분모는 **13** --- 다르면 이 채점기가 실패한다
6. 🔴 **엄한 쪽으로 채점한다** --- 두 읽기가 가능하면 빗맞힌 쪽으로 적고 둘 다 싣는다

돌리기::

    python3 -m runners.out950_score
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out950_score.json"
R = "runners/out950_rulers.json"
F = "runners/out950_fiveprime.json"
D = "runners/out950_docstamp.json"
E = "runners/exp950_onehop.json"

MISSING = object()


def J(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def dig(obj, *keys):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return MISSING
        cur = cur[k]
    return cur


#: 🔴 **분모 13** --- 사전등록 §2 의 행 수와 같아야 한다.
PRED_N = 13


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    r, f, d, e = J(R), J(F), J(D), J(E)
    rows = {}

    def put(name, pred, got, ok, note=""):
        rows[name] = {"예측(사전등록 본문 그대로)": pred, "실측": got,
                      "🔴 맞았나": (None if got is MISSING or ok is None else bool(ok)),
                      **({"⚠": note} if note else {})}

    # ── P1 56 의 분해 ──────────────────────────────────────────────────────
    want1 = {"소비자아님": 28, "기록기": 13, "동결산출물+재실행무해": 6,
             "동결산출물": 2, "모듈": 1, "🔴 자가 없다": 6}
    got = dig(r, "1 56 가르기", "자별 분해")
    g1 = ({k: v["수"] for k, v in got.items()} if got is not MISSING else MISSING)
    put("P1 56 의 분해 = 28·13·6·2·1·6",
        want1, g1, (g1 == want1) if g1 is not MISSING else None)

    # ── P2 기록기 참 11 · 거짓 2 ──────────────────────────────────────────
    a = dig(r, "2 자 `기록기`", "🔴 자가 참을 낸 것")
    b = dig(r, "2 자 `기록기`", "🔴 자가 **거짓**을 낸 것")
    put("P2 `기록기` 참 11 · 거짓 2", {"참": 11, "거짓": 2}, {"참": a, "거짓": b},
        (a == 11 and b == 2) if MISSING not in (a, b) else None)

    # ── P3 동결산출물 6/6 참 ───────────────────────────────────────────────
    n = dig(r, "3 자 `동결산출물`", "🔴 분모")
    t = dig(r, "3 자 `동결산출물`", "🔴 자가 참을 낸 것")
    put("P3 `동결산출물` **6/6** 참", {"분모": 6, "참": 6}, {"분모": n, "참": t},
        (n == 6 and t == 6) if MISSING not in (n, t) else None,
        "🔴 **엄한 쪽으로 채점한다**(§3-6): 거짓이 0 인 것과 **분모가 6 인 것**은 다른 주장이다")

    # ── P4 재실행무해 ≥4 초록 ─────────────────────────────────────────────
    s = dig(r, "4 자 `재실행무해`", "🔴 절 판정이 같은 것")
    put("P4 `재실행무해` 6 중 절 판정이 같은 것 **≥ 4**", "≥ 4", s,
        (s >= 4) if s is not MISSING else None)

    # ── P5 ⑤′ §2 자가 없는 사유 ≤ 3 ───────────────────────────────────────
    k2 = dig(f, "2 게이트", "🔴 사유의 자(949 · 티처 #88 ㄷ)", "🔴 자가 없는 사유 수")
    put("P5 ⑤′ §2 「자가 없는 사유」 37 → **≤ 3**", "≤ 3 (949 는 37 · 티처 예측 9)", k2,
        (k2 <= 3) if k2 is not MISSING else None,
        "🔴 **분모가 949 와 다르다**(base 가 달라 소비자 집합이 다르다 · 조항 60) --- 두 수를 잇지 마라. "
        "그리고 이 수에는 🔴 **이 사이클이 새로 만든 경로 둘**(`out949_stamp.py`·`out950_score.py`)이 "
        "들어 있다. **뺀 값이 아니라 넣은 값으로 채점한다**(엄한 쪽 · §3-6)")

    # ── P6 ⑤′ §1 자가 없는 사유 ≤ 3 ───────────────────────────────────────
    k1 = dig(f, "1 소비자 역참조", "🔴 사유의 자(949 · 티처 #88 ㄷ)", "🔴 자가 없는 사유 수")
    put("P6 ⑤′ §1 「자가 없는 사유」 28 → **≤ 3**", "≤ 3 (949 는 28)", k1,
        (k1 <= 3) if k1 is not MISSING else None,
        "🔴 **분모가 949 와 다르다**(43 → 오늘의 분모 · 조항 60). 이 수에도 "
        "**이 사이클이 새로 만든 경로 둘**이 들어 있다 --- **빼지 않고 채점한다**")

    # ── P7 ⑤′ 절 2 통과 False ─────────────────────────────────────────────
    p2 = dig(f, "2 게이트", "통과")
    put("P7 ⑤′ 절 2 의 `통과` 는 **여전히 False**", False, p2,
        (p2 is False) if p2 is not MISSING else None)

    # ── P8 ⑤′ 실패한 절 ≥ 4 ───────────────────────────────────────────────
    fl = dig(f, "🔴 실패한 절")
    nf = (len(fl) if isinstance(fl, list) else (0 if fl == "없음" else MISSING))
    put("P8 ⑤′ **실패한 절 ≥ 4**", "≥ 4 (949 는 5)", {"수": nf, "목록": fl},
        (nf >= 4) if nf is not MISSING else None)

    # ── P9 M1 diff 1 줄 ───────────────────────────────────────────────────
    m1 = dig(d, "🔴 M1 diff --- 커밋된 판 대 다시 찍은 판", "🔴 바뀐 줄 수")
    m1b = dig(d, "🔴 M1 diff --- 커밋된 판 대 다시 찍은 판", "🔴 바뀐 원본 줄 수(`-` 쪽)")
    put("P9 M1 --- 다시 찍으면 **바뀌는 줄 1**(2 이상이면 빗맞혔다)", 1,
        {"🔴 바뀐 줄 수(±)": m1, "바뀐 원본 줄 수(- 쪽)": m1b},
        (m1 == 1) if m1 is not MISSING else None,
        "🔴 **엄한 쪽으로 채점한다**(§3-6). 내가 산출물에 낸 자는 `±` 를 둘로 세는 통합 diff 다 "
        "--- 원본 줄로 세면 1 이라 「맞았다」가 되지만, **사전등록이 가리킨 키로는 2** 다. "
        "🔴 **자를 애매하게 정의한 것은 내 잘못이다**")

    # ── P10 7 문서 대조 초록 ──────────────────────────────────────────────
    dc = dig(f, "7 🔴 문서 대조(950 · 티처 #89 M1)", "통과")
    put("P10 새 절 `7 문서 대조` 는 **오늘 초록**", True, dc,
        (dc is True) if dc is not MISSING else None)

    # ── P11 M3 재현 ───────────────────────────────────────────────────────
    m3 = {"§1": dig(r, "6 M3 분모와 겹침", "🔴 §1 의 수 / 분모"),
          "§2": dig(r, "6 M3 분모와 겹침", "🔴 §2 의 수 / 분모"),
          "교집합": dig(r, "6 M3 분모와 겹침", "🔴 교집합"),
          "합집합": dig(r, "6 M3 분모와 겹침", "🔴 합집합(= 서로 다른 파일 수)")}
    want3 = {"§1": "28 / 43", "§2": "37 / 45", "교집합": 9, "합집합": 56}
    put("P11 M3 --- 28/43 · 37/45 · 교집합 9 · 합집합 56 이 **재현된다**", want3, m3,
        (m3 == want3) if MISSING not in m3.values() else None)

    # ── P12 탐색 --- 한 홉 ────────────────────────────────────────────────
    hit = dig(e, "ㄱ 한 홉 변수", "🔴 티처 #89 C2 의 자리가 들어오나")
    cnt = dig(e, "ㄱ 한 홉 변수", "🔴 새로 들어오는 자리 수")
    put("P12 [탐색] 한 홉까지 넓히면 `out946_recount.py` 의 그 자리가 **들어온다** · 새 자리 ≥ 1",
        {"들어오나": True, "새 자리": "≥ 1"}, {"들어오나": hit, "새 자리": cnt},
        (hit is True and isinstance(cnt, int) and cnt >= 1)
        if MISSING not in (hit, cnt) else None,
        "🔴 이 수는 **결론에 안 들어간다**(레인 규칙 1). 채점에만 쓴다")

    # ── P13 dead_numbers ──────────────────────────────────────────────────
    dn = dig(f, "2 게이트", "돌린 게이트의 절별 판정", "죽은 숫자")
    put("P13 `dead_numbers()` **통과 True** 유지", True, dn,
        (dn is True) if dn is not MISSING else None)

    hit_n = sum(1 for v in rows.values() if v["🔴 맞았나"] is True)
    miss_n = sum(1 for v in rows.values() if v["🔴 맞았나"] is False)
    none_n = sum(1 for v in rows.values() if v["🔴 맞았나"] is None)
    res = {
        "무엇": "🔴 사전등록 950 채점 --- 규칙은 `docs/prereg_950_rulers.md` §3 에 **측정 전**에 적혔다",
        "🔴 분모": len(rows),
        "🔴 맞았다": hit_n,
        "🔴 빗맞혔다": miss_n,
        "🔴 못 쟀다(「빗맞혔다」가 아니다 · 조항 59)": none_n,
        "🔴 빗맞힌 것": sorted(k for k, v in rows.items() if v["🔴 맞았나"] is False),
        "예측별": rows,
        "⚠ 이 수를 성적으로 읽지 마라": (
            "사전등록 §4 「나는 이미 읽었다」 --- P1·P5(부분)·P9·P11 은 **티처 #89 가 이미 준 답**이다. "
            "🔴 **눈 감고 한 예측은 8/13 뿐이다**"),
        "🔴 분모가 사전등록과 같은가": len(rows) == PRED_N,
        "통과": len(rows) == PRED_N and none_n == 0,
        "🔴 통과의 뜻": ("🔴 **성적이 아니다.** 「예측 13 을 전부 **쟀다**」는 뜻이다 --- "
                   "빗맞힌 것은 빗맞힌 채로 싣는다"),
        "시각(UTC)": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("맞았다 %d · 빗맞혔다 %d · 못 쟀다 %d → %s"
          % (hit_n, miss_n, none_n, OUT))


if __name__ == "__main__":
    main()
