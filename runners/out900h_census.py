# -*- coding: utf-8 -*-
"""지평 900 --- 시장팝업 두 필드(`is_free_entry`·`reservation_required`) 결측 전수 계수. 읽기 전용.

🔴 **901 수리 B 개정(이슈 #136 M9)**. 옛 판은 JSON 을 **스크래치패드**에 썼고
(`/private/tmp/.../scratchpad/census.json` --- 세션이 끝나면 사라진다) 도장이 하나도 없었다.
그래서 티처 #63 M2(카테고리 계수 다섯이 틀렸다)를 **되짚을 근거가 저장소에 0** 이었다.
티처가 이 스크립트를 직접 돌려 수는 전량 재현했지만(V10·V11),
**재현되는 것과 기록이 남는 것은 다르다.**

이제:
  ① 산출물을 **저장소에** 쓴다 --- `runners/out900h_census.json`
  ② 도장 규약 v3.2 --- 시작 시각 · **끝 시각** · **코드 sha256** · **입력 파일 sha256**.
     🔴 `git HEAD` 는 **판정에 쓰지 마라**(v3.2 가 폐기했다 --- 긴 러너에선 원리상 「시작 시점」).
     본보기는 `runners/out899a_gates.py:235-249`.
  ③ 🔴 **조항 60** --- 계수마다 **분모를 이름으로 달고 나른다**. 이 파일의 병이 정확히
     「분모가 다른 두 수를 이어 붙인 것」이었다(원천 408 · 축 파일 249 · 유보 126 · 결측 37).
"""
import collections
import datetime as dt
import glob
import hashlib
import json
import statistics
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT_PATH = ROOT / "runners/out900h_census.json"

#: 이 러너가 값을 길어 오는 코드. 지금은 자기 자신뿐이다(반입 없음).
STAMP_CODE = ["runners/out900h_census.py"]
#: 단일 입력 파일. 여러 파일 묶음은 아래 `sha_many` 로 따로 도장을 찍는다.
STAMP_INPUT = ["data/state/market_axes.json"]
#: 묶음 입력.
STAMP_INPUT_GLOB = "data/market_records/*.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def sha_many(paths) -> dict:
    """🔴 647개 파일에 sha 를 하나씩 박으면 산출물이 도장으로 뒤덮인다.
    대신 **(상대경로, 파일sha) 목록을 정렬해 그 자체를 다시 해싱**한다 --- 결정적이고,
    한 파일만 바뀌어도 묶음 sha 가 바뀐다. 재현 절차를 값 옆에 적어 둔다."""
    items = sorted((str(p.relative_to(ROOT)), sha(p)) for p in paths)
    blob = "\n".join("%s %s" % it for it in items).encode()
    return {"파일 수": len(items),
            "묶음 sha256": hashlib.sha256(blob).hexdigest()[:16],
            "재현법": "sorted((상대경로, sha256(파일)[:16])) 를 '경로 공백 sha' 줄로 이어 개행 결합 → sha256[:16]"}


def stamp() -> dict:
    head = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    return {
        "시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "⚠ git HEAD(시작 시점 · 판정에 쓰지 마라)": head,
        "🔴 코드 sha256(이게 자다)": {c: (sha(ROOT / c) if (ROOT / c).exists() else "🔴 파일 없음")
                                for c in STAMP_CODE},
        "🔴 입력 파일 sha256": {c: (sha(ROOT / c) if (ROOT / c).exists() else "🔴 파일 없음")
                           for c in STAMP_INPUT},
        "🔴 입력 묶음 sha256": {STAMP_INPUT_GLOB: sha_many(sorted(ROOT.glob(STAMP_INPUT_GLOB)))},
    }


def stamp_close(st: dict) -> dict:
    """🔴 끝 시각을 박는다 --- 시작 시각만으로는 「언제까지의 코드를 봤나」를 못 말한다."""
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return st


ST = stamp()
OUT = {
    "무엇": "시장팝업 intervention 두 필드 결측 전수 계수 + 🔴 티처 #63 M2 카테고리 재계수",
    "🔴 조항 60": "이 산출물의 모든 계수는 **분모 이름을 달고** 나른다. 분모가 다르면 잇지 마라",
    "도장": ST,
}


def batch(rid):
    return "MKT2" if rid.startswith("MKT2") else "MKT"


