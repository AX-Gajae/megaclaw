# -*- coding: utf-8 -*-
"""노트 949 의 **수를 손으로 옮기지 않는다**(티처 #88 M1).

948 은 산출물의 `A−B 161` 을 노트에 **159**(옆 칸의 `소비자 수`)로 적었다.
그래서 949 는 노트의 숫자 칸을 **이 러너가 산출물에서 읽어 찍는다.**

쓰기::

    python3 -m runners.note949_gen        # docs/판정/949.md 의 §숫자 블록을 만든다
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "docs/판정/949_수.md"


def J(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    b = J("runners/out949_stamp_before.json")
    a = J("runners/out949_stamp_after.json")
    f = J("runners/out949_fiveprime.json")
    s = J("runners/out949_score.json")
    e = J("runners/exp949_harm.json")
    r = J("runners/out949_refix.json")
    L = []
    W = L.append
    W("<!-- 🔴 이 파일은 `runners/note949_gen.py` 가 산출물에서 **읽어 찍는다**. -->")
    W("<!--    손으로 고치지 마라 --- 고칠 것이 있으면 러너를 고쳐라(티처 #88 M1). -->")
    W("")
    W("## 🔴 숫자 — 러너가 찍었다 (손 전사 없음)")
    W("")
    W("### ㄱ 대조(check) 전수 · `runners/out949_stamp_before.json` › `2 대조 전수`")
    W("")
    c = b["2 대조 전수"]
    W("| 칸 | 값 |")
    W("|---|---|")
    for k in ("훑은 `.py`(분모)", "🔴 대조 자리 수", "🔴 대조가 덮는 파일 수",
              "🔴 대상을 못 푼 자리 수(「모른다」)"):
        W("| %s | **%s** |" % (k, c[k]))
    W("| 🔴 자연 양성 대조가 잡은 자리 | `%s` |"
      % ("` · `".join(c["🔴 자연 양성 대조"]["잡은 자리"]) or "🔴 못 잡았다"))
    W("| ⚠ 이 자로 **안 센** 갈래(rev 기준 비교) | %s |"
      % c["🔴 이 자로 안 센 갈래(rev 기준 비교)"]["수"])
    p1 = b["1 자와 검정력"]["심어서 확인"]
    W("| 🔴 검정력 — 심은 양성 | **%s/%s** |"
      % (p1["🔴 양성 중 잡은 수"], p1["🔴 심은 양성(분모)"]))
    W("| 🔴 검정력 — 심은 음성 **오발** | **%s**/%s |"
      % (p1["🔴 음성 오발 수"], p1["🔴 심은 음성(분모)"]))
    W("")
    W("### ㄴ ㉮/㉯/㉲/순㉯ — 🔴 **두 실행이다. 수를 잇지 마라**(티처 #88 M2)")
    W("")
    W("| 칸 | 고치기 **전**<br>`out949_stamp_before.json` | 고친 **뒤**<br>`out949_stamp_after.json` |")
    W("|---|---|---|")
    KS = ["🔴 날 것", "🔴 ㉮ 원리상 못 고친다(대조 ≥ 1)",
          "⚠ 옛 자(도장 ≥ 1)로 세면 ㉮ 는", "🔴 ㉯ 고칠 수 있다",
          "🔴 ㉲ 규약상 안 고친다(㉯ 의 부분집합)", "🔴 순㉯ 막는 것이 아무것도 없는 것"]
    for k in KS:
        W("| %s | **%s** | **%s** |"
          % (k, b["3 ㉮/㉯/㉲/순㉯"][k], a["3 ㉮/㉯/㉲/순㉯"][k]))
    for tag, d in (("전", b), ("뒤", a)):
        pass
    W("| 분해가 닫히나(날 것+의도적+안전 == 자 A 호출 자리) | %s == %s → **%s** | %s == %s → **%s** |"
      % (b["3 ㉮/㉯/㉲/순㉯"]["🔴 분해가 닫히나"]["날 것 + 의도적 + 안전"],
         b["3 ㉮/㉯/㉲/순㉯"]["🔴 분해가 닫히나"]["자 A 호출 자리"],
         b["3 ㉮/㉯/㉲/순㉯"]["🔴 분해가 닫히나"]["🔴 같은가"],
         a["3 ㉮/㉯/㉲/순㉯"]["🔴 분해가 닫히나"]["날 것 + 의도적 + 안전"],
         a["3 ㉮/㉯/㉲/순㉯"]["🔴 분해가 닫히나"]["자 A 호출 자리"],
         a["3 ㉮/㉯/㉲/순㉯"]["🔴 분해가 닫히나"]["🔴 같은가"]))
    W("")
    W("🔴 **고친 순㉯ 둘**: %s"
      % " · ".join("`%s`" % x for x in b["3 ㉮/㉯/㉲/순㉯"]["🔴 순㉯ 목록"]))
    W("")
    W("### ㄷ `seed_pad` 가드 · `out949_stamp_before.json` › `4 ㄱ seed_pad 가드`")
    W("")
    g = b["4 ㄱ seed_pad 가드"]
    W("| 칸 | 값 |")
    W("|---|---|")
    for k in ("🔴 원소가 A−B 에 있나", "🔴 가드가 발화했나",
              "🔴 948 이 공표한 `A−B`", "🔴 대조 원소를 안 넣고 세면 `A−B`",
              "🔴 948 이 공표한 `분모 ④ 안 돌린 수`", "🔴 차"):
        W("| %s | **%s** |" % (k, g[k]))
    W("| 음성 대조(양쪽에 없는 원소로는 안 터진다) 발화 | %s |"
      % g["🔴 음성 대조(양쪽에 없는 원소로는 안 터진다)"]["발화했나"])
    W("")
    W("### ㄹ 사유의 자 · `runners/out949_fiveprime.json`")
    W("")
    W("| 절 | 자가 붙은 사유 | 🔴 자가 **없는** 사유 | 자를 통과한 사유 |")
    W("|---|---|---|---|")
    for sec in ("1 소비자 역참조", "2 게이트"):
        d = f[sec]["🔴 사유의 자(949 · 티처 #88 ㄷ)"]
        W("| %s | %s | **%s** | %s |"
          % (sec, d["🔴 자가 붙은 사유 수"], d["🔴 자가 없는 사유 수"],
             d["🔴 자를 통과한 사유 수"]))
    W("")
    W("**절 2 의 ㉡ 을 「사유가 자를 통과한 것」으로 바꾸니 `A − B` = %s** "
      "(옛 자로는 **원리상 0** 이었다)."
      % f["2 게이트"]["🔴 조항 62 ㉡ 자를 통과한 사유만 B 로(949)"]["🔴 A − B"])
    W("")
    W("### ㅁ ⑤′ 취합 검사 — **붉은 채로 싣는다**")
    W("")
    W("절 수(분모) **%s** · `통과` 키를 가진 절 **%s** · ⓪ 관문 **%s**"
      % (f["🔴 절 수(분모)"], f["🔴 `통과` 키를 가진 절"], f["⓪ 관문(작업 트리)"]["통과"]))
    W("")
    W("🔴 **실패한 절 %s**(948 은 2 였다):" % len(f["🔴 실패한 절"]))
    for x in f["🔴 실패한 절"]:
        W("* ❌ `%s`" % x)
    W("")
    W("### ㅂ 사전등록 채점 · `runners/out949_score.json`")
    W("")
    W("**분모 %s · 맞았다 %s · 🔴 빗맞혔다 %s · 못 쟀다 %s**"
      % (s["🔴 분모"], s["🔴 맞았다"], s["🔴 빗맞혔다"],
         s["🔴 못 쟀다(「빗맞혔다」가 아니다 · 조항 59)"]))
    W("")
    W("| 예측 | 맞았나 | 실측 |")
    W("|---|---|---|")
    for k, v in s["예측별"].items():
        got = v.get("실측")
        got = json.dumps(got, ensure_ascii=False) if isinstance(got, dict) else got
        W("| %s | %s | %s |"
          % (k, {True: "✅", False: "🔴 **빗맞혔다**"}.get(v.get("🔴 맞았나"), "🔴 못 쟀다"),
             str(got).replace("|", "·")[:300]))
    W("")
    W("### ㅅ 고친 두 자리가 실제로 도나 · `runners/out949_refix.json`")
    W("")
    for k, v in r["① runners/gate940_wiring.py (통째로)"]["🔴 절별 판정"].items():
        W("* `gate940_wiring.py` › %s → **%s**" % (k, v))
    W("* `ratio940_run.py` › `part0()` 이 돌았나 → **%s** · 사전등록 sha 대조 → **%s**"
      % (r["② runners/ratio940_run.py (고친 줄이 든 `part0()` 만)"].get("🔴 part0() 이 돌았나"),
         r["② runners/ratio940_run.py (고친 줄이 든 `part0()` 만)"].get("사전등록 sha256 대조")))
    W("")
    W("### ㅇ [탐색] · `runners/exp949_harm.json` — 🔴 **이 수는 결론에 안 들어간다**(규칙 1)")
    W("")
    W("분모(오늘 트리의 날 것 자리) **%s** · 좁은 자 `%s` · 넓은 자 `%s`"
      % (e["🔴 분모(오늘 트리의 날 것 자리 수)"],
         json.dumps(e["948 의 좁은 자로 세면"], ensure_ascii=False),
         json.dumps(e["🔴 949 의 넓은 자로 세면"], ensure_ascii=False)))
    W("")
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("산출물: %s" % OUT)


if __name__ == "__main__":
    main()
