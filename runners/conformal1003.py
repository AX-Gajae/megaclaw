# -*- coding: utf-8 -*-
"""확증 1003 러너 — 배포 앙상블 위 «등각(split-conformal) 구간 보정» (루프 v5.3 동결 첫 사이클).

주대비 «하나»(조항 79): 전역 CQR 가산 보정(δ)이 ④ 90% 덮개율의 목표 거리
|0.90 − 덮개율| 을 줄이는가. 재학습 없음 — 모형(앙상블 manifest af7cebd02e77af9c) 불변 ·
보정층(q05−δ · q95+δ · q25/q50/q75 무접촉)만 얹는다.

보정셋(누수 금지): train «개체 이름» 단위 — 도메인 층화 20%(개체 뽑기 seed [11003,0]) ·
val(개체 분리 1,129 행 · 70 개체)과 개체 겹침 0. 🔴 정직 신고: 보정셋 개체는 앙상블 학습에
쓰였다(재학습 금지 제약) — 잔차가 낙관적일 수 있고 그 방향은 «val 과소 덮개»(목표 미달) 쪽이다.

판정(사전등록 docs/탐색/1003.md §3~§4 · 게이트마다 악화 방향 한 줄 · 비반올림 집행):
  앵커  배포 정본 재현 항등 13칸(도메인 10 + 전체 + 덮개율 + 폭) ≤ 1.5e-4 — 성분 «실행 간»
        (같은 모형·자료·코드 경로 — 재추첨 0) · 깨지면 전부 「관찰」 강등 · 배포 0.
  ㉠  C = |0.90−cov_전| − |0.90−cov_후| > max(J″_cov 0.0232, 2×SE_C)   [악화 = C 하락(−)]
  ㉡  판정 8 도메인 Δ_d(MdAPE 후−전) > max(J″_d, 2.6×SE_d) 인 곳 0     [악화 = 상승(+)]
  ㉢  Δ전체(MdAPE 후−전) ≤ +max(J″_전체 0.0055, 2×SE)                  [악화 = 상승(+)]
  ㉣  Δ폭(log · 후−전) ≤ 0.10 × W_전 (1001·1002 규격 승계 — §4 사유)      [악화 = 증가(+)]
조항 78 자료-항등 신고(㉮): ㉡8·㉢1 은 q50 무접촉이라 원리상 0 (그래도 잰다 — 회귀 감시) ·
㉣ 의 Δ폭 = 2δ 항등이라 δ 가 서는 순간 사실상 판정된다. 최상위 성공의 증거 하중은 ㉠ 이 진다.
🔴 v5.3-2 측정-«전» 합성 방향 탐침(t=1)이 시작 관문 — 첫 이행. 어긋나면 측정 없이 중단.
🔴 등록 시점 기대(정직 · estimate.json): δ_est = −0.0454 < 0 — 보정층은 val 덮개율을 «내리는»
   쪽으로 배웠다. 기대 판정어 = 「실패 — ㉠ 불통과 (배포 0)」. 반증가능한 몫은 val 쪽 실측:
   세계 명제(§0)는 C < −max(J″_cov, 2×SE) («유의하게 멀어짐»)를 요구한다 — C ≈ 0 이면 명제 기각.
🔴 순열 p 퇴화 신고: 가산 δ 는 개체 덮개율을 «한 방향으로만» 움직인다(δ≥0 이면 b_i ≥ a_i ·
   δ<0 이면 b_i ≤ a_i 항등) — p 는 구조상 극단(1/(B+1) 또는 ≈1). 증거 하중은 SE·문턱 몫.

🔴 CPU 전용 4스레드 · 유료 API 0 · MPS 0 · 학습 0 · 배포 파일 무변경(읽기만) ·
시작 전 load1 > 10 이면 60초 대기 반복. 씀: python3 runners/conformal1003.py
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.transition import load_ensemble  # noqa: E402

torch.set_num_threads(4)
STAT_SEED = 11003        # 🔴 신규 통계 스트림 — 11001·11002·9990/9991·998/999/1000·136/1136 회피
N_BOOT = N_PERM = 10000
ALPHA = 0.10             # 목표 덮개 0.90
CAL_FRAC = 0.20          # train 개체의 도메인 층화 20% 를 보정셋으로
TARGET = 0.90
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
SMALL = ("게임", "만화")  # n_val < 30 — ㉡ 판정 제외 (관찰)
MULT_OTHER = 2.6
# ㉣ 폭 지불 — 🔴 이론 지불 실측(보정셋 · estimate1003.py 가 같은 compute_calibration 을
# import · val 무접촉)이 «음수»다: 2δ_est = −0.0908 (train 한계-덮개 0.9671 — 과잉 덮개).
# 문언 그대로 한도로 쓰면 퇴화 문턱(v5.3-3 · thr ≤ 0 → 미판정)이라, 한도는 1001·1002 폭
# 규격(0.10 × W_전)을 승계하고 이론 지불 실측값은 «수로» 신고한다(사전등록 §4 사유).
THEORY_PAY_2DELTA = -0.0908
WIDTH_LIMIT_REL = 0.10

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "conformal1003")
OUT_JSON = os.path.join(REPO, "runners", "out1003_conformal.json")
LOAD_GATE = 10.0

# 조항 66 — 원천 sha 가 사전등록과 일치해야 잰다 (어긋나면 측정 없이 중단)
EXPECT_SHA = {
    os.path.join(TROUT, "ensemble_manifest.json"): "af7cebd02e77af9c",
    os.path.join(TROUT, "leaderboard.json"): "332bda6caf87cee1",   # 앵커(도메인·전체) 원천
    os.path.join(TROUT, "report.json"): "a8de5293852b5d9a",        # 앵커(덮개율·폭) 원천
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
    os.path.join(REPO, "runners/out1002_ensemble.json"): "bad5616b2561a21f",  # J″ 정본
    os.path.join(REPO, "data/lab/1002_판_후.json"): "3edf28e289312fff",       # 전판 (④ SE)
}
KEY_JPP = "J″_d (셋째 씨앗 5 |Δ리더보드| 최대 · 1001 J′ 와 같은 정의 — 다음 앵커 정본 신고 · ㉯)"


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


# ── 게이트 함수 (통과 = True) + 부호 서명 (v5.3-1) ────────────────────
GATES = {
    "㉠": {"pass_fn": lambda x, t: x > t, "worse_sign": -1.0,
          "악화 한 줄": "보정 뒤 val 덮개율이 목표 0.90 에서 «더 멀어지면»(과소·과잉 어느 쪽으로든 "
                    "목표 거리 |0.90−cov| 가 커지면 — C 가 음(−)이면) 구간이 더 크게 거짓말하는 것 — 악화"},
    "㉡": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "그 도메인의 누적 90일 중앙 예측 오차(MdAPE)가 «오르면»(+) 점 예측이 나빠진 것 — 악화"},
    "㉢": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "전체 MdAPE 가 «오르면»(+) 점 예측이 나빠진 것 — 악화"},
    "㉣": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "구간 평균 로그 폭이 한도 넘게 «넓어지면»(+) 덮개율을 정보 없는 구간 부풀리기로 "
                    "산 것 — 악화 (이번엔 넓힘이 목적의 일부라 «한도»가 게이트다)"},
}


def presynth_probe(t=1.0):
    """🔴 v5.3-2 측정-«전» 합성 방향 탐침 — 자료 없이 게이트 함수를 t>0 으로 검사.
    악화 쪽 극값(악화 방향×2t)에서 거짓 · 개선 쪽 극값에서 참. 어긋나면 측정 없이 중단."""
    res, ok = {}, True
    for g, spec in GATES.items():
        worse = bool(spec["pass_fn"](spec["worse_sign"] * 2.0 * t, t))
        better = bool(spec["pass_fn"](-spec["worse_sign"] * 2.0 * t, t))
        good = (not worse) and better
        ok = ok and good
        res[g] = {"악화 극값(×2t) 통과값": worse, "개선 극값 통과값": better,
                  "검사(악화 거짓 ∧ 개선 참)": good}
    return ok, {"t(합성 문턱)": t, "게이트": res,
                "조문": "v5.3-2 첫 이행 — 측정 «전» · 어긋나면 측정 없이 중단"}


def gate_probe(pass_fn, obs, thr, worse_sign):
    """조항 78 강화 탐침(측정 «후» · v5.3-3) — 자료 유래 격자 + 방향 검사 + ㉰㉱ 성분."""
    ext = 4.0 * max(abs(thr), abs(obs))
    grid = [("실측", obs), ("부호반전", -obs), ("0", 0.0),
            ("+2문턱", 2.0 * thr), ("-2문턱", -2.0 * thr),
            ("악화 극값", worse_sign * ext), ("개선 극값", -worse_sign * ext)]
    vals = {name: bool(pass_fn(x, thr)) for name, x in grid}
    return {"격자": {name: round(x, 6) for name, x in grid}, "통과값(참=통과)": vals,
            "참 나옴": any(vals.values()), "거짓 나옴": not all(vals.values()),
            "㉰ 악화 극값에서 참": bool(vals["악화 극값"]),
            "㉱ 개선 극값에서 거짓": bool(not vals["개선 극값"]),
            "퇴화 문턱(thr ≤ 0)": bool(thr <= 0),
            "방향 검사(악화 극값 거짓 ∧ 개선 극값 참)": bool((not vals["악화 극값"]) and vals["개선 극값"])}


# ── 자료 (999~1002 러너와 자구까지 같은 전처리) ───────────────────────
def load_data():
    z = np.load(os.path.join(TRI, "sao.npz"))
    domains = json.load(open(os.path.join(TRI, "domains.json"), encoding="utf-8"))
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
    C = np.concatenate([onehot, sin, cos, year, base, E], axis=1).astype(np.float32)
    meta = [json.loads(l) for l in open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")]
    return {"S": S, "base": base, "Sc": Sc, "R": R, "dom_id": dom_id, "split": split,
            "C": C, "domains": domains, "meta": meta,
            "tr": np.where(split == 0)[0], "va": np.where(split == 1)[0]}


def predict_rows(model, D, rows, chunk=2048):
    outs = []
    with torch.no_grad():
        for k in range(0, len(rows), chunk):
            ii = rows[k:k + chunk]
            x = torch.from_numpy(np.concatenate([D["Sc"][ii], D["C"][ii]], axis=1))
            outs.append(model(x).numpy())
    return np.concatenate(outs)              # (n,91,5) 잔차 눈금


def carve_calibration(D):
    """train «개체 이름» 단위 도메인 층화 20% — 뽑기 seed [11003,0] · val 무접촉.
    개체의 도메인 = 그 개체 첫 행의 도메인. 반환: (보정 행 인덱스, 요약 dict)."""
    ent_dom, ent_rows = {}, {}
    for i in D["tr"]:
        name = D["meta"][i]["개체"]
        ent_rows.setdefault(name, []).append(int(i))
        ent_dom.setdefault(name, D["domains"][D["dom_id"][i]])
    rng = np.random.default_rng([STAT_SEED, 0])
    picked = []
    by_dom = {}
    for name in sorted(ent_dom):
        by_dom.setdefault(ent_dom[name], []).append(name)
    for d in sorted(by_dom):
        names = sorted(by_dom[d])
        k = max(1, int(np.ceil(CAL_FRAC * len(names))))
        sel = rng.permutation(len(names))[:k]
        picked += [names[j] for j in sel]
    rows = np.asarray(sorted(i for n in picked for i in ent_rows[n]), dtype=np.int64)
    va_names = {D["meta"][i]["개체"] for i in D["va"]}
    overlap = sorted(set(picked) & va_names)
    return rows, {"train 개체(유일)": len(ent_dom), "뗀 개체 수": len(picked),
                  "보정 행 수": int(len(rows)),
                  "도메인별 뗀 개체": {d: sum(1 for n in picked if ent_dom[n] == d)
                                for d in sorted(by_dom)},
                  "val 개체 겹침(누수 검사 — 0 이어야)": overlap if overlap else 0,
                  "뽑기 seed": "[11003,0] · 도메인 층화 · 개체 이름 정렬 뒤 순열"}


def compute_calibration(model=None, D=None):
    """보정셋 CQR 점수 → 전역 δ (유한표본 보정 분위수 · method='higher' 보수).
    val 을 «읽지 않는다» — estimate1003.py 가 이 함수를 import 해 ㉣ 한도를 추정했다."""
    if model is None:
        model, _man, _ = load_ensemble()
    if D is None:
        D = load_data()
    rows, summary = carve_calibration(D)
    pred = predict_rows(model, D, rows)
    r = D["R"][rows].astype(np.float64)
    q05, q95 = pred[..., 0].astype(np.float64), pred[..., 4].astype(np.float64)
    scores = np.maximum(q05 - r, r - q95).ravel()          # CQR 적합도 점수 (행×91)
    n = scores.size
    q_level = min(1.0, (1.0 - ALPHA) * (1.0 + 1.0 / n))
    delta = float(np.quantile(scores, q_level, method="higher"))
    dom_rows = D["dom_id"][rows]
    delta_d = {}
    for di, d in enumerate(D["domains"]):
        m = dom_rows == di
        if not m.any():
            continue
        s_d = np.maximum(q05[m] - r[m], r[m] - q95[m]).ravel()
        ql = min(1.0, (1.0 - ALPHA) * (1.0 + 1.0 / s_d.size))
        delta_d[d] = round(float(np.quantile(s_d, ql, method="higher")), 4)
    summary.update({
        "score n(행×91)": int(n), "q_level(유한표본 보정)": round(q_level, 6),
        "δ(전역 · log)": delta,
        "보정셋 한계-덮개(전·개체일 한계)": round(float((scores <= 0).mean()), 4),
        "보정셋 한계-덮개(후·δ 적용)": round(float((scores <= delta).mean()), 4),
        "관찰 — 도메인별 δ_d(적용 안 함 · 참고)": delta_d})
    return delta, rows, summary, model, D


def eval_val(pred, D):
    """(n_va,91,5) → 개체별 (ape, cover_ent) + 집계 — 999~1002 평가식 (폭은 float64)."""
    va = D["va"]
    b = D["base"][va]
    R = D["R"][va]
    cum_true = np.expm1(R + b).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + b).sum(axis=1)
    ape = np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1.0)
    cover_ent = ((R >= pred[..., 0]) & (R <= pred[..., 4])).mean(axis=1)
    piw_ent = (pred[..., 4].astype(np.float64) - pred[..., 0].astype(np.float64)).mean(axis=1)
    dom_va = D["dom_id"][va]
    per_dom = {D["domains"][d]: float(np.median(ape[dom_va == d]))
               for d in range(len(D["domains"]))}
    return {"ape": ape, "cover_ent": cover_ent, "piw_ent": piw_ent, "per_dom": per_dom,
            "cover": float(cover_ent.mean()), "tot": float(np.median(ape)),
            "W": float(piw_ent.mean()), "dom_va": dom_va}


def dist(x):
    return abs(TARGET - x)


def main():
    t_all = time.time()
    시작 = time.strftime("%Y-%m-%dT%H:%M:%S")
    # ── 🔴 v5.3-2 시작 관문: 측정-«전» 합성 방향 탐침 (첫 이행) ─────────
    ok, pre_probe = presynth_probe(1.0)
    if not ok:
        out = {"판정어": "중단 — v5.3-2 합성 방향 탐침 어긋남 (등록 결함 · 측정 없이 중단)",
               "합성 방향 탐침(측정 전)": pre_probe, "시작 시각": 시작}
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    # ── 조항 66: 원천 sha 검증 ────────────────────────────────────────
    sha_verify = {}
    for p, want in EXPECT_SHA.items():
        got = sha16(p) if os.path.exists(p) else "없음"
        sha_verify[os.path.basename(p)] = {"기대": want, "실측": got, "일치": got == want}
    if not all(v["일치"] for v in sha_verify.values()):
        out = {"판정어": "중단 — 원천 sha 불일치 (조항 66 · 측정 없이 중단)",
               "sha 검증": sha_verify, "합성 방향 탐침(측정 전)": pre_probe, "시작 시각": 시작}
        with open(OUT_JSON, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    # load1 관문 (4B 임베딩 pid 8555 보호)
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60

    o1002 = json.load(open(os.path.join(REPO, "runners/out1002_ensemble.json"), encoding="utf-8"))
    JPP = o1002[KEY_JPP]
    J = {d: float(JPP[d]) for d in ROSTER}
    J_cov, J_tot = float(JPP["덮개율"]), float(JPP["전체"])
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    rep = json.load(open(os.path.join(TROUT, "report.json"), encoding="utf-8"))
    전판 = json.load(open(os.path.join(REPO, "data/lab/1002_판_후.json"), encoding="utf-8"))

    # ── 보정 계수 (val 무접촉 단계) ───────────────────────────────────
    delta, cal_rows, cal_sum, model, D = compute_calibration()
    prog({"δ": delta, "보정 행": cal_sum["보정 행 수"], "load대기초": waited})

    # ── val 측정: 전 → 앵커 → 후 ─────────────────────────────────────
    pred = predict_rows(model, D, D["va"])
    before = eval_val(pred, D)
    # 앵커: 배포 정본 재현 항등 13칸 (성분 «실행 간» · 허용 1.5e-4 = 게재 반올림 몫)
    anchor, aok = {}, []
    for d in ROSTER:
        dv = abs(before["per_dom"][d] - float(lb["도메인별"][d]["transition"]))
        anchor[d] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
        aok.append(dv <= 1.5e-4)
    for name, mine, ref in (("전체", before["tot"], float(lb["전체"]["transition"])),
                            ("덮개율", before["cover"], float(rep["평가"]["90% 구간 덮개율(목표 0.90)"])),
                            ("폭", before["W"], float(rep["평가"]["구간 평균 폭(log)"]))):
        dv = abs(mine - ref)
        anchor[name] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
        aok.append(dv <= 1.5e-4)
    anchor_ok = all(aok)

    pred_after = pred.copy()
    pred_after[..., 0] -= delta
    pred_after[..., 4] += delta
    after = eval_val(pred_after, D)

    # 관찰 — «일반화 갭» 정량 (val 쪽 필요 δ — 🔴 적용·배포 금지 · 다음 사이클 설계 입력)
    r_va = D["R"][D["va"]].astype(np.float64)
    s_va = np.maximum(pred[..., 0].astype(np.float64) - r_va,
                      r_va - pred[..., 4].astype(np.float64)).ravel()
    ql_va = min(1.0, (1.0 - ALPHA) * (1.0 + 1.0 / s_va.size))
    delta_val_req = float(np.quantile(s_va, ql_va, method="higher"))
    gap_obs = {"val 한계-덮개(개체일 · 전)": round(float((s_va <= 0).mean()), 4),
               "val 필요 δ(0.90 · 관찰 — 적용 금지)": round(delta_val_req, 4),
               "train 보정셋 δ": round(delta, 4),
               "갭 δ_val−δ_cal(log)": round(delta_val_req - delta, 4),
               "val 쪽 이론 지불 2δ_val(관찰)": round(2.0 * delta_val_req, 4),
               "비고": "보정셋(train 개체 — 학습에 쓰임)은 과잉 덮개 · val(새 개체)은 과소 덮개 — "
                     "이 갭이 «개체-밖 일반화 갭»의 구간 쪽 수치다"}

    # ── 항등 검사 (조항 78 ㉮ 신고 — «그래도 잰다») ───────────────────
    ape_diff = float(np.max(np.abs(after["ape"] - before["ape"])))
    width_iden = abs((after["W"] - before["W"]) - 2.0 * delta)
    identity = {"q50 무접촉 → 개체 APE 최대 차(0 이어야)": ape_diff,
                "Δ폭 − 2δ (항등 확인 · float64)": width_iden,
                "신고": "㉡8·㉢1 은 이 항등 위에서 원리상 못 떨어진다(조항 78 ㉮ = 9) — 회귀 감시로 잰다 · "
                      "㉣ 은 Δ폭=2δ 항등이라 등록 시점에 사실상 판정(㉮ 성격 · 한도가 게이트) · "
                      "최상위 성공의 증거 하중은 ㉠ 이 진다(조항 78-2)"}

    # ── 주대비 ㉠ 통계 (개체 1129 · B=10,000 · seed [11003,·]) ────────
    a_i = before["cover_ent"].astype(np.float64)          # 전
    b_i = after["cover_ent"].astype(np.float64)           # 후 (b_i ≥ a_i 항등)
    n_ent = len(a_i)
    C_obs = dist(a_i.mean()) - dist(b_i.mean())
    rngb = np.random.default_rng([STAT_SEED, 1])
    cs = np.empty(N_BOOT)
    done = 0
    while done < N_BOOT:
        m = min(2000, N_BOOT - done)
        idx = rngb.integers(0, n_ent, size=(m, n_ent))
        cs[done:done + m] = (np.abs(TARGET - a_i[idx].mean(axis=1))
                             - np.abs(TARGET - b_i[idx].mean(axis=1)))
        done += m
    se_C = float(cs.std(ddof=1))
    rngp = np.random.default_rng([STAT_SEED, 2])
    flips = rngp.random((N_PERM, n_ent)) < 0.5
    ap = np.where(flips, b_i[None, :], a_i[None, :])
    bp = np.where(flips, a_i[None, :], b_i[None, :])
    stat = np.abs(TARGET - ap.mean(axis=1)) - np.abs(TARGET - bp.mean(axis=1))
    p_one = float((1 + (stat >= C_obs).sum()) / (1 + N_PERM))
    # Δ폭 SE (짝지은 개체 붓스트랩 — 관찰 · ㉣ 판정은 CAP «수» 대비)
    w_a = before["piw_ent"].astype(np.float64)
    w_b = after["piw_ent"].astype(np.float64)
    rngw = np.random.default_rng([STAT_SEED, 3])
    idx = rngw.integers(0, n_ent, size=(N_BOOT, n_ent))
    se_W = float((w_b[idx].mean(axis=1) - w_a[idx].mean(axis=1)).std(ddof=1))

    # ── 판정 (비반올림 집행 · 여유 = Δ − 문턱 비반올림) ───────────────
    thr_t = max(J_cov, 2.0 * se_C)
    g1 = bool(C_obs > thr_t)
    delta_d_val = {d: after["per_dom"][d] - before["per_dom"][d] for d in ROSTER}
    judge = [d for d in ROSTER if d not in SMALL]
    bad = {}
    thr_d = {}
    for d in judge:
        thr_d[d] = max(J[d], MULT_OTHER * 0.0)            # SE_d = 0 (항등 — 신고 위)
        if delta_d_val[d] > thr_d[d]:
            bad[d] = {"Δ": delta_d_val[d], "문턱": thr_d[d]}
    g2 = bool(not bad)
    d_tot = after["tot"] - before["tot"]
    thr_tot = max(J_tot, 2.0 * 0.0)                       # SE_전체 = 0 (항등)
    g3 = bool(d_tot <= thr_tot)
    d_W = after["W"] - before["W"]
    thr_w = WIDTH_LIMIT_REL * before["W"]                 # 1001·1002 규격 승계 (§4 사유)
    g4 = bool(d_W <= thr_w)

    probes = {"㉠": gate_probe(GATES["㉠"]["pass_fn"], C_obs, thr_t, -1.0),
              "㉢": gate_probe(GATES["㉢"]["pass_fn"], d_tot, thr_tot, +1.0),
              "㉣": gate_probe(GATES["㉣"]["pass_fn"], d_W, thr_w, +1.0)}
    for d in judge:
        probes["㉡ " + d] = gate_probe(GATES["㉡"]["pass_fn"], delta_d_val[d], thr_d[d], +1.0)
    n_m = sum(1 for p in probes.values() if not p["거짓 나옴"])
    n_n = sum(1 for p in probes.values() if not p["참 나옴"])
    n_worse_true = sum(1 for p in probes.values() if p["㉰ 악화 극값에서 참"])
    n_better_false = sum(1 for p in probes.values() if p["㉱ 개선 극값에서 거짓"])
    n_degen = sum(1 for p in probes.values() if p["퇴화 문턱(thr ≤ 0)"])
    n_dir = sum(1 for p in probes.values()
                if not p["방향 검사(악화 극값 거짓 ∧ 개선 극값 참)"])

    if ape_diff != 0.0:
        verdict = ("장치 결함 — q50 항등 깨짐(개체 APE 최대 차 %g ≠ 0) — ㉡㉢ 의 SE=0 전제 붕괴 "
                   "(관찰 강등 · 배포 0)" % ape_diff)
    elif n_worse_true or n_better_false or n_dir:
        verdict = ("등록 결함 — 자료 탐침 ㉰ %d · ㉱ %d · 방향 위반 %d (관찰 강등 · 배포 0)"
                   % (n_worse_true, n_better_false, n_dir))
    elif n_degen:
        verdict = "미판정(퇴화 문턱) %d — 관찰 강등 · 배포 0" % n_degen
    elif not anchor_ok:
        verdict = "관찰 강등 — 앵커(배포 정본 재현 항등) 불통과 (배포 0)"
    elif g1 and g2 and g3 and g4:
        verdict = "성공 — 배포 진행 (사전등록 §6 절차 그대로)"
    elif g1:
        verdict = "부분 — ㉠ 통과나 ㉡/㉢/㉣ 불통과 (배포 0)"
    else:
        verdict = "실패 — ㉠ 불통과 (배포 0)"

    # ── 산출물 ────────────────────────────────────────────────────────
    man_sha = sha16(os.path.join(TROUT, "ensemble_manifest.json"))
    cand = {"형식": "등각 보정 v1 (사이클 1003 · split-conformal CQR 가산 · 전역)",
            "α": ALPHA, "δ(log)": delta,
            "적용": "q05 − δ · q95 + δ (q25/q50/q75 무접촉 · 잔차 log 눈금)",
            "보정셋": {k: v for k, v in cal_sum.items() if k != "관찰 — 도메인별 δ_d(적용 안 함 · 참고)"},
            "잰 소스 (조항 66)": {"ensemble_manifest.json": man_sha,
                             "sao.npz": sha16(os.path.join(TRI, "sao.npz")),
                             "text_emb_qwen05b.npz": sha16(os.path.join(TRI, "text_emb_qwen05b.npz")),
                             "러너": sha16(os.path.abspath(__file__))},
            "사전등록": {"문서": "docs/탐색/1003.md"},
            "생성 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    os.makedirs(EXP, exist_ok=True)
    with open(os.path.join(EXP, "conformal_candidate.json"), "w", encoding="utf-8") as f:
        json.dump(cand, f, ensure_ascii=False, indent=1)

    out = {"러너": "runners/conformal1003.py",
           "표적": "④ 90% 덮개율(전역) — 등각 보정층 · 재학습 없음",
           "시작 시각": 시작,
           "합성 방향 탐침(측정 전 · v5.3-2 첫 이행)": pre_probe,
           "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
           "sha 검증(사전등록 대조)": sha_verify,
           "러너 자신": sha16(os.path.abspath(__file__)),
           "설정": {"α": ALPHA, "보정셋 비율(개체)": CAL_FRAC, "통계 씨앗": STAT_SEED,
                  "threads": torch.get_num_threads(), "device": "cpu", "학습": 0,
                  "B": {"붓스트랩": N_BOOT, "순열": N_PERM},
                  "㉣ 한도(0.10×W_전 승계 · §4)": WIDTH_LIMIT_REL,
                  "㉣ 이론 지불 실측(음수 — §4 신고)": THEORY_PAY_2DELTA, "load대기초": waited},
           "보정셋·δ": cal_sum,
           "관찰 — 일반화 갭(val 쪽 필요 δ · 적용 금지)": gap_obs,
           "앵커(배포 정본 재현 항등 13칸 · 성분 «실행 간» · 허용 1.5e-4)": dict(
               anchor, 통과=bool(anchor_ok),
               성분="같은 모형·자료·코드 경로 재실행 — 재추첨 0 · 문턱은 게재 반올림 몫만"),
           "항등 검사(조항 78 ㉮ 신고)": identity,
           "val 전/후 (관찰 26칸)": {
               "전": {"도메인별 MdAPE": {d: round(before["per_dom"][d], 4) for d in ROSTER},
                     "전체 MdAPE": round(before["tot"], 4),
                     "90% 덮개율": round(before["cover"], 4),
                     "구간 평균 폭(log)": round(before["W"], 4)},
               "후": {"도메인별 MdAPE": {d: round(after["per_dom"][d], 4) for d in ROSTER},
                     "전체 MdAPE": round(after["tot"], 4),
                     "90% 덮개율": round(after["cover"], 4),
                     "구간 평균 폭(log)": round(after["W"], 4)}},
           "도메인별 덮개율 전/후 (관찰 20칸)": {
               d: {"전": round(float(a_i[before["dom_va"] == D["domains"].index(d)].mean()), 4),
                   "후": round(float(b_i[before["dom_va"] == D["domains"].index(d)].mean()), 4)}
               for d in ROSTER},
           "헤드라인(㉠ 주대비 · 조항 79)": {
               "n(개체)": n_ent,
               "|0.90−cov| 전": round(dist(a_i.mean()), 6),
               "|0.90−cov| 후": round(dist(b_i.mean()), 6),
               "C(거리 감소 · 원값)": C_obs,
               "붓스트랩 SE": round(se_C, 5),
               "t": round(C_obs / se_C, 2) if se_C > 0 else None,
               "동부호(덮개율 오른/내린/그대로 개체)": "%d/%d/%d (n %d)" % (
                   int((b_i > a_i).sum()), int((b_i < a_i).sum()),
                   int((b_i == a_i).sum()), n_ent),
               "부호뒤집기 순열 p(한쪽꼬리·개선=C 상승)": round(p_one, 5),
               "🔴 순열 p 퇴화 신고": "가산 δ 는 개체 덮개율을 한 방향으로만 움직인다(δ<0 이면 "
                                "b_i ≤ a_i 항등) — p 는 구조상 극단. 증거 하중은 SE·문턱 몫",
               "B": {"붓스트랩": N_BOOT, "순열": N_PERM,
                     "seed 스트림": "[11003,0 보정셋]·[11003,1 SE]·[11003,2 순열]·[11003,3 폭SE]"}},
           "판정 (사전등록 §4 · 판정 11칸 · 비반올림 집행 · 여유 = Δ − 문턱)": {
               "앵커": bool(anchor_ok),
               "㉠ 목표 거리 감소(악화=C 하락)": {
                   "통과": g1, "C": C_obs, "문턱 max(J″_cov 0.0232, 2×SE)": thr_t,
                   "여유(원값)": C_obs - thr_t},
               "㉡ 도메인 MdAPE 유의 악화(판정 8 · 악화=상승 · 항등 신고 위)": {
                   "통과": g2, "걸린 도메인": bad if bad else "없음(0/8)",
                   "여유(원값 · Δ_d − 문턱)": {d: delta_d_val[d] - thr_d[d] for d in judge}},
               "㉢ 전체 MdAPE 비악화(악화=상승 · 항등 신고 위)": {
                   "통과": g3, "Δ전체(원값)": d_tot, "문턱": thr_tot, "여유(원값)": d_tot - thr_tot},
               "㉣ 폭 지불 한도(악화=증가 · 0.10×W_전 승계)": {
                   "통과": g4, "Δ폭(원값)": d_W, "한도(0.10×W_전 · 원값)": thr_w,
                   "여유(원값)": d_W - thr_w, "Δ폭 SE(관찰)": round(se_W, 6),
                   "🔴 이론 지불 실측(보정셋 2δ_est — §4 신고)": THEORY_PAY_2DELTA},
               "게임·만화(관찰 — n_val<30)": {d: {"Δ": delta_d_val[d]} for d in SMALL}},
           "조항 78 탐침 (측정 후 · v5.3-3 격자 + ㉰㉱ 계수)": dict(
               probes, 계수={"㉮ 원리상 못 떨어짐(격자)": n_m, "㉯ 원리상 못 통과(격자)": n_n,
                           "㉰ 악화 극값에서 참": n_worse_true,
                           "㉱ 개선 극값에서 거짓": n_better_false,
                           "퇴화 문턱": n_degen, "방향 검사 위반": n_dir}),
           "판정어": verdict,
           "배포 후보(성공 시 §6 그대로)": {
               "conformal_candidate.json": {"경로": os.path.join(EXP, "conformal_candidate.json"),
                                        "sha": sha16(os.path.join(EXP, "conformal_candidate.json"))},
               "δ": delta},
           "관찰 분모 신고(조항 79)": ("대비 주장 1(㉠ 목표 거리·전역) · 관찰: 앵커 13 + 보정셋 요약 7 + "
                                  "도메인 δ_d 10 + 일반화 갭 6 + val 전/후 26 + 도메인 덮개율 20 + "
                                  "헤드라인 8 + 항등 2 + Δ폭 SE 1 = 93 · 판정 11(㉠1 ㉡8 ㉢1 ㉣1)"),
           "총소요초": round(time.time() - t_all, 1),
           "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "δ": round(delta, 4),
                      "덮개율": "%.4f → %.4f" % (before["cover"], after["cover"]),
                      "C": round(C_obs, 4), "Δ폭": round(d_W, 4), "p": p_one,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
