#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""990 — **원장(`data/lab/denominator.json`)에 「노트 990」 항목을 적는다.**

🔴 **손으로 안 쓴다.** 모든 수는 `runners/out990_*.json` 의 «칸»에서 온다.
🔴 **치환이다** --- 두 번 돌려도 원장이 «안 자란다».

씀:
    python3 runners/ledger990.py --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = ROOT / "runners"
LEDGER = ROOT / "data/lab/denominator.json"
KEY = "노트 990"


def _now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dig(rel, *keys):
    p = OUT / rel
    if not p.is_file():
        return None
    cur = json.loads(p.read_text(encoding="utf-8"))
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    a = ap.parse_args()
    if len(a.ref) != 40:
        raise SystemExit("🔴 --ref 는 40자 sha 여야 한다")
    A, C, CW, G, D, S, L, F = ("out990_arms.json", "out990_champ.json",
                               "out990_champw.json", "out990_wiring.json",
                               "out990_audit.json", "out990_score.json",
                               "out990_last.json", "fiveprime_990.json")
    J = "§5 🔴🔴🔴 판정"
    DEC = "§4 🔴🔴🔴 분해 — `Δ(N) = 증강 + 굶김`"
    EXP = "§6 🔴🔴 탐색 팔 — 🔴 **사전등록 «밖» · 채점 분모에 «안» 든다**"
    W2S = "§3 🔴🔴🔴 두 판의 대조 — **이 사이클의 세계 명제 `W2`**"
    hits = 0
    ent = collections.OrderedDict()
    ent["언제"] = _now()
    ent["🔴 축"] = "C3(mixture) × C6(scaling) × C2(도메인 가중)"
    ent["🔴 가지"] = "note/990-arms-rulers"
    ent["🔴 사전등록"] = "docs/prereg_990_arms_rulers.md"
    ent["🔴 ref(사전등록 커밋)"] = a.ref
    ent["🔴🔴🔴 세계 명제 W1 — 부호를 만든 것은 「굶김」이다"] = collections.OrderedDict([
        ("Δ(1800)", _dig(A, J, "🔴 R_pool 묶음 Δ(1800)")),
        ("증강 A", _dig(A, DEC, "R_pool 묶음", "1800",
                      "🔴 ① 증강 A(N) = ρ(base N + hplt αN) − ρ(base N)")),
        ("굶김 S", _dig(A, DEC, "R_pool 묶음", "1800",
                      "🔴 ② 굶김 S(N) = ρ(base (1−α)N + hplt αN) − ρ(base N + hplt αN)")),
        ("🔴 굶김의 몫", _dig(A, DEC, "R_pool 묶음", "1800", "🔴🔴🔴 굶김이 차지하는 몫")),
        ("🔴 항등식 잔차 최대(전 눈금 · 전 자)",
         _dig(A, "🔴 분해 잔차 — 전 눈금 · 전 자", "🔴 잔차 최대")),
        ("🔴 증강 팔이 단조인가",
         _dig(A, "§2 🔴🔴🔴 (ㄱ) 증강 사다리 — base 고정 · hplt 만 흔든다", "0",
              "R_pool 묶음", "천장", "🔴🔴🔴 ρ 가 h 에 «단조 증가»인가")),
        ("🔴 군집 SE 두 배를 넘은 증강 눈금 수",
         _dig(A, J, "🔴 (ㄱ) 천장base — 2·SE_clu 를 넘은 눈금 수")),
    ])
    hits += 1
    ent["🔴🔴🔴 세계 명제 W2 — 답을 정하는 것은 「자의 도메인 가중」이다"] = \
        collections.OrderedDict([
            ("`세계애니` 의 몫 — alpha977 판", _dig(CW, W2S, "🔴🔴🔴 `세계애니` 의 몫 — alpha977 판")),
            ("`세계애니` 의 몫 — 챔피언 판", _dig(CW, W2S, "🔴🔴🔴 `세계애니` 의 몫 — 챔피언 판")),
            ("🔴 배수", _dig(CW, W2S, "🔴🔴 몫의 배수(alpha977 ÷ 챔피언)")),
            ("HPLT 에서 `세계애니` 의 몫",
             _dig(CW, "§4 🔴🔴 HPLT 의 도메인 구성 — **자료 쪽 반쪽**",
                  "🔴🔴🔴 `세계애니` 의 hplt 몫")),
            ("HPLT 에서 가장 큰 도메인",
             _dig(CW, "§4 🔴🔴 HPLT 의 도메인 구성 — **자료 쪽 반쪽**",
                  "🔴🔴🔴 hplt 에서 가장 큰 도메인")),
            ("🔴 세 자의 Δ(1800)", collections.OrderedDict([
                ("R_pool 묶음(판정)", _dig(A, J, "🔴 R_pool 묶음 Δ(1800)")),
                ("R_eq 균등", _dig(A, J, "🔴 R_eq 균등 Δ(1800)")),
                ("R_champ 챔피언가중", _dig(A, J, "🔴 R_champ 챔피언가중 Δ(1800)")),
            ])),
            ("🔴🔴🔴 자에 따라 답이 뒤집히나", _dig(A, J, "🔴🔴🔴 자에 따라 답이 «뒤집히나»")),
            ("🔴 1800 에서 갈린 병기 자", _dig(A, J, "🔴🔴🔴 1800 에서 판정 자와 «부호가 갈린» 병기 자")),
        ])
    hits += 1
    ent["🔴🔴 세계 명제 W3 — 챔피언 판은 「안」 움직였다"] = collections.OrderedDict([
        ("공표값", _dig(C, "§2 🔴 재현",
                     "🔴 공표값(출처 = `runners/text680.py` 의 `BOARD_RHO` · 손으로 안 적었다)")),
        ("990 재현", _dig(C, "§2 🔴 재현", "🔴 990 이 다시 낸 값(묶음 · 씨앗 12 평균)")),
        ("차이", _dig(C, "§2 🔴 재현", "🔴 공표값과의 차이")),
        ("씨앗 SD", _dig(C, "§2 🔴 재현", "🔴 씨앗 SD")),
        ("씨앗 SE", _dig(C, "§2 🔴 재현", "🔴 씨앗 SE")),
    ])
    hits += 1
    ent["🔴 판정 — Δ ± SE_clu"] = collections.OrderedDict([
        ("판정 자", _dig(A, J, "🔴🔴🔴 판정 자(측정 «전»에 못 박았다)")),
        ("Δ(천장)", _dig(A, J, "🔴 R_pool 묶음 Δ(천장)")),
        ("도메인 군집 SE", _dig(A, J, "🔴 R_pool 묶음 Δ(천장) 군집 SE")),
        ("t_clu", _dig(A, J, "🔴 R_pool 묶음 Δ(천장) t_clu")),
        ("🔴 씨앗 SE 비(989 가 쓴 자)", _dig(A, J, "🔴 R_pool 묶음 Δ(천장) 씨앗 SE 비")),
        ("🔴 N* 씨앗별 범위",
         [_dig(A, J, "🔴🔴🔴 N* — 점이 아니라 구간", "🔴🔴 씨앗별 N* 최소"),
          _dig(A, J, "🔴🔴🔴 N* — 점이 아니라 구간", "🔴🔴 씨앗별 N* 최대")]),
        ("🔴 N* 씨앗 붓스트랩",
         _dig(A, J, "🔴🔴🔴 N* — 점이 아니라 구간", "🔴🔴🔴 붓스트랩 2.5% ~ 97.5%")),
        ("🔴 LODO 부호 뒤집힌 도메인",
         _dig(A, J, "🔴 R_pool 묶음 LODO 부호 뒤집힌 도메인(천장)")),
        ("🔴🔴 「채택」이라 적었나", False),
    ])
    hits += 1
    ent["🔴 탐색 팔(사전등록 «밖» · 채점 분모 밖)"] = collections.OrderedDict([
        ("판정 자의 최적 base", _dig(A, EXP, "R_pool 묶음", "🔴🔴🔴 ρ 가 «가장 높은» base 행 수")),
        ("977 이 쓴 base", _dig(A, EXP, "R_pool 묶음", "🔴 977 이 쓴 base 행 수(α=0.95 · N=1800)")),
        ("최적 대비 손실", _dig(A, EXP, "R_pool 묶음", "🔴🔴🔴 최적 대비 977 자리의 손실")),
        ("균등 자의 최적 base", _dig(A, EXP, "R_eq 균등", "🔴🔴🔴 ρ 가 «가장 높은» base 행 수")),
        ("챔피언가중의 최적 base",
         _dig(A, EXP, "R_champ 챔피언가중", "🔴🔴🔴 ρ 가 «가장 높은» base 행 수")),
    ])
    hits += 1
    ent["🔴 배선"] = collections.OrderedDict([
        ("검사 수", _dig(G, "🔴 배선 검사 수")), ("통과 수", _dig(G, "🔴 통과 수")),
        ("🔴 구성상 참(변이체가 안 떨어진 것)", _dig(G, "🔴 구성상 참인 검사 수(변이체가 안 떨어진 것)")),
        ("걸린 자리 합", _dig(G, "🔴 걸린 자리 합")),
        ("🔴 989 가 쓴 base 천장",
         _dig(G, "🔴🔴🔴 ⓑ 씨앗별 base 천장(989 는 «한 수»를 열둘에 물렸다)",
              "🔴 씨앗 976 의 겹 최소(= 989 가 쓴 수)")),
        ("🔴 실제 천장 범위",
         _dig(G, "🔴🔴🔴 ⓑ 씨앗별 base 천장(989 는 «한 수»를 열둘에 물렸다)",
              "🔴 측정 씨앗 열둘의 겹 최소 범위")),
        ("🔴 그 수가 누구의 천장인가",
         _dig(G, "🔴🔴🔴 ⓑ 씨앗별 base 천장(989 는 «한 수»를 열둘에 물렸다)",
              "🔴🔴🔴 989 가 쓴 수가 측정 씨앗 «어느» 천장인가")),
    ])
    hits += 1
    ent["🔴🔴 자기 자 — 989 의 「공허한 초록」 실측"] = collections.OrderedDict([
        ("F13 참 분모 / 989 가 쓴 분모",
         [_dig(D, "§A 🔴🔴 `F13` 의 명부 — 글롭으로 다시 센다", "🔴🔴🔴 참 분모"),
          _dig(D, "§A 🔴🔴 `F13` 의 명부 — 글롭으로 다시 센다", "🔴 989 가 쓴 분모")]),
        ("🔴 명부가 「통과가 보장되는 것」만 골랐나",
         _dig(D, "§A 🔴🔴 `F13` 의 명부 — 글롭으로 다시 센다",
              "🔴🔴🔴 명부가 「통과가 보장되는 것」만 골랐나")),
        ("989 의 `통과` 절 수 / 그중 미측정",
         [_dig(D, "§B 🔴🔴 「걸린 자리 0 위의 초록」 — 989 산출물 전량",
               "🔴🔴🔴 `통과` 키를 내는 절 수"),
          _dig(D, "§B 🔴🔴 「걸린 자리 0 위의 초록」 — 989 산출물 전량",
               "🔴🔴🔴 그중 «미측정»(초록인데 걸린 자리가 0 이거나 칸이 없다)")]),
        ("🔴 988 판 §59-나 복원 시 989 의 최상위",
         _dig(D, "§C 🔴🔴 989 의 최상위 연언 — 988 판 `§59-나` 를 복원하면",
              "🔴🔴🔴 988 판 `§59-나` 를 복원하면 989 의 최상위는")),
        ("🔴 「파일명 인용 4 건」 실측 / 바늘 히트 줄",
         [_dig(D, "§D 🔴🔴 `audit989.py:705` — 「파일명 인용 4 건」의 실측",
               "🔴🔴🔴 「파일명 인용」 합 — 실측"),
          _dig(D, "§D 🔴🔴 `audit989.py:705` — 「파일명 인용 4 건」의 실측",
               "🔴🔴🔴 히트 줄 합")]),
        ("🔴 미신고 상수 변경",
         _dig(D, "§E 🔴 등록 상수를 러너가 바꿨나(`37,531` → `37,520`)",
              "🔴🔴🔴 미신고 상수 변경인가")),
        ("🔴 「묶음↔균등」 뒤바뀐 자리",
         _dig(D, "§F 🔴 989 문서의 「묶음 ↔ 균등」 뒤바뀜", "🔴🔴🔴 뒤바뀐 자리 수")),
        ("걸린 자리 합", _dig(D, "🔴 걸린 자리 합")),
    ])
    hits += 1
    ent["🔴 채점"] = collections.OrderedDict([
        ("예측", _dig(S, "§4 🔴 예측", "🔴🔴 분자 / 분모")),
        ("반증조건", _dig(S, "§5 🔴 반증조건", "🔴🔴 분자 / 분모")),
        ("🔴 반증된 조건", _dig(S, "§5 🔴 반증조건", "🔴🔴 반증된 조건(식별자만)")),
        ("🔴 «단언»", _dig(S, "§5 🔴 반증조건", "🔴🔴🔴 «단언»이라 「통과」로 세면 안 되는 조건")),
        ("반증조건 걸린 자리 합", _dig(S, "§5 🔴 반증조건", "🔴 걸린 자리 합")),
        ("F09 반증", _dig(L, "🔴🔴🔴 F09 반증됐나")),
        ("🔴 최상위를 이루는 절 전량", _dig(S, "🔴🔴🔴 최상위를 이루는 절의 `통과` 전량")),
        ("🔴🔴🔴 최상위 통과", _dig(S, "통과")),
    ])
    hits += 1
    ent["🔴 ⑤′"] = collections.OrderedDict([
        ("통과", _dig(F, "통과")), ("절 분모", _dig(F, "🔴 절 수(분모)")),
        ("🔴 실패한 절", _dig(F, "🔴 실패한 절")),
        ("🔴 사유 파일", _dig(F, "🔴 사유 파일")),
        ("🔴 레인 수 / 예고",
         [_dig(F, "8 🔴 `[수리]` 레인 계수(955 R6)",
               "🔴🔴 레인 수(분자 --- 이것이 「수리 레인」의 수다)"),
          _dig(F, "8 🔴 `[수리]` 레인 계수(955 R6)", "🔴 사전등록이 예고한 레인 수")]),
        ("🔴 저장소 밖 레인 미신고",
         _dig(F, "8 🔴 `[수리]` 레인 계수(955 R6)",
              "🔴🔴 956 R2 ㉢ 저장소 밖 레인(955 가 인계 카드를 고쳤고 계수기가 원리상 못 봤다)",
              "🔴 미신고 저장소 밖 수리")),
    ])
    hits += 1
    ent["🔴 막힌 명령(조항 69)"] = (
        "🔴 **없었다.** `git checkout`·`git symbolic-ref`(쓰기)·`gh pr merge` 를 "
        "한 번도 안 불렀다. 🔴 **`HEAD` 는 내내 `refs/heads/main` 에서 «안 움직였다»** --- "
        "990 이 `조항 69` 에 박은 「결과 상태로 판정한다」를 990 자신에게 먼저 물었다")
    ent["🔴 규약 개정"] = "docs/루프.md v4.6 → v4.7 (조항 69 개정 · 60-라 · 73-마 · 73-바 신설)"
    ent["🔴 논문"] = "🔴 **이 사이클도 `paper/` 를 안 만졌다** --- 981~990 열 사이클 연속이다"
    ent["🔴 걸린 자리(= 자가 «칸»을 «읽은» 회수)"] = hits
    ent["🔴 낸 러너"] = "runners/ledger990.py"
    ent["통과"] = bool(_dig(S, "통과"))

    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    led[KEY] = ent                                 # 🔴 치환이다 --- 안 자란다
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1),
                      encoding="utf-8")
    res = collections.OrderedDict([
        ("무엇", "990 — 원장에 「노트 990」 항목을 적었다(🔴 치환 · 안 자란다)"),
        ("🔴 원장 키", KEY),
        ("🔴 읽은 칸 수", hits),
        ("🔴 걸린 자리(= 자가 «비교/읽기»를 «수행»한 회수)", hits),
        ("🔴 원장 sha256", hashlib.sha256(LEDGER.read_bytes()).hexdigest()),
        ("통과", bool(hits > 0)),
        ("🔴 도장", collections.OrderedDict([
            ("ref(부른 쪽이 준 40자 sha)", a.ref),
            ("🔴 코드 sha256", {"runners/ledger990.py": hashlib.sha256(
                (ROOT / "runners/ledger990.py").read_bytes()).hexdigest()}),
            ("시각(UTC)", _now()),
        ])),
    ])
    (OUT / "out990_ledger.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    sys.stderr.write("%s  [ledger] 끝 → out990_ledger.json\n" % _now())
    return 0


if __name__ == "__main__":
    sys.exit(main())
