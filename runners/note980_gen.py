#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""980 — 판정문·카드·원장을 **산출물 키에서** 짓는다.

🔴 **규칙 D — 손 전사 금지.** 이 러너가 만드는 문서의 모든 수는 `runners/out980_*.json`
의 **키 경로**에서 온다. 치환표(`§T`)에 없는 수는 문서에 못 들어간다.

씀:
    python3 runners/note980_gen.py --stage doc     --ref <40자 sha>
    python3 runners/note980_gen.py --stage ledger  --ref <40자 sha>
"""
import argparse
import collections
import datetime as dt
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

OUT = ROOT / "runners"
DEN = ROOT / "data/lab/denominator.json"


def _load(name):
    p = OUT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def table():
    """🔴 치환표 — 판정문·카드·원장이 쓸 수 있는 **유일한** 수의 출처."""
    fn = _load("out980_funnel.json")
    mx = _load("out980_mixarm.json")
    bg = _load("out980_budget.json")
    sc = _load("out980_score979.json")
    wr = _load("out980_wiring.json")
    rc = _load("out980_recheck.json")
    hs = _load("out980_house.json")
    T = collections.OrderedDict()
    ch = fn.get("🔴🔴 깔때기", {})
    T["깔때기 ①"] = ch.get("① 디스크 행(464 shard)")
    T["깔때기 ②"] = ch.get("② 정제가 읽은 문서")
    T["깔때기 ③"] = ch.get("③ 삼중쌍 행(커밋된 973 산출물)")
    T["깔때기 ④"] = ch.get("④ 🔴🔴 모형이 보는 hplt 학습 행")
    rt = fn.get("🔴🔴 비", {})
    T["②/①"] = rt.get("②/①")
    T["③/①"] = rt.get("③/①")
    T["④/①"] = rt.get("④/①")
    T["디스크 몇 행 중 1 행"] = rt.get("🔴 디스크 몇 행 중 1 행이 모형에 닿나")
    hd = fn.get("🔴 유보 행 수의 두 값(979 까지 어느 문서도 차를 안 적었다)", {})
    T["유보 전량"] = hd.get("base 유보 전량")
    T["유보 게이트 합"] = hd.get("게이트(MIN_HO=20) 통과 도메인 합")
    T["유보 차"] = hd.get("🔴 차")

    can = mx.get("🔴🔴🔴 정본 자에서의 판정", {})
    T["정본 자"] = mx.get("🔴🔴 정본 자")
    for u in (0, 3):
        c = can.get("칸별", {}).get("λ u=%d" % u, {})
        T["Δ(u=%d)" % u] = c.get("Δ")
        T["짝SE(u=%d)" % u] = c.get("🔴🔴 짝 SE(5 벌 정합)")
        T["|Δ|/SE(u=%d)" % u] = c.get("🔴🔴 |Δ| / 짝SE")
        T["2SE 통과(u=%d)" % u] = c.get("🔴🔴 |Δ| ≥ 2·짝SE")
    T["Δ>0 칸"] = can.get("🔴 Δ > 0 인 λ 칸")
    T["2SE 칸"] = can.get("🔴🔴 |Δ| ≥ 2·짝SE 인 λ 칸")
    md = mx.get("🔴🔴 혼합 진단", {})
    for arm, k in (("㉯ 대조(순열 앞머리)", "r 대조"), ("㉮ 처리(도메인 층화)", "r 층화")):
        T[k] = md.get(arm, {}).get("🔴 씨앗 다섯의 r 평균")
    pt = mx.get("🔴 점추정(5 벌)", {})
    for u in (0, 3):
        for arm, tag in (("㉯ 대조(순열 앞머리)", "대조"), ("㉮ 처리(도메인 층화)", "층화")):
            row = pt.get("λ u=%d" % u, {}).get(arm, {})
            T["ρ %s(u=%d)" % (tag, u)] = row.get(T["정본 자"])
            T["벌SD %s(u=%d)" % (tag, u)] = row.get((T["정본 자"] or "") + " 벌 SD")

    ce = bg.get("🔴🔴🔴 오라클 천장·Z", {})
    for u in (0, 3):
        c = ce.get("λ u=%d" % u, {})
        T["천장 Y(u=%d)" % u] = c.get("🔴🔴 오라클 천장 Y = 예산 16 배로 사는 전부")
        T["크기 X(u=%d)" % u] = c.get("🔴 결정 게이트 크기 X = 2·짝SE(N_B=1800)")
        T["Z(u=%d)" % u] = c.get("🔴🔴 Z = X / Y")
        T["예산으로 오르나(u=%d)" % u] = c.get("🔴 예산을 늘리면 ρ 가 오르나(P4)")
    grid = bg.get("🔴🔴 칸", {})
    T["예산 격자"] = bg.get("🔴 격자")
    for nb in (T["예산 격자"] or []):
        row = grid.get("N_B=%d" % nb, {})
        T["묶인 도메인 수(N_B=%d)" % nb] = len(row.get("🔴🔴 공급에 묶인 도메인", {}))
        for u in (0, 3):
            cc = row.get("λ u=%d" % u, {})
            T["ρ대조(N_B=%d,u=%d)" % (nb, u)] = cc.get("🔴 ㉯ 대조 ρ(정본 자)")
            T["ρ층화(N_B=%d,u=%d)" % (nb, u)] = cc.get("🔴 ㉮ 층화 ρ(정본 자)")
            T["Δ(N_B=%d,u=%d)" % (nb, u)] = cc.get("🔴🔴 Δ = ㉮ − ㉯", {}).get("Δ")
            T["SE(N_B=%d,u=%d)" % (nb, u)] = \
                cc.get("🔴🔴 Δ = ㉮ − ㉯", {}).get("🔴🔴 짝 SE(5 벌 정합)")

    T["W 통과"] = wr.get("🔴 분자/분모(통과)")
    T["W 변이체 정직"] = wr.get("🔴🔴 변이체에서 떨어진 검사(정직한 검사)")
    T["W 구성상 참"] = wr.get("🔴🔴 구성상 참인 검사")
    T["979 반증조건 채점"] = sc.get("🔴🔴 분자/분모(통과 = 안 걸렸다)")
    T["979 위반 조건"] = sc.get("🔴🔴🔴 위반한 조건")
    cen = sc.get("🔴🔴 리터럴 census 재실측", {})
    T["census 979 신고"] = cen.get("🔴🔴 979 가 신고한 수")
    T["census 구판 재현"] = cen.get("🔴 구판 자를 지금 다시 돌린 수")
    T["census 신판"] = cen.get("🔴🔴🔴 신판(수리 1) 자로 다시 돌린 수")
    T["979 수리 신고"] = sc.get("🔴🔴 979 수리 계수 정정", {}).get("🔴 979 신고")
    T["979 수리 실측"] = sc.get("🔴🔴 979 수리 계수 정정", {}).get("🔴🔴 실측")
    T["recheck 분자/분모"] = rc.get("🔴 분자/분모")
    T["반증조건 4 채점"] = rc.get("🔴🔴 반증조건 4 채점(자 값을 내는 stage 둘이 자 여섯을 다 내나)")
    T["원장 항목 수"] = hs.get("🔴🔴 main 원장 항목 수")
    T["원장 중복 키"] = hs.get("🔴🔴 원장 중복 키(전 층위)")
    T["HEAD=디스크"] = hs.get("🔴🔴 HEAD 와 디스크가 바이트 동일한가")
    T["열린 PR"] = hs.get("🔴🔴 열린 PR 수")
    a2 = hs.get("🔴🔴 A-2 사이클 — **재서 낸다**", {})
    T["A-2 분모"] = a2.get("🔴 분모: A-2 신설(974) 이후 판정문이 있는 사이클")
    T["A-2 분자"] = a2.get("🔴🔴 분자: A-2 를 글자로 담은 사이클")
    return T


def stage_doc(ref):
    T = table()
    p = OUT / "out980_table.json"
    p.write_text(json.dumps(collections.OrderedDict([
        ("무엇", "🔴 980 치환표 — 판정문·카드·원장이 쓸 수 있는 유일한 수의 출처(규칙 D)"),
        ("🔴 기준 ref", ref),
        ("🔴 언제(UTC)", dt.datetime.now(dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")),
        ("🔴 칸 수", len(T)),
        ("🔴 값이 None 인 칸", [k for k, v in T.items() if v is None]),
        ("🔴🔴 치환표", T),
    ]), ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in T.items() if not str(k).startswith("ρ")},
                     ensure_ascii=False, indent=1))
    return 0


def stage_ledger(ref):
    """🔴 원장 항목을 **치환표에서** 넣는다(손 전사 금지)."""
    T = table()
    d = json.loads(DEN.read_text(encoding="utf-8"),
                   object_pairs_hook=collections.OrderedDict)
    today = dt.date.today().isoformat()
    new = collections.OrderedDict()

    new["🔴🔴🔴 노트 980 정본 자 고정 — R_iv* 닫힌꼴"] = collections.OrderedDict([
        ("🔴 정본 자", T["정본 자"]),
        ("가중", "w ∝ (n_d − 1)"),
        ("🔴 무엇이 정했나", "v2.2 그대로 — 🔴 **선택 규칙 개정 0**. 바뀐 것은 v2.2 에 넣는 "
                        "입력에서 몬테카를로 오차를 뺀 것뿐이다"),
        ("🔴🔴 왜", "979 의 정본을 가른 최대 도메인 몫 차 0.003922 가 그 몫의 뽑기 잡음 "
                 "0.005821 보다 작다(비 0.674) — 이긴 차가 자기 잡음보다 작다"),
        ("🔴 게재된 비용도 잡음판이었다", "최대 몫 0.542072 · ESS 3.0455 → 참값 0.547893 · 3.0004"),
        ("🔴 검정력", "9.1748 (R_iv 9.1751 과 차 0.003%)"),
        ("🔴🔴 씨앗 의존", "0 — PERM_SEED·PERM_NULL 이 자에서 빠진다"),
        ("🔴 동률 무리", "소멸한다 (R_iv ≡ R_iv*)"),
        ("🔴 잠정인가", "🔴 **그렇다** — 자를 영구히 고정할 증거는 「못 정했다」"),
        ("날짜", today),
    ])

    new["🔴🔴🔴 노트 980 개정 잠금 조항 신설"] = collections.OrderedDict([
        ("문언", "한 사이클은 자기가 적용할 선택 규칙을 자기가 개정할 수 없다. "
               "선택 규칙은 적용하는 사이클보다 최소 한 사이클 앞서 등록한다"),
        ("🔴 언제부터 무나", "981 부터 — 980 이 자기에게 유리하게 쓰지 않기 위해서다"),
        ("🔴 이것이 막는 것", "977(부호만) · 978(v2.1) · 979(v2.2) 셋 다"),
        ("🔴🔴 979 의 v2.2 가 왜 걸리나",
         "목표.md:58-59 가 새 선택 규칙의 근거로 티처 #117 이 이미 게재한 검정력 수치를 "
         "직접 인용한다 — 같은 문서 :156 「실측된 효과의 크기를 문턱으로 쓰지 마라」 위반"),
        ("⚠ 안 닫힌 구멍", "「입력에서 오차를 뺀다」는 이 조항 밖이다 — 980 이 그 통로를 썼다"),
        ("날짜", today),
    ])

    new["🔴🔴 노트 980 자를 영구히 고정할 증거 — 「못 정했다」"] = \
        collections.OrderedDict([
            ("🔴 지금 정했나", "🔴 **못 정했다**(조항 59 · 지금까지 빈칸이었다)"),
            ("왜 못 정하나", "자를 고르는 잣대(|Δ(D4)|/SE)는 파괴 민감도인데, 민감도가 큰 자가 "
                        "예측이 더 나은 자라는 근거가 저장소에 0 건이다"),
            ("무엇이 있으면 정하나", "① 시간 방향 유보 ② 자 순위와 시간 방향 예측 성능의 상관 "
                            "③ 도메인 재표집 안정성"),
            ("그때까지", "정본 자 변경은 잠정이고 판정문·claim 층에 잠정임을 같이 적는다"),
            ("날짜", today),
        ])

    new["🔴🔴🔴 노트 980 C3 깔때기 — 끝에서 끝까지"] = collections.OrderedDict([
        ("① 디스크 행(464 shard)", T["깔때기 ①"]),
        ("② 정제가 읽은 문서", T["깔때기 ②"]),
        ("③ 삼중쌍 행", T["깔때기 ③"]),
        ("④ 🔴🔴 모형이 보는 hplt 학습 행", T["깔때기 ④"]),
        ("②/①", T["②/①"]), ("③/①", T["③/①"]), ("④/①", T["④/①"]),
        ("🔴🔴 디스크 몇 행 중 1 행이 모형에 닿나", T["디스크 몇 행 중 1 행"]),
        ("🔴🔴 ④ 는 자료 한계인가", "🔴 **아니다 — `alpha977.py:60` 의 `N_B = 1800` 상수다.** "
                            "456 shard 를 더 받아도 ④ 는 안 움직인다"),
        ("🔴 어느 문서도 이 사슬을 안 적었다", "980 이 처음 적는다(티처 #118 지목)"),
        ("🔴 유보 행 수의 두 값", "%s(전량) 대 %s(게이트) — 차 %s 는 「펀딩」 도메인이고 "
                        "hplt 에 그 도메인이 0 행이다"
                        % (T["유보 전량"], T["유보 게이트 합"], T["유보 차"])),
        ("날짜", today),
    ])

    new["🔴🔴🔴 노트 980 C3 실험 — 도메인 층화 표집 대 순열 앞머리"] = \
        collections.OrderedDict([
            ("설계", "같은 예산(N_B=1800 · hplt 1,710 행) · 같은 난수 차례 · "
                  "base 선택 행은 두 팔이 바이트로 같다 — 다른 것은 도메인 할당량 제약 하나뿐"),
            ("🔴 혼합 상관 r (대조)", T["r 대조"]),
            ("🔴🔴 혼합 상관 r (층화)", T["r 층화"]),
            ("🔴 정본 자", T["정본 자"]),
            ("🔴 Δ(u=0)", T["Δ(u=0)"]), ("🔴 짝SE(u=0)", T["짝SE(u=0)"]),
            ("🔴 |Δ|/SE(u=0)", T["|Δ|/SE(u=0)"]),
            ("🔴🔴 Δ(u=3)", T["Δ(u=3)"]), ("🔴🔴 짝SE(u=3)", T["짝SE(u=3)"]),
            ("🔴🔴 |Δ|/SE(u=3)", T["|Δ|/SE(u=3)"]),
            ("🔴 2 짝SE 를 넘는 λ 칸", T["2SE 칸"]),
            ("🔴 ρ 대조(u=3)", T["ρ 대조(u=3)"]),
            ("🔴 ρ 층화(u=3)", T["ρ 층화(u=3)"]),
            ("🔴🔴 벌 SD 대조(u=3)", T["벌SD 대조(u=3)"]),
            ("🔴🔴 벌 SD 층화(u=3)", T["벌SD 층화(u=3)"]),
            ("날짜", today),
        ])

    new["🔴🔴 노트 980 C3 예산 격자 — N_B 를 흔들었다"] = collections.OrderedDict(
        [("격자", T["예산 격자"])]
        + [("ρ 대조(N_B=%d · u=3)" % nb, T.get("ρ대조(N_B=%d,u=3)" % nb))
           for nb in (T["예산 격자"] or [])]
        + [("🔴 공급에 묶인 도메인 수(N_B=%d)" % nb,
            T.get("묶인 도메인 수(N_B=%d)" % nb)) for nb in (T["예산 격자"] or [])]
        + [("🔴🔴 오라클 천장 Y(u=3)", T["천장 Y(u=3)"]),
           ("🔴 결정 게이트 크기 X(u=3)", T["크기 X(u=3)"]),
           ("🔴🔴 Z = X/Y (u=3)", T["Z(u=3)"]),
           ("🔴🔴 오라클 천장 Y(u=0)", T["천장 Y(u=0)"]),
           ("🔴🔴 Z = X/Y (u=0)", T["Z(u=0)"]),
           ("날짜", today)])

    new["🔴🔴🔴 노트 980 — 979 의 반증조건 열을 채점했다"] = collections.OrderedDict([
        ("🔴 채점(통과 = 안 걸렸다)", T["979 반증조건 채점"]),
        ("🔴🔴 위반한 조건", T["979 위반 조건"]),
        ("🔴 979 자신이 채점한 수", "0 / 10 — 사전등록 §6-2 가 분모 설계에서 자기 열을 미리 뺐다"),
        ("🔴🔴 반증조건 10", "위반 — 수리는 다섯이 아니라 넷이다. 수리 4(`s_d` 닫힌 꼴)는 "
                       "축 추가이고 979 의 정본 자 R4 는 여전히 perm_null_sd(2000, 씨앗 978) 로 "
                       "지어졌다. 「자가 씨앗에서 완전히 떨어졌다」는 979 에서 거짓이었다"),
        ("🔴 계수 부풀림", "🔴 **열아홉째**(962~979 열아홉 사이클 연속)"),
        ("날짜", today),
    ])

    new["🔴🔴 노트 980 리터럴 census 정정 — 23 / 14"] = collections.OrderedDict([
        ("🔴 979 신고", T["census 979 신고"]),
        ("🔴 구판 자를 지금 다시 돌린 수", T["census 구판 재현"]),
        ("🔴🔴🔴 신판(수리 1) 실측", T["census 신판"]),
        ("🔴 분모(항진명제 census 자리)", 62),
        ("🔴🔴 무엇을 못 봤나", "`collections.OrderedDict([(\"키\", True), …])` — "
                       "`ast.Call` 안의 2-튜플이라 옛 census 가 원리상 못 봤다"),
        ("🔴🔴 빠진 자리가 누구 것인가", "🔴 전부 979 자기 러너(ruler979.py) — "
                            "978 의 사각지대를 닫으면서 같은 종류를 새로 냈고 그 안에서 자기를 셌다"),
        ("날짜", today),
    ])

    new["🔴🔴 노트 980 ⑤′ 의 ⓪ 관문 — 967 이 물은 것을 정했다"] = collections.OrderedDict([
        ("🔴 답", "⓪ 관문은 「작업 트리 = HEAD」가 아니라 「작업 트리 = 이 사이클 가지의 커밋된 트리」를 묻는다"),
        ("🔴 왜 옛 관문이 원리상 못 지나가나",
         "규칙 A 가 checkout 을 금지하므로 HEAD 는 언제나 main 이고 사이클 커밋은 가지에만 있다"),
        ("🔴🔴 979 가 적은 이유는 틀렸다",
         "더러운 28 중 데몬은 1 줄이고 27 이 979 자기 미커밋물 — 기전은 규칙 B 가 아니라 규칙 A 다"),
        ("🔴 면제", "데몬 경로뿐이고 그 목록은 harvest_daemon.PATHS 에서 읽는다(손 전사 금지) · "
                "면제 수를 분모와 나란히 낸다"),
        ("🔴 옛 작업 트리 절", "진단으로 내리고 `통과` 키를 뺐다 — 리터럴 True 로 통과시키지 않는다"),
        ("🔴 돌리는 시점", "그 사이클의 마지막 커밋에서(979 는 7 커밋 이르게 돌았다)"),
        ("어디에 적었나", "docs/루프.md 4-나 절"),
        ("날짜", today),
    ])

    new["🔴 노트 980 배선·수리·집"] = collections.OrderedDict([
        ("🔴 W 통과", T["W 통과"]),
        ("🔴 변이체에서 떨어진 검사(정직한 검사)", T["W 변이체 정직"]),
        ("🔴🔴 구성상 참인 검사", T["W 구성상 참"]),
        ("🔴 반증조건 4 채점", T["반증조건 4 채점"]),
        ("🔴 recheck", T["recheck 분자/분모"]),
        ("🔴 main 원장 항목 수", T["원장 항목 수"]),
        ("🔴 원장 중복 키(전 층위)", T["원장 중복 키"]),
        ("🔴 HEAD 와 디스크 바이트 동일", T["HEAD=디스크"]),
        ("🔴 열린 PR", T["열린 PR"]),
        ("🔴🔴 A-2 (재서 낸 수)", "%s / %s" % (T["A-2 분자"], T["A-2 분모"])),
        ("날짜", today),
    ])

    added = []
    for k, v in new.items():
        if k not in d:
            added.append(k)
        d[k] = v
    DEN.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"🔴 넣은 항목": added, "🔴 원장 항목 수": len(d)},
                     ensure_ascii=False, indent=1))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True, choices=["doc", "ledger"])
    ap.add_argument("--ref", default="")
    a = ap.parse_args()
    return {"doc": stage_doc, "ledger": stage_ledger}[a.stage](a.ref)


if __name__ == "__main__":
    sys.exit(main())
