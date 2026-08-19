# -*- coding: utf-8 -*-
"""확증 1005 러너 — 임베더 3파전: 없음 / Qwen2.5-0.5B(896d · 현행) / Qwen3-Embedding-4B(2560d)
(사전등록 docs/탐색/1005.md 에서 언 코드 · 루프 v5.3 동결 · 티처 #139 ⑦ + #141 ①~⑦ 반영).

주대비 «하나»(조항 79): Δ웹툰 = MdAPE_웹툰(4B팔 앙상블) − MdAPE_웹툰(0.5B팔 앙상블) —
q50 은 등각 보정 무접촉이라 보정 전후 동일값(명기). 세 팔 전부: 같은 축소 train(1004 홀드아웃
98 개체 제외 · 명단 sha 0cbc70bb8b83d579 재현 강제) · 다섯째 학습 씨앗 집합 1401~1405 ·
분위수 텐서 산술 평균 앙상블 · 팔마다 «제» δ̂(홀드아웃 CQR — 1004 δ +0.2336 물려쓰기 금지
#141-4) · val 평가. 비교는 «앙상블 대 앙상블»(#139 ⑦-3).

판정 11칸(㉠1 ㉡7 ㉢1 ㉣1 ㉤1 · 비반올림 집행):
  앵커A  배포(1004 앙상블+δ) 재현 항등 13칸 ≤ 1.5e-4 («실행 간»)
  앵커A′ 배포 «미보정» 재현 2칸(덮개 0.7530 · 폭 0.5026 — out1004 관찰값 · «실행 간»)
  앵커B  홀드아웃 로스터 재현 3칸(98 개체 · 1,752 행 · 명단 sha 0cbc70bb8b83d579)
  앵커C  «보정 팔» 굵은 관문(v5.2) 13칸: |0.5B팔 앙상블 − 배포(미보정)| ≤ max(J″_x, 3×SE_x^행)
         성분 신고: J″ 는 «씨앗 간 · 단일 눈금»(1002 정본) — 앙상블 재추첨의 상계(관대·굵은 관문 취지)
  ㉠  Δ웹툰 < −max(J5_웹툰, 2×SE^cl_웹툰)                       [악화 = 상승(+) · 판정 눈금 = 클러스터(9 개체)]
  ㉡  타 7 도메인 Δ_d ≤ max(J5_d, 2.6×SE_d^행) 인 곳 0          [악화 = 상승(+) · 게임·만화 관찰]
  ㉢  Δ전체 ≤ +max(J5_전체, 2×SE^cl)                            [악화 = 상승(+)]
  ㉣  Δ덮개율(보정 후) ≥ −2×SE^cl_cov  (🔴 J‴·J5 금지 — #141 ⑥) [악화 = 하락(−) · 과잉 쪽은 관찰]
  ㉤  Δ폭(보정 후 총폭) ≤ +2×SE^cl_폭  (🔴 J‴·J5 금지 — #141 ⑥) [악화 = 초과(+)]
J5_x(이번 실측·보정 팔 ㉯): max_{s∈1401..1405}|셀(0.5B팔 s 단일) − 셀(0.5B팔 앙상블)| —
성분 «씨앗 간(다섯째) · 축소 train · 단일 대 앙상블» — 다음 사이클 앵커 정본으로 신고.
🔴 #141 ⑥-1 코드 관문: J‴(out1004 · 성분 «씨앗 간+train 축소» 합성)을 문턱으로 쓰는 게이트가
   있으면 성분 대조 — 이번 등록은 J‴ 사용 0 을 기계로 확인(불일치면 측정 없이 등록 결함 중단).
🔴 #141 ① 연역 계수 보강: 값 연역(SE=0·등록상수 문턱) + «부호 구조 연역»(행 차 상수 항등 ·
   전행 동부호 + 그 부호를 강제한 등록-전 상수 유무 — 선언 맵) 둘 다 기계 게재.
🔴 v5.3-2 측정-«전» 합성 방향 탐침(t=1) — 어긋나면 측정 없이 중단.

🔴 CPU 전용 4스레드 · 유료 API 0 · MPS 0 · 학습 15(3팔×5씨앗 · 순차 · 각 학습 전 load1>10
이면 60초 대기 반복) · 배포 파일 무변경(읽기만) · 씀: python3 runners/embed1005.py
"""
import hashlib
import itertools
import json
import os
import sys
import time

import numpy as np
import torch

sys.path.insert(0, "/Users/ax/world_model")
from pretrain.transition import Transition, pinball, load_ensemble, load_conformal, ConformalWrap  # noqa: E402

torch.set_num_threads(4)
SEEDS = (1401, 1402, 1403, 1404, 1405)   # 🔴 다섯째 집합 — 997·1001~1005·1101~1105·1201~1205·1301~1305 금지 이행
STAT_SEED = 11005                        # 🔴 신규 통계 스트림 — 11001~11004 재사용 금지
CARVE_SEED = [11004, 0]                  # 🔴 로스터 «재현» 전용(새 뽑기 아님) — 명단 sha 일치 강제(앵커 B)
N_BOOT = 10000
ALPHA = 0.10
TARGET = 0.90
HOLD_FRAC = 0.15
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
SMALL = ("게임", "만화")                  # n_val 5·6 행 — ㉡ 판정 제외(관찰)
TGT = "웹툰"                              # 표적 — ㉠ 전용(㉡ 에서 제외)
JUDGE_D = tuple(d for d in ROSTER if d not in SMALL and d != TGT)   # ㉡ 7 도메인
MULT_OTHER = 2.6
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

