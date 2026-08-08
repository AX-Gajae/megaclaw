# -*- coding: utf-8 -*-
# 노트 864 — 게임 노크 수리 (사전등록 '864' · 티처 #29 P2/P3 · 무캐시 · 기존 수집기 3종 불변)
# P2: day0b 지평 정합 코호트([2026-09-15, 2026-10-31] 일-입도) + 모집단 입도 분포 첫 실측
# P3: y_w30 꼬리 재게이트(y>=100 전수 32행 + 독립 씨앗 20행) · 갈래 내 UTC 실통일(새 파일)
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
SEARCH = ("https://store.steampowered.com/search/results/?query&count=50"
          "&category1=998&infinite=1&json=1&cc=kr&l=korean"
          "&filter=comingsoon&start={start}")
WIN_LO, WIN_HI = "2026-09-15", "2026-10-31"
ENG = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def granularity(s):
    """예정일 원문 → (입도, 표준일 or None). 863 파서의 죽은 31행 제거 + 영어 월 처리."""
    s = str(s or "").strip()
    if not s:
        return "미정", None
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", s)
    if m:
        return "일", f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[a-z]*,?\s+(\d{4})", s)
    if m and m.group(2).lower() in ENG:
        return "일", f"{m.group(3)}-{ENG[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2}),\s*(\d{4})", s)
    if m and m.group(1).lower() in ENG:
        return "일", f"{m.group(3)}-{ENG[m.group(1).lower()]:02d}-{int(m.group(2)):02d}"
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월(?!.*일)", s)
    if m:
        return "월", f"{m.group(1)}-{int(m.group(2)):02d}"
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{4})", s)
    if m and m.group(1).lower() in ENG:
        return "월", f"{m.group(2)}-{ENG[m.group(1).lower()]:02d}"
    if re.search(r"분기|Q[1-4]", s):
        return "분기", None
    if re.search(r"\d{4}", s) and not re.search(r"월|일", s):
        return "연", None
    return "미정", None


def fetch_page(start):
    """한 쪽 → [(appid, 제목, 원문, 입도, 표준일)] · 번들(콤마 appid) 제외."""
    d = _get(SEARCH.format(start=start))
    time.sleep(1.2)
    if not d:
        return None, None
    html_blob = d.get("results_html") or ""
    out = []
    for b in re.split(r'data-ds-appid="', html_blob)[1:]:
        mid = re.match(r'([\d,]+)"', b)
        if not mid or "," in mid.group(1):
            continue
        mt = re.search(r'<span class="title">([^<]{1,120})</span>', b)
        mr = re.search(r'search_released[^>]*>\s*([^<]{0,60})<', b)
        if not mt:
            continue
        rel = (mr.group(1) if mr else "").strip()
        g, std = granularity(rel)
        out.append({"appid": mid.group(1), "제목": mt.group(1).strip(),
                    "예정일 원문": rel, "입도": g, "표준일": std})
    return out, d.get("total_count")


def comp(items):
    c = {}
    for it in items:
        c[it["입도"]] = c.get(it["입도"], 0) + 1
    return c


# ── P2ⓐ 눈금 훑기(150~2900, 250 간격) ───────────────────────────
pages = {}          # offset -> items (모집단 추정에 재사용)
total_count = None
probes = []
for off in range(150, 2901, 250):
    items, tc = fetch_page(off)
    if items is None:
        continue
    total_count = total_count or tc
    pages[off] = items
    days = sorted(it["표준일"] for it in items if it["입도"] == "일")
    probes.append({"offset": off, "n": len(items), "구성": comp(items),
                   "일 최소": days[0] if days else None, "일 최대": days[-1] if days else None})
print("눈금:", json.dumps(probes, ensure_ascii=False), flush=True)

band_start = 150
for p in probes:
    if p["일 최대"] and p["일 최대"] < WIN_LO:
        band_start = p["offset"]

# ── P2ⓐ 대역 걷기(상한 60쪽) ────────────────────────────────────
day0b, seen = [], set()
walk_log = []
off = band_start
pages_walked = 0
while pages_walked < 60 and len(day0b) < 150:
    if off in pages:
        items = pages[off]
    else:
        items, _ = fetch_page(off)
        if items is None:
            break
        pages[off] = items
    pages_walked += 1
    days = sorted(it["표준일"] for it in items if it["입도"] == "일")
    walk_log.append({"offset": off, "구성": comp(items),
                     "일 범위": [days[0], days[-1]] if days else None})
    for it in items:
        if it["입도"] == "일" and WIN_LO <= it["표준일"] <= WIN_HI and it["appid"] not in seen:
            seen.add(it["appid"])
            day0b.append(dict(it, _offset=off))
    if days and days[0] > WIN_HI:
        break
    off += 50
