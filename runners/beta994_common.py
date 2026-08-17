# -*- coding: utf-8 -*-
"""994 공용 — **챔피언 판을 「시간 방향 유보」에서 재기 위한 배관.**

🔴 이 파일은 «측정하지 않는다». 자료를 열고, 시간 블록을 짓고, 챔피언 경로대로
적합·채점하고, 도장을 찍는 함수만 둔다. 판정은 세 러너가 각자 자기 산출물에 낸다.

🔴🔴🔴 **설계 팔이 ⓪ 에서 찾은 것 — 사전등록 §0-나에 등기했다.**
    사이클 지시문은 *"정본 `0.470343` 은 옛 「개체 묶음」 유보(2,359 행)의 값이라
    예측이 아니라 보간이다"* 라고 적었다. **그 전제는 거짓이다.**
    · 챔피언 판 `0.470343` 은 `lab.harness.evaluate(protocol="deploy", T=2025.0)` 의
      값이고, 그 갈래는 **`yr < 2025` 로 적합하고 `yr >= 2025` 로 채점한다** ---
      **이미 시간 방향 분할이다**(학습 19,018 · 유보 3,775 · 12 도메인 · 원점 «하나»).
    · **2,359 행 개체 묶음 유보는 `runners/alpha977.py:Pool` 의 것**이고 그 풀은
      `sao941+sao959+hplt_ko` 원장 자료를 읽는다 --- **챔피언과 «다른 자료·다른 모형»이다**
      (`runners/out982_wiring.json` 의 키 `🔴🔴 개체 묶음 판(981)의 도메인별 유보 행`
      합 = 2,359 · `🔴🔴 유보 전량 행 수(블록 1~4)` = 1,892).
    · 그래서 이 사이클이 실제로 여는 물음은 **「보간이냐 예측이냐」가 아니라
      「`0.470343` 이 «원점 2025 하나»의 성질인가」**다. 원점을 넷으로 늘려 잰다.

🔴 **조항 60** --- 원점을 옮기면 **분모가 같이 움직인다.** 챔피언 자료에서 `영화`·`팝업`은
2024.477 이전에 «0 행»이고 `애니`는 블록 0 에 «0 행»이다. 그래서 채점되는 도메인 수가
원점마다 다르다. 이 파일은 그 수를 **버림 장부**(조항 59 개정판)로 낱낱이 센다.
"""
import collections
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
for _p in (str(ROOT), str(ROOT / "runners")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import ff753 as FF                                          # noqa: E402
from lab.harness import Data, MIN_TRAIN                      # noqa: E402

# ── 사전등록 상수 (측정 전에 박았다 · docs/prereg_994_time_holdout_board.md) ──
SEEDS = tuple(range(12))          #: 🔴 `ff753.RULER_SEEDS` 와 같은 목록 --- 정본 12 씨앗
T_CANON = 2025.0                  #: 정본 원점 (챔피언 판 0.470343 이 선 자리)
NBLOCK = 5                        #: 시간 블록 수
QS = (0.2, 0.4, 0.6, 0.8)         #: 블록 절단 분위 --- 982 와 «같은 절단 규칙»
ORIGINS = (1, 2, 3, 4)            #: 원점 --- 학습 = 블록 < k · 유보 = 블록 k
MIN_SCORE = 20                    #: `lab/harness.py:_score_one` 의 최소 채점 행
B_DOM = 2000                      #: 도메인 군집 SE 뽑기 수
DOM_BOOT_SEED = 994

#: 🔴 챔피언 판 정본 --- `runners/text680.py:64 BOARD_RHO` 와 `runners/out898_board.json`
#: 의 «전정밀» 값. 여기서 «고치지 않는다»(정본 갱신은 정비 팔이 판정 뒤에 한다).
BOARD_RHO_FULL = 0.47034252170476804
BOARD_S0_FULL = 0.4731063028988084     #: `runners/board898.py:112 EXPECT_S0["B(동률평균)"]`
BOARD_W_SUM = 3775
BOARD_NDOM = 12
TOL_S0 = 1e-12
TOL_MEAN = 1e-9

#: 🔴 규칙 C --- 코드 지문이 덮는 파일. **`git` 을 안 부른다**(HEAD 스탬프는 폐기됐다).
SRC = (
    "runners/beta994_common.py",
    "runners/beta994_tf.py",
    "runners/beta994_org.py",
    "runners/beta994_ctl.py",
    "runners/ff753.py",
    "lab/harness.py",
    "lab/forms.py",
    "lab/loop.py",
    "state/rank_test.py",
)

#: 🔴 조항 59 개정판 --- 「없다」와 「못 봤다」와 「쟀는데 설정이 버렸다」는 셋이다.
DROP_ZERO = "0 행"                       # 그 칸에 행이 «없다»
DROP_GATE = "행부족 --- 쟀는데 설정이 버렸다"   # 행은 있는데 MIN_SCORE 미만
DROP_TRAIN = "학습부족 --- 쟀는데 설정이 버렸다"  # 학습 쪽이 MIN_TRAIN 미만
DROP_NAN = "결측 --- rho 가 유한하지 않다"
DROP_PRED = "결측 --- 예측이 유한한 행이 MIN_SCORE 미만"
SCORED = "채점"


# ══════════════════════════════════════════════════════════════════════
# 도장 (규칙 C · 조항 66·67) --- 🔴 `git` 을 한 번도 안 부른다
# ══════════════════════════════════════════════════════════════════════
def now_utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha_file(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    h = hashlib.sha256()
    with open(str(p), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def code_stamp():
    return collections.OrderedDict([(r, sha_file(r)) for r in SRC])


def sha_arr(a):
    return hashlib.sha256(np.ascontiguousarray(np.asarray(a)).tobytes()).hexdigest()


def stamp(t0, cs0, data_fp):
    """🔴 코드 sha256 · 끝 시각(UTC) · 자료 지문. **`git HEAD` 스탬프 없음**(폐기)."""
    cs1 = code_stamp()
    return collections.OrderedDict([
        ("언제(시작 · UTC)", t0),
        ("언제(끝 · UTC)", now_utc()),
        ("🔴 코드 sha256(시작)", cs0),
        ("🔴 코드 sha256(끝)", cs1),
        ("🔴 시작=끝", bool(cs0 == cs1)),
        ("분모: 도장이 덮는 소스 파일", len(cs1)),
        ("🔴 소스 sha 결측", [k for k, v in cs1.items() if v is None]),
        ("🔴 자료 지문(도메인별 배열 sha256)", data_fp),
        ("분모: 자료 지문 도메인", len(data_fp)),
        ("🔴 git HEAD 스탬프", "폐기됐다 --- 긴 러너에선 「시작 시점」이라 뜻이 없다"),
    ])


# ══════════════════════════════════════════════════════════════════════
# 자료 · 시간 블록
# ══════════════════════════════════════════════════════════════════════
def load():
    """🔴 챔피언 자료 --- `runners/board898.py:140` 과 «글자까지» 같은 한 줄."""
    d0 = FF.shell(FF.base())
    return d0, sorted(d0.dom)


def data_fp(d0, doms):
    """자료 지문 --- 도메인별 (A, M, y, t, yr) 배열의 sha256."""
    fp = collections.OrderedDict()
    for d in doms:
        A, M, y, t = d0.dom[d]
        fp[d] = collections.OrderedDict([
            ("행", int(len(y))),
            ("y", sha_arr(np.asarray(y, float))),
            ("yr", sha_arr(np.asarray(d0.yr[d], float))),
            ("A", sha_arr(np.asarray(A, float))),
            ("M", sha_arr(np.asarray(M, float))),
        ])
    return fp


def labeled(d0, d):
    """라벨과 연도가 «둘 다» 유한한 행. 블록은 이 행들 위에서만 센다."""
    y = np.asarray(d0.dom[d][2], float)
    yr = np.asarray(d0.yr[d], float)
    return np.isfinite(y) & np.isfinite(yr)


def blocks(d0, doms):
    """🔴 시간 블록 --- **전 도메인 라벨 행을 모은 `yr` 의 20/40/60/80 분위**로 자른다.

    도메인마다 따로 자르지 않는다. 그러면 「같은 블록 = 같은 시대」가 깨지고
    원점이 도메인마다 다른 날짜를 뜻하게 된다.
    """
    allyr = np.concatenate([np.asarray(d0.yr[d], float)[labeled(d0, d)]
                            for d in doms])
    cuts = [float(np.quantile(allyr, q)) for q in QS]
    edges = [-1e9] + cuts + [1e9]
    blk = {}
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        lb = labeled(d0, d)
        blk[d] = [(yr >= edges[k]) & (yr < edges[k + 1]) & lb
                  for k in range(NBLOCK)]
    return collections.OrderedDict([
        ("분위", list(QS)), ("절단(yr)", [round(c, 6) for c in cuts]),
        ("전량 라벨 행", int(len(allyr))),
        ("블록별 행", [int(sum(int(blk[d][k].sum()) for d in doms))
                    for k in range(NBLOCK)]),
        ("도메인별 블록 행", collections.OrderedDict(
            [(d, [int(blk[d][k].sum()) for k in range(NBLOCK)]) for d in doms])),
    ]), blk, edges


def train_mask_lt(blk, doms, k):
    """학습 = 블록 `< k` 합집합."""
    return {d: np.logical_or.reduce(blk[d][:k]) for d in doms}


def canon_masks(d0, doms):
    """정본 원점 --- 학습 `yr < 2025` · 유보 `yr >= 2025`(둘 다 라벨 유한)."""
    tr, ho = {}, {}
    for d in doms:
        yr = np.asarray(d0.yr[d], float)
        lb = labeled(d0, d)
        tr[d] = lb & (yr < T_CANON)
        ho[d] = lb & (yr >= T_CANON)
    return tr, ho


# ══════════════════════════════════════════════════════════════════════
# 적합 · 채점 --- `lab/harness.py:evaluate` 의 deploy 갈래를 «글자 그대로»
# ══════════════════════════════════════════════════════════════════════
def fit(d0, tmask, seed):
    """돌려주는 것 = (적합된 정식화 or None, 학습 장부)."""
    train, tm = {}, {}
    ledger = collections.OrderedDict()
    for d in sorted(d0.dom):
        k = np.asarray(tmask.get(d), bool) if tmask.get(d) is not None else None
        n = 0 if k is None else int(k.sum())
        if k is not None and n >= MIN_TRAIN:
            train[d] = d0.slice(d, k)
            tm[d] = k
            ledger[d] = {"학습 행": n, "쓰였나": True}
        else:
            ledger[d] = {"학습 행": n, "쓰였나": False,
                         "까닭": DROP_ZERO if n == 0 else DROP_TRAIN}
    if len(train) < 3:
        return None, collections.OrderedDict([
            ("도메인별", ledger), ("학습 도메인", len(train)),
            ("학습 행 합", int(sum(v["학습 행"] for v in ledger.values()
                                if v["쓰였나"]))),
            ("🔴 못 돌았다", "학습 도메인이 3 미만 --- harness 가 {} 를 낸다")])
    f = FF.CLS(seed=int(seed))
    f.fit(Data(train, d0.names, {d: d0.yr[d][tm[d]] for d in train}))
    return f, collections.OrderedDict([
        ("도메인별", ledger), ("학습 도메인", len(train)),
        ("학습 행 합", int(sum(v["학습 행"] for v in ledger.values()
                            if v["쓰였나"]))),
        ("🔴 못 돌았다", None)])


def score(d0, f, hmask, doms, sub=None):
    """도메인별 스피어만. 🔴 **동률 평균**(`scipy.stats.spearmanr`) --- 오늘의 정본.

    `sub` 가 있으면 `sub[d]` 는 **그 도메인 유보 행 안에서 고를 자리 색인**이다
    (하향 표본 팔이 쓴다). 없으면 전량.

    돌려주는 것 = (도메인별 {rho, n}, 버림 장부).
    """
    out, drop = collections.OrderedDict(), collections.OrderedDict()
    if f is None:
        for d in doms:
            drop[d] = DROP_TRAIN
        return out, drop
    for d in doms:
        m = np.asarray(hmask.get(d), bool) if hmask.get(d) is not None else None
        if m is None or int(m.sum()) == 0:
            drop[d] = DROP_ZERO
            continue
        A_, M_, y_, t_ = d0.slice(d, m)
        if sub is not None:
            ix = np.asarray(sub[d], int)
            A_, M_, y_, t_ = A_[ix], M_[ix], y_[ix], t_[ix]
        if len(y_) < MIN_SCORE:
            drop[d] = DROP_GATE
            continue
        p = np.asarray(f.predict(d, A_, M_, t_), float)
        ok = np.isfinite(p) & np.isfinite(y_)
        if int(ok.sum()) < MIN_SCORE:
            drop[d] = DROP_PRED
            continue
        rho = float(spearmanr(p[ok], y_[ok])[0])
        if not np.isfinite(rho):
            drop[d] = DROP_NAN
            continue
        out[d] = {"rho": rho, "n": int(ok.sum()),
                  "n(유보 행 전량)": int(len(y_))}
    return out, drop


def pooled(sc):
    """`Data.pooled` 와 같은 가중(채점 표본 수). 🔴 도메인 «사전 차례»로 더한다."""
    num = den = 0.0
    for d in sorted(sc):
        num += sc[d]["rho"] * sc[d]["n"]
        den += sc[d]["n"]
    return (num / den) if den else float("nan")


def pooled_w(rho_by_dom, w_by_dom):
    """🔴 가중을 «밖에서» 준다 --- ctl 의 「도메인 혼합 재가중」이 쓴다."""
    num = den = 0.0
    for d in sorted(rho_by_dom):
        if d in w_by_dom and w_by_dom[d] > 0:
            num += float(rho_by_dom[d]) * float(w_by_dom[d])
            den += float(w_by_dom[d])
    return (num / den) if den else float("nan")


# ══════════════════════════════════════════════════════════════════════
# SE 둘 --- 씨앗 SE 와 도메인 «군집» SE
# ══════════════════════════════════════════════════════════════════════
def seed_se(vals):
    a = np.asarray([v for v in vals if np.isfinite(v)], float)
    if len(a) < 2:
        return collections.OrderedDict([
            ("씨앗 수", int(len(a))), ("평균", float(a.mean()) if len(a) else None),
            ("SD(ddof=1)", None), ("씨앗 SE", None)])
    return collections.OrderedDict([
        ("씨앗 수", int(len(a))), ("평균", float(a.mean())),
        ("SD(ddof=1)", float(a.std(ddof=1))),
        ("씨앗 SE", float(a.std(ddof=1) / np.sqrt(len(a)))),
    ])


def dom_cluster_se(rho_by_dom, w_by_dom, B=B_DOM, seed=DOM_BOOT_SEED):
    """🔴 도메인 «군집» SE --- 도메인을 복원 재표집해 pooled 를 다시 낸다.

    씨앗 SE 는 **모형 무작위성**만 잰다. 판 ρ 가 12(또는 그보다 적은) 도메인의
    가중 평균이므로 **도메인이 진짜 군집**이고 그 SE 가 훨씬 크다. 둘 다 낸다.
    """
    ds = sorted(rho_by_dom)
    if len(ds) < 2:
        return collections.OrderedDict([("도메인 수", len(ds)), ("도메인 군집 SE", None),
                                        ("뽑기 수", 0)])
    r = np.asarray([rho_by_dom[d] for d in ds], float)
    w = np.asarray([w_by_dom[d] for d in ds], float)
    rng = np.random.RandomState(int(seed))
    bs = np.empty(int(B))
    for b in range(int(B)):
        ix = rng.randint(0, len(ds), len(ds))
        den = w[ix].sum()
        bs[b] = (r[ix] * w[ix]).sum() / den if den > 0 else np.nan
    ok = np.isfinite(bs)
    return collections.OrderedDict([
        ("도메인 수", len(ds)), ("뽑기 수", int(B)),
        ("도메인 군집 SE", float(bs[ok].std(ddof=1))),
        ("유한 뽑기", int(ok.sum())),
        ("2.5%", float(np.percentile(bs[ok], 2.5))),
        ("97.5%", float(np.percentile(bs[ok], 97.5))),
    ])


def drop_ledger(drops, doms):
    """🔴 조항 59 개정판 --- 넷을 «구분해» 센다. 합이 시도 도메인 수와 맞아야 한다."""
    cnt = collections.Counter()
    for d in doms:
        cnt[drops.get(d, SCORED)] += 1
    return collections.OrderedDict([
        ("시도 도메인", len(doms)),
        ("채점", int(cnt[SCORED])),
        (DROP_ZERO, int(cnt[DROP_ZERO])),
        (DROP_GATE, int(cnt[DROP_GATE])),
        (DROP_TRAIN, int(cnt[DROP_TRAIN])),
        (DROP_NAN, int(cnt[DROP_NAN])),
        (DROP_PRED, int(cnt[DROP_PRED])),
        ("🔴 합 = 시도 도메인인가", bool(sum(cnt.values()) == len(doms))),
        ("도메인별", collections.OrderedDict(
            [(d, drops.get(d, SCORED)) for d in doms])),
    ])


def say(msg):
    """🔴 진행 --- **stderr 로만** 낸다. 러너는 자기 산출물 하나 말고 파일을 안 만든다."""
    sys.stderr.write("%s  %s\n" % (now_utc(), msg))
    sys.stderr.flush()


def write(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1),
                          encoding="utf-8")
