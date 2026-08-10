# -*- coding: utf-8 -*-
"""이슈 #113 수리 — **896 팔 B 를 12씨앗으로 다시 잰다.**

티처 #59 C3 · M1 · M9 · M10 이 한 덩어리다.

    C3  팔 B-ㄱ 의 "신호 몫 0.00318 = 문턱의 0.90배" 가 **씨앗 하나를 빼면 뒤집힌다**
    M1  🔴 자와 잰 것의 씨앗 수가 다르다 --- 문턱 0.00353 은 `thresh891` 의
        **12씨앗** 자인데 896 은 `ff753.SEEDS`(**6씨앗**)로 쟀다. 씨앗 성분만 √2 어긋난다
    M9  ㄴ 팔의 「패」도 LOO 6개 중 5개에서 구간이 0 을 문다
    M10 두 팔의 널평균이 기준선에서 서로 다른 쪽으로 벌어진다(마스크 넓이만 달라도)

**이 파일이 하는 일**

    loo     896 산출물의 씨앗별 판에서 티처의 LOO 를 **내가 다시 낸다**(적합 0)
    B       팔 B 를 **12씨앗**으로 다시 잰다(9판 × 12씨앗 = 108적합)
    thresh  SEEDS 정본화 뒤 `thresh891` 을 다시 돌려 문턱이 0.00353 인지 확인
            (🔴 조항 59 새 형태: 고치는 작업의 성공 ≠ 그 숫자가 옳음)

🔴 옛 6씨앗 값을 **지우지 않는다** --- 산출물에 병기한다(이 실험실은 이력을 안 뭉갠다).
🔴 티처 #59 M7: `dose896.stamp()` 은 `__file__`(=dose896.py)을 해싱한다.
   여기서는 **이 파일의 sha** 를 박고 참조 파일 sha 를 따로 병기한다.
"""
import os

#: 적합은 사실상 단일 코어다(노트 892 실측) --- 스레드를 못박고 프로세스로 병렬한다.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import datetime as dt                                           # noqa: E402
import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import multiprocessing as mp                                    # noqa: E402
import shutil                                                   # noqa: E402
import subprocess                                               # noqa: E402
import sys                                                      # noqa: E402
import time                                                     # noqa: E402
from pathlib import Path                                        # noqa: E402

import numpy as np                                              # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()

import dose896 as D                                             # noqa: E402
import ff753 as FF                                              # noqa: E402
from lab import pairboot as PB                                  # noqa: E402

T = 2025.0
SEEDS12 = tuple(FF.RULER_SEEDS)        #: 🔴 정본(ff753 한 곳) --- 문턱과 같은 분모
SEEDS6 = tuple(FF.SEEDS)               #: 896 이 쓴 옛 목록(병기용)
NULL_DRAWS = D.NULL_DRAWS
THRESH = D.THRESH                      #: 0.00353 (노트 891 R5)
B_BOOT = D.B_BOOT
BOOT_SEED = D.BOOT_SEED
BASE_OK = D.BASE_OK
ARMS = ("ㄱ 존재 이진", "ㄴ 양(설명문 글자수)")
NPROC = 8

#: 티처 #59 가 이슈 #113 본문에 적어 둔 값 --- **대조용으로만** 박는다.
TEACHER = {
    "ㄱ 씨앗별 짝": [-0.00031, 0.00243, 0.00312, 0.00281, 0.00356, 0.00744],
    "ㄱ LOO 신호 몫": {0: 0.00387, 1: 0.00332, 2: 0.00319, 3: 0.00325,
                    4: 0.00310, 5: 0.00232},
    "ㄱ LOO BCa": {0: [0.00280, 0.00589], 1: [0.00115, 0.00571],
                  2: [0.00109, 0.00559], 3: [0.00115, 0.00557],
                  4: [0.00106, 0.00557], 5: [0.00031, 0.00310]},
    "ㄴ LOO BCa 상한(M9)": {0: 0.00010, 1: 0.00059, 2: 0.00001,
                          3: 0.00002, 4: 0.00010},
    "M10 ㄱ 널평균": 0.46529, "M10 ㄴ 널평균": 0.46989, "M10 차": 0.00461,
}

