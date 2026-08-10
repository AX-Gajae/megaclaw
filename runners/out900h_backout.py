# -*- coding: utf-8 -*-
"""지평 900 --- 조항 60: 저장소가 이미 가진 열로 두 필드를 역산할 수 있나. 읽기 전용.

🔴 **901 수리 B 개정(이슈 #136 M9)**. 옛 판은 `json.dump` 가 **0건**이었다 --- 표를 화면에
찍고 끝났다. 화면은 세션과 함께 사라지고, 그래서 무엇을 셌는지 저장소에 남은 게 없었다.
이제 `runners/out900h_backout.json` 에 쓰고 도장 규약 v3.2 를 박는다:
시작 시각 · **끝 시각** · **코드 sha256** · **입력 파일 sha256**.
🔴 `git HEAD` 는 **판정에 쓰지 마라**(v3.2 폐기 --- 긴 러너에선 원리상 「시작 시점」).
본보기는 `runners/out899a_gates.py:235-249`.

🔴 **조항 60** --- 아래 모든 계수는 **분모 이름을 달고** 나른다.
"""
import collections
import datetime as dt
import glob
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
OUT_PATH = ROOT / "runners/out900h_backout.json"

STAMP_CODE = ["runners/out900h_backout.py"]
STAMP_INPUT = ["data/state/market_axes.json"]
STAMP_INPUT_GLOB = "data/market_records/*.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def sha_many(paths) -> dict:
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
    st["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return st


ax = json.load(open(ROOT / "data/state/market_axes.json"))

FREE_POS = [r"무료\s*입장", r"입장\s*무료", r"무료로\s*입장", r"관람\s*무료", r"입장료\s*(는\s*)?없", r"무료\s*운영", r"누구나\s*무료"]
FREE_NEG = [r"입장료", r"유료\s*입장", r"입장\s*유료", r"티켓\s*(가격|구매|판매|값)", r"관람료", r"\d[\d,]*\s*원\s*(의\s*)?입장"]
RESV_POS = [r"사전\s*예약", r"예약\s*(필수|제)", r"네이버\s*예약", r"캐치테이블", r"예약\s*링크", r"예약자\s*(만|에\s*한)", r"예약\s*후\s*(방문|입장)"]
RESV_NEG = [r"예약\s*없이", r"예약\s*불(필요|가)", r"현장\s*(방문|접수|등록)만", r"워크\s*인", r"walk[- ]?in", r"자유\s*관람"]
ANY_RESV = [r"예약"]

TEXT_FIELDS = ("event_name·brand·ip_or_collab·notes·intervention.concept_description·"
               "outcome.counting_basis_note·outcome.visitors_source_quote·outcome.sales_source_quote·"
               "outcome.demand_signals.waiting_time_reported·intervention.experience_elements[]·"
               "intervention.promotions[]·outcome.demand_signals.signal_quotes[]")


def txt(d):
    iv = d.get("intervention") or {}
    oc = d.get("outcome") or {}
    ds = oc.get("demand_signals") or {}
    parts = [d.get("event_name"), d.get("brand"), d.get("ip_or_collab"), d.get("notes"),
             iv.get("concept_description"), oc.get("counting_basis_note"),
             oc.get("visitors_source_quote"), oc.get("sales_source_quote"),
             ds.get("waiting_time_reported")]
    parts += list(iv.get("experience_elements") or []) + list(iv.get("promotions") or [])
    parts += list(ds.get("signal_quotes") or [])
    return " \n ".join(str(x) for x in parts if x)


def hit(pats, s):
    return [p for p in pats if re.search(p, s)]


recs = {}
for f in glob.glob(str(ROOT / STAMP_INPUT_GLOB)):
    d = json.load(open(f))
    recs[d["market_record_id"]] = d

groups = {
    "유보결측37": [k for k in ax if ax[k]["period_from"][:4] >= "2025"
                and (recs[k]["intervention"].get("is_free_entry") is None
                     and recs[k]["intervention"].get("reservation_required") is None)],
    "축파일결측88": [k for k in ax
                 if (recs[k]["intervention"].get("is_free_entry") is None
                     and recs[k]["intervention"].get("reservation_required") is None)],
    "MKT2전체239": [k for k in recs if k.startswith("MKT2")],
    "MKT값있음(검정용)": [k for k in recs if not k.startswith("MKT2")
                     and recs[k]["intervention"].get("is_free_entry") is not None],
}

ST = stamp()
OUT = {
    "무엇": "조항 60 --- 저장소가 이미 가진 텍스트 열로 is_free_entry·reservation_required 를 역산할 수 있나",
    "🔴 조항 60": "모든 계수는 **분모 이름(=그룹 이름과 n)** 을 달고 나른다",
    "도장": ST,
    "훑은 텍스트 칸": TEXT_FIELDS,
    "정규식": {"FREE_POS": FREE_POS, "FREE_NEG": FREE_NEG,
             "RESV_POS": RESV_POS, "RESV_NEG": RESV_NEG, "ANY_RESV": ANY_RESV},
}

CUE = {}
for name, ids in groups.items():
    fp = fn = rp = rn = both = 0
    anyr = 0
    for k in sorted(ids):
        s = txt(recs[k])
        a, b = bool(hit(FREE_POS, s)), bool(hit(FREE_NEG, s))
        c, e = bool(hit(RESV_POS, s)), bool(hit(RESV_NEG, s))
        fp += a
        fn += b
        rp += c
        rn += e
        anyr += bool(hit(ANY_RESV, s))
        both += (a or b) and (c or e)
    print("%-16s n=%4d | 무료단서 %3d · 유료단서 %3d · 예약필요단서 %3d · 예약없음단서 %3d · '예약'언급 %3d · 둘다 %3d"
          % (name, len(ids), fp, fn, rp, rn, anyr, both))
    CUE[name] = {"🔴 분모": "%s (n=%d)" % (name, len(ids)), "n": len(ids),
                 "무료단서": fp, "유료단서": fn, "예약필요단서": rp, "예약없음단서": rn,
                 "'예약' 언급": anyr, "둘 다 단서 있음": both}
OUT["단서 계수(그룹별 · 분모 명기)"] = CUE

# 검정: MKT 에서 값이 있는 행에 규칙을 돌려 정확도를 잰다
print("\n=== 규칙 검정 (MKT 중 값이 있는 행) ===")
VAL = {}
for fld, POS, NEG, want_pos in (("is_free_entry", FREE_POS, FREE_NEG, True),
                                ("reservation_required", RESV_POS, RESV_NEG, True)):
    tab = collections.Counter()
    for k, d in recs.items():
        if k.startswith("MKT2"):
            continue
        v = d["intervention"].get(fld)
        if v is None:
            continue
        s = txt(d)
        p, n = bool(hit(POS, s)), bool(hit(NEG, s))
        pred = "pos" if (p and not n) else ("neg" if (n and not p) else ("both" if p and n else "none"))
        tab[(bool(v), pred)] += 1
    print(" ", fld)
    blk = {}
    for kk in sorted(tab, key=lambda x: (x[0], x[1])):
        print("     실제=%-5s 규칙=%-5s %4d" % (kk[0], kk[1], tab[kk]))
        blk["실제=%s · 규칙=%s" % (kk[0], kk[1])] = tab[kk]
    n = sum(tab.values())
    #: 🔴 조항 59 --- 「단서 없음(none)」은 「틀렸다」가 아니라 **「안 잡혔다」**다. 셋을 가른다.
    correct = tab[(True, "pos")] + tab[(False, "neg")]
    wrong = tab[(True, "neg")] + tab[(False, "pos")]
    silent = tab[(True, "none")] + tab[(False, "none")] + tab[(True, "both")] + tab[(False, "both")]
    VAL[fld] = {"🔴 분모": "MKT 중 %s 값이 있는 행 (n=%d)" % (fld, n), "n": n,
                "표": blk,
                "맞음": correct, "틀림": wrong, "🔴 안 잡힘(none/both)": silent,
                "적용률": (round((correct + wrong) / n, 4) if n else None),
                "적용된 것 중 정확도": (round(correct / (correct + wrong), 4) if (correct + wrong) else None)}
    print("     → 적용 %d/%d · 맞음 %d · 틀림 %d · 🔴 안 잡힘 %d" % (correct + wrong, n, correct, wrong, silent))
OUT["규칙 검정(MKT 중 값이 있는 행)"] = VAL

OUT["🔴 판정"] = {
    "reservation_required": "일부 역산된다(적용된 행에서만) --- 적용률이 낮아 전량 채움은 불가",
    "is_free_entry": "🔴 안 된다 --- 값이 있는 274행에서 규칙이 사실상 아무것도 안 잡는다",
    "왜": "무료 팝업은 무료를 안 적는다(무표지가 기본값) --- 텍스트에 단서가 원리상 없다",
}

#: 🔴 끝 시각은 **도장 안**에 박는다(census 와 같은 이유 --- 꼭대기에 떨어지면 도장만 읽는
#: 소비자에겐 「없다」로 보인다).
stamp_close(ST)
json.dump(OUT, open(OUT_PATH, "w"), ensure_ascii=False, indent=1)
print("\n→ %s" % OUT_PATH)
