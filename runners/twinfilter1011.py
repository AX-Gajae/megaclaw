# -*- coding: utf-8 -*-
"""사이클 1011 — wm_coldstart 쌍둥이 필터 백테스트 (사전등록 docs/탐색/1011.md · 이 커밋에서 언다).

물음(#142 ⑥-1 · 1007 §11 재재등록 조건): «작품 동일성»을 사전등록 정의로 고정하고 쌍둥이를
풀에서 걸어낸 뒤에도, 참조군 가중이 도메인 기후값을 유의하게 이기는가(G1′) — 이기면 참조군
정본 복권, 못 이기면 기후값 정본 존속.

쌍둥이 정의(사전등록 §1 — 정의 «자체»가 등록 대상):
  쌍둥이(v, t) ⇔ ㉮ 곡선 동일성 — v·t «최초 관측» 행의 181일 연결 곡선(S 90칸 + O 91칸 ·
    원 눈금)이 전 칸 비트 일치(np.array_equal) — 같은 작품이면 같은 위키 곡선(#142 ⑥-1 근거)
  ∨ ㉯ 임베딩 cos(v, t) ≥ τ = 0.9999 — «후보» 자(텍스트 재식별 신호 · #142 명기 미러)
  τ·성분 민감도는 관찰만 — 격자 모양 주장 금지(조항 68 · K 격자 8/12/20 도 동일).

주대비 G1′(조항 79 — 하나 · 1007 G1 규격 미러 · 모집단 = 쌍둥이-제외 풀 = «진짜 신작» 대리):
  Δ′ = MdAPE_M′ − MdAPE_B1 (val 70 유지 · B1 무변 · 풀 쪽 쌍둥이 제거 후 top-K=12)
  SE′ = 짝지은 개체(=군집) 붓스트랩 B=10,000 · seed [1011,0] (새 스트림 — [1007,*] 재사용 금지)
  순열 p = 개체 안 (APE_M′, APE_B1) 라벨 부호 뒤집기 B=10,000 · seed [1011,1] · 단측(개선
    방향) — 보조 눈금(판정 밖 · 관찰)
  복권 ⇔ Δ′ < −2×SE′ · SE′ ≤ 0 → 미판정(퇴화 문턱) · 여유 = 문턱 − Δ′ (>0 ⇔ 통과 — 1007 §3)
  악화 방향 = +Δ′ (참조군 점예측의 절대 상대 오차 중앙값이 커지는 쪽 = 실측 90일 누적에서
    더 멀어지는 쪽) — v5.3 부호 서명 · 방향 탐침(측정 전) · 자료 탐침 ㉰㉱(측정 후)

위생: CPU 4스레드(임포트 전 env) · load1>10 대기 · 부칙 4(assert_epoch) · 조항 66(잰 소스
  등록 기재값 대조 — 불일치면 측정 없이 중단) · 판 무접촉 증명(판 사슬 sha 전/후 무변) ·
  앵커(v5.2 — 결정 항등 · 재추첨 0): Δ′ 등 결정론 4칸 대 커밋된 out1007_twin_supp 6자리.

씀: python3 runners/twinfilter1011.py           # → runners/out1011_twinfilter.json
"""
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "4")               # CPU 4스레드 — numpy 임포트 «전»
import hashlib
import json
import sys
import time

import numpy as np

REPO = "/Users/ax/world_model"
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from pretrain.epoch_guard import assert_epoch, EpochMismatch   # 부칙 4

TRI = "/Users/ax/wm_harvest/foundation/triples"
TRANS = "/Users/ax/wm_harvest/foundation/transition"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out1011_twinfilter.json")
K = 12                        # 판정 K (관찰 K ∈ {8, 20} — 모양 주장 금지)
K_MIN = 5
TAU = 0.9999                  # ㉯ «후보» 자 (사전 명기 · 관찰 τ ∈ {0.999, 0.9995})
B_BOOT = 10000
B_PERM = 10000
SEED_BOOT = [1011, 0]         # 🔴 새 seed 스트림 — 1007·[1007,1] 재사용 금지
SEED_PERM = [1011, 1]
SEED_PIECE = [1011, 2]
QS = [0.10, 0.25, 0.50, 0.75, 0.90]
EPOCH = "3a5c2543a55f1dab"    # 부칙 4 — 등록 시대(1004 manifest · 1009 배포 0 존속)