#: 노트 891 이 R5 를 만든 성분(out891_thresh.json 에서 **읽는다** --- 손 전사 금지)
THRESH_REF = ROOT / "runners/out891_thresh.json"


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamp() -> dict:
    """🔴 티처 #59 M7 --- `__file__` 이 **이 파일**이어야 한다."""
    try:
        head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        br = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                            capture_output=True, text=True).stdout.strip()
    except Exception:
        head = br = "안 잡힘"
    return {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": head, "git 브랜치": br,
        "🔴 코드 sha256(이 파일 · runners/dose113.py)": sha(ME),
        "참조 코드 sha256": {
            "runners/dose896.py": sha(ROOT / "runners/dose896.py"),
            "runners/ff753.py": sha(ROOT / "runners/ff753.py"),
            "runners/thresh891.py": sha(ROOT / "runners/thresh891.py"),
            "lab/pairboot.py": sha(ROOT / "lab/pairboot.py"),
        },
        "⚠ M7 주의": "dose896.stamp() 은 dose896.py 를 해싱한다 --- 여기서 안 쓴다",
    }


def _bca_mean(vals):
    """씨앗 짝 값 배열 → (점추정, lo, hi, 종류, 군집병기). 규약 47 · BCa."""
    a = np.asarray(vals, float)
    cl, wire = PB.solo_clusters(len(a))
    try:
        pt, lo, hi, kind = PB.cluster_boot(lambda ix: float(np.mean(a[ix])),
                                           cl, B=B_BOOT, seed=BOOT_SEED)
        fb = None
    except Exception as e:                       # 폴백은 **사유를 적는다**(규약 47)
        pt, lo, hi, kind, fb = float(a.mean()), float("nan"), float("nan"), "실패", repr(e)
    return pt, lo, hi, kind, fb, wire


# ── ① 티처 LOO 재현 (적합 0) ────────────────────────────────────────────────
def loo(src=None, tag="896 산출물(6씨앗 · 5자리 반올림)"):
    """`out896_armB.json` 의 **씨앗별 판**에서 짝 값과 LOO 를 다시 낸다."""
    src = src or (ROOT / "runners/out896_armB.json")
    BD = json.loads(Path(src).read_text(encoding="utf-8"))["판 원자료"]
    seeds = sorted(int(s) for s in BD["기준선"]["씨앗별"])
    base = {int(s): v for s, v in BD["기준선"]["씨앗별"].items()}
    out = {"원천": str(Path(src).relative_to(ROOT)), "무엇": tag,
           "씨앗": seeds, "기준선 씨앗별": base}
    for nm in ARMS:
        real = {int(s): v for s, v in BD[f"{nm} · 진짜"]["씨앗별"].items()}
        nul = {s: float(np.mean([BD[f"{nm} · 널 {d}"]["씨앗별"][str(s)]
                                 for d in NULL_DRAWS])) for s in seeds}
        paired = np.array([real[s] - nul[s] for s in seeds])
        full_pt, full_lo, full_hi, kind, fb, wire = _bca_mean(paired)
        rec = {
            "씨앗별 짝(진짜 − 널평균)": [round(float(x), 5) for x in paired],
            "씨앗별 진짜 판": {str(s): round(real[s], 5) for s in seeds},
            "씨앗별 널평균 판": {str(s): round(nul[s], 5) for s in seeds},
            "전체 신호 몫": round(float(paired.mean()), 5),
            "전체 문턱 배수": round(float(paired.mean()) / THRESH, 3),
            "전체 BCa 95%": [round(full_lo, 5), round(full_hi, 5)],
            "전체 판정": PB.verdict(full_lo, full_hi), "구간 종류": kind,
            "구간 폴백 사유": fb, "군집 병기": wire,
            "LOO": {},
        }
        for i, s in enumerate(seeds):
            keep = np.delete(paired, i)
            pt, lo, hi, k2, fb2, _ = _bca_mean(keep)
            rec["LOO"][str(s)] = {
                "신호 몫": round(float(keep.mean()), 5),
                "문턱 배수": round(float(keep.mean()) / THRESH, 3),
                "문턱 넘나": bool(keep.mean() > THRESH),
                "BCa 95%": [round(lo, 5), round(hi, 5)],
                "판정": PB.verdict(lo, hi), "구간 종류": k2, "폴백 사유": fb2}
        out[nm] = rec
    # 티처 값과 대조
    my_g = out[ARMS[0]]["씨앗별 짝(진짜 − 널평균)"]
    cmp_ = {
        "ㄱ 씨앗별 짝 일치": my_g == TEACHER["ㄱ 씨앗별 짝"],
        "ㄱ 씨앗별 짝(내 값)": my_g, "ㄱ 씨앗별 짝(티처)": TEACHER["ㄱ 씨앗별 짝"],
        "ㄱ LOO 신호 몫 일치": {str(s): (out[ARMS[0]]["LOO"][str(s)]["신호 몫"],
                                    TEACHER["ㄱ LOO 신호 몫"][s],
                                    abs(out[ARMS[0]]["LOO"][str(s)]["신호 몫"]
                                        - TEACHER["ㄱ LOO 신호 몫"][s]) <= 1e-5)
                            for s in range(6)},
        "ㄱ LOO BCa 일치": {str(s): (out[ARMS[0]]["LOO"][str(s)]["BCa 95%"],
                                 TEACHER["ㄱ LOO BCa"][s],
                                 all(abs(a - b) <= 1e-5 for a, b in
                                     zip(out[ARMS[0]]["LOO"][str(s)]["BCa 95%"],
                                         TEACHER["ㄱ LOO BCa"][s])))
                         for s in range(6)},
        "ㄴ LOO BCa 상한 일치(M9)": {
            str(s): (out[ARMS[1]]["LOO"][str(s)]["BCa 95%"][1],
                     TEACHER["ㄴ LOO BCa 상한(M9)"][s],
                     abs(out[ARMS[1]]["LOO"][str(s)]["BCa 95%"][1]
                         - TEACHER["ㄴ LOO BCa 상한(M9)"][s]) <= 1e-5)
            for s in range(5)},
        "🔴 ㄴ 6개 중 몇 개가 0 을 무나":
            sum(1 for s in range(6)
                if out[ARMS[1]]["LOO"][str(s)]["판정"] == "판정 불능"),
    }
    out["🔴 티처 대조"] = cmp_
    return out


