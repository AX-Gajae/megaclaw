# -*- coding: utf-8 -*-
"""확증 1000 러너 — 표적 «웹툰» · 씨앗 앙상블(분위수 평균) (사전등록 docs/탐색/1000.md 에서 언 코드).

주대비 «하나»(조항 79): 현행 레시피 씨앗 1001~1005 5모형의 «분위수 평균 앙상블»의 웹툰 q50 효과.
비교 기준 = 같은 씨앗 «단일모형»의 도메인별 씨앗 중앙값 M(d) = median_s MdAPE(현행,s,d).
배포(seed 997) 모형과의 비교는 «관찰»로만 — 그 비교는 999 §9-3 윗꼬리 관찰에서 «나온» 가설이라
확증에 못 쓴다(순환 금지).

999 러너는 P3 체크포인트만 저장했다 — 현행 레시피 5모형은 «재학습»한다(같은 학습 루프 · 같은
씨앗 → 재현 항등 검사로 999 실측과 4자리 대조). 앙상블은 씨앗·구성원이 고정이라 자체 지터가
정의상 0 — 불확실성은 개체 붓스트랩 SE 로만 잰다.

판정(v5.1 5-다 · 사전등록 §3~§4):
  앵커  전 도메인 |median_s MdAPE(현행,s,d) − 리더보드_d| ≤ J_d(999) · 덮개율 ≤ J_cov(999)=0.0378
        (999 실측 J_d 표 인용 — out999_confirm.json sha 359420568d14f724 · v5.1 재사용 조항)
        — 깨지면 전부 「관찰」 강등
  ㉠  −Δ웹툰 > max(J_웹툰 0.0343, 2×SE_웹툰) · Δ웹툰 = MdAPE(앙상블,웹툰) − M(웹툰)
  ㉡  판정 7 도메인(게임·만화 n_val<30 제외) 중 Δ_d > max(J_d, 2.6×SE_d) 인 곳 0
  ㉢  Δ덮개율 ≥ −max(J_cov, 2×SE_cov)
헤드라인: 웹툰 60 개체 짝지은 붓스트랩 SE + 부호뒤집기 순열 p (B=10,000 · seed 1000 스트림 —
앙상블 열을 5행 복제해 999 와 같은 «묶음 뒤집기» 검정을 쓴다).
조항 78: 게이트 탐침 — 자료 유래 격자(실측·부호반전·0·±2문턱)에서 참/거짓 둘 다 나오나.

🔴 CPU 전용 4스레드 · 유료 API 0 · MPS 0 · 배포 파일 무변경(읽기만) · 각 학습 전 load1 > 10 이면
60초 대기 반복. 씀: python3 runners/ensemble1000.py
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.transition import Transition, pinball  # noqa: E402

torch.set_num_threads(4)
SEEDS = (1001, 1002, 1003, 1004, 1005)          # 사전등록 §2 — 999 와 같은 씨앗 · 997 금지 유지
STAT_SEED = 1000                                 # 통계 씨앗 (스트림: [1000,1,k] · [1000,2] · [1000,3])
N_BOOT = N_PERM = 10000
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
TARGET = "웹툰"
SMALL = ("게임", "만화")                          # n_val < 30 — ㉠㉡ 판정 제외 (관찰)
MULT_OTHER = 2.6                                 # v5.1 ㉡ 다중비교 몫

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "ensemble1000")
OUT_JSON = os.path.join(REPO, "runners", "out1000_ensemble.json")
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

# 조항 66 — 앵커·전판·자료 원천은 sha 가 사전등록과 일치해야 쓴다 (어긋나면 즉시 중단)
EXPECT_SHA = {
    os.path.join(REPO, "runners/out999_confirm.json"): "359420568d14f724",   # J_d 표 원천
    os.path.join(REPO, "data/lab/999_판_후.json"): "ea37c5c09e7aaaad",        # 전판 (인용)
    os.path.join(TROUT, "leaderboard.json"): "da73fed24780e355",
    os.path.join(TROUT, "model.pt"): "5122c2eb3c21bfbd",
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
}


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def prog(rec):
    os.makedirs(EXP, exist_ok=True)
    with open(os.path.join(EXP, "progress.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(rec, t=time.strftime("%H:%M:%S")), ensure_ascii=False) + "\n")


def load_gate():
    """각 학습 전 — load1 > 10 이면 60초 대기 반복 (불가침 작업 보호)."""
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60
    return waited


# ── 자료 (999 러너와 자구까지 같은 전처리 — 재현 항등의 전제) ──────────
z = np.load(os.path.join(TRI, "sao.npz"))
DOMAINS = json.load(open(os.path.join(TRI, "domains.json"), encoding="utf-8"))
S = np.log1p(z["S"].astype(np.float64)).astype(np.float32)
O = np.log1p(z["O"].astype(np.float64)).astype(np.float32)
base = S.mean(axis=1, keepdims=True)
Sc = S - base
R = O - base
dom_id = z["dom_id"].astype(np.int64)
split = z["split"]
doy = z["doy"].astype(np.float32)
sin = np.sin(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
cos = np.cos(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
year = ((z["year"].astype(np.float32) - 2013.0) / 10.0)[:, None]
E = np.load(os.path.join(TRI, "text_emb_qwen05b.npz"))["E"].astype(np.float32)
assert len(E) == len(S), "🔴 텍스트 임베딩 행 수 불일치"
n_dom = int(dom_id.max()) + 1
onehot = np.zeros((len(S), n_dom), dtype=np.float32)
onehot[np.arange(len(S)), dom_id] = 1.0
C_FULL = np.concatenate([onehot, sin, cos, year, base, E], axis=1).astype(np.float32)
TR_IDX = np.where(split == 0)[0]
VA_IDX = np.where(split == 1)[0]
DOM_VA = dom_id[VA_IDX]


def eval_pred(pred):
    """(n,91,5) 잔차 눈금 예측 → (ape, cover_ent, per_dom, cover, 전체 MdAPE) — 999 평가식."""
    b = base[VA_IDX]
    cum_true = np.expm1(R[VA_IDX] + b).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + b).sum(axis=1)
    ape = np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1.0)
    cover_ent = ((R[VA_IDX] >= pred[..., 0]) & (R[VA_IDX] <= pred[..., 4])).mean(axis=1)
    per_dom = {DOMAINS[d]: float(np.median(ape[DOM_VA == d])) for d in range(n_dom)}
    return ape, cover_ent, per_dom, float(cover_ent.mean()), float(np.median(ape))


def predict(model):
    model.eval()
    with torch.no_grad():
        xe = torch.from_numpy(np.concatenate([Sc[VA_IDX], C_FULL[VA_IDX]], axis=1))
        return model(xe).numpy()


def train_cur(seed):
    """현행 레시피 — confirm999.train_cfg(cfg={}) 와 같은 연산 순서 (재현 항등의 전제)."""
    d_in = Sc.shape[1] + C_FULL.shape[1]
    torch.manual_seed(seed)
    model = Transition(d_in, hidden=HIDDEN)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    t0 = time.time()
    loss = None
    for step in range(STEPS):
        rng = np.random.default_rng([seed, step])
        ii = TR_IDX[rng.integers(0, len(TR_IDX), size=BATCH)]
        x = torch.from_numpy(np.concatenate([Sc[ii], C_FULL[ii]], axis=1))
        r = torch.from_numpy(R[ii])
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
    return model, round(float(loss.item()), 5), round(time.time() - t0, 1)


def boot_delta_ens(A_cur, a_ens, rng, agg):
    """짝지은 개체 붓스트랩 — Δ* = agg(앙상블) − median_s agg(단일 s) 함수 «전체» 재계산.
    A_cur (K,n) · a_ens (n,). agg: np.median(도메인 MdAPE) 또는 np.mean(덮개율)."""
    n = A_cur.shape[1]
    out = np.empty(N_BOOT)
    done = 0
    while done < N_BOOT:
        m = min(2000, N_BOOT - done)
        idx = rng.integers(0, n, size=(m, n))
        cur = np.median(agg(A_cur[:, idx], axis=2), axis=0)      # (m,)
        ens = agg(a_ens[idx], axis=1)                             # (m,)
        out[done:done + m] = ens - cur
        done += m
    return out


def gate_probe(fn, obs, thr):
    """조항 78 탐침 — 자료 유래 격자에서 참/거짓이 둘 다 나오는지 (리터럴 금지)."""
    grid = [obs, -obs, 0.0, 2.0 * thr, -2.0 * thr]
    vals = [bool(fn(g, thr)) for g in grid]
    return {"격자": [round(g, 6) for g in grid], "결과": vals,
            "참 나옴": any(vals), "거짓 나옴": not all(vals)}


def main():
    t_all = time.time()
    # ── 조항 66 — 원천 sha 검증 (앵커 재사용은 sha 일치가 조건 · v5.1) ──
    sha_verify = {}
    for p, want in EXPECT_SHA.items():
        got = sha16(p) if os.path.exists(p) else "없음"
        sha_verify[os.path.basename(p)] = {"기대": want, "실측": got, "일치": got == want}
    if not all(v["일치"] for v in sha_verify.values()):
        out = {"판정어": "중단 — 원천 sha 불일치 (조항 66 · 앵커 인용 불가)",
               "sha 검증": sha_verify}
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    o999 = json.load(open(os.path.join(REPO, "runners/out999_confirm.json"), encoding="utf-8"))
    J999 = o999["지터 바닥 J_d (현행 5씨앗 |Δ리더보드| 최대 · v5.1)"]
    J = {d: float(J999[d]) for d in ROSTER}
    J_cov = float(J999["덮개율"])
    ref999 = o999["씨앗별 결과 (관찰 120칸 = 씨앗5×구성2×12)"]["현행"]
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    pre_dom = {d: lb["도메인별"][d]["transition"] for d in ROSTER}
    전판 = json.load(open(os.path.join(REPO, "data/lab/999_판_후.json"), encoding="utf-8"))
    pre_cover = 전판["④90% 덮개율"]["직접 재계산"]          # 0.7242 — 커밋된 판이 정본 (조항 81)

    out = {"러너": "runners/ensemble1000.py", "표적": TARGET,
           "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
           "sha 검증(사전등록 대조)": sha_verify,
           "러너 자신": sha16(os.path.abspath(__file__)),
           "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
                  "학습 씨앗": list(SEEDS), "통계 씨앗": STAT_SEED,
                  "threads": torch.get_num_threads(), "device": "cpu",
                  "B": {"붓스트랩": N_BOOT, "순열": N_PERM},
                  "앙상블": "5모형 (91,5) 분위수 텐서 산술 평균 — 자체 지터 정의상 0"},
           "앵커 문턱(사전등록 §3 · 999 J_d 표 재사용 · sha 359420568d14f724)": dict(
               {d: J[d] for d in ROSTER}, 덮개율=J_cov)}

    # ── 학습 5회 — 한 번에 하나 · load 관문 · 체크포인트 보존 ─────────
    ape_s, cov_s, mdape_s, cover_s, meta_s, preds, ckpts = {}, {}, {}, {}, {}, {}, {}
    os.makedirs(EXP, exist_ok=True)
    for sd in SEEDS:
        waited = load_gate()
        model, pin, sec = train_cur(sd)
        pred = predict(model)
        a, ce, pd, cv, tot = eval_pred(pred)
        ape_s[sd], cov_s[sd], mdape_s[sd], cover_s[sd] = a, ce, pd, cv
        preds[sd] = pred
        meta_s[sd] = {"pinball(train)": pin, "sec": sec, "load대기초": waited,
                      "전체 MdAPE": round(tot, 4)}
        ckp = os.path.join(EXP, "cur_seed%d.pt" % sd)
        torch.save({"model": model.state_dict(), "d_in": Sc.shape[1] + C_FULL.shape[1],
                    "hidden": HIDDEN,
                    "text_emb": os.path.join(TRI, "text_emb_qwen05b.npz"),
                    "레시피": "현행 레시피 · seed %d · steps 3000 · 앙상블 1000 구성원" % sd},
                   ckp)
        ckpts[sd] = {"경로": ckp, "sha": sha16(ckp)}
        prog({"구성": "현행", "seed": sd, "웹툰": round(pd[TARGET], 4),
              "덮개율": round(cv, 4), "sec": sec})
    out["씨앗별 결과 (관찰 60칸 = 씨앗5×12)"] = {
        str(sd): {"도메인별 MdAPE": {d: round(v, 4) for d, v in mdape_s[sd].items()},
                  "90% 덮개율": round(cover_s[sd], 4), **meta_s[sd]} for sd in SEEDS}
    out["체크포인트 (저장소 밖 · 조항 73-마)"] = {str(sd): ckpts[sd] for sd in SEEDS}

    # ── 재현 항등 (관찰 55칸) — 999 실측과 4자리 대조 ─────────────────
    mism = {}
    for sd in SEEDS:
        r = ref999[str(sd)]
        for d in ROSTER:
            if round(mdape_s[sd][d], 4) != r["도메인별 MdAPE"][d]:
                mism["%d/%s" % (sd, d)] = {"이번": round(mdape_s[sd][d], 4),
                                           "999": r["도메인별 MdAPE"][d]}
        if round(cover_s[sd], 4) != r["90% 덮개율"]:
            mism["%d/덮개율" % sd] = {"이번": round(cover_s[sd], 4), "999": r["90% 덮개율"]}
    out["재현 항등 (관찰 55칸 · 999 씨앗별 실측과 4자리 대조)"] = {
        "일치": 55 - len(mism), "불일치": len(mism),
        "불일치 상세": mism if mism else "없음(55/55)"}

    # ── 앙상블 — 분위수 평균 → 같은 평가식 ────────────────────────────
    ens_pred = np.mean(np.stack([preds[sd] for sd in SEEDS]), axis=0)
    ape_e, cov_e, mdape_e, cover_e, tot_e = eval_pred(ens_pred)
    out["앙상블 결과 (관찰 12칸)"] = {
        "도메인별 MdAPE": {d: round(v, 4) for d, v in mdape_e.items()},
        "90% 덮개율": round(cover_e, 4), "전체 MdAPE": round(tot_e, 4)}

    # ── 앵커 검사 (11칸 · 999 J_d 도메인별 문턱) ─────────────────────
    M = {d: float(np.median([mdape_s[sd][d] for sd in SEEDS])) for d in ROSTER}
    M_cov = float(np.median([cover_s[sd] for sd in SEEDS]))
    anchor, flags = {}, []
    for d in ROSTER:
        dv = abs(M[d] - pre_dom[d])
        ok = bool(dv <= J[d])
        anchor[d] = {"|Δ|": round(dv, 4), "J_d": J[d], "통과": ok}
        flags.append(ok)
    dv = abs(M_cov - pre_cover)
    ok = bool(dv <= J_cov)
    anchor["덮개율"] = {"|Δ|": round(dv, 4), "J_cov": J_cov, "통과": ok}
    flags.append(ok)
    anchor_ok = all(flags)
    out["앵커 검사 (11칸 · 깨지면 전부 관찰 강등)"] = dict(anchor, 통과=bool(anchor_ok))

    # ── Δ · SE (짝지은 개체 붓스트랩) ─────────────────────────────────
    delta, se = {}, {}
    for k, d in enumerate(ROSTER):
        m = DOM_VA == DOMAINS.index(d)
        A_cur = np.stack([ape_s[sd][m] for sd in SEEDS])
        delta[d] = mdape_e[d] - M[d]
        rng = np.random.default_rng([STAT_SEED, 1, k])
        se[d] = float(boot_delta_ens(A_cur, ape_e[m], rng, np.median).std(ddof=1))
    C_cur = np.stack([cov_s[sd] for sd in SEEDS])
    d_cov = cover_e - M_cov
    se_cov = float(boot_delta_ens(C_cur, cov_e, np.random.default_rng([STAT_SEED, 2]),
                                  np.mean).std(ddof=1))
    out["Δ·SE 표 (앙상블 − 단일 씨앗 중앙값 · 짝지은 붓스트랩 · 관찰 22칸)"] = {
        **{d: {"Δ": round(delta[d], 4), "SE": round(se[d], 4), "J_d": J[d]} for d in ROSTER},
        "덮개율": {"Δ": round(d_cov, 4), "SE": round(se_cov, 4), "J_cov": J_cov}}

    # ── 헤드라인 (웹툰 60 개체 · 조항 79) ────────────────────────────
    wm = DOM_VA == DOMAINS.index(TARGET)
    A_cur = np.stack([ape_s[sd][wm] for sd in SEEDS])             # (5, 60)
    A_ens = np.tile(ape_e[wm], (len(SEEDS), 1))                   # (5, 60) — 열 복제
    d_obs = delta[TARGET]
    a_i, b_i = np.median(A_cur, axis=0), ape_e[wm]
    rngp = np.random.default_rng([STAT_SEED, 3])
    flips = rngp.random((N_PERM, A_cur.shape[1])) < 0.5           # (B, 60)
    Aq = np.where(flips[:, None, :], A_ens[None], A_cur[None])    # 개체 단위 묶음 뒤집기
    Bq = np.where(flips[:, None, :], A_cur[None], A_ens[None])
    stat = (np.median(np.median(Bq, axis=2), axis=1)
            - np.median(np.median(Aq, axis=2), axis=1))
    p_one = float((1 + (stat <= d_obs).sum()) / (1 + N_PERM))
    out["헤드라인(웹툰 · 조항 79)"] = {
        "n(짝)": int(wm.sum()),
        "Δ웹툰(앙상블 − 단일 씨앗 중앙값)": round(d_obs, 4),
        "붓스트랩 SE": round(se[TARGET], 4),
        "t": round(d_obs / se[TARGET], 2) if se[TARGET] > 0 else None,
        "동부호(앙상블이 이긴 개체)": "%d/%d" % (int((b_i < a_i).sum()), int(wm.sum())),
        "부호뒤집기 순열 p(한쪽꼬리·개선 방향)": round(p_one, 5),
        "B": {"붓스트랩": N_BOOT, "순열": N_PERM, "seed 스트림": "[1000,1,k]·[1000,2]·[1000,3]"}}

    # ── 판정 ㉠㉡㉢ (v5.1 · 판정 9칸) + 조항 78 탐침 ─────────────────
    thr_t = max(J[TARGET], 2.0 * se[TARGET])
    g1 = bool(-delta[TARGET] > thr_t)
    judge = [d for d in ROSTER if d != TARGET and d not in SMALL]
    bad = {}
    for d in judge:
        thr_d = max(J[d], MULT_OTHER * se[d])
        if delta[d] > thr_d:
            bad[d] = {"Δ": round(delta[d], 4), "문턱": round(thr_d, 4)}
    g2 = bool(not bad)
    thr_c = max(J_cov, 2.0 * se_cov)
    g3 = bool(d_cov >= -thr_c)
    probes = {"㉠": gate_probe(lambda x, t: -x > t, d_obs, thr_t),
              "㉢": gate_probe(lambda x, t: x >= -t, d_cov, thr_c)}
    for d in judge:
        probes["㉡ " + d] = gate_probe(lambda x, t: x > t, delta[d],
                                      max(J[d], MULT_OTHER * se[d]))
    n_m = sum(1 for p in probes.values() if not p["거짓 나옴"])
    n_n = sum(1 for p in probes.values() if not p["참 나옴"])
    out["조항 78 탐침 (자료 유래 격자 · 리터럴 0)"] = dict(
        probes, 계수={"㉮ 원리상 못 떨어짐": n_m, "㉯ 원리상 못 통과": n_n})
    out["판정 (v5.1 5-다 · 판정 9칸)"] = {
        "앵커": bool(anchor_ok),
        "㉠ 표적 개선": {"통과": g1, "−Δ웹툰": round(-delta[TARGET], 4),
                     "문턱 max(J,2SE)": round(thr_t, 4)},
        "㉡ 타 도메인 유의 악화(판정 7 — 게임·만화 제외)": {
            "통과": g2, "걸린 도메인": bad if bad else "없음(0/7)"},
        "㉢ 덮개율 비악화": {"통과": g3, "Δ덮개율": round(d_cov, 4),
                        "문턱 −max(J_cov,2SE)": round(-thr_c, 4)},
        "게임·만화(관찰 — n_val<30)": {d: {"Δ": round(delta[d], 4), "SE": round(se[d], 4)}
                                   for d in SMALL}}
    if not anchor_ok:
        verdict = "관찰 강등 — 앵커 불통과 (배포 0)"
    elif g1 and g2 and g3:
        verdict = "성공 — 배포 진행"
    elif g1:
        verdict = "부분 — ㉠ 통과(세계 명제 확증)나 ㉡/㉢ 불통과 (배포 0)"
    else:
        verdict = "실패 — ㉠ 불통과 (배포 0)"
    out["판정어"] = verdict

    # ── 관찰 — 배포(seed 997) 대비 (순환 금지 · 확증에 안 쓴다) ───────
    out["관찰 — 앙상블 대 배포 997 (11칸 · 확증에 안 씀)"] = {
        **{d: {"앙상블": round(mdape_e[d], 4), "배포 997": pre_dom[d],
               "Δ": round(mdape_e[d] - pre_dom[d], 4)} for d in ROSTER},
        "덮개율": {"앙상블": round(cover_e, 4), "배포 997": pre_cover,
                "Δ": round(cover_e - pre_cover, 4)}}

    # 배포물 후보(성공 시 조타수가 §6 절차대로 집행) — 구성원 5 전부 · 선택 없음
    out["배포물 후보(성공 시)"] = {
        "구성원": {str(sd): ckpts[sd] for sd in SEEDS},
        "결합": "분위수 텐서 (91,5) 산술 평균",
        "비고": "선택 없음(5모형 전부) — 윗꼬리 뽑기 순환이 원리상 없다"}

    out["관찰 분모 신고(조항 79)"] = ("대비 주장 1(웹툰) · 관찰: 씨앗별 60 + 앙상블 12 + "
                                "재현 항등 55 + Δ·SE 22 + 앵커 11 + 헤드라인 5 + "
                                "소도메인 4 + 배포997 대비 11 · 판정 9")
    out["총소요초"] = round(time.time() - t_all, 1)
    out["끝 시각"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "Δ웹툰": round(d_obs, 4), "p": p_one,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