def state(iv, key):
    """조항 59 --- 없다/널/빈문자열/값 을 넷으로 가른다."""
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
for f in sorted(glob.glob(str(ROOT / STAMP_INPUT_GLOB))):
    d = json.load(open(f))
    rid = d.get("market_record_id")
    rows.append(dict(
        rid=rid, file=Path(f).name, b=batch(rid or ""),
        free=state(d.get("intervention"), "is_free_entry"),
        resv=state(d.get("intervention"), "reservation_required"),
        cat=d.get("category"),
        ingested=d.get("ingested_from"), d=d))

print("=== 분모 A: data/market_records 파일 전수 =", len(rows))


def tab(rows, label):
    print("\n--- %s (n=%d)" % (label, len(rows)))
    blk = {"🔴 분모": label, "n": len(rows)}
    for fld in ("free", "resv"):
        c = collections.Counter((r["b"], r[fld]) for r in rows)
        print(" %s:" % fld)
        sub = {}
        for k in sorted(c, key=lambda x: (x[0], x[1])):
            print("   %-5s %-22s %4d" % (k[0], k[1], c[k]))
            sub["%s · %s" % (k[0], k[1])] = c[k]
        blk[fld] = sub
    # 둘 다 없음(= _friction 이 None) 계수
    both = [r for r in rows if r["free"] in ("absent", "null") and r["resv"] in ("absent", "null")]
    print("  둘 다 결측(=_friction None) : %d  (MKT %d / MKT2 %d)" % (
        len(both), sum(1 for r in both if r["b"] == "MKT"), sum(1 for r in both if r["b"] == "MKT2")))
    blk["둘 다 결측(=_friction None)"] = {
        "계": len(both),
        "MKT": sum(1 for r in both if r["b"] == "MKT"),
        "MKT2": sum(1 for r in both if r["b"] == "MKT2")}
    return both, blk


DEN = {}
_, DEN["분모 A · data/market_records 파일 전수"] = tab(rows, "분모 A · data/market_records 파일 전수 %d" % len(rows))

# 분모 B: market_axes.json 에 실린 249행
ax = json.load(open(ROOT / "data/state/market_axes.json"))
sel = [r for r in rows if r["rid"] in ax]
print("\n=== 분모 B: 판 축 파일 %d 행" % len(ax))
b_both, DEN["분모 B · 판 축 파일(market_axes.json)"] = tab(sel, "분모 B · 판 축 파일 %d" % len(ax))

# 분모 C: 유보(period_from >= 2025)
hold = [r for r in sel if ax[r["rid"]]["period_from"][:4] >= "2025"]
train = [r for r in sel if ax[r["rid"]]["period_from"][:4] < "2025"]
print("\n=== 분모 C: 유보 %d · 학습 %d" % (len(hold), len(train)))
h_both, DEN["분모 C · 유보(period_from ≥ 2025)"] = tab(hold, "분모 C · 유보 %d" % len(hold))
_, DEN["분모 C′ · 학습(period_from < 2025)"] = tab(train, "분모 C′ · 학습 %d" % len(train))
OUT["분모별 계수"] = DEN

# 마스크 실측(축 파일이 적어 둔 값)
MASK = {}
for name, sub in (("분모 B · 축 파일 249", sel), ("분모 C · 유보 126", hold), ("분모 C′ · 학습 123", train)):
    m = [ax[r["rid"]]["mask"]["entry_friction"] for r in sub]
    print("%s entry_friction 마스크 평균 %.4f  (1인 행 %d / 0인 행 %d)" % (
        name, statistics.mean(m), sum(1 for x in m if x == 1.0), sum(1 for x in m if x == 0.0)))
    blk = {"n": len(sub), "마스크 평균": statistics.mean(m),
           "1인 행": sum(1 for x in m if x == 1.0), "0인 행": sum(1 for x in m if x == 0.0)}
    for bb in ("MKT", "MKT2"):
        mm = [ax[r["rid"]]["mask"]["entry_friction"] for r in sub if r["b"] == bb]
        if mm:
            print("    %-5s n=%3d 마스크평균 %.4f" % (bb, len(mm), statistics.mean(mm)))
            blk[bb] = {"n": len(mm), "마스크 평균": statistics.mean(mm)}
    MASK[name] = blk
OUT["entry_friction 마스크"] = MASK

# ── 🔴 티처 #63 M2 --- 카테고리 계수 재계수 ───────────────────────────────────
#: 🔴 옛 `docs/지평/900.md:143,149` 가 적은 수 다섯이 틀렸다는 지적. **합이 둘 다 37 이라
#: 검산이 안 걸렸다.** 여기서 분모를 이름으로 달고 다시 센다.
CAT = {}


