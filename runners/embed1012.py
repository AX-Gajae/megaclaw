# -*- coding: utf-8 -*-
"""반증 1012 러너 — 텍스트 조건화 셔플 반증: 원본 / 개체-내 셔플 / 없음(관찰)
(사전등록 docs/탐색/1012.md 에서 언 코드 · 루프 v5.3 동결 · 부칙 1~5 · 외부 심사 발의 이행).

세계 명제(외부 심사 발의 · 반증가능 형): 텍스트 조건화의 이득(1005 절제 실측: 없음 0.0839 대
0.5B 0.0569 — Δ+0.0270)은 «액션의 타이밍 신호»가 아니라 «개체의 정체 서술»이 나른다.
반증 실험: 학습 자료(tr_pool)에서 개체 내 액션 텍스트(임베딩 행)를 시점끼리 무작위 재배열해
재학습 — ⓐ 성적 비악화 → 명제 확증(텍스트 = 정체) ⓑ 유의 악화 → 명제 기각(타이밍 실재).
🔴 val 은 개체 분리 — 이것은 «누수» 검사가 아니라 «신호의 종류» 검사다(사전등록 §0 명시).

주대비 «하나»(조항 79): Δ전체 = MdAPE_전체(셔플팔 앙상블) − MdAPE_전체(원본팔 앙상블).
세 팔 전부: 같은 축소 train(1004 홀드아웃 98 제외 · 명단 sha 0cbc70bb8b83d579 재현 강제) ·
🔴 일곱째 학습 씨앗 집합 1601~1605 · 분위수 텐서 산술 평균 앙상블 · 팔마다 «제» δ̂(홀드아웃
CQR — 조항 66) · val 1,129 행 평가. 비교는 «앙상블 대 앙상블»(#139 ⑦-3) · 짝지은 씨앗.

판정 1칸(㉠ · 비반올림 집행) + 앵커:
  앵커A  배포(1004 앙상블+δ) 재현 항등 13칸 ≤ 1.5e-4 («실행 간» · 1005 자구)
  앵커A′ 배포 «미보정» 재현 2칸(0.7530 · 0.5026 — out1004 관찰값)
  앵커B  홀드아웃 로스터 재현 3칸(98 개체 · 1,752 행 · 명단 sha 0cbc70bb8b83d579)
  앵커C  «보정 팔» 굵은 관문 13칸(v5.2 ㉮ · 1005·1009 자구): |원본팔 앙상블 − 배포(미보정)|
         ≤ max(J″_x(out1002 — «씨앗 간 · 단일 눈금 · 원 train» 상계 · 관대함을 알고 쓴다),
         3×SE_x^행([11012,7]))
  ㉠  Δ전체 ≤ +max(J5_전체(out1005 정본 0.0079), 2×SE^cl_전체([11012,4] 실측))
      [악화 = 상승(+) · 통과 = 비악화 = 명제 확증 · 불통과 = 유의 악화 = 명제 기각]
관찰 D(앵커 아님 — 사전등록 §4): |원본팔(1601~1605) − 1005 0.5B팔(1401~1405 · out1005)| 13칸
  을 J5 상계와 대조 게재 — 같은-시대 «앙상블 간» 재추첨 지터의 첫 직접 실측(1005 §9-ⓐ ·
  1009 §3-3 두 번 «미측정» 자백의 해소). 초과 칸은 «지터 > J5 상계» 신고(판정 아님 — 주대비는
  짝지은 씨앗이라 재추첨 지터가 대부분 상쇄된다 · 사유 §4).
🔴 부칙 4: 배포물 여는 시점 assert_epoch("3a5c2543a55f1dab") — 게재는 반환값(실측).
🔴 #141 ⑥-1: GATE_THRESH_SRC 에 J‴ 있으면 측정 없이 중단(이번 0 — 기계 게재) · J5 성분
   문자열 대조(«단일 대 (같은 팔) 앙상블»·«씨앗 간» — 1009 §3-2 자구).
🔴 #141 ① + #140 ⑦-6: 값 연역 + 부호 구조 연역 기계 게재 — 등록 시점 기대 = 연역 불가 1/1.
🔴 v5.3-2 측정-«전» 합성 방향 탐침(t=1) — 어긋나면 측정 없이 중단.

MDE(외부 심사 발의 · 자발 게재 — 사전등록 §1): 예상 2×SE^cl_전체 = 0.01856(out1005 실측
SE^cl 0.00928 재사용 · sha cd3a6ce8c4f4841a) · MDE = max(J5 0.0079, 0.01856) = +0.01856 ·
예상 효과 상계 = 절제 이득 +0.0270(타이밍 몫 100% 일 때) > MDE → 판정 게이트 등록.
타이밍 몫 s < 0.69 인 «부분 타이밍»은 이 실험이 못 가른다 — 확증 판정어는 이 MDE 눈금 한정.

🔴 CPU 전용 4스레드 · 유료 API 0 · MPS 0 · 학습 15(3팔×5씨앗 · 순차 · 각 학습 전 load1>10
이면 60초 대기 반복) · 배포 파일 무변경(읽기만) · 씀: python3 runners/embed1012.py
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
from pretrain.epoch_guard import assert_epoch, EpochMismatch  # noqa: E402

torch.set_num_threads(4)
SEEDS = (1601, 1602, 1603, 1604, 1605)   # 🔴 일곱째 집합 — 997·1001~1005·1101~1105·1201~1205·1301~1305·1401~1405·1501~1505 금지 이행
STAT_SEED = 11012                        # 🔴 신규 통계 스트림 — 11001~11010·[1011,·]·[1008,·] 재사용 금지
SHUF_STREAM = 1012                       # 🔴 개체 순열 seed [1012, k] — k = 정렬 tr_pool 개체 색인(사전등록 §3)
CARVE_SEED = [11004, 0]                  # 로스터 «재현» 전용(새 뽑기 아님) — 명단 sha 일치 강제(앵커 B)
N_BOOT = 10000
ALPHA = 0.10
HOLD_FRAC = 0.15
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
STEPS, BATCH, LR, HIDDEN = 3000, 256, 1e-3, 512
LOAD_GATE = 10.0

REG_HOLD_ENT = 98
REG_HOLD_ROWS = 1752
REG_HOLD_SHA = "0cbc70bb8b83d579"
REG_DEP_UNCAL_COV = 0.7530               # out1004 「신 앙상블 미보정 val」 관찰값
REG_DEP_UNCAL_W = 0.5026
REG_META_ROWS = 10654
REG_EPOCH_SHA = "3a5c2543a55f1dab"       # 부칙 4 등록 기재값(1004 시대 — 1005~1011 배포 0)
# 사전등록 §3 실측 신고값(구성 계수 — 성능 실측 0) — 러너가 재실측 대조
REG_POOL_ROWS = 7773
REG_POOL_ENT = 536
REG_FIX_ENT = 126                        # 행 1 개체 — 셔플 불능(분모 신고)
REG_SHUF_ENT = 410
REG_SHUF_ROWS = 7647
# MDE(자발 게재 · §1) — out1005 실측 재사용(사전 예상치 — 실현 문턱은 아래 실측)
REG_MDE = {"예상 2×SE^cl_전체": 0.01856322, "J5_전체(out1005)": 0.0079,
           "MDE(사전)": 0.01856322, "예상 효과 상계(절제 이득 없음−0.5B)": 0.0270,
           "검출 가능 타이밍 몫 s": "≥ 0.69 (0.01856/0.0270)",
           "원천": "out1005_embed.json cd3a6ce8c4f4841a — Δ전체(4B−0.5B) SE^cl 0.00928 · "
                 "짝지은 씨앗·같은 임베더 비교라 실현 SE 는 이보다 작을 개연(관대 쪽 예상 자백)"}

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
TROUT = os.path.join(ART, "transition")
EXP = os.path.join(ART, "exp", "embed1012")
OUT_JSON = os.path.join(REPO, "runners", "out1012_embed.json")
EMB_PATH = os.path.join(TRI, "text_emb_qwen05b.npz")

ARMS = ("원본", "셔플", "없음")

EXPECT_SHA = {
    os.path.join(TROUT, "ensemble_manifest.json"): "3a5c2543a55f1dab",
    os.path.join(TROUT, "conformal.json"): "d8f40489c9341302",
    os.path.join(TROUT, "leaderboard.json"): "f15a9907fb3ef6b9",
    os.path.join(TROUT, "report.json"): "6dfb0a4ff2935de0",
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "meta.jsonl"): "f74f94235bc5f032",
    EMB_PATH: "c4128e73c8ea52ca",
    os.path.join(REPO, "runners/out1002_ensemble.json"): "bad5616b2561a21f",   # J″ 정본(앵커 C)
    os.path.join(REPO, "runners/out1004_holdout.json"): "0a28715ab5632f50",    # J‴ 성분 검사 원천
    os.path.join(REPO, "runners/out1005_embed.json"): "cd3a6ce8c4f4841a",      # J5 정본 · 관찰 D 원천 · MDE 원천
    os.path.join(REPO, "data/lab/1010_판_후.json"): "180f88fd744f6286",        # 전판
}
KEY_JPP = "J″_d (셋째 씨앗 5 |Δ리더보드| 최대 · 1001 J′ 와 같은 정의 — 다음 앵커 정본 신고 · ㉯)"
KEY_JPPP = "J‴ (넷째 씨앗 5 |Δ배포 리더보드| 최대 — 다음 앵커 정본 신고 · ㉯ · 관찰 13칸)"
KEY_J5 = "J5 (보정 팔 ㉯ — 다음 앵커 정본 신고 · 관찰 13칸)"
KEY_ARM_UNCAL = "팔별 앙상블 미보정 val (관찰 39칸)"

# 🔴 #141 ⑥-1 — 게이트별 문턱 원천 선언(코드 관문이 검사): J‴ 는 어디에도 없어야 한다
GATE_THRESH_SRC = {"㉠": ("J5", "2×SE^cl")}
# 🔴 #141 ① — 부호 구조 연역 선언 맵: 게이트 부호를 강제하는 «등록-전 상수» 유무
SIGN_FORCING_CONST = {"㉠": None}
# (이번 설계는 ㉠ 이 등록-후 15 학습 산출에 의존 — 강제 상수 없음 · 기대 = 연역 불가 1/1 「판정 사이클」)


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
                           ensure_ascii=False) + "\n")     # 부칙 4 ㉰ — 전 행 시각 칸


def load_gate_wait():
    waited = 0
    while os.getloadavg()[0] > LOAD_GATE:
        prog({"load 관문": round(os.getloadavg()[0], 2), "대기": "60초"})
        time.sleep(60)
        waited += 60
    return waited


# ── 게이트 «하나» + 부호 서명 (v5.3-1) ────────────────────────────────
GATES = {
    "㉠": {"pass_fn": lambda x, t: x <= t, "worse_sign": +1.0,
          "악화 한 줄": "학습 텍스트의 «개체 내 시점 정렬»만 부순 재학습으로 전체 누적 90일 중앙 예측 "
                    "오차(MdAPE)가 «오르면»(+) — 텍스트가 나르던 것이 개체 정체 서술이 아니라 액션의 "
                    "타이밍 신호였다는 뜻 — 모형 성능의 악화 = 명제의 기각 방향. 통과 = 비악화(Δ ≤ +문턱) "
                    "= 명제 확증(이 MDE 눈금 한정). 반대쪽 극단(유의 «개선» Δ < −문턱)은 관찰 신고(v5.3-1)"},
}


def presynth_probe(t=1.0):
    """v5.3-2 측정-«전» 합성 방향 탐침 — 한쪽형: 악화 극값(+2t) 거짓 ∧ 개선 극값(−2t) 참."""
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
    """#141 ① — 부호 구조 검사(1005 자구)."""
    d = np.asarray(diffs, dtype=np.float64)
    const = bool(len(d) > 0 and float(d.max() - d.min()) == 0.0)
    npos, nneg, nzero = int((d > 0).sum()), int((d < 0).sum()), int((d == 0).sum())
    onesided = bool((npos == 0) or (nneg == 0))
    forced = bool(onesided and forcing is not None)
    return {"행 차 상수 항등(1003 ㉣형)": const, "행 동부호(+/−/0)": "%d/%d/%d" % (npos, nneg, nzero),
            "단측 구조": onesided, "부호 강제 등록-전 상수": forcing if forcing else "없음(선언 맵)",
            "부호 구조 연역(1003 ㉠형)": forced or const}


