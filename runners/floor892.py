# -*- coding: utf-8 -*-
"""노트 892 — **순수 난수 열의 잡음 바닥을 12도메인·유보 3,775 로 다시 잰다**.

티처 #54 C1 1순위. 논문 146(`paper/steps/146_roughcol/`)이 11도메인 시대에
*'연속 쓰레기 3열이 0.0043 으로 판 2σ(0.0045)와 같다'* 를 실측했고, 티처는 그 수가
새 채택 문턱 0.00353 의 1.22배라는 이유로 *'문턱이 자기 실험실의 잡음 바닥 아래로
내려갔다'* 고 적었다.

🔴 **그런데 0.0043 은 죽은 숫자다.** 노트 741·742 가 뽑기 여섯(900~905)으로 다시 재서
**평균 0.0153 · 뽑기 SD 0.0030 · 범위 0.0094~0.0212** 를 실측하고 논문 146 의 헤드라인을
명시 정정했으며, 그 정정은 `ingest/audit.py` 의 `DEAD_NUMBERS` 에 등록돼 있다
(`0.0043 → 0.0153`, 문맥어 `쓰레기 3열`). 그래도 **둘 다 11도메인·유보 3,369 시대 값**이라
지금 판에 그대로 못 댄다.

**그래서 이 러너가 하는 일**: 노트 741 의 설계(`runners/draw741.py`)를 그대로
**12도메인·유보 3,775·씨앗 0~11 정본**으로 확장해 다시 잰다.

    · 뽑기 R=12 (난수 씨앗 900~911 --- 741 의 여섯을 포함해 혈통을 잇는다)
    · 열 수 1·2·3 **포개기**(1열 = 3열의 첫 열) --- 뽑기 잡음이 열 수 비교에서 상쇄된다
    · 카디널리티 사다리 k=2·4·10·100·연속 (146 의 계단 재현)
    · 모형 씨앗: 기준선 0~11 · 연속 팔 0~5 · 사다리 0~2
    · **잡음 바닥 = 뽑기 평균 + 2σ_뽑기** (사전등록) · 병기 90 백분위 · 최대 · cluster_boot 구간

사전등록은 `data/lab/denominator.json` 의
*'**사전등록** 순수 난수 열의 잡음 바닥을 12도메인·유보 3,775 로 다시 잰다'* 칸.

🔴 **이 파일이 머리기사 수를 전부 낸다**(티처 #54 M4 --- 891 은 오발률·분위수를 내는 코드가
저장소에 없어 다음 세션이 재현할 수 없었다). 참조값은 **복사하지 않고 다시 센다**(M4).
"""
import os

#: 🔴 적합은 사실상 단일 코어다(실측 1스레드 58.1초 대 기본 68.1초 --- 스레드가 **해롭다**).
#: 프로세스를 여러 개 띄우는 편이 8배 가깝게 빠르므로 스레드를 못박고 병렬로 간다.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import multiprocessing as mp                                    # noqa: E402
import sys                                                      # noqa: E402
import time                                                     # noqa: E402
from pathlib import Path                                        # noqa: E402

import numpy as np                                              # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out892_floor.json"
LOG = ROOT / "runners/out892_log.txt"

T = 2025.0
AX = "junk"
NCOL = 3                       #: 뽑기는 늘 3열을 낳는다 --- 팔은 앞에서 잘라 쓴다(포개기)
DRAWS = tuple(range(900, 912))         #: 뽑기 12 (741 의 900~905 포함)
DRAWS_LADDER = tuple(range(900, 906))  #: 카디널리티 사다리는 뽑기 6
SEEDS_BASE = tuple(range(12))          #: 정본 씨앗
SEEDS_CONT = tuple(range(6))
SEEDS_LADDER = tuple(range(3))
KS = (2, 4, 10, 100)
NCOLS = (1, 2, 3)
NPROC = 11
BOOT_B = 10_000

#: 자 (티처 #54: 0.00353 은 '잠정' · 방어 대역 병기 의무)
THR = 0.00353
THR_BAND = (0.00312, 0.00393)
OLD_THR = 0.0045               #: 11도메인 유물 --- 옛 값과 대면하기 위해서만 쓴다

#: 가드 (사전등록)
BASE_OK = (0.4650, 0.4760)
POST_N = 3775
DATA_SHA_890 = "d7e2df860139efba"

