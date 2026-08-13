#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""956 --- 정본을 **자①** 로 옮기고 `K` 를 판정에서 뗀다.

🔴 왜(티처 #94 C1·C2·C3): 955 의 정본 `자② D_문서^{K=21}` 은
  ① 근거가 반증된 상수 `K=21` 에 매달려 있고(**자①에서 같은 URL 이 최대 478번 살아남는다** ·
     `collection ≠ 크롤`),
  ② 그 위의 「강함」은 **사후에 고른 여덟**에서 나왔으며,
  ③ 그 여덟은 **실질 둘**이다.
자①은 정규화를 안 하므로 **뭉침 병이 원리상 없고 절단도 자유파라미터도 안 쓴다.**

🔴 그리고 티처 #94 M1 --- 955 의 「배선 24/24」는 독립이 아니었다(FineWeb 쪽 해시를
954 의 npz 에서 **그대로 읽었다**). 956 은 **받은 parquet 에서 키를 처음부터 다시 계산하고**
954 의 npz 는 **재현 대상(W8)** 으로만 쓴다.

사전등록: `docs/prereg_956_ruler1.md` (커밋 efc82effc · 측정 전 · 이 파일 하나)

씀:
    python3 runners/dupe956_ruler1.py extract      # (ㄴ) 받은 parquet 의 url 열 전량 → scratch npz
    python3 runners/dupe956_ruler1.py analyze      # 측정·판정
"""
import argparse
import glob
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from runners.dupe954_hplt_scan import h64, norm_url  # noqa: E402

SCRATCH954 = pathlib.Path("/Users/ax/wm_harvest/954")
SCAN = SCRATCH954 / "scan"          # HPLT 464 shard npz (954)
FWS = SCRATCH954 / "fw"             # FineWeb 행군 층화 표본 npz (954) = (ㄱ) 판
RECV = pathlib.Path("/Users/ax/wm_harvest/fineweb2_ko")     # 955 가 받는 중인 전량
FULL = pathlib.Path("/Users/ax/wm_harvest/956/full")        # (ㄴ) 판 url 키 저장소
FULLT = pathlib.Path("/Users/ax/wm_harvest/956/fulltext")   # (ㄴ) 판 본문 키 저장소
HPLT_DIR = REPO / "data/ingest/hplt_ko"

NAMES = ["%03d_%05d.parquet" % (g, k) for g in range(5) for k in range(5)]
KS = [1, 2, 5, 10, 21, 50, 100, 478, 503, 1000]     # 🔴 사전등록 §6 부칙 2′(나) --- 목록을 안 자른다
K_PAIR = 21                                          # 자②의 하한을 만드는 절단(정본 아님)


# ─────────────────────────────────────────────────── (ㄴ) 받은 parquet → 키

def extract_text(force=False):
    """🔴 **사전등록 §7 은 이것을 「안 한다」로 적었다. 그런데 했다.**

    사유: §7 이 댄 근거는 *「`text` 열은 코퍼스 105GB 를 흘려야 한다」* 였는데
    **실측이 그 추정을 뒤집었다** --- 88,000 행/초 · 전량 ≈ 11.5분이다.
    🔴 **「안 한다」를 「했다」로 바꾸는 것은 판정을 못 뒤집는다** --- 판정 규칙(§6)은
    안 바뀌었고 「강함」의 (나)는 이미 거짓이다. 바뀌는 것은 부칙 2′(다)의 **분모가
    같아진다**는 것뿐이고, **(ㄱ) 값도 그대로 같이 싣는다**.
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    FULLT.mkdir(parents=True, exist_ok=True)
    md5 = hashlib.md5
    done = []
    for name in NAMES:
        src = RECV / name
        out = FULLT / (name.replace(".parquet", ".npz"))
        if not src.exists():
            continue
        if out.exists() and not force:
            done.append(name)
            continue
        t0 = time.time()
        pf = pq.ParquetFile(src)
        n = pf.metadata.num_rows
        hed_h = np.empty(n, dtype=np.uint64)
        txt_h = np.empty(n, dtype=np.uint64)
        i = 0
        for b in pf.iter_batches(batch_size=32768, columns=["text"]):
            for t in pc.cast(b.column("text"), "binary").to_pylist():
                t = t or b""
                s = t.strip()
                hed_h[i] = int.from_bytes(md5(
                    s[:800].decode("utf-8", "ignore")[:200].encode("utf-8")
                ).digest()[:8], "little")
                txt_h[i] = int.from_bytes(md5(t).digest()[:8], "little")
                i += 1
        assert i == n, "행 수가 메타와 다르다: %d != %d" % (i, n)
        tmp = out.with_name(out.stem + ".tmp.npz")
        np.savez(tmp, hed_h=hed_h, txt_h=txt_h)
        os.replace(tmp, out)
        done.append(name)
        print("본문추출 %s · 행 %d · %.1fs" % (name, n, time.time() - t0), flush=True)
    return done


