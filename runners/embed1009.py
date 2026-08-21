# -*- coding: utf-8 -*-
"""확증 1009 러너 — ft-v1 재임베딩 · 기획서 문체 개방 판정: base-0.5B(현행) 대 ft-0.5B
(사전등록 docs/탐색/1009.md 에서 언 코드 · 루프 v5.3 동결 · 부칙 1~4 · 티처 #139 ⑦ 승계).

🔴 이 사이클의 표적은 정확도가 아니라 «개방»이다 — 주대비 «하나»(조항 79):
  ㉠ 기획서 문체 OOD 비율 «중앙값»(ft 공간 · 프로브 24문) < 3.0 (등록 상수 = 현행 가드 경고선)
분별 유지(사전 명기 — 「기획서만 가까워지고 분별이 죽으면 실패」):
  ㉥1 분포-안 대조군(val 유일 텍스트 128 · seed [11009,0]) ft 중앙값 ≤ 1.5 (base 실측 1.07급의 자리)
  ㉥2 원거리 대조군(20문 — 영어 산문·코드·무의미 음절) ft 중앙값 > 3.0 (경고선 밖 유지)
비열화 게이트(ft팔 − base팔 · 앙상블 대 앙상블 · 같은 축소 train · 씨앗 1501~1505 · δ̂ 각자):
  ㉡ 판정 6 도메인(도서·모바일·세계애니·시장팝업·애니·팝업) Δ_d > max(J5_d, 2.6×SE_d^행) 0
     (n_val<30 게임·만화 관찰 · 🔴 웹툰·아이돌 관찰만 — 1008 「자 존속」 · 과업 지시)
  ㉢ Δ전체 ≤ +max(J5_전체, 2×SE^cl) · ㉣ Δ덮개율(보정) ≥ −2×SE^cl (J 금지 #141 ⑥)
  ㉤ Δ폭(보정) ≤ +2×SE^cl (J 금지)
판정 12칸 = ㉠1 ㉥2 ㉡6 ㉢1 ㉣1 ㉤1 · 비반올림 집행 · OOD 자 = serve.py 자구 미러
(REF_NN = E[tr] 512 표본 rng(0) 최근접 중앙값 · 비율 = dmin/REF_NN · fp32).
앵커: A 배포(1004+δ) 재현 13칸 · A′ 미보정 2칸 · B 로스터 3칸 · C base팔 대 배포 13칸
(max(J″,3SE^행)) · D 라이브=저장 미러 항등 16칸(cos ≥ 0.999 · base 8 + ft 8 — 조항 66
학습·서빙 임베더 불일치 금지의 실측 관문). 🔴 부칙 4: epoch_guard.assert_epoch — 게재는 반환값.
🔴 CPU 4스레드 · MPS 0 · 유료 API 0 · 학습 10(2팔×5씨앗 · 순차 · load1>10 대기) ·
배포 파일 무변경(읽기만) · 씀: python3 runners/embed1009.py
"""
import gc
import hashlib
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.transition import Transition, pinball, load_ensemble, load_conformal, ConformalWrap  # noqa: E402
from pretrain.epoch_guard import assert_epoch  # noqa: E402  (부칙 4)

torch.set_num_threads(4)
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

SEEDS = (1501, 1502, 1503, 1504, 1505)   # 🔴 여섯째 집합 — 997·1001~1005·1101~·1201~·1301~·1401~·1601~(1006) 금지 이행
STAT_SEED = 11009                        # 🔴 신규 통계 스트림 — 11001~11006·[1007,·] 재사용 금지
CARVE_SEED = [11004, 0]                  # 로스터 «재현» 전용(새 뽑기 아님 · 앵커 B sha 강제)
N_BOOT = 10000
ALPHA = 0.10
HOLD_FRAC = 0.15
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
SMALL = ("게임", "만화")                  # n_val 5·6 행 — 관찰(v5.1 하한)
OBS_ONLY = ("웹툰", "아이돌")             # 🔴 관찰만 — 1008 자 존속(웹툰 val 9 개체) · 과업 지시
JUDGE_D = tuple(d for d in ROSTER if d not in SMALL and d not in OBS_ONLY)   # ㉡ 6 도메인
MULT_OTHER = 2.6
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

THR_OPEN = 3.0                           # ㉠ 등록 상수 — 현행 serve OOD 경고선(3+ 경고)
THR_IND = 1.5                            # ㉥1 등록 상수 — base 분포-안 실측 1.07급 × 1.4 여유
THR_FAR = 3.0                            # ㉥2 등록 상수 — 원거리는 경고선 «밖» 유지
MIRROR_COS = 0.999                       # 앵커 D — 라이브=저장 cos 하한
N_IND = 128                              # 분포-안 대조군 표본 수

REG_HOLD_ENT, REG_HOLD_ROWS = 98, 1752
REG_HOLD_SHA = "0cbc70bb8b83d579"
REG_DEP_UNCAL_COV, REG_DEP_UNCAL_W = 0.7530, 0.5026   # out1004 관찰값(«실행 간»)
REG_META_ROWS, REG_D = 10654, 896
REG_MANIFEST_SHA = "3a5c2543a55f1dab"    # 부칙 4 등록 기재값(1004 시대)

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "embed1009")
OUT_JSON = os.path.join(REPO, "runners", "out1009_embed.json")
SNAP = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
        "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
FT_SLIM = os.path.join(ART, "ft", "ckpt", "ft-v1", "model_slim_fp32.pt")
FT_CKPT = os.path.join(ART, "ft", "ckpt", "ft-v1", "latest.pt")
P_PLAN = os.path.join(REPO, "data", "probe1009_기획서.txt")
P_FAR = os.path.join(REPO, "data", "probe1009_원거리.txt")

ARMS = ("base05b", "ftv1")
ARM_EMB = {"base05b": os.path.join(TRI, "text_emb_qwen05b.npz"),
           "ftv1": os.path.join(TRI, "text_emb_ftv1.npz")}
MIRROR_IDX = (0, 1500, 3000, 4500, 6000, 7500, 9000, 10653)   # 앵커 D 항등 행

EXPECT_SHA = {
    os.path.join(TROUT, "ensemble_manifest.json"): "3a5c2543a55f1dab",
    os.path.join(TROUT, "conformal.json"): "d8f40489c9341302",
    os.path.join(TROUT, "leaderboard.json"): "f15a9907fb3ef6b9",
    os.path.join(TROUT, "report.json"): "6dfb0a4ff2935de0",
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "meta.jsonl"): "f74f94235bc5f032",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
    os.path.join(TRI, "text_emb_ftv1.npz"): "5bcdd8f26b1520b8",           # 🔴 재임베딩 sha 사슬
    os.path.join(TRI, "text_emb_ftv1.config.json"): "80dbf10f68dc20c2",
    os.path.join(ART, "ft", "embed_triples_ftv1.py"): "7eb5fa0f6ed21c04",  # 생성 코드
    FT_SLIM: "a9f55691c1acf83f",
    FT_CKPT: "de370e7bd54d6945",                                           # ft-v1 ckpt(5.9GB)
    P_PLAN: "0cda661219f9443c",                                            # 기획서 프로브 24문
    P_FAR: "9a27d24f1aa7a5c7",                                             # 원거리 프로브 20문
    os.path.join(REPO, "runners/out1002_ensemble.json"): "bad5616b2561a21f",  # J″ 정본(앵커 C)
    os.path.join(REPO, "runners/out1005_embed.json"): "cd3a6ce8c4f4841a",     # J5 정본(㉡㉢ 문턱)
    os.path.join(REPO, "data/lab/1005_판_후.json"): "01214fc2a7ff8f31",       # 전판
}
KEY_JPP = "J″_d (셋째 씨앗 5 |Δ리더보드| 최대 · 1001 J′ 와 같은 정의 — 다음 앵커 정본 신고 · ㉯)"
KEY_J5 = "J5 (보정 팔 ㉯ — 다음 앵커 정본 신고 · 관찰 13칸)"

# 🔴 #141 ⑥-1 — 게이트별 문턱 원천 선언(코드 관문이 검사): J‴ 는 어디에도 없어야 한다
GATE_THRESH_SRC = {"㉠": ("등록상수 3.0",), "㉥1": ("등록상수 1.5",), "㉥2": ("등록상수 3.0",),
                   "㉡": ("J5", "2.6×SE^행"), "㉢": ("J5", "2×SE^cl"),
                   "㉣": ("2×SE^cl",), "㉤": ("2×SE^cl",)}
