# 노트 836 — kobis_axes.json 빌더 (사전등록 '836' 사상 규칙 그대로)
import datetime as dt
import json, re, sys, time
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")

t0 = time.time()
RAW = "/Users/ax/world_model/data/ingest/kobis/axes_raw_897.jsonl"
B1 = json.load(open("/Users/ax/world_model/data/ingest/kobis/backfill_2023-01-01_full.json"))
B2 = json.load(open("/Users/ax/world_model/data/ingest/kobis/backfill_2026-05-04_90d.json"))
data = {**B1, **B2}

rows = [json.loads(l) for l in open(RAW)]
cov_pre = {}
ok = [r for r in rows if "⛔" not in r and r.get("code")]
n_fail = len(rows) - len(ok)
assert len(rows) == 897, f"전수 아님({len(rows)}) — 수집 완료 후 1회 빌드(티처 #9)"
for r in ok:
    for k_, cond in (("등급", r.get("등급") is not None), ("장르", bool(r.get("장르"))),
                     ("배급사", bool(r.get("배급사"))), ("국적", bool(r.get("국적 후보")))):
        cov_pre[k_] = cov_pre.get(k_, 0) + bool(cond)
print(f"수집 행 {len(rows)} · 상세 성공 {len(ok)} · 실패 {n_fail}", flush=True)

# 라벨: K=21 마지막 누적 (시사회 포함 — 개봉 전 관측도 누적에 반영돼 있음)
series = {}
for d, rr in data.items():
    for r in rr:
        k = (r["제목"], r.get("개봉일"))
        c = r["숫자 셀(원본 순서)"]
        if len(c) >= 5:
            series.setdefault(k, {})[d] = c[4]

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
    import html
    s = html.unescape(str(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    #: 🔴 중간 구분자 **선절단**(티처 #9 — '제공/수입사' 복합 문자열이 사전 키 29% 오염)
    s = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", s)[0].strip()
    s = re.split(r"\s*(?:제공|배급)\s*$", s)[0].strip()
    m = re.match(r"([가-힣0-9()주식회사㈜\s]+)", s)
    cand = m.group(1).strip() if m else ""
    #: '(주)'·괄호·공백뿐이면 한글-우선을 버리고 전체(영문 포함) 사용 — '(주)NEW' 붕괴 방지
    core = re.sub(r"[()㈜\s]|주식회사", "", cand)
    out = cand if len(core) >= 2 else s
    return out.rstrip("( ").strip()[:30]

# 배급사 규모 사전 — 학습 구간(<2025 개봉)만
train_count = {}
for r in ok:
    if r["개봉일"] < "2025-01-01" and r.get("배급사"):
        d_ = clean_dist(r["배급사"])
        train_count[d_] = train_count.get(d_, 0) + 1
ranked = sorted(train_count.values())
def dist_pct(name):
    d_ = clean_dist(name) if name else None
    if not d_ or d_ not in train_count:
        return 0.0
    c = train_count[d_]
    return float(np.searchsorted(ranked, c, side="right") / len(ranked))

axes_out = {}
missing_label = 0
cov = {"등급": 0, "장르": 0, "배급사": 0, "국적": 0}
for r in ok:
    key = (r["제목"], r["개봉일"])
    sv = series.get(key)
    if not sv:
        missing_label += 1
        continue
    op_d = dt.date.fromisoformat(r["개봉일"])
    obs = {d: v for d, v in sv.items()
           if 0 <= (dt.date.fromisoformat(d) - op_d).days <= 20}
    if not obs:
        missing_label += 1
        continue
    last_off = max((dt.date.fromisoformat(d) - op_d).days for d in obs)
    y = float(np.log10(max(obs[max(obs)], 1)))
    ef = grade_val(r.get("등급"))
    genres = [g for g in str(r.get("장르") or "").split(",") if g.strip()]
    tb = min(len(genres), 4) / 4 if genres else None
    vp = dist_pct(r.get("배급사")) if r.get("배급사") else None
    axes = {"target_breadth": tb if tb is not None else 0.5,
            "venue_prominence": vp if vp is not None else 0.5,
            "entry_friction": ef if ef is not None else 0.5,
            "media_push": 0.5, "goods_scale": 0.5}
    mask = {"target_breadth": 1.0 if tb is not None else 0.0,
            "venue_prominence": 1.0 if vp is not None else 0.0,
            "entry_friction": 1.0 if ef is not None else 0.0,
            "media_push": 0.0, "goods_scale": 0.0}

    axes_out[f"KOBIS-{r['code']}"] = {
        "axes": axes, "mask": mask,
        "why": {"entry_friction": f"등급 {r.get('등급')}",
                "target_breadth": f"장르 {len(genres)}개",
                "venue_prominence": f"배급 {clean_dist(r.get('배급사') or '')} (학습 사전)",
                "media_push": "정보 없음(마스크 0)", "goods_scale": "정보 없음(마스크 0)"},
        "y": y, "release_date": r["개봉일"], "name": r["제목"],
        "국적": r.get("국적 후보"), "상영등급 원문": r.get("등급"),
        "검열(개봉+14 미달)": bool(last_off < 14), "마지막 관측일차": int(last_off)}

n = len(axes_out)
identity_ok = (n + missing_label + n_fail == 897)
out_meta = {"행": n, "라벨 결측 제외": missing_label, "상세 실패": n_fail,
            "항등식(행+결측+실패=897)": identity_ok,
            "커버리지(상세 성공 기준)": {k: round(v / max(len(ok), 1), 3) for k, v in cov_pre.items()},
            "검열 행": sum(1 for v in axes_out.values() if v.get("검열(개봉+14 미달)")),
            "배급 사전 크기(학습)": len(train_count)}
assert identity_ok, out_meta
print(json.dumps(out_meta, ensure_ascii=False), flush=True)
json.dump(axes_out, open("/Users/ax/world_model/data/state/kobis_axes.json", "w"), ensure_ascii=False, indent=1)
json.dump(out_meta, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out836_build.json", "w"), ensure_ascii=False, indent=1)
print(f"kobis_axes.json 저장 — {n}행 · {time.time()-t0:.0f}s", flush=True)