def extract(force=False):
    """🔴 받은 parquet 의 `url` 열을 **전량** 읽어 자①·자② 키를 **다시 계산**한다.

    954 의 npz 를 **안 읽는다**(티처 #94 M1). 파일 단위로 이어서 돌 수 있다.
    """
    import pyarrow.parquet as pq
    FULL.mkdir(parents=True, exist_ok=True)
    md5 = hashlib.md5
    done = []
    for name in NAMES:
        src = RECV / name
        out = FULL / (name.replace(".parquet", ".npz"))
        if not src.exists():
            continue
        if out.exists() and not force:
            done.append(name)
            continue
        t0 = time.time()
        pf = pq.ParquetFile(src)
        n = pf.metadata.num_rows
        url_h = np.empty(n, dtype=np.uint64)
        urn_h = np.empty(n, dtype=np.uint64)
        i = 0
        for b in pf.iter_batches(batch_size=131072, columns=["url"]):
            us = b.column("url").to_pylist()
            for u in us:
                u = u or ""
                url_h[i] = int.from_bytes(md5(u.encode("utf-8")).digest()[:8], "little")
                urn_h[i] = int.from_bytes(md5(norm_url(u).encode("utf-8")).digest()[:8], "little")
                i += 1
        assert i == n, "행 수가 메타와 다르다: %d != %d" % (i, n)
        # 🔴 `np.savez` 는 이름이 `.npz` 로 안 끝나면 **덧붙인다**. 그래서 임시 이름도
        #    `.npz` 로 끝나게 만든다(954 의 `.part` 사고와 같은 종류의 함정이다).
        tmp = out.with_name(out.stem + ".tmp.npz")
        np.savez(tmp, url_h=url_h, urn_h=urn_h)
        os.replace(tmp, out)
        done.append(name)
        print("추출 %s · 행 %d · %.1fs" % (name, n, time.time() - t0), flush=True)
    return done


# ─────────────────────────────────────────────────── 적재

def load_concat(d, key, pat):
    fs = sorted(d.glob(pat))
    parts = [np.load(p, allow_pickle=True)[key] for p in fs]
    return (np.concatenate(parts) if parts else np.zeros(0, dtype=np.uint64)), [p.name for p in fs]


def load_per_file(d, key, pat):
    """파일 단위 잭나이프(⓪-가 검출력 줄)를 위해 **파일별로** 돌려준다."""
    out = []
    for p in sorted(d.glob(pat)):
        out.append((p.name, np.load(p, allow_pickle=True)[key]))
    return out


# ─────────────────────────────────────────────────── 한 자

def measure(label, hp, fw, want_curve=False):
    """🔴 사전등록 §2-A 표 그대로 --- **한 줄에 정의 하나 · 분자와 분모를 한 줄에.**"""
    t0 = time.time()
    hset, hcnt = np.unique(hp, return_counts=True)
    fset, fcnt = np.unique(fw, return_counts=True)
    inter = np.intersect1d(hset, fset, assume_unique=True)
    mult_h = hcnt[np.searchsorted(hset, inter)].astype(np.int64)
    mult_f = fcnt[np.searchsorted(fset, inter)].astype(np.int64)
    nH, nF = int(len(hp)), int(len(fw))
    nHk, nFk = int(len(hset)), int(len(fset))
    nI = int(len(inter))
    fw_doc_hit = int(mult_f.sum())
    hp_doc_hit = int(mult_h.sum())

    out = {
        "자": label,
        "분모 ① HPLT 문서": nH,
        "분모 ② FineWeb 문서": nF,
        "분모 ③ HPLT 서로 다른 키": nHk,
        "분모 ④ FineWeb 서로 다른 키": nFk,
        "분자 ⓐ 교집합(서로 다른 키)": nI,
        "분자 ⓑ 맞은 FineWeb 문서": fw_doc_hit,
        "분자 ⓒ 맞은 HPLT 문서": hp_doc_hit,
        "🔴 D_문서 = ⓑ ÷ ②": round(fw_doc_hit / nF, 6) if nF else None,
        "🔴 D_키 = ⓐ ÷ ④": round(nI / nFk, 6) if nFk else None,
        "E_문서 = ⓒ ÷ ①": round(hp_doc_hit / nH, 6) if nH else None,
        "E_키 = ⓐ ÷ ③": round(nI / nHk, 6) if nHk else None,
        "다중도 --- 교집합 키당 HPLT 문서(평균)": round(float(mult_h.mean()), 4) if nI else None,
        "다중도 --- 교집합 키당 HPLT 문서(최대)": int(mult_h.max()) if nI else None,
        "다중도 --- 코퍼스 전체 최대(이 자의 천장)": int(hcnt.max()) if nHk else None,
        "다중도 --- 코퍼스 전체 평균(= ① ÷ ③)": round(nH / nHk, 4) if nHk else None,
        "반대 방향 --- HPLT − FineWeb(키)": nHk - nI,
        "반대 방향 --- FineWeb − HPLT(키)": nFk - nI,
        "초": round(time.time() - t0, 1),
        "통과": bool(nI <= min(nHk, nFk) and fw_doc_hit <= nF and hp_doc_hit <= nH
                   and nI <= fw_doc_hit and nI <= hp_doc_hit),
    }
    if want_curve:
        cur = {}
        for K in KS:
            m = mult_h <= K
            cur["K<=%d" % K] = {
                "분자 = 다중도<=K 인 교집합 키에 걸린 FineWeb 문서": int(mult_f[m].sum()),
                "분모 = FineWeb 문서": nF,
                "🔴 D_문서^K": round(float(mult_f[m].sum()) / nF, 6),
                "통과": bool(int(mult_f[m].sum()) <= fw_doc_hit),
            }
        cur["K=∞(절단 없음)"] = {
            "분자 = 맞은 FineWeb 문서": fw_doc_hit,
            "분모 = FineWeb 문서": nF,
            "🔴 D_문서^K": round(fw_doc_hit / nF, 6),
            "통과": True,
        }
        out["🔴 절단 곡선(전량 --- 목록을 안 자른다)"] = cur
    return out, (hset, hcnt, inter, mult_h)


def _in_sorted(a, hset):
    """`np.isin` 대신 정렬된 집합에 대한 이분 탐색(34M × 60M 이라 자를 고른다)."""
    if len(hset) == 0:
        return np.zeros(len(a), dtype=bool)
    idx = np.searchsorted(hset, a)
    np.clip(idx, 0, len(hset) - 1, out=idx)
    return hset[idx] == a


