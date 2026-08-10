# -*- coding: utf-8 -*-
"""노트 894 을 --- **디시 과거 도달 노크**. 크롤이 아니다.

사전등록은 `data/lab/denominator.json` 의 '**사전등록** 디시로 과거를 팔 수 있는가 …' 칸.

**왜 이것이 관문인가.** 디시는 전이 간선(G3 · 답글 119/119 · 초 단위 시각)의 **유일한**
원천인데, 893 캐시로 세니 `t_0 < 2019` 인 작품 **116개 중 2019 이전까지 닿은 것이 0개**
였다(드래곤볼 1984년작조차 제일 오래된 디시 항목이 2026-05-16 · 디시 항목의 61.6%가
2026년). 즉 **검색은 최신순 1쪽만 준다.** 이게 안 풀리면 시간축 코퍼스가 '최근 몇 달'로
잘린다.

두드릴 것 셋(싼 것부터):
  ⓐ 검색에 **날짜/페이지 파라미터**가 있는가        ← 제일 쌈
  ⓑ 작품별 **전용 갤러리 존재율**
  ⓒ 웨이백 --- 커버리지가 생존 편의라 **모양 학습 전용**(노트 639). 이 사이클에서는
     ⓐ·ⓑ 로 결론이 서면 **안 두드린다**(요청을 아낀다).

🔴 **예의.** 요청 총량 **≤ 100**(사전등록 F6 --- 넘으면 이 사이클의 노크는 자가 무효).
워커 1 · 요청 사이 ≥ 2.5초. 893 이 이미 네이버 403 을 82건 맞았고 에펨은 HTTP 430 으로
영구히 잃었다. **차단당하면 그 문을 영구히 잃는다.**
"""
from __future__ import annotations

import datetime as dt
import glob
import html as _html
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
from ingest import social                                     # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out894_knock.json"
BUDGET = 100                    # 🔴 사전등록 F6
SLEEP = 2.5
PRE_USED = 4                    # 배선 탐침으로 이미 쓴 것(post 2 · gallery 2) --- 정직하게 얹는다

REQ = {"n": PRE_USED, "fail": Counter(), "by": Counter()}

DC_EMPTY = "검색 결과가 없"
DC_BOX = "sch_result"
_DC_LI = re.compile(r"<li>(.*?)</li>", re.S)
_DC_DT = re.compile(r'class="date_time">([\d.]+)\s+([\d:]+)<')
_DC_LN = re.compile(r"gall\.dcinside\.com/(?:mgallery/|mini/)?board/view/\?id=([\w]+)&(?:amp;)?no=(\d+)")
_DC_END = re.compile(r'href="/post/p/(\d+)/q/[^"]*"\s+class="sp_pagingicon page_end"')
_GAL = re.compile(r'<li><a href="https://gall\.dcinside\.com/(mgallery/|mini/|person/)?board/lists/\?id=([\w]+)"[^>]*class="gallname_txt[^"]*">(.*?)</a>'
                  r'.*?<span class="info txtnum">새글\s*([\d,]+)/([\d,]+)</span>', re.S)


RAW = ROOT / "data/state/cache_k894"      # 🔴 894 교훈 --- **원본을 남긴다**


def get(url: str, tag: str) -> str:
    # 🔴 893 이 원본 HTML 을 안 남겨서 894 가 '캐시 재해석' 을 못 하고 재요청해야 했다.
    # 파서가 틀리면 원본 없이는 다시 셀 수 없다 --- 이번엔 남긴다.
    RAW.mkdir(parents=True, exist_ok=True)
    import hashlib
    p = RAW / (hashlib.sha1(url.encode()).hexdigest()[:20] + ".html")
    if p.exists():
        return p.read_text(encoding="utf-8")
    if REQ["n"] >= BUDGET:
        raise RuntimeError(f"🔴 요청 예산 {BUDGET} 소진 --- 사전등록 F6")
    REQ["n"] += 1
    REQ["by"][tag] += 1
    try:
        b = urllib.request.urlopen(
            urllib.request.Request(url, headers=dict(social.UA)), timeout=25).read()
    except Exception as e:
        REQ["fail"][f"{tag}:{type(e).__name__}:{getattr(e, 'code', '-')}"] += 1
        raise
    finally:
        time.sleep(SLEEP)
    h = b.decode("utf-8", "ignore")
    p.write_text(h, encoding="utf-8")
    return h


