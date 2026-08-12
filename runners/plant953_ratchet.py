# -*- coding: utf-8 -*-
"""노트 953 --- 🔴 **래칫의 ④ 칸이 실제로 무는가**를 **심어서** 잰다.

「돈다」와 「막는다」는 둘이다. 칸을 넣고 초록이 나오는 것은 **아무것도 증명하지 않는다** ---
결함을 심었을 때 **붉어지고**, 되돌렸을 때 **초록으로 돌아와야** 자다.

🔴 **진짜 자료를 안 자른다.** 상시 데몬이 `data/ingest`·`data/state` 를 1분마다 자동
커밋하므로 저장소 안의 gz 를 일부러 자르면 **그것이 티처 #91 C1 의 재발**이다.
그래서 고정물을 **저장소 밖**(스크래치패드)에 짓고 `ingest.collect.ROOT` 와
`ingest.harvest_ratchet` 의 경로 전역을 갈아 끼운다.

**심는 것 넷**

    ㄱ 줄을 지운다        gz 에서 5행 삭제 → ④ 가 「줄었다」로 붉어야 한다
    ㄴ 되돌린다           → 초록으로 돌아와야 한다
    ㄷ 바이트를 자른다     gz 뒤를 잘라 깨뜨림 → 🔴 **「0 행」이 아니라 「못 쟀다」**로 붉어야 한다
    ㄹ 되돌린다           → 초록으로 돌아와야 한다

**🔴 음성 대조** --- 같은 결함을 **옛 자(④ 칸이 없는 판정)**에 물리면 **안 잡힌다**.
그게 「이 칸이 물었다」의 증거다(칸 말고 다른 것이 붉힌 게 아니다).

    python3 -m runners.plant953_ratchet
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIX = Path("/private/tmp/claude-501/-Users-ax-world-model/"
           "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad/plant953")
OUT = ROOT / "runners/out953_plant.json"


def _gz(path: Path, n: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for i in range(n):
            f.write(json.dumps({"i": i}, ensure_ascii=False) + "\n")


def build() -> None:
    if FIX.exists():
        shutil.rmtree(FIX)
    (FIX / "data/lab").mkdir(parents=True)
    (FIX / "data/state").mkdir(parents=True)
    _gz(FIX / "data/ingest/모의_한글/가.jsonl.gz", 100)     # 🔴 한글 경로도 함께 판다
    _gz(FIX / "data/ingest/모의_한글/나.jsonl.gz", 50)
    _gz(FIX / "data/ingest/sao/pairs.jsonl.gz", 7)
    (FIX / "data/state/plain.jsonl").write_text(
        "".join("{\"x\":%d}\n" % i for i in range(30)), encoding="utf-8")
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    (FIX / "data/state/collect_log.jsonl").write_text(
        "".join(json.dumps({"이름": n, "판정": "성장", "시각(UTC)": now},
                           ensure_ascii=False) + "\n"
                for n in ("모의gz", "모의행")), encoding="utf-8")
    (FIX / "data/lab/sources.json").write_text(json.dumps({
        "판": 0, "생긴때": "고정물 --- 노트 953 심기 시험",
        "원천": [
            {"이름": "모의gz", "모듈": "x", "켬": True, "최소간격초": 60, "단위": "행",
             "측정": {"꼴": "jsonl_gz행합", "디렉터리": "data/ingest/모의_한글"},
             "라이선스": "고정물"},
            {"이름": "모의행", "모듈": "y", "켬": True, "최소간격초": 60, "단위": "행",
             "측정": {"꼴": "jsonl행", "경로": "data/state/plain.jsonl"},
             "라이선스": "고정물"},
            {"이름": "모의측정없음", "모듈": None, "켬": False, "왜안켰나": "고정물",
             "측정": None, "라이선스": "고정물"},
        ]}, ensure_ascii=False, indent=1), encoding="utf-8")


def snap(hr):
    cur = hr.read()
    return cur


def main() -> int:
    import ingest.collect as C
    import ingest.harvest_ratchet as HR

    build()
    C.ROOT = FIX
    HR.ROOT = FIX
    HR.REGISTRY = FIX / "data/lab/sources.json"
    HR.COLLECT_LOG = FIX / "data/state/collect_log.jsonl"
    HR.SAO = FIX / "data/ingest/sao/pairs.jsonl.gz"

    res = {
        "무엇": "🔴 래칫 ④ 칸이 **실제로 무는가** --- 심어서 잰다(노트 953)",
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "래칫sha": subprocess.run(["shasum", "-a", "256", str(ROOT / "ingest/harvest_ratchet.py")],
                                capture_output=True, text=True).stdout.split()[0],
        "🔴 고정물": str(FIX),
        "🔴 왜 저장소 밖인가": ("상시 데몬이 `data/ingest`·`data/state` 를 자동 커밋한다. "
                        "진짜 gz 를 일부러 자르면 **그게 티처 #91 C1 의 재발**이다"),
        "🔴 갈아 끼운 것": ["ingest.collect.ROOT", "harvest_ratchet.ROOT/REGISTRY/COLLECT_LOG/SAO"],
    }

    base = snap(HR)
    res["0 기준선"] = {
        "④ 원천별": [{"이름": r["이름"], "수": r["수"]} for r in base["④ 원천별 수량"]["원천별"]],
        "🔴 측정꼴 없는 원천": base["④ 원천별 수량"]["🔴 측정꼴이 없는 원천"],
        "판정(prev=자기 자신)": HR.judge(base, base)["초록인가"],
        "통과": HR.judge(base, base)["초록인가"] is True,
    }

    tgt = FIX / "data/ingest/모의_한글/가.jsonl.gz"
    keep = tgt.read_bytes()

    # ── ㄱ 줄을 지운다 ──────────────────────────────────────────────
    _gz(tgt, 95)
    cur = snap(HR)
    j = HR.judge(cur, base)
    got = [r for r in cur["④ 원천별 수량"]["원천별"] if r["이름"] == "모의gz"][0]
    res["1 심음 ㄱ --- 5행 지웠다"] = {
        "④ 모의gz": got["수"], "기준선": 150,
        "붉나": not j["초록인가"], "붉은 항목": j["🔴 붉은 항목"],
        "🔴 ④ 때문에 붉나": any("④" in x and "줄었다" in x for x in j["🔴 붉은 항목"]),
        "통과": (not j["초록인가"]) and any("④" in x and "줄었다" in x for x in j["🔴 붉은 항목"]),
    }

    # ── 🔴 음성 대조: 옛 자(④ 칸이 없는 판정)는 못 잡는다 ─────────────
    old_cur = dict(cur)
    old_base = dict(base)
    old_cur.pop("④ 원천별 수량")
    old_base.pop("④ 원천별 수량")
    jo = HR.judge(old_cur, old_base)
    res["1-나 🔴 음성 대조 --- 옛 자(④ 없음)"] = {
        "🔴 옛 자는 초록인가": jo["초록인가"],
        "옛 자의 붉은 항목": jo["🔴 붉은 항목"] or "없음",
        "🔴 뜻": ("같은 결함(5행 손실)을 ④ 칸 없이 보면 **안 잡힌다**. "
                "그래서 ㄱ 의 붉음은 **이 칸이 낸 것**이다 --- 다른 것이 붉힌 게 아니다"),
        "통과": jo["초록인가"] is True,
    }

    # ── ㄴ 되돌린다 ────────────────────────────────────────────────
    tgt.write_bytes(keep)
    cur2 = snap(HR)
    j2 = HR.judge(cur2, base)
    res["2 되돌림"] = {
        "④ 모의gz": [r for r in cur2["④ 원천별 수량"]["원천별"]
                   if r["이름"] == "모의gz"][0]["수"],
        "초록인가": j2["초록인가"], "붉은 항목": j2["🔴 붉은 항목"] or "없음",
        "통과": j2["초록인가"] is True,
    }

    # ── ㄷ 바이트를 자른다 --- 🔴 「0 행」이 아니라 「못 쟀다」 ──────────
    tgt.write_bytes(keep[:len(keep) // 2])
    cur3 = snap(HR)
    j3 = HR.judge(cur3, base)
    g3 = [r for r in cur3["④ 원천별 수량"]["원천별"] if r["이름"] == "모의gz"][0]
    res["3 심음 ㄷ --- gz 를 바이트 절단"] = {
        "④ 모의gz 수": g3["수"],
        "🔴 0 으로 셌나": g3["수"] == 0,
        "🔴 못 쟀다로 셌나": g3["수"] is None,
        "사유": g3.get("🔴 못 쟀다", "없음"),
        "붉나": not j3["초록인가"], "붉은 항목": j3["🔴 붉은 항목"],
        "🔴 「줄었다」와 갈랐나": any("못 쟀다" in x for x in j3["🔴 붉은 항목"]),
        "통과": (g3["수"] is None and (not j3["초록인가"])
               and any("못 쟀다" in x for x in j3["🔴 붉은 항목"])),
    }

    # ── ㄹ 되돌린다 ────────────────────────────────────────────────
    tgt.write_bytes(keep)
    cur4 = snap(HR)
    j4 = HR.judge(cur4, base)
    res["4 되돌림"] = {
        "초록인가": j4["초록인가"], "붉은 항목": j4["🔴 붉은 항목"] or "없음",
        "통과": j4["초록인가"] is True,
    }

    # ── ㅁ 원천이 등기부에서 사라지면 ────────────────────────────────
    reg = json.loads(HR.REGISTRY.read_text(encoding="utf-8"))
    reg["원천"] = [s for s in reg["원천"] if s["이름"] != "모의행"]
    HR.REGISTRY.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    cur5 = snap(HR)
    j5 = HR.judge(cur5, base)
    res["5 심음 ㅁ --- 원천을 등기부에서 뺐다"] = {
        "붉나": not j5["초록인가"], "붉은 항목": j5["🔴 붉은 항목"],
        "🔴 ④ 가 사라짐을 봤나": any("사라졌다" in x for x in j5["🔴 붉은 항목"]),
        "통과": (not j5["초록인가"]) and any("사라졌다" in x for x in j5["🔴 붉은 항목"]),
    }

    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    fail = sorted(k for k, v in secs.items() if not v["통과"])
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 실패한 절"] = fail or "없음"
    res["통과"] = not fail
    res["🔴 이 시험이 못 재는 것"] = [
        "고정물은 **작다**(150행). 실제 원천 크기에서의 성능은 안 쟀다",
        "같은 수의 **다른 행**으로 갈아치우는 것은 여전히 못 잡는다 --- ④ 는 행 수만 본다",
        "`디렉터리관측`·`디렉터리바이트` 꼴은 **안 심었다**(gz·jsonl 둘만)",
        "동시 쓰기(데몬과 러너가 같은 파일을) 는 안 심었다",
    ]
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT, "통과" if res["통과"] else "🔴 실패: " + ", ".join(fail))
    for k, v in secs.items():
        print("   %-34s %s" % (k, "✅" if v["통과"] else "🔴"))
    return 0 if res["통과"] else 1


if __name__ == "__main__":
    sys.exit(main())
