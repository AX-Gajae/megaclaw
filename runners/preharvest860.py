# -*- coding: utf-8 -*-
# 노트 860 — 수확 전 완결 3시험 (사전등록 '860' · 라벨 무접촉)
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.stats import rankdata, spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from lab import pairboot as PB  # noqa: E402
from runners.harvest844b import norm_title  # noqa: E402 — 진단 사이드카의 정규화기 재사용

t0 = time.time()
ROOT = Path("/Users/ax/world_model")
KOBIS_DIR = ROOT / "cycle_log/forward/kobis"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
      "Accept-Language": "ko-KR,ko;q=0.9"}

seal = json.load(open(KOBIS_DIR / "seal_2026-08-08.json"))
films = seal["작품"]
scores = np.array([m["yhat_log10_21일누적"] for m in films])
codes = [m["code"] for m in films]

# ── ⓐ 동점 민감도(합성 라벨 1,000뽑기 × 타이브레이크 3규칙) ──────
rng = np.random.default_rng(860)
r_code = rankdata([-s for s in scores], method="ordinal")            # 실제로는 argsort+코드 — 근사 병기
order_code = sorted(range(30), key=lambda i: (-scores[i], codes[i]))
rank_code = np.empty(30)
rank_code[order_code] = np.arange(1, 31)
rank_mid = rankdata([-s for s in scores], method="average")          # 평균순위
diffs = []
for k in range(1000):
    y_syn = -rank_mid + rng.normal(0, 6, 30)                          # 그럴듯한 합성 라벨
    perm = rng.permutation(30)                                        # 무작위 타이브레이크: 동점 안 섞기
    order_rnd = sorted(range(30), key=lambda i: (-scores[i], perm[i]))
    rank_rnd = np.empty(30)
    rank_rnd[order_rnd] = np.arange(1, 31)
    rhos = [float(spearmanr(-r, y_syn)[0]) for r in (rank_code, rank_rnd, rank_mid)]
    diffs.append(max(rhos) - min(rhos))
p95 = float(np.percentile(diffs, 95))
p50 = float(np.percentile(diffs, 50))
print(f"ⓐ 동점 민감도: |Δρ| p50 {p50:.4f} · p95 {p95:.4f}", flush=True)

# ── ⓑ 문간 제목 실측(개봉일람 대 상세 페이지 · 코드 키) ──────────
def detail_title(code):
    data = urllib.parse.urlencode({"code": code, "titleYN": "Y", "isOuterReq": "false"}).encode()
    req = urllib.request.Request(
        "https://www.kobis.or.kr/kobis/business/mast/mvie/searchMovieDtl.do",
        data=data, headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    h = ""
    for attempt in range(3):                      # 재시도(네트워크 리셋 1회 실측)
        try:
            h = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
            break
        except Exception:
            time.sleep(3 * (attempt + 1))
    m = re.search(r'<strong class="tit">([^<]{1,120})</strong>', h)
    return (m.group(1).strip() if m else "")


pairs = []
n_exact = n_norm = 0
for m in films:
    dt_ = detail_title(m["code"])
    dt_clean = re.sub(r"\([^)]*\)\s*$", "", dt_).strip()
    exact = dt_clean == m["제목"].strip()
    normed = norm_title(dt_clean) == norm_title(m["제목"])
    n_exact += exact
    n_norm += normed
    if not normed:
        pairs.append({"code": m["code"], "일람": m["제목"], "상세": dt_})
    time.sleep(1.5)
print(f"ⓑ 문간 제목: 정확 {n_exact}/30 · 정규화 후 {n_norm}/30 · 불일치 {pairs}", flush=True)

# ── ⓓ 859 percentile 재계산(자백 정정 · 동결 행 벡터 · seed 827) ──
R = json.load(open(ROOT / "runners/out859_rows.json"))
rows = R["행"]
yv = np.array([r["y"] for r in rows])
ens = np.array([r["champ_ens"] for r in rows])
tb = np.array([r["tabpfn_ens"] for r in rows])
ALIAS = json.load(open(ROOT / "data/lab/idol_agency_alias_v1.json"))["별칭"]
from ingest.idol_axes import norm_agency  # noqa: E402


def key(raw):
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s in ALIAS:
        return ALIAS[s]
    seg = re.split(r"\s*[\(（]", s)[0].strip()
    if seg in ALIAS:
        return ALIAS[seg]
    n = norm_agency(seg)
    return ALIAS.get(n, n)


groups = {}
solo = 0
for i, r in enumerate(rows):
    k = key(r["agency"])
    if k is None:
        groups[f"_s{solo}"] = [i]
        solo += 1
    else:
        groups.setdefault(k, []).append(i)
cl = [np.array(v) for v in groups.values()]


def rho2(p, y):
    ok = np.isfinite(p) & np.isfinite(y)
    return float(spearmanr(p[ok], y[ok])[0])


def stat(idx):
    return rho2(tb[idx], yv[idx]) - rho2(ens[idx], yv[idx])


def perc(clusters, seed=827, B=10000):
    rg = np.random.default_rng(seed)
    vals = []
    n_cl = len(clusters)
    for _ in range(B):
        pick = rg.integers(0, n_cl, n_cl)
        idx = np.concatenate([clusters[j] for j in pick])
        if len(np.unique(yv[idx])) < 5:
            continue
        vals.append(stat(idx))
    v = np.array(vals)
    lo, hi = float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))
    se_end = float(np.std(v, ddof=1)) * 1.36 / np.sqrt(len(v))       # 끝점 SE 근사(질서통계)
    return lo, hi, se_end, len(v)