# 조항 66 — 잰 소스 등록 기재값 (불일치면 측정 없이 중단)
REG_SHA = {
    TRI + "/sao.npz": "f120013017dcf512",
    TRI + "/meta.jsonl": "f74f94235bc5f032",
    TRI + "/text_emb_qwen05b.npz": "c4128e73c8ea52ca",
    TRI + "/domains.json": "ef6affbf7bee39ad",
    REPO + "/runners/out1007_twin_supp.json": "35cc8aed43dec54a",
    REPO + "/runners/out1007_coldstart.json": "be3eace908775d83",
}
# 판 무접촉 증명 대상 — 전/후 sha 무변 실측 게재 (하네스 층 사이클 · scoreboard 무변)
PAN = {
    TRANS + "/ensemble_manifest.json": "3a5c2543a55f1dab",
    TRANS + "/conformal.json": "d8f40489c9341302",
    TRANS + "/leaderboard.json": "f15a9907fb3ef6b9",
    TRANS + "/report.json": "6dfb0a4ff2935de0",
    REPO + "/pretrain/scoreboard.py": "1503a48a174d881d",
    REPO + "/data/lab/1005_판_후.json": "01214fc2a7ff8f31",
}
# 앵커 (v5.2 — 결정 항등 검사 · 재추첨 성분 0 · 문턱 = 6자리 게재 자리 일치 + 원값 차 게재):
# 커밋된 out1007_twin_supp.json 「4수 (6자리)」의 결정론 칸. 사전등록 §0 계수 실측 —
# 정의 합집합(㉮∨㉯)이 cos 단독(㉯)과 같은 집합(30 val · 117쌍 · 배타 0)이라 항등이 기대다.
# 깨지면 G1′ 은 「관찰 강등」 + 귀속을 out 에 적는다.
ANCHOR = {"MdAPE_M′": 0.717051, "MdAPE_B1": 0.765216, "Δ′": -0.048166, "덮개율′": 0.614286}


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ── 게이트 (v5.3 부호 서명 — 1007 자구 미러) ─────────────────────────
def gate_g1p(delta, se):
    """복권 게이트 — Δ′ = MdAPE_M′ − MdAPE_B1 · 복권 ⇔ Δ′ < −2×SE′.
    악화 방향 = +Δ′ (참조군 오차 중앙값이 더 크다 = 점예측이 실측 90일 누적에서 더 멀다)."""
    return bool(delta < -2.0 * se)


def probe_pre():
    """측정 «전» 방향 탐침 — 합성 문턱 t>0 · 악화 극값(+2t)서 거짓 · 개선 극값(−2t)서 참."""
    t = 1.0
    se = t / 4.0
    bad_at_worse = gate_g1p(+2.0 * t, se)
    ok_at_better = gate_g1p(-2.0 * t, se)
    return {"합성 t": t, "악화 극값(+2t)에서 참(기대 거짓)": bad_at_worse,
            "개선 극값(−2t)에서 참(기대 참)": ok_at_better,
            "통과": (not bad_at_worse) and ok_at_better}


def probe_post(se):
    """측정 «후» 자료 탐침(조항 78 확장) — 실측 문턱 2·SE′ 로 ㉰㉱ 계수."""
    if se <= 0:
        return {"판정": "미판정(퇴화 문턱 — SE ≤ 0)", "㉰": None, "㉱": None}
    t = 2.0 * se
    r0 = 1 if gate_g1p(+2.0 * t, se) else 0
    r1 = 0 if gate_g1p(-2.0 * t, se) else 1
    return {"㉰ 악화 극값에서 참": r0, "㉱ 개선 극값에서 거짓": r1,
            "판정": "통과" if (r0 == 0 and r1 == 0) else "🔴 강등(관찰)"}


