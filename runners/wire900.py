# -*- coding: utf-8 -*-
"""노트 900 ② 배선 검사 — **게임 전용 축 넷이 정말로 설계행렬에 닿나.**

사전등록: `docs/prereg_900_levers.md` (커밋 `f3ca1d3ea` · 이 파일보다 앞선다).
물음: GitHub 이슈 #134 · 티처 #62 M2.

🔴 이 사이클의 제일 큰 함정은 **887형 중립화**다 — 축을 넣었는데 모형에 한 칸도
안 닿아 Δ 가 정확히 0 이 되는 병. `lab/forms.py:150-168` 의 `_feat` docstring 이
그 사고를 직접 적어 두고 있다(*"축을 여덟 개 덧붙여도 모형에 한 칸도 안 닿았다"*).

그래서 여기서는 **`Boost._design()`(챔피언의 진짜 설계행렬 · `lab/forms.py:1101-1130`)
의 열 수를 직접 센다.** 안 늘면 그 팔은 팔 A 이고 **안 잰 것**이다.

산출물: `runners/out900_wire.json`
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import datetime as dt                                            # noqa: E402
import hashlib                                                   # noqa: E402
import json                                                      # noqa: E402
import subprocess                                                # noqa: E402
import sys                                                       # noqa: E402
import time                                                      # noqa: E402
from pathlib import Path                                         # noqa: E402

import numpy as np                                               # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out900_wire.json"

import ff753 as FF                                               # noqa: E402
from lab import forms, guards as G                               # noqa: E402
from lab.harness import fingerprint                              # noqa: E402
from state.tri_domain import ALL5                                # noqa: E402

T = 2025.0
GAME4 = ("price", "n_category", "ram_gb", "age_rating")


# ── 팔 D 용 `_feat` --- **도메인에 축이 아예 없는 칸만** NaN 으로 ────────────
_ORIG_FEAT = forms.DirectPool._feat


def _feat_nan(A, M, names, order=None):
    """`DirectPool._feat` 과 **한 줄만** 다르다.

    그 도메인의 축 목록에 이름이 **아예 없는** 축은 0.5 가 아니라 NaN 을 넣는다.
    관측 안 된 칸(M==0)은 **그대로 0.5** 로 둔다 --- 그쪽까지 건드리면 36축
    전체가 바뀌어 팔 D 가 팔 B 와 안 갈린다.
    """
    nm = list(names or ALL5)
    ix = {a: i for i, a in enumerate(nm)}
    cols = []
    for a in (order or ALL5):
        if a in ix:
            j = ix[a]
            ok = M[:, j] > 0
            cols.append(np.where(ok, A[:, j], 0.5))
            cols.append(ok.astype(float))
        else:
            cols.append(np.full(len(A), np.nan))     # 🔴 0.5 대신 NaN
            cols.append(np.zeros(len(A)))
    return np.column_stack(cols)


def patch_nan(on: bool) -> None:
    forms.DirectPool._feat = staticmethod(_feat_nan) if on else _ORIG_FEAT


# ── 팔 ─────────────────────────────────────────────────────────────────────
BASE = forms.REGISTRY["F18_bagboost"]["cls"]


class ArmA(BASE):
    """오늘 챔피언 --- `axis_order` 가 모듈 기본 `AXIS_MODE="common"` 을 쓴다."""
    pass


class ArmB(BASE):
    axes = "union"


class ArmC(BASE):
    DOMAX = {"게임": GAME4}


class ArmD(BASE):
    """B 와 같은 축 목록. `_feat` 를 NaN 판으로 **패치한 채** 돌려야 한다."""
    axes = "union"


ARMS = {"A_common": ArmA, "B_union": ArmB, "C_domax": ArmC, "D_nanpad": ArmD}
NAN_ARMS = {"D_nanpad"}


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamp() -> dict:
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        br = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref",
                             "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception:
        head = br = "안 잡힘"
    return {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head, "git 브랜치": br,
            "🔴 코드 sha256(이 파일 · runners/wire900.py)": sha(ME),
            "참조 코드 sha256": {
                "lab/forms.py": sha(ROOT / "lab/forms.py"),
                "lab/harness.py": sha(ROOT / "lab/harness.py"),
                "lab/pairboot.py": sha(ROOT / "lab/pairboot.py"),
                "runners/ff753.py": sha(ROOT / "runners/ff753.py"),
                "docs/prereg_900_levers.md": sha(ROOT / "docs/prereg_900_levers.md")}}


def _uniq_rows(X: np.ndarray) -> int:
    """설계행의 **고유 행 수**. NaN 은 하나의 표지값으로 몰아 센다."""
    Z = np.nan_to_num(np.asarray(X, float), nan=-9.87e18,
                      posinf=9.87e18, neginf=-9.86e18)
    return int(len(np.unique(Z, axis=0)))


def cheap(cls, seed=0):
    """설계행렬만 보려는 **싼 적합**. `order/doms/names/spec` 는 진짜와 같다.

    `_design` 은 K·깊이·반복수에 안 걸린다 --- 그 셋은 나무에만 간다.
    `_traincap` 은 `default_rng(7000+seed)` 라 씨앗만 같으면 같은 행을 뽑는다.
    """
    return cls(depth=2, it=5, K=1, seed=seed)


def main():
    t0 = time.time()
    log = []

    def say(x):
        print(x, flush=True)
        log.append(x)

    data = FF.shell(FF.base())
    doms = sorted(data.dom)
    W = data.weights(T)
    fp = fingerprint(data)

    res = {"노트": 900, "무엇": "② 배선 검사 — 게임 4열이 _design() 에 닿나",
           "사전등록": "docs/prereg_900_levers.md (커밋 f3ca1d3ea)",
           "배선 스탬프": stamp()}

    # ── ㄱ 판의 뼈대 ────────────────────────────────────────────────────────
    res["ㄱ 판"] = {
        "도메인 수": len(doms), "도메인": doms,
        "도메인 == 12": len(doms) == 12,
        "유보 가중": {d: int(W[d]) for d in sorted(W)},
        "유보 가중 합": int(sum(W.values())),
        "🔴 유보 가중 합 == 3775": int(sum(W.values())) == 3775,
        "자료 sha(전체)": fp["_전체"], "자료 sha(도메인별)": fp,
    }
    say(f"ㄱ 도메인 {len(doms)} · 유보 합 {sum(W.values())} · sha {fp['_전체']}")

    # ── ㄴ common / union 실측 (티처의 36/40 을 베끼지 않는다) ──────────────
    tr = {d: sl for d, (sl, _k) in G._split(data, T).items()}
    from lab.harness import Data as _D
    train = _D(tr, data.names, {d: data.yr[d][k] for d, (_s, k) in
                                G._split(data, T).items()})
    common = forms.axis_order(train, "common")
    union = forms.axis_order(train, "union")
    per = {d: list(train.names.get(d) or ALL5) for d in train.dom}
    res["ㄴ common/union 실측"] = {
        "common 수": len(common), "union 수": len(union),
        "차(union − common)": len(union) - len(common),
        "union − common 목록": [a for a in union if a not in common],
        "common 목록": list(common),
        "학습 도메인 수": len(train.dom),
        "🔴 티처 #62 가 적은 값": {"common": 36, "union": 40},
        "티처와 일치": (len(common) == 36 and len(union) == 40),
        "도메인별 축 수": {d: len(per[d]) for d in sorted(per)},
    }
    say(f"ㄴ common={len(common)} union={len(union)} "
        f"추가={[a for a in union if a not in common]}")

    # ── ㄷ 게임 4축이 어디에 있고 유보에서 살아 있나 ─────────────────────────
    ax = {}
    for a in GAME4:
        rec = {"이 축을 가진 도메인": [d for d in sorted(per) if a in per[d]],
               "common 에 있나": a in common, "union 에 있나": a in union}
        for d in rec["이 축을 가진 도메인"]:
            A, M, y, t = data.dom[d]
            post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
            j = list(data.names.get(d) or ALL5).index(a)
            mk = M[post, j] > 0
            v = A[post, j][mk]
            rec[f"{d} 유보"] = {"행": int(post.sum()), "마스크": int(mk.sum()),
                              "고유값": int(len(np.unique(v))),
                              "값 범위": [float(np.min(v)), float(np.max(v))]
                              if len(v) else None}
        ax[a] = rec
    res["ㄷ 게임 4축 실재"] = ax
    for a in GAME4:
        say(f"ㄷ {a}: 도메인 {ax[a]['이 축을 가진 도메인']} · "
            f"common {ax[a]['common 에 있나']}")

    # ── ㄹ 🔴 _design() 열 수 --- 팔마다 · 도메인마다 ────────────────────────
    des, fitted = {}, {}
    for nm, cls in ARMS.items():
        patch_nan(nm in NAN_ARMS)
        try:
            f = G._fit_on(lambda c=cls: cheap(c, 0), data, T, seed=0)
            rec = {"axis_order 수": len(f.order),
                   "axes 속성": getattr(cls, "axes", None),
                   "DOMAX": {k: list(v) for k, v in (cls.DOMAX or {}).items()},
                   "🔴 fit 이 본 설계 열 수(m.n_features_in_)":
                       int(f.ms[0].n_features_in_),
                   "도메인별": {}}
            for d in doms:
                post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
                A, M, y, t = data.slice(d, post)
                X = f._design(d, A, M, t)
                p = np.asarray(f.predict(d, A, M, t), float)
                ur, up = _uniq_rows(X), int(len(np.unique(p[np.isfinite(p)])))
                rec["도메인별"][d] = {
                    "유보 행": int(len(y)), "설계 열": int(X.shape[1]),
                    "설계 고유행": ur, "예측 고유": up,
                    "🔴 예측 고유 <= 설계 고유행": up <= ur,
                    "NaN 칸": int(np.isnan(X).sum()),
                    "채점행(isfinite p & y)":
                        int((np.isfinite(p) & np.isfinite(y)).sum()),
                    "채점행 == 판 가중":
                        int((np.isfinite(p) & np.isfinite(y)).sum()) == W.get(d),
                }
            rec["🔴 _design 열 == fit 열"] = all(
                v["설계 열"] == rec["🔴 fit 이 본 설계 열 수(m.n_features_in_)"]
                for v in rec["도메인별"].values())
            rec["🔴 예측 고유 <= 설계 고유행 (전 도메인)"] = all(
                v["🔴 예측 고유 <= 설계 고유행"] for v in rec["도메인별"].values())
            rec["🔴 채점행 == 판 가중 (전 도메인)"] = all(
                v["채점행 == 판 가중"] for v in rec["도메인별"].values())
            des[nm] = rec
            fitted[nm] = f
            say(f"ㄹ {nm}: order {len(f.order)} · fit 열 "
                f"{rec['🔴 fit 이 본 설계 열 수(m.n_features_in_)']} · "
                f"assert(예측<=설계) {rec['🔴 예측 고유 <= 설계 고유행 (전 도메인)']}")
        finally:
            patch_nan(False)

    base_w = des["A_common"]["🔴 fit 이 본 설계 열 수(m.n_features_in_)"]
    for nm in des:
        w = des[nm]["🔴 fit 이 본 설계 열 수(m.n_features_in_)"]
        des[nm]["🔴 팔 A 대비 늘어난 열"] = int(w - base_w)
        des[nm]["🔴 이 팔은 팔 A 인가(열이 안 늘었다)"] = bool(w == base_w) \
            and nm != "A_common"
    res["ㄹ _design 열 수"] = des

    # ── ㅁ 🔴 팔 B 와 팔 C 의 설계행렬이 내용까지 같은가 ─────────────────────
    cmp_bc = {}
    fb, fc = fitted["B_union"], fitted["C_domax"]
    for d in doms:
        post = np.isfinite(data.yr[d]) & (data.yr[d] >= T)
        A, M, y, t = data.slice(d, post)
        Xb, Xc = fb._design(d, A, M, t), fc._design(d, A, M, t)
        sb = {tuple(np.round(c, 12)) for c in Xb.T}
        sc = {tuple(np.round(c, 12)) for c in Xc.T}
        cmp_bc[d] = {"B 열": int(Xb.shape[1]), "C 열": int(Xc.shape[1]),
                     "열 다중집합(순서 무시) 같나": sb == sc,
                     "B 에만 있는 열 수": len(sb - sc),
                     "C 에만 있는 열 수": len(sc - sb)}
    res["ㅁ 🔴 팔 B vs 팔 C 설계행렬"] = {
        "도메인별": cmp_bc,
        "🔴 전 도메인에서 열 집합이 같다": all(v["열 다중집합(순서 무시) 같나"]
                                    for v in cmp_bc.values()),
        "뜻": ("같으면 --- 게임 4축이 정말 게임 전용이라 union 과 DOMAX 가 "
              "같은 8열을 만든다는 뜻이고, **도메인별로 자기 축만 보는 정식화**가 "
              "패딩을 못 피한다는 증거다"),
    }
    say(f"ㅁ B vs C 열집합 일치: "
        f"{res['ㅁ 🔴 팔 B vs 팔 C 설계행렬']['🔴 전 도메인에서 열 집합이 같다']}")

    # ── ㅂ 🔴 팔 D 의 NaN 이 실제로 그 자리에만 있나 ─────────────────────────
    nanchk = {}
    for d in doms:
        v = des["D_nanpad"]["도메인별"][d]
        nanchk[d] = {"NaN 칸": v["NaN 칸"], "유보 행": v["유보 행"],
                     "기대(축 4개 × 유보 행, 게임이면 0)":
                         0 if all(a in (data.names.get(d) or []) for a in GAME4)
                         else None}
    res["ㅂ 팔 D NaN 위치"] = {
        "도메인별": nanchk,
        "게임 NaN 칸": des["D_nanpad"]["도메인별"].get("게임", {}).get("NaN 칸"),
        "팔 B 의 NaN 칸 합": int(sum(v["NaN 칸"] for v in
                                des["B_union"]["도메인별"].values())),
        "팔 D 의 NaN 칸 합": int(sum(v["NaN 칸"] for v in
                                des["D_nanpad"]["도메인별"].values())),
    }

    # ── ㅅ 문턱 · 필요 도메인 Δ (산출물에서 읽는다 --- 손 전사 금지) ──────────
    th891 = json.loads((ROOT / "runners/out891_thresh.json").read_text("utf-8"))
    th899 = json.loads((ROOT / "runners/out899_dateclust.json").read_text("utf-8"))
    R5 = float(th891["자 다섯"]["🔴 R5 합성 2σ = 채택 문턱"])
    R5d = float(th899["🔴 문턱 후보(제안 · 정본 안 바꾼다)"]["일 군집"]["R5 = 2·hypot"])
    tot = float(sum(W.values()))
    res["ㅅ 자와 필요 Δ"] = {
        "문턱(정본 · 891 R5 · 12씨앗)": R5,
        "문턱(후보 · 일 군집 · 899)": R5d,
        "유보 가중 합": int(tot),
        "🔴 그 도메인 하나로 판 문턱을 넘으려면 필요한 도메인 Δ":
            {d: {"w": int(W[d]),
                 "필요 Δ(문턱 0.00353)": round(R5 * tot / W[d], 5),
                 "필요 Δ(문턱 0.00370)": round(R5d * tot / W[d], 5)}
             for d in sorted(W)},
    }
    say(f"ㅅ 문턱 {R5} / {R5d} · 게임 하나로 넘으려면 Δ "
        f"{res['ㅅ 자와 필요 Δ']['🔴 그 도메인 하나로 판 문턱을 넘으려면 필요한 도메인 Δ']['게임']}")

    # ── ㅇ 관문 ─────────────────────────────────────────────────────────────
    gate = {
        "도메인 12": res["ㄱ 판"]["도메인 == 12"],
        "유보 합 3775": res["ㄱ 판"]["🔴 유보 가중 합 == 3775"],
        "팔 B 열이 늘었다": des["B_union"]["🔴 팔 A 대비 늘어난 열"] > 0,
        "팔 C 열이 늘었다": des["C_domax"]["🔴 팔 A 대비 늘어난 열"] > 0,
        "팔 D 열이 늘었다": des["D_nanpad"]["🔴 팔 A 대비 늘어난 열"] > 0,
        "예측 고유 <= 설계 고유행 (전 팔·전 도메인)":
            all(v["🔴 예측 고유 <= 설계 고유행 (전 도메인)"] for v in des.values()),
        "채점행 == 판 가중 (전 팔·전 도메인)":
            all(v["🔴 채점행 == 판 가중 (전 도메인)"] for v in des.values()),
        "_design 열 == fit 열 (전 팔)":
            all(v["🔴 _design 열 == fit 열"] for v in des.values()),
    }
    gate["🔴 전부 통과"] = all(gate.values())
    res["ㅇ 관문"] = gate
    res["로그"] = log
    res["초"] = round(time.time() - t0, 1)

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("=== 관문 ===", flush=True)
    print(json.dumps(gate, ensure_ascii=False, indent=1), flush=True)
    print(f"완료 · {OUT}", flush=True)


if __name__ == "__main__":
    main()
