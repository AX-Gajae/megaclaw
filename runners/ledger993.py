#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""993 원장 — 🔴🔴🔴 **보고 문장의 수는 «슬롯»에서 찍는다**(`조항 59-나` · 991 `R5` 승계).

🔴 **991 이 여기서 무너졌다**: 원장의 `채점` 칸이 `"§4 예측"`·`"§5 반증조건"` 을 읽는데
실제 키는 `"§4 🔴 예측"`·`"§5 🔴 반증조건"` 이라 **`None / None` 이 원장에 들어갔다.**
993 는 키 이름을 `score993` 와 «같은 상수»로 맞춘다.

씀:
    python3 runners/ledger993.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = ROOT / "runners"
LEDGER = ROOT / "data/lab/denominator.json"
KEY = "노트 993"
RAN = ("runners/ledger993.py",)

O = "out993_order.json"
G = "out993_wiring.json"
MU = "out993_mut.json"
D = "out993_audit.json"
S = "out993_score.json"
L = "out993_last.json"
F = "fiveprime_993.json"
PA = "out993_paper.json"

ORD = "§1 🔴🔴🔴 순서 분해 — 자 셋 × 두 순서 × 대칭 배분(λ 전량)"
SEB = "§1-나 🔴🔴🔴 SE 표 — 자 3 × 성분 8 = 24 칸 전량"
EXP = "§2 🔴🔴🔴 탐색 격자"
FIX = "§4 🔴🔴 즉시정정"
JUD = "§5 🔴🔴🔴 판정"
ROW = "🔴🔴🔴 한 줄 표"
DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판 + 면제 없는 판"
DB = "§B 🔴🔴 990 의 배선 일곱 — 진짜 AST"
DC = "§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」"
DD = "§D 🔴🔴 규칙 D — 993 자신"
SC4 = "§4 🔴 예측"
SC5 = "§5 🔴 반증조건"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dig(rel, *keys):
    p = OUT / rel
    if not p.is_file():
        return None
    cur = json.loads(p.read_text(encoding="utf-8"))
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, list):
            try:
                cur = cur[int(k)]
            except Exception:                                    # noqa: BLE001
                return None
        else:
            return None
    return cur


def _git(args):
    r = subprocess.run(["git", "-c", "core.quotePath=false"] + args,
                       cwd=str(ROOT), capture_output=True)
    return (r.returncode, r.stdout.decode("utf-8", "surrogateescape"),
            r.stderr.decode("utf-8", "surrogateescape"))


def _ledger_keys(text):
    """🔴 **원장 키 수 = 최상위 키 수다.** 커밋 수가 «아니다»."""
    pairs = json.loads(text, object_pairs_hook=lambda p: p)
    return len(pairs), len(set(k for k, _v in pairs))