#: 🔴 **검산 참조**(예측 아님) --- 11도메인 시대. 손 전사 금지 원칙상 출처를 함께 적는다.
REF_11DOM = {
    "노트 738 연속 3열(뽑기 하나 · 죽은 값)": 0.0043,
    "노트 740 연속 3열(다른 뽑기 하나)": 0.0167,
    "노트 742 연속 3열 뽑기 6 평균(산 값)": 0.0153,
    "노트 742 뽑기 SD": 0.0030,
    "노트 742 모형 씨앗 SD": 0.0026,
    "노트 742 범위(평균±2σ)": [0.0094, 0.0212],
    "노트 740 1열": 0.0060,
    "노트 146 카디널리티 열당(이진·사분위·십분위·백분위·연속)":
        [-0.0001, 0.0004, 0.0009, 0.0015, 0.0014],
    "노트 146 시장팝업 흔들림(연속 3열)": -0.0329,
    "출처": "data/lab/denominator.json 노트 738·740·742 칸 · ingest/audit.py DEAD_NUMBERS",
}


# ────────────────────────────────────────────────────────────────────────
# 자료
# ────────────────────────────────────────────────────────────────────────
def junk_raw(draw, doms, rows):
    """뽑기 하나 --- 도메인마다 (n_d, 3) 연속 난수. **741 과 같은 생성 순서**.

    도메인 정렬 순으로 한 rng 에서 연속으로 뽑는다. 열 수 1·2·3 팔은 이 배열의
    앞에서 잘라 쓰므로 **포개진다**(뽑기 잡음이 열 수 비교에서 상쇄된다).
    """
    rng = np.random.default_rng(draw)
    return {d: rng.random((rows[d], NCOL)) for d in doms}


def junk_axes(raw, doms, ncol, k):
    """축 딕트. `k=None` 이면 연속, 아니면 **도메인 안 분위** k 단계로 이산화(노트 737)."""
    ax = {}
    for j in range(ncol):
        per = {}
        for d in doms:
            v = raw[d][:, j].astype(np.float64).copy()
            if k is not None:
                v = np.clip(np.floor(v * k), 0, k - 1) / max(k - 1, 1)
            per[d] = (v.astype(np.float32), np.ones(len(v), np.float32))
        ax[f"{AX}_{j}"] = per
    return ax


def build(arm):
    """팔 하나의 `Data`. 팔 키는 `(kind, draw, ncol, k)`."""
    import ff753 as FF
    kind, draw, ncol, k = arm
    b = FF.base()
    #: `항등:기준선` 도 기준선이다 --- 자료부터 다시 지어 같은 값이 나오나 보는 팔
    if kind.endswith("기준선"):
        return FF.shell(b)
    d0 = FF.shell(b)
    doms = sorted(d0.dom)
    rows = {d: len(d0.dom[d][2]) for d in doms}
    ax = junk_axes(junk_raw(draw, doms, rows), doms, ncol, k)
    return FF.shell({**b, **ax})


def digest_data(d):
    """자료 sha256 앞 16 --- 890·891 과 **같은 판 위에서 재는가**(손 전사 아님)."""
    h = hashlib.sha256()
    for k in sorted(d.dom):
        A, M, y, t = d.dom[k]
        for arr in (A, M, y, t):
            a = np.ascontiguousarray(np.asarray(arr, float))
            h.update(str(a.shape).encode()); h.update(a.tobytes())
        h.update(("|".join(map(str, d.names[k]))).encode())
    return h.hexdigest()[:16]


# ────────────────────────────────────────────────────────────────────────
# 병렬 일꾼 --- 한 프로세스 안에서 **같은 팔이면 자료를 다시 안 짓는다**
# ────────────────────────────────────────────────────────────────────────
_CACHE = {}


def work(task):
    arm, seed = task
    from lab import forms
    from lab.harness import evaluate
    if _CACHE.get("arm") != arm:
        _CACHE.clear()
        _CACHE["arm"] = arm
        _CACHE["data"] = build(arm)
    data = _CACHE["data"]
    CLS = forms.REGISTRY["F18_bagboost"]["cls"]
    t0 = time.time()
    sc = evaluate(lambda: CLS(seed=seed), data, T=T)
    return {"arm": list(arm), "seed": seed,
            "판": float(data.pooled(sc, T=T)),
            "도메인": {k: float(v) for k, v in sc.items() if np.isfinite(v)},
            "초": round(time.time() - t0, 1)}


