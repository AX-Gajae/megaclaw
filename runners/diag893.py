# -*- coding: utf-8 -*-
"""노트 893 사후 진단 --- **요청을 하나도 더 안 보낸다**(캐시만 읽는다).

사전등록 밖의 계산이므로 **전부 '사후 탐색' 으로 표시**한다(892 가 P8 에서 배운 것).
답해야 할 것 넷:
  ① 음성 통제의 **시각 분포**가 실물과 같은가 --- 같으면 G1 은 작품의 성질이 아니라
     검색엔진+창의 성질이다.
  ② 단계 실패가 **창에 대칭이 아니다**(블로그 사전 6 대 사후 79). 짝이 둘 다 성공한
     작품으로 제한하면 후견지명이 얼마인가.
  ③ 질의어가 **한글이냐 로마자냐**가 수확을 얼마나 가르나.
  ④ 수확 항목이 실제로 그 작품 이야기인가 --- 제목에 질의 어절이 들어 있나(정밀도 대용).
"""
from __future__ import annotations

import json
import statistics
from collections import Counter
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
CACHE = ROOT / "data/state/cache_p893"


def med(xs):
    return round(statistics.median(xs), 2) if xs else None


def main():
    smp = json.loads((ROOT / "data/state/pilot893_sample.json").read_text(encoding="utf-8"))
    recs = {}
    for it in smp["표본"] + smp["음성 통제"]:
        p = CACHE / f"{it['record_id']}.json"
        recs[it["record_id"]] = json.loads(p.read_text(encoding="utf-8"))
    real = {k: v for k, v in recs.items() if not k.startswith("FAKE")}
    fake = {k: v for k, v in recs.items() if k.startswith("FAKE")}

    # ① 음성 통제의 시각 분포
    def pool(d, srcs=None):
        rows = []
        for v in d.values():
            for x in v["항목"]:
                if srcs is None or x["원천"] in srcs:
                    rows.append((x, v["t_0"]))
        return rows

    def _clsrows(rows):
        pre = post = bad = 0
        for x, t0 in rows:
            if not x.get("시각"):
                bad += 1
            elif x["시각"] < t0:
                pre += 1
            else:
                post += 1
        n = pre + post
        return {"사전": pre, "사후": post, "날짜불명": bad, "판정가능": n,
                "후견지명": round(pre / n, 4) if n else None}

    g1 = {
        "실물 전체": _clsrows(pool(real)),
        "음성 전체": _clsrows(pool(fake)),
        "실물 창 준(뉴스·블로그)": _clsrows(pool(real, {"뉴스", "블로그"})),
        "음성 창 준(뉴스·블로그)": _clsrows(pool(fake, {"뉴스", "블로그"})),
        "실물 디시": _clsrows(pool(real, {"디시"})),
        "음성 디시": _clsrows(pool(fake, {"디시"})),
    }

    # ② 창 짝이 **둘 다 성공한** 작품으로 제한
    def paired(d, src, a, b):
        rows = []
        n_ok = 0
        for v in d.values():
            st = v.get("단계별", {})
            if st.get(a) == "판정 불가" or st.get(b) == "판정 불가":
                continue
            n_ok += 1
            for x in v["항목"]:
                if x["원천"] == src:
                    rows.append((x, v["t_0"]))
        return n_ok, _clsrows(rows)

    pair = {}
    for lab, (src, a, b) in {"블로그": ("블로그", "블로그사전", "블로그사후"),
                             "뉴스": ("뉴스", "뉴스사전", "뉴스사후")}.items():
        n_ok, c = paired(real, src, a, b)
        pair[f"{lab}(짝 성공 작품 {n_ok}/200)"] = c
    # 둘 다 짝이 성공한 작품에서 창 준 원천 합
    rows, n_ok = [], 0
    for v in real.values():
        st = v.get("단계별", {})
        if any(st.get(k) == "판정 불가" for k in
               ("뉴스사전", "뉴스사후", "블로그사전", "블로그사후")):
            continue
        n_ok += 1
        for x in v["항목"]:
            if x["원천"] in ("뉴스", "블로그"):
                rows.append((x, v["t_0"]))
    pair[f"창 준 원천 합(네 단계 다 성공 {n_ok}/200)"] = _clsrows(rows)

    # ③ 질의어 종류별 수확
    byq = {}
    for v in real.values():
        byq.setdefault(v["질의출처"], []).append(v["항목수"])
    byq = {k: {"n": len(x), "중앙값": med(x), "평균": round(sum(x) / len(x), 2),
               "0건": sum(1 for y in x if y == 0)} for k, x in sorted(byq.items())}

    # 층 × 질의어
    lay = {}
    for v in real.values():
        key = (v["층"], "한글" if "한글" in v["질의출처"] else "비한글")
        lay.setdefault(key, []).append(v["항목수"])
    lay = {f"{a}·{b}": {"n": len(x), "중앙값": med(x)} for (a, b), x in sorted(lay.items())}

    # ④ 정밀도 대용 --- 항목 제목에 질의 어절이 들어 있나
    def prec(d):
        hit = tot = 0
        for v in d.values():
            toks = [t for t in str(v["질의"]).split() if len(t) >= 2]
            for x in v["항목"]:
                tot += 1
                t = str(x.get("제목", ""))
                if v["질의"] in t or (toks and all(k in t for k in toks)):
                    hit += 1
        return {"항목": tot, "질의 전부 포함": hit,
                "비율": round(hit / tot, 4) if tot else None}

    out = {"무엇": "노트 893 사후 진단 --- **사전등록 밖**(전부 사후 탐색). 요청 0건 · 캐시만 읽었다",
           "① 음성 통제도 같은 시각 분포를 내는가": g1,
           "② 창 짝이 둘 다 성공한 작품으로 제한한 후견지명(단계 실패가 창에 비대칭이었다)": pair,
           "③ 질의어 종류별 수확(실물)": byq,
           "③-b 층 × 질의어": lay,
           "④ 정밀도 대용(제목에 질의 어절 전부 포함)": {"실물": prec(real), "음성": prec(fake)},
           "🔴 ⑤ 언어를 맞춘 음성 비교(사전등록 비는 교란돼 있었다)": {
               "실물 한글 질의": {"n": len([1 for v in real.values() if "한글" in v["질의출처"]]),
                            "중앙값": med([v["항목수"] for v in real.values() if "한글" in v["질의출처"]])},
               "실물 비한글 질의": {"n": len([1 for v in real.values() if "한글" not in v["질의출처"]]),
                             "중앙값": med([v["항목수"] for v in real.values() if "한글" not in v["질의출처"]])},
               "음성(전부 한글)": {"n": len(fake), "중앙값": med([v["항목수"] for v in fake.values()])},
               "언어 맞춘 비(음성 ÷ 실물한글)": round(
                   med([v["항목수"] for v in fake.values()])
                   / med([v["항목수"] for v in real.values() if "한글" in v["질의출처"]]), 4),
               "사전등록 비(음성 ÷ 실물전체)": round(
                   med([v["항목수"] for v in fake.values()])
                   / med([v["항목수"] for v in real.values()]), 4),
               "읽는 법": "사전등록 비 2.31 은 **음성이 전부 한글**이고 실물은 31% 만 한글이라 "
                       "언어가 섞인 값이다. 언어를 맞춰도 0.74 --- **문턱 0.25 를 여전히 세 배 넘는다.**"},
           "⑥ 단계 회계(실물 1,200 단계)": {
               "잰 것": sum(1 for v in real.values() for x in v.get("단계별", {}).values()
                         if x != "판정 불가"),
               "판정 불가(레이트 리밋)": sum(1 for v in real.values()
                                    for x in v.get("단계별", {}).values() if x == "판정 불가")},
           "음성 원천별 중앙값": {s: med([sum(1 for x in v["항목"] if x["원천"] == s)
                                   for v in fake.values()])
                          for s in ("뉴스", "블로그", "디시")},
           "실물 원천별 중앙값": {s: med([sum(1 for x in v["항목"] if x["원천"] == s)
                                   for v in real.values()])
                          for s in ("뉴스", "블로그", "디시")},
           "단계 실패의 창 비대칭": {k: dict(Counter(v.get("단계별", {}).get(k) if
                                             isinstance(v.get("단계별", {}).get(k), str)
                                             else "항목" for v in real.values()))
                            for k in ("뉴스사전", "뉴스사후", "블로그사전", "블로그사후")},
           }
    p = ROOT / "runners/out893_diag.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
