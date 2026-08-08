# -*- coding: utf-8 -*-
# 노트 863 — 게임 봉인 노크 day0 (사전등록 '863' · 무캐시 · 기존 수집기 3종 불변)
import datetime as dt
import json
import re
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from ingest.game_sample import _get  # noqa: E402 — 무캐시 HTTP(재시도만)

t0 = time.time()
ROOT = Path("/Users/ax/world_model")
NOW_UTC = dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"
SEARCH = ("https://store.steampowered.com/search/results/?query&count=50"
          "&category1=998&infinite=1&json=1&cc=kr&l=korean"
          "&filter=comingsoon&start={start}")


def granularity(s):
    """예정일 원문 → (입도, 표준일 or None). parse_date 재사용 금지(오파싱 실측)."""
    s = str(s or "").strip()
    if not s:
        return "미정", None
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", s)
    if m:
        return "일", f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})\s*(?:월|Mar|Jan|Feb|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\d]*(\d{4})", s)
    m2 = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월(?!.*일)", s)
    if m2:
        return "월", f"{m2.group(1)}-{int(m2.group(2)):02d}"
    if re.search(r"분기|Q[1-4]", s):
        return "분기", None
    if re.fullmatch(r".*(\d{4})\s*년?.*", s) and not re.search(r"월|일", s):
        return "연", None
    return "미정", None


# ── ⓑ day0 코호트 수집 ───────────────────────────────────────────
cohort = []
total_count = None
start = 0
while len([c for c in cohort if c["입도"] == "일"]) < 150 and start <= 4000:
    d = _get(SEARCH.format(start=start))
    if not d:
        break
    if total_count is None:
        total_count = d.get("total_count")
    html_blob = d.get("results_html") or ""
    blocks = re.split(r'data-ds-appid="', html_blob)[1:]
    items = []
    for b in blocks:
        mid = re.match(r"(\d+)", b)
        mt = re.search(r'<span class="title">([^<]{1,120})</span>', b)
        mr = re.search(r'search_released[^>]*>\s*([^<]{0,60})<', b)
        if mid and mt:
            items.append((mid.group(1), mt.group(1), (mr.group(1) if mr else "")))
    if not items:
        break
    for appid, title, rel in items:
        g, std = granularity(rel)
        cohort.append({"appid": appid, "제목": title.strip(), "예정일 원문": rel.strip(),
                       "입도": g, "표준일": std, "_offset": start})
    start += 50
    time.sleep(1.2)
by_g = {}
for c in cohort:
    by_g[c["입도"]] = by_g.get(c["입도"], 0) + 1
n_day = by_g.get("일", 0)
print(f"day0 코호트 {len(cohort)} · total {total_count} · 입도 {by_g} ({time.time()-t0:.0f}s)", flush=True)

