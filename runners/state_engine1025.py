# -*- coding: utf-8 -*-
"""러너 1025 — 상태 엔진 «재시험»(합류 확충 후 · 사전등록 docs/탐색/1025.md · 커밋 2c3126741).

1022 러너 복제·수정 — 순서를 «기계로» 강제한다(§4): 방향 탐침 → 시대 관문 → 문서층 재구성
(색인 항등) → 격자 동결·사다리 → leak 전수 → 임베딩(체크포인트) → 특징 → ⓐ×4 →
위약·assert_mde(레인 기록 ×3) → ⓑⓒ×4 → 판·게이트 → 산출물.
문서층만 1024 순 색인으로 교체 · 격자·팔·자 = 1022 항등(state_engine 임포트 — 무수정).
CPU 전용(임베딩 torch 6 · 학습 4) · load1>10 이면 60초 재잼 반복 · 국면 체크포인트(재개).

씀: python3 runners/state_engine1025.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
_os.environ.setdefault("OMP_NUM_THREADS", "6")
_os.environ.setdefault("MKL_NUM_THREADS", "6")
import bisect
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

# ── 사전 고정 상수 (사전등록 §1·§2 — 커밋 2c3126741 과 일치해야 한다) ──────────
OUT = os.path.join(SE.FND, "state_engine", "v1")
ED = os.path.join(SE.FND, "entity_docs")
LOG = os.path.join(OUT, "run1025.out")
STATE = os.path.join(OUT, "phase_state1025.json")

SEEDS = [20, 21, 22, 23]            # 🔴 새 씨앗 집합(1022 의 0~3 금지 · 판 0~11 무교차)
BOOT_SEED = 1025                    # 🔴 새 통계 스트림 — 주대비·관찰 B=10,000
PLACEBO_SEED = 7025                 # 위약 B=2,000
SUB_SEED = 1025                     # 도메인·층별 B=2,000
K_DISC = 256                        # §1-3 벡터 소비 상한(양팔 공통)
QUAR_EXPECT = {"fineweb|T2", "fineweb|T3", "fresh|T3", "sao|T3"}
FRESH_DIFF_MAX = 2

SHA_PAIRS_1022 = "608e06c22cf6b20e"
SHA_ENT_PUB = "fa876576823010c4"
SHA_DOCS = {"docs_fresh.jsonl.gz": "9a3eaed319affa96",
            "docs_sao.jsonl.gz": "f5c2d974bda58699",
            "docs_fineweb.jsonl.gz": "0c716d206f2db191"}
SHA_FP_GATE = "5bb0d66c8dbd27a3"
SHA_REPORT = "6dfb0a4ff2935de0"
ANCHOR_A_1022 = 0.091745            # arms1022.json a7b571b5d0a1f377 (§3 앵커 ①)
ANCHOR_Q50_DEPLOY = 0.2076          # report.json (§3 앵커 ② — 1022 항등)
RULER_A = 0.07242                   # 자 A 판 핀볼(1020 표 · sha 9d424ee035e07154) — 의미 문턱
VAL_DATED_EXPECT = 3220             # 1024 §9-4 — 불일치 = 중단
FROZEN_EXPECT = 179196
QWEN_SNAP = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
             "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
EMB_PART = 20480


def log(msg):
    line = "%s %s" % (dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), msg)
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_gate():
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


def iso_ord(s):
    return dt.date(int(s[:4]), int(s[5:7]), int(s[8:10])).toordinal()


# ── s_disc 상한 창 — 직접식·누적합 (사전등록 §1-3 · 자기시험 §8) ─────────────
def w_full_cum(pa, tau=SE.TAU):
    """전 접두사 W 누적합 재료 — u_j = 2^((pub_j − ref)/τ) · ref = 마지막 pub."""
    ref = pa[-1]
    u = np.exp2((pa - ref) / tau)
    return ref, np.cumsum(u)


def w_full_at(ref, cu, pa_len, k, t, tau=SE.TAU):
    if k <= 0:
        return 0.0
    return float(np.exp2((ref - t) / tau) * cu[k - 1])


def sdisc_selftest():
    """§4-1 s_disc 상한 창 자기시험 3 — 어긋나면 측정 없이 중단."""
    rng = np.random.default_rng(1025)
    pa = np.sort(rng.integers(730000, 733000, size=40)).astype(np.float64)
    emb = rng.normal(size=(40, 8))
    t = 733100.0
    out = []
    # ① n≤K 직접식 항등 (K=64 ≥ n=40)
    w = np.exp2((pa - t) / SE.TAU)
    direct = (w[:, None] * emb).sum(0) / w.sum()
    lo = max(0, 40 - 64)
    ww = np.exp2((pa[lo:] - t) / SE.TAU)
    capped = (ww[:, None] * emb[lo:]).sum(0) / ww.sum()
    ok1 = bool(np.abs(direct - capped).max() < 1e-12)
    out.append({"이름": "① n≤K 직접식 항등", "기대대로": ok1})
    # ② n>K 최고령 배제 (K=8 — 창이 최근 8건만)
    lo = 40 - 8
    ww = np.exp2((pa[lo:] - t) / SE.TAU)
    capped8 = (ww[:, None] * emb[lo:]).sum(0) / ww.sum()
    only_old = (w[:lo, None] * emb[:lo]).sum(0) / w[:lo].sum()
    ok2 = bool(np.abs(capped8 - direct).max() > 0.0 and
               np.abs(capped8 - only_old).max() > np.abs(capped8 - direct).max())
    out.append({"이름": "② n>K 최고령 배제(창≠전체·창이 최근 쪽)", "기대대로": ok2})
    # ③ W 누적합 = 직접 합 (상대 오차 <1e-9) + 정렬 불변식(창 안 최신 = 접두사 최신)
    ref, cu = w_full_cum(pa)
    k = 25
    wd = float(np.exp2((pa[:k] - t) / SE.TAU).sum())
    wc = w_full_at(ref, cu, len(pa), k, t)
    ok3 = bool(abs(wd - wc) / wd < 1e-9 and pa[max(0, k - 8):k].max() == pa[:k].max())
    out.append({"이름": "③ W 누적합 항등·정렬 불변식", "기대대로": ok3})
    return {"경우": out, "전부_기대대로": bool(ok1 and ok2 and ok3)}


# ── 국면 1: 문서층 재구성 (§1-2 — 1024 순 규칙 항등 미러) ─────────────────
def build_doclayer(quar):
    """docs_* → 개체별 [(pub_ord, pub_iso, dk, text_sha16, tier, B)] + head280 사전 + 계수.

    티처 #145 ⑥ ⓒ 이행(§7-보): tier·검사B 를 부착 단위로 보존 — «질» 층화 관찰용.
    """
    ent_docs = {}
    heads = {}
    seen = set()
    cnt = {"행": 0, "중복(원천|doc)": 0, "비엔진/발행일무효": 0, "차이일 위반": 0,
           "카탈로그 제외": 0, "격리 티어 부착 제외": 0, "부착 채택": 0}
    for fn in ("docs_fresh.jsonl.gz", "docs_sao.jsonl.gz", "docs_fineweb.jsonl.gz"):
        src = fn.split("_")[1].split(".")[0]
        with gzip.open(os.path.join(ED, fn), "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                cnt["행"] += 1
                dk = r["원천"] + "|" + r["doc"]
                if dk in seen:
                    cnt["중복(원천|doc)"] += 1
                    continue
                seen.add(dk)
                if r.get("층") != "엔진" or not r.get("published_at"):
                    cnt["비엔진/발행일무효"] += 1
                    continue
                diff = r.get("차이일")
                lim = FRESH_DIFF_MAX if src == "fresh" else 0
                if diff is not None and diff > lim:
                    cnt["차이일 위반"] += 1
                    continue
                if r.get("catalog"):
                    cnt["카탈로그 제외"] += 1
                    continue
                pub = r["published_at"]
                ts = r["text_sha16"]
                kept = False
                for a in r["부착"]:
                    if ("%s|T%d" % (src, a[1])) in quar:
                        cnt["격리 티어 부착 제외"] += 1
                        continue
                    ent_docs.setdefault(a[0], []).append((iso_ord(pub), pub, dk, ts, int(a[1]), int(a[3])))
                    cnt["부착 채택"] += 1
                    kept = True
                if kept and ts not in heads:
                    heads[ts] = r.get("head280", "")
    for e in ent_docs:
        ent_docs[e].sort(key=lambda x: (x[0], x[2]))
    return ent_docs, heads, cnt


def identity_gate(ent_docs):
    """색인 항등 관문(경성) — 재구성 dates 다중집합 == entity_pub_dates 전 개체."""
    n_ent = n_att = mism = 0
    extra = set(ent_docs.keys())
    with gzip.open(os.path.join(ED, "entity_pub_dates.jsonl.gz"), "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            n_ent += 1
            n_att += r["n"]
            mine = sorted(x[1] for x in ent_docs.get(r["키"], []))
            if mine != sorted(r["dates"]):
                mism += 1
                if mism <= 3:
                    log("🔴 색인 불일치 개체(계수만): n_mine=%d n_idx=%d" % (len(mine), r["n"]))
            extra.discard(r["키"])
    return {"색인 개체": n_ent, "색인 부착": n_att, "불일치 개체": mism,
            "재구성에만 있는 개체": len(extra)}


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "ckpt"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "emb_parts"), exist_ok=True)
    log("=== 1025 러너 시작 · pid %d ===" % os.getpid())

    # ── 0. 방향 탐침(v5.3-2) + 자기시험 — 어긋나면 측정 없이 중단 ──────────
    t = 0.7
    g_main = lambda d, th: d > th
    g_cov = lambda d, th: d >= -th
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
    sd_self = sdisc_selftest()
    probes["s_disc 상한 창 자기시험 3"] = bool(sd_self["전부_기대대로"])
    import subprocess
    r = subprocess.run([_sys.executable, os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "pretrain", "mde_guard.py")], capture_output=True)
    probes["mde_guard 자기시험"] = (r.returncode == 0)
    jdump(os.path.join(OUT, "probes1025.json"),
          {"방향 탐침": probes, "leak": ls, "s_disc": sd_self})
    if not all(probes.values()):
        log("🔴 방향 탐침 어긋남 — 측정 없이 중단: %s" % probes)
        raise SystemExit(1)
    log("방향 탐침 %d/%d 기대대로" % (sum(probes.values()), len(probes)))

    # ── 1. 시대 관문(§8) ─────────────────────────────────────────────
    epoch = {}
    fails = []
    for fn, want in [("pairs_index.jsonl.gz", SHA_PAIRS_1022)]:
        got = SE.sha16(os.path.join(SE.FND, "state_engine", fn))
        epoch["1022 " + fn] = got
        if got != want:
            fails.append(fn)
    for fn, want in list(SHA_DOCS.items()) + [("entity_pub_dates.jsonl.gz", SHA_ENT_PUB),
                                              ("fp_gate1024.json", SHA_FP_GATE)]:
        got = SE.sha16(os.path.join(ED, fn))
        epoch[fn] = got
        if got != want:
            fails.append(fn)
    ep = assert_epoch(SHA_REPORT, path=SE.REPORT_PATH)
    epoch["report.json(assert_epoch 실측)"] = ep
    epoch["Qwen 스냅숏 존재"] = os.path.isdir(QWEN_SNAP)
    if fails or not epoch["Qwen 스냅숏 존재"]:
        log("🔴 시대 불일치 %s — 측정 없이 중단" % fails)
        raise SystemExit(1)
    quar = set(json.load(open(os.path.join(ED, "fp_gate1024.json")))["격리"])
    if quar != QUAR_EXPECT:
        log("🔴 격리층 불일치 %s ≠ %s — 중단" % (quar, QUAR_EXPECT))
        raise SystemExit(1)
    log("시대 관문 통과(격리층 4 일치): %s" % json.dumps(
        {k: v for k, v in epoch.items() if k != "report.json(assert_epoch 실측)"},
        ensure_ascii=False)[:400])

    # ── 2. 문서층 재구성 + 색인 항등(경성) ─────────────────────────────
    load_gate()
    dl_path = os.path.join(OUT, "doclayer1025.jsonl.gz")
    cnt_path = os.path.join(OUT, "doclayer_counts1025.json")
    log("문서층 재구성 시작(fresh→sao→fineweb · 원천|doc 접힘)")
    ent_docs, heads, doc_cnt = build_doclayer(quar)
    ident = identity_gate(ent_docs)
    doc_cnt["재구성 개체"] = len(ent_docs)
    log("문서 계수: %s" % json.dumps(doc_cnt, ensure_ascii=False))
    log("색인 항등: %s" % json.dumps(ident, ensure_ascii=False))
    if ident["불일치 개체"] != 0 or ident["재구성에만 있는 개체"] != 0:
        log("🔴 색인 항등 관문 불통과 — 측정 없이 중단")
        raise SystemExit(1)
    if not phase_done("doclayer"):
        with gzip.open(dl_path, "wt", encoding="utf-8") as f:
            for e in sorted(ent_docs):
                f.write(json.dumps({"개체": e, "문서": [[x[1], x[2], x[3], x[4], x[5]]
                        for x in ent_docs[e]]}, ensure_ascii=False) + "\n")
        jdump(cnt_path, {"계수": doc_cnt, "색인 항등": ident})
        mark_done("doclayer")

    # ── 3. 격자 동결 + 사다리 + 필요 임베딩 집합 (§1-1·1-5) ──────────────
    ents, panel_shas = SE.load_panel()
    meta1022_panel = json.load(open(os.path.join(
        SE.FND, "state_engine", "meta1022.json")))["시대"]["패널"]
    panel_same = all(panel_shas.get(k) == v for k, v in meta1022_panel.items())
    keys_all, pairs_all, ladder_all = SE.build_pairs(ents, ent_docs)
    frozen = {}
    with gzip.open(os.path.join(SE.FND, "state_engine", "pairs_index.jsonl.gz"),
                   "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            frozen[(r["개체"], r["t"])] = r["분할"]
    pairs = []
    found = 0
    split_mism = 0
    for (ei, to, sp, n_pre) in pairs_all:
        k = (keys_all[ei], dt.date.fromordinal(to).isoformat())
        want = frozen.get(k)
        if want is None:
            continue
        found += 1
        if want != ("train" if sp == 0 else "val"):
            split_mism += 1
            continue
        pairs.append((ei, to, sp, n_pre))
    ladder = {"패널 개체": len(keys_all), "재생성 격자 쌍": ladder_all["격자 쌍"],
              "동결 대상": len(frozen), "동결 재현": found, "분할 불일치": split_mism,
              "잉여(패널 성장분 · 미사용)": ladder_all["train"] + ladder_all["val"] - found,
              "roster n": ladder_all["roster n"], "패널 sha 1022 동일": bool(panel_same)}
    tr_n = sum(1 for p in pairs if p[2] == 0)
    va_n = sum(1 for p in pairs if p[2] == 1)
    tr_d = sum(1 for p in pairs if p[2] == 0 and p[3] > 0)
    va_d = sum(1 for p in pairs if p[2] == 1 and p[3] > 0)
    ladder.update({"train": tr_n, "val": va_n,
                   "train 유문서(pre-t≥1)": tr_d, "val 유문서(pre-t≥1)": va_d})
    log("사다리: %s" % json.dumps(ladder, ensure_ascii=False))
    if found != FROZEN_EXPECT or split_mism != 0 or len(pairs) != FROZEN_EXPECT:
        log("🔴 격자 동결 관문 불통과(재현 %d/%d · 분할 불일치 %d) — 중단"
            % (found, FROZEN_EXPECT, split_mism))
        raise SystemExit(1)
    if va_d != VAL_DATED_EXPECT:
        log("🔴 val 유문서 재계 %d ≠ %d(1024 §9-4) — 색인 결합 결함 · 중단"
            % (va_d, VAL_DATED_EXPECT))
        raise SystemExit(1)
    keys = keys_all

    # 필요 임베딩 집합(사용 쌍 K창 합집합) + 상한 계수·버린 가중 몫(발행일만 — §1-3)
    needs_path = os.path.join(OUT, "needs1025.jsonl.gz")
    cap_cnt = {"유문서 쌍": 0, "val 유문서": 0, "상한 도달": 0, "상한 도달 val": 0}
    drop_fr = []
    need = set()
    ent_pa = {}
    for e, dl in ent_docs.items():
        ent_pa[e] = np.array([x[0] for x in dl], dtype=np.float64)
    for (ei, to, sp, n_pre) in pairs:
        if n_pre == 0:
            continue
        cap_cnt["유문서 쌍"] += 1
        if sp == 1:
            cap_cnt["val 유문서"] += 1
        dl = ent_docs[keys[ei]]
        lo = max(0, n_pre - K_DISC)
        for j in range(lo, n_pre):
            need.add(dl[j][3])
        if n_pre > K_DISC:
            cap_cnt["상한 도달"] += 1
            if sp == 1:
                cap_cnt["상한 도달 val"] += 1
            pa = ent_pa[keys[ei]]
            w = np.exp2((pa[:n_pre] - to) / SE.TAU)
            drop_fr.append(float(w[:lo].sum() / w.sum()))
    need = sorted(need)
    fr = np.array(drop_fr) if drop_fr else np.zeros(1)
    cap_stats = {"K_disc": K_DISC, **cap_cnt, "필요 유일 텍스트": len(need),
                 "버린 가중 몫": {"p50": float(np.median(fr)),
                                  "p90": float(np.percentile(fr, 90)),
                                  "p99": float(np.percentile(fr, 99)),
                                  "max": float(fr.max())}}
    log("상한 계수: %s" % json.dumps(cap_stats, ensure_ascii=False))
    if not phase_done("grid"):
        with gzip.open(needs_path, "wt", encoding="utf-8") as f:
            for ts in need:
                f.write(json.dumps({"sha": ts, "head": heads.get(ts, "")},
                                   ensure_ascii=False) + "\n")
        with gzip.open(os.path.join(OUT, "pairs1025.jsonl.gz"), "wt", encoding="utf-8") as f:
            for (ei, to, sp, n_pre) in pairs:
                f.write(json.dumps({"개체": keys[ei],
                                    "t": dt.date.fromordinal(to).isoformat(),
                                    "분할": "train" if sp == 0 else "val",
                                    "n_pre": n_pre}, ensure_ascii=False) + "\n")
        mark_done("grid")
    del heads

    # ── 4. leak_guard 사용 쌍 전수 (§6) ───────────────────────────────
    stamps_path = os.path.join(OUT, "leak_stamps1025.json")
    if not phase_done("leak"):
        load_gate()
        log("leak_guard 전수 검사 시작(쌍 %d)" % len(pairs))
        n_doc = n_curve = 0
        mm_doc = mm_curve = None
        rep = None
        try:
            for (ei, to, sp, n_pre) in pairs:
                k = keys[ei]
                as_of = dt.date.fromordinal(to).isoformat()
                if n_pre > 0:
                    dl = ent_docs[k]
                    lo = max(0, n_pre - K_DISC)
                    rows = [{"id": dl[j][2], "published_at": dl[j][1]}
                            for j in range(lo, n_pre)]
                    st = assert_no_leak(rows, as_of,
                                        tag="1025 문서 ent=%s t=%s" % (k, as_of))
                    n_doc += 1
                    if st["여유일"] is not None and (mm_doc is None or st["여유일"] < mm_doc):
                        mm_doc = st["여유일"]
                    if rep is None:
                        rep = st
                rows = [{"id": "curve|%d" % o,
                         "published_at": dt.date.fromordinal(o).isoformat()}
                        for o in range(to - SE.PRE, to)]
                st = assert_no_leak(rows, as_of, tag="1025 곡선 ent=%s t=%s" % (k, as_of))
                n_curve += 1
                if mm_curve is None or st["여유일"] < mm_curve:
                    mm_curve = st["여유일"]
        except LeakDetected as e:
            log("🔴 LeakDetected — 측정 없이 중단: %s" % e)
            raise SystemExit(1)
        stamps = {"문서 검사 쌍(유문서 · K창)": n_doc, "곡선 검사 쌍": n_curve,
                  "위반": 0, "최소 여유일(문서)": mm_doc, "최소 여유일(곡선)": mm_curve,
                  "대표 스탬프(문서·실측 반환값)": rep}
        jdump(stamps_path, stamps)
        mark_done("leak")
        log("leak 통과: %s" % json.dumps({k: v for k, v in stamps.items()
                                          if k != "대표 스탬프(문서·실측 반환값)"},
                                         ensure_ascii=False))
    stamps = json.load(open(stamps_path))

    # ── 5. 임베딩 (§1-4 — 체크포인트 조각 · 재개 가능 · 자료 준비) ─────────
    emb_path = os.path.join(OUT, "emb1025.f32")
    if not phase_done("embed"):
        needs = []
        with gzip.open(needs_path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                needs.append((r["sha"], r["head"]))
        assert [x[0] for x in needs] == need, "needs 파일·필요 집합 불일치"
        import torch
        from transformers import AutoModel, AutoTokenizer
        torch.set_num_threads(6)
        tok = AutoTokenizer.from_pretrained(QWEN_SNAP, local_files_only=True)
        model = AutoModel.from_pretrained(QWEN_SNAP, local_files_only=True,
                                          torch_dtype=torch.float32)
        model.eval()
        n_parts = (len(needs) + EMB_PART - 1) // EMB_PART
        t_all = time.time()
        for pi in range(n_parts):
            pth = os.path.join(OUT, "emb_parts", "part_%04d.npz" % pi)
            if os.path.exists(pth):
                continue
            load_gate()
            t0 = time.time()
            chunk = needs[pi * EMB_PART:(pi + 1) * EMB_PART]
            E = np.zeros((len(chunk), 896), dtype=np.float32)
            with torch.no_grad():
                for i in range(0, len(chunk), 32):
                    texts = [(c[1] or " ")[:500] for c in chunk[i:i + 32]]
                    enc = tok(texts, padding=True, truncation=True,
                              max_length=96, return_tensors="pt")
                    h = model(**enc).last_hidden_state
                    m = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
                    v = (h * m).sum(dim=1) / m.sum(dim=1).clamp(min=1.0)
                    E[i:i + len(texts)] = v.numpy().astype(np.float32)
            np.savez_compressed(pth + ".tmp.npz", E=E)
            os.replace(pth + ".tmp.npz", pth)
            done_n = min((pi + 1) * EMB_PART, len(needs))
            rate = done_n / max(time.time() - t_all, 1e-9)
            log("임베딩 조각 %d/%d (%d건 · %.1f초 · 누적 %.1f건/초 · 남은 예상 %.1f분)"
                % (pi + 1, n_parts, len(chunk), time.time() - t0, rate,
                   (len(needs) - done_n) / max(rate, 1e-9) / 60))
        mm = np.memmap(emb_path, dtype=np.float32, mode="w+", shape=(len(need), 896))
        for pi in range(n_parts):
            E = np.load(os.path.join(OUT, "emb_parts", "part_%04d.npz" % pi))["E"]
            mm[pi * EMB_PART: pi * EMB_PART + len(E)] = E
        mm.flush()
        del mm
        with gzip.open(os.path.join(OUT, "emb_index1025.jsonl.gz"), "wt",
                       encoding="utf-8") as f:
            for i, ts in enumerate(need):
                f.write(json.dumps({"sha": ts, "row": i}) + "\n")
        jdump(os.path.join(OUT, "emb_config1025.json"),
              {"모형": "Qwen2.5-0.5B(로컬 스냅숏)", "스냅숏": QWEN_SNAP,
               "산식": "last_hidden_state attention-mask 평균 · 최대 96토큰 · 배치 32 · "
                        "float32 · CPU threads 6 (discourse_field.embed_texts 항등)",
               "텍스트": "head280(≤500자 규약 안)", "n": len(need), "dim": 896})
        mark_done("embed")
        log("임베딩 완료 %d건" % len(need))
    row_of = {ts: i for i, ts in enumerate(need)}
    emb = np.fromfile(emb_path, dtype=np.float32).reshape(len(need), 896)

    # ── 6. 특징 (§1·§2 — 1022 미러 + K창 s_disc) ─────────────────────
    load_gate()
    # 문서 튜플 (po, emb_row, iso, dk) — SE.gather_seq/train_arm 형식 항등
    docs = {}
    for e, dl in ent_docs.items():
        docs[e] = [(x[0], row_of.get(x[3], -1), x[1], x[2]) for x in dl]
    feat = SE.build_features(keys, ents, pairs)
    train_mask = feat["split"] == 0
    n = len(pairs)
    dated = [i for i, p in enumerate(pairs) if p[3] > 0]
    # 창 행 유효성(접근 전수 — row ≥ 0) + s_disc·스칼라
    scal = np.zeros((n, 4), dtype=np.float64)
    S = np.zeros((len(dated), 896), dtype=np.float32)
    bad_rows = 0
    cum = {}
    for e in ent_docs:
        pa = ent_pa[e]
        cum[e] = w_full_cum(pa)
    for j, i in enumerate(dated):
        ei, to, sp, n_pre = pairs[i]
        e = keys[ei]
        dl = docs[e]
        lo = max(0, n_pre - K_DISC)
        rows = np.array([d[1] for d in dl[lo:n_pre]], dtype=np.int64)
        if (rows < 0).any():
            bad_rows += 1
            continue
        pa = ent_pa[e]
        w = np.exp2((pa[lo:n_pre] - to) / SE.TAU)
        S[j] = (w[:, None] * emb[rows].astype(np.float64)).sum(0) / w.sum()
        ref, cu = cum[e]
        W_full = w_full_at(ref, cu, len(pa), n_pre, to)
        scal[i] = [1.0, np.log1p(n_pre), np.log1p(W_full), np.log1p(to - pa[n_pre - 1])]
    if bad_rows:
        log("🔴 창 안 미임베딩 행 %d — 측정 없이 중단(조항 59)" % bad_rows)
        raise SystemExit(1)
    tr_dated = [j for j, i in enumerate(dated) if train_mask[i]]
    M = S[np.array(tr_dated)].astype(np.float64)
    mu = M.mean(0)
    covm = (M - mu).T @ (M - mu) / max(len(M) - 1, 1)
    evals, evecs = np.linalg.eigh(covm)
    order = np.argsort(evals)[::-1][:8]
    comp = evecs[:, order]
    expl = float(evals[order].sum() / max(evals.sum(), 1e-12))
    P = np.zeros((n, 8), dtype=np.float64)
    P[np.array(dated)] = (S.astype(np.float64) - mu) @ comp
    F = np.concatenate([scal, P], axis=1)
    trF = F[train_mask]
    m_, s_ = trF.mean(0), trF.std(0, ddof=0)
    s_[s_ < 1e-6] = 1.0
    extra_b = ((F - m_) / s_).astype(np.float32)
    pca_info = {"PCA8 설명분산비": expl, "PCA 적합 쌍(train 유문서)": len(tr_dated),
                "유문서 쌍": len(dated)}
    c_scal_raw = scal[:, :2].copy()
    mm2 = c_scal_raw[train_mask].mean(0)
    ss2 = c_scal_raw[train_mask].std(0)
    ss2[ss2 < 1e-6] = 1.0
    c_scal = ((c_scal_raw - mm2) / ss2)
    for nm, arr in (("Sc", feat["Sc"]), ("C", feat["C"]), ("R", feat["R"]),
                    ("extra_b", extra_b), ("c_scal", c_scal), ("emb", emb)):
        if not np.isfinite(arr).all():
            log("🔴 비유한 특징 %s — 측정 없이 중단(조항 59)" % nm)
            raise SystemExit(1)
    log("특징 완성(전 배열 유한 실측) · PCA: %s" % json.dumps(pca_info, ensure_ascii=False))

    va = np.where(feat["split"] == 1)[0]
    clusters = feat["ent_i"][va]
    seq_ctx = (pairs, keys, docs, emb, c_scal)

    def run_arm(arm):
        preds = {}
        npar = None
        for seed in SEEDS:
            pth = os.path.join(OUT, "pred_%s_s%d.npz" % (arm, seed))
            if os.path.exists(pth):
                z = np.load(pth)
                preds[seed] = z["P"]
                npar = int(z["n_par"])
                continue
            load_gate()
            t0 = time.time()
            P_, n_par, mods = SE.train_arm(arm, seed, feat, extra_b, seq_ctx, threads=4)
            npar = n_par
            preds[seed] = P_
            np.savez_compressed(pth, P=P_, n_par=n_par)
            import torch
            torch.save([md.state_dict() for md in mods],
                       os.path.join(OUT, "ckpt", "%s_s%d.pt" % (arm, seed)))
            log("팔 %s 씨앗 %d 완료 %.1f분 · 파라미터 %d"
                % (arm, seed, (time.time() - t0) / 60, n_par))
        return preds, npar

    # ── 7. ⓐ ×4 (문서 무접촉) ────────────────────────────────────────
    preds_a, npar_a = run_arm("a")
    Rva = feat["R"][va].astype(np.float64)
    pp_a = {s: SE.pinball_cells(preds_a[s].astype(np.float64), Rva) for s in SEEDS}
    cov_a = {s: SE.coverage_pairs(preds_a[s].astype(np.float64), Rva) for s in SEEDS}
    pp_a_bar = np.mean([pp_a[s] for s in SEEDS], axis=0)
    n_pre_va = np.array([pairs[i][3] for i in va])
    hd = n_pre_va > 0

    # ── 8. 위약·MDE «먼저» (§4 · 부칙 6 — 전량·유문서층·cov) ─────────────
    mde_path = os.path.join(OUT, "placebo1025.json")
    lane_path = os.path.join(OUT, "mde_lane1025.json")
    if not phase_done("mde"):
        def placebo_of(mask, cl):
            ds, ses = [], []
            for i in range(len(SEEDS)):
                for j in range(i + 1, len(SEEDS)):
                    d = (pp_a[SEEDS[i]] - pp_a[SEEDS[j]])[mask]
                    ds.append(float(d.mean()))
                    ses.append(SE.cluster_boot_se(d, cl, 2000, PLACEBO_SEED))
            return ds, ses
        full_mask = np.ones(len(va), dtype=bool)
        d_all, se_all = placebo_of(full_mask, clusters)
        d_hd, se_hd = placebo_of(hd, clusters[hd])
        ds_c, ses_c = [], []
        for i in range(len(SEEDS)):
            for j in range(i + 1, len(SEEDS)):
                dc = cov_a[SEEDS[i]] - cov_a[SEEDS[j]]
                ds_c.append(float(dc.mean()))
                ses_c.append(SE.cluster_boot_se(dc, clusters, 2000, PLACEBO_SEED))
        mde_pre = mde_of(max(se_all), float(np.std(d_all, ddof=1)))
        mde_pre_hd = mde_of(max(se_hd), float(np.std(d_hd, ddof=1)))
        mde_pre_cov = mde_of(max(ses_c), float(np.std(ds_c, ddof=1)))
        aim = 0.15 * SE.sd_cl(pp_a_bar, clusters)
        aim_hd = 0.15 * SE.sd_cl(pp_a_bar[hd], clusters[hd])
        placebo = {"Δ_위약 전량(6)": d_all, "SE^cl 전량(B=2000·시드7025)": se_all,
                   "Δ_위약 유문서(6)": d_hd, "SE^cl 유문서": se_hd,
                   "cov Δ_위약": ds_c, "cov SE^cl": ses_c,
                   "MDE_사전 전량": mde_pre, "MDE_사전 유문서": mde_pre_hd,
                   "MDE_cov_사전": mde_pre_cov,
                   "겨냥 ㉠(0.15×SD_cl 전량)": aim, "겨냥 유문서층": aim_hd,
                   "겨냥 ㉢ 악화": 0.05,
                   "유문서 n(실측)": int(hd.sum()),
                   "1024 §9-4 산술 환산 MDE(대조)": 0.000499}
        jdump(mde_path, placebo)
        pl_sha = sha16b(open(mde_path, "rb").read())
        lanes = {"위약 파일 sha": pl_sha}
        for nm, mde_v, aim_v in (("㉠", mde_pre, aim),
                                 ("㉠′ 유문서층(관찰)", mde_pre_hd, aim_hd),
                                 ("㉢", mde_pre_cov, 0.05)):
            try:
                st = assert_mde(mde_v, aim_v, pl_sha)
                lanes[nm] = {"레인": "[판정]" if nm == "㉠" else
                             ("[판정](보조)" if nm == "㉢" else "관찰(검출력 게재)"),
                             "스탬프": st}
            except MdeUnderpowered as e:
                lanes[nm] = {"레인": "[측정] 강등" if nm == "㉠" else "관찰 강등",
                             "사유": str(e)}
        jdump(lane_path, lanes)
        mark_done("mde")
        log("MDE 사전: ㉠ %s (MDE %.6f · 겨냥 %.6f) · 유문서층 MDE %.6f · cov %.6f"
            % (lanes["㉠"]["레인"], mde_pre, aim, mde_pre_hd, mde_pre_cov))
    placebo = json.load(open(mde_path))
    lanes = json.load(open(lane_path))

    # ── 9. ⓑⓒ ×4 (레인 기록 «후») ───────────────────────────────────
    preds_b, npar_b = run_arm("b")
    preds_c, npar_c = run_arm("c")
    pp_b = {s: SE.pinball_cells(preds_b[s].astype(np.float64), Rva) for s in SEEDS}
    pp_c = {s: SE.pinball_cells(preds_c[s].astype(np.float64), Rva) for s in SEEDS}
    cov_b = {s: SE.coverage_pairs(preds_b[s].astype(np.float64), Rva) for s in SEEDS}
    cov_c = {s: SE.coverage_pairs(preds_c[s].astype(np.float64), Rva) for s in SEEDS}

    # ── 10. 판·게이트 (§3·§5) ────────────────────────────────────────
    pp_b_bar = np.mean([pp_b[s] for s in SEEDS], axis=0)
    pp_c_bar = np.mean([pp_c[s] for s in SEEDS], axis=0)
    d_main = pp_b_bar - pp_c_bar
    delta_main = float(d_main.mean())
    se_cl = SE.cluster_boot_se(d_main, clusters, 10000, BOOT_SEED)
    d_seed = [float((pp_b[s] - pp_c[s]).mean()) for s in SEEDS]
    j_meas = float(np.std(d_seed, ddof=1) / np.sqrt(len(SEEDS)))
    mde_meas = 2.0 * max(se_cl, j_meas)
    gate_main = delta_main > mde_meas

    cov_b_bar = np.mean([cov_b[s] for s in SEEDS], axis=0)
    cov_c_bar = np.mean([cov_c[s] for s in SEEDS], axis=0)
    d_cov = cov_c_bar - cov_b_bar
    delta_cov = float(d_cov.mean())
    se_cl_cov = SE.cluster_boot_se(d_cov, clusters, 10000, BOOT_SEED)
    j_cov = float(np.std([float((cov_c[s] - cov_b[s]).mean()) for s in SEEDS],
                         ddof=1) / np.sqrt(len(SEEDS)))
    mde_cov = 2.0 * max(se_cl_cov, j_cov)
    gate_cov = delta_cov >= -mde_cov

    d_ca = pp_a_bar - pp_c_bar
    d_ba = pp_a_bar - pp_b_bar
    se_ca = SE.cluster_boot_se(d_ca, clusters, 10000, BOOT_SEED)
    se_ba = SE.cluster_boot_se(d_ba, clusters, 10000, BOOT_SEED)

    # 자료 탐침(v5.3-3)
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

    # 층별(등록 관찰) — 전량/유문서/무문서 3팔 표 + Δ주 ± SE^cl + 유문서 MDE층
    def stratum(mask, cl_m, label):
        out = {"n쌍": int(mask.sum()), "n개체": int(len(np.unique(cl_m)))}
        if not mask.any():
            return out
        out.update({
            "ppⓐ": float(pp_a_bar[mask].mean()), "ppⓑ": float(pp_b_bar[mask].mean()),
            "ppⓒ": float(pp_c_bar[mask].mean()),
            "covⓐ": float(np.mean([cov_a[s][mask].mean() for s in SEEDS])),
            "covⓑ": float(cov_b_bar[mask].mean()), "covⓒ": float(cov_c_bar[mask].mean()),
            "Δ주(ⓑ−ⓒ)": float(d_main[mask].mean()),
            "SE^cl": SE.cluster_boot_se(d_main[mask], cl_m, 2000, SUB_SEED)
            if len(np.unique(cl_m)) > 1 else None,
            "Δ_ba(ⓐ−ⓑ)": float(d_ba[mask].mean()), "Δ_ca(ⓐ−ⓒ)": float(d_ca[mask].mean())})
        return out
    full_mask = np.ones(len(va), dtype=bool)
    strata = {"전량": stratum(full_mask, clusters, "전량"),
              "유문서": stratum(hd, clusters[hd], "유문서"),
              "무문서": stratum(~hd, clusters[~hd], "무문서")}
    d_seed_hd = [float((pp_b[s] - pp_c[s])[hd].mean()) for s in SEEDS]
    j_hd = float(np.std(d_seed_hd, ddof=1) / np.sqrt(len(SEEDS)))
    se_hd_main = SE.cluster_boot_se(d_main[hd], clusters[hd], 10000, BOOT_SEED)
    mde_hd = 2.0 * max(se_hd_main, j_hd)
    strata["유문서"].update({"SE^cl(B=10000)": se_hd_main, "J층": j_hd,
                             "MDE층": mde_hd, "씨앗별 Δ": d_seed_hd,
                             "여유(관찰)": float(d_main[hd].mean()) - mde_hd})

    # 질 층화(§7-보 ⓒ — 티처 #145 · K창 가중 몫 기준 · 관찰)
    src_lab = np.full(len(va), "", dtype=object)
    tier_lab = np.full(len(va), "", dtype=object)
    sig_lab = np.full(len(va), "", dtype=object)
    for vi, i in enumerate(va):
        ei, to, sp, n_pre = pairs[i]
        if n_pre == 0:
            continue
        dl = ent_docs[keys[ei]]
        lo = max(0, n_pre - K_DISC)
        pa = ent_pa[keys[ei]][lo:n_pre]
        w = np.exp2((pa - to) / SE.TAU)
        W = w.sum()
        shares = {}
        t2 = 0.0
        b0 = 0.0
        for j, x in enumerate(dl[lo:n_pre]):
            src = x[2].split("|", 1)[0]
            shares[src] = shares.get(src, 0.0) + w[j]
            if x[4] == 2:
                t2 += w[j]
            if x[5] == 0:
                b0 += w[j]
        src_lab[vi] = max(sorted(shares), key=lambda k_: shares[k_])
        tier_lab[vi] = "T2우세" if t2 / W > 0.5 else "T1우세"
        sig_lab[vi] = "유신호우세(B0몫≥0.5)" if b0 / W >= 0.5 else "무신호우세"
    qual = {}
    for nm, lab in (("원천 우세", src_lab), ("신뢰 우세", tier_lab), ("유신호 우세", sig_lab)):
        tbl = {}
        for v in sorted({x for x in lab if x}):
            mask = lab == v
            cl = clusters[mask]
            tbl[v] = {"n쌍": int(mask.sum()), "n개체": int(len(np.unique(cl))),
                      "ppⓐ": float(pp_a_bar[mask].mean()),
                      "ppⓑ": float(pp_b_bar[mask].mean()),
                      "ppⓒ": float(pp_c_bar[mask].mean()),
                      "Δ주(ⓑ−ⓒ)": float(d_main[mask].mean()),
                      "SE^cl": SE.cluster_boot_se(d_main[mask], cl, 2000, SUB_SEED)
                      if len(np.unique(cl)) > 1 else None}
        qual[nm] = tbl

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
            "SE^cl": SE.cluster_boot_se(d_main[mask], cl, 2000, SUB_SEED)
            if len(np.unique(cl)) > 1 else None}
    q50mae = {arm: float(np.mean([np.abs(P_[s][..., 2] - Rva).mean() for s in SEEDS]))
              for arm, P_ in (("a", preds_a), ("b", preds_b), ("c", preds_c))}
    anchor1 = abs(float(pp_a_bar.mean()) - ANCHOR_A_1022)
    anchor2 = q50mae["a"] / ANCHOR_Q50_DEPLOY

    rel_A = delta_main / RULER_A * 100.0
    rel_own = delta_main / float(pp_a_bar.mean()) * 100.0
    if rel_A >= 5.0:
        rel_word = "검출 시 「크다」(≥5%)"
    elif rel_A >= 1.0:
        rel_word = "검출 시 「중간」(1~5%)"
    else:
        rel_word = "검출 시 「검출 — 그러나 작음」(<1%)"

    lane_main = lanes["㉠"]["레인"]
    if degenerate:
        verdict = "판정 불가(퇴화 문턱)"
    elif lane_main == "[판정]" and gate_main and probe_r == 0 and probe_s == 0:
        verdict = ("통과 — ⓒ가 ⓑ를 검출 가능하게 이김 · 의미 문턱: 자 A 대비 %+.3f%% (%s)"
                   % (rel_A, rel_word))
    elif lane_main == "[판정]":
        verdict = ("불통과 — 개선 효과는 MDE %.6f 미만(점추정 %+.6f · 자 A 대비 %+.3f%%)"
                   % (mde_meas, delta_main, rel_A))
    else:
        verdict = "[측정] — 관찰 게재(MDE 미달 강등)"

    arms_out = {
        "레인": lanes,
        "표본": {"val 쌍": int(len(va)), "val 개체": int(len(np.unique(clusters))),
                 "train 쌍": int(train_mask.sum()),
                 "val 유문서": int(hd.sum()), "val 무문서": int((~hd).sum())},
        "파라미터(실측)": {"ⓐ": npar_a, "ⓑ": npar_b, "ⓒ": npar_c, "상한": SE.PARAM_CAP},
        "3팔 판(val 전량 · 씨앗 4 평균)": {
            "핀볼": {"ⓐ": float(pp_a_bar.mean()), "ⓑ": float(pp_b_bar.mean()),
                     "ⓒ": float(pp_c_bar.mean())},
            "핀볼(씨앗별)": {"ⓐ": [float(pp_a[s].mean()) for s in SEEDS],
                             "ⓑ": [float(pp_b[s].mean()) for s in SEEDS],
                             "ⓒ": [float(pp_c[s].mean()) for s in SEEDS]},
            "덮개율90": {"ⓐ": float(np.mean([cov_a[s] for s in SEEDS], axis=0).mean()),
                         "ⓑ": float(cov_b_bar.mean()), "ⓒ": float(cov_c_bar.mean())},
            "q50MAE": q50mae},
        "주대비 ㉠ (Δ=ppⓑ−ppⓒ · +=ⓒ개선 · 전량)": {
            "Δ_주": delta_main, "SE^cl(B=10000·시드1025)": se_cl, "J_실측": j_meas,
            "MDE_실측": mde_meas, "여유": delta_main - mde_meas,
            "씨앗별 Δ": d_seed, "게이트": bool(gate_main)},
        "의미 문턱 ㉠′ (자 A 0.07242 · sha 9d424ee035e07154)": {
            "자 A 대비 %": rel_A, "pp̄ⓐ(1025) 대비 %": rel_own, "문언": rel_word},
        "㉢ 덮개율 비악화 (Δ_cov=covⓒ−covⓑ)": {
            "Δ_cov": delta_cov, "SE^cl_cov": se_cl_cov, "J_cov": j_cov,
            "MDE_cov": mde_cov, "여유": delta_cov + mde_cov, "게이트": bool(gate_cov)},
        "㉡ 문서 채널 재검(관찰)": {"Δ_ba(ⓐ−ⓑ)": float(d_ba.mean()), "SE^cl_ba": se_ba,
                                    "Δ_ca(ⓐ−ⓒ)": float(d_ca.mean()), "SE^cl_ca": se_ca},
        "층별(등록 관찰 — 전량/유문서/무문서)": strata,
        "질 층화(§7-보 ⓒ — 티처 #145 · val 유문서 K창 가중 몫 · 관찰)": qual,
        "자료 탐침": {"㉰ 악화 극값 참": probe_r, "㉱ 개선 극값 거짓": probe_s,
                      "퇴화": bool(degenerate)},
        "앵커(관찰)": {"① |ⓐ−1022 0.091745|": anchor1, "기대 ≤0.002": bool(anchor1 <= 0.002),
                       "② ⓐ q50MAE/0.2076": anchor2,
                       "기대 [0.4,2.5] 안": bool(0.4 <= anchor2 <= 2.5)},
        "도메인 관찰(조항 68 — SE 병기)": dom_table,
        "판정문(조각)": verdict,
    }
    jdump(os.path.join(OUT, "arms1025.json"), arms_out)

    meta = {"사다리": ladder, "문서 계수": doc_cnt, "색인 항등": ident,
            "상한 계수(§1-3)": cap_stats, "leak": stamps, "PCA": pca_info,
            "시대": {**{k: v for k, v in epoch.items()}, "패널": panel_shas,
                     "패널 sha 1022 동일": bool(panel_same)},
            "씨앗": SEEDS, "통계 스트림": {"boot": BOOT_SEED, "placebo": PLACEBO_SEED,
                                           "sub": SUB_SEED},
            "끝 시각": dt.datetime.now().isoformat()}
    jdump(os.path.join(OUT, "meta1025.json"), meta)
    log("완료 — 판정문(조각): %s" % verdict)
    log("Δ_주 %+.6f · SE^cl %.6f · J %.6f · MDE %.6f · 여유 %+.6f · 유문서층 Δ %+.6f ± %.6f (MDE층 %.6f)"
        % (delta_main, se_cl, j_meas, mde_meas, delta_main - mde_meas,
           strata["유문서"]["Δ주(ⓑ−ⓒ)"], se_hd_main, mde_hd))
    mark_done("all")


if __name__ == "__main__":
    main()
