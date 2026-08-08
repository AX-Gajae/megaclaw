# -*- coding: utf-8 -*-
# 절단 만기 러너(865 P3′ⓑ) — game_recent.json 의 절단 행이 만기(출시+30일 경과)하면
# lab.gamew30(UTC 정본 정의)로 재계산해 game_recent_utc.json 에 **추가**한다(원본 불변 · provenance 병기).
# 사용: python3 runners/gamematured.py [--plan]   · 만기 22행 완료 예정 2026-08-23
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from lab.gamew30 import w30_epoch  # noqa: E402 — UTC 정본의 유일 구현

ROOT = Path("/Users/ax/world_model")


def main():
    today = dt.date.today()
    GR = json.load(open(ROOT / "data/state/game_recent.json"))
    rows = list(GR.values()) if isinstance(GR, dict) else GR
    UF = ROOT / "data/state/game_recent_utc.json"
    u = json.load(open(UF))
    done = set(u["행"])
    matured = [r for r in rows if r.get("y_w30_truncated") and r.get("release_date")
               and dt.date.fromisoformat(r["release_date"]) + dt.timedelta(days=30) <= today
               and r["appid"] not in done]
    trunc_left = sum(1 for r in rows if r.get("y_w30_truncated") and r["appid"] not in done)
    print(f"절단 잔여 {trunc_left} · 오늘({today}) 만기 {len(matured)}", flush=True)
    if "--plan" in sys.argv or not matured:
        return
    added, dropped = {}, []
    for r in matured:
        v = w30_epoch(r["appid"], r["release_date"], True)
        if v is None:
            dropped.append(r["appid"])   # 침묵 탈락 금지(티처 #45·#46) — 값으로 남긴다
            continue
        added[r["appid"]] = {"y_w30_utc": v, "y_w30_stored_kst": r.get("y_w30"),
                             "rel_diff": None, "release_date": r["release_date"],
                             "provenance": f"만기 재계산 {today}(절단→성숙 · KST 저장값은 절단분)"}
    u["행"].update(added)
    u["만기 추가 이력"] = u.get("만기 추가 이력", []) + [{"일": str(today), "n": len(added)}]
    tmp = UF.with_suffix(".tmp")        # 원자적 쓰기(866 — 정본은 성장물·단일 필자)
    json.dump(u, open(tmp, "w"), ensure_ascii=False, indent=1)
    tmp.replace(UF)
    with open(ROOT / f"runners/out_matured_{today}.json", "x") as fh:
        json.dump({"일": str(today), "만기": len(matured), "추가": added,
                   "조회실패 탈락": dropped}, fh, ensure_ascii=False, indent=1)
    print(f"UTC 정본에 {len(added)}행 추가(만기 {len(matured)} · 탈락 {len(dropped)})", flush=True)


if __name__ == "__main__":
    main()
