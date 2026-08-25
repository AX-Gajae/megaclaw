# -*- coding: utf-8 -*-
"""1037 A부 집계 — 사슬 단계별 계수 · 분모 넷 · 크롤 덩이별 · 게이트 판정 · 선택 편향."""
import json, gzip, collections, statistics, sys
import datetime as dt
from pathlib import Path
import numpy as np

OUT = Path("/Users/ax/wm_harvest/foundation/warc1037")
TF = Path("/Users/ax/wm_harvest/foundation/textfix1036")

coords = {}
for line in gzip.open(OUT / "warc_coords.jsonl.gz", "rt"):
    v = json.loads(line)
    f = v["f"]
    if "CC-MAIN-" not in f:
        v["덩이"] = "wide16(비CC)"
    else:
        d = f.split("CC-MAIN-")[-1][:8]
        v["덩이"] = ("㉠2017-04" if d.startswith("201701") else "㉡2018-05" if d.startswith("201801")
                     else "㉢2021-43" if d.startswith("202110")
                     else "㉣2022-40" if d < "20221100" else "㉤2022-49")
    coords[v["문서id"]] = v

res = {}
for line in open(OUT / "warc_pub.jsonl", encoding="utf-8"):
    r = json.loads(line)
    res[r["문서id"]] = r

D1 = len(coords)
cc = [d for d, v in coords.items() if "CC-MAIN-" in v["f"]]
D2 = len(cc)
rows = json.load(open(TF / "row_docid.json", encoding="utf-8"))
D3docs = set(r["문서id"] for r in rows)

chain = collections.Counter()
by = collections.defaultdict(collections.Counter)
meth = collections.Counter()
diffs = []
for d in cc:
    v = coords[d]; r = res.get(d)
    g = v["덩이"]
    by[g]["S1좌표"] += 1
    if r is None:
        chain["미시도"] += 1; by[g]["미시도"] += 1; continue
    st = r.get("단계")
    if st == "S2":
        chain["S2경로없음"] += 1; by[g]["S2실패"] += 1; continue
    by[g]["S2통과"] += 1
    if st == "S3":
        chain["S3실패:" + str(r.get("실패"))[:12]] += 1; by[g]["S3실패"] += 1; continue
    if st == "S4":
        chain["S4실패"] += 1; by[g]["S4실패"] += 1; continue
    if st == "S5":
        chain["S5실패:" + str(r.get("실패"))[:12]] += 1; by[g]["S5실패"] += 1; continue
    by[g]["S5통과"] += 1
    if r.get("published_at"):
        chain["S6성공"] += 1; by[g]["S6성공"] += 1
        meth[r["method"]] += 1
        diffs.append((dt.date.fromisoformat(r["crawl_ts"][:10])
                      - dt.date.fromisoformat(r["published_at"])).days)
    else:
        chain["S6실패:" + str(r.get("실패"))[:10]] += 1; by[g]["S6실패"] += 1

got = {d for d, r in res.items() if r.get("published_at")}
rep = {
    "분모": {"D1 전체문서": D1, "D2 CC문서": D2, "D3 실험행": len(rows),
             "D3 고유문서": len(D3docs), "D4 고유호스트": len(set(r["host"] for r in rows))},
    "사슬": dict(chain.most_common()),
    "방법별": dict(meth.most_common()),
    "회수율": {
        "🔴 문서가중 D2(CC) [게이트]": round(len(got & set(cc)) / D2, 4),
        "문서가중 D1(전체)": round(len(got) / D1, 4),
        "S2 통과분 기준": round(len(got & set(cc)) / max(1, sum(by[g]["S2통과"] for g in by)), 4),
        "S5 통과분 기준(HTML 손에 쥔 것)": round(len(got & set(cc)) / max(1, sum(by[g]["S5통과"] for g in by)), 4),
    },
    "크롤 덩이별": {g: dict(c) for g, c in sorted(by.items())},
}
rep["크롤 덩이별 회수율"] = {g: round(c["S6성공"] / c["S1좌표"], 4) for g, c in sorted(by.items())}
if diffs:
    rep["크롤−발행 차이일"] = {
        "n": len(diffs), "중앙": statistics.median(diffs), "평균": round(statistics.mean(diffs), 1),
        "창안(0~90) 비율": round(sum(1 for x in diffs if 0 <= x <= 90) / len(diffs), 4),
        "🔴 창밖 비율": round(sum(1 for x in diffs if not 0 <= x <= 90) / len(diffs), 4),
        "음수(발행>크롤)": sum(1 for x in diffs if x < 0),
        "십분위": [int(np.percentile(diffs, p)) for p in range(10, 100, 10)],
    }

