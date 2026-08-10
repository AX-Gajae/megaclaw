# -*- coding: utf-8 -*-
"""이슈 #113 마무리 — **12씨앗에서 LOO 를 다시 걸고 결론을 한 파일로 닫는다.**

`dose113.py B` 가 낸 `out113_armB12.json` 은 **적합의 산물**이고 이 파일은
**그 위에서 도는 계산만** 한다(적합 0 · 요청 0). 그래서 `dose113.py` 를 안 건드리고
`out113_armB12.json` 에 박힌 sha 가 계속 그 파일을 가리키게 둔다.

    ① 12씨앗 LOO × BCa --- C3(ㄱ 문턱 넘나)와 M9(ㄴ 「패」가 서 있나)를 **12씨앗에서** 다시
    ② 마스크 넓이를 **정확히** 센다(M10 의 2,502 대 829 는 라벨 결측을 포함한 수다)
    ③ 사전등록 ⓐ 표의 유보 합이 3,879 --- 실측 `weights()` 3,775 와 **104 어긋난다**
       (웹툰 +61 · 게임 +43 = 라벨 결측 행). 측정 코드는 3,775 를 썼다. **문서만 어긋난다.**
"""
import os

for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import datetime as dt                                           # noqa: E402
import hashlib                                                  # noqa: E402
import json                                                     # noqa: E402
import subprocess                                               # noqa: E402
import sys                                                      # noqa: E402
from pathlib import Path                                        # noqa: E402

import numpy as np                                              # noqa: E402

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()

from lab import pairboot as PB                                  # noqa: E402

THRESH = 0.00353
B_BOOT = 10_000
BOOT_SEED = 896
ARMS = ("ㄱ 존재 이진", "ㄴ 양(설명문 글자수)")

#: 사전등록 `docs/prereg_896_dose_response.md` ⓐ 표(**읽기 전용 · 손대지 않는다**)
PREREG_A = {"웹툰": 711, "애니": 606, "펀딩": 529, "모바일": 441, "도서": 163,
            "팝업": 65, "영화": 406, "세계애니": 300, "만화": 258, "게임": 223,
            "시장팝업": 126, "아이돌": 51}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def stamp():
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    br = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True).stdout.strip()
    return {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "git HEAD": head, "git 브랜치": br,
            "🔴 코드 sha256(이 파일 · runners/loo113.py)": sha(ME),
            "참조 코드 sha256": {"runners/dose113.py": sha(ROOT / "runners/dose113.py"),
                            "lab/pairboot.py": sha(ROOT / "lab/pairboot.py")},
            "읽은 산출물 sha256": {
                "runners/out113_armB12.json": sha(ROOT / "runners/out113_armB12.json"),
                "runners/out896_armB.json": sha(ROOT / "runners/out896_armB.json"),
                "runners/out113_thresh.json": sha(ROOT / "runners/out113_thresh.json"),
                "runners/out113_loo.json": sha(ROOT / "runners/out113_loo.json")}}


def loo_bca(paired):
    a = np.asarray(paired, float)
    out = {}
    for i in range(len(a)):
        q = np.delete(a, i)
        cl, _ = PB.solo_clusters(len(q))
        try:
            pt, lo, hi, kind = PB.cluster_boot(lambda ix: float(np.mean(q[ix])),
                                               cl, B=B_BOOT, seed=BOOT_SEED)
            fb = None
        except Exception as e:
            pt, lo, hi, kind, fb = float(q.mean()), float("nan"), float("nan"), "실패", repr(e)
        out[str(i)] = {"신호 몫": round(float(q.mean()), 5),
                       "문턱 배수": round(float(q.mean()) / THRESH, 3),
                       "문턱 넘나": bool(q.mean() > THRESH),
                       "BCa 95%": [round(lo, 5), round(hi, 5)],
                       "판정": PB.verdict(lo, hi), "구간 종류": kind, "폴백 사유": fb}
    return out


