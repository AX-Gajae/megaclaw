# -*- coding: utf-8 -*-
"""파운데이션 판 — 루프 v5.0/v5.1 의 정본 채점기 v2 (docs/루프.md 제5장 + 5-가 보강 v5.1).

한 방: python3 pretrain/scoreboard.py [--out 경로.json]

넷을 한 판에 «불확실성과 함께» 적는다 (5-가 보강 v5.1 · 티처 #136):
  ① 최약 도메인 MdAPE — 도메인별 붓스트랩 SE · 95%CI · «최약 정체» P(argmax)
  ② pers 에 지는 도메인 수 — 붓스트랩 분포 P(k). 정의는 「도메인 MdAPE «중앙값의 차» > 0」
    (짝지은 개체 차의 중앙값과 부호가 다를 수 있음을 안다 — v5.1 5-가-5 · 동률(=)은 «안 지는» 쪽)
  ③ LODO 제로샷 승수 — 「낡음」은 문자열이 아니라 sha 대조로 판정. LODO 산출물에 sha 가
    아직 없으면 「sha 미기재(재실측 전 낡은 산출물)」 (불일치가 아니다 — 조항 59 의 셋 구별)
  ④ 90% 덮개율 — «직접 재계산» + 개체 군집 SE. report.json 은 «대조»로만 (티처 #136 ②-5)

v2 가 v1 에서 고친 것 (티처 #136 ②-1~②-5 · 5-가 보강 v5.1):
  · 개체별 APE·덮개율을 «직접» 계산한다 — 배포 model.pt 를 998 러너(runners/repair998.py)의
    평가식으로 CPU 평가 (B=10,000 · seed 는 판 JSON 에 기록)
  · 도메인 명부 10 개를 상수로 박는다 (조항 59) — 원천에서 빠진 도메인은 분모를 줄이지 말고
    그 칸을 「못 읽었다」로 찍는다
  · 출처 사슬 (조항 66) — leaderboard/report/LODO 에 «적힌» 모형 sha 를 실물 model.pt 와
    대조하고, 내 평가가 리더보드 칸을 재현하는지(평가 항등) 확인한다.
    어긋나면 판 전체를 「불일치」로 찍고 값을 적지 않는다.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import hashlib
import json
import os
import time

# 🔴 도메인 명부 — 조항 59. 원천이 무엇을 주든 이 10 이름이 분모다.
ROSTER = ("게임", "도서", "만화", "모바일", "세계애니", "시장팝업", "아이돌", "애니", "웹툰", "팝업")
B_BOOT = 10000
BOOT_SEED = 9990          # 판 JSON 에 기록 — 재현용 (학습 씨앗과 무관한 재표집 씨앗)

ART = "/Users/ax/wm_harvest/foundation"
SRC = {
    "리더보드": os.path.join(ART, "transition", "leaderboard.json"),
    "LODO": os.path.join(ART, "exp", "lodo", "results.json"),
    "보고서": os.path.join(ART, "transition", "report.json"),
}
MODEL_PT = os.path.join(ART, "transition", "model.pt")
SAO_NPZ = os.path.join(ART, "triples", "sao.npz")
DOMS_JSON = os.path.join(ART, "triples", "domains.json")


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def _provenance(path):
    if not os.path.exists(path):
        return {"상태": "없음"}
    return {"sha256": _sha16(path),
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path)))}


def _read_json(path):
    if not os.path.exists(path):
        return None
    return json.load(open(path, encoding="utf-8"))


def _direct_eval():
    """배포 model.pt 를 998 러너의 평가식으로 CPU 평가 — 개체별 APE·pers APE·덮개율.

    실패(파일 없음·차원 불일치)면 {"오류": …} 를 돌려준다 — 조항 59 대로 못 읽은 것은 못 읽었다."""
    if not (os.path.exists(MODEL_PT) and os.path.exists(SAO_NPZ) and os.path.exists(DOMS_JSON)):
        missing = [p for p in (MODEL_PT, SAO_NPZ, DOMS_JSON) if not os.path.exists(p)]
        return {"오류": "못 읽었다 — 없음: %s" % missing}
    import numpy as np
    import torch
    from pretrain.transition import Transition
    torch.set_num_threads(4)
    z = np.load(SAO_NPZ)
    domains = json.load(open(DOMS_JSON, encoding="utf-8"))
    S = np.log1p(z["S"].astype(np.float64)).astype(np.float32)
    O = np.log1p(z["O"].astype(np.float64)).astype(np.float32)
    base = S.mean(axis=1, keepdims=True)
    Sc = S - base
    R = O - base
    dom_id = z["dom_id"].astype(np.int64)
    split = z["split"]
    doy = z["doy"].astype(np.float32)
    sin = np.sin(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
    cos = np.cos(2 * np.pi * doy / 365.0)[:, None].astype(np.float32)
    year = ((z["year"].astype(np.float32) - 2013.0) / 10.0)[:, None]
    n_dom = int(dom_id.max()) + 1
    onehot = np.zeros((len(S), n_dom), dtype=np.float32)
    onehot[np.arange(len(S)), dom_id] = 1.0
    cond = [onehot, sin, cos, year, base.astype(np.float32)]
    ck = torch.load(MODEL_PT, map_location="cpu", weights_only=False)
    text_emb = ck.get("text_emb")
    if text_emb:
        if not os.path.exists(text_emb):
            return {"오류": "못 읽었다 — 체크포인트의 text_emb 경로가 없다: %s" % text_emb}
        E = np.load(text_emb)["E"].astype(np.float32)
        if len(E) != len(S):
            return {"오류": "불일치 — 텍스트 임베딩 행 수 %d ≠ sao %d" % (len(E), len(S))}
        cond.append(E)
    C = np.concatenate(cond, axis=1).astype(np.float32)
    if Sc.shape[1] + C.shape[1] != ck["d_in"]:
        return {"오류": "불일치 — 조건 차원 %d ≠ 체크포인트 d_in %d"
                       % (Sc.shape[1] + C.shape[1], ck["d_in"])}
    model = Transition(ck["d_in"], hidden=ck["hidden"])
    model.load_state_dict(ck["model"])
    model.eval()
    va = np.where(split == 1)[0]
    with torch.no_grad():
        xe = torch.from_numpy(np.concatenate([Sc[va], C[va]], axis=1))
        pred = model(xe).numpy()                          # (n,91,5) 잔차 눈금
    b = base[va]
    cum_true = np.expm1(R[va] + b).sum(axis=1)
    cum_q50 = np.expm1(pred[..., 2] + b).sum(axis=1)
    cum_pers = np.expm1(0 * R[va] + b).sum(axis=1)
    ape_tr = np.abs(cum_q50 - cum_true) / np.maximum(cum_true, 1.0)
    ape_pers = np.abs(cum_pers - cum_true) / np.maximum(cum_true, 1.0)
    cover_ent = ((R[va] >= pred[..., 0]) & (R[va] <= pred[..., 4])).mean(axis=1)
    return {"domains": domains, "dom_va": dom_id[va], "ape_tr": ape_tr,
            "ape_pers": ape_pers, "cover_ent": cover_ent,
            "text_emb": text_emb, "n_va": int(len(va))}


def build():
    판 = {"판": "파운데이션 판 v2 (루프 v5.0 제5장 + 5-가 보강 v5.1 · 티처 #136)",
          "잰 시각": time.strftime("%Y-%m-%dT%H:%M:%S"),
          "도메인 명부(상수 · 조항 59)": list(ROSTER),
          "원천": {k: _provenance(p) for k, p in SRC.items()},
          "실물": {"model.pt": _provenance(MODEL_PT), "sao.npz": _provenance(SAO_NPZ)},
          "붓스트랩": {"B": B_BOOT, "seed": BOOT_SEED,
                    "방식": "①② 도메인별 독립 개체 재표집 · ④ 개체 군집(개체 덮개율 평균) — "
                          "개체별 값은 배포 model.pt 를 998 러너 평가식으로 CPU 직접 평가"}}
    lb = _read_json(SRC["리더보드"])
    rep = _read_json(SRC["보고서"])
    lodo = _read_json(SRC["LODO"])
    ev = _direct_eval()

    # ── 출처 사슬 (조항 66 · v5.1 5-가-2) ────────────────────────────
    사슬 = {}
    실물_model = _sha16(MODEL_PT) if os.path.exists(MODEL_PT) else None
    실물_sao = _sha16(SAO_NPZ) if os.path.exists(SAO_NPZ) else None
    미기재, 어긋남 = [], []

    def _대조(이름, 기재, key, 실물값):
        if not isinstance(기재, dict) or key not in 기재:
            미기재.append("%s:%s" % (이름, key))
            return "sha 미기재(재실측 전 낡은 산출물)"
        if 실물값 is None:
            어긋남.append("%s:%s — 실물이 없다" % (이름, key))
            return "불일치 — 실물이 없다"
        if 기재[key] != 실물값:
            어긋남.append("%s:%s 기재 %s ≠ 실물 %s" % (이름, key, 기재[key], 실물값))
            return "불일치(기재 %s ≠ 실물 %s)" % (기재[key], 실물값)
        return "일치"
    lb_src = (lb or {}).get("잰 소스 (조항 66)")
    rep_src = (rep or {}).get("잰 소스 (조항 66)")
    lodo_src = (lodo or {}).get("잰 소스 (조항 66)")
    사슬["리더보드→model.pt"] = _대조("리더보드", lb_src, "model.pt", 실물_model)
    사슬["리더보드→sao.npz"] = _대조("리더보드", lb_src, "sao.npz", 실물_sao)
    사슬["보고서→model.pt"] = _대조("보고서", rep_src, "model.pt", 실물_model)
    사슬["보고서→sao.npz"] = _대조("보고서", rep_src, "sao.npz", 실물_sao)
    사슬["LODO→sao.npz"] = _대조("LODO", lodo_src, "sao.npz", 실물_sao)
    # ③ 의 「낡음」— LODO 가 주행 당시의 배포 model.pt sha 를 «시대 표지»로 남겼으면 그것으로 판정
    if isinstance(lodo_src, dict) and "배포 model.pt(시대 표지)" in lodo_src:
        사슬["LODO 시대 표지"] = ("일치(현 배포와 같은 시대)"
                             if lodo_src["배포 model.pt(시대 표지)"] == 실물_model
                             else "낡음 — LODO 주행 뒤 model.pt 가 바뀌었다")
    else:
        사슬["LODO 시대 표지"] = "sha 미기재(재실측 전 낡은 산출물)"

    # 평가 항등 — 내 직접 평가가 리더보드 칸을 재현하나 (조항 66 — P0e 형)
    항등_어긋남 = {}
    if lb and "오류" not in ev:
        import numpy as np
        doms = ev["domains"]
        for d in ROSTER:
            if d not in lb.get("도메인별", {}):
                continue
            if d not in doms:
                continue
            di = doms.index(d)
            m = ev["dom_va"] == di
            내값_tr = round(float(np.median(ev["ape_tr"][m])), 4)
            내값_pe = round(float(np.median(ev["ape_pers"][m])), 4)
            for col, 내값 in (("transition", 내값_tr), ("persistence", 내값_pe)):
                lb값 = lb["도메인별"][d].get(col)
                if lb값 is None or abs(내값 - lb값) > 1e-4:
                    항등_어긋남["%s/%s" % (d, col)] = {"내 평가": 내값, "리더보드": lb값}
        사슬["평가 항등(리더보드 20칸)"] = ("일치" if not 항등_어긋남
                                     else {"어긋남": 항등_어긋남})
        if 항등_어긋남:
            어긋남.append("평가 항등 %d칸" % len(항등_어긋남))
    elif "오류" in ev:
        사슬["평가 항등(리더보드 20칸)"] = ev["오류"]
    불일치 = bool(어긋남)
    사슬["판정"] = ("🔴 불일치 — 값 안 적음(조항 66): %s" % "; ".join(어긋남) if 불일치
                  else ("일치 (sha 미기재 원천: %s)" % ", ".join(미기재) if 미기재 else "일치(전부)"))
    판["출처 사슬 (조항 66)"] = 사슬

    if 불일치:
        for k in ("①최약 도메인", "②pers에 지는 도메인", "③LODO 제로샷", "④90% 덮개율"):
            판[k] = "🔴 불일치 — 값 안 적음 (출처 사슬을 먼저 고쳐라)"
        return 판

    # ── 붓스트랩 밑작업 (①②④ 공용 · 도메인별 독립 개체 재표집) ─────
    boot = None
    if "오류" not in ev:
        import numpy as np
        rng = np.random.default_rng(BOOT_SEED)
        doms = ev["domains"]
        tr_med, pers_med, dom_cells = {}, {}, {}
        for d in ROSTER:
            if d not in doms:
                continue
            m = ev["dom_va"] == doms.index(d)
            n_d = int(m.sum())
            if n_d == 0:
                continue
            a_tr, a_pe = ev["ape_tr"][m], ev["ape_pers"][m]
            idx = rng.integers(0, n_d, size=(B_BOOT, n_d))
            tr_med[d] = np.median(a_tr[idx], axis=1)
            pers_med[d] = np.median(a_pe[idx], axis=1)
            dom_cells[d] = {"n_val": n_d,
                            "MdAPE": round(float(np.median(a_tr)), 4),
                            "SE": round(float(tr_med[d].std(ddof=1)), 4),
                            "CI95": [round(float(np.percentile(tr_med[d], 2.5)), 4),
                                     round(float(np.percentile(tr_med[d], 97.5)), 4)]}
        boot = {"tr_med": tr_med, "pers_med": pers_med, "cells": dom_cells, "np": np}

    # ── ①② 리더보드 (없거나 빠진 칸은 「못 읽었다」 · 분모 10 불변) ──
    if lb and boot:
        np = boot["np"]
        dom = lb["도메인별"]
        있는 = [d for d in ROSTER if d in dom]
        없는 = [d for d in ROSTER if d not in dom]
        명부밖 = sorted(set(dom) - set(ROSTER))
        worst = max(있는, key=lambda d: dom[d]["transition"])
        # 최약 정체 P(argmax) — 도메인별 독립 재표집의 결합
        측정 = [d for d in 있는 if d in boot["tr_med"]]
        스택 = np.stack([boot["tr_med"][d] for d in 측정])        # (n도메인, B)
        amax = np.argmax(스택, axis=0)
        p_argmax = {측정[i]: round(float((amax == i).mean()), 3)
                    for i in range(len(측정)) if (amax == i).any()}
        판["①최약 도메인"] = {
            "도메인": worst,
            "MdAPE": dom[worst]["transition"], "n_val": dom[worst]["n_val"],
            "SE": boot["cells"][worst]["SE"], "CI95": boot["cells"][worst]["CI95"],
            "P(argmax·최약 정체)": dict(sorted(p_argmax.items(), key=lambda kv: -kv[1])),
            "도메인별": {d: dict(boot["cells"].get(d, {"개체값": "못 읽었다"}),
                             리더보드=dom[d]["transition"])
                     for d in sorted(있는, key=lambda d: -dom[d]["transition"])},
            "못 읽었다": 없는 if 없는 else "없음(10/10)"}
        if 명부밖:
            판["①최약 도메인"]["명부 밖 도메인(조항 59 — 계수 안 함)"] = 명부밖
        지는 = sorted([d for d in 있는 if dom[d]["transition"] > dom[d]["persistence"]],
                    key=lambda d: dom[d]["transition"] - dom[d]["persistence"], reverse=True)
        # ② 붓스트랩 분포 — 같은 재표집에서 «중앙값의 차 > 0» 인 도메인 수
        cnt = np.zeros(B_BOOT, dtype=np.int64)
        for d in 측정:
            cnt += (boot["tr_med"][d] > boot["pers_med"][d]).astype(np.int64)
        분포 = {int(k): round(float((cnt == k).mean()), 3) for k in np.unique(cnt)}
        판["②pers에 지는 도메인"] = {
            "수": "%d/%d" % (len(지는), len(ROSTER)), "목록": 지는,
            "정의": "도메인 MdAPE 중앙값의 차 > 0 (동률은 «안 지는» 쪽 · v5.1 5-가-5)",
            "붓스트랩 분포 P(k)": 분포,
            "P(현행 수)": 분포.get(len(지는), 0.0),
            "못 읽었다": 없는 if 없는 else "없음(10/10)"}
    else:
        사유 = ("리더보드 없음 (pretrain/council.py build)" if not lb
                else "직접 평가 실패: %s" % ev.get("오류"))
        판["①최약 도메인"] = 판["②pers에 지는 도메인"] = "못 읽었다 — " + 사유

    # ── ③ LODO 제로샷 ────────────────────────────────────────────────
    if lodo and "도메인별" in lodo:
        lo = lodo["도메인별"]
        있는 = [d for d in ROSTER if d in lo]
        없는 = [d for d in ROSTER if d not in lo]
        이김 = sorted([d for d in 있는 if lo[d]["B_zeroshot"] < lo[d]["persistence"]])
        짐 = sorted(set(있는) - set(이김))
        판["③LODO 제로샷"] = {"승수": "%d/%d" % (len(이김), len(ROSTER)),
                           "이기는 곳": 이김, "지는 곳": 짐,
                           "못 읽었다": 없는 if 없는 else "없음(10/10)",
                           "신선도(sha 대조)": 사슬["LODO 시대 표지"]}
    else:
        판["③LODO 제로샷"] = "못 읽었다 — exp/lodo/results.json 없음"

    # ── ④ 90% 덮개율 — 직접 재계산 + 개체 군집 SE (report 는 대조) ──
    if boot:
        np = boot["np"]
        cov = ev["cover_ent"]
        점 = round(float(cov.mean()), 4)
        rng2 = np.random.default_rng(BOOT_SEED + 1)
        idx = rng2.integers(0, len(cov), size=(B_BOOT, len(cov)))
        cov_b = cov[idx].mean(axis=1)
        rep대조 = "못 읽었다 — report.json 없음"
        if rep:
            평가 = rep.get("평가", rep)
            rep값 = next((v for k, v in 평가.items() if "덮개" in k or "coverage" in k.lower()), None)
            rep대조 = ("일치(%s)" % rep값 if rep값 is not None and abs(rep값 - 점) <= 1e-4
                     else "어긋남 — report %s vs 직접 %s" % (rep값, 점))
        판["④90% 덮개율"] = {"직접 재계산": 점, "n(개체)": int(len(cov)),
                          "개체 군집 SE": round(float(cov_b.std(ddof=1)), 4),
                          "CI95": [round(float(np.percentile(cov_b, 2.5)), 4),
                                   round(float(np.percentile(cov_b, 97.5)), 4)],
                          "report.json 대조": rep대조}
    else:
        판["④90% 덮개율"] = "못 읽었다 — 직접 평가 실패: %s" % ev.get("오류")
    return 판


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="판 JSON 저장 경로 (사이클 산출물로 커밋할 것)")
    a = ap.parse_args()
    판 = build()
    s = json.dumps(판, ensure_ascii=False, indent=1)
    print(s)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(s + "\n")


if __name__ == "__main__":
    main()