print(f"day0b {len(day0b)} · 걸은 쪽 {pages_walked} · 대역 시작 {band_start}", flush=True)

# ── P2ⓑ 심층 표집({2000..12000}) + 모집단 추정 ──────────────────
for offp in (2000, 4000, 6000, 8000, 10000, 12000):
    if offp not in pages:
        items, _ = fetch_page(offp)
        if items is not None:
            pages[offp] = items
six = [it for offp in (2000, 4000, 6000, 8000, 10000, 12000) for it in pages.get(offp, [])]
six_nonday = sum(1 for it in six if it["입도"] != "일") / max(len(six), 1)

# 조각별 상수 보간(863 전면 0~150 = 전원 일 포함)
samples = [(0, 0.0)] + sorted(
    (o, sum(1 for it in its if it["입도"] != "일") / max(len(its), 1)) for o, its in pages.items())
N = int(total_count or 12827)
acc = 0.0
for i, (o, sh) in enumerate(samples):
    lo = 0 if i == 0 else (samples[i - 1][0] + o) / 2
    hi = N if i == len(samples) - 1 else (o + samples[i + 1][0]) / 2
    acc += sh * (min(hi, N) - lo)
pop_nonday = acc / N
print(f"모집단 비-일: 6점 {six_nonday:.3f} · 조각보간 {pop_nonday:.3f}", flush=True)

NOW = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
with open(ROOT / "runners/out864_day0b.json", "x") as fh:
    json.dump({"수집 시각(UTC)": NOW, "total_count": total_count, "창": [WIN_LO, WIN_HI],
               "코호트": day0b, "눈금": probes, "걷기": walk_log,
               "모집단 입도": {"6점 표본": comp(six), "6점 비-일": round(six_nonday, 3),
                            "조각보간 비-일": round(pop_nonday, 3)},
               "재수집": "2026-08-22 · 2026-08-29 appid 전수 무캐시 — 이동률 갈래는 사전등록 864 동결분"},
              fh, ensure_ascii=False, indent=1)

# ── P3 y_w30 꼬리 재게이트 ──────────────────────────────────────
GR = json.load(open(ROOT / "data/state/game_recent.json"))
rows = [r for r in (GR.values() if isinstance(GR, dict) else GR)
        if not r.get("y_w30_truncated") and r.get("y_w30") is not None and r.get("release_date")]
tail = [r for r in rows if r["y_w30"] >= 100]
rest = [r for r in rows if r["y_w30"] < 100]
rng = np.random.default_rng(86403)                       # 독립 스트림(결합 금지)
extra = [rest[int(i)] for i in rng.choice(len(rest), size=min(20, len(rest)), replace=False)]
print(f"틀 {len(rows)} · 꼬리 {len(tail)} · 추가 {len(extra)}", flush=True)


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
    time.sleep(1.0)
    q = (d or {}).get("query_summary") or {}
    return q.get("total_reviews")