# ── M10 (추가 적합 없이 산출물에서) ────────────────────────────────────────
def m10(BD, seeds, wire, cov, W):
    """두 팔의 **널평균**이 기준선에서 어느 쪽으로 얼마나 벌어지나."""
    base = float(np.mean([BD["기준선"]["씨앗별"][s] for s in seeds]))
    r = {"기준선 판": round(base, 5), "씨앗 수": len(seeds)}
    for nm in ARMS:
        nul = float(np.mean([np.mean([BD[f"{nm} · 널 {d}"]["씨앗별"][s]
                                      for d in NULL_DRAWS]) for s in seeds]))
        rows = int(sum(wire[nm][k]["관측"] for k in wire[nm]
                       if isinstance(wire[nm][k], dict) and "관측" in wire[nm][k]))
        post_rows = int(sum(W.get(k, 0) for k in W
                            if isinstance(wire[nm].get(k), dict)
                            and wire[nm][k]["관측"] > 0))
        r[nm] = {"널평균 판": round(nul, 5),
                 "기준선 대비": round(nul - base, 5),
                 "마스크 넓이(관측 행 · 전체)": rows,
                 "마스크 넓이(채점 유보 행)": post_rows,
                 "채택 도메인": sorted(k for k in wire[nm]
                                  if isinstance(wire[nm].get(k), dict)
                                  and wire[nm][k]["관측"] > 0)}
    dif = r[ARMS[0]]["널평균 판"] - r[ARMS[1]]["널평균 판"]
    r["🔴 두 널평균 차"] = round(dif, 5)
    r["🔴 차 / 문턱"] = round(abs(dif) / THRESH, 3)
    r["🔴 뜻"] = (
        "같은 절차(값만 섞고 마스크 무늬 보존)·같은 백분위 1열인데 **마스크 넓이만** 달라도 "
        f"널평균이 문턱의 {round(abs(dif)/THRESH,2)}배만큼 갈린다. "
        "문턱 0.00353 은 노트 891 이 **12도메인 전면 난수열**(널 팔 쌍 A−B)로 잰 자이고 "
        "**이 마스크들로 보정된 자가 아니다** --- 마스크가 좁을수록/넓을수록 널 자체가 "
        "기준선에서 다른 쪽으로 밀린다. 두 팔의 신호 몫을 같은 문턱에 대는 것은 "
        "**팔 안에서 짝(진짜−널)을 뺀 뒤에만** 성립하고, 팔 사이 비교에는 안 선다.")
    return r


