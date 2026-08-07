"""입장 허들의 진짜 측정 --- 가격이 아니라 접근 장벽.

노트 16이 가격을 허들 자리에서 뺐다. 두 도메인(아이돌·게임)에서 가격은 치르는
값이 아니라 만든 규모를 알리는 신호였다. 축 자체는 남아 있다 --- '닿는 데 무엇을
치르는가'는 실재할 수 있고, 가격이 그것을 재지 못했을 뿐이다.

게임에는 가격과 독립인 접근 장벽이 있다. **최소 사양**이다. 돈이 있어도 기기가
안 되면 못 산다.

**함정 하나를 미리 피한다.** 최소 사양을 절대값으로 쓰면 가격과 같은 함정에
빠진다 --- 사양이 높은 게임은 대개 대작이고, 대작은 반응이 크다. 그리고 사양
요구는 해가 갈수록 올라간다(2015년의 8GB와 2026년의 8GB는 다른 뜻이다).

그래서 **같은 해 출시작 대비 상대값**으로 잰다. 동시대 작품보다 사양이 높으면
그만큼 돌릴 수 있는 사람이 적다 --- 그것이 순수한 접근 장벽이다.

측정 항목:
    최소 RAM (GB)        --- 그 해 중앙값 대비 비율
    최소 저장 공간 (GB)   --- 그 해 중앙값 대비 비율
    연령 등급             --- 볼 수 있는 사람의 범위를 직접 자른다

사용: python3 -m ingest.game_friction
"""
from __future__ import annotations

import glob
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

CACHE = Path("data/state/cache_steam")
REC = Path("data/state/game_records.json")
OUT = Path("data/state/game_friction.json")

RAM = re.compile(r"(?:메모리|Memory)\s*:?\s*([\d.]+)\s*(GB|MB)", re.I)
DISK = re.compile(r"(?:저장\s*공간|Storage)\s*:?\s*([\d.]+)\s*(GB|MB)", re.I)


def strip(h: str) -> str:
    return re.sub(r"<[^>]+>", " ", h or "")


def parse_min(a: dict) -> dict:
    pr = a.get("pc_requirements") or {}
    txt = strip(pr.get("minimum") if isinstance(pr, dict) else "")
    out = {}
    for key, rx in (("ram_gb", RAM), ("disk_gb", DISK)):
        m = rx.search(txt)
        if m:
            v = float(m.group(1))
            out[key] = v / 1024.0 if m.group(2).upper() == "MB" else v
    out["required_age"] = int(a.get("required_age") or 0)
    out["is_64bit"] = bool(re.search(r"64\s*(비트|bit)", txt, re.I))
    return out


def run(write: bool = True) -> dict:
    recs = json.loads(REC.read_text())
    raw = {}
    for f in CACHE.glob("app_*.json"):
        appid = f.stem.split("_", 1)[1]
        rid = f"GAME-{appid}"
        if rid not in recs:
            continue
        try:
            d = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        x = (d.get(appid) or {})
        if not x.get("success"):
            continue
        raw[rid] = parse_min(x.get("data") or {})

    print(f"사양 파싱 {len(raw)}/{len(recs)}건")
    for k in ("ram_gb", "disk_gb"):
        got = sum(1 for v in raw.values() if v.get(k))
        print(f"  {k:<10}{got:>4}건 ({got/max(1,len(raw)):.0%})")
    ages = [v["required_age"] for v in raw.values()]
    print(f"  required_age  0인 비율 {np.mean([a == 0 for a in ages]):.0%}  "
          f"최대 {max(ages)}")

    # 같은 해 중앙값으로 정규화 --- 절대 사양은 규모와 교란되고 해마다 올라간다
    by_year = defaultdict(list)
    for rid, v in raw.items():
        y = (recs[rid].get("release_date") or "")[:4]
        if v.get("ram_gb"):
            by_year[y].append(v["ram_gb"])
    med = {y: float(np.median(v)) for y, v in by_year.items() if len(v) >= 5}
    print(f"\n연도별 최소 RAM 중앙값(5건 이상): "
          f"{ {y: round(m, 1) for y, m in sorted(med.items())[-6:]} }")

    out = {}
    for rid, v in raw.items():
        y = (recs[rid].get("release_date") or "")[:4]
        rel = None
        if v.get("ram_gb") and y in med and med[y] > 0:
            rel = float(np.log2(v["ram_gb"] / med[y]))     # 0 = 동시대 평균
        out[rid] = {**v, "ram_rel_log2": rel, "year": y}
    got = sum(1 for v in out.values() if v["ram_rel_log2"] is not None)
    print(f"상대 사양 산출 {got}건")
    if write:
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"저장: {OUT}")
    return out


if __name__ == "__main__":
    run()