def cat_count(rs, label):
    c = collections.Counter(r["cat"] for r in rs)
    d = {"🔴 분모": label, "n": len(rs),
         "계수": dict(sorted(c.items(), key=lambda x: (-x[1], str(x[0])))),
         "🔴 검산 · 계수 합": sum(c.values()),
         "🔴 검산 · 합 == n": sum(c.values()) == len(rs),
         "고유 카테고리 수": len(c)}
    print("\n[카테고리] %s (n=%d) → %s  (합 %d · 일치 %s)" % (
        label, len(rs), d["계수"], d["🔴 검산 · 계수 합"], d["🔴 검산 · 합 == n"]))
    CAT[label] = d
    return c


mkt_hold_miss = [r for r in h_both if r["b"] == "MKT"]
mkt2_hold_miss = [r for r in h_both if r["b"] == "MKT2"]
c15 = cat_count(mkt_hold_miss, "분모 D · 유보 결측 중 MKT %d행" % len(mkt_hold_miss))
c22 = cat_count(mkt2_hold_miss, "분모 D′ · 유보 결측 중 MKT2 %d행" % len(mkt2_hold_miss))
c37 = cat_count(h_both, "분모 E · 유보 결측 %d행" % len(h_both))
cat_count(b_both, "분모 F · 축 파일 결측 %d행" % len(b_both))
c408 = cat_count([r for r in rows if r["b"] == "MKT"], "분모 G · 원천 MKT %d행" % sum(1 for r in rows if r["b"] == "MKT"))

# 원천 408 분모의 「둘 다 null 비율」 표(900.md §2.2 의 표)
mkt_rows = [r for r in rows if r["b"] == "MKT"]
mkt_miss = collections.Counter(r["cat"] for r in mkt_rows
                               if r["free"] in ("absent", "null") and r["resv"] in ("absent", "null"))
OUT["분모 G · 원천 MKT 카테고리별 둘 다 null"] = {
    "🔴 분모": "카테고리별 MKT 원천 행 수(각 행마다 분모가 다르다 --- 조항 60)",
    "표": {k: {"n": c408[k], "둘 다 null": mkt_miss.get(k, 0),
               "비율": round(mkt_miss.get(k, 0) / c408[k], 4)} for k in sorted(c408, key=lambda x: str(x))},
    "합계": {"n": len(mkt_rows), "둘 다 null": sum(mkt_miss.values()),
             "비율": round(sum(mkt_miss.values()) / len(mkt_rows), 4)},
}

#: 🔴 옛 값과의 대조를 **손 전사 없이** 산출물 안에서 끝낸다.
OLD = {
    "docs/지평/900.md:143 · 유보 15행 중 fashion": (9, c15.get("fashion", 0)),
    "docs/지평/900.md:143 · 37행 중 fashion": (12, c37.get("fashion", 0)),
    "docs/지평/900.md:149 · 37행 중 character": (5, c37.get("character", 0)),
    "docs/지평/900.md:149 · 37행 중 fnb": (4, c37.get("fnb", 0)),
    "docs/지평/900.md:149 · 37행 중 「그 밖」": (3, 0),
}
OUT["🔴 티처 #63 M2 판정"] = {
    "무엇": "docs/지평/900.md 가 적은 카테고리 계수 다섯을 다시 셌다",
    "🔴 「그 밖」의 뜻": ("옛 본문이 카테고리 일곱을 나열하고 남은 것을 「그 밖 3」으로 적었다. "
                    "실측 37행의 고유 카테고리는 **일곱뿐**이라 잔여는 **0** 이다"),
    "대조": {k: {"옛 값(900.md)": o, "다시 센 값": n, "일치": o == n} for k, (o, n) in OLD.items()},
    "🔴 틀린 항목 수": sum(1 for o, n in OLD.values() if o != n),
    "🔴 왜 검산이 안 걸렸나": "옛 여덟 항목의 합도 37 · 새 일곱 항목의 합도 37 --- 합만으로는 못 가른다",
    "카테고리 계수 전량": CAT,
}

OUT["행 전수(증거물)"] = [{k: r[k] for k in ("rid", "file", "b", "cat", "free", "resv", "ingested")}
                     for r in rows]

#: 🔴 끝 시각은 **도장 안**에 박는다 --- 초판은 `stamp_close(OUT)` 을 불러서 끝 시각이
#: 산출물 **꼭대기**에 떨어졌고, 도장만 읽는 소비자에겐 「끝 시각이 없다」로 보였다.
#: (901 에서 산출물을 되읽다가 `KeyError` 로 잡았다 --- 조항 59: 확인 안 하면 못 본다.)
stamp_close(ST)
json.dump(OUT, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
print("\n→ %s" % OUT_PATH)