def wquant(vals, wts, qs):
    """가중 분위수(역CDF 계단 · 결정적) — 1007 언 러너와 같은 정의."""
    v = np.asarray(vals, dtype=np.float64)
    w = np.asarray(wts, dtype=np.float64)
    if w.sum() <= 0:
        w = np.ones_like(w)
    o = np.argsort(v)
    v, w = v[o], w[o]
    cw = np.cumsum(w) / w.sum()
    return [float(v[np.searchsorted(cw, q, side="left").clip(0, len(v) - 1)]) for q in qs]


def ape(pred, actual):
    pred = np.asarray(pred, dtype=np.float64)
    actual = np.asarray(actual, dtype=np.float64)
    return np.abs(pred - actual) / np.maximum(actual, 1.0)


def fail_out(payload):
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print(json.dumps({"중단": payload.get("중단")}, ensure_ascii=False))


def main():
    t_start = time.strftime("%Y-%m-%dT%H:%M:%S")
    # 0. 부하 관문 — load1 > 10 이면 60초 대기 반복
    waited = 0
    while os.getloadavg()[0] > 10.0:
        time.sleep(60)
        waited += 60
    # 1. 방향 탐침 — 측정 «전». 어긋나면 측정 없이 중단.
    pp = probe_pre()
    if not pp["통과"]:
        fail_out({"중단": "🔴 등록 결함 — 방향 탐침 실패(측정 안 함)", "탐침": pp})
        return
    # 2. 부칙 4 — 시대 고정 (여는-시점 실측 · 게재는 반환값)
    try:
        epoch_stamp = assert_epoch(EPOCH)
    except EpochMismatch as e:
        fail_out({"중단": "🔴 시대 불일치 — 측정 없이 중단(부칙 4)", "사유": str(e)})
        return
    # 3. 조항 66 — 잰 소스 + 판 사슬 «전» sha 실측 대조 (불일치면 측정 없이 중단)
    src = {p: sha16(p) for p in REG_SHA}
    pan_before = {p: sha16(p) for p in PAN}
    bad = ([p for p, s in src.items() if s != REG_SHA[p]] +
           [p for p, s in pan_before.items() if s != PAN[p]])
    if bad:
        fail_out({"중단": "🔴 잰 소스/판 사슬 sha 불일치 — 측정 없이 중단(조항 66)",
                  "불일치": bad, "실측": src, "판 사슬": pan_before})
        return
    src[os.path.abspath(__file__)] = sha16(os.path.abspath(__file__))   # 러너 자신

    # 4. 적재 · 최초 관측 행 색인 (1007 언 러너 자구 미러)
    z = np.load(TRI + "/sao.npz")
    S, O = z["S"].astype(np.float64), z["O"].astype(np.float64)
    meta = [json.loads(l) for l in open(TRI + "/meta.jsonl", encoding="utf-8")]
    doms = json.load(open(TRI + "/domains.json", encoding="utf-8"))
    E = np.load(TRI + "/text_emb_qwen05b.npz")["E"].astype(np.float64)
    first = {}
    for i, m in enumerate(meta):
        k = m["개체"]
        if k not in first or m["언제"] < meta[first[k]]["언제"]:
            first[k] = i                       # 동률 언제는 앞 행(결정적)
    Y = {k: float(O[i][:90].sum()) for k, i in first.items()}
    pool = {d: [] for d in doms}
    evals = []
    for k, i in sorted(first.items()):
        if meta[i]["분할"] == "train":
            pool[meta[i]["도메인"]].append(k)
        else:
            evals.append(k)
    En = E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-12)

    # 5. 쌍둥이 판정(사전등록 정의) + 예측 — 주대비 + 관찰 변형들
    #    einsum 사용(macOS Accelerate matmul 허위 FPE 경고 회피 — wm_tools 전례) +
    #    조항 59 위생: NaN/Inf 0 · |cos| ≤ 1+1e-12 전수 검사
    variants = {"㉮∨㉯ (판정)": None, "㉮만 (관찰)": None, "㉯만 (관찰)": None,
                "㉮∨cos≥0.999 (관찰)": None, "㉮∨cos≥0.9995 (관찰)": None}
    preds = {vn: [] for vn in variants}        # 개체별 q50 (판정 변형은 q10/q90 도)
    twin_pairs = []                            # 명단(#142 ⑥-1 ㉯ — out 게재)
    n_twin_val = {vn: 0 for vn in variants}
    n_pairs = {vn: 0 for vn in variants}
    b1_rows = []
    kk_preds = {8: [], 20: []}                 # 관찰 K (판정 필터 ㉮∨㉯ 위에서)
    sims_bad = 0
    pool_after_min = {}
    for kv in evals:
        i = first[kv]
        d = meta[i]["도메인"]
        cand = pool[d]
        idxs = [first[c] for c in cand]
        sims = np.einsum("ij,j->i", En[idxs], En[i])
        if not np.all(np.isfinite(sims)) or float(np.max(np.abs(sims))) > 1.0 + 1e-12:
            sims_bad += 1
        cv = np.concatenate([S[i], O[i]])
        curve_tw = np.array([np.array_equal(np.concatenate([S[j], O[j]]), cv)
                             for j in idxs])
        cos_tw = sims >= TAU
        masks = {"㉮∨㉯ (판정)": curve_tw | cos_tw,
                 "㉮만 (관찰)": curve_tw,
                 "㉯만 (관찰)": cos_tw,
                 "㉮∨cos≥0.999 (관찰)": curve_tw | (sims >= 0.999),
                 "㉮∨cos≥0.9995 (관찰)": curve_tw | (sims >= 0.9995)}
        vy = np.array([Y[c] for c in cand])
        for vn, rm in masks.items():
            n_pairs[vn] += int(rm.sum())
            if rm.any():
                n_twin_val[vn] += 1
            keep = ~rm
            vk, sk = vy[keep], sims[keep]
            order = np.argsort(-sk)[:K]
            w = np.maximum(sk[order], 0.0)
            q = wquant(vk[order], w, QS)
            if vn == "㉮∨㉯ (판정)":
                preds[vn].append({"q50": q[2], "q10": q[0], "q90": q[4]})
                pool_after_min[d] = min(pool_after_min.get(d, 10 ** 9), int(keep.sum()))
                for kk in (8, 20):             # 관찰 K — 같은 필터
                    ok = np.argsort(-sk)[:kk]
                    kk_preds[kk].append(
                        wquant(vk[ok], np.maximum(sk[ok], 0.0), [0.5])[0])
                for j_local in np.where(rm)[0]:   # 명단 (판정 정의 쌍만)
                    gt = cand[j_local]
                    twin_pairs.append({
                        "val": kv, "train": gt, "도메인": d,
                        "성분": ("㉮㉯" if (curve_tw[j_local] and cos_tw[j_local])
                               else ("㉮" if curve_tw[j_local] else "㉯")),
                        "cos": round(float(sims[j_local]), 6),
                        "Y_train": Y[gt]})
            else:
                preds[vn].append({"q50": q[2]})
        qb = wquant(vy, np.ones_like(vy), QS)  # B1 무변 (1007 자구)
        b1_rows.append({"q50": qb[2], "q10": qb[0], "q90": qb[4]})

    ya = np.array([Y[kv] for kv in evals])
    ape_m2 = ape([r["q50"] for r in preds["㉮∨㉯ (판정)"]], ya)
    ape_b1 = ape([r["q50"] for r in b1_rows], ya)
    md_m2, md_b1 = float(np.median(ape_m2)), float(np.median(ape_b1))
    delta = md_m2 - md_b1
    cov2 = float(np.mean([(r["q10"] <= y <= r["q90"])
                          for r, y in zip(preds["㉮∨㉯ (판정)"], ya)]))
    cov_b1 = float(np.mean([(r["q10"] <= y <= r["q90"])
                            for r, y in zip(b1_rows, ya)]))
    n_ape0 = int((ape_m2 == 0.0).sum())

    # 5-앵커. 결정 항등 4칸 대 커밋된 out1007_twin_supp (v5.2 — 재추첨 0 · 항등 형)
    got_anchor = {"MdAPE_M′": round(md_m2, 6), "MdAPE_B1": round(md_b1, 6),
                  "Δ′": round(delta, 6), "덮개율′": round(cov2, 6)}
    anchor_ok = {kk: bool(got_anchor[kk] == ANCHOR[kk]) for kk in ANCHOR}
    anchor_pass = all(anchor_ok.values())

    # 6. 주대비 통계 — 짝지은 개체(=군집) 붓스트랩 SE′ · 순열 p (새 seed 스트림)
    rng = np.random.default_rng(SEED_BOOT)
    n = len(evals)
    boots = np.empty(B_BOOT)
    for b in range(B_BOOT):
        ii = rng.integers(0, n, size=n)
        boots[b] = np.median(ape_m2[ii]) - np.median(ape_b1[ii])
    se = float(boots.std(ddof=1))
    thresh = -2.0 * se
    margin = thresh - delta                    # 여유 > 0 ⇔ 통과 (1007 §3 부호 규약)
    degen = (se <= 0)
    adopted = (not degen) and gate_g1p(delta, se)
    rngp = np.random.default_rng(SEED_PERM)
    signs = rngp.integers(0, 2, size=(B_PERM, n)).astype(bool)
    Tb = np.empty(B_PERM)
    for b in range(B_PERM):
        s = signs[b]
        aa = np.where(s, ape_b1, ape_m2)
        bb = np.where(s, ape_m2, ape_b1)
        Tb[b] = np.median(aa) - np.median(bb)
    p_perm = float((1 + int((Tb <= delta).sum())) / (B_PERM + 1.0))

    # 7. 조각 표 (조항 79 — 도메인별 · 전부 관찰 · seed [1011,2])
    rngc = np.random.default_rng(SEED_PIECE)
    pieces = []
    same_sign = 0
    dom_of = [meta[first[kv]]["도메인"] for kv in evals]
    for d in doms:
        jj = np.array([j for j, dd in enumerate(dom_of) if dd == d])
        if len(jj) == 0:
            pieces.append({"도메인": d, "n": 0, "낙인": "칸 없음(val 0)"})
            continue
        dd_ = float(np.median(ape_m2[jj]) - np.median(ape_b1[jj]))
        bs = np.empty(2000)
        for b in range(2000):
            ii = jj[rngc.integers(0, len(jj), size=len(jj))]
            bs[b] = np.median(ape_m2[ii]) - np.median(ape_b1[ii])
        sed = float(bs.std(ddof=1))
        pieces.append({"도메인": d, "n": int(len(jj)), "Δ′": round(dd_, 4),
                       "SE": round(sed, 4),
                       "t": round(dd_ / sed, 2) if sed > 0 else None,
                       "MdAPE_M′": round(float(np.median(ape_m2[jj])), 4),
                       "MdAPE_B1": round(float(np.median(ape_b1[jj])), 4)})
        if dd_ < 0:
            same_sign += 1

    # 8. 관찰 격자 — 정의 성분·τ·K (조항 68 — 모양 주장 금지 · 점만)
    grid = {}
    for vn in variants:
        if vn == "㉮∨㉯ (판정)":
            continue
        am = ape([r["q50"] for r in preds[vn]], ya)
        grid[vn] = {"MdAPE": round(float(np.median(am)), 6),
                    "Δ(대 B1)": round(float(np.median(am)) - md_b1, 6),
                    "쌍둥이 보유 val": n_twin_val[vn], "제거 쌍": n_pairs[vn]}
    for kk in (8, 20):
        am = ape(kk_preds[kk], ya)
        grid["K=%d (판정 필터 ㉮∨㉯ · 관찰)" % kk] = {
            "MdAPE": round(float(np.median(am)), 6),
            "Δ(대 B1)": round(float(np.median(am)) - md_b1, 6)}

    # 9. 판 사슬 «후» 재실측 — 전=후 무변 증명
    pan_after = {p: sha16(p) for p in PAN}
    pan_same = bool(pan_before == pan_after)

    out = {
        "사전등록": "docs/탐색/1011.md §0~§6",
        "시각": {"시작": t_start, "끝": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "부하 대기(초)": waited},
        "시대(부칙 4 — 게재는 실측 반환값)": epoch_stamp,
        "잰 소스 (조항 66 — 등록 기재값 전 칸 일치)": src,
        "방향 탐침(측정 전)": pp,
        "쌍둥이 정의(사전등록 §1)": {
            "㉮ 곡선 동일성": "최초 관측 행 181일(S90+O91 · 원 눈금) 전 칸 비트 일치",
            "㉯ cos ≥ τ": TAU, "판정 필터": "㉮ ∨ ㉯ (풀 쪽 제거 · val 70 유지 · B1 무변)"},
        "분모 (조항 59·79)": {
            "val": n, "쌍둥이 보유 val(판정 정의)": n_twin_val["㉮∨㉯ (판정)"],
            "제거 쌍(판정 정의)": n_pairs["㉮∨㉯ (판정)"],
            "제거 후 도메인별 최소 풀": pool_after_min,
            "K 하한(5) 미달 풀": [d for d, v in pool_after_min.items() if v < K_MIN],
            "제외 후 APE 정확 0": n_ape0,
            "데뷔 정렬": "미측정 존속 — 1007 실측 데뷔급 0/704 (원천 sha 동일 · 관측 정렬 채점)"},
        "판정 G1′ (주대비 · 게이트)": {
            "MdAPE_M′(쌍둥이 제외 · K=12)": round(md_m2, 6),
            "MdAPE_B1(기후값 · 무변)": round(md_b1, 6),
            "Δ′ (M′ − B1 · 악화 방향 +)": round(delta, 6),
            "SE′ (개체 붓스트랩 B=%d · seed %s)" % (B_BOOT, SEED_BOOT): round(se, 6),
            "순열 p (부호 뒤집기 B=%d · seed %s · 단측 — 보조 눈금·판정 밖)"
            % (B_PERM, SEED_PERM): round(p_perm, 6),
            "문턱 (−2×SE′)": round(thresh, 6),
            "여유 (문턱 − Δ′ · >0 ⇔ 통과)": round(margin, 6),
            "복권(참조군 정본)": adopted,
            "지위": ("관찰 강등 — 앵커 불일치(귀속을 관찰에)" if not anchor_pass else
                   ("미판정(퇴화 문턱)" if degen else "판정")),
            "분기": ("참조군 정본 복권 — 쌍둥이 필터 상시 적용" if adopted
                   else "기후값 정본 존속 — 참조군은 참고 칸 · ⚠ 은 이 out 을 read")},
        "자료 탐침(측정 후 · 조항 78 확장)": probe_post(se),
        "앵커 (v5.2 — 결정 항등 · 재추첨 0 · 대 out1007_twin_supp 6자리)": {
            "목표": ANCHOR, "실측": got_anchor, "일치": anchor_ok,
            "전 칸 일치": anchor_pass,
            "SE′ 대 [1007,1] 0.061541 (씨앗 간 — 관찰 · 앵커 아님)": round(se, 6)},
        "관찰": {
            "80% 구간 실측 덮개율 — M′(q10~q90)": round(cov2, 4),
            "80% 구간 실측 덮개율 — B1(q10~q90)": round(cov_b1, 4),
            "정의 성분·τ·K 격자 (조항 68 — 모양 주장 금지 · 점만)": grid,
            "조각 표 (조항 79 · 도메인별 — 관찰)": pieces,
            "동부호 수(Δ′<0 도메인)": same_sign,
            "위생 — cos NaN/Inf/범위 위반 개체 수": sims_bad},
        "쌍둥이 명단 (판정 정의 · #142 ⑥-1 ㉯ — val·train·성분·cos·Y_train)": twin_pairs,
        "판 무접촉 증명 (전/후 sha)": {"전": pan_before, "후": pan_after,
                                "무변": pan_same},
        "판 넷": "무접촉 — 전이 모형·scoreboard·리더보드·LODO 이 러너는 안 만진다",
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"Δ′": round(delta, 6), "SE′": round(se, 6),
                      "순열 p": round(p_perm, 6), "여유": round(margin, 6),
                      "복권": adopted, "앵커": anchor_pass, "판 무변": pan_same,
                      "쌍둥이 val": n_twin_val["㉮∨㉯ (판정)"],
                      "쌍": n_pairs["㉮∨㉯ (판정)"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
