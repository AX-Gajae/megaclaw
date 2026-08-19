# -*- coding: utf-8 -*-
"""사이클 1007 — 콜드스타트 참조군 백테스트 (사전등록 docs/탐색/1007.md · 이 커밋에서 언다).

물음: «텍스트+도메인만 아는 신작»에게 참조군(텍스트 유사 실작들의 실측 90일 곡선 분포)이
도메인 기후값(climatology)보다 나은 답을 주는가.

설계(요지 — 정본은 사전등록 §1~§5):
  · 평가 개체 = val(개체 분리) 70 개체의 «최초 관측» 행 — 곡선(S)을 숨기고 텍스트·도메인만 사용
  · 표적 Y = 최초 관측일 포함 앞 90일 누적 조회수 = sum(O[0:90]) (원 눈금)
  · 방법 M(참조군 가중) = 같은 도메인 train 개체 최초 행에서 코사인 top-K(K=12) ·
    w=max(cos,0) 가중 분위수(q50 점 · q10~q90 구간)
  · 기준선 B1(기후값) = 같은 도메인 train 전 개체 Y 의 무가중 중앙값·q10~q90
  · 기준선 B2(무가중 평균) = 같은 top-K 의 산술 평균(점만 판정 밖 관찰)
  · 주대비 G1(게이트 · 조항 79 — 하나): Δ = MdAPE_M − MdAPE_B1 (풀드 70 · 짝지은
    개체(=군집) 붓스트랩 B=10,000 · seed [1007,0]) · 채택 ⇔ Δ < −2×SE_Δ
  · 악화 방향(+): 참조군 점예측의 절대 상대 오차 중앙값이 커지는 쪽 — 예측이 실측
    90일 누적에서 더 멀어지는 쪽이 악화다 (v5.3 게이트 부호 서명 1)
  · 방향 탐침: 측정 «전» 합성 문턱 검사(어긋나면 측정 없이 중단) · 측정 «후» ㉰㉱ 계수
  · 조항 59 구분: 데뷔급 / 머리 잘림(t0<7) / 꼬리 부족(t0>91) / 무신호 — 분모와 나란히
  · 판 넷 무접촉 — 이 러너는 전이 모형·scoreboard 를 만지지 않는다 (torch 미사용)

씀: python3 runners/coldstart1007.py            # → runners/out1007_coldstart.json
"""
import hashlib
import json
import os
import time

import numpy as np

TRI = "/Users/ax/wm_harvest/foundation/triples"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out1007_coldstart.json")
K = 12                       # 판정 K (사전등록 §2 — 관찰 K ∈ {8, 20})
K_MIN = 5                    # 참조군 빈약 하한 (도구 규격과 동일)
B_BOOT = 10000
SEED = [1007, 0]
QS = [0.10, 0.25, 0.50, 0.75, 0.90]


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ── 게이트 (v5.3 부호 서명) ──────────────────────────────────────────
def gate_g1(delta, se):
    """참조군 채택 게이트 — Δ = MdAPE_M − MdAPE_B1 · 채택 ⇔ Δ < −2×SE.
    악화 방향 = +Δ (참조군 오차 중앙값이 더 크다 = 점예측이 실측에서 더 멀다)."""
    return bool(delta < -2.0 * se)


def probe_pre():
    """측정 «전» 방향 탐침 — 합성 문턱 t>0 · 악화 극값(+2t)서 거짓 · 개선 극값(−2t)서 참."""
    t = 1.0
    se = t / 4.0                             # 문턱 = −2·se = −t/2
    bad_at_worse = gate_g1(+2.0 * t, se)     # 기대: False
    ok_at_better = gate_g1(-2.0 * t, se)     # 기대: True
    return {"합성 t": t, "악화 극값(+2t)에서 참(기대 거짓)": bad_at_worse,
            "개선 극값(−2t)에서 참(기대 참)": ok_at_better,
            "통과": (not bad_at_worse) and ok_at_better}


