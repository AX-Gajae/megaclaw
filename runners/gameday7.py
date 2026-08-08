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
    "863": {"파일": "runners/out863_day0.json", "가드": ">=2026-08-15",
            "갈래": "정시출시율>=0.90 ∧ 폐지<=0.02 → 배선 신뢰(봉인 판정 아님) / 이동+폐지>0.15 → 노크 중단 / 사이 → 유보(864로)"},
    "864": {"파일": "runners/out864_day0b.json", "가드": "{2026-08-22, 2026-08-29}",
            "갈래": "**권위 = 8/29 누적 · 8/22 는 중간 관측**(사전등록 865 P1′). 8/29 누적 이동률(미출시 잔존 분모) <=0.05 → 봉인 규칙 사전등록 진행 / (0.05,0.15] → 9월 첫 주 1회 추가 관측 후 재판정 / >0.15 → 봉인 금지. 추가 조항: (폐지+조기출시)/전체 >=0.05 → 이동률 무관 판정 유보"},
    "865": {"파일": "runners/out865_day0c.json", "가드": "{2026-08-22, 2026-08-29}",
            "갈래": "후미 병기 전용(권위 없음) — 앞창(864)과의 이동률 |Δ|>5%p → 앞창 편향 실물(봉인 문서에 창 제한 의무)"},
}

mode = sys.argv[1] if len(sys.argv) > 1 else ""
plan = "--plan" in sys.argv
if mode not in CFG:
    sys.exit("사용: gameday7.py 863|864|865 [--plan]")
cfg = CFG[mode]
today = dt.date.today().isoformat()
cohort = json.load(open(ROOT / cfg["파일"]))["코호트"]
print(f"코호트 {len(cohort)} · 가드 {cfg['가드']} · 오늘 {today}\n갈래(동결): {cfg['갈래']}", flush=True)
if plan:
    sys.exit(0)
if mode == "863":
    if today < "2026-08-15":
        sys.exit("거부: 2026-08-15 이전 실행 금지(사전등록 864)")
elif today not in ("2026-08-22", "2026-08-29"):
    sys.exit("거부: 실행일은 {8/22, 8/29} 로 고정(사전등록 865 P1′)")

outp = ROOT / f"runners/out_day7_{mode}_{today}.json"
states = []
for i, c in enumerate(cohort):
    url = f"https://store.steampowered.com/api/appdetails?appids={c['appid']}&cc=kr&l=korean"
    d = _get(url)
    time.sleep(1.2)
    if d is None:                       # 조회실패 ≠ 상장폐지(865 P1′②) — 재시도 1회 더
        d = _get(url)
        time.sleep(1.2)
    node = (d or {}).get(str(c["appid"])) or {}
    if d is None:
        st, new_std = "조회실패", None
    elif not node.get("success"):
        st, new_std = "상장폐지", None
    else:
        rdi = (node.get("data") or {}).get("release_date") or {}
        g, new_std = granularity(rdi.get("date"))
        if not rdi.get("coming_soon"):
            # 조기출시 = 이동(865 P1′①) — 동결 표준일이 아직 미래인데 벌써 나왔다
            st = "선행(조기출시)" if (c.get("표준일") and c["표준일"] > today) else "출시"
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
조기 = sum(1 for s in states if s["상태"] == "선행(조기출시)")
폐지 = cnt.get("상장폐지", 0) / n
실패 = cnt.get("조회실패", 0)
이동 = cnt.get("후행", 0) + cnt.get("선행", 0)
미출시잔존 = n - cnt.get("출시", 0) - 조기 - cnt.get("상장폐지", 0) - 실패
verdict = []
if 실패:
    verdict.append(f"조회실패 {실패}건 — 분모에서 제외·판정에 불산입(폐지 아님 · 865 P1′②)")
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
    권위 = "판정(권위)" if today == "2026-08-29" else "중간 관측(권위 아님 — 판정은 8/29 누적)"
    if mode == "865":
        verdict.append(f"후미 병기 전용(권위 없음) — 이동률 {mv:.3f}(잔존 {미출시잔존}) · 앞창(864)과 |Δ|>5%p 면 앞창 편향 실물")
    elif (폐지 + 조기 / n) >= 0.05:
        verdict.append(f"판정 유보 — 폐지+조기출시 {폐지 + 조기 / n:.3f} ≥ 0.05(이동률 무관 · 865 P1′⑤) · 이동률 {mv:.3f} 병기 · {권위}")
    else:
        verdict.append(("봉인 규칙 사전등록 진행" if mv <= 0.05 else
                        "9월 첫 주 1회 추가 관측 후 재판정" if mv <= 0.15 else "봉인 금지")
                       + f" — 이동률 {mv:.3f}(분모 미출시 잔존 {미출시잔존}) · 전체 분모 기준 {이동 / n:.3f} 병기 · {권위}")

out = {"모드": mode, "판정일": today, "분포": cnt, "조기출시": 조기, "상태": states,
       "분모": {"전체": n, "미출시 잔존": 미출시잔존, "조회실패 제외": 실패}, "판정": verdict}
with open(outp, "x") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print(json.dumps({"분포": cnt, "판정": verdict, "동결": str(outp)}, ensure_ascii=False, indent=1), flush=True)
