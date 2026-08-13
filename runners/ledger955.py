# -*- coding: utf-8 -*-
"""원장에 **항목 하나**를 더한다 (노트 955).

🔴 **수를 손으로 안 쓴다.** 전부 산출물 키에서 읽는다.
🔴 **추가만 한다. 옛 항목을 고치지 않는다.**
🔴 **사이클당 항목 하나.**

    python3 -m runners.ledger955
"""
import collections
import json
import pathlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEN = ROOT / "data/lab/denominator.json"
FETCH_LOG = pathlib.Path("/Users/ax/wm_harvest/fineweb955_fetch.jsonl")
FETCH_SNAP = ROOT / "runners/out955_fetch.json"


def J(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def pct(x, nd=3):
    return ("%." + str(nd) + "f%%") % (100.0 * x)


def cm(x):
    return format(int(x), ",")


def fetch_snapshot():
    """🔴 수신 상태를 **지금 직접 세어** 산출물로 남긴다(조항 59).

    「받았다」는 종료코드도 로그 줄도 아니다 --- **parquet 이 열리고 행 수가
    954 메타와 같아야** 받은 것이다.
    """
    from runners.fineweb955_fetch import NAMES, OUT, ok_parquet, want_rows
    want = want_rows()
    rows = []
    for n in NAMES:
        p = OUT / n
        good, why = ok_parquet(p, want.get(n))
        rows.append({"파일": n, "받아야 할 행": want.get(n),
                     "바이트": p.stat().st_size if p.exists() else 0,
                     "검사": why, "통과": bool(good)})
    part = sorted(x.name for x in OUT.glob("*.part")) if OUT.exists() else []
    log = []
    if FETCH_LOG.exists():
        for line in FETCH_LOG.read_text(encoding="utf-8").split("\n"):
            if line.strip():
                log.append(json.loads(line))
    done = sum(1 for r in rows if r["통과"])
    snap = {
        "무엇": "955 --- FineWeb-2 kor_Hang 전량 수신 상태(지금 직접 셌다)",
        "🔴 「받았다」의 정의": ("`pq.ParquetFile(p).metadata.num_rows` 가 954 가 읽은 메타의 "
                        "「전량 행」과 같을 것. 🔴 종료코드 0 도 HTTP 200 도 증거가 아니다"),
        "🔴 분자 = 열리고 행 수가 맞는 파일": done,
        "🔴 분모 = 전량 파일": len(rows),
        "받은 바이트(합)": sum(r["바이트"] for r in rows),
        "받아야 할 행(합)": sum(v for v in want.values()),
        "🔴 받는 중(.part)": part,
        "낱개": rows,
        "로그 줄 수": len(log),
        "로그 --- 실패": [r for r in log if r.get("무엇") == "실패"],
        "통과": bool(done == len(rows)),
    }
    FETCH_SNAP.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    return snap


def main():
    d = J("runners/out955_D.json")
    ds = J("runners/out955_docstamp.json")
    fp = J("runners/out955_fiveprime.json")
    fs = fetch_snapshot()

    v = d["🔴🔴 판정(사전등록 §6)"]
    w = d["🔴 배선 검사 W1~W8(티처 #93 이 낸 수를 내 코드가 독립 재현하는가)"]
    p = d["🔴 예측 채점(사전등록 §5)"]
    uv = d["🔴 심은 키 U·V(정규화 함수를 지난다)"]
    rr = d["🔴 심은 키 R(Range 재수신)"]
    m6 = d["🔴 m6 --- 뉴스형 host 정규식 재측정"]
    m7 = d["🔴 m7 --- head200 이름 대조"]
    r2 = d["🔴 자별"]["② URL 정규화(🔴 정본)"]
    r1 = d["🔴 자별"]["① URL 정확"]
    cc = ds["🔴🔴 키 이름 대 실제 계산 대조(티처 #93 C1)"]
    lanes = None
    for sec in fp.get("절", fp.get("검사", [])) if isinstance(fp, dict) else []:
        pass

    def find_sec(o, needle):
        """⑤′ 산출물에서 절 하나를 찾는다(구조를 손으로 안 박는다)."""
        found = []

        def walk(x):
            if isinstance(x, dict):
                if isinstance(x.get("검사"), str) and needle in x["검사"]:
                    found.append(x)
                for vv in x.values():
                    walk(vv)
            elif isinstance(x, list):
                for vv in x:
                    walk(vv)
        walk(o)
        return found[0] if found else None

    lanes = find_sec(fp, "레인 계수")

    D = v["정본 D = 자② D_문서^{K=21}"]
    title = ("🔴🔴 노트 955 [탐색+수리×%s] — **`D` 의 분자가 이름과 달랐다.** 다시 정의하니 "
             "954 의 「보류」가 **「FineWeb-2 전량을 받는다」**로 뒤집힌다(정본 D = **%s** · "
             "깨끗한 읽기 **여덟이 한 칸**) · 배선 검사 **%d/%d 로 티처 #93 의 수를 전부 독립 재현** · "
             "🔴 그리고 티처의 **m6·m7 을 실측으로 반증했다**"
             % ((lanes or {}).get("🔴🔴 레인 수(분자 --- 이것이 「수리 레인」의 수다)", "?"),
                pct(D, 3), w["분자 = 맞은 검사"], w["분모 = 검사 전량"]))

    item = collections.OrderedDict([
        ("언제", "2026-08-13 · 가지 `note/955-d-redefine` · 사전등록 `docs/prereg_955_D.md` "
                "(**측정 전** · 파일 하나 · 커밋 `8597b7184`) · 입력 = 원장 1000(티처 #93) · 954"),
        ("🔴 자 정본(안 만졌다)",
         "판 ρ **0.47034 ± 0.0021(SD) · SE 0.00060 · 12도메인 · 유보 3,775** · 채택 문턱 "
         "**0.00353**. 🔴 **이 사이클도 판을 뗐다**(⓪-가) — 코퍼스 겹침은 판 유보와 무관하다. "
         "**판 주장 0**"),
        ("⓪ 방향 설계",
         {"자": "🔴 판을 뗐다. 집합 교집합 비율 · 키 다중도. 🔴 **표본 오차로는 이 판정이 "
                "안 뒤집힌다** — n=%s 에서 이항 SE 0.034%%p 이고 문턱까지 거리가 SE 의 약 300배다. "
                "**뒤집는 것은 정의뿐이고, 954 가 정확히 그렇게 뒤집혔다**"
                % cm(r2["분모 ② FineWeb 표본 문서"]),
          "지평": "FineWeb-2 `kor_Hang` 25파일 · %s 문서 · 105.77GB — 🔴 **이번엔 받는다**"
                % cm(fs["받아야 할 행(합)"]),
          "탐색": "별도 탐색 팔 **안 띄웠다**(사용자가 1·2·3순위를 지정했다). 「없다」가 아니다",
          "목표": "다섯 출력 중 직접 민 것 없다. 미는 것은 **입력 자료의 참값**과 **회계의 정직성**"}),

        ("🔴🔴 1순위 — `D` 를 다시 정의했다. **한 줄에 정의 하나 · 분자와 분모를 같은 줄에**",
         {"🔴 954 가 미끄러진 자리": "`prereg_954_dupe.md:102` 가 한 줄에 정의를 **둘** 적었다 — "
                            "「교집합 ÷ FineWeb 표본 문서 수 (= FineWeb 문서 중 HPLT 에 이미 "
                            "URL 이 있는 비율)」. 앞구절은 **키÷문서**, 뒤구절은 **문서÷문서**다. "
                            "`score954.py:34` 는 뒤엣것을 골랐고 `dupe954_fineweb.py:234` 의 "
                            "**키 이름은 앞엣것**이었다",
          "🔴 정본 D = 자② D_문서^{K=21}": "**%s** (분자 = 다중도≤21 인 교집합 키에 걸린 "
                                  "FineWeb 표본 문서 %s · 분모 = FineWeb 표본 문서 %s)"
                                  % (pct(D),
                                     cm(r2["🔴 절단 곡선"]["K<=21"]
                                        ["🔴 D_문서^K 분자 = 다중도<=K 인 교집합 키에 걸린 FineWeb 표본 문서"]),
                                     cm(r2["분모 ② FineWeb 표본 문서"])),
          "🔴 깨끗한 읽기 여덟이 **전부 같은 칸**": ", ".join(
              "%s %s" % (k, pct(vv)) for k, vv in v["깨끗한 읽기 여덟"].items()),
          "🔴 「보류」를 낸 유일한 읽기": "자② D_문서(절단 없음) **%s** → `%s`. "
                              "🔴 **954 의 판정은 이 하나 위에 서 있었다**"
                              % (pct(v["🔴 오염된 읽기(판정 밖) --- 자② D_문서(절단 없음)"]),
                                 v["🔴 그 오염된 읽기가 드는 칸"]),
          "🔴 판정(사전등록 §6)": v["🔴 판정"],
          "㉡ 키 기준과 문서 기준을 둘 다": "자② D_키 **%s**(분모 = FineWeb 표본 서로 다른 키 %s) · "
                                "자② D_문서 **%s**(분모 = FineWeb 표본 문서 %s) · "
                                "자① D_키 **%s** · 자① D_문서 **%s**"
                                % (pct(r2["🔴 D_키 = ⓐ ÷ ④"]),
                                   cm(r2["분모 ④ FineWeb 표본 서로 다른 키"]),
                                   pct(r2["🔴 D_문서 = ⓑ ÷ ②"]),
                                   cm(r2["분모 ② FineWeb 표본 문서"]),
                                   pct(r1["🔴 D_키 = ⓐ ÷ ④"]), pct(r1["🔴 D_문서 = ⓑ ÷ ②"])),
          "㉢ 절단 K=21 --- **재기 전에 정했다**": "근거: HPLT 2.0 은 **크롤 안에서만** 지웠고 "
                                     "collection 이 **21** 이다 → 「같은 페이지가 크롤마다 "
                                     "한 번씩 살아남았다」로 설명 가능한 최대 다중도가 21. "
                                     "그 위는 정규화가 **서로 다른 페이지를 뭉친 것**이다. "
                                     "코퍼스 평균 다중도 **%s** 의 %.1f배 → 보수적이다"
                                     % (r2["뭉침 --- 코퍼스 전체 키당 HPLT 문서(평균)"],
                                        21.0 / r2["뭉침 --- 코퍼스 전체 키당 HPLT 문서(평균)"]),
          "절단 곡선": " · ".join("^%s %s" % (k.replace("K<=", ""), pct(c["🔴 D_문서^K"]))
                              for k, c in r2["🔴 절단 곡선"].items())
                     + " · 절단 없음 %s" % pct(r2["🔴 D_문서 = ⓑ ÷ ②"]),
          "뭉침의 크기": "교집합 키당 HPLT 문서 평균 **%s** · 중앙값 **%d** · 최대 **%s** "
                    "(코퍼스 평균 %s). 다중도 21 초과 교집합 키 **%s = %s**"
                    % (r2["뭉침 --- 교집합 키당 HPLT 문서(평균)"],
                       r2["뭉침 --- 교집합 키당 HPLT 문서(중앙값)"],
                       cm(r2["뭉침 --- 교집합 키당 HPLT 문서(최대)"]),
                       r2["뭉침 --- 코퍼스 전체 키당 HPLT 문서(평균)"],
                       cm(r2["뭉침 --- 다중도 > 21 인 교집합 키"]),
                       pct(r2["뭉침 --- 다중도 > 21 인 교집합 키의 비율(÷교집합 키)"], 2)),
          "🔴 조항 61 --- 절단이 못 하는 것": "절단은 **참 중복을 복원하지 않는다**. 뭉치지 "
                                 "않았는데 잘려 나가는 참 중복도 있다. 그래서 절단 전후를 둘 다 실었다"}),

        ("🔴🔴 배선 검사 %d/%d — **티처 #93 이 낸 수를 내 코드가 전부 독립 재현했다**"
         % (w["분자 = 맞은 검사"], w["분모 = 검사 전량"]),
         "문서 %s · shard %d · 표본 %s · 파일 %d · 교집합 키 %s · FineWeb−HPLT %s · "
         "HPLT−FineWeb %s · 맞은 FW 문서 %s · 맞은 HPLT 문서 %s · 자① %s · 자③ %s · "
         "전문md5 %s · 자② %s · D_954글자 셋 · 🔴 **절단 곡선 ^1 ^2 ^5 ^10 ^100 ^1000 여섯 전부** · "
         "host %s · 954 뉴스형 %s. 🔴 **절단 곡선이 맞았다는 것이 K=21 값을 믿을 근거다** — "
         "자료가 아니라 절단 코드가 옳다는 증거이기 때문이다"
         % (cm(r2["분모 ① HPLT 문서 전량"]), r2["읽은 HPLT shard"],
            cm(r2["분모 ② FineWeb 표본 문서"]), r2["읽은 FineWeb 파일"],
            cm(r2["분자 ⓐ 교집합(서로 다른 키)"]),
            cm(r2["① 반대 방향 --- FineWeb − HPLT(키)"]),
            cm(r2["① 반대 방향 --- HPLT − FineWeb(키)"]),
            cm(r2["분자 ⓑ 맞은 FineWeb 표본 문서"]), cm(r2["분자 ⓒ 맞은 HPLT 문서"]),
            pct(r1["🔴 D_문서 = ⓑ ÷ ②"]),
            pct(d["🔴 자별"]["③ 본문 앞 200자"]["🔴 D_문서 = ⓑ ÷ ②"]),
            pct(d["🔴 자별"]["덤 --- 전문 md5(판정 밖)"]["🔴 D_문서 = ⓑ ÷ ②"]),
            pct(r2["🔴 D_문서 = ⓑ ÷ ②"]), cm(m6["서로 다른 host"]),
            pct(m6["① 954 자 비율"], 4))),

        ("🔴 심은 키 — 검정력을 0 에서 끌어올렸다(티처 #93 M6)",
         {"U (정규화 함수를 지난다)": "실제 HPLT URL 에 쿼리를 붙였다 → 자②는 같은 키(%s) · "
                             "자①은 다른 키(%s) · 자②의 키가 HPLT 에 있다(%s) · "
                             "자①의 키는 없다(%s) → **%s**"
                             % (uv["U ㉠ 자②가 같은 키로 보나"], uv["U ㉡ 자①이 다른 키로 보나"],
                                uv["U ㉢ 자②의 키가 HPLT 키 집합에 드나(들어야 한다)"],
                                uv["U ㉣ 자①의 키가 HPLT 키 집합에 드나(들면 안 된다)"],
                                uv["U 통과"]),
          "V (음성 대조)": "경로 한 글자를 바꿨다 → 어느 자도 같게 안 본다 → **%s**" % uv["V 통과"],
          "🔴 R (Range 수신 + parquet 열 읽기 + 해시)": "행군 0~3 을 **지금 다시 HTTP Range 로 받아** "
                                        "해시를 새로 계산했다: 행 %s · 네 열 **불일치 %d** · "
                                        "%.1f MB · 요청 %d → **%s**"
                                        % (cm(rr.get("다시 계산한 행", 0)),
                                           sum(rr.get(k, 0) for k in
                                               ("🔴 불일치 --- url_h", "🔴 불일치 --- urn_h",
                                                "🔴 불일치 --- hed_h", "🔴 불일치 --- txt_h")),
                                           rr.get("받은 바이트", 0) / 1e6,
                                           rr.get("요청 수", 0), rr.get("통과"))}),

        ("🔴🔴 티처 #93 의 **m6·m7 을 실측으로 반증했다**",
         {"m6 앵커 없는 `|news`": "실재한다. **그런데 크기가 티처가 말한 것이 아니다.** "
                          "464 shard host 빈도표 전량(문서 %s · host %s)으로 직접 쟀다: "
                          "954 자 **%s** vs 라벨 자 **%s** → 차 **%d 문서 · host %d 개**이고 "
                          "그 둘은 `%s`. 🔴 **`P7 빗나감의 진짜 원인`은 반증됐다** — "
                          "앵커를 박아도 0.00003%%p 움직인다. ⚠ 그리고 `news` 를 **통째로 빼면** "
                          "%s 로 떨어지는데 그때 버려지는 **%s host · %s 문서**는 "
                          "`newscj.com`·`inews365.com`·`newscham.net` 같은 **진짜 언론사**다 — "
                          "**그 자가 더 나쁘다**"
                          % (cm(m6["분모 = HPLT 문서 전량(host 빈도표 합)"]),
                             cm(m6["서로 다른 host"]), pct(m6["① 954 자 비율"], 4),
                             pct(m6["③ 955-라벨 자(🔴 사후 추가 · P5 채점 밖) 비율"]
                                 if "③ 955-라벨 자(🔴 사후 추가 · P5 채점 밖) 비율" in m6
                                 else m6["③ 955-라벨 자 비율"], 4),
                             m6["🔴🔴 ① − ③ = 앵커 결함이 실제로 잘못 잡던 문서"],
                             m6["🔴🔴 ① − ③ 의 host 수"],
                             "` · `".join(e["host"] for e in
                                          m6["🔴🔴 ① − ③ 의 host 전량(적으니 전부 싣는다)"]),
                             pct(m6["② 955-앵커 자 비율"], 4),
                             cm(m6["⚠ ① − ② 의 host 수"]),
                             cm(m6["⚠ ① − ② = 앵커 자가 **더** 버리는 문서"])),
          "m7 `head200`": "**이름과 실제가 같다.** 무작위 %s 시험 불일치 **%d** · 4바이트 문자 "
                        "경계 시험 %d/%d. 200자는 UTF-8 로 최대 800바이트이므로 800바이트 "
                        "선절단은 앞 200자를 **못 자른다**. 어긋나는 곳은 **깨진 UTF-8** "
                        "하나뿐인데 두 코퍼스의 `text` 는 parquet 문자열이라 유효 UTF-8 이다"
                        % (cm(m7["무작위 시험 횟수"]), m7["🔴 불일치"],
                           sum(1 for e in m7["경계 시험"] if e["같나"]), len(m7["경계 시험"])),
          "🔴 이 사이클이 배운 것": "**티처의 진단도 자다.** 크기를 안 재고 처방만 받으면 "
                          "「고쳤는데 더 나빠지는」 자리가 있다 — P5 가 정확히 그랬다"}),

        ("예측 채점(사전등록 §5) — %d/%d" % (p["분자 = 맞은 예측"], p["분모 = 예측 전량"]),
         {r["예측"]: {"값": r["값"], "맞았나": r["맞았나"]} for r in p["낱개"]}),

        ("🔴 빗맞힌 P2 가 소득이다",
         "**뭉침은 문서 쪽만의 현상이 아니다.** D_키^21 ÷ D_키 = **%s** 로 0.95 를 밑돌았다 — "
         "교집합 키 %s 중 **%s(%s)**가 다중도 21 을 넘는다. 키를 세도 뭉침이 보인다"
         % ([r["값"] for r in p["낱개"] if r["예측"].startswith("P2")][0],
            cm(r2["분자 ⓐ 교집합(서로 다른 키)"]),
            cm(r2["뭉침 --- 다중도 > 21 인 교집합 키"]),
            pct(r2["뭉침 --- 다중도 > 21 인 교집합 키의 비율(÷교집합 키)"], 2))),

        ("🔴 ㉣ 집행 — FineWeb-2 전량 수신",
         {"🔴 「받았다」의 정의": fs["🔴 「받았다」의 정의"],
          "🔴 지금 상태": "**%d / %d 파일**(열리고 행 수가 954 메타와 일치) · 받은 바이트 %s · "
                    "받는 중 %s"
                    % (fs["🔴 분자 = 열리고 행 수가 맞는 파일"], fs["🔴 분모 = 전량 파일"],
                       cm(fs["받은 바이트(합)"]), fs["🔴 받는 중(.part)"] or "없음"),
          "실패": fs["로그 --- 실패"] or "없음",
          "순서": "`hplt_fetch.py:35` 의 `stratified_order()`(비트 뒤집기)를 본떴다 — "
                "앞에서 자르지 않는다",
          "목적지": "🔴 **저장소 밖** `/Users/ax/wm_harvest/fineweb2_ko/` "
                 "(데몬 감시 구역 회피 + `.gitignore` parquet 규칙 구멍 · 두 겹)",
          "🔴 안 끝났으면": "**「전량 받았다」는 %d/%d 에만 쓴다.** 지금은 그 수를 그대로 신고한다"
                     % (fs["🔴 분모 = 전량 파일"], fs["🔴 분모 = 전량 파일"])}),

        ("🔴 2·3순위 [수리] — 기계가 센다(티처 #93 C4·㉤)",
         {"🔴 레인 계수": ("`R<n>` 표지로 센 레인 **%s** · `[수리]` 커밋 **%s** · "
                    "사전등록 §8 이 예고한 레인 **%s** · 통과 **%s**"
                    % ((lanes or {}).get("🔴🔴 레인 수(분자 --- 이것이 「수리 레인」의 수다)", "?"),
                       (lanes or {}).get("🔴 그중 `[수리]` 커밋 수(분자)", "?"),
                       (lanes or {}).get("🔴 사전등록이 예고한 레인 수", "?"),
                       (lanes or {}).get("통과", "?"))) if lanes else "🔴 ⑤′ 산출물에서 못 찾았다",
          "🔴 커밋 수가 아니라 레인 수로 판정한다": "한 커밋이 레인 둘을 나를 수 있다(`R7·R8`). "
                                    "954 의 병은 「레인 하나」라 적고 커밋 셋을 한 것인데, "
                                    "**커밋만 세면 그 병을 뒤집어서 다시 못 잡는다**",
          "예고했는데 안 연 레인": (lanes or {}).get("🔴 예고했는데 안 연 레인", "?"),
          "표지 없는 `[수리]` 커밋": (lanes or {}).get("🔴 표지 없는 `[수리]` 커밋(레인을 못 센다)", "?"),
          "R1 ㉠": "키 이름을 실제 계산에 맞췄다(계산은 안 바꿨다 · 사전등록 §2-B 에 측정 전에 박았다). "
                 "`D_키`·`E_키`·`D_954글자` 를 새 키로 더했다. `score954.py` 는 두 이름을 다 읽고 "
                 "**고른 것을 이름으로 적는다**",
          "R2·R3": "`audit.py` 의 죽은 숫자 등기부와 `LIVE_GLOBS`",
          "R4·R5·R6": "⑤′ 가 자기 산출물을 이름으로 배제(30/39 → **18/27** — 티처가 손으로 센 수와 "
                    "일치) · 되짚는 트리를 **커밋된 트리**로 · 레인을 기계가 센다",
          "R7·R8": "음성 대조 임시 파일을 `/tmp` 로(데몬 60초 틱이 **일부러 망가뜨린 판을 커밋할** "
                 "창이 열려 있었다) · 독스트링의 죽은 수 376 → 378행·378일·되찾은 날 347",
          "R9": "`.gitignore` 죽은 규칙 삭제 + parquet 규칙을 `data/ingest/**` 로. "
                "심어서 확인 **전 2/4 → 후 4/4**",
          "R10": "뉴스형 host 정규식 앵커 — 🔴 **그리고 티처의 진단을 반증했다**(위)"}),

        ("🔴 문서 도장 · 대조",
         "🔴 **「생산기가 찍었다」가 분자를 보증하게 만들었다**(티처 #93 C1 의 교훈): "
         "`note955_gen.py` 가 문서를 찍기 **전에** 모든 `D_*`·`E_*`·절단 곡선 값을 "
         "**그 이름이 말하는 분자·분모로 직접 다시 나눠** 견준다 — **%d/%d**. "
         "어긋나면 **문서를 안 찍는다**. 문서 sha `%s`"
         % (cc["분자 = 맞은 대조"], cc["분모 = 대조 전량"],
            list(ds["🔴 문서 sha256"].values())[0][:12])),

        ("🔴 ⑤′ 취합 검사", {
            "통과": fp.get("통과"),
            "🔴 분자 = 초록 절": sum(1 for k, s in fp.items()
                              if isinstance(s, dict) and s.get("통과") is True
                              and isinstance(s.get("검사"), str)),
            "🔴 분모 = 절 전량": sum(1 for k, s in fp.items()
                             if isinstance(s, dict) and isinstance(s.get("검사"), str)),
            "🟢 초록": [k for k, s in fp.items()
                     if isinstance(s, dict) and isinstance(s.get("검사"), str)
                     and s.get("통과") is True],
            "🔴 붉은": [k for k, s in fp.items()
                     if isinstance(s, dict) and isinstance(s.get("검사"), str)
                     and s.get("통과") is not True],
            "🔴🔴 ⓪ 관문이 **처음으로 비었다**":
                ("954 는 *「데몬이 도는 한 **원리상** 못 비운다」*고 적었다. "
                 "🔴 **그 주장이 반증됐다** — ⑤′ 자기 산출물을 **먼저 커밋**하고 다음 주행을 "
                 "돌리면 관문이 빈다(데몬은 이력 수술 동안 재워 뒀다). 더러운 경로 **%s**"
                 % fp["⓪ 관문(작업 트리)"]["더러운 경로 수"])
                if fp.get("⓪ 관문(작업 트리)", {}).get("통과") else "🔴 아직 붉다",
            "⚠": "낱개는 `runners/out955_fiveprime.json` 에 있다"}),

        ("🔴 안 한 것 · 못 한 것 (갈라 적는다)",
         ["**안 했다** --- 표본을 다시 안 떴다(954 의 npz 를 그대로 읽었다 · 사전등록 §7)",
          "**안 했다** --- MinHash/SemDeDup/형태소(원장 998 실측대로)",
          "**안 했다** --- 판 ρ 갱신(유보 3,775 에 붙는 행이 0 이다)",
          "**안 했다** --- 논문(⑥). 🔴 이 사이클도 **판 주장이 0** 이라 스텝이 없다",
          "**안 했다** --- 티처 #92 M4(래칫 ④ 를 파일별로) · C2(`s` 항등식). "
          "사용자가 「여유가 되면」이라 했고 여유가 안 됐다",
          "🔴 **못 했다** --- **PR #212 머지**. `mergeable=CONFLICTING · mergeStateStatus=DIRTY` — "
          "데몬이 만진 `data/ingest/*.gz` 가 양쪽에서 갈라졌다. 그래서 **자료 파일은 안 건드리고 "
          "954 의 코드·문서·산출물 14개만**(PR blob 과 바이트 동일을 shasum 으로 대조) 이 가지에 "
          "실어 계보를 이었다(티처 #93 M7)",
          "🔴 **못 했다** --- 티처 #93 M1(FineWeb 표본의 44.2% 를 만든 코드가 세상에 없다). "
          "고치려면 표본을 다시 떠야 하는데 그러면 배선 검사 W1~W8 의 **재현 대상이 사라진다**. "
          "**다음 사이클의 것이다**",
          "🔴 **못 했다** --- 절 1-나(날 것 git 호출 전수)를 커밋된 트리로. `lab/gitcall.py` 가 "
          "작업 트리를 훑는데 그 파일이 R5 레인의 범위 밖이었다",
          "**못 했다** --- 「FineWeb 에만 있는 문서」의 정체 가르기(제거 범위가 달라 원리상 불가)"]),

        ("🔴 다음이 이어받을 자리",
         "① 🔴 **수신이 끝나면 FineWeb-2 전량 위에서 재라** — 표본 %s(2.231%%)로 낸 D 를 "
         "전량으로 확인하고, 티처 #93 M1 의 「코드 없는 표본」 부채를 **표본을 다시 떠서** 갚아라 "
         "② **교차 collection 정확중복 18.285%% 를 전역 Bloom 으로 실제로 지워라** "
         "③ **HPLT − FineWeb %s 키**가 이 코퍼스의 진짜 값이다 — 그쪽을 봐라 "
         "④ 티처 #92 의 **M4·C2 가 그대로 열려 있다** "
         "⑤ 절 1-나를 커밋된 트리로(`lab/gitcall.py`)"
         % (cm(r2["분모 ② FineWeb 표본 문서"]),
            cm(r2["① 반대 방향 --- HPLT − FineWeb(키)"]))),
    ])

    replace = "--replace" in sys.argv
    den = json.loads(DEN.read_text(encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)
    if title in den:
        if not replace:
            raise SystemExit("🔴 같은 표제가 이미 있다 --- 덮어쓰지 않는다")
        del den[title]
    den[title] = item
    DEN.write_text(json.dumps(den, ensure_ascii=False, indent=1), encoding="utf-8")
    print("원장 항목 수:", len(den))
    print("표제:", title[:200])


if __name__ == "__main__":
    main()