# ── 자료 (999~1005 러너와 자구까지 같은 전처리) ───────────────────────
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
    E = np.load(EMB_PATH)["E"].astype(np.float32)
    assert len(E) == len(S) == len(meta) == REG_META_ROWS, \
        "🔴 행 수 항등 실패: E %d · S %d · meta %d" % (len(E), len(S), len(meta))
    return {"S": S, "base": base, "Sc": Sc, "R": R, "dom_id": dom_id, "split": split,
            "C_common": C_common, "E": E, "domains": domains, "meta": meta,
            "tr": np.where(split == 0)[0], "va": np.where(split == 1)[0]}


def carve_holdout(D):
    """1004 로스터 «재현» — seed [11004,0] · 15% 층화 · 명단 sha 일치 강제(앵커 B · 1005 자구)."""
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
               "뽑기 seed": "[11004,0] — 1004 로스터 «재현» 전용(새 뽑기 아님 · 사전등록 §3)"}
    return set(picked), rows, summary, lst_sha


def build_shuffle(D, tr_pool):
    """개체 내 시점 셔플 — E 행을 «tr_pool 안 · 같은 개체» 사이에서만 재배열(사전등록 §3).

    개체 k(정렬 tr_pool 개체 색인) 순열 seed = [1012, k] · 행 순서 = (언제, 전역 행 색인) 정렬 ·
    항등 순열이면 재추첨(최대 64 — n≥2). 홀드아웃·val 행 무접촉(정체/타이밍 검사 — 누수 검사
    아님 · δ̂ 와 평가는 원본 텍스트 정렬로 잰다). 기계 검증: ㉮ 개체별 임베딩 다중집합 보존
    (행 해시 정렬 대조) ㉯ 셔플 밖 행 바이트 항등 ㉰ 분모 계수 게재."""
    meta = D["meta"]
    E = D["E"]
    ents = {}
    for i in tr_pool:
        ents.setdefault(meta[int(i)]["개체"], []).append(int(i))
    names = sorted(ents)
    row_hash = {}
    E_shuf = E.copy()
    n_fix_ent = n_fix_rows = n_shuf_ent = n_shuf_rows = 0
    n_moved = n_redraw = n_identity_kept = 0
    touched = []
    for k, name in enumerate(names):
        rows = sorted(ents[name], key=lambda i: (meta[i]["언제"], i))
        n = len(rows)
        if n < 2:
            n_fix_ent += 1
            n_fix_rows += n
            continue
        rng = np.random.default_rng([SHUF_STREAM, k])
        perm = rng.permutation(n)
        tries = 0
        while bool((perm == np.arange(n)).all()) and tries < 64:
            tries += 1
            perm = rng.permutation(n)
        n_redraw += tries
        if bool((perm == np.arange(n)).all()):
            n_identity_kept += 1              # 원리상 (1/2)^64 — 실측 게재 자리
        idx = np.asarray(rows, dtype=np.int64)
        E_shuf[idx] = E[idx[perm]]
        n_shuf_ent += 1
        n_shuf_rows += n
        n_moved += int((perm != np.arange(n)).sum())
        touched.append(idx)
        # ㉮ 다중집합 보존 — 행 바이트 해시 정렬 대조
        for i in idx:
            if int(i) not in row_hash:
                row_hash[int(i)] = hashlib.sha1(E[int(i)].tobytes()).hexdigest()
        before = sorted(row_hash[int(i)] for i in idx)
        after = sorted(hashlib.sha1(E_shuf[int(i)].tobytes()).hexdigest() for i in idx)
        assert before == after, "🔴 다중집합 보존 실패 — 개체 %s (셔플이 재배열이 아니라 교체)" % name
    touched_set = np.zeros(len(E), dtype=bool)
    if touched:
        touched_set[np.concatenate(touched)] = True
    # ㉯ 셔플 밖 행 바이트 항등(홀드아웃·val 포함 전부)
    assert bool((E_shuf[~touched_set] == E[~touched_set]).all()), "🔴 셔플 밖 행이 변했다"
    n_changed = int((~(E_shuf[touched_set] == E[touched_set]).all(axis=1)).sum())
    denom = {"tr_pool 행": int(len(tr_pool)), "tr_pool 개체": len(names),
             "셔플 불능 개체(행 1 — 분모 신고)": n_fix_ent, "셔플 불능 행": n_fix_rows,
             "셔플 적용 개체": n_shuf_ent, "셔플 적용 행": n_shuf_rows,
             "행 이동 수(perm≠항등 자리)": n_moved,
             "임베딩 실변경 행 수(바이트 대조)": n_changed,
             "항등 순열 재추첨 횟수": n_redraw, "항등 순열 잔존 개체(0 기대)": n_identity_kept,
             "다중집합 보존 검사": "통과(개체별 행 해시 정렬 대조)",
             "셔플 밖 행 항등 검사": "통과(홀드아웃·val 원본 정렬 유지 — §3 사유)"}
    reg_ok = (len(tr_pool) == REG_POOL_ROWS and len(names) == REG_POOL_ENT
              and n_fix_ent == REG_FIX_ENT and n_shuf_ent == REG_SHUF_ENT
              and n_shuf_rows == REG_SHUF_ROWS)
    return E_shuf, denom, reg_ok


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
    세 팔이 «같은 행»을 뽑아 학습한다(짝지은 설계 — 사전등록 §3)."""
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


def abort(out):
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))


def main():
    t_all = time.time()
    시작 = time.strftime("%Y-%m-%dT%H:%M:%S")
    ok, pre_probe = presynth_probe(1.0)
    if not ok:
        abort({"판정어": "중단 — v5.3-2 합성 방향 탐침 어긋남 (등록 결함 · 측정 없이 중단)",
               "합성 방향 탐침(측정 전)": pre_probe, "시작 시각": 시작})
        return

    # 부칙 4 — 배포물 여는 시점 시대 실측(게재는 반환값)
    try:
        epoch_stamp = assert_epoch(REG_EPOCH_SHA)
    except EpochMismatch as e:
        abort({"판정어": "중단 — 부칙 4 시대 불일치 (측정 없이 중단)", "사유": str(e),
               "시작 시각": 시작})
        return

    sha_verify = {}
    for p, want in EXPECT_SHA.items():
        got = sha16(p) if os.path.exists(p) else "없음"
        sha_verify[os.path.basename(p)] = {"기대": want, "실측": got, "일치": got == want}
    if not all(v["일치"] for v in sha_verify.values()):
        abort({"판정어": "중단 — 원천 sha 불일치 (조항 66 · 측정 없이 중단)",
               "sha 검증": sha_verify, "시작 시각": 시작})
        return

    # 🔴 #141 ⑥-1 — J‴ 사용 0 기계 확인 + J5 성분 문자열 대조(1009 §3-2 자구)
    o1004 = json.load(open(os.path.join(REPO, "runners/out1004_holdout.json"), encoding="utf-8"))
    o1005 = json.load(open(os.path.join(REPO, "runners/out1005_embed.json"), encoding="utf-8"))
    jppp_used = [g for g, srcs in GATE_THRESH_SRC.items() if any("J‴" in s for s in srcs)]
    j5_comp = o1005[KEY_J5]["성분"]
    j5_comp_ok = ("단일 대 (같은 팔)" in j5_comp) and ("씨앗 간" in j5_comp)
    check_thresh = {"out1004 J‴ 성분 기재": o1004[KEY_JPPP]["성분"],
                    "J‴ 를 문턱으로 쓰는 게이트": jppp_used if jppp_used else 0,
                    "J5 성분 문자열(out1005)": j5_comp,
                    "J5 성분 대조(«씨앗 간»·«단일 대 (같은 팔)»)": j5_comp_ok,
                    "판정": ("통과 — J‴ 사용 0 · J5 성분 일치" if (not jppp_used and j5_comp_ok)
                           else "등록 결함")}
    if jppp_used or not j5_comp_ok:
        abort({"판정어": "중단 — 등록 결함(#141 ⑥-1 문턱 성분 · 측정 없이 중단)",
               "문턱 성분 검사": check_thresh, "시작 시각": 시작})
        return
    J5 = {k: float(v) for k, v in o1005[KEY_J5].items() if k != "성분"}
    ref05 = o1005[KEY_ARM_UNCAL]["qwen05b"]          # 관찰 D 원천(1401~1405 앙상블)

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
    C_orig = np.concatenate([D["C_common"], D["E"]], axis=1).astype(np.float32)
    pred_dep_uncal = predict_rows(dep_raw, D, C_orig, D["va"])
    pred_dep_cal = predict_rows(dep_cal, D, C_orig, D["va"])
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
          "load대기초": waited0, "시대(부칙 4)": epoch_stamp})

    # ── 셔플 구성(측정 아님 — 입력 구성) + 팔별 조건행렬 ──────────────
    hold_set = set(hold_rows.tolist())
    tr_pool = np.asarray([i for i in D["tr"] if int(i) not in hold_set], dtype=np.int64)
    E_shuf, shuf_denom, shuf_reg_ok = build_shuffle(D, tr_pool)
    if not shuf_reg_ok:
        abort({"판정어": "중단 — 셔플 분모가 사전등록 구성 계수와 불일치 (등록 결함 · 측정 없이 중단)",
               "셔플 분모": shuf_denom, "시작 시각": 시작})
        return
    C_arm = {"원본": C_orig,
             "셔플": np.concatenate([D["C_common"], E_shuf], axis=1).astype(np.float32),
             "없음": D["C_common"]}
    prog({"셔플 분모": shuf_denom})

    # ── 학습 15 (3팔 × 5씨앗 · 순차 · load 관문 · 짝지은 씨앗) ────────
    r_h = D["R"][hold_rows].astype(np.float64)
    arm_seed_cells, arm_ens_val, arm_ens_hold, arm_ckpts = {}, {}, {}, {}
    os.makedirs(EXP, exist_ok=True)
    for arm in ARMS:
        Carm = C_arm[arm]
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
                        "레시피": "현행 레시피 · seed %d · steps 3000 · 홀드아웃 98 제외 train · "
                               "팔 %s (사이클 1012 — 셔플 반증)" % (sd, arm)}, cp)
            ck[sd] = {"경로": cp, "sha": sha16(cp)}
            prog({"팔": arm, "seed": sd, "전체": cells[sd]["전체 MdAPE"],
                  "웹툰": cells[sd]["도메인별 MdAPE"]["웹툰"], "sec": sec})
        arm_seed_cells[arm] = cells
        arm_ckpts[arm] = ck
        arm_ens_val[arm] = np.mean(np.stack([preds_val[sd] for sd in SEEDS]), axis=0)
        arm_ens_hold[arm] = np.mean(np.stack([preds_hold[sd] for sd in SEEDS]), axis=0)

    # ── 팔별: 미보정 평가 · δ̂(제 것 · 홀드아웃 원본 정렬) · 보정 후 ────
    arm_uncal, arm_delta, arm_cal, arm_dsum = {}, {}, {}, {}
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
        arm_dsum[arm] = {"δ̂(전역 · log · 제 것 — 조항 66)": delta,
                         "q_level": round(ql, 6), "score n(행×91)": int(scores_h.size),
                         "홀드아웃 한계-덮개(전)": round(float((scores_h <= 0).mean()), 4),
                         "홀드아웃 한계-덮개(후 · δ̂ 적용)": round(float((scores_h <= delta).mean()), 4)}
        prog({"팔": arm, "δ̂": round(delta, 4), "val 미보정": round(u["cover"], 4),
              "val 보정": round(c["cover"], 4), "전체": round(u["tot"], 4)})

    # ── J7 (원본팔 씨앗 지터 · 단일 대 앙상블 — 다음 앵커 정본 신고) ───
    c_o = arm_seed_cells["원본"]
    u_o = arm_uncal["원본"]
    J7 = {d: max(abs(c_o[sd]["도메인별 MdAPE"][d] - u_o["per_dom"][d]) for sd in SEEDS)
          for d in ROSTER}
    J7["전체"] = max(abs(c_o[sd]["전체 MdAPE"] - u_o["tot"]) for sd in SEEDS)
    J7["덮개율(미보정)"] = max(abs(c_o[sd]["90% 덮개율"] - u_o["cover"]) for sd in SEEDS)
    J7["폭(미보정)"] = max(abs(c_o[sd]["구간 평균 폭(log)"] - u_o["W"]) for sd in SEEDS)

    # ── 앵커 C — «보정 팔» 굵은 관문(v5.2 · 1005·1009 자구): 원본팔 대 배포 13칸 ──
    va = D["va"]
    val_names = [D["meta"][int(i)]["개체"] for i in va]
    vuniq, vids, vgroups = cluster_groups(val_names)
    ape_dep = ev_dep_uncal["ape"].astype(np.float64)
    ape_o = u_o["ape"].astype(np.float64)
    dom_va = ev_dep_uncal["dom_va"]
    rng7 = np.random.default_rng([STAT_SEED, 7])
    anchorC, cok = {}, []
    for d in ROSTER:
        m = dom_va == D["domains"].index(d)
        A, Bv = ape_dep[m], ape_o[m]
        n_d = int(m.sum())
        idxd = rng7.integers(0, n_d, size=(N_BOOT, n_d))
        se = float((np.median(Bv[idxd], axis=1) - np.median(A[idxd], axis=1)).std(ddof=1))
        dv = abs(u_o["per_dom"][d] - ev_dep_uncal["per_dom"][d])
        thr = max(J2[d], 3.0 * se)
        anchorC[d] = {"|Δ|": round(dv, 4), "문턱 max(J″,3SE행)": round(thr, 4),
                      "통과": bool(dv <= thr)}
        cok.append(dv <= thr)
    cov_dep_rows = ev_dep_uncal["cover_ent"].astype(np.float64)
    cov_o_rows = u_o["cover_ent"].astype(np.float64)
    w_dep_rows = ev_dep_uncal["piw_ent"].astype(np.float64)
    w_o_rows = u_o["piw_ent"].astype(np.float64)
    idxr = rng7.integers(0, len(va), size=(N_BOOT, len(va)))
    for name, Bv, A, Jx in (("전체", ape_o, ape_dep, J2_tot),
                            ("덮개율(미보정)", cov_o_rows, cov_dep_rows, J2_cov),
                            ("폭(미보정)", w_o_rows, w_dep_rows, J2_W)):
        if name == "전체":
            boot = np.median(Bv[idxr], axis=1) - np.median(A[idxr], axis=1)
            dv = abs(u_o["tot"] - ev_dep_uncal["tot"])
        else:
            boot = Bv[idxr].mean(axis=1) - A[idxr].mean(axis=1)
            dv = abs(Bv.mean() - A.mean())
        se = float(boot.std(ddof=1))
        thr = max(Jx, 3.0 * se)
        anchorC[name] = {"|Δ|": round(dv, 4), "문턱 max(J″,3SE행)": round(thr, 4),
                        "통과": bool(dv <= thr)}
        cok.append(dv <= thr)
    anchorC_ok = all(cok)

    # ── 관찰 D — 앙상블 간 재추첨 지터 첫 실측: 원본팔 대 1005 0.5B팔 13칸 (판정 아님) ──
    obsD = {}
    for d in ROSTER:
        dv = abs(u_o["per_dom"][d] - float(ref05["도메인별 MdAPE"][d]))
        obsD[d] = {"|Δ|(1601~1605 대 1401~1405)": round(dv, 4), "J5 상계": J5[d],
                   "상계 안": bool(dv <= J5[d])}
    for name, mine, ref, jk in (("전체", u_o["tot"], float(ref05["전체 MdAPE"]), "전체"),
                                ("덮개율(미보정)", u_o["cover"], float(ref05["90% 덮개율"]), "덮개율(미보정)"),
                                ("폭(미보정)", u_o["W"], float(ref05["구간 평균 폭(log)"]), "폭(미보정)")):
        dv = abs(mine - ref)
        obsD[name] = {"|Δ|(1601~1605 대 1401~1405)": round(dv, 4), "J5 상계": J5[jk],
                      "상계 안": bool(dv <= J5[jk])}
    n_D_over = sum(1 for v in obsD.values() if not v["상계 안"])

    # ── ㉠ 주대비 — Δ전체(셔플 − 원본) · val 70 개체 클러스터 눈금 ─────
    ape_s = arm_uncal["셔플"]["ape"].astype(np.float64)
    d_tot = float(arm_uncal["셔플"]["tot"] - u_o["tot"])
    rng4 = np.random.default_rng([STAT_SEED, 4])
    se_tot_cl = float(cboot(vgroups, rng4,
                            lambda pos: np.median(ape_s[pos]) - np.median(ape_o[pos])).std(ddof=1))
    rng8 = np.random.default_rng([STAT_SEED, 8])
    idxa = rng8.integers(0, len(va), size=(N_BOOT, len(va)))
    se_tot_row = float((np.median(ape_s[idxa], axis=1) - np.median(ape_o[idxa], axis=1)).std(ddof=1))
    # 순열(관찰 병기 — 70 클러스터 라벨 교환 표집 B=10,000 · 한쪽꼬리 «악화» · (1+k)/(B+1))
    rng3 = np.random.default_rng([STAT_SEED, 3])
    n_cl = len(vgroups)
    perm_stats = np.empty(N_BOOT)
    for b in range(N_BOOT):
        flip = rng3.integers(0, 2, size=n_cl).astype(bool)[vids]
        ap = np.where(flip, ape_s, ape_o)
        bp = np.where(flip, ape_o, ape_s)
        perm_stats[b] = np.median(bp) - np.median(ap)
    p_perm = float((1 + int((perm_stats >= d_tot).sum())) / (N_BOOT + 1))
    thr_tot = max(J5["전체"], 2.0 * se_tot_cl)
    g1 = bool(GATES["㉠"]["pass_fn"](d_tot, thr_tot))
    ent_o = np.asarray([np.median(ape_o[g]) for g in vgroups])
    ent_s = np.asarray([np.median(ape_s[g]) for g in vgroups])

    # ── 관찰: 도메인별 Δ·SE · 웹툰 조각(정확 순열 512) · 덮개·폭 ───────
    delta_d = {d: arm_uncal["셔플"]["per_dom"][d] - u_o["per_dom"][d] for d in ROSTER}
    se_d, se_d_cl = {}, {}
    for k, d in enumerate(ROSTER):
        m = dom_va == D["domains"].index(d)
        A, Bv = ape_o[m], ape_s[m]
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
    m_web = dom_va == D["domains"].index("웹툰")
    Aw, Bw = ape_o[m_web], ape_s[m_web]
    web_names = [val_names[j] for j in np.where(m_web)[0]]
    wuniq, wids, wgroups = cluster_groups(web_names)
    d_web = float(np.median(Bw) - np.median(Aw))
    rng2 = np.random.default_rng([STAT_SEED, 2])
    se_web_cl = float(cboot(wgroups, rng2,
                            lambda pos: np.median(Bw[pos]) - np.median(Aw[pos])).std(ddof=1))
    stats_pw = np.empty(2 ** len(wgroups))
    for bi, bits in enumerate(itertools.product([0, 1], repeat=len(wgroups))):
        flip = np.asarray(bits, dtype=bool)[wids]
        ap = np.where(flip, Bw, Aw)
        bp = np.where(flip, Aw, Bw)
        stats_pw[bi] = np.median(bp) - np.median(ap)
    p_web = float((stats_pw >= d_web).sum() / len(stats_pw))   # 한쪽꼬리 «악화» · 해상도 1/512
    cov_s = arm_cal["셔플"]["cover_ent"].astype(np.float64)
    cov_o = arm_cal["원본"]["cover_ent"].astype(np.float64)
    d_cov = float(cov_s.mean() - cov_o.mean())
    rng5 = np.random.default_rng([STAT_SEED, 5])
    se_cov_cl = float(cboot(vgroups, rng5,
                            lambda pos: cov_s[pos].mean() - cov_o[pos].mean()).std(ddof=1))
    w_s = arm_cal["셔플"]["piw_ent"].astype(np.float64)
    w_o2 = arm_cal["원본"]["piw_ent"].astype(np.float64)
    d_W = float(w_s.mean() - w_o2.mean())
    rng6 = np.random.default_rng([STAT_SEED, 6])
    se_W_cl = float(cboot(vgroups, rng6,
                          lambda pos: w_s[pos].mean() - w_o2[pos].mean()).std(ddof=1))
    dW_base = float(arm_uncal["셔플"]["W"] - u_o["W"])
    d2d = 2.0 * (arm_delta["셔플"] - arm_delta["원본"])

    # ── 탐침(측정 후 · v5.3-3) — 판정 게이트 ㉠ 하나 ─────────────────
    probes = {"㉠": gate_probe(GATES["㉠"]["pass_fn"], d_tot, thr_tot, +1.0)}
    n_worse = sum(1 for p in probes.values() if p["㉰ 악화 극값에서 참"])
    n_better = sum(1 for p in probes.values() if p["㉱ 개선 극값에서 거짓"])
    n_degen = sum(1 for p in probes.values() if p["퇴화 문턱(thr ≤ 0)"])
    n_dir = sum(1 for p in probes.values() if not p["방향 검사"])

    # ── #140 ⑦-6 + #141 ① — 연역 계수 ───────────────────────────────
    ded_val = {"㉠": se_tot_cl == 0.0}
    sign_cells = {"㉠": sign_structure(ape_s - ape_o, SIGN_FORCING_CONST["㉠"])}
    n_sign_ded = sum(1 for v in sign_cells.values() if v["부호 구조 연역(1003 ㉠형)"])
    n_cells = 1
    n_deducible = sum(1 for v in ded_val.values() if v is True) + n_sign_ded
    n_nondeducible = n_cells - n_deducible
    등록어 = "판정 사이클" if n_nondeducible > 0 else "측정 사이클(#140 ⑦-6 — 연역 불가 0)"

    # ── 판정어(사전 고정 문언) ────────────────────────────────────────
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
    elif g1:
        verdict = ("명제 확증 — 셔플 비악화(Δ전체 ≤ +문턱) · 텍스트 이득은 «개체 정체 서술»이 "
                   "나른다(이 자료·이 레시피·이 MDE 눈금 한정 — 타이밍 몫 s<0.69 는 못 가른다 · "
                   "「텍스트 조건부 전이」 규정 문구 정정은 티처 몫 이관 · 배포 0)"
                   + (" · 🔴 반대쪽 극단: 유의 «개선»(Δ < −문턱) — 관찰 신고(v5.3-1)"
                      if d_tot < -thr_tot else ""))
    else:
        verdict = ("명제 기각 — 타이밍 신호 실재(셔플 유의 악화 Δ전체 > +문턱 · 배포 0)")

    out = {
        "러너": "runners/embed1012.py",
        "표적": "텍스트 조건화 셔플 반증(외부 심사 발의) — 원본/개체-내 셔플/없음 · 앙상블 대 앙상블 · "
              "«신호의 종류» 검사(val 개체 분리 — 누수 검사 아님)",
        "시작 시각": 시작,
        "시대(부칙 4 — 게재는 실측 반환값)": epoch_stamp,
        "합성 방향 탐침(측정 전 · v5.3-2)": pre_probe,
        "잰 소스 (조항 66)": {k: v["실측"] for k, v in sha_verify.items()},
        "sha 검증(사전등록 대조)": sha_verify,
        "러너 자신": sha16(os.path.abspath(__file__)),
        "문턱 성분 검사(#141 ⑥-1 코드 관문)": check_thresh,
        "MDE(외부 심사 발의 · 자발 게재 — 사전등록 §1 상수 + 실현 문턱)": dict(
            REG_MDE, **{"실현 문턱(㉠)": thr_tot, "실현 2×SE^cl": 2.0 * se_tot_cl,
                       "실현 문턱 ≤ 사전 MDE": bool(thr_tot <= REG_MDE["MDE(사전)"])}),
        "설정": {"steps": STEPS, "batch": BATCH, "lr": LR, "hidden": HIDDEN,
               "학습 씨앗(일곱째)": list(SEEDS), "통계 씨앗": STAT_SEED,
               "셔플 순열 스트림": "[%d, k] — k = 정렬 tr_pool 개체 색인 · 항등이면 재추첨" % SHUF_STREAM,
               "α": ALPHA, "threads": torch.get_num_threads(), "device": "cpu",
               "B": {"붓스트랩": N_BOOT, "순열(전체)": "표집 10,000(70 클러스터 — 전수 불가 자백)",
                    "순열(웹툰)": "정확 512(2^9 전수)"},
               "판정 눈금": "㉠ = val 개체(70) 클러스터 SE · 행 SE 병기 · 도메인별은 관찰",
               "짝지은 설계": "세 팔이 같은 씨앗·같은 tr_pool·같은 배치 행(rng[seed,step])으로 학습 — "
                         "차이는 조건 입력(E 원본/E 셔플/E 없음)뿐"},
        "홀드아웃 구성(로스터 재현 · 관찰 6칸)": hold_sum,
        "셔플 분모·기계 검증(관찰 12칸 — 조항 79 분모 신고)": shuf_denom,
        "앵커 A (배포 보정 재현 13칸 · «실행 간» · ≤1.5e-4)": dict(
            anchorA, 통과=bool(anchorA_ok), 성분="같은 모형·자료·코드 경로 재실행 — 재추첨 0"),
        "앵커 A′ (배포 미보정 재현 2칸)": dict(anchorA2, 통과=bool(anchorA2_ok)),
        "앵커 B (로스터 재현 3칸)": dict(anchorB, 통과=bool(anchorB_ok)),
        "앵커 C (보정 팔 굵은 관문 · v5.2 · 13칸)": dict(
            anchorC, 통과=bool(anchorC_ok),
            성분="🔴 J″(1002)는 «씨앗 간 · 단일 눈금 · 원 train» — 이번 비교(앙상블 · 축소 train)의 "
               "상계로 «관대»함을 알고 쓰는 굵은 설정 관문(v5.2 ㉮) · 3×SE^행 병용"),
        "관찰 D (앙상블 간 재추첨 지터 첫 실측 13칸 — 판정 아님 · 1005 §9-ⓐ 해소)": dict(
            obsD, **{"J5 상계 초과 칸 수": n_D_over,
                    "성분": "원본팔(일곱째 1601~1605) 대 out1005 0.5B팔(다섯째 1401~1405) — 같은 "
                          "레시피·같은 축소 train·앙상블 대 앙상블 · 주대비는 짝지은 씨앗이라 이 "
                          "지터가 대부분 상쇄된다(§4 사유 — 판정 아님)"}),
        "씨앗별 결과 (관찰 195칸 = 3팔×5씨앗×13)": {arm: {str(sd): arm_seed_cells[arm][sd]
                                                 for sd in SEEDS} for arm in ARMS},
        "체크포인트 (저장소 밖 · 조항 73-마)": {arm: {str(sd): arm_ckpts[arm][sd] for sd in SEEDS}
                                      for arm in ARMS},
        "팔별 앙상블 미보정 val (관찰 39칸)": {arm: summarize(arm_uncal[arm]) for arm in ARMS},
        "팔별 보정 후 val (관찰 6칸)": {arm: {"90% 덮개율": round(arm_cal[arm]["cover"], 4),
                                       "구간 평균 폭(log)": round(arm_cal[arm]["W"], 4)}
                                for arm in ARMS},
        "팔별 δ̂ 요약 (관찰 15칸)": arm_dsum,
        "없음 대 원본 (텍스트 가치 재확인 · 일곱째 집합 · 관찰 14칸)": {
            "Δ웹툰(없음 − 원본)": round(arm_uncal["없음"]["per_dom"]["웹툰"] - u_o["per_dom"]["웹툰"], 4),
            "Δ전체": round(arm_uncal["없음"]["tot"] - u_o["tot"], 4),
            "Δ덮개율(보정)": round(arm_cal["없음"]["cover"] - arm_cal["원본"]["cover"], 4),
            "Δ폭(보정)": round(arm_cal["없음"]["W"] - arm_cal["원본"]["W"], 4),
            "도메인 Δ(없음 − 원본)": {d: round(arm_uncal["없음"]["per_dom"][d] - u_o["per_dom"][d], 4)
                                  for d in ROSTER}},
        "Δ·SE 표 (셔플 − 원본 · 관찰 26칸)": {
            **{d: {"Δ": round(delta_d[d], 4), "SE(행)": round(se_d[d], 4),
                   "SE(클러스터·관찰)": se_d_cl.get(d, "미계산(유일 개체 <8)"),
                   "J5_d(참고)": J5[d]} for d in ROSTER},
            "전체": {"Δ": round(d_tot, 4), "SE^cl": round(se_tot_cl, 5), "J5": J5["전체"]},
            "덮개율(보정)": {"Δ": round(d_cov, 4), "SE^cl": round(se_cov_cl, 5)},
            "폭(보정)": {"Δ": round(d_W, 4), "SE^cl": round(se_W_cl, 5)}},
        "웹툰 조각 (관찰 4칸 — 1005 주대비 자리의 재사용 · 판정 아님)": {
            "Δ웹툰(셔플 − 원본)": d_web,
            "클러스터 SE([11012,2])": round(se_web_cl, 5),
            "정확 순열 p(512 전수 · 한쪽꼬리 악화)": round(p_web, 5),
            "개체 동부호(셔플 오른/내린/같음)": "%d/%d/%d" % (
                int((np.asarray([np.median(Bw[g]) for g in wgroups])
                     > np.asarray([np.median(Aw[g]) for g in wgroups])).sum()),
                int((np.asarray([np.median(Bw[g]) for g in wgroups])
                     < np.asarray([np.median(Aw[g]) for g in wgroups])).sum()),
                int((np.asarray([np.median(Bw[g]) for g in wgroups])
                     == np.asarray([np.median(Aw[g]) for g in wgroups])).sum()))},
        "헤드라인(㉠ 주대비 · 조항 79 · 관찰 10칸)": {
            "val n(행)": int(len(va)), "val 유일 개체": n_cl,
            "MdAPE_전체(원본팔)": round(u_o["tot"], 6),
            "MdAPE_전체(셔플팔)": round(arm_uncal["셔플"]["tot"], 6),
            "Δ전체(원값)": d_tot,
            "클러스터 SE(판정 눈금 · [11012,4])": round(se_tot_cl, 5),
            "행 SE(관찰 · [11012,8])": round(se_tot_row, 5),
            "t(클러스터)": round(d_tot / se_tot_cl, 2) if se_tot_cl > 0 else None,
            "순열 p(70 클러스터 라벨 교환 표집 · 한쪽꼬리 악화 · (1+k)/(B+1))": round(p_perm, 5),
            "🔴 판정어 층의 연역 불가능 칸 수(#140 ⑦-6 + #141 ①)": "%d/%d → 등록어 = %s" % (
                n_nondeducible, n_cells, 등록어)},
        "동부호 (관찰 2칸)": {
            "행(셔플 오른/내린/같음)": "%d/%d/%d" % (int((ape_s > ape_o).sum()),
                                             int((ape_s < ape_o).sum()),
                                             int((ape_s == ape_o).sum())),
            "개체(70 · 오른/내린/같음)": "%d/%d/%d" % (int((ent_s > ent_o).sum()),
                                             int((ent_s < ent_o).sum()),
                                             int((ent_s == ent_o).sum()))},
        "폭 분해 (관찰 3칸)": {"Δ폭(보정)": round(d_W, 6),
                         "ΔW_base(미보정 기저)": round(dW_base, 6),
                         "Δ2δ̂(지불 차)": round(d2d, 6)},
        "연역 계수 (#140 ⑦-6 값 + #141 ① 부호 구조 · 관찰 2칸)": {
            "값 연역(SE=0·등록상수 문턱)": ded_val,
            "부호 구조(행 차 상수 항등 · 단측 구조 · 강제 상수)": sign_cells,
            "부호 구조 연역 칸": n_sign_ded, "연역 가능 합": n_deducible,
            "연역 불가능": n_nondeducible, "등록어": 등록어},
        "J7 (원본팔 — 다음 앵커 정본 신고 · 관찰 13칸)": dict(
            {k: round(v, 4) for k, v in J7.items()},
            성분="«씨앗 간(일곱째 집합 1601~1605) · 축소 train(홀드아웃 98 제외) · 단일 대 (같은 팔) "
               "앙상블» — 앙상블 간 재추첨 지터의 상계(관대 ≈√5)임을 알고 신고"),
        "판정 (사전등록 §5 · 판정 1칸 · 비반올림 집행 · 여유 = 판정 갈린 원값)": {
            "앵커 A": bool(anchorA_ok), "앵커 A′": bool(anchorA2_ok),
            "앵커 B": bool(anchorB_ok), "앵커 C": bool(anchorC_ok),
            "㉠ 주대비 Δ전체(셔플−원본 · 악화=상승 · 통과=비악화=명제 확증)": {
                "통과": g1, "Δ전체": d_tot,
                "문턱 max(J5_전체, 2×SE^cl)": thr_tot,
                "여유(원값 · 문턱−Δ · 양수=통과)": thr_tot - d_tot,
                "악화 한 줄(v5.3-1)": GATES["㉠"]["악화 한 줄"]}},
        "조항 78 탐침 (측정 후 · v5.3-3 + ㉰㉱)": dict(
            probes, 계수={"㉰ 악화 극값에서 참": n_worse, "㉱ 개선 극값에서 거짓": n_better,
                        "퇴화 문턱": n_degen, "방향 검사 위반": n_dir}),
        "판정어": verdict,
        "관찰 분모 신고(조항 79)": (
            "대비 주장 1(㉠ Δ전체 · 셔플팔 − 원본팔) · 판정 1(㉠) · 관찰 393 = "
            "로스터 6 + 셔플 분모 12 + 앵커 31(A 13 + A′ 2 + B 3 + C 13) + 관찰 D 13 + "
            "씨앗별 195 + 팔별 미보정 39 + 보정 6 + δ̂ 15 + 없음대비 14 + Δ·SE 26 + 웹툰 4 + "
            "헤드라인 10 + 동부호 2 + 폭 분해 3 + 연역 2 + 문턱 성분 검사 1 + J7 13 + 시대 1 · "
            "배포 0(판 무접촉 — 어느 결과든)"),
        "총소요초": round(time.time() - t_all, 1),
        "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({"판정어": verdict, "Δ전체": round(d_tot, 5), "문턱": round(thr_tot, 5),
                      "SE^cl": round(se_tot_cl, 5), "p(표집)": round(p_perm, 4),
                      "전체(원본/셔플/없음)": [round(arm_uncal[a]["tot"], 4) for a in ARMS],
                      "웹툰(원본/셔플/없음)": [round(arm_uncal[a]["per_dom"]["웹툰"], 4) for a in ARMS],
                      "Δ웹툰": round(d_web, 4), "관찰D 초과": n_D_over,
                      "연역 불가": "%d/1" % n_nondeducible,
                      "총소요초": out["총소요초"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
