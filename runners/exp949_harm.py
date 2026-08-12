# -*- coding: utf-8 -*-
"""노트 949 [탐색] — 「원리상 못 고친다」로 덮여 있던 자리들의 **실해**를 전수로 잰다.

🔴 **탐색 레인이다**(`docs/루프.md` 규칙 1·2): 여기서 나온 수는 **이 사이클의 결론에
안 들어간다.** 원장 표제·커밋 제목·PR 제목에도 안 들어간다. 다음 사이클의 후보일 뿐이다.

무엇: 948 은 날 것 자리의 `실해` 를 `_run_both` 로 쟀는데 재현 대상 판정이
``body[0] in ("ls-files","ls-tree","status","grep")`` 이었다. argv 의 첫 낱말이
옵션(`-c` 따위)이거나 하위명령이 `log`·`show`·`diff` 면 **무조건 「못 돌렸다」**가 났다.
`wide=True` 는 **읽힌 하위명령**으로 판정하고 `log`·`show`·`diff` 계열을 넣는다.

쓰기::

    python3 -m runners.exp949_harm
"""
import datetime as dt
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import gitcall as gc            # noqa: E402

OUT = ROOT / "runners/exp949_harm.json"


def main() -> None:
    if OUT.exists():                     # 🔴 옛 산출물을 새 결과로 읽는 사고가 두 번 있었다
        OUT.unlink()
    t0 = time.time()
    cen = gc.census(harm=False)
    raw = cen["🔴 날 것 전량(목록)"]
    rows = {}
    for s in raw:
        vec = s["인자"]
        rows[s["파일:줄"]] = {
            "인자(자 A 가 본 argv 상수)": vec,
            "⚠ 실제 argv 가 아니다": ("동적 값(`str(ROOT)`·변수)은 자 A 가 못 본다 "
                              "--- 티처 #88 M6 이 지목한 칸이다"),
            "948 의 좁은 자": gc._run_both(vec, ROOT),
            "🔴 949 의 넓은 자(읽힌 하위명령 + log·show·diff)":
                gc._run_both(vec, ROOT, wide=True),
        }
    def _kind(r, key):
        v = r[key]
        return ("못 돌렸다" if "🔴 못 돌렸다" in v else
                "분모 0" if v.get("날 것이 낸 수") == 0 and v.get("정본이 낸 수") == 0 else
                "쟀다")
    narrow = {k: _kind(v, "948 의 좁은 자") for k, v in rows.items()}
    wide = {k: _kind(v, "🔴 949 의 넓은 자(읽힌 하위명령 + log·show·diff)") for k, v in rows.items()}
    pos = {k: v["🔴 949 의 넓은 자(읽힌 하위명령 + log·show·diff)"]
           for k, v in rows.items()
           if wide[k] == "쟀다" and
           v["🔴 949 의 넓은 자(읽힌 하위명령 + log·show·diff)"]["🔴 날것 − 정본"] > 0}
    res = {
        "무엇": "[탐색] 날 것 자리의 **실해**를 넓힌 자로 전수로 잰다(티처 #88 3순위)",
        "🔴 레인": "탐색 --- 이 수는 이 사이클의 결론·원장 표제·커밋 제목에 **안 들어간다**",
        "🔴 분모(오늘 트리의 날 것 자리 수)": len(raw),
        "⚠ 분모가 15 가 아닌 이유": ("같은 커밋 계열의 [판정] 팔이 순㉯ 둘을 고쳐서 "
                          "날 것이 줄었다. **두 수를 잇지 마라** --- 이 러너의 분모는 "
                          "이 실행의 것이다(티처 #88 M2)"),
        "948 의 좁은 자로 세면": {k: sum(1 for x in narrow.values() if x == k)
                        for k in ("쟀다", "못 돌렸다", "분모 0")},
        "🔴 949 의 넓은 자로 세면": {k: sum(1 for x in wide.values() if x == k)
                           for k in ("쟀다", "못 돌렸다", "분모 0")},
        "🔴 넓은 자로 재서 **날것 − 정본 > 0** 인 자리": {k: {
            "날 것이 낸 수": v["날 것이 낸 수"], "정본이 낸 수": v["정본이 낸 수"],
            "🔴 날것 − 정본": v["🔴 날것 − 정본"],
            "예시 다섯": v["🔴 날 것에서 이름이 바뀌는 예시 다섯"]}
            for k, v in pos.items()},
        "자리별": rows,
        "🔴 못 한 것": [
            "고치기 전 트리(순㉯ 둘이 살아 있던 트리)에서는 **안 쟀다** --- 오늘 트리 하나뿐이다",
            "`인자` 칸이 실제 argv 가 아니다(동적 값이 조용히 빠진다 · 티처 #88 M6) "
            "--- **자 A 가 본 상수만** 재현했다. 실제 실행 인자는 여전히 모른다",
            "「못 돌렸다」로 남은 자리의 실해는 **여전히 「모른다」**다 --- 「무해」가 아니다",
        ],
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "초": round(time.time() - t0, 1),
        "통과": True,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("산출물: %s" % OUT)


if __name__ == "__main__":
    main()
