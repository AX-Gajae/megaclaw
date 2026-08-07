"""노트 788(1열로 다시) — **만화 3열을 집 밖 둘(KR·CN)에서 잰다.** 규약 12.

🔴 배선 함정 둘을 지킨다:
  ① `pairs.to_arrays` 가 짝 행에 없는 열을 **0.5 · 마스크 0** 으로 채운다 ---
     그래서 **짝 행에도 3열을 붙인다**(안 붙이면 '안 통한다' 와 '열이 없다' 가
     구분되지 않는다).
  ② 사상을 **판(JP)에서 배워 짝(KR·CN)에 적용한다** --- 짝에서 다시 계산하면
     다른 축이다. 범주는 JP 집단 순서표, 수치는 JP 경험분포로 사상.

그리고 **시험 ②**(기준선 KR 0.6841 · CN 0.3094 를 ±0.02 재현)를 먼저 본다.
"""
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad")
import ff753 as FF
from lab import pairs as PR, rawaxes as RA

SRC = Path("/Users/ax/world_model/data/state/manga_records.json")
AXJ = Path("/Users/ax/world_model/data/state/manga_axes.json")
#: 🔴 노트 788 --- **`mg_nauthor` 1열만**(노트 787 이 고른 열)
FIELDS = [("n_author", False, "mg_nauthor")]
DRAWS = (7880, 7881, 7882)
SEEDS = (0, 1, 2)
#: 그 짝의 표본 2σ (상시 가드)
THR = {"KR 만화": 0.025, "CN 만화": 0.022}
PAIRNAMES = ("KR 만화",)      # 노트 788 --- KR 만


def _num_val(x):
    return (float(x) if isinstance(x, (int, float))
            and not isinstance(x, bool) else np.nan)


def learn_and_apply():
    """**판(JP)에서 사상을 배워 판·짝에 적용한다.** 라벨을 안 본다."""
    rec = json.loads(SRC.read_text())
    byid = rec if isinstance(rec, dict) else {
        x.get("record_id") or x.get("id"): x for x in rec}
    jp_ids = list(json.loads(AXJ.read_text()))          # 판의 만화 행 순서
    out = {"판": {}, "사상": {}}
    for field, cat, name in FIELDS:
        raw_jp = [(byid.get(k) or {}).get(field) for k in jp_ids]
        if cat:
            c = Counter(x for x in raw_jp if x not in (None, ""))
            big = [u for u, n in c.items() if n >= RA.MIN_GROUP]
            order = sorted(big, key=lambda u: -c[u])
            pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
            out["사상"][name] = ("cat", pos)
            v = np.array([pos.get(x, 0.5) for x in raw_jp], np.float32)
            m = np.array([1.0 if x in pos else 0.0 for x in raw_jp], np.float32)
        else:
            vv = np.array([_num_val(x) for x in raw_jp], float)
            ok = np.isfinite(vv)
            srt = np.sort(vv[ok])
            out["사상"][name] = ("num", srt)
            v = np.full(len(vv), 0.5)
            v[ok] = (np.searchsorted(srt, vv[ok], side="left")
                     / max(len(srt) - 1, 1))
            v = np.clip(v, 0.0, 1.0).astype(np.float32)
            m = ok.astype(np.float32)
        out["판"][name] = (v, m)
    return out, byid


def apply_to(rows, maps, byid):
    """짝 행에 3열을 붙인다. **판에서 배운 사상만 쓴다.**"""
    stat = {}
    for name, (kind, mp) in maps["사상"].items():
        field = next(f for f, _c, n in FIELDS if n == name)
        got = 0
        for rid, r in rows.items():
            raw = (byid.get(rid) or {}).get(field)
            ax = r.setdefault("axes", {})
            mk = r.setdefault("mask", {})
            if kind == "cat":
                if raw in mp:
                    ax[name] = float(mp[raw]); mk[name] = 1.0; got += 1
                else:
                    ax[name] = 0.5; mk[name] = 0.0
            else:
                x = _num_val(raw)
                if np.isfinite(x) and len(mp) > 1:
                    ax[name] = float(np.clip(
                        np.searchsorted(mp, x, side="left") / (len(mp) - 1), 0, 1))
                    mk[name] = 1.0; got += 1
                else:
                    ax[name] = 0.5; mk[name] = 0.0
        stat[name] = round(got / max(len(rows), 1), 3)
    return stat


