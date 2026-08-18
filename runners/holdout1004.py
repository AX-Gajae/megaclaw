# -*- coding: utf-8 -*-
"""확증 1004 러너 — 보정 전용 개체 «홀드아웃 재학습» 앙상블 + 무누수 등각 보정
(사전등록 docs/탐색/1004.md 에서 언 코드 · 루프 v5.3 동결 · 티처 #140 ④-1~4·⑦-1~9 반영).

주대비 «하나»(조항 79): C = |0.90−cov_전| − |0.90−cov_후| — cov_전 = 현 배포 앙상블
(1201~1205 · manifest af7cebd02e77af9c) val 덮개율 · cov_후 = 신 앙상블(1301~1305 ·
홀드아웃 98 개체 제외 재학습 · 분위수 평균) + 전역 등각 보정(q05−δ · q95+δ)의 val 덮개율.
val = 1,129 행(개체창) · 유일 개체 70 (🔴 「1,129 개체」 문언 금지 — #140 ⑦-2).

판정(사전등록 §3~§4 · 비반올림 집행 · 판정 눈금 = 개체 이름 클러스터 SE(㉠㉢㉤㉥) ·
㉡ 은 행 SE(도메인 안 클러스터 3~16 퇴화 사유)):
  앵커A  배포 정본 재현 항등 13칸 ≤ 1.5e-4 («실행 간» · 재추첨 0)
  앵커B  사전 실측 재현 3칸 (홀드아웃 98 개체 · 1,752 행 · in-sample 덮개 0.9628)
  ㉤  |cov_신(홀드아웃) − cov_신(val)| ≤ max(J″_cov 0.0232, 2×SE_diff^cl)   [양쪽형 · 전제]
  ㉥  A/B 내부 정합: cov_B(δ̂_A) ∈ 0.90 ± max(J″_cov, 2×SE_B^cl)            [양쪽형 · 전제]
  ㉠  C > max(J″_cov 0.0232, 2×SE_C^cl)                     [악화 = C 하락(−) · 과잉 덮개 포함]
  ㉡  판정 8 도메인 Δ_d(신−배포 MdAPE) > max(J″_d, 2.6×SE_d^행) 인 곳 0     [악화 = 상승(+)]
  ㉢  Δ전체 ≤ +max(J″_전체 0.0055, 2×SE^cl)  — train 축소 비용이 잡히는 자리 [악화 = 상승(+)]
  ㉣  Δ폭 ≤ 2δ_holdout + max(J″_폭 0.0346, 2×SE_폭^cl) · 2δ≤0 이면 「미판정(퇴화)」 사전 규칙
     (#140 ⑦-5)                                                            [악화 = 초과(+)]
🔴 #140 ⑦-6: 「자료-조건부 연역」 계수 — 판정 칸별 연역 가능성(관측 SE=0 이고 문턱이 등록
   상수뿐인가)을 기계로 세고 «판정어 층의 연역 불가능 칸 수»를 헤드라인에 게재. 0 이면
   등록어 = 「측정 사이클」.
🔴 v5.3-2 측정-«전» 합성 방향 탐침(t=1 · 양쪽형 포함) 시작 관문 — 어긋나면 측정 없이 중단.
🔴 #140 ⑦-7: 이번 설계는 두 모형 비교라 순열 p 비퇴화 기대 — 구조 퇴화로 판명되면
   「항등(정보 0)」 게재.

🔴 CPU 전용 4스레드 · 유료 API 0 · MPS 0 · 학습 5(순차 · 각 학습 전 load1 > 10 이면 60초
대기 반복) · 배포 파일 무변경(읽기만) · 씀: python3 runners/holdout1004.py
"""
import hashlib
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.transition import Transition, pinball, load_ensemble  # noqa: E402

torch.set_num_threads(4)
SEEDS = (1301, 1302, 1303, 1304, 1305)   # 🔴 넷째 집합 — 997·1001~1005·1101~1105·1201~1205 금지
STAT_SEED = 11004                        # 🔴 신규 통계 스트림 — 11003 재사용 금지(#140 ⑦-3)
N_BOOT = N_PERM = 10000
ALPHA = 0.10
TARGET = 0.90
HOLD_FRAC = 0.15
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
SMALL = ("게임", "만화")                  # n_val 5·6 행 — ㉡ 판정 제외 (관찰)
MULT_OTHER = 2.6
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

# 사전등록 §0 실측 상수 (앵커 B — 러너가 재현해야 함)
REG_HOLD_ENT = 98
REG_HOLD_ROWS = 1752
REG_INSAMPLE_COV = 0.9628
# #140 ④-1 — 홀드아웃 «비보정» 덮개 예측 구간 (등록 §6)
BAND_41 = (0.7108, 0.8284)
# 1003 관찰 인용 (참고 눈금 · out1003 §7)
REF_2DELTA_VAL_1003 = 0.3281

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "holdout1004")
OUT_JSON = os.path.join(REPO, "runners", "out1004_holdout.json")

EXPECT_SHA = {
    os.path.join(TROUT, "ensemble_manifest.json"): "af7cebd02e77af9c",
    os.path.join(TROUT, "leaderboard.json"): "332bda6caf87cee1",
    os.path.join(TROUT, "report.json"): "a8de5293852b5d9a",
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
    os.path.join(REPO, "runners/out1002_ensemble.json"): "bad5616b2561a21f",   # J″ 정본
    os.path.join(REPO, "runners/out1003_conformal.json"): "7a29fd4aa3abfb32",  # 1003 관찰 인용
    os.path.join(REPO, "data/lab/1003_판_후.json"): "24ea1e366ba6777c",        # 전판
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


def load_gate_wait():
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60
    return waited


# ── 게이트 함수 + 부호 서명 (v5.3-1 · 양쪽형 포함) ────────────────────
GATES = {
    "㉠": {"pass_fn": lambda x, t: x > t, "worse_sign": -1.0, "two": False,
          "악화 한 줄": "보정 뒤 val 덮개율이 목표 0.90 에서 «더 멀어지면»(과소·과잉 어느 쪽으로든 "
                    "|0.90−cov| 가 커지면 — C 가 음(−)이면) 구간이 더 크게 거짓말하는 것 — 악화"},
    "㉡": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0, "two": False,
          "악화 한 줄": "그 도메인의 누적 90일 중앙 예측 오차가 «오르면»(+) 점 예측이 나빠진 것 — 악화 "
                    "(이번엔 재학습이라 실측정 게이트 — 1003 형 항등 아님)"},
    "㉢": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0, "two": False,
          "악화 한 줄": "전체 MdAPE 가 «오르면»(+) 악화 — train 축소(−98 개체)의 지불이 잡히는 자리 · "
                    "오르면 그것이 ④ 개선을 사는 값(한도는 이 문턱)"},
    "㉣": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0, "two": False,
          "악화 한 줄": "구간 평균 로그 폭이 «홀드아웃이 가르친 이론 지불(2δ) + 지터 여유»를 넘게 "
                    "넓어지면(+) 정보 없는 부풀리기로 덮개를 산 것 — 악화 (0.90 엔 폭 지불이 필연 — "
                    "한도는 «초과 지불» 금지다)"},
    "㉤": {"pass_fn": lambda x, t: abs(x) <= t, "worse_sign": +1.0, "two": True,
          "악화 한 줄": "신 앙상블 눈에 «안 본 개체»인 홀드아웃과 val 의 덮개가 어느 쪽으로든 유의하게 "
                    "다르면 교환가능성 붕괴 — δ 가 val 로 이전 안 된다 — 악화 (양쪽형)"},
    "㉥": {"pass_fn": lambda x, t: abs(x) <= t, "worse_sign": +1.0, "two": True,
          "악화 한 줄": "홀드아웃 «안»에서 반쪽 δ̂_A 가 다른 반쪽 B 를 0.90 에 못 앉히면(과소·과잉 "
                    "어느 쪽이든) split-conformal 전제가 자료 안에서 안 서는 것 — 악화 (양쪽형)"},
}


