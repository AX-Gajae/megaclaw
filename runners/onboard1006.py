# -*- coding: utf-8 -*-
"""온보딩 1006 — B-스타일(텍스트 전용) 앙상블 학습 → 드라마 삼중쌍 → 0.5B 임베딩 → 제로샷 평가.

사전등록 docs/탐색/1006.md §1~§6 에서 얼었다(조항 66 · 74). 단계는 부명령으로 강제한다:

  python3 runners/onboard1006.py train    # ① 기존 10도메인만으로 B-앙상블 5(씨앗 1601~1605)
                                          #    + 앵커 A 재현 + 방향 탐침 + DONE_TRAIN 스탬프
  python3 runners/onboard1006.py triples  # ③ (fetch 뒤) 드라마 원본 → 삼중쌍 npz
  python3 runners/onboard1006.py embed    # ④ 드라마 텍스트 → Qwen2.5-0.5B 임베딩(자구 미러)
  python3 runners/onboard1006.py eval     # ⑤ B-앙상블 vs persistence vs last7 + 관찰 6칸

🔴 누수 원리 차단: `train` 은 드라마 자료를 원리상 못 본다(기존 sao.npz 만 · sha 대조).
   `fetch`(별도 러너)는 DONE_TRAIN 없으면 시작을 거부한다. 드라마 곡선은 오직 평가에만.
🔴 CPU 전용 · torch.set_num_threads(4) · 각 학습 전 load1 > 10 이면 60초 대기(러너 안 관문).
"""
import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.transition import Transition, pinball, load_ensemble, load_conformal  # noqa: E402

torch.set_num_threads(4)

SEEDS = (1601, 1602, 1603, 1604, 1605)      # 사전등록 §3 — 기존 집합 전부 회피
BOOT_B, BOOT_SEED = 10000, 11006            # §1 클러스터 붓스트랩
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
EXP = os.path.join(ART, "exp", "onboard1006")
DRAMA = os.path.join(ART, "onboard_drama")
REPO = "/Users/ax/world_model"
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

# §0 등록 sha (시작 시 실측 대조 — 어긋나면 「불일치」로 중단)
SAO_SHA = "f120013017dcf512"
EMB_SHA = "c4128e73c8ea52ca"
MAN_SHA = "3a5c2543a55f1dab"
# §4 앵커 A (게재 반올림 몫 1.5e-4)
ANCHOR_MDAPE, ANCHOR_COV, TOL = 0.0571, 0.9173, 1.5e-4
PERS_LB = 0.1235                            # §4 보정 팔 굵은 관문(리더보드 persistence)


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def prog(rec):
    os.makedirs(EXP, exist_ok=True)
    with open(os.path.join(EXP, "progress.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(rec, t=time.strftime("%Y-%m-%dT%H:%M:%S")),
                           ensure_ascii=False) + "\n")


def load_gate():
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60
    return waited


# ── 게이트 함수(부호 서명 대상 — v5.3) ────────────────────────────────
def gate_G1(delta):
    """Δ₁ = 삼중쌍 가능 개체 수 − 30 · 떨어지는 쪽 −."""
    return delta >= 0


def gate_G2(delta, thr):
    """Δ₂ = MdAPE_pers − MdAPE_B · 문턱 thr>0 · 떨어지는 쪽 −."""
    return delta > thr


def gate_A0(delta):
    """앵커 ㉮: Δ₀ = 0.1235 − MdAPE_Bval · 떨어지는 쪽 −."""
    return delta >= 0


def sign_probes(t=1.0):
    """측정 «전» 방향 탐침(v5.3-2): 악화 극값(−2t) 거짓 · 개선 극값(+2t) 참."""
    checks = {
        "G1 악화극값 거짓": gate_G1(-2 * t) is False,
        "G1 개선극값 참": gate_G1(+2 * t) is True,
        "G2 악화극값 거짓": gate_G2(-2 * t, t) is False,
        "G2 개선극값 참": gate_G2(+2 * t, t) is True,
        "앵커㉮ 악화극값 거짓": gate_A0(-2 * t) is False,
        "앵커㉮ 개선극값 참": gate_A0(+2 * t) is True,
    }
    ok = all(checks.values())
    return ok, checks


