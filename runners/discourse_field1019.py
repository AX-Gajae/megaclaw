# -*- coding: utf-8 -*-
"""사이클 1019 — L1 담론 장 인코더 + 검증 ⓐⓑⓒ (사전등록 docs/탐색/1019.md 의 실행기).

단계(순서 강제 — 각 단계는 앞 단계 산출을 읽는다):
  probe    방향 탐침(v5.3-2) + leak/field 자기시험 — 실패면 측정 없이 중단
  denom    §3 검증 실효 분모 사다리 + 곡선 특징 + y + SD_cl (원장 sha 시대 관문)
  snapshot §1-1 신선 담론 스냅숏 복사 + 매칭(원장 이름 전체 + 키워드 18)
  fineweb  §1-2 과거 담론 — dated 부분집합 RE2 매칭(V3 이름 + 키워드 · 샤드 체크포인트)
  embed    §1-4 임베딩(상한 규칙 · 512 체크포인트) → store(docs_*, emb_*)
  mde      §4 MDE «먼저» — ⓐ 팔 + 순열 위약 40 → assert_mde → 레인 확정
  validate §5 검증 ⓐⓑⓒ × τ{30,90,180,365} + 게이트/관찰 + 붓스트랩 SE
  grid     §7 격자(grid_sov + sdisc_T0)
  report   meta1019.json 취합(sha·스탬프·사다리)

위생: CPU ≤5스레드(torch4·pyarrow4) · load1>10 → 60초 재잼 · 원본 무수정 ·
신규 네트워크 0 · 주행 중 소스 수정 금지(조항 66).
"""
import os

os.environ.setdefault("OMP_NUM_THREADS", "4")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "4")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")

import argparse
import datetime as dt
import glob
import gzip
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pretrain.leak_guard import assert_no_leak, LeakDetected
from pretrain.mde_guard import assert_mde, mde_of, MdeUnderpowered
from pretrain import discourse_field as dfield

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = "/Users/ax/wm_harvest/foundation/l1_discourse"
WORK = os.path.join(OUT, "work")
LEDGER = "/Users/ax/wm_harvest/foundation/ledger_interventions/ledger.jsonl"
LEDGER_SHA_1016 = "9a76948d3e619424ceadcfb0e2c0c06eceb80992dfd36784b9cd554ed998cffd"
DISCOURSE_DIR = "/Users/ax/wm_harvest/discourse"
FW_DIR = "/Users/ax/wm_harvest/fineweb2_ko"
PUB_DIR = "/Users/ax/wm_harvest/foundation/pubdate/fineweb2_pubdate"
WD_DIR = os.path.join(REPO, "data/ingest/wiki_daily")
WV_DIR = os.path.join(REPO, "data/state/wiki_views")

GUARD_DAYS = 14                    # §3 T0 = announced ∥ opened−14 (1018 §1 미러)
PRE_COVER = 85                     # §3 사전 창 커버 관문
TAUS = dfield.TAUS
TAU_CANON = dfield.TAU_CANON
KEYWORDS = ["웹툰", "웹소설", "팝업스토어", "팝업 스토어", "아이돌 데뷔", "콜라보",
            "굿즈", "IP 라이선스", "캐릭터 IP", "애니메이션 개봉", "단행본", "정주행",
            "콘서트", "팬덤", "스토어 오픈", "네이버웹툰", "카카오웹툰", "카카오페이지"]
NAME_BAD = {"null", "none", "unresolved"}
TEXT_MATCH_CHARS = 2000            # §1-2 매칭 창
TEXT_STORE_CHARS = 500             # §1-4 저장·임베딩 창
CAP_FRESH_TOTAL = 20000            # §1-4 상한
CAP_FRESH_PER_ENT = 400
CAP_PAST_PER_ENT = 150
CAP_BG_PER_MONTH = 40
CAP_BG_TOTAL = 8000
LAMBDAS = (0.01, 0.1, 1.0, 10.0, 100.0, 1000.0)   # §5 능형 격자
SEEDS = tuple(range(10))            # §5 외부 씨앗
KFOLD = 5
PERM_SEEDS = (7019, 8019)           # §4 위약 시드
PERM_P = 20                         # 시드당 순열 수
B_BOOT = 10000                      # §5 붓스트랩
BOOT_SEED = 1019
AIM_FRAC = 0.15                     # §4 겨냥 = 0.15×SD_cl(y)

LOG_FH = None


def say(msg):
    line = "[%s] %s" % (time.strftime("%H:%M:%S"), msg)
    print(line, flush=True)
    if LOG_FH:
        LOG_FH.write(line + "\n")
        LOG_FH.flush()


def open_log():
    global LOG_FH
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    LOG_FH = open(os.path.join(OUT, "run1019.out"), "a", encoding="utf-8")


