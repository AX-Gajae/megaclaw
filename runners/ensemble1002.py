# -*- coding: utf-8 -*-
"""확증 1002 러너 — ㉢ 부호를 고친 «재등록» · 씨앗 «셋째» 집합(1201~1205) 앙상블 확증
(사전등록 docs/탐색/1002.md 에서 언 코드 · 루프 v5.2 다섯째 사이클).

주대비 «하나»(조항 79): 현행 레시피 셋째 씨앗 1201~1205 5모형의 분위수 평균 앙상블의
90% 덮개율 효과. 비교 기준 = 같은 셋째 씨앗 «단일모형»의 덮개율 씨앗 중앙값.
1101~1105 는 1001 판정에 쓰였다 — 재사용 금지(1001 §9-6). 997·1001~1005 도 금지.

판정(사전등록 §3~§4 · 각 게이트 «악화 방향» 명기 · 비반올림 집행):
  앵커(v5.2)  전 도메인 |M″(d) − M′(d)| ≤ max(J′_d(1001), 3×전판 SE_d) ·
        덮개율 |M″_cov − M′_cov| ≤ max(J′_cov 0.0293, 3×0.0066) — 성분 일치(«씨앗 간» 대
        «씨앗 간») · 깨지면 전부 「관찰」 강등. 이번 J″ 를 다음 앵커 정본으로 신고(㉯).
  ㉠  Δ덮개율 > max(J′_cov, 2×SE_cov)                      [악화 = 하락(−) → 떨어져야]
  ㉡  판정 8 도메인 중 Δ_d > max(J′_d, 2.6×SE_d) 인 곳 0    [악화 = 상승(+) → 떨어져야]
  ㉢  Δ전체 ≤ +max(J′_전체, 2×SE_전체)  (🔴 부호 정정)      [악화 = 상승(+) → 떨어져야]
  ㉣  Δ폭 ≤ 0.10 × median_s W(단일,s)                      [악화 = 증가(+) → 떨어져야]
헤드라인: 덮개율 1129 개체 짝지은 붓스트랩 SE + 부호뒤집기 순열 p (B=10,000 ·
seed 스트림 [11002,1,k]·[11002,2]·[11002,3]·[11002,4]·[11002,5] — 🔴 신규 스트림).
조항 78 «강화» 탐침: 격자 {실측·부호반전·0·±2문턱·악화 극값·개선 극값}에서 참/거짓 +
🔴 방향 검사(악화 극값 거짓 ∧ 개선 극값 참) — 위반이 하나라도 나오면 「등록 결함 —
관찰 강등(배포 0)」. 1001 §9-1 부호 사건의 사전 기계 관문.

🔴 CPU 전용 4스레드 · 유료 API 0 · MPS 0 · 배포 파일 무변경(읽기만) · 각 학습 전 load1 > 10
이면 60초 대기 반복. 씀: python3 runners/ensemble1002.py
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
SEEDS = (1201, 1202, 1203, 1204, 1205)   # 🔴 셋째 집합 — 997·1001~1005·1101~1105 금지 이행
PREV_SEEDS = ("1101", "1102", "1103", "1104", "1105")  # 1001 씨앗 (앵커 기준 M′ 의 원천)
STAT_SEED = 11002    # 🔴 신규 통계 스트림 — 11001(1001)·9990/9991·998/999/1000·136/1136 회피
N_BOOT = N_PERM = 10000
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
SMALL = ("게임", "만화")                  # n_val < 30 — ㉡ 판정 제외 (관찰)
MULT_OTHER = 2.6                          # v5.1 ㉡ 다중비교 몫
WIDTH_LIMIT_REL = 0.10                    # ㉣ 폭 한도(상대 · 1001 규격 승계)

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "ensemble1002")
OUT_JSON = os.path.join(REPO, "runners", "out1002_ensemble.json")
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

# 조항 66 — 앵커·전판·자료 원천은 sha 가 사전등록과 일치해야 쓴다 (어긋나면 즉시 중단)
EXPECT_SHA = {
    os.path.join(REPO, "runners/out1001_ensemble.json"): "6e5c3720c52f269e",  # J′·M′ 원천
    os.path.join(REPO, "data/lab/1001_판_후.json"): "d56e54eb6cc25d2e",        # 전판 (SE_d)
    os.path.join(TROUT, "leaderboard.json"): "da73fed24780e355",
    os.path.join(TROUT, "model.pt"): "5122c2eb3c21bfbd",
    os.path.join(TROUT, "report.json"): "c4c37793a10b1bc5",                    # 폭 0.5709 원천
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
}
KEY_JP = "J′_d (새 씨앗 5 |Δ리더보드| 최대 · v5.1 정의 — 다음 사이클 앵커 정본 신고 · ㉯)"
KEY_SEEDCELLS = "씨앗별 결과 (관찰 65칸 = 씨앗5×13)"


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


# ── 자료 (999~1001 러너와 자구까지 같은 전처리) ───────────────────────
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
    """(n,91,5) 잔차 눈금 예측 → 개체별 (ape, cover_ent, piw_ent) + 집계 — 999~1001 평가식."""
    b = base[VA_IDX]
    cum_true = np.expm1(R[VA_IDX] + b).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + b).sum(axis=1)
    ape = np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1.0)
    cover_ent = ((R[VA_IDX] >= pred[..., 0]) & (R[VA_IDX] <= pred[..., 4])).mean(axis=1)
    piw_ent = (pred[..., 4] - pred[..., 0]).mean(axis=1)
    per_dom = {DOMAINS[d]: float(np.median(ape[DOM_VA == d])) for d in range(n_dom)}
    return (ape, cover_ent, piw_ent, per_dom, float(cover_ent.mean()),
            float(np.median(ape)), float(piw_ent.mean()))


def predict(model):
    model.eval()
    with torch.no_grad():
        xe = torch.from_numpy(np.concatenate([Sc[VA_IDX], C_FULL[VA_IDX]], axis=1))
        return model(xe).numpy()


def train_cur(seed):
    """현행 레시피 — ensemble1000/1001.train_cur 와 같은 연산 순서 (씨앗만 셋째 집합)."""
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
    """짝지은 개체 붓스트랩 — Δ* = agg(앙상블) − median_s agg(단일 s) 함수 «전체» 재계산."""
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


def gate_probe(pass_fn, obs, thr, worse_sign):
    """조항 78 «강화» 탐침 (사전등록 §4) — 자료 유래 격자 + 🔴 방향 검사.
    pass_fn(x, thr) 는 «통과 = True» 함수. worse_sign = 악화 방향의 Δ 부호(+1/−1).
    격자 극값 크기 = 4×max(문턱, |실측|) — 자료 유래 · 리터럴 0."""
    ext = 4.0 * max(abs(thr), abs(obs))
    grid = [("실측", obs), ("부호반전", -obs), ("0", 0.0),
            ("+2문턱", 2.0 * thr), ("-2문턱", -2.0 * thr),
            ("악화 극값", worse_sign * ext), ("개선 극값", -worse_sign * ext)]
    vals = {name: bool(pass_fn(x, thr)) for name, x in grid}
    방향 = (not vals["악화 극값"]) and vals["개선 극값"]
    return {"격자": {name: round(x, 6) for name, x in grid}, "통과값(참=통과)": vals,
            "참 나옴": any(vals.values()), "거짓 나옴": not all(vals.values()),
            "방향 검사(악화 극값 거짓 ∧ 개선 극값 참)": bool(방향)}


def main():
    t_all = time.time()
    # ── 조항 66 — 원천 sha 검증 (어긋나면 측정 없이 중단) ────────────
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

    o1001 = json.load(open(os.path.join(REPO, "runners/out1001_ensemble.json"),
                           encoding="utf-8"))
    JP = o1001[KEY_JP]                                   # 앵커 정본 (1001 ㉯ 신고 · «씨앗 간»)
    cells = o1001[KEY_SEEDCELLS]                          # 1101~1105 씨앗별 실측
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    pre_dom = {d: lb["도메인별"][d]["transition"] for d in ROSTER}
    lb_tot = float(lb["전체"]["transition"])              # 0.0626 (배포-전)
    전판 = json.load(open(os.path.join(REPO, "data/lab/1001_판_후.json"), encoding="utf-8"))
    pre_cover = 전판["④90% 덮개율"]["직접 재계산"]            # 0.7242
    SE_pan = {d: float(전판["①최약 도메인"]["도메인별"][d]["SE"]) for d in ROSTER}
    SE_cov_pan = float(전판["④90% 덮개율"]["개체 군집 SE"])   # 0.0066
    rep = json.load(open(os.path.join(TROUT, "report.json"), encoding="utf-8"))
    pre_piw = float(rep["평가"]["구간 평균 폭(log)"])         # 0.5709 (배포 997 · 관찰 인용)

    # ── J′ 재계산 대조 (조항 66 — ㉯ 신고 칸 대 씨앗별 실측 칸 · 허용 1.5e-4) ──
    J = {d: float(JP[d]) for d in ROSTER}
    J_cov, J_tot, J_W = float(JP["덮개율"]), float(JP["전체"]), float(JP["폭"])
    recompute = {d: max(abs(cells[s]["도메인별 MdAPE"][d] - pre_dom[d]) for s in PREV_SEEDS)
                 for d in ROSTER}
    recompute["덮개율"] = max(abs(cells[s]["90% 덮개율"] - pre_cover) for s in PREV_SEEDS)
    recompute["전체"] = max(abs(cells[s]["전체 MdAPE"] - lb_tot) for s in PREV_SEEDS)
    recompute["폭"] = max(abs(cells[s]["구간 평균 폭(log)"] - pre_piw) for s in PREV_SEEDS)
    jp_diff = {k: abs(recompute[k] - float(JP[k]))
               for k in list(ROSTER) + ["덮개율", "전체", "폭"]}
    if max(jp_diff.values()) > 1.5e-4:
        out = {"판정어": "중단 — J′ 신고 칸과 씨앗별 실측 재계산 불일치 (조항 66)",
               "차이": {k: round(v, 6) for k, v in jp_diff.items()}}
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    # 앵커 기준 M′ (1101~1105 씨앗 중앙값) · 문턱
    Mp = {d: float(np.median([cells[s]["도메인별 MdAPE"][d] for s in PREV_SEEDS]))
          for d in ROSTER}
    Mp_cov = float(np.median([cells[s]["90% 덮개율"] for s in PREV_SEEDS]))
    ANC = {d: max(J[d], 3.0 * SE_pan[d]) for d in ROSTER}
    ANC_cov = max(J_cov, 3.0 * SE_cov_pan)

    out = {"러너": "runners/ensemble1002.py",
           "표적": "④ 90% 덮개율(전역) — ㉢ 부호 정정 재등록 · 셋째 씨앗 집합",
           "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
           "sha 검증(사전등록 대조)": sha_verify,
           "러너 자신": sha16(os.path.abspath(__file__)),
           "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
                  "학습 씨앗(셋째)": list(SEEDS), "통계 씨앗": STAT_SEED,
                  "threads": torch.get_num_threads(), "device": "cpu",
                  "B": {"붓스트랩": N_BOOT, "순열": N_PERM},
                  "앙상블": "5모형 (91,5) 분위수 텐서 산술 평균 — 자체 지터 정의상 0"},
           "앵커 문턱(사전등록 §3 · max(J′_d(1001), 3×전판 SE_d))": dict(
               {d: round(ANC[d], 4) for d in ROSTER}, 덮개율=round(ANC_cov, 4)),
           "앵커 기준 M′(1101~1105 씨앗 중앙값 · out1001 sha 6e5c3720c52f269e)": dict(
               {d: round(Mp[d], 4) for d in ROSTER}, 덮개율=round(Mp_cov, 4)),
           "J′ 재계산 대조(조항 66 · 13칸 · 허용 1.5e-4)": {
               k: round(v, 6) for k, v in jp_diff.items()},
           "㉢ 문턱 원천": {"J′_전체(씨앗 간 · 1001 ㉯)": round(J_tot, 4),
                       "리더보드 전체(배포-전)": lb_tot,
                       "집행": "비반올림 원값 — Δ전체 ≤ +max(J′_전체, 2×SE_전체)"},
           "㉣ 폭 참고(배포 997 · report 인용)": pre_piw}

    # ── 학습 5회 — 한 번에 하나 · load 관문 · 체크포인트 보존 ─────────
    ape_s, cov_s, piw_s = {}, {}, {}
    mdape_s, cover_s, tot_s, W_s, meta_s, preds, ckpts = {}, {}, {}, {}, {}, {}, {}
    os.makedirs(EXP, exist_ok=True)
    for sd in SEEDS:
        waited = load_gate()
        model, pin, sec = train_cur(sd)
        pred = predict(model)
        a, ce, pw, pd, cv, tot, W = eval_pred(pred)
        ape_s[sd], cov_s[sd], piw_s[sd] = a, ce, pw
        mdape_s[sd], cover_s[sd], tot_s[sd], W_s[sd] = pd, cv, tot, W
        preds[sd] = pred
        meta_s[sd] = {"pinball(train)": pin, "sec": sec, "load대기초": waited}
        ckp = os.path.join(EXP, "cur_seed%d.pt" % sd)
        torch.save({"model": model.state_dict(), "d_in": Sc.shape[1] + C_FULL.shape[1],
                    "hidden": HIDDEN,
                    "text_emb": os.path.join(TRI, "text_emb_qwen05b.npz"),
                    "레시피": "현행 레시피 · seed %d · steps 3000 · 앙상블 1002 구성원" % sd},
                   ckp)
        ckpts[sd] = {"경로": ckp, "sha": sha16(ckp)}
        prog({"구성": "현행(셋째 씨앗)", "seed": sd, "덮개율": round(cv, 4),
              "전체": round(tot, 4), "폭": round(W, 4), "sec": sec})
    out["씨앗별 결과 (관찰 65칸 = 씨앗5×13)"] = {
        str(sd): {"도메인별 MdAPE": {d: round(v, 4) for d, v in mdape_s[sd].items()},
                  "전체 MdAPE": round(tot_s[sd], 4),
                  "90% 덮개율": round(cover_s[sd], 4),
                  "구간 평균 폭(log)": round(W_s[sd], 4), **meta_s[sd]} for sd in SEEDS}
    out["체크포인트 (저장소 밖 · 조항 73-마)"] = {str(sd): ckpts[sd] for sd in SEEDS}

    # ── 앙상블 — 분위수 평균 → 같은 평가식 ────────────────────────────
    ens_pred = np.mean(np.stack([preds[sd] for sd in SEEDS]), axis=0)
    ape_e, cov_e, piw_e, mdape_e, cover_e, tot_e, W_e = eval_pred(ens_pred)
    out["앙상블 결과 (관찰 13칸)"] = {
        "도메인별 MdAPE": {d: round(v, 4) for d, v in mdape_e.items()},
        "전체 MdAPE": round(tot_e, 4), "90% 덮개율": round(cover_e, 4),
        "구간 평균 폭(log)": round(W_e, 4)}

    # ── 앵커 검사 (11칸 · v5.2 · 셋째 중앙값 대 1001 중앙값) ──────────
    M = {d: float(np.median([mdape_s[sd][d] for sd in SEEDS])) for d in ROSTER}
    M_cov = float(np.median([cover_s[sd] for sd in SEEDS]))
    M_tot = float(np.median([tot_s[sd] for sd in SEEDS]))
    M_W = float(np.median([W_s[sd] for sd in SEEDS]))
    anchor, flags = {}, []
    for d in ROSTER:
        dv = abs(M[d] - Mp[d])
        ok = bool(dv <= ANC[d])
        anchor[d] = {"|Δ|": round(dv, 4), "문턱": round(ANC[d], 4), "통과": ok}
        flags.append(ok)
    dv = abs(M_cov - Mp_cov)
    ok = bool(dv <= ANC_cov)
    anchor["덮개율"] = {"|Δ|": round(dv, 4), "문턱": round(ANC_cov, 4), "통과": ok}
    flags.append(ok)
    anchor_ok = all(flags)
    out["앵커 검사 (11칸 · v5.2 · 깨지면 전부 관찰 강등)"] = dict(
        anchor, 통과=bool(anchor_ok),
        성분="«씨앗 간»(셋째 5뽑기 중앙값 대 1101~1105 5뽑기 중앙값) — J′_d(1001) 도 «씨앗 간» · 일치")
    # 앵커 참고 관찰 11칸 — |M″(d) − 리더보드_d(배포-전)| (판정에 안 씀)
    out["앵커 참고 관찰 (11칸 · 대 배포-전 997 리더보드 — 판정에 안 씀)"] = dict(
        {d: {"|Δ|": round(abs(M[d] - pre_dom[d]), 4), "J′_d(1001)": J[d]} for d in ROSTER},
        덮개율={"|Δ|": round(abs(M_cov - pre_cover), 4), "J′_cov": J_cov})

    # ── J″ (셋째 씨앗 «씨앗 간» 지터 — 다음 사이클 앵커 정본 · 관찰 13칸) ─
    Jpp = {d: round(float(max(abs(mdape_s[sd][d] - pre_dom[d]) for sd in SEEDS)), 4)
           for d in ROSTER}
    out["J″_d (셋째 씨앗 5 |Δ리더보드| 최대 · 1001 J′ 와 같은 정의 — 다음 앵커 정본 신고 · ㉯)"] = dict(
        Jpp,
        덮개율=round(float(max(abs(cover_s[sd] - pre_cover) for sd in SEEDS)), 4),
        전체=round(float(max(abs(tot_s[sd] - lb_tot) for sd in SEEDS)), 4),
        폭=round(float(max(abs(W_s[sd] - pre_piw) for sd in SEEDS)), 4),
        비고="대 «배포-전(997)» 리더보드·전판 — 배포되면 리더보드가 앙상블로 갈리는 것을 안다")

    # ── Δ · SE (짝지은 개체 붓스트랩 · 씨앗 11002 스트림) ─────────────
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
    A_tot = np.stack([ape_s[sd] for sd in SEEDS])
    d_tot = tot_e - M_tot
    se_tot = float(boot_delta_ens(A_tot, ape_e, np.random.default_rng([STAT_SEED, 4]),
                                  np.median).std(ddof=1))
    P_cur = np.stack([piw_s[sd] for sd in SEEDS])
    d_W = W_e - M_W
    se_W = float(boot_delta_ens(P_cur, piw_e, np.random.default_rng([STAT_SEED, 5]),
                                np.mean).std(ddof=1))
    out["Δ·SE 표 (앙상블 − 단일 씨앗 중앙값 · 짝지은 붓스트랩 · 관찰 26칸)"] = {
        **{d: {"Δ": round(delta[d], 4), "SE": round(se[d], 4), "J′_d": J[d]} for d in ROSTER},
        "덮개율": {"Δ": round(d_cov, 4), "SE": round(se_cov, 4), "J′_cov": J_cov},
        "전체": {"Δ": round(d_tot, 4), "SE": round(se_tot, 4), "J′_전체": round(J_tot, 4)},
        "폭": {"Δ": round(d_W, 4), "SE": round(se_W, 4),
              "한도(0.10×단일 중앙값 폭)": round(WIDTH_LIMIT_REL * M_W, 4)}}

    # ── 헤드라인 (덮개율 1129 개체 · 조항 79) ────────────────────────
    C_ent = np.stack([cov_s[sd] for sd in SEEDS])                 # (5, n) 개체별 덮개율
    E_ent = np.tile(cov_e, (len(SEEDS), 1))                       # (5, n) — 열 복제
    n_ent = C_ent.shape[1]
    a_i, b_i = np.median(C_ent, axis=0), cov_e
    rngp = np.random.default_rng([STAT_SEED, 3])
    flips = rngp.random((N_PERM, n_ent)) < 0.5                    # (B, n)
    Aq = np.where(flips[:, None, :], E_ent[None], C_ent[None])    # 개체 단위 묶음 뒤집기
    Bq = np.where(flips[:, None, :], C_ent[None], E_ent[None])
    stat = (np.median(np.mean(Bq, axis=2), axis=1)
            - np.median(np.mean(Aq, axis=2), axis=1))
    p_one = float((1 + (stat >= d_cov).sum()) / (1 + N_PERM))     # 개선 방향 = 덮개율 «상승»
    out["헤드라인(덮개율 · 조항 79)"] = {
        "n(짝)": int(n_ent),
        "Δ덮개율(앙상블 − 단일 씨앗 중앙값)": round(d_cov, 4),
        "붓스트랩 SE": round(se_cov, 4),
        "t": round(d_cov / se_cov, 2) if se_cov > 0 else None,
        "동부호(앙상블이 이긴 개체)": "%d/%d" % (int((b_i > a_i).sum()), int(n_ent)),
        "부호뒤집기 순열 p(한쪽꼬리·개선=상승)": round(p_one, 5),
        "B": {"붓스트랩": N_BOOT, "순열": N_PERM,
              "seed 스트림": "[11002,1,k]·[11002,2]·[11002,3]·[11002,4]·[11002,5]"}}

    # ── 판정 ㉠㉡㉢㉣ (판정 11칸 · 비반올림 원값 집행) + 강화 탐침 ────
    thr_t = max(J_cov, 2.0 * se_cov)
    g1 = bool(d_cov > thr_t)
    judge = [d for d in ROSTER if d not in SMALL]                 # 8 도메인 (웹툰 포함)
    bad = {}
    for d in judge:
        thr_d = max(J[d], MULT_OTHER * se[d])
        if delta[d] > thr_d:
            bad[d] = {"Δ": round(delta[d], 4), "문턱": round(thr_d, 4)}
    g2 = bool(not bad)
    thr_tot = max(J_tot, 2.0 * se_tot)
    g3 = bool(d_tot <= thr_tot)                                   # 🔴 부호 정정 (1001 §9-1)
    thr_w = WIDTH_LIMIT_REL * M_W
    g4 = bool(d_W <= thr_w)
    probes = {"㉠": gate_probe(lambda x, t: x > t, d_cov, thr_t, worse_sign=-1.0),
              "㉢": gate_probe(lambda x, t: x <= t, d_tot, thr_tot, worse_sign=+1.0),
              "㉣": gate_probe(lambda x, t: x <= t, d_W, thr_w, worse_sign=+1.0)}
    for d in judge:
        probes["㉡ " + d] = gate_probe(lambda x, t: x <= t, delta[d],
                                      max(J[d], MULT_OTHER * se[d]), worse_sign=+1.0)
    n_m = sum(1 for p in probes.values() if not p["거짓 나옴"])
    n_n = sum(1 for p in probes.values() if not p["참 나옴"])
    n_dir = sum(1 for p in probes.values()
                if not p["방향 검사(악화 극값 거짓 ∧ 개선 극값 참)"])
    out["조항 78 탐침 (강화 · 자료 유래 격자 + 방향 검사 · 리터럴 0)"] = dict(
        probes, 계수={"㉮ 원리상 못 떨어짐": n_m, "㉯ 원리상 못 통과": n_n,
                    "🔴 방향 검사 위반": n_dir})
    out["판정 (사전등록 §4 · 판정 11칸 · 비반올림 집행)"] = {
        "앵커": bool(anchor_ok),
        "㉠ 표적 개선(덮개율 · 악화=하락)": {"통과": g1, "Δ덮개율": round(d_cov, 4),
                                  "문턱 max(J′_cov,2SE)": round(thr_t, 4)},
        "㉡ 도메인 MdAPE 유의 악화(판정 8 · 악화=상승)": {
            "통과": g2, "걸린 도메인": bad if bad else "없음(0/8)"},
        "㉢ 전체 MdAPE 비악화(🔴 부호 정정 · 악화=상승)": {
            "통과": g3, "Δ전체": round(d_tot, 4),
            "문턱 +max(J′_전체,2SE)": round(thr_tot, 4),
            "원값": {"Δ전체": d_tot, "문턱": thr_tot}},
        "㉣ 폭 한도(악화=증가)": {"통과": g4, "Δ폭": round(d_W, 4),
                          "문턱 0.10×단일 중앙값 폭": round(thr_w, 4)},
        "게임·만화(관찰 — n_val<30)": {d: {"Δ": round(delta[d], 4), "SE": round(se[d], 4)}
                                   for d in SMALL}}
    if n_dir > 0:
        verdict = "등록 결함 — 탐침 방향 검사 위반 %d (관찰 강등 · 배포 0)" % n_dir
    elif not anchor_ok:
        verdict = "관찰 강등 — 앵커 불통과 (배포 0)"
    elif g1 and g2 and g3 and g4:
        verdict = "성공 — 배포 진행 (사전등록 §6 절차 그대로)"
    elif g1:
        verdict = "부분 — ㉠ 통과나 ㉡/㉢/㉣ 불통과 (배포 0)"
    else:
        verdict = "실패 — ㉠ 불통과 (배포 0)"
    out["판정어"] = verdict

    # ── 관찰 — 배포(seed 997) 대비 (관찰 전용 12칸) ───────────────────
    out["관찰 — 앙상블 대 배포 997 (12칸 · 확증에 안 씀)"] = {
        **{d: {"앙상블": round(mdape_e[d], 4), "배포 997": pre_dom[d],
               "Δ": round(mdape_e[d] - pre_dom[d], 4)} for d in ROSTER},
        "전체": {"앙상블": round(tot_e, 4), "배포 997": lb_tot,
               "Δ": round(tot_e - lb_tot, 4)},
        "덮개율": {"앙상블": round(cover_e, 4), "배포 997": pre_cover,
                "Δ": round(cover_e - pre_cover, 4)}}

    # 배포물 (성공 시 조타수가 §6 절차대로 집행) — 구성원 5 전부 · 선택 없음
    out["배포물(성공 시 · §6 ① 그대로)"] = {
        "구성원": {str(sd): ckpts[sd] for sd in SEEDS},
        "결합": "분위수 텐서 (91,5) 산술 평균",
        "manifest": os.path.join(TROUT, "ensemble_manifest.json"),
        "비고": "선택 없음(5모형 전부) — 윗꼬리 뽑기 순환이 원리상 없다"}

    out["관찰 분모 신고(조항 79)"] = ("대비 주장 1(덮개율 전역) · 관찰: 씨앗별 65 + 앙상블 13 + "
                                "앵커 11 + 앵커 참고 11 + J″ 13 + Δ·SE 26 + 헤드라인 5 + "
                                "배포997 대비 12 = 156 · 판정 11(㉠1 ㉡8 ㉢1 ㉣1) · "
                                "배포 시 LODO 관찰 += 10")
    out["총소요초"] = round(time.time() - t_all, 1)
    out["끝 시각"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "Δ덮개율": round(d_cov, 4), "p": p_one,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
