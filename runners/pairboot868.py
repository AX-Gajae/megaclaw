# -*- coding: utf-8 -*-
# 노트 868 B — 0순위 도달 산수(공개 전제 · 사전등록 '868'): 군집 대 무군집 부트의 끝점 이동이
# 자(2×끝점SE ∧ 플립)를 넘나 — 넘지 않으면 미결 16 은 '기결 — 자 무관' 마감(실험은 돌리지 않는다).
import json
import time
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

import sys
sys.path.insert(0, "/Users/ax/world_model")
from lab.entkey import ent_key_v3  # noqa: E402 — 동결 사본(entity862 import 금지)

ROOT = Path("/Users/ax/world_model")


def main():
    t0 = time.time()
    R = json.load(open(ROOT / "runners/out859_rows.json"))
    rows = R["행"]
    yv = np.array([r["y"] for r in rows])
    ens = np.array([r["champ_ens"] for r in rows])
    tb = np.array([r["tabpfn_ens"] for r in rows])

    def stat(idx):
        ok = np.isfinite(tb[idx]) & np.isfinite(yv[idx])
        a = float(spearmanr(tb[idx][ok], yv[idx][ok])[0])
        ok2 = np.isfinite(ens[idx]) & np.isfinite(yv[idx])
        b = float(spearmanr(ens[idx][ok2], yv[idx][ok2])[0])
        return a - b

    groups = {}
    solo = 0
    for i, r in enumerate(rows):
        k = ent_key_v3(r["group"])
        if not k:
            groups[f"_s{solo}"] = [i]
            solo += 1
        else:
            groups.setdefault(k, []).append(i)
    cl = [np.array(v) for v in groups.values()]
    arms = {"군집(v3·엔티티 %d)" % len(cl): cl,
            "무군집(행 51)": [np.array([i]) for i in range(len(rows))]}

    out = {"팔": {}}
    for name, units in arms.items():
        rg = np.random.default_rng(827)
        n_u = len(units)
        vals = []
        for _ in range(10000):
            pick = rg.integers(0, n_u, n_u)
            idx = np.concatenate([units[j] for j in pick])
            if len(np.unique(yv[idx])) < 5:
                continue
            vals.append(stat(idx))
        v = np.array(vals)
        lo, hi = float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
        sd = float(np.std(v, ddof=1))
        se_end = sd * 2.67 / np.sqrt(len(v))          # 862 와 같은 자(끝점 SE)
        verdict = "승(하한>0)" if lo > 0 else ("패(상한<0)" if hi < 0 else "불능(0 물음)")
        out["팔"][name] = {"percentile": [round(lo, 4), round(hi, 4)], "부트 SD": round(sd, 4),
                          "끝점 SE": round(se_end, 4), "유효 부트": len(v), "명목 판정": verdict}

    (c_arm,), (n_arm,) = [v for k, v in out["팔"].items() if k.startswith("군집")], \
                         [v for k, v in out["팔"].items() if k.startswith("무군집")]
    mv_lo = abs(c_arm["percentile"][0] - n_arm["percentile"][0])
    mv_hi = abs(c_arm["percentile"][1] - n_arm["percentile"][1])
    se2 = 2 * max(c_arm["끝점 SE"], n_arm["끝점 SE"])
    flip = c_arm["명목 판정"] != n_arm["명목 판정"]
    sig = (mv_lo >= se2) or (mv_hi >= se2)

    # ⓒ 재현 게이트: 862 동결 산출물의 군집 percentile 과 대조(±0.005)
    o862 = json.load(open(ROOT / "runners/out862_entity_v3.json"))
    p862 = o862["v3 자"]["percentile"]
    repro = (abs(c_arm["percentile"][0] - p862[0]) <= 0.005 and
             abs(c_arm["percentile"][1] - p862[1]) <= 0.005)

    if not repro:
        branch = f"ⓒ 재현 실패 — 862 {p862} 대 {c_arm['percentile']}: 구현 의심 우선·판정 중단"
    elif sig and flip:
        branch = "ⓐ 승격 후보 — 이동 유의 ∧ 플립 실재: 본사전등록 별도"
    else:
        branch = (f"ⓑ 기결 — 자 무관: 이동 (하한 {mv_lo:.4f} · 상한 {mv_hi:.4f}) 대 2×끝점SE {se2:.4f} · "
                  f"플립 {'있음(859 기각 선례 안)' if flip else '없음'} — 미결 16 마감·실험 안 돌림")
    out.update({"이동": {"하한": round(mv_lo, 4), "상한": round(mv_hi, 4)},
                "2×끝점SE": round(se2, 4), "플립": flip, "862 재현": repro,
                "갈래": branch, "초": round(time.time() - t0, 1)})
    with open(ROOT / "runners/out868_pairboot.json", "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