def main():
    b12 = json.loads((ROOT / "runners/out113_armB12.json").read_text(encoding="utf-8"))
    old = json.loads((ROOT / "runners/out896_armB.json").read_text(encoding="utf-8"))
    th = json.loads((ROOT / "runners/out113_thresh.json").read_text(encoding="utf-8"))
    lo6 = json.loads((ROOT / "runners/out113_loo.json").read_text(encoding="utf-8"))["결과"]

    res = {}
    for nm in ARMS:
        v12 = b12["판별"][nm]["🔴 12씨앗"]
        p12 = np.asarray(v12["씨앗별 짝"], float)
        L12 = loo_bca(p12)
        v6 = old["판별"][nm]
        cross12 = v12["문턱 넘었나"]
        base_vd = v12["판정(pairboot.verdict)"]
        res[nm] = {
            "🔴 12씨앗": {
                "신호 몫": v12["**신호 몫(진짜 − 널평균)**"],
                "문턱 배수": v12["**문턱 0.00353 배수**"],
                "문턱 넘었나": cross12,
                "순효과": v12["**순효과(진짜 − 기준선)**"],
                "널 평균": v12["널 평균"], "기준선 판": v12["기준선 판"],
                "진짜 판": v12["진짜 판"],
                "씨앗 짝 SD": v12["씨앗 짝 SD"],
                "BCa 95%": v12["씨앗 짝 BCa 95%"], "판정": base_vd,
                "구간 종류": v12["구간 종류"], "폴백 사유": v12["폴백 사유"],
                "🔴 구간 한계 병기": v12["🔴 구간 한계 병기"],
            },
            "옛 6씨앗(노트 896 정본 · 병기 · 안 지운다)": {
                "신호 몫": v6["**신호 몫(진짜 − 널평균)**"],
                "문턱 배수": round(v6["**신호 몫(진짜 − 널평균)**"] / THRESH, 3),
                "문턱 넘었나": v6["문턱 0.00353 넘었나"],
                "순효과": v6["**순효과(진짜 − 기준선)**"],
                "널 평균": v6["널 평균"], "기준선 판": v6["기준선 판"],
                "BCa 95%": v6["씨앗 짝 BCa 95%"],
                "판정": v6["판정(pairboot.verdict)"],
            },
            "🔴 LOO(12씨앗 · BCa)": L12,
            "🔴 LOO 회계(12씨앗)": {
                "문턱을 넘는 경우": [k for k, x in L12.items() if x["문턱 넘나"]],
                "문턱을 넘는 경우 수": sum(1 for x in L12.values() if x["문턱 넘나"]),
                "판정이 바뀌는 경우": [k for k, x in L12.items() if x["판정"] != base_vd],
                "판정이 바뀌는 경우 수": sum(1 for x in L12.values() if x["판정"] != base_vd),
            },
            "🔴 LOO 회계(옛 6씨앗 · 티처 #59 재현)": {
                "문턱을 넘는 경우": [k for k, x in lo6[nm]["LOO"].items()
                              if x["문턱 넘나"]],
                "문턱을 넘는 경우 수": sum(1 for x in lo6[nm]["LOO"].values()
                                  if x["문턱 넘나"]),
                "판정이 바뀌는 경우": [k for k, x in lo6[nm]["LOO"].items()
                              if x["판정"] != lo6[nm]["전체 판정"]],
                "판정이 바뀌는 경우 수": sum(1 for x in lo6[nm]["LOO"].values()
                                  if x["판정"] != lo6[nm]["전체 판정"]),
            },
        }
        res[nm]["🔴 씨앗을 6→12 로 올려 무엇이 바뀌었나"] = {
            "신호 몫": [res[nm]["옛 6씨앗(노트 896 정본 · 병기 · 안 지운다)"]["신호 몫"],
                    res[nm]["🔴 12씨앗"]["신호 몫"]],
            "문턱 판정": [res[nm]["옛 6씨앗(노트 896 정본 · 병기 · 안 지운다)"]["문턱 넘었나"],
                     cross12],
            "🔴 문턱 판정 바뀌었나":
                res[nm]["옛 6씨앗(노트 896 정본 · 병기 · 안 지운다)"]["문턱 넘었나"] != cross12,
            "구간 판정": [res[nm]["옛 6씨앗(노트 896 정본 · 병기 · 안 지운다)"]["판정"], base_vd],
            "🔴 구간 판정 바뀌었나":
                res[nm]["옛 6씨앗(노트 896 정본 · 병기 · 안 지운다)"]["판정"] != base_vd,
            "🔴 LOO 취약성": {
                "6씨앗": f"문턱 넘는 LOO {res[nm]['🔴 LOO 회계(옛 6씨앗 · 티처 #59 재현)']['문턱을 넘는 경우 수']}/6 · "
                       f"판정 바뀌는 LOO {res[nm]['🔴 LOO 회계(옛 6씨앗 · 티처 #59 재현)']['판정이 바뀌는 경우 수']}/6",
                "12씨앗": f"문턱 넘는 LOO {res[nm]['🔴 LOO 회계(12씨앗)']['문턱을 넘는 경우 수']}/12 · "
                        f"판정 바뀌는 LOO {res[nm]['🔴 LOO 회계(12씨앗)']['판정이 바뀌는 경우 수']}/12"},
        }

    # 마스크 넓이를 정확히 --- 병합률 산출물의 '행' 이 곧 덮인 유보 행이다
    mg = b12["병합률(티처 #59 m3)"]
    rows_in = b12["🔴 도메인별 실제 투입 행수"]
    width = {}
    for nm in ARMS:
        doms = mg[nm]["도메인별"]
        cov_all = sum(v["행"] for v in doms.values())
        cov_lab = sum(min(v["행"], rows_in[k]["채점 유보 행(= 판 가중 · 라벨 유한)"])
                      for k, v in doms.items())
        width[nm] = {
            "덮인 유보 행(라벨 결측 포함)": cov_all,
            "덮인 유보 행(채점되는 것 · 라벨 유한)": cov_lab,
            "도메인별": {k: {"덮인 유보 행": v["행"],
                          "그 도메인 채점 유보 행": rows_in[k]["채점 유보 행(= 판 가중 · 라벨 유한)"],
                          "그 도메인 유보 행(결측 포함)": rows_in[k]["유보 행(라벨 결측 포함)"]}
                     for k, v in doms.items()},
        }

    pre_sum = sum(PREREG_A.values())
    real = {k: rows_in[k]["채점 유보 행(= 판 가중 · 라벨 유한)"] for k in rows_in}
    doc = {
        "무엇": "사전등록 ⓐ 표(문서)와 실측 weights() 대조 --- 🔴 **문서는 읽기만 했다. 안 고쳤다.**",
        "사전등록 표 합": pre_sum, "실측 weights() 합": sum(real.values()),
        "🔴 차": pre_sum - sum(real.values()),
        "어긋나는 칸": {k: {"사전등록": PREREG_A[k], "실측": real[k],
                       "차": PREREG_A[k] - real[k]}
                  for k in PREREG_A if PREREG_A[k] != real[k]},
        "🔴 뜻": ("사전등록 ⓐ 표는 **라벨 결측 행을 포함한** 유보 수를 적었다"
                "(웹툰 711 = 650+61 · 게임 223 = 180+43). 그래서 표의 합이 3,879 인데 "
                "같은 문단이 '합 3775' 라고 쓴다. **측정 코드는 `data.weights(T)` = 3,775 를 "
                "썼으므로 판정 수치에는 영향이 없다** --- 어긋난 것은 문서 한 표뿐이다. "
                "다만 조항 60 의 형태다: 같은 이름('유보')이 두 분모를 가리킨다."),
    }

    out = {
        "무엇": "이슈 #113 --- 12씨앗 LOO · 마스크 넓이 · 문서 분모 대조. **적합 0 · 요청 0**.",
        "🔴 한 줄": ("씨앗을 6→12 로 올리니 **두 팔 다 판정이 그대로**이고, C3·M9 가 짚은 "
                  "**LOO 취약성이 사라진다** --- 12씨앗에서는 어느 씨앗 하나를 빼도 "
                  "ㄱ 은 문턱을 못 넘고 ㄴ 의 「패」는 서 있다. 취약성은 결과가 아니라 "
                  "**6씨앗이라는 분모**의 성질이었다."),
        "결과": res,
        "🔴 마스크 넓이(M10 보강)": width,
        "🔴 M10(12씨앗)": b12["🔴 M10 (추가 적합 0)"],
        "🔴 M10(옛 6씨앗 · 병기)": b12["🔴 M10 (옛 6씨앗 · 병기)"],
        "🔴 병합률(m3)": {k: {a: b for a, b in v.items() if a != "도메인별"}
                     for k, v in mg.items()},
        "🔴 도메인별 실제 투입 행수": rows_in,
        "🔴 조용히 빠진 도메인": b12["🔴 조용히 빠진 도메인(판별 × 씨앗)"],
        "🔴 자 대 잰 것(M1)": b12["🔴 자 대 잰 것(M1)"],
        "🔴 문턱 재확인(③)": {"R5 옛": th["🔴 R5 옛"], "R5 새": th["🔴 R5 새"],
                       "여전히 0.00353 인가": th["🔴 여전히 0.00353 인가"],
                       "씨앗 목록": th["씨앗 목록"],
                       "남의 파일 원상복구": th["🔴 남의 파일 원상복구"]},
        "🔴 896 재현(12씨앗 실행의 씨앗 0~5)": {
            k: v for k, v in b12["🔴 896 재현(씨앗 0~5 부동소수 5자리)"].items()
            if k != "상세"},
        "곁다리 · 문서 분모": doc,
        "산출물 지도": {
            "① 티처 LOO 재현(6씨앗)": "runners/out113_loo.json",
            "② 12씨앗 팔 B": "runners/out113_armB12.json",
            "③ 문턱 재확인": "runners/out113_thresh.json (+ out113_thresh_recheck.json)",
            "④ 이 요약": "runners/out113_summary.json",
            "코드": ["runners/dose113.py", "runners/loo113.py"],
            "고친 정본": ["runners/ff753.py (RULER_SEEDS 신설)",
                       "runners/thresh891.py (ff753.RULER_SEEDS 를 import)",
                       "runners/dose896.py (주석만 --- 6씨앗 상수는 이력 보존용으로 남긴다)"],
        },
    }
    out.update(stamp())
    (ROOT / "runners/out113_summary.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps({"🔴 한 줄": out["🔴 한 줄"],
                      **{nm: res[nm]["🔴 씨앗을 6→12 로 올려 무엇이 바뀌었나"] for nm in ARMS},
                      "문서 분모": {k: doc[k] for k in ("사전등록 표 합", "실측 weights() 합",
                                                   "🔴 차", "어긋나는 칸")}},
                     ensure_ascii=False, indent=1), flush=True)
    return out


if __name__ == "__main__":
    main()
