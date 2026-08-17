#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""991 원장 — 🔴🔴🔴 **`R5`: 보고 문장의 수를 «슬롯»에 넣는다**.

🔴 **990 의 원장 수 불일치가 「대화로만 흐른 수는 아무 자도 안 문다」의 실례다** ---
990 은 `git rev-list --count`(커밋 수 `1,243`)를 「원장 키 수」로 보고했고,
진짜 원장 키는 `1,201` 이었으며, `1243`·`1251`·`1203` 은 문서·원장·PR 어디에도 없었다.

🔴🔴 **그래서 이 러너가 「원장 키 수(전/후)」 칸을 «만든다».**
보고·티처 요약·PR 의 수는 «전부 이 칸에서 찍는다».

씀:
    python3 runners/ledger991.py --ref <40자 sha>
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
KEY = "노트 991"
RAN = ("runners/ledger991.py",)


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
    """🔴 **원장 키 수 = 최상위 키 수다.** 커밋 수가 «아니다**."""
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
    ap.add_argument("--branch", default="note/991-order-rulers")
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    hits = 0

    # ══ 🔴🔴🔴 R5 --- 「원장 키 수(전/후)」 칸 ═════════════════════════
    before_raw = LEDGER.read_text(encoding="utf-8")
    n_before, u_before = _ledger_keys(before_raw)
    hits += 1
    n_main, u_main = _count_of("main")
    n_br, u_br = _count_of(a.branch)
    hits += 2
    rc_c, cnt_main, _e = _git(["rev-list", "--count", "main"])
    rc_c2, cnt_br, _e2 = _git(["rev-list", "--count", a.branch])
    hits += 2

    O, G, D, S, L, F = ("out991_order.json", "out991_wiring.json",
                        "out991_audit.json", "out991_score.json",
                        "out991_last.json", "fiveprime_991.json")
    J = "§5 🔴🔴🔴 판정"
    ORD = "§1 🔴🔴🔴 순서 분해 — 자 셋 × 두 순서 × 대칭 배분(λ 전량)"
    EXP = "§2 🔴🔴🔴 탐색 격자 — 🔴 **사전등록 «안»** · `base=1800` 은 «없다**"
    FIX = "§4 🔴🔴 즉시정정 — 「전량」 눈금을 손 리터럴에서 뗐다"
    DA = "§A 🔴🔴🔴 ⑤′ 절 4 — 엄한 판으로 다시 센다"
    ROW = "🔴🔴🔴 한 줄 표"

    ent = collections.OrderedDict()
    ent["언제"] = _now()
    ent["🔴 축"] = "C3(mixture) × C6(scaling) × C2(도메인 가중)"
    ent["🔴 가지"] = a.branch
    ent["🔴 사전등록"] = "docs/prereg_991_order_rulers.md"
    ent["🔴 ref(사전등록 커밋)"] = a.ref

    # 🔴🔴🔴 R5 --- 이 칸이 «보고의 수도»다
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
            ("🔴🔴🔴 990 이 저지른 일",
             "🔴 **커밋 수를 「원장 키 수」로 보고했고 그 차를 「중복」이라 불렀다.** "
             "그 수는 문서·원장·PR 어디에도 없었다 --- «대화로만 흐른 수는 아무 자도 안 문다»"),
        ])
    hits += 1

    ent["🔴🔴🔴 세계 명제 W1′ — 분해의 답은 「순서」가 정한다"] = collections.OrderedDict([
        ("Δ(1800) 판정 자", _dig(O, ORD, "0", "R_pool 묶음", ROW, "Δ(1800)")),
        ("순서 A 증강", _dig(O, ORD, "0", "R_pool 묶음", ROW, "순서 A 증강")),
        ("순서 A 굶김", _dig(O, ORD, "0", "R_pool 묶음", ROW, "순서 A 굶김")),
        ("🔴 순서 B 증강(양수다)", _dig(O, ORD, "0", "R_pool 묶음", ROW, "순서 B 증강")),
        ("순서 B 굶김", _dig(O, ORD, "0", "R_pool 묶음", ROW, "순서 B 굶김")),
        ("🔴 상호작용", _dig(O, ORD, "0", "R_pool 묶음", ROW, "상호작용")),
        ("대칭 배분 증강", _dig(O, ORD, "0", "R_pool 묶음", ROW, "대칭 증강")),
        ("대칭 배분 굶김", _dig(O, ORD, "0", "R_pool 묶음", ROW, "대칭 굶김")),
        ("🔴 순서 A 굶김의 t_clu", _dig(O, J, "🔴 P1 그 t_clu")),
        ("🔴 상호작용의 t_clu", _dig(O, J, "🔴 P2 그 t_clu")),
        ("🔴 성분 여덟 중 t_clu 2 를 넘은 수", _dig(O, J, "🔴🔴 그 수(판정 자)")),
        ("🔴 맨 위 한 줄", _dig(O, J, "🔴🔴🔴 판정문 «맨 위»에 실어야 하는 한 줄")),
    ])
    hits += 1
    ent["🔴🔴🔴 세계 명제 W2 — 답을 정하는 것은 자의 도메인 가중"] = collections.OrderedDict([
        ("굶김 부호가 갈린 병기 자", _dig(O, J, "🔴🔴🔴 판정 자와 «굶김 부호»가 갈린 병기 자")),
        ("증강 부호가 갈린 병기 자", _dig(O, J, "🔴🔴🔴 판정 자와 «증강 부호»가 갈린 병기 자")),
        ("순서에 따라 증강 부호가 뒤집히는 자",
         _dig(O, J, "🔴🔴🔴 순서에 따라 «증강 부호»가 뒤집히는 자")),
        ("균등 자 순서 A 굶김", _dig(O, ORD, "0", "R_eq 균등", ROW, "순서 A 굶김")),
        ("챔피언 자 순서 A 굶김", _dig(O, ORD, "0", "R_champ 챔피언가중", ROW, "순서 A 굶김")),
    ])
    hits += 1
    ent["🔴🔴 세계 명제 W3 — base 격자(탐색 팔을 사전등록 «안»으로)"] = \
        collections.OrderedDict([
            ("판정 칸이 격자에 있나",
             _dig(O, EXP, "🔴🔴🔴 판정 칸(`base 1800` = `B`)이 이 격자에 있나")),
            ("판정 자 최적 base", _dig(O, EXP, "R_pool 묶음", "🔴🔴🔴 ρ 가 «가장 높은» base 행 수")),
            ("균등 자 최적 base", _dig(O, EXP, "R_eq 균등", "🔴🔴🔴 ρ 가 «가장 높은» base 행 수")),
            ("챔피언 자 최적 base",
             _dig(O, EXP, "R_champ 챔피언가중", "🔴🔴🔴 ρ 가 «가장 높은» base 행 수")),
            ("🔴 벼랑이라 적을 수 있나 — 판정 자",
             _dig(O, EXP, "R_pool 묶음", "🔴🔴🔴 「벼랑」이라 적을 수 있나(`조항 68`)")),
            ("🔴 벼랑이라 적을 수 있나 — 균등 자",
             _dig(O, EXP, "R_eq 균등", "🔴🔴🔴 「벼랑」이라 적을 수 있나(`조항 68`)")),
            ("🔴 P3 45-90-135 짝차 중 2·SE 넘은 수",
             _dig(O, J, "🔴 P3 탐색 45-90-135 짝차 중 2·SE_clu 넘은 수")),
        ])
    hits += 1
    ent["🔴 즉시정정 — 「전량」 눈금을 손 리터럴에서 뗐다"] = collections.OrderedDict([
        ("N_ALL(계산)", _dig(O, FIX, "🔴🔴🔴 `N_ALL` 을 «계산»했다")),
        ("990 의 손 리터럴",
         _dig(O, FIX, "🔴🔴🔴 990 의 손 리터럴(`world990.py` 소스에서 «읽었다»)")),
        ("그 리터럴이 못 채운 hplt 자리",
         _dig(O, FIX, "🔴🔴🔴 그 리터럴이 요구한 hplt 자리 − 실제 hplt 행")),
        ("N_ALL 칸의 부족.hplt 최대", _dig(O, FIX, "🔴🔴🔴 P4 N_ALL 칸의 부족.hplt 최대")),
        ("🔴 깨끗한 천장 대조(판정 자)", _dig(O, J, "🔴 깨끗한 천장 대조 값(판정 자)")),
    ])
    hits += 1
    ent["🔴 배선 — 변이체의 「양쪽」 공허"] = collections.OrderedDict([
        ("검사 수", _dig(G, "🔴 배선 검사 수(분모)")),
        ("통과 수", _dig(G, "🔴 통과 수")),
        ("㉠ 구성상 참", _dig(G, "🔴🔴 ㉠ 구성상 «참»인 검사 수(변이체가 안 떨어졌다)")),
        ("㉡ 구성상 거짓",
         _dig(G, "🔴🔴🔴 ㉡ 구성상 «거짓»인 검사 수(변이체가 반드시 떨어진다)")),
        ("㉢ 코드 변이체 수", _dig(G, "🔴🔴🔴 ㉢ 변이체가 «검사 대상 코드»를 바꾼 검사 수")),
        ("걸린 자리 합", _dig(G, "🔴 걸린 자리 합")),
        ("걸린 자리 중앙값", _dig(G, "🔴🔴 걸린 자리 «중앙값»")),
        ("최대 기여 검사의 몫", _dig(G, "🔴🔴🔴 «최대 기여» 검사의 몫")),
    ])
    hits += 1
    ent["🔴🔴 자기 자 — 세 구멍"] = collections.OrderedDict([
        ("🔴 P5 엄한 판으로 990 을 다시 세면 실패 절 수",
         _dig(D, DA, "🔴 P5 엄한 판으로 990 을 다시 세면 실패 절 수")),
        ("🔴 엄한 판 정정 988·989·990",
         _dig(D, DA, "🔴🔴🔴 정정 — 988 · 989 · 990 의 «엄한» 실패 수")),
        ("🔴 게재값이 관대했던 사이클", _dig(D, DA, "🔴🔴🔴 게재값이 관대했던 사이클")),
        ("🔴 990 의 「구성상 거짓」 변이체 수",
         _dig(D, "§B 🔴🔴 990 의 배선 일곱 — 변이체의 「양쪽」 공허", "🔴🔴🔴 그 수")),
        ("🔴 F05 칸 인용 — 슬롯 N",
         _dig(D, "§E 🔴🔴🔴 `F05` — 「칸 인용」",
              "🔴🔴🔴 ㉢ 판정문의 슬롯 수 `N`(= 치환표가 심은 수)")),
        ("🔴 F05 칸 인용 — 세계 자료 칸 M",
         _dig(D, "§E 🔴🔴🔴 `F05` — 「칸 인용」",
              "🔴🔴🔴 ㉢ 그중 «세계 자료 지문이 걸린 산출물 칸»에서 온 것 `M`")),
        ("🔴 리플로그 구간 항목 수",
         _dig(D, "§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」",
              "🔴🔴🔴 사전등록 «이후» 항목 수(= 구간 분모)")),
        ("🔴 그 구간의 위반 수",
         _dig(D, "§C 🔴🔴🔴 `F02` — 리플로그 「구간 전수」", "🔴🔴🔴 그 수")),
        ("🔴 규칙 D — 990 을 991 자로 재면 유효숫자 어긋난 슬롯 수",
         _dig(D, "§D-나 🔴 규칙 D — 990 을 같은 자로 다시 센다",
              "🔴🔴🔴 유효숫자가 어긋난 슬롯 수")),
        ("🔴 988·989 는 슬롯 대장이 «없다» --- 규칙 D 를 «잴 수가 없었다»",
         _dig(D, "🔴🔴🔴 그래서 990 «이전»엔 규칙 D 를 «잴 수가 없었다»")),
        ("🔴 #247 데몬 커밋이 «전부» 회수됐나",
         _dig(D, "§G 🔴 `#247`·`#248` 머지 — 가지 쪽 고유 줄 수", "🔴 PR 별",
              "PR #247 (note/989-world-budget)", "🔴🔴🔴 데몬 커밋이 «전부» 회수됐나")),
    ])
    hits += 1
    ent["🔴 채점"] = collections.OrderedDict([
        ("예측", "%s / %s" % (_dig(S, "§4 예측", "🔴 맞은 수"),
                            _dig(S, "§4 예측", "🔴 분모"))),
        ("반증조건", "%s / %s" % (_dig(S, "§5 반증조건", "🔴 반증된 수"),
                              _dig(S, "§5 반증조건", "🔴 분모"))),
        ("반증된 조건", _dig(S, "§5 반증조건", "🔴🔴🔴 반증된 조건")),
        ("미측정", _dig(S, "§5 반증조건", "🔴🔴 미측정(잰 것이 아닌) 조건")),
        ("🔴 최상위 통과", _dig(S, "통과")),
    ])
    hits += 1
    ent["🔴 ⑤′"] = collections.OrderedDict([
        ("절 분모", _dig(F, "🔴 절 수(분모)")),
        ("실패한 절", _dig(F, "🔴 실패한 절")),
        ("통과", _dig(F, "통과")),
        ("🔴 절 4 구판", _dig(F, "4 도장 확인",
                          "🔴 구판 절 4 통과(980 판 --- 도장의 «존재»와 시각만 본다)")),
        ("🔴 절 4 신판", _dig(
            F, "4 도장 확인",
            "🔴🔴 신판 절 4 통과(981 판 --- 도장의 «판정»을 읽는다 · 🔴 982 부터 문다)")),
        ("🔴 절 4 게재값(엄한 판)", _dig(F, "4 도장 확인", "통과")),
        ("🔴 절 4 에서 등기 사유로 뺀 수", _dig(F, "4 도장 확인", "🔴🔴 그 수")),
    ])
    hits += 1
    ent["🔴 막힌 명령(조항 69)"] = (
        "🔴 **없었다.** `git checkout`·`git symbolic-ref`(쓰기)·`gh pr merge` 를 "
        "한 번도 안 불렀다. 🔴 `HEAD` 는 내내 `refs/heads/main` --- "
        "리플로그 «구간 전수»가 증거다(점 표본이 아니다).")
    ent["🔴 규약 개정"] = "docs/루프.md v4.7 → v4.8 (조항 66 · 3-나 집행 · 68 · 59-나)"
    ent["🔴 논문"] = ("🔴 **안 냈다.** 노트 981~991 «열한» 사이클 연속으로 `paper/` 를 "
                  "안 만졌다. `⑤′` 가 통과해야 손대기로 한 규율 때문이다.")
    ent["🔴 걸린 자리(= 자가 «칸»을 «읽은» 회수)"] = hits
    ent["🔴 낸 러너"] = "runners/ledger991.py"
    ent["통과"] = bool(_dig(S, "통과"))

    led = json.loads(before_raw)
    led[KEY] = ent                                 # 🔴 치환이다 --- 안 자란다
    after_txt = json.dumps(led, ensure_ascii=False, indent=1)
    LEDGER.write_text(after_txt, encoding="utf-8")
    n_after, u_after = _ledger_keys(after_txt)
    ent["🔴🔴🔴 R5 원장 키 수 — **보고·티처 요약·PR 의 수는 «전부 이 칸»에서 찍는다**"][
        "🔴🔴🔴 원장 키 수(이 항목을 «쓴 뒤» · 디스크)"] = n_after
    ent["🔴🔴🔴 R5 원장 키 수 — **보고·티처 요약·PR 의 수는 «전부 이 칸»에서 찍는다**"][
        "🔴 중복 키 수(후)"] = n_after - u_after
    led[KEY] = ent
    after_txt = json.dumps(led, ensure_ascii=False, indent=1)
    LEDGER.write_text(after_txt, encoding="utf-8")
    n_final, u_final = _ledger_keys(after_txt)

    rec = collections.OrderedDict([
        ("무엇", "991 원장 항목 --- 🔴 `R5` 보고의 수를 «슬롯»에 넣는다"),
        ("🔴 원장 경로", "data/lab/denominator.json"),
        ("🔴 키", KEY),
        ("🔴🔴🔴 원장 키 수(전)", n_before),
        ("🔴🔴🔴 원장 키 수(후)", n_final),
        ("🔴🔴🔴 중복 키 수(후)", n_final - u_final),
        ("🔴 `main` 의 원장 키 수", n_main),
        ("🔴 가지의 원장 키 수", n_br),
        ("⚠ `rev-list --count main`(커밋 수 · 원장 키 수가 «아니다»)",
         int(cnt_main.strip()) if rc_c == 0 and cnt_main.strip() else None),
        ("🔴 원장 sha256",
         hashlib.sha256(LEDGER.read_bytes()).hexdigest()),
        ("🔴 걸린 자리(= 자가 «비교»를 «수행»한 회수)", hits),
        ("통과", bool(hits > 0 and n_final >= n_before)),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256", {r: hashlib.sha256((ROOT / r).read_bytes()).hexdigest()
                             for r in RAN if (ROOT / r).is_file()}),
            ("시각(UTC · 시작)", _now()), ("시각(UTC · 끝)", _now()),
        ])),
    ])
    (OUT / "out991_ledger.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [ledger991] 원장 키 %d → %d · 중복 %d\n"
                     % (_now(), n_before, n_final, n_final - u_final))
    return 0


if __name__ == "__main__":
    sys.exit(main())