# 호스트 가중(직전 시험 방식) 병기 — 조항 60
hostdoc = {}
for r in rows:
    hostdoc.setdefault(r["host"], r["문서id"])
hn = sum(1 for h, d in hostdoc.items() if d in got)
rep["회수율"]["호스트가중(D4 · 호스트당 1건 — 직전 방식)"] = round(hn / len(hostdoc), 4)

# 기존 v1/v2 사슬과의 대조(외부 검증) — 등록된 부수 관심사
v1 = json.load(open("/Users/ax/wm_harvest/foundation/pubdate/sao_state.json", encoding="utf-8"))["문서"]
agree = collections.Counter()
for d, r in res.items():
    a = v1.get(d, {}).get("published_at")
    b = r.get("published_at")
    if a and b:
        agree["둘 다"] += 1
        gap = abs((dt.date.fromisoformat(a[:10]) - dt.date.fromisoformat(b)).days)
        agree["≤1일" if gap <= 1 else "≤7일" if gap <= 7 else ">7일"] += 1
    elif a and not b:
        agree["v1만"] += 1
    elif b and not a:
        agree["WARC만"] += 1
    else:
        agree["둘 다 없음"] += 1
rep["v1 사슬 외부검증"] = dict(agree)

# 실험행 기준 커버리지 + 재부착 후보
def pubof(d):
    r = res.get(d)
    if r and r.get("published_at"):
        return r["published_at"], "warc"
    a = v1.get(d, {}).get("published_at")
    return (a[:10], "v1") if a else (None, None)

cov = 0; inwin = 0; rowdiff = []
for r in rows:
    p, _ = pubof(r["문서id"])
    if not p:
        continue
    cov += 1
    dd = (dt.date.fromisoformat(r["언제"]) - dt.date.fromisoformat(p)).days
    rowdiff.append(dd)
    if 0 <= dd <= 90:
        inwin += 1
rep["D3 실험행"] = {"발행일 붙은 행": cov, "비율": round(cov / len(rows), 4),
                    "창안 행": inwin, "창밖 행": cov - inwin,
                    "창밖 비율": round((cov - inwin) / max(1, cov), 4),
                    "1036 대비(v1만 1,942 = 18.23%)": f"{cov}행 = {100*cov/len(rows):.2f}%"}

# 선택 편향 표 — 회수 vs 미회수 (D3 문서)
prof = {}
for tag, sel in [("회수", lambda d: d in got), ("미회수", lambda d: d not in got)]:
    sub = [r for r in rows if sel(r["문서id"])]
    if not sub:
        continue
    y = np.load(TF / "y_event.npy")
    idx = [i for i, r in enumerate(rows) if sel(r["문서id"])]
    tld = collections.Counter(r["host"].rsplit(".", 1)[-1] for r in sub)
    prof[tag] = {"행": len(sub), "문서": len(set(r["문서id"] for r in sub)),
                 "기저율": round(float(y[idx].mean()), 4),
                 "글자수 중앙": int(statistics.median(r["글자수"] for r in sub)),
                 "tld 상위": dict(tld.most_common(5))}
rep["🔴 선택 편향"] = prof

# 게이트
g1 = rep["회수율"]["🔴 문서가중 D2(CC) [게이트]"]
rep["게이트"] = {"G-A1 (≥0.50)": f"{g1:.4f} → {'통과' if g1 >= 0.50 else '미달'}",
                 "G-A2 (≥3,000행)": f"{cov}행 붙음 — 재부착 성공 수는 B부에서"}
(OUT / "a_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps(rep, ensure_ascii=False, indent=1))
