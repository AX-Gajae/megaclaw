# -*- coding: utf-8 -*-
# 노트 884 절 C — 신규 1열 집안 측정(사전등록 '884' + 부칙 · raw780 관례 그대로)
# 1순위(판정) 모바일 n_device(2σ 0.0124) · 병기 관측 영화 국적(2σ 0.0130 · 판정 불가).
# 위약 6뽑기(값만 섞고 마스크 무늬 보존 — 노트 335) · 씨앗 3 · 라벨 안 봄 · 1열씩(규약 39).
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")
import ff753 as FF  # noqa: E402 — 열 주입 정본(raw780 관례)
from lab import rawaxes as RA  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402
from lab.harness import evaluate  # noqa: E402

ROOT = Path("/Users/ax/world_model")
CLS = REGISTRY["F18_bagboost"]["cls"]
T = 2025.0
SEEDS = (3,)
BASE_OK = (0.455, 0.485)          # 기준선 게이트(raw780 관례)
PLACEBO = (8840, 8841, 8842, 8843, 8844, 8845)      # 뽑기 6(규약 20·38)
MIN_GROUP = 20
# (도메인, 축 파일, 레코드 파일(없으면 축 파일 자신), 필드, 범주형?, 이름, 2σ, 역할)
COLS = [
    ("모바일", "mobile_axes", "mobile_records", "n_device", False, "mob_ndevice", 0.0124, "1순위(판정)"),
    ("영화", "kobis_axes", None, "국적", True, "film_nation", 0.0130, "병기(관측 — 판정 불가)"),
]


def board(data):
    """raw780 관례 — pooled 로 판, 도메인별 평균."""
    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": float(np.mean(vals)),
            "도메인": {k: float(np.mean(a)) for k, a in per.items()}}