# ── 병합률(티처 #59 m3) ────────────────────────────────────────────────────
def merge_rates(d0, post, dz, cov):
    """팔 A 가 쓴 행 집합의 **프랜차이즈 병합률**을 센다(적합 0).

    `lab/pairboot.py:62-63` 은 `merged == 0` 일 때만 「⚠ 무군집」을 띄운다.
    병합이 **몇 줄이라도** 있으면 병기가 안 뜨는데, 실제 병합률이 3.3% / 1.0%
    면 사실상 행 부트다 --- **폭 과소 방향**인데 경고가 없다.
    """
    from ingest.news_counts import titles
    out = {}
    for nm, ax in dz.items():
        use = [k for k in sorted(d0.dom) if cov[nm][k]["채택"]]
        ti, per = [], {}
        for k in use:
            v, m = ax[k]
            te = post[k]
            sel = (m[te] > 0) & np.isfinite(v[te])
            t_ = titles(k)
            if t_ is not None and len(t_) == len(te):
                tt = [str(x) for x in np.asarray(t_, object)[te][sel]]
            else:
                tt = ["" for _ in range(int(sel.sum()))]
            per[k] = {"행": int(sel.sum()), "제목 원천": t_ is not None}
            ti += tt
        cl, wire = PB.clusters_of(ti)
        out[nm] = {
            "행": wire["행"], "군집": wire["군집"], "병합": wire["병합"],
            "🔴 병합률": round(wire["병합"] / max(wire["행"], 1), 4),
            "⚠ 무군집 병기 떴나": "⚠ 무군집" in wire,
            "🔴 병기 없이 사실상 행 부트인가":
                bool(wire["병합"] > 0 and wire["병합"] / max(wire["행"], 1) < 0.10),
            "도메인별": per,
            "근거": "lab/pairboot.py:62-63 --- merged == 0 일 때만 병기가 뜬다",
        }
    return out


