# -*- coding: utf-8 -*-
# 노트 877 2단 — R/S 발화(사전등록 '877' · is_ov = IP 기준 22행 · 875 동결 갈래 그대로)
# 수동 8건의 눈 판정(IP 단위)은 아래 VERDICTS 에 근거와 함께 박는다 — 산출물 필드 의무(#42).
import datetime as dt
import json
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
from lab.pairboot import franchise_key  # noqa: E402
from lab.titlekey import norm  # noqa: E402
from lab.decay import AXD, AX  # noqa: E402

ROOT = Path("/Users/ax/world_model")

VERDICTS = {   # 수동 8건 — IP 단위 눈 판정(로마자↔한글 대역 · 전부 같은 IP)
    16: "통과 — 해골기사님 = Gaikotsu Kishi(Skeleton Knight) 동일 IP",
    70: "통과 — Re:Zero 동일 IP(4기 대 2기 — 시즌 불문)",
    126: "통과 — 최애의 아이 = [Oshi no Ko] 동일 IP",
    227: "통과 — 불멸의 그대에게 = Fumetsu no Anata e 동일 IP",
    463: "통과 — 베헤모스 동일 작품(동일 IP)",
    591: "통과 — 5등분의 신부 = Go-toubun no Hanayome 동일 IP(스페셜 대 2기 — 시즌 불문)",
    2045: "통과 — 흑집사 = Kuroshitsuji 동일 IP",
    2046: "통과 — 흑집사 = Kuroshitsuji II 동일 IP",
}


def rho(p, yy):
    ok = np.isfinite(p) & np.isfinite(yy)
    return float(spearmanr(p[ok], yy[ok])[0]) if ok.sum() >= 5 else np.nan


def main():
    t0 = time.time()
    ipmap = json.load(open(ROOT / "runners/out877_ipmap.json"))
    rows = []
    for r in ipmap["전행 표"]:
        if r["IP 판정"].startswith("통과"):
            rows.append(r["행"])
        elif r["행"] in VERDICTS and VERDICTS[r["행"]].startswith("통과"):
            rows.append(r["행"])
    ov_rows = sorted(set(rows))
    n = len(ov_rows)
    print(f"IP 기준 겹침 최종 {n} (자동 {ipmap['자동 통과']} + 수동 통과 {n - ipmap['자동 통과']})", flush=True)
    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "눈금": ipmap["눈금"], "겹침 행": ov_rows, "수동 판정": VERDICTS, "계수": n}
    if n < 20:
        out["갈래"] = f"W — IP 기준 {n} < 20: 그 수로 재선언('19' 철회)"
        _save(out); return

    data = sideaudit.champion_data()
    f = G._fit_on(lambda: REGISTRY["F18_bagboost"]["cls"](seed=0), data, 2025.0)
    print(f"적합 {time.time()-t0:.0f}s", flush=True)
    r_an = json.loads((AXD / f"{AX['애니']}.json").read_text())
    an_items = list(r_an.items())
    tl_full = [norm(v.get("name") or v.get("title") or "") for _k, v in an_items]
    yr = np.asarray(data.yr["애니"], float)
    y_all = np.asarray(data.dom["애니"][2], float)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y_all)
    ktr = np.isfinite(yr) & (yr < 2025.0) & np.isfinite(y_all)
    ho_ix = np.flatnonzero(kho)
    ovset = set(ov_rows)
    is_ov = np.array([int(i) in ovset for i in ho_ix])

    A, M, yv, tv = data.slice("애니", kho)
    p_joint = np.asarray(f.predict("애니", A, M, tv), float)
    Atr, Mtr, ytr, ttr = data.slice("애니", ktr)
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
        nn = int(mask.sum())
        if nn < 20:
            return {"n": nn}
        dj, dr = rho(p_joint[mask], yv[mask]), rho(p_ridge[mask], yv[mask])
        return {"n": nn, "합동": round(dj, 4), "릿지": round(dr, 4),
                "Δ": round(dj - dr, 4), "2σ": round(2 * 0.262 / np.sqrt(nn), 4)}
    full, clean, over = sub(np.ones(len(yv), bool)), sub(~is_ov), sub(is_ov)
    out.update({"alpha": best_a, "전체": full, "비겹침": clean, "겹침": over, "822 Δ": 0.1526})
    cl = clean
    if cl.get("Δ") is not None and cl["Δ"] >= cl["2σ"]:
        out["갈래 R"] = "지도 3/3 — 애니 합동승도 오염 아님(825 각주 최종 해소)"
    elif cl.get("Δ") is not None and cl["Δ"] < cl["2σ"] and over.get("Δ") is not None and over["Δ"] > cl["Δ"]:
        out["갈래 R"] = "오염 — 애니 합동승 강등"
    else:
        out["갈래 R"] = "판정 유보(그 외)"

    idx = np.flatnonzero(~is_ov)
    keys = [franchise_key(tl_full[int(ho_ix[j])]) for j in idx]
    groups = {}
    for j, k in enumerate(keys):
        groups.setdefault(k or f"_s{j}", []).append(j)
    cl_units = [np.array(v) for v in groups.values()]

    def boot(units):
        rg = np.random.default_rng(877)
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
    out["S(868 문)"] = {"행 부트 CI": rows_ci, "군집 부트 CI": clus_ci, "군집 수": len(cl_units),
                      "판정 갈림": (rows_ci[0] > 0) != (clus_ci[0] > 0),
                      "갈래": ("승격 후보 — 별도 사전등록" if (rows_ci[0] > 0) != (clus_ci[0] > 0)
                             else "일치 — 병기 유지·868 기결 강화")}
    out["초"] = round(time.time() - t0, 1)
    _save(out)


def _save(out):
    with open(ROOT / "runners/out877_recheck.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("겹침 행", "수동 판정")},
                     ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
