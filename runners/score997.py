#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""🔴 노트 997 채점기 --- `runners/out997_score.json`.

🔴 **아무것도 «다시 재지» 않는다.** 이 러너는 **커밋된 산출물의 키 경로**만 읽어
④ 판정 · ⑤ 채점(예측 18 · 반증조건 17)을 «계산»한다(조항 81).

    python3 runners/score997.py [--fiveprime runners/out997_fiveprime.json]

- 🔴 **규칙 D**: 손으로 친 수가 없다. 모든 수는 `out997_probe.json` ·
  `out997_mask.json` · `out997_gate.json` 의 키 경로에서 온다.
- 🔴 **조항 78**: 판정 칸은 «리터럴»이 아니라 위 키에서 «계산»한 불리언이다.
- 🔴 **조항 60**: 분모가 갈리는 자리(팝업 · k 팔 도메인 수)를 «나란히» 싣는다.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
OUT = "runners/out997_score.json"
SRC = ("runners/score997.py",)
INS = ("runners/out997_probe.json", "runners/out997_mask.json",
       "runners/out997_gate.json", "docs/prereg_997_unsupervised_mde.md")

K_MDE_S = "🔴🔴 MDE_s"
K_HEAD = "🔴 ㉠ 2·SE(헤드라인)"
K_INTERP = "MDE_s(선형 보간)"
K_PERMONLY = "㉡ 순열만"
K_CONJ = "㉠∧㉡ 연언"
K_T1SE = "🔴 1종 오류(2·SE 만)"
K_MONO = "🔴 힘이 δ 에 단조인가"
K_MAXPOW = "격자 안 최대 힘"
K_LASTPOW = "🔴 마지막 격자점의 힘"


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
    """조각 한 줄 --- 조항 79-1(점추정 · 등록된 자의 SE · t · 동부호)."""
    return collections.OrderedDict([
        ("점추정", s["점추정"]), ("도메인 군집 SE", s["도메인 군집 SE"]),
        ("t_clu", s["t_clu"]), ("🔴 동부호", s["🔴 동부호 수"]),
        ("🔴 2·SE 를 넘나", s["🔴🔴 2·SE 를 넘나"]),
        ("🔴 양측 p(정규 근사)", s["🔴 양측 p(정규 근사)"]),
        ("도메인 수", s["도메인 수"])])


def mde_row(pc, name, dn, doms):
    """한 설정의 `MDE` 한 줄 --- 분모(도메인 수·이름)를 «같은 자리»에 적는다(조항 60)."""
    h = G(pc, K_MDE_S if K_MDE_S in pc else "🔴🔴 MDE", K_HEAD)
    ak = "🔴 해석식 MDE_a" if "🔴 해석식 MDE_a" in pc else "해석식 MDE_a"
    a = G(pc, ak, "🔴 MDE_a")
    t1 = G(pc, "귀무 δ=0 에서 잰 것", K_T1SE) if "귀무 δ=0 에서 잰 것" in pc \
        else G(pc, "귀무 1종 오류", K_T1SE)
    lo = G(pc, "분기", "분기 문턱(측정 전에 박은 것)", "좋음") if "분기" in pc else None
    return collections.OrderedDict([
        ("설정", name),
        ("🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)", h[K_INTERP]),
        ("MDE_s(격자점)", h["🔴 MDE_s(격자점)"]),
        ("MDE_a(해석식)", a),
        ("MDE_s / MDE_a", r(h[K_INTERP] / a) if a else None),
        ("🔴 1종 오류(㉠ · δ=0)", t1),
        ("🔴 힘이 δ 에 단조인가(㉠)", h[K_MONO]),
        ("🔴🔴 분모: 잰 도메인 수", dn),
        ("🔴 분모: 도메인", doms),
        ("좋음 문턱(측정 전)", lo)])


def branch_of(x, lo, hi):
    """🔴 분기를 «계산»한다 --- 리터럴 라벨이 아니다."""
    if x is None:
        return "🔴 못 쟀다"
    if x < lo:
        return "🔴 `ρ 0.10` 아래"
    if x >= hi:
        return "🔴 `ρ 0.30` 이상"
    return "사이(0.10 ≤ MDE < 0.30)"


