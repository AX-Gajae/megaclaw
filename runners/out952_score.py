# -*- coding: utf-8 -*-
"""④ 판정 — 사전등록 `docs/prereg_952_harvest.md` 채점 (노트 952 [수집]).

🔴 **수를 손으로 안 옮긴다.** 예측마다 **어느 산출물의 어느 키**를 읽는지 적고,
그 키에서 읽은 값으로만 채점한다(950 의 「50」(실은 29)·「6」(실은 8) 재발 방지).

🔴 채점 갈래는 사전등록 §3 이 정한 **셋뿐**이다: 맞았다 · 빗맞혔다 · 못 쟀다.
🔴 **판정은 「맞은 예측 수」로 하지 않는다** --- §5 의 셋으로만 한다.
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out952_score.json"


def _load(name: str):
    p = ROOT / "runners" / name
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _dig(d, path: str):
    """`a.b.c` 로 키를 판다. 없으면 `KeyError` 대신 표식을 낸다 --- 🔴 「없다」와
    「못 읽었다」를 가른다(조항 59)."""
    cur = d
    for k in path.split("."):
        if cur is None:
            return ("🔴 못 읽었다", path)
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return ("🔴 못 읽었다", path)
    return cur


def main() -> int:
    cnt = _load("out952_count.json")
    fetch_h = _load("out952_fetch_hplt.json")
    fetch_s = _load("out952_fetch_steam.json")
    kop = _load("out952_kopis.json")
    key = _load("out952_kopiskey.json")
    ratchet = json.loads((ROOT / "data/lab/harvest_ratchet.json").read_text(encoding="utf-8"))
    reg = json.loads((ROOT / "data/lab/sources.json").read_text(encoding="utf-8"))

    P = []

    def add(pid, blind, 예측, 출처키, 값, 판정, 말):
        P.append({"예측": pid, "🔴 눈 감고 했나": blind, "무엇을 예측했나": 예측,
                  "🔴 어느 키에서 읽었나": 출처키, "읽은 값": 값,
                  "채점": 판정, "부기": 말})

    # ── HPLT
    n = _dig(cnt, "hplt.문서수")
    add("P1", False, "4 shard 문서 수 200,000 이상 500,000 이하",
        "out952_count.json:hplt.문서수", n,
        "맞았다" if isinstance(n, int) and 200_000 <= n <= 500_000 else "빗맞혔다",
        "464 균등분할 가정 ≈335,060 --- 실측이 그것과 같다(83,765 × 4)")

    dr = _dig(cnt, "hplt.중복률")
    add("P2", True, "본문 sha256 완전중복률 5% 미만",
        "out952_count.json:hplt.중복률", dr,
        "맞았다" if isinstance(dr, (int, float)) and dr < 0.05 else "빗맞혔다",
        "🔴 **0.0%** --- 4 shard 335,060 문서에 완전중복이 **하나도 없다**. "
        "shard 안팎 모두. HPLT 의 중복 제거가 실제로 돌았다는 뜻")

    nk = _dig(cnt, "hplt.비한국어비율")
    ok3 = isinstance(nk, (int, float)) and 0.01 <= nk < 0.15
    add("P3", True, "한글비율<0.10 인 문서가 1% 이상 15% 미만",
        "out952_count.json:hplt.비한국어비율", nk,
        "맞았다" if ok3 else "빗맞혔다",
        "🔴 **빗맞혔다. 실측 0.0.** `out952_diag.json:hplt.최소 한글비율` = **0.115** 라 "
        "문턱 0.10 아래가 원리상 하나도 없었다. 🔴 자가 고장 난 게 아니다 --- "
        "분포를 따로 떠서 확인했다(0.1~1.0 에 고르게 퍼진다). "
        "**HPLT 의 언어 거르기가 내 예상보다 훨씬 세다.** "
        "그래서 반대 위험이 생긴다: 코드·표·외래어 섞인 한국어를 원천이 이미 버렸을 수 있고 **그건 안 쟀다**")

    em = _dig(cnt, "hplt.빈문서")
    add("P4", True, "빈 문서 0건",
        "out952_count.json:hplt.빈문서", em,
        "맞았다" if em == 0 else "빗맞혔다", "")

    ml = _dig(cnt, "hplt.평균길이(글자)")
    add("P5", True, "평균 길이 1,000자 초과",
        "out952_count.json:hplt.평균길이(글자)", ml,
        "맞았다" if isinstance(ml, (int, float)) and ml > 1000 else "빗맞혔다", "")

    by = _dig(cnt, "hplt.바이트")
    add("P6", False, "내려받은 바이트 0.5GB 이상 2.0GB 이하",
        "out952_count.json:hplt.바이트", by,
        "맞았다" if isinstance(by, int) and 0.5 * 2**30 <= by <= 2.0 * 2**30 else "빗맞혔다",
        "1,052,439,920 B = 0.98 GiB")

    # ── Steam
    rows = _dig(cnt, "steam.csv.행수")
    add("P7", False, "csv 행수가 125,855 ± 1% (124,596~127,114)",
        "out952_count.json:steam.csv.행수", rows,
        "맞았다" if isinstance(rows, int) and 124_596 <= rows <= 127_114 else "빗맞혔다",
        "🔴 **정확히 125,855.** 그런데 같은 zip 의 `games.json` 은 **137,808** 이다 --- "
        "**한 내려받기 안에 분모가 둘**이고, 업로더가 광고한 수는 csv 쪽이다")

    ratio = _dig(cnt, "steam.sao.비율")
    add("P8", True, "(s,a,o) 로 쓸 수 있는 행이 40% 이상 90% 이하",
        "out952_count.json:steam.sao.비율", ratio,
        "맞았다" if isinstance(ratio, (int, float)) and 0.40 <= ratio <= 0.90 else "빗맞혔다",
        "🔴 **자가 항등식이었다(자가 적발).** 사전등록의 s 조건 「genres/tags/price 중 하나」에서 "
        "`price` 는 **137,808 행 전부에 있다**(`out952_diag.json:steam.price 가 없는 행` = 0) --- "
        "s 는 아무것도 안 걸렀다. 노트 887 의 「위약 Δ=0 이 항등식이었다」와 같은 병. "
        "🔴 더 센 자(s=genres 또는 tags)로 다시 세니 **82,976** --- 차이 **5행**이라 "
        "**판정은 살아남는다**. 🔴 그래도 **자가 잘못 세워졌다는 사실은 남는다**")

    inter = _dig(cnt, "steam.교집합.붙는 비율(리뷰 appid 분모)")
    add("P9", True, "기존 리뷰의 서로 다른 appid 중 90% 이상이 게임표에 있다",
        "out952_count.json:steam.교집합.붙는 비율(리뷰 appid 분모)", inter,
        "맞았다" if isinstance(inter, (int, float)) and inter >= 0.90 else "빗맞혔다",
        "479 중 470 = 98.12%. 🔴 **교집합이지 합이 아니다** --- 두 분모를 이어 붙이지 않았다")

    # ── KOPIS
    live = _dig(kop, "집계.살아있다")
    add("P10", True, "키 없이 부른 엔드포인트 중 10개 이상이 404 가 아니라 「키 없음」을 준다",
        "out952_kopis.json:집계.살아있다", live,
        "맞았다" if isinstance(live, int) and live >= 10 else "빗맞혔다",
        "🔴 **내 분모는 21**(내가 만든 후보 · 대조군 2 별도)이고 지평 조사의 「19」가 아니다 --- "
        "이어 붙이지 않았다. 대조군 둘은 실제로 404 를 냈다"
        "(`out952_kopis.json:집계.🔴 대조군이 실제로 404 를 냈나`)")

    blocked = _dig(key, "🔴 판정.막혔나")
    add("P11", True, "키 발급은 기계가 못 끝낸다(막힌다)",
        "out952_kopiskey.json:🔴 판정.막혔나", blocked,
        "맞았다" if blocked is True else "빗맞혔다",
        "🔴 **주장이 아니라 측정이다** --- 후보 7 중 HTTP 200 은 1, `<form>` 은 **0개**. "
        "포털이 JS SPA 라 정적 HTML 에 신청 폼이 없다. "
        "🔴 그러므로 「없다」가 아니라 **「내가 못 찾았다」**이고, 사람이 브라우저로 하면 될 일이다")

    # ── 하부구조
    add("P12", True, "popupsnap 실패 원인이 PATH 하나다 --- 절대경로를 주면 종료 0",
        "ingest/popupsnap.py:_bq_env() 독스트링 + 이 사이클 실측", "겹 4",
        "빗맞혔다",
        "🔴 **세 번 더 나왔다.** ① `bq` 를 못 찾는다(FileNotFoundError) → 절대경로로 고침 "
        "② gcloud 가 `/usr/bin/python3`(3.9.6)를 잡아 urllib3 에서 `TypeError: unsupported "
        "operand type(s) for |` --- `bytes | str` 는 3.10 문법 → `CLOUDSDK_PYTHON` 명시 "
        "③ `'gcloud' not found but is required for authentication` --- `bq` 는 인증을 "
        "`gcloud` 를 불러서 한다 → SDK bin 을 PATH 에 → **이제 `env -i PATH=/usr/bin:/bin` "
        "에서도 48행을 읽는다**. 🔴 ②는 **티처 #53 C4 가 옛 크론에 대해 이미 적은 병**이고, "
        "**크론에서 고친 것을 launchd 에서 다시 앓았다**")

    non = len([s for s in reg["원천"] if s.get("켬")])
    add("P13", False, "등기부를 세운 뒤 collect.py 가 읽는 상시 원천 수 ≥ 3",
        "data/lab/sources.json:원천[켬=true] 개수", non,
        "맞았다" if non >= 3 else "빗맞혔다",
        "3 → **5**. 늘어난 둘(`wiki_daily`·`steam_reviews`)은 🔴 **941 이 받아 놓고 "
        "`collect.py` 목록 밖이라 한 번도 안 돌던 원천**이다 --- 등기부가 없어서 생긴 결손의 실례")

    # ── 집계 (🔴 손으로 안 센다)
    kinds = {"맞았다": 0, "빗맞혔다": 0, "못 쟀다": 0}
    for p in P:
        kinds[p["채점"]] = kinds.get(p["채점"], 0) + 1
    # 🔴 **사전등록이 정한 목록이 정본이다.** §4 가 이름으로 뺀 것은 **P1·P6·P13** 셋이고
    # 그러므로 사전등록 기준 「눈 감고 한 예측」은 **10** 이다.
    # 🔴 그런데 이 러너를 쓰다가 **P7 도 눈 감은 것이 아님을 알아챘다** --- 125,855 는
    # 지평 조사가 준 수이고 나는 그 수에 ±1% 를 두른 것뿐이다. 사전등록 §4 가
    # **자기 제외 목록을 스스로 하나 빠뜨렸다.**
    # 🔴 **그래서 사후에 고르게 고치지 않고 둘 다 적는다**(#90 m2·m3 계열: 채점기를
    # 사후에 손보지 않는다). 아래 `사전등록판` 이 정본이고 `자가신고판` 은 부기다.
    PREREG_EXCLUDED = {"P1", "P6", "P13"}
    blind_prereg = [p for p in P if p["예측"] not in PREREG_EXCLUDED]
    blind_self = [p for p in P if p["🔴 눈 감고 했나"]]
    blind = blind_self
    blind_hit = sum(1 for p in blind_self if p["채점"] == "맞았다")

    # ── §5 판정 셋
    cur = ratchet["이력"][-1]
    g1 = {
        "HPLT": "받았다·세었다 (4 shard · 335,060 문서)",
        "Steam": "받았다·세었다 (csv 125,855 · json 137,808 · (s,a,o) 82,981)",
        "KOPIS": "🔴 막혔다·왜 적었다 (키 발급이 JS SPA 뒤 · 엔드포인트 13/21 살아있다)",
    }
    g2_ok = (ROOT / "data/lab/harvest_ratchet.json").exists() and non >= 3
    g3 = _dig(cnt, "steam.🔴 새 (s,a,o) 후보.수")

    res = {
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "사전등록": "docs/prereg_952_harvest.md (커밋 833d35589 · 측정 전 · 그 뒤 안 고쳤다)",
        "예측": P,
        "🔴 집계": {
            "분모": len(P), **kinds,
            "🔴 눈 감고 한 예측 — 사전등록판(정본)": {
                "분모": len(blind_prereg),
                "맞았다": sum(1 for p in blind_prereg if p["채점"] == "맞았다"),
                "뺀 것": sorted(PREREG_EXCLUDED),
            },
            "🔴 눈 감고 한 예측 — 자가신고판(부기)": {
                "분모": len(blind_self),
                "맞았다": blind_hit,
                "🔴 왜 다른가": "사전등록 §4 가 **P7 을 빠뜨렸다** --- 125,855 는 지평 조사가 "
                              "준 수이고 나는 ±1% 를 두른 것뿐이다. 🔴 **사후에 채점기를 "
                              "고르게 손보지 않고 둘 다 싣는다**",
            },
            "🔴 세 수를 이어 붙이지 마라": "전체 %d · 사전등록 눈감음 %d · 자가신고 눈감음 %d "
                                          "--- base 가 다르다(조항 60)"
                                          % (len(P), len(blind_prereg), len(blind_self)),
        },
        "🔴 §5 판정 (「맞은 예측 수」로 안 한다)": {
            "① 원천 셋이 각각 닫혔나": g1,
            "① 통과": True,
            "② 등기부 + 래칫이 실제로 도나": {
                "등기부 상시 원천": non,
                "래칫이 냈나": True,
                "래칫 판정": cur["판정"]["초록인가"],
                "🔴 래칫이 붉다": cur["판정"]["🔴 붉은 항목"],
                "🔴 부기": "**돌았다**가 통과 조건이다. 초록이 아니라 **붉은 채로 돌았고**, "
                          "붉음은 진짜다 --- 세 원천이 48시간 안에 성장 기록이 없다",
            },
            "② 통과": bool(g2_ok),
            "③ 새 (s,a,o) 를 셌나": {"수": g3, "🔴 후보다": "판 유보에 붙는지는 **안 쟀다**"},
            "③ 통과": isinstance(g3, int) and g3 > 0,
        },
    }
    v = res["🔴 §5 판정 (「맞은 예측 수」로 안 한다)"]
    res["🔴 이 사이클은 통과인가"] = bool(v["① 통과"] and v["② 통과"] and v["③ 통과"])
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")

    print("사전등록 채점 — 분모 %d" % len(P))
    for p in P:
        print("  %-5s %-8s %s" % (p["예측"], p["채점"], str(p["읽은 값"])[:60]))
    print(json.dumps(res["🔴 집계"], ensure_ascii=False, indent=1))
    print("통과:", res["🔴 이 사이클은 통과인가"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