def jackknife_files(per_file_fw, hset):
    """🔴 파일 단위 잭나이프 --- 티처 #94 M4('군집 표본에 iid 자를 댄 것') 를 안 되풀이한다.

    분모가 「받은 N 파일」이면 **파일이 군집**이다. 파일 하나씩 빼고 D 를 다시 내
    잭나이프 SE 를 낸다. 이항 SE 를 쓰지 않는다.
    """
    if len(per_file_fw) < 2:
        return {"🔴 못 쟀다": "파일이 둘 미만이라 잭나이프가 원리상 안 선다(조항 59)",
                "파일 수": len(per_file_fw), "통과": False}
    hits, tots = [], []
    for _name, arr in per_file_fw:
        m = _in_sorted(arr, hset)
        hits.append(int(m.sum()))
        tots.append(int(len(arr)))
    H, T = float(sum(hits)), float(sum(tots))
    n = len(hits)
    theta = H / T
    reps = [(H - hits[i]) / (T - tots[i]) for i in range(n)]
    mbar = sum(reps) / n
    se = (float(n - 1) / n * sum((r - mbar) ** 2 for r in reps)) ** 0.5
    return {
        "자": "자① D_문서",
        "군집 = 파일": n,
        "전체 D": round(theta, 6),
        "잭나이프 평균": round(mbar, 6),
        "🔴 잭나이프 SE": round(se, 6),
        "🔴 가를 수 있는 최소 효과(= 2 × SE)": round(2 * se, 6),
        "파일별 D": [{"파일": per_file_fw[i][0], "분자 = 맞은 문서": hits[i],
                   "분모 = 문서": tots[i], "D": round(hits[i] / tots[i], 6)} for i in range(n)],
        "⚠ 뜻": ("이항 SE 가 아니다. 파일이 군집이므로 **파일을 하나씩 빼서** 잰다. "
               "🔴 **25/25 를 받으면 이것은 더 이상 표집오차가 아니다** --- 전수이므로 "
               "표집오차가 0 이고, 이 수는 그때 **파일 사이의 이질성**을 재는 것이 된다. "
               "부분 수신일 때만 「남은 파일이 다르면 D 가 얼마나 움직일 수 있나」로 읽어라."),
        "통과": True,
    }


# ─────────────────────────────────────────────────── W8 · 표본 대 전량 배선

def w8_sample_vs_full():
    """🔴🔴 티처 #94 M1 을 갚는 자리.

    954 가 뜬 **행군 층화 표본**의 행을 **받은 로컬 parquet 에서 다시 읽어** 자① 키를
    새로 계산하고 954 의 npz 와 **바이트 동일**한지 본다.
    `고른 행군` 수로 `dupe954_fineweb.fetch_one` 의 `starts` 를 **역산**한다.
    """
    import pyarrow.parquet as pq
    md5 = hashlib.md5
    rows = []
    for name in NAMES:
        src = RECV / name
        npz = FWS / name.replace(".parquet", ".npz")
        meta = FWS / (name + ".json")
        if not (src.exists() and npz.exists() and meta.exists()):
            continue
        m = json.loads(meta.read_text(encoding="utf-8"))
        pf = pq.ParquetFile(src)
        nrg = pf.metadata.num_row_groups
        if nrg != int(m["전량 행군"]):
            rows.append({"파일": name, "🔴 못 쟀다": "행군 수가 954 메타와 다르다",
                         "받은 행군": nrg, "954 메타": m["전량 행군"], "통과": False})
            continue
        # 🔴🔴 `고른 행군` 수로 `(CS, CL)` 을 **역산**한다.
        #    954 의 `dupe954_fineweb.fetch_one` 은 `CS = 4` 를 하드코딩했는데, 🔴 **표본의
        #    44.2%(600,000행 · 6파일)는 그 코드가 낸 것이 아니다**(티처 #93 M1: 그 코드는
        #    저장소에 없다 · 그 파일들의 「요청 수 202」는 CS=4 로 원리상 못 낸다).
        #    → **CS 후보를 넓혀 찾는다.** 🔴 통과 조건(**바이트 동일 · 불일치 0**)은 안 바꿨다.
        ref = np.load(npz)["url_h"]
        best = None
        tried = []
        for CS in (1, 2, 4, 5, 10):
            idx = None
            for CL in range(1, 3000):
                starts = sorted(set(int(round(x))
                                    for x in np.linspace(0, max(nrg - CS, 0), CL)))
                cand = sorted({g for s0 in starts for g in range(s0, min(s0 + CS, nrg))})
                if len(cand) == int(m["고른 행군"]):
                    idx = cand
                    break
            if idx is None:
                continue
            got = []
            for gi in range(0, len(idx), CS):
                tb = pf.read_row_groups(idx[gi:gi + CS], columns=["url"])
                for u in tb.column("url").to_pylist():
                    got.append(int.from_bytes(
                        md5((u or "").encode("utf-8")).digest()[:8], "little"))
            g = np.array(got, dtype=np.uint64)
            same_len = bool(len(g) == len(ref))
            bad = int((g != ref[:len(g)]).sum()) if same_len else None
            tried.append({"CS": CS, "CL": CL, "행": int(len(g)), "불일치": bad})
            if same_len and bad == 0:
                best = {"CS": CS, "CL": CL, "행": int(len(g)), "불일치": 0}
                break
        rows.append({
            "파일": name,
            "954 표본 행": int(len(ref)),
            "954 메타의 요청 수": m.get("요청 수"),
            "🔴 맞은 (CS, CL)": best or "🔴 못 찾았다",
            "시도": tried,
            "🔴 불일치(자① url_h)": (best or {}).get("불일치", tried[-1]["불일치"] if tried else None),
            "통과": bool(best is not None),
        })
    ok = [r for r in rows if r.get("통과")]
    cs_used = {}
    for r in rows:
        b = r.get("🔴 맞은 (CS, CL)")
        if isinstance(b, dict):
            cs_used.setdefault("CS=%d" % b["CS"], []).append(r["파일"])
    return {
        "무엇": ("🔴 표본 대 전량 배선 --- 954 의 행군 표본을 **받은 로컬 parquet 에서 다시 읽어** "
               "자① 키를 새로 계산하고 954 npz 와 바이트 동일한지 본다(티처 #94 M1)"),
        "분자 = 통과한 파일": len(ok),
        "분모 = 대조한 파일": len(rows),
        "낱개": rows,
        "🔴🔴 어느 (CS) 가 맞았나 --- 티처 #93 M1 이 여기서 실측으로 풀린다": {
            "파일별 CS": {k: sorted(v) for k, v in sorted(cs_used.items())},
            "🔴 뜻": ("`dupe954_fineweb.py:132` 는 `CS = 4` 를 **하드코딩**했다. "
                   "그런데 표본의 44.2%(600,000행)를 낸 파일들은 **CS=1**(행군 낱개 100 · "
                   "요청 202 = 행군 100 + footer 2)로만 바이트 동일이 된다. "
                   "🔴 **티처 #93 M1(「그 표본을 만든 코드가 저장소에 없다」)이 참임이 "
                   "실측으로 확인되고, 동시에 그 표본의 「어느 행군이었나」가 복원됐다.** "
                   "코드는 여전히 없지만 **선택은 이제 재현 가능하다**"),
        },
        "🔴 뜻": ("통과하면 ① 받은 파일과 Range 표본이 **같은 자료**이고 "
               "② 내 해시 배선이 954 와 **같다**. 그래서 (ㄴ) 전량 판의 수를 (ㄱ) 표본 판과 "
               "견줄 수 있다"),
        "⚠ 자를 안 바꿨다": ("통과 조건은 **바이트 동일 · 불일치 0** 그대로다. 넓힌 것은 "
                     "**내 재구성의 탐색 공간(CS 후보)** 이지 판정선이 아니다"),
        "통과": bool(rows and all(r.get("통과") for r in rows)),
    }