# 🔴 #141 ① — 부호 구조 연역 선언 맵(㉡㉢㉣㉤ 짝 대비만 · ㉠㉥ 는 비대비 게이트 — 자백 각주)
SIGN_FORCING_CONST = {"㉡": None, "㉢": None, "㉣": None, "㉤": None}


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
                           ensure_ascii=False) + "\n")     # 부칙 4 ㉰ — 전 행 시각


def load_gate_wait():
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60
    return waited


# ── 게이트 함수 + 부호 서명 (v5.3-1) ──────────────────────────────────
GATES = {
    "㉠": {"pass_fn": lambda x, t: x < t, "worse_sign": +1.0,
          "악화 한 줄": "기획서 문체가 학습 분포에서 멀수록(OOD 비율 «오르면» +) 나쁘다 — 개방 불가. "
                    "통과는 ft 공간 중앙값이 가드 경고선(3.0) «안»일 때만"},
    "㉥1": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
           "악화 한 줄": "분포-안 대조군의 OOD 비율이 «올라»(+) 분포 밖으로 밀리면 — ft 공간이 제 "
                     "학습 분포조차 못 담는 것 — 악화(자 파손)"},
    "㉥2": {"pass_fn": lambda x, t: x > t, "worse_sign": -1.0,
           "악화 한 줄": "전혀 무관한 텍스트의 OOD 비율이 «내려와»(−) 경고선 안으로 들어오면 — "
                     "가드가 분별을 잃은 것(기획서 개방이 공허) — 악화. 반대쪽 극단(원거리가 더 "
                     "멀어짐 +)은 관찰 신고(v5.3-1)"},
    "㉡": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "그 도메인 누적 90일 중앙 예측 오차가 «오르면»(+) 임베더 교체가 남의 도메인을 "
                    "해친 것 — 악화 (1005 시장팝업형 숨은 청구서 검사)"},
    "㉢": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "전체 MdAPE 가 «오르면»(+) 개방을 전역 점 예측으로 사는 것 — 악화"},
    "㉣": {"pass_fn": lambda x, t: x >= -t, "worse_sign": -1.0,
          "악화 한 줄": "ft팔이 제 δ̂ 로도 val 구간 약속을 base팔만큼 못 지키면(덮개 «하락» −) — 악화. "
                    "과잉 쪽(+)은 폭(㉤)이 무는 자리 — 관찰 신고(v5.3-1)"},
    "㉤": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "같은 0.90 약속을 사는 값(보정 후 구간 평균 로그 폭)이 유의하게 «넓으면»(+) — "
                    "정보 없는 부풀리기로 산 것 — 악화"},
}


def presynth_probe(t=1.0):
    """v5.3-2 측정-«전» 합성 방향 탐침 — 전부 한쪽형: 악화 극값(악화방향×2t) 거짓 ∧ 개선 극값 참."""
    res, ok = {}, True
    for g, spec in GATES.items():
        worse = bool(spec["pass_fn"](spec["worse_sign"] * 2.0 * t, t))
        better = bool(spec["pass_fn"](-spec["worse_sign"] * 2.0 * t, t))
        good = (not worse) and better
        res[g] = {"악화 극값(×2t) 통과값": worse, "개선 극값 통과값": better,
                  "검사(악화 거짓 ∧ 개선 참)": good, "형": "한쪽"}
        ok = ok and good
    return ok, {"t(합성 문턱)": t, "게이트": res,
                "조문": "v5.3-2 — 측정 «전» · 어긋나면 측정 없이 중단"}


def gate_probe(pass_fn, obs, thr, worse_sign):
    """v5.3-3 자료 탐침 — 격자 + ㉰㉱ + 퇴화."""
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
            "방향 검사": bool((not vals["악화 극값"]) and vals["개선 극값"])}


def sign_structure(diffs, forcing):
    """#141 ① — 부호 구조 검사(1005 자구): 행 차 상수 항등 · 전행 동부호 + 강제 상수."""
    d = np.asarray(diffs, dtype=np.float64)
    const = bool(len(d) > 0 and float(d.max() - d.min()) == 0.0)
    npos, nneg, nzero = int((d > 0).sum()), int((d < 0).sum()), int((d == 0).sum())
    onesided = bool((npos == 0) or (nneg == 0))
    forced = bool(onesided and forcing is not None)
    return {"행 차 상수 항등(1003 ㉣형)": const, "행 동부호(+/−/0)": "%d/%d/%d" % (npos, nneg, nzero),
            "단측 구조": onesided, "부호 강제 등록-전 상수": forcing if forcing else "없음(선언 맵)",
            "부호 구조 연역(1003 ㉠형)": forced or const}


