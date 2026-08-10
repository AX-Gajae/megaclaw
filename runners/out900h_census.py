"""지평 900 — 시장팝업 두 필드 결측 전수 계수. 읽기 전용."""
import glob, json, collections
from pathlib import Path

ROOT = Path("/Users/ax/world_model")

def batch(rid):
    return "MKT2" if rid.startswith("MKT2") else "MKT"

def state(iv, key):
    """조항 59 — 없다/널/빈문자열/값 을 넷으로 가른다."""
    if not isinstance(iv, dict):
        return "no-intervention"
    if key not in iv:
        return "absent"
    v = iv[key]
    if v is None:
        return "null"
    if isinstance(v, str) and v.strip() == "":
        return "empty-str"
    return "value:%r" % (v,)

rows = []
for f in sorted(glob.glob(str(ROOT / "data/market_records/*.json"))):
    d = json.load(open(f))
    iv = d.get("intervention")
    rows.append(dict(
        rid=d.get("market_record_id"), file=Path(f).name, b=batch(d.get("market_record_id","")),
        free=state(iv, "is_free_entry"), resv=state(iv, "reservation_required"),
        ingested=d.get("ingested_from"), d=d))

print("=== 분모 A: data/market_records 파일 전수 =", len(rows))
def tab(rows, label):
    print("\n--- %s (n=%d)" % (label, len(rows)))
    for fld in ("free", "resv"):
        c = collections.Counter((r["b"], r[fld]) for r in rows)
        print(" %s:" % fld)
        for k in sorted(c, key=lambda x: (x[0], x[1])):
            print("   %-5s %-22s %4d" % (k[0], k[1], c[k]))
    # 둘 다 없음(= _friction 이 None) 계수
    both = [r for r in rows if r["free"] in ("absent","null") and r["resv"] in ("absent","null")]
    print("  둘 다 결측(=_friction None) : %d  (MKT %d / MKT2 %d)" % (
        len(both), sum(1 for r in both if r["b"]=="MKT"), sum(1 for r in both if r["b"]=="MKT2")))
    return both

tab(rows, "전수 647")

# 분모 B: market_axes.json 에 실린 249행
ax = json.load(open(ROOT / "data/state/market_axes.json"))
sel = [r for r in rows if r["rid"] in ax]
print("\n=== 분모 B: 판 축 파일 %d 행" % len(ax))
b_both = tab(sel, "축 파일 249")

# 분모 C: 유보(period_from >= 2025)
hold = [r for r in sel if ax[r["rid"]]["period_from"][:4] >= "2025"]
train = [r for r in sel if ax[r["rid"]]["period_from"][:4] < "2025"]
print("\n=== 분모 C: 유보 %d · 학습 %d" % (len(hold), len(train)))
h_both = tab(hold, "유보 126")
tab(train, "학습 123")

# 마스크 실측(축 파일이 적어 둔 값)
import statistics
for name, sub in (("전체249", sel), ("유보126", hold), ("학습123", train)):
    m = [ax[r["rid"]]["mask"]["entry_friction"] for r in sub]
    print("%s entry_friction 마스크 평균 %.4f  (1인 행 %d / 0인 행 %d)" % (
        name, statistics.mean(m), sum(1 for x in m if x==1.0), sum(1 for x in m if x==0.0)))
    for bb in ("MKT","MKT2"):
        mm = [ax[r["rid"]]["mask"]["entry_friction"] for r in sub if r["b"]==bb]
        if mm:
            print("    %-5s n=%3d 마스크평균 %.4f" % (bb, len(mm), statistics.mean(mm)))

json.dump([{k: r[k] for k in ("rid","file","b","free","resv","ingested")} for r in rows],
          open("/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad/census.json","w"),
          ensure_ascii=False, indent=1)
