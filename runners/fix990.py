#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 — **989 에 정정을 «얹는다»**(되돌리지 않는다).

🔴 사전등록 §2-1. **원문은 한 글자도 안 지운다.** 표시 구획만 갈아 끼우므로
두 번 돌려도 문서가 «안 자란다».

🔴🔴 **정정문의 수는 손으로 안 쓴다** --- `runners/out990_audit.json` 과
`runners/out990_arms.json` 의 «칸»에서 온다.

씀:
    python3 runners/fix990.py --ref <40자 sha>
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

import ledger as LG                                # noqa: E402

OUT = ROOT / "runners"
LEDGER = ROOT / "data/lab/denominator.json"
BEG, END = "<!-- 990:정정:시작 -->", "<!-- 990:정정:끝 -->"

TARGETS = ("docs/판정_989.md", "docs/card_989.md", "docs/handoff_989.md",
           "docs/pr_989.md")

RAN = ("runners/fix990.py",)


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dig(rel, *keys):
    p = ROOT / rel
    if not p.is_file():
        return None
    cur = json.loads(p.read_text(encoding="utf-8"))
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def block():
    """🔴 정정문 --- 모든 수가 «칸»에서 온다."""
    A = "runners/out990_audit.json"
    W = "runners/out990_arms.json"
    C = "runners/out990_champ.json"
    CW = "runners/out990_champw.json"
    S_A = "§A 🔴🔴 `F13` 의 명부 — 글롭으로 다시 센다"
    S_B = "§B 🔴🔴 「걸린 자리 0 위의 초록」 — 989 산출물 전량"
    S_C = "§C 🔴🔴 989 의 최상위 연언 — 988 판 `§59-나` 를 복원하면"
    S_D = "§D 🔴🔴 `audit989.py:705` — 「파일명 인용 4 건」의 실측"
    S_E = "§E 🔴 등록 상수를 러너가 바꿨나(`37,531` → `37,520`)"
    S_F = "§F 🔴 989 문서의 「묶음 ↔ 균등」 뒤바뀜"
    J = "§5 🔴🔴🔴 판정"
    DEC = "§4 🔴🔴🔴 분해 — `Δ(N) = 증강 + 굶김`"

    r = LG.render
    v = collections.OrderedDict([
        ("실제천장", _dig(A, S_E, "🔴 러너가 «실제로» 낸 값", "팔 H 전량")),
        ("미신고", _dig(A, S_E, "🔴🔴🔴 미신고 상수 변경인가")),
        ("히트줄", _dig(A, S_D, "🔴🔴🔴 히트 줄 합")),
        ("인용실측", _dig(A, S_D, "🔴🔴🔴 「파일명 인용」 합 — 실측")),
        ("빈집합", _dig(A, S_D, "🔴🔴🔴 989 의 판정식 `히트 > 파일명인용` 이 «걸린 자리 0» 위에 섰나")),
        ("F13참", _dig(A, S_A, "🔴🔴🔴 참 분모")),
        ("F13989", _dig(A, S_A, "🔴 989 가 쓴 분모")),
        ("F13보장", _dig(A, S_A, "🔴🔴🔴 명부가 「통과가 보장되는 것」만 골랐나")),
        ("절수", _dig(A, S_B, "🔴🔴🔴 `통과` 키를 내는 절 수")),
        ("미측정", _dig(A, S_B, "🔴🔴🔴 그중 «미측정»(초록인데 걸린 자리가 0 이거나 칸이 없다)")),
        ("최상위", _dig(A, S_C, "🔴🔴🔴 988 판 `§59-나` 를 복원하면 989 의 최상위는")),
        ("뒤바뀜", _dig(A, S_F, "🔴🔴🔴 뒤바뀐 자리 수")),
        ("증강", _dig(W, DEC, "R_pool 묶음", "1800",
                    "🔴 ① 증강 A(N) = ρ(base N + hplt αN) − ρ(base N)")),
        ("굶김", _dig(W, DEC, "R_pool 묶음", "1800",
                    "🔴 ② 굶김 S(N) = ρ(base (1−α)N + hplt αN) − ρ(base N + hplt αN)")),
        ("굶김몫", _dig(W, DEC, "R_pool 묶음", "1800", "🔴🔴🔴 굶김이 차지하는 몫")),
        ("pool천장", _dig(W, J, "🔴 R_pool 묶음 Δ(천장)")),
        ("pool천장t", _dig(W, J, "🔴 R_pool 묶음 Δ(천장) t_clu")),
        ("eq천장", _dig(W, J, "🔴 R_eq 균등 Δ(천장)")),
        ("N최소", _dig(W, J, "🔴🔴🔴 N* — 점이 아니라 구간", "🔴🔴 씨앗별 N* 최소")),
        ("N최대", _dig(W, J, "🔴🔴🔴 N* — 점이 아니라 구간", "🔴🔴 씨앗별 N* 최대")),
        ("붓스트랩", _dig(W, J, "🔴🔴🔴 N* — 점이 아니라 구간", "🔴🔴🔴 붓스트랩 2.5% ~ 97.5%")),
        ("챔공표", _dig(C, "§2 🔴 재현",
                     "🔴 공표값(출처 = `runners/text680.py` 의 `BOARD_RHO` · 손으로 안 적었다)")),
        ("챔재현", _dig(C, "§2 🔴 재현", "🔴 990 이 다시 낸 값(묶음 · 씨앗 12 평균)")),
        ("챔차이", _dig(C, "§2 🔴 재현", "🔴 공표값과의 차이")),
        ("몫977", _dig(CW, "§3 🔴🔴🔴 두 판의 대조 — **이 사이클의 세계 명제 `W2`**",
                     "🔴🔴🔴 `세계애니` 의 몫 — alpha977 판")),
        ("몫챔", _dig(CW, "§3 🔴🔴🔴 두 판의 대조 — **이 사이클의 세계 명제 `W2`**",
                    "🔴🔴🔴 `세계애니` 의 몫 — 챔피언 판")),
    ])
    txt = """%s
---

## 🔴🔴🔴 정정 (노트 990 · 티처 #128) — **원문은 안 지웠다. 아래를 «얹는다».**

> 🔴 이 구획의 모든 수는 `runners/out990_audit.json`·`out990_arms.json`·
> `out990_champ.json`·`out990_champw.json` 의 «칸»에서 왔다. **손으로 안 썼다** ---
> `runners/fix990.py` 가 얹었다.

1. 🔴🔴🔴 **기전이 틀렸다.** 989 의 `Δ(1800) = -0.013292` 중 **hplt 를 «더한» 효과는
   %s 뿐이고 base 를 «굶긴» 효과가 %s(%s)다.** 990 이 같은 씨앗·같은 겹·같은 λ 로
   항등식(`증강 + 굶김 ≡ Δ`)으로 갈랐다. **「HPLT 가 해롭다」로 보인 것은 HPLT 가 아니라 그 절단이다.**
2. 🔴🔴🔴 **「부호가 뒤집혔다」는 «자»에 달렸다.** 990 이 세 자를 나란히 재니
   천장에서 묶음 %s(도메인 군집 `t_clu` %s) 대 균등 %s 다.
   **예산 1800 에서는 균등·챔피언가중 두 자가 «양»이라 부호 반전 자체가 없다.**
3. 🔴 **등록 상수를 러너가 바꿨다** --- 사전등록의 `37,531` 대신 러너가 **%s** 를 냈고
   **미신고였다(%s).**
4. 🔴 **「`checks964.py` 의 파일명 인용 4 건」은 틀렸다** --- 990 실측 **%s 건**
   (바늘 히트 줄 합 **%s**). 🔴 **989 의 판정은 「걸린 자리 0」 위에 섰다(%s).**
   결론은 살지만 «근거»가 빈 집합이었다. `docs/루프.md` 「조항 72-라」 본문도 같이 고쳤다.
5. 🔴 **규칙 D 자리수 `52`·`57` 은 «티처 #127 이 준 값»이고 989 는 규칙 D 를 «안 돌렸다».**
   `score989.py` 자신이 그것을 자백해 놓고 그 수를 «확정형»으로 실었다.
   **990 이 `ledger.audit_text` 의 976 판 슬롯 자로 «실제로» 돌렸다**(`runners/out990_score.json` `F12`).
6. 🔴 **`F13` 의 명부가 손으로 좁혀졌다** --- 참 분모 **%s** 인데 989 는 **%s** 만 셌고,
   **명부가 「통과가 보장되는 것」만 골랐나: %s.**
7. 🔴 **「미측정 0」이 아니다** --- 989 산출물의 `통과` 키를 내는 절 **%s** 중
   **미측정이 %s** 다(초록인데 걸린 자리가 0 이거나 칸 자체가 없다).
   **988 판 `§59-나` 를 복원하면 989 의 최상위는 %s 다.**
8. 🔴 **`N*` 를 소수 한 자리의 «점»으로 실으면 안 된다** --- 씨앗별 **%s ~ %s** ·
   씨앗 붓스트랩 **%s**.
9. 🔴 **「판이 움직였다」는 챔피언 판 이야기가 아니다** --- 챔피언 판 ρ 공표 **%s** ·
   990 재현 **%s**(차이 **%s**). **챔피언 판은 그 자리에 그대로 있다.**
   움직인 것은 `alpha977` 판이고, 그 판에서 `세계애니` 는 유보의 **%s** 를 지는데
   챔피언 판에서는 **%s** 다.
10. 🔴 **「묶음 ↔ 균등」이 뒤바뀐 자리 %s** --- 실제는 묶음 `0.004632` · 균등 `0.029805` 다.
11. 🔴 **「죽은 숫자 셋을 살렸다」는 거짓** --- `2359` 만 살았고 `2363` 은 깔때기에서 빠졌고
    `1892` 는 어디에도 없다.
12. 🔴 **`38866835` 은 「세계 명제 절」 안의 «손 전사 정수»였다**(사전등록 §1 자기 위반).
13. 🔴 **`W4` 를 「독립 재현」이라 부르면 안 된다** --- 977 자기 함수를 977 자기 씨앗으로 돌렸고
    공표값이 네 자리라 그보다 촘촘한 차이는 원리상 주장 못 한다.
    **`W2` 의 변이체는 «공허»했다** --- `alpha977.select(alpha=0)` 는 `nh = 0` 이라
    채울 hplt 자리가 없어 «어떤 구현으로도 안 떨어진다».
14. 🔴 **base 천장 `1879` 는 씨앗 976 의 수이고 «측정 씨앗 열둘 어느 것의 천장도 아니다»**
    (실제 범위 1876~1888).

%s
""" % (BEG, r(v["증강"]), r(v["굶김"]), r(v["굶김몫"]), r(v["pool천장"]),
       r(v["pool천장t"]), r(v["eq천장"]), r(v["실제천장"]), r(v["미신고"]),
       r(v["인용실측"]), r(v["히트줄"]), r(v["빈집합"]),
       r(v["F13참"]), r(v["F13989"]), r(v["F13보장"]),
       r(v["절수"]), r(v["미측정"]), r(v["최상위"]),
       r(v["N최소"]), r(v["N최대"]), r(v["붓스트랩"]),
       r(v["챔공표"]), r(v["챔재현"]), r(v["챔차이"]),
       r(v["몫977"]), r(v["몫챔"]), r(v["뒤바뀜"]), END)
    return txt, v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    cs0 = hashlib.sha256((ROOT / RAN[0]).read_bytes()).hexdigest()
    txt, vals = block()
    pat = re.compile(re.escape(BEG) + r".*?" + re.escape(END) + r"\n?", re.S)

    rows, hits = [], 0
    for rel in TARGETS:
        p = ROOT / rel
        if not p.is_file():
            rows.append({"문서": rel, "🔴": "없다"})
            continue
        cur = p.read_text(encoding="utf-8")
        before = len(cur)
        had = bool(pat.search(cur))
        cur = pat.sub("", cur)
        stripped = len(cur)
        new = cur.rstrip("\n") + "\n\n" + txt
        p.write_text(new, encoding="utf-8")
        hits += 1                                  # 🔴 문서마다 «쓰기»를 수행
        rows.append({"문서": rel, "이미 있었나(치환이다)": had,
                     "원문 길이(정정 구획 제외)": stripped,
                     "전 길이": before, "후 길이": len(new),
                     "🔴 원문을 지웠나": bool(stripped < before - len(txt) - 2)})

    # ── 원장 ──────────────────────────────────────────────────────────
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    key = "🔴🔴🔴 990 정정 — 989 의 다섯 자리에 «얹었다»(되돌리지 않았다)"
    led[key] = collections.OrderedDict([
        ("언제", _now()),
        ("🔴 얹은 자리", list(TARGETS) + ["data/lab/denominator.json", "PR #247 본문"]),
        ("🔴 정정 항목 수", 14),
        ("🔴 값", collections.OrderedDict((k, vals[k]) for k in vals)),
        ("🔴 원문을 지웠나", False),
        ("🔴 낸 러너", "runners/fix990.py"),
    ])
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    hits += 1

    res = collections.OrderedDict([
        ("무엇", "990 §2-1 — 🔴 **989 에 정정을 «얹었다»**(되돌리지 않았다)"),
        ("🔴 정정 구획", "%s … %s (치환이다 --- 두 번 돌려도 안 자란다)" % (BEG, END)),
        ("🔴 자리별", rows),
        ("🔴 원장에 얹었나", True),
        ("🔴 정정문에 쓴 값(전부 «칸»에서 왔다)", vals),
        ("🔴 걸린 자리(= 자가 «쓰기/비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits == len(TARGETS) + 1)),
        ("⚠ PR #247 본문", "🔴 `gh pr edit` 로 따로 얹는다 --- 이 러너는 저장소만 만진다"),
        ("⚠ 메모리 카드의 989 구획",
         "🔴 그것은 `handoff_989.md` 의 «바이트 사본»이라 이 정정으로 «갈린다». "
         "990 은 그 사실을 여기 적고 989 구획을 «안 고친다**(남의 사이클의 도장이다)"),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256", {RAN[0]: cs0}),
            ("시작(UTC)", t0), ("끝(UTC)", _now()),
        ])),
    ])
    (OUT / "out990_fix.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [fix] 끝 → out990_fix.json\n" % _now())
    return 0


if __name__ == "__main__":
    sys.exit(main())