gate_rows = []
for r in tail + extra:
    v_utc = w30_epoch(r["appid"], r["release_date"], True)
    v_kst = w30_epoch(r["appid"], r["release_date"], False)
    gate_rows.append({"appid": r["appid"], "release_date": r["release_date"],
                      "v_utc": v_utc, "v_kst": v_kst, "stored": r["y_w30"],
                      "층": "꼬리" if r["y_w30"] >= 100 else "추가",
                      "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})


def diffs(rows_, layer=None):
    out = []
    for g in rows_:
        if layer and g["층"] != layer:
            continue
        if g["v_utc"] is not None and g["v_kst"] is not None:
            out.append(abs(g["v_utc"] - g["v_kst"]) / max(g["v_utc"], g["v_kst"], 1))
    return out


tail_d = diffs(gate_rows, "꼬리")
all_d = diffs(gate_rows)
repro = [abs(g["v_kst"] - g["stored"]) / max(g["stored"], 1) <= 0.05
         for g in gate_rows if g["v_kst"] is not None and g["stored"] is not None]
tail_p95 = float(np.percentile(tail_d, 95)) if tail_d else None
tail_med = float(np.median(tail_d)) if tail_d else None
rr = float(np.mean(repro)) if repro else None
print(f"꼬리 p95 {tail_p95} · 중앙 {tail_med} · 전체 p95 "
      f"{float(np.percentile(all_d, 95)) if all_d else None} · 재현률 {rr} (실효 {len(repro)})", flush=True)

json.dump({"행": gate_rows, "꼬리 p95": tail_p95, "꼬리 중앙": tail_med,
           "전체 p95": float(np.percentile(all_d, 95)) if all_d else None,
           "재현률": rr, "실효 n": {"꼬리": len(tail_d), "전체": len(all_d), "재현": len(repro)}},
          open(ROOT / "runners/out864_gate_rows.json", "w"), ensure_ascii=False, indent=1)

# ── 갈래 내 실행: 꼬리 p95 ≤5% → 전 행 UTC 실통일(새 파일 · 원본 불변) ──
branches = []
utc_done = 0
if tail_p95 is not None and tail_p95 <= 0.05:
    branches.append(f"P3-1 꼬리 p95 {tail_p95:.4f} ≤ 0.05 → 전 행 UTC 재계산(새 파일) 실행")
    have = {g["appid"]: g["v_utc"] for g in gate_rows if g["v_utc"] is not None}
    unified = {}
    for r in rows:
        v = have.get(r["appid"])
        if v is None:
            v = w30_epoch(r["appid"], r["release_date"], True)
        if v is None:
            continue
        unified[r["appid"]] = {"y_w30_utc": v, "y_w30_stored_kst": r["y_w30"],
                               "rel_diff": round(abs(v - r["y_w30"]) / max(r["y_w30"], 1), 4),
                               "release_date": r["release_date"]}
        utc_done += 1
    dd = [u["rel_diff"] for u in unified.values()]
    json.dump({"생성 시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "정의": "y_w30_utc = [출시일 00:00 UTC, +30일) appreviews total — 이후 게임 라벨 정본",
               "행": unified,
               "diff 요약": {"n": len(dd), "중앙": float(np.median(dd)) if dd else None,
                           "p95": float(np.percentile(dd, 95)) if dd else None,
                           ">5% 행": sum(1 for x in dd if x > 0.05)}},
              open(ROOT / "data/state/game_recent_utc.json", "w"), ensure_ascii=False, indent=1)
    branches.append(f"P3-1b UTC 정본 파일 {utc_done}행 동결(game_recent_utc.json — 원본 불변)")
elif tail_p95 is not None:
    branches.append(f"P3-2 꼬리 p95 {tail_p95:.4f} > 0.05 → UTC 정본 철회 · KST 운영 정의 재선언")
if rr is not None and rr < 0.95:
    branches.append(f"P3-3 재현률 {rr:.3f} < 0.95 → '소형작 반증 없음' 철회 · 백필 오차항 병기")
branches.append(("P2-1 모집단 비-일 ≥30% → '명단은 있으나 날짜가 없다' 실물"
                 if min(six_nonday, pop_nonday) >= 0.30 else
                 ("P2-1 모집단 비-일 <30% → 그대로 진행" if max(six_nonday, pop_nonday) < 0.30
                  else f"P2-1 판정 유보 — 6점 {six_nonday:.3f} 대 조각보간 {pop_nonday:.3f} 가 30% 를 사이에 둠")))
branches.append((f"P2-2 day0b {len(day0b)}(≥100) 확보" if len(day0b) >= 100 else
                 (f"P2-2 day0b {len(day0b)}(<50) — 지평 정합 명단 부족 실물" if len(day0b) < 50
                  else f"P2-2 day0b {len(day0b)}(50~99) — 있는 만큼 동결·병기")))

out = {"P2": {"day0b": len(day0b), "창": [WIN_LO, WIN_HI], "대역 시작": band_start,
              "걸은 쪽": pages_walked, "total": total_count,
              "모집단 비-일": {"6점": round(six_nonday, 3), "조각보간": round(pop_nonday, 3)}},
       "P3": {"꼬리 p95": tail_p95, "꼬리 중앙": tail_med, "재현률": rr,
              "실효 n": len(repro), "UTC 통일 행": utc_done},
       "갈래": branches, "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out864_repair.json", "w"), ensure_ascii=False, indent=1)
