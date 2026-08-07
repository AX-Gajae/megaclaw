# 노트 830 — KOBIS 90일 백필 파일럿 (사전등록: 대장 '사전등록 830' · 커밋 후 측정)
import datetime as dt
import json, sys, time
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")
from ingest.kobis import fetch_daily, SLEEP

t0 = time.time()
start = dt.date(2026, 5, 4)
days = [(start + dt.timedelta(days=i)).isoformat() for i in range(90)]
data, fails = {}, []
for d in days:
    try:
        rows = fetch_daily(d)
        if not rows:
            fails.append(d)
        else:
            data[d] = rows
    except Exception as e:
        fails.append(f"{d}:{type(e).__name__}")
    time.sleep(SLEEP)
    if len(data) % 15 == 0 and len(data) > 0:
        print(f"  {len(data)}/{90} 일 ({time.time()-t0:.0f}s)", flush=True)

print(f"백필 완료 — 성공 {len(data)}일 · 실패 {len(fails)} ({time.time()-t0:.0f}s)", flush=True)
out = {"찍은 때": dt.datetime.now().isoformat(timespec="seconds"),
       "창": [days[0], days[-1]], "성공일": len(data), "실패": fails}

# 영화별 시계열 (제목+개봉일 열쇠)
series = {}
for d, rows in data.items():
    for r in rows:
        k = (r["제목"], r.get("개봉일"))
        c = r["숫자 셀(원본 순서)"]
        if len(c) >= 5:
            series.setdefault(k, {})[d] = {"일관객": c[3], "누적": c[4]}

# 불변식: 누적 단조
viol = 0; total_pairs = 0
for k, sv in series.items():
    ds = sorted(sv)
    for a, b in zip(ds, ds[1:]):
        total_pairs += 1
        if sv[b]["누적"] < sv[a]["누적"]:
            viol += 1
viol_rate = viol / max(total_pairs, 1)
out["불변식"] = {"누적 역행 쌍": viol, "전체 쌍": total_pairs, "비율": round(viol_rate, 5)}

# 창 안 개봉작 · 관측 ≥21일 → 개봉일 정렬 log1p 평균 곡선
IN = {k: sv for k, sv in series.items()
      if k[1] and days[0] <= k[1] <= days[-1]}
aligned = []
stay, last_audi = [], []
reopen = sum(1 for k in series if k[1] and k[1] < "2025-05-04")
for (title, op), sv in IN.items():
    ds = sorted(sv)
    stay.append(len(ds))
    last_audi.append(sv[ds[-1]]["일관객"])
    if len(ds) >= 21:
        base = dt.date.fromisoformat(op)
        curve = np.full(45, np.nan)
        for d in ds:
            off = (dt.date.fromisoformat(d) - base).days
            if 0 <= off < 45:
                curve[off] = np.log1p(sv[d]["일관객"])
        aligned.append(curve)
A = np.vstack(aligned) if aligned else np.zeros((0, 45))
mean_curve = np.nanmean(A, axis=0) if len(A) else np.array([])
ok_days = ~np.isnan(mean_curve) if len(A) else np.array([])
amp = float(np.nanmax(mean_curve) - np.nanmin(mean_curve)) if len(A) else float("nan")
out["개봉작"] = {"창 안 개봉": len(IN), "관측 ≥21일": len(aligned),
    "생존율": round(len(aligned) / max(len(IN), 1), 3),
    "체류일 중앙": float(np.median(stay)) if stay else None,
    "탈락 시점 일관객 중앙": float(np.median(last_audi)) if last_audi else None}
out["곡선"] = {"진폭(log1p)": round(amp, 3),
    "평균 곡선(5일 간격)": [round(float(x), 2) for x in mean_curve[::5]] if len(A) else [],
    "재개봉(개봉일<1년 전) 편수": reopen}

# 갈래(사전등록)
if len(fails) > 9 or viol_rate > 0.01:
    out["판정"] = f"1.배선 — 실패 {len(fails)}일 · 역행 {viol_rate:.3%}"
elif amp >= 1.0:
    out["판정"] = f"2.진폭 확보 ({amp:.2f} ≥ 1.0) — 문패 3건(813/814/818) 전제 성립 · 831 합류 사전등록 진행"
else:
    out["판정"] = f"3.진폭 미달 ({amp:.2f}) — 그 3건은 KOBIS 로 못 연다"
out["초"] = round(time.time() - t0, 1)
print(json.dumps({k: out[k] for k in ("불변식", "개봉작", "곡선", "판정")}, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out830.json", "w"), ensure_ascii=False, indent=1)
# 원시 백필도 저장(재사용 — 831 라벨 확정 재료)
json.dump({d: rows for d, rows in data.items()},
          open("/Users/ax/world_model/data/ingest/kobis/backfill_2026-05-04_90d.json", "w"), ensure_ascii=False)
print("완료", flush=True)