lo_c, hi_c, se_c, B_c = perc(cl)
cl_s, _ = PB.solo_clusters(len(rows))
lo_s, hi_s, se_s, B_s = perc(cl_s)
print(f"ⓓ percentile 군집 [{lo_c:+.4f},{hi_c:+.4f}](끝점SE~{se_c:.4f}) · 무군집 [{lo_s:+.4f},{hi_s:+.4f}](~{se_s:.4f})", flush=True)
repro = abs(lo_c - (-0.0131)) < 0.005 and abs(lo_s - (-0.0202)) < 0.005

# ── ⓒ+ⓔ 규칙 동결(annex6) ───────────────────────────────────────
annex6 = {
    "작성일": "2026-08-08", "성격": "수확 전 완결 동결(860) — 정본·기존 annex 불변",
    "연기 귀속 규칙": "연기 감지(844b 진단) 시 원봉인 개봉일 기준 검열 처리 유지(재배정 금지 — 봉인 문면 불변) · 진단 보고서에 '연기 N편' 병기 · 연기 ≥5편이면 수확 보고에 '명단 안정성 경고' 문단 의무",
    "두 봉인 중복 규칙": "후봉인(seal2)은 선봉인 코드 제외(코드로 이행) · 합산(≥60) 시 코드 중복은 선봉인 소속으로 단일 계상",
    "동점 민감도(합성 1000뽑기)": {"p50": round(p50, 4), "p95": round(p95, 4),
        "판정": ("현행 타이브레이크 유지" if p95 <= 0.02 else
                 ("평균순위 병기 승격" if p95 > 0.05 else "중간 — p95 병기"))},
    "문간 제목 실측": {"정확": n_exact, "정규화 후": n_norm, "불일치": pairs},
    "859 percentile 정정 커밋": {"군집": [round(lo_c, 4), round(hi_c, 4)], "무군집": [round(lo_s, 4), round(hi_s, 4)],
        "끝점 SE": [round(se_c, 4), round(se_s, 4)], "임시 실행 재현": bool(repro),
        "무군집 BCa 하한 +0.0001 판독": f"끝점 SE ~{se_s:.4f} — '오차 안' 판독의 수치 근거(재량 아님을 소급 증빙)"},
    "잔여 정직": "harvest844 판정문 조립 ~30줄은 9/28 첫 실행(동결 수정 금지 — 크래시 시 harvest844b 진단 + 사이드카 경로)",
}
with open(KOBIS_DIR / "annex6_2026-08-08.json", "x") as fh:
    json.dump(annex6, fh, ensure_ascii=False, indent=1)

out = {"ⓐ": annex6["동점 민감도(합성 1000뽑기)"], "ⓑ": {"정확": n_exact, "정규화": n_norm},
       "ⓓ 재현": bool(repro), "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out860_preharvest.json", "w"), ensure_ascii=False, indent=1)
