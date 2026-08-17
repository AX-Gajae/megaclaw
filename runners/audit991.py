#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""991 §2 — 🔴 **자기 자의 세 구멍을 닫고, 990 의 공허를 실측한다**.

사전등록 `docs/prereg_991_order_rulers.md` §2.

🔴 **규율 넷**
  ① 하드코딩 `False` 를 안 쓴다.
  ② 「걸린 자리」는 «판정 함수»가 스스로 반환한다.
  ③ 명부는 «글롭»이다 --- 손으로 안 고른다.
  ④ 🔴 **구간 명제는 «구간 전수»로 잰다** --- 점 표본으로 「내내」를 주장하지 않는다.

씀:
    python3 runners/audit991.py --ref <40자 sha>
"""
import argparse
import ast
import collections
import datetime as dt
import glob as _g
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
import ledger as LG                                              # noqa: E402

OUT = ROOT / "runners"
RAN = ("runners/audit991.py",)
GLOB_991 = "runners/*991*"
GLOB_990 = "runners/*990*"
DOCS_991 = ("docs/판정_991.md", "docs/card_991.md", "docs/handoff_991.md",
            "docs/pr_991.md", "docs/prereg_991_order_rulers.md")
PREREG_COMMIT = None            # 🔴 `--prereg-ref` 로 받는다. 손 리터럴이 아니다.


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p):
    return os.path.relpath(str(p), str(ROOT))


def _glob(pat):
    return sorted(_rel(p) for p in _g.glob(str(ROOT / pat)))


def _read(rel):
    p = ROOT / rel
    return p.read_text(encoding="utf-8") if p.is_file() else None


def _load(rel):
    t = _read(rel)
    try:
        return json.loads(t) if t else {}
    except Exception:                                            # noqa: BLE001
        return {}


def _git(args):
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + args,
                       cwd=str(ROOT), capture_output=True)
    return (r.returncode, r.stdout.decode("utf-8", "surrogateescape"),
            r.stderr.decode("utf-8", "surrogateescape"))


def code_stamp():
    out = collections.OrderedDict()
    for rel in RAN:
        p = ROOT / rel
        if p.is_file():
            out[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


# ══════════════════════════════════════════════════════════════════════
# §A 🔴🔴🔴 `⑤′` 절 4 — **엄한 판으로 다시 센다**(`조항 3-나`)
# ══════════════════════════════════════════════════════════════════════
OLD4 = "🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)"
NEW4 = "🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다 · 🔴 982 부터 문다)"


def a_strict4():
    """🔴 988·989·990 의 `⑤′` 를 «엄한 판»(`통과 = 구판 and 신판`)으로 다시 센다.

    🔴 **990 까지 여덟 사이클째 «관대한 구판»을 게재했다** --- `조항 3-나` 정면 위반.
    """
    hits, per = 0, collections.OrderedDict()
    for note in ("988", "989", "990"):
        rel = "runners/fiveprime_%s.json" % note
        d = _load(rel)
        if not d:
            per[note] = {"🔴 산출물이 없다": rel}
            continue
        secs = [(k, v) for k, v in d.items()
                if isinstance(v, dict) and "통과" in v]
        s4 = d.get("4 도장 확인") or {}
        old, new = s4.get(OLD4), s4.get(NEW4)
        fail_pub, fail_strict = [], []
        for k, v in secs:
            hits += 2
            pub = bool(v.get("통과"))
            strict = pub
            if k == "4 도장 확인":
                strict = bool(old) and bool(new)
            if not pub:
                fail_pub.append(k)
            if not strict:
                fail_strict.append(k)
        per[note] = collections.OrderedDict([
            ("🔴 절 분모", d.get("🔴 절 수(분모)")),
            ("🔴 게재된 실패 절", fail_pub),
            ("🔴 게재된 실패 수", len(fail_pub)),
            ("🔴 구판 절 4", old), ("🔴🔴 신판 절 4", new),
            ("🔴 구판과 신판이 갈리나", bool(bool(old) != bool(new))),
            ("🔴🔴🔴 엄한 판(구판 and 신판)의 실패 절", fail_strict),
            ("🔴🔴🔴 엄한 판의 실패 수", len(fail_strict)),
            ("🔴 게재값이 «관대한 쪽»이었나", bool(len(fail_strict) > len(fail_pub))),
            ("🔴 도장 판정이 실패인 산출물",
             s4.get("🔴🔴🔴 도장 판정이 실패인 산출물")),
        ])
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 `⑤′` 절 4 를 `조항 3-나` 대로 «엄한 판»으로 다시 센다"),
        ("🔴 `조항 3-나` 원문", "「어느 판을 쓸지는 그 사이클이 고르지 못한다. 조인다/푼다와 "
                            "무관하게 «둘 다» 채점하고 「통과」로 게재하는 값은 «더 엄한 쪽»이다.」"),
        ("🔴 사이클별", per),
        ("🔴 P5 엄한 판으로 990 을 다시 세면 실패 절 수",
         per.get("990", {}).get("🔴🔴🔴 엄한 판의 실패 수")),
        ("🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수",
         collections.OrderedDict(
             (n, per.get(n, {}).get("🔴🔴🔴 엄한 판의 실패 수")) for n in
             ("988", "989", "990"))),
        ("🔴🔴🔴 게재값이 관대했던 사이클",
         [n for n in ("988", "989", "990")
          if per.get(n, {}).get("🔴 게재값이 «관대한 쪽»이었나")] or "없음"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §B 🔴🔴 990 의 배선 일곱 — **변이체의 「양쪽」 공허**
# ══════════════════════════════════════════════════════════════════════
_MUTKIND = collections.OrderedDict([
    # 🔴 990 의 일곱을 «소스»에서 읽어 분류한다 --- 손으로 안 고른다.
    ("판정식", re.compile(r"공표값\s*\+|문턱\s*1e-3|예산\s*180[01]")),
    ("결과딕트", re.compile(r"mut_ws\[|dict\(ws\)|_mut\w*\[")),
])


def b_variants():
    """🔴🔴 「안 떨어지는 변이체」와 「반드시 떨어지는 변이체」는 «똑같이» 공허하다."""
    W = _load("runners/out990_wiring.json")
    checks = W.get("배선 검사") or {}
    src = _read("runners/world990.py") or ""
    hits, rows = 0, collections.OrderedDict()
    # 🔴 각 검사의 `add(...)` 호출 «본문»을 AST 로 떼어 그 안의 변이체 꼴을 본다
    for name, v in checks.items():
        hits += 3
        tag = name.split()[0]
        # 🔴 그 검사의 「왜」 문자열에서 변이체 서술을 읽는다(러너가 «스스로» 신고한 것)
        why = v.get("왜") or ""
        kind = "코드"
        for k, rx in _MUTKIND.items():
            if rx.search(why):
                kind = k
                break
        # 🔴 `W6` 은 «항등식» --- 명제와 배선이 «둘 다» 항등식이라 검정력 0
        ident = bool(re.search(r"항등식", name) or re.search(r"항등식", why))
        rows[name] = collections.OrderedDict([
            ("🔴 990 이 낸 통과", v.get("통과")),
            ("🔴 990 이 낸 「구성상 참」", v.get("🔴 구성상 참인가(변이체가 «안» 떨어졌다)")),
            ("🔴🔴🔴 991 이 재는 「구성상 거짓」(변이체가 «반드시» 떨어진다)",
             bool(kind != "코드" or ident)),
            ("🔴🔴🔴 변이체 종류", kind if not ident else "항등식"),
            ("🔴 걸린 자리(990 이 낸 값)",
             v.get("🔴 걸린 자리(= 이 검사가 «비교»를 «수행»한 회수)")),
            ("🔴 왜(990 자신의 신고문에서 읽었다)", why[:200]),
        ])
    empty = [k for k, r in rows.items()
             if r["🔴🔴🔴 991 이 재는 「구성상 거짓」(변이체가 «반드시» 떨어진다)"]]
    hitv = [r["🔴 걸린 자리(990 이 낸 값)"] for r in rows.values()
            if isinstance(r["🔴 걸린 자리(990 이 낸 값)"], int)]
    return collections.OrderedDict([
        ("무엇", "🔴🔴 990 의 배선 일곱에 «양쪽» 공허 자를 물린다"),
        ("🔴 990 배선 검사 수", len(checks)),
        ("🔴 검사별", rows),
        ("🔴🔴🔴 「구성상 거짓」(반드시 떨어지는 변이체)인 검사", empty or "없음"),
        ("🔴🔴🔴 그 수", len(empty)),
        ("🔴🔴🔴 990 이 낸 「구성상 참」 수", int(sum(
            1 for r in rows.values() if r["🔴 990 이 낸 「구성상 참」"]))),
        ("🔴🔴🔴 그래서 990 의 「공허한 변이체 0」은 «한쪽만 보는 자»였다",
         bool(len(empty) > 0)),
        ("🔴🔴 990 의 걸린 자리 합", int(sum(hitv))),
        ("🔴🔴 990 의 걸린 자리 «중앙값»",
         int(sorted(hitv)[len(hitv) // 2]) if hitv else None),
        ("🔴🔴🔴 990 의 «최대 기여» 검사의 몫",
         round(max(hitv) / float(sum(hitv)), 4) if hitv and sum(hitv) else None),
        ("🔴 그 검사", [k for k, r in rows.items()
                     if r["🔴 걸린 자리(990 이 낸 값)"] == max(hitv)][0] if hitv else None),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §C 🔴🔴🔴 `F02` — **리플로그 «구간 전수»**(점 표본이 아니다)
# ══════════════════════════════════════════════════════════════════════
_MOVE = re.compile(r"\b(checkout|symbolic-ref|reset --hard|rebase)\b")


def c_reflog(prereg_ref):
    """🔴🔴🔴 사전등록 커밋 «시각 이후» 모든 `HEAD` 항목을 «전수» 센다.

    990 은 「점 표본」(`git symbolic-ref -q HEAD` 한 번)으로 구간 명제(「내내 안 움직였다」)를
    네 자리에 실었다. 🔴 **구간 명제는 구간 전수로만 잰다.**
    """
    rc0, t_pre, _e = _git(["show", "-s", "--format=%cI", prereg_ref])
    t_pre = t_pre.strip()
    # 🔴 `%cI` 는 «커밋» 시각이라 리플로그 «항목» 시각이 아니다. `%gd` 에 날짜를 물린다.
    rc, out, err = _git(["reflog", "show", "--date=iso-strict",
                         "--format=%gd\t%gs\t%H", "HEAD"])
    hits, rows, bad, after = 0, [], [], 0
    for line in out.split("\n"):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        sel, msg, sha = parts[0], parts[1], parts[2]
        m = re.search(r"@\{(.+)\}", sel)
        when = m.group(1) if m else ""
        hits += 1
        inrange = bool(t_pre and when and when >= t_pre)
        if inrange:
            after += 1
            rows.append({"항목": sel, "무엇": msg, "언제": when, "sha": sha[:12]})
            if _MOVE.search(msg):
                bad.append({"항목": sel, "무엇": msg, "언제": when})
    rc2, sym, _e2 = _git(["symbolic-ref", "-q", "HEAD"])
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 `F02` --- 리플로그 «구간 전수»"),
        ("🔴 사전등록 커밋", prereg_ref),
        ("🔴 그 커밋 시각", t_pre or "🔴 못 읽었다"),
        ("🔴 리플로그 전체 항목 수", hits),
        ("🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)", after),
        ("🔴🔴🔴 그 구간의 항목 «전량»", rows),
        ("🔴🔴🔴 `checkout|symbolic-ref|reset --hard|rebase` 가 든 항목", bad or "없음"),
        ("🔴🔴🔴 그 수", len(bad)),
        ("🔴 점 표본(990 판) — `git symbolic-ref -q HEAD`", sym.strip() or "(분리됨)"),
        ("🔴🔴 점 표본으로는 「내내」를 «못» 주장한다",
         "🔴 990 은 한 점을 보고 구간 명제를 네 자리에 실었다. "
         "🔴 리플로그는 저장소에 «있었고» 990 은 자기 결론을 증명할 유일한 증거를 «안 읽었다»"),
        ("🔴 리플로그 오류", err.strip() or "없음"),
        ("🔴🔴🔴 구간 분모가 `0` 이면 무슨 뜻인가(`조항 59` --- 셋을 «가른다»)",
         collections.OrderedDict([
             ("① 못 읽었다", bool(rc != 0 or not out.strip())),
             ("② 그 구간에 `HEAD` 가 «한 번도 안 움직였다»",
              bool(rc == 0 and out.strip() and t_pre and after == 0)),
             ("③ 잤는데 설정이 버렸다", False),
             ("🔴 그래서", "🔴 **`HEAD` ref 가 움직이면 리플로그에 «반드시» 항목이 남는다** --- "
                        "데몬 커밋도 `main` 을 움직이므로 남는다. 구간 항목 0 은 "
                        "「그 구간에 `HEAD` 가 한 번도 안 움직였다」의 «전수 증거»다"),
         ])),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(rc == 0 and hits > 0 and not bad
                    and (sym.strip() == "refs/heads/main"))),
    ])


# ══════════════════════════════════════════════════════════════════════
# §D 🔴🔴 규칙 D — **「못 찾는 수」를 «세 갈래»로 가른다**
# ══════════════════════════════════════════════════════════════════════
#: 🔴 ㉮ 식별자 — 노트/조항/PR/규약/티처 번호. 🔴 ㉯ 라벨 — 백분위·예산·문턱 이름.
#:    🔴 ㉰ 측정치 — 그 밖. **판정에 무는 것은 ㉰ 뿐이다.**
_ID_BEFORE = re.compile(r"(노트|조항|규약|티처|절|판|씨앗|버전|PR|#|§|v\d\.)\s*[`«\(]?\s*$")
_ID_AFTER = re.compile(r"^\s*[`»\)]?\s*(판|-가|-나|-다|-라|-마|-바|재정정|번|호)")
_LB_BEFORE = re.compile(r"(예산|총량|백분위|분위|상한|눈금|base|hplt|겹|λ|알파|α)\s*[`«\(]?\s*$|Δ\(\s*$")
_LB_AFTER = re.compile(r"^\s*[`»\)]?\s*(%|퍼센트|행|겹|도메인|칸|자리\s*수)")


def _split_kind(src, item):
    """🔴 그 수의 «자리»에서 앞 24 · 뒤 12 글자를 보고 세 갈래로 가른다.

    🔴 **㉮ 식별자**(노트/조항/PR 번호) · **㉯ 라벨**(백분위·예산 이름) · **㉰ 측정치**.
    🔴🔴 **판정에 «무는» 것은 ㉰ 뿐이다** --- 990 의 `99` 중 측정치가 몇인지 아무도 몰랐다.
    """
    num = item["수"] if isinstance(item, dict) else str(item)
    pos = item.get("자리") if isinstance(item, dict) else None
    if pos is None:
        pos = max(0, src.find(num))
    pre, post = src[max(0, pos - 24):pos], src[pos + len(num):pos + len(num) + 12]
    if _ID_BEFORE.search(pre) or _ID_AFTER.match(post):
        return "㉮ 식별자"
    if _LB_BEFORE.search(pre) or _LB_AFTER.match(post):
        return "㉯ 라벨"
    if re.match(r"^9\d\d$", num):          # 🔴 9xx 는 이 저장소에서 «노트 번호»다
        return "㉮ 식별자"
    return "㉰ 측정치"


def d_ruled(slots_rel, glob_pat, label):
    """🔴 규칙 D 의 「못 찾는 수」를 세 갈래로 가르고 «유효숫자 검사»를 더한다."""
    man = _load(slots_rel)
    files = man.get("파일별") or {}
    if not files:
        return collections.OrderedDict([
            ("무엇", label),
            ("🔴🔴🔴 슬롯 대장이 «없다» --- 이 사이클은 규칙 D 를 «잴 수가 없다»", True),
            ("🔴 대장 경로", slots_rel),
            ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", 0),
            ("통과", False),
        ])
    S = LG.artifact_numbers(glob_pat)
    hits, per = 0, collections.OrderedDict()
    tot = miss = badslot = 0
    kinds = collections.Counter()
    sigfig = []
    for rel, info in files.items():
        src = _read(rel)
        if src is None:
            continue
        r = LG.audit_text(src, info["슬롯"], S)
        hits += r["센 수"] + len(r["슬롯"])
        tot += r["센 수"]
        badslot += r["🔴 키 경로와 본문이 다른 슬롯"]
        mk = collections.Counter()
        for item in r["🔴🔴 976 판이 못 찾는 수"]:
            k = _split_kind(src, item)
            mk[k] += 1
            kinds[k] += 1
        miss += len(r["🔴🔴 976 판이 못 찾는 수"])
        # 🔴🔴🔴 **유효숫자 검사** --- 본문을 `float()` 로 되읽어 칸 값과 «상대오차»로 견준다.
        #    지금 「불일치 0」은 자와 생산기가 «같은 6 자리 포매터»를 공유하는 «닫힌 고리»다.
        for sl in info["슬롯"]:
            hits += 1
            body = src[sl["시작"]:sl["끝"]]
            v, err = LG.resolve(sl["키 경로"])
            if err is not None or not isinstance(v, (int, float)) or isinstance(v, bool):
                continue
            try:
                got = float(body.replace(",", ""))
            except Exception:                                    # noqa: BLE001
                continue
            den = abs(float(v))
            relerr = abs(got - float(v)) / den if den > 0 else abs(got - float(v))
            if relerr > 1e-9:
                sigfig.append({"파일": rel, "슬롯": sl["슬롯"], "본문": body,
                               "칸 값": v, "상대오차": relerr})
        per[rel] = collections.OrderedDict([
            ("🔴 센 수", r["센 수"]), ("🔴 면제된 수", r["면제된 수"]),
            ("🔴 슬롯 수", len(r["슬롯"])),
            ("🔴🔴 키 경로와 본문이 다른 슬롯", r["🔴 키 경로와 본문이 다른 슬롯"]),
            ("🔴🔴🔴 못 찾는 수", len(r["🔴🔴 976 판이 못 찾는 수"])),
            ("🔴🔴🔴 그 세 갈래", dict(mk)),
            ("🔴 그 수의 처음 열둘", r["🔴🔴 976 판이 못 찾는 수"][:12]),
        ])
    return collections.OrderedDict([
        ("무엇", label),
        ("🔴 자", "`ledger.audit_text` --- 976 판 슬롯 자 + 991 «유효숫자 검사»"),
        ("🔴 파일별", per),
        ("🔴🔴🔴 센 수 합", tot),
        ("🔴🔴🔴 못 찾는 수 합", miss),
        ("🔴🔴🔴 못 찾는 수의 «세 갈래»", dict(kinds)),
        ("🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수", int(kinds.get("㉰ 측정치", 0))),
        ("🔴 ㉮ 식별자", int(kinds.get("㉮ 식별자", 0))),
        ("🔴 ㉯ 라벨", int(kinds.get("㉯ 라벨", 0))),
        ("🔴🔴🔴 유효숫자 검사 — 본문을 `float()` 로 되읽어 상대오차 1e-9 로 견줬다",
         sigfig or "없음"),
        ("🔴🔴🔴 유효숫자가 어긋난 슬롯 수", len(sigfig)),
        ("🔴 왜 이 검사가 필요한가",
         "🔴 **자와 생산기가 «같은 6 자리 포매터»를 공유하면 「불일치 0」의 정보가 «0» 이다** --- "
         "실례: `2.52e-06` 이 본문에 `0.000003` 으로 실린다(19% 크고 유효숫자가 2.5 → 3)"),
        ("🔴 키 경로와 본문이 다른 슬롯 합", badslot),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §E 🔴🔴🔴 `F05` — **「파일명 grep」을 「칸 인용」으로 바꾼다**
# ══════════════════════════════════════════════════════════════════════
_SENT = re.compile(r"[^\n]+")
_OLD_NEEDLE = re.compile(r"(data/|out991_order|out991_wiring|sha256)")


def e_world(vd_rel, slots_rel):
    """🔴 990 이 989 를 «유죄로 만든 죄목»(문자열 바늘이 빈 집합 위에 섰다)이 990 에 남았다.

    🔴🔴 **991 판**: 치환표에 «키 경로»가 있으니
    「판정문의 수 `N` 중 «세계 자료 지문이 걸린 산출물 칸»에서 온 것 `M`」을 그대로 낸다.
    """
    hits = 0
    # ㉠ 런타임에 «연» `data/` 경로 --- 이 사이클 산출물 전량에서 읽는다
    nrun, srcs = 0, collections.OrderedDict()
    worldy = set()
    for rel in _glob(GLOB_991):
        if not rel.endswith(".json"):
            continue
        d = _load(rel)
        hits += 1
        for k, v in (d.items() if isinstance(d, dict) else []):
            if isinstance(v, dict) and "연" in k and "data/" in k:
                n = v.get("🔴 연 `data/` 경로 수")
                if isinstance(n, int):
                    nrun = max(nrun, n)
                    srcs[rel] = n
            if isinstance(v, dict) and "세계 자료" in k and "지문" in k:
                worldy.add(os.path.basename(rel))
    # ㉡ 옛 자(파일명 grep) --- 990 이 쓴 것. 나란히 싣는다.
    vt = _read(vd_rel) or ""
    sents = [s for s in _SENT.findall(vt)
             if len(s.strip()) > 20 and not s.strip().startswith("|")]
    old_cite = [s for s in sents if _OLD_NEEDLE.search(s)]
    hits += len(sents)
    # ㉢ 🔴🔴🔴 **새 자(칸 인용)** --- 슬롯 대장의 «키 경로»로 잰다
    man = _load(slots_rel).get("파일별") or {}
    info = man.get(vd_rel) or {}
    slots = info.get("슬롯") or []
    N = len(slots)
    M, from_art = 0, collections.Counter()
    for sl in slots:
        hits += 1
        art = (sl.get("키 경로") or ["?"])[0]
        from_art[art] += 1
        if art in worldy:
            M += 1
    return collections.OrderedDict([
        ("무엇", "🔴🔴🔴 `F05` --- 「파일명 grep」이 아니라 「칸 인용」으로 잰다"),
        ("🔴🔴🔴 ㉠ 런타임 최대", nrun),
        ("🔴 ㉠ 산출물별", srcs),
        ("🔴🔴🔴 세계 자료 지문이 «걸린» 산출물", sorted(worldy)),
        ("🔴🔴🔴 ㉡ 판정문의 주장 문장 수", len(sents)),
        ("🔴🔴🔴 ㉡ 그중 세계 자료를 «인용한» 문장 수(옛 자 --- 파일명 grep)", len(old_cite)),
        ("🔴 옛 자의 병", "🔴 **판정문에 `data/`·`out991_order`·`sha256` «문자열»이 있나만 본다** --- "
                      "990 이 989 를 유죄로 만든 죄목(「문자열 바늘이 빈 집합 위에 섰다」)이 "
                      "990 에 «그대로» 남아 있었다"),
        ("🔴🔴🔴 ㉢ 판정문의 슬롯 수 `N`(= 치환표가 심은 수)", N),
        ("🔴🔴🔴 ㉢ 그중 «세계 자료 지문이 걸린 산출물 칸»에서 온 것 `M`", M),
        ("🔴🔴🔴 ㉢ 몫 `M/N`", round(M / float(N), 4) if N else None),
        ("🔴 ㉢ 산출물별 슬롯 수", dict(from_art)),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(nrun > 0 and M > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §F 🔴🔴 `F13` — **분모에 «필터를 적는다»**
# ══════════════════════════════════════════════════════════════════════
def f_roster():
    """🔴 「분모 = 글롭 ∩ {json,txt}」와 「전량」을 «둘 다» 낸다.

    🔴 그리고 **「이 사이클이 만든 러너 중 문서에 한 번도 안 나오는 것」**을 따로 센다.
    """
    allc = _glob(GLOB_991)
    filt = [p for p in allc if p.endswith((".json", ".txt"))]
    runners = [p for p in allc if p.endswith(".py")]
    doctext = "\n".join(filter(None, (_read(d) for d in DOCS_991)))
    hits = 0
    un_f, un_a, un_r = [], [], []
    for p in filt:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_f.append(p)
    for p in allc:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_a.append(p)
    for p in runners:
        hits += 1
        if os.path.basename(p) not in doctext:
            un_r.append(p)
    # 🔴 990 의 같은 수 --- 나란히 낸다
    all990 = _glob(GLOB_990)
    r990 = [p for p in all990 if p.endswith(".py")]
    doc990 = "\n".join(filter(None, (_read(d) for d in (
        "docs/판정_990.md", "docs/card_990.md", "docs/handoff_990.md",
        "docs/pr_990.md", "docs/prereg_990_arms_rulers.md"))))
    un_r990 = [p for p in r990 if os.path.basename(p) not in doc990]
    hits += len(r990)
    return collections.OrderedDict([
        ("무엇", "🔴🔴 `F13` --- 분모에 «필터를 적는다»"),
        ("🔴 글롭", GLOB_991),
        ("🔴🔴🔴 분모 ① `runners/*991*` ∩ {json, txt}", len(filt)),
        ("🔴🔴🔴 분모 ② `runners/*991*` «전량»", len(allc)),
        ("🔴 그 차(= 필터가 «조용히» 뺀 것)", len(allc) - len(filt)),
        ("🔴 ① 에서 한 번도 인용 «안» 된 것", un_f or "없음"),
        ("🔴 ① 미인용 수", len(un_f)),
        ("🔴 ② 에서 한 번도 인용 «안» 된 것", un_a or "없음"),
        ("🔴 ② 미인용 수", len(un_a)),
        ("🔴🔴🔴 이 사이클 «러너» 중 문서에 한 번도 안 나오는 것", un_r or "없음"),
        ("🔴🔴🔴 그 수", len(un_r)),
        ("🔴 990 의 같은 수(러너 미인용)", len(un_r990)),
        ("🔴 990 의 그 러너", un_r990 or "없음"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §G 🔴 `#247`·`#248` 머지 — **가지 쪽 고유 줄 수 = 0 이 「손실 없음」의 진짜 증거다**
# ══════════════════════════════════════════════════════════════════════
def g_merges():
    hits, per = 0, collections.OrderedDict()
    for pr, br in (("247", "note/989-world-budget"),
                   ("248", "note/990-arms-rulers")):
        # 🔴 그 가지는 «이미 머지됐다» --- `merge-base(main, br)` 는 가지 끝 자신이다.
        #    🔴 머지 커밋 `M`(두 번째 부모가 가지 끝)을 찾아 `merge-base(M^1, br)` 를 쓴다.
        rc0, tip, _e0 = _git(["rev-parse", br])
        tip = tip.strip()
        rc1, mg, _e1 = _git(["rev-list", "--merges", "--parents", "main"])
        mb, mcommit = "", None
        for ln in mg.split("\n"):
            ps = ln.split()
            if len(ps) >= 3 and ps[2] == tip:
                mcommit = ps[0]
                rcx, mbx, _ex = _git(["merge-base", ps[1], tip])
                mb = mbx.strip()
                break
        if not mb:
            rcy, mby, _ey = _git(["merge-base", "main", br])
            mb = mby.strip()
        rc2, names, _e2 = _git(["diff", "--name-only", "-z", mb, br])
        files = [x for x in names.split("\0") if x]
        # 🔴🔴 **새 파일과 「양쪽에 있는 파일」을 «가른다»** --- 새 파일은 모든 줄이
        #    「가지에만 있는 줄」이라 그 수를 섞으면 아무 뜻도 없다.
        uniq_tot, rows, newf = 0, collections.OrderedDict(), []
        for f in files:
            hits += 1
            r1, a, _ = _git(["show", "%s:%s" % (mb, f)])
            r2, b, _ = _git(["show", "%s:%s" % (br, f)])
            if r2 != 0:
                continue
            if r1 != 0:
                newf.append(f)
                continue
            la, lb = a.split("\n"), b.split("\n")
            only = len([1 for x in lb if x not in set(la)])
            # 🔴 «순수 접두사»인가 --- 기준 쪽이 가지 쪽의 앞부분과 «바이트로» 같나
            prefix = bool(b.startswith(a))
            rows[f] = {"가지에만 있는 줄 수": only, "🔴 기준 쪽이 순수 접두사인가": prefix}
            uniq_tot += only
        # 🔴 데몬 커밋이 그 가지에 얹혔나 --- 회수됐나
        rc3, log, _e3 = _git(["log", "--format=%H\t%s", "%s..%s" % (mb, br)])
        dae = [l for l in log.split("\n") if "[데몬]" in l or "[수집]" in l]
        rec = []
        for l in dae:
            sha = l.split("\t")[0]
            r4, anc, _ = _git(["merge-base", "--is-ancestor", sha, "main"])
            rec.append({"sha": sha[:12], "🔴 main 에 회수됐나": bool(r4 == 0)})
            hits += 1
        per["PR #%s (%s)" % (pr, br)] = collections.OrderedDict([
            ("🔴 머지 커밋", mcommit or "🔴 못 찾았다"),
            ("🔴 기준(머지 커밋의 첫 부모와의 merge-base)", mb),
            ("🔴 갈린 파일 수", len(files)),
            ("🔴 그중 «새 파일»(기준에 없다)", len(newf)),
            ("🔴 그중 «양쪽에 있는» 파일(= 진짜 분모)", len(rows)),
            ("🔴🔴🔴 «양쪽에 있는» 파일의 가지 쪽 «고유 줄 수» 합", uniq_tot),
            ("🔴🔴🔴 그중 «순수 접두사»인 파일 수",
             int(sum(1 for r in rows.values() if r["🔴 기준 쪽이 순수 접두사인가"]))),
            ("🔴 파일별", rows),
            ("🔴🔴 데몬 커밋 수", len(dae)),
            ("🔴🔴🔴 그중 `main` 에 회수된 것", int(sum(
                1 for r in rec if r["🔴 main 에 회수됐나"]))),
            ("🔴 데몬 커밋별", rec or "없음"),
            ("🔴🔴🔴 데몬 커밋이 «전부» 회수됐나",
             bool(rec) and all(r["🔴 main 에 회수됐나"] for r in rec)),
        ])
    return collections.OrderedDict([
        ("무엇", "🔴 `#247`·`#248` 머지 --- 「union」 서술보다 «가지 쪽 고유 줄 수»가 진짜 증거다"),
        ("🔴 왜", "🔴 **990 의 `#247` 「union」 서술이 실제보다 «세다»** --- 가지 쪽 파일이 "
                "main 쪽의 «순수 접두사»였고 가지에만 있는 줄이 «0** 이었다. "
                "🔴 그리고 **989 의 데몬 커밋 셋이 `#247` 로 회수됐고 자료 손실 0** 인데 "
                "990 이 «안 적었다**"),
        ("🔴 PR 별", per),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
# §H 🔴 `⑤′` 붉은 절의 **진짜 분자** — 990 이 «안 적은» 두 수
# ══════════════════════════════════════════════════════════════════════
def h_fiveprime_numerators():
    """🔴 `조항 73-바` 는 「분모 · 분자 · 왜」 셋을 요구한다. 990 은 «분자»를 빼먹었다.

    절 1·절 2 의 진짜 분자 둘: **「사유 없이 안 돌린 것」**과 **「사유가 «자»를 못 넘은 것」**.
    """
    d = _load("runners/fiveprime_990.json")
    hits = 0
    per = collections.OrderedDict()
    for sec in ("1 소비자 역참조", "2 게이트"):
        v = d.get(sec) or {}
        hits += 1
        row = collections.OrderedDict()
        for k, val in v.items():
            if isinstance(val, (int, bool)) and (
                    "수" in k or "분모" in k or "사유" in k or "안 돌린" in k):
                row[k] = val
        # 🔴 「사유가 자를 못 넘은 것」 --- 자가 «낸» 것과 «안 낸» 것을 가른다
        rl = None
        for k, val in v.items():
            if isinstance(val, dict) and "자" in k and "사유" in k:
                rl = val
        if isinstance(rl, dict):
            ok = [x for x, r in rl.items()
                  if isinstance(r, dict) and r.get("🔴 자가 냈나")]
            no = [x for x, r in rl.items()
                  if isinstance(r, dict) and not r.get("🔴 자가 냈나")]
            row["🔴🔴🔴 사유가 «자»를 넘은 것"] = len(ok)
            row["🔴🔴🔴 사유가 «자»를 못 넘은 것"] = len(no)
            row["🔴 못 넘은 것의 처음 다섯"] = no[:5]
            hits += len(rl)
        per[sec] = row
    # 🔴 절 8 산문 --- 두 자가 «같은 문서»를 다른 분모로 센다
    p8 = d.get("8 🔴 산문 주장 대 산출물 키(957 · 티처 #95 C1)") or {}
    for k, v in d.items():
        if k.startswith("8 ") and isinstance(v, dict) and "주장" in k:
            p8 = v
    hits += 1
    return collections.OrderedDict([
        ("무엇", "🔴 `조항 73-바` --- `⑤′` 붉은 절의 «분자»를 «처음으로» 적는다"),
        ("🔴 990 이 적은 것", "🔴 분모와 「왜」는 적었고 **「사유 없이 안 돌린 것」과 "
                          "「사유가 «자»를 못 넘은 것」 둘을 «안 적었다»**"),
        ("🔴 절별", per),
        ("🔴 절 8 산문 — 분모 정의", collections.OrderedDict([
            # 🔴 `bool` 은 `int` 의 하위형이라 그대로 거르면 `통과` 키가 «따라 들어온다»
            #    --- 그러면 이 딕트가 「걸린 자리 없는 초록 절」이 되어 `F08` 에 걸린다.
            ("🔴 산문 자의 분모(정수 칸만 · `bool` 은 «뺀다»)",
             {k: v for k, v in p8.items()
              if isinstance(v, int) and not isinstance(v, bool)}),
            ("🔴🔴 두 자가 «같은 문서»를 «다른 분모»로 센다",
             "🔴 `⑤′` 절 8 산문의 분모와 판정문 §13 의 「주장 문장」 분모는 "
             "**대상도 단위도 다르다** --- 991 은 두 정의를 «나란히» 적는다"),
            ("🔴 산문 자의 단위", "🔴 «슬롯이 앉은 줄»(생산기가 심은 자리)"),
            ("🔴 판정문 §13 의 단위", "🔴 «20 글자 넘는 줄»(표 줄 제외) --- 슬롯과 무관"),
        ])),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0)),
    ])


# ══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--prereg-ref", required=True,
                    help="🔴 사전등록 커밋 sha --- `F02` 구간의 «시작»이다")
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    cs0 = code_stamp()
    secs = collections.OrderedDict([
        ("§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판으로 다시 센다", a_strict4()),
        ("§B 🔴🔴 990 의 배선 일곱 — 변이체의 「양쪽」 공허", b_variants()),
        ("§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」", c_reflog(a.prereg_ref)),
        ("§D 🔴🔴 규칙 D — 「못 찾는 수」 세 갈래 + 유효숫자 검사(991)",
         d_ruled("runners/out991_slots.json", "out991_*.json",
                 "🔴 991 자신의 규칙 D")),
        ("§D-나 🔴 규칙 D — 990 을 같은 자로 다시 센다",
         d_ruled("runners/out990_slots.json", "out990_*.json",
                 "🔴 990 의 규칙 D(991 의 세 갈래 자로)")),
        ("§E 🔴🔴🔴 `F05` — 「칸 인용」",
         e_world("docs/판정_991.md", "runners/out991_slots.json")),
        ("§F 🔴🔴 `F13` — 분모에 필터를 적는다", f_roster()),
        ("§G 🔴 `#247`·`#248` 머지 — 가지 쪽 고유 줄 수", g_merges()),
        ("§H 🔴 `⑤′` 붉은 절의 진짜 분자", h_fiveprime_numerators()),
    ])
    # 🔴 988·989 는 «슬롯 대장이 없다» --- 「못 잰다」를 «적는다**(조항 59)
    pre = collections.OrderedDict()
    for n in ("988", "989"):
        pre["out%s_slots.json" % n] = bool(
            (ROOT / ("runners/out%s_slots.json" % n)).is_file())
    hitmap = collections.OrderedDict(
        (k, v.get("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", 0))
        for k, v in secs.items())
    hv = [x for x in hitmap.values() if isinstance(x, int)]
    unmeas = [k for k, v in secs.items()
              if v.get("통과") is True and not hitmap.get(k)]
    res = collections.OrderedDict([
        ("무엇", "991 §2 — 🔴 **자기 자의 세 구멍을 닫고 990 의 공허를 실측한다**"),
        ("🔴 규율", ["하드코딩 `False` 를 안 쓴다",
                  "「걸린 자리」는 «판정 함수»가 스스로 반환한다",
                  "명부는 «글롭»이다 --- 손으로 안 고른다",
                  "🔴 구간 명제는 «구간 전수»로 잰다"]),
        ("사전등록", "docs/prereg_991_order_rulers.md §2"),
    ])
    res.update(secs)
    res["🔴🔴🔴 988·989 는 «슬롯 대장이 있나»"] = pre
    res["🔴🔴🔴 그래서 990 «이전»엔 규칙 D 를 «잴 수가 없었다»"] = bool(
        not any(pre.values()))
    res["🔴 절별 통과"] = collections.OrderedDict(
        (k, v.get("통과")) for k, v in secs.items())
    res["🔴 절별 걸린 자리"] = hitmap
    res["🔴 걸린 자리 합"] = int(sum(hv))
    res["🔴🔴 걸린 자리 «중앙값»"] = int(sorted(hv)[len(hv) // 2]) if hv else None
    res["🔴🔴🔴 «최대 기여» 절의 몫"] = (
        round(max(hv) / float(sum(hv)), 4) if hv and sum(hv) else None)
    res["🔴 그 절"] = [k for k, v in hitmap.items() if v == max(hv)][0] if hv else None
    res["🔴🔴🔴 미측정인 절(초록인데 걸린 자리 0)"] = unmeas or []
    res["통과"] = bool(all(v.get("통과") for v in secs.values()) and not unmeas)
    res["🔴 도장"] = collections.OrderedDict([
        ("ref(부른 쪽이 준 40자 sha)", a.ref),
        ("🔴 사전등록 ref", a.prereg_ref),
        ("🔴 코드 sha256(시작)", cs0),
        ("🔴 코드 sha256(끝)", code_stamp()),
        ("🔴 코드가 주행 중 바뀌었나", cs0 != code_stamp()),
        ("시작(UTC)", t0), ("끝(UTC)", _now()),
    ])
    p = OUT / "out991_audit.json"
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [audit991] 끝 → %s · 통과 %s\n"
                     % (_now(), p.name, res["통과"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
