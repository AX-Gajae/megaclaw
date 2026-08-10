# -*- coding: utf-8 -*-
"""노트 900 ③ 측정 · ④ 판정 — **게임 전용 축 넷을 모형에 닿게 하면 판이 오르나.**

사전등록: `docs/prereg_900_levers.md` (커밋 `f3ca1d3ea` · **측정보다 앞선다**).
배선 검사: `runners/wire900.py` → `runners/out900_wire.json` (관문 전부 통과).
물음: GitHub 이슈 #134 · 티처 #62 M2.

팔(전부 `F18_bagboost` · 씨앗 0~11 로 **짝짓는다**):

    A_common   오늘 챔피언. `AXIS_MODE="common"` --- 게임 4열이 안 닿는다. 설계 88열
    B_union    `axes="union"` --- 40축. 설계 96열
    C_domax    `DOMAX={"게임": 4축}` (노트 529 가 이미 만든 장치). 설계 96열
    D_nanpad   B 와 같되 **축이 아예 없는 칸을 0.5 가 아니라 NaN 으로**

🔴 규약 47 --- 구간은 `lab.pairboot.cluster_boot` 의 **BCa**(폴백이면 사유 필드).
🔴 노트 133 --- 첫 양수를 그대로 채택하지 않는다.
🔴 조항 60 --- 이 파일이 쓰는 유일한 유보 분모는 **3,775** 다.

산출물: `runners/out900_levers.json`
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import datetime as dt                                            # noqa: E402
import hashlib                                                   # noqa: E402
import json                                                      # noqa: E402
import multiprocessing as mp                                     # noqa: E402
import subprocess                                                # noqa: E402
import sys                                                       # noqa: E402
import time                                                      # noqa: E402
from pathlib import Path                                         # noqa: E402

import numpy as np                                               # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out900_levers.json"
WIRE = ROOT / "runners/out900_wire.json"

T = 2025.0
NPROC = 8
B_BOOT = 10_000
BOOT_SEED = 827          #: `pairboot.cluster_boot` 기본과 같은 값(고정)
ARM_ORDER = ("A_common", "B_union", "C_domax", "D_nanpad")


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
            "🔴 코드 sha256(이 파일 · runners/levers900.py)": sha(ME),
            "참조 코드 sha256": {
                "runners/wire900.py": sha(ROOT / "runners/wire900.py"),
                "lab/forms.py": sha(ROOT / "lab/forms.py"),
                "lab/harness.py": sha(ROOT / "lab/harness.py"),
                "lab/pairboot.py": sha(ROOT / "lab/pairboot.py"),
                "runners/ff753.py": sha(ROOT / "runners/ff753.py"),
                "docs/prereg_900_levers.md": sha(ROOT / "docs/prereg_900_levers.md")}}


# ── 한 적합 ─────────────────────────────────────────────────────────────────
def _one(args):
    """(팔 이름, 씨앗) → 도메인 점수 · 판. **팔 정의는 wire900 에서 가져온다.**"""
    name, seed = args
    import ff753 as FF
    import wire900 as WW
    from lab.harness import evaluate
    cls = WW.ARMS[name]
    WW.patch_nan(name in WW.NAN_ARMS)
    try:
        d = FF.shell(FF.base())
        sc = evaluate(lambda: cls(seed=seed), d, T=T)
        W = d.weights(T)
        return (name, seed, {k: float(v) for k, v in sc.items()},
                float(d.pooled(sc, T=T)),
                int(sum(W[k] for k in sc if k in W)))
    finally:
        WW.patch_nan(False)


def _bca(vals):
    """씨앗 짝 값 → (점추정, lo, hi, 종류, 폴백 사유, 군집 병기). 규약 47."""
    from lab import pairboot as PB
    a = np.asarray(vals, float)
    cl, wire = PB.solo_clusters(len(a))
    try:
        pt, lo, hi, kind = PB.cluster_boot(lambda ix: float(np.mean(a[ix])), cl,
                                           B=B_BOOT, seed=BOOT_SEED)
        fb = None
    except Exception as e:
        pt, lo, hi, kind, fb = float(a.mean()), float("nan"), float("nan"), "실패", repr(e)
    return pt, lo, hi, kind, fb, wire


def _rec(vals, thresh, thresh_day):
    from lab import pairboot as PB
    pt, lo, hi, kind, fb, wire = _bca(vals)
    r = {"씨앗별 짝 Δ": [round(float(x), 6) for x in vals],
         "평균 Δ": round(float(np.mean(vals)), 6),
         "SD(ddof=1)": round(float(np.std(vals, ddof=1)), 6),
         "양수 씨앗 수": int(np.sum(np.asarray(vals) > 0)),
         "n": len(vals),
         "BCa 95%": [round(lo, 6), round(hi, 6)],
         "구간 종류": kind, "🔴 구간 폴백 사유": fb, "군집 병기": wire,
         "규약 47 판정": PB.verdict(lo, hi) if np.isfinite(lo) and np.isfinite(hi)
         else "구간 계산 실패 — 판정 불능 아님",
         "문턱(정본 0.00353) 배수": round(float(np.mean(vals)) / thresh, 3),
         "문턱(일 군집 0.00370) 배수": round(float(np.mean(vals)) / thresh_day, 3),
         "문턱 넘나(정본)": bool(np.mean(vals) > thresh)}
    return r


def main():
    t0 = time.time()
    import ff753 as FF
    import wire900 as WW                                          # noqa: F401
    from lab import pairboot as PB

    wire = json.loads(WIRE.read_text("utf-8"))
    assert wire["ㅇ 관문"]["🔴 전부 통과"], "🔴 배선 관문 미통과 — 측정 안 한다"

    R5 = float(wire["ㅅ 자와 필요 Δ"]["문턱(정본 · 891 R5 · 12씨앗)"])
    R5d = float(wire["ㅅ 자와 필요 Δ"]["문턱(후보 · 일 군집 · 899)"])
    need = wire["ㅅ 자와 필요 Δ"]["🔴 그 도메인 하나로 판 문턱을 넘으려면 필요한 도메인 Δ"]

    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    W = d0.weights(T)
    TOT = int(sum(W.values()))
    assert TOT == 3775, f"🔴 유보 가중 합이 3775 가 아니다: {TOT}"
    seeds = list(range(12))

    tasks = [(nm, s) for nm in ARM_ORDER for s in seeds]
    print(f"팔 {len(ARM_ORDER)} × 씨앗 {len(seeds)} = {len(tasks)} 적합 "
          f"(프로세스 {NPROC})", flush=True)
    with mp.Pool(NPROC) as pool:
        raw = pool.map(_one, tasks)
    print(f"적합 끝 {time.time()-t0:.0f}s", flush=True)

    BD, MISS, WSUM = {}, {}, {}
    for name, seed, sc, pooled, wsum in raw:
        BD.setdefault(name, {"판": {}, "도메인": {}})
        BD[name]["판"][seed] = pooled
        for k, v in sc.items():
            if np.isfinite(v):
                BD[name]["도메인"].setdefault(k, {})[seed] = float(v)
        MISS.setdefault(name, {})[str(seed)] = sorted(set(W) - set(sc))
        WSUM.setdefault(name, {})[str(seed)] = int(wsum)

    # ── 🔴 조용한 탈락 회계 (사전등록 5.4 의 「모른다」 조건 ③) ────────────────
    silent = {nm: {"씨앗별 빠진 도메인": MISS[nm],
                   "씨앗별 채점 가중 합": WSUM[nm],
                   "🔴 전 씨앗 12도메인": all(len(BD[nm]["판"]) == 12 for _ in [0])
                   and all(not v for v in MISS[nm].values()),
                   "🔴 전 씨앗 가중 합 3775": all(v == 3775 for v in WSUM[nm].values())}
              for nm in BD}
    ok_all = all(v["🔴 전 씨앗 12도메인"] and v["🔴 전 씨앗 가중 합 3775"]
                 for v in silent.values())

    # ── 판 수준 ────────────────────────────────────────────────────────────
    level = {nm: {"씨앗별 판(전정밀)": [BD[nm]["판"][s] for s in seeds],
                  "평균": float(np.mean([BD[nm]["판"][s] for s in seeds])),
                  "SD(ddof=1)": float(np.std([BD[nm]["판"][s] for s in seeds], ddof=1)),
                  "SE": float(np.std([BD[nm]["판"][s] for s in seeds], ddof=1)
                              / np.sqrt(len(seeds)))}
             for nm in ARM_ORDER}

    base = np.array([BD["A_common"]["판"][s] for s in seeds], float)
    arms = {}
    for nm in ARM_ORDER[1:]:
        cur = np.array([BD[nm]["판"][s] for s in seeds], float)
        dl = cur - base
        rec = _rec(dl, R5, R5d)
        rec["🔴 짝 Δ 가 전부 정확히 0 인가(887형 의심)"] = bool(np.all(dl == 0.0))

        # 도메인별 짝 Δ
        dom = {}
        for k in doms:
            a = np.array([BD["A_common"]["도메인"][k][s] for s in seeds], float)
            b = np.array([BD[nm]["도메인"][k][s] for s in seeds], float)
            dd = b - a
            pt, lo, hi, kind, fb, _w = _bca(dd)
            dom[k] = {
                "유보 가중": int(W[k]), "판 가중": round(W[k] / TOT, 5),
                "평균 Δρ": round(float(dd.mean()), 6),
                "SD": round(float(dd.std(ddof=1)), 6),
                "양수 씨앗": int(np.sum(dd > 0)),
                "BCa 95%": [round(lo, 6), round(hi, 6)],
                "구간 종류": kind, "폴백 사유": fb,
                "규약 47 판정": PB.verdict(lo, hi),
                "🔴 판 기여(w/3775 × Δρ)": round(float(dd.mean()) * W[k] / TOT, 6),
                "🔴 이 도메인 하나로 판 문턱을 넘으려면 필요한 Δρ":
                    need[k]["필요 Δ(문턱 0.00353)"],
                "🔴 필요 Δρ 대비 실측 배수":
                    round(float(dd.mean()) / need[k]["필요 Δ(문턱 0.00353)"], 4),
            }
        rec["도메인별 짝 Δ"] = dom

        # 🔴 분해 검사 — 판 Δ 는 도메인 기여의 합이어야 한다
        s_contrib = float(sum(v["🔴 판 기여(w/3775 × Δρ)"] for v in dom.values()))
        rec["🔴 분해 검사"] = {
            "도메인 기여 합": round(s_contrib, 6),
            "판 짝 Δ 평균": round(float(dl.mean()), 6),
            "차": round(abs(s_contrib - float(dl.mean())), 8),
            "일치(1e-4 안)": abs(s_contrib - float(dl.mean())) < 1e-4}

        # 🔴 게임만 좋아지고 남이 나빠지나 (사전등록 5.3)
        g = dom["게임"]
        others = {k: v for k, v in dom.items() if k != "게임"}
        oc = float(sum(v["🔴 판 기여(w/3775 × Δρ)"] for v in others.values()))
        rec["🔴 5.3 게임 대 나머지 열하나"] = {
            "게임 Δρ": g["평균 Δρ"], "게임 BCa": g["BCa 95%"],
            "게임 판 기여": g["🔴 판 기여(w/3775 × Δρ)"],
            "나머지 11 판 기여 합": round(oc, 6),
            "나머지 11 중 Δρ 음수 도메인 수":
                int(sum(1 for v in others.values() if v["평균 Δρ"] < 0)),
            "나머지 11 중 음수 도메인": sorted(k for k, v in others.items()
                                      if v["평균 Δρ"] < 0),
            "🔴 판정문": (
                "게임 전용 열이 남을 해친다 — 게임은 오르는데 나머지 열하나의 "
                "판 기여 합이 음수다(899 의 「축이 있는 척한다」의 대가)"
                if g["평균 Δρ"] > 0 and oc < 0 else
                "축을 닿게 해도 그 도메인조차 안 산다 — 남은 원인 (가) 넷이 라벨과 "
                "무관 (나) 패딩 열이 그 넷의 값을 덮음. **이 사이클은 둘을 못 가른다**"
                if g["평균 Δρ"] <= 0 else
                "게임도 오르고 나머지 열하나 기여 합도 음수가 아니다")}
        arms[nm] = rec

    # ── ④ 판정 (사전등록 5 의 어법 그대로) ──────────────────────────────────
    verdict = {}
    for nm, r in arms.items():
        lo, hi = r["BCa 95%"]
        m = r["평균 Δ"]
        if r["🔴 짝 Δ 가 전부 정확히 0 인가(887형 의심)"]:
            v = "🔴 모른다 — 짝 Δ 가 전부 정확히 0. 887형 중립화 의심(배선 재검사)"
        elif r["구간 종류"] not in ("BCa",):
            v = f"🔴 자가 흔들렸다 — 유보. 구간 종류 {r['구간 종류']}"
        elif lo > 0 and m > R5:
            v = "제안(채택 아님) — 하한 > 0 이고 문턱을 넘었다. 노트 133: 확인 측정은 다음 사이클"
        elif hi < 0:
            v = "패 — 상한 < 0 (규약 47). 이건 「모른다」가 아니다"
        elif lo <= 0 <= hi:
            v = ("🔴 **이 자를 못 넘었다** — 구간이 0 을 문다. "
                 "「이 자로는 모른다」이지 반증이 아니다")
        else:
            v = ("🔴 **이 자를 못 넘었다** — 구간은 0 밖인데 문턱 미달"
                 if lo > 0 else "🔴 **이 자를 못 넘었다**")
        verdict[nm] = {
            "판 짝 Δ": m, "BCa 95%": [lo, hi], "구간 종류": r["구간 종류"],
            "문턱(정본)": R5, "문턱 배수": r["문턱(정본 0.00353) 배수"],
            "문턱(일 군집 병기)": R5d,
            "🔴 판정": v,
            "🔴 넘으려면 게임 Δρ 가 얼마여야 하나(문턱 0.00353)":
                need["게임"]["필요 Δ(문턱 0.00353)"],
            "🔴 넘으려면 게임 Δρ 가 얼마여야 하나(문턱 0.00370)":
                need["게임"]["필요 Δ(문턱 0.00370)"],
            "실측 게임 Δρ": r["🔴 5.3 게임 대 나머지 열하나"]["게임 Δρ"],
            "🔴 실측 / 필요": round(
                r["🔴 5.3 게임 대 나머지 열하나"]["게임 Δρ"]
                / need["게임"]["필요 Δ(문턱 0.00353)"], 4),
            "🔴 도메인 Δ 병기": {k: v2["평균 Δρ"] for k, v2 in
                            sorted(r["도메인별 짝 Δ"].items())},
        }

    res = {
        "노트": 900, "이슈": 134,
        "무엇": "AXIS_MODE — 게임 전용 축 넷이 모형에 닿게 하면 판이 오르나",
        "사전등록": {"파일": "docs/prereg_900_levers.md", "커밋": "f3ca1d3ea",
                 "커밋 시각(UTC)": "2026-08-10T16:34:28Z",
                 "🔴 측정보다 앞선다": True},
        "배선 스탬프": stamp(),
        "② 배선 검사 요약(out900_wire.json 에서 읽음)": {
            "관문 전부 통과": wire["ㅇ 관문"]["🔴 전부 통과"],
            "common / union 실측": [wire["ㄴ common/union 실측"]["common 수"],
                                 wire["ㄴ common/union 실측"]["union 수"]],
            "추가되는 축": wire["ㄴ common/union 실측"]["union − common 목록"],
            "팔별 설계 열 수": {k: v["🔴 fit 이 본 설계 열 수(m.n_features_in_)"]
                          for k, v in wire["ㄹ _design 열 수"].items()},
            "팔 A 대비 늘어난 열": {k: v["🔴 팔 A 대비 늘어난 열"]
                            for k, v in wire["ㄹ _design 열 수"].items()},
            "팔 B 와 팔 C 의 열 집합이 같다":
                wire["ㅁ 🔴 팔 B vs 팔 C 설계행렬"]["🔴 전 도메인에서 열 집합이 같다"],
            "자료 sha(전체)": wire["ㄱ 판"]["자료 sha(전체)"],
        },
        "판 뼈대": {"도메인 수": len(doms), "유보 가중 합": TOT,
                 "씨앗": seeds,
                 "🔴 분모": "3,775 하나만 쓴다(897 의 3,710 을 안 섞는다 · 조항 60)"},
        "🔴 조용한 탈락 회계": {**silent, "🔴 전 팔 전 씨앗 온전": ok_all},
        "판 수준(팔별)": level,
        "🔴 팔 A 와 판 정본 대조": {
            "이번 팔 A 평균": level["A_common"]["평균"],
            "정본(out112_board.json)": 0.4698232980146997,
            "차": round(level["A_common"]["평균"] - 0.4698232980146997, 8),
            "출처": "runners/out112_board.json 의 「평균」",
        },
        "③ 짝 Δ(팔 X − 팔 A · 같은 씨앗)": arms,
        "④ 판정": verdict,
        "초": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("=== ④ 판정 ===", flush=True)
    print(json.dumps(verdict, ensure_ascii=False, indent=1), flush=True)
    print(f"완료 · {OUT} · {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