# appdetails 교차 20건(coming_soon 비율)
rng = np.random.default_rng(863)
pick = rng.choice(len(cohort), size=min(20, len(cohort)), replace=False)
n_cs = n_chk = 0
detail_snap = {}
for i in pick:
    appid = cohort[int(i)]["appid"]
    d = _get(f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=kr&l=korean")
    time.sleep(1.2)
    try:
        dd = d[str(appid)]["data"]
    except Exception:
        continue
    n_chk += 1
    rdi = dd.get("release_date") or {}
    if rdi.get("coming_soon"):
        n_cs += 1
    detail_snap[appid] = {"coming_soon": bool(rdi.get("coming_soon")),
                          "date 원문": rdi.get("date"),
                          "price_overview_none": dd.get("price_overview") is None,
                          "is_free": dd.get("is_free")}
cs_rate = n_cs / max(n_chk, 1)
print(f"appdetails 교차 {n_chk}건 · coming_soon 비율 {cs_rate:.2f}", flush=True)

day0 = {"수집 시각(UTC)": NOW_UTC, "total_count": total_count,
        "코호트": cohort, "입도 분포": by_g,
        "appdetails 교차": {"n": n_chk, "coming_soon 비율": round(cs_rate, 3), "표본": detail_snap},
        "day7 재수집": "2026-08-15 이후 · 무캐시 · 갈래는 사전등록 863ⓒ(절대 문턱) 동결분"}
with open(ROOT / "runners/out863_day0.json", "x") as fh:
    json.dump(day0, fh, ensure_ascii=False, indent=1)

# ── ⓐ y_w30 정본화 게이트(기출시 30행 표본 · 무캐시) ─────────────
GR = json.load(open(ROOT / "data/state/game_recent.json"))
rows = [r for r in (GR.values() if isinstance(GR, dict) else GR)
        if not r.get("y_w30_truncated") and r.get("y_w30") is not None and r.get("release_date")]
print(f"비절단 행 {len(rows)}", flush=True)
samp = rng.choice(len(rows), size=min(30, len(rows)), replace=False)


def w30_epoch(appid, rd, tz_utc):
    d0 = dt.date.fromisoformat(rd)
    end = d0 + dt.timedelta(days=30)
    if tz_utc:
        s = int(dt.datetime.combine(d0, dt.time(), tzinfo=dt.timezone.utc).timestamp())
        e = int(dt.datetime.combine(end, dt.time(), tzinfo=dt.timezone.utc).timestamp())
    else:
        s = int(dt.datetime.combine(d0, dt.time()).timestamp())
        e = int(dt.datetime.combine(end, dt.time()).timestamp())
    d = _get(f"https://store.steampowered.com/appreviews/{appid}?json=1"
             f"&num_per_page=0&filter=all&language=all&purchase_type=all"
             f"&date_range_type=include&start_date={s}&end_date={e}")
    q = (d or {}).get("query_summary") or {}
    return q.get("total_reviews")


rel_diffs, repro = [], []
for i in samp:
    r = rows[int(i)]
    v_utc = w30_epoch(r["appid"], r["release_date"], True)
    time.sleep(1.0)
    v_kst = w30_epoch(r["appid"], r["release_date"], False)
    time.sleep(1.0)
    stored = r["y_w30"]
    if v_utc is not None and v_kst is not None and max(v_utc, v_kst) > 0:
        rel_diffs.append(abs(v_utc - v_kst) / max(v_utc, v_kst, 1))
    if v_kst is not None and stored:
        repro.append(abs(v_kst - stored) / max(stored, 1) <= 0.05)
med = float(np.median(rel_diffs)) if rel_diffs else None
p95 = float(np.percentile(rel_diffs, 95)) if rel_diffs else None
rr = float(np.mean(repro)) if repro else None
print(f"ⓐ UTC/KST 상대차 중앙 {med} · p95 {p95} · 재현률(±5%) {rr}", flush=True)

branches = []
branches.append(("ⓐ UTC 정본 선언" if (med is not None and med <= 0.01 and p95 <= 0.05)
                 else f"ⓐ 초과 — 중앙 {med} p95 {p95}: 라벨 재계산 등록"))
if rr is not None and rr < 0.95:
    branches.append(f"ⓐ 재현률 {rr:.2f} < 0.95 — 소급 집계 불안정 실물(백필 오차항 병기)")
branches.append(("ⓑ 필터 신뢰" if cs_rate >= 0.98 else f"ⓑ 필터 불신({cs_rate:.2f}) — appdetails 폴백 재설계"))
branches.append(f"ⓑ 일-입도 확보 {n_day}" + ("(≥150)" if n_day >= 150 else " — 층화 미달 병기"))
branches.append("ⓒ day7(8/15+) 달력 등록 — 갈래는 863ⓒ 동결분")

out = {"day0": {"코호트": len(cohort), "total": total_count, "입도": by_g,
                "교차 coming_soon": round(cs_rate, 3)},
       "y_w30 게이트": {"표본": int(len(samp)), "상대차 중앙": med, "p95": p95, "재현률": rr},
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out863_knock.json", "w"), ensure_ascii=False, indent=1)