# ── 디시 게시물 검색(쪽 지원) ────────────────────────────────
def dc_post(q: str, page: int = 1) -> dict:
    u = ("https://search.dcinside.com/post/"
         + (f"p/{page}/" if page > 1 else "") + "q/" + urllib.parse.quote(q))
    h = get(u, "post")
    items = []
    for b in _DC_LI.findall(h):
        ln = _DC_LN.search(b)
        if not ln:
            continue
        d = _DC_DT.search(b)
        iso = None
        if d:
            p = d.group(1).strip(".").split(".")
            if len(p) == 3:
                iso = "%04d-%02d-%02d" % (int(p[0]), int(p[1]), int(p[2]))
        items.append({"id": f"dc:{ln.group(1)}:{ln.group(2)}", "시각": iso})
    end = _DC_END.search(h)
    verdict = ("항목" if items else
               "확인된 0" if (DC_EMPTY in h or DC_BOX in h) else "판정 불가")
    ds = [x["시각"] for x in items if x["시각"]]
    return {"쪽": page, "항목": len(items), "판정": verdict, "바이트": len(h),
            "무결과 표지": DC_EMPTY in h, "결과 컨테이너": DC_BOX in h,
            "끝쪽": int(end.group(1)) if end else None,
            "제일 오래된": min(ds) if ds else None, "제일 최신": max(ds) if ds else None,
            "ids": [x["id"] for x in items]}


# ── 디시 갤러리 검색 ─────────────────────────────────────────
def norm(s: str) -> str:
    # 🔴 894 자가 적발. 초판이 `ⓜ`(마이너)·`ⓝ`(미니)·`ⓟ` 아이콘 글자를 안 걷어서
    # **정확일치가 0/30 으로 나왔다** --- `상수리 나무 아래ⓜ` 대 `상수리나무 아래`.
    # 조항 59 그대로: '확인된 0' 처럼 보이는 것이 **파서 고장**이었다. 눈으로 상세를
    # 안 읽었으면 *"작품별 전용 갤은 없다"* 라고 적을 뻔했다.
    s = re.sub(r"[ⓜⓝⓟⓖⒼⓂ]", "", _html.unescape(s))
    return re.sub(r"[\s!?~·:,.'\"\-()\[\]<>_/]", "", s).lower()


def dc_gallery(q: str) -> dict:
    h = get("https://search.dcinside.com/gallery/q/" + urllib.parse.quote(q), "gallery")
    gs = []
    for kind, gid, name, new, tot in _GAL.findall(h):
        nm = re.sub(r"\s+", " ", re.sub(r"<em[^>]*>.*?</em>", "",
                                        name, flags=re.S)).strip()
        gs.append({"갤": gid, "이름": nm,
                   "종류": {"mgallery/": "마이너", "mini/": "미니", "person/": "인물"}.get(kind, "정식"),
                   "새글": int(new.replace(",", "")), "총글": int(tot.replace(",", ""))})
    exact = [g for g in gs if norm(g["이름"]) == norm(q)]
    return {"질의": q, "결과 갤 수": len(gs), "무결과 표지": DC_EMPTY in h,
            "판정": ("항목" if gs else "확인된 0" if (DC_EMPTY in h or DC_BOX in h) else "판정 불가"),
            "정확일치": exact[:3], "상위 3": gs[:3]}


def boot_ratio(hit, n, B=10000, seed=894):
    if not n:
        return [None, None]
    rng = random.Random(seed)
    es = sorted(sum(1 for _ in range(n) if rng.randrange(n) < hit) / n for _ in range(B))
    return [round(es[int(0.025 * B)], 4), round(es[int(0.975 * B)], 4)]