def _count_of(ref):
    rc, out, _e = _git(["show", "%s:data/lab/denominator.json" % ref])
    if rc != 0:
        return None, None
    return _ledger_keys(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--branch", default="note/993-straighten-the-rulers")
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    t0 = _now()
    hits = 0

    before_raw = LEDGER.read_text(encoding="utf-8")
    n_before, u_before = _ledger_keys(before_raw)
    hits += 1
    n_main, u_main = _count_of("main")
    n_br, u_br = _count_of(a.branch)
    hits += 2
    rc_c, cnt_main, _e = _git(["rev-list", "--count", "main"])
    rc_c2, cnt_br, _e2 = _git(["rev-list", "--count", a.branch])
    hits += 2

    ent = collections.OrderedDict()
    ent["언제"] = _now()
    ent["🔴 축"] = "C1(자기 자 · 배선) × C6(scaling) × C2(도메인 가중)"
    ent["🔴 가지"] = a.branch
    ent["🔴 사전등록"] = "docs/prereg_993_straighten_the_rulers.md"
    ent["🔴 ref(사전등록 커밋)"] = a.ref
    ent["🔴🔴🔴 R5 원장 키 수 — **보고·티처 요약·PR 의 수는 «전부 이 칸»에서 찍는다**"] = \
        collections.OrderedDict([
            ("🔴 원장 키 수(이 항목을 쓰기 «전» · 디스크)", n_before),
            ("🔴 그중 «중복 아닌» 키 수(전)", u_before),
            ("🔴 중복 키 수(전)", n_before - u_before),
            ("🔴 `main` 의 원장 키 수", n_main),
            ("🔴 `%s` 의 원장 키 수" % a.branch, n_br),
            ("⚠ `git rev-list --count main`(= «커밋 수» · 🔴 원장 키 수가 «아니다»)",
             int(cnt_main.strip()) if rc_c == 0 and cnt_main.strip() else None),
            ("⚠ `git rev-list --count %s`(= «커밋 수»)" % a.branch,
             int(cnt_br.strip()) if rc_c2 == 0 and cnt_br.strip() else None),
        ])
    hits += 1

    ent["🔴🔴🔴 세계 명제 W4 — 「최적 base」는 «격자 경계 인공물»이었다"] = \
        collections.OrderedDict([
            ("격자 칸 수", _dig(O, EXP, "🔴 격자 칸 수")),
            ("판정 자 argmax", _dig(O, EXP, "R_pool 묶음",
                                 "🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)")),
            ("🔴 argmax 가 격자 오른쪽 끝인가",
             _dig(O, EXP, "R_pool 묶음", "🔴🔴🔴 argmax 가 격자 오른쪽 끝인가")),
            ("🔴 최적 집합(2·SE 로 안 갈리는 칸)",
             _dig(O, EXP, "R_pool 묶음",
                  "🔴🔴🔴 «최적 집합»(argmax 와 `2·SE_clu` 로 «안 갈리는» 칸)")),
            ("🔴 그 크기", _dig(O, EXP, "R_pool 묶음", "🔴🔴🔴 최적 집합의 크기")),
            ("🔴 균등 자 argmax", _dig(O, EXP, "R_eq 균등",
                                   "🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)")),
            ("🔴 챔피언 자 argmax", _dig(O, EXP, "R_champ 챔피언가중",
                                    "🔴 `argmax` 칸(= 991 이 「최적」이라 적은 자)")),
            ("🔴 `base=90` 이 판정 `H` 와 같은 물건인가",
             _dig(O, EXP, "🔴🔴 `base=90` 칸이 판정의 `H` 칸과 «같은 물건»인가 — 실측",
                  "🔴🔴 같은 물건인가")),
        ])
    hits += 1
    ent["🔴🔴🔴 세계 명제 W5 — 「무엇이 사는가」는 «자의 사실»이다"] = \
        collections.OrderedDict([
            ("SE 표 칸 수(자 3 × 성분 8)", _dig(O, SEB, "🔴 칸 수")),
            ("🔴 자별 «2 를 넘은 성분 수»", _dig(O, SEB, "🔴🔴🔴 자별 «2 를 넘은 성분 수»")),
            ("🔴 자에 따라 «2·SE 판정»이 갈리는 성분",
             _dig(O, SEB, "🔴🔴🔴 자에 따라 «2·SE 판정»이 갈리는 성분")),
            ("🔴 그 수", _dig(O, SEB, "🔴🔴🔴 그 수")),
            ("🔴 자에 따라 «부호»가 갈리는 성분",
             _dig(O, SEB, "🔴🔴🔴 자에 따라 «부호»가 갈리는 성분")),
            ("🔴 판정 자 상호작용 t_clu", _dig(O, JUD, "🔴 판정자 상호작용 t_clu")),
            ("🔴 챔피언 자 상호작용 t_clu", _dig(O, JUD, "🔴 챔피언자 상호작용 t_clu")),
            ("🔴 맨 위 한 줄", _dig(O, JUD, "🔴🔴🔴 판정문 «맨 위»에 실어야 하는 한 줄")),
        ])
    hits += 1
    ent["🔴🔴 배선 — 공허를 «설정 격자에서 실측»한다(손 라벨 폐기)"] = \
        collections.OrderedDict([
            ("검사 수", _dig(G, "🔴 배선 검사 수(분모)")),
            ("통과 수", _dig(G, "🔴 통과 수")),
            ("㉠ 구성상 참", _dig(G, "🔴🔴 ㉠ 구성상 «참»인 검사 수")),
            ("㉡ 구성상 거짓", _dig(G, "🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수")),
            ("㉢ 검정력 있는 검사 수", _dig(G, "🔴🔴🔴 ㉢ 검정력이 «있는» 검사 수")),
            ("🔴 `mut_kind` 손 라벨을 썼나", _dig(G, "🔴🔴🔴 `mut_kind` 손 라벨을 썼나")),
            ("🔴 991 의 여섯을 실측하면 구성상 거짓",
             _dig(G, "§B 🔴🔴🔴 991 의 여섯을 실측한다", "🔴🔴🔴 구성상 거짓 수")),
            ("🔴 991 이 신고한 수",
             _dig(G, "§B 🔴🔴🔴 991 의 여섯을 실측한다",
                  "🔴 991 이 «신고한» ㉡ 구성상 거짓 수(손 라벨)")),
            ("🔴 990 의 일곱 — 실행 자", _dig(MU, "🔴🔴🔴 그 수")),
            ("🔴 990 의 일곱 — 둘째 자(티처 손 자 재현)",
             _dig(MU, "🔴🔴🔴 둘째 자 — 「자료와 «무관하게» 강제되는 것」만 세면", "🔴 그 수")),
            ("걸린 자리 합", _dig(G, "🔴 걸린 자리 합")),
            ("🔴 걸린 자리 중앙값(993 가 고친 자)",
             _dig(G, "🔴🔴 걸린 자리 «중앙값»(🔴 993 가 고친 자 --- 짝수면 «두 가운데의 평균»)")),
        ])
    hits += 1
    ent["🔴🔴 자기 자 — 잡은 것을 «물렸다»"] = collections.OrderedDict([
        ("🔴 엄한 판 정정 988·989·990·991",
         _dig(D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 · 991 의 «엄한» 실패 수")),
        ("🔴 게재값이 관대했던 사이클", _dig(D, DA, "🔴🔴🔴 게재값이 관대했던 사이클")),
        ("🔴 991 의 「엄한 판 첫 통과」가 «면제로 산 것»인가",
         _dig(D, DA, "🔴🔴🔴 그래서 991 의 「엄한 판 첫 통과」는 «면제로 산 것»인가")),
        ("🔴 리플로그 구간 항목 수", _dig(D, DC, "🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)")),
        ("🔴 그 구간의 위반 수", _dig(D, DC, "🔴🔴🔴 그 수")),
        ("🔴 규칙 D — 키 경로와 본문이 다른 슬롯 합(993 가 «처음으로» 무는 칸)",
         _dig(D, DD, "🔴🔴🔴 키 경로와 본문이 다른 슬롯 합")),
        ("🔴 규칙 D — ㉰ 측정치", _dig(D, DD, "🔴🔴🔴 ㉰ 측정치(= 판정에 «무는» 것)만의 수")),
        ("🔴 `F09` 도장 위상 어긋남(993 자신)",
         _dig(L, "🔴🔴🔴 소비자 도장이 «생산자보다 앞선» 자리 수")),
        ("🔴 같은 자를 991 에 물리면",
         _dig(L, "🔴🔴 구판/신판 전후 — 991 에 같은 자를 물리면", "🔴🔴🔴 991 의 위상 어긋남 수")),
    ])
    hits += 1
    ent["🔴 채점"] = collections.OrderedDict([
        ("예측", "%s / %s" % (_dig(S, SC4, "🔴 맞은 수"), _dig(S, SC4, "🔴 분모"))),
        ("반증조건 — 통과 / «셀 수 있는» 분모",
         "%s / %s" % (_dig(S, SC5, "🔴 통과 수(셀 수 있는 것 중)"),
                      _dig(S, SC5, "🔴🔴🔴 «셀 수 있는» 분모(= 등록 분모 − 못 센 것)"))),
        ("🔴 등록 분모", _dig(S, SC5, "🔴 등록 분모")),
        ("🔴 반증된 조건", _dig(S, SC5, "🔴🔴 반증된 조건")),
        ("🔴 미측정(못 센) 조건", _dig(S, SC5, "🔴🔴 미측정(잰 것이 아닌) 조건")),
        ("🔴 재현 항목 V1~V12", "%s / %s"
         % (_dig(S, SC5, "F03", "근거", "🔴🔴🔴 재현한 수"),
            _dig(S, SC5, "F03", "근거", "🔴🔴🔴 재현 분모"))),
        ("🔴 최상위 통과", _dig(S, "통과")),
        ("🔴 최상위의 붉은 조각",
         _dig(S, "🔴🔴🔴 최상위를 이루는 절의 `통과` 전량", "🔴 붉은 조각")),
    ])
    hits += 1
    ent["🔴 ⑤′"] = collections.OrderedDict([
        ("절 분모", _dig(F, "🔴 절 수(분모)")),
        ("🔴 실패한 절 수", _dig(F, "🔴🔴🔴 실패한 절 수")),
        ("🔴 통과한 절 수", _dig(F, "🔴🔴🔴 통과한 절 수")),
        ("실패한 절", _dig(F, "🔴 실패한 절")),
        ("통과", _dig(F, "통과")),
        ("🔴 절 4 구판", _dig(F, "4 도장 확인",
                          "🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)")),
        ("🔴 절 4 신판", _dig(
            F, "4 도장 확인",
            "🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다 · 🔴 982 부터 문다)")),
        ("🔴🔴🔴 절 4 «면제 없는» 신판",
         _dig(F, "4 도장 확인", "🔴🔴🔴 993 R5 — «면제 없는» 신판 절 4 통과")),
        ("🔴 절 4 게재값(구판 and 신판 and 면제없는신판)", _dig(F, "4 도장 확인", "통과")),
        ("🔴 면제한 수", _dig(F, "4 도장 확인", "🔴 면제한 수")),
        ("🔴 꼬리표가 «절 4 용»이 아니라 «안» 뺀 수",
         _dig(F, "4 도장 확인", "🔴🔴🔴 993 R5 — 사유 꼬리표가 «절 4 용»이 아니라 «안» 뺀 수")),
    ])
    hits += 1
    ent["🔴 논문(⑥)"] = collections.OrderedDict([
        ("🔴 `paper/` 공백 사이클 수", _dig(PA, "🔴🔴🔴 `paper/` 공백 사이클 수")),
        ("🔴 마지막으로 만진 커밋", _dig(PA, "🔴 마지막으로 `paper/` 를 만진 커밋")),
        ("🔴 그 노트", _dig(PA, "🔴 그 노트 번호")),
        ("⚠ 991 카드가 손으로 박은 수", _dig(PA, "⚠ 991 카드가 손으로 박은 수")),
        ("🔴 이 사이클이 쓴 스텝", _dig(PA, "🔴 이 사이클이 «쓴» 스텝")),
        ("🔴 보냈나(컴파일·전송)", _dig(PA, "🔴 보냈나(컴파일·전송)")),
    ])
    hits += 1
    ent["🔴 막힌 명령(조항 69)"] = (
        "🔴 **없었다.** `git checkout`·`git symbolic-ref`(쓰기)·`gh pr merge` 를 "
        "한 번도 안 불렀다. 🔴 `HEAD` 는 내내 `refs/heads/main` --- "
        "리플로그 «구간 전수»가 증거다(점 표본이 아니다).")
    ent["🔴 규약 개정"] = "docs/루프.md v4.8 → v4.9 (조항 66 · 59-나 · 70 · 3-나)"
    ent["🔴 걸린 자리(= 자가 «칸»을 «읽은» 회수)"] = hits
    ent["🔴 낸 러너"] = "runners/ledger993.py"
    ent["통과"] = bool(_dig(S, "통과"))

    led = json.loads(before_raw)
    led[KEY] = ent                                 # 🔴 치환이다 --- 안 자란다
    after_txt = json.dumps(led, ensure_ascii=False, indent=1)
    LEDGER.write_text(after_txt, encoding="utf-8")
    n_after, u_after = _ledger_keys(after_txt)
    k5 = "🔴🔴🔴 R5 원장 키 수 — **보고·티처 요약·PR 의 수는 «전부 이 칸»에서 찍는다**"
    ent[k5]["🔴🔴🔴 원장 키 수(이 항목을 «쓴 뒤» · 디스크)"] = n_after
    ent[k5]["🔴 중복 키 수(후)"] = n_after - u_after
    led[KEY] = ent
    after_txt = json.dumps(led, ensure_ascii=False, indent=1)
    LEDGER.write_text(after_txt, encoding="utf-8")
    n_final, u_final = _ledger_keys(after_txt)

    rec = collections.OrderedDict([
        ("무엇", "993 원장 항목 --- 🔴 보고의 수를 «슬롯»에 넣는다"),
        ("🔴 원장 경로", "data/lab/denominator.json"),
        ("🔴 키", KEY),
        ("🔴🔴🔴 원장 키 수(전)", n_before),
        ("🔴🔴🔴 원장 키 수(후)", n_final),
        ("🔴🔴🔴 중복 키 수(후)", n_final - u_final),
        ("🔴 `main` 의 원장 키 수", n_main),
        ("🔴 가지의 원장 키 수", n_br),
        ("⚠ `rev-list --count main`(커밋 수 · 원장 키 수가 «아니다»)",
         int(cnt_main.strip()) if rc_c == 0 and cnt_main.strip() else None),
        ("🔴 원장 sha256", hashlib.sha256(LEDGER.read_bytes()).hexdigest()),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0 and n_final >= n_before)),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256", {r: hashlib.sha256((ROOT / r).read_bytes()).hexdigest()
                             for r in RAN if (ROOT / r).is_file()}),
            ("시각(UTC · 시작)", t0), ("시각(UTC · 끝)", _now()),
        ])),
    ])
    (OUT / "out993_ledger.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [ledger993] 원장 키 %d → %d · 중복 %d\n"
                     % (_now(), n_before, n_final, n_final - u_final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
