# -*- coding: utf-8 -*-
"""노트 901 · 지평 팔 ①단계 — **서울 생활인구 250m 두 달치를 실제로 열어서 센다.**

899 가 받아 두고 899·900 두 사이클이 안 만진 zip 둘을 **압축을 풀지 않고 스트림으로**
읽어 행수·열·기간·격자 수를 센다. 🔴 zip 은 `.gitignore` 라 저장소엔 요약만 남긴다.

산출물
  runners/out901h_grid.json                 요약(저장소에 남는다)
  <스크래치패드>/out901h_gridmap.json       격자 → 행정동코드 집합(다음 단계 입력 · 저장소 밖)

사용: python3 runners/out901h_lifepop.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
SRC = ROOT / "data/ingest/seoul_lifepop"
ZIPS = ["250_LOCAL_RESD_202606.zip", "250_LOCAL_RESD_202607.zip"]
SCRATCH = Path(os.environ.get(
    "OUT901H_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad"))
OUT = ROOT / "runners/out901h_grid.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sha_text(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def stamp() -> dict:
    return {"시각(UTC · 시작)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "🔴 코드 sha256(이게 자다)": {"runners/out901h_lifepop.py": sha_text(Path(__file__).resolve())}}


def scan_zip(zp: Path) -> dict:
    """CSV 를 풀지 않고 읽는다. 필드 0~3 만 본다(일자·시간·행정동코드·250M격자)."""
    rows = 0
    days: dict[str, int] = {}
    hours: set[str] = set()
    dongs: set[str] = set()
    grids: set[str] = set()
    pairs: set[tuple[str, str]] = set()
    headers: set[str] = set()
    members = []
    bad = 0
    with zipfile.ZipFile(zp) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        members = sorted(names)
        for n in members:
            with z.open(n) as f:
                first = True
                for raw in f:
                    if first:
                        first = False
                        headers.add(raw.decode("cp949", "replace").strip().replace('"', ""))
                        continue
                    if not raw.strip():
                        continue
                    p = raw.split(b",", 4)
                    if len(p) < 4:
                        bad += 1
                        continue
                    rows += 1
                    # 🔴 필드는 큰따옴표로 싸여 있고 `행정동코드` 는 오른쪽 공백 패딩이다.
                    # 둘 다 안 벗기면 조인이 조용히 0건 난다(899 §5.2 의 함정 (가)).
                    d = p[0].decode("ascii", "replace").strip().strip('"').strip()
                    h = p[1].decode("ascii", "replace").strip().strip('"').strip()
                    dg = p[2].decode("ascii", "replace").strip().strip('"').strip()
                    gd = p[3].decode("cp949", "replace").strip().strip('"').strip()
                    days[d] = days.get(d, 0) + 1
                    hours.add(h)
                    dongs.add(dg)
                    grids.add(gd)
                    pairs.add((dg, gd))
    return {"파일": zp.name, "바이트": zp.stat().st_size, "sha256": sha(zp),
            "CSV 수": len(members), "포장": ("폴더" if any("/" in m for m in members) else "평면"),
            "헤더 가짓수": len(headers), "헤더": sorted(headers)[0].split(","),
            "열 수": len(sorted(headers)[0].split(",")),
            "행수": rows, "쪼개기 실패 행": bad,
            "일수": len(days), "기간": [min(days), max(days)] if days else None,
            "하루 행수 최소/최대": [min(days.values()), max(days.values())] if days else None,
            "시간 칸": sorted(hours),
            "서로 다른 행정동코드": len(dongs),
            "서로 다른 250M격자": len(grids),
            "서로 다른 (행정동,격자) 쌍": len(pairs),
            "_grids": sorted(grids), "_pairs": sorted(pairs)}


def main() -> None:
    st = stamp()
    st["입력 파일"] = {}
    per = []
    for nm in ZIPS:
        zp = SRC / nm
        if not zp.exists():
            per.append({"파일": nm, "🔴": f"없다 — {zp} 를 봤는데 없다"})
            continue
        r = scan_zip(zp)
        st["입력 파일"][f"data/ingest/seoul_lifepop/{nm}"] = r["sha256"]
        per.append(r)

    allg, allp = set(), set()
    for r in per:
        allg |= set(r.get("_grids") or [])
        allp |= {tuple(x) for x in (r.get("_pairs") or [])}
    g2d: dict[str, list[str]] = {}
    for dg, gd in allp:
        g2d.setdefault(gd, []).append(dg)

    SCRATCH.mkdir(parents=True, exist_ok=True)
    (SCRATCH / "out901h_gridmap.json").write_text(
        json.dumps({"격자→행정동코드": {k: sorted(v) for k, v in g2d.items()}},
                   ensure_ascii=False), encoding="utf-8")

    out = {"노트": 901, "갈래": "지평(⓪-나) ①단계 — 자료 실측",
           "🔴 자": "뗐다 — 계수만. 효과도 판정도 없다",
           **st,
           "달별": [{k: v for k, v in r.items() if not k.startswith("_")} for r in per],
           "합": {"두 달 합 행수": sum(r.get("행수", 0) for r in per),
                  "두 달 합집합 격자": len(allg),
                  "두 달 합집합 (행정동,격자) 쌍": len(allp),
                  "격자→행정동 1:1 인 격자": sum(1 for v in g2d.values() if len(v) == 1),
                  "격자가 여러 행정동에 걸친 수": sum(1 for v in g2d.values() if len(v) > 1),
                  "서로 다른 시군구(행정동코드[:5])": len({d[:5] for d, _ in allp})},
           "격자 지도 둔 곳(저장소 밖)": str(SCRATCH / "out901h_gridmap.json")}
    out["시각(UTC · 끝)"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("합", "시각(UTC · 끝)")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