REG_HOLD_ENT = 98
REG_HOLD_ROWS = 1752
REG_HOLD_SHA = "0cbc70bb8b83d579"        # 1004 manifest·conformal 기재 명단 sha
REG_DEP_UNCAL_COV = 0.7530               # out1004 「신 앙상블 미보정 val」 관찰값
REG_DEP_UNCAL_W = 0.5026
REG_META_ROWS = 10654                    # 행 수 항등(#139 ⑦-1)
REG_D4B = 2560

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "embed1005")
OUT_JSON = os.path.join(REPO, "runners", "out1005_embed.json")

ARMS = ("없음", "qwen05b", "qwen3e4b")
ARM_EMB = {"없음": None,
           "qwen05b": os.path.join(TRI, "text_emb_qwen05b.npz"),
           "qwen3e4b": os.path.join(TRI, "text_emb_qwen3e4b.npz")}

EXPECT_SHA = {
    os.path.join(TROUT, "ensemble_manifest.json"): "3a5c2543a55f1dab",
    os.path.join(TROUT, "conformal.json"): "d8f40489c9341302",
    os.path.join(TROUT, "leaderboard.json"): "f15a9907fb3ef6b9",
    os.path.join(TROUT, "report.json"): "6dfb0a4ff2935de0",
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "meta.jsonl"): "f74f94235bc5f032",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
    os.path.join(TRI, "text_emb_qwen3e4b.npz"): "074624894b1305d3",       # 🔴 재임베딩 sha 사슬(#139 ⑦-1)
    os.path.join(TRI, "text_emb_qwen3e4b.config.json"): "efd2249673c00056",
    os.path.join(ART, "ft", "embed_triples_qwen3e4b.py"): "f9215467dd00632e",  # 생성 코드
    os.path.join(REPO, "runners/out1002_ensemble.json"): "bad5616b2561a21f",   # J″ 정본(앵커 C)
    os.path.join(REPO, "runners/out1004_holdout.json"): "0a28715ab5632f50",    # J‴ 성분 검사 원천 + 전판 관찰
    os.path.join(REPO, "data/lab/1004_판_후.json"): "3e15be59bd3ea749",        # 전판
}
KEY_JPP = "J″_d (셋째 씨앗 5 |Δ리더보드| 최대 · 1001 J′ 와 같은 정의 — 다음 앵커 정본 신고 · ㉯)"
KEY_JPPP = "J‴ (넷째 씨앗 5 |Δ배포 리더보드| 최대 — 다음 앵커 정본 신고 · ㉯ · 관찰 13칸)"

# 🔴 #141 ⑥-1 — 게이트별 문턱 원천 선언(코드 관문이 검사): J‴ 는 어디에도 없어야 한다
GATE_THRESH_SRC = {"㉠": ("J5", "2×SE^cl"), "㉡": ("J5", "2.6×SE^행"), "㉢": ("J5", "2×SE^cl"),
                   "㉣": ("2×SE^cl",), "㉤": ("2×SE^cl",)}
# 🔴 #141 ① — 부호 구조 연역 선언 맵: 게이트 부호를 강제하는 «등록-전 상수» 유무
SIGN_FORCING_CONST = {"㉠": None, "㉡": None, "㉢": None, "㉣": None, "㉤": None}
# (이번 설계는 전 게이트가 등록-후 15 학습 산출에 의존 — 강제 상수 없음. 1003 ㉠형이면 여기 δ 가 선다)


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


# ── 게이트 함수 + 부호 서명 (v5.3-1) ──────────────────────────────────
GATES = {
    "㉠": {"pass_fn": lambda x, t: x < -t, "worse_sign": +1.0,
          "악화 한 줄": "4B팔의 웹툰 누적 90일 중앙 예측 오차(MdAPE)가 0.5B팔보다 «오르면»(+) — 더 큰 "
                    "임베더가 표적 도메인 점 예측을 되레 망친 것 — 악화. 통과는 «유의 개선»(Δ<−문턱)만"},
    "㉡": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "그 도메인의 누적 90일 중앙 예측 오차가 «오르면»(+) 임베더 교체가 남의 도메인을 "
                    "해친 것 — 악화 (재학습 실측정 게이트 — 항등 아님)"},
    "㉢": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "전체 MdAPE 가 «오르면»(+) 웹툰 개선을 전역 점 예측으로 사는 것 — 악화 "
                    "(한도는 이 문턱 · 넘으면 「부분」)"},
    "㉣": {"pass_fn": lambda x, t: x >= -t, "worse_sign": -1.0,
          "악화 한 줄": "4B팔의 val 90% 덮개율이 0.5B팔보다 유의하게 «내리면»(−) 제 δ̂ 로도 구간 약속을 "
                    "못 지키는 것 — 악화. 과잉 쪽(+)은 폭(㉤)이 물므로 여기선 관찰 신고(v5.3-1 반대쪽 극단)"},
    "㉤": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "같은 0.90 약속을 사는 값(보정 후 구간 평균 로그 폭)이 0.5B팔보다 유의하게 "
                    "«넓으면»(+) — 기저 폭이든 δ̂ 지불이든 — 정보 없는 부풀리기로 산 것 — 악화"},
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
    worse_true = bool(vals["악화 극값"])
    better_false = bool(not vals["개선 극값"])
    direction = (not vals["악화 극값"]) and vals["개선 극값"]
    return {"격자": {name: round(x, 6) for name, x in grid}, "통과값(참=통과)": vals,
            "참 나옴": any(vals.values()), "거짓 나옴": not all(vals.values()),
            "㉰ 악화 극값에서 참": worse_true, "㉱ 개선 극값에서 거짓": better_false,
            "퇴화 문턱(thr ≤ 0)": bool(thr <= 0), "방향 검사": bool(direction)}


