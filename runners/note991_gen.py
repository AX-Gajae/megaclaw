#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""991 문서 생성기 — 🔴 **문서의 모든 수는 «치환표»의 칸에서 온다. 손으로 안 쓴다.**

🔴 `SPEC` 은 **`슬롯 이름 -> [산출물, 키, …]`** 다(`조항 60-라`).
🔴 여기 «없는» 수는 문서에 «못 들어간다** --- `render()` 가 모르는 슬롯에서 «멈춘다».
🔴 각 수가 앉은 «문자 자리»를 `out991_slots.json` 에 남겨 규칙 D 의 976 판 슬롯 자가 읽는다.

씀:
    python3 runners/note991_gen.py --stage docs --ref <40자 sha>
    python3 runners/note991_gen.py --stage card --ref <40자 sha>
"""
import argparse
import collections
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
DOCS = ROOT / "docs"
CARD = Path(os.path.expanduser(
    "~/.claude/projects/-Users-ax-world-model/memory/project-lab-state.md"))

O = "out991_order.json"
G = "out991_wiring.json"
D = "out991_audit.json"
S = "out991_score.json"
L = "out991_last.json"
F = "fiveprime_991.json"

J = "§5 🔴🔴🔴 판정"
ORD = "§1 🔴🔴🔴 순서 분해 — 자 셋 × 두 순서 × 대칭 배분(λ 전량)"
EXP = "§2 🔴🔴🔴 탐색 격자 — 🔴 **사전등록 «안»** · `base=1800` 은 «없다**"
CEIL = "§3 🔴🔴 깨끗한 천장 대조 — base 천장 고정 · hplt 만 흔든다"
FIX = "§4 🔴🔴 즉시정정 — 「전량」 눈금을 손 리터럴에서 뗐다"
ROW = "🔴🔴🔴 한 줄 표"
COMP = "🔴 성분"
DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판으로 다시 센다"
DB = "§B 🔴🔴 990 의 배선 일곱 — 변이체의 「양쪽」 공허"
DC = "§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」"
DD = "§D 🔴🔴 규칙 D — 「못 찾는 수」 세 갈래 + 유효숫자 검사(991)"
DD9 = "§D-나 🔴 규칙 D — 990 을 같은 자로 다시 센다"
DE = "§E 🔴🔴🔴 `F05` — 「칸 인용」"
DF = "§F 🔴🔴 `F13` — 분모에 필터를 적는다"
DG = "§G 🔴 `#247`·`#248` 머지 — 가지 쪽 고유 줄 수"

RULERS = collections.OrderedDict([
    ("풀", "R_pool 묶음"), ("균", "R_eq 균등"), ("챔", "R_champ 챔피언가중")])
CELLS = ("Δ(1800)", "순서 A 증강", "순서 A 굶김", "순서 B 증강", "순서 B 굶김",
         "상호작용", "대칭 증강", "대칭 굶김")
CELLKEY = collections.OrderedDict([
    ("Δ", "Δ(1800)"), ("A증", "순서 A 증강"), ("A굶", "순서 A 굶김"),
    ("B증", "순서 B 증강"), ("B굶", "순서 B 굶김"), ("상호", "상호작용"),
    ("대증", "대칭 증강"), ("대굶", "대칭 굶김")])
COMPKEY = collections.OrderedDict([
    ("Δ", "Δ = H − B"), ("A증", "순서 A · 증강 A = M − B"),
    ("A굶", "순서 A · 굶김 S_A = H − M"), ("B증", "순서 B · 증강 A′ = H − S"),
    ("B굶", "순서 B · 굶김 S_B = S − B"), ("상호", "상호작용 A′ − A"),
    ("대증", "대칭 배분 · 증강 (A + A′)/2"),
    ("대굶", "대칭 배분 · 굶김 (S_A + S_B)/2")])

#: 🔴🔴🔴 **치환표 정본** --- 손 리터럴이 아니라 «생성»한다(조항 60-라).
SPEC = collections.OrderedDict()

# ── 순서 분해 한 표: 자 3 × 칸 8 = 24 + t_clu 24 ─────────────────────
for rk, rn in RULERS.items():
    for ck, cn in CELLKEY.items():
        SPEC["표.%s.%s" % (rk, ck)] = [O, ORD, "0", rn, ROW, cn]
        SPEC["t.%s.%s" % (rk, ck)] = [O, ORD, "0", rn, COMP, COMPKEY[ck],
                                      "🔴🔴🔴 t_clu"]
        SPEC["SE.%s.%s" % (rk, ck)] = [O, ORD, "0", rn, COMP, COMPKEY[ck],
                                       "🔴🔴🔴 도메인 군집 SE"]
    SPEC["몫A.%s" % rk] = [O, ORD, "0", rn, "🔴🔴🔴 순서 A 에서 «굶김»이 차지하는 몫"]
    SPEC["몫B.%s" % rk] = [O, ORD, "0", rn, "🔴🔴🔴 순서 B 에서 «굶김»이 차지하는 몫"]
    SPEC["부호A.%s" % rk] = [O, ORD, "0", rn, "🔴🔴🔴 순서 A 의 증강 부호"]
    SPEC["부호B.%s" % rk] = [O, ORD, "0", rn, "🔴🔴🔴 순서 B 의 증강 부호"]
    # 탐색 격자
    for nb in ("45", "90", "135", "270", "450"):
        SPEC["탐.%s.%s" % (rk, nb)] = [
            O, EXP, rn, "🔴 격자(총량 1800 고정 · hplt = 1800 − base)", nb]
    SPEC["탐최적.%s" % rk] = [O, EXP, rn, "🔴🔴🔴 ρ 가 «가장 높은» base 행 수"]
    SPEC["탐넘은.%s" % rk] = [O, EXP, rn, "🔴🔴🔴 그중 넘은 수"]
    SPEC["탐벼랑.%s" % rk] = [O, EXP, rn, "🔴🔴🔴 「벼랑」이라 적을 수 있나(`조항 68`)"]
    for a, b in (("45", "90"), ("90", "135")):
        SPEC["짝.%s.%s" % (rk, a)] = [O, EXP, rn,
                                      "🔴 짝 차(이웃 눈금) — 군집 SE·LODO 를 «전부» 붙였다",
                                      "%s → %s" % (a, b), "🔴🔴🔴 값"]
        SPEC["짝t.%s.%s" % (rk, a)] = [O, EXP, rn,
                                       "🔴 짝 차(이웃 눈금) — 군집 SE·LODO 를 «전부» 붙였다",
                                       "%s → %s" % (a, b), "🔴🔴🔴 t_clu"]
    SPEC["천장.%s" % rk] = [O, CEIL, "🔴 자별", rn, "🔴🔴🔴 값"]
    SPEC["천장t.%s" % rk] = [O, CEIL, "🔴 자별", rn, "🔴🔴🔴 t_clu"]

SPEC.update(collections.OrderedDict([
    ("맨위", [O, J, "🔴🔴🔴 판정문 «맨 위»에 실어야 하는 한 줄"]),
    ("갈린굶김", [O, J, "🔴🔴🔴 판정 자와 «굶김 부호»가 갈린 병기 자"]),
    ("갈린증강", [O, J, "🔴🔴🔴 판정 자와 «증강 부호»가 갈린 병기 자"]),
    ("순서뒤집", [O, J, "🔴🔴🔴 순서에 따라 «증강 부호»가 뒤집히는 자"]),
    ("P1", [O, J, "🔴 P1 판정자 순서A 굶김 t_clu 2 이상인가"]),
    ("P1t", [O, J, "🔴 P1 그 t_clu"]),
    ("P2", [O, J, "🔴 P2 판정자 상호작용 t_clu 2 이상인가"]),
    ("P2t", [O, J, "🔴 P2 그 t_clu"]),
    ("P3", [O, J, "🔴 P3 탐색 45-90-135 짝차 중 2·SE_clu 넘은 수"]),
    ("Δt", [O, J, "🔴 Δ(1800) t_clu"]),
    ("ΔSE", [O, J, "🔴 Δ(1800) 군집 SE"]),
    ("산성분", [O, J, "🔴🔴 성분 여덟 중 t_clu 가 2 를 넘은 것(판정 자)"]),
    ("산성분수", [O, J, "🔴🔴 그 수(판정 자)"]),
    ("천장문턱", [O, J, "🔴 문턱 0.00353 — 깨끗한 천장 대조가 이 «자»를 넘었나"]),
    ("판정걸린", [O, J, "🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)"]),
    ("칸수", [O, "🔴 자", "🔴 잰 칸 수"]),
    ("탐칸수", [O, "🔴 자", "🔴 탐색 칸 수"]),
    ("씨앗수", [O, "🔴 자", "씨앗"]),
    ("도메인", [O, "🔴 자", "게이트 도메인"]),
    ("유보행", [O, "🔴 자", "게이트 유보 행 합"]),
    ("판정칸격자", [O, EXP, "🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나"]),
    ("base90H", [O, EXP, "🔴🔴 `base=90` 칸이 판정의 `H` 칸과 «같은 물건»인가 — 실측",
                 "🔴🔴 같은 물건인가"]),
    ("NALL", [O, FIX, "🔴🔴🔴 `N_ALL` 을 «계산»했다"]),
    ("손리터럴", [O, FIX, "🔴🔴🔴 990 의 손 리터럴(`world990.py` 소스에서 «읽었다»)"]),
    ("모자란hplt", [O, FIX, "🔴🔴🔴 그 리터럴이 요구한 hplt 자리 − 실제 hplt 행"]),
    ("P4", [O, FIX, "🔴🔴🔴 P4 N_ALL 칸의 부족.hplt 최대"]),
    ("hplt행", [O, FIX, "🔴 `len(pool.yh)`"]),
    # ── 배선 ─────────────────────────────────────────────────────
    ("배선수", [G, "🔴 배선 검사 수(분모)"]),
    ("배선통과", [G, "🔴 통과 수"]),
    ("구성참", [G, "🔴🔴 ㉠ 구성상 «참»인 검사 수(변이체가 안 떨어졌다)"]),
    ("구성거짓", [G, "🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수(변이체가 반드시 떨어진다)"]),
    ("코드변이", [G, "🔴🔴🔴 ㉢ 변이체가 «검사 대상 코드»를 바꾼 검사 수"]),
    ("배선걸린", [G, "🔴 걸린 자리 합"]),
    ("배선중앙", [G, "🔴🔴 걸린 자리 «중앙값»"]),
    ("배선최대몫", [G, "🔴🔴🔴 «최대 기여» 검사의 몫"]),
    ("배선최대이름", [G, "🔴 그 검사 이름"]),
    ("천장폭", [G, "🔴 씨앗별 base 천장", "🔴 그 폭(= 씨앗에 따라 base 가 다른 행 수)"]),
    # ── 자기 자 ──────────────────────────────────────────────────
    ("P5", [D, DA, "🔴 P5 엄한 판으로 990 을 다시 세면 실패 절 수"]),
    ("엄한988", [D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수", "988"]),
    ("엄한989", [D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수", "989"]),
    ("엄한990", [D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수", "990"]),
    ("관대사이클", [D, DA, "🔴🔴🔴 게재값이 관대했던 사이클"]),
    ("990거짓변이", [D, DB, "🔴🔴🔴 「구성상 거짓」(반드시 떨어지는 변이체)인 검사"]),
    ("990거짓수", [D, DB, "🔴🔴🔴 그 수"]),
    ("990참수", [D, DB, "🔴🔴🔴 990 이 낸 「구성상 참」 수"]),
    ("990걸린", [D, DB, "🔴🔴 990 의 걸린 자리 합"]),
    ("990중앙", [D, DB, "🔴🔴 990 의 걸린 자리 «중앙값»"]),
    ("990최대몫", [D, DB, "🔴🔴🔴 990 의 «최대 기여» 검사의 몫"]),
    ("리플전체", [D, DC, "🔴 리플로그 전체 항목 수"]),
    ("리플구간", [D, DC, "🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)"]),
    ("리플위반", [D, DC, "🔴🔴🔴 그 수"]),
    ("HEAD", [D, DC, "🔴 점 표본(990 판) — `git symbolic-ref -q HEAD`"]),
    ("D못찾", [D, DD, "🔴🔴🔴 못 찾는 수 합"]),
    ("D측정치", [D, DD, "🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수"]),
    ("D유효", [D, DD, "🔴🔴🔴 유효숫자가 어긋난 슬롯 수"]),
    ("D센수", [D, DD, "🔴🔴🔴 센 수 합"]),
    ("D9못찾", [D, DD9, "🔴🔴🔴 못 찾는 수 합"]),
    ("D9측정치", [D, DD9, "🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수"]),
    ("D9유효", [D, DD9, "🔴🔴🔴 유효숫자가 어긋난 슬롯 수"]),
    ("F5N", [D, DE, "🔴🔴🔴 ㉢ 판정문의 슬롯 수 `N`(= 치환표가 심은 수)"]),
    ("F5M", [D, DE, "🔴🔴🔴 ㉢ 그중 «세계 자료 지문이 걸린 산출물 칸»에서 온 것 `M`"]),
    ("F5몫", [D, DE, "🔴🔴🔴 ㉢ 몫 `M/N`"]),
    ("F5옛", [D, DE, "🔴🔴🔴 ㉡ 그중 세계 자료를 «인용한» 문장 수(옛 자 --- 파일명 grep)"]),
    ("F5문장", [D, DE, "🔴🔴🔴 ㉡ 판정문의 주장 문장 수"]),
    ("연경로", [D, DE, "🔴🔴🔴 ㉠ 런타임 최대"]),
    ("F13분모1", [D, DF, "🔴🔴🔴 분모 ① `runners/*991*` ∩ {json, txt}"]),
    ("F13분모2", [D, DF, "🔴🔴🔴 분모 ② `runners/*991*` «전량»"]),
    ("F13러너미인용", [D, DF, "🔴🔴🔴 그 수"]),
    ("F13러너990", [D, DF, "🔴 990 의 같은 수(러너 미인용)"]),
    ("자기걸린", [D, "🔴 걸린 자리 합"]),
    ("자기중앙", [D, "🔴🔴 걸린 자리 «중앙값»"]),
    ("자기최대몫", [D, "🔴🔴🔴 «최대 기여» 절의 몫"]),
    ("슬롯988", [D, "🔴🔴🔴 988·989 는 «슬롯 대장이 있나»", "out988_slots.json"]),
    ("슬롯989", [D, "🔴🔴🔴 988·989 는 «슬롯 대장이 있나»", "out989_slots.json"]),
    # ── 채점 ────────────────────────────────────────────────────
    ("예측맞은", [S, "§4 예측", "🔴 맞은 수"]),
    ("예측분모", [S, "§4 예측", "🔴 분모"]),
    ("반증수", [S, "§5 반증조건", "🔴 반증된 수"]),
    ("반증분모", [S, "§5 반증조건", "🔴 분모"]),
    ("반증목록", [S, "§5 반증조건", "🔴🔴🔴 반증된 조건"]),
    ("미측정", [S, "§5 반증조건", "🔴🔴 미측정(잰 것이 아닌) 조건"]),
    ("최상위", [S, "통과"]),
    # ── ⑤′ ──────────────────────────────────────────────────────
    ("오분모", [F, "🔴 절 수(분모)"]),
    ("오실패", [F, "🔴 실패한 절"]),
    ("오통과", [F, "통과"]),
    ("오4구판", [F, "4 도장 확인",
               "🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)"]),
    ("오4신판", [F, "4 도장 확인",
               "🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다 · 🔴 982 부터 문다)"]),
    ("오4면제", [F, "4 도장 확인", "🔴🔴 그 수"]),
    ("오4통과", [F, "4 도장 확인", "통과"]),
]))


def _now():
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def table(ref):
    """🔴 `SPEC` 전량을 «산출물에서» 따라간다. 못 읽은 것을 «수와 이름»으로 남긴다."""
    vals, paths, errs = collections.OrderedDict(), collections.OrderedDict(), {}
    for name, path in SPEC.items():
        v, err = LG.resolve(path)
        paths[name] = path
        if err is None:
            vals[name] = v
        else:
            vals[name] = None
            errs[name] = err
    return collections.OrderedDict([
        ("ref", ref),
        ("🔴 슬롯 수", len(SPEC)),
        ("🔴 못 읽은 슬롯 수", len(errs)),
        ("🔴 못 읽은 슬롯", errs or "없음"),
        ("값", vals), ("키 경로", paths),
        ("🔴 이 표의 규율",
         "🔴 **여기 «없는» 수는 문서에 못 들어간다.** `render()` 가 모르는 슬롯에서 멈춘다"),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", len(SPEC)),
        ("통과", bool(not errs)),
    ])


SLOT = re.compile(r"\{\{([^}]+)\}\}")


def render(tpl, t):
    """🔴 치환하며 «슬롯이 앉은 문자 자리»를 기록한다."""
    vals, paths = t["값"], t["키 경로"]
    out, slots, i, pos = [], [], 0, 0
    for m in SLOT.finditer(tpl):
        k = m.group(1).strip()
        if k not in vals:
            raise SystemExit("🔴 치환표에 없는 슬롯: %s" % k)
        out.append(tpl[i:m.start()])
        pos += m.start() - i
        s = LG.render(vals[k]) if vals[k] is not None else "없음"
        slots.append({"키 경로": paths[k], "값": s, "슬롯": k,
                      "시작": pos, "끝": pos + len(s)})
        out.append(s)
        pos += len(s)
        i = m.end()
    out.append(tpl[i:])
    return "".join(out), slots


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="docs", choices=("docs", "card"))
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t = table(a.ref)
    (OUT / "out991_table.json").write_text(
        json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.stage == "docs":
        man, shas = collections.OrderedDict(), collections.OrderedDict()
        for name in ("판정_991", "card_991", "handoff_991", "pr_991"):
            tp = DOCS / "tpl" / ("%s.md.tpl" % name)
            if not tp.is_file():
                raise SystemExit("🔴 템플릿이 없다: %s" % tp)
            body, slots = render(tp.read_text(encoding="utf-8"), t)
            rel = "docs/%s.md" % name
            (ROOT / rel).write_text(body, encoding="utf-8")
            man[rel] = {"절대경로": str(ROOT / rel), "슬롯": slots}
            shas[rel] = hashlib.sha256(body.encode("utf-8")).hexdigest()
        (OUT / "out991_slots.json").write_text(json.dumps(
            collections.OrderedDict([
                ("무엇", "🔴 슬롯 대장 — 규칙 D(`ledger.audit_text` 976 판)가 읽는다"),
                ("파일별", man),
                ("🔴 슬롯 수 합", int(sum(len(v["슬롯"]) for v in man.values()))),
                ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)",
                 int(sum(len(v["슬롯"]) for v in man.values()))),
                ("통과", bool(man)),
                ("시각(UTC)", _now()),
            ]), ensure_ascii=False, indent=1), encoding="utf-8")
        (OUT / "out991_docsha.json").write_text(json.dumps(
            collections.OrderedDict([
                ("무엇", "🔴 문서 sha256 — `F10`(문서 고리 수렴)이 읽는다"),
                ("ref", a.ref), ("파일별", shas),
                ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", len(shas)),
                ("통과", bool(shas)), ("시각(UTC)", _now()),
            ]), ensure_ascii=False, indent=1), encoding="utf-8")
        sys.stderr.write("%s  [note991] 문서 %d · 슬롯 %d · 못 읽은 슬롯 %d\n"
                         % (_now(), len(man), t["🔴 슬롯 수"],
                            t["🔴 못 읽은 슬롯 수"]))
    else:
        body = (DOCS / "handoff_991.md").read_text(encoding="utf-8")
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        head = ("<!-- 991:인계:시작 -->\n"
                "## 🔴🔴🔴 지금 여기부터 — **노트 991 이 끝났다**\n\n"
                "> 🔴🔴🔴 **아래는 `docs/handoff_991.md` 를 «바이트로» 옮긴 것이다.**\n"
                "> `sha256 = %s`\n"
                "> 🔴 **손으로 안 썼다** --- `runners/note991_gen.py --stage card` 가 옮겼다.\n"
                "> 🔴🔴 **이 쓰기는 «치환»이다** --- 표지 구획만 갈아 끼우므로 두 번 돌려도 "
                "파일이 «안 자란다».\n\n"
                "%s\n<!-- 991:인계:끝 -->\n" % (sha, body))
        cur = CARD.read_text(encoding="utf-8") if CARD.is_file() else ""
        cur = re.sub(r"<!-- 991:인계:시작 -->.*?<!-- 991:인계:끝 -->\n?", "", cur,
                     flags=re.S)
        i = cur.index("\n") + 1 if "\n" in cur else 0
        CARD.write_text(cur[:i] + "\n" + head + "\n" + cur[i:], encoding="utf-8")
        sys.stderr.write("%s  [note991] 메모리 카드 갱신 · sha %s\n" % (_now(), sha[:12]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
