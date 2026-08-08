# -*- coding: utf-8 -*-
"""노트 858 — 봉인 2호 러너(재사용 가능 · 날짜 파라미터화).

seal844 의 로직에 858 봉합을 얹었다:
  · **spec None assert 복원**(사전등록 857ⓒ 문면 — seal844 실물은 기록만이었다)
  · 날짜 파라미터(--today · --open-max · --months)
  · 조용한 기본값 체크리스트 실행 기록(페이지 크기·클립·MIN_TRAIN — 봉인 파일에)
  · 동점 타이브레이크 명문: 예측 순위 동점은 영화 코드 오름차순(854 설계 동결)
  · --plan: 명단 수집·확보율만 보고(적합·봉인 없음 — 드라이런)

    python3 runners/seal2.py --plan --months 2026-09,2026-10
    python3 runners/seal2.py --seal --today 2026-09-01 --open-max 2026-09-30
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
ROOT = Path("/Users/ax/world_model")
SEALDIR = ROOT / "cycle_log/forward/kobis"
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9"}
SLEEP = 1.5
CHECKLIST = {"개봉일람 페이지 크기": "viewEa=100 · 신규 0 이면 종료(페이징 검증 851 절단 교훈)",
             "TRAINW 클립 하한": "0.2 — 영화는 TRAINW 등재(837)라 무관",
             "MIN_TRAIN": "15 — 봉인은 적합 아님·무관",
             "타이브레이크": "예측 순위 동점 = 영화 코드 오름차순"}


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def open_schedule(month):
    out = {}
    for page in range(1, 8):
        b = post("https://www.kobis.or.kr/kobis/business/mast/mvie/findOpenScheduleList.do",
                 {"openDt": month, "viewEa": "100", "pageIndex": str(page)})
        items = re.findall(
            r"mstView\('movie','(\d+)'\);return false;\" >([^<]+)</a>.*?"
            r"개봉예정일\s*</dt>\s*<dd>\s*<span>\s*([\d-]+)", b, re.S)
        new = 0
        for code, title, od in items:
            if code not in out:
                out[code] = {"code": code, "제목": html.unescape(title).strip(), "개봉일": od}
                new += 1
        if new == 0:
            break
        time.sleep(SLEEP)
    return out


def plan(months, today, open_max):
    movies = {}
    for month in months:
        movies.update(open_schedule(month))
    pool = [m for m in movies.values() if today < m["개봉일"] <= open_max]
    out = {"수집": len(movies), "개봉 전 풀": len(pool),
           "명단": [(m["제목"], m["개봉일"]) for m in sorted(pool, key=lambda x: x["개봉일"])[:40]]}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return pool


def seal(months, today, open_max):
    from ingest.kobis import movie_detail
    from lab import guards as G, sideaudit
    from lab.forms import REGISTRY

    t0 = time.time()
    pool = plan(months, today, open_max)
    if not pool:
        raise SystemExit("⛔ 개봉 전 풀 0 — 봉인 불가(그 사실만 기록)")
    for i, m in enumerate(pool):
        try:
            m.update(movie_detail(m["code"]))
        except Exception as e:
            m["⛔상세"] = str(e)[:80]
        time.sleep(SLEEP)

    # 축 사상(836 규칙 · v1 사전) — seal844 와 동일
    def grade_val(g):
        g = str(g or "")
        if "전체" in g:
            return 0.0
        if "12" in g:
            return 0.33
        if "15" in g:
            return 0.67
        if "청소년" in g or "제한" in g or "18" in g or "불가" in g:
            return 1.0
        return None

    def clean_dist(s):
        s = html.unescape(str(s or ""))
        s = re.sub(r"\s+", " ", s).strip()
        s = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", s)[0].strip()
        s = re.split(r"\s*(?:제공|배급)\s*$", s)[0].strip()
        mm = re.match(r"([가-힣0-9()주식회사㈜\s]+)", s)
        cand = mm.group(1).strip() if mm else ""
        core = re.sub(r"[()㈜\s]|주식회사", "", cand)
        return (cand if len(core) >= 2 else s).rstrip("( ").strip()[:30]

    raw = [json.loads(l) for l in open(ROOT / "data/ingest/kobis/axes_raw_897.jsonl")]
    tc = {}
    for r in raw:
        if "⛔" not in r and r.get("code") and r["개봉일"] < "2025-01-01" and r.get("배급사"):
            k = clean_dist(r["배급사"])
            tc[k] = tc.get(k, 0) + 1
    ranked = sorted(tc.values())

    def dist_pct(name):
        k = clean_dist(name) if name else None
        if not k or k not in tc:
            return None
        return float(np.searchsorted(ranked, tc[k], side="right") / len(ranked))

    ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
    for m in pool:
        genres = [g for g in str(m.get("장르") or "").split(",") if g.strip()]
        tb = min(len(genres), 4) / 4 if genres else None
        vp = dist_pct(m.get("배급사")) if m.get("배급사") else None
        ef = grade_val(m.get("등급"))
        m["axes"] = {"target_breadth": tb if tb is not None else 0.5,
                     "venue_prominence": vp if vp is not None else 0.5,
                     "entry_friction": ef if ef is not None else 0.5,
                     "media_push": 0.5, "goods_scale": 0.5}
        m["mask"] = {"target_breadth": float(tb is not None), "venue_prominence": float(vp is not None),
                     "entry_friction": float(ef is not None), "media_push": 0.0, "goods_scale": 0.0}

    data12 = sideaudit.champion_data()
    names = list(data12.names["영화"])
    X = np.full((len(pool), len(names)), 0.5)
    Mx = np.zeros((len(pool), len(names)))
    for j, a in enumerate(names):
        if a in ALL5:
            X[:, j] = [m["axes"][a] for m in pool]
            Mx[:, j] = [m["mask"][a] for m in pool]
    tx = np.array([float(m["개봉일"][:4]) for m in pool])
    cls = REGISTRY["F18_bagboost"]["cls"]
    preds, spec_picks = [], []
    T = 2025.0
    for s in range(12):
        f = G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s)
        sp = f.spec.get("영화")
        spec_picks.append(str(sp))
        #: 🔴 857ⓒ 문면 복원 — 등가(856 규약 ⑥)의 전제를 코드로 강제.
        assert sp is None, f"spec('영화') 활성({sp}) — 레짐 등가 붕괴: 단독-배치 밴드 별도 산출 필요"
        preds.append(np.asarray(f.predict("영화", X, Mx, tx), float))
        print(f"  씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
    yhat = np.nanmean(preds, axis=0)
    # 타이브레이크 명문: (−점수, 코드) 오름차순
    order = sorted(range(len(pool)), key=lambda i: (-yhat[i], pool[i]["code"]))
    rank = {i: k + 1 for k, i in enumerate(order)}

    today_s = today
    sealp = SEALDIR / f"seal_{today_s}.json"
    code_sha = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
    git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                             cwd=ROOT).stdout.strip()[:12]
    seal_doc = {
        "봉인일": today_s, "층": "갑(개봉 전 청정)",
        "작품": [{"code": m["code"], "제목": m["제목"], "개봉일": m["개봉일"],
                  "장르": m.get("장르"), "등급": m.get("등급"), "배급사": m.get("배급사"),
                  "axes": m["axes"], "mask": m["mask"],
                  "예측 점수(자루 평균 순위)": round(float(yhat[i]), 4),
                  "예측 순위": rank[i]} for i, m in enumerate(pool)],
        "모형 지문": {"form": "F18_bagboost 합동(12도메인)", "T": T, "씨앗": list(range(12)),
                     "spec 픽(영화·씨앗별)": spec_picks, "코드 sha256": code_sha, "git": git_sha},
        "조용한 기본값 체크리스트": CHECKLIST,
        "채점": "harvest844.py(동결) + harvest844b.py 진단 사이드카 — 규칙 동일(836 라벨·검열 14·문턱 0.2046 은 1호 전용 · 2호 밴드는 봉인 후 같은 절차로 산출)",
    }
    with open(sealp, "x") as fh:
        json.dump(seal_doc, fh, ensure_ascii=False, indent=1)
    print(f"봉인 완료 — {sealp} · {len(pool)}편")
    return seal_doc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--seal", action="store_true")
    ap.add_argument("--months", default="2026-09,2026-10")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--open-max", dest="open_max", default="2026-10-15")
    a = ap.parse_args()
    months = a.months.split(",")
    if a.plan:
        plan(months, a.today, a.open_max)
    elif a.seal:
        seal(months, a.today, a.open_max)
    else:
        print("사용: --plan | --seal")
