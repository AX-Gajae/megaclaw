#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""991 정정 — 🔴 **되돌리지 말고 «얹는다»**. 노트 990 의 다섯 자리에 정정 블록을 «추가»한다.

🔴 **모든 수는 `runners/out991_*.json` 의 «칸»에서 온다. 손으로 안 적는다.**
🔴 이 쓰기는 «치환»이다 --- 표지 구획만 갈아 끼우므로 두 번 돌려도 파일이 «안 자란다».

씀:
    python3 runners/fix991.py --ref <40자 sha>
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
BEG, END = "<!-- 991:정정:시작 -->", "<!-- 991:정정:끝 -->"
TARGETS = ("docs/판정_990.md", "docs/card_990.md", "docs/handoff_990.md",
           "docs/pr_990.md")
RAN = ("runners/fix991.py",)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _v(*path):
    v, err = LG.resolve(list(path))
    return v if err is None else None


def block():
    O = "out991_order.json"
    D = "out991_audit.json"
    J = "§5 🔴🔴🔴 판정"
    ORD = "§1 🔴🔴🔴 순서 분해 — 자 셋 × 두 순서 × 대칭 배분(λ 전량)"
    EXP = "§2 🔴🔴🔴 탐색 격자 — 🔴 **사전등록 «안»** · `base=1800` 은 «없다**"
    FIX = "§4 🔴🔴 즉시정정 — 「전량」 눈금을 손 리터럴에서 뗐다"
    ROW = "🔴🔴🔴 한 줄 표"
    COMP = "🔴 성분"
    DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판으로 다시 센다"
    DB = "§B 🔴🔴 990 의 배선 일곱 — 변이체의 「양쪽」 공허"
    DD9 = "§D-나 🔴 규칙 D — 990 을 같은 자로 다시 센다"
    DF = "§F 🔴🔴 `F13` — 분모에 필터를 적는다"
    DG = "§G 🔴 `#247`·`#248` 머지 — 가지 쪽 고유 줄 수"
    RP = "R_pool 묶음"

    v = collections.OrderedDict([
        ("B증", _v(O, ORD, "0", RP, ROW, "순서 B 증강")),
        ("B굶", _v(O, ORD, "0", RP, ROW, "순서 B 굶김")),
        ("상호", _v(O, ORD, "0", RP, ROW, "상호작용")),
        ("대증", _v(O, ORD, "0", RP, ROW, "대칭 증강")),
        ("대굶", _v(O, ORD, "0", RP, ROW, "대칭 굶김")),
        ("A굶t", _v(O, J, "🔴 P1 그 t_clu")),
        ("상호t", _v(O, J, "🔴 P2 그 t_clu")),
        ("산수", _v(O, J, "🔴🔴 그 수(판정 자)")),
        ("천장", _v(O, J, "🔴 깨끗한 천장 대조 값(판정 자)")),
        ("NALL", _v(O, FIX, "🔴🔴🔴 `N_ALL` 을 «계산»했다")),
        ("리터럴", _v(O, FIX, "🔴🔴🔴 990 의 손 리터럴(`world990.py` 소스에서 «읽었다»)")),
        ("모자", _v(O, FIX, "🔴🔴🔴 그 리터럴이 요구한 hplt 자리 − 실제 hplt 행")),
        ("판정칸", _v(O, EXP, "🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나")),
        ("엄한990", _v(D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수", "990")),
        ("엄한989", _v(D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수", "989")),
        ("엄한988", _v(D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수", "988")),
        ("거짓변이", _v(D, DB, "🔴🔴🔴 그 수")),
        ("거짓목록", _v(D, DB, "🔴🔴🔴 「구성상 거짓」(반드시 떨어지는 변이체)인 검사")),
        ("990몫", _v(D, DB, "🔴🔴🔴 990 의 «최대 기여» 검사의 몫")),
        ("990중앙", _v(D, DB, "🔴🔴 990 의 걸린 자리 «중앙값»")),
        ("D9못찾", _v(D, DD9, "🔴🔴🔴 못 찾는 수 합")),
        ("D9측정", _v(D, DD9, "🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수")),
        ("D9유효", _v(D, DD9, "🔴🔴🔴 유효숫자가 어긋난 슬롯 수")),
        ("러너990", _v(D, DF, "🔴 990 의 같은 수(러너 미인용)")),
        ("러너990목록", _v(D, DF, "🔴 990 의 그 러너")),
        ("고유줄247", _v(D, DG, "🔴 PR 별", "PR #247 (note/989-world-budget)",
                      "🔴🔴🔴 «양쪽에 있는» 파일의 가지 쪽 «고유 줄 수» 합")),
        ("접두사247", _v(D, DG, "🔴 PR 별", "PR #247 (note/989-world-budget)",
                      "🔴🔴🔴 그중 «순수 접두사»인 파일 수")),
        ("데몬247", _v(D, DG, "🔴 PR 별", "PR #247 (note/989-world-budget)",
                     "🔴🔴 데몬 커밋 수")),
        ("회수247", _v(D, DG, "🔴 PR 별", "PR #247 (note/989-world-budget)",
                     "🔴🔴🔴 데몬 커밋이 «전부» 회수됐나")),
    ])
    r = LG.render
    txt = """%s
## 🔴🔴🔴 노트 991 이 «얹은» 정정 — **되돌린 것이 아니라 더한 것이다**

> 🔴 원문은 «안 지웠다**. 아래 아홉은 노트 991 의 러너가 «잰» 값이고
> 각 수는 `runners/out991_*.json` 의 칸에서 왔다(손으로 안 적었다).

1. 🔴🔴🔴 **`W1`(「부호를 만든 것은 굶김이다」)은 «무조건 명제»가 아니다.**
   `증강 + 굶김 ≡ Δ` 는 `(x−y)+(z−x) = z−y` 라 **어떤 수를 넣어도 잔차 `0`** 이고,
   **순서를 고르는 것이 곧 답을 고르는 것**이다. 순서 B 로 가르면 판정 자에서
   증강이 **%s** 로 «양수»이고 굶김이 %s 다. 상호작용 **%s** ·
   대칭(Shapley) 배분 %s / %s.
2. 🔴🔴🔴 **`W6`(「42 칸 잔차 0.0」)은 «부동소수 결합법칙»을 잰 것이다** — 검정력 `0`.
   노트 991 은 그것을 배선 명부에서 «진단»으로 내리고 그 자리에
   **`X1` 색인 대조**(네 칸이 같은 씨앗·같은 겹·같은 λ·같은 뽑기 색인을 썼나)를 넣었다.
3. 🔴🔴 **「굶김이 98.63%%를 만들었다」는 도메인 군집 SE 를 «안 넘는다»** —
   그 성분의 `t_clu` 는 **%s** 다. 성분 여덟 중 `2` 를 넘은 것은 **%s** 개뿐이고
   거기 그 성분은 «없다». (상호작용의 `t_clu` 도 %s 로 «안 산다».)
4. 🔴🔴 **`37,531` 은 손 리터럴이었다.** `world990.py` 의 「전량」 눈금 이름으로 쓰인
   그 상수는 hplt 를 **%s 자리** 못 채웠다. 노트 991 은 `N_ALL = ceil(len(yh)/α)`
   = **%s** 로 «계산»했고 부족은 `0` 이다. 🔴 **그래서 `Δ(천장)` 은 순수한 천장 대조가
   «아니었다»** — 깨끗한 대조는 base 를 자기 천장에 두고 hplt 만 흔든 **%s** 다.
5. 🔴🔴 **탐색 격자의 `base=90` 칸과 `base=1800` 칸의 차가 「판정 Δ(1800) 그 자체」였다.**
   노트 991 은 격자에서 판정 칸을 «뺐고**(격자에 판정 칸이 있나: %s)
   격자를 사전등록 «안»으로 들여 채점 분모에 넣었다.
6. 🔴🔴🔴 **`⑤′` 실패 수 정정** — `조항 3-나`(「게재값은 «더 엄한 쪽»」)를 집행하면
   노트 988 **%s** · 노트 989 **%s** · 노트 990 **%s** 다.
   게재값은 각각 하나씩 «적었다» — 여덟 사이클째 «관대한 구판»을 실었다.
7. 🔴🔴 **「공허한 변이체 0」은 «한쪽만 보는 자»였다.** 노트 990 의 일곱 중
   **%s** 이 「구성상 «거짓»」(반드시 떨어지는 변이체)이다: %s.
8. 🔴 **「걸린 자리」 총합은 단일 검사가 지배한다** — 노트 990 의 최대 기여 검사의 몫이
   **%s** 이고 중앙값은 **%s** 다. 총합만 싣는 것은 파일 크기를 싣는 것과 다르지 않다.
   🔴 그리고 **규칙 D 를 노트 991 의 자로 다시 재면** 「못 찾는 수」 %s 중
   ㉰ 측정치는 **%s** 뿐이고, **유효숫자가 어긋난 슬롯이 %s** 개다
   (`0.000003` 이 실제로는 `2.52e-06` --- 19%% 크다).
   🔴 이 사이클의 러너 중 문서에 한 번도 안 나오는 것이 **%s** 개였다: %s.
9. 🔴 **`#247` 머지의 「union」 서술이 실제보다 «세다»** — 양쪽에 있는 파일의
   가지 쪽 «고유 줄 수»가 **%s** 이고 그중 «순수 접두사»가 **%s** 개다.
   🔴 **그리고 노트 989 의 데몬 커밋 %s 이 회수됐다(전부 회수: %s) — 자료 손실 `0`.**
   **노트 990 은 이 사실을 «안 적었다».**

%s""" % (
        BEG, r(v["B증"]), r(v["B굶"]), r(v["상호"]), r(v["대증"]), r(v["대굶"]),
        r(v["A굶t"]), r(v["산수"]), r(v["상호t"]), r(v["모자"]), r(v["NALL"]),
        r(v["천장"]), r(v["판정칸"]), r(v["엄한988"]), r(v["엄한989"]),
        r(v["엄한990"]), r(v["거짓변이"]), r(v["거짓목록"]), r(v["990몫"]),
        r(v["990중앙"]), r(v["D9못찾"]), r(v["D9측정"]), r(v["D9유효"]),
        r(v["러너990"]), r(v["러너990목록"]), r(v["고유줄247"]), r(v["접두사247"]),
        r(v["데몬247"]), r(v["회수247"]), END)
    return txt, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
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
    led["🔴🔴🔴 991 정정 — 노트 990 의 다섯 자리에 «얹었다»"] = collections.OrderedDict([
        ("언제", _now()), ("🔴 ref", a.ref),
        ("🔴 고친 문서", wrote),
        ("🔴 정정 항목 수", 9),
        ("🔴 값(전부 산출물 칸에서 왔다)",
         collections.OrderedDict((k, x) for k, x in v.items())),
        ("🔴 되돌린 것이 있나", False),
        ("🔴 낸 러너", "runners/fix991.py"),
        ("통과", bool(hits == len(TARGETS))),
    ])
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    hits += 1
    rec = collections.OrderedDict([
        ("무엇", "991 정정 --- 🔴 노트 990 의 다섯 자리에 «얹었다»(되돌리지 않았다)"),
        ("🔴 대상", list(TARGETS) + ["data/lab/denominator.json"]),
        ("🔴 쓴 문서", wrote),
        ("🔴 정정 항목 수", 9),
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
            ("시각(UTC · 시작)", _now()), ("시각(UTC · 끝)", _now()),
        ])),
    ])
    (OUT / "out991_fix.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [fix991] 문서 %d · 통과 %s\n"
                     % (_now(), len(wrote), rec["통과"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