# ── 자료 (1005 러너와 자구까지 같은 전처리 · 팔별 C) ──────────────────
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
    n_dom = int(dom_id.max()) + 1
    onehot = np.zeros((len(S), n_dom), dtype=np.float32)
    onehot[np.arange(len(S)), dom_id] = 1.0
    C_common = np.concatenate([onehot, sin, cos, year, base], axis=1).astype(np.float32)
    meta = [json.loads(l) for l in open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")]
    C_arm, E_arm = {}, {}
    for arm in ARMS:
        E = np.load(ARM_EMB[arm])["E"].astype(np.float32)
        assert len(E) == len(S) == len(meta) == REG_META_ROWS, \
            "🔴 행 수 항등 실패(#139 ⑦-1): E %d · S %d · meta %d" % (len(E), len(S), len(meta))
        assert E.shape[1] == REG_D, "🔴 d 불일치(%s): %d ≠ %d" % (arm, E.shape[1], REG_D)
        C_arm[arm] = np.concatenate([C_common, E], axis=1).astype(np.float32)
        E_arm[arm] = E
    return {"S": S, "base": base, "Sc": Sc, "R": R, "dom_id": dom_id, "split": split,
            "C_arm": C_arm, "E_arm": E_arm, "domains": domains, "meta": meta,
            "tr": np.where(split == 0)[0], "va": np.where(split == 1)[0]}


def carve_holdout(D):
    """1004 로스터 «재현» — seed [11004,0] · 15% 층화 · 명단 sha 일치 강제(앵커 B) · 1005 자구."""
    ent_dom, ent_rows = {}, {}
    for i in D["tr"]:
        name = D["meta"][i]["개체"]
        ent_rows.setdefault(name, []).append(int(i))
        ent_dom.setdefault(name, D["domains"][D["dom_id"][i]])
    rng = np.random.default_rng(CARVE_SEED)
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
    lst_sha = hashlib.sha256("\n".join(sorted(picked)).encode("utf-8")).hexdigest()[:16]
    summary = {"홀드아웃 개체 수": len(picked), "홀드아웃 행 수": int(len(rows)),
               "남는 train 행 수": int(len(D["tr"]) - len(rows)),
               "명단 sha256/16": lst_sha,
               "val 개체 겹침(누수 검사 — 0 이어야)": overlap if overlap else 0,
               "뽑기 seed": "[11004,0] — 1004 로스터 «재현» 전용(새 뽑기 아님 · 사전등록 §2)"}
    return set(picked), rows, summary, lst_sha


def predict_rows(model, D, Carm, rows, chunk=2048):
    outs = []
    with torch.no_grad():
        for k in range(0, len(rows), chunk):
            ii = rows[k:k + chunk]
            x = torch.from_numpy(np.concatenate([D["Sc"][ii], Carm[ii]], axis=1))
            outs.append(model(x).numpy())
    return np.concatenate(outs)


def train_cur(seed, tr_pool, D, Carm):
    """현행 레시피 자구 동일 — 조건행렬만 팔별. rng [seed,step] · tr_pool 동일 →
    두 팔이 같은 씨앗에서 «같은 행»을 보고 학습한다(짝지은 설계 — 차이는 임베더뿐)."""
    d_in = D["Sc"].shape[1] + Carm.shape[1]
    torch.manual_seed(seed)
    model = Transition(d_in, hidden=HIDDEN)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    t0 = time.time()
    loss = None
    for step in range(STEPS):
        rng = np.random.default_rng([seed, step])
        ii = tr_pool[rng.integers(0, len(tr_pool), size=BATCH)]
        x = torch.from_numpy(np.concatenate([D["Sc"][ii], Carm[ii]], axis=1))
        r = torch.from_numpy(D["R"][ii])
        opt.zero_grad(set_to_none=True)
        loss = pinball(model(x), r)
        loss.backward()
        opt.step()
    model.eval()
    return model, round(float(loss.item()), 5), round(time.time() - t0, 1), d_in


def eval_val(pred, D):
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
    n = len(groups)
    out = np.empty(B)
    for b in range(B):
        gs = rng.integers(0, n, size=n)
        pos = np.concatenate([groups[g] for g in gs])
        out[b] = stat(pos)
    return out


def q_conf(scores, alpha=ALPHA):
    n = scores.size
    ql = min(1.0, (1.0 - alpha) * (1.0 + 1.0 / n))
    return float(np.quantile(scores, ql, method="higher")), ql


def summarize(ev):
    return {"도메인별 MdAPE": {d: round(ev["per_dom"][d], 4) for d in ROSTER},
            "전체 MdAPE": round(ev["tot"], 4), "90% 덮개율": round(ev["cover"], 4),
            "구간 평균 폭(log)": round(ev["W"], 4)}


# ── OOD 자 — serve.py 자구 미러 ───────────────────────────────────────
def embed_texts_live(model, tok, texts, bs=16):
    """embed_triples_ftv1.py = embed_triples_qwen05b.py = serve._embed_text_live 자구 미러:
    마지막 은닉 · attention-mask 평균 · 96 토큰 · fp32."""
    outs = []
    for b0 in range(0, len(texts), bs):
        batch = texts[b0:b0 + bs]
        enc = tok(batch, padding=True, truncation=True, max_length=96, return_tensors="pt")
        with torch.no_grad():
            h = model(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
        outs.append(((h * mask).sum(1) / mask.sum(1).clamp(min=1.0)).numpy().astype(np.float32))
    return np.concatenate(outs)


def ref_nn(E_tr):
    """serve.py 자구 미러 — 학습 임베딩 512 표본 최근접 거리 중앙값."""
    samp = E_tr[np.random.default_rng(0).choice(len(E_tr), size=min(512, len(E_tr)), replace=False)]
    d = np.sqrt(((samp[:, None, :] - samp[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    return float(np.median(d.min(axis=1)))


def ood_ratios(embs, E_tr, refnn, chunk=1024):
    """비율 = min 유클리드 거리(E_tr 전체) / REF_NN — serve._features_from_raw 자구 미러."""
    out = np.empty(len(embs))
    for i, e in enumerate(embs):
        dmin = np.inf
        for k in range(0, len(E_tr), chunk):
            d = np.sqrt(((E_tr[k:k + chunk] - e[None]) ** 2).sum(-1)).min()
            dmin = min(dmin, float(d))
        out[i] = dmin / max(refnn, 1e-9)
    return out


def pctiles(v):
    qs = (1, 5, 10, 25, 50, 75, 90, 95, 99)
    return {("p%02d" % q): round(float(np.percentile(v, q)), 4) for q in qs}


def cos(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


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

    epoch_stamp = assert_epoch(REG_MANIFEST_SHA)         # 부칙 4 — 불일치면 예외로 즉중단
    sha_verify = {}
    for p, want in EXPECT_SHA.items():
        got = sha16(p) if os.path.exists(p) else "없음"
        sha_verify[os.path.basename(p)] = {"기대": want, "실측": got, "일치": got == want}
    if not all(v["일치"] for v in sha_verify.values()):
        out = {"판정어": "중단 — 원천 sha 불일치 (조항 66 · 측정 없이 중단)",
               "sha 검증": sha_verify, "시작 시각": 시작, "시대(부칙 4)": epoch_stamp}
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

    # 🔴 #141 ⑥-1 코드 관문 — J‴ 금지 + J5 성분 확인(문턱 원천 선언표 기계 검사)
    o1005 = json.load(open(os.path.join(REPO, "runners/out1005_embed.json"), encoding="utf-8"))
    j5_rec = o1005[KEY_J5]
    j5_comp = j5_rec["성분"]
    jppp_used = [g for g, srcs in GATE_THRESH_SRC.items() if any("J‴" in s for s in srcs)]
    comp_ok = ("씨앗 간" in j5_comp) and ("축소 train" in j5_comp) and ("단일 대" in j5_comp)
    check_j = {"J‴ 를 문턱으로 쓰는 게이트": jppp_used if jppp_used else 0,
               "J5 성분 기재(out1005)": j5_comp,
               "성분 확인": ("일치 — 이번 비교(앙상블 대 앙상블 · 같은 축소 train · 씨앗 집합 재추첨)의 "
                        "잡음 상계로 1005 §4 와 같은 용법(관대 ≈√5 자백)" if comp_ok else "불일치"),
               "판정": "통과" if (not jppp_used and comp_ok) else "등록 결함"}
    if jppp_used or not comp_ok:
        out = {"판정어": "중단 — 등록 결함(#141 ⑥-1 · 문턱 성분) (측정 없이 중단)",
               "J‴/J5 성분 검사": check_j, "시작 시각": 시작, "시대(부칙 4)": epoch_stamp}
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return
    J5 = {k: float(v) for k, v in j5_rec.items() if k != "성분"}

    waited0 = load_gate_wait()
    o1002 = json.load(open(os.path.join(REPO, "runners/out1002_ensemble.json"), encoding="utf-8"))
    JPP = o1002[KEY_JPP]
    J2 = {d: float(JPP[d]) for d in ROSTER}
    J2_cov, J2_tot, J2_W = float(JPP["덮개율"]), float(JPP["전체"]), float(JPP["폭"])
    lb = json.load(open(os.path.join(TROUT, "leaderboard.json"), encoding="utf-8"))
    rep = json.load(open(os.path.join(TROUT, "report.json"), encoding="utf-8"))
    dep_dom = {d: float(lb["도메인별"][d]["transition"]) for d in ROSTER}
    dep_tot = float(lb["전체"]["transition"])
    dep_cover = float(rep["평가"]["90% 구간 덮개율(목표 0.90)"])
    dep_piw = float(rep["평가"]["구간 평균 폭(log)"])

    D = load_data()
    dep_raw, _man, _shas = load_ensemble()
    cf = load_conformal()
    assert cf is not None, "🔴 conformal.json 부재 — 배포 시대 전제 실패"
    dep_cal = ConformalWrap(dep_raw, cf[0])
    C05 = D["C_arm"]["base05b"]
    pred_dep_uncal = predict_rows(dep_raw, D, C05, D["va"])
    pred_dep_cal = predict_rows(dep_cal, D, C05, D["va"])
    ev_dep_uncal = eval_val(pred_dep_uncal, D)
    ev_dep_cal = eval_val(pred_dep_cal, D)

    # 앵커 A — 배포(보정) 재현 13칸 («실행 간» · ≤1.5e-4)
    anchorA, aok = {}, []
    for d in ROSTER:
        dv = abs(ev_dep_cal["per_dom"][d] - dep_dom[d])
        anchorA[d] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
        aok.append(dv <= 1.5e-4)
    for name, mine, ref in (("전체", ev_dep_cal["tot"], dep_tot),
                            ("덮개율(보정)", ev_dep_cal["cover"], dep_cover),
                            ("폭(보정)", ev_dep_cal["W"], dep_piw)):
        dv = abs(mine - ref)
        anchorA[name] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
        aok.append(dv <= 1.5e-4)
    anchorA_ok = all(aok)
    anchorA2 = {}
    for name, mine, ref in (("미보정 덮개율(=0.7530)", ev_dep_uncal["cover"], REG_DEP_UNCAL_COV),
                            ("미보정 폭(=0.5026)", ev_dep_uncal["W"], REG_DEP_UNCAL_W)):
        dv = abs(mine - ref)
        anchorA2[name] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
    anchorA2_ok = all(v["통과"] for v in anchorA2.values())

    picked, hold_rows, hold_sum, lst_sha = carve_holdout(D)
    anchorB = {"홀드아웃 개체 수(=98)": {"실측": hold_sum["홀드아웃 개체 수"],
                                 "통과": hold_sum["홀드아웃 개체 수"] == REG_HOLD_ENT},
               "홀드아웃 행 수(=1752)": {"실측": hold_sum["홀드아웃 행 수"],
                                  "통과": hold_sum["홀드아웃 행 수"] == REG_HOLD_ROWS},
               "명단 sha(=0cbc70bb8b83d579)": {"실측": lst_sha, "통과": lst_sha == REG_HOLD_SHA}}
    anchorB_ok = all(v["통과"] for v in anchorB.values())
    leak_ok = hold_sum["val 개체 겹침(누수 검사 — 0 이어야)"] == 0
    prog({"앵커A": anchorA_ok, "앵커A′": anchorA2_ok, "앵커B": anchorB_ok, "누수0": leak_ok,
          "load대기초": waited0, "시대": epoch_stamp["실측 sha"]})

    # ── 학습 10 (2팔 × 5씨앗 · 순차 · load 관문) ──────────────────────
    hold_set = set(hold_rows.tolist())
    tr_pool = np.asarray([i for i in D["tr"] if int(i) not in hold_set], dtype=np.int64)
    r_h = D["R"][hold_rows].astype(np.float64)
    arm_seed_cells, arm_ens_val, arm_ens_hold, arm_ckpts = {}, {}, {}, {}
    os.makedirs(EXP, exist_ok=True)
    for arm in ARMS:
        Carm = D["C_arm"][arm]
        preds_val, preds_hold, cells, ck = {}, {}, {}, {}
        for sd in SEEDS:
            waited = load_gate_wait()
            model, pin, sec, d_in = train_cur(sd, tr_pool, D, Carm)
            pv = predict_rows(model, D, Carm, D["va"])
            ph = predict_rows(model, D, Carm, hold_rows)
            ev = eval_val(pv, D)
            preds_val[sd], preds_hold[sd] = pv, ph
            cells[sd] = {"도메인별 MdAPE": {d: round(ev["per_dom"][d], 4) for d in ROSTER},
                         "전체 MdAPE": round(ev["tot"], 4), "90% 덮개율": round(ev["cover"], 4),
                         "구간 평균 폭(log)": round(ev["W"], 4),
                         "pinball(train)": pin, "sec": sec, "d_in": d_in, "load대기초": waited}
            cp = os.path.join(EXP, "%s_seed%d.pt" % (arm, sd))
            torch.save({"model": model.state_dict(), "d_in": d_in, "hidden": HIDDEN,
                        "text_emb": ARM_EMB[arm],
                        "레시피": "현행 레시피 · seed %d · steps 3000 · 홀드아웃 98 제외 train · "
                               "임베더 %s (사이클 1009)" % (sd, arm)}, cp)
            ck[sd] = {"경로": cp, "sha": sha16(cp)}
            prog({"팔": arm, "seed": sd, "덮개율": cells[sd]["90% 덮개율"],
                  "전체": cells[sd]["전체 MdAPE"], "sec": sec})
        arm_seed_cells[arm] = cells
        arm_ckpts[arm] = ck
        arm_ens_val[arm] = np.mean(np.stack([preds_val[sd] for sd in SEEDS]), axis=0)
        arm_ens_hold[arm] = np.mean(np.stack([preds_hold[sd] for sd in SEEDS]), axis=0)

    # ── 팔별: 미보정 평가 · δ̂ · 보정 후 평가 · Mondrian(관찰) ─────────
    arm_uncal, arm_delta, arm_cal, arm_mond, arm_dsum = {}, {}, {}, {}, {}
    dom_h = D["dom_id"][hold_rows]
    for arm in ARMS:
        u = eval_val(arm_ens_val[arm], D)
        q05h = arm_ens_hold[arm][..., 0].astype(np.float64)
        q95h = arm_ens_hold[arm][..., 4].astype(np.float64)
        scores_h = np.maximum(q05h - r_h, r_h - q95h)
        delta, ql = q_conf(scores_h.ravel())
        pa = arm_ens_val[arm].copy()
        pa[..., 0] -= delta
        pa[..., 4] += delta
        c = eval_val(pa, D)
        arm_uncal[arm], arm_delta[arm], arm_cal[arm] = u, delta, c
        arm_dsum[arm] = {"δ̂(전역 · log · 제 것 — 1004 δ 물려쓰기 금지 #141-4)": delta,
                         "q_level": round(ql, 6), "score n(행×91)": int(scores_h.size),
                         "홀드아웃 한계-덮개(전)": round(float((scores_h <= 0).mean()), 4),
                         "홀드아웃 한계-덮개(후 · δ̂ 적용)": round(float((scores_h <= delta).mean()), 4)}
        mond = {}
        for d in ROSTER:
            m = dom_h == D["domains"].index(d)
            if m.any():
                dv, _ = q_conf(scores_h[m].ravel())
                mond[d] = round(dv, 4)
        arm_mond[arm] = mond
        prog({"팔": arm, "δ̂": round(delta, 4), "val 미보정": round(u["cover"], 4),
              "val 보정": round(c["cover"], 4)})

    # ── J6 (여섯째 집합 ㉯ 신고 — base팔 단일 대 앙상블 최대차 13칸) ────
    c05 = arm_seed_cells["base05b"]
    u05 = arm_uncal["base05b"]
    J6 = {d: max(abs(c05[sd]["도메인별 MdAPE"][d] - u05["per_dom"][d]) for sd in SEEDS)
          for d in ROSTER}
    J6["전체"] = max(abs(c05[sd]["전체 MdAPE"] - u05["tot"]) for sd in SEEDS)
    J6["덮개율(미보정)"] = max(abs(c05[sd]["90% 덮개율"] - u05["cover"]) for sd in SEEDS)
    J6["폭(미보정)"] = max(abs(c05[sd]["구간 평균 폭(log)"] - u05["W"]) for sd in SEEDS)

    # ── 앵커 C — «보정 팔» 굵은 관문(v5.2 · 1005 자구): base팔 대 배포 13칸 ──
    va = D["va"]
    val_names = [D["meta"][int(i)]["개체"] for i in va]
    vuniq, vids, vgroups = cluster_groups(val_names)
    ape_dep = ev_dep_uncal["ape"].astype(np.float64)
    ape_05 = u05["ape"].astype(np.float64)
    dom_va = ev_dep_uncal["dom_va"]
    rng7 = np.random.default_rng([STAT_SEED, 7])
    anchorC, cok = {}, []
    for d in ROSTER:
        m = dom_va == D["domains"].index(d)
        A, Bv = ape_dep[m], ape_05[m]
        n_d = int(m.sum())
        idxd = rng7.integers(0, n_d, size=(N_BOOT, n_d))
        se = float((np.median(Bv[idxd], axis=1) - np.median(A[idxd], axis=1)).std(ddof=1))
        dv = abs(u05["per_dom"][d] - ev_dep_uncal["per_dom"][d])
        thr = max(J2[d], 3.0 * se)
        anchorC[d] = {"|Δ|": round(dv, 4), "문턱 max(J″,3SE행)": round(thr, 4),
                      "통과": bool(dv <= thr)}
        cok.append(dv <= thr)
    cov_dep_rows = ev_dep_uncal["cover_ent"].astype(np.float64)
    cov_05_rows = u05["cover_ent"].astype(np.float64)
    w_dep_rows = ev_dep_uncal["piw_ent"].astype(np.float64)
    w_05_rows = u05["piw_ent"].astype(np.float64)
    idxr = rng7.integers(0, len(va), size=(N_BOOT, len(va)))
    for name, Bv, A, Jx in (("전체", ape_05, ape_dep, J2_tot),
                            ("덮개율(미보정)", cov_05_rows, cov_dep_rows, J2_cov),
                            ("폭(미보정)", w_05_rows, w_dep_rows, J2_W)):
        if name == "전체":
            boot = np.median(Bv[idxr], axis=1) - np.median(A[idxr], axis=1)
            dv = abs(u05["tot"] - ev_dep_uncal["tot"])
        else:
            boot = Bv[idxr].mean(axis=1) - A[idxr].mean(axis=1)
            dv = abs(Bv.mean() - A.mean())
        se = float(boot.std(ddof=1))
        thr = max(Jx, 3.0 * se)
        anchorC[name] = {"|Δ|": round(dv, 4), "문턱 max(J″,3SE행)": round(thr, 4),
                        "통과": bool(dv <= thr)}
        cok.append(dv <= thr)
    anchorC_ok = all(cok)
    prog({"앵커C": anchorC_ok})

    # ── OOD 국면 — 프로브 3세트 × 2공간 + 앵커 D 미러 항등 ────────────
    plan_txt = [l.strip() for l in open(P_PLAN, encoding="utf-8") if l.strip()]
    far_txt = [l.strip() for l in open(P_FAR, encoding="utf-8") if l.strip()]
    assert len(plan_txt) >= 20 and len(far_txt) >= 20, "🔴 프로브 세트 크기"
    va_txts = sorted({(D["meta"][int(i)].get("텍스트") or "").strip()
                      for i in D["va"]} - {""})
    ind_idx = np.random.default_rng([STAT_SEED, 0]).choice(len(va_txts), size=N_IND, replace=False)
    ind_txt = [va_txts[int(j)] for j in ind_idx]
    mir_txt = [(D["meta"][i].get("텍스트") or "").strip() or (D["meta"][i].get("개체") or "").strip()
               for i in MIRROR_IDX]

    from transformers import AutoModel, AutoModelForCausalLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(SNAP)
    ood, mirror = {}, {}
    for arm, E_full in (("base05b", D["E_arm"]["base05b"]), ("ftv1", D["E_arm"]["ftv1"])):
        if arm == "base05b":
            enc = AutoModel.from_pretrained(SNAP, dtype=torch.float32).eval()
        else:
            sl = torch.load(FT_SLIM, map_location="cpu", weights_only=False)
            lm = AutoModelForCausalLM.from_pretrained(SNAP, dtype=torch.float32)
            lm.load_state_dict(sl["model"])
            enc = lm.model.eval()
            del sl, lm
        E_tr = E_full[D["tr"]]
        refnn = ref_nn(E_tr)
        emb_plan = embed_texts_live(enc, tok, plan_txt)
        emb_far = embed_texts_live(enc, tok, far_txt)
        emb_ind = embed_texts_live(enc, tok, ind_txt)
        emb_mir = embed_texts_live(enc, tok, mir_txt)
        mirror[arm] = {str(i): round(cos(emb_mir[j], E_full[i]), 6)
                       for j, i in enumerate(MIRROR_IDX)}
        r_plan = ood_ratios(emb_plan, E_tr, refnn)
        r_far = ood_ratios(emb_far, E_tr, refnn)
        r_ind = ood_ratios(emb_ind, E_tr, refnn)
        rngp = np.random.default_rng([STAT_SEED, 2 if arm == "ftv1" else 12])
        rngi = np.random.default_rng([STAT_SEED, 3 if arm == "ftv1" else 13])
        rngf = np.random.default_rng([STAT_SEED, 11 if arm == "ftv1" else 14])
        se_plan = float(np.median(r_plan[rngp.integers(0, len(r_plan), size=(N_BOOT, len(r_plan)))],
                                  axis=1).std(ddof=1))
        se_ind = float(np.median(r_ind[rngi.integers(0, len(r_ind), size=(N_BOOT, len(r_ind)))],
                                 axis=1).std(ddof=1))
        se_far = float(np.median(r_far[rngf.integers(0, len(r_far), size=(N_BOOT, len(r_far)))],
                                 axis=1).std(ddof=1))
        ood[arm] = {"REF_NN": round(refnn, 6),
                    "기획서": {"중앙값": float(np.median(r_plan)), "SE(문장 붓스트랩)": round(se_plan, 5),
                            "분위수": pctiles(r_plan), "n": len(r_plan),
                            "경고선(3.0) 안 문장 수": int((r_plan < THR_OPEN).sum()),
                            "문장별": [round(float(x), 3) for x in r_plan]},
                    "분포-안": {"중앙값": float(np.median(r_ind)), "SE": round(se_ind, 5),
                             "분위수": pctiles(r_ind), "n": len(r_ind)},
                    "원거리": {"중앙값": float(np.median(r_far)), "SE": round(se_far, 5),
                            "분위수": pctiles(r_far), "n": len(r_far),
                            "경고선(3.0) 위 문장 수": int((r_far > THR_FAR).sum()),
                            "문장별": [round(float(x), 3) for x in r_far]}}
        del enc, emb_plan, emb_far, emb_ind, emb_mir
        gc.collect()
        prog({"OOD": arm, "기획서 중앙값": round(ood[arm]["기획서"]["중앙값"], 4),
              "분포-안": round(ood[arm]["분포-안"]["중앙값"], 4),
              "원거리": round(ood[arm]["원거리"]["중앙값"], 4)})
    anchorD = {"base(라이브 대 저장 qwen05b · cos ≥ %.3f)" % MIRROR_COS: mirror["base05b"],
               "ft(라이브 대 저장 ftv1 · cos ≥ %.3f)" % MIRROR_COS: mirror["ftv1"]}
    anchorD_ok = all(v >= MIRROR_COS for mm in mirror.values() for v in mm.values())

    # ── 게이트 실측 ───────────────────────────────────────────────────
    g_open = float(ood["ftv1"]["기획서"]["중앙값"])
    g_ind = float(ood["ftv1"]["분포-안"]["중앙값"])
    g_far = float(ood["ftv1"]["원거리"]["중앙값"])
    g1 = bool(GATES["㉠"]["pass_fn"](g_open, THR_OPEN))
    g61 = bool(GATES["㉥1"]["pass_fn"](g_ind, THR_IND))
    g62 = bool(GATES["㉥2"]["pass_fn"](g_far, THR_FAR))

    ape_ft = arm_uncal["ftv1"]["ape"].astype(np.float64)
    delta_d = {d: arm_uncal["ftv1"]["per_dom"][d] - u05["per_dom"][d] for d in ROSTER}
    se_d, se_d_cl = {}, {}
    for k, d in enumerate(ROSTER):
        m = dom_va == D["domains"].index(d)
        A, Bv = ape_05[m], ape_ft[m]
        n_d = int(m.sum())
        rngd = np.random.default_rng([STAT_SEED, 1, k])
        idxd = rngd.integers(0, n_d, size=(N_BOOT, n_d))
        se_d[d] = float((np.median(Bv[idxd], axis=1) - np.median(A[idxd], axis=1)).std(ddof=1))
        dn = [val_names[j] for j in np.where(m)[0]]
        if len(set(dn)) >= 8:
            _du, _did, dgroups = cluster_groups(dn)
            rngdc = np.random.default_rng([STAT_SEED, 9, k])
            se_d_cl[d] = round(float(cboot(dgroups, rngdc,
                                           lambda pos, A=A, Bv=Bv: np.median(Bv[pos]) - np.median(A[pos]),
                                           B=2000).std(ddof=1)), 4)
    thr_d = {d: max(J5[d], MULT_OTHER * se_d[d]) for d in JUDGE_D}
    bad = {d: {"Δ": delta_d[d], "문턱": thr_d[d]} for d in JUDGE_D if delta_d[d] > thr_d[d]}
    g2 = bool(not bad)
    d_tot = float(arm_uncal["ftv1"]["tot"] - u05["tot"])
    rng4 = np.random.default_rng([STAT_SEED, 4])
    se_tot_cl = float(cboot(vgroups, rng4,
                            lambda pos: np.median(ape_ft[pos]) - np.median(ape_05[pos])).std(ddof=1))
    thr_tot = max(J5["전체"], 2.0 * se_tot_cl)
    g3 = bool(d_tot <= thr_tot)
    cov_f = arm_cal["ftv1"]["cover_ent"].astype(np.float64)
    cov_b = arm_cal["base05b"]["cover_ent"].astype(np.float64)
    d_cov = float(cov_f.mean() - cov_b.mean())
    rng5 = np.random.default_rng([STAT_SEED, 5])
    se_cov_cl = float(cboot(vgroups, rng5,
                            lambda pos: cov_f[pos].mean() - cov_b[pos].mean()).std(ddof=1))
    thr_cov = 2.0 * se_cov_cl                            # 🔴 J 금지(#141 ⑥) — SE 눈금 단독
    g4 = None if thr_cov <= 0 else bool(d_cov >= -thr_cov)
    w_f = arm_cal["ftv1"]["piw_ent"].astype(np.float64)
    w_b = arm_cal["base05b"]["piw_ent"].astype(np.float64)
    d_W = float(w_f.mean() - w_b.mean())
    rng6 = np.random.default_rng([STAT_SEED, 6])
    se_W_cl = float(cboot(vgroups, rng6,
                          lambda pos: w_f[pos].mean() - w_b[pos].mean()).std(ddof=1))
    thr_W = 2.0 * se_W_cl                                # 🔴 J 금지(#141 ⑥) — SE 눈금 단독
    g5 = None if thr_W <= 0 else bool(d_W <= thr_W)
    dW_base = float(arm_uncal["ftv1"]["W"] - u05["W"])
    d2d = 2.0 * (arm_delta["ftv1"] - arm_delta["base05b"])

    # ── 탐침(측정 후 · v5.3-3) ────────────────────────────────────────
    probes = {"㉠": gate_probe(GATES["㉠"]["pass_fn"], g_open, THR_OPEN, +1.0),
              "㉥1": gate_probe(GATES["㉥1"]["pass_fn"], g_ind, THR_IND, +1.0),
              "㉥2": gate_probe(GATES["㉥2"]["pass_fn"], g_far, THR_FAR, -1.0),
              "㉢": gate_probe(GATES["㉢"]["pass_fn"], d_tot, thr_tot, +1.0)}
    if g4 is not None:
        probes["㉣"] = gate_probe(GATES["㉣"]["pass_fn"], d_cov, thr_cov, -1.0)
    if g5 is not None:
        probes["㉤"] = gate_probe(GATES["㉤"]["pass_fn"], d_W, thr_W, +1.0)
    for d in JUDGE_D:
        probes["㉡ " + d] = gate_probe(GATES["㉡"]["pass_fn"], delta_d[d], thr_d[d], +1.0)
    n_m = sum(1 for p in probes.values() if not p["거짓 나옴"])
    n_n = sum(1 for p in probes.values() if not p["참 나옴"])
    n_worse = sum(1 for p in probes.values() if p["㉰ 악화 극값에서 참"])
    n_better = sum(1 for p in probes.values() if p["㉱ 개선 극값에서 거짓"])
    n_degen = sum(1 for p in probes.values() if p["퇴화 문턱(thr ≤ 0)"])
    n_dir = sum(1 for p in probes.values() if not p["방향 검사"])

    # ── #140 ⑦-6 + #141 ① — 연역 계수 + 부호 구조 ────────────────────
    ded_val = {"㉠": ood["ftv1"]["기획서"]["SE(문장 붓스트랩)"] == 0.0,
               "㉥1": ood["ftv1"]["분포-안"]["SE"] == 0.0,
               "㉥2": ood["ftv1"]["원거리"]["SE"] == 0.0,
               "㉢": se_tot_cl == 0.0,
               "㉣": (None if g4 is None else se_cov_cl == 0.0),
               "㉤": (None if g5 is None else se_W_cl == 0.0)}
    for d in JUDGE_D:
        ded_val["㉡ " + d] = se_d[d] == 0.0
    sign_cells = {"㉢": sign_structure(ape_ft - ape_05, SIGN_FORCING_CONST["㉢"]),
                  "㉣": sign_structure(cov_f - cov_b, SIGN_FORCING_CONST["㉣"]),
                  "㉤": sign_structure(w_f - w_b, SIGN_FORCING_CONST["㉤"])}
    for d in JUDGE_D:
        m = dom_va == D["domains"].index(d)
        sign_cells["㉡ " + d] = sign_structure(ape_ft[m] - ape_05[m], SIGN_FORCING_CONST["㉡"])
    n_sign_ded = sum(1 for v in sign_cells.values() if v["부호 구조 연역(1003 ㉠형)"])
    n_cells = 12
    n_deducible = sum(1 for v in ded_val.values() if v is True) + n_sign_ded
    n_nondeducible = n_cells - n_deducible
    등록어 = "판정 사이클" if n_nondeducible > 0 else "측정 사이클(#140 ⑦-6 — 연역 불가 0)"

    # ── 판정어 ────────────────────────────────────────────────────────
    open_ok = g1 and g61 and g62
    harm_ok = g2 and g3 and (g4 is None or g4) and (g5 is None or g5)
    if n_worse or n_better or n_dir:
        verdict = ("등록 결함 — 자료 탐침 ㉰ %d · ㉱ %d · 방향 위반 %d (관찰 강등 · 배포 0)"
                   % (n_worse, n_better, n_dir))
    elif not leak_ok:
        verdict = "등록 결함 — 홀드아웃-val 개체 누수 ≠ 0 (관찰 강등 · 배포 0)"
    elif not (anchorA_ok and anchorA2_ok and anchorB_ok):
        verdict = ("관찰 강등 — 앵커 불통과 (A %s · A′ %s · B %s) (배포 0)"
                   % (anchorA_ok, anchorA2_ok, anchorB_ok))
    elif not anchorC_ok:
        verdict = "관찰 강등 — 앵커 C(보정 팔 굵은 관문) 불통과 (배포 0 · 귀속 §관찰)"
    elif not anchorD_ok:
        verdict = "관찰 강등 — 앵커 D(라이브=저장 미러 항등) 불통과 (배포 0 · 조항 66 전제 실패)"
    elif open_ok and harm_ok:
        verdict = ("성공 — ft-v1 채택 · 배포 진행 + 기획서 개방 (사전등록 §6 · 커밋→집행)"
                   + ("" if (g4 is not None and g5 is not None) else " · ㉣/㉤ 일부 미판정(퇴화) 병기"))
    elif not open_ok:
        verdict = ("실패 — 개방 불성립 (배포 0 · ㉠ %s ㉥1 %s ㉥2 %s)" % (g1, g61, g62))
    else:
        verdict = "부분 — 개방 게이트 통과이나 비열화 게이트 일부 불통과 (배포 0)"

    # ── 배포 후보물 (성공 시 §6 그대로 집행) ──────────────────────────
    man_cand = {"형식": "앙상블 manifest 후보 (사이클 1009 · 임베더 ft-v1)",
                "구성원": {str(sd): {"경로": arm_ckpts["ftv1"][sd]["경로"],
                                  "sha256": arm_ckpts["ftv1"][sd]["sha"]} for sd in SEEDS},
                "결합": "분위수 텐서 (91,5) 산술 평균", "씨앗": list(SEEDS),
                "text_emb": ARM_EMB["ftv1"],
                "text_emb sha256/16": sha16(ARM_EMB["ftv1"]),
                "sao sha": sha16(os.path.join(TRI, "sao.npz")),
                "학습 제외 홀드아웃": {"개체 수": len(picked), "명단 sha256/16": lst_sha},
                "사전등록": "docs/탐색/1009.md"}
    with open(os.path.join(EXP, "manifest_candidate.json"), "w", encoding="utf-8") as f:
        json.dump(man_cand, f, ensure_ascii=False, indent=1)
    conf_cand = {"형식": "등각 보정 v2 (사이클 1009 · 무누수 홀드아웃 · 전역 · ft-v1 팔)",
                 "α": ALPHA, "δ(log)": arm_delta["ftv1"],
                 "적용": "q05 − δ · q95 + δ (q25/q50/q75 무접촉 · 잔차 log 눈금)",
                 "유효 조건": "배포 시 새 manifest sha 기입 — 소비자 대조(#140 ⑦-3 ㉰)",
                 "구성원 sha": {str(sd): arm_ckpts["ftv1"][sd]["sha"] for sd in SEEDS},
                 "홀드아웃": {"개체 수": len(picked), "행 수": int(len(hold_rows)),
                         "명단 sha256/16": lst_sha,
                         "score n": arm_dsum["ftv1"]["score n(행×91)"],
                         "q_level": arm_dsum["ftv1"]["q_level"]},
                 "잰 소스 (조항 66)": {"sao.npz": sha16(os.path.join(TRI, "sao.npz")),
                                  "text_emb_ftv1.npz": sha16(ARM_EMB["ftv1"]),
                                  "러너": sha16(os.path.abspath(__file__))},
                 "생성 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(EXP, "conformal_candidate.json"), "w", encoding="utf-8") as f:
        json.dump(conf_cand, f, ensure_ascii=False, indent=1)

    # ── 관찰 상세 ─────────────────────────────────────────────────────
    cond_cov = {"배포(1004 앙상블+δ · «전»)": {
        d: round(float(ev_dep_cal["cover_ent"][dom_va == D["domains"].index(d)].mean()), 4)
        for d in ROSTER}}
    for arm in ARMS:
        ce = arm_cal[arm]["cover_ent"]
        cond_cov[arm + "(보정 후)"] = {
            d: round(float(ce[dom_va == D["domains"].index(d)].mean()), 4) for d in ROSTER}
    idol = {}
    for arm in ARMS:
        cells = arm_seed_cells[arm]
        vals = [cells[sd]["도메인별 MdAPE"]["아이돌"] for sd in SEEDS]
        worse_n = sum(1 for v in vals if v > dep_dom["아이돌"])
        idol[arm] = {"씨앗 5(아이돌 MdAPE)": vals,
                     "앙상블": round(arm_uncal[arm]["per_dom"]["아이돌"], 4),
                     "배포(%.4f)보다 나쁜 씨앗 수" % dep_dom["아이돌"]: "%d/5" % worse_n}
    obs_wt_idol = {d: {"Δ(ft−base)": round(delta_d[d], 4), "SE(행)": round(se_d[d], 4),
                       "SE(클러스터·관찰)": se_d_cl.get(d, "미계산(유일 개체 <8)"),
                       "J5_d": round(J5[d], 4), "J5_d/√5(관대 자백 눈금)": round(J5[d] / np.sqrt(5), 4),
                       "판정 밖 사유": "1008 자 존속(웹툰 val 9 개체) · #141-7 아이돌 장부 — 관찰만"}
                   for d in OBS_ONLY}
    vs_dep = {"도메인 Δ(ft팔 − 배포)": {d: round(arm_uncal["ftv1"]["per_dom"][d] - dep_dom[d], 4)
                                   for d in ROSTER},
              "Δ전체": round(arm_uncal["ftv1"]["tot"] - dep_tot, 4),
              "Δ덮개율(보정 후 대 배포 0.9173)": round(arm_cal["ftv1"]["cover"] - dep_cover, 4),
              "Δ폭(보정 후 대 배포 0.9699)": round(arm_cal["ftv1"]["W"] - dep_piw, 4)}

    out = {
        "러너": "runners/embed1009.py",
        "표적": "개방 — 기획서 문체 OOD(ft-v1 공간) 가드 경고선 안 진입 · 비열화 게이트 동반",
        "시작 시각": 시작,
        "시대(부칙 4 — assert_epoch 반환값)": epoch_stamp,
        "합성 방향 탐침(측정 전 · v5.3-2)": pre_probe,
        "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
        "sha 검증(사전등록 대조)": sha_verify,
        "러너 자신": sha16(os.path.abspath(__file__)),
        "재임베딩 sha 사슬(#139 ⑦-1 · 과업 지시)": {
            "ft-v1 ckpt": {"경로": FT_CKPT, "sha": sha_verify["latest.pt"]["실측"]},
            "slim(모형만 추출 · 항등)": {"경로": FT_SLIM, "sha": sha_verify["model_slim_fp32.pt"]["실측"]},
            "emb npz": {"경로": ARM_EMB["ftv1"], "sha": sha_verify["text_emb_ftv1.npz"]["실측"]},
            "생성 코드": {"경로": os.path.join(ART, "ft", "embed_triples_ftv1.py"),
                      "sha": sha_verify["embed_triples_ftv1.py"]["실측"]},
            "원천 meta.jsonl sha": sha_verify["meta.jsonl"]["실측"],
            "행 수 항등(10,654 = meta = sao)": bool(len(D["meta"]) == REG_META_ROWS),
            "d(=896 유지)": REG_D,
            "규약": "현행 학습 미러와 동일 — 마지막 은닉 mask 평균 · 96tok · fp32 (조항 66 · "
                  "앵커 D 가 cos 로 실측)"},
        "J‴/J5 성분 검사(#141 ⑥-1 코드 관문)": check_j,
        "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
               "학습 씨앗(여섯째)": list(SEEDS), "통계 씨앗": STAT_SEED, "α": ALPHA,
               "threads": torch.get_num_threads(), "device": "cpu",
               "B": {"붓스트랩": N_BOOT},
               "판정 눈금": "㉠㉥ = 프로브 문장 붓스트랩 SE 병기(문턱은 등록 상수) · ㉢㉣㉤ = val "
                        "개체(70) 클러스터 SE · ㉡ = 행 SE(도메인 클러스터 3~16 퇴화 사유 · "
                        "1004 §4 승계 · 클러스터 SE 관찰 병기)",
               "짝지은 설계": "두 팔이 같은 씨앗·같은 tr_pool·같은 배치 행(rng[seed,step])으로 학습 — "
                         "차이는 조건 입력(임베더 가중치)뿐"},
        "홀드아웃 구성(로스터 재현 · 관찰 6칸)": hold_sum,
        "앵커 A (배포 보정 재현 13칸 · «실행 간» · ≤1.5e-4)": dict(
            anchorA, 통과=bool(anchorA_ok), 성분="같은 모형·자료·코드 경로 재실행 — 재추첨 0"),
        "앵커 A′ (배포 미보정 재현 2칸)": dict(anchorA2, 통과=bool(anchorA2_ok)),
        "앵커 B (로스터 재현 3칸)": dict(anchorB, 통과=bool(anchorB_ok)),
        "앵커 C (보정 팔 굵은 관문 · v5.2 · 13칸)": dict(
            anchorC, 통과=bool(anchorC_ok),
            성분="🔴 J″(1002)는 «씨앗 간 · 단일 눈금 · 원 train» — 이번 비교(앙상블 · 축소 train)의 "
               "상계로 «관대»함을 알고 쓰는 굵은 설정 관문(v5.2 ㉮ · 1005 자구) · 3×SE^행 병용"),
        "앵커 D (라이브=저장 미러 항등 16칸 · cos ≥ 0.999 · 조항 66)": dict(
            anchorD, 통과=bool(anchorD_ok)),
        "씨앗별 결과 (관찰 130칸 = 2팔×5씨앗×13)": {arm: {str(sd): arm_seed_cells[arm][sd]
                                                 for sd in SEEDS} for arm in ARMS},
        "체크포인트 (저장소 밖 · 조항 73-마)": {arm: {str(sd): arm_ckpts[arm][sd] for sd in SEEDS}
                                      for arm in ARMS},
        "팔별 앙상블 미보정 val (관찰 26칸)": {arm: summarize(arm_uncal[arm]) for arm in ARMS},
        "팔별 보정 후 val (관찰 4칸)": {arm: {"90% 덮개율": round(arm_cal[arm]["cover"], 4),
                                       "구간 평균 폭(log)": round(arm_cal[arm]["W"], 4)}
                                for arm in ARMS},
        "팔별 δ̂ 요약 (관찰 10칸)": arm_dsum,
        "Mondrian δ_d (관찰 20칸 · 적용·배포·조건부 δ 등록 금지 — #141-3)": arm_mond,
        "도메인 조건부 val 덮개 (관찰 30칸 · #141-2 의무)": cond_cov,
        "아이돌 계통 악화 장부 (#141-7 · 관찰 14칸)": idol,
        "웹툰·아이돌 관찰(판정 밖 — 1008 자 존속 · 과업 지시)": obs_wt_idol,
        "ft팔 대 배포 (참고 관찰 13칸)": vs_dep,
        "J6 (여섯째 집합 ㉯ — 다음 앵커 정본 신고 · 관찰 13칸)": dict(
            {k: round(v, 4) for k, v in J6.items()},
            성분="«씨앗 간(여섯째 집합 1501~1505) · 축소 train(홀드아웃 98 제외) · 단일 대 (같은 팔) "
               "앙상블» — 앙상블 간 재추첨 지터의 상계(관대 ≈√5)임을 알고 신고"),
        "OOD 실측 (3세트 × 2공간 · serve 자구 미러)": ood,
        "헤드라인(㉠ 주대비 · 조항 79)": {
            "기획서 OOD 중앙값(ft)": g_open, "문턱(등록 상수 — 현행 가드 경고선)": THR_OPEN,
            "기획서 OOD 중앙값(base · «전» 관찰)": float(ood["base05b"]["기획서"]["중앙값"]),
            "분포-안(base→ft)": [float(ood["base05b"]["분포-안"]["중앙값"]),
                              float(ood["ftv1"]["분포-안"]["중앙값"])],
            "원거리(base→ft)": [float(ood["base05b"]["원거리"]["중앙값"]),
                             float(ood["ftv1"]["원거리"]["중앙값"])],
            "SE(문장 붓스트랩 · [11009,2])": ood["ftv1"]["기획서"]["SE(문장 붓스트랩)"],
            "중앙값+2SE < 3.0 (엄격 참고 · 관찰)": bool(
                g_open + 2 * ood["ftv1"]["기획서"]["SE(문장 붓스트랩)"] < THR_OPEN),
            "🔴 판정어 층의 연역 불가능 칸 수(#140 ⑦-6 + #141 ①)": "%d/%d → 등록어 = %s" % (
                n_nondeducible, n_cells, 등록어)},
        "Δ·SE 표 (ft − base · 관찰 26칸)": {
            **{d: {"Δ": round(delta_d[d], 4), "SE(행)": round(se_d[d], 4),
                   "SE(클러스터·관찰)": se_d_cl.get(d, "미계산(유일 개체 <8)"),
                   "J5_d": round(J5[d], 4)} for d in ROSTER},
            "전체": {"Δ": round(d_tot, 4), "SE^cl": round(se_tot_cl, 5), "J5": round(J5["전체"], 4)},
            "덮개율(보정)": {"Δ": round(d_cov, 4), "SE^cl": round(se_cov_cl, 5)},
            "폭(보정)": {"Δ": round(d_W, 4), "SE^cl": round(se_W_cl, 5)}},
        "폭 분해 (관찰 3칸)": {"Δ폭(보정)": round(d_W, 6),
                         "ΔW_base(미보정 기저)": round(dW_base, 6),
                         "Δ2δ̂(지불 차)": round(d2d, 6)},
        "연역 계수 (#140 ⑦-6 값 + #141 ① 부호 구조 · 관찰 2칸)": {
            "값 연역(SE=0·등록상수 문턱)": {k: v for k, v in ded_val.items()},
            "부호 구조(짝 대비 게이트만 — ㉠㉥ 는 비대비 · 자백 각주)": sign_cells,
            "부호 구조 연역 칸": n_sign_ded, "연역 가능 합": n_deducible,
            "연역 불가능": n_nondeducible, "등록어": 등록어,
            "자백 각주": "㉠㉥ 문턱은 등록 상수이나 관측값은 등록-후 재임베딩·라이브 임베딩 실측 — "
                     "등록-전 실측 0(값·부호 연역 불가)"},
        "판정 (사전등록 §4 · 판정 12칸 · 비반올림 집행 · 여유 = 판정 갈린 원값)": {
            "앵커 A": bool(anchorA_ok), "앵커 A′": bool(anchorA2_ok),
            "앵커 B": bool(anchorB_ok), "앵커 C": bool(anchorC_ok), "앵커 D": bool(anchorD_ok),
            "㉠ 기획서 개방(악화=상승 · 통과=경고선 안)": {
                "통과": g1, "중앙값(ft · 원값)": g_open, "문턱": THR_OPEN,
                "여유(원값 · 문턱−실측 · 양수=통과)": THR_OPEN - g_open},
            "㉥1 분포-안 유지(악화=상승)": {
                "통과": g61, "중앙값(ft · 원값)": g_ind, "문턱": THR_IND,
                "여유(원값)": THR_IND - g_ind},
            "㉥2 원거리 분별 유지(악화=하락)": {
                "통과": g62, "중앙값(ft · 원값)": g_far, "문턱": THR_FAR,
                "여유(원값 · 실측−문턱 · 양수=통과)": g_far - THR_FAR,
                "반대쪽 극단(더 멀어짐 +)": "관찰 신고 자리(v5.3-1)"},
            "㉡ 타 도메인 유의 악화(판정 6 · 악화=상승)": {
                "통과": g2, "걸린 도메인": bad if bad else "없음(0/6)",
                "여유(원값 · Δ_d − 문턱)": {d: delta_d[d] - thr_d[d] for d in JUDGE_D},
                "🔴 자 관대성 신고(#141 ⑤)": "J5_d 는 «단일 씨앗» 지터 — 앙상블(잡음 ≈1/√5) 대비엔 "
                                      "구조적으로 관대 · 참고 눈금 J5_d/√5 병기(관찰)",
                "J5_d/√5(참고)": {d: round(J5[d] / np.sqrt(5), 4) for d in JUDGE_D}},
            "㉢ 전체 비악화(악화=상승)": {"통과": g3, "Δ전체(원값)": d_tot, "문턱": thr_tot,
                                "여유(원값)": d_tot - thr_tot},
            "㉣ 덮개율 비악화(악화=하락 · J 금지 #141 ⑥)": (
                {"판정": "미판정(퇴화 — thr ≤ 0)"} if g4 is None else
                {"통과": g4, "Δ덮개율(원값)": d_cov, "문턱(−2×SE^cl)": -thr_cov,
                 "여유(원값 · Δ−(−문턱) · 양수=통과)": d_cov + thr_cov,
                 "과잉 쪽 관찰(v5.3-1 반대 극단)": "Δ>0 은 ㉤ 폭이 무는 자리 — 관찰"}),
            "㉤ 폭 한도(악화=초과 · J 금지 #141 ⑥)": (
                {"판정": "미판정(퇴화 — thr ≤ 0)"} if g5 is None else
                {"통과": g5, "Δ폭(원값)": d_W, "문턱(2×SE^cl)": thr_W, "여유(원값)": d_W - thr_W}),
            "게임·만화(관찰 — n_val 5·6행)": {d: {"Δ": round(delta_d[d], 4),
                                          "SE(행)": round(se_d[d], 4)} for d in SMALL}},
        "조항 78 탐침 (측정 후 · v5.3-3 + ㉰㉱)": dict(
            probes, 계수={"㉮ 원리상 못 떨어짐(격자)": n_m, "㉯ 원리상 못 통과(격자)": n_n,
                        "㉰ 악화 극값에서 참": n_worse, "㉱ 개선 극값에서 거짓": n_better,
                        "퇴화 문턱": n_degen, "방향 검사 위반": n_dir}),
        "판정어": verdict,
        "배포 후보(성공 시 §6 그대로 · ft-v1 팔)": {
            "manifest_candidate.json": {"경로": os.path.join(EXP, "manifest_candidate.json"),
                                        "sha": sha16(os.path.join(EXP, "manifest_candidate.json"))},
            "conformal_candidate.json": {"경로": os.path.join(EXP, "conformal_candidate.json"),
                                         "sha": sha16(os.path.join(EXP, "conformal_candidate.json"))},
            "δ̂(ft)": arm_delta["ftv1"]},
        "관찰 분모 신고(조항 79)": (
            "대비 주장 1(㉠ 기획서 OOD ft 중앙값) · 판정 12(㉠1 ㉥2 ㉡6 ㉢1 ㉣1 ㉤1) · 관찰 ≈438 = "
            "앵커 47(A13+A′2+B3+C13+D16) + 로스터 6 + 씨앗별 130 + 팔별 미보정 26 + 보정 4 + "
            "δ̂ 10 + Mondrian 20 + 조건부 덮개 30 + 아이돌 14 + 웹툰·아이돌 병기 6(중복 계상 제외) + "
            "ft대배포 13 + J6 13 + OOD 66(3세트×2공간×11) + REF_NN 2 + 헤드라인 10 + Δ·SE 26 + "
            "폭 분해 3 + 연역 2 + 성분 검사 2 + 게임·만화 4 + 문장 계수 4 · 배포 시 LODO += 10 · "
            "재보정 3 · serve 미러 재검 8"),
        "총소요초": round(time.time() - t_all, 1),
        "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict,
                      "㉠ 기획서 OOD(base→ft)": [round(float(ood["base05b"]["기획서"]["중앙값"]), 3),
                                            round(g_open, 3)],
                      "㉥1 분포-안(ft)": round(g_ind, 3), "㉥2 원거리(ft)": round(g_far, 3),
                      "㉡": g2, "Δ전체": round(d_tot, 4), "Δ덮개": round(d_cov, 4),
                      "Δ폭": round(d_W, 4), "연역 불가": "%d/12" % n_nondeducible,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