def wait_load():
    while os.getloadavg()[0] > 10:
        say("load1 %.1f > 10 — 60초 재잼" % os.getloadavg()[0])
        time.sleep(60)


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def sha_full(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def jdump(obj, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, default=str)
    os.replace(tmp, path)


def jload(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_iso(s):
    if not s:
        return None
    try:
        return dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def name_ok(nm):
    nm = (nm or "").strip()
    if len(nm) < 2 or nm.lower() in NAME_BAD:
        return None
    return nm


# ── 게이트 함수 + 방향 탐침 (v5.3-2 — 측정 «전») ─────────────────────────

def gate_improve(delta, thr):
    """ⓑ−ⓐ 게이트 — Δ = MAE_ⓐ − MAE_ⓑ. + 쪽(오차 감소)만 통과."""
    return delta > thr


def direction_probe():
    t = 0.1
    checks = {
        "개선극값(+2t)=참": gate_improve(+2 * t, t) is True,
        "악화극값(−2t)=거짓": gate_improve(-2 * t, t) is False,
        "0=거짓(한쪽)": gate_improve(0.0, t) is False,
    }
    leak_ok = __import__("pretrain.leak_guard", fromlist=["selftest"]).selftest()["전부_기대대로"]
    field_ok = dfield.selftest()["전부_기대대로"]
    checks["leak_guard 자기시험 6경우"] = bool(leak_ok)
    checks["discourse_field 자기시험 7경우"] = bool(field_ok)
    ok = all(checks.values())
    return {"통과": ok, "검사": checks}


# ── denom: §3 사다리 ─────────────────────────────────────────────────────

def load_wiki_daily():
    rows, shas = [], {}
    for fp in sorted(glob.glob(os.path.join(WD_DIR, "*.jsonl.gz"))):
        shas[os.path.basename(fp)] = sha16(fp)
        with gzip.open(fp, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if not r.get("날짜"):
                    continue
                curve = {int(a): int(b) for a, b in zip(r["날짜"], r["조회수"])}
                rows.append({"키": r["키"], "도메인": r["도메인"], "문서": r["문서"],
                             "curve": curve})
    return rows, shas


def d2i(d):
    return d.year * 10000 + d.month * 100 + d.day


def stage_denom():
    wait_load()
    led_sha = sha_full(LEDGER)
    if led_sha != LEDGER_SHA_1016:
        say("🔴 시대 결함 — 원장 sha %s ≠ 1016 도장 — 측정 없이 중단" % led_sha[:16])
        raise SystemExit(2)
    ledger = [json.loads(l) for l in open(LEDGER, encoding="utf-8")]
    wrows, wd_shas = load_wiki_daily()
    by_doc = {}
    for r in wrows:
        by_doc.setdefault(r["문서"], []).append(r)
    by_key = {}
    for r in wrows:
        by_key.setdefault(r["키"], []).append(r)

    ladder = {"V0": len(ledger)}
    v1 = [r for r in ledger if (r.get("Y") or {}).get("u_daily_visitors") is not None]
    ladder["V1_U가능"] = len(v1)
    v2, drop_scope, drop_name = [], 0, 0
    for r in v1:
        sc = (r.get("Y") or {}).get("scope") or {}
        if sc.get("interim") or sc.get("per_day") or sc.get("forecast"):
            drop_scope += 1
            continue
        w = (r.get("A") or {}).get("what") or {}
        nm = name_ok(w.get("ip_name") or w.get("brand"))
        if nm is None:
            drop_name += 1
            continue
        v2.append((r, nm))
    ladder["V2_scope정상∩이름"] = len(v2)
    ladder["V2_탈락"] = {"scope": drop_scope, "이름없음": drop_name}

    records = []
    drop_curve = 0
    route_cnt = {"wiki_daily": 0, "route2": 0}
    leak_curve = []
    for r, nm in v2:
        w = r["A"]["when"]
        opened = parse_iso(w.get("opened_at"))
        ann = parse_iso(w.get("announced_at"))
        T0 = ann if ann else opened - dt.timedelta(days=GUARD_DAYS)
        pre_days = [T0 - dt.timedelta(days=90) + dt.timedelta(days=k) for k in range(90)]
        # 곡선 채택 — 1018 §2 미러의 사전 창 한정판 (§3 사전 고정)
        wr = (r.get("source") or {}).get("wiki_resolution")
        pg = wr.get("page") if wr else None
        cands = list(by_doc.get(pg, [])) if pg else []
        for row in by_key.get(r["record_id"], []):
            if row not in cands:
                cands.append(row)
        best = None
        for row in cands:
            cov = sum(1 for d in pre_days if d2i(d) in row["curve"])
            key = (-cov, row["도메인"], row["키"])
            if best is None or key < best[0]:
                best = (key, row, cov)
        curve, route = None, None
        if best is not None and best[2] >= PRE_COVER:
            curve, route = best[1]["curve"], "wiki_daily"
        else:
            fp = os.path.join(WV_DIR, r["record_id"] + ".json")
            if os.path.exists(fp):
                v = json.load(open(fp))
                if v.get("days") and v.get("page"):
                    c2 = {int(x[0]): int(x[1]) for x in v["days"]}
                    if sum(1 for d in pre_days if d2i(d) in c2) >= PRE_COVER:
                        curve, route = c2, "route2"
        if curve is None:
            drop_curve += 1
            continue
        route_cnt[route] += 1
        obs = [d for d in pre_days if d2i(d) in curve]
        stamp = assert_no_leak([{"id": d.isoformat(), "published_at": d.isoformat()}
                                for d in obs], T0, "곡선 사전창 rid=%s" % r["record_id"])
        leak_curve.append(stamp["여유일"])
        vec = np.array([math.log1p(curve.get(d2i(d), 0)) for d in pre_days])
        filled = sum(1 for d in pre_days if d2i(d) not in curve)
        doy = T0.timetuple().tm_yday / 365.25 * 2 * math.pi
        feats = [float(vec.mean()), float(vec.std()),
                 float(vec[60:].mean() - vec[:30].mean()), float(vec[-7:].mean()),
                 float(vec.max()), math.sin(doy), math.cos(doy)]
        y = math.log1p(r["Y"]["u_daily_visitors"])
        records.append({
            "rid": r["record_id"], "layer": r["layer"], "name": nm,
            "T0": T0.isoformat(), "opened": opened.isoformat(),
            "announced": w.get("announced_at"), "y": y,
            "basis": (r["Y"].get("visitors_basis") or "unknown"),
            "curve_feats": feats, "curve_route": route, "filled": filled,
            "cover": 90 - filled,
        })
    ladder["V3_최종"] = len(records)
    ladder["V3_탈락_곡선"] = drop_curve
    names_v3 = sorted({r["name"] for r in records})
    clusters = names_v3
    ymeans = {}
    for r in records:
        ymeans.setdefault(r["name"], []).append(r["y"])
    cl_means = np.array([np.mean(v) for v in ymeans.values()])
    sd_cl = float(np.std(cl_means, ddof=1)) if len(cl_means) > 1 else float("nan")
    basis_cnt = {}
    for r in records:
        basis_cnt[r["basis"]] = basis_cnt.get(r["basis"], 0) + 1
    st = {
        "사다리": ladder, "route": route_cnt, "n_클러스터": len(clusters),
        "SD_cl(y)": sd_cl, "basis": basis_cnt,
        "곡선_최소여유일": min(leak_curve) if leak_curve else None,
        "곡선_채움_합": sum(r["filled"] for r in records),
        "ledger_sha256": led_sha, "wiki_daily_sha16": wd_shas,
        "records": records, "names_v3": names_v3,
        "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    jdump(st, os.path.join(WORK, "state1019.json"))
    say("denom: V0 %d → V1 %d → V2 %d → V3 %d (곡선 탈락 %d · scope %d · 이름 %d) · "
        "클러스터 %d · SD_cl %.4f" %
        (ladder["V0"], ladder["V1_U가능"], ladder["V2_scope정상∩이름"], ladder["V3_최종"],
         drop_curve, drop_scope, drop_name, len(clusters), sd_cl))


# ── snapshot: §1-1 신선 담론 ─────────────────────────────────────────────

def ledger_names():
    names = set()
    for ln in open(LEDGER, encoding="utf-8"):
        r = json.loads(ln)
        w = (r.get("A") or {}).get("what") or {}
        nm = name_ok(w.get("ip_name") or w.get("brand"))
        if nm:
            names.add(nm)
    return names


def stage_snapshot():
    wait_load()
    snap = os.path.join(OUT, "snapshot_in")
    os.makedirs(snap, exist_ok=True)
    srcs = ["bing_news", "news_rss", "dcinside", "theqoo", "ruliweb", "instiz"]
    file_shas = {}
    for s in srcs:
        d = os.path.join(DISCOURSE_DIR, s)
        if not os.path.isdir(d):
            continue
        os.makedirs(os.path.join(snap, s), exist_ok=True)
        for fp in sorted(glob.glob(os.path.join(d, "*.jsonl.gz"))):
            dst = os.path.join(snap, s, os.path.basename(fp))
            shutil.copy2(fp, dst)
            file_shas["%s/%s" % (s, os.path.basename(fp))] = sha16(dst)
    names = sorted(ledger_names())
    nameset = set(names)
    say("snapshot: 파일 %d · 원장 유일 이름 %d" % (len(file_shas), len(names)))

    ent_rows, bg_rows = [], []
    seen = set()
    n_docs = n_pubnull = n_trunc = 0
    route_cnt = {"text": 0, "query": 0, "both": 0}
    for s in srcs:
        for fp in sorted(glob.glob(os.path.join(snap, s, "*.jsonl.gz"))):
            try:
                fh = gzip.open(fp, "rt", encoding="utf-8")
                lines = fh.readlines()
                fh.close()
            except (EOFError, OSError):
                # 잘린 꼬리 멤버 — 읽힌 데까지 쓰고 그 뒤 버림(계수)
                n_trunc += 1
                lines = []
                try:
                    with gzip.open(fp, "rt", encoding="utf-8") as fh:
                        for line in fh:
                            lines.append(line)
                except (EOFError, OSError):
                    pass
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                n_docs += 1
                pub = parse_iso(d.get("published_at"))
                if pub is None:
                    n_pubnull += 1
                    continue
                key = s[:2] + hashlib.sha1((d.get("url") or "").encode()).hexdigest()[:16]
                if key in seen:
                    continue
                seen.add(key)
                title = d.get("제목") or ""
                body = d.get("본문") or ""
                t = (title + " " + body)[:TEXT_MATCH_CHARS]
                m_text = [n for n in names if n in t]
                m_query = []
                if s == "bing_news":
                    for nm in (d.get("매칭") or []):
                        nm = name_ok(nm)
                        if nm and nm in nameset and nm not in m_text:
                            m_query.append(nm)
                matched = m_text + m_query
                text500 = (title + " · " + body)[:TEXT_STORE_CHARS]
                if matched:
                    if m_text and m_query:
                        route_cnt["both"] += 1
                    elif m_text:
                        route_cnt["text"] += 1
                    else:
                        route_cnt["query"] += 1
                    ent_rows.append({"key": key, "published_at": pub.isoformat(),
                                     "원천": s, "names": matched,
                                     "routes": {"text": m_text, "query": m_query},
                                     "text500": text500,
                                     "text_sha16": hashlib.sha256(
                                         text500.encode()).hexdigest()[:16]})
                else:
                    kws = [k for k in KEYWORDS if k in t]
                    if kws:
                        bg_rows.append({"key": key, "published_at": pub.isoformat(),
                                        "원천": s, "kw": kws, "text500": text500,
                                        "text_sha16": hashlib.sha256(
                                            text500.encode()).hexdigest()[:16]})
    with gzip.open(os.path.join(WORK, "fresh_ent.jsonl.gz"), "wt", encoding="utf-8") as f:
        for r in ent_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with gzip.open(os.path.join(WORK, "fresh_bg.jsonl.gz"), "wt", encoding="utf-8") as f:
        for r in bg_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {"파일": file_shas, "행": n_docs, "pub_null": n_pubnull,
            "잘린파일": n_trunc, "개체행": len(ent_rows), "배경행": len(bg_rows),
            "귀속경로": route_cnt, "이름수": len(names),
            "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    jdump(meta, os.path.join(WORK, "snapshot_meta.json"))
    say("snapshot: 행 %d · pub null %d · 개체 %d(경로 %s) · 배경 %d · 잘림 %d" %
        (n_docs, n_pubnull, len(ent_rows), route_cnt, len(bg_rows), n_trunc))


# ── fineweb: §1-2 과거 담론 ──────────────────────────────────────────────

def stage_fineweb(max_seconds):
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    pa.set_cpu_count(4)
    pa.set_io_thread_count(2)
    st_path = os.path.join(WORK, "fineweb_state.json")
    st = jload(st_path, {"done": [], "counts": {}})
    state = jload(os.path.join(WORK, "state1019.json"))
    names_v3 = state["names_v3"]
    pats = sorted(set(names_v3) | set(KEYWORDS), key=len, reverse=True)
    pattern = "|".join(re.escape(p) for p in pats)
    name_set = set(names_v3)
    t_start = time.time()
    parts_dir = os.path.join(WORK, "fw_parts")
    os.makedirs(parts_dir, exist_ok=True)
    shards = sorted(glob.glob(os.path.join(FW_DIR, "*.parquet")))
    for sp in shards:
        base = os.path.basename(sp).replace(".parquet", "")
        if base in st["done"]:
            continue
        if time.time() - t_start > max_seconds:
            say("fineweb: 예산 %ds 소진 — 같은 명령 반복으로 재개" % max_seconds)
            return False
        wait_load()
        # dated 색인 (차이일 ≤ 0 채택 관문)
        pub_fp = os.path.join(PUB_DIR, base + ".pub.jsonl.gz")
        dated, n_diffpos = {}, 0
        with gzip.open(pub_fp, "rt", encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                if r.get("차이일") is not None and r["차이일"] > 0:
                    n_diffpos += 1
                    continue
                dated[r["id"]] = r["published_at"]
        n_rows = n_dated = n_hit = n_ent = n_bg = 0
        ent_out, bg_out = [], []
        pf = pq.ParquetFile(sp)
        for batch in pf.iter_batches(batch_size=8192, columns=["id", "text"]):
            ids = batch.column(0).to_pylist()
            n_rows += len(ids)
            keep = [i for i, x in enumerate(ids) if x in dated]
            if not keep:
                continue
            n_dated += len(keep)
            sub = batch.column(1).take(pa.array(keep, type=pa.int64()))
            heads = pc.utf8_slice_codeunits(sub, 0, TEXT_MATCH_CHARS)
            mask = pc.match_substring_regex(heads, pattern)
            for j, hit in enumerate(mask.to_pylist()):
                if not hit:
                    continue
                n_hit += 1
                head = heads[j].as_py()
                i = keep[j]
                names_hit = [n for n in names_v3 if n in head]
                row = {"key": "fw" + hashlib.sha1(ids[i].encode()).hexdigest()[:16],
                       "id": ids[i], "published_at": dated[ids[i]], "원천": "fineweb2",
                       "샤드": base, "text500": head[:TEXT_STORE_CHARS],
                       "text_sha16": hashlib.sha256(
                           head[:TEXT_STORE_CHARS].encode()).hexdigest()[:16]}
                if names_hit:
                    row["names"] = names_hit
                    row["routes"] = {"text": names_hit, "query": []}
                    ent_out.append(row)
                    n_ent += 1
                else:
                    kws = [k for k in KEYWORDS if k in head]
                    if kws:
                        row["kw"] = kws
                        bg_out.append(row)
                        n_bg += 1
        with gzip.open(os.path.join(parts_dir, base + ".ent.jsonl.gz"), "wt",
                       encoding="utf-8") as f:
            for r in ent_out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with gzip.open(os.path.join(parts_dir, base + ".bg.jsonl.gz"), "wt",
                       encoding="utf-8") as f:
            for r in bg_out:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        st["done"].append(base)
        st["counts"][base] = {"행": n_rows, "dated": n_dated, "diff>0제외": n_diffpos,
                              "명중": n_hit, "개체": n_ent, "배경": n_bg}
        jdump(st, st_path)
        say("fineweb %s: 행 %d · dated %d · 명중 %d · 개체 %d · 배경 %d (%.0fs)" %
            (base, n_rows, n_dated, n_hit, n_ent, n_bg, time.time() - t_start))
    say("fineweb: 25 샤드 전량 완주")
    return True


# ── embed: §1-4 선택 + 임베딩 ────────────────────────────────────────────

def _even_pick(items, cap):
    """(published_at, key) 정렬 뒤 등간격 — 시간 덮개 보존 (§1-4)."""
    items = sorted(items, key=lambda r: (r["published_at"], r["key"]))
    if len(items) <= cap:
        return items
    idx = sorted({round(i * (len(items) - 1) / (cap - 1)) for i in range(cap)})
    return [items[i] for i in idx]


def _load_work_rows():
    ent, bg = [], []
    for fp in [os.path.join(WORK, "fresh_ent.jsonl.gz")] + sorted(
            glob.glob(os.path.join(WORK, "fw_parts", "*.ent.jsonl.gz"))):
        if os.path.exists(fp):
            with gzip.open(fp, "rt", encoding="utf-8") as fh:
                for line in fh:
                    ent.append(json.loads(line))
    for fp in [os.path.join(WORK, "fresh_bg.jsonl.gz")] + sorted(
            glob.glob(os.path.join(WORK, "fw_parts", "*.bg.jsonl.gz"))):
        if os.path.exists(fp):
            with gzip.open(fp, "rt", encoding="utf-8") as fh:
                for line in fh:
                    bg.append(json.loads(line))
    return ent, bg


def stage_embed():
    wait_load()
    ent, bg = _load_work_rows()
    say("embed: 개체 행 %d · 배경 행 %d 적재" % (len(ent), len(bg)))
    # ── 개체 선택 (§1-4): 신선 전량(상한 20,000/개체당 400) · 과거 개체당 150 ──
    fresh = [r for r in ent if r["원천"] != "fineweb2"]
    past = [r for r in ent if r["원천"] == "fineweb2"]
    sel_keys = set()
    if len(fresh) <= CAP_FRESH_TOTAL:
        sel_keys.update(r["key"] for r in fresh)
    else:
        by_e = {}
        for r in fresh:
            for nm in r["names"]:
                by_e.setdefault(nm, []).append(r)
        for nm, rs in sorted(by_e.items()):
            for r in _even_pick(rs, CAP_FRESH_PER_ENT):
                sel_keys.add(r["key"])
    by_e = {}
    for r in past:
        for nm in r["names"]:
            by_e.setdefault(nm, []).append(r)
    for nm, rs in sorted(by_e.items()):
        for r in _even_pick(rs, CAP_PAST_PER_ENT):
            sel_keys.add(r["key"])
    # ── 배경 선택: 월별 40 · 합 8,000 (순위-우선 라운드로빈 — 결정론) ──
    by_m = {}
    for r in bg:
        by_m.setdefault(r["published_at"][:7], []).append(r)
    ranked = {m: sorted(rs, key=lambda r: (r["published_at"], r["key"]))[:CAP_BG_PER_MONTH]
              for m, rs in by_m.items()}
    bg_sel = []
    for rank in range(CAP_BG_PER_MONTH):
        for m in sorted(ranked):
            if rank < len(ranked[m]):
                bg_sel.append(ranked[m][rank])
            if len(bg_sel) >= CAP_BG_TOTAL:
                break
        if len(bg_sel) >= CAP_BG_TOTAL:
            break
    bg_sel_keys = {r["key"] for r in bg_sel}
    say("embed: 선택 — 개체 %d/%d · 배경 %d/%d" %
        (len(sel_keys), len(ent), len(bg_sel_keys), len(bg)))

    # ── 문서 파일 확정 (emb 행 번호 부여) ──
    def finalize(rows, selset, path):
        idx = 0
        texts = []
        with gzip.open(path, "wt", encoding="utf-8") as f:
            for r in sorted(rows, key=lambda r: (r["published_at"], r["key"])):
                r = dict(r)
                if r["key"] in selset:
                    r["emb"] = idx
                    texts.append(r["text500"])
                    idx += 1
                else:
                    r["emb"] = -1
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        return texts

    # 중복 key 접기(원천 간 중복은 원리상 없음 — 안전망)
    ent_u = list({r["key"]: r for r in ent}.values())
    bg_u = list({r["key"]: r for r in bg}.values())
    texts_ent = finalize(ent_u, sel_keys, os.path.join(OUT, "docs_ent.jsonl.gz"))
    texts_bg = finalize(bg_u, bg_sel_keys, os.path.join(OUT, "docs_bg.jsonl.gz"))

    # ── 임베딩 (512 체크포인트) ──
    def embed_ck(texts, tag):
        ckdir = os.path.join(WORK, "emb_%s" % tag)
        os.makedirs(ckdir, exist_ok=True)
        outp = os.path.join(OUT, "emb_%s.npz" % tag)
        n = len(texts)
        chunks = (n + 511) // 512
        for c in range(chunks):
            fp = os.path.join(ckdir, "%05d.npy" % c)
            if os.path.exists(fp):
                continue
            wait_load()
            arr = dfield.embed_texts(texts[c * 512:(c + 1) * 512], threads=4, log=None)
            np.save(fp, arr)
            say("  embed %s %d/%d" % (tag, c + 1, chunks))
        parts = [np.load(os.path.join(ckdir, "%05d.npy" % c)) for c in range(chunks)]
        emb = np.concatenate(parts, axis=0) if parts else np.zeros((0, dfield.EMB_DIM),
                                                                  dtype=np.float32)
        np.savez_compressed(outp, emb=emb.astype(np.float32))
        return emb.shape

    t0 = time.time()
    sh_e = embed_ck(texts_ent, "ent")
    sh_b = embed_ck(texts_bg, "bg")
    jdump({"개체": {"행": len(ent_u), "임베딩": list(sh_e)},
           "배경": {"행": len(bg_u), "임베딩": list(sh_b)},
           "분": (time.time() - t0) / 60,
           "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S")},
          os.path.join(WORK, "embed_meta.json"))
    say("embed: 개체 %s · 배경 %s · %.1f분" % (sh_e, sh_b, (time.time() - t0) / 60))


# ── 특징 · CV 엔진 (§5) ─────────────────────────────────────────────────

def build_disc_raw(field, records, tau, sigma=None):
    """레코드별 담론 원료: {스칼라4, vec(896)|None}. sigma: 이름→이름(위약 순열)."""
    sbg_cache = {}
    out = []
    stamps = []
    for r in records:
        nm = sigma[r["name"]] if sigma else r["name"]
        T0 = r["T0"]
        vec, m_s = field.s_disc(nm, T0, tau)
        sov, m_v = field.sov(nm, T0, tau)
        if T0 not in sbg_cache:
            sbg_cache[T0] = field.s_bg(T0, tau)
        bgv, _m_b = sbg_cache[T0]
        cosv = 0.0
        if vec is not None and bgv is not None:
            na, nb = np.linalg.norm(vec), np.linalg.norm(bgv)
            if na > 0 and nb > 0:
                cosv = float(np.dot(vec.astype(np.float64), bgv.astype(np.float64))
                             / (na * nb))
        out.append({"scal": [math.log1p(m_s["W_pre"]),
                             (sov if sov is not None else 0.0),
                             math.log1p(m_s["n_pre"]),
                             1.0 if vec is not None else 0.0,
                             cosv],
                    "vec": vec, "n_pre": m_s["n_pre"]})
        stamps.append({"rid": r["rid"], "ent": m_s["누수관문(L0-3)"],
                       "bg": m_v["누수관문(L0-3)"]["bg"]})
    return out, stamps


def make_folds(clusters, seed):
    rs = np.random.RandomState(seed)
    perm = rs.permutation(len(clusters))
    chunks = np.array_split(perm, KFOLD)
    return [set(clusters[i] for i in ch) for ch in chunks]


def _pca_fit(vecs, k=8):
    """훈련 접힘 vec(존재분)로 PCA — 결정론(성분 부호 고정)."""
    present = [v for v in vecs if v is not None]
    if len(present) < 2:
        return None
    M = np.stack([v.astype(np.float64) for v in present])
    mu = M.mean(axis=0)
    _u, _s, Vt = np.linalg.svd(M - mu, full_matrices=False)
    comps = Vt[:k]
    for i in range(comps.shape[0]):
        j = int(np.argmax(np.abs(comps[i])))
        if comps[i, j] < 0:
            comps[i] = -comps[i]
    return mu, comps


def _pca_apply(pca, vec, k=8):
    if pca is None or vec is None:
        return [0.0] * k
    mu, comps = pca
    p = (vec.astype(np.float64) - mu) @ comps.T
    out = [0.0] * k
    for i in range(min(k, p.shape[0])):
        out[i] = float(p[i])
    return out


def _ridge(Xtr, ytr, Xte, lam):
    mx, sx = Xtr.mean(axis=0), Xtr.std(axis=0)
    sx[sx == 0] = 1.0
    Ztr, Zte = (Xtr - mx) / sx, (Xte - mx) / sx
    my = ytr.mean()
    A = Ztr.T @ Ztr + lam * np.eye(Ztr.shape[1])
    w = np.linalg.solve(A, Ztr.T @ (ytr - my))
    return Zte @ w + my


def _fit_predict(X_by_item, y, items_tr, items_te, seed, ofold):
    """내부 5접힘으로 λ 고르고(동률 낮은 λ) 시험 예측."""
    Xtr = np.array([X_by_item[i] for i in items_tr])
    ytr = np.array([y[i] for i in items_tr])
    rs = np.random.RandomState(seed * 7919 + ofold)
    perm = rs.permutation(len(items_tr))
    chunks = np.array_split(perm, KFOLD)
    best_lam, best_mae = None, None
    for lam in LAMBDAS:
        errs = []
        for ch in chunks:
            te = set(int(x) for x in ch)
            tr = [k for k in range(len(items_tr)) if k not in te]
            if not tr or not te:
                continue
            pred = _ridge(Xtr[tr], ytr[tr], Xtr[sorted(te)], lam)
            errs.extend(np.abs(pred - ytr[sorted(te)]))
        mae = float(np.mean(errs)) if errs else float("inf")
        if best_mae is None or mae < best_mae - 1e-12:
            best_mae, best_lam = mae, lam
    Xte = np.array([X_by_item[i] for i in items_te])
    pred = _ridge(Xtr, ytr, Xte, best_lam)
    return pred, best_lam


def run_arm(records, y, arm, disc_raw, seeds=SEEDS):
    """한 팔의 씨앗별 항목 오차. arm ∈ {'a','b','c'} · disc_raw: build_disc_raw 결과(τ 고정).
    반환 err[seed][item]."""
    n = len(records)
    clusters = sorted({r["name"] for r in records})
    cl_of = [r["name"] for r in records]
    errs = np.full((len(seeds), n), np.nan)
    lam_used = []
    for si, seed in enumerate(seeds):
        folds = make_folds(clusters, seed)
        for ofold, te_cl in enumerate(folds):
            items_te = [i for i in range(n) if cl_of[i] in te_cl]
            items_tr = [i for i in range(n) if cl_of[i] not in te_cl]
            if not items_te or len(items_tr) < 10:
                continue
            # 특징 조립(PCA 는 훈련 접힘에서만 — §5)
            if arm == "a":
                X = {i: records[i]["curve_feats"] for i in range(n)}
            else:
                pca = _pca_fit([disc_raw[i]["vec"] for i in items_tr]) \
                    if disc_raw else None
                X = {}
                for i in range(n):
                    d = disc_raw[i]["scal"] + _pca_apply(pca, disc_raw[i]["vec"])
                    X[i] = (records[i]["curve_feats"] + d) if arm == "b" else d
            pred, lam = _fit_predict(X, y, items_tr, items_te, seed, ofold)
            lam_used.append(lam)
            for k, i in enumerate(items_te):
                errs[si, i] = abs(pred[k] - y[i])
    return errs, lam_used


def item_err(errs):
    return np.nanmean(errs, axis=0)          # 씨앗 평균 |ŷ−y|


def cluster_boot_se(d, cl_of, B=B_BOOT, seed=BOOT_SEED):
    clusters = sorted(set(cl_of))
    idx_by = {c: [i for i, x in enumerate(cl_of) if x == c] for c in clusters}
    rs = np.random.RandomState(seed)
    means = np.empty(B)
    C = len(clusters)
    for b in range(B):
        pick = rs.randint(0, C, C)
        rows = [i for p in pick for i in idx_by[clusters[p]]]
        means[b] = np.mean(d[rows])
    return float(np.std(means, ddof=1))


# ── mde: §4 ─────────────────────────────────────────────────────────────

def stage_mde():
    wait_load()
    probe = direction_probe()
    say("방향 탐침: %s" % json.dumps(probe, ensure_ascii=False))
    if not probe["통과"]:
        say("🔴 방향 탐침 실패 — 측정 없이 중단")
        raise SystemExit(2)
    state = jload(os.path.join(WORK, "state1019.json"))
    records = state["records"]
    y = np.array([r["y"] for r in records])
    field = dfield.DiscourseField.load(OUT)
    say("장 적재: 개체 이름 %d · 배경 행 %d" % (len(field.by_name), len(field.bg_rows)))

    t0 = time.time()
    err_a, lam_a = run_arm(records, y, "a", None)
    e_a = item_err(err_a)
    mae_a = float(np.nanmean(e_a))
    say("ⓐ 곡선만: MAE %.4f (%.0fs)" % (mae_a, time.time() - t0))

    clusters = sorted({r["name"] for r in records})
    disc_true, stamps = build_disc_raw(field, records, TAU_CANON)
    n_leak = len(stamps)
    min_margin = min(int(s["ent"]["여유일"]) for s in stamps if s["ent"]["여유일"] is not None) \
        if any(s["ent"]["여유일"] is not None for s in stamps) else None
    say("담론 특징(실제 τ90) 원료 계산 — 누수 스탬프 %d 건 전부 통과 · 최소 여유 %s" %
        (n_leak, min_margin))

    deltas = {}
    for pseed in PERM_SEEDS:
        rs = np.random.RandomState(pseed)
        ds = []
        for p in range(PERM_P):
            perm = rs.permutation(len(clusters))
            sigma = {clusters[i]: clusters[int(perm[i])] for i in range(len(clusters))}
            disc_p, _ = build_disc_raw(field, records, TAU_CANON, sigma=sigma)
            err_b, _l = run_arm(records, y, "b", disc_p)
            mae_bp = float(np.nanmean(item_err(err_b)))
            ds.append(mae_a - mae_bp)
            if p % 5 == 0:
                say("  위약 시드 %d · %d/%d (Δ_perm %.4f · %.0fs)" %
                    (pseed, p + 1, PERM_P, ds[-1], time.time() - t0))
        deltas[pseed] = ds
    all_d = deltas[PERM_SEEDS[0]] + deltas[PERM_SEEDS[1]]
    sd1 = float(np.std(deltas[PERM_SEEDS[0]], ddof=1))
    sd2 = float(np.std(deltas[PERM_SEEDS[1]], ddof=1))
    sd_pool = float(np.std(all_d, ddof=1))
    J = abs(sd1 - sd2) / math.sqrt(2)
    plc = {"Δ_perm": {str(k): v for k, v in deltas.items()},
           "SD_시드별": {str(PERM_SEEDS[0]): sd1, str(PERM_SEEDS[1]): sd2},
           "SD_합동40": sd_pool, "J": J, "MAE_ⓐ": mae_a,
           "위약중앙값": float(np.median(all_d)),
           "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    plc_path = os.path.join(OUT, "placebo1019.json")
    jdump(plc, plc_path)
    plc_sha = sha16(plc_path)

    mde = mde_of(sd_pool, J)
    aim = AIM_FRAC * state["SD_cl(y)"]
    lane = None
    try:
        stamp = assert_mde(mde, aim, plc_sha)
        lane = "판정"
        say("MDE 관문 통과 — [판정] 레인: %s" % json.dumps(stamp, ensure_ascii=False))
    except MdeUnderpowered as e:
        lane = "측정"
        stamp = {"MdeUnderpowered": str(e)[:400]}
        say("MDE 미달 — [측정] 강등 등록: %s" % str(e)[:200])
    mst = {"레인": lane, "MDE_사전": mde, "겨냥": aim, "SD_perm": sd_pool, "J": J,
           "MAE_ⓐ": mae_a, "위약sha16": plc_sha, "스탬프": stamp,
           "방향탐침": probe, "누수_최소여유일": min_margin,
           "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    jdump(mst, os.path.join(WORK, "mde_state.json"))
    say("mde: SD_perm %.4f · J %.4f · MDE %.4f · 겨냥 %.4f → [%s]" %
        (sd_pool, J, mde, aim, lane))


# ── validate: §5 ────────────────────────────────────────────────────────

def stage_validate():
    wait_load()
    state = jload(os.path.join(WORK, "state1019.json"))
    mst = jload(os.path.join(WORK, "mde_state.json"))
    if mst is None:
        say("🔴 mde 단계 미완 — 순서 위반(§4) — 중단")
        raise SystemExit(2)
    records = state["records"]
    y = np.array([r["y"] for r in records])
    cl_of = [r["name"] for r in records]
    field = dfield.DiscourseField.load(OUT)

    err_a, lam_a = run_arm(records, y, "a", None)
    e_a = item_err(err_a)
    res = {"n": len(records), "n_클러스터": len(set(cl_of)),
           "레인": mst["레인"], "MDE_사전": mst["MDE_사전"], "겨냥": mst["겨냥"]}
    per_tau = {}
    leak_agg = None
    for tau in TAUS:
        disc, stamps = build_disc_raw(field, records, tau)
        if tau == TAU_CANON:
            margins = [int(s["ent"]["여유일"]) for s in stamps
                       if s["ent"]["여유일"] is not None]
            leak_agg = {"건": len(stamps), "위반": 0,
                        "최소여유일": min(margins) if margins else None,
                        "대표스탬프": stamps[0]["ent"] if stamps else None}
        err_b, lam_b = run_arm(records, y, "b", disc)
        err_c, lam_c = run_arm(records, y, "c", disc)
        e_b, e_c = item_err(err_b), item_err(err_c)
        d_ab = e_a - e_b
        d_ca = e_c - e_a
        delta = float(np.mean(d_ab))
        se_cl = cluster_boot_se(d_ab, cl_of)
        d_seed = [float(np.nanmean(err_a[s] - err_b[s])) for s in range(len(SEEDS))]
        Jm = float(np.std(d_seed, ddof=1) / math.sqrt(len(SEEDS)))
        mde_m = mde_of(se_cl, Jm)
        per_tau[tau] = {
            "MAE_ⓐ": float(np.nanmean(e_a)), "MAE_ⓑ": float(np.nanmean(e_b)),
            "MAE_ⓒ": float(np.nanmean(e_c)),
            "Δ(ⓐ−ⓑ)": delta, "SE^cl": se_cl, "J_실측": Jm, "MDE_실측": mde_m,
            "여유": delta - mde_m, "게이트(Δ>MDE)": bool(gate_improve(delta, mde_m)),
            "Δ_ca(ⓒ−ⓐ)": float(np.mean(d_ca)),
            "SE^cl_ca": cluster_boot_se(d_ca, cl_of),
            "λ_최빈": {"ⓑ": max(set(lam_b), key=lam_b.count) if lam_b else None,
                       "ⓒ": max(set(lam_c), key=lam_c.count) if lam_c else None},
        }
        say("τ=%d: MAEⓐ %.4f ⓑ %.4f ⓒ %.4f · Δ %.4f ± SE %.4f · MDE %.4f · 게이트 %s" %
            (tau, per_tau[tau]["MAE_ⓐ"], per_tau[tau]["MAE_ⓑ"], per_tau[tau]["MAE_ⓒ"],
             delta, se_cl, mde_m, per_tau[tau]["게이트(Δ>MDE)"]))
    # 자료 탐침(v5.3-3) — 정본 τ 게이트의 실측 문턱으로
    thr = per_tau[TAU_CANON]["MDE_실측"]
    probe_bad = {"㉰악화극값참": int(gate_improve(-2 * thr, thr) is True),
                 "㉱개선극값거짓": int(gate_improve(+2 * thr, thr) is False),
                 "퇴화문턱": bool(thr <= 0)}
    # τ 뒤집힘 지점 (L1-3 게재 의무)
    taus_sorted = list(TAUS)
    flips = []
    for i in range(len(taus_sorted) - 1):
        a, b = taus_sorted[i], taus_sorted[i + 1]
        if (per_tau[a]["Δ(ⓐ−ⓑ)"] > 0) != (per_tau[b]["Δ(ⓐ−ⓑ)"] > 0):
            flips.append("Δⓑ 부호 뒤집힘 τ %d→%d" % (a, b))
        if (per_tau[a]["MAE_ⓑ"] < per_tau[a]["MAE_ⓒ"]) != \
           (per_tau[b]["MAE_ⓑ"] < per_tau[b]["MAE_ⓒ"]):
            flips.append("ⓑ/ⓒ 순서 뒤집힘 τ %d→%d" % (a, b))
    res.update({"τ표": {str(k): v for k, v in per_tau.items()},
                "뒤집힘": flips or ["없음(격자 안 부호·순서 불변)"],
                "자료탐침": probe_bad, "누수집계(τ90)": leak_agg,
                "담론덮개율": {
                    "V3중_사전문서≥1": int(sum(1 for r in records
                                          if field.by_name.get(r["name"]) and
                                          any(p < dt.date.fromisoformat(r["T0"])
                                              for (p, _k, _e) in field.by_name[r["name"]]))),
                    "V3": len(records)},
                "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S")})
    jdump(res, os.path.join(OUT, "valid_abc.json"))
    say("validate 저장 — 레인 [%s] · 정본 τ90 게이트 %s · 여유 %.5f" %
        (mst["레인"], per_tau[TAU_CANON]["게이트(Δ>MDE)"], per_tau[TAU_CANON]["여유"]))


# ── grid: §7 격자 ───────────────────────────────────────────────────────

def month_ends(y0=2022, m0=1, y1=2026, m1=8):
    out = []
    y_, m_ = y0, m0
    while (y_, m_) <= (y1, m1):
        nxt = dt.date(y_ + (m_ // 12), (m_ % 12) + 1, 1)
        out.append(nxt - dt.timedelta(days=1))
        y_, m_ = nxt.year, nxt.month
    return out


def stage_grid():
    wait_load()
    field = dfield.DiscourseField.load(OUT)
    state = jload(os.path.join(WORK, "state1019.json"))
    mes = month_ends()
    names = sorted(field.by_name)
    say("grid: 이름 %d × 월말 %d × τ %d" % (len(names), len(mes), len(TAUS)))
    gpath = os.path.join(OUT, "grid_sov.jsonl.gz")
    n_cells = 0
    with gzip.open(gpath, "wt", encoding="utf-8") as f:
        for me in mes:
            # 배경 절단 1회/as_of — 스탬프 공유(같은 입력 집합 · 코드 주석 신고)
            bg_sel, bg_stamp = field._cut(field.bg_rows, me, "격자 bg as_of=%s" % me)
            Wb = {tau: sum(dfield.weight((me - p).days, tau) for (p, _k, _e) in bg_sel)
                  for tau in TAUS}
            for nm in names:
                sel, _st = field._cut(field.by_name[nm], me, "격자 e=%s as_of=%s" % (nm, me))
                if not sel:
                    continue
                row = {"개체": nm, "as_of": me.isoformat(), "n_pre": len(sel)}
                for tau in TAUS:
                    We = sum(dfield.weight((me - p).days, tau) for (p, _k, _e) in sel)
                    row["W_ent_%d" % tau] = We
                    row["SoV_%d" % tau] = (We / (We + Wb[tau])
                                           if (We + Wb[tau]) > 0 else None)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                n_cells += 1
    # 검증 T0 의 s_disc 벡터 (레코드 × τ)
    arrs = {}
    n_none = 0
    for r in state["records"]:
        for tau in TAUS:
            vec, _m = field.s_disc(r["name"], r["T0"], tau)
            if vec is None:
                n_none += 1
                continue
            arrs["%s|%d" % (r["rid"], tau)] = vec
    np.savez_compressed(os.path.join(OUT, "sdisc_T0.npz"), **arrs)
    jdump({"격자행": n_cells, "이름": len(names), "월말": len(mes),
           "sdisc_T0_키": len(arrs), "무벡터(레코드×τ)": n_none,
           "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S")},
          os.path.join(WORK, "grid_meta.json"))
    say("grid: 행 %d · sdisc_T0 키 %d · 무벡터 %d" % (n_cells, len(arrs), n_none))


# ── report ──────────────────────────────────────────────────────────────

def stage_report():
    state = jload(os.path.join(WORK, "state1019.json"))
    meta = {
        "사이클": 1019,
        "사다리": state["사다리"],
        "SD_cl(y)": state["SD_cl(y)"], "basis": state["basis"],
        "route": state["route"], "곡선_최소여유일": state["곡선_최소여유일"],
        "곡선_채움_합": state["곡선_채움_합"],
        "ledger_sha256": state["ledger_sha256"],
        "wiki_daily_sha16": state["wiki_daily_sha16"],
        "snapshot": jload(os.path.join(WORK, "snapshot_meta.json")),
        "fineweb": jload(os.path.join(WORK, "fineweb_state.json")),
        "embed": jload(os.path.join(WORK, "embed_meta.json")),
        "mde": jload(os.path.join(WORK, "mde_state.json")),
        "grid": jload(os.path.join(WORK, "grid_meta.json")),
        "emb_config_규약": sha16(os.path.join(
            "/Users/ax/wm_harvest/foundation/triples", "text_emb_qwen05b.config.json")),
        "코드sha256_16": {
            "runners/discourse_field1019.py": sha16(os.path.abspath(__file__)),
            "pretrain/discourse_field.py": sha16(os.path.join(
                REPO, "pretrain/discourse_field.py")),
            "pretrain/leak_guard.py": sha16(os.path.join(REPO, "pretrain/leak_guard.py")),
            "pretrain/mde_guard.py": sha16(os.path.join(REPO, "pretrain/mde_guard.py")),
        },
        "산출물sha256_16": {os.path.basename(p): sha16(p) for p in sorted(
            glob.glob(os.path.join(OUT, "*.json")) +
            glob.glob(os.path.join(OUT, "*.jsonl.gz")) +
            glob.glob(os.path.join(OUT, "*.npz")))},
        "끝시각": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    jdump(meta, os.path.join(OUT, "meta1019.json"))
    say("report: meta1019.json 저장")
    print(json.dumps({k: v for k, v in meta.items()
                      if k in ("사다리", "SD_cl(y)", "산출물sha256_16")},
                     ensure_ascii=False, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["probe", "denom", "snapshot", "fineweb", "embed",
                             "mde", "validate", "grid", "report"])
    ap.add_argument("--max-seconds", type=int, default=480)
    a = ap.parse_args()
    open_log()
    say("=== stage %s 시작 · load1 %.2f ===" % (a.stage, os.getloadavg()[0]))
    if a.stage == "probe":
        p = direction_probe()
        say(json.dumps(p, ensure_ascii=False))
        raise SystemExit(0 if p["통과"] else 2)
    elif a.stage == "denom":
        stage_denom()
    elif a.stage == "snapshot":
        stage_snapshot()
    elif a.stage == "fineweb":
        done = stage_fineweb(a.max_seconds)
        raise SystemExit(0 if done else 3)
    elif a.stage == "embed":
        stage_embed()
    elif a.stage == "mde":
        stage_mde()
    elif a.stage == "validate":
        stage_validate()
    elif a.stage == "grid":
        stage_grid()
    elif a.stage == "report":
        stage_report()


if __name__ == "__main__":
    main()