def presynth_probe(t=1.0):
    """v5.3-2 측정-«전» 합성 방향 탐침 — 한쪽형: 악화 극값(×2t) 거짓 ∧ 개선 극값 참 ·
    양쪽형: ±2t 둘 다 거짓 ∧ 0 참. 어긋나면 측정 없이 중단."""
    res, ok = {}, True
    for g, spec in GATES.items():
        if spec["two"]:
            w1 = bool(spec["pass_fn"](+2.0 * t, t))
            w2 = bool(spec["pass_fn"](-2.0 * t, t))
            better = bool(spec["pass_fn"](0.0, t))
            good = (not w1) and (not w2) and better
            res[g] = {"+2t 통과값": w1, "-2t 통과값": w2, "0 통과값": better,
                      "검사(±2t 거짓 ∧ 0 참)": good, "형": "양쪽"}
        else:
            worse = bool(spec["pass_fn"](spec["worse_sign"] * 2.0 * t, t))
            better = bool(spec["pass_fn"](-spec["worse_sign"] * 2.0 * t, t))
            good = (not worse) and better
            res[g] = {"악화 극값(×2t) 통과값": worse, "개선 극값 통과값": better,
                      "검사(악화 거짓 ∧ 개선 참)": good, "형": "한쪽"}
        ok = ok and good
    return ok, {"t(합성 문턱)": t, "게이트": res,
                "조문": "v5.3-2 — 측정 «전» · 어긋나면 측정 없이 중단"}


def gate_probe(pass_fn, obs, thr, worse_sign, two=False):
    """v5.3-3 자료 탐침 — 격자 + ㉰㉱ + 퇴화. 양쪽형: 악화 극값 = ±ext 둘 다 · 개선 극값 = 0."""
    ext = 4.0 * max(abs(thr), abs(obs))
    if two:
        grid = [("실측", obs), ("부호반전", -obs), ("0", 0.0),
                ("+2문턱", 2.0 * thr), ("-2문턱", -2.0 * thr),
                ("악화 극값(+)", +ext), ("악화 극값(-)", -ext), ("개선 극값(0)", 0.0)]
        vals = {name: bool(pass_fn(x, thr)) for name, x in grid}
        worse_true = bool(vals["악화 극값(+)"] or vals["악화 극값(-)"])
        better_false = bool(not vals["개선 극값(0)"])
        direction = (not vals["악화 극값(+)"]) and (not vals["악화 극값(-)"]) and vals["개선 극값(0)"]
    else:
        grid = [("실측", obs), ("부호반전", -obs), ("0", 0.0),
                ("+2문턱", 2.0 * thr), ("-2문턱", -2.0 * thr),
                ("악화 극값", worse_sign * ext), ("개선 극값", -worse_sign * ext)]
        vals = {name: bool(pass_fn(x, thr)) for name, x in grid}
        worse_true = bool(vals["악화 극값"])
        better_false = bool(not vals["개선 극값"])
        direction = (not vals["악화 극값"]) and vals["개선 극값"]
    return {"격자": {name: round(x, 6) for name, x in grid}, "통과값(참=통과)": vals,
            "참 나옴": any(vals.values()), "거짓 나옴": not all(vals.values()),
            "㉰ 악화 극값에서 참": worse_true, "㉱ 개선 극값에서 거짓": better_false,
            "퇴화 문턱(thr ≤ 0)": bool(thr <= 0), "방향 검사": bool(direction)}


# ── 자료 (999~1003 러너와 자구까지 같은 전처리) ───────────────────────
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


def carve_holdout(D):
    """사전 실측기 pre1004.py 와 같은 층화(1003 방식) — seed [11004,0] · 15%."""
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
        k = max(1, int(np.ceil(HOLD_FRAC * len(names))))
        sel = rng.permutation(len(names))[:k]
        picked += [names[j] for j in sel]
    rows = np.asarray(sorted(i for n in picked for i in ent_rows[n]), dtype=np.int64)
    va_names = {D["meta"][i]["개체"] for i in D["va"]}
    overlap = sorted(set(picked) & va_names)
    # 1003 보정셋(20% · [11003,0]) 겹침 — 관찰
    rng3 = np.random.default_rng([11003, 0])
    p03 = []
    for d in sorted(by_dom):
        names = sorted(by_dom[d])
        k = max(1, int(np.ceil(0.20 * len(names))))
        sel = rng3.permutation(len(names))[:k]
        p03 += [names[j] for j in sel]
    summary = {"train 개체(유일)": len(ent_dom), "홀드아웃 개체 수": len(picked),
               "홀드아웃 행 수": int(len(rows)),
               "남는 train 행 수": int(len(D["tr"]) - len(rows)),
               "도메인별 홀드아웃 개체": {d: sum(1 for n in picked if ent_dom[n] == d)
                                for d in sorted(by_dom)},
               "val 개체 겹침(누수 검사 — 0 이어야)": overlap if overlap else 0,
               "1003 보정셋과 개체 겹침(관찰)": len(set(picked) & set(p03)),
               "뽑기 seed": "[11004,0] · 도메인 층화 15% · 개체 이름 정렬 뒤 순열"}
    return set(picked), rows, summary, ent_dom, ent_rows