# ────────────────────────────────────────────────────────────────────────
# 통계 --- 머리기사 수는 **전부 여기서** 난다
# ────────────────────────────────────────────────────────────────────────
def draw_stats(base_by_seed, arm_by_draw_seed, seeds, label):
    """뽑기별 하락과 잡음 바닥.

    Δ_r = mean_s [ ρ_기준선(s) − ρ_팔_r(s) ]  --- **양수 = 쓰레기가 판을 깎는다**.
    같은 씨앗끼리 짝짓는다.
    """
    from lab import pairboot as PB
    draws = sorted(arm_by_draw_seed)
    per, within = {}, []
    for r in draws:
        dif = np.array([base_by_seed[s] - arm_by_draw_seed[r][s] for s in seeds])
        per[r] = float(dif.mean())
        within.append(float(dif.std(ddof=1)))
    v = np.array([per[r] for r in draws])
    av = np.abs(v)
    mu = float(v.mean())
    sd = float(v.std(ddof=1))
    model_sd = float(np.mean(within))          #: 뽑기 안 **짝** SD(모형 씨앗 잡음)
    S = len(seeds)
    corr = float(np.sqrt(max(0.0, sd ** 2 - model_sd ** 2 / S)))
    #: 규약 47 --- 구간은 cluster_boot 로. 뽑기 하나가 군집 하나다.
    idx = [np.array([i]) for i in range(len(v))]
    pt, lo, hi, kind = PB.cluster_boot(lambda ix: float(v[ix].mean()), idx,
                                       B=BOOT_B, seed=892)
    return {
        "이름": label,
        "뽑기 수": len(draws),
        "모형 씨앗 수": S,
        "뽑기별 하락": {str(r): round(per[r], 4) for r in draws},
        "**뽑기 평균 μ**": round(mu, 5),
        "**뽑기 SD σ**": round(sd, 5),
        "모형 짝 SD(뽑기 안 평균)": round(model_sd, 5),
        "뽑기 SD / 모형 SD": round(sd / max(model_sd, 1e-12), 2),
        "씨앗 잡음 보정 σ": round(corr, 5),
        "🔴 **잡음 바닥 = μ + 2σ**": round(mu + 2 * sd, 5),
        "바닥(보정 σ 로)": round(mu + 2 * corr, 5),
        "|Δ| 90 백분위": round(float(np.percentile(av, 90)), 5),
        "|Δ| 최대": round(float(av.max()), 5),
        "|Δ| 최소": round(float(av.min()), 5),
        "양수 뽑기": int((v > 0).sum()),
        "음수 뽑기": int((v < 0).sum()),
        "μ 구간(cluster_boot · 뽑기=군집)": [round(pt, 5), round(lo, 5), round(hi, 5)],
        "구간 종류": kind,
        "**바닥 / 문턱 0.00353**": round((mu + 2 * sd) / THR, 2),
        "바닥 / 방어대역": [round((mu + 2 * sd) / THR_BAND[1], 2),
                       round((mu + 2 * sd) / THR_BAND[0], 2)],
        "바닥 / 옛 문턱 0.0045": round((mu + 2 * sd) / OLD_THR, 2),
    }


def say_factory():
    f = open(LOG, "w", buffering=1)

    def say(s):
        print(s, flush=True)
        f.write(str(s) + "\n")
    return say, f