def shuffled(cols, seed):
    """위약 --- 값만 섞고 마스크는 그대로(노트 335)."""
    rng = np.random.default_rng(seed)
    out = {}
    for name, (v, m) in cols.items():
        v2 = np.asarray(v, np.float32).copy()
        ii = np.flatnonzero(np.asarray(m) > 0)
        if len(ii) > 1:
            sh = v2[ii].copy(); rng.shuffle(sh); v2[ii] = sh
        out[name] = (v2, m)
    return out


def board_axes(colmap, doms, d0):
    """판 축 딕트 --- 만화에만 붙이고 나머지는 마스크 0."""
    ax = {}
    for name, (v, m) in colmap.items():
        per = {}
        for dd in doms:
            n = len(d0.dom[dd][2])
            if dd == "만화":
                per[dd] = (np.asarray(v, np.float32), np.asarray(m, np.float32))
            else:
                per[dd] = (np.full(n, 0.5, np.float32), np.zeros(n, np.float32))
        ax[name] = per
    return ax


def main():
    maps, byid = learn_and_apply()
    d0 = FF.shell(FF.base())
    doms = sorted(d0.dom)
    print(json.dumps({"판 만화 행": len(maps["판"][FIELDS[0][2]][0]),
                      "판 행": len(d0.dom["만화"][2]),
                      "사상": {k: (t, len(m) if t == "cat" else len(m))
                             for k, (t, m) in maps["사상"].items()}},
                     ensure_ascii=False), flush=True)

    # 짝 행을 한 번만 만들고 3열을 붙인다
    prow, pstat = {}, {}
    for nm in PAIRNAMES:
        rows = PR.build(nm)                      # 행수 불일치면 예외(시험 ①)
        pstat[nm] = apply_to(rows, maps, byid)
        prow[nm] = rows
        print(json.dumps({nm: {"행": len(rows), "붙은 비율": pstat[nm]}},
                         ensure_ascii=False), flush=True)
    low = [f"{nm}.{k}" for nm in PAIRNAMES for k, v in pstat[nm].items() if v < 0.9]
    if low:
        print(json.dumps({"중단": f"짝 마스크 0.9 미만 {low}"},
                         ensure_ascii=False), flush=True)
        return

    def score_all(data, tag, with_cols):
        out = {}
        for nm in PAIRNAMES:
            rows = prow[nm]
            if not with_cols:                    # 없이 팔 --- 3열을 지운다
                rows = {k: {**v,
                            "axes": {a: b for a, b in (v.get("axes") or {}).items()
                                     if a not in maps["사상"]},
                            "mask": {a: b for a, b in (v.get("mask") or {}).items()
                                     if a not in maps["사상"]}}
                        for k, v in rows.items()}
            src = PR.SRC_DOM[nm]
            names = list(data.names.get(src) or [])
            A, M, y, t = PR.to_arrays(rows, names)
            # 그 3열의 마스크 덮음을 찍는다(조용한 중립화 검사)
            idx = {n: i for i, n in enumerate(names)}
            cov = {k: round(float(M[:, idx[k]].mean()), 3)
                   for k in maps["사상"] if k in idx}
            from scipy.stats import spearmanr
            from lab import forms, guards as G
            cls = forms.REGISTRY["F18_bagboost"]["cls"]
            ok = np.isfinite(y)
            rs = []
            for s in SEEDS:
                f = G._fit_on(lambda s=s: cls(seed=s), data, 2025.0, seed=s)
                p = np.asarray(f.predict(src, A, M, t), float)
                kk = ok & np.isfinite(p)
                if kk.sum() >= 40 and len(np.unique(p[kk])) >= 3:
                    rs.append(float(spearmanr(p[kk], y[kk]).statistic))
            out[nm] = {"rho": round(float(np.mean(rs)), 4) if rs else None,
                       "씨앗별": [round(x, 4) for x in rs],
                       "그 3열 마스크": cov, "행": len(rows)}
        print(f"[{tag}] " + json.dumps({k: v["rho"] for k, v in out.items()},
                                       ensure_ascii=False), flush=True)
        return out

    t0 = time.time()
    none = score_all(d0, "① 없이", False)
    base_ok = {}
    for nm in PAIRNAMES:
        b = PR.BASELINE[nm]
        d = abs((none[nm]["rho"] or -9) - b)
        base_ok[nm] = {"기록": b, "실측": none[nm]["rho"], "차": round(d, 4),
                       "**±0.02 안**": bool(d <= 0.02)}
    print(json.dumps({"🔴 시험 ②": base_ok}, ensure_ascii=False), flush=True)

    real = score_all(FF.shell({**FF.base(), **board_axes(maps["판"], doms, d0)}),
                     "② 진짜", True)
    plac = []
    for ds in DRAWS:
        sh = shuffled(maps["판"], ds)
        # 짝도 같은 방식으로 섞는다
        prow_bak = {nm: {k: dict(v) for k, v in prow[nm].items()}
                    for nm in PAIRNAMES}
        for nm in PAIRNAMES:
            rng = np.random.default_rng(ds + hash(nm) % 1000)
            for name in maps["사상"]:
                keys = [k for k, v in prow[nm].items()
                        if (v.get("mask") or {}).get(name, 0) > 0]
                vals = [prow[nm][k]["axes"][name] for k in keys]
                rng.shuffle(vals)
                for k, x in zip(keys, vals):
                    prow[nm][k]["axes"][name] = x
        plac.append(score_all(FF.shell({**FF.base(),
                                        **board_axes(sh, doms, d0)}),
                              f"③ 위약 {ds}", True))
        for nm in PAIRNAMES:                      # 원래대로 되돌린다
            prow[nm] = prow_bak[nm]

    res = {}
    for nm in PAIRNAMES:
        pv = np.array([p[nm]["rho"] for p in plac], float)
        d = float((real[nm]["rho"] or np.nan) - np.nanmean(pv))
        res[nm] = {"없이": none[nm]["rho"], "**진짜**": real[nm]["rho"],
                   "위약 셋": [round(float(x), 4) for x in pv],
                   "위약 평균": round(float(np.nanmean(pv)), 4),
                   "**Δ**": round(d, 4), "**문턱**": THR[nm],
                   "**문턱 밖**": bool(d > THR[nm]),
                   "위약 전부보다 큼(참고)":
                       bool((real[nm]["rho"] or -9) > np.nanmax(pv)),
                   "그 3열 마스크": real[nm]["그 3열 마스크"], "행": real[nm]["행"]}
    ok2 = all(base_ok[nm]["**±0.02 안**"] for nm in PAIRNAMES)
    passed = [nm for nm in PAIRNAMES if res[nm]["**문턱 밖**"]]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "🔴 시험 ② 통과": ok2, "기준선 대조": base_ok,
        "짝별": res,
        "**문턱 넘은 짝**": passed or "없음",
        "판정 (가) 둘 다 넘음 → 규약 12 충족 · 채택":
            bool(ok2 and len(passed) == 2),
        "판정 (나) 하나만 → 미달": bool(ok2 and len(passed) == 1),
        "판정 (다) 둘 다 못 넘음 → 전이 안 된다": bool(ok2 and not passed),
        "판정 (라) 시험 ② 실패 → 판정 미룸": bool(not ok2),
        "집안(노트 781)": {"신호 몫": 0.0231, "2×뽑기SD": 0.0200, "도메인 2σ": 0.0163},
        "초": round(time.time() - t0, 1),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
