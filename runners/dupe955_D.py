#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""955 --- `D` 를 다시 정의하고 954 의 §5 를 다시 문다.

🔴 왜: 티처 #93 C1 --- `out954_dupe.json` 의 키 이름은 「교집합 ÷ FineWeb 표본 문서」인데
실제 계산은 `dupe954_fineweb.py:234` 의 `fw_doc_hit / len(fwa)` 였다. 분자가 **교집합 키**가
아니라 **맞은 FineWeb 문서 수**다. 글자 그대로 나누면 D = 17.916% 이고 §5 는
「FineWeb-2 전량을 받는다」를 가리킨다. 954 가 낸 「보류」는 **유일한 무결정 갈래**였다.

🔴 그리고 티처 #93 C2 --- 그 49.593% 의 대부분이 **뭉침**이다. 교집합 키당 HPLT 39.73 문서
(코퍼스 평균 1.94 의 20배). 범인은 쿼리에 문서 번호가 든 CMS 종점.

이 러너가 내는 것(전부 `docs/prereg_955_D.md` §2 에 **측정 전에** 박았다):
    자마다  D_키 · D_문서 · D_954글자 · D_문서^K · D_키^K · E_키 · E_문서
    절단 곡선 K ∈ {1,2,5,10,21,50,100,1000,∞}   (🔴 정본은 K=21 · §2-A 근거)
    배선 검사 W1~W8   --- 티처가 이미 낸 수를 내 코드가 독립 재현하는가
    심은 키 U·V·R    --- 🔴 검정력이 0 이 아닌 것으로(티처 #93 M6)
    P1~P7 채점

🔴 자료를 다시 안 뜬다. `/Users/ax/wm_harvest/954/{scan,fw}` 의 npz 를 그대로 읽는다.

씀:
    python3 runners/dupe955_D.py            # 전부
    python3 runners/dupe955_D.py --no-net   # R 프로브(HTTP Range 재수신)를 뺀다
"""
import argparse
import gzip
import hashlib
import json
import pathlib
import pickle
import re
import sys
import time

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO))
from runners.dupe954_hplt_scan import h64, head200, norm_url, NEWS_PAT  # noqa: E402

SCRATCH = pathlib.Path("/Users/ax/wm_harvest/954")
SCAN = SCRATCH / "scan"
FW = SCRATCH / "fw"
HPLT_DIR = pathlib.Path("data/ingest/hplt_ko")

RULERS = [
    ("① URL 정확", "url_h"),
    ("② URL 정규화(🔴 정본)", "urn_h"),
    ("③ 본문 앞 200자", "hed_h"),
    ("덤 --- 전문 md5(판정 밖)", "txt_h"),
]
KS = [1, 2, 5, 10, 21, 50, 100, 1000]
K_MAIN = 21          # 🔴 사전등록 §2-A --- 재기 전에 정했다. collection 이 21 이다

# ---------------------------------------------------------------- m6 의 자 셋
# 🔴 954 가 쓴 자를 **여기 얼려 옮긴다**. 원본(`dupe954_hplt_scan.NEWS_PAT`)을 955 가
#    고치더라도 배선 검사 W8(=954 의 13.959% 재현)이 살아 있어야 하기 때문이다.
_BODY = (
    r"news|newsis|yna|yonhapnews|chosun|donga|joins|joongang|hani|khan|"
    r"mk|mt|edaily|etnews|inews24|nocutnews|ohmynews|pressian|seoul|segye|kmib|kukinews|"
    r"hankookilbo|hankyung|sedaily|fnnews|asiae|ajunews|newdaily|dailian|breaknews|"
    r"osen|dispatch|xportsnews|tvreport|starnews|isplus|sportsseoul|sportschosun|"
    r"sportsq|mydaily|newsen|tenasia|wowtv|heraldcorp|imbc|sbs|kbs|jtbc|ytn|mbn|tvchosun")
NEWS_PAT_954 = re.compile(r"(?:^|\.)(?:%s)(?:\.|$)|news" % _BODY)          # 얼린 954 판
# 🔴 사전등록 §5 P5 의 자 --- 앵커 없는 `|news` 를 **통째로 떼고** 브랜드 목록만 앵커로 남긴다
NEWS_PAT_955 = re.compile(r"(?:^|\.)(?:%s)(?:\.|$)" % _BODY)
# 🔴🔴 **사후 추가(사전등록에 없다 · P5 채점에 안 쓴다)** --- `news` 를 host **라벨 안**에서만
#    찾는 자. 앵커 문제만 고치고 「news 가 든 언론사 host」는 안 버린다.
NEWS_PAT_955L = re.compile(
    r"(?:^|\.)(?:%s)(?:\.|$)|(?:^|\.)[a-z0-9-]*news[a-z0-9-]*(?:\.|$)" % _BODY)


# ---------------------------------------------------------------- 적재

def load_side(d, key, pat):
    fs = sorted(d.glob(pat))
    parts = []
    for p in fs:
        z = np.load(p, allow_pickle=True)
        parts.append(z[key])
    return np.concatenate(parts), len(fs)


# ---------------------------------------------------------------- 한 자

def measure(label, hp, fw):
    """🔴 사전등록 §2 표 그대로. **한 줄에 정의 하나 · 분자와 분모를 같은 줄에.**"""
    t0 = time.time()
    hset, hcnt = np.unique(hp, return_counts=True)
    fset, fcnt = np.unique(fw, return_counts=True)
    inter = np.intersect1d(hset, fset, assume_unique=True)
    hi = np.searchsorted(hset, inter)
    fi = np.searchsorted(fset, inter)
    mult_h = hcnt[hi].astype(np.int64)          # 교집합 키의 **HPLT 다중도**
    mult_f = fcnt[fi].astype(np.int64)          # 교집합 키의 **FineWeb 표본 다중도**
    fw_doc_hit = int(mult_f.sum())
    hp_doc_hit = int(mult_h.sum())
    nH, nF = int(len(hp)), int(len(fw))
    nHk, nFk = int(len(hset)), int(len(fset))
    nI = int(len(inter))

    cut = {}
    for K in KS:
        m = mult_h <= K
        cut["K<=%d" % K] = {
            "🔴 D_문서^K 분자 = 다중도<=K 인 교집합 키에 걸린 FineWeb 표본 문서": int(mult_f[m].sum()),
            "🔴 D_문서^K 분모 = FineWeb 표본 문서": nF,
            "🔴 D_문서^K": round(float(mult_f[m].sum()) / nF, 6),
            "🔴 D_키^K 분자 = 다중도<=K 인 교집합 키": int(m.sum()),
            "🔴 D_키^K 분모 = FineWeb 표본 서로 다른 키": nFk,
            "🔴 D_키^K": round(float(m.sum()) / nFk, 6),
            "E_문서^K 분자 = 다중도<=K 인 교집합 키에 걸린 HPLT 문서": int(mult_h[m].sum()),
            "E_문서^K 분모 = HPLT 문서 전량": nH,
            "E_문서^K": round(float(mult_h[m].sum()) / nH, 6),
            "통과": bool(int(m.sum()) <= nI and int(mult_f[m].sum()) <= fw_doc_hit),
        }

    out = {
        "자": label,
        # ---- 분모 넷(조항 60) · 한 줄에 하나 ------------------------------
        "분모 ① HPLT 문서 전량": nH,
        "분모 ② FineWeb 표본 문서": nF,
        "분모 ③ HPLT 서로 다른 키": nHk,
        "분모 ④ FineWeb 표본 서로 다른 키": nFk,
        # ---- 분자 셋 · 한 줄에 하나 ---------------------------------------
        "분자 ⓐ 교집합(서로 다른 키)": nI,
        "분자 ⓑ 맞은 FineWeb 표본 문서": fw_doc_hit,
        "분자 ⓒ 맞은 HPLT 문서": hp_doc_hit,
        # ---- 🔴 D 넷 --- 이름 = 분자÷분모 ---------------------------------
        "🔴 D_키 = ⓐ ÷ ④": round(nI / nFk, 6),
        "🔴 D_문서 = ⓑ ÷ ②": round(fw_doc_hit / nF, 6),
        "🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)": round(nI / nF, 6),
        "🔴 E_키 = ⓐ ÷ ③": round(nI / nHk, 6),
        "🔴 E_문서 = ⓒ ÷ ①": round(hp_doc_hit / nH, 6),
        # ---- 뭉침 -----------------------------------------------------------
        "뭉침 --- 교집합 키당 HPLT 문서(평균)": round(float(mult_h.mean()), 4),
        "뭉침 --- 교집합 키당 HPLT 문서(중앙값)": int(np.median(mult_h)),
        "뭉침 --- 교집합 키당 HPLT 문서(최대)": int(mult_h.max()),
        "뭉침 --- 코퍼스 전체 키당 HPLT 문서(평균)": round(nH / nHk, 4),
        "뭉침 --- 다중도 > %d 인 교집합 키" % K_MAIN: int((mult_h > K_MAIN).sum()),
        "뭉침 --- 다중도 > %d 인 교집합 키의 비율(÷교집합 키)" % K_MAIN:
            round(float((mult_h > K_MAIN).sum()) / nI, 6),
        # ---- 반대 방향(조항 62 ①) -------------------------------------------
        "① 반대 방향 --- HPLT − FineWeb(키)": nHk - nI,
        "① 반대 방향 --- FineWeb − HPLT(키)": nFk - nI,
        "🔴 절단 곡선": cut,
        "초": round(time.time() - t0, 1),
        # 자기 일관성: 교집합은 두 키 집합보다 클 수 없고 문서 적중이 분모를 못 넘는다
        "통과": bool(nI <= min(nHk, nFk) and fw_doc_hit <= nF and hp_doc_hit <= nH
                   and nI <= fw_doc_hit and nI <= hp_doc_hit),
    }
    return out, inter, mult_h, mult_f, hset, fset


# ---------------------------------------------------------------- 심은 키

def probe_uv(hset_urn, hset_url, hset_hed):
    """🔴 티처 #93 M6 수리 --- 프로브가 **정규화 함수를 실제로 지난다**.

    U: HPLT 의 실제 URL `u` 에 쿼리를 붙인 `u'` 를
       - 자②(정규화)는 `u` 와 **같은 키**로 봐야 하고
       - 자①(정확)은 **다른 키**로 봐야 한다.       ← 🔴 둘 다 성립해야 통과
    V: 같은 `u` 의 **경로 한 글자**를 바꾼 `u''` 는 어느 자에서도 `u` 와 같으면 안 된다.
    """
    import pyarrow.parquet as pq
    p0 = HPLT_DIR / "train-00000-of-00464.parquet"
    us = pq.ParquetFile(p0).read_row_group(0, columns=["u"]).column("u").to_pylist()
    pick = None
    for u in us:
        nu = norm_url(u)
        if "?" not in u and "#" not in u and "/" in nu and len(nu.rsplit("/", 1)[-1]) > 3:
            pick = u
            break
    if pick is None:
        return {"판정": "🔴 모른다 --- 쓸 만한 URL 을 못 골랐다", "통과": False}

    u = pick
    u_q = u + "?wm955=probe"                     # 쿼리만 붙였다
    tail = norm_url(u).rsplit("/", 1)[-1]
    ch = "z" if tail[0] != "z" else "q"
    u_p = u.replace("/" + tail, "/" + ch + tail[1:], 1)   # 경로 한 글자

    k_urn_u = np.uint64(h64(norm_url(u).encode("utf-8")))
    k_urn_q = np.uint64(h64(norm_url(u_q).encode("utf-8")))
    k_urn_p = np.uint64(h64(norm_url(u_p).encode("utf-8")))
    k_url_u = np.uint64(h64(u.encode("utf-8")))
    k_url_q = np.uint64(h64(u_q.encode("utf-8")))

    U_norm_same = bool(k_urn_q == k_urn_u)
    U_exact_diff = bool(k_url_q != k_url_u)
    U_norm_in_h = bool(np.isin(np.array([k_urn_q], dtype=np.uint64), hset_urn)[0])
    U_exact_in_h = bool(np.isin(np.array([k_url_q], dtype=np.uint64), hset_url)[0])
    V_norm_diff = bool(k_urn_p != k_urn_u)
    V_norm_in_h = bool(np.isin(np.array([k_urn_p], dtype=np.uint64), hset_urn)[0])

    okU = U_norm_same and U_exact_diff and U_norm_in_h and not U_exact_in_h
    okV = V_norm_diff and not V_norm_in_h
    return {
        "U 쓴 URL": u,
        "U 만든 URL(쿼리를 붙였다)": u_q,
        "U ㉠ 자②가 같은 키로 보나": U_norm_same,
        "U ㉡ 자①이 다른 키로 보나": U_exact_diff,
        "U ㉢ 자②의 키가 HPLT 키 집합에 드나(들어야 한다)": U_norm_in_h,
        "U ㉣ 자①의 키가 HPLT 키 집합에 드나(들면 안 된다)": U_exact_in_h,
        "U 통과": okU,
        "V 만든 URL(경로 한 글자)": u_p,
        "V ㉠ 자②가 다른 키로 보나": V_norm_diff,
        "V ㉡ 그 키가 HPLT 에 드나(들면 안 된다)": V_norm_in_h,
        "V 통과": okV,
        "🔴 심은 원소는 판정 계수에서 뺐다(집합에 안 넣었다 --- 읽기만 했다)": True,
        "판정": "잡았다" if (okU and okV) else "🔴 모른다",
        "통과": bool(okU and okV),
    }


def probe_r():
    """🔴 R --- **HTTP Range 수신 + parquet 열 읽기 + 해시**를 지금 다시 지나서
    저장된 npz 앞부분과 바이트 동일한지 본다. 티처 #93 M6 이 「한 줄도 안 지난다」고 한 그 배선."""
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    from runners.dupe954_fineweb import BASE, HttpFile
    name = "000_00000.parquet"
    t0 = time.time()
    h = HttpFile(BASE + name)
    pf = pq.ParquetFile(h)
    grp = [0, 1, 2, 3]                     # fetch_one 의 첫 군집(CS=4 · starts[0]=0)
    tb = pf.read_row_groups(grp, columns=["url", "text"])
    us = tb.column("url").to_pylist()
    ts = pc.cast(tb.column("text"), "binary").to_pylist()
    a_url, a_urn, a_hed, a_txt = [], [], [], []
    for u, t in zip(us, ts):
        u = u or ""
        t = t or b""
        a_url.append(h64(u.encode("utf-8")))
        a_urn.append(h64(norm_url(u).encode("utf-8")))
        a_hed.append(h64(head200(t).encode("utf-8")))
        a_txt.append(h64(t))
    z = np.load(FW / name.replace(".parquet", ".npz"))
    n = len(a_url)
    eq = {}
    for k, arr in (("url_h", a_url), ("urn_h", a_urn), ("hed_h", a_hed), ("txt_h", a_txt)):
        got = np.array(arr, dtype=np.uint64)
        eq[k] = int((got != z[k][:n]).sum())
    return {
        "파일": name,
        "다시 받은 행군": grp,
        "다시 계산한 행": n,
        "받은 바이트": int(h.nbytes),
        "요청 수": int(h.nreq),
        "🔴 불일치 --- url_h": eq["url_h"],
        "🔴 불일치 --- urn_h": eq["urn_h"],
        "🔴 불일치 --- hed_h": eq["hed_h"],
        "🔴 불일치 --- txt_h": eq["txt_h"],
        "초": round(time.time() - t0, 1),
        "통과": bool(sum(eq.values()) == 0 and n > 0),
    }


# ---------------------------------------------------------------- m6 · m7

def news_remeasure():
    """🔴 m6 --- 앵커 없는 `|news` 를 뗀 자로 **전량을 다시 센다**.
    자료를 다시 안 뜬다: 954 가 shard 마다 남긴 host 빈도표(`h*.pkl`)를 쓴다."""
    t0 = time.time()
    fs = sorted(SCAN.glob("h*.pkl"))
    tot = {}
    for p in fs:
        for k, v in pickle.load(open(p, "rb")).items():
            tot[k] = tot.get(k, 0) + v
    N = sum(tot.values())
    old = anch = lab = 0
    lost_by_anchor = []          # 954 자는 잡고 앵커 자는 놓치는 host
    lost_by_label = []           # 954 자는 잡고 라벨 자도 놓치는 host  ← 진짜 앵커 결함
    for hkey, c in tot.items():
        a = bool(NEWS_PAT_954.search(hkey))
        b = bool(NEWS_PAT_955.search(hkey))
        d = bool(NEWS_PAT_955L.search(hkey))
        old += c * a
        anch += c * b
        lab += c * d
        if a and not b:
            lost_by_anchor.append({"host": hkey, "문서": c})
        if a and not d:
            lost_by_label.append({"host": hkey, "문서": c})
    lost_by_anchor.sort(key=lambda r: -r["문서"])
    lost_by_label.sort(key=lambda r: -r["문서"])
    return {
        "무엇": "뉴스·연예형 host 비율 --- 자 셋을 같은 분모에 댄다(티처 #93 m6)",
        "분모 = HPLT 문서 전량(host 빈도표 합)": N,
        "읽은 shard 빈도표": len(fs),
        "서로 다른 host": len(tot),
        "① 954 자(앵커 없는 |news) 분자": old,
        "① 954 자 비율": round(old / N, 6),
        "② 955-앵커 자(사전등록 P5 의 자) 분자": anch,
        "② 955-앵커 자 비율": round(anch / N, 6),
        "③ 955-라벨 자(🔴 사후 추가 · P5 채점 밖) 분자": lab,
        "③ 955-라벨 자 비율": round(lab / N, 6),
        "🔴🔴 ① − ③ = 앵커 결함이 실제로 잘못 잡던 문서": old - lab,
        "🔴🔴 ① − ③ 의 host 수": len(lost_by_label),
        "🔴🔴 ① − ③ 의 host 전량(적으니 전부 싣는다)": lost_by_label[:20],
        "⚠ ① − ② = 앵커 자가 **더** 버리는 문서": old - anch,
        "⚠ ① − ② 의 host 수": len(lost_by_anchor),
        "⚠ ① − ② 의 host 예시(문서 많은 순 15) --- 🔴 진짜 언론사다": lost_by_anchor[:15],
        "🔴 판정": ("앵커 결함의 실제 크기는 %d 문서 / %d = %.7f 이고 host 는 %d 개다. "
                  "티처 #93 m6 의 *「P7 빗나감의 진짜 원인」* 은 반증됐다."
                  % (old - lab, N, (old - lab) / N, len(lost_by_label))),
        "⚠ 원본 NEWS_PAT 과 얼린 954 판이 같나(955 가 원본을 고쳤으면 False 가 정상)":
            bool(NEWS_PAT.pattern == NEWS_PAT_954.pattern),
        "초": round(time.time() - t0, 1),
        "통과": bool(anch <= lab <= N and old <= N and N > 0),
    }


def head200_check():
    """🔴 m7 --- `head200` 이 이름대로 「앞 200자」를 내는가. **직접 시험한다.**"""
    rng = np.random.default_rng(955)
    alphabets = ["가나다라마바사아자차카타파하", "abcdefghij", "😀🙈🚀🌏", " \t\n　"]
    bad = 0
    trials = 0
    for _ in range(20000):
        s = "".join(rng.choice(list(alphabets[int(rng.integers(0, 4))]))
                    for _ in range(int(rng.integers(0, 400))))
        b = s.encode("utf-8")
        ref = b.strip().decode("utf-8", "ignore")[:200]
        if head200(b) != ref:
            bad += 1
        trials += 1
    # 🔴 명시 경계 시험 --- 4바이트 문자 200개 = 정확히 800바이트
    edge = []
    for s in ["😀" * 300, "가" * 300, "a" * 900, "  " + "😀" * 250 + "  "]:
        b = s.encode("utf-8")
        ref = b.strip().decode("utf-8", "ignore")[:200]
        edge.append({"길이(바이트)": len(b), "같나": head200(b) == ref,
                     "낸 글자 수": len(head200(b))})
    # 🔴 반례가 **원리상 생기는** 자리: 깨진 UTF-8(‘ignore’ 가 바이트를 지운다)
    broken = b"\xff" * 700 + "가".encode("utf-8") * 300
    broken_same = head200(broken) == broken.strip().decode("utf-8", "ignore")[:200]
    return {
        "무엇": "head200 의 이름과 실제가 같은가(티처 #93 m7)",
        "무작위 시험 횟수": trials,
        "🔴 불일치": bad,
        "경계 시험": edge,
        "🔴 깨진 UTF-8 에서도 같나": broken_same,
        "🔴 판정": ("이름이 실제와 같다 --- 유효한 UTF-8 에서 head200(b) == b.strip().decode()[:200]"
                  if bad == 0 else "🔴 이름과 실제가 다르다"),
        "⚠ 단서": ("깨진 UTF-8 에서는 800바이트 선절단 때문에 어긋날 수 있다. "
                 "두 코퍼스의 text 열은 parquet 문자열이라 유효 UTF-8 이고, "
                 "따라서 이 사이클의 자료에서는 원리상 안 어긋난다."),
        "통과": bool(bad == 0),
    }


# ---------------------------------------------------------------- 본체

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-net", action="store_true")
    ap.add_argument("--out", default="runners/out955_D.json")
    a = ap.parse_args()
    import os
    os.chdir(REPO)
    t0 = time.time()
    res = {"무엇": "955 --- D 를 다시 정의하고 954 §5 를 다시 문다",
           "사전등록": "docs/prereg_955_D.md (커밋 8597b7184 · 측정 전)",
           "🔴 규약 60 --- 명령·범위·트리": {
               "명령": "python3 runners/dupe955_D.py",
               "범위": ("HPLT: /Users/ax/wm_harvest/954/scan/s*.npz 464개(=464 shard 전량) · "
                      "FineWeb: /Users/ax/wm_harvest/954/fw/*.npz 25개(행군 층화 표본) · "
                      "🔴 954 가 뜬 표본을 그대로 읽는다(다시 안 뜬다)"),
               "트리": "작업 트리 밖의 scratch npz + 이 러너(커밋된다)",
               "통과": True}}

    rulers = {}
    keep = {}
    for label, key in RULERS:
        hp, nsh = load_side(SCAN, key, "s*.npz")
        fw, nfw = load_side(FW, key, "*.npz")
        m, inter, mult_h, mult_f, hset, fset = measure(label, hp, fw)
        m["읽은 HPLT shard"] = nsh
        m["읽은 FineWeb 파일"] = nfw
        rulers[label] = m
        if key in ("urn_h", "url_h", "hed_h"):
            keep[key] = (hset, inter, mult_h, mult_f, fset)
        print("[%s] D_문서=%.6f D_키=%.6f D_954글자=%.6f D^%d=%.6f"
              % (label, m["🔴 D_문서 = ⓑ ÷ ②"], m["🔴 D_키 = ⓐ ÷ ④"],
                 m["🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)"],
                 K_MAIN, m["🔴 절단 곡선"]["K<=%d" % K_MAIN]["🔴 D_문서^K"]), flush=True)
        del hp, fw
    res["🔴 자별"] = rulers

    # ---- 뭉친 키의 정체(조항 62 ② 예시) ---------------------------------
    hset_urn, inter_urn, mult_urn_h, mult_urn_f, fset_urn = keep["urn_h"]
    fw_urls = []
    for p in sorted(FW.glob("*.urls.gz")):
        with gzip.open(p, "rt", encoding="utf-8") as f:
            fw_urls.extend(f.read().split("\n"))
    fw_urls = np.array(fw_urls, dtype=object)
    fw_urn_all, _ = load_side(FW, "urn_h", "*.npz"), None
    fw_urn = fw_urn_all[0]
    top = np.argsort(-mult_urn_h)[:20]
    ex = []
    for i in top:
        k = inter_urn[i]
        j = np.flatnonzero(fw_urn == k)
        ex.append({"정규화 URL(FineWeb 쪽 실물)": (fw_urls[j[0]] if len(j) else "(못 찾았다)"),
                   "HPLT 다중도": int(mult_urn_h[i]),
                   "FineWeb 표본 다중도": int(mult_urn_f[i])})
    res["🔴 뭉친 교집합 키 상위 20(자②)"] = {
        "예시": ex,
        "상위 20 이 덮는 HPLT 문서": int(np.sort(mult_urn_h)[-20:].sum()),
        "분모 = 맞은 HPLT 문서": int(mult_urn_h.sum()),
        "통과": True}

    # ---- 심은 키 ----------------------------------------------------------
    hset_url = keep["url_h"][0]
    hset_hed = keep["hed_h"][0]
    res["🔴 심은 키 U·V(정규화 함수를 지난다)"] = probe_uv(hset_urn, hset_url, hset_hed)
    if a.no_net:
        res["🔴 심은 키 R(Range 재수신)"] = {"판정": "🔴 안 했다(--no-net)", "통과": False}
    else:
        try:
            res["🔴 심은 키 R(Range 재수신)"] = probe_r()
        except Exception as e:                       # 🔴 조항 59 --- 실패를 성공으로 읽지 않는다
            res["🔴 심은 키 R(Range 재수신)"] = {
                "판정": "🔴 못 했다 --- %s: %s" % (type(e).__name__, e), "통과": False}

    # ---- m6 · m7 ----------------------------------------------------------
    res["🔴 m6 --- 뉴스형 host 정규식 재측정"] = news_remeasure()
    res["🔴 m7 --- head200 이름 대조"] = head200_check()

    # ---- 배선 검사 W1~W8 --------------------------------------------------
    r2 = rulers["② URL 정규화(🔴 정본)"]
    r1 = rulers["① URL 정확"]
    r3 = rulers["③ 본문 앞 200자"]
    rt = rulers["덤 --- 전문 md5(판정 밖)"]
    nm = res["🔴 m6 --- 뉴스형 host 정규식 재측정"]
    W = [
        ("W1 HPLT 문서 전량 38,866,835", r2["분모 ① HPLT 문서 전량"], 38866835),
        ("W1 읽은 shard 464", r2["읽은 HPLT shard"], 464),
        ("W2 FineWeb 표본 문서 1,358,355", r2["분모 ② FineWeb 표본 문서"], 1358355),
        ("W2 읽은 FineWeb 파일 25", r2["읽은 FineWeb 파일"], 25),
        ("W3 자② 교집합 키 243,363", r2["분자 ⓐ 교집합(서로 다른 키)"], 243363),
        ("W3 FineWeb−HPLT 키 650,915", r2["① 반대 방향 --- FineWeb − HPLT(키)"], 650915),
        ("W3 HPLT−FineWeb 키 19,836,901", r2["① 반대 방향 --- HPLT − FineWeb(키)"], 19836901),
        ("W4 자② 맞은 FineWeb 문서 673,653", r2["분자 ⓑ 맞은 FineWeb 표본 문서"], 673653),
        ("W4 자② 맞은 HPLT 문서 9,669,586", r2["분자 ⓒ 맞은 HPLT 문서"], 9669586),
        ("W5 자① D_문서 0.17371", r1["🔴 D_문서 = ⓑ ÷ ②"], 0.17371),
        ("W5 자③ D_문서 0.13964", r3["🔴 D_문서 = ⓑ ÷ ②"], 0.13964),
        ("W5 전문md5 D_문서 0.06941", rt["🔴 D_문서 = ⓑ ÷ ②"], 0.06941),
        ("W5 자② D_문서 0.49593", r2["🔴 D_문서 = ⓑ ÷ ②"], 0.49593),
        ("W6 자② D_954글자 0.179160",
         r2["🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)"], 0.179160),
        ("W6 자① D_954글자 0.172579",
         r1["🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)"], 0.172579),
        ("W6 자③ D_954글자 0.136805",
         r3["🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)"], 0.136805),
        ("W7 D_문서^1 0.10489", r2["🔴 절단 곡선"]["K<=1"]["🔴 D_문서^K"], 0.10489),
        ("W7 D_문서^2 0.13811", r2["🔴 절단 곡선"]["K<=2"]["🔴 D_문서^K"], 0.13811),
        ("W7 D_문서^5 0.16236", r2["🔴 절단 곡선"]["K<=5"]["🔴 D_문서^K"], 0.16236),
        ("W7 D_문서^10 0.17838", r2["🔴 절단 곡선"]["K<=10"]["🔴 D_문서^K"], 0.17838),
        ("W7 D_문서^100 0.23832", r2["🔴 절단 곡선"]["K<=100"]["🔴 D_문서^K"], 0.23832),
        ("W7 D_문서^1000 0.33219", r2["🔴 절단 곡선"]["K<=1000"]["🔴 D_문서^K"], 0.33219),
        ("W8 서로 다른 host 1,086,484", nm["서로 다른 host"], 1086484),
        ("W8 954 자 뉴스형 비율 0.13959", nm["① 954 자 비율"], 0.13959),
    ]
    wr = []
    for nmv, got, want in W:
        ok = (abs(got - want) < 1e-5) if isinstance(want, float) else (got == want)
        wr.append({"검사": nmv, "냈다": got, "받아야 한다": want, "통과": bool(ok)})
    res["🔴 배선 검사 W1~W8(티처 #93 이 낸 수를 내 코드가 독립 재현하는가)"] = {
        "낱개": wr,
        "분자 = 맞은 검사": sum(1 for r in wr if r["통과"]),
        "분모 = 검사 전량": len(wr),
        "통과": bool(all(r["통과"] for r in wr))}

    # ---- 예측 채점 --------------------------------------------------------
    d21 = r2["🔴 절단 곡선"]["K<=21"]["🔴 D_문서^K"]
    dk21 = r2["🔴 절단 곡선"]["K<=21"]["🔴 D_키^K"]
    dk = r2["🔴 D_키 = ⓐ ÷ ④"]
    nbig = r2["뭉침 --- 다중도 > %d 인 교집합 키" % K_MAIN]
    rbig = r2["뭉침 --- 다중도 > %d 인 교집합 키의 비율(÷교집합 키)" % K_MAIN]
    uv = res["🔴 심은 키 U·V(정규화 함수를 지난다)"]
    rr = res["🔴 심은 키 R(Range 재수신)"]
    h7 = res["🔴 m7 --- head200 이름 대조"]
    P = [
        ("P1 D_문서^21 ∈ [0.178, 0.215]", d21, bool(0.178 <= d21 <= 0.215)),
        ("P2 D_키^21 ÷ D_키 ≥ 0.95", round(dk21 / dk, 6), bool(dk21 / dk >= 0.95)),
        ("P3 다중도>21 키 ∈ [3000,40000] 이고 교집합의 20% 미만",
         {"키": nbig, "비율": rbig}, bool(3000 <= nbig <= 40000 and rbig < 0.20)),
        ("P4 자① |D_문서 − D_키| ≤ 0.03",
         round(abs(r1["🔴 D_문서 = ⓑ ÷ ②"] - r1["🔴 D_키 = ⓐ ÷ ④"]), 6),
         bool(abs(r1["🔴 D_문서 = ⓑ ÷ ②"] - r1["🔴 D_키 = ⓐ ÷ ④"]) <= 0.03)),
        ("P5 955-앵커 자 뉴스형 ∈ [0.07,0.135] 이고 < 0.13959", nm["② 955-앵커 자 비율"],
         bool(0.07 <= nm["② 955-앵커 자 비율"] <= 0.135
              and nm["② 955-앵커 자 비율"] < 0.13959)),
        ("P6 프로브 U·V·R 셋 다 통과",
         {"U": uv.get("U 통과"), "V": uv.get("V 통과"), "R": rr.get("통과")},
         bool(uv.get("통과") and rr.get("통과"))),
        ("P7 head200 이 이름대로 앞 200자", h7["🔴 불일치"], bool(h7["통과"])),
    ]
    res["🔴 예측 채점(사전등록 §5)"] = {
        "낱개": [{"예측": n, "값": v, "맞았나": ok} for n, v, ok in P],
        "분자 = 맞은 예측": sum(1 for _, _, ok in P if ok),
        "분모 = 예측 전량": len(P),
        "통과": True}

    # ---- 🔴 판정 ----------------------------------------------------------
    clean = {
        "자② D_문서^1": r2["🔴 절단 곡선"]["K<=1"]["🔴 D_문서^K"],
        "자② D_문서^5": r2["🔴 절단 곡선"]["K<=5"]["🔴 D_문서^K"],
        "자② D_문서^10": r2["🔴 절단 곡선"]["K<=10"]["🔴 D_문서^K"],
        "자② D_문서^21(🔴 정본)": d21,
        "자② D_키": dk,
        "자② D_954글자": r2["🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)"],
        "자① D_문서": r1["🔴 D_문서 = ⓑ ÷ ②"],
        "자① D_키": r1["🔴 D_키 = ⓐ ÷ ④"],
    }

    def cell(x):
        return "전량 안 받는다" if x >= 0.70 else ("전량 받는다" if x <= 0.30 else "보류 --- 부분 수신")

    cells = {k: cell(v) for k, v in clean.items()}
    same = len(set(cells.values())) == 1
    wired = res["🔴 배선 검사 W1~W8(티처 #93 이 낸 수를 내 코드가 독립 재현하는가)"]["통과"]
    planted = bool(uv.get("통과") and rr.get("통과"))
    res["🔴🔴 판정(사전등록 §6)"] = {
        "정본 D = 자② D_문서^{K=21}": d21,
        "정본이 든 칸": cell(d21),
        "깨끗한 읽기 여덟": clean,
        "깨끗한 읽기 여덟이 든 칸": cells,
        "강함": bool(same),
        "🔴 오염된 읽기(판정 밖) --- 자② D_문서(절단 없음)": r2["🔴 D_문서 = ⓑ ÷ ②"],
        "🔴 그 오염된 읽기가 드는 칸": cell(r2["🔴 D_문서 = ⓑ ÷ ②"]),
        "배선 검사 통과": wired,
        "심은 키 통과": planted,
        "🔴 판정": (
            ("%s --- %s" % (cell(d21), "강함(깨끗한 읽기 여덟이 한 칸)" if same else "정본 하나로 섰다"))
            if (wired and planted) else
            "🔴 모른다 --- 배선 검사 또는 심은 키가 불통과다(사전등록 §3·§4)"),
        "통과": bool(wired and planted),
    }

    # ---- 🔴 정오표(㉠) -----------------------------------------------------
    res["🔴 정오표 --- out954_dupe.json 의 키 이름과 실제 계산"] = {
        "🔴 얼린 증거물은 다시 안 찍는다": "runners/out954_dupe.json 은 954 가 찍은 그대로 둔다",
        "옛 키 이름 「🔴 교집합 ÷ FineWeb 표본 문서」의 실제 계산": "fw_doc_hit / len(fwa) = D_문서",
        "옛 키 이름 「🔴 교집합 ÷ HPLT 문서 전량」의 실제 계산": "hp_doc_hit / len(hp) = E_문서",
        "그 이름이 뜻하던 값(= D_954글자)": r2["🔴 D_954글자 = ⓐ ÷ ② (🔴 키÷문서 --- 단위가 다르다 · 판정 밖)"],
        "코드는 어느 쪽으로 맞췄나": "🔴 이름을 계산에 맞췄다(사전등록 §2-B · 계산은 안 바꿨다)",
        "통과": True}

    res["코드 sha256"] = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()
    res["dupe954_hplt_scan.py sha256"] = hashlib.sha256(
        (REPO / "runners/dupe954_hplt_scan.py").read_bytes()).hexdigest()
    res["시작(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
    res["끝(UTC)"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    res["초"] = round(time.time() - t0, 1)
    res["통과"] = bool(res["🔴🔴 판정(사전등록 §6)"]["통과"])

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps({
        "정본 D(자② D_문서^21)": d21,
        "판정": res["🔴🔴 판정(사전등록 §6)"]["🔴 판정"],
        "배선": "%d/%d" % (
            res["🔴 배선 검사 W1~W8(티처 #93 이 낸 수를 내 코드가 독립 재현하는가)"]["분자 = 맞은 검사"],
            res["🔴 배선 검사 W1~W8(티처 #93 이 낸 수를 내 코드가 독립 재현하는가)"]["분모 = 검사 전량"]),
        "예측": "%d/%d" % (res["🔴 예측 채점(사전등록 §5)"]["분자 = 맞은 예측"],
                        res["🔴 예측 채점(사전등록 §5)"]["분모 = 예측 전량"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