# ── ② 팔 B 12씨앗 ──────────────────────────────────────────────────────────
def stageB(seeds=SEEDS12, out_name="out113_armB12.json"):
    import ff753 as FF_
    t0 = time.time()
    seeds = tuple(int(s) for s in seeds)
    d0 = FF_.shell(FF_.base())
    doms = sorted(d0.dom)
    post = {k: (np.isfinite(np.asarray(d0.yr[k], float))
                & (np.asarray(d0.yr[k], float) >= T)) for k in doms}
    W = d0.weights(T)
    tot = sum(W.values())
    dz = D.doses(d0)
    cov = {nm: D.coverage(d0, v, post) for nm, v in dz.items()}

    # ── 배선 검사 (측정 전) ────────────────────────────────────────────────
    wire, axes = {}, {}
    for nm, ax in dz.items():
        keep = {k for k in doms if cov[nm][k]["채택"]}
        real = D._pct_axis(ax, post, keep=keep)
        axes[(nm, "진짜")] = real
        w = {}
        for k in doms:
            v, m = real[k]
            te = post[k]
            mm = np.asarray(m) > 0
            uniq = int(len(np.unique(np.asarray(v)[mm])))
            w[k] = {"관측": int(mm.sum()), "행": len(v),
                    "덮음률": round(float(mm.mean()), 4),
                    "유보 덮음률": round(float((mm & te).sum()
                                        / max(int(te.sum()), 1)), 4),
                    "고유값": uniq,
                    "🔴 조용한 중립화": bool(mm.sum() == 0 or uniq < 2)}
        wire[nm] = w
        wire[nm]["🔴 등록된 배제(사전등록 ⓓ)"] = sorted(set(doms) - keep)
        for ds in NULL_DRAWS:
            axes[(nm, f"널 {ds}")] = D._pct_axis(ax, post, shuffle_seed=ds, keep=keep)

    def dig(a, j):
        h = hashlib.sha256()
        for k in sorted(a):
            h.update(np.ascontiguousarray(np.asarray(a[k][j], np.float32)).tobytes())
        return h.hexdigest()[:16]

    shas = {f"{nm} · {tag}": {"값 sha": dig(a, 0), "마스크 sha": dig(a, 1)}
            for (nm, tag), a in axes.items()}
    for nm in dz:
        rm = dig(axes[(nm, "진짜")], 1)
        shas[f"{nm} · 마스크 무늬 보존"] = all(
            dig(axes[(nm, f"널 {d}")], 1) == rm for d in NULL_DRAWS)
        shas[f"{nm} · 널이 진짜와 다른 값"] = all(
            dig(axes[(nm, f"널 {d}")], 0) != dig(axes[(nm, "진짜")], 0)
            for d in NULL_DRAWS)

    # ── 108 적합 ──────────────────────────────────────────────────────────
    jobs = [("기준선", None)] + [(f"{nm} · {tag}", a) for (nm, tag), a in axes.items()]
    tasks = [(name, a, s) for (name, a) in jobs for s in seeds]
    print(f"팔 B: 판 {len(jobs)}개 × 씨앗 {len(seeds)} = {len(tasks)} 적합 "
          f"(프로세스 {NPROC})", flush=True)
    with mp.Pool(NPROC) as pool:
        res = pool.map(D._board_one, tasks)

    BD, MISS = {}, {}
    for name, seed, sc, pooled in res:
        BD.setdefault(name, {"씨앗별": {}, "도메인": {}, "도메인 씨앗수": {}})
        BD[name]["씨앗별"][str(seed)] = pooled
        for k, v in sc.items():
            if np.isfinite(v):
                BD[name]["도메인"].setdefault(k, []).append(float(v))
                BD[name]["도메인 씨앗수"][k] = BD[name]["도메인 씨앗수"].get(k, 0) + 1
        MISS.setdefault(name, {})[str(seed)] = sorted(set(W) - set(sc))
    for name in BD:
        v = [BD[name]["씨앗별"][str(s)] for s in seeds]
        BD[name]["판"] = float(np.mean(v))
        BD[name]["씨앗SD"] = float(np.std(v, ddof=1))
        BD[name]["도메인"] = {k: float(np.mean(a)) for k, a in BD[name]["도메인"].items()}

    # 🔴 도메인별 **실제 투입 행수**와 조용한 탈락 회계
    rows_in = {k: {"채점 유보 행(= 판 가중 · 라벨 유한)": int(W.get(k, 0)),
                   "유보 행(라벨 결측 포함)": int(post[k].sum()),
                   "🔴 라벨 결측": int(post[k].sum() - W.get(k, 0)),
                   "판 가중": round(W.get(k, 0) / tot, 5)} for k in doms}
    silent = {name: {k: len(seeds) - BD[name]["도메인 씨앗수"].get(k, 0) for k in W
                     if BD[name]["도메인 씨앗수"].get(k, 0) < len(seeds)}
              for name in BD}

    base = BD["기준선"]["판"]
    ss = [str(s) for s in seeds]
    s6 = [str(s) for s in SEEDS6]

    verdicts = {}
    for nm in dz:
        real = BD[f"{nm} · 진짜"]
        nulmean = {s: float(np.mean([BD[f"{nm} · 널 {d}"]["씨앗별"][s]
                                     for d in NULL_DRAWS])) for s in ss}
        paired = np.array([real["씨앗별"][s] - nulmean[s] for s in ss])
        nl = [BD[f"{nm} · 널 {d}"]["판"] for d in NULL_DRAWS]
        sig = real["판"] - float(np.mean(nl))
        net = real["판"] - base
        pt, lo, hi, kind, fb, cwire = _bca_mean(paired)
        fb_note = ("⚠ 씨앗 짝 부트 --- 행 군집이 아니라 **씨앗** 재표집이다. "
                   "행 잡음은 이 구간에 안 들어간다(병기 의무)")
        # 옛 6씨앗 부분집합(같은 적합에서 · 896 재현 대조)
        p6 = np.array([real["씨앗별"][s] - nulmean[s] for s in s6])
        pt6, lo6, hi6, kind6, fb6, _ = _bca_mean(p6)
        sig6 = (float(np.mean([real["씨앗별"][s] for s in s6]))
                - float(np.mean([np.mean([BD[f"{nm} · 널 {d}"]["씨앗별"][s]
                                          for d in NULL_DRAWS]) for s in s6])))
        net6 = (float(np.mean([real["씨앗별"][s] for s in s6]))
                - float(np.mean([BD["기준선"]["씨앗별"][s] for s in s6])))
        # LOO on 12 seeds
        loo12 = {}
        for i, s in enumerate(ss):
            kp = np.delete(paired, i)
            loo12[s] = {"신호 몫": round(float(kp.mean()), 5),
                        "문턱 배수": round(float(kp.mean()) / THRESH, 3),
                        "문턱 넘나": bool(kp.mean() > THRESH)}
        per = {}
        for k in set(real["도메인"]) & set(BD["기준선"]["도메인"]):
            pm = float(np.mean([BD[f"{nm} · 널 {d}"]["도메인"].get(k, np.nan)
                                for d in NULL_DRAWS]))
            per[k] = {"신호 몫": round(real["도메인"][k] - pm, 4),
                      "순효과": round(real["도메인"][k] - BD["기준선"]["도메인"][k], 4),
                      "채점 유보 행": int(W.get(k, 0)),
                      "유보 덮음률": wire[nm][k]["유보 덮음률"],
                      "판 기여": round((real["도메인"][k] - pm) * W.get(k, 0) / tot, 5),
                      "🔴 점수 난 씨앗 수": BD[f"{nm} · 진짜"]["도메인 씨앗수"].get(k, 0)}
        verdicts[nm] = {
            "🔴 12씨앗": {
                "기준선 판": round(base, 5), "진짜 판": round(real["판"], 5),
                "널 판 셋": {str(d): round(BD[f"{nm} · 널 {d}"]["판"], 5)
                          for d in NULL_DRAWS},
                "널 평균": round(float(np.mean(nl)), 5),
                "널 폭(최대−최소)": round(float(np.max(nl) - np.min(nl)), 5),
                "**신호 몫(진짜 − 널평균)**": round(sig, 5),
                "**문턱 0.00353 배수**": round(sig / THRESH, 3),
                "문턱 넘었나": bool(sig > THRESH),
                "**순효과(진짜 − 기준선)**": round(net, 5),
                "씨앗별 짝": [round(float(x), 5) for x in paired],
                "씨앗 짝 평균": round(float(paired.mean()), 5),
                "씨앗 짝 SD": round(float(paired.std(ddof=1)), 5),
                "씨앗 짝 BCa 95%": [round(lo, 5), round(hi, 5)],
                "구간 종류": kind, "폴백 사유": fb, "🔴 구간 한계 병기": fb_note,
                "군집 병기": cwire,
                "판정(pairboot.verdict)": PB.verdict(lo, hi),
                "🔴 LOO(12씨앗)": loo12,
                "🔴 LOO 에서 뒤집히는 씨앗": [s for s in ss if loo12[s]["문턱 넘나"] != (sig > THRESH)],
                "🔴 잡음 바닥 0.01055 병기": round(sig / D.JUNK_FLOOR, 3),
                "도메인별": dict(sorted(per.items(), key=lambda x: -abs(x[1]["판 기여"]))),
            },
            "옛 6씨앗(같은 적합의 부분집합 · 병기)": {
                "**신호 몫**": round(sig6, 5),
                "**문턱 배수**": round(sig6 / THRESH, 3),
                "문턱 넘었나": bool(sig6 > THRESH),
                "**순효과**": round(net6, 5),
                "씨앗별 짝": [round(float(x), 5) for x in p6],
                "씨앗 짝 BCa 95%": [round(lo6, 5), round(hi6, 5)],
                "구간 종류": kind6, "폴백 사유": fb6,
                "판정(pairboot.verdict)": PB.verdict(lo6, hi6),
            },
        }

    # 896 재현 대조 --- 씨앗 0~5 는 **같은 적합**이어야 한다
    try:
        old = json.loads((ROOT / "runners/out896_armB.json").read_text(encoding="utf-8"))
        oldBD = old["판 원자료"]
        rep = {}
        for name in oldBD:
            if name not in BD:
                continue
            rep[name] = {s: [round(BD[name]["씨앗별"][s], 5),
                             oldBD[name]["씨앗별"][s],
                             round(BD[name]["씨앗별"][s], 5) == oldBD[name]["씨앗별"][s]]
                         for s in s6}
        repro = {"칸": sum(len(v) for v in rep.values()),
                 "불일치": sum(1 for v in rep.values() for x in v.values() if not x[2]),
                 "상세": rep}
    except Exception as e:
        repro = {"⛔": repr(e)}

    # 문턱이 전제하는 씨앗 수 --- 자를 **읽어서** 성분을 가져온다(손 전사 금지)
    tref = json.loads(THRESH_REF.read_text(encoding="utf-8"))
    comp = tref["자 다섯"]["성분"]
    seed_c12, row_c = comp["씨앗(12대12 환산)"], comp["행 짝(널)"]
    ruler = {
        "원천": "runners/out891_thresh.json (읽음)",
        "sha256(out891_thresh.json)": sha(THRESH_REF),
        "R5(정본 문턱)": tref["자 다섯"]["🔴 R5 합성 2σ = 채택 문턱"],
        "성분 씨앗(12대12 환산)": seed_c12, "성분 행 짝(널)": row_c,
        "🔴 6씨앗 측정에 맞춘 자(씨앗 성분 ×√2)":
            round(2 * float(np.hypot(seed_c12 * np.sqrt(2), row_c)), 5),
        "🔴 뜻": ("문턱 0.00353 은 씨앗 성분을 **12씨앗 앙상블 짝**으로 환산해 만든 자다. "
                "896 이 쓴 6씨앗 측정에 맞춘 자는 위의 값이며, 그 자에 대면 6씨앗 "
                "신호 몫은 더 멀어진다. 12씨앗으로 재는 것이 자와 분모를 맞추는 길이다."),
    }

    out = {
        "무엇": "이슈 #113 --- 노트 896 팔 B 를 **12씨앗**으로 다시 잰다. 요청 0 · 네트워크 0.",
        "설계": {"주입": "ff753 열 주입 정본 · 도메인 안 백분위 1열 + 마스크",
               "널 팔": f"값만 섞고 마스크 무늬 보존(노트 335) · 뽑기 {list(NULL_DRAWS)}",
               "씨앗(정본 ff753.RULER_SEEDS)": list(seeds),
               "옛 씨앗(ff753.SEEDS)": list(SEEDS6),
               "판정선": THRESH, "적합 수": len(tasks),
               "구간": "lab.pairboot.cluster_boot BCa · 씨앗 재표집 · seed=896"},
        "🔴 자 대 잰 것(M1)": ruler,
        "🔴 896 재현(씨앗 0~5 부동소수 5자리)": repro,
        "배선 검사": wire, "주입 열 sha256": shas,
        "기준선 게이트": {"판": round(base, 5), "범위": list(BASE_OK),
                   "통과": bool(BASE_OK[0] <= base <= BASE_OK[1])},
        "🔴 도메인별 실제 투입 행수": rows_in,
        "🔴 조용히 빠진 도메인(판별 × 씨앗)": {k: v for k, v in silent.items() if v},
        "🔴 점수 안 난 도메인(판별 × 씨앗)": {k: {s: m for s, m in v.items() if m}
                                   for k, v in MISS.items()
                                   if any(v.values())},
        "판별": verdicts,
        "🔴 M10 (추가 적합 0)": m10(BD, ss, wire, cov, W),
        "🔴 M10 (옛 6씨앗 · 병기)": m10(BD, s6, wire, cov, W),
        "병합률(티처 #59 m3)": merge_rates(d0, post, dz, cov),
        "판 원자료": {k: {"판": round(v["판"], 5), "씨앗SD": round(v["씨앗SD"], 5),
                      "씨앗별": {s: round(v["씨앗별"][s], 5) for s in ss},
                      "도메인": {a: round(b, 4) for a, b in v["도메인"].items()},
                      "도메인별 점수 난 씨앗 수": v["도메인 씨앗수"]}
                  for k, v in BD.items()},
        "용량 덮음(재계산)": cov,
        "초": round(time.time() - t0, 1),
    }
    out.update(stamp())
    (ROOT / "runners" / out_name).write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({nm: verdicts[nm] for nm in verdicts}, ensure_ascii=False,
                     indent=1)[:6000], flush=True)
    print(f"=== 저장 runners/{out_name} · {out['초']}s ===", flush=True)
    return out


