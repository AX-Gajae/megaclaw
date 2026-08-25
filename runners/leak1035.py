# -*- coding: utf-8 -*-
"""1035 — 분할 누수 실측·판정 러너 (사전등록 docs/탐색/1035.md · 커밋 2e72875d4).

한 방: python3 runners/leak1035.py --out runners/out1035_measure.json

하는 것 (사전등록 §5):
  ㉠ 배선 검사 — sao.npz sha · _direct_eval 핀볼 항등 · n=1129 · 도메인 10칸
  ㉡ 누수 실측 — 원천 재읽기 + 행 정렬 «독립» 확인 후 누수 계수
  ㉢ 판정 대비 — 도메인 층화 Δ_str · 문서 클러스터 붓스트랩 SE · 층화 순열 p
  ㉣ 신판(무누수 부분집합) 판 + 공동언급 연결성분 관찰

🔴 배포 정본 디렉터리(/Users/ax/wm_harvest/foundation)에 «쓰지» 않는다 — 읽기만.
🔴 주행 중 이 파일 수정 금지(조항 66) — 자기 sha256 을 산출물에 박는다.
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
BOARD_PREV = os.path.join(ROOT, "data/lab/1029_판_후.json")
ART = "/Users/ax/wm_harvest/foundation"          # 🔴 읽기 전용
SAO_NPZ = os.path.join(ART, "triples", "sao.npz")

# 사전등록 §5 ㉢·㉣ — seed 전부
SEED_CL_SE = [1035, 0]      # 주대비 문서 클러스터 붓스트랩 SE
SEED_PERM = [1035, 1]       # 층화 순열
SEED_BOARD_CL = [1035, 2]   # 신판 판 문서 클러스터 SE
SEED_BOARD_ROW = [1035, 3]  # 신판 판 행 SE
B_BOOT = 10000
B_PERM = 10000

# 사전등록 §5 ㉠ — 기대값(1029_판_후.json 인용)
EXP_SAO_SHA = "f120013017dcf512"
EXP_PINBALL = 0.07242
EXP_N = 1129


def _sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# ── G2 게이트 함수 + 방향 탐침 (측정 «전» · v5.3 2) ──────────────────────
def gate_g2(delta, mde, p):
    """사전등록 §6-가 G2: Δ_str < −MDE 그리고 p < 0.05.
    핀볼은 낮을수록 좋다 → 누수 행이 더 좋으면 Δ = 누수 − 무누수 < 0."""
    return bool(delta < -mde and p < 0.05)


def direction_probe():
    """자료 없이 합성값으로: 개선 극값 참 · 악화 극값 거짓 · 0 거짓."""
    t = 0.01
    rows = [("개선 쪽 극값(Δ=−2t)", gate_g2(-2 * t, t, 0.001), True),
            ("악화 쪽 극값(Δ=+2t)", gate_g2(+2 * t, t, 0.001), False),
            ("Δ=0", gate_g2(0.0, t, 0.001), False),
            ("Δ 충분히 음수인데 p 큼", gate_g2(-2 * t, t, 0.5), False)]
    ok = all(got is want for _, got, want in rows)
    return ok, [{"경우": n, "게이트": got, "기대": want, "일치": got is want}
                for n, got, want in rows]


# ── 원천 재읽기 — triples.py 와 «같은 순서·같은 중복 제거» ──────────────
def read_source():
    seen = set()
    rows = []
    with gzip.open(SRC, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line)
                a = r["a_액션"]
                key = (a["개체"], a["언제"])
                if key in seen:
                    continue
                s = r["s_상태"]["값"]
                o = r["o_결과"]["값"]
                if len(s) != 90 or len(o) != 91:
                    continue
                seen.add(key)
                rows.append({"개체": a["개체"], "언제": a["언제"], "문서": a["문서"],
                             "맞은 제목": a["맞은 제목"], "문서id": a["문서id"],
                             "도메인": r.get("도메인", "?"), "s": s, "o": o})
            except Exception:
                continue
    return rows


def curve_sha(s, o):
    return hashlib.sha256((json.dumps(s) + "|" + json.dumps(o)).encode()).hexdigest()[:16]


# ── 통계 ────────────────────────────────────────────────────────────────
def strat_delta(vals, dom, leak, doms_in=None):
    """Δ_str = Σ_d w_d (핀볼̄(누수,d) − 핀볼̄(무누수,d)) · w_d ∝ min(n_누수, n_무누수).
    양쪽에 행이 있는 도메인만 참여. 참여 도메인이 0 이면 None."""
    parts = []
    for d in (doms_in if doms_in is not None else np.unique(dom)):
        m = dom == d
        a = vals[m & leak]
        b = vals[m & ~leak]
        if len(a) == 0 or len(b) == 0:
            continue
        parts.append((min(len(a), len(b)), a.mean() - b.mean(), d, len(a), len(b)))
    if not parts:
        return None, []
    W = sum(p[0] for p in parts)
    delta = sum(p[0] * p[1] for p in parts) / W
    return float(delta), parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "runners/out1035_measure.json"))
    a = ap.parse_args()
    t0 = time.time()
    out = {"러너": {"경로": os.path.abspath(__file__), "sha256/16": _sha16(os.path.abspath(__file__))},
           "사전등록": "docs/탐색/1035.md · 커밋 2e72875d4",
           "시작 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # ── 방향 탐침 (측정 전) ──
    ok, probe = direction_probe()
    out["방향 탐침(측정 전 · v5.3 2)"] = {"통과": ok, "표": probe}
    if not ok:
        out["판정"] = "🔴 등록 결함 — 방향 탐침 실패 · 측정 없이 중단"
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2

    # ── G0 배선 ──
    g0 = {}
    got_sha = _sha16(SAO_NPZ)
    g0["sao.npz sha256/16"] = {"기대(1029 판)": EXP_SAO_SHA, "실측": got_sha,
                               "일치": got_sha == EXP_SAO_SHA}
    from pretrain.scoreboard import _direct_eval
    ev = _direct_eval()
    if "오류" in ev:
        out["판정"] = "🔴 못 읽었다 — _direct_eval: %s" % ev["오류"]
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return 2
    pin_row = np.asarray(ev["pinball_row"], dtype=np.float64)
    n_va = int(ev["n_va"])
    pin_all = float(pin_row.mean())
    g0["n(행)"] = {"기대": EXP_N, "실측": n_va, "일치": n_va == EXP_N}
    g0["자 A 핀볼(전체 val)"] = {"기대(1029 판)": EXP_PINBALL, "실측": round(pin_all, 5),
                                "일치(소수 5자리)": round(pin_all, 5) == EXP_PINBALL}
    prev = json.load(open(BOARD_PREV, encoding="utf-8"))
    prev_dom = prev["자 A — 구간 점수(핀볼 · 판정 정본 · v6.0 ⓐ)"][
        "도메인별(관찰 — 표적 선정 참고 · 판정은 헤드라인만)"]
    doms = ev["domains"]
    dom_va = np.asarray(ev["dom_va"])
    dom_name_va = np.asarray([doms[i] for i in dom_va])
    dcheck = {}
    for d, cell in prev_dom.items():
        n_got = int((dom_name_va == d).sum())
        p_got = round(float(pin_row[dom_name_va == d].mean()), 5) if n_got else None
        dcheck[d] = {"n행 기대": cell["n행"], "n행 실측": n_got, "n행 일치": n_got == cell["n행"],
                     "핀볼 기대": cell["핀볼 평균"], "핀볼 실측": p_got,
                     "핀볼 일치": p_got == cell["핀볼 평균"]}
    g0["도메인 10칸"] = dcheck
    g0["전 칸 일치"] = bool(g0["sao.npz sha256/16"]["일치"] and g0["n(행)"]["일치"]
                          and g0["자 A 핀볼(전체 val)"]["일치(소수 5자리)"]
                          and all(v["n행 일치"] and v["핀볼 일치"] for v in dcheck.values()))
    out["㉠ 배선 검사 (G0)"] = g0
    if not g0["전 칸 일치"]:
        out["판정"] = "🔴 G0 불일치 — 측정 없이 중단(사전등록 §6-가 G0)"
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2

    # ── 행 정렬 «독립» 확인 (§7 ㉠) ──
    rows = read_source()
    z = np.load(SAO_NPZ)
    Sz, Oz = z["S"], z["O"]
    split = z["split"]
    dom_id_all = z["dom_id"]
    align = {"원천 재읽기 행": len(rows), "npz 행": int(len(Sz)),
             "행 수 일치": len(rows) == len(Sz)}
    if align["행 수 일치"]:
        bad_dom = bad_curve = 0
        for i, r in enumerate(rows):
            if doms[int(dom_id_all[i])] != r["도메인"]:
                bad_dom += 1
            if bad_dom > 5:
                break
        s_ok = np.array_equal(Sz, np.asarray([r["s"] for r in rows], dtype=np.float32))
        o_ok = np.array_equal(Oz, np.asarray([r["o"] for r in rows], dtype=np.float32))
        align.update({"도메인 불일치 행": bad_dom, "S 비트 일치": bool(s_ok),
                      "O 비트 일치": bool(o_ok)})
        align["통과"] = bool(bad_dom == 0 and s_ok and o_ok)
    else:
        align["통과"] = False
    out["행 정렬 «독립» 확인 (§7 ㉠)"] = align
    if not align["통과"]:
        out["판정"] = "🔴 행 정렬 깨짐 — 측정 없이 중단(§7 ㉠)"
        json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return 2

    # ── ㉡ 누수 실측 ──
    va_idx = np.where(split == 1)[0]
    tr_idx = np.where(split == 0)[0]
    docs_all = [r["문서"] for r in rows]
    ents_all = [r["개체"] for r in rows]
    tr_docs = set(docs_all[i] for i in tr_idx)
    va_docs = [docs_all[i] for i in va_idx]
    doc2ents = collections.defaultdict(set)
    for r in rows:
        doc2ents[r["문서"]].add(r["개체"])
    sha_all = [curve_sha(r["s"], r["o"]) for r in rows]
    tr_shas = set(sha_all[i] for i in tr_idx)

    leak_doc = np.asarray([d in tr_docs for d in va_docs])          # 정본
    leak_bit = np.asarray([sha_all[i] in tr_shas for i in va_idx])  # 보조(관찰)

    straddle = sorted(d for d in set(va_docs) if d in tr_docs)
    ent2doc = {r["개체"]: r["문서"] for r in rows}
    ent_bucket_docs = collections.defaultdict(set)
    for e, d in ent2doc.items():
        ent_bucket_docs[d].add(e)
    # 갈린 묶음: 같은 (문서, 언제) 인데 split 이 갈린 묶음
    grp = collections.defaultdict(list)
    for i, r in enumerate(rows):
        grp[(r["문서"], r["언제"])].append(i)
    split_groups = [k for k, v in grp.items() if len({int(split[i]) for i in v}) > 1]
    # 그 묶음들의 곡선 동일성
    same = diff = 0
    for k in split_groups:
        shas = {sha_all[i] for i in grp[k]}
        n = len(grp[k])
        if len(shas) == 1:
            same += n
        else:
            diff += n
    # (문서, 언제) 묶음 중 곡선 2종 이상 (§0 잔여 누수 경로)
    multi_curve = sum(1 for v in grp.values() if len({sha_all[i] for i in v}) > 1)

    meas = {
        "유일 문서": len(set(docs_all)), "유일 개체": len(set(ents_all)),
        "유일 맞은제목": len({r["맞은 제목"] for r in rows}),
        "개체 2개 이상인 문서": sum(1 for v in doc2ents.values() if len(v) >= 2),
        "train/val 걸친 문서": len(straddle),
        "val 행": int(len(va_idx)), "train 행": int(len(tr_idx)),
        "🔴 val 누수 행(정본 · 문서가 train 에 있음)": int(leak_doc.sum()),
        "🔴 val 누수 비율(정본)": round(float(leak_doc.mean()), 4),
        "val 누수 행(보조 · 비트 동일 (S,O) 쌍둥이)": int(leak_bit.sum()),
        "val 누수 비율(보조)": round(float(leak_bit.mean()), 4),
        "갈린 묶음((문서,언제) 에서 split 이 갈림)": len(split_groups),
        "갈린 묶음 안 곡선 비교": {"비트 동일 행": same, "다른 행": diff},
        "🔴 잔여 — (문서,언제) 묶음인데 곡선 2종 이상": multi_curve,
        "도메인별 누수율(정본)": {},
    }
    for d in sorted(set(dom_name_va)):
        m = dom_name_va == d
        meas["도메인별 누수율(정본)"][d] = {
            "n행": int(m.sum()), "누수 행": int(leak_doc[m].sum()),
            "누수율": round(float(leak_doc[m].mean()), 4)}
    out["㉡ 누수 실측"] = meas

    # ── G1 ──
    g1 = {"통과": bool(leak_doc.mean() >= 0.10 and leak_doc.sum() >= 300),
          "비율": round(float(leak_doc.mean()), 4), "행": int(leak_doc.sum()),
          "문턱": "비율 ≥ 0.10 그리고 ≥ 300 행"}
    out["G1 누수 존재"] = g1

    # ── ㉢ 판정 대비 ──
    va_doc_arr = np.asarray(va_docs)
    for label, leak in (("정본(문서)", leak_doc), ("보조(비트 동일 · 관찰)", leak_bit)):
        raw = float(pin_row[leak].mean() - pin_row[~leak].mean()) if (
            leak.any() and (~leak).any()) else None
        delta, parts = strat_delta(pin_row, dom_name_va, leak)
        sec = {"층화 안 한 생짜 Δ(관찰 — 교란 포함 · 앞 세션 ρ 와 같은 급)":
               round(raw, 5) if raw is not None else "못 잰다(한쪽 팔 0)",
               "Δ_str(층화 · 누수 − 무누수)": round(delta, 5) if delta is not None else None,
               "참여 도메인": [{"도메인": p[2], "Δ": round(p[1], 5),
                              "n누수": p[3], "n무누수": p[4], "w분자": p[0]} for p in parts],
               "참여 도메인 수": len(parts),
               "불참(한쪽 팔 0)": [d for d in sorted(set(dom_name_va))
                                 if d not in {p[2] for p in parts}]}
        if delta is not None:
            # 문서 클러스터 붓스트랩 SE
            uniq = sorted(set(va_docs))
            lut = {n: i for i, n in enumerate(uniq)}
            ids = np.asarray([lut[n] for n in va_doc_arr])
            groups = [np.where(ids == i)[0] for i in range(len(uniq))]
            rng = np.random.default_rng(SEED_CL_SE)
            reps, degen = [], 0
            for _ in range(B_BOOT):
                gs = rng.integers(0, len(uniq), size=len(uniq))
                sel = np.concatenate([groups[g] for g in gs])
                dd, _p = strat_delta(pin_row[sel], dom_name_va[sel], leak[sel])
                if dd is None:
                    degen += 1
                else:
                    reps.append(dd)
            se = float(np.std(reps, ddof=1))
            sec["문서 클러스터 붓스트랩 SE"] = round(se, 5)
            sec["붓스트랩"] = {"B": B_BOOT, "seed": SEED_CL_SE, "퇴화 뽑기(참여 도메인 0)": degen}
            sec["CI95(백분위)"] = [round(float(np.percentile(reps, 2.5)), 5),
                                  round(float(np.percentile(reps, 97.5)), 5)]
            # 층화 순열 — 문서 라벨을 «도메인 안»에서 재배치
            doc_dom, doc_leak = {}, {}
            for dc, dm, lk in zip(va_doc_arr, dom_name_va, leak):
                doc_dom[dc] = dm
                doc_leak[dc] = bool(lk)
            by_dom = collections.defaultdict(list)
            for dc, dm in doc_dom.items():
                by_dom[dm].append(dc)
            rng2 = np.random.default_rng(SEED_PERM)
            null = []
            for _ in range(B_PERM):
                lab = {}
                for dm, dcs in by_dom.items():
                    flags = np.asarray([doc_leak[x] for x in dcs])
                    flags = rng2.permutation(flags)
                    for x, fl in zip(dcs, flags):
                        lab[x] = bool(fl)
                pl = np.asarray([lab[x] for x in va_doc_arr])
                dd, _p = strat_delta(pin_row, dom_name_va, pl)
                if dd is not None:
                    null.append(dd)
            null = np.asarray(null)
            p_two = float((np.abs(null) >= abs(delta)).mean())
            p_low = float((null <= delta).mean())
            sec["순열검정"] = {"B": B_PERM, "seed": SEED_PERM, "유효 뽑기": int(len(null)),
                              "p(양측)": round(p_two, 4), "p(단측 · Δ ≤ 관측)": round(p_low, 4),
                              "귀무 중앙값": round(float(np.median(null)), 5),
                              "귀무 SD": round(float(null.std(ddof=1)), 5)}
            mde = 2 * max(se, 0.0)
            sec["MDE 스탬프"] = {"산식": "2×max(SE_클러스터, J)", "SE": round(se, 5),
                                "J(핀볼 재학습 지터)": "🔴 미측정 — 0 대입(하한 낙인)",
                                "MDE(하한)": round(mde, 5)}
            sec["G2"] = {"통과": gate_g2(delta, mde, p_two),
                         "여유 = |Δ| − MDE": round(abs(delta) - mde, 5),
                         "부호 서명": "핀볼은 낮을수록 좋다 → Δ<0 = 누수 행이 더 좋다 = 「누수가 판을 부풀렸다」 쪽"}
        out.setdefault("㉢ 판정 대비 — 도메인 층화", {})[label] = sec

    # ── ㉣ 신판(무누수 부분집합) 판 ──
    clean = ~leak_doc
    cov = np.asarray(ev["cover_ent"], dtype=np.float64)

    def cl_se(vals, keys, seed):
        uniq = sorted(set(keys))
        lut = {n: i for i, n in enumerate(uniq)}
        ids = np.asarray([lut[n] for n in keys])
        groups = [np.where(ids == i)[0] for i in range(len(uniq))]
        rng = np.random.default_rng(seed)
        reps = np.empty(B_BOOT)
        for bi in range(B_BOOT):
            gs = rng.integers(0, len(uniq), size=len(uniq))
            reps[bi] = vals[np.concatenate([groups[g] for g in gs])].mean()
        return round(float(reps.std(ddof=1)), 5), len(uniq)

    def row_se(vals, seed):
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, len(vals), size=(B_BOOT, len(vals)))
        return round(float(vals[idx].mean(axis=1).std(ddof=1)), 5)

    board = {"🔴 낙인": "이것은 «누수 없앤 헤드라인»이 아니다(사전등록 §4). 같은 배포 정본을 "
                      "val 의 «무누수 부분집합»에서 다시 집계한 «분모가 다른 별개 추정량»이다(조항 60).",
             "정본": ev["정본"], "보정": ev["보정(v2.3)"],
             "구판(전체 val)": {"자 A 핀볼": round(pin_all, 5), "n행": n_va,
                              "유일 문서": len(set(va_docs)),
                              "④ 덮개율(보조 관찰)": round(float(cov.mean()), 4)}}
    if clean.sum() > 0:
        se_cl, n_doc = cl_se(pin_row[clean], va_doc_arr[clean], SEED_BOARD_CL)
        board["신판(무누수 부분집합)"] = {
            "자 A 핀볼": round(float(pin_row[clean].mean()), 5),
            "n행": int(clean.sum()), "유일 문서": n_doc,
            "유일 개체": len({ents_all[i] for i, k in zip(va_idx, clean) if k}),
            "문서 클러스터 SE(판정 눈금 · seed %s)" % SEED_BOARD_CL: se_cl,
            "행 SE(참고 · seed %s)" % SEED_BOARD_ROW: row_se(pin_row[clean], SEED_BOARD_ROW),
            "④ 덮개율(보조 관찰)": round(float(cov[clean].mean()), 4),
            "도메인별": {d: {"핀볼 평균": round(float(pin_row[clean & (dom_name_va == d)].mean()), 5),
                           "n행": int((clean & (dom_name_va == d)).sum())}
                       for d in sorted(set(dom_name_va[clean]))},
            "도메인 구성 변화": "🔴 구성이 바뀌었다 — 구판과 나란히 놓지 마라(조항 60)"}
        board["Δ(신판 − 구판)"] = round(float(pin_row[clean].mean()) - pin_all, 5)
    else:
        board["신판(무누수 부분집합)"] = "🔴 못 잰다 — 무누수 행 0"
    if leak_doc.sum() > 0:
        board["참고 — 누수 부분집합"] = {
            "자 A 핀볼": round(float(pin_row[leak_doc].mean()), 5),
            "n행": int(leak_doc.sum()),
            "④ 덮개율": round(float(cov[leak_doc].mean()), 4)}
    out["㉣ 신판 판(무누수 부분집합)"] = board

    # ── 공동언급 연결성분 (관찰 · §3) ──
    par = {}

    def find(x):
        par.setdefault(x, x)
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            par[rx] = ry

    docid2ents = collections.defaultdict(set)
    for r in rows:
        docid2ents[r["문서id"]].add(r["개체"])
    for e in ents_all:
        find(e)
    for es in docid2ents.values():
        es = list(es)
        for e in es[1:]:
            union(es[0], e)
    comp = collections.defaultdict(list)
    for e in set(ents_all):
        comp[find(e)].append(e)
    sizes = sorted((len(v) for v in comp.values()), reverse=True)
    ent2comp = {e: find(e) for e in set(ents_all)}
    comp_of_row = [ent2comp[r["개체"]] for r in rows]
    import hashlib as _h
    comp_split = np.asarray([int(_h.md5(str(c).encode()).hexdigest()[:8], 16) % 10 == 0
                             for c in comp_of_row])
    out["공동언급 연결성분 (관찰 · §3)"] = {
        "성분 수": len(comp), "최대 성분 개체 수": sizes[0] if sizes else 0,
        "최대 성분이 덮는 행": int(sum(1 for c in comp_of_row if len(comp[c]) == sizes[0])),
        "상위 5 성분 크기": sizes[:5],
        "이 단위로 분할했다면 val 행": int(comp_split.sum()),
        "판정": ("🔴 거대 성분 — 정본으로 못 쓴다(등록 §3 예측 적중)"
                if sizes and sizes[0] > 0.5 * len(set(ents_all))
                else "거대 성분 없음 — 등록 §3 의 위험 예측이 «빗나갔다»(정직 신고)")}

    out["끝 시각"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    out["걸린 초"] = round(time.time() - t0, 1)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    _sys.exit(main())
