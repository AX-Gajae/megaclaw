# -*- coding: utf-8 -*-
"""수집 래칫 — **수집이 뒷걸음질 치는 것을 막는 자** (노트 952 [수집]).

🔴 **이 사이클의 핵심이다.** 이유 하나: **자가 없으면 루프가 그 방향을 영영 안 본다.**
실측 근거 — 원장 최근 40 항목 중 내부 점검 14 + 티처 17 = 31 · **수집·원천 1**.
`data/ingest/` 도메인은 20사이클째 안 늘었다. 판 ρ 에는 자가 셋(문턱·유보·씨앗SD)이
붙어 있는데 **수집에는 자가 하나도 없었다.** 그래서 아무도 안 봤다.

🔴 **이름이 `ingest/audit.py` 가 아닌 이유**: 그 파일은 **이미 있다**(노트 643 · 2,603줄 ·
덮음/출처/절단/신선도/대조를 재는 다른 물건). 지시서가 그 이름을 불렀지만 **덮어쓰면
남의 자를 죽인다** --- 「없다」와 「못 찾았다」를 가르는 것과 같은 규율이다(조항 59).

**네 칸.**

    ① 상시 원천 수      등기부(`data/lab/sources.json`)에서 `켬:true` 인 것
    ② 마지막 성공 이후   원천마다 마지막 `성장` 부터 몇 시간
    ③ 새로 붙은 (s,a,o)  `data/ingest/sao941/pairs.jsonl.gz` + 이 사이클 후보
    ④ 원천별 수량       🔴 **953 신설** --- 등기부의 `측정꼴` 을 실제로 불러서 센다

🔴 **④ 가 왜 생겼나 (티처 #91 C1)**: main 에서 `data/ingest/wiki_daily/` **넷이 잘렸는데**
(만화는 **0 바이트**) 이 래칫이 **원리상 못 봤다.** 칸이 ①②③ 뿐이라 **원천별 행수를 세는
칸이 없었기 때문**이다. 등기부는 각 원천에 `측정꼴`(`jsonl_gz행합` 등)을 **이미 적어 두었고**
`ingest/collect.py:_measure_fn` 이 그걸 쓴다 --- 🔴 **래칫만 그 함수를 안 불렀다.**
「자를 세웠다」와 「그 자가 이 사고를 잰다」는 둘이다.

**판정.**

    🔴 단조 감소 금지 --- ① 과 ③ 과 **④ 원천별 수량**이 지난 판보다 **줄면 붉다**.
       래칫이란 그런 뜻이다.
    🔴 경과가 **2일**을 넘으면 붉다. 하루가 아니라 이틀인 이유: 크론 실패로 하루가
       흔히 빈다(주 세션 기본값). 하루로 잡으면 늑대소년이 되고, 그러면 진짜를 놓친다.
    🔴 ④ 를 **못 쟀으면**(깨진 gz 등) 그것도 붉다. **「0 행」과 「못 읽었다」는 둘이고**
       (조항 59), C1 을 낸 것이 바로 그 혼동이다. 「줄었다」와도 갈라서 신고한다.

🔴 **이 자가 못 재는 것**(스스로 신고한다):
  · **품질을 안 잰다.** 행이 늘어도 쓸 수 있는 행인지는 다른 자의 일이다(조항 59).
  · ③ 은 **후보 수**다. 판 유보에 실제로 붙는지는 **안 쟀다**.
  · 등기부에 안 적힌 원천은 **안 보인다** --- 등기부가 곧 시야다.
  · ④ 는 **행을 셀 뿐 내용을 안 본다.** 같은 수의 다른 행으로 통째 갈아치우면 못 본다.
  · ④ 는 **등기부에 `측정` 이 null 인 원천을 못 센다**(그 목록을 산출물에 싣는다).

    python3 -m ingest.harvest_ratchet          # 재고 판정 · 이력에 덧붙인다
    python3 -m ingest.harvest_ratchet --dry    # 이력에 안 쓴다
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/lab/sources.json"
COLLECT_LOG = ROOT / "data/state/collect_log.jsonl"
HISTORY = ROOT / "data/lab/harvest_ratchet.json"
SAO = ROOT / "data/ingest/sao941/pairs.jsonl.gz"

#: 🔴 **2일**이다. 하루는 크론 실패로 흔히 빈다 --- 위 독스트링에 이유를 적었다.
STALE_HOURS = 48.0


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _registry() -> dict:
    if not REGISTRY.exists():
        raise FileNotFoundError(
            "등기부가 없다: %s — 🔴 「원천이 없다」가 아니라 「등기부를 못 찾았다」다" % REGISTRY)
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def _log_rows() -> list:
    if not COLLECT_LOG.exists():
        return []
    out = []
    for ln in COLLECT_LOG.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def _sao_count() -> dict:
    """재고의 (s,a,o) 쌍 수. 🔴 **분모를 이어 붙이지 않는다**(조항 60)."""
    n = 0
    if SAO.exists():
        try:
            with gzip.open(SAO, "rt", encoding="utf-8") as f:
                n = sum(1 for _ in f)
        except Exception as e:                                    # noqa: BLE001
            return {"수": None, "🔴 못 읽었다": str(e)[:120], "통과": False}
    else:
        return {"수": None, "🔴 못 찾았다": str(SAO), "통과": False}
    extra = {}
    cnt = ROOT / "runners/out952_count.json"
    if cnt.exists():
        try:
            d = json.loads(cnt.read_text(encoding="utf-8"))
            extra["952 후보(steam_games)"] = d["steam"]["🔴 새 (s,a,o) 후보"]["수"]
        except Exception:
            extra["952 후보(steam_games)"] = "🔴 못 읽었다"
    return {"수": n, "파일": str(SAO.relative_to(ROOT)), "통과": True,
            "🔴 이것은 재고다": "아래 후보와 **이어 붙이지 않는다** --- 후보는 아직 판에 안 붙었다",
            "후보": extra}


def _source_rows() -> dict:
    """④ 원천별 수량 --- 🔴 **등기부의 `측정꼴` 을 실제로 불러서** 센다(953 신설).

    🔴 **손으로 다시 구현하지 않는다.** `ingest/collect.py:_measure_fn` 이 이미 그 일을
    하고 있고, 두 벌로 두면 **둘이 갈라진다**. 래칫이 못 본 이유는 자가 없어서가 아니라
    **있는 자를 안 불렀기 때문**이다(티처 #91 C1).

    🔴 `못읽었다` 를 **삼키지 않는다.** 깨진 gz 는 `수: None` + 사유로 남고, 판정에서
    「줄었다」와 **다른 항목**으로 붉어진다. 이 둘을 섞은 것이 C1 그 자체다.
    """
    from ingest import collect as C                    # 🔴 지연 수입 --- 순환을 피한다

    reg = _registry()
    per, nospec = [], []
    for s in reg.get("원천", []):
        spec = s.get("측정")
        if not spec:
            nospec.append({"이름": s["이름"],
                           "왜": "등기부에 `측정` 이 null --- 🔴 「0 행」이 아니라 **안 잰다**"})
            continue
        row = {"이름": s["이름"], "켬": bool(s.get("켬")), "꼴": spec.get("꼴"),
               "대상": spec.get("경로") or spec.get("디렉터리") or "🔴 모른다"}
        try:
            row["수"] = C._measure_fn(spec)()
        except Exception as e:                                    # noqa: BLE001
            row["수"] = None
            row["🔴 못 쟀다"] = "%s: %s" % (type(e).__name__, str(e)[:200])
        per.append(row)
    return {
        "원천별": per,
        "🔴 측정꼴이 없는 원천": nospec or "없음",
        "🔴 자": "등기부 `측정꼴` → `ingest/collect.py:_measure_fn` --- 두 벌로 안 만든다",
        "🔴 「0」과 「못 쟀다」는 둘이다": "깨진 gz 는 `수: None` 이다. 0 이 아니다(조항 59)",
        # 🔴 953 --- `docs/루프.md:256` 「모든 절이 `통과` 키를 갖는다」. ⑤′ 의 새 대상이
        #    **이 사이클 산출물**이 되면서 이 자가 **자기 산출물에 걸리기 시작했다**.
        "통과": all(r["수"] is not None for r in per),
    }


def read() -> dict:
    reg = _registry()
    srcs = reg.get("원천", [])
    on = [s for s in srcs if s.get("켬")]
    off = [s for s in srcs if not s.get("켬")]
    rows = _log_rows()
    now = _now()

    per = []
    for s in on:
        last = None
        for r in reversed(rows):
            if r.get("이름") == s["이름"] and r.get("판정") == "성장":
                last = r.get("시각(UTC)")
                break
        age = None
        if last:
            try:
                age = round((now - dt.datetime.fromisoformat(last)).total_seconds() / 3600, 2)
            except Exception:
                age = None
        per.append({
            "이름": s["이름"],
            "마지막 성장(UTC)": last or "🔴 장부에 성장 기록이 없다",
            "경과시간": age,
            "🔴 붉나": (age is None or age > STALE_HOURS),
            "🔴 왜": ("장부에 성장이 한 번도 없다 --- 🔴 **「안 자란다」가 아니라 "
                     "「이 자가 생기기 전이라 기록이 없다」일 수 있다**(조항 59)"
                     if age is None else
                     ("%.1f시간 > %.0f시간" % (age, STALE_HOURS) if age > STALE_HOURS else "괜찮다")),
            "라이선스": s.get("라이선스", "🔴 모른다"),
        })

    unknown_lic = [s["이름"] for s in srcs
                   if "모른다" in str(s.get("라이선스", "모른다"))]

    return {
        "시각(UTC)": now.isoformat(timespec="seconds"),
        "① 상시 원천 수": len(on),
        "① 켠 원천": [s["이름"] for s in on],
        "① 끈 원천": [{"이름": s["이름"], "왜": s.get("왜안켰나", "🔴 사유 없음")} for s in off],
        "② 원천별 경과": per,
        "② 붉은 원천 수": sum(1 for p in per if p["🔴 붉나"]),
        "③ (s,a,o)": _sao_count(),
        "④ 원천별 수량": _source_rows(),
        "🔴 라이선스를 모르는 원천": unknown_lic,
        "🔴 이 자가 못 재는 것": [
            "품질 --- 행이 늘어도 쓸 수 있는 행인지는 안 본다",
            "③ 은 **후보** 수다. 판 유보에 붙는지는 안 쟀다",
            "등기부에 없는 원천은 안 보인다 --- 등기부가 곧 시야다",
            "④ 는 **행 수**만 본다 --- 같은 수의 다른 행으로 갈아치우면 못 본다",
            "④ 는 등기부에 `측정` 이 null 인 원천을 **안 잰다**(목록을 싣는다)",
        ],
    }


def judge(cur: dict, prev: dict | None) -> dict:
    """🔴 래칫 --- **줄면 붉다.**"""
    v = {}
    if prev is None:
        v["🔴 지난 판"] = "없다 --- 오늘이 첫 판이다. **단조 검사를 못 한다**(「통과」가 아니라 「못 쟀다」)"
        v["① 안 줄었나"] = None
        v["③ 안 줄었나"] = None
    else:
        a0, a1 = prev.get("① 상시 원천 수"), cur.get("① 상시 원천 수")
        v["① 안 줄었나"] = (a1 >= a0)
        v["① 지난 판 → 오늘"] = "%s → %s" % (a0, a1)
        b0 = (prev.get("③ (s,a,o)") or {}).get("수")
        b1 = (cur.get("③ (s,a,o)") or {}).get("수")
        v["③ 안 줄었나"] = (b1 >= b0) if (b0 is not None and b1 is not None) else None
        v["③ 지난 판 → 오늘"] = "%s → %s" % (b0, b1)
    v["② 2일 넘은 원천"] = [p["이름"] for p in cur["② 원천별 경과"] if p["🔴 붉나"]]

    # ── ④ 원천별 수량 --- 🔴 953 신설(티처 #91 C1) ──────────────────────
    def _four(d):
        return {r["이름"]: r for r in ((d or {}).get("④ 원천별 수량") or {}).get("원천별", [])}

    c4, p4 = _four(cur), _four(prev)
    dec, unk, fresh = [], [], []
    for name, r in sorted(c4.items()):
        n1 = r.get("수")
        if n1 is None:
            # 🔴 **「줄었다」가 아니다.** 깨진 gz --- C1 이 정확히 이 자리다
            unk.append({"이름": name, "🔴 왜": r.get("🔴 못 쟀다", "사유 없음")})
            continue
        p = p4.get(name)
        if p is None or p.get("수") is None:
            fresh.append({"이름": name, "오늘": n1,
                          "🔴 왜": ("지난 판에 이 원천이 없다" if p is None
                                  else "지난 판이 이 원천을 **못 쟀다**")})
            continue
        if n1 < p["수"]:
            dec.append({"이름": name, "지난 판 → 오늘": "%s → %s" % (p["수"], n1),
                        "차": n1 - p["수"]})
    gone = sorted(set(p4) - set(c4))
    v["④ 원천별"] = {
        "잰 원천 수": len(c4),
        "🔴 안 줄었나": (None if not p4 else (not dec and not gone)),
        "🔴 줄어든 원천": dec or "없음",
        "🔴 못 쟀다(=깨졌다. 「0 행」이 아니다)": unk or "없음",
        "지난 판과 못 견주는 것(첫 판·지난 판이 못 쟀다)": fresh or "없음",
        "🔴 지난 판에서 사라진 원천": gone or "없음",
        "🔴 부기": ("지난 판에 ④ 칸이 아예 없으면 **「통과」가 아니라 「못 쟀다」**다"
                  if not p4 else "지난 판의 ④ 와 이름별로 견줬다"),
    }

    reds = []
    if v.get("① 안 줄었나") is False:
        reds.append("① 상시 원천 수가 줄었다")
    if v.get("③ 안 줄었나") is False:
        reds.append("③ (s,a,o) 가 줄었다")
    if dec:
        reds.append("④ 원천 %d 의 수량이 줄었다: %s"
                    % (len(dec), ", ".join("%s(%s)" % (d["이름"], d["지난 판 → 오늘"]) for d in dec)))
    if unk:
        reds.append("④ 원천 %d 을 **못 쟀다**(「0 행」이 아니다): %s"
                    % (len(unk), ", ".join(u["이름"] for u in unk)))
    if gone:
        reds.append("④ 원천 %d 이 등기부에서 사라졌다: %s" % (len(gone), ", ".join(gone)))
    if v["② 2일 넘은 원천"]:
        reds.append("② %d 원천이 %.0f시간을 넘겼다: %s"
                    % (len(v["② 2일 넘은 원천"]), STALE_HOURS, ", ".join(v["② 2일 넘은 원천"])))
    v["🔴 붉은 항목"] = reds
    v["초록인가"] = (not reds)
    v["통과"] = (not reds)          # 🔴 953 --- 키 이름을 규약(`통과`)에 맞춘다
    v["🔴 부기"] = ("붉은 채로 싣는다. 🔴 **붉음을 없애려고 문턱을 올리지 마라** --- "
                   "그건 자를 고치는 게 아니라 자를 버리는 것이다")
    return v


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="이력에 안 쓴다")
    ap.add_argument("--out", default=None,
                    help="🔴 이번 판을 이 경로에도 찍는다(채점기가 읽을 자리 · 953)")
    a = ap.parse_args()

    hist = []
    if HISTORY.exists():
        try:
            hist = json.loads(HISTORY.read_text(encoding="utf-8")).get("이력", [])
        except Exception:
            hist = []
    prev = hist[-1] if hist else None

    cur = read()
    cur["판정"] = judge(cur, prev)

    print("수집 래칫 %s" % cur["시각(UTC)"])
    print("  ① 상시 원천 %d개: %s" % (cur["① 상시 원천 수"], ", ".join(cur["① 켠 원천"])))
    for p in cur["② 원천별 경과"]:
        print("     %-14s %-8s %s" % (p["이름"],
                                      ("%.1fh" % p["경과시간"]) if p["경과시간"] is not None else "기록없음",
                                      "🔴" if p["🔴 붉나"] else "✅"))
    print("  ③ (s,a,o) 재고 %s · 후보 %s"
          % (cur["③ (s,a,o)"].get("수"), cur["③ (s,a,o)"].get("후보")))
    for r in cur["④ 원천별 수량"]["원천별"]:
        print("     ④ %-14s %-12s %s" % (r["이름"], r["꼴"],
                                         r["수"] if r["수"] is not None
                                         else "🔴 못 쟀다 — " + r.get("🔴 못 쟀다", "")[:60]))
    if cur["🔴 라이선스를 모르는 원천"]:
        print("  🔴 라이선스 모름:", ", ".join(cur["🔴 라이선스를 모르는 원천"]))
    j = cur["판정"]
    print("  판정:", "✅ 초록" if j["초록인가"] else "🔴 붉음 — " + " · ".join(j["🔴 붉은 항목"]))

    if a.out:
        # 🔴 이력은 **덧붙이는 물건**이라 채점기가 「이번 판」을 가리키기 어렵다.
        #    이번 판을 따로 찍어 둔다 --- 손으로 옮겨 적는 자리를 없앤다.
        p = ROOT / a.out
        p.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")
        print("→", p)

    if not a.dry:
        hist.append(cur)
        HISTORY.write_text(json.dumps(
            {"무엇": "수집 래칫 이력 — 🔴 추가만 한다. 옛 판을 고치지 않는다(노트 952)",
             "문턱": {"경과 붉음": "%.0f시간" % STALE_HOURS,
                     "왜 하루가 아닌가": "크론 실패로 하루는 흔히 빈다 — 하루로 잡으면 늑대소년이 된다"},
             "이력": hist}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("→", HISTORY)
    return 0 if cur["판정"]["초록인가"] else 1


if __name__ == "__main__":
    sys.exit(main())
