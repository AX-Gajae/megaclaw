# -*- coding: utf-8 -*-
"""러너 1022 — 내재 상태 엔진 v0 (사전등록 docs/탐색/1022.md · 커밋 01903d326).

순서를 «기계로» 강제한다(§4): 방향 탐침 → 시대 관문 → 자료·사다리·leak → ⓐ×4 →
위약·MDE(assert_mde — 레인 기록) → ⓑⓒ×4 → 판·게이트 → 산출물.
CPU 전용(threads 4) · load1>10 이면 60초 재잼 반복 · 국면 체크포인트(재개 가능).

씀: python3 runners/state_engine1022.py run
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_os.environ.setdefault("OMP_NUM_THREADS", "4")
_os.environ.setdefault("MKL_NUM_THREADS", "4")
import datetime as dt
import gzip
import hashlib
import json
import os
import time

import numpy as np

from pretrain import state_engine as SE
from pretrain.leak_guard import assert_no_leak, LeakDetected
from pretrain.mde_guard import mde_of, assert_mde, MdeUnderpowered
from pretrain.epoch_guard import assert_epoch

OUT = SE.OUT_DIR
LOG = os.path.join(OUT, "run1022.out")
STATE = os.path.join(OUT, "phase_state.json")


def log(msg):
    line = "%s %s" % (dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_gate():
    """조항 76 미러 — load1>10 이면 60초 재잼 반복(until 관문)."""
    while True:
        l1 = os.getloadavg()[0]
        if l1 <= 10.0:
            return l1
        log("load1=%.2f > 10 — 60초 대기" % l1)
        time.sleep(60)


def jdump(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)


def sha16b(b):
    return hashlib.sha256(b).hexdigest()[:16]


def phase_done(name):
    if not os.path.exists(STATE):
        return False
    return name in json.load(open(STATE)).get("done", [])


def mark_done(name):
    st = json.load(open(STATE)) if os.path.exists(STATE) else {"done": []}
    if name not in st["done"]:
        st["done"].append(name)
    st["시각"] = dt.datetime.now().isoformat()
    jdump(STATE, st)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "ckpt"), exist_ok=True)
    log("=== 1022 러너 시작 · pid %d ===" % os.getpid())

    # ── 0. 방향 탐침(v5.3-2) + 자기시험 — 어긋나면 측정 없이 중단 ──────────
    if True:
        t = 0.7
        g_main = lambda d, th: d > th            # ㉠ Δ_주 > MDE
        g_cov = lambda d, th: d >= -th           # ㉢ Δ_cov ≥ −MDE_cov
        probes = {
            "㉠ 개선 극값 +2t 참": g_main(+2 * t, t) is True,
            "㉠ 악화 극값 −2t 거짓": g_main(-2 * t, t) is False,
            "㉢ 악화 극값 −2t 거짓": g_cov(-2 * t, t) is False,
            "㉢ 개선 극값 +2t 참": g_cov(+2 * t, t) is True,
            "㉢ 0 참": g_cov(0.0, t) is True,
        }
        from pretrain.leak_guard import selftest as leak_self
        ls = leak_self()
        probes["leak_guard 자기시험"] = bool(ls["전부_기대대로"])
        se_self = SE.selftest()
        probes["state_engine 자기시험(핀볼 항등 포함)"] = bool(se_self["전부_기대대로"])
        import subprocess
        r = subprocess.run([_sys.executable, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "pretrain", "mde_guard.py")], capture_output=True)
        probes["mde_guard 자기시험"] = (r.returncode == 0)
        jdump(os.path.join(OUT, "probes1022.json"), {"방향 탐침": probes, "leak": ls})
        if not all(probes.values()):
            log("🔴 방향 탐침 어긋남 — 측정 없이 중단: %s" % probes)
            raise SystemExit(1)
        log("방향 탐침 %d/%d 기대대로" % (sum(probes.values()), len(probes)))

    # ── 1. 시대 관문(§8 · 부칙 4) ─────────────────────────────────────
    got_sao = SE.sha16(SE.SAO_PATH)
    if got_sao != SE.SHA_SAO:
        log("🔴 시대 불일치 sao.npz %s ≠ %s — 측정 없이 중단" % (got_sao, SE.SHA_SAO))
        raise SystemExit(1)
    ep = assert_epoch(SE.SHA_REPORT, path=SE.REPORT_PATH)
    epoch = {"sao.npz(실측)": got_sao, "report.json(assert_epoch 실측)": ep,
             "meta.jsonl": SE.sha16(SE.META_PATH), "emb": SE.sha16(SE.EMB_PATH),
             "pubdate_v1": SE.sha16(SE.PUB_V1), "pubdate_v2": SE.sha16(SE.PUB_V2)}
    log("시대 관문 통과: %s" % json.dumps(epoch, ensure_ascii=False)[:200])

    # ── 2. 자료·사다리·leak (§1·§6) ───────────────────────────────────
    load_gate()
    log("패널·문서 적재 시작")
    ents, panel_shas = SE.load_panel()
    docs, doc_cnt = SE.load_docs()
    keys, pairs, ladder = SE.build_pairs(ents, docs)
    log("사다리: %s" % json.dumps(ladder, ensure_ascii=False))
    log("문서 계수: %s" % json.dumps(doc_cnt, ensure_ascii=False))
    stamps_path = os.path.join(OUT, "leak_stamps.json")
    if not phase_done("leak"):
        log("leak_guard 사용 쌍 전수 검사 시작 (쌍 %d)" % len(pairs))
        try:
            stamps = SE.leak_stamps(keys, ents, docs, pairs)
        except LeakDetected as e:
            log("🔴 LeakDetected — 측정 없이 중단: %s" % e)
            raise SystemExit(1)
        jdump(stamps_path, stamps)
        mark_done("leak")
        log("leak 통과: %s" % json.dumps({k: v for k, v in stamps.items()
                                          if k != "대표 스탬프(문서·실측 반환값)"},
                                         ensure_ascii=False))
    stamps = json.load(open(stamps_path))

    feat = SE.build_features(keys, ents, pairs)
    emb = np.load(SE.EMB_PATH)["E"]
    train_mask = feat["split"] == 0
    extra_b, pca_info, c_scal_raw = SE.build_disc_features(keys, docs, pairs, emb, train_mask)
    # ⓒ 스칼라 2 [has_disc, log1p n_pre] — train 통계 z 표준화(§2)
    m = c_scal_raw[train_mask].mean(0)
    s = c_scal_raw[train_mask].std(0)
    s[s < 1e-6] = 1.0
    c_scal = ((c_scal_raw - m) / s)
    for nm, arr in (("Sc", feat["Sc"]), ("C", feat["C"]), ("R", feat["R"]),
                    ("extra_b", extra_b), ("c_scal", c_scal)):
        if not np.isfinite(arr).all():
            log("🔴 비유한 특징 %s — 측정 없이 중단(조항 59)" % nm)
            raise SystemExit(1)
    log("특징 완성(전 배열 유한 실측) · PCA: %s" % json.dumps(pca_info, ensure_ascii=False))

    # 쌍 색인 산출물(§7)
    idx_path = os.path.join(OUT, "pairs_index.jsonl.gz")
    if not phase_done("index"):
        with gzip.open(idx_path, "wt", encoding="utf-8") as f:
            for (ei, t, sp, n_pre) in pairs:
                f.write(json.dumps({
                    "개체": keys[ei], "t": dt.date.fromordinal(t).isoformat(),
                    "분할": "train" if sp == 0 else "val", "n_pre": n_pre,
                    "문서id": [d[3] for d in docs.get(keys[ei], [])[:n_pre]]},
                    ensure_ascii=False) + "\n")
        mark_done("index")

    va = np.where(feat["split"] == 1)[0]
    clusters = feat["ent_i"][va]
    seq_ctx = (pairs, keys, docs, emb, c_scal)

    def run_arm(arm):
        preds = {}
        npar = None
        for seed in SE.SEEDS:
            pth = os.path.join(OUT, "pred_%s_s%d.npz" % (arm, seed))
            if os.path.exists(pth):
                z = np.load(pth)
                preds[seed] = z["P"]
                npar = int(z["n_par"])
                continue
            load_gate()
            t0 = time.time()
            P, n_par, mods = SE.train_arm(arm, seed, feat, extra_b, seq_ctx)
            npar = n_par
            np.savez_compressed(pth, P=P, n_par=n_par)
            import torch
            torch.save([md.state_dict() for md in mods],
                       os.path.join(OUT, "ckpt", "%s_s%d.pt" % (arm, seed)))
            log("팔 %s 씨앗 %d 완료 %.1f분 · 파라미터 %d" % (arm, seed, (time.time() - t0) / 60, n_par))
        return preds, npar

    # ── 3. ⓐ ×4 (§4-3 — 문서 무접촉) ─────────────────────────────────
    preds_a, npar_a = run_arm("a")
    Rva = feat["R"][va].astype(np.float64)
    pp_a = {s: SE.pinball_cells(preds_a[s].astype(np.float64), Rva) for s in SE.SEEDS}
    cov_a = {s: SE.coverage_pairs(preds_a[s].astype(np.float64), Rva) for s in SE.SEEDS}
    pp_a_bar = np.mean([pp_a[s] for s in SE.SEEDS], axis=0)

    # ── 4. 위약 = 씨앗쌍 영대비 → MDE 사전 (§4-4~6 · 부칙 6) ──────────
    mde_path = os.path.join(OUT, "placebo1022.json")
    if not phase_done("mde"):
        deltas, ses, deltas_cov, ses_cov = [], [], [], []
        for i in range(len(SE.SEEDS)):
            for j in range(i + 1, len(SE.SEEDS)):
                d = pp_a[SE.SEEDS[i]] - pp_a[SE.SEEDS[j]]
                deltas.append(float(d.mean()))
                ses.append(SE.cluster_boot_se(d, clusters, 2000, 7022))
                dc = cov_a[SE.SEEDS[i]] - cov_a[SE.SEEDS[j]]
                deltas_cov.append(float(dc.mean()))
                ses_cov.append(SE.cluster_boot_se(dc, clusters, 2000, 7022))
        se_pre = max(ses)
        j_pre = float(np.std(deltas, ddof=1))
        mde_pre = mde_of(se_pre, j_pre)
        se_pre_c = max(ses_cov)
        j_pre_c = float(np.std(deltas_cov, ddof=1))
        mde_pre_cov = mde_of(se_pre_c, j_pre_c)
        sdcl = SE.sd_cl(pp_a_bar, clusters)
        aim = 0.15 * sdcl
        placebo = {"Δ_위약(씨앗쌍 6)": deltas, "SE^cl_위약(B=2000·시드7022)": ses,
                   "SD(Δ_위약·ddof=1)": j_pre, "MDE_사전": mde_pre,
                   "cov Δ_위약": deltas_cov, "cov SE^cl": ses_cov,
                   "cov SD": j_pre_c, "MDE_cov_사전": mde_pre_cov,
                   "SD_cl(pp̄_ⓐ)": sdcl, "겨냥(㉠)=0.15×SD_cl": aim, "겨냥(㉢ 악화)": 0.05,
                   "MAE참고 pp̄_ⓐ 평균": float(pp_a_bar.mean())}
        jdump(mde_path, placebo)                       # 위약 파일은 이후 불변(조항 66)
        pl_sha = sha16b(open(mde_path, "rb").read())
        lanes = {"위약 파일 sha": pl_sha}
        try:
            st = assert_mde(mde_pre, aim, pl_sha)
            lanes["㉠"] = {"레인": "[판정]", "스탬프": st}
        except MdeUnderpowered as e:
            lanes["㉠"] = {"레인": "[측정] 강등", "사유": str(e)}
        try:
            st = assert_mde(mde_pre_cov, 0.05, pl_sha)
            lanes["㉢"] = {"레인": "[판정](보조)", "스탬프": st}
        except MdeUnderpowered as e:
            lanes["㉢"] = {"레인": "관찰 강등", "사유": str(e)}
        jdump(os.path.join(OUT, "mde_lane1022.json"), lanes)
        mark_done("mde")
        log("MDE 사전: ㉠ %s (MDE %.5f · 겨냥 %.5f) · ㉢ %s (MDE_cov %.5f)"
            % (lanes["㉠"]["레인"], mde_pre, aim, lanes["㉢"]["레인"], mde_pre_cov))
    placebo = json.load(open(mde_path))
    lanes = json.load(open(os.path.join(OUT, "mde_lane1022.json")))

    # ── 5. ⓑⓒ ×4 (레인 기록 «후» — §4 순서) ──────────────────────────
    preds_b, npar_b = run_arm("b")
    preds_c, npar_c = run_arm("c")
    pp_b = {s: SE.pinball_cells(preds_b[s].astype(np.float64), Rva) for s in SE.SEEDS}
    pp_c = {s: SE.pinball_cells(preds_c[s].astype(np.float64), Rva) for s in SE.SEEDS}
    cov_b = {s: SE.coverage_pairs(preds_b[s].astype(np.float64), Rva) for s in SE.SEEDS}
    cov_c = {s: SE.coverage_pairs(preds_c[s].astype(np.float64), Rva) for s in SE.SEEDS}

    # ── 6. 판·게이트 (§3·§5) ─────────────────────────────────────────
    pp_b_bar = np.mean([pp_b[s] for s in SE.SEEDS], axis=0)
    pp_c_bar = np.mean([pp_c[s] for s in SE.SEEDS], axis=0)
    d_main = pp_b_bar - pp_c_bar                      # + = ⓒ 개선
    delta_main = float(d_main.mean())
    se_cl = SE.cluster_boot_se(d_main, clusters, 10000, 1022)
    d_seed = [float((pp_b[s] - pp_c[s]).mean()) for s in SE.SEEDS]
    j_meas = float(np.std(d_seed, ddof=1) / np.sqrt(len(SE.SEEDS)))
    mde_meas = 2.0 * max(se_cl, j_meas)
    gate_main = delta_main > mde_meas

    cov_b_bar = np.mean([cov_b[s] for s in SE.SEEDS], axis=0)
    cov_c_bar = np.mean([cov_c[s] for s in SE.SEEDS], axis=0)
    d_cov = cov_c_bar - cov_b_bar
    delta_cov = float(d_cov.mean())
    se_cl_cov = SE.cluster_boot_se(d_cov, clusters, 10000, 1022)
    j_cov = float(np.std([float((cov_c[s] - cov_b[s]).mean()) for s in SE.SEEDS],
                         ddof=1) / np.sqrt(len(SE.SEEDS)))
    mde_cov = 2.0 * max(se_cl_cov, j_cov)
    gate_cov = delta_cov >= -mde_cov

    d_ca = pp_a_bar - pp_c_bar
    d_ba = pp_a_bar - pp_b_bar
    se_ca = SE.cluster_boot_se(d_ca, clusters, 10000, 1022)
    se_ba = SE.cluster_boot_se(d_ba, clusters, 10000, 1022)

    # 자료 탐침(v5.3-3) ㉰㉱
    probe_r = probe_s = 0
    if mde_meas > 0:
        if (-2 * mde_meas) > mde_meas:
            probe_r += 1
        if not ((+2 * mde_meas) > mde_meas):
            probe_s += 1
    if mde_cov > 0:
        if (-2 * mde_cov) >= -mde_cov:
            probe_r += 1
        if not ((+2 * mde_cov) >= -mde_cov):
            probe_s += 1
    degenerate = (mde_meas <= 0) or (mde_cov <= 0)

    # 도메인 관찰·q50·앵커
    dom_of = feat["C"][va][:, :len(SE.DOMS)].argmax(1)
    dom_table = {}
    for di, dom in enumerate(SE.DOMS):
        mask = dom_of == di
        if not mask.any():
            continue
        cl = clusters[mask]
        dom_table[dom] = {
            "n쌍": int(mask.sum()), "n개체": int(len(np.unique(cl))),
            "ppⓐ": float(pp_a_bar[mask].mean()), "ppⓑ": float(pp_b_bar[mask].mean()),
            "ppⓒ": float(pp_c_bar[mask].mean()),
            "Δ주(ⓑ−ⓒ)": float(d_main[mask].mean()),
            "SE^cl": SE.cluster_boot_se(d_main[mask], cl, 2000, 1022) if len(np.unique(cl)) > 1 else None}
    q50mae = {arm: float(np.mean([np.abs(P[s][..., 2] - Rva).mean() for s in SE.SEEDS]))
              for arm, P in (("a", preds_a), ("b", preds_b), ("c", preds_c))}
    anchor_ratio = q50mae["a"] / 0.2076
    # 유문서 val 부분집합 관찰
    n_pre_va = np.array([pairs[i][3] for i in va])
    hd = n_pre_va > 0
    sub = {"n쌍(유문서 val)": int(hd.sum()),
           "Δ주(유문서)": float(d_main[hd].mean()) if hd.any() else None,
           "SE^cl(유문서)": SE.cluster_boot_se(d_main[hd], clusters[hd], 2000, 1022) if hd.any() else None,
           "Δ주(무문서)": float(d_main[~hd].mean()) if (~hd).any() else None}

    lane_main = lanes["㉠"]["레인"]
    verdict = ("판정 불가(퇴화 문턱)" if degenerate else
               ("통과 — ⓒ가 ⓑ를 검출 가능하게 이김" if (lane_main == "[판정]" and gate_main and probe_r == 0 and probe_s == 0)
                else ("불통과 — 개선 효과는 MDE %.5f 미만(점추정 %+.5f)" % (mde_meas, delta_main)
                      if lane_main == "[판정]" else "[측정] — 관찰 게재(MDE 미달 강등)")))
    arms_out = {
        "레인": lanes,
        "표본": {"val 쌍": int(len(va)), "val 개체": int(len(np.unique(clusters))),
                 "train 쌍": int((feat["split"] == 0).sum())},
        "파라미터(실측)": {"ⓐ": npar_a, "ⓑ": npar_b, "ⓒ": npar_c, "상한": SE.PARAM_CAP},
        "3팔 판(val · 씨앗 4 평균)": {
            "핀볼": {"ⓐ": float(pp_a_bar.mean()), "ⓑ": float(pp_b_bar.mean()),
                     "ⓒ": float(pp_c_bar.mean())},
            "핀볼(씨앗별)": {"ⓐ": [float(pp_a[s].mean()) for s in SE.SEEDS],
                             "ⓑ": [float(pp_b[s].mean()) for s in SE.SEEDS],
                             "ⓒ": [float(pp_c[s].mean()) for s in SE.SEEDS]},
            "덮개율90": {"ⓐ": float(cov_a_mean(cov_a)), "ⓑ": float(cov_b_bar.mean()),
                         "ⓒ": float(cov_c_bar.mean())},
            "q50MAE": q50mae},
        "주대비 ㉠ (Δ=ppⓑ−ppⓒ · +=ⓒ개선)": {
            "Δ_주": delta_main, "SE^cl(B=10000·시드1022)": se_cl, "J_실측": j_meas,
            "MDE_실측": mde_meas, "여유": delta_main - mde_meas,
            "씨앗별 Δ": d_seed, "게이트": bool(gate_main)},
        "㉢ 덮개율 비악화 (Δ_cov=covⓒ−covⓑ)": {
            "Δ_cov": delta_cov, "SE^cl_cov": se_cl_cov, "J_cov": j_cov,
            "MDE_cov": mde_cov, "여유": delta_cov + mde_cov, "게이트": bool(gate_cov)},
        "㉡ 관찰": {"Δ_ca(ⓐ−ⓒ)": float(d_ca.mean()), "SE^cl": se_ca,
                    "Δ_ba(ⓐ−ⓑ)": float(d_ba.mean()), "SE^cl_ba": se_ba},
        "자료 탐침": {"㉰ 악화 극값 참": probe_r, "㉱ 개선 극값 거짓": probe_s,
                      "퇴화": bool(degenerate)},
        "앵커(관찰)": {"ⓐ q50MAE": q50mae["a"], "배포 0.2076 대비 비율": anchor_ratio,
                       "기대 [0.4, 2.5] 안": bool(0.4 <= anchor_ratio <= 2.5)},
        "도메인 관찰(조항 68 — SE 병기)": dom_table,
        "유문서 부분집합 관찰": sub,
        "판정문(조각)": verdict,
    }
    jdump(os.path.join(OUT, "arms1022.json"), arms_out)

    meta = {"사다리": ladder, "문서 계수": doc_cnt, "leak": {k: v for k, v in stamps.items()},
            "PCA": pca_info, "시대": {**epoch, "패널": panel_shas},
            "끝 시각": dt.datetime.now().isoformat()}
    jdump(os.path.join(OUT, "meta1022.json"), meta)
    log("완료 — 판정문(조각): %s" % verdict)
    log("Δ_주 %+.5f · SE^cl %.5f · J %.5f · MDE %.5f · 여유 %+.5f"
        % (delta_main, se_cl, j_meas, mde_meas, delta_main - mde_meas))
    mark_done("all")


def cov_a_mean(cov_a):
    return np.mean([cov_a[s] for s in SE.SEEDS], axis=0).mean()


if __name__ == "__main__":
    main()