def sign_structure(diffs, gate, forcing):
    """#141 ① — 부호 구조 검사: ㉮ 행 차가 «상수»면 구조 항등(1003 ㉣형) ·
    ㉯ 전행 동부호이고 그 부호를 강제한 등록-전 상수가 선언돼 있으면 부호 구조 연역(1003 ㉠형)."""
    d = np.asarray(diffs, dtype=np.float64)
    const = bool(len(d) > 0 and float(d.max() - d.min()) == 0.0)
    npos, nneg, nzero = int((d > 0).sum()), int((d < 0).sum()), int((d == 0).sum())
    onesided = bool((npos == 0) or (nneg == 0))
    forced = bool(onesided and forcing is not None)
    return {"행 차 상수 항등(1003 ㉣형)": const, "행 동부호(+/−/0)": "%d/%d/%d" % (npos, nneg, nzero),
            "단측 구조": onesided, "부호 강제 등록-전 상수": forcing if forcing else "없음(선언 맵)",
            "부호 구조 연역(1003 ㉠형)": forced or const}


# ── 자료 (999~1004 러너와 자구까지 같은 전처리 · 팔별 C) ──────────────
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
    C_arm = {}
    for arm in ARMS:
        if ARM_EMB[arm] is None:
            C_arm[arm] = C_common
        else:
            E = np.load(ARM_EMB[arm])["E"].astype(np.float32)
            assert len(E) == len(S) == len(meta) == REG_META_ROWS, \
                "🔴 행 수 항등 실패(#139 ⑦-1): E %d · S %d · meta %d" % (len(E), len(S), len(meta))
            if arm == "qwen3e4b":
                assert E.shape[1] == REG_D4B, "🔴 4B 차원 불일치: %d ≠ %d" % (E.shape[1], REG_D4B)
            C_arm[arm] = np.concatenate([C_common, E], axis=1).astype(np.float32)
    return {"S": S, "base": base, "Sc": Sc, "R": R, "dom_id": dom_id, "split": split,
            "C_arm": C_arm, "domains": domains, "meta": meta,
            "tr": np.where(split == 0)[0], "va": np.where(split == 1)[0]}


