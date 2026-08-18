# -*- coding: utf-8 -*-
"""확증 999 러너 — 표적 «웹툰» · P3(도메인 균형 표본) (사전등록 docs/탐색/999.md 에서 언 코드).

주대비 «하나»(티처 #136 조건 1): P3 의 웹툰 q50 효과. 씨앗 K=5 (1001~1005 · 997 금지).
학습 10회 = 현행 레시피 ×5 (지터 바닥 J) + P3 ×5. 전부 CPU 4스레드 · 순차 ·
각 학습 전 load1 > 10 이면 60초 대기 반복 (4B 임베딩 등 불가침 작업과 안 싸운다).

판정(v5.1 5-다 · 사전등록 §3~§4):
  앵커  전 도메인 |median_s MdAPE(현행,s,d) − 리더보드_d| ≤ 0.0209 · 덮개율 ≤ 0.0101
        (998 P0 실측 인용 — out998_pieces.json) — 깨지면 전부 「관찰」 강등
  ㉠  −Δ웹툰(씨앗 중앙값) > max(J_웹툰, 2×SE_웹툰)
  ㉡  판정 7 도메인(게임·만화 제외) 중 Δ_d > max(J_d, 2.6×SE_d) 인 곳 0
  ㉢  Δ덮개율 ≥ −max(J_cov, 2×SE_cov)
헤드라인: 웹툰 60 개체 짝지은 붓스트랩 SE + 부호뒤집기 순열 p (B=10,000 · seed 999 스트림).
조항 78: 게이트 탐침 — 자료 유래 격자(실측·부호반전·0·±2문턱)에서 참/거짓 둘 다 나오나.

🔴 CPU 전용 · 유료 API 0 · 배포 파일 무변경(읽기만) · 씀: python3 runners/confirm999.py
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
SEEDS = (1001, 1002, 1003, 1004, 1005)          # 사전등록 §2 — 997 금지 이행
STAT_SEED = 999                                  # 통계 씨앗 (스트림: [999,1,k] · [999,2] · [999,3])
N_BOOT = N_PERM = 10000
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
TARGET = "웹툰"
SMALL = ("게임", "만화")                          # n_val < 30 — ㉠㉡ 판정 제외 (관찰)
ANCHOR_J, ANCHOR_JCOV = 0.0209, 0.0101           # 998 P0 실측 (사전등록 §3)
MULT_OTHER = 2.6                                 # v5.1 ㉡ 다중비교 몫

ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "confirm999")
OUT_JSON = "/Users/ax/world_model/runners/out999_confirm.json"
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0


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
    """각 학습 전 — load1 > 10 이면 60초 대기 반복 (사전등록 · 불가침 작업 보호)."""
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60
    return waited


# ── 자료 (998 러너와 같은 전처리 — 도구 재사용) ───────────────────────
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
POOLS = {d: TR_IDX[dom_id[TR_IDX] == d] for d in range(n_dom)}
DOM_VA = dom_id[VA_IDX]


def eval_model(model):
    """998 러너 평가식 + 개체별 덮개율."""
    model.eval()
    with torch.no_grad():
        xe = torch.from_numpy(np.concatenate([Sc[VA_IDX], C_FULL[VA_IDX]], axis=1))
        pred = model(xe).numpy()
    b = base[VA_IDX]
    cum_true = np.expm1(R[VA_IDX] + b).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + b).sum(axis=1)
    ape = np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1.0)
    cover_ent = ((R[VA_IDX] >= pred[..., 0]) & (R[VA_IDX] <= pred[..., 4])).mean(axis=1)
    per_dom = {DOMAINS[d]: float(np.median(ape[DOM_VA == d])) for d in range(n_dom)}
    return ape, cover_ent, per_dom, float(cover_ent.mean()), float(np.median(ape))


def train_cfg(cfg, seed):
    d_in = Sc.shape[1] + C_FULL.shape[1]
    torch.manual_seed(seed)
    model = Transition(d_in, hidden=HIDDEN)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    t0 = time.time()
    loss = None
    for step in range(STEPS):
        rng = np.random.default_rng([seed, step])
        if cfg.get("balanced"):
            dd = rng.integers(0, n_dom, size=BATCH)
            ii = np.empty(BATCH, dtype=np.int64)
            for d in range(n_dom):
                m = dd == d
                if m.any():
                    ii[m] = POOLS[d][rng.integers(0, len(POOLS[d]), size=int(m.sum()))]
        else:
            ii = TR_IDX[rng.integers(0, len(TR_IDX), size=BATCH)]
        x = torch.from_numpy(np.concatenate([Sc[ii], C_FULL[ii]], axis=1))
        r = torch.from_numpy(R[ii])
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
    return model, round(float(loss.item()), 5), round(time.time() - t0, 1)


def boot_delta(A_cur, A_p3, rng, agg):
    """짝지은 개체 붓스트랩 — 씨앗별 집계 → 씨앗 중앙값 → Δ 함수 «전체» 재계산.
    A_* 형상 (K, n). agg: np.median(도메인 MdAPE) 또는 np.mean(덮개율)."""
    n = A_cur.shape[1]
    out = np.empty(N_BOOT)
    done = 0
    while done < N_BOOT:
        m = min(2000, N_BOOT - done)
        idx = rng.integers(0, n, size=(m, n))
        cur = np.median(agg(A_cur[:, idx], axis=2), axis=0)      # (m,)
        p3 = np.median(agg(A_p3[:, idx], axis=2), axis=0)
        out[done:done + m] = p3 - cur
        done += m
    return out


def gate_probe(fn, obs_args, thr):
    """조항 78 탐침 — 자료 유래 격자에서 참/거짓이 둘 다 나오는지 (리터럴 금지).
    fn(delta, thr) → bool. 격자: 실측 Δ · 부호반전 · 0 · ±2×문턱."""
    d = obs_args
    grid = [d, -d, 0.0, 2.0 * thr, -2.0 * thr]
    vals = [bool(fn(g, thr)) for g in grid]
    return {"격자": [round(g, 6) for g in grid], "결과": vals,
            "참 나옴": any(vals), "거짓 나옴": not all(vals)}


def main():
    t_all = time.time()
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    pre_dom = {d: r["transition"] for d, r in lb["도메인별"].items()}
    전판 = json.load(open("/Users/ax/world_model/data/lab/999_판_전.json", encoding="utf-8"))
    pre_cover = 전판["④90% 덮개율"]["직접 재계산"]      # 커밋된 전판이 정본 (조항 81)
    out = {"러너": "runners/confirm999.py", "표적": TARGET,
           "잰 소스 (조항 66)": {
               "sao.npz": sha16(os.path.join(TRI, "sao.npz")),
               "text_emb_qwen05b.npz": sha16(os.path.join(TRI, "text_emb_qwen05b.npz")),
               "model.pt(전·배포)": sha16(os.path.join(TROUT, "model.pt")),
               "leaderboard.json(전)": sha16(os.path.join(TROUT, "leaderboard.json")),
               "러너 자신": sha16(os.path.abspath(__file__))},
           "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
                  "학습 씨앗": list(SEEDS), "통계 씨앗": STAT_SEED,
                  "threads": torch.get_num_threads(), "device": "cpu",
                  "B": {"붓스트랩": N_BOOT, "순열": N_PERM}},
           "앵커 문턱(사전등록 §3 · 998 P0 인용)": {"J(998)": ANCHOR_J, "J_cov(998)": ANCHOR_JCOV}}

    # ── 학습 10회 — 한 번에 하나 · load 관문 ─────────────────────────
    configs = [("현행", {}), ("P3 균형", {"balanced": True})]
    ape, cov, mdape, cover, meta = {}, {}, {}, {}, {}
    os.makedirs(EXP, exist_ok=True)
    for cname, cfg in configs:
        ape[cname], cov[cname], mdape[cname], cover[cname], meta[cname] = {}, {}, {}, {}, {}
        for sd in SEEDS:
            waited = load_gate()
            model, pin, sec = train_cfg(cfg, sd)
            a, ce, pd, cv, tot = eval_model(model)
            ape[cname][sd], cov[cname][sd] = a, ce
            mdape[cname][sd], cover[cname][sd] = pd, cv
            meta[cname][sd] = {"pinball(train)": pin, "sec": sec, "load대기초": waited,
                               "전체 MdAPE": round(tot, 4)}
            if cfg.get("balanced"):                   # 배포 후보 — 체크포인트 보존
                ckp = os.path.join(EXP, "p3_seed%d.pt" % sd)
                torch.save({"model": model.state_dict(), "d_in": Sc.shape[1] + C_FULL.shape[1],
                            "hidden": HIDDEN,
                            "text_emb": os.path.join(TRI, "text_emb_qwen05b.npz"),
                            "레시피": "P3 도메인 균형 표본 · seed %d · steps 3000 (탐색 999)" % sd},
                           ckp)
            prog({"구성": cname, "seed": sd, "웹툰": round(pd[TARGET], 4),
                  "덮개율": round(cv, 4), "sec": sec})
    out["씨앗별 결과 (관찰 120칸 = 씨앗5×구성2×12)"] = {
        cname: {str(sd): {"도메인별 MdAPE": {d: round(v, 4) for d, v in mdape[cname][sd].items()},
                          "90% 덮개율": round(cover[cname][sd], 4), **meta[cname][sd]}
                for sd in SEEDS} for cname, _ in configs}

    # ── 지터 바닥 J · 앵커 ───────────────────────────────────────────
    J = {d: max(abs(mdape["현행"][sd][d] - pre_dom[d]) for sd in SEEDS) for d in ROSTER}
    J_cov = max(abs(cover["현행"][sd] - pre_cover) for sd in SEEDS)
    out["지터 바닥 J_d (현행 5씨앗 |Δ리더보드| 최대 · v5.1)"] = {
        **{d: round(J[d], 4) for d in ROSTER}, "덮개율": round(J_cov, 4)}
    M = {c: {d: float(np.median([mdape[c][sd][d] for sd in SEEDS])) for d in ROSTER}
         for c, _ in configs}
    M_cov = {c: float(np.median([cover[c][sd] for sd in SEEDS])) for c, _ in configs}
    anchor, flags = {}, []
    for d in ROSTER:
        dv = abs(M["현행"][d] - pre_dom[d])
        ok = bool(dv <= ANCHOR_J)
        anchor[d] = {"|Δ|": round(dv, 4), "≤ 0.0209": ok}
        flags.append(ok)
    dv = abs(M_cov["현행"] - pre_cover)
    ok = bool(dv <= ANCHOR_JCOV)
    anchor["덮개율"] = {"|Δ|": round(dv, 4), "≤ 0.0101": ok}
    flags.append(ok)
    anchor_ok = all(flags)
    out["앵커 검사 (11칸 · 깨지면 전부 관찰 강등)"] = dict(anchor, 통과=bool(anchor_ok))

    # ── Δ · SE (짝지은 개체 붓스트랩 · 씨앗 중앙값 함수 전체) ────────
    delta, se = {}, {}
    for k, d in enumerate(ROSTER):
        m = DOM_VA == DOMAINS.index(d)
        A_cur = np.stack([ape["현행"][sd][m] for sd in SEEDS])
        A_p3 = np.stack([ape["P3 균형"][sd][m] for sd in SEEDS])
        delta[d] = M["P3 균형"][d] - M["현행"][d]
        rng = np.random.default_rng([STAT_SEED, 1, k])
        se[d] = float(boot_delta(A_cur, A_p3, rng, np.median).std(ddof=1))
    C_cur = np.stack([cov["현행"][sd] for sd in SEEDS])
    C_p3 = np.stack([cov["P3 균형"][sd] for sd in SEEDS])
    d_cov = M_cov["P3 균형"] - M_cov["현행"]
    se_cov = float(boot_delta(C_cur, C_p3, np.random.default_rng([STAT_SEED, 2]),
                              np.mean).std(ddof=1))
    out["Δ·SE 표 (씨앗 중앙값 · 짝지은 붓스트랩 · 관찰 22칸)"] = {
        **{d: {"Δ": round(delta[d], 4), "SE": round(se[d], 4), "J_d": round(J[d], 4)}
           for d in ROSTER},
        "덮개율": {"Δ": round(d_cov, 4), "SE": round(se_cov, 4), "J_cov": round(J_cov, 4)}}

    # ── 헤드라인 (웹툰 60 개체 · 조항 79) ────────────────────────────
    wm = DOM_VA == DOMAINS.index(TARGET)
    A_cur = np.stack([ape["현행"][sd][wm] for sd in SEEDS])       # (5, 60)
    A_p3 = np.stack([ape["P3 균형"][sd][wm] for sd in SEEDS])
    d_obs = delta[TARGET]
    a_i, b_i = np.median(A_cur, axis=0), np.median(A_p3, axis=0)
    rngp = np.random.default_rng([STAT_SEED, 3])
    flips = rngp.random((N_PERM, A_cur.shape[1])) < 0.5           # (B, 60)
    Aq = np.where(flips[:, None, :], A_p3[None], A_cur[None])     # 개체 단위 · 씨앗 묶음 뒤집기
    Bq = np.where(flips[:, None, :], A_cur[None], A_p3[None])
    stat = (np.median(np.median(Bq, axis=2), axis=1)
            - np.median(np.median(Aq, axis=2), axis=1))
    p_one = float((1 + (stat <= d_obs).sum()) / (1 + N_PERM))
    out["헤드라인(웹툰 · 조항 79)"] = {
        "n(짝)": int(wm.sum()), "Δ웹툰(씨앗 중앙값 · 후−전)": round(d_obs, 4),
        "붓스트랩 SE": round(se[TARGET], 4),
        "t": round(d_obs / se[TARGET], 2) if se[TARGET] > 0 else None,
        "동부호(개선 개체 수)": "%d/%d" % (int((b_i < a_i).sum()), int(wm.sum())),
        "부호뒤집기 순열 p(한쪽꼬리·개선 방향)": round(p_one, 5),
        "B": {"붓스트랩": N_BOOT, "순열": N_PERM, "seed 스트림": "[999,1,k]·[999,2]·[999,3]"}}

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

    # 배포 승자(성공 시): P3 웹툰 MdAPE 순위 3위 씨앗 (동률 작은 씨앗)
    if verdict.startswith("성공"):
        order = sorted(SEEDS, key=lambda sd: (mdape["P3 균형"][sd][TARGET], sd))
        win = order[2]
        out["승자"] = {"씨앗": win, "웹툰 MdAPE": round(mdape["P3 균형"][win][TARGET], 4),
                     "체크포인트": os.path.join(EXP, "p3_seed%d.pt" % win),
                     "체크포인트 sha": sha16(os.path.join(EXP, "p3_seed%d.pt" % win))}
    else:
        out["승자"] = "없음 (배포 0) — " + verdict

    out["관찰 분모 신고(조항 79)"] = ("대비 주장 1(웹툰) · 관찰 120 + Δ·SE 22 + 앵커 11 + "
                                "헤드라인 5 + 소도메인 4 · 판정 9")
    out["총소요초"] = round(time.time() - t_all, 1)
    out["끝 시각"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "Δ웹툰": round(d_obs, 4), "p": p_one,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