def predict_rows(model, D, rows, chunk=2048):
    outs = []
    with torch.no_grad():
        for k in range(0, len(rows), chunk):
            ii = rows[k:k + chunk]
            x = torch.from_numpy(np.concatenate([D["Sc"][ii], D["C"][ii]], axis=1))
            outs.append(model(x).numpy())
    return np.concatenate(outs)


def train_cur(seed, tr_pool, D):
    """현행 레시피 — ensemble1002.train_cur 와 같은 연산 순서 · 표본 풀만 축소 train."""
    d_in = D["Sc"].shape[1] + D["C"].shape[1]
    torch.manual_seed(seed)
    model = Transition(d_in, hidden=HIDDEN)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    t0 = time.time()
    loss = None
    for step in range(STEPS):
        rng = np.random.default_rng([seed, step])
        ii = tr_pool[rng.integers(0, len(tr_pool), size=BATCH)]
        x = torch.from_numpy(np.concatenate([D["Sc"][ii], D["C"][ii]], axis=1))
        r = torch.from_numpy(D["R"][ii])
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
    model.eval()
    return model, round(float(loss.item()), 5), round(time.time() - t0, 1)


def eval_val(pred, D):
    """(n_va,91,5) → 행별 (ape, cover_ent, piw_ent) + 집계 — 999~1003 평가식."""
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


def cluster_groups(names):
    uniq = sorted(set(names))
    lut = {n: i for i, n in enumerate(uniq)}
    ids = np.asarray([lut[n] for n in names], dtype=np.int64)
    groups = [np.where(ids == i)[0] for i in range(len(uniq))]
    return uniq, ids, groups


def cboot(groups, rng, stat, B=N_BOOT):
    """개체 이름 클러스터 붓스트랩 — 클러스터 복원 추출 · 그 행 전부 · 통계 전체 재계산."""
    n = len(groups)
    out = np.empty(B)
    for b in range(B):
        gs = rng.integers(0, n, size=n)
        pos = np.concatenate([groups[g] for g in gs])
        out[b] = stat(pos)
    return out


def dist(x):
    return abs(TARGET - x)


def q_conf(scores, alpha=ALPHA):
    n = scores.size
    ql = min(1.0, (1.0 - alpha) * (1.0 + 1.0 / n))
    return float(np.quantile(scores, ql, method="higher")), ql


