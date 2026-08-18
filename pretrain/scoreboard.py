# -*- coding: utf-8 -*-
"""파운데이션 판 — 루프 v5.0 의 정본 채점기 (docs/루프.md 제5장).

한 방: python3 pretrain/scoreboard.py [--out 경로.json]

넷을 한 판에 적는다:
  ① 최약 도메인 MdAPE (리더보드 · 개체 분리 val) — 합산 MdAPE 는 착시 전과가 있어 «최악»을 적는다
  ② transition 이 persistence 에 지는 도메인 (인도메인 val)
  ③ LODO 제로샷 승수 — 안 본 도메인에서 persistence 를 이기는 수 (「임의 도메인 대처력」의 자)
  ④ 90% 구간 덮개율 (report.json)

원천 셋: transition/leaderboard.json (pretrain/council.py build 산출) ·
exp/lodo/results.json · transition/report.json — 조항 66 대로 각 원천의
sha256 · mtime 을 판에 함께 적는다(자가 자기 출처를 못 대면 자가 아니다).
LODO 는 비싼 실험(재학습 20회)이라 매 사이클 재지 않는다 — 전이 모형을 바꾼
사이클은 LODO 재실측 여부를 사전등록에 적는다(안 재면 ③ 옆에 「낡음」 표시가 남는다).
"""
import argparse
import hashlib
import json
import os
import time

ART = "/Users/ax/wm_harvest/foundation"
SRC = {
    "리더보드": os.path.join(ART, "transition", "leaderboard.json"),
    "LODO": os.path.join(ART, "exp", "lodo", "results.json"),
    "보고서": os.path.join(ART, "transition", "report.json"),
}


def _provenance(path):
    if not os.path.exists(path):
        return {"상태": "없음"}
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {"sha256": h.hexdigest()[:16],
            "mtime": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(os.path.getmtime(path)))}


def build():
    판 = {"판": "파운데이션 판 v1 (루프 v5.0 · docs/루프.md 제5장)",
          "잰 시각": time.strftime("%Y-%m-%dT%H:%M:%S"),
          "원천": {k: _provenance(p) for k, p in SRC.items()}}

    # ①② 리더보드 (없으면 조항 59 대로 「못 읽었다」)
    if os.path.exists(SRC["리더보드"]):
        lb = json.load(open(SRC["리더보드"], encoding="utf-8"))
        dom = lb["도메인별"]
        worst = max(dom.items(), key=lambda kv: kv[1]["transition"])
        지는 = sorted([d for d, r in dom.items() if r["transition"] > r["persistence"]],
                    key=lambda d: dom[d]["transition"] - dom[d]["persistence"], reverse=True)
        판["①최약 도메인"] = {"도메인": worst[0], "MdAPE": worst[1]["transition"],
                          "n_val": worst[1]["n_val"],
                          "도메인별": {d: r["transition"] for d, r in
                                    sorted(dom.items(), key=lambda kv: -kv[1]["transition"])}}
        판["②pers에 지는 도메인"] = {"수": "%d/%d" % (len(지는), len(dom)), "목록": 지는}
    else:
        판["①최약 도메인"] = 판["②pers에 지는 도메인"] = "못 읽었다 — 리더보드 없음 (pretrain/council.py build)"

    # ③ LODO 제로샷
    if os.path.exists(SRC["LODO"]):
        lo = json.load(open(SRC["LODO"], encoding="utf-8"))["도메인별"]
        이김 = sorted([d for d, r in lo.items() if r["B_zeroshot"] < r["persistence"]])
        짐 = sorted(set(lo) - set(이김))
        판["③LODO 제로샷"] = {"승수": "%d/%d" % (len(이김), len(lo)),
                           "이기는 곳": 이김, "지는 곳": 짐,
                           "주의": "전이 모형이 바뀌었으면 이 수는 낡은 것이다 — 재실측 여부를 사전등록에"}
    else:
        판["③LODO 제로샷"] = "못 읽었다 — exp/lodo/results.json 없음"

    # ④ 덮개율 (report.json 의 키는 세대에 따라 다르다 — 있는 것만 옮긴다)
    if os.path.exists(SRC["보고서"]):
        rep = json.load(open(SRC["보고서"], encoding="utf-8"))
        평가 = rep.get("평가", rep)   # 덮개율은 「평가」 아래에 산다 (세대에 따라 최상위일 수도)
        cov = {k: v for k, v in 평가.items() if "덮개" in k or "coverage" in k.lower()}
        판["④90% 덮개율"] = cov if cov else "못 읽었다 — report.json 에 덮개율 키 없음"
    else:
        판["④90% 덮개율"] = "못 읽었다 — report.json 없음"
    return 판


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="판 JSON 저장 경로 (사이클 산출물로 커밋할 것)")
    a = ap.parse_args()
    판 = build()
    s = json.dumps(판, ensure_ascii=False, indent=1)
    print(s)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(s + "\n")


if __name__ == "__main__":
    main()