# ─────────────────────────────────────────────────── 심은 키 C · N

def probe_c(nshard=3):
    """🔴🔴 티처 #94 M3 --- **C2 를 실제로 잡는** 심은 키.

    955 의 U 는 *「자②가 `u` 와 `u?probe` 를 **같은 키로 보면 통과**」* 였다 ---
    **병을 재현하고 초록을 찍는다.** C 는 방향이 반대다:

      HPLT 안에서 **원 URL 이 다르고**(쿼리의 문서 번호만 다르다) **정규화하면 같아지고**
      **본문도 다른** 실제 문서 쌍을 찾아, 자가 그 둘을 **한 키로 뭉치면 붉다**.
    """
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    t0 = time.time()
    shards = sorted(HPLT_DIR.glob("train-*.parquet"))[:nshard]
    found = None
    ngroup = 0
    nrows = 0
    for sp in shards:
        pf = pq.ParquetFile(sp)
        for b in pf.iter_batches(batch_size=65536, columns=["u", "text"]):
            us = b.column("u").to_pylist()
            ts = pc.cast(b.column("text"), "binary").to_pylist()
            nrows += len(us)
            bag = {}
            for u, t in zip(us, ts):
                u = u or ""
                t = t or b""
                if "?" not in u:
                    continue
                bag.setdefault(norm_url(u), []).append((u, t))
            for nu, lst in bag.items():
                if len(lst) < 2:
                    continue
                seen = {}
                for u, t in lst:
                    seen.setdefault(u, t)
                if len(seen) < 2:
                    continue
                items = list(seen.items())
                for i in range(len(items)):
                    for j in range(i + 1, len(items)):
                        (uA, tA), (uB, tB) = items[i], items[j]
                        if hashlib.md5(tA).digest() != hashlib.md5(tB).digest():
                            ngroup += 1
                            if found is None:
                                found = (uA, tA, uB, tB, nu)
                            break
                    if found is not None and ngroup >= 1:
                        break
        if found is not None:
            break
    if found is None:
        return {"판정": "🔴 못 찾았다 --- 쌍을 못 골랐다(「없다」가 아니다 · 조항 59)",
                "읽은 shard": len(shards), "읽은 행": nrows, "통과": False}
    uA, tA, uB, tB, nu = found

    def keys(u, t):
        s = t.strip()
        return {
            "① URL 정확": h64(u.encode("utf-8")),
            "② URL 정규화": h64(norm_url(u).encode("utf-8")),
            "③ 본문 앞 200자": h64(s[:800].decode("utf-8", "ignore")[:200].encode("utf-8")),
            "덤 전문 md5": h64(t),
        }
    kA, kB = keys(uA, tA), keys(uB, tB)
    per = {}
    for r in kA:
        merged = bool(kA[r] == kB[r])
        per[r] = {"두 문서를 한 키로 뭉치나": merged,
                  "🔴 통과(뭉치지 않는다)": not merged}
    return {
        "무엇": ("🔴 C --- 서로 다른 두 **실제** 문서(`?no=A` / `?no=B` 꼴)를 자가 한 키로 "
               "뭉치면 붉다. 955 의 U 는 통과 조건이 **뭉침 그 자체**였다(티처 #94 M3)"),
        "읽은 shard": len(shards),
        "읽은 행": nrows,
        "이 표본에서 찾은 그런 쌍(≥1 인 군)": ngroup,
        "A URL": uA,
        "B URL": uB,
        "정규화하면 둘 다": nu,
        "A 본문 md5": hashlib.md5(tA).hexdigest(),
        "B 본문 md5": hashlib.md5(tB).hexdigest(),
        "A 본문 바이트": len(tA),
        "B 본문 바이트": len(tB),
        "🔴 두 문서가 정말 다른가(본문 md5 가 다른가)": hashlib.md5(tA).digest() != hashlib.md5(tB).digest(),
        "🔴 자별": per,
        "🔴 정본 자(자①)가 초록인가": per["① URL 정확"]["🔴 통과(뭉치지 않는다)"],
        "🔴 자②가 붉은가(= 이 프로브가 C2 를 실제로 잡았다)":
            not per["② URL 정규화"]["🔴 통과(뭉치지 않는다)"],
        "초": round(time.time() - t0, 1),
        # 🔴 이 절의 `통과` 는 **정본 자**에 대한 것이다. 자②의 붉음은 판정을 안 막는다.
        "통과": bool(per["① URL 정확"]["🔴 통과(뭉치지 않는다)"]),
    }


