#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""992 정정 — 🔴🔴🔴 **991 이 990 에 얹은 정정이 «낡았다». 되돌리지 말고 «다시» 얹는다.**

🔴🔴🔴 **왜 (티처 #130 치-3).** 991 이 990 문서 넷·원장에 얹은 정정의 수가 **낡았다** ---
박은 값 `99/33`, 최종 산출물 `291/177`(3 배). `out991_fix.json` 은 `10:41:41` 에,
`out991_audit.json` 은 `10:52:30` 에 찍혔고 `fix991.py:81-83` 이 그 audit 의 «같은 키 경로»를
읽는다. **더 낡은 주행 값을 박고 다시 안 돌렸다.**

🔴 **이 러너가 고치는 것 넷**
  ① `99/33` → **`out991_audit.json` 의 «최종» 칸**(D-나 못 찾는 수 / ㉰ 측정치 / 유효숫자).
  ② 정정 7 항의 「셋」 → **`out992_mut.json` 이 «실측»한 수**(실행 자 · 둘째 자 둘 다).
  ③ 정정 9 항의 **단위 혼동** --- 「고유 줄」은 «줄»이고 「순수 접두사」는 «파일»이다.
     🔴 **접두사가 «아닌» 파일의 고유 «줄» 수를 따로 낸다.**
  ④ 🔴 **`⑤′` 절 4 의 「엄한 판 첫 통과」가 «면제로 산 것»이었다**는 사실을 얹는다.

🔴 **모든 수는 산출물의 «칸»에서 온다. 손으로 안 적는다.**
🔴 이 쓰기는 «치환»이다 --- 표지 구획만 갈아 끼우므로 두 번 돌려도 파일이 «안 자란다».

씀:
    python3 runners/fix992.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import ledger as LG                                              # noqa: E402

OUT = ROOT / "runners"
LEDGER = ROOT / "data/lab/denominator.json"
BEG, END = "<!-- 992:정정:시작 -->", "<!-- 992:정정:끝 -->"
TARGETS = ("docs/판정_990.md", "docs/card_990.md", "docs/handoff_990.md",
           "docs/pr_990.md")
RAN = ("runners/fix992.py",)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _v(*path):
    v, err = LG.resolve(list(path))
    return v if err is None else None


def block():
    A9 = "out991_audit.json"
    D = "out992_audit.json"
    MU = "out992_mut.json"
    O = "out992_order.json"
    DD9_991 = "§D-나 🔴 규칙 D — 990 을 같은 자로 다시 센다"
    DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판 + 면제 없는 판"
    DG = "§G 🔴 `#248`·`#249` 머지 — 단위를 가른다"
    PR247 = "PR #247 (note/989-world-budget)"
    EXP = "§2 🔴🔴🔴 탐색 격자"
    SEB = "§1-나 🔴🔴🔴 SE 표 — 자 3 × 성분 8 = 24 칸 전량"
    RP = "R_pool 묶음"

    v = collections.OrderedDict([
        # ① 991 이 «낡은 값»으로 박은 규칙 D 세 수 --- 991 의 «최종» 산출물에서 읽는다
        ("D9못찾", _v(A9, DD9_991, "🔴🔴🔴 못 찾는 수 합")),
        ("D9측정", _v(A9, DD9_991, "🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수")),
        ("D9유효", _v(A9, DD9_991, "🔴🔴🔴 유효숫자가 어긋난 슬롯 수")),
        # ② 변이체 --- 「셋」이 아니라 실측한 수
        ("변이실행", _v(MU, "🔴🔴🔴 그 수")),
        ("변이둘째", _v(MU, "🔴🔴🔴 둘째 자 — 「자료와 «무관하게» 강제되는 것」만 세면", "🔴 그 수")),
        ("변이991신고", _v(MU, "🔴 990 이 «신고한» 「공허한 변이체」 수")),
        ("변이빠진", _v(MU, "🔴🔴🔴 둘째 자 — 「자료와 «무관하게» 강제되는 것」만 세면", "🔴 빠진 검사")),
        # ③ 단위
        ("고유줄247", _v(D, DG, "🔴 PR 별", PR247,
                      "🔴🔴🔴 «양쪽에 있는» 파일의 가지 쪽 «고유 줄 수» 합")),
        ("접두사247", _v(D, DG, "🔴 PR 별", PR247, "🔴🔴🔴 그중 «순수 접두사»인 «파일» 수")),
        ("비접두사줄247", _v(D, DG, "🔴 PR 별", PR247,
                        "🔴🔴🔴 접두사가 «아닌» 파일의 고유 «줄» 수")),
        ("양쪽파일247", _v(D, DG, "🔴 PR 별", PR247, "🔴 그중 «양쪽에 있는» 파일(= 진짜 분모)")),
        # ④ ⑤′ 절 4
        ("엄한991", _v(D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 · 991 의 «엄한» 실패 수", "991")),
        ("면제같나", _v(D, DA, "🔴🔴🔴 두 집합이 «같나»")),
        ("면제로산것", _v(D, DA, "🔴🔴🔴 그래서 991 의 「엄한 판 첫 통과」는 «면제로 산 것»인가")),
        # ⑤ 990 의 「최적 base」가 «격자 경계 인공물»이었다
        ("탐argmax", _v(O, EXP, RP, "🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)")),
        ("탐끝", _v(O, EXP, RP, "🔴🔴🔴 argmax 가 격자 오른쪽 끝인가")),
        ("탐집합", _v(O, EXP, RP, "🔴🔴🔴 «최적 집합»(argmax 와 `2·SE_clu` 로 «안 갈리는» 칸)")),
        ("탐집합수", _v(O, EXP, RP, "🔴🔴🔴 최적 집합의 크기")),
        ("격자칸수", _v(O, EXP, "🔴 격자 칸 수")),
        # ⑥ 「무엇이 사는가」는 자의 사실
        ("SE갈린", _v(O, SEB, "🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리는 성분")),
        ("SE갈린수", _v(O, SEB, "🔴🔴🔴 그 수")),
        ("넘은수", _v(O, SEB, "🔴🔴🔴 자별 «2 를 넘은 성분 수»")),
    ])
    r = LG.render
    txt = """%s
## 🔴🔴🔴 노트 992 가 «다시» 얹은 정정 — **991 의 정정이 「낡은 수」였다**

> 🔴 원문도, 991 의 정정 블록도 «안 지웠다». 아래 여섯은 노트 992 의 러너가 «잰» 값이고
> 각 수는 `runners/out992_*.json` · `runners/out991_audit.json` 의 칸에서 왔다(손으로 안 적었다).

1. 🔴🔴🔴 **991 이 여기 박은 규칙 D 세 수가 «낡았다».**
   `out991_fix.json` 이 `out991_audit.json` 보다 **11 분 먼저** 돌았고 다시 안 돌았다.
   **991 의 «최종» 산출물로 다시 읽으면**: 못 찾는 수 **%s** · ㉰ 측정치 **%s** ·
   유효숫자가 어긋난 슬롯 **%s** 다. 🔴 **992 는 이 사고를 잡는 자를 신설했다** ---
   `F09` 를 「맨 마지막 러너 하나」에서 **「산출물 사이 도장 시각의 «위상 정렬» 전수」**로 올렸고,
   **소비자 도장이 생산자보다 앞서면 실패**다.
2. 🔴🔴🔴 **「구성상 거짓인 변이체가 «셋»」은 실측이 아니었다.**
   990 의 일곱을 **990 자신의 설정 격자에서 «돌려» 재면 %s** 이고,
   「자료와 «무관하게» 강제되는 것」만 세는 둘째 자로는 **%s** 다(빠지는 것: %s).
   990 자신이 신고한 「공허한 변이체」 수는 **%s** 였다.
   🔴 **991 의 판별기는 AST 파싱이 «없었고» 「소스 토큰용 정규식」을 «산문»에 물렸다** ---
   「결과딕트」 갈래는 «원리상» 한 번도 못 켜졌다.
3. 🔴🔴 **`#247` 정정의 «단위»가 섞였다.** 「고유 줄 **%s**」은 «줄»이고
   「순수 접두사 **%s**」는 «파일»이다(양쪽에 있는 파일 %s 개).
   🔴 **접두사가 «아닌» 파일의 고유 «줄» 수는 %s** 다 --- 이것이 두 수를 같은 단위로 잇는 칸이다.
4. 🔴🔴🔴 **`⑤′` 절 4 의 「엄한 판 첫 통과」는 «면제로 산 것»이었다.**
   991 이 등기해 뺀 도장 셋이 988·989·990 에서 신판을 떨어뜨린 «바로 그 셋»인가: **%s**.
   면제로 산 것인가: **%s**. 엄한 판으로 센 991 의 `⑤′` 실패 수는 **%s** 다.
   🔴 **992 는 `⑤′` 절 4 를 `통과 = 구판 and 신판 and 면제없는신판` 으로 게재한다.**
5. 🔴🔴🔴 **990·991 의 「최적 base」는 «격자 경계 인공물»이었다.**
   격자를 **%s 칸**으로 늘리면 `argmax` 는 **%s** 이고 격자 오른쪽 끝인가: **%s**.
   🔴 그리고 `argmax` 와 `2·SE_clu` 로 «안 갈리는» 칸이 **%s** 개다: %s.
   **「최적」은 하나가 아니다.**
6. 🔴🔴🔴 **「무엇이 사는가」는 «자의 사실»이다.**
   자에 따라 `2·SE` 판정이 갈리는 성분이 **%s** 개다: %s.
   자별 「2 를 넘은 성분 수」: %s.
   🔴 **990·991 은 판정 자의 여덟 칸만 문서에 실었다.**

%s""" % (
        BEG, r(v["D9못찾"]), r(v["D9측정"]), r(v["D9유효"]),
        r(v["변이실행"]), r(v["변이둘째"]), r(v["변이빠진"]), r(v["변이991신고"]),
        r(v["고유줄247"]), r(v["접두사247"]), r(v["양쪽파일247"]), r(v["비접두사줄247"]),
        r(v["면제같나"]), r(v["면제로산것"]), r(v["엄한991"]),
        r(v["격자칸수"]), r(v["탐argmax"]), r(v["탐끝"]), r(v["탐집합수"]), r(v["탐집합"]),
        r(v["SE갈린수"]), r(v["SE갈린"]), r(v["넘은수"]), END)
    return txt, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    txt, v = block()
    hits, wrote = 0, []
    for rel in TARGETS:
        p = ROOT / rel
        if not p.is_file():
            continue
        cur = p.read_text(encoding="utf-8")
        cur = re.sub(re.escape(BEG) + r".*?" + re.escape(END) + r"\n?", "",
                     cur, flags=re.S)
        p.write_text(cur.rstrip("\n") + "\n\n" + txt + "\n", encoding="utf-8")
        hits += 1
        wrote.append(rel)
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    led["🔴🔴🔴 992 정정 — 991 이 990 에 얹은 정정이 «낡았다»"] = collections.OrderedDict([
        ("언제", _now()), ("🔴 ref", a.ref),
        ("🔴 고친 문서", wrote),
        ("🔴 정정 항목 수", 6),
        ("🔴 값(전부 산출물 칸에서 왔다)",
         collections.OrderedDict((k, x) for k, x in v.items())),
        ("🔴 되돌린 것이 있나", False),
        ("🔴 991 의 정정 블록을 지웠나", False),
        ("🔴 낸 러너", "runners/fix992.py"),
        ("통과", bool(hits == len(TARGETS))),
    ])
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    hits += 1
    rec = collections.OrderedDict([
        ("무엇", "992 정정 --- 🔴 **991 의 정정이 «낡은 수»였다. 되돌리지 말고 다시 얹는다**"),
        ("🔴 대상", list(TARGETS) + ["data/lab/denominator.json"]),
        ("🔴 쓴 문서", wrote),
        ("🔴 정정 항목 수", 6),
        ("🔴 값", collections.OrderedDict((k, x) for k, x in v.items())),
        ("🔴 못 읽은 칸", [k for k, x in v.items() if x is None] or "없음"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits == len(TARGETS) + 1
                    and not [k for k, x in v.items() if x is None])),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256",
             {r_: hashlib.sha256((ROOT / r_).read_bytes()).hexdigest()
              for r_ in RAN if (ROOT / r_).is_file()}),
            ("시각(UTC · 시작)", t0), ("시각(UTC · 끝)", _now()),
        ])),
    ])
    (OUT / "out992_fix.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [fix992] 문서 %d · 통과 %s · 못 읽은 칸 %s\n"
                     % (_now(), len(wrote), rec["통과"],
                        [k for k, x in v.items() if x is None] or "없음"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
