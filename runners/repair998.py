# -*- coding: utf-8 -*-
"""수리 998 러너 — 표적 «웹툰» (루프 v5.0 제5장 · 사전등록 docs/탐색/998.md 에서 언 코드).

조각 여섯 (조항 79 — 대비 주장은 웹툰 하나 · 나머지 아홉 도메인은 관찰):
  P0e 배포 model.pt «평가 항등» — 내 평가식이 리더보드 transition 열을 재현하나 (조항 66)
  P0  현행 레시피 «재학습 항등» — 내 학습 루프가 transition.py train 과 동치인가
  P1  도메인 원핫 제거 (LODO B 스타일 · 텍스트 전용 조건)
  P2  도메인-원핫 드롭아웃 p=0.5 (학습 때만 · 추론 불변)
  P3  도메인 균형 표본 (배치를 도메인 균등 추첨)
  P4  가중감쇠 1e-4 (Adam weight_decay)
  P5  조기중단 1500 스텝

채택 규칙(사전등록 — 기계로 적용):
  P1~P5 중 ㉠ 웹툰 val MdAPE < 전(리더보드 0.2149) ㉡ 타 도메인 최대 악화 < 웹툰 개선폭의 ½
  ㉢ val 전체 90% 덮개율 ≥ 전(report.json 0.7242) — 셋 다 만족하는 것 가운데
  웹툰 MdAPE 최소를 승자로. 없으면 승자 없음(배포 안 함).

헤드라인 통계(조항 79 개정): 웹툰 val 60 개체의 짝지은 APE(전=배포 model.pt · 후=승자 seed 997)
  Δ중앙값 · 붓스트랩 SE(B=10000 · seed 998) · t · 동부호 수 · 부호뒤집기 순열 한쪽꼬리 p.
안정성 관찰: 승자 설정을 seed 998·999 로 재학습.

🔴 CPU 전용 · torch.set_num_threads(4) · 유료 API 0 · 배포 파일 무변경(읽기만).
씀: python3 runners/repair998.py            # 산출 runners/out998_pieces.json
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
SEED = 997
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
PROG_DIR = os.path.join(ART, "exp", "repair998")
OUT_JSON = "/Users/ax/world_model/runners/out998_pieces.json"
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
N_BOOT, N_PERM, STAT_SEED = 10000, 10000, 998


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def prog(rec):
    os.makedirs(PROG_DIR, exist_ok=True)
    with open(os.path.join(PROG_DIR, "progress.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(rec, t=time.strftime("%H:%M:%S")), ensure_ascii=False) + "\n")


# ── 자료 (transition.SAO 와 같은 전처리 — lodo.py 전례) ───────────────
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

C_FULL = np.concatenate([onehot, sin, cos, year, base, E], axis=1).astype(np.float32)   # 현행
C_NOOH = np.concatenate([sin, cos, year, base, E], axis=1).astype(np.float32)           # P1
TR_IDX = np.where(split == 0)[0]
VA_IDX = np.where(split == 1)[0]
POOLS = {d: TR_IDX[dom_id[TR_IDX] == d] for d in range(n_dom)}


# ── 평가 — council build · transition.evaluate 와 같은 눈금 ──────────
def eval_model(model, C):
    model.eval()
    with torch.no_grad():
        xe = torch.from_numpy(np.concatenate([Sc[VA_IDX], C[VA_IDX]], axis=1))
        pred = model(xe).numpy()                       # (n,91,5) 잔차 눈금
    b = base[VA_IDX]
    cum_true = np.expm1(R[VA_IDX] + b).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + b).sum(axis=1)
    ape = np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1.0)
    cover = float(((R[VA_IDX] >= pred[..., 0]) & (R[VA_IDX] <= pred[..., 4])).mean())
    per_dom = {DOMAINS[d]: round(float(np.median(ape[dom_id[VA_IDX] == d])), 4)
               for d in range(n_dom)}
    return {"도메인별 MdAPE": per_dom, "전체 MdAPE": round(float(np.median(ape)), 4),
            "90% 덮개율": round(cover, 4)}, ape


def train_cfg(C, cfg, seed):
    d_in = Sc.shape[1] + C.shape[1]
    torch.manual_seed(seed)
    model = Transition(d_in, hidden=HIDDEN)
    wd = cfg.get("weight_decay", 0.0)
    opt = torch.optim.Adam(model.parameters(), lr=LR, weight_decay=wd)
    steps = cfg.get("steps", STEPS)
    t0 = time.time()
    loss = None
    for step in range(steps):
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
        Cb = C[ii]
        if cfg.get("dom_dropout"):
            rng2 = np.random.default_rng([9982, step])
            mask = rng2.random(BATCH) < cfg["dom_dropout"]
            if mask.any():
                Cb = Cb.copy()
                Cb[mask, :n_dom] = 0.0
        x = torch.from_numpy(np.concatenate([Sc[ii], Cb], axis=1))
        r = torch.from_numpy(R[ii])
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
    return model, round(float(loss.item()), 5), round(time.time() - t0, 1)


def median_diff(a, b, idx=None):
    if idx is None:
        return float(np.median(b) - np.median(a))
    return float(np.median(b[idx]) - np.median(a[idx]))


def main():
    t_all = time.time()
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    rep = json.load(open(os.path.join(TROUT, "report.json"), encoding="utf-8"))
    pre_dom = {d: r["transition"] for d, r in lb["도메인별"].items()}
    pre_cover = rep["평가"]["90% 구간 덮개율(목표 0.90)"]
    out = {"러너": "runners/repair998.py", "표적": "웹툰",
           "잰 소스 (조항 66)": {
               "sao.npz": sha16(os.path.join(TRI, "sao.npz")),
               "text_emb_qwen05b.npz": sha16(os.path.join(TRI, "text_emb_qwen05b.npz")),
               "model.pt(전·배포)": sha16(os.path.join(TROUT, "model.pt")),
               "leaderboard.json(전)": sha16(os.path.join(TROUT, "leaderboard.json")),
               "러너 자신": sha16(os.path.abspath(__file__))},
           "전(등록 판)": {"웹툰": pre_dom["웹툰"], "덮개율": pre_cover},
           "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
                  "seed": SEED, "threads": 4, "device": "cpu"}}

    # ── P0e: 배포 model.pt 평가 항등 ──────────────────────────────────
    ck = torch.load(os.path.join(TROUT, "model.pt"), map_location="cpu", weights_only=False)
    m0 = Transition(ck["d_in"], hidden=ck["hidden"])
    m0.load_state_dict(ck["model"])
    ev0, ape_pre = eval_model(m0, C_FULL)
    mism = {d: (ev0["도메인별 MdAPE"][d], pre_dom[d]) for d in pre_dom
            if abs(ev0["도메인별 MdAPE"][d] - pre_dom[d]) > 1e-4}
    out["P0e 평가 항등"] = {"평가": ev0, "리더보드와 어긋난 칸": mism if mism else "없음(10/10 일치)"}
    prog({"조각": "P0e", "일치": not mism})

    configs = [
        ("P0 재학습 항등(현행 레시피)", C_FULL, {}),
        ("P1 원핫 제거", C_NOOH, {}),
        ("P2 원핫 드롭아웃 0.5", C_FULL, {"dom_dropout": 0.5}),
        ("P3 도메인 균형 표본", C_FULL, {"balanced": True}),
        ("P4 가중감쇠 1e-4", C_FULL, {"weight_decay": 1e-4}),
        ("P5 조기중단 1500", C_FULL, {"steps": 1500}),
    ]
    results, apes = {}, {}
    for name, C, cfg in configs:
        model, pin, sec = train_cfg(C, cfg, SEED)
        ev, ape = eval_model(model, C)
        results[name] = dict(ev, **{"pinball(train)": pin, "sec": sec})
        apes[name] = ape
        prog({"조각": name, "웹툰": ev["도메인별 MdAPE"]["웹툰"],
              "덮개율": ev["90% 덮개율"], "sec": sec})
    out["조각별 결과 (관찰 — 다중비교 분모: 후보 5)"] = results

    # ── 채택 규칙 (사전등록 그대로 · 기계 적용) ───────────────────────
    verdicts = {}
    for name in list(results)[1:]:                      # P1~P5
        ev = results[name]
        imp = pre_dom["웹툰"] - ev["도메인별 MdAPE"]["웹툰"]
        worst = max((ev["도메인별 MdAPE"][d] - pre_dom[d], d)
                    for d in pre_dom if d != "웹툰")
        verdicts[name] = {
            "웹툰 개선폭": round(imp, 4),
            "타 도메인 최대 악화": {"도메인": worst[1], "악화": round(worst[0], 4)},
            "㉠ 웹툰 개선": bool(imp > 0),
            "㉡ 최대 악화 < 개선폭/2": bool(worst[0] < imp / 2),
            "㉢ 덮개율 비악화": bool(ev["90% 덮개율"] >= pre_cover)}
    out["채택 검사 ㉠㉡㉢"] = verdicts
    eligible = [n for n, v in verdicts.items()
                if v["㉠ 웹툰 개선"] and v["㉡ 최대 악화 < 개선폭/2"] and v["㉢ 덮개율 비악화"]]
    winner = (min(eligible, key=lambda n: results[n]["도메인별 MdAPE"]["웹툰"])
              if eligible else None)
    out["승자"] = winner if winner else "없음 — ㉠㉡㉢ 셋 다 만족하는 조각이 없다 (배포 안 함)"
    prog({"승자": winner})

    # ── 헤드라인 통계 + 안정성 (승자가 있을 때만) ─────────────────────
    if winner:
        wi = np.where(dom_id[VA_IDX] == DOMAINS.index("웹툰"))[0]
        a, b = ape_pre[wi], apes[winner][wi]            # 짝지은 60 개체 APE
        d_obs = median_diff(a, b)
        rng = np.random.default_rng(STAT_SEED)
        boots = np.empty(N_BOOT)
        for k in range(N_BOOT):
            idx = rng.integers(0, len(a), size=len(a))
            boots[k] = median_diff(a, b, idx)
        se = float(boots.std(ddof=1))
        flips = rng.random((N_PERM, len(a))) < 0.5
        perm = np.empty(N_PERM)
        aa, bb = np.tile(a, (N_PERM, 1)), np.tile(b, (N_PERM, 1))
        sw = aa[flips].copy()
        aa[flips] = bb[flips]
        bb[flips] = sw
        perm = np.median(bb, axis=1) - np.median(aa, axis=1)
        p_one = float((1 + (perm <= d_obs).sum()) / (1 + N_PERM))
        out["헤드라인(웹툰 · 조항 79)"] = {
            "n(짝)": int(len(a)), "Δ중앙APE(후−전)": round(d_obs, 4),
            "붓스트랩 SE": round(se, 4), "t": round(d_obs / se, 2) if se > 0 else None,
            "동부호(개선 개체 수)": "%d/%d" % (int((b < a).sum()), len(a)),
            "부호뒤집기 순열 p(한쪽꼬리·개선 방향)": round(p_one, 5),
            "B": {"붓스트랩": N_BOOT, "순열": N_PERM, "seed": STAT_SEED}}
        stab = {}
        for sd in (998, 999):
            name0, C, cfg = [c for c in configs if c[0] == winner][0]
            model, pin, sec = train_cfg(C, cfg, sd)
            ev, _ = eval_model(model, C)
            worst = max((ev["도메인별 MdAPE"][d] - pre_dom[d]) for d in pre_dom if d != "웹툰")
            stab["seed %d" % sd] = {"웹툰": ev["도메인별 MdAPE"]["웹툰"],
                                    "타 도메인 최대 악화": round(worst, 4),
                                    "덮개율": ev["90% 덮개율"], "sec": sec}
            prog({"안정성": sd, **stab["seed %d" % sd]})
        out["안정성 관찰(승자 · seed 998/999)"] = stab

    out["총소요초"] = round(time.time() - t_all, 1)
    out["끝 시각"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"승자": out["승자"], "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