def probe_n(c_res):
    """🔴 음성 대조 --- 경로 한 글자가 다르면 URL 자들은 **다른 키**여야 한다.

    N 이 붉으면 C 의 붉음은 자의 병이 아니라 **프로브의 병**이다.
    ⚠ 자③·전문md5 는 **본문**을 읽으므로 URL 프로브의 검정력이 **원리상 0** 이다 --- 그렇게 적는다.
    """
    u = c_res.get("A URL")
    if not u:
        return {"판정": "🔴 못 했다 --- C 가 URL 을 못 골랐다", "통과": False}
    nu = norm_url(u)
    tail = nu.rsplit("/", 1)[-1] or nu
    ch = "z" if tail[:1] != "z" else "q"
    u2 = u.replace("/" + tail, "/" + ch + tail[1:], 1)
    changed = bool(u2 != u)
    k1 = (h64(u.encode("utf-8")) != h64(u2.encode("utf-8")))
    k2 = (h64(norm_url(u).encode("utf-8")) != h64(norm_url(u2).encode("utf-8")))
    return {
        "무엇": "🔴 N --- 경로 한 글자를 바꾸면 URL 자들이 다른 키를 내는가(C 의 검정력 확인)",
        "쓴 URL": u,
        "만든 URL": u2,
        "URL 이 실제로 바뀌었나": changed,
        "① URL 정확이 다른 키로 보나": bool(k1),
        "② URL 정규화가 다른 키로 보나": bool(k2),
        "⚠ ③ 본문 앞 200자 · 덤 전문 md5": ("🔴 검정력 0 --- 원리상. 이 프로브는 URL 만 바꾸는데 "
                                    "그 두 자는 **본문**을 읽는다. 「초록」이 아니라 「못 잰다」다"),
        "통과": bool(changed and k1 and k2),
    }


# ─────────────────────────────────────────────────── 본체