def carve_holdout(D):
    """1004 로스터 «재현» — seed [11004,0] · 15% 층화 · 명단 sha 일치 강제(앵커 B)."""
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
    세 팔이 «같은 행»을 뽑아 학습한다(짝지은 설계 — 사전등록 §2)."""
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

    # 🔴 #141 ⑥-1 코드 관문 — J‴ 성분 검사: 게이트 문턱 원천에 J‴ 이 있으면 성분 대조 · 이번은 0 확인
    o1004 = json.load(open(os.path.join(REPO, "runners/out1004_holdout.json"), encoding="utf-8"))
    jppp_comp = o1004[KEY_JPPP]["성분"]
    jppp_used = [g for g, srcs in GATE_THRESH_SRC.items() if any("J‴" in s for s in srcs)]
    check_jppp = {"out1004 J‴ 성분 기재": jppp_comp,
                  "J‴ 를 문턱으로 쓰는 게이트": jppp_used if jppp_used else 0,
                  "판정": "통과 — J‴ 사용 0 (#141 ⑥ 금지 이행)" if not jppp_used else
                          "등록 결함 — J‴ 성분 «씨앗 간+train 축소» 합성은 이 비교(앙상블 대 앙상블 · "
                          "같은 축소 train)와 성분 불일치"}
    if jppp_used:
        out = {"판정어": "중단 — 등록 결함(#141 ⑥-1 · J‴ 성분 불일치 · 측정 없이 중단)",
               "J‴ 성분 검사": check_jppp, "시작 시각": 시작}
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False))
        return

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
    C05 = D["C_arm"]["qwen05b"]
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
    # 앵커 A′ — 배포 «미보정» 재현 2칸 (out1004 관찰값 · «실행 간»)
    anchorA2 = {}
    for name, mine, ref in (("미보정 덮개율(=0.7530)", ev_dep_uncal["cover"], REG_DEP_UNCAL_COV),
                            ("미보정 폭(=0.5026)", ev_dep_uncal["W"], REG_DEP_UNCAL_W)):
        dv = abs(mine - ref)
        anchorA2[name] = {"|Δ|": round(dv, 6), "통과": bool(dv <= 1.5e-4)}
    anchorA2_ok = all(v["통과"] for v in anchorA2.values())

    # 앵커 B — 홀드아웃 로스터 재현 3칸
    picked, hold_rows, hold_sum, lst_sha = carve_holdout(D)
    anchorB = {"홀드아웃 개체 수(=98)": {"실측": hold_sum["홀드아웃 개체 수"],
                                 "통과": hold_sum["홀드아웃 개체 수"] == REG_HOLD_ENT},
               "홀드아웃 행 수(=1752)": {"실측": hold_sum["홀드아웃 행 수"],
                                  "통과": hold_sum["홀드아웃 행 수"] == REG_HOLD_ROWS},
               "명단 sha(=0cbc70bb8b83d579)": {"실측": lst_sha, "통과": lst_sha == REG_HOLD_SHA}}
    anchorB_ok = all(v["통과"] for v in anchorB.values())
    leak_ok = hold_sum["val 개체 겹침(누수 검사 — 0 이어야)"] == 0
    prog({"앵커A": anchorA_ok, "앵커A′": anchorA2_ok, "앵커B": anchorB_ok, "누수0": leak_ok,
          "load대기초": waited0})

    # ── 학습 15 (3팔 × 5씨앗 · 순차 · load 관문) ──────────────────────
    hold_set = set(hold_rows.tolist())
    tr_pool = np.asarray([i for i in D["tr"] if int(i) not in hold_set], dtype=np.int64)
    r_h = D["R"][hold_rows].astype(np.float64)
    arm_seed_cells, arm_ens_val, arm_ens_hold, arm_ckpts = {}, {}, {}, {}
    arm_seed_ape_tgt = {}
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
                               "임베더 %s (사이클 1005)" % (sd, arm)}, cp)
            ck[sd] = {"경로": cp, "sha": sha16(cp)}
            prog({"팔": arm, "seed": sd, "덮개율": cells[sd]["90% 덮개율"],
                  "웹툰": cells[sd]["도메인별 MdAPE"]["웹툰"], "sec": sec})
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
              "val 보정": round(c["cover"], 4), "웹툰": round(u["per_dom"]["웹툰"], 4)})

    # ── J5 (보정 팔 ㉯ — 0.5B팔 씨앗 지터 · 단일 대 앙상블) ────────────
    c05 = arm_seed_cells["qwen05b"]
    u05 = arm_uncal["qwen05b"]
    J5 = {d: max(abs(c05[sd]["도메인별 MdAPE"][d] - u05["per_dom"][d]) for sd in SEEDS)
          for d in ROSTER}
    J5["전체"] = max(abs(c05[sd]["전체 MdAPE"] - u05["tot"]) for sd in SEEDS)
    J5["덮개율(미보정)"] = max(abs(c05[sd]["90% 덮개율"] - u05["cover"]) for sd in SEEDS)
    J5["폭(미보정)"] = max(abs(c05[sd]["구간 평균 폭(log)"] - u05["W"]) for sd in SEEDS)

    # ── 앵커 C — «보정 팔» 굵은 관문(v5.2): 0.5B팔 대 배포 13칸 ────────
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

    # ── ㉠ 주대비 — Δ웹툰(4B − 0.5B) · 클러스터(9 개체) 눈금 · 정확 순열 ──
    ape_4b = arm_uncal["qwen3e4b"]["ape"].astype(np.float64)
    m_tgt = dom_va == D["domains"].index(TGT)
    At, Bt = ape_05[m_tgt], ape_4b[m_tgt]                # 0.5B · 4B (같은 60 행 — 짝)
    tgt_names = [val_names[j] for j in np.where(m_tgt)[0]]
    tuniq, tids, tgroups = cluster_groups(tgt_names)
    d_tgt = float(np.median(Bt) - np.median(At))
    rng2 = np.random.default_rng([STAT_SEED, 2])
    se_tgt_cl = float(cboot(tgroups, rng2,
                            lambda pos: np.median(Bt[pos]) - np.median(At[pos])).std(ddof=1))
    rng8 = np.random.default_rng([STAT_SEED, 8])
    idxt = rng8.integers(0, len(At), size=(N_BOOT, len(At)))
    se_tgt_row = float((np.median(Bt[idxt], axis=1) - np.median(At[idxt], axis=1)).std(ddof=1))
    # 정확 순열: 9 클러스터 × 2^9 = 512 전수(팔 라벨 클러스터 교환 · 한쪽꼬리 개선=Δ 하락)
    n_cl_t = len(tgroups)
    stats_perm = np.empty(2 ** n_cl_t)
    for bi, bits in enumerate(itertools.product([0, 1], repeat=n_cl_t)):
        flip = np.asarray(bits, dtype=bool)[tids]
        ap = np.where(flip, Bt, At)
        bp = np.where(flip, At, Bt)
        stats_perm[bi] = np.median(bp) - np.median(ap)
    p_exact = float((stats_perm <= d_tgt).sum() / len(stats_perm))
    thr_t = max(J5[TGT], 2.0 * se_tgt_cl)
    g1 = bool(d_tgt < -thr_t)
    ent_a = np.asarray([np.median(At[g]) for g in tgroups])
    ent_b = np.asarray([np.median(Bt[g]) for g in tgroups])

    # ── ㉡ 7 도메인 · ㉢ 전체 · ㉣ 덮개 · ㉤ 폭 (4B − 0.5B) ───────────
    delta_d = {d: arm_uncal["qwen3e4b"]["per_dom"][d] - u05["per_dom"][d] for d in ROSTER}
    se_d, se_d_cl = {}, {}
    for k, d in enumerate(ROSTER):
        m = dom_va == D["domains"].index(d)
        A, Bv = ape_05[m], ape_4b[m]
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
    d_tot = float(arm_uncal["qwen3e4b"]["tot"] - u05["tot"])
    rng4 = np.random.default_rng([STAT_SEED, 4])
    se_tot_cl = float(cboot(vgroups, rng4,
                            lambda pos: np.median(ape_4b[pos]) - np.median(ape_05[pos])).std(ddof=1))
    thr_tot = max(J5["전체"], 2.0 * se_tot_cl)
    g3 = bool(d_tot <= thr_tot)
    cov4 = arm_cal["qwen3e4b"]["cover_ent"].astype(np.float64)
    cov5 = arm_cal["qwen05b"]["cover_ent"].astype(np.float64)
    d_cov = float(cov4.mean() - cov5.mean())
    rng5 = np.random.default_rng([STAT_SEED, 5])
    se_cov_cl = float(cboot(vgroups, rng5,
                            lambda pos: cov4[pos].mean() - cov5[pos].mean()).std(ddof=1))
    thr_cov = 2.0 * se_cov_cl                            # 🔴 J 금지(#141 ⑥) — SE 눈금 단독
    g4 = None if thr_cov <= 0 else bool(d_cov >= -thr_cov)
    w4 = arm_cal["qwen3e4b"]["piw_ent"].astype(np.float64)
    w5 = arm_cal["qwen05b"]["piw_ent"].astype(np.float64)
    d_W = float(w4.mean() - w5.mean())
    rng6 = np.random.default_rng([STAT_SEED, 6])
    se_W_cl = float(cboot(vgroups, rng6,
                          lambda pos: w4[pos].mean() - w5[pos].mean()).std(ddof=1))
    thr_W = 2.0 * se_W_cl                                # 🔴 J 금지(#141 ⑥) — SE 눈금 단독
    g5 = None if thr_W <= 0 else bool(d_W <= thr_W)
    dW_base = float(arm_uncal["qwen3e4b"]["W"] - u05["W"])
    d2d = 2.0 * (arm_delta["qwen3e4b"] - arm_delta["qwen05b"])

    # ── 탐침(측정 후 · v5.3-3) ────────────────────────────────────────
    probes = {"㉠": gate_probe(GATES["㉠"]["pass_fn"], d_tgt, thr_t, +1.0),
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

    # ── #140 ⑦-6 + #141 ① — 연역 계수(값) + 부호 구조 계수 ───────────
    ded_val = {"㉠": se_tgt_cl == 0.0, "㉢": se_tot_cl == 0.0,
               "㉣": (None if g4 is None else se_cov_cl == 0.0),
               "㉤": (None if g5 is None else se_W_cl == 0.0)}
    for d in JUDGE_D:
        ded_val["㉡ " + d] = se_d[d] == 0.0
    sign_cells = {"㉠": sign_structure(Bt - At, "㉠", SIGN_FORCING_CONST["㉠"]),
                  "㉢": sign_structure(ape_4b - ape_05, "㉢", SIGN_FORCING_CONST["㉢"]),
                  "㉣": sign_structure(cov4 - cov5, "㉣", SIGN_FORCING_CONST["㉣"]),
                  "㉤": sign_structure(w4 - w5, "㉤", SIGN_FORCING_CONST["㉤"])}
    for d in JUDGE_D:
        m = dom_va == D["domains"].index(d)
        sign_cells["㉡ " + d] = sign_structure(ape_4b[m] - ape_05[m], "㉡", SIGN_FORCING_CONST["㉡"])
    n_sign_ded = sum(1 for v in sign_cells.values() if v["부호 구조 연역(1003 ㉠형)"])
    n_cells = 11
    n_deducible = sum(1 for v in ded_val.values() if v is True) + n_sign_ded
    n_nondeducible = n_cells - n_deducible
    등록어 = "판정 사이클" if n_nondeducible > 0 else "측정 사이클(#140 ⑦-6 — 연역 불가 0)"

    # ── 판정어 ────────────────────────────────────────────────────────
    if n_worse or n_better or n_dir:
        verdict = ("등록 결함 — 자료 탐침 ㉰ %d · ㉱ %d · 방향 위반 %d (관찰 강등 · 배포 0)"
                   % (n_worse, n_better, n_dir))
    elif not leak_ok:
        verdict = "등록 결함 — 홀드아웃-val 개체 누수 ≠ 0 (관찰 강등 · 배포 0)"
    elif not (anchorA_ok and anchorA2_ok and anchorB_ok):
        verdict = ("관찰 강등 — 앵커 불통과 (A %s · A′ %s · B %s) (배포 0)"
                   % (anchorA_ok, anchorA2_ok, anchorB_ok))
    elif not anchorC_ok:
        verdict = "관찰 강등 — 앵커 C(보정 팔 굵은 관문) 불통과 (배포 0 · 귀속 분석 §관찰)"
    elif g1 and g2 and g3 and (g4 is None or g4) and (g5 is None or g5):
        verdict = ("성공 — 4B 채택 · 배포 진행 (사전등록 §6 절차 · 커밋→집행 순서 #141 ③)"
                   + ("" if (g4 is not None and g5 is not None) else " · ㉣/㉤ 일부 미판정(퇴화) 병기"))
    elif g1:
        verdict = "부분 — ㉠ 통과나 ㉡/㉢/㉣/㉤ 일부 불통과 (배포 0)"
    else:
        verdict = ("실패 — ㉠ 불통과 (배포 0)"
                   + (" · Δ웹툰 부호는 개선(−)이나 비유의" if d_tgt < 0 else ""))

    # ── 배포 후보물 (성공 시 §6 그대로 집행) ──────────────────────────
    man_cand = {"형식": "앙상블 manifest 후보 (사이클 1005 · 임베더 qwen3e4b)",
                "구성원": {str(sd): {"경로": arm_ckpts["qwen3e4b"][sd]["경로"],
                                  "sha256": arm_ckpts["qwen3e4b"][sd]["sha"]} for sd in SEEDS},
                "결합": "분위수 텐서 (91,5) 산술 평균", "씨앗": list(SEEDS),
                "text_emb": ARM_EMB["qwen3e4b"],
                "text_emb sha256/16": sha16(ARM_EMB["qwen3e4b"]),
                "sao sha": sha16(os.path.join(TRI, "sao.npz")),
                "학습 제외 홀드아웃": {"개체 수": len(picked), "명단 sha256/16": lst_sha},
                "사전등록": "docs/탐색/1005.md"}
    with open(os.path.join(EXP, "manifest_candidate.json"), "w", encoding="utf-8") as f:
        json.dump(man_cand, f, ensure_ascii=False, indent=1)
    conf_cand = {"형식": "등각 보정 v2 (사이클 1005 · 무누수 홀드아웃 · 전역 · 4B 팔)",
                 "α": ALPHA, "δ(log)": arm_delta["qwen3e4b"],
                 "적용": "q05 − δ · q95 + δ (q25/q50/q75 무접촉 · 잔차 log 눈금)",
                 "유효 조건": "배포 시 새 manifest sha 기입 — 소비자 대조(#140 ⑦-3 ㉰)",
                 "구성원 sha": {str(sd): arm_ckpts["qwen3e4b"][sd]["sha"] for sd in SEEDS},
                 "홀드아웃": {"개체 수": len(picked), "행 수": int(len(hold_rows)),
                         "명단 sha256/16": lst_sha,
                         "score n": arm_dsum["qwen3e4b"]["score n(행×91)"],
                         "q_level": arm_dsum["qwen3e4b"]["q_level"]},
                 "잰 소스 (조항 66)": {"sao.npz": sha16(os.path.join(TRI, "sao.npz")),
                                  "text_emb_qwen3e4b.npz": sha16(ARM_EMB["qwen3e4b"]),
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
        worse = sum(1 for v in vals if v > dep_dom["아이돌"])
        idol[arm] = {"씨앗 5(아이돌 MdAPE)": vals,
                     "앙상블": round(arm_uncal[arm]["per_dom"]["아이돌"], 4),
                     "배포(0.1618)보다 나쁜 씨앗 수(계통 자백 자리)": "%d/5" % worse}
    notext = {"Δ웹툰(없음 − 0.5B)": round(arm_uncal["없음"]["per_dom"]["웹툰"] - u05["per_dom"]["웹툰"], 4),
              "Δ전체": round(arm_uncal["없음"]["tot"] - u05["tot"], 4),
              "Δ덮개율(보정)": round(arm_cal["없음"]["cover"] - arm_cal["qwen05b"]["cover"], 4),
              "Δ폭(보정)": round(arm_cal["없음"]["W"] - arm_cal["qwen05b"]["W"], 4),
              "도메인 Δ(없음 − 0.5B)": {d: round(arm_uncal["없음"]["per_dom"][d] - u05["per_dom"][d], 4)
                                    for d in ROSTER}}
    vs_dep = {"도메인 Δ(4B − 배포)": {d: round(arm_uncal["qwen3e4b"]["per_dom"][d] - dep_dom[d], 4)
                                  for d in ROSTER},
              "Δ전체": round(arm_uncal["qwen3e4b"]["tot"] - dep_tot, 4),
              "Δ덮개율(보정 후 대 배포 보정 0.9173)": round(arm_cal["qwen3e4b"]["cover"] - dep_cover, 4),
              "Δ폭(보정 후 대 배포 보정 0.9699)": round(arm_cal["qwen3e4b"]["W"] - dep_piw, 4)}
    tgt_ent = {}
    for j, name in enumerate(tuniq):
        g = tgroups[j]
        tgt_ent[name] = {"행": int(len(g)),
                         "없음": round(float(np.median(arm_uncal["없음"]["ape"][m_tgt][g])), 4),
                         "0.5B": round(float(np.median(At[g])), 4),
                         "4B": round(float(np.median(Bt[g])), 4)}

    out = {
        "러너": "runners/embed1005.py",
        "표적": "웹툰(최약 0.2345 · P 0.933 · ② 에서도 짐) — 임베더 3파전(없음/0.5B/4B) · 앙상블 대 앙상블",
        "시작 시각": 시작,
        "합성 방향 탐침(측정 전 · v5.3-2)": pre_probe,
        "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
        "sha 검증(사전등록 대조)": sha_verify,
        "러너 자신": sha16(os.path.abspath(__file__)),
        "재임베딩 sha 사슬(#139 ⑦-1)": {
            "emb npz": {"경로": ARM_EMB["qwen3e4b"], "sha": sha16(ARM_EMB["qwen3e4b"])},
            "임베더 정체": {"모형": "Qwen3-Embedding-4B", "스냅숏 경로":
                        "/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen3-Embedding-4B/"
                        "snapshots/5cf2132abc99cad020ac570b19d031efec650f2b",
                        "스냅숏 합성 sha16(파일명+내용 사슬)": "80b6377c287208f4"},
            "생성 코드": {"경로": os.path.join(ART, "ft", "embed_triples_qwen3e4b.py"),
                      "sha": sha16(os.path.join(ART, "ft", "embed_triples_qwen3e4b.py"))},
            "원천 meta.jsonl sha": sha16(os.path.join(TRI, "meta.jsonl")),
            "행 수 항등(10,654 = meta)": bool(len(D["meta"]) == REG_META_ROWS),
            "d": REG_D4B, "완주 표지": "ft/embed4b.done = ok (2026-08-19T10:18:30 · 동결 후 등록)"},
        "J‴ 성분 검사(#141 ⑥-1 코드 관문)": check_jppp,
        "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
               "학습 씨앗(다섯째)": list(SEEDS), "통계 씨앗": STAT_SEED, "α": ALPHA,
               "threads": torch.get_num_threads(), "device": "cpu",
               "B": {"붓스트랩": N_BOOT, "순열": "정확 512(2^9 클러스터 전수)"},
               "판정 눈금": "㉠ = 웹툰 개체(9) 클러스터 SE · ㉢㉣㉤ = val 개체(70) 클러스터 SE · "
                        "㉡ = 행 SE(도메인 클러스터 3~16 퇴화 사유 · 1004 §4 승계) · 행 SE 병기",
               "짝지은 설계": "세 팔이 같은 씨앗·같은 tr_pool·같은 배치 행(rng[seed,step])으로 학습 — "
                         "차이는 조건 입력(임베더)뿐"},
        "홀드아웃 구성(로스터 재현 · 관찰 6칸)": hold_sum,
        "앵커 A (배포 보정 재현 13칸 · «실행 간» · ≤1.5e-4)": dict(
            anchorA, 통과=bool(anchorA_ok), 성분="같은 모형·자료·코드 경로 재실행 — 재추첨 0"),
        "앵커 A′ (배포 미보정 재현 2칸)": dict(anchorA2, 통과=bool(anchorA2_ok)),
        "앵커 B (로스터 재현 3칸)": dict(anchorB, 통과=bool(anchorB_ok)),
        "앵커 C (보정 팔 굵은 관문 · v5.2 · 13칸)": dict(
            anchorC, 통과=bool(anchorC_ok),
            성분="🔴 J″(1002)는 «씨앗 간 · 단일 눈금 · 원 train» — 이번 비교(앙상블 · 축소 train)의 "
               "상계로 «관대»함을 알고 쓰는 굵은 설정 관문(v5.2 ㉮) · 3×SE^행 병용"),
        "씨앗별 결과 (관찰 195칸 = 3팔×5씨앗×13)": {arm: {str(sd): arm_seed_cells[arm][sd]
                                                 for sd in SEEDS} for arm in ARMS},
        "체크포인트 (저장소 밖 · 조항 73-마)": {arm: {str(sd): arm_ckpts[arm][sd] for sd in SEEDS}
                                      for arm in ARMS},
        "팔별 앙상블 미보정 val (관찰 39칸)": {arm: summarize(arm_uncal[arm]) for arm in ARMS},
        "팔별 보정 후 val (관찰 6칸)": {arm: {"90% 덮개율": round(arm_cal[arm]["cover"], 4),
                                       "구간 평균 폭(log)": round(arm_cal[arm]["W"], 4)}
                                for arm in ARMS},
        "팔별 δ̂ 요약 (관찰 15칸)": arm_dsum,
        "Mondrian δ_d (관찰 30칸 · 적용·배포·조건부 δ 등록 금지 — #141-3 홀드아웃 웹툰 8 개체)": arm_mond,
        "도메인 조건부 val 덮개 (관찰 40칸 · #141-2 의무 · 팔마다)": cond_cov,
        "아이돌 계통 악화 장부 (#141-7 · 관찰 21칸)": dict(
            idol, 배경="1004: 아이돌 +0.0475 · 씨앗 5/5 계통(#141 ⑤) — 임베더가 이걸 움직이나"),
        "없음 대 0.5B (텍스트 가치 재확인 · 관찰 14칸)": notext,
        "4B 대 배포 (참고 관찰 13칸)": vs_dep,
        "웹툰 개체 수준 (관찰 27칸 · #139 ⑦-7 ㉮)": tgt_ent,
        "J5 (보정 팔 ㉯ — 다음 앵커 정본 신고 · 관찰 13칸)": dict(
            {k: round(v, 4) for k, v in J5.items()},
            성분="«씨앗 간(다섯째 집합 1401~1405) · 축소 train(홀드아웃 98 제외) · 단일 대 (같은 팔) "
               "앙상블» — 앙상블 간 재추첨 지터의 상계(관대 ≈√5)임을 알고 신고"),
        "헤드라인(㉠ 주대비 · 조항 79 · 관찰 10칸)": {
            "웹툰 n(행)": int(m_tgt.sum()), "웹툰 유일 개체": n_cl_t,
            "MdAPE_웹툰(0.5B팔)": round(float(np.median(At)), 6),
            "MdAPE_웹툰(4B팔)": round(float(np.median(Bt)), 6),
            "Δ웹툰(원값)": d_tgt,
            "클러스터 SE(판정 눈금 · [11005,2])": round(se_tgt_cl, 5),
            "행 SE(관찰 · [11005,8])": round(se_tgt_row, 5),
            "t(클러스터)": round(d_tgt / se_tgt_cl, 2) if se_tgt_cl > 0 else None,
            "정확 순열 p(클러스터 교환 512 전수 · 한쪽꼬리 개선=하락)": round(p_exact, 5),
            "개체 동부호(4B 오른/내린/같음)": "%d/%d/%d" % (
                int((ent_b > ent_a).sum()), int((ent_b < ent_a).sum()),
                int((ent_b == ent_a).sum())),
            "🔴 판정어 층의 연역 불가능 칸 수(#140 ⑦-6 + #141 ①)": "%d/%d → 등록어 = %s" % (
                n_nondeducible, n_cells, 등록어)},
        "Δ·SE 표 (4B − 0.5B · 관찰 26칸)": {
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
            "부호 구조(행 차 상수 항등 · 단측 구조 · 강제 상수)": sign_cells,
            "부호 구조 연역 칸": n_sign_ded, "연역 가능 합": n_deducible,
            "연역 불가능": n_nondeducible, "등록어": 등록어},
        "판정 (사전등록 §4 · 판정 11칸 · 비반올림 집행 · 여유 = 판정 갈린 원값)": {
            "앵커 A": bool(anchorA_ok), "앵커 A′": bool(anchorA2_ok),
            "앵커 B": bool(anchorB_ok), "앵커 C": bool(anchorC_ok),
            "㉠ 주대비 Δ웹툰(악화=상승 · 통과=유의 개선)": {
                "통과": g1, "Δ웹툰": d_tgt, "문턱 max(J5_웹툰, 2×SE^cl)": thr_t,
                "여유(원값 · −문턱−Δ · 양수=통과)": -thr_t - d_tgt},
            "㉡ 타 도메인 유의 악화(판정 7 · 악화=상승)": {
                "통과": g2, "걸린 도메인": bad if bad else "없음(0/7)",
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
                                          "SE(행)": round(se_d[d], 4)} for d in SMALL},
            "웹툰 행 동부호(4B−0.5B · 오른/내린/같음 · 관찰)": "%d/%d/%d" % (
                int((Bt > At).sum()), int((Bt < At).sum()), int((Bt == At).sum()))},
        "조항 78 탐침 (측정 후 · v5.3-3 + ㉰㉱)": dict(
            probes, 계수={"㉮ 원리상 못 떨어짐(격자)": n_m, "㉯ 원리상 못 통과(격자)": n_n,
                        "㉰ 악화 극값에서 참": n_worse, "㉱ 개선 극값에서 거짓": n_better,
                        "퇴화 문턱": n_degen, "방향 검사 위반": n_dir}),
        "판정어": verdict,
        "배포 후보(성공 시 §6 그대로 · 4B 팔)": {
            "manifest_candidate.json": {"경로": os.path.join(EXP, "manifest_candidate.json"),
                                        "sha": sha16(os.path.join(EXP, "manifest_candidate.json"))},
            "conformal_candidate.json": {"경로": os.path.join(EXP, "conformal_candidate.json"),
                                         "sha": sha16(os.path.join(EXP, "conformal_candidate.json"))},
            "δ̂(4B)": arm_delta["qwen3e4b"]},
        "관찰 분모 신고(조항 79)": (
            "대비 주장 1(㉠ Δ웹툰 · 4B팔 − 0.5B팔) · 판정 11(㉠1 ㉡7 ㉢1 ㉣1 ㉤1) · 관찰 498 = "
            "앵커 31(A 13 + A′ 2 + B 3 + C 13) + 로스터 6 + 씨앗별 195 + 팔별 미보정 39 + "
            "보정 6 + δ̂ 15 + Mondrian 30 + 조건부 덮개 40 + 아이돌 21 + 없음대비 14 + "
            "4B대배포 13 + 웹툰 개체 27 + J5 13 + 헤드라인 10 + Δ·SE 26 + 폭 분해 3 + 연역 2 + "
            "J‴ 검사 1 + 게임·만화 4 + 동부호 2 · 배포 시 LODO 관찰 += 10"),
        "총소요초": round(time.time() - t_all, 1),
        "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "Δ웹툰": round(d_tgt, 4), "문턱": round(thr_t, 4),
                      "SE^cl": round(se_tgt_cl, 4), "p(정확)": round(p_exact, 4),
                      "웹툰(없음/0.5B/4B)": [round(arm_uncal[a]["per_dom"]["웹툰"], 4) for a in ARMS],
                      "㉡": g2, "Δ전체": round(d_tot, 4), "Δ덮개": round(d_cov, 4),
                      "Δ폭": round(d_W, 4), "연역 불가": "%d/11" % n_nondeducible,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