def med(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2] if xs else None


def main():
    """`python3 runners/knock894.py b` 로 ⓑ 만 다시 잰다(파서 자가 적발 후 재측정용).
    건너뛴 칸은 이전 `out894_knock.json` 에서 그대로 가져온다."""
    only = sys.argv[1] if len(sys.argv) > 1 else None
    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    t0 = time.time()
    rows = [json.loads(open(p, encoding="utf-8").read())
            for p in sorted(glob.glob(str(ROOT / "data/state/cache_p893/*.json")))]
    real = [r for r in rows if r.get("ok") and not r["key"].startswith("FAKE")]

    res = {"무엇": "노트 894 --- 디시 과거 도달 노크(크롤 아님)",
           "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip()}

    # ── 배선 검사 ①  양성/음성 통제(이미 쓴 탐침 2요청의 결과를 여기 적는다)
    res["배선 ㄱ 양성·음성 통제(탐침 2요청 · 위 PRE_USED 에 포함)"] = {
        "양성 `체인소맨`": {"바이트": 56519, "결과 컨테이너": True, "무결과 표지": False,
                       "검색결과 링크": 81},
        "음성 `Aldo no Isekai Tensei`(893 이 ValueError 로 죽인 질의)":
            {"바이트": 43561, "결과 컨테이너": False, "무결과 표지": True, "옛 파서 항목": 0},
        "읽는 법": "893 의 `ValueError` 는 **차단이 아니라 무결과**였다. 새 가드는 이걸 '확인된 0' 으로 읽는다.",
    }

    # ── P4  가드 뒤집기의 전제를 실측 검증(12건 재요청)
    fails = sorted({r["질의"] for r in real
                    if "결과 컨테이너 없음" in str(r.get("실패단계", {}).get("디시최신", ""))})
    rng = random.Random(894)
    p4q = rng.sample(fails, 12)
    p4 = []
    for q in (p4q if only in (None, "all") else []):
        try:
            p4.append({"질의": q, **{k: v for k, v in dc_post(q).items() if k != "ids"}})
        except Exception as e:
            p4.append({"질의": q, "오류": f"{type(e).__name__}:{getattr(e, 'code', '-')}"})
    n_mark = sum(1 for x in p4 if x.get("무결과 표지"))
    n_zero = sum(1 for x in p4 if x.get("판정") == "확인된 0")
    p4res = {
        "모집단": {"893 이 ValueError 로 죽인 서로 다른 질의": len(fails)},
        "표본": 12, "씨앗": 894,
        "무결과 표지 보유": f"{n_mark}/12", "새 가드가 '확인된 0' 으로 읽음": f"{n_zero}/12",
        "부트 95%(표지 보유율)": boot_ratio(n_mark, 12),
        "예측": "≥ 11/12 (반증: ≤ 9/12)",
        "판정": "적중" if n_mark >= 11 else ("반증(F1 발화)" if n_mark <= 9 else "구간 안(미달·미반증)"),
        "상세": p4,
    }
    if only in (None, "all"):
        res["🔴 P4 --- 가드 뒤집기의 전제 실측"] = p4res

    # ── ⓐ  쪽 파라미터와 과거 도달
    #     표본 규칙(고정): 한글 질의 · 893 디시 항목 ≥ 10 인 작품 중 **t_0 오름차순 5개**
    cand = []
    for r in real:
        dc = [x for x in r["항목"] if x["원천"] == "디시" and x.get("시각")]
        if len(dc) >= 10 and "한글" in str(r.get("질의출처")):
            cand.append({"질의": r["질의"], "t_0": r["t_0"], "층": r["층"],
                         "893 디시 항목": len(dc), "893 제일 오래된": min(x["시각"] for x in dc)})
    cand.sort(key=lambda x: x["t_0"])
    a_smp = cand[:5]
    a = []
    for s in (a_smp if only in (None, "all") else []):
        q = s["질의"]
        row = dict(s)
        try:
            p1 = dc_post(q, 1)
            row["1쪽"] = {k: v for k, v in p1.items() if k != "ids"}
            end = p1["끝쪽"]
            p2 = dc_post(q, 2)
            row["2쪽"] = {k: v for k, v in p2.items() if k != "ids"}
            s1, s2 = set(p1["ids"]), set(p2["ids"])
            row["1·2쪽 자카드"] = (round(len(s1 & s2) / len(s1 | s2), 4) if (s1 | s2) else None)
            last = end if end else 2
            pl = dc_post(q, last) if last > 2 else p2
            row["끝쪽 결과"] = {"요청한 쪽": last, **{k: v for k, v in pl.items() if k != "ids"}}
            row["끝쪽이 1쪽보다 과거인가"] = (
                bool(pl["제일 오래된"] and p1["제일 오래된"]
                     and pl["제일 오래된"] < p1["제일 오래된"]))
            row["끝쪽 최오래 < 2019"] = bool(pl["제일 오래된"] and pl["제일 오래된"] < "2019-01-01")
        except Exception as e:
            row["오류"] = f"{type(e).__name__}:{getattr(e, 'code', '-')}"
        a.append(row)

    olds = [x["끝쪽 결과"]["제일 오래된"] for x in a
            if x.get("끝쪽 결과", {}).get("제일 오래된")]
    deeper = sum(1 for x in a if x.get("끝쪽이 1쪽보다 과거인가"))
    ares = {
        "표본 규칙(고정)": "한글 질의 · 893 디시 항목 ≥ 10 인 작품 중 **t_0 오름차순 5개**. 뽑기 없음 --- 재현 가능.",
        "🔵 구조 관찰(요청 0건 · 1쪽 HTML 에서)": {
            "쪽 파라미터": "`/post/p/{N}/q/{질의}` --- **있다**. 하단 페이징이 `끝` 링크로 마지막 쪽 번호를 준다.",
            "🔴 날짜/기간 파라미터": "게시물 검색 페이지의 정렬·페이징·폼 마크업 어디에도 **없다**. "
                            "정렬은 `sort/accuracy` 하나뿐이고 기간 UI 가 존재하지 않는다.",
            "갤러리 검색 필터": "`stype`(전체/갤/마이너/미니/인물) · `sort`(인기순/가나다순) --- **여기도 기간 없음**",
        },
        "P5 쪽이 실제로 다른 결과를 주는가(자카드 ≤ 0.2)": {
            "자카드": [x.get("1·2쪽 자카드") for x in a],
            "판정": ("적중" if all((x.get("1·2쪽 자카드") is not None and x["1·2쪽 자카드"] <= 0.2)
                                for x in a) else "반증"),
        },
        "P6 깊은 쪽에서도 2019 이전에는 못 닿는다": {
            "끝쪽 제일 오래된": olds, "중앙값": med(olds),
            "예측": "중앙값 ≥ 2023-01-01 (반증: < 2021-01-01)",
            "판정": ("적중" if (med(olds) and med(olds) >= "2023-01-01")
                   else "반증(F3 발화)" if (med(olds) and med(olds) < "2021-01-01")
                   else "구간 안(미달·미반증)"),
            "2019 이전에 닿은 질의 수": sum(1 for x in a if x.get("끝쪽 최오래 < 2019")),
        },
        "P7 날짜 파라미터는 안 먹는다": {
            "판정": "적중(구조 관찰 --- 창 파라미터 자체가 없다)",
            "🔴 정직하게": "창을 **줘 본 것이 아니라** 줄 자리가 없다는 것을 봤다. '창 밖 비율' 은 "
                     "잴 수 있는 물건이 아니었다 --- 반증 조건 F4 는 **발화가 불가능한 형태**였다.",
        },
        "ⓐ 판정 규칙 대조": {"깊은 쪽이 1쪽보다 과거인 질의": f"{deeper}/5", "필요": "≥ 4"},
        "상세": a,
    }
    if only in (None, "all"):
        res["🔴 ⓐ 쪽 파라미터와 과거 도달"] = ares

    # ── ⓑ  작품별 전용 갤 존재율
    alias = json.loads((ROOT / "data/state/manga_alias.json").read_text(encoding="utf-8"))
    al = alias["별칭"]
    ko = []
    for k, v in al.items():
        names = [a["값"] for a in v.get("별칭", []) if a.get("표기") == "한글" and a.get("값")]
        if names:
            ko.append({"record_id": k, "국가": v.get("국가"), "시작": v.get("시작"),
                       "질의": names[0]})
    rng2 = random.Random(894)
    b_smp = rng2.sample(ko, 30) if len(ko) >= 30 else ko
    b = []
    for s in (b_smp if only in (None, "all", "b") else []):
        try:
            b.append({**s, **dc_gallery(s["질의"])})
        except Exception as e:
            b.append({**s, "오류": f"{type(e).__name__}:{getattr(e, 'code', '-')}"})
    hit = sum(1 for x in b if x.get("정확일치"))
    dec = [x for x in b if x.get("판정") in ("항목", "확인된 0")]
    tot = [x["정확일치"][0]["총글"] for x in b if x.get("정확일치")]
    bres = {
        "🔴 분모": {"모집단": "만화 7,982 중 **한글 별칭 보유 레코드**", "모집단 크기": len(ko),
                 "표본": len(b_smp), "씨앗": 894, "판정 가능": len(dec),
                 "🔴 일반화 금지": "만화 7,982 로 일반화하면 안 된다 --- 한글 별칭이 없으면 갤 검색을 할 수조차 없다."},
        "정확일치 갤 보유": f"{hit}/{len(dec)}",
        "비율": round(hit / len(dec), 4) if dec else None,
        "부트 95%": boot_ratio(hit, len(dec)),
        "예측": "점 0.25 · 구간 [0.10, 0.45] (반증: 0.00 또는 > 0.60)",
        "정확일치 갤의 총 글 수": {"n": len(tot), "중앙값": med(tot),
                          "최소": min(tot) if tot else None, "최대": max(tot) if tot else None},
        "상세": b,
    }

    # ── ⓒ' 도달 깊이의 정체 --- 🔴 **사후 탐색**(사전등록에 없다)
    #    ⓐ 가 "쪽은 있는데 2019 이전엔 못 닿는다" 를 냈다. 그러면 **무엇이 깊이를 정하는가**.
    #    가설: 검색 상한이 `끝쪽 120 × 25건 = 3,000건` 이고, 총 언급이 그보다 적은 작품은
    #    **검색만으로 전량 도달**한다. 즉 도달 한계는 원천의 성질이 아니라 **작품의 밀도**다.
    #    1작품당 **1요청**(1쪽의 `끝` 링크가 마지막 쪽 번호를 준다)으로 잰다.
    if only == "c":
        res.update({k: v for k, v in prev.items() if k.startswith(("배선", "🔴"))})
        used = {x["질의"] for x in prev["🔴 ⓐ 쪽 파라미터와 과거 도달"]["상세"]}
        pool = [c for c in cand if c["질의"] not in used]
        pool.sort(key=lambda x: (x["층"], x["질의"]))
        rng3 = random.Random(894)
        pick = rng3.sample(pool, 7)
        depth = []
        for s2 in pick:
            try:
                p1 = dc_post(s2["질의"], 1)
                depth.append({**s2, "끝쪽": p1["끝쪽"], "1쪽 항목": p1["항목"],
                              "1쪽 제일 오래된": p1["제일 오래된"],
                              "검색 상한 추정(건)": (p1["끝쪽"] or 1) * 25})
            except Exception as e:
                depth.append({**s2, "오류": f"{type(e).__name__}:{getattr(e, 'code', '-')}"})
        try:
            over = dc_post(pick[0]["질의"], 130)
            cap = {"질의": pick[0]["질의"], "요청한 쪽": 130,
                   "항목": over["항목"], "제일 오래된": over["제일 오래된"],
                   "판정": over["판정"]}
        except Exception as e:
            cap = {"오류": f"{type(e).__name__}:{getattr(e, 'code', '-')}"}
        prior = prev["🔴 ⓐ 쪽 파라미터와 과거 도달"]["상세"]
        allend = ([x["1쪽"]["끝쪽"] for x in prior if x.get("1쪽", {}).get("끝쪽")]
                  + [x["끝쪽"] for x in depth if x.get("끝쪽")])
        res["🔴 ⓒ' 도달 깊이는 무엇이 정하는가(사후 탐색)"] = {
            "🔴 이것은 사후 탐색이다": "사전등록에 없다. 예측도 반증 조건도 안 걸었다 --- 설계 재료로만 쓴다.",
            "표본": {"규칙": "ⓐ 표본 5를 뺀 나머지 한글질의·디시≥10 작품에서 씨앗 894 로 7개",
                   "n": len(depth), "ⓐ 5 를 합친 끝쪽 분포 n": len(allend)},
            "끝쪽 분포": sorted(allend),
            "끝쪽 = 120(상한에 붙음)": sum(1 for x in allend if x >= 120),
            "끝쪽 < 120(검색이 전량을 소진)": sum(1 for x in allend if x < 120),
            "상한 검증(쪽 130 요청)": cap,
            "상세": depth,
        }
        REQ["n"] += prev.get("요청 회계", {}).get("총", 0) - PRE_USED
        for k, v in prev.get("요청 회계", {}).get("태그별", {}).items():
            REQ["by"][k] += v

    if only == "b":
        REQ["n"] += prev.get("요청 회계", {}).get("총", 0) - PRE_USED
        for k, v in prev.get("요청 회계", {}).get("태그별", {}).items():
            REQ["by"][k] += v
    res["🔴 요청 회계 --- F6 이 발화했다(자가 적발)"] = {
        "실제로 디시에 간 요청": 125, "사전등록 예산": BUDGET, "초과": 25,
        "🔴 F6 발화": True,
        "서로 다른 URL": len(list(RAW.glob("*.html"))),
        "무엇이 초과를 만들었나": (
            "`only == 'c'` 로 세 번째 조각만 돌리려 했는데 **P4·ⓐ 블록의 모드 가드를 "
            "`!= \"b\"` 로만 걸어** 두 블록이 통째로 다시 돌았다(P4 12 + ⓐ 15 = 27건이 "
            "**같은 URL 재요청**). 모드 가드를 손으로 세 군데 적었고 한 군데를 빠뜨렸다. "
            "초과 25 = 재요청 27 + 신규 8(도달 깊이 7 + 클램프 1) + 실패 2 − 캐시 적중 14, 그리고 **고친 코드를 캐시로 재현하려던 마지막 실행이 2건을 더 썼다**(893 에서 `TimeoutError` 로 죽은 요청은 캐시에 안 남아 다시 갔다 --- 실패도 캐시에 적어야 한다는 `fanout.py` 설계 규칙 ②를 이 스크립트가 안 지켰다)."),
        "🔴 무엇이 무효인가": (
            "사전등록 F6 은 *'요청 총량이 100건을 넘으면 이 사이클의 노크는 규약 위반으로 "
            "자가 무효'* 다. **규칙대로 이 노크에는 「규약 위반」 표시를 붙인다.** 다만 "
            "무효인 것은 **예의 계약**이지 수치가 아니다 --- 초과분의 대부분(27/33)이 "
            "**이미 받은 URL 의 재요청**이라 새로 건드린 표면은 8건뿐이고, 답들은 "
            "`data/state/cache_k894`(서로 다른 URL 63건)에 있어 **다음 세션이 요청 0건으로 "
            "전량 재현**할 수 있다. 값을 살리려고 규칙을 다시 읽지 않는다 --- 어긴 것은 어겼다."),
        "고침": "모드 가드를 `only in (None, 'all', …)` 화이트리스트로 바꿨다(부정 조건은 빠뜨리기 쉽다).",
        "태그별(이번 실행)": dict(REQ["by"]), "실패": dict(REQ["fail"]),
        "이번 실행의 신규 요청": REQ["n"] - PRE_USED, "초": round(time.time() - t0, 1)}
    # ── 종합(요청 0건 · 위 칸들에서만 접는다)
    for k, v in prev.items():
        res.setdefault(k, v)
    A = res.get("🔴 ⓐ 쪽 파라미터와 과거 도달", {}).get("상세", [])
    C = res.get("🔴 ⓒ' 도달 깊이는 무엇이 정하는가(사후 탐색)", {}).get("상세", [])
    works = ([{"질의": x["질의"], "층": x["층"], "t_0": x["t_0"],
               "끝쪽": x.get("1쪽", {}).get("끝쪽"), "1쪽 항목": x.get("1쪽", {}).get("항목"),
               "확인한 제일 오래된": x.get("끝쪽 결과", {}).get("제일 오래된")} for x in A]
             + [{"질의": x["질의"], "층": x["층"], "t_0": x["t_0"], "끝쪽": x.get("끝쪽"),
                 "1쪽 항목": x.get("1쪽 항목"), "확인한 제일 오래된": x.get("1쪽 제일 오래된")}
                for x in C])
    dec = [w for w in works if w["1쪽 항목"]]
    cap = [w for w in dec if w["끝쪽"] == 120]
    exh = [w for w in dec if w["끝쪽"] != 120]
    olds = sorted(w["확인한 제일 오래된"] for w in dec if w["확인한 제일 오래된"])
    res["🔴 종합 --- 도달 깊이를 무엇이 정하는가(요청 0건 · 사후)"] = {
        "표본": {"두드린 작품": len(works), "판정 가능(1쪽에 항목 있음)": len(dec),
               "확인된 0": len(works) - len(dec)},
        "🔴 검색의 상한": "**끝쪽 120 · 쪽당 25건 = 작품당 3,000건**. 쪽 130 을 요청하면 "
                   "서버가 **실제 마지막 쪽으로 클램프**한다(`리블루밍` p=130 → 본문의 현재쪽 "
                   "표시가 `15`). 즉 `끝` 링크는 진짜 끝이고, 넘어서 파는 길이 아니다.",
        "상한에 붙은 작품(끝쪽=120)": {"n": len(cap), "목록": [w["질의"] for w in cap]},
        "검색이 전량을 소진하는 작품(끝쪽<120 또는 페이징 없음)":
            {"n": len(exh), "목록": [(w["질의"], w["끝쪽"]) for w in exh]},
        "🔴 창의 폭은 인기의 함수다(상한에 붙은 작품)": {
            w["질의"]: {"1쪽": next((x["1쪽"]["제일 최신"] for x in A if x["질의"] == w["질의"]), None),
                      "120쪽": w["확인한 제일 오래된"]} for w in cap
            if any(x["질의"] == w["질의"] for x in A)},
        "🔴 색인 바닥 가설(다음 사이클이 검정할 것)":
            {"관측한 제일 오래된 시각": olds[:5],
             "893 캐시 3,758항목의 최솟값": "2019-06-26",
             "894 노크에서 새로 본 최솟값": "2019-06-09(`리블루밍` 마지막 쪽)",
             "🔴 왜 가설인가": "두 번의 독립한 뽑기가 **둘 다 2019-06 에서 바닥을 친다**. "
                        "`t_0 < 2019` 인 작품이 표본에 116개 있는데 2019 이전 항목이 "
                        "**하나도 없다**. 색인 바닥이 아니라면 우연이 너무 크다 --- 그러나 "
                        "**아직 안 쟀다**. 검정: 끝쪽 < 120 이고 `t_0 < 2015` 인 작품의 "
                        "**진짜 마지막 쪽**을 받아 최솟값이 또 2019-06 이면 바닥이다(요청 ~10건)."},
    }
    res.pop("요청 회계", None)

    # 이번 실행이 안 돈 칸은 **이전 산출물에서 그대로 이어받는다**(조각 실행 지원).
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k.startswith("🔴") or k == "요청 회계"},
                     ensure_ascii=False, indent=1)[:6000], flush=True)


if __name__ == "__main__":
    main()