def main():
    t0 = time.time()
    say, fh = say_factory()
    import ff753 as FF
    from lab import forms
    from scipy.stats import spearmanr

    # ── ② 배선 검사 (측정 전에 닫는다)
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    rows = {d: len(d0.dom[d][2]) for d in doms}
    W = d0.weights(T)
    sha0 = digest_data(d0)
    order0 = forms.axis_order(d0)
    raw_probe = junk_raw(DRAWS[0], doms, rows)
    ax_probe = junk_axes(raw_probe, doms, 3, None)
    d_probe = FF.shell({**FF.base(), **ax_probe})
    order1 = forms.axis_order(d_probe)
    uniq = {d: int(len(np.unique(ax_probe[f"{AX}_0"][d][0]))) for d in doms}
    wiring = {
        "ㄱ 자료 sha256(기준선)": sha0,
        "ㄱ 890·891 과 같은가": sha0 == DATA_SHA_890,
        "ㄴ 도메인 수": len(doms),
        "ㄴ 유보 가중 합": int(sum(W.values())),
        "ㄴ 유보 3,775 인가": int(sum(W.values())) == POST_N,
        "ㄴ 도메인별 유보": {d: int(W[d]) for d in doms},
        "ㄷ axis_order 기준선": len(order0),
        "ㄷ axis_order 난수 3열 주입 후": len(order1),
        "🔴 ㄷ 난수 열이 설계행렬에 **들어갔나**(+3 인가)": len(order1) - len(order0) == 3,
        "ㄷ 들어간 이름": sorted(set(order1) - set(order0)),
        #: float32 로 내리면 5,905행 만화에서 **한 번** 충돌한다(5904/5905) --- 실측이므로
        #: '고유값 = 행수' 를 딱 맞추지 말고 비율로 본다. 값 가짓수가 1 이면 그건 퇴화다.
        "ㄹ 연속 열 고유값 / 행수": {d: round(uniq[d] / rows[d], 6) for d in doms},
        "ㄹ 연속 열 고유값이 행수의 99.9% 이상인가":
            {d: bool(uniq[d] >= 0.999 * rows[d]) for d in doms},
        "ㄹ 행수": rows,
        "ㅁ 중립화 없음(마스크 전부 1)":
            all(float(np.asarray(ax_probe[f"{AX}_{j}"][d][1]).min()) == 1.0
                for j in range(3) for d in doms),
        "ㅂ 포개기 확인(1열 == 3열의 첫 열)":
            bool(np.array_equal(junk_axes(raw_probe, doms, 1, None)[f"{AX}_0"][doms[0]][0],
                                ax_probe[f"{AX}_0"][doms[0]][0])),
        "ㅅ 난수 자체 sha256(뽑기 900 · 12도메인)":
            hashlib.sha256(b"".join(np.ascontiguousarray(raw_probe[d]).tobytes()
                                    for d in doms)).hexdigest()[:16],
    }
    say("=== ② 배선 검사 ===")
    say(json.dumps(wiring, ensure_ascii=False, indent=1))
    if not (wiring["ㄴ 유보 3,775 인가"] and wiring["ㄱ 890·891 과 같은가"]
            and wiring["🔴 ㄷ 난수 열이 설계행렬에 **들어갔나**(+3 인가)"]):
        say(json.dumps({"🔴 중단": "가드 위반 --- 사전등록 F6/가드"}, ensure_ascii=False))
        return
    del d_probe

    # ── 일감
    tasks = []
    tasks += [(("기준선", None, None, None), s) for s in SEEDS_BASE]
    for nc in NCOLS:
        for r in DRAWS:
            tasks += [(("연속", r, nc, None), s) for s in SEEDS_CONT]
    for k in KS:
        for r in DRAWS_LADDER:
            tasks += [(("이산", r, 3, k), s) for s in SEEDS_LADDER]
    #: 🔴 항등 통제(티처 #54 m5 · 노트 887 이 무효화된 자리) --- **자료부터 다시 지어** 재적합
    tasks += [(("항등:기준선", None, None, None), 0),
              (("항등:연속900_3", 900, 3, None), 0)]
    say(f"=== ③ 측정 · 적합 {len(tasks)}회 · 프로세스 {NPROC} ===")

    mp.set_start_method("spawn", force=True)
    res = []
    with mp.Pool(NPROC) as pool:
        for i, r in enumerate(pool.imap(work, tasks, chunksize=3), 1):
            res.append(r)
            if i % 20 == 0 or i == len(tasks):
                say(f"  [{i}/{len(tasks)}] {round(time.time()-t0)}초")

    # ── 표로 접기
    by = {}
    for r in res:
        by.setdefault(tuple(r["arm"]), {})[r["seed"]] = r
    base_arm = ("기준선", None, None, None)
    base_by_seed = {s: by[base_arm][s]["판"] for s in SEEDS_BASE}
    b12 = float(np.mean([base_by_seed[s] for s in SEEDS_BASE]))
    if not (BASE_OK[0] <= b12 <= BASE_OK[1]):
        say(json.dumps({"🔴 중단": f"기준선 {b12} 가 {BASE_OK} 밖"}, ensure_ascii=False))
        return

    # ── F4 항등 통제
    ident = {
        "기준선 씨앗0 재구축 Δ":
            by[("항등:기준선", None, None, None)][0]["판"] - by[base_arm][0]["판"],
        "연속 3열 뽑기900 씨앗0 재구축 Δ":
            by[("항등:연속900_3", 900, 3, None)][0]["판"] - by[("연속", 900, 3, None)][0]["판"],
    }
    ident["🔴 둘 다 부동소수 정확 0 인가"] = all(v == 0.0 for v in ident.values())
    say("=== F4 항등 통제 ===")
    say(json.dumps(ident, ensure_ascii=False))

    # ── 연속 팔 · 열 수별
    cont = {}
    for nc in NCOLS:
        arm_by = {r: {s: by[("연속", r, nc, None)][s]["판"] for s in SEEDS_CONT}
                  for r in DRAWS}
        cont[f"연속 {nc}열"] = draw_stats(
            {s: base_by_seed[s] for s in SEEDS_CONT}, arm_by, SEEDS_CONT, f"연속 {nc}열")

    # ── 카디널리티 사다리(3열 · 뽑기 6 · 씨앗 3) + 같은 조건의 연속
    ladder = {}
    for k in KS:
        arm_by = {r: {s: by[("이산", r, 3, k)][s]["판"] for s in SEEDS_LADDER}
                  for r in DRAWS_LADDER}
        ladder[f"k={k}"] = draw_stats(
            {s: base_by_seed[s] for s in SEEDS_LADDER}, arm_by, SEEDS_LADDER, f"k={k} · 3열")
    arm_by = {r: {s: by[("연속", r, 3, None)][s]["판"] for s in SEEDS_LADDER}
              for r in DRAWS_LADDER}
    ladder["연속"] = draw_stats({s: base_by_seed[s] for s in SEEDS_LADDER},
                              arm_by, SEEDS_LADDER, "연속 · 3열")
    lad_mu = [ladder[f"k={k}"]["**뽑기 평균 μ**"] for k in KS]
    mono = all(lad_mu[i] <= lad_mu[i + 1] + 1e-9 for i in range(len(lad_mu) - 1))

    # ── 도메인별 흔들림 (연속 3열 · 뽑기 12 · 씨앗 0~5)
    dom_shift, dom_per_draw = {}, {}
    for d in doms:
        bs = np.array([np.mean([by[base_arm][s]["도메인"][d] for s in SEEDS_CONT])])
        vals = []
        for r in DRAWS:
            a = np.mean([by[("연속", r, 3, None)][s]["도메인"][d] for s in SEEDS_CONT])
            vals.append(float(a - bs[0]))          #: **팔 − 기준선**(146 의 부호 규약)
        dom_per_draw[d] = [round(x, 4) for x in vals]
        dom_shift[d] = {"뽑기 평균 흔들림": round(float(np.mean(vals)), 4),
                        "뽑기 SD": round(float(np.std(vals, ddof=1)), 4),
                        "|평균| / 문턱": round(abs(float(np.mean(vals))) / THR, 1),
                        "유보 행": int(W[d])}
    ns = np.array([dom_shift[d]["유보 행"] for d in doms], float)
    sh = np.array([abs(dom_shift[d]["뽑기 평균 흔들림"]) for d in doms])
    rho_s, p_s = spearmanr(sh, ns)

    floor3 = cont["연속 3열"]["🔴 **잡음 바닥 = μ + 2σ**"]
    floor1 = cont["연속 1열"]["🔴 **잡음 바닥 = μ + 2σ**"]
    verdict = {
        "(가) 3열 바닥 ≥ 0.00353": bool(floor3 >= THR),
        "(나) 1열 바닥 ≥ 0.00353": bool(floor1 >= THR),
        "(다) 바닥 < 0.00353 (146/742 는 11도메인 유물)": bool(max(floor1, floor3) < THR),
        "(마) 첫 양수를 채택하지 않는다": "제안만 한다 --- 정본 채택은 다음 사이클 확인 뒤",
        "F1 모형 짝 SD > 0.005":
            bool(cont["연속 3열"]["모형 짝 SD(뽑기 안 평균)"] > 0.005),
        "F2 부호가 갈린다(양·음 각 ≥3)":
            {f"연속 {nc}열": bool(cont[f'연속 {nc}열']["양수 뽑기"] >= 3
                                and cont[f'연속 {nc}열']["음수 뽑기"] >= 3)
             for nc in NCOLS},
        "F3 뽑기 SD > 3 × 모형 SD":
            bool(cont["연속 3열"]["뽑기 SD / 모형 SD"] > 3.0),
        "F4 항등 통제 실패": bool(not ident["🔴 둘 다 부동소수 정확 0 인가"]),
        "F5 1열 바닥 ≥ 3열 바닥": bool(floor1 >= floor3),
        "F6 난수 열이 설계행렬 밖": bool(not wiring["🔴 ㄷ 난수 열이 설계행렬에 **들어갔나**(+3 인가)"]),
    }
    scored = {
        "P1 μ₃ ∈ [0.008,0.022]":
            [cont["연속 3열"]["**뽑기 평균 μ**"],
             bool(0.008 <= cont["연속 3열"]["**뽑기 평균 μ**"] <= 0.022)],
        "P2 σ₃ ∈ [0.0015,0.0055]":
            [cont["연속 3열"]["**뽑기 SD σ**"],
             bool(0.0015 <= cont["연속 3열"]["**뽑기 SD σ**"] <= 0.0055)],
        "P3 μ₁ ∈ [0.002,0.010]":
            [cont["연속 1열"]["**뽑기 평균 μ**"],
             bool(0.002 <= cont["연속 1열"]["**뽑기 평균 μ**"] <= 0.010)],
        "P4 3열 바닥/문턱 ∈ [2.0,7.0]":
            [cont["연속 3열"]["**바닥 / 문턱 0.00353**"],
             bool(2.0 <= cont["연속 3열"]["**바닥 / 문턱 0.00353**"] <= 7.0)],
        "P5 1열 바닥 ≥ 문턱": [floor1, bool(floor1 >= THR)],
        "P6 카디널리티 단조": [lad_mu, bool(mono)],
        "P7 시장팝업이 |흔들림| 최대":
            [max(doms, key=lambda d: abs(dom_shift[d]["뽑기 평균 흔들림"])),
             bool(max(doms, key=lambda d: abs(dom_shift[d]["뽑기 평균 흔들림"])) == "시장팝업")],
        "P8 |흔들림| ↔ 유보 행 스피어만 < 0":
            [round(float(rho_s), 3), round(float(p_s), 4), bool(rho_s < 0)],
    }

    out = {
        "노트": 892,
        "언제": time.strftime("%Y-%m-%d %H:%M"),
        "초": round(time.time() - t0, 1),
        "적합 수": len(tasks),
        "② 배선": wiring,
        "F4 항등 통제": ident,
        "기준선": {"12씨앗 판": round(b12, 5),
                "씨앗별": {str(s): round(base_by_seed[s], 5) for s in SEEDS_BASE},
                "씨앗 SD": round(float(np.std(list(base_by_seed.values()), ddof=1)), 5),
                "정본": "0.4710 ± 0.0021(SD) · 12도메인 · 유보 3,775"},
        "🔴 열 수별 잡음 바닥(연속 · 뽑기 12 · 씨앗 0~5)": cont,
        "카디널리티 사다리(3열 · 뽑기 6 · 씨앗 0~2)": ladder,
        "카디널리티 단조인가": mono,
        "도메인별 흔들림(연속 3열 · 팔 − 기준선)":
            dict(sorted(dom_shift.items(),
                        key=lambda x: -abs(x[1]["뽑기 평균 흔들림"]))),
        "도메인별 뽑기 원자료": dom_per_draw,
        "|흔들림| ↔ 유보 행 스피어만": [round(float(rho_s), 3), round(float(p_s), 4)],
        "판정": verdict,
        "예측 채점": scored,
        "🔴 검산 참조(11도메인 · 손 전사 아님 · 출처 병기)": REF_11DOM,
        "자": {"문턱": THR, "방어 대역": list(THR_BAND), "옛 문턱(11도메인 유물)": OLD_THR},
        "원자료": res,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    say("=== ④ 모아서 ===")
    say(json.dumps({k: v for k, v in out.items() if k != "원자료"},
                   ensure_ascii=False, indent=1))
    fh.close()


if __name__ == "__main__":
    main()