def analyze(out_path):
    t0 = time.time()
    os.chdir(REPO)
    res = {"무엇": "956 --- 정본을 자① 로 옮기고 K 를 판정에서 뗀다",
           "사전등록": "docs/prereg_956_ruler1.md (커밋 efc82effc · 측정 전 · 파일 하나)"}

    # ── 측정 조건(사전등록 §10) ──────────────────────────────────────────
    def _running(pat):
        p = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True)
        return [x for x in p.stdout.split("\n") if x.strip()]
    res["🔴 측정 조건(955 가 이걸 안 적어 C5 가 났다)"] = {
        "상시 데몬이 도는 중인가": bool(_running("harvest_daemon.py")),
        "상시 데몬 pid": _running("harvest_daemon.py") or "없음",
        "🔴 데몬을 재웠나": False,
        "FineWeb 수신이 도는 중인가": bool(_running("fineweb955_fetch.py")),
        "FineWeb 수신 pid": _running("fineweb955_fetch.py") or "없음",
        "통과": True,
    }

    # ── 수신 상태 ────────────────────────────────────────────────────────
    got = sorted(p.name for p in RECV.glob("*.parquet"))
    part = sorted(p.name for p in RECV.glob("*.part"))
    res["🔴 수신 상태(이 시각의 값 --- 진행 중인 수다 · m5)"] = {
        "잰 시각(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "🔴 받은 파일": len(got),
        "분모 = 파일 전량": 25,
        "받는 중(.part)": part or "없음",
        "받은 파일 이름": got,
        "🔴 「전량 받았다」라 써도 되나(25/25 에만)": bool(len(got) == 25),
        "통과": True,
    }

    # ── (ㄴ) 판 적재 ─────────────────────────────────────────────────────
    fullnames = sorted(p.name for p in FULL.glob("*.npz"))
    if not fullnames:
        res["🔴 (ㄴ) 전량 판"] = {"🔴 못 쟀다": "추출된 키가 0 --- `extract` 를 먼저 돌려라",
                            "통과": False}
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=1)
        return 1

    # ── 자별 측정 ────────────────────────────────────────────────────────
    rulers_g, rulers_n = {}, {}
    keep = {}

    # (ㄱ) 표본 판 --- 네 자 전부
    for label, key, curve in (("① URL 정확", "url_h", False),
                              ("② URL 정규화", "urn_h", True),
                              ("③ 본문 앞 200자", "hed_h", False),
                              ("덤 --- 전문 md5", "txt_h", False)):
        hp, shards = load_concat(SCAN, key, "s*.npz")
        fw, fws = load_concat(FWS, key, "*.npz")
        m, aux = measure(label, hp, fw, want_curve=curve)
        m["읽은 HPLT shard"] = len(shards)
        m["읽은 FineWeb 표본 npz"] = len(fws)
        rulers_g[label] = m
        if key == "url_h":
            keep["url_h"] = aux[0]                # hset --- 잭나이프에 다시 쓴다
        print("[ㄱ %s] D_문서=%s D_키=%s" % (label, m["🔴 D_문서 = ⓑ ÷ ②"], m["🔴 D_키 = ⓐ ÷ ④"]),
              flush=True)
        del hp, fw
    res["🔴 (ㄱ) 표본 판 --- 954 의 행군 층화 군집 표본이 분모"] = rulers_g

    # (ㄴ) 전량 판 --- url 열 자 둘 + (있으면) 본문 열 자 둘
    have_text = bool(sorted(FULLT.glob("*.npz")))
    nfull_url = len(sorted(FULL.glob("*.npz")))
    nfull_txt = len(sorted(FULLT.glob("*.npz")))
    jobs = [("① URL 정확", "url_h", True, FULL), ("② URL 정규화", "urn_h", True, FULL)]
    if have_text and nfull_txt == nfull_url:
        # 🔴 사전등록 §7 은 이것을 「안 한다」로 적었다. 실측이 그 근거(비용)를 뒤집어서 했다.
        jobs += [("③ 본문 앞 200자", "hed_h", False, FULLT),
                 ("덤 --- 전문 md5", "txt_h", False, FULLT)]
    for label, key, curve, src in jobs:
        curve = (label == "② URL 정규화")
        hp, shards = load_concat(SCAN, key, "s*.npz")
        fw, fns = load_concat(src, key, "*.npz")
        m, aux = measure(label, hp, fw, want_curve=curve)
        m["읽은 HPLT shard"] = len(shards)
        m["🔴 읽은 FineWeb parquet 파일"] = len(fns)
        m["🔴 분모 = 25 인가"] = bool(len(fns) == 25)
        rulers_n[label] = m
        print("[ㄴ %s] D_문서=%s D_키=%s (파일 %d)"
              % (label, m["🔴 D_문서 = ⓑ ÷ ②"], m["🔴 D_키 = ⓐ ÷ ④"], len(fns)), flush=True)
        del hp, fw
    res["🔴 (ㄴ) 전량 판 --- 받은 parquet 의 모든 행이 분모(키를 다시 계산했다)"] = rulers_n

    # ── 잭나이프(⓪-가 검출력 줄 · 티처 #94 M4) ───────────────────────────
    res["🔴 파일 단위 잭나이프((ㄴ) 자① D_문서) --- 티처 #94 M4"] = jackknife_files(
        load_per_file(FULL, "url_h", "*.npz"), keep["url_h"])

    # ── W8 ───────────────────────────────────────────────────────────────
    res["🔴🔴 W8 표본 대 전량 배선(티처 #94 M1)"] = w8_sample_vs_full()

    # ── 심은 키 ──────────────────────────────────────────────────────────
    try:
        c = probe_c()
    except Exception as e:                                   # 🔴 조항 59
        c = {"판정": "🔴 못 했다 --- %s: %s" % (type(e).__name__, e), "통과": False}
    res["🔴🔴 심은 키 C --- C2 를 실제로 잡는다(티처 #94 M3)"] = c
    res["🔴 심은 키 N --- 음성 대조"] = probe_n(c)

    # ── 배선 검사 W1~W7 ──────────────────────────────────────────────────
    g1, g2, g3, gt = (rulers_g["① URL 정확"], rulers_g["② URL 정규화"],
                      rulers_g["③ 본문 앞 200자"], rulers_g["덤 --- 전문 md5"])
    cur_g = g2["🔴 절단 곡선(전량 --- 목록을 안 자른다)"]
    W = [
        ("W1 HPLT 문서 전량 38,866,835", g1["분모 ① HPLT 문서"], 38866835),
        ("W1 읽은 shard 464", g1["읽은 HPLT shard"], 464),
        ("W2 자① 서로 다른 HPLT 키 34,162,776", g1["분모 ③ HPLT 서로 다른 키"], 34162776),
        ("W2 자② 서로 다른 HPLT 키 20,080,264", g2["분모 ③ HPLT 서로 다른 키"], 20080264),
        ("W3 자① 코퍼스 전체 최대 다중도 478", g1["다중도 --- 코퍼스 전체 최대(이 자의 천장)"], 478),
        ("W3 자① 교집합 키 최대 다중도 294", g1["다중도 --- 교집합 키당 HPLT 문서(최대)"], 294),
        ("W4 (ㄱ) 자① D_문서 0.173709", g1["🔴 D_문서 = ⓑ ÷ ②"], 0.173709),
        ("W4 (ㄱ) 자① D_키 0.173083", g1["🔴 D_키 = ⓐ ÷ ④"], 0.173083),
        ("W5 (ㄱ) 자② D_문서(절단 없음) 0.495933", g2["🔴 D_문서 = ⓑ ÷ ②"], 0.495933),
        ("W5 (ㄱ) 자② D_문서^21 0.195556", cur_g["K<=21"]["🔴 D_문서^K"], 0.195556),
        ("W5 (ㄱ) 자② D_문서^1 0.104892", cur_g["K<=1"]["🔴 D_문서^K"], 0.104892),
        ("W5 (ㄱ) 자② D_문서^1000 0.332190", cur_g["K<=1000"]["🔴 D_문서^K"], 0.332190),
        ("W6 (ㄱ) 자③ D_문서 0.13964", g3["🔴 D_문서 = ⓑ ÷ ②"], 0.13964),
        ("W6 (ㄱ) 전문md5 D_문서 0.06941", gt["🔴 D_문서 = ⓑ ÷ ②"], 0.06941),
        ("W7 (ㄱ) FineWeb 표본 문서 1,358,355", g1["분모 ② FineWeb 문서"], 1358355),
        ("W7 (ㄱ) 읽은 npz 25", g1["읽은 FineWeb 표본 npz"], 25),
    ]
    wr = [{"검사": n, "냈다": v, "받아야 한다": w,
           "통과": bool((abs(v - w) < 1e-5) if isinstance(w, float) else (v == w))}
          for n, v, w in W]
    w8 = res["🔴🔴 W8 표본 대 전량 배선(티처 #94 M1)"]
    wr.append({"검사": "W8 표본 대 전량 자① 키 불일치 0",
               "냈다": "%d/%d 파일 통과" % (w8["분자 = 통과한 파일"], w8["분모 = 대조한 파일"]),
               "받아야 한다": "전량 통과", "통과": bool(w8["통과"])})
    res["🔴 배선 검사 W1~W8"] = {
        "낱개": wr,
        "분자 = 맞은 검사": sum(1 for r in wr if r["통과"]),
        "분모 = 검사 전량": len(wr),
        "통과": bool(all(r["통과"] for r in wr)),
    }

    # ── 판정 ─────────────────────────────────────────────────────────────
    def cell(x):
        return "전량 안 받는다" if x >= 0.70 else ("전량 받는다" if x <= 0.30 else "보류 --- 부분 수신")

    n1, n2 = rulers_n["① URL 정확"], rulers_n["② URL 정규화"]
    D = n1["🔴 D_문서 = ⓑ ÷ ②"]
    cur_n = n2["🔴 절단 곡선(전량 --- 목록을 안 자른다)"]
    curve_cells = {k: cell(v["🔴 D_문서^K"]) for k, v in cur_n.items()}
    curve_one = len(set(curve_cells.values())) == 1

    # 🔴 부칙 2′(다) --- 입력 열로 계열을 센다
    n3 = rulers_n.get("③ 본문 앞 200자")
    if n3 is not None:
        text_row = {"값": n3["🔴 D_문서 = ⓑ ÷ ②"], "칸": cell(n3["🔴 D_문서 = ⓑ ÷ ②"]),
                    "분모": "🔴 (ㄴ) 받은 파일 전량 --- **같은 분모다**",
                    "⚠ 사전등록 §7 은 이것을 「안 한다」로 적었다":
                        ("근거가 비용 추정이었는데 **실측이 그것을 뒤집었다**(88,000행/초). "
                         "🔴 판정 규칙은 안 바꿨고 (나)는 이미 거짓이라 「강함」은 그대로 못 쓴다. "
                         "**(ㄱ) 표본 값도 같이 싣는다**: %s" % g3["🔴 D_문서 = ⓑ ÷ ②"])}
    else:
        text_row = {"값": g3["🔴 D_문서 = ⓑ ÷ ②"], "칸": cell(g3["🔴 D_문서 = ⓑ ÷ ②"]),
                    "분모": "🔴 (ㄱ) 표본 --- text 열은 전량을 안 읽었다(§7)"}
    fam = {
        "url 계열(자① D_문서)": {"값": D, "칸": cell(D), "분모": "(ㄴ) 받은 파일 전량"},
        "text 계열(자③ D_문서)": text_row,
    }
    fam_cells = {k: v["칸"] for k, v in fam.items()}
    fam_same = len(set(fam_cells.values())) == 1
    freeparams = 0

    wired = res["🔴 배선 검사 W1~W8"]["통과"]
    c_ok = bool(c.get("통과"))
    n_ok = bool(res["🔴 심은 키 N --- 음성 대조"].get("통과"))
    strong = bool(freeparams == 0 and curve_one and fam_same)

    res["🔴🔴 판정(사전등록 §6)"] = {
        "🔴 정본 D = 자① D_문서 (분모 = (ㄴ) 받은 파일 전량)": D,
        "🔴 정본이 든 칸": cell(D),
        "정본 자의 자유파라미터 수": freeparams,
        "🔴 부칙 2′(나) 곡선 전량이 한 칸인가": curve_one,
        "곡선 전량이 든 칸": curve_cells,
        "🔴 부칙 2′(다) 입력 열이 다른 자 둘": fam,
        "그 둘이 한 칸인가": fam_same,
        "🔴 부칙 3 --- 자②는 상·하한 쌍으로만 싣는다": {
            "상한 = 자② D_문서(절단 없음)": n2["🔴 D_문서 = ⓑ ÷ ②"],
            "하한 = 자② D_문서^{K=21}": cur_n["K<=%d" % K_PAIR]["🔴 D_문서^K"],
            "🔴 한 줄": "참값은 이 사이에 있고 우리는 어디인지 모른다",
            "⚠ 어느 쪽도 정본이 아니다": True,
        },
        "🔴 K 가 바뀌면 판정이 어디서 바뀌나": {
            "정본(자①)": "🔴 K 를 안 쓴다 --- 어디서도 안 바뀐다",
            "참고 --- 자②-절단을 정본으로 삼았다면": {
                "K=478(자료가 보증하는 자① 천장)": cur_n["K<=478"]["🔴 D_문서^K"],
                "K=503": cur_n["K<=503"]["🔴 D_문서^K"],
                "칸이 바뀌는 자리": "K=503 근방(955 가 선 자리)",
            },
        },
        "배선 검사 통과": wired,
        "심은 키 C(정본 자) 통과": c_ok,
        "심은 키 N 통과": n_ok,
        "🔴 자②가 C 에서 붉었나(= 정본에서 뗀 이유의 실물 증거)":
            c.get("🔴 자②가 붉은가(= 이 프로브가 C2 를 실제로 잡았다)"),
        "🔴 판정": (
            ("%s --- %s" % (cell(D), "강함" if strong else
                            "🔴 강하다고 못 쓴다(정본 하나로 섰다)"))
            if (wired and c_ok and n_ok) else
            "🔴 모른다 --- 배선 검사 또는 정본 자의 심은 키가 불통과다(사전등록 §3·§4)"),
        "🔴 「강하다고 못 쓴다」의 사유": {
            "(가) 자유파라미터 0": freeparams == 0,
            "(나) 곡선 전량이 한 칸": curve_one,
            "(다) 입력 열이 다른 자 둘이 한 칸": fam_same,
        },
        "통과": bool(wired and c_ok and n_ok),
    }

    # ── 예측 채점 ────────────────────────────────────────────────────────
    Dg = g1["🔴 D_문서 = ⓑ ÷ ②"]
    jk = res["🔴 파일 단위 잭나이프((ㄴ) 자① D_문서) --- 티처 #94 M4"]
    P = [
        ("P1 (ㄴ) 자① D_문서 ∈ [0.150, 0.200]", D, bool(0.150 <= D <= 0.200)),
        ("P2 |(ㄴ) − (ㄱ)| ≤ 0.020", round(abs(D - Dg), 6), bool(abs(D - Dg) <= 0.020)),
        ("P3 C 에서 자②는 붉고 자①은 초록",
         {"자① 초록": c.get("🔴 정본 자(자①)가 초록인가"),
          "자② 붉음": c.get("🔴 자②가 붉은가(= 이 프로브가 C2 를 실제로 잡았다)")},
         bool(c.get("🔴 정본 자(자①)가 초록인가")
              and c.get("🔴 자②가 붉은가(= 이 프로브가 C2 를 실제로 잡았다)"))),
        ("P4 곡선 전량이 한 칸인가 = 아니오", curve_one, bool(curve_one is False)),
        ("P5 자① 교집합 키 최대 다중도 ≥ 22",
         g1["다중도 --- 교집합 키당 HPLT 문서(최대)"],
         bool(g1["다중도 --- 교집합 키당 HPLT 문서(최대)"] >= 22)),
        ("P6 (ㄴ) 자① |D_문서 − D_키| ≤ 0.010",
         round(abs(n1["🔴 D_문서 = ⓑ ÷ ②"] - n1["🔴 D_키 = ⓐ ÷ ④"]), 6),
         bool(abs(n1["🔴 D_문서 = ⓑ ÷ ②"] - n1["🔴 D_키 = ⓐ ÷ ④"]) <= 0.010)),
        ("P7 (ㄴ) 자② D_문서(절단 없음) ∈ [0.40, 0.58]", n2["🔴 D_문서 = ⓑ ÷ ②"],
         bool(0.40 <= n2["🔴 D_문서 = ⓑ ÷ ②"] <= 0.58)),
        ("P8 파일 단위 잭나이프 SE ≤ 0.010", jk.get("🔴 잭나이프 SE"),
         bool(jk.get("🔴 잭나이프 SE") is not None and jk["🔴 잭나이프 SE"] <= 0.010)),
    ]
    res["🔴 예측 채점(사전등록 §5)"] = {
        "낱개": [{"예측": n, "값": v, "맞았나": ok} for n, v, ok in P],
        "분자 = 맞은 예측": sum(1 for _, _, ok in P if ok),
        "분모 = 예측 전량": len(P),
        "통과": True,
    }

    res["코드 sha256"] = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    res["dupe954_hplt_scan.py sha256"] = hashlib.sha256(
        (REPO / "runners/dupe954_hplt_scan.py").read_bytes()).hexdigest()
    res["시작(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    res["끝(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    res["초"] = round(time.time() - t0, 1)
    res["입력 파일 수"] = {"HPLT shard npz": len(glob.glob(str(SCAN / "s*.npz"))),
                     "FineWeb 표본 npz": len(glob.glob(str(FWS / "*.npz"))),
                     "🔴 FineWeb 전량 키 npz": len(fullnames)}
    res["통과"] = bool(res["🔴🔴 판정(사전등록 §6)"]["통과"])

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({
        "정본 D(자① D_문서 · (ㄴ))": D,
        "판정": res["🔴🔴 판정(사전등록 §6)"]["🔴 판정"],
        "배선": "%d/%d" % (res["🔴 배선 검사 W1~W8"]["분자 = 맞은 검사"],
                        res["🔴 배선 검사 W1~W8"]["분모 = 검사 전량"]),
        "예측": "%d/%d" % (res["🔴 예측 채점(사전등록 §5)"]["분자 = 맞은 예측"],
                        res["🔴 예측 채점(사전등록 §5)"]["분모 = 예측 전량"]),
    }, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "extract-text", "analyze"])
    ap.add_argument("--out", default="runners/out956_ruler1.json")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    if a.cmd == "extract":
        d = extract(force=a.force)
        print(json.dumps({"추출된 파일": len(d), "분모": 25}, ensure_ascii=False))
        return 0
    if a.cmd == "extract-text":
        d = extract_text(force=a.force)
        print(json.dumps({"본문 추출된 파일": len(d), "분모": 25}, ensure_ascii=False))
        return 0
    return analyze(a.out)


if __name__ == "__main__":
    sys.exit(main())