# ── ③ SEEDS 정본화 뒤 문턱 재확인 ──────────────────────────────────────────
def thresh():
    """`thresh891` 을 다시 돌려 R5 가 여전히 0.00353 인지 본다.

    🔴 `out891_thresh.json` · `out891_log.txt` 는 **내 파일 집합이 아니다.**
    돌리기 전에 떠 두고 끝나면 되돌린다(sha 로 확인). 새 산출물은 `out113_` 로 낸다.
    """
    import thresh891 as TH
    t0 = time.time()
    keep = [ROOT / "runners/out891_thresh.json", ROOT / "runners/out891_log.txt"]
    bak = Path("/private/tmp/claude-501/-Users-ax-world-model/"
               "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")
    bak.mkdir(parents=True, exist_ok=True)
    before = {}
    for p in keep:
        if p.exists():
            before[p.name] = sha(p)
            shutil.copy2(p, bak / p.name)
    TH.OUT = ROOT / "runners/out113_thresh_recheck.json"
    try:
        res = TH.main()
    finally:
        for p in keep:                       # 🔴 남의 파일은 원상복구
            if p.name in before:
                shutil.copy2(bak / p.name, p)
    after = {p.name: sha(p) for p in keep if p.exists()}
    old = json.loads((ROOT / "runners/out891_thresh.json").read_text(encoding="utf-8"))
    new5, old5 = res["자 다섯"], old["자 다섯"]
    rep = {
        "무엇": "이슈 #113 ③ --- SEEDS 를 ff753 한 곳에서 오게 고친 뒤 문턱 재확인",
        "🔴 조항 59(새 형태)": "고치는 작업의 성공 ≠ 그 숫자가 옳음. 그래서 다시 돌렸다.",
        "씨앗 목록": {"thresh891.SEEDS": list(TH.SEEDS),
                  "ff753.RULER_SEEDS": list(FF.RULER_SEEDS),
                  "ff753.SEEDS": list(FF.SEEDS),
                  "🔴 같은 물건인가": tuple(TH.SEEDS) == tuple(FF.RULER_SEEDS),
                  "HALF_A/HALF_B": [list(TH.HALF_A), list(TH.HALF_B)]},
        "🔴 R5 옛": old5["🔴 R5 합성 2σ = 채택 문턱"],
        "🔴 R5 새": new5["🔴 R5 합성 2σ = 채택 문턱"],
        "🔴 여전히 0.00353 인가":
            new5["🔴 R5 합성 2σ = 채택 문턱"] == old5["🔴 R5 합성 2σ = 채택 문턱"] == 0.00353,
        "자 다섯 옛": old5, "자 다섯 새": new5,
        "성분 일치": new5["성분"] == old5["성분"],
        "씨앗 분할 옛": old["씨앗 분할"], "씨앗 분할 새": res["씨앗 분할"],
        "배선(새)": res["배선"],
        "🔴 남의 파일 원상복구": {"대상": [p.name for p in keep],
                        "전 sha": before, "후 sha": after,
                        "복구됨": before == after},
        "초": round(time.time() - t0, 1),
    }
    rep.update(stamp())
    (ROOT / "runners/out113_thresh.json").write_text(
        json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps({k: rep[k] for k in rep if k.startswith("🔴") or k == "씨앗 목록"},
                     ensure_ascii=False, indent=1), flush=True)
    return rep


def loo_main():
    out = {"무엇": "이슈 #113 ① --- 티처 #59 의 LOO 를 **내가 다시 낸다**. 적합 0.",
           "🔴 주의": "out896_armB.json 의 씨앗별 판은 5자리 반올림값이다. "
                   "12씨앗 재측정(out113_armB12.json)의 씨앗 0~5 가 무반올림 대조다.",
           "결과": loo()}
    out.update(stamp())
    (ROOT / "runners/out113_loo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(out["결과"]["🔴 티처 대조"], ensure_ascii=False, indent=1), flush=True)
    return out


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "loo"
    {"loo": loo_main, "B": stageB, "thresh": thresh}[which]()
