# -*- coding: utf-8 -*-
# 노트 874 — 매처 v1 로 애니 재검(사전등록 '874' · ipctl825 사본 — 원본 불변 · 애니 케이스만)
# 825 동결 문: '언어-정합 매칭 후 유보 겹침행 ≥20 이면 1회 재검'. 868 문: 행/군집 부트 병기.
import json
import re
import sys
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

sys.path.insert(0, "/Users/ax/world_model")
from lab import sideaudit, guards as G  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402
from lab.decay import AXD, AX  # noqa: E402
from lab.titlekey import norm, keys_of  # noqa: E402
from lab.pairboot import franchise_key  # noqa: E402

ROOT = Path("/Users/ax/world_model")


def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    if ok.sum() < 5:
        return np.nan
    return float(spearmanr(p[ok], yy[ok])[0])


def main():
    t0 = time.time()
    data = sideaudit.champion_data()
    f = G._fit_on(lambda: REGISTRY["F18_bagboost"]["cls"](seed=0), data, 2025.0)
    print(f"적합 {time.time()-t0:.0f}s", flush=True)

    def titles_of(dkey):
        r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
        return [norm(v.get("name") or v.get("title") or "") for v in r.values()]

    def train_titleset(dkey, expand=False):
        r = json.loads((AXD / f"{AX[dkey]}.json").read_text())
        # 1차 실행(wfail1)의 배선 인공물: AX 레지스트리는 *_axes.json(문패용 — synonyms 없음)을
        # 가리킨다. 확장 키는 **records 원본**에서 record_id 로 조인한다(교집합 2948/2948 실측).
        rrec = {}
        if expand:
            rrec = json.loads((ROOT / "data/state/wanime_records.json").read_text())
        yr = np.asarray(data.yr[dkey], float)
        y = np.asarray(data.dom[dkey][2], float)
        ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y)
        items = list(r.items())
        assert len(items) == len(y), f"{dkey} 정렬 어긋남"
        out = set()
        for (rid, rec), k in zip(items, ktr):
            if not k:
                continue
            base_key = {norm(rec.get("name") or rec.get("title") or "")} - {""}
            out |= (keys_of(rrec[rid]) | base_key) if (expand and rid in rrec) else base_key
        return out

    d = "애니"
    tl = titles_of(d)
    yr = np.asarray(data.yr[d], float)
    y_all = np.asarray(data.dom[d][2], float)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    assert len(tl) == len(y_all), "애니 정렬 어긋남"
    # 파트너: 세계애니는 v1 확장 · 만화/웹툰은 기존 norm(한글 원천)
    ptrain = train_titleset("세계애니", expand=True) | train_titleset("만화") | train_titleset("웹툰")
    p_exact = train_titleset("세계애니") | train_titleset("만화") | train_titleset("웹툰")
    ho_ix = np.flatnonzero(kho)
    is_ov = np.array([tl[i] in ptrain and tl[i] != "" for i in ho_ix])
    is_ov_ex = np.array([tl[i] in p_exact and tl[i] != "" for i in ho_ix])
    n_ov, n_ex = int(is_ov.sum()), int(is_ov_ex.sum())
    print(f"유보 {len(ho_ix)} · 겹침 v1 {n_ov}(exact {n_ex})", flush=True)

    out = {"유보": int(kho.sum()), "겹침 v1": n_ov, "겹침 exact": n_ex,
           "매처": "titlekey v1(세계애니 title/native/english/synonyms)"}
    if n_ov < 20:
        out["갈래"] = f"W — 언어-정합 후에도 겹침 {n_ov} < 20: 하한 그대로 실물 · 825 각주 종결(재검 문 닫힘)"
    else:
        A, M, yv, tv = data.slice(d, kho)
        p_joint = np.asarray(f.predict(d, A, M, tv), float)
        Atr, Mtr, ytr, ttr = data.slice(d, ktr)
        okr = np.isfinite(ytr)
        Xtr = np.nan_to_num(np.hstack([Atr, Mtr, np.asarray(ttr, float)[:, None]]), nan=0.5)[okr]
        Xho = np.nan_to_num(np.hstack([A, M, np.asarray(tv, float)[:, None]]), nan=0.5)
        best_a, best_s = None, -9
        for a in (0.1, 1.0, 10.0, 100.0, 1000.0):
            ss = []
            for tr, te in KFold(5, shuffle=True, random_state=1).split(Xtr):
                m = Ridge(alpha=a).fit(Xtr[tr], ytr[okr][tr])
                ss.append(rho(m.predict(Xtr[te]), ytr[okr][te]))
            s = float(np.nanmean(ss))
            if s > best_s:
                best_a, best_s = a, s
        p_ridge = Ridge(alpha=best_a).fit(Xtr, ytr[okr]).predict(Xho)

        def sub(mask):
            n = int(mask.sum())
            if n < 20:
                return {"n": n}
            dj, dr = rho(p_joint[mask], yv[mask]), rho(p_ridge[mask], yv[mask])
            return {"n": n, "합동": round(dj, 4), "릿지": round(dr, 4),
                    "Δ": round(dj - dr, 4), "2σ": round(2 * 0.262 / np.sqrt(n), 4)}
        full, clean, over = sub(np.ones(len(yv), bool)), sub(~is_ov), sub(is_ov)
        out.update({"alpha": best_a, "전체": full, "비겹침": clean, "겹침": over, "822 Δ": 0.1526})

        cl = clean
        if cl.get("Δ") is not None and cl["Δ"] >= cl["2σ"]:
            out["갈래 R"] = "지도 3/3 — 애니 합동승도 오염 아님(825 각주 해소)"
        elif cl.get("Δ") is not None and cl["Δ"] < cl["2σ"] and over.get("Δ") is not None and over["Δ"] > cl["Δ"]:
            out["갈래 R"] = "오염 — 애니 합동승 강등(지도 각주를 강등문으로)"
        else:
            out["갈래 R"] = "판정 유보(그 외)"

        # S(868 문): 비겹침 Δ 의 행 부트 대 franchise_key 군집 부트 병기(예측 벡터 재사용)
        idx = np.flatnonzero(~is_ov)
        keys = [franchise_key(tl[ho_ix[i]]) for i in idx]
        groups = {}
        for j, k in enumerate(keys):
            groups.setdefault(k or f"_s{j}", []).append(j)
        cl_units = [np.array(v) for v in groups.values()]

        def boot(units):
            rg = np.random.default_rng(874)
            vals = []
            n_u = len(units)
            for _ in range(10000):
                pick = rg.integers(0, n_u, n_u)
                sel = idx[np.concatenate([units[j] for j in pick])]
                vals.append(rho(p_joint[sel], yv[sel]) - rho(p_ridge[sel], yv[sel]))
            v = np.array(vals)
            return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
        rows_ci = boot([np.array([j]) for j in range(len(idx))])
        clus_ci = boot(cl_units)
        v_rows, v_clus = rows_ci[0] > 0, clus_ci[0] > 0
        out["S(868 문)"] = {"행 부트 CI": rows_ci, "군집 부트 CI": clus_ci,
                          "군집 수": len(cl_units), "판정 갈림": v_rows != v_clus,
                          "갈래": ("승격 후보 — 군집 자가 판정을 가른 첫 실물(별도 사전등록)"
                                 if v_rows != v_clus else "일치 — 병기 의무 유지·868 기결 강화")}
    out["초"] = round(time.time() - t0, 1)
    with open(ROOT / "runners/out874_ipctl.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