def main():
    t_all = time.time()
    시작 = time.strftime("%Y-%m-%dT%H:%M:%S")
    ok, pre_probe = presynth_probe(1.0)
    if not ok:
        out = {"판정어": "중단 — v5.3-2 합성 방향 탐침 어긋남 (등록 결함 · 측정 없이 중단)",
               "합성 방향 탐침(측정 전)": pre_probe, "시작 시각": 시작}
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    sha_verify = {}
    for p, want in EXPECT_SHA.items():
        got = sha16(p) if os.path.exists(p) else "없음"
        sha_verify[os.path.basename(p)] = {"기대": want, "실측": got, "일치": got == want}
    if not all(v["일치"] for v in sha_verify.values()):
        out = {"판정어": "중단 — 원천 sha 불일치 (조항 66 · 측정 없이 중단)",
               "sha 검증": sha_verify, "시작 시각": 시작}
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    waited0 = load_gate_wait()
    o1002 = json.load(open(os.path.join(REPO, "runners/out1002_ensemble.json"), encoding="utf-8"))
    JPP = o1002[KEY_JPP]
    J = {d: float(JPP[d]) for d in ROSTER}
    J_cov, J_tot, J_W = float(JPP["덮개율"]), float(JPP["전체"]), float(JPP["폭"])
    o1003 = json.load(open(os.path.join(REPO, "runners/out1003_conformal.json"), encoding="utf-8"))
    ref_2dv = float(o1003["관찰 — 일반화 갭(val 쪽 필요 δ · 적용 금지)"]["val 쪽 이론 지불 2δ_val(관찰)"])
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    rep = json.load(open(os.path.join(TROUT, "report.json"), encoding="utf-8"))
    pre_dom = {d: float(lb["도메인별"][d]["transition"]) for d in ROSTER}
    pre_tot = float(lb["전체"]["transition"])
    pre_cover = float(rep["평가"]["90% 구간 덮개율(목표 0.90)"])
    pre_piw = float(rep["평가"]["구간 평균 폭(log)"])

    D = load_data()
    dep_model, _man, dep_shas = load_ensemble()
    pred_dep = predict_rows(dep_model, D, D["va"])
    before = eval_val(pred_dep, D)

    # ── 앵커 A: 배포 정본 재현 항등 13칸 («실행 간» · ≤1.5e-4) ─────────
    anchorA, aok = {}, []
    for d in ROSTER:
        dv = abs(before["per_dom"][d] - pre_dom[d])
        anchorA[d] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
        aok.append(dv <= 1.5e-4)
    for name, mine, ref in (("전체", before["tot"], pre_tot),
                            ("덮개율", before["cover"], pre_cover),
                            ("폭", before["W"], pre_piw)):
        dv = abs(mine - ref)
        anchorA[name] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
        aok.append(dv <= 1.5e-4)
    anchorA_ok = all(aok)

    # ── 홀드아웃 재현 + 앵커 B (사전 실측 재현 3칸) ───────────────────
    picked, hold_rows, hold_sum, ent_dom, _er = carve_holdout(D)
    pred_dep_hold = predict_rows(dep_model, D, hold_rows)
    r_h = D["R"][hold_rows].astype(np.float64)
    inb_dep = (r_h >= pred_dep_hold[..., 0]) & (r_h <= pred_dep_hold[..., 4])
    insample_cov = float(inb_dep.mean(axis=1).mean())
    anchorB = {"홀드아웃 개체 수(=98)": {"실측": hold_sum["홀드아웃 개체 수"],
                                 "통과": hold_sum["홀드아웃 개체 수"] == REG_HOLD_ENT},
               "홀드아웃 행 수(=1752)": {"실측": hold_sum["홀드아웃 행 수"],
                                  "통과": hold_sum["홀드아웃 행 수"] == REG_HOLD_ROWS},
               "in-sample 덮개(=0.9628 ± 1.5e-4)": {"실측": round(insample_cov, 6),
                                              "통과": bool(abs(insample_cov - REG_INSAMPLE_COV) <= 1.5e-4)}}
    anchorB_ok = all(v["통과"] for v in anchorB.values())
    leak_ok = hold_sum["val 개체 겹침(누수 검사 — 0 이어야)"] == 0
    prog({"앵커A": anchorA_ok, "앵커B": anchorB_ok, "누수0": leak_ok, "load대기초": waited0})

    # ── 재학습 5 (홀드아웃 제외 · 순차 · load 관문) ───────────────────
    hold_set = set(hold_rows.tolist())
    tr_pool = np.asarray([i for i in D["tr"] if int(i) not in hold_set], dtype=np.int64)
    seed_cells, preds_val, preds_hold, ckpts = {}, {}, {}, {}
    os.makedirs(EXP, exist_ok=True)
    for sd in SEEDS:
        waited = load_gate_wait()
        model, pin, sec = train_cur(sd, tr_pool, D)
        pv = predict_rows(model, D, D["va"])
        ph = predict_rows(model, D, hold_rows)
        ev = eval_val(pv, D)
        preds_val[sd], preds_hold[sd] = pv, ph
        seed_cells[sd] = {"도메인별 MdAPE": {d: round(ev["per_dom"][d], 4) for d in ROSTER},
                          "전체 MdAPE": round(ev["tot"], 4),
                          "90% 덮개율": round(ev["cover"], 4),
                          "구간 평균 폭(log)": round(ev["W"], 4),
                          "pinball(train)": pin, "sec": sec, "load대기초": waited}
        ckp = os.path.join(EXP, "cur_seed%d.pt" % sd)
        torch.save({"model": model.state_dict(), "d_in": D["Sc"].shape[1] + D["C"].shape[1],
                    "hidden": HIDDEN, "text_emb": os.path.join(TRI, "text_emb_qwen05b.npz"),
                    "레시피": "현행 레시피 · seed %d · steps 3000 · 홀드아웃 98 개체 제외 train "
                           "(사이클 1004)" % sd}, ckp)
        ckpts[sd] = {"경로": ckp, "sha": sha16(ckp)}
        prog({"seed": sd, "덮개율": seed_cells[sd]["90% 덮개율"],
              "전체": seed_cells[sd]["전체 MdAPE"], "sec": sec})

    # ── 신 앙상블 (분위수 평균) — val 미보정 · 홀드아웃 미보정 ─────────
    ens_val = np.mean(np.stack([preds_val[sd] for sd in SEEDS]), axis=0)
    ens_hold = np.mean(np.stack([preds_hold[sd] for sd in SEEDS]), axis=0)
    uncal = eval_val(ens_val, D)

    # J‴ 신고 (씨앗 간 + train 축소 · 대 배포 리더보드/report — 다음 앵커 정본)
    Jppp = {d: round(max(abs(seed_cells[sd]["도메인별 MdAPE"][d] - pre_dom[d]) for sd in SEEDS), 4)
            for d in ROSTER}
    Jppp["덮개율"] = round(max(abs(seed_cells[sd]["90% 덮개율"] - pre_cover) for sd in SEEDS), 4)
    Jppp["전체"] = round(max(abs(seed_cells[sd]["전체 MdAPE"] - pre_tot) for sd in SEEDS), 4)
    Jppp["폭"] = round(max(abs(seed_cells[sd]["구간 평균 폭(log)"] - pre_piw) for sd in SEEDS), 4)

    # ── 홀드아웃 비보정 덮개 (④-1) + 클러스터 SE ─────────────────────
    inb_h = (r_h >= ens_hold[..., 0].astype(np.float64)) & (r_h <= ens_hold[..., 4].astype(np.float64))
    cov_h_rows = inb_h.mean(axis=1)                      # (1752,)
    cov_hold_uncal = float(cov_h_rows.mean())
    hold_names = [D["meta"][int(i)]["개체"] for i in hold_rows]
    _hu, _hid, hgroups = cluster_groups(hold_names)
    rng_h = np.random.default_rng([STAT_SEED, 6])
    se_hold_cl = float(cboot(hgroups, rng_h, lambda pos: cov_h_rows[pos].mean()).std(ddof=1))
    band_ok = bool(BAND_41[0] <= cov_hold_uncal <= BAND_41[1])
    obs_41 = {"홀드아웃 비보정 덮개(신 앙상블 · 행 평균)": round(cov_hold_uncal, 4),
              "클러스터 SE(98 개체 · seed [11004,6])": round(se_hold_cl, 5),
              "등록 구간 [0.7108, 0.8284] 안": band_ok,
              "낙인": ("구간 안 — 교환가능성 신고 정합" if band_ok else
                     "🔴 구간 밖 — «홀드아웃과 val 은 다른 종류» 신고(판정 전 · #140 ④-1) — "
                     "판정 자체는 ㉤·㉥ 이 진다")}

    # ── ④-3 재가중 + Mondrian δ_d 관찰 ────────────────────────────────
    dom_h = D["dom_id"][hold_rows]
    val_w = {d: float((before["dom_va"] == D["domains"].index(d)).sum()) / len(D["va"])
             for d in ROSTER}
    hold_cov_d = {}
    for d in ROSTER:
        m = dom_h == D["domains"].index(d)
        hold_cov_d[d] = float(cov_h_rows[m].mean()) if m.any() else None
    reweighted = float(sum(val_w[d] * hold_cov_d[d] for d in ROSTER if hold_cov_d[d] is not None))
    obs_43 = {"val 행 구성 재가중 홀드아웃 덮개": round(reweighted, 4),
              "원값과 차(재가중 − 원값)": round(reweighted - cov_hold_uncal, 4)}
    # Mondrian δ_d (관찰 — 적용·배포 금지)
    q05h = ens_hold[..., 0].astype(np.float64)
    q95h = ens_hold[..., 4].astype(np.float64)
    scores_h = np.maximum(q05h - r_h, r_h - q95h)
    mond = {}
    for d in ROSTER:
        m = dom_h == D["domains"].index(d)
        if m.any():
            dv, _ = q_conf(scores_h[m].ravel())
            mond[d] = round(dv, 4)

    # ── ㉥ 내부 정합 A/B (#140 ④-2) ──────────────────────────────────
    rng9 = np.random.default_rng([STAT_SEED, 9])
    A_names, B_names = [], []
    by_dom_h = {}
    for n in sorted(picked):
        by_dom_h.setdefault(ent_dom[n], []).append(n)
    for d in sorted(by_dom_h):
        names = sorted(by_dom_h[d])
        perm = rng9.permutation(len(names))
        for j, pi in enumerate(perm):
            (A_names if j % 2 == 0 else B_names).append(names[pi])
    nameset_A, nameset_B = set(A_names), set(B_names)
    maskA = np.asarray([n in nameset_A for n in hold_names])
    maskB = np.asarray([n in nameset_B for n in hold_names])
    dA, _ = q_conf(scores_h[maskA].ravel())
    covB_rows = ((r_h[maskB] >= q05h[maskB] - dA) & (r_h[maskB] <= q95h[maskB] + dA)).mean(axis=1)
    cov_B = float(covB_rows.mean())
    _bu, _bid, bgroups = cluster_groups([n for n in hold_names if n in nameset_B])
    rng91 = np.random.default_rng([STAT_SEED, 9, 1])
    se_B_cl = float(cboot(bgroups, rng91, lambda pos: covB_rows[pos].mean()).std(ddof=1))
    thr_6 = max(J_cov, 2.0 * se_B_cl)
    obs_6 = float(cov_B - TARGET)
    g6 = bool(abs(obs_6) <= thr_6)
    cell_6 = {"n_A/n_B(개체)": "%d/%d" % (len(A_names), len(B_names)),
              "δ̂_A": round(dA, 4), "cov_B(δ̂_A 적용)": round(cov_B, 4),
              "문턱(0.90 ± max(J″_cov, 2×SE_B^cl))": round(thr_6, 4)}

    # ── δ 전역 (홀드아웃 전체) → val 적용 ─────────────────────────────
    delta, ql = q_conf(scores_h.ravel())
    marg_pre = float((scores_h <= 0).mean())
    marg_post = float((scores_h <= delta).mean())
    pred_after = ens_val.copy()
    pred_after[..., 0] -= delta
    pred_after[..., 4] += delta
    after = eval_val(pred_after, D)
    prog({"δ": round(delta, 4), "cov_hold_uncal": round(cov_hold_uncal, 4),
          "val 미보정": round(uncal["cover"], 4), "val 보정": round(after["cover"], 4)})

    # ── ㉤ 전제 관문 — 교환가능성 (짝 눈금) ───────────────────────────
    val_names = [D["meta"][int(i)]["개체"] for i in D["va"]]
    vuniq, vids, vgroups = cluster_groups(val_names)
    ucov = uncal["cover_ent"].astype(np.float64)
    rng8 = np.random.default_rng([STAT_SEED, 8])
    se_val_cl = float(cboot(vgroups, rng8, lambda pos: ucov[pos].mean()).std(ddof=1))
    obs_5 = float(cov_hold_uncal - uncal["cover"])
    se_diff = float(np.sqrt(se_hold_cl ** 2 + se_val_cl ** 2))
    thr_5 = max(J_cov, 2.0 * se_diff)
    g5 = bool(abs(obs_5) <= thr_5)
    cell_5 = {"cov_신(홀드아웃 · 미보정)": round(cov_hold_uncal, 4),
              "cov_신(val · 미보정)": round(uncal["cover"], 4),
              "차": round(obs_5, 4),
              "SE_diff^cl(√(SE²h+SE²v))": round(se_diff, 5)}

    # ── ㉠ 주대비 — 클러스터 SE(판정) + 행 SE(관찰) + 클러스터 순열 ────
    a_i = before["cover_ent"].astype(np.float64)
    b_i = after["cover_ent"].astype(np.float64)
    n_rows = len(a_i)
    C_obs = dist(a_i.mean()) - dist(b_i.mean())
    rng2 = np.random.default_rng([STAT_SEED, 2])
    cs_cl = cboot(vgroups, rng2,
                  lambda pos: dist(a_i[pos].mean()) - dist(b_i[pos].mean()))
    se_C_cl = float(cs_cl.std(ddof=1))
    rng10 = np.random.default_rng([STAT_SEED, 10])
    idx = rng10.integers(0, n_rows, size=(N_BOOT, n_rows))
    se_C_row = float((np.abs(TARGET - a_i[idx].mean(axis=1))
                      - np.abs(TARGET - b_i[idx].mean(axis=1))).std(ddof=1))
    rng3s = np.random.default_rng([STAT_SEED, 3])
    flips_cl = rng3s.random((N_PERM, len(vgroups))) < 0.5
    flips_row = flips_cl[:, vids]                        # (B, n_rows)
    ap = np.where(flips_row, b_i[None, :], a_i[None, :])
    bp = np.where(flips_row, a_i[None, :], b_i[None, :])
    stat = np.abs(TARGET - ap.mean(axis=1)) - np.abs(TARGET - bp.mean(axis=1))
    p_one = float((1 + (stat >= C_obs).sum()) / (1 + N_PERM))
    ent_a = np.asarray([a_i[g].mean() for g in vgroups])
    ent_b = np.asarray([b_i[g].mean() for g in vgroups])

    # ── ㉡ Δ_d (행 SE 판정 · 클러스터 SE 관찰) · ㉢ · ㉣ ──────────────
    ape_dep = before["ape"].astype(np.float64)
    ape_new = uncal["ape"].astype(np.float64)            # q50 은 보정 무접촉 — after 와 동일
    delta_d = {d: after["per_dom"][d] - before["per_dom"][d] for d in ROSTER}
    se_d, se_d_cl = {}, {}
    for k, d in enumerate(ROSTER):
        m = before["dom_va"] == D["domains"].index(d)
        A, B = ape_dep[m], ape_new[m]
        n_d = int(m.sum())
        rngd = np.random.default_rng([STAT_SEED, 1, k])
        idxd = rngd.integers(0, n_d, size=(N_BOOT, n_d))
        se_d[d] = float((np.median(B[idxd], axis=1) - np.median(A[idxd], axis=1)).std(ddof=1))
        dn = [val_names[j] for j in np.where(m)[0]]
        if len(set(dn)) >= 8:
            _du, _did, dgroups = cluster_groups(dn)
            rngdc = np.random.default_rng([STAT_SEED, 11, k])
            se_d_cl[d] = round(float(cboot(dgroups, rngdc,
                                           lambda pos, A=A, B=B: np.median(B[pos]) - np.median(A[pos]),
                                           B=2000).std(ddof=1)), 4)
    d_tot = after["tot"] - before["tot"]
    rng4 = np.random.default_rng([STAT_SEED, 4])
    se_tot_cl = float(cboot(vgroups, rng4,
                            lambda pos: np.median(ape_new[pos]) - np.median(ape_dep[pos])).std(ddof=1))
    w_a = before["piw_ent"].astype(np.float64)
    w_b = after["piw_ent"].astype(np.float64)
    d_W = after["W"] - before["W"]
    dW_base = uncal["W"] - before["W"]                   # 신 앙상블 기저 폭 − 배포 폭
    rng5 = np.random.default_rng([STAT_SEED, 5])
    se_W_cl = float(cboot(vgroups, rng5,
                          lambda pos: w_b[pos].mean() - w_a[pos].mean()).std(ddof=1))
    pay2d = 2.0 * delta

    # ── 판정 (비반올림 · 여유 게재) ───────────────────────────────────
    thr_t = max(J_cov, 2.0 * se_C_cl)
    g1 = bool(C_obs > thr_t)
    judge = [d for d in ROSTER if d not in SMALL]
    thr_d = {d: max(J[d], MULT_OTHER * se_d[d]) for d in judge}
    bad = {d: {"Δ": delta_d[d], "문턱": thr_d[d]} for d in judge if delta_d[d] > thr_d[d]}
    g2 = bool(not bad)
    thr_tot = max(J_tot, 2.0 * se_tot_cl)
    g3 = bool(d_tot <= thr_tot)
    if pay2d <= 0:
        g4, thr_w = None, None                           # 사전 규칙(#140 ⑦-5) — 미판정(퇴화)
    else:
        thr_w = pay2d + max(J_W, 2.0 * se_W_cl)
        g4 = bool(d_W <= thr_w)

    probes = {"㉠": gate_probe(GATES["㉠"]["pass_fn"], C_obs, thr_t, -1.0),
              "㉢": gate_probe(GATES["㉢"]["pass_fn"], d_tot, thr_tot, +1.0),
              "㉤": gate_probe(GATES["㉤"]["pass_fn"], obs_5, thr_5, +1.0, two=True),
              "㉥": gate_probe(GATES["㉥"]["pass_fn"], obs_6, thr_6, +1.0, two=True)}
    if g4 is not None:
        probes["㉣"] = gate_probe(GATES["㉣"]["pass_fn"], d_W, thr_w, +1.0)
    for d in judge:
        probes["㉡ " + d] = gate_probe(GATES["㉡"]["pass_fn"], delta_d[d], thr_d[d], +1.0)
    n_m = sum(1 for p in probes.values() if not p["거짓 나옴"])
    n_n = sum(1 for p in probes.values() if not p["참 나옴"])
    n_worse = sum(1 for p in probes.values() if p["㉰ 악화 극값에서 참"])
    n_better = sum(1 for p in probes.values() if p["㉱ 개선 극값에서 거짓"])
    n_degen = sum(1 for p in probes.values() if p["퇴화 문턱(thr ≤ 0)"])
    n_dir = sum(1 for p in probes.values() if not p["방향 검사"])

    # ── #140 ⑦-6 자료-조건부 연역 계수 (기계 규칙: 관측 SE = 0 이면 연역 가능) ──
    ded = {"㉠": se_C_cl == 0.0, "㉢": se_tot_cl == 0.0,
           "㉣": (None if g4 is None else se_W_cl == 0.0),
           "㉤": se_diff == 0.0, "㉥": se_B_cl == 0.0}
    for d in judge:
        ded["㉡ " + d] = se_d[d] == 0.0
    n_cells = 13
    n_deducible = sum(1 for v in ded.values() if v is True)
    n_nondeducible = sum(1 for v in ded.values() if v is False)
    등록어 = "판정 사이클" if n_nondeducible > 0 else "측정 사이클(#140 ⑦-6 — 연역 불가 0)"

    # ── 판정어 ────────────────────────────────────────────────────────
    if n_worse or n_better or n_dir:
        verdict = ("등록 결함 — 자료 탐침 ㉰ %d · ㉱ %d · 방향 위반 %d (관찰 강등 · 배포 0)"
                   % (n_worse, n_better, n_dir))
    elif not leak_ok:
        verdict = "등록 결함 — 홀드아웃-val 개체 누수 ≠ 0 (관찰 강등 · 배포 0)"
    elif not (anchorA_ok and anchorB_ok):
        verdict = "관찰 강등 — 앵커 불통과 (A %s · B %s) (배포 0)" % (anchorA_ok, anchorB_ok)
    elif not (g5 and g6):
        verdict = "전제 붕괴 — 교환가능성 관문 ㉤ %s · ㉥ %s (관찰 강등 · 배포 0)" % (g5, g6)
    elif g1 and g2 and g3 and (g4 is None or g4):
        verdict = ("성공 — 배포 진행 (사전등록 §6 절차 그대로)"
                   + (" · ㉣ 미판정(퇴화 — 지불 음수 · 사전 규칙 병기)" if g4 is None else ""))
    elif g1:
        verdict = "부분 — ㉠ 통과나 ㉡/㉢/㉣ 일부 불통과 (배포 0)"
    else:
        verdict = "실패 — ㉠ 불통과 (배포 0)"

    # ── 배포 후보물 (성공 시 §6 그대로 집행) ──────────────────────────
    hold_list_sha = hashlib.sha256("\n".join(sorted(picked)).encode("utf-8")).hexdigest()[:16]
    man_cand = {"형식": "앙상블 manifest 후보 (사이클 1004 · 홀드아웃 재학습)",
                "구성원": {str(sd): {"경로": ckpts[sd]["경로"], "sha256": ckpts[sd]["sha"]}
                        for sd in SEEDS},
                "결합": "분위수 텐서 (91,5) 산술 평균", "씨앗": list(SEEDS),
                "text_emb": os.path.join(TRI, "text_emb_qwen05b.npz"),
                "sao sha": sha16(os.path.join(TRI, "sao.npz")),
                "학습 제외 홀드아웃": {"개체 수": len(picked), "명단 sha256/16": hold_list_sha},
                "사전등록": "docs/탐색/1004.md"}
    with open(os.path.join(EXP, "manifest_candidate.json"), "w", encoding="utf-8") as f:
        json.dump(man_cand, f, ensure_ascii=False, indent=1)
    conf_cand = {"형식": "등각 보정 v2 (사이클 1004 · 무누수 홀드아웃 · 전역)",
                 "α": ALPHA, "δ(log)": delta,
                 "적용": "q05 − δ · q95 + δ (q25/q50/q75 무접촉 · 잔차 log 눈금)",
                 "유효 조건": "배포 시 새 manifest sha 를 기입해 소비자가 대조(#140 ⑦-3 ㉰) — "
                          "후보 단계는 구성원 sha 목록이 그 자리",
                 "구성원 sha": {str(sd): ckpts[sd]["sha"] for sd in SEEDS},
                 "홀드아웃": {"개체 수": len(picked), "행 수": int(len(hold_rows)),
                         "명단 sha256/16": hold_list_sha, "score n": int(scores_h.size),
                         "q_level": round(ql, 6)},
                 "잰 소스 (조항 66)": {"sao.npz": sha16(os.path.join(TRI, "sao.npz")),
                                  "text_emb_qwen05b.npz": sha16(os.path.join(TRI, "text_emb_qwen05b.npz")),
                                  "러너": sha16(os.path.abspath(__file__))},
                 "생성 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(EXP, "conformal_candidate.json"), "w", encoding="utf-8") as f:
        json.dump(conf_cand, f, ensure_ascii=False, indent=1)

    # ── out ───────────────────────────────────────────────────────────
    out = {
        "러너": "runners/holdout1004.py",
        "표적": "④ 90% 덮개율(전역 marginal — #140 ④-4 자백) — 홀드아웃 재학습 + 무누수 등각",
        "시작 시각": 시작,
        "합성 방향 탐침(측정 전 · v5.3-2)": pre_probe,
        "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
        "sha 검증(사전등록 대조)": sha_verify,
        "러너 자신": sha16(os.path.abspath(__file__)),
        "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
               "학습 씨앗(넷째)": list(SEEDS), "통계 씨앗": STAT_SEED, "α": ALPHA,
               "홀드아웃 비율": HOLD_FRAC, "threads": torch.get_num_threads(),
               "device": "cpu", "B": {"붓스트랩": N_BOOT, "순열": N_PERM},
               "판정 눈금": "㉠㉢㉤㉥ = 개체 이름 클러스터 SE · ㉡ = 행 SE(등록 §4 사유) · "
                        "행 SE 는 병기(#140 ⑦-2)"},
        "홀드아웃 구성 (앵커 B 원천 · 관찰 16칸)": hold_sum,
        "앵커 A (배포 정본 재현 항등 13칸 · «실행 간» · ≤1.5e-4)": dict(
            anchorA, 통과=bool(anchorA_ok), 성분="같은 모형·자료·코드 경로 재실행 — 재추첨 0"),
        "앵커 B (사전 실측 재현 3칸)": dict(anchorB, 통과=bool(anchorB_ok)),
        "씨앗별 결과 (관찰 65칸 = 씨앗5×13)": {str(sd): seed_cells[sd] for sd in SEEDS},
        "체크포인트 (저장소 밖 · 조항 73-마)": {str(sd): ckpts[sd] for sd in SEEDS},
        "신 앙상블 미보정 val (관찰 13칸)": {
            "도메인별 MdAPE": {d: round(uncal["per_dom"][d], 4) for d in ROSTER},
            "전체 MdAPE": round(uncal["tot"], 4), "90% 덮개율": round(uncal["cover"], 4),
            "구간 평균 폭(log)": round(uncal["W"], 4)},
        "J‴ (넷째 씨앗 5 |Δ배포 리더보드| 최대 — 다음 앵커 정본 신고 · ㉯ · 관찰 13칸)": dict(
            Jppp, 성분="🔴 «씨앗 간 + train 축소(−98 개체 · −18.4% 행)» — 순수 씨앗 지터 아님을 "
                     "알고 신고(등록 §3)"),
        "δ 요약 (관찰 5칸)": {"score n(행×91)": int(scores_h.size),
                         "q_level(유한표본 보정)": round(ql, 6), "δ(전역 · log)": delta,
                         "홀드아웃 한계-덮개(전)": round(marg_pre, 4),
                         "홀드아웃 한계-덮개(후 · δ 적용)": round(marg_post, 4)},
        "Mondrian δ_d (관찰 10칸 · 적용·배포 금지 · #140 ④-3)": mond,
        "#140 ④-1 신고 (관찰 3칸)": obs_41,
        "#140 ④-3 재가중 (관찰 2칸)": obs_43,
        "㉤ 전제 관문 수치 (관찰 4칸)": cell_5,
        "㉥ 전제 관문 수치 (관찰 4칸)": cell_6,
        "val 전/후 (관찰 26칸)": {
            "전(배포 앙상블)": {"도메인별 MdAPE": {d: round(before["per_dom"][d], 4) for d in ROSTER},
                          "전체 MdAPE": round(before["tot"], 4),
                          "90% 덮개율": round(before["cover"], 4),
                          "구간 평균 폭(log)": round(before["W"], 4)},
            "후(신 앙상블+δ)": {"도메인별 MdAPE": {d: round(after["per_dom"][d], 4) for d in ROSTER},
                          "전체 MdAPE": round(after["tot"], 4),
                          "90% 덮개율": round(after["cover"], 4),
                          "구간 평균 폭(log)": round(after["W"], 4)}},
        "도메인 조건부 val 덮개 전/후 (관찰 20칸 · #140 ④-4 의무)": {
            d: {"전": round(float(a_i[before["dom_va"] == D["domains"].index(d)].mean()), 4),
                "후": round(float(b_i[before["dom_va"] == D["domains"].index(d)].mean()), 4)}
            for d in ROSTER},
        "도메인 조건부 val 덮개 (Mondrian δ_d 적용 시 · 관찰 10칸)": {
            d: round(float(((D["R"][D["va"]][before["dom_va"] == D["domains"].index(d)]
                             >= ens_val[before["dom_va"] == D["domains"].index(d), :, 0] - mond.get(d, 0.0))
                            & (D["R"][D["va"]][before["dom_va"] == D["domains"].index(d)]
                               <= ens_val[before["dom_va"] == D["domains"].index(d), :, 4] + mond.get(d, 0.0))
                            ).mean()), 4)
            for d in ROSTER if d in mond},
        "헤드라인(㉠ 주대비 · 조항 79 · 관찰 10칸)": {
            "n(행 · 개체창)": n_rows, "유일 개체": len(vgroups),
            "|0.90−cov| 전": round(dist(a_i.mean()), 6),
            "|0.90−cov| 후": round(dist(b_i.mean()), 6),
            "C(거리 감소 · 원값)": C_obs,
            "행 SE(관찰 · [11004,10])": round(se_C_row, 5),
            "클러스터 SE(판정 눈금 · [11004,2])": round(se_C_cl, 5),
            "t(클러스터)": round(C_obs / se_C_cl, 2) if se_C_cl > 0 else None,
            "동부호(행 오른/내린/그대로 · 개체 오른/내린/그대로)": "%d/%d/%d · %d/%d/%d" % (
                int((b_i > a_i).sum()), int((b_i < a_i).sum()), int((b_i == a_i).sum()),
                int((ent_b > ent_a).sum()), int((ent_b < ent_a).sum()),
                int((ent_b == ent_a).sum())),
            "부호뒤집기 순열 p(클러스터 묶음 · 한쪽꼬리 · 개선=C 상승)": round(p_one, 5),
            "🔴 판정어 층의 연역 불가능 칸 수(#140 ⑦-6)": "%d/%d → 등록어 = %s" % (
                n_nondeducible, n_cells, 등록어)},
        "Δ·SE 표 (신+δ − 배포 · 관찰 28칸)": {
            **{d: {"Δ": round(delta_d[d], 4), "SE(행·판정)": round(se_d[d], 4),
                   "SE(클러스터·관찰)": se_d_cl.get(d, "미계산(유일 개체 <8)"),
                   "J″_d": J[d]} for d in ROSTER},
            "덮개율": {"Δ": round(after["cover"] - before["cover"], 4),
                    "SE^cl(㉠ 은 C 로 판정)": round(se_C_cl, 5), "J″_cov": J_cov},
            "전체": {"Δ": round(d_tot, 4), "SE^cl": round(se_tot_cl, 5), "J″_전체": J_tot},
            "폭": {"Δ": round(d_W, 4), "SE^cl": round(se_W_cl, 5), "J″_폭": J_W}},
        "폭 분해 (관찰 3칸)": {
            "Δ폭": round(d_W, 6), "2δ(보정 몫 · 이론 지불)": round(pay2d, 6),
            "ΔW_base(신 기저 − 배포 · 씨앗+train 축소 몫)": round(dW_base, 6),
            "참고 눈금": "1003 val 관찰 2δ_val = +%.4f (out1003 · 등록 §4)" % ref_2dv},
        "자료-조건부 연역 계수 (#140 ⑦-6 · 관찰 1칸)": {
            "칸별(참=연역 가능)": {k: v for k, v in ded.items()},
            "연역 가능": n_deducible, "연역 불가능": n_nondeducible, "등록어": 등록어},
        "판정 (사전등록 §4 · 판정 13칸 · 비반올림 집행 · 여유 = Δ − 문턱)": {
            "앵커 A": bool(anchorA_ok), "앵커 B": bool(anchorB_ok),
            "㉤ 교환가능성(양쪽 · 전제)": {"통과": g5, "|차|": abs(obs_5), "문턱": thr_5,
                                 "여유(원값 · 문턱−|차|)": thr_5 - abs(obs_5)},
            "㉥ 내부 정합 A/B(양쪽 · 전제)": {"통과": g6, "|cov_B−0.90|": abs(obs_6),
                                    "문턱": thr_6, "여유(원값)": thr_6 - abs(obs_6)},
            "㉠ 목표 거리 감소(악화=C 하락)": {"통과": g1, "C": C_obs,
                                   "문턱 max(J″_cov, 2×SE^cl)": thr_t,
                                   "여유(원값)": C_obs - thr_t},
            "㉡ 도메인 MdAPE 유의 악화(판정 8 · 악화=상승)": {
                "통과": g2, "걸린 도메인": bad if bad else "없음(0/8)",
                "여유(원값 · Δ_d − 문턱)": {d: delta_d[d] - thr_d[d] for d in judge}},
            "㉢ 전체 MdAPE 비악화(악화=상승 · train 축소 지불 자리)": {
                "통과": g3, "Δ전체(원값)": d_tot, "문턱": thr_tot, "여유(원값)": d_tot - thr_tot},
            "㉣ 폭 지불 한도(악화=초과 · 2δ+max(J″_폭,2SE))": (
                {"판정": "미판정(퇴화 — 지불 음수 · 사전 규칙 #140 ⑦-5)", "2δ": pay2d,
                 "Δ폭(관찰)": d_W} if g4 is None else
                {"통과": g4, "Δ폭(원값)": d_W, "문턱(원값)": thr_w, "여유(원값)": d_W - thr_w,
                 "2δ": pay2d}),
            "게임·만화(관찰 — n_val 5·6행)": {d: {"Δ": round(delta_d[d], 4),
                                          "SE(행)": round(se_d[d], 4)} for d in SMALL}},
        "조항 78 탐침 (측정 후 · v5.3-3 + ㉰㉱ + 연역 계수)": dict(
            probes, 계수={"㉮ 원리상 못 떨어짐(격자)": n_m, "㉯ 원리상 못 통과(격자)": n_n,
                        "㉰ 악화 극값에서 참": n_worse, "㉱ 개선 극값에서 거짓": n_better,
                        "퇴화 문턱": n_degen, "방향 검사 위반": n_dir}),
        "순열 p 규약(#140 ⑦-7)": "두 모형 비교 — 구조 퇴화 아님(행별 양방향 이동 가능) · "
                             "동부호 칸에서 실측 확인",
        "판정어": verdict,
        "배포 후보(성공 시 §6 그대로)": {
            "manifest_candidate.json": {"경로": os.path.join(EXP, "manifest_candidate.json"),
                                        "sha": sha16(os.path.join(EXP, "manifest_candidate.json"))},
            "conformal_candidate.json": {"경로": os.path.join(EXP, "conformal_candidate.json"),
                                         "sha": sha16(os.path.join(EXP, "conformal_candidate.json"))},
            "δ": delta},
        "관찰 분모 신고(조항 79)": (
            "대비 주장 1(㉠ 목표 거리 · 전역 marginal) · 관찰 249 = 앵커A 13 + 앵커B 3 + "
            "씨앗별 65 + 신 앙상블 13 + 홀드아웃 구성 16 + δ 요약 5 + Mondrian 10 + ④-1 3 + "
            "④-3 2 + 조건부 덮개 20 + Mondrian 조건부 10 + ㉤ 4 + ㉥ 4 + val 전/후 26 + "
            "헤드라인 10 + Δ·SE 28 + J‴ 13 + 폭 분해 3 + 연역 1 · 판정 13(㉠1 ㉡8 ㉢1 ㉣1 "
            "㉤1 ㉥1) · 배포 시 LODO 관찰 += 10"),
        "총소요초": round(time.time() - t_all, 1),
        "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "δ": round(delta, 4),
                      "덮개율": "%.4f → %.4f(미보정 %.4f)" % (before["cover"], after["cover"],
                                                       uncal["cover"]),
                      "C": round(C_obs, 4), "㉤": g5, "㉥": g6, "Δ전체": round(d_tot, 4),
                      "Δ폭": round(d_W, 4), "p": p_one, "연역 불가": "%d/13" % n_nondeducible,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
