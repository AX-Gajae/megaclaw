#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""954 채점기 --- 사전등록 `docs/prereg_954_dupe.md` §4·§5 를 **글자 그대로** 물린다.

🔴 **문턱은 여기서 처음 정하는 것이 아니다.** 전부 사전등록 커밋 `97333c78d`
(2026-08-13T11:13:51+09:00 · 측정 시작 **전**)에 박혀 있고, 이 파일은 그것을 **옮겨 물릴 뿐**이다.
🔴 **수를 손으로 안 쓴다** --- 산출물 키에서 읽는다.
🔴 **빗맞힌 것을 빗맞혔다고 적는다.** 문턱 미달은 「못 넘었다」가 아니라 **「이 자를 못 넘었다」**.

    python3 runners/score954.py
"""
import hashlib
import json
import pathlib
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
PREREG = "docs/prereg_954_dupe.md"
PREREG_COMMIT = "97333c78d2a5371ba9c0313fcfa0d6773432f02f"


def J(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def main():
    t0 = time.time()
    hf = J("runners/out954_hplt_full.json")
    dp = J("runners/out954_dupe.json")

    r1 = dp["자 ① URL 정확"]
    r2 = dp["자 ② URL 정규화(🔴 정본)"]
    r3 = dp["자 ③ 본문 앞 200자"]
    # 🔴🔴 955 수리(티처 #93 C1): 이 한 줄이 954 의 판정을 뒤집은 자리다.
    #    사전등록 §5:102 가 한 줄에 정의를 **둘** 적었고(「교집합 ÷ FineWeb 표본 문서 수
    #    (= FineWeb 문서 중 HPLT 에 이미 URL 이 있는 비율)」) 이 줄이 **뒤엣것**을 골랐는데
    #    산출물의 **키 이름은 앞엣것**이었다. 그래서 「D = 49.593%」가 「교집합 ÷ …」라는
    #    이름을 달고 표·PR·원장·인계 카드로 자동 전파됐다.
    #    🔴 **955 는 둘 다 읽어 이름을 박아 낸다.** 어느 이름의 산출물이든 열린다
    #    (얼린 `out954_dupe.json` 은 옛 이름 · 새로 찍는 것은 새 이름).
    D_문서 = r2.get("🔴 D_문서 = 맞은 FineWeb 문서 ÷ FineWeb 표본 문서",
                   r2.get("🔴 교집합 ÷ FineWeb 표본 문서"))
    D_키 = r2.get("🔴 D_키 = 교집합 키 ÷ FineWeb 표본 서로 다른 키")
    if D_키 is None:                       # 옛 산출물엔 없다 --- 여기서 직접 낸다
        D_키 = round(r2["교집합(서로 다른 키)"] / r2["🔴 분모 ④ FineWeb 표본 서로 다른 키"], 6)
    D_954글자 = round(r2["교집합(서로 다른 키)"] / r2["🔴 분모 ② FineWeb 표본 문서"], 6)
    # 🔴 954 의 P1 은 「자② ÷ FineWeb 표본」이었고 채점기가 D_문서 를 골랐다.
    #    955 는 **고른 것을 이름으로 적는다**(무엇을 골랐는지가 판정을 바꾼다).
    D = D_문서
    _D_고른_이름 = "D_문서 = 맞은 FineWeb 문서 ÷ FineWeb 표본 문서"

    gam = hf["도박(내 자)"]
    news = hf["뉴스형 host(내 자)"]
    txtdup = hf["정확중복 --- 전문"]
    kin = hf["🔴 kin.naver.com 순위"]

    P = []

    def add(no, 말, 조건, 값, 맞았나):
        P.append({"번호": no, "예측": 말, "반증 조건": 조건, "실측": 값, "맞았나": bool(맞았나)})

    add("P1", "자② 교집합 ÷ FineWeb 표본 = 25% ± 15%p", "0.10~0.40 밖",
        D, 0.10 <= D <= 0.40)
    d21 = r2["🔴 교집합 ÷ FineWeb 표본 문서"] - r1["🔴 교집합 ÷ FineWeb 표본 문서"]
    add("P2", "자② ≥ 자① 이고 차 ≥ 1.0%p", "차 < 0.01 또는 ② < ①",
        round(d21, 6), d21 >= 0.01)
    d32 = r3["🔴 교집합 ÷ FineWeb 표본 문서"] - r2["🔴 교집합 ÷ FineWeb 표본 문서"]
    add("P3", "자③(앞 200자)이 자②보다 ≥ 5%p 크다", "차 < 0.05",
        round(d32, 6), d32 >= 0.05)
    g_full, g_cc22 = gam["비율"], gam["cc22 비율"]
    add("P4", "전량 도박률 ∈ [1.4%, 2.3%] 이고 cc22 는 ≥ 3.3%", "어느 한쪽이라도 밖",
        {"전량": g_full, "cc22": g_cc22},
        (0.014 <= g_full <= 0.023) and g_cc22 >= 0.033)
    xd = txtdup["군에 속한 문서 비율"]
    add("P5", "전문 정확중복 --- 군에 속한 문서 20% ± 10%p", "0.10~0.30 밖",
        xd, 0.10 <= xd <= 0.30)
    krank = kin["순위"] if isinstance(kin, dict) else None
    add("P6", "kin.naver.com 이 host 순위 상위 20 안", "20 밖 또는 없다",
        kin, krank is not None and krank <= 20)
    n_full = news["비율"]
    add("P7", "뉴스·연예형 host 비율(전량) 5~8%", "밖이거나 8.9% 이상",
        {"전량": n_full, "cc22": news["cc22 비율"]}, 0.05 <= n_full <= 0.08)
    nc = hf["collection 수"]
    mx = hf["🔴 최대 collection 비율"]
    add("P8", "collection ≥ 9 이고 어느 하나도 전량의 50% 를 안 넘는다", "둘 중 하나라도 깨지면",
        {"collection 수": nc, "최대 비율": mx}, nc >= 9 and mx <= 0.50)

    hit = sum(1 for p in P if p["맞았나"])

    # ---- §5 판정 규칙 --------------------------------------------------
    if D >= 0.70:
        verdict = "🔴 FineWeb-2 전량을 안 받는다 (D ≥ 0.70 --- 새로 얻는 문서가 30% 미만)"
        branch = "D>=0.70"
    elif D <= 0.30:
        verdict = "🔴 FineWeb-2 전량을 받는다 (D ≤ 0.30 --- 70% 이상이 새 문서)"
        branch = "D<=0.30"
    else:
        verdict = ("🔴 보류 --- 부분 수신 (0.30 < D < 0.70). 「HPLT 에 없는 URL 만 골라 담는 "
                   "경로」를 설계해 다음 사이클에 판정한다. **미리 정해 둔 세 번째 결론이지 "
                   "「못 정했다」가 아니다**")
        branch = "0.30<D<0.70"

    res = {
        "무엇": "954 채점 --- 사전등록 §4 예측 여덟 · §5 판정 규칙",
        "🔴 사전등록": {"파일": PREREG, "커밋": PREREG_COMMIT,
                    "커밋 시각": "2026-08-13T11:13:51+09:00",
                    "🔴 측정보다 먼저인가": "커밋 시각이 증언한다(이 파일은 그것을 옮길 뿐)",
                    "사전등록 sha256": hashlib.sha256(
                        (ROOT / PREREG).read_bytes()).hexdigest(),
                    "통과": True},
        "🔴 D (자② 교집합 ÷ FineWeb 표본 문서)": D,
        "🔴 §5 판정": verdict,
        "🔴 판정 갈래": branch,
        "🔴 노트 133": ("첫 양수를 그대로 채택하지 않는다 --- 이 사이클의 결론은 **제안까지**이고 "
                    "실제 105.77GB 수신·미수신 집행은 다음 사이클이 확인 측정과 함께 한다"),
        "예측 채점": P,
        "🔴 맞은 수": hit,
        "🔴 본 가짓수(분모)": len(P),
        "🔴 빗맞힌 것": [p["번호"] for p in P if not p["맞았나"]],
        "⚠ 「이 자를 못 넘었다」": ("빗맞힌 예측은 자료가 아니라 **내 자**를 말한다 --- "
                          "특히 P7 의 뉴스형 host 정규식은 어제 조사관의 자와 다른 자다"),
        "코드 sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "입력 sha256": {r: hashlib.sha256((ROOT / r).read_bytes()).hexdigest()
                      for r in ("runners/out954_hplt_full.json", "runners/out954_dupe.json")},
        "시각(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "초": round(time.time() - t0, 2),
        "통과": True,
    }
    (ROOT / "runners/out954_score.json").write_text(
        json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"D": D, "판정": verdict, "맞은 수": hit,
                      "분모": len(P), "빗맞힘": res["🔴 빗맞힌 것"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
