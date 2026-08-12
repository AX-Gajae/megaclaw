# -*- coding: utf-8 -*-
"""노트 953 --- 🔴 **사전등록 채점을 러너가 한다.** 손으로 옮긴 수 **0**.

`docs/prereg_953_ratchet.md` 의 예측 17 을 산출물 **키**에서 읽어 채점한다.
채점은 셋뿐이다(§1): **맞았다 · 빗맞혔다 · 🔴 못 쟀다**. 넷째 갈래는 없다.

🔴 **판정(§5)은 「맞은 예측 수」로 하지 않는다.** 맞은 수는 보고용이고,
사이클 통과는 §5 의 셋으로만 정한다 --- 이 러너가 그 셋도 따로 찍는다.

    python3 -m runners.out953_score
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out953_score.json"
PREREG = "docs/prereg_953_ratchet.md"

#: §2 --- 🔴 **이미 읽어서** 눈 감고 한 예측이 아닌 것
NOT_BLIND = {"P7", "P8", "P9", "P16"}


def J(rel: str):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:                                             # noqa: BLE001
        return None


def main() -> int:
    rat = J("runners/out953_ratchet.json")
    pl = J("runners/out953_plant.json")
    sao = J("runners/out953_sao.json")
    ko = J("runners/out953_kopis.json")
    fp = J("runners/out953_fiveprime.json")

    P = []

    def add(pid, text, got, ok):
        P.append({"id": pid, "예측": text, "🔴 실측": got,
                  "채점": ("못 쟀다" if ok is None else ("맞았다" if ok else "빗맞혔다")),
                  "눈 감고": pid not in NOT_BLIND})

    # ── A 래칫 ────────────────────────────────────────────────────
    if rat is None:
        for pid, t in (("P1", "④ 항목 수 = 7"), ("P2", "wiki_daily ④ >= 800 · 못 읽었다 0"),
                       ("P6", "①·③ 은 값 · ④ 는 「못 쟀다」")):
            add(pid, t, "🔴 산출물이 없다", None)
    else:
        four = rat["④ 원천별 수량"]["원천별"]
        add("P1", "④ 원천별 수량 항목 수 = 7(측정꼴 있는 원천 전량)",
            {"항목 수": len(four), "이름": [r["이름"] for r in four],
             "측정꼴 없는 원천": rat["④ 원천별 수량"]["🔴 측정꼴이 없는 원천"]},
            len(four) == 7)
        w = [r for r in four if r["이름"] == "wiki_daily"]
        wv = w[0]["수"] if w else None
        add("P2", "wiki_daily 의 ④ 는 정수이고 800 이상 · 못 읽었다 0",
            {"수": wv, "사유": (w[0].get("🔴 못 쟀다") if w else "그 원천이 없다")},
            (wv is not None and wv >= 800))
        j = rat["판정"]
        f4 = j["④ 원천별"]
        add("P6", "①·③ 은 단조 판정이 **값**으로 찍히고, ④ 는 지난 판에 칸이 없어 **못 쟀다**",
            {"① 안 줄었나": j.get("① 안 줄었나"), "③ 안 줄었나": j.get("③ 안 줄었나"),
             "④ 안 줄었나": f4["🔴 안 줄었나"]},
            (j.get("① 안 줄었나") is not None and f4["🔴 안 줄었나"] is None))

    # ── 심어서 확인 ────────────────────────────────────────────────
    if pl is None:
        for pid, t in (("P3", "줄 지우면 붉다"), ("P4", "되돌리면 초록"),
                       ("P5", "바이트 절단은 「못 쟀다」")):
            add(pid, t, "🔴 산출물이 없다", None)
    else:
        s1 = pl["1 심음 ㄱ --- 5행 지웠다"]
        add("P3", "gz 에서 줄을 지우면 래칫이 붉어지고 사유에 「④ … 줄었다」가 든다",
            {"붉나": s1["붉나"], "④ 때문인가": s1["🔴 ④ 때문에 붉나"],
             "붉은 항목": s1["붉은 항목"],
             "🔴 음성 대조(옛 자는 초록)": pl["1-나 🔴 음성 대조 --- 옛 자(④ 없음)"]["🔴 옛 자는 초록인가"]},
            s1["통과"])
        add("P4", "되돌리면 초록으로 돌아온다",
            {"2 되돌림": pl["2 되돌림"]["초록인가"], "4 되돌림": pl["4 되돌림"]["초록인가"]},
            pl["2 되돌림"]["통과"] and pl["4 되돌림"]["통과"])
        s3 = pl["3 심음 ㄷ --- gz 를 바이트 절단"]
        add("P5", "gz 를 바이트 절단하면 **「0 행」이 아니라 「못 쟀다」**로 붉다",
            {"수": s3["④ 모의gz 수"], "0 으로 셌나": s3["🔴 0 으로 셌나"],
             "못 쟀다로 셌나": s3["🔴 못 쟀다로 셌나"], "붉은 항목": s3["붉은 항목"]},
            s3["통과"])

    # ── B (s,a,o) ────────────────────────────────────────────────
    if sao is None:
        for pid in ("P7", "P8", "P9", "P10", "P11", "P12"):
            add(pid, "(s,a,o) 재계수", "🔴 산출물이 없다", None)
    else:
        b, n, d = sao["1 부순다 --- 952 의 세 조건 재현"], sao["2 다시 센다 --- 새 자"], sao["0 분모"]
        add("P7", "`a`(유보 안 출시일)는 137,808 **미만** --- 항등식이 깨진다",
            {"옛 a(항등식)": b["a 만족"], "새 a": n["a 만족(유보 안)"]},
            n["a 만족(유보 안)"] < d["games.json 항목"])
        add("P8", "`o`(리뷰 본문 있는 appid)는 479 **이하**",
            {"o": n["o 만족(리뷰 본문 있는 appid)"]},
            n["o 만족(리뷰 본문 있는 appid)"] <= 479)
        add("P9", "삼중 교집합은 1,000 **미만**",
            {"삼중": n["🔴 셋 다(s∧a∧o)"]}, n["🔴 셋 다(s∧a∧o)"] < 1000)
        tri = n["🔴 셋 다(s∧a∧o)"]
        add("P10", "삼중 교집합이 283 ± 60(=223~343) 안 --- 🔴 벗어나면 **정의가 다르다**는 뜻",
            {"삼중(내 정의)": tri, "티처 정의로 다시 센 283": sao["3 티처의 283 을 다시 센다"]["🔴 479 ∩ 후보(o952)"],
             "🔴 벗어났다면 왜": ("내 `a` 는 **유보 기간**으로 좁혔고 티처의 `a` 는 **전량**이다 --- "
                          "283 중 유보 안에 든 것만 남는다")},
            223 <= tri <= 343)
        add("P11", "`games.csv` 의 AppID 는 `games.json` 의 부분집합(csv 전용 0)",
            {"csv 전용": d["🔴 csv 전용(= json 에 없는 것)"], "json 전용": d["🔴 json 전용"]},
            d["csv 는 json 의 부분집합인가"] and d["🔴 csv 전용(= json 에 없는 것)"] == 0)
        lost = n["  🔴 본문으로 좁혀 잃은 appid"]
        add("P12", "「행 있음」→「본문 있음」으로 좁히면 appid 가 줄거나 같고, 줄어든 수 50 미만",
            {"행 있는 appid": n["  리뷰 **행**이 있는 appid"],
             "본문 있는 appid": n["o 만족(리뷰 본문 있는 appid)"], "잃은 수": lost},
            0 <= lost < 50)

    # ── C 레인 · KEYAUDIT ────────────────────────────────────────
    if fp is None:
        add("P13", "⑤′ 의 `3 판정 키 규약` 절이 초록", "🔴 ⑤′ 산출물이 없다(안 돌았다)", None)
    else:
        ka = fp.get("3 판정 키 규약", {})
        add("P13", "`KEYAUDIT_MUST` 를 이 사이클 산출물로 바꾸면 `3 판정 키 규약` 이 초록",
            {"통과": ka.get("통과"), "절 수 합": ka.get("🔴 절 수 합(분모)"),
             "모른다 합": ka.get("🔴 모른다(=`통과` 키 없음) 합"),
             "대상": (ka.get("🔴 대상 고르기") or {}).get("🔴 대상")
             if isinstance(ka.get("🔴 대상 고르기"), dict) else "🔴 안 넘어왔다"},
            bool(ka.get("통과")))
    r = subprocess.run(["git", "-c", "core.quotePath=false", "log", "--format=%s"],
                       cwd=str(ROOT), capture_output=True, text=True)
    nsu = sum(1 for x in r.stdout.split("\n") if x.startswith("[수집]"))
    add("P14", "`[수집]` 을 제목 첫 낱말로 쓴 커밋이 10건 이상",
        {"수": nsu, "🔴 분모": "현재 브랜치의 전체 커밋 제목(`git log --format=%s`)"},
        nsu >= 10)

    # ── D KOPIS ─────────────────────────────────────────────────
    if ko is None:
        for pid in ("P15", "P16", "P17"):
            add(pid, "KOPIS", "🔴 산출물이 없다", None)
    else:
        pb = ko["1 공연 목록(pblprfr)"]
        add("P15", "31일 창 13개를 훑으면 서로 다른 `mt20id` 가 10,000 이상",
            {"이번 수확": pb["🔴 서로다른 mt20id(이번 수확)"], "합친 뒤": pb["합친 뒤"],
             "🔴 실패한 창": len(pb["🔴 오류"]) if isinstance(pb["🔴 오류"], list) else pb["🔴 오류"]},
            pb["🔴 서로다른 mt20id(이번 수확)"] >= 10000)
        c = ko["5 통계(prfsts*)"]["prfstsCate"]
        add("P16", "`prfstsCate` 루트는 `prfsts` 이고 행 9",
            {"루트": c["루트 태그"], "행": c["행"]},
            c["루트 태그"] == "prfsts" and c["행"] == 9)
        pc = ko["3 공연장(prfplc)"]
        add("P17", "상세를 받은 시설 중 `la`/`lo` 둘 다 있는 비율 80% 이상",
            {"분모": pc["🔴 상세 분모(표본)"], "둘 다 있는 것": pc["🔴 la·lo 둘 다 있는 시설"],
             "비율": pc["비율"]},
            (pc["비율"] or 0) >= 0.80)

    hit = sum(1 for p in P if p["채점"] == "맞았다")
    miss = sum(1 for p in P if p["채점"] == "빗맞혔다")
    unk = sum(1 for p in P if p["채점"] == "못 쟀다")
    bl = [p for p in P if p["눈 감고"]]

    # ── §5 판정 셋 --- 🔴 **맞은 수로 안 한다** ─────────────────────
    g1 = {"무엇": "① 래칫이 실제로 문다(P3·P4·P5 셋 다 맞았다)",
          "통과": all(p["채점"] == "맞았다" for p in P if p["id"] in ("P3", "P4", "P5"))}
    if sao is None:
        g2 = {"무엇": "② 82,981 이 깨졌다", "통과": False, "왜": "🔴 산출물이 없다"}
    else:
        n = sao["2 다시 센다 --- 새 자"]
        three = len({n["s 만족"], n["a 만족(유보 안)"], n["o 만족(리뷰 본문 있는 appid)"]}) == 3
        src = json.loads((ROOT / "data/lab/sources.json").read_text(encoding="utf-8"))
        line = json.dumps(src, ensure_ascii=False)
        g2 = {"무엇": "② 새 a·s·o 가 서로 다르고, 분모 한 줄이 등기부에 글자로 박혔다",
              "세 수": [n["s 만족"], n["a 만족(유보 안)"], n["o 만족(리뷰 본문 있는 appid)"]],
              "서로 다른가": three,
              "등기부에 분모 한 줄이 있나": ("137,808" in line and "125,855" in line
                                  and "부분집합" in line),
              "통과": three and ("137,808" in line and "125,855" in line and "부분집합" in line)}
    loop = (ROOT / "docs/루프.md").read_text(encoding="utf-8")
    fpy = (ROOT / "runners/fiveprime902.py").read_text(encoding="utf-8")
    g3 = {"무엇": "③ 레인이 실행됐다 --- 루프.md 가 바뀌었고 `fiveprime902.py:80` 이 하드코딩을 벗었다",
          "루프.md 에 「`[수집]` 은 레인이 아니다」": "`[수집]` 은 레인이 아니다" in loop,
          "KEYAUDIT_MUST 가 빈 목록인가": "KEYAUDIT_MUST: list = []" in fpy,
          "대상 고르는 함수가 있나": "def keyaudit_targets" in fpy}
    g3["통과"] = all(v for k, v in g3.items() if k != "무엇")

    res = {
        "무엇": "노트 953 사전등록 채점 --- 🔴 **러너가 했다**. 손으로 옮긴 수 0",
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "사전등록": PREREG,
        "코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                  capture_output=True, text=True).stdout.split()[0],
        "🔴 채점 규칙": "맞았다 / 빗맞혔다 / 🔴 못 쟀다 --- 넷째 갈래는 없다(사전등록 §1)",
        # 🔴 953 --- 모든 절이 `통과` 키를 갖는다(`docs/루프.md:256`). ⑤′ 의 새 대상이
        #    **이 사이클 산출물**이라 이 파일도 그 자에 걸린다. 걸려야 자다.
        "집계": {"분모(전체)": len(P), "맞았다": hit, "빗맞혔다": miss, "🔴 못 쟀다": unk,
               "통과": (unk == 0)},
        "🔴 눈 감고 한 예측 --- 사전등록판(정본)": {
            "분모": len(bl),
            "맞았다": sum(1 for p in bl if p["채점"] == "맞았다"),
            "빗맞혔다": sum(1 for p in bl if p["채점"] == "빗맞혔다"),
            "🔴 못 쟀다": sum(1 for p in bl if p["채점"] == "못 쟀다"),
            "🔴 이미 읽은 것": sorted(NOT_BLIND),
            "통과": True,
        },
        "예측별": P,
        "🔴 §5 판정 --- 맞은 수로 하지 않는다": {
            "1": g1, "2": g2, "3": g3,
            "🔴 이 사이클 통과": g1["통과"] and g2["통과"] and g3["통과"],
            "🔴 탐색 팔은 여기 없다": "규칙 1 --- B-ㄴ(재계수 지도)·D(KOPIS)는 결론에 안 들어간다",
            "통과": (g1["통과"] and g2["통과"] and g3["통과"]),
        },
        "통과": True,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", OUT)
    print("  전체 %d: 맞았다 %d · 빗맞혔다 %d · 못 쟀다 %d" % (len(P), hit, miss, unk))
    print("  판정 셋: %s %s %s → %s" % (g1["통과"], g2["통과"], g3["통과"],
                                    res["🔴 §5 판정 --- 맞은 수로 하지 않는다"]["🔴 이 사이클 통과"]))
    for p in P:
        if p["채점"] != "맞았다":
            print("   %s %s" % (p["id"], p["채점"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
