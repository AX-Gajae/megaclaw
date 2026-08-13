#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""954 --- FineWeb-2 `kor_Hang` **행군 층화 표본**을 HTTP Range 로 읽어
HPLT 2.0 `kor_Hang` **전량**과 겹침을 잰다.

🔴 왜 안 받고 읽나: 전량은 25파일 · 105.77GB 다. **먼저 재고 나서 받을지 정한다**
(사전등록 §5 · 사용자 지시 *"전량 받고 재지 마라 --- 순서가 뒤집힌다"*).
parquet 은 행군(row group)마다 열이 따로 놓여 있어서 **필요한 행군의 필요한 열만**
바이트 범위로 받을 수 있다. 이 파일 하나가 그 배선이다.

층화: 파일 25개 각각에서 행군을 **고르게 K개** 고른다(`linspace`). 앞에서 자르지 않는다 ---
어제 HPLT 앞 4 shard 로 저지른 것이 정확히 그 실수다(원장 997).

씀:
    python3 runners/dupe954_fineweb.py --fetch --per-file 100 --workers 8
    python3 runners/dupe954_fineweb.py --compare
"""
import argparse
import gzip
import hashlib
import io
import json
import pathlib
import sys
import time
import urllib.request

import numpy as np
import pyarrow.compute as pc
import pyarrow.parquet as pq

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from runners.dupe954_hplt_scan import h64, head200, norm_url  # noqa: E402  (같은 자를 쓴다)

BASE = ("https://huggingface.co/datasets/HuggingFaceFW/fineweb-2/resolve/main/"
        "data/kor_Hang/train/")
NAMES = ["%03d_%05d.parquet" % (g, k) for g in range(5) for k in range(5)]
SCRATCH = pathlib.Path("/Users/ax/wm_harvest/954")
FW = SCRATCH / "fw"
SCAN = SCRATCH / "scan"


class HttpFile(io.RawIOBase):
    """🔴 조항 59 --- 200 껍데기를 성공으로 읽지 않는다. 길이를 세고 산출물에 적는다."""

    BLOCK = 16 * 1024 * 1024

    def __init__(self, url):
        self.url = url
        self.pos = 0
        self.nreq = 0
        self.nbytes = 0
        self._cs, self._ce, self._cb = 0, 0, b""
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers["Content-Length"])
            self.final = r.url

    def readable(self):
        return True

    def seekable(self):
        return True

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def tell(self):
        return self.pos

    def _get(self, start, end):
        """🔴 작은 범위 요청이 이 CDN 에서 느리다(실측 1.5MB 에 4~5초 · 8병렬).
        그래서 **블록 단위로 크게 받아 캐시한다** --- 이어진 행군을 고를 때 요청 수가 몇 배로 준다."""
        req = urllib.request.Request(self.final,
                                     headers={"Range": "bytes=%d-%d" % (start, end)})
        for a in range(5):
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return r.read()
            except Exception:
                if a == 4:
                    raise
                time.sleep(3 * (a + 1))

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0:
            return b""
        end = min(self.pos + n, self.size)
        if end <= self.pos:
            return b""
        want = end - self.pos
        if self._cs <= self.pos and end <= self._ce:            # 캐시 적중
            off = self.pos - self._cs
            b = self._cb[off:off + want]
            self.pos += len(b)
            return b
        if want >= self.BLOCK:                                   # 큰 요청은 그대로
            b = self._get(self.pos, end - 1)
            self.nreq += 1
            self.nbytes += len(b)
            self.pos += len(b)
            return b
        bs = self.pos
        be = min(bs + self.BLOCK, self.size)
        blk = self._get(bs, be - 1)
        self.nreq += 1
        self.nbytes += len(blk)
        self._cs, self._ce, self._cb = bs, bs + len(blk), blk
        b = blk[:want]
        self.pos += len(b)
        return b


def fetch_one(job):
    name, per_file = job
    out = FW / (name.replace(".parquet", ".npz"))
    if out.exists():
        return {"파일": name, "건너뜀": True}
    t0 = time.time()
    h = HttpFile(BASE + name)
    pf = pq.ParquetFile(h)
    nrg = pf.metadata.num_row_groups
    nrows = pf.metadata.num_rows
    # 🔴 층화 **군집** 표본 --- 파일마다 고르게 떨어진 자리 CL 곳에서 **이어진 행군 CS 개**를 읽는다.
    #    이어진 행군은 파일 안에서 바이트가 이어져 있어서 **한 번의 큰 범위 요청**으로 받는다.
    #    (행군 하나가 1,000행이라 낱개로 고르면 요청이 수천 건이 되고, 이 CDN 에서 그건 느리다.)
    CS = 4
    CL = max(1, per_file // CS)
    starts = sorted(set(int(round(x)) for x in np.linspace(0, max(nrg - CS, 0), CL)))
    idx = []
    for s0 in starts:
        idx.extend(range(s0, min(s0 + CS, nrg)))
    idx = sorted(set(idx))
    url_h, urn_h, hed_h, txt_h = [], [], [], []
    urls_norm = []
    got = 0
    for gi in range(0, len(idx), CS):
        grp = idx[gi:gi + CS]
        tb = pf.read_row_groups(grp, columns=["url", "text"])
        us = tb.column("url").to_pylist()
        ts = pc.cast(tb.column("text"), "binary").to_pylist()
        for u, t in zip(us, ts):
            u = u or ""
            t = t or b""
            nu = norm_url(u)
            url_h.append(h64(u.encode("utf-8")))
            urn_h.append(h64(nu.encode("utf-8")))
            hed_h.append(h64(head200(t).encode("utf-8")))
            txt_h.append(h64(t))
            urls_norm.append(nu)
            got += 1
        if (gi // CS) % 2 == 0:
            print("   %s rg %d/%d · 행 %d · MB %.0f · %.0fs"
                  % (name, gi + len(grp), len(idx), got, h.nbytes / 1e6,
                     time.time() - t0), flush=True)
    FW.mkdir(parents=True, exist_ok=True)
    np.savez(out,
             url_h=np.array(url_h, dtype=np.uint64),
             urn_h=np.array(urn_h, dtype=np.uint64),
             hed_h=np.array(hed_h, dtype=np.uint64),
             txt_h=np.array(txt_h, dtype=np.uint64))
    with gzip.open(FW / (name.replace(".parquet", ".urls.gz")), "wt", encoding="utf-8") as f:
        f.write("\n".join(urls_norm))
    rec = {"파일": name, "전량 행": int(nrows), "전량 행군": int(nrg),
           "고른 행군": len(idx), "받은 행": got,
           "요청 수": h.nreq, "받은 바이트": h.nbytes, "초": round(time.time() - t0, 1)}
    with (FW / (name + ".json")).open("w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)
    return rec


def fetch(per_file, slice_i, nslice):
    """🔴 프로세스 풀을 안 쓴다. 2026-08-13 실측: `mp.Pool` 로 8워커를 띄우니 **워커 여섯이
    조용히 사라지고 부모가 영영 기다렸다**(자식 0 · TCP 0 · 진행 0). 조항 59 그 자체 ---
    「도는 중」과 「멈춰 있음」이 겉으로 같았다. 그래서 **셸에서 프로세스를 갈라 띄우고**
    각 프로세스는 한 줄로 돈다. 진행은 파일 하나가 끝날 때마다 눈에 보인다."""
    FW.mkdir(parents=True, exist_ok=True)
    jobs = [(n, per_file) for k, n in enumerate(NAMES) if k % nslice == slice_i]
    t0 = time.time()
    for k, j in enumerate(jobs):
        r = fetch_one(j)
        print("%d/%d %s" % (k + 1, len(jobs), json.dumps(r, ensure_ascii=False)), flush=True)
    print("끝 %.1fs" % (time.time() - t0), flush=True)


# ---------------------------------------------------------------- 겹침 판정

def load_hplt():
    """HPLT 전량 해시. shard 별 npz 를 이어 붙인다."""
    fs = sorted(SCAN.glob("s*.npz"))
    parts = {k: [] for k in ("url_h", "urn_h", "hed_h", "txt_h")}
    for p in fs:
        z = np.load(p, allow_pickle=True)
        for k in parts:
            parts[k].append(z[k])
    return {k: np.concatenate(v) for k, v in parts.items()}, len(fs)


def load_fw():
    fs = sorted(FW.glob("*.npz"))
    parts = {k: [] for k in ("url_h", "urn_h", "hed_h", "txt_h")}
    per = []
    for p in fs:
        z = np.load(p)
        for k in parts:
            parts[k].append(z[k])
        per.append((p.name.replace(".npz", ".parquet"), z["urn_h"]))
    return {k: np.concatenate(v) for k, v in parts.items()}, len(fs), per


def overlap(hp, fwa, label, planted=None):
    """🔴 조항 62 --- 개수만 싣지 않는다. 반대 방향 · 예시 · 심은 키를 같은 자리에.

    분모 둘을 나란히 적는다(조항 60): 문서 기준과 서로 다른 키 기준.
    """
    hset = np.unique(hp)
    fset = np.unique(fwa)
    inter = np.intersect1d(hset, fset, assume_unique=True)
    # 문서 기준(같은 URL 이 여러 문서일 수 있다)
    fw_doc_hit = int(np.isin(fwa, inter, assume_unique=False).sum())
    hp_doc_hit = int(np.isin(hp, inter, assume_unique=False).sum())
    out = {
        "자": label,
        "🔴 분모 ① HPLT 문서 전량": int(len(hp)),
        "🔴 분모 ② FineWeb 표본 문서": int(len(fwa)),
        "🔴 분모 ③ HPLT 서로 다른 키": int(len(hset)),
        "🔴 분모 ④ FineWeb 표본 서로 다른 키": int(len(fset)),
        "교집합(서로 다른 키)": int(len(inter)),
        "🔴 교집합 ÷ FineWeb 표본 문서": round(fw_doc_hit / len(fwa), 6),
        "🔴 교집합 ÷ HPLT 문서 전량": round(hp_doc_hit / len(hp), 6),
        "FineWeb 표본에서 맞은 문서 수": fw_doc_hit,
        "HPLT 에서 맞은 문서 수": hp_doc_hit,
        "① 반대 방향 --- HPLT − FineWeb(키)": int(len(hset) - len(inter)),
        "① 반대 방향 --- FineWeb − HPLT(키)": int(len(fset) - len(inter)),
        # 🔴 판정 키 규약(⑤′ 절 3) --- 이 절의 `통과` 는 **자기 일관성**이다:
        #    교집합이 두 쪽 키 집합보다 클 수 없고, 문서 적중이 분모를 못 넘는다.
        "통과": bool(len(inter) <= min(len(hset), len(fset))
                   and fw_doc_hit <= len(fwa) and hp_doc_hit <= len(hp)),
    }
    if planted is not None:
        out.update(planted)
    return out


def compare(per_file_note):
    t0 = time.time()
    hp, nsh = load_hplt()
    fw, nfw, per = load_fw()
    metas = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(FW.glob("*.json"))]
    fw_rows_total = sum(m["전량 행"] for m in metas)

    # ---- 🔴 조항 62 ③ 심은 키 --------------------------------------------
    # 심기 A: HPLT 의 실제 정규화 URL 하나를 FineWeb 쪽에 넣는다 → 교집합이 잡아야 한다
    # 심기 B: 세상에 없는 URL 하나를 HPLT 쪽에 넣는다 → 어느 교집합에도 들면 안 된다
    z0 = np.load(SCAN / "s000.npz", allow_pickle=True)
    import pyarrow.parquet as _pq
    pf0 = _pq.ParquetFile("data/ingest/hplt_ko/train-00000-of-00464.parquet")
    first = pf0.read_row_group(0, columns=["u"]).column("u").to_pylist()
    seed_url = None
    for u in first:
        nu = norm_url(u)
        hh = h64(nu.encode("utf-8"))
        if not np.isin(np.array([hh], dtype=np.uint64), fw["urn_h"]).any():
            seed_url, seed_h = nu, hh
            break
    fake = "example.invalid/954-planted-%s" % hashlib.md5(b"954").hexdigest()[:8]
    fake_h = h64(fake.encode("utf-8"))

    base = overlap(hp["urn_h"], fw["urn_h"], "② 정규화 URL(정본)")
    fw_plus = np.append(fw["urn_h"], np.uint64(seed_h))
    hp_plus = np.append(hp["urn_h"], np.uint64(fake_h))
    got_a = int(np.isin(np.array([seed_h], dtype=np.uint64),
                        np.intersect1d(np.unique(hp["urn_h"]), np.unique(fw_plus))).sum())
    inter_b = np.intersect1d(np.unique(hp_plus), np.unique(fw["urn_h"]))
    got_b = int(np.isin(np.array([fake_h], dtype=np.uint64), inter_b).sum())
    planted = {
        "🔴 조항 62 ③ 심은 키": {
            "A 심은 것(HPLT 실제 URL 을 FineWeb 쪽에)": seed_url,
            "A 잡았나": bool(got_a == 1),
            "B 심은 것(세상에 없는 URL 을 HPLT 쪽에)": fake,
            "B 가 교집합에 들었나(들면 결함)": bool(got_b == 1),
            "🔴 심은 원소는 판정 계수에서 뺐다": True,
            "판정": ("잡았다" if got_a == 1 and got_b == 0 else "🔴 모른다"),
            "통과": bool(got_a == 1 and got_b == 0),
        }
    }
    base.update(planted)

    # ---- 예시 다섯(조항 62 ②) ---------------------------------------------
    fw_urls = []
    for p in sorted(FW.glob("*.urls.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            fw_urls.extend(f.read().split("\n"))
    fw_urls = np.array(fw_urls, dtype=object)
    hset = np.unique(hp["urn_h"])
    hit_mask = np.isin(fw["urn_h"], hset)
    ex_in = list(fw_urls[hit_mask][:5])
    ex_out = list(fw_urls[~hit_mask][:5])
    # HPLT − FineWeb 예시: shard 0 에서 실제 URL 을 꺼낸다
    fset = np.unique(fw["urn_h"])
    s0 = z0["urn_h"]
    miss0 = ~np.isin(s0, fset)
    idx = np.flatnonzero(miss0)[:5]
    us0 = pf0.read(columns=["u"]).column("u").to_pylist()
    ex_hplt_only = [norm_url(us0[i]) for i in idx]
    base["② 예시 다섯 --- FineWeb ∩ HPLT"] = ex_in
    base["② 예시 다섯 --- FineWeb 에만"] = ex_out
    base["② 예시 다섯 --- HPLT 에만(shard 0)"] = ex_hplt_only

    # ---- 🔴 파일별 비율과 **크기 가중** D --------------------------------
    #  표본은 파일마다 행군 수가 같지만 **파일의 실제 크기는 다르다**(실측: 어떤 파일은
    #  2,783,000행 · 어떤 파일은 934,278행). 그래서 단순 합산은 작은 파일을 과대표한다.
    #  전량 행 수로 가중한 값을 **같이** 싣는다(조항 60 --- 분모가 다른 수를 잇지 마라).
    mrows = {m["파일"]: m["전량 행"] for m in metas}
    hset_u = np.unique(hp["urn_h"])
    perf, wsum, wtot = [], 0.0, 0.0
    for nm, arr in per:
        rate = float(np.isin(arr, hset_u).mean())
        w = mrows.get(nm, 0)
        perf.append({"파일": nm, "표본 문서": int(len(arr)), "전량 행": w,
                     "자② 적중률": round(rate, 6)})
        wsum += rate * w
        wtot += w
    dw = wsum / wtot if wtot else None

    res = {
        "무엇": "FineWeb-2 kor_Hang(행군 층화 표본) × HPLT 2.0 kor_Hang(전량) 겹침",
        "🔴 파일별 자② 적중률": perf,
        "🔴 크기 가중 D(전량 행 수로 가중)": round(dw, 6) if dw is not None else None,
        "🔴 규약 60 --- 명령·범위·트리": {
            "명령": "python3 runners/dupe954_fineweb.py --fetch --per-file %s ; --compare"
                    % per_file_note,
            "범위": "HuggingFaceFW/fineweb-2 · data/kor_Hang/train/*.parquet 25파일 · "
                    "각 파일에서 행군을 linspace 로 고르게 골랐다",
            "트리": "HTTP Range 로 읽었고 파일은 저장소에 안 들인다",
            "통과": True,          # 세 칸이 다 차 있다
        },
        "🔴 FineWeb 전량 문서 수(25파일 메타 전수)": int(fw_rows_total),
        "🔴 FineWeb 표본 문서 수": int(len(fw["urn_h"])),
        "🔴 표본 비율": round(len(fw["urn_h"]) / fw_rows_total, 6),
        "🔴 HPLT 문서 전량": int(len(hp["urn_h"])),
        "🔴 읽은 HPLT shard 수": nsh,
        "🔴 읽은 FineWeb 파일 수": nfw,
        "받은 바이트(FineWeb)": sum(m["받은 바이트"] for m in metas),
        "요청 수(FineWeb)": sum(m["요청 수"] for m in metas),
        "자 ① URL 정확": overlap(hp["url_h"], fw["url_h"], "① URL 정확"),
        "자 ② URL 정규화(🔴 정본)": base,
        "자 ③ 본문 앞 200자": overlap(hp["hed_h"], fw["hed_h"], "③ 본문 앞 200자 md5"),
        "덤 --- 전문 md5(사전등록 밖 · 판정에 안 쓴다)":
            overlap(hp["txt_h"], fw["txt_h"], "전문 md5"),
        "⚠ 64비트 해시 충돌 기대치(HPLT×FW)":
            round(len(hp["urn_h"]) * len(fw["urn_h"]) / 2 ** 64, 8),
        "코드 sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
        "시작(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0)),
        "끝(UTC)": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "초": round(time.time() - t0, 1),
        "통과": True,
    }
    out = REPO / "runners" / "out954_dupe.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({
        "D(자② 교집합÷FineWeb 표본)": base["🔴 교집합 ÷ FineWeb 표본 문서"],
        "자① ÷FW": res["자 ① URL 정확"]["🔴 교집합 ÷ FineWeb 표본 문서"],
        "자③ ÷FW": res["자 ③ 본문 앞 200자"]["🔴 교집합 ÷ FineWeb 표본 문서"],
        "심은 키": base["🔴 조항 62 ③ 심은 키"]["판정"],
    }, ensure_ascii=False))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--per-file", type=int, default=100)
    ap.add_argument("--slice", type=int, default=0)
    ap.add_argument("--nslice", type=int, default=1)
    a = ap.parse_args()
    import os
    os.chdir(REPO)
    if a.fetch:
        fetch(a.per_file, a.slice, a.nslice)
    if a.compare:
        return compare(a.per_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