def probe_post(se):
    """측정 «후» 자료 탐침(조항 78 확장) — 실측 문턱 2·SE 로 ㉰㉱ 계수."""
    if se <= 0:
        return {"판정": "미판정(퇴화 문턱 — SE ≤ 0)", "㉰": None, "㉱": None}
    t = 2.0 * se                             # 실측 문턱 크기
    r0 = 1 if gate_g1(+2.0 * t, se) else 0   # ㉰ 악화 극값에서 참이 나온 게이트 수
    r1 = 0 if gate_g1(-2.0 * t, se) else 1   # ㉱ 개선 극값에서 거짓이 나온 게이트 수
    return {"㉰ 악화 극값에서 참": r0, "㉱ 개선 극값에서 거짓": r1,
            "판정": "통과" if (r0 == 0 and r1 == 0) else "🔴 강등(관찰)"}


# ── 가중 분위수 (역CDF 계단 — 결정적) ────────────────────────────────
def wquant(vals, wts, qs):
    v = np.asarray(vals, dtype=np.float64)
    w = np.asarray(wts, dtype=np.float64)
    if w.sum() <= 0:
        w = np.ones_like(w)
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w) / w.sum()
    return [float(v[np.searchsorted(cw, q, side="left").clip(0, len(v) - 1)]) for q in qs]


