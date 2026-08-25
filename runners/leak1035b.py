# -*- coding: utf-8 -*-
"""1035-보 — 사후 보충 측정 + 재빌드 물증 (사전등록 docs/탐색/1035.md §5 ㉣ 의 «보완»).

🔴 정직 신고: 이 러너는 **사전등록에 없다.** `leak1035.py` 를 돌리고 나서, 판 이동
Δ(신판 − 구판)을 «SE 없이» 적을 뻔했다는 것을 알아채고 추가했다(사용자 지시: 「신판 val 이
작아지면 SE 가 커진다 — 좋아졌다/나빠졌다를 SE 없이 적지 마라」). 그러므로 여기 나오는
Δ 의 SE 는 **[관찰]** 이고, 이 사이클의 판정 게이트(G2)는 `leak1035.py` 것 그대로다.
사후에 «더 유리한» 자를 만든 것이 아님을 보이기 위해: 이 SE 는 판정을 **깐깐하게** 만든다.

한 방: python3 runners/leak1035b.py --out runners/out1035_supplement.json
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import collections
import gzip
import hashlib
import json
import os
import time

import numpy as np

ROOT = "/Users/ax/world_model"
SRC = os.path.join(ROOT, "data/ingest/sao973_hplt/pairs.jsonl.gz")
ART = "/Users/ax/wm_harvest/foundation"
SAO_NPZ = os.path.join(ART, "triples", "sao.npz")
REBUILDS = {"버킷 {0} (등록 정본 — 하한 미달로 «미채택»)": "/Users/ax/wm_harvest/foundation_1035b_bucket0",
            "버킷 {0,1} (사전 지정 대체 — «인도»)": "/Users/ax/wm_harvest/foundation_1035"}
SEED_DELTA = [1035, 4]
B_BOOT = 10000
EXP_SAO_SHA = "f120013017dcf512"


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "runners/out1035_supplement.json"))
    a = ap.parse_args()
    out = {"러너": {"경로": os.path.abspath(__file__),
                   "sha256/16": _sha16(os.path.abspath(__file__))},
           "🔴 지위": "사후 보충 — 사전등록에 없다. 산출은 [관찰] 등급.",
           "시작 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # ── 배포 정본 무접촉 증명 (조항 66) ──
    got = _sha16(SAO_NPZ)
    out["배포 정본 무접촉"] = {"sao.npz sha256/16": got, "기대": EXP_SAO_SHA,
                             "일치": got == EXP_SAO_SHA,
                             "뜻": "이 사이클은 배포 triples 를 한 바이트도 안 썼다"}

    # ── 원천 재읽기(같은 순서) → val 누수 표지 ──
    seen, rows = set(), []
    with gzip.open(SRC, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                ax = r["a_액션"]
                k = (ax["개체"], ax["언제"])
                if k in seen:
                    continue
                s, o = r["s_상태"]["값"], r["o_결과"]["값"]
                if len(s) != 90 or len(o) != 91:
                    continue
                seen.add(k)
                rows.append((ax["개체"], ax["문서"]))
            except Exception:
                continue
    z = np.load(SAO_NPZ)
    split = z["split"]
    assert len(rows) == len(split), "행 정렬 깨짐 — 중단"
    tr_docs = {rows[i][1] for i in np.where(split == 0)[0]}
    va = np.where(split == 1)[0]
    va_docs = np.asarray([rows[i][1] for i in va])
    leak = np.asarray([d in tr_docs for d in va_docs])

    from pretrain.scoreboard import _direct_eval
    ev = _direct_eval()
    if "오류" in ev:
        out["판정"] = "🔴 못 읽었다 — %s" % ev["오류"]
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 2
    pin = np.asarray(ev["pinball_row"], dtype=np.float64)
    cov = np.asarray(ev["cover_ent"], dtype=np.float64)

    # ── Δ(신판 − 구판) 과 그 SE — 문서 클러스터 붓스트랩 ──
    # 항등: 신판(무누수) − 구판(전체) = (n_누수/n_전체) × (핀볼̄_무누수 − 핀볼̄_누수)
    uniq = sorted(set(va_docs))
    lut = {n: i for i, n in enumerate(uniq)}
    ids = np.asarray([lut[n] for n in va_docs])
    groups = [np.where(ids == i)[0] for i in range(len(uniq))]
    rng = np.random.default_rng(SEED_DELTA)

    def stat(sel):
        lk = leak[sel]
        if lk.all() or (~lk).all():
            return None
        return float(pin[sel][~lk].mean() - pin[sel].mean())

    obs = stat(np.arange(len(pin)))
    reps, degen = [], 0
    for _ in range(B_BOOT):
        gs = rng.integers(0, len(uniq), size=len(uniq))
        sel = np.concatenate([groups[g] for g in gs])
        v = stat(sel)
        if v is None:
            degen += 1
        else:
            reps.append(v)
    reps = np.asarray(reps)
    se = float(reps.std(ddof=1))
    out["판 이동 Δ(신판 무누수 부분집합 − 구판 전체 val)"] = {
        "Δ(핀볼)": round(obs, 5),
        "문서 클러스터 붓스트랩 SE": round(se, 5),
        "붓스트랩": {"B": B_BOOT, "seed": SEED_DELTA, "퇴화 뽑기": degen,
                    "유효 뽑기": int(len(reps)), "클러스터(val 유일 문서)": len(uniq)},
        "CI95(백분위)": [round(float(np.percentile(reps, 2.5)), 5),
                        round(float(np.percentile(reps, 97.5)), 5)],
        "2×SE(MDE 하한 · J=0)": round(2 * se, 5),
        "|Δ| − 2SE": round(abs(obs) - 2 * se, 5),
        "🔴 이 자를 넘었나": bool(abs(obs) > 2 * se),
        "🔴 읽는 법": "이것은 «중첩된» 두 집합의 비교다(신판 709행 ⊂ 구판 1,129행) — "
                    "판정 게이트가 아니다. 판정은 G2(서로 «겹치지 않는» 누수/무누수 층화 대비)다.",
        "덮개율 이동": {"구판 전체 val": round(float(cov.mean()), 4),
                      "무누수 부분집합": round(float(cov[~leak].mean()), 4),
                      "누수 부분집합": round(float(cov[leak].mean()), 4)}}

    # ── 재빌드 물증 ──
    rb = {}
    for name, d in REBUILDS.items():
        rep = os.path.join(d, "triples", "report.json")
        npz = os.path.join(d, "triples", "sao.npz")
        if not os.path.exists(rep):
            rb[name] = {"상태": "없음 — 못 읽었다(조항 59)"}
            continue
        j = json.load(open(rep, encoding="utf-8"))
        rb[name] = {"sao.npz sha256/16": _sha16(npz),
                    "train": j["train"], "val": j["val(🔴 문서 분리 — 1035)"],
                    "val 유일 문서": j["val 유일 문서"],
                    "G3 비트 동일 cross-split 행": j[
                        "🔴 누수 검사 G3 — val 행 중 train 에 비트 동일 (S,O) 있는 행"],
                    "cross-split 문서 공유 행": j["🔴 누수 검사 — val 행 중 문서가 train 에도 있는 행"],
                    "도메인×val": j["도메인×val"],
                    "val 0 인 도메인": [k for k, v in j["도메인×val"].items() if v == 0]}
    out["재빌드 물증 (G3)"] = rb
    out["§3 val 하한 판정"] = {
        "하한": "val 행 ≥ 500 · val>0 도메인 ≥ 8 · 웹툰 val 행 ≥ 30",
        "버킷 {0}": "🔴 미달 — 웹툰 25(<30) · 시장팝업 0 → 사전 지정 대체 발동",
        "버킷 {0,1}": "통과 — val 1,943 · 10/10 도메인 · 웹툰 330",
        "추가 시도": 0}
    out["끝 시각"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    _sys.exit(main())
