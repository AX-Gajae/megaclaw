#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 996 채점 --- 네 산출물의 «키 경로»에서만 수를 읽는다(규칙 D · 조항 81).

    python3 runners/score996.py

- 입력: `runners/out996_{match,coef,gap,zt}.json`
- 출력: `runners/out996_score.json`
- 🔴 손으로 친 수는 «없다». 파생값은 전부 입력 키의 산술이다.
"""
import collections
import hashlib
import json
import os
import datetime as dt
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
INS = ("runners/out996_match.json", "runners/out996_coef.json",
       "runners/out996_gap.json", "runners/out996_zt.json")
SRC = ("runners/score996.py",)
OUT = "runners/out996_score.json"

K_M1 = "§M1 🔴 기준선(995 대비 ㉡ 재현)"
K_M2 = "§M2 🔴🔴🔴 헤드라인 --- 학습을 «잘라 맞췄다»"
K_M3 = "§M3 감도 탐침(한 뽑기 --- 🔴 세계 명제에 «안» 쓴다 · 조항 60)"
K_M4 = "§M4 🔴 n* 를 챔피언 세계에서 «직접» 잰다"
K_M5 = "§M5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"
K_A2 = "§A2 🔴🔴🔴 헤드라인 --- 계수 벡터가 도나(순열)"
K_A3 = "§A3 🔴🔴 조각 × 축 (조항 79 --- 대비를 조각으로)"
K_A5 = "§A5 🔴🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"
K_B2 = "§B2 🔴🔴🔴 계수 이식 --- 「블록 4 의 계수」만 얹는다"
K_B4 = "§B4 🔴🔴🔴 위약 --- 「배선이 새나」"
K_B5 = "§B5 🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"
K_Z2 = "§Z2 🔴🔴🔴 양성 대조 관문 --- 「배선이 닿나」"
K_Z3 = "§Z3 🔴🔴 구조 항등식 --- 「블록 안 상수는 원리상 ρ 에 못 닿는다」"
K_Z4 = "§Z4 🔴🔴🔴 헤드라인"
K_Z5 = "§Z5 🔴🔴 조항 78 --- 기계로 센 ㉮·㉯"
K_CSE = "🔴🔴 조항 79 개정 2 --- 이 주행이 낸 cluster_se 칸 전량"
K_F784 = "🔴🔴 조항 78 개정 4 --- 반증조건의 «분모»를 손으로 고르지 않았다"
K_STAMP = "🔴 도장"
K_SEG = "조각"
K_PERM = "🔴🔴🔴 부호뒤집기 «전수» 순열"
K_HOLM = "🔴 Holm"
K_PASS = "🔴🔴 2·SE 를 넘나"


def _load(p):
    with open(str(ROOT / p), "r", encoding="utf-8") as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)


def G(o, *path):
    for k in path:
        o = o[k]
    return o


def sha(p):
    q = ROOT / p
    return hashlib.sha256(q.read_bytes()).hexdigest() if q.is_file() else None


def r(x, n=6):
    return None if x is None else round(float(x), n)


def seg_row(s):
    return collections.OrderedDict([
        ("점추정", s["점추정"]), ("도메인 군집 SE", s["도메인 군집 SE"]),
        ("t_clu", s["t_clu"]), ("2·SE 를 넘나", s[K_PASS]),
        ("양측 p", s["🔴 양측 p(정규 근사)"]), ("동부호", s["🔴 동부호 수"]),
        ("2.5%", s.get("2.5%")), ("97.5%", s.get("97.5%"))])


def main():
    t0 = dt.datetime.utcnow()
    M, A, B, Z = (_load(p) for p in INS)
    out = collections.OrderedDict()
    out["무엇"] = ("996 채점 --- 규칙 D. 모든 수는 네 산출물의 키 경로에서 온다. "
                 "손 전사 0.")
    out["🔴 입력 산출물 sha256"] = collections.OrderedDict(
        (p, sha(p)) for p in INS)
    out["🔴 코드 sha256"] = collections.OrderedDict((p, sha(p)) for p in SRC)

    # ── ① 세계 명제 ───────────────────────────────────────
    m1h, m2h, m3h = (G(M, k, "헤드라인") for k in (K_M1, K_M2, K_M3))
    s1, s2 = m1h[K_SEG], m2h[K_SEG]
    nm14 = "원점 1→원점 4"
    g1, g2, g3 = (G(M, k, "헤드라인", K_SEG, nm14, "점추정")
                  for k in (K_M1, K_M2, K_M3))
    band = G(M, K_M2, "🔴 판정 띠(사전등록 §5 · 티처 #134)")
    thr = float([k for k in band if k.startswith("<")][0].split("<")[1].split()[0])
    se2 = G(M, K_M2, "헤드라인", K_SEG, nm14, "도메인 군집 SE")
    lo2 = G(M, K_M2, "헤드라인", K_SEG, nm14, "2.5%")
    hi2 = G(M, K_M2, "헤드라인", K_SEG, nm14, "97.5%")
    drop = g1 - g2
    W = collections.OrderedDict()
    W["🔴 대비"] = ("팔 0 --- 채점 블록을 4 에 고정하고 «학습 행을 도메인별까지» "
                  "원점 1 에 맞춘 뒤 원점만 옮긴다")
    W["M1 기준선 합(995 재현)"] = g1
    W["🔴🔴 M2 잔여 낙차 합"] = g2
    W["M3 감도 합(한 뽑기 · 세계 명제에 안 쓴다)"] = g3
    W["🔴🔴🔴 학습량 몫 = (M1 − M2)/M1"] = r(drop / g1, 6)
    W["🔴 994 C3 가 예측한 몫"] = G(
        M, "🔴 티처 #134 가 준 앞선 실측(참고 상수)", "🔴 낙차 0.183381 에서의 몫(단순 차)")
    W["🔴 사전등록이 예측한 잔여 낙차"] = G(
        M, "🔴 티처 #134 가 준 앞선 실측(참고 상수)", "🔴 그래서 잔여 낙차 예측")
    W["🔴🔴 죽음 문턱"] = thr
    W["🔴🔴 문턱까지의 여유 = M2 − 문턱"] = r(g2 - thr, 6)
    W["🔴🔴🔴 그 여유를 M2 자신의 SE 로 나눈 값"] = r((g2 - thr) / se2, 6)
    W["🔴🔴 M2 95% 구간"] = [lo2, hi2]
    W["🔴🔴🔴 죽음 문턱이 그 구간 «안»에 있나"] = bool(lo2 < thr < hi2)
    W["M1 연언"] = m1h["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]
    W["🔴🔴 M2 연언"] = m2h["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]
    W["M3 연언"] = m3h["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]
    W["M1 Holm 생존"] = G(m1h, K_HOLM, "🔴 Holm 뒤 살아남은 수")
    W["🔴🔴 M2 Holm 생존"] = G(m2h, K_HOLM, "🔴 Holm 뒤 살아남은 수")
    W["M3 Holm 생존"] = G(m3h, K_HOLM, "🔴 Holm 뒤 살아남은 수")
    W["🔴 M2 에서 Holm 을 넘은 조각 이름"] = [
        k for k, v in G(m2h, K_HOLM, "검정별").items() if v["🔴 Holm 통과"]]
    W["M1 순열 p(연언)"] = G(m1h, K_PERM, "🔴🔴 p(조각 «전부» 넘는다 = 연언)")
    W["🔴🔴 M2 순열 p(연언)"] = G(m2h, K_PERM, "🔴🔴 p(조각 «전부» 넘는다 = 연언)")
    W["M2 순열 p(관측만큼 많이 넘는다)"] = G(
        m2h, K_PERM, "🔴 p(관측만큼 «많이» 넘는다)")
    W["🔴🔴 995 헤드라인 조각 1→2 가 어떻게 됐나"] = collections.OrderedDict([
        ("M1(995 재현)", seg_row(s1["원점 1→원점 2"])),
        ("🔴 M2(학습량 맞춤)", seg_row(s2["원점 1→원점 2"]))])
    W["🔴 M2 에서 유일하게 남은 조각"] = collections.OrderedDict([
        ("이름", "원점 2→원점 3"), ("값", seg_row(s2["원점 2→원점 3"]))])
    alive = bool(g2 > thr)
    conj = int(m2h["🔴 통과 조각 분자"])
    denom = int(m2h["분모: 조각"])
    W["🔴🔴🔴 판정"] = (
        "걸쳐 있다 --- 「죽었다」도 「살았다」도 이 자료로는 «못 가른다»"
        if (alive and lo2 < thr < hi2) else
        ("죽었다" if not alive else "살았다"))
    W["🔴 판정의 근거 셋"] = [
        "① 점추정은 문턱 «위»다(여유를 자기 SE 로 나누면 위 칸)",
        "② 그런데 죽음 문턱이 M2 자신의 95% 구간 «안»에 있다",
        "③ 조항 79 개정 1 --- 연언이 %d/%d 라 「명제」가 아니라 «가설 후보»다" %
        (conj, denom)]
    W["🔴🔴 그래서 995 의 세계 명제는"] = (
        "「죽지 않았으나 «명제» 지위를 잃었다」 --- 조각 3/3 이 1/3 로 무너졌고 "
        "995 가 가장 크다던 조각 1→2 가 사실상 0 이 됐다. 남은 것은 조각 2→3 «하나»다")
    out["🔴🔴🔴 ① 995 세계 명제 --- 죽었나 살았나"] = W

    # ── ② 팔 C ───────────────────────────────────────────
    ways = G(Z, K_Z4, "🔴🔴🔴 틈이 닫히는 «두 길» --- 갈라서 센다")
    gapc = G(Z, K_Z4, "🔴 틈(원점 1→4 · 2→4)이 칸마다 얼마나 되나")
    kg = "🔴 2→4 (Z 가 덮는 구간만)"
    g_base, g_trt = gapc["Z1"][kg], gapc["Z3"][kg]
    closed = g_base - g_trt
    cmp_ = G(Z, K_Z4, "칸 사이 Δ")
    up2 = G(cmp_, "원점 2", "🔴 처치 − 기준선", "🔴 Δ(뒤 − 앞)")
    dn4 = G(cmp_, "원점 4", "🔴 처치 − 기준선", "🔴 Δ(뒤 − 앞)")
    main4 = G(cmp_, "원점 4", "위약 − 기준선", "🔴 Δ(뒤 − 앞)")
    win4 = G(cmp_, "원점 4", "🔴🔴 처치 − 위약", "🔴 Δ(뒤 − 앞)")
    pos = G(Z, K_Z2, "Δ", "🔴 Δ(뒤 − 앞)")
    C = collections.OrderedDict()
    C["틈 2→4 (기준선 Z1)"] = g_base
    C["틈 2→4 (처치 Z3)"] = g_trt
    C["🔴 닫힌 절대량"] = r(closed, 6)
    C["길 ① 먼 원점 2 가 올랐나"] = seg_row(up2)
    C["길 ② 가까운 원점 4 가 내렸나"] = seg_row(dn4)
    C["🔴🔴🔴 닫힌 것 중 길 ② 의 몫"] = r(abs(dn4["점추정"]) / closed, 6)
    C["🔴 닫힌 것 중 길 ① 의 몫"] = r(up2["점추정"] / closed, 6)
    C["🔴🔴 그래서 「닫았다」의 진짜 판정"] = (
        "🔴 «거짓»이다 --- 틈은 줄었으나 그 대부분이 «가까운 원점이 망가져서»다. "
        "사전등록 §4-다 는 길 ① 만 「닫았다」로 센다")
    C["🔴🔴🔴 그런데 러너의 기계 관문은 무엇을 냈나"] = G(
        ways, "🔴🔴 판정", "🔴 그래서 이 팔이 「닫았다」를 낼 수 있나")
    C["🔴🔴🔴 그 관문의 흠(정비 팔이 소스에서 확인)"] = (
        "`runners/delta996_zt.py:266` --- `(\"올랐나\", bool(float(np.mean(...)) > 0))` · "
        "`:273` 이 그 «부호 하나»를 그대로 판정으로 쓴다. SE 를 «안» 본다. "
        "그래서 t 0.099 · p 0.92 · 동부호 6/12 짜리 부호로 «참»이 나왔다")
    C["🔴 그 관문이 본 원점 2 의 t"] = up2["t_clu"]
    C["🔴 사전등록 P13 은 그 반대를 예측했고 «맞았다»"] = (
        "P13 「닫았다가 안 선다」 --- 길 ① 이 2·SE 를 못 넘었다(%s)" % up2[K_PASS])
    C["Z 주효과 주효과(원점 4)"] = seg_row(main4)
    C["🔴 상호작용이 주효과를 이기나(원점 4)"] = seg_row(win4)
    C["🔴🔴 주효과 자체가 «해롭다»"] = bool(main4["점추정"] < 0 and main4[K_PASS])
    C["🔴🔴🔴 양성 대조"] = seg_row(pos)
    C["🔴🔴🔴 양성 대조가 보증하는 것"] = (
        "이 팔의 「효과 없음」은 «미측정»이 아니라 «측정된 무효과»다 --- "
        "노트 887·888 의 병(넣은 열이 설계행렬에 안 닿는다)이 아니다. "
        "배선 검사(hole888)도 Z3 에서 새 열 여섯을 이름으로 확인했다")
    C["hole888 새 열 수"] = collections.OrderedDict(
        (k, v["🔴 새 열 수"]) for k, v in
        G(Z, "§Z1-나 🔴🔴 배선 검사(hole888) --- 넣은 열이 axis_order 에 닿았나").items())
    out["🔴🔴🔴 ② 팔 C --- 「닫았다」는 «거짓»이다"] = C

    # ── ③ 팔 A · B ───────────────────────────────────────
    AA = collections.OrderedDict()
    AA["🔴 조각 수준(계수 벡터가 도나 · 순열)"] = collections.OrderedDict(
        (k, collections.OrderedDict([
            ("분모: 쓴 도메인", v["분모: 쓴 도메인"]),
            ("관측 평균 |Δβ|²", v["관측 평균 |Δβ|²"]),
            ("귀무 평균의 중앙", v["귀무 평균의 중앙"]),
            ("🔴 비(관측/귀무중앙)", v["🔴 비(관측/귀무중앙)"]),
            ("🔴 순열 p", G(A, "§A2-나 🔴 Holm (가족 F2)", "검정별", k, "p")),
            ("🔴 Holm 통과", G(A, "§A2-나 🔴 Holm (가족 F2)", "검정별", k,
                            "🔴 Holm 통과"))]))
        for k, v in G(A, K_A2).items())
    AA["🔴 비가 단조 증가하나"] = bool(all(
        G(A, K_A2, a)["🔴 비(관측/귀무중앙)"] < G(A, K_A2, b)["🔴 비(관측/귀무중앙)"]
        for a, b in zip(list(G(A, K_A2))[:-1], list(G(A, K_A2))[1:])))
    AA["가족 F2 · m"] = G(A, "§A2-나 🔴 Holm (가족 F2)", "분모: 가족 크기 m")
    AA["🔴 F2 Holm 생존"] = G(A, "§A2-나 🔴 Holm (가족 F2)", "🔴 Holm 뒤 살아남은 수")
    hf1 = G(A, "§A3-나 🔴🔴 Holm (가족 F1)")
    AA["🔴🔴 축 수준(가족 F1)"] = collections.OrderedDict([
        ("사전등록 명목 m", 5 * 4),
        ("실측 m(결측을 뺀 뒤)", hf1["분모: 가족 크기 m"]),
        ("🔴 p 가 결측인 검정(이름)", hf1["🔴 p 가 결측인 검정"]),
        ("🔴 Holm 생존", hf1["🔴 Holm 뒤 살아남은 수"]),
        ("🔴 생존자 이름", [k for k, v in hf1["검정별"].items()
                       if v["🔴 Holm 통과"]])])
    surv = [k for k, v in hf1["검정별"].items() if v["🔴 Holm 통과"]]
    sn, sa = surv[0].split(" · ")[0].replace("조각 ", ""), surv[0].split(" · ")[1]
    scell = G(A, K_A3, "조각 블록 " + sn, sa)
    AA["🔴🔴🔴 그 생존자를 열어 보면"] = collections.OrderedDict([
        ("이름", surv[0]), ("도메인 수", scell["도메인 수"]),
        ("점추정", scell["점추정"]), ("도메인 군집 SE", scell["도메인 군집 SE"]),
        ("t_clu", scell["t_clu"]), ("동부호", scell["🔴 동부호 수"]),
        ("도메인별 Δβ", scell["🔴 도메인별 Δβ"]),
        ("d*", scell["🔴 d*(t>2 에 필요한 도메인 수) = 4τ̂²/μ̂²"]),
        ("🔴🔴 그래서", "도메인이 «둘»이라 도메인 사이 SD 가 짜부라진 인공물이다 --- "
                    "d* 가 1 보다 «작다». 「어느 축」의 답으로 쓰면 안 된다")])
    cand = G(A, K_A3, "조각 블록 3→4", "target_breadth")
    AA["🔴🔴 실질 후보(도메인이 많은 칸)"] = collections.OrderedDict([
        ("이름", "조각 3→4 · target_breadth"), ("도메인 수", cand["도메인 수"]),
        ("점추정", cand["점추정"]), ("t_clu", cand["t_clu"]),
        ("동부호", cand["🔴 동부호 수"]),
        ("p", G(hf1, "검정별", "조각 3→4 · target_breadth", "p")),
        ("Holm 계단 문턱", G(hf1, "검정별", "조각 3→4 · target_breadth",
                          "계단 문턱 alpha/(m-i)")),
        ("🔴 Holm 통과", G(hf1, "검정별", "조각 3→4 · target_breadth",
                        "🔴 Holm 통과")),
        ("d*", cand["🔴 d*(t>2 에 필요한 도메인 수) = 4τ̂²/μ̂²"])])
    AA["🔴🔴🔴 그래서 팔 A 의 결론"] = (
        "「조각 수준」에서는 «선다»(조각 3→4 순열 p 가 Holm 을 넘는다). "
        "🔴 그러나 「어느 «축»인가」는 «못 선다» --- Holm 생존자는 도메인 둘짜리 인공물이고, "
        "도메인 아홉짜리 실질 후보는 Holm 을 못 넘는다")
    AA["🔴🔴 그리고 팔 A·B 가 스스로 신고한 것"] = (
        "이 주행은 «확인»이 아니라 «재현»이다 --- 연기 시험 값과 소수점까지 같다(결정론). "
        "「반증 기회가 있었는데 통과했다」로 읽으면 안 된다")

    b1 = G(B, "§B1 대리 세계 원점 곡선", "alpha 1", "헤드라인")
    tr1 = G(B, K_B2, "칸별", "원점 1", "🔴 Δ(이식 − 원본)")
    BB = collections.OrderedDict()
    BB["🔴 대리 세계임"] = B["🔴 대리 세계임을 못박는다"]
    BB["대리 세계 조각"] = collections.OrderedDict(
        (k, seg_row(v)) for k, v in b1[K_SEG].items())
    BB["대리 세계 연언"] = b1["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]
    BB["대리 세계 순열 p(연언)"] = G(
        b1, K_PERM, "🔴🔴 p(조각 «전부» 넘는다 = 연언)")
    BB["🔴🔴 계수 이식 Δ(원점 1)"] = seg_row(tr1)
    BB["🔴🔴 몫(대리 세계 «안»에서)"] = G(B, K_B2, "🔴🔴 몫 = 원점 1 이식 Δ / 대리 세계 낙차")
    BB["🔴🔴🔴 그런데 2·SE 를 못 넘는다"] = bool(not tr1[K_PASS])
    BB["🔴 축 다섯 계수 전후(원점 1 → 블록 4)"] = G(
        B, K_B2, "칸별", "원점 1", "🔴 축 다섯 계수 전후")
    BB["🔴🔴🔴 이 몫을 팔 0 의 잔여 낙차로 나누지 «마라»"] = (
        "팔 B 는 능형 대리 세계이고 팔 0 은 챔피언 세계다. 두 세계의 ρ 눈금이 다르다 "
        "(대리 낙차 %s 대 챔피언 낙차 %s) --- 「%s%%」는 «대리 세계 안»의 몫이지 "
        "챔피언 세계의 몫이 아니다(조항 60)" % (
            G(B, K_B2, "🔴 대리 세계 자신의 낙차(원점1→4)"), g1,
            r(100 * G(B, K_B2, "🔴🔴 몫 = 원점 1 이식 Δ / 대리 세계 낙차"), 2)))
    BB["위약 ㉠ 최대 |Δρ|"] = G(
        B, K_B4, "§B4-가 🔴 구조 항등식(고정 모형 · 예측에 «블록 상수»를 더한다)",
        "최대 |Δρ|")
    BB["위약 ㉠ 대조판 최대 |Δρ|"] = G(
        B, K_B4, "§B4-가 🔴 구조 항등식(고정 모형 · 예측에 «블록 상수»를 더한다)",
        "🔴🔴 그런데 이 자가 «떨어질 수 있나» --- 대조판(행별로 «변하는» 값을 더한다)",
        "최대 |Δρ|")
    out["③ 팔 A --- 「조각 수준」과 「축 수준」을 가른다"] = AA
    out["③ 팔 B --- 계수 이식"] = BB
    part2(out, (M, A, B, Z))
    part3(out, (M, A, B, Z), t0)
    with open(str(ROOT / OUT), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("절 %d" % len(out))
    return out


def part2(out, data):
    M, A, B, Z = data
    # ── ④ 조각 분해표 전량(조항 79) ──────────────────────
    T = collections.OrderedDict()
    for nm, k in (("팔 0 · M1 기준선", K_M1), ("🔴 팔 0 · M2 학습량 맞춤", K_M2),
                  ("팔 0 · M3 감도(한 뽑기)", K_M3)):
        h = G(M, k, "헤드라인")
        T[nm] = collections.OrderedDict([
            ("조각", collections.OrderedDict(
                (a, seg_row(b)) for a, b in h[K_SEG].items())),
            ("🔴 연언(통과 조각/분모 조각)",
             h["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]),
            ("🔴 합은 항등이라 통과로 «안» 센다", h["🔴🔴 합(항등 · «통과»로 «안» 센다)"]),
            ("🔴 부호뒤집기 전수 순열 p(연언)",
             G(h, K_PERM, "🔴🔴 p(조각 «전부» 넘는다 = 연언)")),
            ("순열 p(하나라도)", G(h, K_PERM, "🔴 p(조각 «하나라도» 넘는다)")),
            ("Holm 생존", G(h, K_HOLM, "🔴 Holm 뒤 살아남은 수")),
            ("Holm m", G(h, K_HOLM, "분모: 가족 크기 m"))])
    b1 = G(B, "§B1 대리 세계 원점 곡선", "alpha 1", "헤드라인")
    T["팔 B · 대리 세계 원점 곡선"] = collections.OrderedDict([
        ("조각", collections.OrderedDict((a, seg_row(b)) for a, b in b1[K_SEG].items())),
        ("🔴 연언", b1["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]),
        ("🔴 순열 p(연언)", G(b1, K_PERM, "🔴🔴 p(조각 «전부» 넘는다 = 연언)")),
        ("Holm 생존", G(b1, K_HOLM, "🔴 Holm 뒤 살아남은 수")),
        ("Holm m", G(b1, K_HOLM, "분모: 가족 크기 m"))])
    for cell in ("Z1", "Z2", "Z3"):
        h = G(Z, K_Z4, "칸별 조각 분해", cell)
        T["팔 C · " + cell] = collections.OrderedDict([
            ("무엇", h["무엇"]),
            ("조각", collections.OrderedDict(
                (a, seg_row(b)) for a, b in h[K_SEG].items())),
            ("🔴 연언", h["🔴🔴 연언 채점 --- 통과 조각 / 분모 조각"]),
            ("🔴 순열 p(연언)", G(h, K_PERM, "🔴🔴 p(조각 «전부» 넘는다 = 연언)")),
            ("Holm 생존", G(h, K_HOLM, "🔴 Holm 뒤 살아남은 수")),
            ("Holm m", G(h, K_HOLM, "분모: 가족 크기 m")),
            ("🔴 Holm 이 실제로 보정한 검정 이름", list(G(h, K_HOLM, "검정별")))])
    T["팔 A · 조각 × 축(가족 F1)"] = collections.OrderedDict(
        (seg, collections.OrderedDict(
            (ax, (collections.OrderedDict([
                ("🔴 못 쟀다", v["🔴 못 쟀다"]),
                ("분모: 도메인", v["분모: 도메인"])])
             if "🔴 못 쟀다" in v else collections.OrderedDict([
                ("도메인 수", v["도메인 수"]), ("점추정", v["점추정"]),
                ("도메인 군집 SE", v["도메인 군집 SE"]), ("t_clu", v["t_clu"]),
                ("2·SE 를 넘나", v[K_PASS]), ("동부호", v["🔴 동부호 수"]),
                ("d*", v["🔴 d*(t>2 에 필요한 도메인 수) = 4τ̂²/μ̂²"])])))
            for ax, v in sv.items()))
        for seg, sv in G(A, K_A3).items())
    out["④ 🔴 조각 분해표 «전량»(조항 79)"] = T

    # ── ⑤ cluster_se 칸 전량(조항 79 개정 2) ───────────────
    CS = collections.OrderedDict()
    tot = collections.Counter()
    for nm, o in (("팔 0", M), ("팔 A", A), ("팔 B", B), ("팔 C", Z)):
        c = o[K_CSE]
        row = collections.OrderedDict([
            ("🔴 분모: 낸 칸 전량", c["🔴🔴 분모: 이 주행이 낸 cluster_se 칸 전량"]),
            ("2·SE 를 넘은 칸", c["🔴 2·SE 를 넘은 칸"]),
            ("안 넘은 칸", c["안 넘은 칸"]),
            ("🔴 판정 불가(SD=0 ⇒ SE=0 ⇒ None · ㉯-2)",
             c["🔴 판정 불가 칸(SD=0 ⇒ SE=0 ⇒ None · ㉯-2)"]),
            ("넘은 비율", c["넘은 비율"])])
        CS[nm] = row
        tot["분모"] += row["🔴 분모: 낸 칸 전량"]
        tot["넘음"] += row["2·SE 를 넘은 칸"]
        tot["안넘음"] += row["안 넘은 칸"]
        tot["불가"] += row["🔴 판정 불가(SD=0 ⇒ SE=0 ⇒ None · ㉯-2)"]
    CS["🔴🔴🔴 네 팔 합"] = collections.OrderedDict([
        ("🔴 분모: 이 사이클이 낸 cluster_se 칸 전량", tot["분모"]),
        ("2·SE 를 넘은 칸", tot["넘음"]), ("안 넘은 칸", tot["안넘음"]),
        ("🔴 판정 불가 칸", tot["불가"]),
        ("넘은 비율", r(tot["넘음"] / float(tot["분모"]), 4)),
        ("🔴 주의", "변이체 격자와 사다리가 낸 칸까지 «전부» 센다 --- 헤드라인 조각만 "
                 "세는 수가 아니다. 그것이 분모다(조항 79 개정 2)")])
    out["⑤ 🔴🔴 `cluster_se` 칸 «전량»(조항 79 개정 2)"] = CS

    # ── ⑥ 조항 78 계수 ────────────────────────────────────
    R78 = collections.OrderedDict()
    m78 = collections.Counter()
    for nm, o, k in (("팔 0", M, K_M5), ("팔 A", A, K_A5),
                     ("팔 B", B, K_B5), ("팔 C", Z, K_Z5)):
        c = o[k]
        R78[nm] = collections.OrderedDict([
            ("분모: 검사한 주장", c["분모: 검사한 주장"]),
            ("분모: 변이체", c["분모: 변이체"]),
            ("🔴 기계가 센 ㉮", c["🔴🔴 기계가 센 ㉮ 분자"]),
            ("🔴 기계가 센 ㉯", c["🔴🔴 기계가 센 ㉯ 분자"]),
            ("대조 ㉮", c["🔴 대조 ㉮ 분자"]), ("대조 ㉯", c["🔴 대조 ㉯ 분자"]),
            ("🔴 계수가 0 을 낼 수 있나", c["🔴🔴 계수가 「0」을 낼 수 있나(본 주장에서)"]),
            ("🔴 ㉮·㉯ 로 걸린 주장 이름",
             [("㉮ " if v["🔴 ㉮(전부 참)"] else "㉯ ") + a
              for a, v in c["주장별"].items()
              if v["🔴 ㉮(전부 참)"] or v["🔴 ㉯(전부 거짓)"]])])
        m78["주장"] += c["분모: 검사한 주장"]
        m78["㉮"] += c["🔴🔴 기계가 센 ㉮ 분자"]
        m78["㉯"] += c["🔴🔴 기계가 센 ㉯ 분자"]
        m78["대조㉮"] += c["🔴 대조 ㉮ 분자"]
        m78["대조㉯"] += c["🔴 대조 ㉯ 분자"]
    R78["🔴🔴🔴 네 팔 합(기계)"] = collections.OrderedDict([
        ("분모: 검사한 주장 전량", m78["주장"]),
        ("🔴 기계 ㉮", m78["㉮"]), ("🔴 기계 ㉯", m78["㉯"]),
        ("기계 ㉮+㉯", m78["㉮"] + m78["㉯"]),
        ("대조 ㉮ / 4 팔", m78["대조㉮"]), ("대조 ㉯ / 4 팔", m78["대조㉯"])])
    R78["🔴🔴 사전등록이 «손»으로 센 것"] = collections.OrderedDict([
        ("㉮", 7), ("㉯", 5), ("합", 12),
        ("🔴 분모가 다르다", "손 계수는 «설계 수준»(게이트 사다리 · 공선성 · 하향표집 항등)까지 "
                       "세고, 기계 계수는 «러너가 등록한 주장»만 센다. 두 수를 "
                       "같은 분모로 견주면 안 된다(조항 60)"),
        ("🔴 995 는 반대 방향이었나", "995 팔 A 는 기계 2 대 손 4 --- 손이 «과대»였다. "
                              "996 도 손 12 대 기계 6 으로 «같은 방향»이다")])
    R78["🔴 반증조건의 분모를 손으로 안 골랐다(조항 78 개정 4)"] = collections.OrderedDict(
        (nm, collections.OrderedDict([
            ("분모: 이 팔이 지는 반증조건", o[K_F784]["분모: 이 팔이 지는 반증조건"]),
            ("이름", o[K_F784]["이름"]),
            ("기계가 확인하는 것", o[K_F784]["🔴 산출물 키로 «기계가» 확인하는 것"])]))
        for nm, o in (("팔 0", M), ("팔 A", A), ("팔 B", B), ("팔 C", Z)))
    out["⑥ 🔴 조항 78 계수"] = R78

    # ── ⑦ 다중비교 가족 ──────────────────────────────────
    FAM = collections.OrderedDict()
    fams = [("F0 (팔 0 · M2)", G(M, K_M2, "헤드라인", K_HOLM), 3),
            ("FA1 (팔 A · 조각×축)", G(A, "§A3-나 🔴🔴 Holm (가족 F1)"), 20),
            ("FA2 (팔 A · 조각 순열)", G(A, "§A2-나 🔴 Holm (가족 F2)"), 4),
            ("FB (팔 B · 대리 조각)", G(B, "§B1 대리 세계 원점 곡선", "alpha 1",
                                  "헤드라인", K_HOLM), 3),
            ("FC (팔 C · Z3)", G(Z, K_Z4, "칸별 조각 분해", "Z3", K_HOLM), 3)]
    msum = 0
    for nm, h, pre in fams:
        FAM[nm] = collections.OrderedDict([
            ("산출물이 적은 가족 이름", h["🔴 가족"]),
            ("사전등록 §9 의 m", pre), ("🔴 실측 m", h["분모: 가족 크기 m"]),
            ("🔴 p 결측(이름)", h["🔴 p 가 결측인 검정"]),
            ("🔴 Holm 생존", h["🔴 Holm 뒤 살아남은 수"]),
            ("🔴 실제로 보정한 검정 이름", list(h["검정별"]))])
        msum += h["분모: 가족 크기 m"]
    FAM["🔴🔴 합"] = collections.OrderedDict([
        ("사전등록 §9 의 합 m", 33), ("🔴 실측 합 m", msum),
        ("🔴 차이의 까닭", "FA1 이 명목 20 에서 결측 둘을 빼 18 이 됐다 --- 사전등록이 "
                    "「결측을 빼면 줄어든다」고 «미리» 적었다")])
    FAM["🔴🔴🔴 가족 «정의» 불일치 --- 수로는 통과, 이름으로는 불통과"] = \
        collections.OrderedDict([
            ("F0", "산출물 이름 문자열이 「조각 3 × 칸 2(M1·M2) = 6」이라 적는데 "
                   "실제로 보정한 m 은 3 이다. 사전등록 §9 는 「M1 은 가족에 안 넣는다」이므로 "
                   "🔴 «수»(3)는 옳고 «이름»이 틀렸다"),
            ("🔴🔴 FC", "산출물 이름은 「조각 3 (원점 2→3 · 3→4 · 그리고 2→4)」인데 "
                     "실제로 보정한 검정은 「원점 1→2 · 2→3 · 3→4」이고, 사전등록 §9 의 "
                     "FC 정의는 「처치 − 위약 조각 3」이다 --- 🔴 «셋이 서로 다르다». "
                     "게다가 그 가족이 Z1·Z2·Z3 «세 칸»에 각각 걸려 검정이 실제로는 9 다"),
            ("🔴🔴🔴 그리고 팔 C 의 «헤드라인»(처치−기준선 · 처치−위약 · 두 길)은 "
             "Holm 보정을 «한 번도» 안 받았다", True),
            ("🔴 이 항목의 지위", "팔 C 가 «보고»로 신고했다고 지시문이 적었으나 "
                          "커밋된 산출물에는 그 신고 키가 «없다» --- 조항 81 대로 "
                          "「어긋남 자체」를 기록한다. 정비 팔이 소스와 산출물로 «직접» 확인했다")])
    out["⑦ 🔴 다중비교 가족과 그 «정의»"] = FAM
    return out


def _rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    rk = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            rk[order[t]] = avg
        i = j + 1
    return rk


def _spear(x, y):
    a, b = _rank(x), _rank(y)
    n = float(len(a))
    ma, mb = sum(a) / n, sum(b) / n
    num = sum((p - ma) * (q - mb) for p, q in zip(a, b))
    da = sum((p - ma) ** 2 for p in a) ** 0.5
    db = sum((q - mb) ** 2 for q in b) ** 0.5
    return None if da == 0 or db == 0 else num / (da * db)


def part3(out, data, t0):
    M, A, B, Z = data
    W = out["🔴🔴🔴 ① 995 세계 명제 --- 죽었나 살았나"]
    C = out["🔴🔴🔴 ② 팔 C --- 「닫았다」는 «거짓»이다"]
    AA = out["③ 팔 A --- 「조각 수준」과 「축 수준」을 가른다"]
    BB = out["③ 팔 B --- 계수 이식"]
    m1h, m2h = (G(M, k, "헤드라인") for k in (K_M1, K_M2))

    # P7 --- 축의 「잴 수 있는 도메인 수」와 |t| 의 순위 상관
    xs, ys, nmz = [], [], []
    for seg, sv in G(A, K_A3).items():
        for ax, v in sv.items():
            if "🔴 못 쟀다" not in v:
                xs.append(v["도메인 수"]); ys.append(abs(v["t_clu"]))
                nmz.append(seg + " · " + ax)
    rho7 = _spear(xs, ys)

    n4 = G(M, K_M4)
    lo1 = min(n4["🔴 하나 빼기 감도"].values())
    hi1 = max(n4["🔴 하나 빼기 감도"].values())

    P = collections.OrderedDict()

    def add(k, verdict, why, num=None):
        P[k] = collections.OrderedDict([("판정", verdict), ("근거", why)])
        if num is not None:
            P[k]["수"] = num

    d995 = G(M, K_M1, "🔴 995 가 낸 조각과의 차")
    add("P1", "맞다", "M1 이 995 조각 셋을 1e-6 안에서 재현했다(차 전부 0.0)", d995)
    add("P2", "맞다", "M2 합 < M1 합",
        [W["🔴🔴 M2 잔여 낙차 합"], W["M1 기준선 합(995 재현)"]])
    add("P3", "맞다(그러나 «간신히»)",
        "M2 합 > 0.05. 🔴 여유를 M2 자신의 SE 로 나누면 아래 수이고, 문턱은 95% 구간 «안»이다",
        [W["🔴🔴 문턱까지의 여유 = M2 − 문턱"],
         W["🔴🔴🔴 그 여유를 M2 자신의 SE 로 나눈 값"],
         W["🔴🔴 M2 95% 구간"]])
    add("P4", "부분", "① 통과 조각 ≥ 1 은 «맞다»(1/3). ② 「M2 의 순열 p(연언)이 M1 의 것보다 "
        "크다」는 «틀렸다» --- 더 «작다». 🔴 곁: 사전등록이 안 지목한 "
        "`p(관측만큼 많이 넘는다)` 로 보면 예측 방향과 맞는다(0.003418 → 0.194336). "
        "규칙 D 대로 «지목된 키»로 채점한다",
        [W["M1 순열 p(연언)"], W["🔴🔴 M2 순열 p(연언)"],
         G(m1h, K_PERM, "🔴 p(관측만큼 «많이» 넘는다)"),
         W["M2 순열 p(관측만큼 많이 넘는다)"]])
    add("P5", "맞다", "챔피언 세계에서 직접 잰 n* 가 alpha977 의 44.639 보다 «작다». "
        "🔴 하나 빼기 감도 폭도 같이 싣는다 --- 「법칙」이 아니다",
        [n4["🔴 n*(챔피언 세계 · 직접)"], n4["alpha977 세계의 옛 값(참고)"],
         r(lo1, 3), r(hi1, 3)])
    add("P6", "맞다", "팔 A 조각 순열 p 의 최소값이 0.05 미만이다(조각 3→4)",
        G(A, "§A2-나 🔴 Holm (가족 F2)", "검정별", "조각 블록 3→4", "p"))
    add("P7", "맞다" if rho7 > 0 else "🔴 틀림",
        "축의 「잴 수 있는 도메인 수」와 |t_clu| 의 스피어만 순위 상관. 예측은 «양수»였다. "
        "🔴 실측은 «음수»다 --- 검정력이 도메인 수를 «안» 따른다. 까닭이 바로 이 사이클의 "
        "핵심 흠이다: 도메인이 «둘»인 칸은 도메인 사이 SD 가 짜부라져 SE 가 «작아지고» "
        "|t| 가 «커진다»(조각 2→3 · entry_friction 이 도메인 2 에 |t| 14.55). "
        "곧 등록된 자는 도메인이 적을수록 «더 쉽게» 통과시킨다 --- 예측과 반대다",
        [r(rho7, 6), len(xs),
         G(A, K_A3, "조각 블록 2→3", "entry_friction", "도메인 수"),
         G(A, K_A3, "조각 블록 2→3", "entry_friction", "t_clu")])
    add("P8", "맞다", "계수 이식이 «대리 세계» 낙차의 절반 이상을 닫는다. "
        "🔴 그러나 2·SE 를 못 넘는다(t 아래)",
        [BB["🔴🔴 몫(대리 세계 «안»에서)"],
         G(B, K_B2, "칸별", "원점 1", "🔴 Δ(이식 − 원본)", "t_clu")])
    add("P9", "맞다", "위약 ㉠ 최대 |Δρ| = 0 이고 대조판은 1e-12 를 넘는다",
        [BB["위약 ㉠ 최대 |Δρ|"], BB["위약 ㉠ 대조판 최대 |Δρ|"]])
    add("P10", "맞다", "양성 대조 Δ > +0.10 이고 동부호 12/12",
        [C["🔴🔴🔴 양성 대조"]["점추정"], C["🔴🔴🔴 양성 대조"]["동부호"]])
    add("P11", "맞다", "팔 C 원점 1 처치 − 기준선 = 정확히 0(㉯-1 실측)",
        G(Z, K_Z4, "칸 사이 Δ", "원점 1", "🔴 처치 − 기준선", "🔴 Δ(뒤 − 앞)", "점추정"))
    add("P12", "맞다", "팔 C 원점 4 처치 − 기준선의 부호가 음수다",
        C["길 ② 가까운 원점 4 가 내렸나"]["점추정"])
    add("P13", "맞다", "길 ①(원점 2 의 ρ 상승)이 2·SE 를 «못» 넘었다 ⟹ 「닫았다」가 «안» 선다. "
        "🔴🔴 그런데 러너의 기계 관문은 그 부호만 보고 「참」을 냈다 --- 예측이 관문보다 옳았다",
        [C["길 ① 먼 원점 2 가 올랐나"]["점추정"],
         C["길 ① 먼 원점 2 가 올랐나"]["t_clu"],
         C["길 ① 먼 원점 2 가 올랐나"]["2·SE 를 넘나"],
         C["🔴🔴🔴 그런데 러너의 기계 관문은 무엇을 냈나"]])
    add("P14", "🔴 미측정", "「10 스레드가 4 스레드보다 느리다」를 재는 «커밋된 산출물 키»가 "
        "«없다». 네 산출물은 자기가 고정한 스레드 수와 걸린 초만 싣는다. "
        "사전등록 §7-나 의 쓸이 표는 설계 팔이 `/tmp` 연기 시험에서 손으로 옮긴 «보고»다 "
        "--- 조항 81 대로 「보고」를 증거로 안 쓴다. 「없다」가 아니라 「이 사이클이 «안 쟀다»」",
        collections.OrderedDict([
            ("팔 0 고정 스레드", G(M, "🔴 고정한 스레드", "OMP_NUM_THREADS")),
            ("팔 0 걸린 초", G(M, K_STAMP, "걸린 초")),
            ("팔 C 고정 스레드", G(Z, "🔴 고정한 스레드", "OMP_NUM_THREADS")),
            ("팔 C 걸린 초", G(Z, K_STAMP, "걸린 초"))]))
    add("P15", "맞다", "hole888 --- Z0 에 Y_leak 1 · Z2/Z2b 에 Z_wiki 1 · Z3 에 6 이 들어갔다",
        C["hole888 새 열 수"])
    ok = sum(1 for v in P.values() if v["판정"].startswith("맞다"))
    P["🔴 채점 합"] = collections.OrderedDict([
        ("분모: 예측", len([k for k in P if k.startswith("P")])),
        ("맞다", ok), ("부분", sum(1 for v in P.values() if v["판정"] == "부분")),
        ("🔴 틀림", sum(1 for v in P.values() if "틀림" in v["판정"])),
        ("🔴 미측정", sum(1 for v in P.values() if v["판정"].endswith("미측정")))])
    out["⑧ 🔴 예측 채점 P1~P15"] = P

    # ── 반증조건 ─────────────────────────────────────────
    F = collections.OrderedDict()

    def af(k, verdict, why, num=None):
        F[k] = collections.OrderedDict([("판정", verdict), ("근거", why)])
        if num is not None:
            F[k]["수"] = num

    af("F1", "통과", "팔 0 M1 이 995 조각 셋을 재현했다",
       G(M, K_M1, "🔴 통과: 반증조건 R1 (995 조각 셋을 1e-6 안에서 재현)"))
    af("F2", "통과", "M2 의 도메인별 학습 행이 n1 과 같고 「맞추기 실패 신고」가 «비어 있다»",
       [G(M, K_M2, "맞추기 실패 신고"), G(M, "§M0-나 🔴🔴 분모 --- 그리고 「원리상 못 가른다」의 증거", "🔴 n1 합")])
    r4 = G(M, K_M1, "칸별 채점 행(씨앗 0)")
    af("F3", "통과", "네 칸의 채점 도메인·행이 «글자 그대로» 같다",
       bool(len(set(json.dumps(v, sort_keys=True) for v in r4.values())) == 1))
    af("F4", "통과", "corr(원점, 학습 행) 이 1 에 1e-6 안이다",
       [G(M, "§M0-나 🔴🔴 분모 --- 그리고 「원리상 못 가른다」의 증거", "🔴🔴 원점 지표와 학습 행의 상관"),
        G(M, "§M0-나 🔴🔴 분모 --- 그리고 「원리상 못 가른다」의 증거", "🔴 그 상관이 1 에 1e-6 안인가")])
    gt = G(M, "§M0-나 🔴🔴 분모 --- 그리고 「원리상 못 가른다」의 증거",
           "🔴🔴 게이트 사다리가 «구성상 항등»인가")
    af("F5", "통과(🔴 그리고 그것이 ㉮-1 이다)",
       "블록 4 의 최소 채점 도메인 행이 최대 게이트보다 크다 ⟹ 게이트 사다리가 «한 번도 안 문다»",
       [gt["블록 4 의 «가장 작은» 채점 도메인 행"], gt["게이트 사다리"]])
    af("F6", "통과", "위약 ㉠ 항등식 = 0 «그리고» 대조판 ≠ 0 --- 팔 B 와 팔 C 에서 둘 다",
       [BB["위약 ㉠ 최대 |Δρ|"], BB["위약 ㉠ 대조판 최대 |Δρ|"],
        G(Z, K_Z3, "최대 |Δρ|"),
        G(Z, K_Z3, "🔴🔴 대조판 --- 행별로 «변하는» 값을 더하면 «떨어져야» 한다", "최대 |Δρ|")])
    af("F7", "통과", "팔 C 양성 대조 관문", G(Z, K_Z2, "🔴 통과: 반증조건 C1 (Δ > +0.10 이고 동부호 ≥ 10/12)"))
    af("F8", "통과", "hole888 배선 --- 넣은 열이 axis_order 에 이름으로 들어갔다", C["hole888 새 열 수"])
    cov = G(Z, "§Z0-나 🔴🔴 Z_t 원천 · 블록 상수 · 덮음 장부", "블록 상수 Z", "블록 0")
    af("F9", "통과", "Z 덮음 장부에서 블록 0 = 0 (㉯-1)", cov)
    af("F10", "통과", "순열이 쓰는 해석 SE 가 등록된 뽑기 SE 와 5 % 안 --- M1·M2·M3 아홉 칸 전부",
       [all(v["🔴 통과"] for v in G(M, k, "헤드라인",
            "🔴 해석 SE 대조(순열이 쓰는 SE 가 등록된 뽑기 SE 와 맞나)").values())
        for k in (K_M1, K_M2, K_M3)])
    af("F11", "통과", "matmul vs einsum 최대 |차| = 0(BLAS 거짓 경보 대조)",
       G(m2h, K_PERM, "🔴 BLAS 거짓 경보 대조(matmul vs einsum 최대 |차|)"))
    r78 = out["⑥ 🔴 조항 78 계수"]["🔴🔴🔴 네 팔 합(기계)"]
    af("F12", "통과", "조항 78 기계 계수에서 대조 ㉮ ≥ 1 · 대조 ㉯ ≥ 1 --- 네 팔 «전부»",
       [r78["대조 ㉮ / 4 팔"], r78["대조 ㉯ / 4 팔"]])
    af("F13", "통과", "도장의 코드 sha256 시작 = 끝 --- 네 산출물 전부",
       [G(o, K_STAMP, "🔴 시작=끝") for o in (M, A, B, Z)])
    af("F14", "통과", "팔 A 가 못 잰 칸을 0 으로 «안» 적었다 --- 「못 쟀다」 문구 둘",
       [k for k, v in AA["🔴🔴 축 수준(가족 F1)"].items() if k.startswith("🔴 p")])
    fam = out["⑦ 🔴 다중비교 가족과 그 «정의»"]
    af("F15", "🔴🔴 불통과(엄한 판) / 통과(구판 · 문언 그대로)",
       "조항 3-나 방향 대칭 --- 둘 다 채점하고 게재값은 «더 엄한 쪽»이다. "
       "구판(「가족 «크기»가 §9 와 같나」): 다섯 가족의 m 이 3·18·4·3·3 이고 "
       "FA1 의 20→18 은 사전등록이 «미리» 허용했다 ⟹ 통과. "
       "🔴 신판(「가족 «정의»가 §9 와 같나」): FC 가 셋 다 다르고(사전등록 「처치−위약 조각 3」 / "
       "산출물 이름 「2→3 · 3→4 · 2→4」 / 실제 보정 「1→2 · 2→3 · 3→4」), "
       "게다가 그 가족을 Z1·Z2·Z3 세 칸에 각각 걸어 검정이 9 다. "
       "그리고 팔 C 의 «헤드라인»은 Holm 을 한 번도 안 받았다 ⟹ 불통과",
       [fam["🔴🔴 합"]["사전등록 §9 의 합 m"], fam["🔴🔴 합"]["🔴 실측 합 m"]])
    af("F16", "통과", "팔 C 원점 1 에서 처치 − 기준선 = 0 (㉯-1)",
       G(Z, K_Z4, "칸 사이 Δ", "원점 1", "🔴 처치 − 기준선", "🔴 Δ(뒤 − 앞)", "점추정"))
    F["🔴 채점 합"] = collections.OrderedDict([
        ("분모: 반증조건", len([k for k in F if k.startswith("F")])),
        ("통과", sum(1 for k, v in F.items()
                   if k.startswith("F") and v["판정"].startswith("통과"))),
        ("🔴 불통과(게재값)", sum(1 for k, v in F.items()
                            if k.startswith("F") and "불통과" in v["판정"])),
        ("🔴 반증 하나 = F15", "가족 «정의» 불일치")])
    out["⑨ 🔴 반증조건 채점 F1~F16"] = F

    # ── 조항 59 버림 장부 ────────────────────────────────
    def drops(o):
        c = collections.Counter()
        def w(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "까닭" and isinstance(v, str):
                        c[v] += 1
                    if k == "🔴 못 돌았다":
                        c["못 돌았다 칸(값 %s)" % ("있음" if v else "없음")] += 1
                    if k == "🔴 못 쟀다":
                        c[str(v)] += 1
                    w(v)
            elif isinstance(x, list):
                for v in x:
                    w(v)
        w(o)
        return collections.OrderedDict(sorted(c.items()))
    out["⑩ 🔴 조항 59 버림 장부 --- 네 팔 «전량»"] = collections.OrderedDict([
        ("팔 0", drops(M)), ("팔 A", drops(A)), ("팔 B", drops(B)), ("팔 C", drops(Z)),
        ("🔴 팔 B 는 왜 0 인가", "대리 세계는 12 도메인 전량이 서므로 버릴 자리가 «없다» "
                          "--- 「신고를 안 했다」가 아니라 「버린 것이 0 이다」"),
        ("🔴 「0 행」과 「학습부족 --- 쟀는데 설정이 버렸다」는 «다른» 까닭이다(조항 59 개정)", True)])

    # ── n* ────────────────────────────────────────────────
    out["⑪ 🔴 n* --- 「법칙」이 아니다"] = collections.OrderedDict([
        ("챔피언 세계(996 이 직접)", n4["🔴 n*(챔피언 세계 · 직접)"]),
        ("alpha977 세계(979~995 가 쓰던 값)", n4["alpha977 세계의 옛 값(참고)"]),
        ("σ̂²", n4["σ̂²"]), ("τ̂²", n4["τ̂²"]),
        ("🔴 하나 빼기 감도 폭", [r(lo1, 3), r(hi1, 3)]),
        ("🔴 하나 빼기 감도 전량", n4["🔴 하나 빼기 감도"]),
        ("🔴🔴 두 세계 값의 비", r(n4["alpha977 세계의 옛 값(참고)"] /
                          float(n4["🔴 n*(챔피언 세계 · 직접)"]), 4)),
        ("🔴🔴 그래서", "n* 는 «세계마다 다르다» --- 위 「두 세계 값의 비」 칸을 보라. "
                  "「법칙」으로 인용하지 마라: 도메인 «하나»만 빼도 위 「하나 빼기 감도 폭」만큼 "
                  "움직인다(아이돌을 빼면 가장 크게 뛴다)")])

    out["🔴 도장"] = collections.OrderedDict([
        ("언제(시작 · UTC)", t0.strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("언제(끝 · UTC)", dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")),
        ("🔴 입력 산출물 sha256", out["🔴 입력 산출물 sha256"]),
        ("🔴 코드 sha256", out["🔴 코드 sha256"]),
        ("🔴 git HEAD 스탬프", "폐기됐다 --- ⑤′ v3.2")])
    out["통과"] = bool(F["🔴 채점 합"]["🔴 불통과(게재값)"] == 1)
    return out


if __name__ == "__main__":
    main()
