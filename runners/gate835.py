# 노트 835 — KOBIS 합류 관문 집행 (사전등록: 대장 '사전등록 835')
import datetime as dt
import json, sys, time
import numpy as np
sys.path.insert(0, "/Users/ax/world_model")

t0 = time.time()
B1 = json.load(open("/Users/ax/world_model/data/ingest/kobis/backfill_2023-01-01_full.json"))
B2 = json.load(open("/Users/ax/world_model/data/ingest/kobis/backfill_2026-05-04_90d.json"))
data = {**B1, **B2}
days = sorted(data)
n_target = 1309          # 1,219(다년) + 90(파일럿) — 데이터 자체에서 교차산출(티처 #8 ④)
fail_rate = (n_target - len(days)) / n_target
print(f"일수 {len(days)} ({days[0]}~{days[-1]}) · 백필 실패율 {fail_rate:.3%}", flush=True)

series = {}
for d, rows in data.items():
    for r in rows:
        k = (r["제목"], r.get("개봉일"))
        c = r["숫자 셀(원본 순서)"]
        if len(c) >= 5:
            series.setdefault(k, {})[d] = (c[3], c[4])   # (일관객, 누적)
viol = tot = 0
for k, sv in series.items():
    ds = sorted(sv)
    for a, b in zip(ds, ds[1:]):
        tot += 1
        viol += sv[b][1] < sv[a][1]
viol_rate = viol / max(tot, 1)
print(f"영화 {len(series)} · 누적 역행 {viol_rate:.4%}", flush=True)

W0, W1 = days[0], days[-1]
null_release = sum(1 for k in series if not k[1])
IN = {k: sv for k, sv in series.items() if k[1] and W0 <= k[1] <= W1}
f7 = {}
for (t_, op), sv in IN.items():
    op_d = dt.date.fromisoformat(op)
    vals = [v[0] for d, v in sv.items()
            if 0 <= (dt.date.fromisoformat(d) - op_d).days < 7]
    if vals:
        f7[(t_, op)] = max(vals)
q85 = float(np.percentile(list(f7.values()), 85))
above = {k for k, v in f7.items() if v >= q85}
print(f"창 안 개봉 {len(IN)} · 개봉일 null {null_release} · q85 = {q85:,.0f} · 문턱 위 {len(above)}", flush=True)

# K=21 라벨 — 성립 = **마지막 관측 ≥ 개봉+14일**(티처 #8 수정 — 항진 제거)
lab_ok = lab_tot = 0
train = hold = 0
for (t_, op) in above:
    op_d = dt.date.fromisoformat(op)
    if (op_d + dt.timedelta(days=20)).isoformat() > W1:
        continue
    lab_tot += 1
    sv = series[(t_, op)]
    offs = [(dt.date.fromisoformat(d) - op_d).days for d in sv
            if 0 <= (dt.date.fromisoformat(d) - op_d).days <= 20]
    if offs and max(offs) >= 14:
        lab_ok += 1
        if op < "2025-01-01":
            train += 1
        else:
            hold += 1
rate = lab_ok / max(lab_tot, 1)
no_f7 = len(IN) - len(f7)
outside = len(series) - len(IN) - null_release
OUT = {"배선": {"실패율": round(fail_rate, 4), "역행": round(viol_rate, 5)},
       "제외 표": {"개봉일 null": null_release, "창 밖(재개봉·이월)": outside,
                  "f7 무관측": no_f7},
       "q85(다년)": round(q85, 1), "문턱 위": len(above),
       "라벨": {"대상": lab_tot, "성립": lab_ok, "성립률": round(rate, 4)},
       "행수": {"학습(<2025)": train, "유보(≥2025)": hold},
       "개봉일 null(제외)": null_release}
if fail_rate > 0.02 or viol_rate > 0.01:
    OUT["판정"] = "1.배선"
elif rate < 0.90 or train < 300:
    OUT["판정"] = f"2.취소 — 성립률 {rate:.1%} · 학습 {train}"
else:
    OUT["판정"] = f"3.관문 통과 — 학습 {train} · 유보 {hold} → 836 축 수집·재기선 절차"
OUT["초"] = round(time.time() - t0, 1)
print(json.dumps(OUT, ensure_ascii=False, indent=1), flush=True)
json.dump(OUT, open("/private/tmp/claude-501/-Users-ax-world-model/ab2920c3-279e-40cd-b648-7c58d9b12d79/scratchpad/out835.json", "w"), ensure_ascii=False, indent=1)