# ── 기존 10도메인 자료(lodo1004 자구 미러) ────────────────────────────
def load_existing():
    for p, want in ((os.path.join(TRI, "sao.npz"), SAO_SHA),
                    (os.path.join(TRI, "text_emb_qwen05b.npz"), EMB_SHA)):
        got = sha16(p)
        if got != want:
            raise RuntimeError("🔴 잰 소스 불일치: %s 등록 %s ≠ 실측 %s" % (p, want, got))
    z = np.load(os.path.join(TRI, "sao.npz"))
    with open(os.path.join(TRI, "domains.json"), encoding="utf-8") as f:
        doms = json.load(f)
    d = {}
    d["S"] = np.log1p(z["S"].astype(np.float64)).astype(np.float32)
    d["O"] = np.log1p(z["O"].astype(np.float64)).astype(np.float32)
    d["base"] = d["S"].mean(axis=1, keepdims=True)
    d["Sc"] = d["S"] - d["base"]
    d["R"] = d["O"] - d["base"]
    d["dom_id"] = z["dom_id"].astype(np.int64)
    d["split"] = z["split"]
    doy = z["doy"].astype(np.float32)
    d["sin"] = np.sin(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
    d["cos"] = np.cos(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
    d["year"] = ((z["year"].astype(np.float32) - 2013.0) / 10.0)[:, None]
    d["E"] = np.load(os.path.join(TRI, "text_emb_qwen05b.npz"))["E"].astype(np.float32)
    assert len(d["E"]) == len(d["S"]), "🔴 텍스트 임베딩 행 수 불일치"
    d["C_B"] = np.concatenate([d["sin"], d["cos"], d["year"], d["base"], d["E"]],
                              axis=1).astype(np.float32)
    n_dom = int(d["dom_id"].max()) + 1
    onehot = np.zeros((len(d["S"]), n_dom), dtype=np.float32)
    onehot[np.arange(len(d["S"])), d["dom_id"]] = 1.0
    d["C_FULL"] = np.concatenate([onehot, d["sin"], d["cos"], d["year"], d["base"],
                                  d["E"]], axis=1).astype(np.float32)
    d["doms"] = doms
    # 홀드아웃 98 개체 재현(사전등록 1004 · seed [11004,0] — 어긋나면 중단)
    meta = [json.loads(l) for l in open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")]
    tr = np.where(d["split"] == 0)[0]
    ent_rows, ent_dom = {}, {}
    for i in tr:
        nm = meta[int(i)]["개체"]
        ent_rows.setdefault(nm, []).append(int(i))
        ent_dom.setdefault(nm, doms[d["dom_id"][int(i)]])
    rng = np.random.default_rng([11004, 0])
    bd = {}
    for nm in sorted(ent_dom):
        bd.setdefault(ent_dom[nm], []).append(nm)
    picked = []
    for dm in sorted(bd):
        names = sorted(bd[dm])
        k = max(1, int(np.ceil(0.15 * len(names))))
        sel = rng.permutation(len(names))[:k]
        picked += [names[j] for j in sel]
    hold_rows = set(i for nm in picked for i in ent_rows[nm])
    assert len(picked) == 98 and len(hold_rows) == 1752, (len(picked), len(hold_rows))
    mask = np.zeros(len(d["S"]), dtype=bool)
    mask[sorted(hold_rows)] = True
    d["tr_idx"] = np.array([i for i in tr if not mask[i]], dtype=np.int64)
    d["va_idx"] = np.where(d["split"] == 1)[0]
    assert len(d["tr_idx"]) == 7773, len(d["tr_idx"])
    return d


def cum_mdape(pred_q50_log, R, base):
    cum_true = np.expm1(R + base).sum(axis=1)
    cum_pred = np.expm1(pred_q50_log + base).sum(axis=1)
    return float(np.median(np.abs(cum_pred - cum_true) / np.maximum(cum_true, 1)))


def row_ape(pred_q50_log, R, base):
    cum_true = np.expm1(R + base).sum(axis=1)
    cum_pred = np.expm1(pred_q50_log + base).sum(axis=1)
    return np.abs(cum_pred - cum_true) / np.maximum(cum_true, 1)


def predict(model, Sc, C, bs=2048):
    model.eval()
    outs = []
    with torch.no_grad():
        for i in range(0, len(Sc), bs):
            x = torch.from_numpy(np.concatenate([Sc[i:i + bs], C[i:i + bs]], axis=1))
            outs.append(model(x).numpy())
    return np.concatenate(outs, axis=0)


def train_one(seed, d):
    d_in = d["Sc"].shape[1] + d["C_B"].shape[1]
    torch.manual_seed(seed)
    model = Transition(d_in, hidden=HIDDEN)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    t0 = time.time()
    loss = None
    tr = d["tr_idx"]
    for step in range(STEPS):
        rng = np.random.default_rng([seed, step])
        ii = tr[rng.integers(0, len(tr), size=BATCH)]
        x = torch.from_numpy(np.concatenate([d["Sc"][ii], d["C_B"][ii]], axis=1))
        r = torch.from_numpy(d["R"][ii])
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
    return model, d_in, round(float(loss.item()), 5), round(time.time() - t0, 1)


def load_bstyle():
    stamp = json.load(open(os.path.join(EXP, "DONE_TRAIN"), encoding="utf-8"))
    members = []
    for s in SEEDS:
        p = os.path.join(EXP, "bstyle_seed%d.pt" % s)
        got = sha16(p)
        if got != stamp["모형 sha"][str(s)]:
            raise RuntimeError("🔴 B-모형 sha 불일치: %s" % p)
        ck = torch.load(p, map_location="cpu", weights_only=False)
        m = Transition(ck["d_in"], hidden=ck["hidden"])
        m.load_state_dict(ck["model"])
        m.eval()
        members.append(m)
    return members, stamp


# ── ① train ──────────────────────────────────────────────────────────
def phase_train():
    os.makedirs(EXP, exist_ok=True)
    if os.path.exists(os.path.join(DRAMA, "raw")):
        # 순서 문서화: 드라마 원본이 이미 있으면 «학습이 먼저»라는 사전등록 순서가 깨진 것
        raise RuntimeError("🔴 onboard_drama/raw 가 이미 있다 — 사전등록 §6 순서 위반")
    ok, checks = sign_probes()
    if not ok:
        out = {"중단": "방향 탐침 실패(v5.3-2) — 측정 없이 중단", "탐침": checks}
        json.dump(out, open(os.path.join(REPO, "runners/out1006_bstyle.json"), "w",
                            encoding="utf-8"), ensure_ascii=False, indent=1)
        raise SystemExit(1)
    prog({"단계": "train 시작", "탐침": "6/6 통과"})
    d = load_existing()
    va = d["va_idx"]

    # 앵커 A — 배포 앙상블+등각의 val 재현(실행 간 · §4)
    ens, man, shas = load_ensemble()
    conf = load_conformal()
    assert conf is not None, "🔴 conformal.json 없음"
    delta = conf[0]
    man_got = sha16(os.path.join(ART, "transition", "ensemble_manifest.json"))
    if man_got != MAN_SHA:
        raise RuntimeError("🔴 manifest sha 불일치: 등록 %s ≠ 실측 %s" % (MAN_SHA, man_got))
    pred = None
    with torch.no_grad():
        x = torch.from_numpy(np.concatenate([d["Sc"][va], d["C_FULL"][va]], axis=1))
        pred = ens(x).numpy()
    q05 = pred[..., 0] - delta
    q95 = pred[..., 4] + delta
    Rv = d["R"][va]
    cov = float(((Rv >= q05) & (Rv <= q95)).mean())
    md = cum_mdape(pred[..., 2], Rv, d["base"][va])
    anchor_ok = (abs(md - ANCHOR_MDAPE) <= TOL) and (abs(cov - ANCHOR_COV) <= TOL)
    prog({"앵커 A": {"MdAPE": md, "덮개율": cov, "통과": anchor_ok}})

    # B-스타일 5 학습(씨앗 1601~1605 · 순차 · load 관문)
    model_shas, losses, secs, singles_val = {}, {}, {}, {}
    ens_pred_val = np.zeros((len(va), 91, 5), dtype=np.float64)
    for s in SEEDS:
        load_gate()
        m, d_in, ls, sec = train_one(s, d)
        p = os.path.join(EXP, "bstyle_seed%d.pt" % s)
        torch.save({"model": m.state_dict(), "d_in": d_in, "hidden": HIDDEN,
                    "seed": s, "조건": "B(텍스트 전용 · 원핫 없음)",
                    "학습": "train−홀드아웃98 = 7773행"}, p)
        model_shas[str(s)] = sha16(p)
        losses[str(s)] = ls
        secs[str(s)] = sec
        pv = predict(m, d["Sc"][va], d["C_B"][va])
        singles_val[str(s)] = cum_mdape(pv[..., 2], Rv, d["base"][va])
        ens_pred_val += pv.astype(np.float64)
        prog({"학습 완료": s, "pinball": ls, "초": sec, "단일 val MdAPE": singles_val[str(s)]})
    ens_pred_val /= len(SEEDS)
    md_bval = cum_mdape(ens_pred_val[..., 2].astype(np.float32), Rv, d["base"][va])
    cov_bval_raw = float(((Rv >= ens_pred_val[..., 0]) & (Rv <= ens_pred_val[..., 4])).mean())
    d0 = PERS_LB - md_bval
    stamp = {"끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "모형 sha": model_shas, "코드 sha(러너 자신)": sha16(os.path.abspath(__file__)),
             "학습 표본": int(len(d["tr_idx"])), "홀드아웃 재현": "98 개체 · 1752 행 ✔",
             "잰 소스": {"sao.npz": SAO_SHA, "text_emb_qwen05b.npz": EMB_SHA}}
    json.dump(stamp, open(os.path.join(EXP, "DONE_TRAIN"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    out = {"러너 자신": sha16(os.path.abspath(__file__)),
           "사전등록": "docs/탐색/1006.md §3~§4",
           "방향 탐침(측정 전 · v5.3-2)": checks,
           "앵커 A(배포 재현 · 실행 간)": {
               "val 전체 MdAPE": round(md, 6), "등록": ANCHOR_MDAPE,
               "val 덮개율(δ 적용)": round(cov, 6), "등록 덮개율": ANCHOR_COV,
               "허용(게재 반올림 몫)": TOL, "통과": bool(anchor_ok)},
           "B-앙상블(씨앗 1601~1605 · 텍스트 전용 · 드라마 반입 전)": {
               "학습 표본": int(len(d["tr_idx"])), "steps": STEPS, "batch": BATCH,
               "lr": LR, "hidden": HIDDEN, "threads": torch.get_num_threads(),
               "pinball": losses, "초": secs, "모형 sha": model_shas,
               "단일 val 전체 MdAPE(관찰)": singles_val,
               "앙상블 val 전체 MdAPE": round(md_bval, 6),
               "앙상블 val 덮개율(생 · 등각 없음 · 관찰)": round(cov_bval_raw, 6)},
           "앵커 ㉮(보정 팔 굵은 관문)": {
               "Δ₀ = 0.1235 − B_val": round(d0, 6),
               "여유(=Δ₀−0 · 비반올림)": d0, "통과": bool(gate_A0(d0)),
               "불통과 시": "전 조각 「관찰」 강등(§4)"},
           "DONE_TRAIN": stamp["끝 시각"]}
    json.dump(out, open(os.path.join(REPO, "runners/out1006_bstyle.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False)[:2000])


# ── ③ triples ────────────────────────────────────────────────────────
def phase_triples():
    assert os.path.exists(os.path.join(EXP, "DONE_TRAIN")), "🔴 DONE_TRAIN 없음(§6 순서)"
    hv = json.load(open(os.path.join(DRAMA, "harvest.json"), encoding="utf-8"))
    H = hv["H(원천 지평 · 최신 관측일)"]
    Hd = np.datetime64("%s-%s-%s" % (H[:4], H[4:6], H[6:8]))
    S, O, meta = [], [], []
    n_short, n_tiny, fills, spans = 0, 0, {}, {}
    for e in hv["개체"]:
        if e.get("실패"):
            continue
        raw = json.load(open(os.path.join(DRAMA, "raw", "%s.json" % e["pageid"]),
                             encoding="utf-8"))
        days = {it["timestamp"][:8]: int(it["views"]) for it in raw["pageviews"]["items"]}
        ks = sorted(days)
        first = np.datetime64("%s-%s-%s" % (ks[0][:4], ks[0][4:6], ks[0][6:8]))
        span = int((Hd - first).astype(int)) + 1
        grid = np.zeros(span, dtype=np.float64)
        n_fill = 0
        for off in range(span):
            dt = first + np.timedelta64(off, "D")
            key = str(dt).replace("-", "")
            if key in days:
                grid[off] = days[key]
            else:
                n_fill += 1
        fills[raw["제목"]] = n_fill
        spans[raw["제목"]] = span
        if span < 181:
            if span >= 91:
                n_short += 1        # 「관측은 있으나 삼중쌍 불가(짧은 곡선)」 — 조항 59
            else:
                n_tiny += 1         # span < 91 — 곡선 자체가 서지 않음
            continue
        text = "%s · 대한민국 텔레비전 드라마 · %s · ko" % (
            raw["제목"], (raw.get("요약") or "")[:800])
        for a0 in range(90, span - 90, 7):
            anchor = first + np.timedelta64(a0, "D")
            iso = str(anchor)
            S.append(grid[a0 - 90:a0])
            O.append(grid[a0:a0 + 91])
            meta.append({"개체": "DRAMA-%s" % e["pageid"], "제목": raw["제목"],
                         "언제": iso, "도메인": "드라마", "분할": "eval",
                         "텍스트": text[:2000], "종영": bool(e.get("종영")),
                         "출처": raw.get("요약출처", ""), "수집시각": raw.get("수집시각", "")})
    S = np.asarray(S, dtype=np.float32)
    O = np.asarray(O, dtype=np.float32)
    year = np.asarray([float(m["언제"][:4]) + (float(m["언제"][5:7]) - 0.5) / 12.0
                       for m in meta], dtype=np.float32)
    doy = np.asarray([int(m["언제"][5:7]) * 30.4 + int(m["언제"][8:10])
                      for m in meta], dtype=np.float32)
    np.savez_compressed(os.path.join(DRAMA, "drama_sao.npz"), S=S, O=O, year=year, doy=doy)
    with open(os.path.join(DRAMA, "drama_meta.jsonl"), "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    ents = sorted(set(m["개체"] for m in meta))
    rep = {"삼중쌍 가능 개체": len(ents), "행(개체창)": int(len(S)),
           "짧은 곡선(91≤span<181 · 조항 59 신고)": n_short,
           "극短(span<91 · 조항 59 신고)": n_tiny,
           "개체별 span": spans,
           "결측일 0 채움(개체별)": fills, "H": H,
           "drama_sao sha": sha16(os.path.join(DRAMA, "drama_sao.npz"))}
    json.dump(rep, open(os.path.join(DRAMA, "drama_report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False)[:1500])


# ── ④ embed ──────────────────────────────────────────────────────────
def phase_embed():
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    from transformers import AutoModel, AutoTokenizer
    SNAP = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
            "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
    meta = [json.loads(l) for l in open(os.path.join(DRAMA, "drama_meta.jsonl"),
                                        encoding="utf-8")]
    texts = [m["텍스트"] for m in meta]
    uniq = sorted(set(texts))
    tok = AutoTokenizer.from_pretrained(SNAP)
    model = AutoModel.from_pretrained(SNAP, dtype=torch.float32)
    model.eval()
    emb_u = {}
    with torch.no_grad():
        for i in range(0, len(uniq), 16):
            batch = uniq[i:i + 16]
            enc = tok(batch, padding=True, truncation=True, max_length=96,
                      return_tensors="pt")
            h = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
            e = (h * mask).sum(1) / mask.sum(1).clamp(min=1.0)
            for t, v in zip(batch, e.numpy().astype(np.float32)):
                emb_u[t] = v
    E = np.stack([emb_u[t] for t in texts]).astype(np.float32)
    np.savez(os.path.join(DRAMA, "drama_text_emb.npz"), E=E)
    cfg = {"모델": "Qwen2.5-0.5B (base)", "스냅숏": SNAP,
           "풀링": "last_hidden_state attention-mask 평균", "최대토큰": 96,
           "형상": list(E.shape), "유일 텍스트": len(uniq), "장치": "cpu",
           "sha": sha16(os.path.join(DRAMA, "drama_text_emb.npz"))}
    json.dump(cfg, open(os.path.join(DRAMA, "drama_text_emb.config.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(cfg, ensure_ascii=False))


# ── ⑤ eval ───────────────────────────────────────────────────────────
def phase_eval():
    ok, checks = sign_probes()
    assert ok, "🔴 방향 탐침 실패"
    members, stamp = load_bstyle()
    bs_train = json.load(open(os.path.join(REPO, "runners/out1006_bstyle.json"),
                              encoding="utf-8"))
    z = np.load(os.path.join(DRAMA, "drama_sao.npz"))
    meta = [json.loads(l) for l in open(os.path.join(DRAMA, "drama_meta.jsonl"),
                                        encoding="utf-8")]
    E = np.load(os.path.join(DRAMA, "drama_text_emb.npz"))["E"].astype(np.float32)
    assert len(E) == len(z["S"]) == len(meta)
    S = np.log1p(z["S"].astype(np.float64)).astype(np.float32)
    O = np.log1p(z["O"].astype(np.float64)).astype(np.float32)
    base = S.mean(axis=1, keepdims=True)
    Sc = S - base
    R = O - base
    doy = z["doy"].astype(np.float32)
    sin = np.sin(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
    cos = np.cos(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
    year = ((z["year"].astype(np.float32) - 2013.0) / 10.0)[:, None]
    C_B = np.concatenate([sin, cos, year, base, E], axis=1).astype(np.float32)
    ents = np.array([m["개체"] for m in meta])
    n_ent = len(set(ents.tolist()))
    n_row = len(S)

    # G1 전제 관문
    d1 = n_ent - 30
    g1 = gate_G1(d1)

    # B-앙상블 예측(+ 단일 5)
    preds = [predict(m, Sc, C_B) for m in members]
    pB = np.mean(np.stack(preds), axis=0)
    apeB = row_ape(pB[..., 2], R, base)
    ape_pers = row_ape(np.zeros_like(R), R, base)
    last7 = Sc[:, -7:].mean(axis=1, keepdims=True) * np.ones_like(R)
    ape_l7 = row_ape(last7, R, base)
    mdB, mdP, mdL = (float(np.median(apeB)), float(np.median(ape_pers)),
                     float(np.median(ape_l7)))
    singles = {str(s): float(np.median(row_ape(pr[..., 2], R, base)))
               for s, pr in zip(SEEDS, preds)}
    J_ens = max(abs(v - mdB) for v in singles.values())

    def mae(p):
        return float(np.abs(p - R).mean())
    covB_raw = float(((R >= pB[..., 0]) & (R <= pB[..., 4])).mean())
    widB = float((pB[..., 4] - pB[..., 0]).mean())
    conf = load_conformal()
    delta = conf[0]
    covB_delta = float(((R >= pB[..., 0] - delta) & (R <= pB[..., 4] + delta)).mean())

    # 관찰 ① ② — A-스타일 영벡터(배포 앙상블 · 드라마 원핫 없음 → 0 벡터 · 분포 밖 실측)
    ens, man, shas = load_ensemble()
    C_A = np.concatenate([np.zeros((n_row, 10), dtype=np.float32), sin, cos, year,
                          base, E], axis=1).astype(np.float32)
    pA = predict(ens, Sc, C_A)
    mdA = float(np.median(row_ape(pA[..., 2], R, base)))
    covA_delta = float(((R >= pA[..., 0] - delta) & (R <= pA[..., 4] + delta)).mean())

    # 주대비 Δ₂ + 클러스터 붓스트랩 SE(개체 이름 · B=10000 · seed 11006)
    d2 = mdP - mdB
    uents = sorted(set(ents.tolist()))
    rows_of = {u: np.where(ents == u)[0] for u in uents}
    rng = np.random.default_rng([BOOT_SEED, 0])
    boots = np.empty(BOOT_B)
    covb = np.empty(BOOT_B)
    for b in range(BOOT_B):
        pick = rng.integers(0, len(uents), size=len(uents))
        ii = np.concatenate([rows_of[uents[j]] for j in pick])
        boots[b] = np.median(ape_pers[ii]) - np.median(apeB[ii])
        covb[b] = ((R[ii] >= pB[ii][..., 0]) & (R[ii] <= pB[ii][..., 4])).mean()
    se_d2 = float(boots.std(ddof=1))
    ci_d2 = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    se_cov = float(covb.std(ddof=1))
    thr2 = max(J_ens, 2 * se_d2)
    g2 = gate_G2(d2, thr2)
    # 자료 탐침(측정 후 · v5.3-3): 악화 극값 참 / 개선 극값 거짓 수
    post_bad = int(gate_G2(-2 * thr2, thr2) is True) + int(gate_G1(-60) is True) \
        + int(gate_A0(-2 * 0.1235) is True)
    post_miss = int(gate_G2(+2 * thr2, thr2) is False) + int(gate_G1(+60) is False) \
        + int(gate_A0(+2 * 0.1235) is False)

    # 관찰 ③ ④ — 유형 분할
    fin = np.array([bool(m["종영"]) for m in meta])
    tot91 = np.array([float(np.expm1(S[i]).sum()) for i in range(n_row)])
    ent_tot = {u: float(np.median([tot91[i] for i in rows_of[u]])) for u in uents}
    med_tot = float(np.median(list(ent_tot.values())))
    hot = np.array([ent_tot[e] > med_tot for e in ents])

    def split_md(mask):
        if mask.sum() == 0:
            return {"행": 0, "MdAPE_B": "해당 없음", "MdAPE_pers": "해당 없음"}
        return {"행": int(mask.sum()), "개체": len(set(ents[mask].tolist())),
                "MdAPE_B": round(float(np.median(apeB[mask])), 4),
                "MdAPE_pers": round(float(np.median(ape_pers[mask])), 4)}

    y_max_train, y_drama = 0.996, [float(year.min()), float(year.max())]
    # 판정어(§5 사전 고정)
    anchorA_ok = bs_train["앵커 A(배포 재현 · 실행 간)"]["통과"]
    anchor0_ok = bs_train["앵커 ㉮(보정 팔 굵은 관문)"]["통과"]
    if not anchorA_ok:
        verdict = "무효(하네스 불신)"
    elif not g1:
        verdict = "원천 불충분 — 온보딩 불가"
    elif not (anchor0_ok):
        verdict = "관찰 강등(앵커 ㉮ 불통과) — 수치는 관찰로만"
    elif g2:
        verdict = "온보딩 가능(제로샷 승)"
    elif abs(d2) <= thr2:
        verdict = "온보딩 가능(무승부 — 관성 동급 · 스트림 가치는 곡선 자산)"
    else:
        verdict = "관측 스트림은 선다 · 제로샷은 진다"

    out = {
        "러너 자신": sha16(os.path.abspath(__file__)),
        "사전등록": "docs/탐색/1006.md (§1 주대비 · §5 게이트·분모)",
        "잰 소스(조항 66)": {
            "B-모형 sha": stamp["모형 sha"], "DONE_TRAIN 끝 시각": stamp["끝 시각"],
            "drama_sao.npz": sha16(os.path.join(DRAMA, "drama_sao.npz")),
            "drama_text_emb.npz": sha16(os.path.join(DRAMA, "drama_text_emb.npz")),
            "harvest.json": sha16(os.path.join(DRAMA, "harvest.json")),
            "배포 manifest": MAN_SHA, "conformal δ": delta},
        "분모(문언 규율 #140)": {"행(개체창)": n_row, "유일 개체": n_ent},
        "방향 탐침(측정 전)": checks,
        "자료 탐침(측정 후 · v5.3-3)": {"㉰ 악화 극값 참": post_bad, "㉱ 개선 극값 거짓": post_miss},
        "표B 제로샷(드라마 · 15칸)": {
            "B-앙상블": {"누적91 MdAPE": round(mdB, 4), "q50 MAE(log)": round(mae(pB[..., 2]), 4),
                       "덮개율(생)": round(covB_raw, 4),
                       "덮개율(배포 δ 차용 — 관찰)": round(covB_delta, 4),
                       "폭(log)": round(widB, 4)},
            "persistence": {"누적91 MdAPE": round(mdP, 4), "q50 MAE(log)": round(mae(np.zeros_like(R)), 4),
                            "덮개율(생)": "해당 없음(점 예측)", "덮개율(δ)": "해당 없음", "폭": "해당 없음"},
            "last7": {"누적91 MdAPE": round(mdL, 4), "q50 MAE(log)": round(mae(last7), 4),
                      "덮개율(생)": "해당 없음(점 예측)", "덮개율(δ)": "해당 없음", "폭": "해당 없음"},
            "덮개율 클러스터 SE(개체)": round(se_cov, 5)},
        "게이트(여유 = Δ − 문턱 · 비반올림)": {
            "G1 수집": {"Δ₁": d1, "문턱": 0, "여유": d1, "통과": bool(g1)},
            "G2 주대비": {"Δ₂": d2, "문턱 max(J_ens, 2SE)": thr2, "J_ens": J_ens,
                        "SE_Δ(클러스터·B=10000·seed 11006)": se_d2,
                        "Δ₂ 95%CI": ci_d2, "여유": d2 - thr2, "통과": bool(g2)}},
        "관찰 6칸": {
            "① A-영벡터 MdAPE(분포 밖)": round(mdA, 4),
            "② A-영벡터 덮개율(δ 배포 경로)": round(covA_delta, 4),
            "③ 방영중 vs 종영": {"방영중": split_md(~fin), "종영": split_md(fin)},
            "④ 화제작 vs 비화제작(90일 총조회 중앙값 분할)": {
                "화제작": split_md(hot), "비화제작": split_md(~hot)},
            "⑤ 씨앗 지터": {"단일 MdAPE": singles, "J_ens": J_ens},
            "⑥ year 외삽": {"드라마 year 특징 범위": y_drama, "학습 최대": y_max_train}},
        "다음 앵커 정본 신고(v5.2 ㉯)": {
            "J_ens(씨앗 간 · 드라마 행)": J_ens,
            "B-val 전체 MdAPE(실행 간 기준점)": bs_train[
                "B-앙상블(씨앗 1601~1605 · 텍스트 전용 · 드라마 반입 전)"]["앙상블 val 전체 MdAPE"]},
        "판정어(§5 규칙)": verdict,
        "판 갱신": "없음(사전 명시 — 10 도메인 정의 무접촉)"}
    json.dump(out, open(os.path.join(REPO, "runners/out1006_zeroshot.json"), "w",
                        encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False)[:3000])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["train", "triples", "embed", "eval"])
    a = ap.parse_args()
    {"train": phase_train, "triples": phase_triples,
     "embed": phase_embed, "eval": phase_eval}[a.phase]()


if __name__ == "__main__":
    main()
