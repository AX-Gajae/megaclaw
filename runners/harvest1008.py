#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""1008 — 웹툰 val 확충(자 수리). 사전등록 `docs/탐색/1008.md` §0~§6 의 자를 글자 그대로.

🔴 바퀴를 다시 만들지 않는다(조항 66): 언급 자·창 자는 `runners/hplt973.py` 의 생산 함수를
   부르고(norm_title·toks_of·title_ok·mentions·window), 도박 자·URL 정규화는 그 안의
   `S954` 를 그대로 쓴다. 임베더는 `runners/onboard1006.py phase_embed` 자구 미러.
🔴 모형·train·배포물 무접촉 — G4 가 11 실물 sha 전/후 항등으로 기계 증명한다.
🔴 부칙 4 — build·score 는 여는-시점 `assert_epoch` 실측, 반환값만 게재.

씀:  python3 runners/harvest1008.py scan
     python3 runners/harvest1008.py build
     python3 runners/harvest1008.py score
"""
import datetime as dt
import glob
import gzip
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import runners.hplt973 as H                      # noqa: E402  생산 함수(언급 자·창 자·S954)
from pretrain.epoch_guard import assert_epoch    # noqa: E402  부칙 4

SCRATCH = Path("/Users/ax/wm_harvest/1008")
SCRATCH.mkdir(parents=True, exist_ok=True)
PROG = SCRATCH / "progress.jsonl"
EXT_DIR = Path("/Users/ax/wm_harvest/foundation/triples/valext1008")

CURVE_SRC = ROOT / "data/ingest/wiki_daily959/웹툰.jsonl.gz"
CURVE_SNAP = SCRATCH / "웹툰_snapshot.jsonl.gz"
SAO_NPZ = Path("/Users/ax/wm_harvest/foundation/triples/sao.npz")
META_JL = Path("/Users/ax/wm_harvest/foundation/triples/meta.jsonl")
DOMS_JSON = Path("/Users/ax/wm_harvest/foundation/triples/domains.json")
TRANS = Path("/Users/ax/wm_harvest/foundation/transition")

EPOCH_SHA = "3a5c2543a55f1dab"                   # 등록 시대(사전등록 §4)
BUDGET_SHARDS = 128                              # §3-2
STOP_NEW_ENTS = 40                               # §3-2 기계 중단(양 규칙 · 자 값 무관)
EXCLUDE = set(H.SHARD_IDX)                       # 973 이 이미 쓴 8

# G4 — 무접촉 항등 실물 11 (사전등록 §5)
UNTOUCH = {
    "sao.npz": str(SAO_NPZ),
    "ensemble_manifest.json": str(TRANS / "ensemble_manifest.json"),
    "conformal.json": str(TRANS / "conformal.json"),
    "text_emb_qwen05b.npz": "/Users/ax/wm_harvest/foundation/triples/text_emb_qwen05b.npz",
    "leaderboard.json": str(TRANS / "leaderboard.json"),
    "report.json": str(TRANS / "report.json"),
    "lodo_results.json": "/Users/ax/wm_harvest/foundation/exp/lodo/results.json",
}


def _now():
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _prog(**kw):
    kw["시각"] = _now()                            # 부칙 4 ㉰ — 전 행 시각 칸
    with PROG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def untouch_shas():
    out = {}
    for k, p in UNTOUCH.items():
        out[k] = sha16(p) if os.path.exists(p) else "없음"
    man = json.load(open(TRANS / "ensemble_manifest.json", encoding="utf-8"))
    for sd, info in sorted(man["구성원"].items()):
        out["구성원 " + sd] = sha16(info["경로"]) if os.path.exists(info["경로"]) else "없음"
    return out


def load_snapshot():
    """스냅숏 곡선 → {키: {ord, views, 문서, 언어}} (H.load_entities 자구의 웹툰-전용 미러)."""
    ent = {}
    with gzip.open(CURVE_SNAP, "rt", encoding="utf-8") as f:
        for line in f:
            d = json.loads(line)
            days = np.asarray(d.get("날짜") or [], dtype=np.int64)
            views = np.asarray(d.get("조회수") or [], dtype=np.int64)
            if days.size != views.size or days.size == 0:
                continue
            order = np.argsort(days)
            days, views = days[order], views[order]
            ordn = np.asarray([dt.date(int(x) // 10000, (int(x) // 100) % 100,
                                       int(x) % 100).toordinal() for x in days],
                              dtype=np.int64)
            ent[d["키"]] = {"도메인": d.get("도메인"), "문서": d.get("문서"),
                          "언어": d.get("언어"), "ord": ordn, "views": views}
    return ent


def sao_webtoon_entities():
    tr, va = set(), set()
    with open(META_JL, encoding="utf-8") as f:
        for line in f:
            m = json.loads(line)
            if m["도메인"] == "웹툰":
                (va if m["분할"] == "val" else tr).add(m["개체"])
    return tr, va


# ══════════════════════════════════════════════════════════════════════
# 게이트 함수(부호 서명 · §5) — 값·문턱·악화 방향. 탐침이 이 함수를 그대로 문다.
# ══════════════════════════════════════════════════════════════════════
GATES = {
    # 이름: (문턱, 방향, 판정 λ) — 방향 '−' = 값이 작으면 악화 · '+' = 값이 크면 악화
    "G0 채점기 무변경(차이 칸 수)": (0, "+", lambda v, t: v <= t),
    "G1 같은-원천 확증(일치 행)": (60, "-", lambda v, t: v >= t),
    "G2 확충 규모(신규 개체 Y)": (21, "-", lambda v, t: v >= t),
    "G3 곡선 창(미달 편입 행)": (0, "+", lambda v, t: v <= t),
    "G4 무접촉 항등(불일치 실물)": (0, "+", lambda v, t: v <= t),
    "G5 병기 결측·변조(칸 수)": (0, "+", lambda v, t: v <= t),
}


def probe_direction(t=7):
    """v5.3-2 방향 탐침 — 측정 «전». 악화 극값 → 거짓 · 개선 극값 → 참. 어긋나면 중단."""
    bad = []
    for name, (thr, sign, fn) in GATES.items():
        worse = (thr - 2 * t) if sign == "-" else (thr + 2 * t)
        better = (thr + 2 * t) if sign == "-" else max(0, thr - 2 * t) if thr else 0
        if fn(worse, thr):
            bad.append(name + " — 악화 극값에서 참")
        if not fn(better, thr):
            bad.append(name + " — 개선 극값에서 거짓")
    if bad:
        _prog(단계="probe", 결함=bad)
        raise SystemExit("🔴 방향 탐침 어긋남 — 측정 없이 중단: %s" % bad)
    return {"합성 t": t, "게이트 수": len(GATES), "어긋남": 0}


def probe_data(measured):
    """v5.3-3 자료 탐침 — 측정 «후». ㉰ 악화 극값 참 · ㉱ 개선 극값 거짓 (둘 다 0 의무)."""
    a = b = 0
    for name, (thr, sign, fn) in GATES.items():
        worse = (thr - 14) if sign == "-" else (thr + 14)
        better = (thr + 14) if sign == "-" else 0
        if fn(worse, thr):
            a += 1
        if not fn(better, thr):
            b += 1
    return {"㉰ 악화 극값 참": a, "㉱ 개선 극값 거짓": b}


# ══════════════════════════════════════════════════════════════════════
# ① scan
# ══════════════════════════════════════════════════════════════════════
def phase_scan():
    import pyarrow.parquet as pq
    t0 = time.time()
    # 잰 소스 고정(조항 66) — 데몬 성장으로부터 스냅숏
    src_sha = sha16(CURVE_SRC)
    shutil.copyfile(CURVE_SRC, CURVE_SNAP)
    snap_sha = sha16(CURVE_SNAP)
    assert src_sha == snap_sha, "스냅숏 복사 어긋남"
    shas0 = untouch_shas()
    json.dump(shas0, open(SCRATCH / "untouch_t0.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    _prog(단계="scan", 무엇="시작", 곡선_sha=snap_sha, 실물_t0=len(shas0))

    ent = load_snapshot()
    tr_ents, va_ents = sao_webtoon_entities()
    exposed = tr_ents | va_ents
    cand = {k: v for k, v in ent.items() if k not in exposed}
    idx = {}
    n_eligible = 0
    for k, e in cand.items():
        t = H.norm_title(e["문서"])
        if not H.title_ok(t):
            continue
        tk = H.toks_of(t)
        if not tk or len(tk) > H.MAXN:
            continue
        idx.setdefault(tk[0], []).append((tuple(tk[1:]), t.lower(), k))
        n_eligible += 1
    못봤다_제목 = len(cand) - n_eligible
    _prog(단계="scan", 무엇="색인", 후보=len(cand), 자_통과=n_eligible, 못봤다_제목=못봤다_제목)

    shards = sorted(glob.glob(str(H.HPLT_DIR / "train-*-of-00464.parquet")))
    order = [i for i in range(len(shards)) if i not in EXCLUDE]
    G = dict((k, 0) for k in ["G0 읽은 문서", "G1 filter=keep", "G2 robotstxt=allowed",
                              "G3 kor_Hang·prob≥0.9", "G4 도박 아님", "G5 길이·한글비율",
                              "G6 URL 정규화 첫등장", "G7 본문 첫등장", "G8 후보 언급 ≥1"])
    seen_url, seen_txt = set(), set()
    hits = []
    df = {}
    valid_ents = set()
    seen_pair = set()
    scanned = []
    못읽었다 = []
    capped = False
    for si in order:
        if len(scanned) >= BUDGET_SHARDS:
            break
        path = shards[si]
        try:
            pf = pq.ParquetFile(path)
            for rg in range(pf.metadata.num_row_groups):
                tb = pf.read_row_group(rg, columns=["u", "ts", "text", "lang", "prob",
                                                    "collection", "filter", "robotstxt", "id"])
                d = tb.to_pydict()
                for j in range(len(d["id"])):
                    G["G0 읽은 문서"] += 1
                    if d["filter"][j] != "keep":
                        continue
                    G["G1 filter=keep"] += 1
                    if d["robotstxt"][j] != "allowed":
                        continue
                    G["G2 robotstxt=allowed"] += 1
                    lg, pr = d["lang"][j] or [], d["prob"][j] or []
                    if not lg or lg[0] != "kor_Hang" or not pr or float(pr[0]) < H.MIN_PROB:
                        continue
                    G["G3 kor_Hang·prob≥0.9"] += 1
                    txt = d["text"][j] or ""
                    if H.S954.GAMBLE_PAT.search(txt.encode("utf-8")):
                        continue
                    G["G4 도박 아님"] += 1
                    if len(txt) < H.MIN_CHARS or H.hangul_ratio(txt[:4000]) < H.MIN_HANGUL:
                        continue
                    G["G5 길이·한글비율"] += 1
                    uh = hashlib.md5(H.S954.norm_url(d["u"][j]).encode("utf-8")).digest()[:8]
                    if uh in seen_url:
                        continue
                    seen_url.add(uh)
                    G["G6 URL 정규화 첫등장"] += 1
                    th = hashlib.md5(txt.encode("utf-8")).digest()[:8]
                    if th in seen_txt:
                        continue
                    seen_txt.add(th)
                    G["G7 본문 첫등장"] += 1
                    ms = H.mentions(txt, idx)
                    if not ms:
                        continue
                    G["G8 후보 언급 ≥1"] += 1
                    ts = d["ts"][j]
                    if ts is None:
                        continue
                    host = H.S954.host_of(d["u"][j])
                    tl = H.tld_of(host)
                    dord = ts.date().toordinal()
                    for title, key in ms:
                        df[title] = df.get(title, 0) + 1
                        if len(hits) < H.ROW_CAP:
                            hits.append((key, title, dord, host, tl,
                                         d["collection"][j], len(txt), d["id"][j]))
                            pk = (key, dord)
                            if pk not in seen_pair and H.window(ent[key], dord) is not None:
                                seen_pair.add(pk)
                                valid_ents.add(key)
                        else:
                            capped = True
        except Exception as e:
            못읽었다.append({"shard": si, "사유": "%s: %s" % (type(e).__name__, str(e)[:200])})
            _prog(단계="scan", shard=si, 못읽었다=str(e)[:120])
            continue
        scanned.append({"shard": si, "파일": Path(path).name, "sha256": sha16(path)})
        _prog(단계="scan", shard=si, 무엇="shard 끝", 읽은=G["G0 읽은 문서"],
              언급문서=G["G8 후보 언급 ≥1"], 행=len(hits), 유효신규개체=len(valid_ents),
              초=round(time.time() - t0, 1))
        if len(valid_ents) >= STOP_NEW_ENTS:
            _prog(단계="scan", 무엇="기계 중단(§3-2)", 유효신규개체=len(valid_ents))
            break

    den_df = max(1, G["G7 본문 첫등장"])
    common = {t for t, n in df.items() if n / float(den_df) > H.DF_CAP}
    with gzip.open(SCRATCH / "hits.jsonl.gz", "wt", encoding="utf-8") as f:
        for key, title, dord, host, tl, coll, nchar, docid in hits:
            f.write(json.dumps({"개체": key, "맞은 제목": title, "날짜ord": dord,
                                "host": host, "tld": tl, "collection": coll,
                                "글자수": nchar, "문서id": docid,
                                "🔴 일반어_의심": bool(title in common)},
                               ensure_ascii=False) + "\n")
    out = {"무엇": "1008 scan — 후보 언급 수확(같은 원천 · 973 자 미러)",
           "언제(시작/끝)": [dt.datetime.fromtimestamp(t0).strftime("%Y-%m-%dT%H:%M:%S"), _now()],
           "초": round(time.time() - t0, 1),
           "곡선 스냅숏": {"원본": str(CURVE_SRC), "sha256/16": snap_sha},
           "후보": {"미노출 개체": len(cand), "언급 자 통과": n_eligible,
                  "🔴 못 봤다(제목 자 미달)": 못봤다_제목},
           "스캔": {"예산": BUDGET_SHARDS, "읽은 shard": len(scanned),
                  "제외(973 기사용)": sorted(EXCLUDE),
                  "🔴 못 봤다(미스캔 shard)": len(shards) - len(scanned) - len(EXCLUDE),
                  "🔴 못 읽었다": 못읽었다, "shard 명부": scanned},
           "게이트": G, "행 상한 걸림": capped,
           "🔴 낸 행": len(hits), "유효 (개체,언제)": len(seen_pair),
           "🔴🔴 유효 신규 개체": len(valid_ents),
           "일반어 의심 제목": sorted(common),
           "네트워크 호출": 0}
    json.dump(out, open(SCRATCH / "out1008_scan.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"유효 신규 개체": len(valid_ents), "행": len(hits),
                      "읽은 shard": len(scanned)}, ensure_ascii=False))


# ══════════════════════════════════════════════════════════════════════
# ② build — 중복 제거·창 재확인·임베딩·npz
# ══════════════════════════════════════════════════════════════════════
def phase_build():
    t0 = time.time()
    stamp = assert_epoch(EPOCH_SHA)                       # 부칙 4 — 여는 시점 실측
    _prog(단계="build", 무엇="시대 관문", **{"실측 sha": stamp["실측 sha"],
                                        "여는 시각": stamp["여는 시각"]})
    ent = load_snapshot()
    rows = []
    seen = set()
    g9_recheck_fail = 0
    with gzip.open(SCRATCH / "hits.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            h = json.loads(line)
            key, dord = h["개체"], h["날짜ord"]
            if (key, dord) in seen:                       # triples.py (개체,언제) 자구
                continue
            w = H.window(ent[key], dord)
            if w is None:
                g9_recheck_fail += 1
                continue
            seen.add((key, dord))
            day = dt.date.fromordinal(dord).isoformat()
            a = {"무엇": "이 한국어 웹문서가 이 개체를 언급했다",
                 "언제": day, "개체": key, "문서": ent[key]["문서"],
                 "언어": ent[key]["언어"], "맞은 제목": h["맞은 제목"],
                 "🔴 일반어_의심": h["🔴 일반어_의심"], "host": h["host"],
                 "tld": h["tld"], "collection": h["collection"],
                 "글자수": h["글자수"], "문서id": h["문서id"]}
            texts = [str(v) for k, v in sorted(a.items())
                     if isinstance(v, str) and k not in ("개체", "언제")]   # triples.py 자구
            rows.append({"개체": key, "언제": day, "s": w[0], "o": w[1],
                         "텍스트": " · ".join(texts)[:2000], "a": a})
    ents = sorted(set(r["개체"] for r in rows))
    _prog(단계="build", 행=len(rows), 개체=len(ents), 창_재확인_탈락=g9_recheck_fail)

    # 임베딩 — onboard1006 phase_embed 자구 미러
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    import torch
    torch.set_num_threads(4)
    from transformers import AutoModel, AutoTokenizer
    SNAP = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
            "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
    texts = [r["텍스트"] for r in rows]
    uniq = sorted(set(texts))
    tok = AutoTokenizer.from_pretrained(SNAP)
    model = AutoModel.from_pretrained(SNAP, dtype=torch.float32)
    model.eval()
    emb_u = {}
    with torch.no_grad():
        for i in range(0, len(uniq), 16):
            batch = uniq[i:i + 16]
            enc = tok(batch, padding=True, truncation=True, max_length=96,
                      return_tensors="pt")
            hdn = model(**enc).last_hidden_state
            mask = enc["attention_mask"].unsqueeze(-1).to(hdn.dtype)
            e = (hdn * mask).sum(1) / mask.sum(1).clamp(min=1.0)
            for t, v in zip(batch, e.numpy().astype(np.float32)):
                emb_u[t] = v
            if i % 160 == 0:
                _prog(단계="build", 임베딩=i, 유일=len(uniq))
    E = np.stack([emb_u[t] for t in texts]).astype(np.float32)

    S = np.asarray([r["s"] for r in rows], dtype=np.float32)
    O = np.asarray([r["o"] for r in rows], dtype=np.float32)
    year = np.asarray([float(r["언제"][:4]) + (float(r["언제"][5:7]) - 0.5) / 12.0
                       for r in rows], dtype=np.float32)      # triples.py 자구
    doy = np.asarray([int(r["언제"][5:7]) * 30.4 + int(r["언제"][8:10])
                      for r in rows], dtype=np.float32)       # triples.py 자구
    names = np.asarray([r["개체"] for r in rows])
    dates = np.asarray([r["언제"] for r in rows])
    EXT_DIR.mkdir(parents=True, exist_ok=True)
    npz_path = EXT_DIR / "val_ext_webtoon.npz"
    np.savez_compressed(str(npz_path), S=S, O=O, year=year, doy=doy, E=E,
                        names=names, dates=dates)
    with open(EXT_DIR / "val_ext_meta.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps({"개체": r["개체"], "언제": r["언제"], "도메인": "웹툰",
                                "분할": "val(확장 1008)", "텍스트": r["텍스트"],
                                "a_액션": r["a"]}, ensure_ascii=False) + "\n")
    roster = {"무엇": "웹툰 val 확장 명부(1008) — 재빌드 시 이 개체들은 분할=val 강제",
              "출처": "docs/탐색/1008.md §3 · 원장 「자 수리 과제 — 웹툰 val 확충」",
              "개체": ents,
              "행": len(rows),
              "val_ext_webtoon.npz sha256/16": sha16(npz_path),
              "곡선 스냅숏 sha256/16": sha16(CURVE_SNAP),
              "만든 때": _now()}
    json.dump(roster, open(EXT_DIR / "val_ext_roster.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    out = {"무엇": "1008 build — val 확장 실물",
           "시대(부칙 4)": stamp,
           "행": len(rows), "개체": len(ents), "창_재확인_탈락": g9_recheck_fail,
           "유일 텍스트": len(uniq), "E 형상": list(E.shape),
           "임베더": {"모델": "Qwen2.5-0.5B (base)", "스냅숏": SNAP, "최대토큰": 96,
                   "풀링": "last_hidden_state attention-mask 평균", "장치": "cpu"},
           "npz": {"경로": str(npz_path), "sha256/16": sha16(npz_path),
                  "MB": round(npz_path.stat().st_size / 1048576.0, 3)},
           "초": round(time.time() - t0, 1)}
    json.dump(out, open(SCRATCH / "out1008_build.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(json.dumps({"행": len(rows), "개체": len(ents)}, ensure_ascii=False))


# ══════════════════════════════════════════════════════════════════════
# ③ score — G0~G5 · 판 전/후
# ══════════════════════════════════════════════════════════════════════
def _strip_volatile(d):
    """비교 제외 칸(시각·채점기 sha·mtime 무관 값 아님) 제거한 깊은 사본."""
    import copy
    x = copy.deepcopy(d)
    x.pop("잰 시각", None)
    x.pop("끝 시각(v3.2)", None)
    x.pop("채점기 자신(조항 66 — 자기 출처 · v3.2)", None)
    return x


def _deep_diff(a, b, path=""):
    diffs = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                diffs.append(path + "/" + str(k) + " ← 없던 칸")
            elif k not in b:
                diffs.append(path + "/" + str(k) + " → 사라진 칸")
            else:
                diffs += _deep_diff(a[k], b[k], path + "/" + str(k))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            diffs.append(path + " 길이 %d≠%d" % (len(a), len(b)))
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                diffs += _deep_diff(x, y, path + "[%d]" % i)
    else:
        if a != b:
            diffs.append(path + " %r≠%r" % (a, b))
    return diffs


def phase_score():
    import subprocess
    t0 = time.time()
    probe = probe_direction()                             # 측정 «전» 방향 탐침
    stamp = assert_epoch(EPOCH_SHA)                       # 부칙 4
    _prog(단계="score", 무엇="시대 관문+탐침", **{"실측 sha": stamp["실측 sha"]})

    # G1 — 같은-원천 재실측(현 val 60행 비트 재현)
    ent = load_snapshot()
    z = np.load(str(SAO_NPZ))
    meta = [json.loads(l) for l in open(META_JL, encoding="utf-8")]
    S, O = z["S"], z["O"]
    idxs = [i for i, m in enumerate(meta) if m["도메인"] == "웹툰" and m["분할"] == "val"]
    g1_ok = 0
    for i in idxs:
        m = meta[i]
        e = ent.get(m["개체"])
        w = H.window(e, dt.date.fromisoformat(m["언제"]).toordinal()) if e else None
        if w is not None and np.array_equal(np.asarray(w[0], np.float32), S[i]) \
                and np.array_equal(np.asarray(w[1], np.float32), O[i]):
            g1_ok += 1
    _prog(단계="score", G1_일치=g1_ok, 분모=len(idxs))

    # 판 «전» — v2.4 기본 호출 (+ G0: v2.3 기준선과 값 항등)
    전_p = ROOT / "data/lab/1008_판_전.json"
    후_p = ROOT / "data/lab/1008_판_후.json"
    r = subprocess.run([sys.executable, str(ROOT / "pretrain/scoreboard.py"),
                        "--out", str(전_p)], capture_output=True, text=True)
    assert r.returncode == 0, "판_전 채점 실패: " + r.stderr[-500:]
    base = json.load(open(SCRATCH / "판_전_구채점기v23.json", encoding="utf-8"))
    전 = json.load(open(전_p, encoding="utf-8"))
    g0_diffs = _deep_diff(_strip_volatile(base), _strip_volatile(전))
    _prog(단계="score", G0_차이=len(g0_diffs))

    # 판 «후» — 눈금 교체 병기
    ext_npz = EXT_DIR / "val_ext_webtoon.npz"
    r = subprocess.run([sys.executable, str(ROOT / "pretrain/scoreboard.py"),
                        "--valext", str(ext_npz), "--out", str(후_p)],
                       capture_output=True, text=True)
    assert r.returncode == 0, "판_후 채점 실패: " + r.stderr[-500:]
    후 = json.load(open(후_p, encoding="utf-8"))

    # G5 — 병기 결측·변조
    EXT_KEY = "눈금 교체(조항 60 — 웹툰 val 확충 1008)"
    need = ["사건", "웹툰 구자", "웹툰 신자", "판 넷 재채점(신자 눈금)", "낙인"]
    miss = 0 if EXT_KEY in 후 else 1
    if EXT_KEY in 후:
        miss += sum(1 for k in need if k not in 후[EXT_KEY])
    구자변조 = _deep_diff(_strip_volatile(전),
                      {k: v for k, v in _strip_volatile(후).items() if k != EXT_KEY})
    g5 = miss + len(구자변조)

    # G2·G3 — build 산출물에서
    bd = json.load(open(SCRATCH / "out1008_build.json", encoding="utf-8"))
    ze = np.load(str(ext_npz))
    g3_bad = int(sum(1 for i in range(len(ze["S"]))
                     if len(ze["S"][i]) != 90 or len(ze["O"][i]) != 91))
    g2_y = int(len(set(ze["names"].tolist())))

    # G4 — 무접촉 항등
    shas0 = json.load(open(SCRATCH / "untouch_t0.json", encoding="utf-8"))
    shas1 = untouch_shas()
    g4_bad = [k for k in shas0 if shas0.get(k) != shas1.get(k)]

    측정 = {"G0 채점기 무변경(차이 칸 수)": len(g0_diffs),
          "G1 같은-원천 확증(일치 행)": g1_ok,
          "G2 확충 규모(신규 개체 Y)": g2_y,
          "G3 곡선 창(미달 편입 행)": g3_bad,
          "G4 무접촉 항등(불일치 실물)": len(g4_bad),
          "G5 병기 결측·변조(칸 수)": g5}
    표 = {}
    전부통과 = True
    for name, v in 측정.items():
        thr, sign, fn = GATES[name]
        ok = fn(v, thr)
        전부통과 = 전부통과 and ok
        여유 = (v - thr) if sign == "-" else (thr - v)
        표[name] = {"값": v, "문턱": thr, "악화 방향": sign, "여유(Δ−문턱, 통과 방향 +)": 여유,
                  "판정": "통과" if ok else "✘ 불통과"}
    dp = probe_data(측정)
    if 측정["G2 확충 규모(신규 개체 Y)"] < 21:
        판정어 = "확충 미달 — 자 존속(신자 불채택 · 명부 미커밋 · 판 갱신 없음)"
    elif 전부통과:
        판정어 = "자 교체 성립(웹툰 val 9→%d 개체) — 성과 주장 없음" % (9 + g2_y)
    else:
        판정어 = "무효 — 자 존속(불통과 게이트 참조)"

    out = {"무엇": "1008 score — 게이트 판정 · 판 전/후",
           "사전등록": "docs/탐색/1008.md §0~§6 (실측 전 커밋)",
           "시대(부칙 4 — 여는 시점 실측)": stamp,
           "방향 탐침(측정 전)": probe,
           "게이트 표(부호 서명 · 여유 비반올림)": 표,
           "자료 탐침(측정 후)": dp,
           "🔴 판정어(사전 고정 문언)": 판정어,
           "G0 차이 칸": g0_diffs[:20], "G4 불일치": g4_bad,
           "G5 구자 변조 칸": 구자변조[:20],
           "판 전/후": {"전": str(전_p), "후": str(후_p),
                    "전 sha256/16": sha16(전_p), "후 sha256/16": sha16(후_p)},
           "확장 실물": {"npz sha256/16": sha16(ext_npz),
                     "행": int(len(ze["S"])), "개체": g2_y,
                     "명부": str(EXT_DIR / "val_ext_roster.json")},
           "네트워크 호출": 0,
           "초": round(time.time() - t0, 1),
           "끝 시각": _now()}
    json.dump(out, open(SCRATCH / "out1008_score.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    json.dump(out, open(ROOT / "runners/out1008_score.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    # G2 통과 시에만 명부를 저장소로 (사전등록 §5 판정어 규칙)
    if 측정["G2 확충 규모(신규 개체 Y)"] >= 21 and 전부통과:
        shutil.copyfile(EXT_DIR / "val_ext_roster.json",
                        ROOT / "data/lab/val_ext_roster.json")
    print(json.dumps({"판정어": 판정어, "게이트": {k: v["판정"] for k, v in 표.items()}},
                     ensure_ascii=False))


if __name__ == "__main__":
    {"scan": phase_scan, "build": phase_build, "score": phase_score}[sys.argv[1]]()
