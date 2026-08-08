# -*- coding: utf-8 -*-
# day7 판정 러너 — 사전등록 864 P1(863 코호트) · P2(864 day0b 코호트) 동결 갈래 전용
# 사용: python3 runners/gameday7.py 863   (2026-08-15 이후에만)
#       python3 runners/gameday7.py 864   (2026-08-22 · 2026-08-29 — 각 1회)
#       python3 runners/gameday7.py 863 --plan   (네트워크 없이 코호트·갈래 확인)
# 방법(재등록 동결): appid 기반 appdetails **무캐시** 전수. 검색 재수집 아님('소멸' 제거).
import datetime as dt
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from ingest.game_sample import _get  # noqa: E402 — 무캐시 HTTP
from lab.gamedate import granularity  # noqa: E402 — 동결 사본(864 러너는 import 시 측정이 실행돼 금지)

ROOT = Path("/Users/ax/world_model")
CFG = {
    "863": {"파일": "runners/out863_day0.json", "가드": "2026-08-15",
            "갈래": "정시출시율>=0.90 ∧ 폐지<=0.02 → 배선 신뢰(봉인 판정 아님) / 이동+폐지>0.15 → 노크 중단 / 사이 → 유보(864로)"},
    "864": {"파일": "runners/out864_day0b.json", "가드": "2026-08-22",
            "갈래": "이동률(미출시 잔존 분모) <=0.05 → 봉인 규칙 사전등록 진행 / (0.05,0.15] → 밴드 누적 후 / >0.15 → 봉인 금지"},
}

mode = sys.argv[1] if len(sys.argv) > 1 else ""
plan = "--plan" in sys.argv
if mode not in CFG:
    sys.exit("사용: gameday7.py 863|864 [--plan]")
cfg = CFG[mode]
today = dt.date.today().isoformat()
cohort = json.load(open(ROOT / cfg["파일"]))["코호트"]
print(f"코호트 {len(cohort)} · 가드 {cfg['가드']} · 오늘 {today}\n갈래(동결): {cfg['갈래']}", flush=True)
if plan:
    sys.exit(0)
if today < cfg["가드"]:
    sys.exit(f"거부: {cfg['가드']} 이전 실행 금지(사전등록 864)")

outp = ROOT / f"runners/out_day7_{mode}_{today}.json"
states = []
for i, c in enumerate(cohort):
    d = _get(f"https://store.steampowered.com/api/appdetails?appids={c['appid']}&cc=kr&l=korean")
    time.sleep(1.2)
    try:
        node = d[str(c["appid"])]
    except Exception:
        node = {}
    if not node.get("success"):
        st, new_std = "상장폐지", None
    else:
        rdi = (node.get("data") or {}).get("release_date") or {}
        g, new_std = granularity(rdi.get("date"))
        if not rdi.get("coming_soon"):
            st = "출시"
        elif new_std is None or g != "일":
            st = "후행(입도 상실)" if c["입도"] == "일" else "동일(막연)"
        elif new_std > c["표준일"]:
            st = "후행"
        elif new_std < c["표준일"]:
            st = "선행"
        else:
            st = "후행(경과 미출시)" if c["표준일"] < today else "동일"
    states.append({"appid": c["appid"], "제목": c["제목"], "동결 표준일": c.get("표준일"),
                   "현재": new_std, "상태": st})
    if (i + 1) % 25 == 0:
        print(f"  {i + 1}/{len(cohort)}", flush=True)

n = len(states)
cnt = {}
for s in states:
    k = s["상태"].split("(")[0]
    cnt[k] = cnt.get(k, 0) + 1
폐지 = cnt.get("상장폐지", 0) / n
이동 = (cnt.get("후행", 0) + cnt.get("선행", 0))
미출시잔존 = n - cnt.get("출시", 0) - cnt.get("상장폐지", 0)
verdict = []
if mode == "863":
    정시 = cnt.get("출시", 0) / n
    if 정시 >= 0.90 and 폐지 <= 0.02:
        verdict.append(f"배선 신뢰 — 정시 {정시:.3f} · 폐지 {폐지:.3f}(봉인 판정 아님 — 권한은 864 코호트)")
    elif (이동 / n + 폐지) > 0.15:
        verdict.append(f"노크 중단 — 4일 지평에서 이동+폐지 {이동 / n + 폐지:.3f} > 0.15")
    else:
        verdict.append(f"유보 — 정시 {정시:.3f} · 폐지 {폐지:.3f} · 이동 {이동 / n:.3f} (864로 이관)")
else:
    mv = 이동 / max(미출시잔존, 1)
    verdict.append(("봉인 규칙 사전등록 진행" if mv <= 0.05 else
                    "밴드 누적 후" if mv <= 0.15 else "봉인 금지")
                   + f" — 이동률 {mv:.3f}(분모 미출시 잔존 {미출시잔존}) · 전체 분모 {이동 / n:.3f} 병기")

out = {"모드": mode, "판정일": today, "분포": cnt, "상태": states,
       "분모 두 벌": {"전체": n, "미출시 잔존": 미출시잔존}, "판정": verdict}
with open(outp, "x") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(json.dumps({"분포": cnt, "판정": verdict, "동결": str(outp)}, ensure_ascii=False, indent=1), flush=True)
