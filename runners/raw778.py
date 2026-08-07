"""노트 778 — **rawaxes 를 만화·게임·도서로 넓힌다.** 🔴 묶음 금지 · 도메인별로.

노트 777 이 `rawaxes.SPEC` 이 다섯 도메인만 훑은 것을 찾았다. 여기서 세 도메인
11열을 **그 관례 그대로**(라벨을 한 번도 안 본다) 만들고 **노트 348 의 순서**로
도메인 하나씩 재고 **그 도메인 점수**로 판정한다.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import forms, rawaxes as RA
from lab.harness import evaluate

T = 2025.0
SEEDS = (0, 1, 2)                 # ⚠️ 팔이 열셋이라 줄였다(사전등록에 적음)
DRAWS = (7780, 7781, 7782)
CLS = forms.REGISTRY["F18_bagboost"]["cls"]
BASE_OK = (0.455, 0.485)
#: (도메인, 축 파일, 레코드 파일, 필드, 범주형인가, 축 이름)
NEW = [
    ("만화", "manga_axes", "manga_records", "format", True, "mg_format"),
    ("만화", "manga_axes", "manga_records", "is_adult", True, "mg_adult"),
    ("만화", "manga_axes", "manga_records", "n_author", False, "mg_nauthor"),
    ("게임", "game_axes", "game_records", "is_free", True, "gm_free"),
    ("게임", "game_axes", "game_records", "n_dlc", False, "gm_ndlc"),
    ("게임", "game_axes", "game_records", "n_platform", False, "gm_nplat"),
    ("도서", "book_axes", "book_records", "book_format", True, "bk_format"),
    ("도서", "book_axes", "book_records", "pages", False, "bk_pages"),
    ("도서", "book_axes", "book_records", "width_mm", False, "bk_width"),
    ("도서", "book_axes", "book_records", "height_mm", False, "bk_height"),
    ("도서", "book_axes", "book_records", "weight_g", False, "bk_weight"),
]
#: 그 도메인 2σ (노트 717 의 c/√n · 유보 채점으로)
SIG2 = {"만화": 0.0163, "게임": 0.0195, "도서": 0.0205}


def board(data):
    vals, per = [], {}
    for s in SEEDS:
        sc = evaluate(lambda s=s: CLS(seed=s), data, T=T)
        vals.append(float(data.pooled(sc, T=T)))
        for k, v in sc.items():
            if np.isfinite(v):
                per.setdefault(k, []).append(float(v))
    return {"판": round(float(np.mean(vals)), 4),
            "씨앗별": [round(v, 4) for v in vals],
            "도메인": {k: round(float(np.mean(a)), 4) for k, a in per.items()}}


def make():
    """`rawaxes` 관례 그대로 만든다. **라벨을 한 번도 안 본다.**"""
    D = Path("/Users/ax/world_model/data/state")
    out, skipped = {}, []
    for dom, axf, recf, field, cat, name in NEW:
        ax = json.loads((D / f"{axf}.json").read_text())
        rec = json.loads((D / f"{recf}.json").read_text())
        byid = rec if isinstance(rec, dict) else {
            x.get("record_id") or x.get("id"): x for x in rec}
        ids = list(ax)
        raw = [(byid.get(k) or {}).get(field) for k in ids]
        got = RA._cat(raw, RA.MIN_GROUP) if cat else RA._num(raw)
        if got is None:
            skipped.append(f"{dom}.{field}")
            continue
        out[name] = (dom, got)
    return out, skipped


def main():
    cols, skipped = make()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    wr = {}
    for name, (dom, (v, m)) in cols.items():
        n = len(d0.dom[dom][2])
        wr[name] = {"도메인": dom, "행": len(v), "판 행": n, "맞나": len(v) == n,
                    "마스크": round(float(np.mean(m)), 3),
                    "값 가짓수": int(len(np.unique(np.asarray(v)[np.asarray(m) > .5])))}
    print(json.dumps({"만든 열": len(cols), "빠진 열": skipped or "없음",
                      "배선": wr}, ensure_ascii=False), flush=True)
    bad = [k for k, r in wr.items() if not r["맞나"] or r["값 가짓수"] < 2]
    if bad:
        print(json.dumps({"중단": f"배선 이상 {bad}"}, ensure_ascii=False), flush=True)
        return

    def axis_for(dom, shuffle_seed=None):
        """그 도메인 열만 넣는다. 다른 도메인은 마스크 0(=열이 없다)."""
        ax = {}
        rng = np.random.default_rng(shuffle_seed) if shuffle_seed else None
        for name, (d, (v, m)) in cols.items():
            if d != dom:
                continue
            per = {}
            for dd in doms:
                nn = len(d0.dom[dd][2])
                if dd == dom:
                    vv = np.asarray(v, np.float32).copy()
                    mm = np.asarray(m, np.float32).copy()
                    if rng is not None:
                        ii = np.flatnonzero(mm > 0)
                        if len(ii) > 1:
                            sh = vv[ii].copy(); rng.shuffle(sh); vv[ii] = sh
                    per[dd] = (vv, mm)
                else:
                    per[dd] = (np.full(nn, 0.5, np.float32),
                               np.zeros(nn, np.float32))
            ax[name] = per
        return ax

    b0 = board(d0)
    print(json.dumps({"① 없이": b0["판"],
                      "도메인": {d: b0["도메인"].get(d) for d in SIG2}},
                     ensure_ascii=False), flush=True)
    if not (BASE_OK[0] <= b0["판"] <= BASE_OK[1]):
        print(json.dumps({"중단": f"기준선 {b0['판']}"}, ensure_ascii=False), flush=True)
        return

    res = {}
    for dom in ("만화", "게임", "도서"):
        ncol = sum(1 for _, (d, _) in cols.items() if d == dom)
        t0 = time.time()
        real = board(FF.shell({**FF.base(), **axis_for(dom)}))
        plac = []
        for ds in DRAWS:
            plac.append(board(FF.shell({**FF.base(), **axis_for(dom, ds)})))
        pv = np.array([p["도메인"].get(dom, np.nan) for p in plac])
        pb = np.array([p["판"] for p in plac])
        sig = float(real["도메인"].get(dom, np.nan) - np.nanmean(pv))
        res[dom] = {
            "열 수": ncol,
            "없이(그 도메인)": b0["도메인"].get(dom),
            "**진짜(그 도메인)**": real["도메인"].get(dom),
            "위약(그 도메인) 셋": [round(float(x), 4) for x in pv],
            "위약 평균": round(float(np.nanmean(pv)), 4),
            "**신호 몫**": round(sig, 4),
            "**그 도메인 2σ**": SIG2[dom],
            "**2σ 밖**": bool(abs(sig) > SIG2[dom]),
            "위약 전부보다 큰가": bool(real["도메인"].get(dom, -9) > np.nanmax(pv)),
            "판 없이": b0["판"], "판 진짜": real["판"],
            "판 변화": round(float(real["판"] - b0["판"]), 4),
            "판 위약 평균": round(float(np.mean(pb)), 4),
            "초": round(time.time() - t0, 1),
        }
        print(f"[{dom}] " + json.dumps(
            {k: res[dom][k] for k in ("열 수", "**진짜(그 도메인)**", "위약 평균",
                                      "**신호 몫**", "**2σ 밖**", "판 변화", "초")},
            ensure_ascii=False), flush=True)

    keep = [d for d in res
            if res[d]["**2σ 밖**"] and res[d]["**신호 몫**"] > 0
            and res[d]["위약 전부보다 큰가"] and res[d]["판 변화"] > -0.0045]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "🔴 판정은 그 도메인 점수로": "노트 348 의 검사 ⑤ · 묶음 금지(규약 36)",
        "기준선": b0["판"], "만든 열": len(cols), "빠진 열": skipped or "없음",
        "도메인별": res,
        "**남길 도메인**": keep or "없음",
        "판정 (가) 남는 도메인 있음": bool(keep),
        "판정 (나)·(다) 셋 다 못 넘음 → 원천이 말랐다": bool(not keep),
        "🔴 남아도 그냥 채택 안 한다": "규약 12 --- 집 밖 둘로 넘긴다",
        "⚠️ 씨앗 3 으로 줄였다": "팔이 열셋이라 · 사전등록에 적음",
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