def main():
    ap = argparse.ArgumentParser(prog="score997.py")
    ap.add_argument("--fiveprime", default=None,
                    help="🔴 ⑤′ 산출물 --- 없으면 P16·F13 을 「미측정」으로 «적는다»(조항 59)")
    a = ap.parse_args()
    t0 = dt.datetime.now(dt.timezone.utc)
    PR = _load("runners/out997_probe.json")
    MK = _load("runners/out997_mask.json")
    GA = _load("runners/out997_gate.json")
    FP = None
    if a.fiveprime and (ROOT / a.fiveprime).is_file():
        FP = _load(a.fiveprime)

    out = collections.OrderedDict()
    out["무엇"] = ("997 채점 --- ④ 판정 · ⑤ 채점. 🔴 «측정은 안 한다»: "
                "커밋된 세 산출물의 키 경로만 읽는다(조항 81)")
    out["노트"] = GA["노트"]

    KS = ["k=8", "k=16", "k=32", "k=64", "k=128"]
    KM = G(PR, "🔴🔴🔴 MDE (자 ㉠ · 소수 라벨)")
    PF = G(PR, "🔴🔴🔴 MDE (자 ㉠ · 전량 라벨)")
    MM = G(MK, "🔴🔴🔴 MDE (자 ㉡ · 라벨 0 개 자)")
    LO = G(PR, "🔴🔴🔴 분기 · 전량 라벨", "분기 문턱(측정 전에 박은 것)", "좋음")
    HI = G(PR, "🔴🔴🔴 분기 · 전량 라벨", "분기 문턱(측정 전에 박은 것)", "나쁨")

    rows = [mde_row(MM, "🔴 ㉡ 라벨 0 개 자(가림 복원)",
                    G(MM, "분모: 도메인 d"), G(MM, "도메인")),
            mde_row(PF, "㉠ 라벨 프로브 · 전량 라벨",
                    G(PF, "분모: 도메인 d"), G(PF, "도메인"))]
    for k in KS:
        rows.append(mde_row(KM[k], "㉠ 라벨 프로브 · %s" % k,
                            G(KM[k], "분모: 잰 도메인"), G(KM[k], "도메인")))
    for row in rows:
        row["🔴🔴 분기(계산)"] = branch_of(
            row["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"], LO, HI)
    mvals = [row["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"] for row in rows]
    brs = [row["🔴🔴 분기(계산)"] for row in rows]
    g915 = G(GA, "🔴🔴 915 의 차를 잴 수 있었나", "915 의 차")

    out["①🔴🔴🔴 `MDE` 표 --- 997 의 «유일한 필수 산출»"] = collections.OrderedDict([
        ("🔴 분모: 잰 설정", len(rows)),
        ("설정별", rows),
        ("🔴🔴 `ρ 0.10` 아래인 설정 수", sum(1 for b in brs if "아래" in b)),
        ("🔴🔴 「사이 칸」 설정 수", sum(1 for b in brs if b.startswith("사이"))),
        ("🔴 `ρ 0.30` 이상인 설정 수", sum(1 for b in brs if "이상" in b)),
        ("🔴 「사이 칸」에 떨어진 설정 이름",
         [row["설정"] for row in rows if row["🔴🔴 분기(계산)"].startswith("사이")]),
        ("🔴 분기 문턱(측정 «전»에 박은 것)",
         collections.OrderedDict([("좋음", LO), ("나쁨", HI)])),
        ("🔴🔴🔴 헤드라인 판정(㉡ · 라벨 0 개 자)", rows[0]["🔴🔴 분기(계산)"]),
        ("🔴🔴🔴 헤드라인 판정(㉠ · 전량 라벨 = 판이 실제로 쓰는 꼴)",
         rows[1]["🔴🔴 분기(계산)"]),
        ("🔴 배수 ㉠전량/㉡", r(mvals[1] / mvals[0])),
        ("🔴 카드의 이분 분기표가 이 자료를 덮나",
         bool(not any(b.startswith("사이") for b in brs))),
        ("🔴 뜻", "🔴 「사이 칸」이 «비어 있지 않다» ⟹ 카드의 이분 분기표(0.10 아래 / 0.30 이상)는 "
               "«불충분»하다. 998 사전등록이 그 칸을 갈라야 한다")])

    out["②🔴🔴 915 는 «못 잴 자»로 갔다 --- 설정 전량에서"] = collections.OrderedDict([
        ("🔴 915 의 차(0.1719 SSL − 0.1708 라벨순열 바닥)", g915),
        ("🔴 분모: 잰 설정", len(rows)),
        ("설정별 MDE ÷ 915 차", collections.OrderedDict(
            (row["설정"], r(row["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"] / g915, 4))
            for row in rows)),
        ("🔴 915 가 실제로 선 자리(`k=16`)의 배수",
         G(GA, "🔴🔴 915 의 차를 잴 수 있었나", "🔴 MDE / 915 차")),
        ("🔴 가장 «유리한» 설정에서도 몇 배인가",
         r(min(mvals) / g915, 4)),
        ("🔴 그 설정 이름", rows[mvals.index(min(mvals))]["설정"]),
        ("🔴🔴 915 와 «같은 종류»의 자(㉠ 라벨 프로브) 안에서 가장 유리한 배수",
         r(min(mvals[1:]) / g915, 4)),
        ("🔴 그 설정 이름(㉠ 안)", rows[1:][mvals[1:].index(min(mvals[1:]))]["설정"]),
        ("🔴 왜 갈라 적나(조항 60)",
         "🔴 ㉡ 은 «라벨을 안 쓰는 다른 자»다. 915 가 쓴 자는 ㉠(라벨 선형 프로브)이므로 "
         "「915 가 못 쟀다」의 분모는 ㉠ 여섯이다. ㉡ 을 섞으면 분모가 바뀐다"),
        ("🔴🔴🔴 그래서 915 는", G(GA, "🔴🔴 915 의 차를 잴 수 있었나", "🔴 판정")),
        ("🔴 어느 설정에서라도 잴 수 있었나(MDE < 915 차인 설정이 있나)",
         bool(any(m < g915 for m in mvals))),
        ("🔴 뜻", "🔴 **「915 는 졌다」가 아니라 「915 는 «못 쟀다»」다.** 그 주행은 자기 "
               "잡음의 45 배 아래에 있는 차를 놓고 결론을 냈다 --- 그 차는 이 자로는 "
               "«원리상» 안 보인다")])

    pc_pf = G(PF, "힘 곡선")
    pc_mm = G(MM, "힘 곡선")

    def povw(pcv, key):
        return collections.OrderedDict((d, v[key]) for d, v in pcv.items())

    out["③🔴🔴 순열 자의 «역단조» --- 효과가 클수록 힘을 잃는다"] = \
        collections.OrderedDict([
            ("🔴 무엇", "조항 79 개정 3 이 «헤드라인 칸으로 병기»하라고 못박은 자 "
                    "(부호뒤집기 «전수» 2^d 순열)의 힘 곡선이다"),
            ("🔴 자", G(MK, "🔴 부호뒤집기 «전수» 순열", "🔴 자")),
            ("🔴 몬테카를로인가", G(MK, "🔴 부호뒤집기 «전수» 순열", "🔴 몬테카를로인가")),
            ("🔴🔴 힘 곡선 · 자 ㉠ 전량 라벨(순열만)", povw(pc_pf, "힘 ㉡ 순열만")),
            ("🔴🔴 힘 곡선 · 자 ㉡(순열만)", povw(pc_mm, "힘 ㉡ 순열만")),
            ("참고: 같은 자리의 ㉠ 2·SE 힘 · 전량 라벨", povw(pc_pf, "🔴 힘 ㉠ 2·SE")),
            ("🔴 δ=0 의 기각률(= 1종 오류) · ㉠ 전량",
             G(PF, "귀무 δ=0 에서 잰 것", "🔴 1종 오류(순열만)")),
            ("🔴 δ=0 의 기각률(= 1종 오류) · ㉡",
             G(MM, "귀무 δ=0 에서 잰 것", "🔴 1종 오류(순열만)")),
            ("🔴🔴 마지막 격자점(δ=0.80)의 힘 · ㉠ 전량",
             G(PF, K_MDE_S, K_PERMONLY, K_LASTPOW)),
            ("🔴🔴 마지막 격자점(δ=0.80)의 힘 · ㉡",
             G(MM, K_MDE_S, K_PERMONLY, K_LASTPOW)),
            ("🔴 최대 힘이 선 δ · ㉠ 전량", G(PF, K_MDE_S, K_PERMONLY, "그 δ")),
            ("🔴 최대 힘이 선 δ · ㉡", G(MM, K_MDE_S, K_PERMONLY, "그 δ")),
            ("🔴 힘이 δ 에 단조인가 --- 일곱 설정 전량", collections.OrderedDict(
                [("㉡", G(MM, K_MDE_S, K_PERMONLY, K_MONO)),
                 ("㉠ 전량", G(PF, K_MDE_S, K_PERMONLY, K_MONO))] +
                [(k, G(KM[k], "🔴🔴 MDE", K_PERMONLY, K_MONO)) for k in KS])),
            ("🔴🔴 `MDE` 를 낸 설정 수(순열 검정 단독)", sum(
                1 for v in ([G(MM, K_MDE_S, K_PERMONLY, K_INTERP),
                             G(PF, K_MDE_S, K_PERMONLY, K_INTERP)] +
                            [G(KM[k], "🔴🔴 MDE", K_PERMONLY, K_INTERP) for k in KS])
                if v is not None)),
            ("🔴 분모: 설정", len(rows)),
            ("🔴🔴 연언(㉠∧㉡)이 `MDE` 를 낸 설정 수", sum(
                1 for v in ([G(MM, K_MDE_S, K_CONJ, K_INTERP),
                             G(PF, K_MDE_S, K_CONJ, K_INTERP)] +
                            [G(KM[k], "🔴🔴 MDE", K_CONJ, K_INTERP) for k in KS])
                if v is not None)),
            ("🔴🔴🔴 헤드라인 대비 ㉡ 의 순열 `p`(조항 79 개정 3 이 요구한 칸)",
             G(MK, "🔴 부호뒤집기 «전수» 순열", "🔴🔴 p(조각 «전부» 넘는다 = 연언)")),
            ("🔴🔴 그런데 같은 대비의 `t_clu`",
             G(MK, "🔴 헤드라인 대비 ㉡ = 학습 − 난수표현", "t_clu")),
            ("🔴🔴🔴 두 자가 서로 반대를 낸다(2·SE 는 넘고 순열 p 는 0.05 를 못 넘는다)",
             bool(G(MK, "🔴 헤드라인 대비 ㉡ = 학습 − 난수표현", "🔴🔴 2·SE 를 넘나")
                  and G(MK, "🔴 부호뒤집기 «전수» 순열",
                        "🔴🔴 p(조각 «전부» 넘는다 = 연언)") > 0.05)),
            ("🔴🔴🔴 함의(원장에 «수»로 남긴다 · 조항은 «안» 건드린다)",
             "🔴 조항 79 개정 3 은 티처 #134 권고를 받아 이 순열 `p` 를 «헤드라인 칸에 "
             "반드시 병기»로 규약화했다. 997 이 그 자의 힘 곡선을 처음 쟀고, 그 힘은 "
             "δ 에 «역단조»다 --- 효과가 0 일 때 가장 많이 기각하고 효과가 커지면 0 이 "
             "된다. 🔴 **일곱 설정 전량에서 이 자로는 `MDE` 를 «못 낸다»**(격자 최대 "
             "δ=0.80 에서 힘 0.000). 🔴 **조항 개정은 이 팔의 일이 아니다 --- 조타수 몫이다**"),
            ("🔴 왜 이런가(설계 팔이 사전등록 §12 에 «측정 전»에 적어 놨다)",
             "d=12 에서 효과가 커지면 도메인을 k 개 뒤집은 부호 패턴도 `|평균| > 2·SE` 를 "
             "만족해 «발화 패턴 수»가 늘고 p 가 «올라간다». 곧 이 자는 「기각 패턴의 희소성」"
             "을 재는데, 큰 효과는 그 희소성을 «깨뜨린다»")])

    sd = G(PR, "위약 짝 · 전량 라벨", "도메인별 SD")
    tot = sum(v * v for v in sd.values())
    zsum = G(PF, "🔴 해석식 MDE_a", "z 합")
    d11 = math.sqrt(tot - sd["팝업"] ** 2) / (len(sd) - 1)
    d12 = math.sqrt(tot) / len(sd)
    kdoms = collections.OrderedDict(
        [("전량 라벨", G(PF, "도메인"))] + [(k, G(KM[k], "도메인")) for k in KS])
    out["④🔴🔴 「사이 칸」의 정체 --- 한 도메인인가. 🔴 두 분모를 «나란히»"] = \
        collections.OrderedDict([
            ("🔴 무엇", "㉠ 전량 팔의 `SE_0` 를 «누가» 만드나. 위약 짝의 도메인별 SD 에서 "
                    "«계산»한다 --- 러너가 이 칸을 «안 냈다»(조항 81: 아래 ⑪ 을 보라)"),
            ("🔴 출처 키", "runners/out997_probe.json:위약 짝 · 전량 라벨/도메인별 SD"),
            ("🔴 분모: 도메인", len(sd)),
            ("도메인별 위약 SD", sd),
            ("도메인별 SD² 몫(등가중 평균의 분산 기여)", collections.OrderedDict(
                (k, r(v * v / tot)) for k, v in
                sorted(sd.items(), key=lambda x: -x[1]))),
            ("🔴🔴🔴 팝업 하나의 몫", r(sd["팝업"] ** 2 / tot)),
            ("🔴 팝업 + 도서 둘의 몫", r((sd["팝업"] ** 2 + sd["도서"] ** 2) / tot)),
            ("🔴 팝업의 학습 라벨", G(PR, "분모", "도메인별 학습 라벨", "팝업")),
            ("🔴🔴 왜 k 팔은 팝업을 «버리나»",
             "`runners/mde997_probe.py:150` `dl = [d for d in doms if len(TR[d]) >= 2*k]` "
             "--- 학습 라벨 24 인 팝업은 `k=16` 부터 «분모 밖»이다"),
            ("🔴🔴🔴 설정별 도메인 수(분모가 갈린다 · 조항 60)",
             collections.OrderedDict((k, len(v)) for k, v in kdoms.items())),
            ("설정별 도메인 이름", kdoms),
            ("🔴🔴 두 분모를 나란히 --- 해석식 `MDE_a`", collections.OrderedDict([
                ("㉮ d=12(팝업 포함 · 러너가 실제로 낸 값)",
                 G(PF, "🔴 해석식 MDE_a", "🔴 MDE_a")),
                ("㉮ 의 `SE_0`(모의)", G(PF, "귀무 δ=0 에서 잰 것", "모의 Δ̄ 의 SD = `SE_0`")),
                ("🔴 정비 팔이 같은 키에서 «계산»한 d=12 해석 근사 `SE_0`", r(d12, 8)),
                ("🔴 그 근사가 모의 `SE_0` 와 맞나(비)",
                 r(G(PF, "귀무 δ=0 에서 잰 것", "모의 Δ̄ 의 SD = `SE_0`") / d12)),
                ("🔴🔴 ㉯ d=11(팝업 뺀 «계산» · 러너 산출물에 이 칸은 «없다»)",
                 r(zsum * d11)),
                ("🔴 ㉯ 의 `SE_0`(해석 근사)", r(d11, 8)),
                ("🔴🔴🔴 ㉮ → ㉯ 로 분기가 바뀌나",
                 [branch_of(G(PF, "🔴 해석식 MDE_a", "🔴 MDE_a"), LO, HI),
                  branch_of(zsum * d11, LO, HI)])])),
            ("🔴🔴🔴 그래서 「사이 칸」은",
             "🔴 **㉠ 전량의 「사이 칸」은 «한 도메인»이 만든다.** 팝업(학습 라벨 24)의 위약 "
             "SD 가 전량 팔 `SE_0` 분산의 대부분을 «혼자» 낸다. 팝업을 빼면 같은 자·같은 "
             "규칙에서 `MDE_a` 가 `ρ 0.10` 아래로 «넘어온다». 🔴 그리고 `k≥16` 팔은 그 "
             "도메인을 «이미» 버리고 있었다 --- 곧 표의 두 수는 «다른 분모»에서 왔다"),
            ("🔴🔴 `P02` 반전의 기전(예측은 `k=16` 이 «더 크다» 였다)",
             "🔴 `k=16`(도메인 11)이 전량(도메인 12)보다 «작은» `MDE` 를 낸 것은 "
             "「소수 라벨이 더 예민해서」가 아니라 «가장 시끄러운 도메인을 뺐기 때문»이다"),
            ("🔴 이 칸의 지위(조항 81)",
             "🔴 이 수들은 «커밋된 키»(도메인별 SD · z 합)에서 정비 팔이 «산술»로 낸 "
             "파생값이다. 러너가 낸 칸이 «아니다». 그래서 여기 «계산 자리»를 같이 적는다")])

    stp = G(MK, "🔴 조항 79 조각 — 스텝 사다리(씨앗 0)")
    stpseg = G(stp, "🔴 조각(이웃 차 + 합 · `delta996_common.seg_from`)")
    stpperm = G(stp, "🔴 부호뒤집기 «전수» 순열(조각 셋)")
    kseg = G(PR, "🔴 조항 79 조각 — k 사다리(소수 라벨 곡선)",
             "🔴 조각(`delta996_common.seg_from`)")
    kperm = G(PR, "🔴 조항 79 조각 — k 사다리(소수 라벨 곡선)",
              "🔴 부호뒤집기 «전수» 순열(조각 넷)")
    pfperm = G(PR, "🔴 부호뒤집기 «전수» 순열 · 전량 라벨")
    mkperm = G(MK, "🔴 부호뒤집기 «전수» 순열")

    def ladder(name, segs, perm, ident, dn, doms):
        keys = [k for k in segs if k != ident]
        return collections.OrderedDict([
            ("🔴 분모: 조각", len(keys)),
            ("🔴 분모: 도메인", dn), ("도메인", doms),
            ("조각별", collections.OrderedDict((k, seg_row(segs[k])) for k in keys)),
            ("⚠ 항등 합(넷째 통과로 «안» 센다 · 조항 79 개정 4)",
             seg_row(segs[ident]) if ident in segs else "없음"),
            ("🔴🔴 연언 k/k(조항 79 개정 1)", perm["🔴🔴 관측 통과 수 / 분모 조각"]),
            ("🔴 넘은 조각 수", sum(1 for k in keys if segs[k]["🔴🔴 2·SE 를 넘나"])),
            ("🔴🔴 연언인가(넘은 조각 == 분모 조각)",
             bool(sum(1 for k in keys if segs[k]["🔴🔴 2·SE 를 넘나"]) == len(keys))),
            ("🔴 순열 p(조각 «전부» 넘는다 = 연언)",
             perm["🔴🔴 p(조각 «전부» 넘는다 = 연언)"]),
            ("🔴 순열 p(조각 «하나라도» 넘는다)", perm["🔴 p(조각 «하나라도» 넘는다)"]),
            ("참고: 티처 #134 귀무 실측(하나라도 / 셋 다)",
             [G(perm, "🔴 티처 #134 의 귀무 실측(참고)", "하나라도"),
              G(perm, "🔴 티처 #134 의 귀무 실측(참고)", "셋 다")]),
            ("🔴 BLAS 거짓 경보 대조(matmul vs einsum 최대 |차|)",
             perm["🔴 BLAS 거짓 경보 대조(matmul vs einsum 최대 |차|)"]),
            ("🔴 이름", name)])

    out["⑤🔴 조각 분해표(조항 79) --- 사다리 셋"] = collections.OrderedDict([
        ("🔴 왜", "조항 79-2: 쪼갠 표 «없이» 판정을 내는 것을 금지한다. "
              "조항 79 개정 1: 조각은 «연언(k/k)»으로 채점한다"),
        ("㉡ 스텝 사다리(0 → 750 → 1500 → 3000)",
         ladder("㉡ 스텝 사다리", stpseg, stpperm, "스텝0→스텝3000",
                G(stpperm, "분모: 도메인 d"), G(stpperm, "도메인"))),
        ("㉠ k 사다리(8 → 16 → 32 → 64 → 128 · 🔴 공통 분모 도메인 고정)",
         ladder("㉠ k 사다리", kseg, kperm, "k=8→k=128",
                G(kperm, "분모: 도메인 d"), G(kperm, "도메인"))),
        ("🔴 k 사다리의 분모 주의(조항 60)",
         "🔴 «사다리 안»에서는 공통 8 도메인으로 분모를 고정했다(옳다). 그러나 위 ① 표의 "
         "설정별 `MDE` 는 «각 k 가 실제로 잰» 도메인 집합(12·11·11·8·8)에서 나왔다 "
         "--- 두 곳의 분모가 다르다"),
        ("㉠ 전량 라벨 · 바닥 둘(④ 난수표현 · ⑤ 라벨순열) 두 조각",
         collections.OrderedDict([
             ("조각별", collections.OrderedDict(
                 (k, seg_row(v)) for k, v in
                 G(PR, "🔴 헤드라인 대비 · 전량 라벨").items())),
             ("🔴🔴 연언 k/k", pfperm["🔴🔴 관측 통과 수 / 분모 조각"]),
             ("🔴 순열 p(연언)", pfperm["🔴🔴 p(조각 «전부» 넘는다 = 연언)"]),
             ("⚠ 항등 합은 통과로 «안» 센다", pfperm["조각 이름"][-1])])),
        ("㉡ 헤드라인(학습 − 난수표현) 단일 조각",
         collections.OrderedDict([
             ("값", seg_row(G(MK, "🔴 헤드라인 대비 ㉡ = 학습 − 난수표현"))),
             ("🔴🔴 연언 k/k", mkperm["🔴🔴 관측 통과 수 / 분모 조각"]),
             ("🔴🔴 순열 p", mkperm["🔴🔴 p(조각 «전부» 넘는다 = 연언)"]),
             ("🔴 순열 p 가 0.05 를 넘나(= 순열 자로는 기각 못 한다)",
              bool(mkperm["🔴🔴 p(조각 «전부» 넘는다 = 연언)"] > 0.05))])),
        ("🔴🔴 사다리 셋의 연언 합", collections.OrderedDict([
            ("㉡ 스텝", stpperm["🔴🔴 관측 통과 수 / 분모 조각"]),
            ("㉠ k", kperm["🔴🔴 관측 통과 수 / 분모 조각"]),
            ("㉠ 전량 바닥 둘", pfperm["🔴🔴 관측 통과 수 / 분모 조각"])]))])

    cse = G(GA, "🔴 조항 79 개정 2 — 이 사이클의 cluster_se 칸 전량")
    out["⑥🔴 `cluster_se` 칸 «전량»(조항 79 개정 2)"] = collections.OrderedDict([
        ("🔴🔴 분모: 전량", cse["분모: 전량"]),
        ("🔴 2·SE 를 넘은 칸", cse["2·SE 를 넘은 칸"]),
        ("안 넘은 칸", cse["안 넘은 칸"]),
        ("판정 불가 칸", cse["판정 불가 칸"]),
        ("넘은 비율", cse["넘은 비율"]),
        ("러너별", collections.OrderedDict(
            (k, collections.OrderedDict([
                ("분모", v["🔴🔴 분모: 이 주행이 낸 cluster_se 칸 전량"]),
                ("넘은 칸", v["🔴 2·SE 를 넘은 칸"])]))
            for k, v in cse["러너별"].items())),
        ("🔴 넘은 비율이 1.0 인 것을 어떻게 읽나",
         "🔴 **이 사이클의 대비는 «전부» 바닥(난수표현·순열) 대비이거나 «단조 학습 곡선»의 "
         "이웃 차다** --- 곧 참 효과가 «크다». 995 의 25/40 과 견주면 분모의 «성격»이 다르다"
         " --- 이 수는 「이 사이클이 얼마나 잘 맞혔나」가 아니라 「분모가 무엇이었나」다")])

    hol = G(GA, "🔴 Holm(가족 FC-997)")
    fam = G(GA, "🔴 가족이 다 모였나")
    out["⑦🔴 다중비교 --- 가족 `FC-997`"] = collections.OrderedDict([
        ("🔴 사전등록 m", fam["🔴 사전등록 m"]),
        ("모인 p 수", fam["모인 p 수"]),
        ("🔴 다 모였나(부분 가족이 아닌가)", fam["🔴 다 모였나"]),
        ("alpha", hol["alpha"]),
        ("🔴 Holm 뒤 살아남은 수", hol["🔴 Holm 뒤 살아남은 수"]),
        ("검정별", collections.OrderedDict(
            (k, collections.OrderedDict([("p", v["p"]),
                                         ("계단 문턱", v["계단 문턱 alpha/(m-i)"]),
                                         ("🔴 Holm 통과", v["🔴 Holm 통과"])]))
            for k, v in hol["검정별"].items())),
        ("🔴 조각은 가족 «밖»이다(조항 79 개정 1·4)",
         "스텝 사다리 3 · k 사다리 4 는 `m` 에 «안» 센다. 연언(k/k)으로만 채점한다"),
        ("🔴 `MDE` 는 가족에 «안» 넣는다",
         G(GA, "🔴 다중비교 가족", "🔴 `MDE` 를 가족에 안 넣는 까닭"))])

    t78 = G(GA, "🔴🔴 조항 78 ㉮·㉯ 합(기계)")
    out["⑧🔴 조항 78 계수(기계 · 손 라벨 «아님»)"] = collections.OrderedDict([
        ("🔴 분모: 검사한 주장 합", t78["분모: 검사한 주장 합"]),
        ("🔴 ㉮ 분자 합", t78["🔴 ㉮ 분자 합"]),
        ("🔴 ㉯ 분자 합", t78["🔴 ㉯ 분자 합"]),
        ("🔴 둘 다 0 인가", t78["🔴 둘 다 0 인가"]),
        ("러너별", t78["러너별"]),
        ("🔴 대조 ㉮ 분자(자료에서 «계산»한 주장 · 리터럴 아님)", [
            G(t78, "러너별", "㉠ 라벨 프로브", "🔴 대조 ㉮ 분자"),
            G(t78, "러너별", "㉡ 라벨 0 개 자", "🔴 대조 ㉮ 분자")]),
        ("🔴 대조 ㉯ 분자", [
            G(t78, "러너별", "㉠ 라벨 프로브", "🔴 대조 ㉯ 분자"),
            G(t78, "러너별", "㉡ 라벨 0 개 자", "🔴 대조 ㉯ 분자")]),
        ("🔴 계수가 「0」을 낼 수 있나(㉠ · ㉡)", [
            G(PR, "🔴🔴 조항 78 ㉮·㉯ (기계)", "🔴🔴 계수가 「0」을 낼 수 있나(본 주장에서)"),
            G(MK, "🔴🔴 조항 78 ㉮·㉯ (기계)", "🔴🔴 계수가 「0」을 낼 수 있나(본 주장에서)")]),
        ("🔴 변이체 분모", [G(PR, "🔴🔴 조항 78 ㉮·㉯ (기계)", "분모: 변이체"),
                     G(MK, "🔴🔴 조항 78 ㉮·㉯ (기계)", "분모: 변이체")]),
        ("🔴 위약이 «리터럴»이 아니라는 증거",
         G(PR, "🔴🔴 조항 78 ㉮·㉯ (기계)", "변이체 목록")[-1])])

    # ── ⑨ 예측 채점 ────────────────────────────────────────────────────
    P = collections.OrderedDict()

    def vd(ok):
        if ok is None:
            return "🔴 미측정"
        if isinstance(ok, str):
            return ok
        return "맞다" if ok else "🔴 틀렸다"

    def ap_(k, ok, why, num=None):
        P[k] = collections.OrderedDict([("판정", vd(ok)), ("근거", why)])
        if num is not None:
            P[k]["수"] = num

    mB = rows[0]["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"]
    mA = rows[1]["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"]
    m16 = G(KM, "k=16", "🔴🔴 MDE", K_HEAD, K_INTERP)
    kmde = [G(KM[k], "🔴🔴 MDE", K_HEAD, K_INTERP) for k in KS]
    ratios = [row["MDE_s / MDE_a"] for row in rows]

    ap_("P01", bool(mB < mA), "㉡(라벨 0 개 자)의 MDE_s 가 ㉠(전량 라벨)보다 작다",
        [mB, mA, r(mA / mB)])
    ap_("P02", bool(m16 > mA),
        "🔴 예측은 `k=16` 이 전량보다 «크다» 였는데 «작다» --- ④ 가 기전을 낸다(팝업)",
        [m16, mA])
    ap_("P03", bool(all(kmde[i] > kmde[i + 1] for i in range(len(kmde) - 1))),
        "🔴 k 가 커질수록 MDE_s 가 작아진다(5/5 단조). ⚠ 그러나 «잰 도메인 집합»이 "
        "12·11·11·8·8 로 갈린다 --- 이 단조는 「k 효과」와 「분모 효과」가 섞여 있다(조항 60)",
        [kmde, [len(v) for v in list(kdoms.values())[1:]]])
    ap_("P04", bool(m16 / g915 > 1),
        "MDE_s(k=16) ÷ 915 의 차 > 1 ⟹ 915 는 그 차를 «못 쟀다»",
        G(GA, "🔴🔴 915 의 차를 잴 수 있었나", "🔴 MDE / 915 차"))
    ap_("P05", bool(all(x is not None and x >= 1 for x in ratios)),
        "🔴 「MDE_s ≥ MDE_a 가 두 자 «모두»」가 예측이었다. ㉡ 은 0.92 로 «작고», "
        "일곱 설정 중 다섯이 1 아래다 --- 정규 근사가 «보수적»이 아니라 «낙관적»이었던 "
        "쪽은 오히려 모의다",
        collections.OrderedDict((row["설정"], row["MDE_s / MDE_a"]) for row in rows))
    ap_("P06", bool(G(MK, "🔴🔴 바닥 ⑤ 라벨 순열 (자 ㉡ · 라벨 0 비트)", "🔴 최대 |차|") == 0.0
                    and G(PR, "🔴 헤드라인 대비 · 전량 라벨", "실측 − 라벨 순열(⑤)",
                          "점추정") != 0.0),
        "㉡ 의 라벨 순열 최대 |차| 가 «글자 그대로» 0 이고, ㉠ 의 라벨 순열 대비는 0 이 아니다",
        [G(MK, "🔴🔴 바닥 ⑤ 라벨 순열 (자 ㉡ · 라벨 0 비트)", "🔴 최대 |차|"),
         G(PR, "🔴 헤드라인 대비 · 전량 라벨", "실측 − 라벨 순열(⑤)", "점추정")])
    ap_("P07", bool(G(MK, "🔴🔴 라벨 누출 대조판 (같은 격자 · 라벨을 «입력열»로 넣었다)",
                      "🔴 최대 |차|") > 0),
        "라벨을 «입력열»로 넣은 누출 대조판은 순열에서 값이 바뀐다 ⟹ P06 은 항등식이 아니다",
        G(MK, "🔴🔴 라벨 누출 대조판 (같은 격자 · 라벨을 «입력열»로 넣었다)", "🔴 최대 |차|"))
    permnone = ([G(MM, K_MDE_S, K_PERMONLY, K_INTERP),
                 G(PF, K_MDE_S, K_PERMONLY, K_INTERP)] +
                [G(KM[k], "🔴🔴 MDE", K_PERMONLY, K_INTERP) for k in KS])
    ap_("P08", bool(all(v is None for v in permnone)),
        "순열 검정의 MDE 는 일곱 설정 «전량»에서 「못 잰다」(격자 최대 δ=0.80 에서 힘 0.000)",
        [len(permnone), sum(1 for v in permnone if v is None)])
    ap_("P09", bool(not G(MM, K_MDE_S, K_PERMONLY, K_MONO)
                    and not G(PF, K_MDE_S, K_PERMONLY, K_MONO)),
        "순열 검정의 힘이 δ 에 «단조가 아니다» --- 두 자 모두. 그리고 «역단조»다(③)",
        [G(PF, "귀무 δ=0 에서 잰 것", "🔴 1종 오류(순열만)"),
         G(PF, K_MDE_S, K_PERMONLY, K_LASTPOW)])
    hmk = G(MK, "🔴 헤드라인 대비 ㉡ = 학습 − 난수표현")
    ap_("P10", bool(hmk["점추정"] > 0 and hmk["동부호 분자"] >= 9),
        "㉡ 헤드라인이 양수이고 동부호 ≥ 9/12",
        [hmk["점추정"], hmk["🔴 동부호 수"], hmk["t_clu"]])
    h4 = G(PR, "🔴 헤드라인 대비 · 전량 라벨", "실측 − 난수 표현(④)", "점추정")
    h5 = G(PR, "🔴 헤드라인 대비 · 전량 라벨", "실측 − 라벨 순열(⑤)", "점추정")
    ap_("P11", bool(h4 > h5), "㉠ 전량에서 `실측−④` 가 `실측−⑤` 보다 크다", [h4, h5])
    ap_("P12", bool(t78["🔴 ㉮ 분자 합"] == 0 and t78["🔴 ㉯ 분자 합"] == 0
                    and G(t78, "러너별", "㉠ 라벨 프로브", "🔴 대조 ㉮ 분자") == 1
                    and G(t78, "러너별", "㉡ 라벨 0 개 자", "🔴 대조 ㉯ 분자") == 1),
        "조항 78 ㉮·㉯ 분자가 둘 다 0 이고 대조 분자가 둘 다 1 --- 러너 «양쪽»에서",
        [t78["🔴 ㉮ 분자 합"], t78["🔴 ㉯ 분자 합"]])
    kconj = kperm["🔴🔴 관측 통과 수 / 분모 조각"]
    ap_("P13", bool(kconj != "%d/%d" % (kperm["분모: 조각"], kperm["분모: 조각"])),
        "🔴 예측은 「k 사다리 연언이 4/4 가 «아니다»」였는데 «4/4 다». 연기 시험(축소 설정 "
        "2/4)이 가리킨 쪽과 본 주행이 «갈렸다» --- 사전등록 §7 이 그 갈림 자체를 산출로 "
        "치라고 적었다. ⟹ 이 사다리는 「가설 후보」가 아니라 «명제»로 읽을 수 있다",
        [kconj, kperm["🔴🔴 p(조각 «전부» 넘는다 = 연언)"]])
    st = [stpseg[k]["점추정"] for k in ("스텝0→스텝750", "스텝750→스텝1500",
                                     "스텝1500→스텝3000")]
    ap_("P14", bool(st[0] == max(st)), "스텝 사다리 조각 셋 중 «첫 조각»이 가장 크다", st)
    ap_("P15", bool(mB < HI), "㉡ 의 MDE_s 가 `ρ 0.30` 아래다", [mB, HI])
    if FP is None:
        ap_("P16", None, "🔴 ⑤′ 산출물을 «안 줬다** --- 「없다」가 아니라 「이 주행이 안 봤다」다"
                         "(조항 59). `--fiveprime` 을 주고 다시 돌리면 채점된다", None)
    else:
        g9 = G(FP, "9 🔴🔴 리터럴 `통과` 금지(983 R1 · AST)")
        ap_("P16", bool(g9["🔴🔴🔴 이 사이클 파일의 리터럴 수(분자)"] == 0),
            "⑤′ 절 9 AST 리터럴 스캔의 «이 사이클» 분자가 0",
            [g9["🔴🔴🔴 이 사이클 파일의 리터럴 수(분자)"], g9["🔴 분모 수"],
             g9["🔴 분모 (이 사이클이 건드린 그 유형의 파일)"]])
    sens = G(MK, "MDE 민감도(통째 풀 재표집)", "MDE_s", K_HEAD, K_INTERP)
    ap_("P17", "부분(㉡ 만 · 🔴 ㉠ 은 «안 쟀다»)" if sens else None,
        "🔴 ㉡ 은 「도메인 짝지어」 대 「통째 풀」이 1.02 배로 같은 쪽을 가리킨다. "
        "🔴 그런데 `runners/mde997_probe.py` 는 «통째 풀» 민감도를 «한 번도 안 냈다» "
        "--- ㉠ 쪽은 「없다」가 아니라 「안 쟀다」다(조항 59)",
        [mB, sens, r(mB / sens)])
    ap_("P18", bool(any(b.startswith("사이") for b in brs)),
        "🔴 「사이 칸」(0.10 ≤ MDE < 0.30)에 «하나 이상» 떨어졌다 ⟹ 카드의 이분 분기표가 "
        "«불충분»하다",
        [row["설정"] for row in rows if row["🔴🔴 분기(계산)"].startswith("사이")])

    ok_ = sum(1 for v in P.values() if v["판정"] == "맞다")
    bad = sum(1 for v in P.values() if v["판정"] == "🔴 틀렸다")
    part = sum(1 for v in P.values() if v["판정"].startswith("부분"))
    unk = sum(1 for v in P.values() if v["판정"] == "🔴 미측정")
    P["🔴 채점 합"] = collections.OrderedDict([
        ("분모: 예측", len(P) - 0), ("맞다", ok_), ("부분", part),
        ("🔴 틀림", bad), ("🔴 미측정", unk),
        ("🔴 틀린 것", [k for k, v in P.items()
                    if isinstance(v, dict) and v.get("판정") == "🔴 틀렸다"]),
        ("🔴 미측정인 것", [k for k, v in P.items()
                      if isinstance(v, dict) and v.get("판정") == "🔴 미측정"])])
    P["🔴 채점 합"]["분모: 예측"] = len(P) - 1
    out["⑨🔴 예측 채점 `P01`~`P18`"] = P

    # ── ⑩ 반증조건 채점 ────────────────────────────────────────────────
    F = collections.OrderedDict()

    def vf(ok):
        if ok is None:
            return "🔴 미측정"
        return "통과" if ok else "🔴 불통과"

    def af(k, ok, why, num=None):
        F[k] = collections.OrderedDict([("판정", vf(ok)), ("근거", why)])
        if num is not None:
            F[k]["수"] = num

    perm0 = G(MK, "🔴🔴 바닥 ⑤ 라벨 순열 (자 ㉡ · 라벨 0 비트)", "🔴 최대 |차|")
    leak = G(MK, "🔴🔴 라벨 누출 대조판 (같은 격자 · 라벨을 «입력열»로 넣었다)", "🔴 최대 |차|")
    af("F01", bool(perm0 == 0.0),
       "㉡ 의 라벨 순열 최대 |차| = 0 ⟹ 「라벨 0 개 자」 주장이 산다", perm0)
    af("F02", bool(leak != 0.0),
       "누출 대조판의 최대 |차| ≠ 0 ⟹ F01 검사는 항등식(㉮)이 «아니다»", leak)
    t1 = collections.OrderedDict(
        [(row["설정"], row["🔴 1종 오류(㉠ · δ=0)"]) for row in rows])
    bad_t1 = collections.OrderedDict((k, v) for k, v in t1.items()
                                     if not (0.02 <= v <= 0.10))
    af("F03", bool(not bad_t1),
       "🔴 귀무 δ=0 의 1종 오류(㉠ 2·SE)가 `[0.02, 0.10]` 밖인 설정이 «있다». "
       "사전등록 처방은 「그 설정의 힘 곡선을 못 믿는다 --- MDE 를 안 낸다」다. "
       "🔴 이 팔은 그 설정의 MDE 를 «싣되 붉게» 표시한다 --- 지우면 「없다」가 되고 "
       "그건 조항 59 위반이다",
       collections.OrderedDict([("설정별 1종 오류", t1), ("🔴 대역 밖", bad_t1),
                                ("🔴 분모: 설정", len(t1))]))
    se_pr = G(PR, "🔴 해석 SE 대 등록된 뽑기 SE")
    se_mk = G(MK, "🔴 해석 SE 대 등록된 뽑기 SE")
    af("F04", bool(se_pr["🔴 통과"] and se_mk["🔴 통과"]),
       "순열이 쓰는 해석 SE 가 등록된 뽑기 SE 와 5 % 안 --- 두 러너 모두",
       [se_pr["🔴 상대 차"], se_mk["🔴 상대 차"], se_pr["허용"]])
    sc = G(MK, "🔴 빠른 순열판이 등록된 자와 같은가")
    af("F05", bool(sc["🔴 같은가"]),
       "🔴 `signflip_selfcheck` 의 「같은가」가 «거짓»이다. 차는 `2.5e-07` 이고 "
       "**빠른 판 `0.08203125` 와 등록된 자 `0.082031` 의 «반올림»**이다"
       "(`runners/delta996_common.py:338` 의 `_r(…, 6)`). 평균·SE 는 «완전 일치». "
       "🔴 사전등록 처방은 「순열 칸 전량 무효」이고 그대로 «집행한다» --- 그런데 "
       "헤드라인 ㉠(2·SE)은 순열을 안 쓰므로 ①②④ 표의 수는 «안 바뀐다». "
       "🔴 고치지 않았다(주행 중 소스 수정 금지 · 조항 66)",
       collections.OrderedDict([("빠른 판 p", sc["빠른 판 p"]),
                                ("등록된 자 p", sc["등록된 자 p(`signflip_exact`)"]),
                                ("차", sc["차"]),
                                ("평균 일치", bool(sc["빠른 판 평균"] == sc["등록된 자 평균"])),
                                ("SE 일치", bool(sc["빠른 판 SE"] == sc["등록된 자 SE"]))]))
    af("F06", bool(t78["🔴 ㉮ 분자 합"] == 0 and t78["🔴 ㉯ 분자 합"] == 0),
       "taut_scan 의 ㉮·㉯ 분자가 둘 다 0",
       [t78["🔴 ㉮ 분자 합"], t78["🔴 ㉯ 분자 합"], t78["분모: 검사한 주장 합"]])
    af("F07", bool(G(t78, "러너별", "㉠ 라벨 프로브", "🔴 대조 ㉮ 분자") > 0
                   and G(t78, "러너별", "㉠ 라벨 프로브", "🔴 대조 ㉯ 분자") > 0
                   and G(t78, "러너별", "㉡ 라벨 0 개 자", "🔴 대조 ㉮ 분자") > 0
                   and G(t78, "러너별", "㉡ 라벨 0 개 자", "🔴 대조 ㉯ 분자") > 0),
       "대조 ㉮·㉯ 분자가 둘 다 0 이 «아니다» --- 계수가 0/1 을 낼 수 있다",
       t78["러너별"])
    af("F08", bool(fam["🔴 다 모였나"]),
       "가족 `FC-997` 의 모인 p 수 == 사전등록 m",
       [fam["🔴 사전등록 m"], fam["모인 p 수"]])
    af("F09", None,
       "🔴 `runners/mde997_probe.py:82` 의 `assert len(intersect1d(TR, HO)) == 0` 이 "
       "«안 터졌다»는 것이 유일한 증거이고, 그 사실을 «칸으로 낸 산출물 키가 없다». "
       "🔴 「통과」가 아니라 「인용할 키가 없다」로 적는다(조항 81 · 인용 규약)",
       "runners/mde997_probe.py:82")
    af("F10", bool(all(row["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"] is not None
                       for row in rows)),
       "🔴 헤드라인 ㉠ 은 일곱 설정 «전량»에서 잡혔다. 🔴 그러나 «검정 ㉡(순열만)»과 "
       "«㉠∧㉡ 연언»은 일곱 설정 전량에서 격자 최대 δ=0.80 까지 «못 잡았다» --- "
       "처방대로 「못 쟀다」로 적고 격자를 «사후에 안 넓혔다»",
       collections.OrderedDict([
           ("헤드라인 ㉠ 이 잡힌 설정 수", sum(
               1 for row in rows
               if row["🔴🔴 MDE_s(헤드라인 ㉠ 2·SE · 보간)"] is not None)),
           ("🔴 순열만 검정이 잡힌 설정 수", sum(1 for v in permnone if v is not None)),
           ("🔴 분모: 설정", len(rows))]))
    af("F11", bool(G(PR, "사전등록", "sha256") == G(MK, "사전등록", "sha256")
                   == G(GA, "사전등록", "sha256") == sha(
                       "docs/prereg_997_unsupervised_mde.md")),
       "두 러너와 관문이 신고한 사전등록 sha256 이 서로 같고 «지금 트리의 파일»과도 같다",
       G(GA, "사전등록", "sha256"))
    codes = G(GA, "코드 sha256")
    now = collections.OrderedDict((k, sha("runners/" + k)) for k in codes)
    af("F12", bool(all(codes[k] == now[k] for k in codes)),
       "러너 넷의 sha256 이 산출물 신고값과 «지금 트리»에서 같다 --- 주행 중 소스 수정 0",
       collections.OrderedDict([("신고", codes), ("지금", now)]))
    if FP is None:
        af("F13", None, "🔴 ⑤′ 산출물을 이 주행에 «안 줬다**(조항 59 --- 「없다」가 아니다)")
    else:
        g9 = G(FP, "9 🔴🔴 리터럴 `통과` 금지(983 R1 · AST)")
        af("F13", bool(g9["🔴🔴🔴 이 사이클 파일의 리터럴 수(분자)"] == 0),
           "⑤′ 절 9 의 «이 사이클» 분자가 0",
           [g9["🔴🔴🔴 이 사이클 파일의 리터럴 수(분자)"], g9["🔴 분모 수"]])
    af("F14", bool(isinstance(cse["분모: 전량"], int) and cse["분모: 전량"] > 0),
       "산출물에 `cluster_se` 칸 «전량» 분모가 있다(관문이 두 러너의 `cse_ledger` 를 합쳐 센다)",
       cse["분모: 전량"])
    dn = G(MK, "분모 --- 🔴 이것이 ③ 을 고르는 «이유»다")
    af("F15", bool(dn["🔴 유보 셀 = ㉡ 의 분모"] > dn["🔴 유보 라벨 = ㉠ 의 분모"]),
       "㉡ 의 유보 셀이 ㉠ 의 유보 라벨보다 «많다» --- ③ 을 고른 근거가 선다",
       [dn["🔴 유보 셀 = ㉡ 의 분모"], dn["🔴 유보 라벨 = ㉠ 의 분모"],
        dn["🔴 배수(㉡ 분모 / ㉠ 분모)"]])
    af("F16", bool(sens and max(mB, sens) / min(mB, sens) <= 3),
       "🔴 ㉡ 은 재표집 «꼴»이 결론을 안 만든다(1.02 배). 🔴 ㉠ 은 «통째 풀»을 안 재서 "
       "이 검사를 «못 걸었다» --- 「통과」가 아니라 「㉠ 쪽은 미측정」이다",
       [mB, sens, r(max(mB, sens) / min(mB, sens))])
    mono = collections.OrderedDict(
        [(row["설정"], row["🔴 힘이 δ 에 단조인가(㉠)"]) for row in rows])
    af("F17", bool(all(mono.values())),
       "🔴 힘 곡선의 ㉠ 이 δ 에 «단조가 아닌» 설정이 있다. 🔴 그리고 `k` 팔은 «힘 곡선 "
       "자체를 산출물에 안 실었다» --- 위반의 «크기»(어느 δ 에서 얼마나 꺾였나)를 "
       "커밋된 키에서 «못 되찾는다**. 조항 59 로 「쟀는데 안 실었다」다",
       collections.OrderedDict([("설정별 단조", mono),
                                ("🔴 단조가 아닌 설정",
                                 [k for k, v in mono.items() if not v]),
                                ("🔴 힘 곡선 키가 있는 설정",
                                 ["🔴 ㉡ 라벨 0 개 자(가림 복원)",
                                  "㉠ 라벨 프로브 · 전량 라벨"]),
                                ("🔴 분모: 설정", len(mono))]))
    okf = sum(1 for v in F.values() if v["판정"] == "통과")
    badf = sum(1 for v in F.values() if v["판정"] == "🔴 불통과")
    unkf = sum(1 for v in F.values() if v["판정"] == "🔴 미측정")
    F["🔴 채점 합"] = collections.OrderedDict([
        ("분모: 반증조건", len(F)), ("통과", okf), ("🔴 불통과", badf),
        ("🔴 미측정", unkf),
        ("🔴 불통과한 것", [k for k, v in F.items()
                      if isinstance(v, dict) and v.get("판정") == "🔴 불통과"]),
        ("🔴 미측정인 것", [k for k, v in F.items()
                      if isinstance(v, dict) and v.get("판정") == "🔴 미측정"])])
    F["🔴 채점 합"]["분모: 반증조건"] = len(F) - 1
    out["⑩🔴 반증조건 채점 `F01`~`F17`"] = F

    out["⑪🔴 조항 81 --- 「보고에만 있는 수」 장부"] = collections.OrderedDict([
        ("🔴 왜", "조항 81: 에이전트의 «보고»는 증거가 아니다. 증거는 «커밋된 산출물의 "
              "키 경로»다. 보고와 산출물이 어긋나면 «어긋남 자체»를 기록한다"),
        ("① 측정 팔 보고 「팝업이 SE_0 분산의 71.3 %」", collections.OrderedDict([
            ("보고값", "0.713"),
            ("🔴 정비 팔이 커밋된 키에서 다시 «계산»한 값", r(sd["팝업"] ** 2 / tot)),
            ("🔴 출처 키", "out997_probe.json:위약 짝 · 전량 라벨/도메인별 SD"),
            ("🔴 어긋나나", bool(abs(sd["팝업"] ** 2 / tot - 0.713) > 0.001)),
            ("🔴 지위", "🔴 러너가 «안 낸» 칸이다. 정비 팔의 «산술»이고 그 계산 자리를 "
                    "④ 에 적었다 --- 「산출물 키」가 아니다")])),
        ("② 측정 팔 보고 「팝업 빼면 전량 MDE_a 0.1296 → 0.0777」",
         collections.OrderedDict([
             ("보고값", "0.0777"),
             ("🔴 정비 팔이 커밋된 키에서 다시 «계산»한 값", r(zsum * d11)),
             ("🔴 출처 키", "out997_probe.json:위약 짝 · 전량 라벨/도메인별 SD + "
                       "🔴🔴🔴 MDE (자 ㉠ · 전량 라벨)/🔴 해석식 MDE_a/z 합"),
             ("🔴 어긋나나", bool(abs(zsum * d11 - 0.0777) > 0.0005)),
             ("🔴 한계", "해석식(`MDE_a`) 자리에서만 다시 냈다. «모의 `MDE_s`»를 d=11 로 "
                     "다시 내려면 러너를 다시 돌려야 하고 이 팔은 «측정을 안 한다»")])),
        ("③ 조타수 보고 「GPU(MPS) 대 CPU 벤치마크」", collections.OrderedDict([
            ("파일", "$CLAUDE_JOB_DIR/tmp/mpsbench.py"),
            ("🔴 커밋됐나", False),
            ("🔴 지위", "🔴 조항 81 --- 「커밋된 산출물」이 아니다. 원장에 «조타수 보고»로 "
                    "이름 붙여 남기고 이 사이클의 어느 판정 칸에도 «안 쓴다»"),
            ("보고된 비(CPU/MPS)", ["997 현행 256·2·256 = 0.85", "512·4·1024 = 3.66",
                                "1024·6·4096 = 3.30"]),
            ("🔴 저장소에 `.to(\"mps\")` 가 있나", "조타수 보고: 0 건. "
                                            "🔴 이 팔이 «따로 안 셌다»(조항 59)")]))])

    out["⑫🔴 조항 59 --- 「안 쟀다」 장부"] = collections.OrderedDict([
        ("🔴 왜", "「없다」·「0 이다」·「안 쟀다」·「쟀는데 안 실었다」·「못 읽었다」는 다섯이다"),
        ("① ㉠ 의 «통째 풀» 민감도", "🔴 안 쟀다 --- `mde997_probe.py` 에 그 갈래가 «없다». "
                             "㉡ 만 `mde997_mask.py:321` 에서 냈다. `P17`·`F16` 이 "
                             "그래서 «부분»이다"),
        ("② k 팔의 힘 곡선", "🔴 쟀는데 «안 실었다** --- `power_curve` 가 곡선을 계산하는데 "
                      "k 갈래는 요약 칸만 산출물에 넣는다. `F17` 위반의 «크기»를 "
                      "커밋된 키에서 못 되찾는다"),
        ("③ 학습∩유보 = 0", "🔴 `assert` 로만 지킨다 --- «칸이 없다**(`F09`)"),
        ("④ 판 ρ", "🔴 «일부러» 안 쟀다 --- 사전등록 §10 이 「판 ρ 를 판정에 안 쓴다」로 "
                "미리 등기했다. 이 사이클의 어느 칸에도 판 ρ 가 없다"),
        ("⑤ HPLT·FineWeb2·`Z_t`", "🔴 «일부러» 안 열었다 --- 사전등록 §⓪-바"),
        ("⑥ `ledger996.py` 의 리터럴 `(\"통과\", True)` 13 건",
         "🔴 «일부러» 안 고쳤다 --- 사전등록 §10 이 「붉은 채로 계상하고 998 로 넘긴다」로 "
         "미리 등기했다. 이 사이클이 그 파일을 안 건드리므로 ⑤′ 절 9 의 «이 사이클» "
         "분자에는 «안» 들어간다(전수 진단에는 들어간다)")])

    out["사전등록"] = collections.OrderedDict([
        ("파일", "docs/prereg_997_unsupervised_mde.md"),
        ("sha256", sha("docs/prereg_997_unsupervised_mde.md"))])
    out["입력 sha256"] = collections.OrderedDict((p, sha(p)) for p in INS)
    out["코드 sha256"] = collections.OrderedDict((p, sha(p)) for p in SRC)
    out["⑤′ 산출물을 봤나"] = a.fiveprime or "🔴 안 줬다(조항 59)"
    out["끝 시각(UTC)"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out["걸린 초"] = round((dt.datetime.now(dt.timezone.utc) - t0).total_seconds(), 3)
    out["통과"] = bool(badf == 0)

    with open(str(ROOT / OUT), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("예측 %d/%d 맞다 · 부분 %d · 틀림 %d · 미측정 %d" % (ok_, len(P) - 1, part, bad, unk))
    print("반증조건 통과 %d/%d · 불통과 %d · 미측정 %d" % (okf, len(F) - 1, badf, unkf))
    print("산출물: %s" % OUT)


if __name__ == "__main__":
    main()