def mdape(pred, actual):
    pred = np.asarray(pred, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    return np.abs(pred - actual) / np.maximum(actual, 1.0)   # 개체별 APE 배열


def main():
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S")
    # 0. 부하 관문 — load1 > 10 이면 60초 대기 반복 (병행 팔 둘이 CPU 를 쓴다)
    waited = 0
    while os.getloadavg()[0] > 10.0:
        time.sleep(60)
        waited += 60
    # 1. 방향 탐침 — 측정 «전». 어긋나면 측정 없이 중단(값 보고 판정 고치는 길 봉쇄).
    pp = probe_pre()
    if not pp["통과"]:
        json.dump({"중단": "🔴 등록 결함 — 방향 탐침 실패(측정 안 함)", "탐침": pp},
                  open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return

    # 2. 자료 적재 + 개체별 최초 관측 행
    src = {"sao.npz": sha16(TRI + "/sao.npz"),
           "meta.jsonl": sha16(TRI + "/meta.jsonl"),
           "text_emb_qwen05b.npz": sha16(TRI + "/text_emb_qwen05b.npz"),
           "domains.json": sha16(TRI + "/domains.json"),
           "러너 자신": sha16(os.path.abspath(__file__))}
    z = np.load(TRI + "/sao.npz")
    S, O = z["S"].astype(np.float64), z["O"].astype(np.float64)   # 원 눈금
    meta = [json.loads(l) for l in open(TRI + "/meta.jsonl", encoding="utf-8")]
    doms = json.load(open(TRI + "/domains.json", encoding="utf-8"))
    E = np.load(TRI + "/text_emb_qwen05b.npz")["E"].astype(np.float64)
    first = {}
    for i, m in enumerate(meta):
        k = m["개체"]
        if k not in first or m["언제"] < meta[first[k]]["언제"]:
            first[k] = i                    # 동률 언제는 앞 행 유지(결정적)

    # 3. 조항 59 구분 — 데뷔 정렬 가능성(분모와 나란히)
    THETA, QUIET, MAXT0 = 1.0, 7, 91
    c59 = {"데뷔급": 0, "머리 잘림(t0<7)": 0, "꼬리 부족(t0>91)": 0, "무신호(전 구간<1)": 0}
    low_head = 0                            # 관찰 — head14/전체 ≤ 0.5 «저머리»
    for k, i in first.items():
        c = np.concatenate([S[i], O[i]])
        nz = np.where(c >= THETA)[0]
        if len(nz) == 0:
            c59["무신호(전 구간<1)"] += 1
            continue
        t0 = int(nz[0])
        if t0 < QUIET:
            c59["머리 잘림(t0<7)"] += 1
        elif t0 > MAXT0:
            c59["꼬리 부족(t0>91)"] += 1
        else:
            c59["데뷔급"] += 1
        if c[:14].mean() <= 0.5 * max(c.mean(), 1e-9):
            low_head += 1

    # 4. 풀 구성 — 도메인별 train 참조 풀 · val 평가 개체 (전부 최초 행)
    Y = {k: float(O[i][:90].sum()) for k, i in first.items()}     # 90일 누적(당일 포함)
    Cum = {k: np.cumsum(O[i][:90]) for k, i in first.items()}     # (도구와 같은 정의)
    pool = {d: [] for d in doms}
    evals = []
    for k, i in sorted(first.items()):
        m = meta[i]
        if m["분할"] == "train":
            pool[m["도메인"]].append(k)
        else:
            evals.append(k)
    En = E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-12)

    # 5. 예측 — M(참조군 가중) · B1(기후값) · B2(무가중 평균) + 관찰 K
    rows = []
    for k in evals:
        i = first[k]
        m = meta[i]
        d = m["도메인"]
        cand = pool[d]
        vy = np.array([Y[c] for c in cand])
        sims = En[[first[c] for c in cand]] @ En[i]
        order = np.argsort(-sims)
        row = {"개체": k, "도메인": d, "Y": Y[k], "풀 n": len(cand)}
        for kk in (8, K, 20):
            top = order[:kk]
            w = np.maximum(sims[top], 0.0)
            q = wquant(vy[top], w, QS)
            row["M_q50(K=%d)" % kk] = q[2]
            if kk == K:
                row["M_q10"], row["M_q90"] = q[0], q[4]
                row["B2_평균(K=%d)" % kk] = float(vy[top].mean())
                row["유사도 top1"] = float(sims[top][0])
        qb = wquant(vy, np.ones_like(vy), QS)
        row["B1_q50"], row["B1_q10"], row["B1_q90"] = qb[2], qb[0], qb[4]
        rows.append(row)

    ya = np.array([r["Y"] for r in rows])
    ape_m = mdape([r["M_q50(K=%d)" % K] for r in rows], ya)
    ape_b1 = mdape([r["B1_q50"] for r in rows], ya)
    ape_b2 = mdape([r["B2_평균(K=%d)" % K] for r in rows], ya)
    ape_k8 = mdape([r["M_q50(K=8)"] for r in rows], ya)
    ape_k20 = mdape([r["M_q50(K=20)"] for r in rows], ya)
    cov_m = float(np.mean([(r["M_q10"] <= r["Y"] <= r["M_q90"]) for r in rows]))
    cov_b1 = float(np.mean([(r["B1_q10"] <= r["Y"] <= r["B1_q90"]) for r in rows]))

    # 6. 주대비 — 짝지은 개체(=군집: 최초 행 1행/개체) 붓스트랩
    rng = np.random.default_rng(SEED)
    n = len(rows)
    deltas = np.empty(B_BOOT)
    for b in range(B_BOOT):
        ii = rng.integers(0, n, size=n)
        deltas[b] = np.median(ape_m[ii]) - np.median(ape_b1[ii])
    delta = float(np.median(ape_m) - np.median(ape_b1))
    se = float(deltas.std(ddof=1))
    thresh = -2.0 * se
    adopted = gate_g1(delta, se)
    margin = thresh - delta                  # 여유 > 0 ⇔ 통과 (사전등록 §3 정의)

    # 7. 조각 표 (조항 79 — 도메인별 · 전부 관찰)
    pieces = []
    same_sign = 0
    for d in doms:
        jj = [j for j, r in enumerate(rows) if r["도메인"] == d]
        if not jj:
            pieces.append({"도메인": d, "n": 0, "낙인": "칸 없음(val 0)"})
            continue
        jj = np.array(jj)
        dd = float(np.median(ape_m[jj]) - np.median(ape_b1[jj]))
        bs = np.empty(2000)
        for b in range(2000):
            ii = jj[rng.integers(0, len(jj), size=len(jj))]
            bs[b] = np.median(ape_m[ii]) - np.median(ape_b1[ii])
        sed = float(bs.std(ddof=1))
        pieces.append({"도메인": d, "n": int(len(jj)), "Δ": round(dd, 4),
                       "SE": round(sed, 4),
                       "t": round(dd / sed, 2) if sed > 0 else None,
                       "MdAPE_M": round(float(np.median(ape_m[jj])), 4),
                       "MdAPE_B1": round(float(np.median(ape_b1[jj])), 4)})
        if dd < 0:
            same_sign += 1

    out = {
        "사전등록": "docs/탐색/1007.md §1~§5",
        "시각": {"시작": t_start, "끝": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "부하 대기(초)": waited},
        "잰 소스 (조항 66)": src,
        "방향 탐침(측정 전)": pp,
        "분모 (조항 59)": {"고유 개체": len(first), "구분": c59,
                       "관찰 — 저머리(head14 ≤ 0.5×전체)": low_head,
                       "평가(val 최초 행)": n,
                       "참조 풀(도메인별 train)": {d: len(pool[d]) for d in doms},
                       "K 하한 미달 풀": [d for d in doms if len(pool[d]) < K_MIN]},
        "🔴 데뷔 정렬": ("미측정 — 데뷔급 %d/%d. 이 자료의 «최초 관측»은 데뷔가 아니라 "
                     "중간 진입이다(머리 잘림 %d). 채점은 «관측 정렬»(최초 관측일 포함 "
                     "앞 90일)로 한다 — 사전등록 §0 신고와 대조하라"
                     % (c59["데뷔급"], len(first), c59["머리 잘림(t0<7)"])),
        "판정 G1 (주대비 · 게이트)": {
            "MdAPE_M(참조군 가중 K=12)": round(float(np.median(ape_m)), 6),
            "MdAPE_B1(기후값)": round(float(np.median(ape_b1)), 6),
            "Δ (M − B1 · 악화 방향 +)": round(delta, 6),
            "SE_Δ (개체 붓스트랩 B=%d · seed %s)" % (B_BOOT, SEED): round(se, 6),
            "문턱 (−2×SE)": round(thresh, 6),
            "여유 (문턱 − Δ · >0 ⇔ 통과)": round(margin, 6),
            "채택(참조군 정본)": adopted,
            "분기": ("참조군 정본 — wm_coldstart 분위수 = 참조군 가중 분위수" if adopted
                   else "기후값 폴백 — wm_coldstart 분위수 정본 = 도메인 기후값 · "
                        "참조군은 유사 사례 명단(관찰)로 동봉")},
        "자료 탐침(측정 후 · 조항 78 확장)": probe_post(se),
        "관찰": {
            "MdAPE_B2(무가중 평균 K=12)": round(float(np.median(ape_b2)), 6),
            "MdAPE_M(K=8)": round(float(np.median(ape_k8)), 6),
            "MdAPE_M(K=20)": round(float(np.median(ape_k20)), 6),
            "80% 구간 실측 덮개율 — M(q10~q90)": round(cov_m, 4),
            "80% 구간 실측 덮개율 — B1(q10~q90)": round(cov_b1, 4),
            "조각 표 (조항 79 · 도메인별 — 관찰)": pieces,
            "동부호 수(Δ<0 도메인)": same_sign},
        "판 넷": "무접촉 — 전이 모형·scoreboard·리더보드 이 러너는 안 만진다",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"Δ": round(delta, 6), "SE": round(se, 6), "채택": adopted,
                      "MdAPE_M": round(float(np.median(ape_m)), 4),
                      "MdAPE_B1": round(float(np.median(ape_b1)), 4),
                      "덮개율 M": cov_m, "덮개율 B1": cov_b1}, ensure_ascii=False))


if __name__ == "__main__":
    main()