def main():
    t0 = time.time()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    built = {}
    DS = ROOT / "data/state"
    for dom, axf, recf, field, cat, name, two_sigma, role in COLS:
        ax = json.loads((DS / f"{axf}.json").read_text())
        ids = list(ax)                              # 판 행 순서의 정본(raw780 관례)
        if recf:
            rec = json.loads((DS / f"{recf}.json").read_text())
            byid = rec if isinstance(rec, dict) else {
                x.get("record_id") or x.get("id"): x for x in rec}
            raw = [(byid.get(k) or {}).get(field) for k in ids]
        else:
            raw = [(ax.get(k) or {}).get(field) for k in ids]
        n_board = len(d0.dom[dom][2])
        got = RA._cat(raw, MIN_GROUP) if cat else RA._num(raw)
        if got is None or len(raw) != n_board:      # 노트 359 — 길이 불일치 = 조용한 중립화
            built[name] = {"⛔": "배선/눈금 실패", "원천 행": len(raw), "판 행": n_board,
                           "눈금 결과": "None" if got is None else "ok"}
            continue
        v, m = got
        k = int(len(np.unique(np.asarray(v)[np.asarray(m) > 0.5])))
        built[name] = {"dom": dom, "v": v, "m": m, "실효 범주/값": k, "2σ": two_sigma,
                       "역할": role, "필드": field, "마스크율": round(float(m.mean()), 4),
                       "원천 행": len(raw), "판 행": n_board}
    wire = {n: {kk: b[kk] for kk in b if kk not in ("v", "m")} for n, b in built.items()}
    print(json.dumps({"배선": wire}, ensure_ascii=False), flush=True)
    ok_names = [n for n, b in built.items() if "v" in b]
    if not ok_names:
        raise SystemExit("배선 전멸 — 중단")

    def axis_for(name, shuffle_seed=None):
        """그 도메인에만 붙이고 나머지는 마스크 0. 위약은 값만 섞는다."""
        b = built[name]
        rng = np.random.default_rng(shuffle_seed) if shuffle_seed else None
        per = {}
        for dd in doms:
            nn = len(d0.dom[dd][2])
            if dd == b["dom"]:
                vv, mm = b["v"].copy(), b["m"].copy()
                if rng is not None:
                    ii = np.flatnonzero(mm > 0)
                    if len(ii) > 1:
                        sh = vv[ii].copy(); rng.shuffle(sh); vv[ii] = sh
                per[dd] = (vv, mm)
            else:
                per[dd] = (np.full(nn, 0.5, np.float32), np.zeros(nn, np.float32))
        return {name: per}

    b0 = board(d0)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        raise SystemExit(f"기준선 이탈 {b0['판']:.4f} — 중단")
    print(json.dumps({"① 없이 판": round(b0["판"], 4),
                      "도메인": {b["dom"]: round(b0["도메인"][b["dom"]], 4)
                              for b in built.values() if "dom" in b}},
                     ensure_ascii=False), flush=True)

    res = {}
    for name in ok_names:
        b = built[name]; dom = b["dom"]
        real = board(FF.shell({**FF.base(), **axis_for(name)}))
        pv, pb = [], []
        for ps in PLACEBO:
            s = board(FF.shell({**FF.base(), **axis_for(name, ps)}))
            pv.append(s["도메인"][dom]); pb.append(s["판"])
            print(f"  {name} 위약 {ps}: {s['도메인'][dom]:.4f}", flush=True)
        pv = np.array(pv, float)
        share = float(real["도메인"][dom] - pv.mean())
        sd = float(pv.std(ddof=1))
        res[name] = {
            "역할": b["역할"], "도메인": dom, "필드": b["필드"], "실효 범주/값": b["실효 범주/값"],
            "마스크율": b["마스크율"],
            "없이(그 도메인)": round(b0["도메인"][dom], 4),
            "진짜(그 도메인)": round(real["도메인"][dom], 4),
            "위약 6": [round(x, 4) for x in pv], "위약 평균": round(float(pv.mean()), 4),
            "뽑기 SD": round(sd, 5), "신호 몫": round(share, 4),
            "그 도메인 2σ": b["2σ"], "2×뽑기SD": round(2 * sd, 4),
            "위약 6/6": bool(real["도메인"][dom] > pv.max()),
            "판 없이": round(b0["판"], 4), "판 진짜": round(real["판"], 4),
            "판 변화": round(float(real["판"] - b0["판"]), 4),
            "판 위약 평균": round(float(np.mean(pb)), 4),
        }
        r = res[name]
        r["자 넷"] = {"① ≥2σ": share >= b["2σ"], "② ≥2×뽑기SD": share >= 2 * sd,
                    "③ 위약 6/6": r["위약 6/6"], "④ 판 −0.0045 밖 아님": r["판 변화"] > -0.0045}
        if b["역할"].startswith("1순위"):
            passed = all(r["자 넷"].values())
            harm = (share < 0 and abs(share) > b["2σ"]) or r["판 변화"] <= -0.0045
            r["갈래"] = ("(가) 집안 통과 — 단 채택 불가(집 밖 짝 부재는 영화 · 모바일은 앱 짝 존재 → 다음 사이클 집 밖)"
                        if passed else "(다) 해롭다 — 영구 제외 후보" if harm else "(나) 미달 — 서랍")
        else:
            r["갈래"] = "판정 불가(병기 관측 — 부칙대로 채택·갈래 발동 없음)"

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
           "학습측 재료 지문": {d: hashlib.sha256(
               np.ascontiguousarray(np.asarray(d0.dom[d][2], float)).tobytes()).hexdigest()[:12]
               for d in doms},
           "설정": {"씨앗": list(SEEDS), "위약": list(PLACEBO), "MIN_GROUP": MIN_GROUP, "T": T},
           "배선": wire, "결과": res, "초": round(time.time() - t0, 1)}
    with open(ROOT / "runners/out884_newcol.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "학습측 재료 지문"},
                     ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
