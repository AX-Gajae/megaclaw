# -*- coding: utf-8 -*-
"""온보딩 1006 — 드라마 원천 확보(무료 위키 API 만 · 사전등록 docs/탐색/1006.md §2 에서 얼었다).

🔴 누수 원리 차단: `exp/onboard1006/DONE_TRAIN`(B-앙상블 학습 완료 스탬프)이 없으면
   시작을 거부한다 — 드라마 자료는 학습 «뒤»에만 세상에 들어온다(§3).

원천(전례 `ingest/wikidaily941.py` 규약 승계 — UA 연락처 · 요청 간격 1.1초):
  ① 명단  ko.wikipedia api.php categorymembers —
          분류:2025년 텔레비전 드라마 ∪ 분류:2026년 텔레비전 드라마 (ns=0)
  ② 곡선  wikimedia.org REST pageviews per-article ko.wikipedia daily 20241001~20260818
  ③ 텍스트 ko.wikipedia REST page/summary

조항 59 — 실패 3형: 「없다」(200 인데 items 비었거나 404 data-not-found) ·
「못 봤다」(60 컷으로 조회 자체를 안 한 후보 — 수를 센다) ·
「못 읽었다」(망 오류·5xx·파싱 실패·검사 ㄱ~ㅂ 위반 — 사유를 값으로 적는다).

쓰는 법:  python3 runners/onboard1006_fetch.py
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ART = "/Users/ax/wm_harvest/foundation"
EXP = os.path.join(ART, "exp", "onboard1006")
DRAMA = os.path.join(ART, "onboard_drama")
REPO = "/Users/ax/world_model"
UA = ("sweetspot-world-model/1.0 (research; alexlee@sweetspot.co.kr) "
      "note1006 onboarding")
SLEEP = 1.1
CATS = ["분류:2025년 텔레비전 드라마", "분류:2026년 텔레비전 드라마"]
PV = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
      "ko.wikipedia/all-access/all-agents/{title}/daily/20241001/20260818")
SUMM = "https://ko.wikipedia.org/api/rest_v1/page/summary/{title}"
CAP = 60


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def api(params):
    return http_json("https://ko.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params))


def cat_members(cat):
    out, cont = [], {}
    while True:
        p = {"action": "query", "format": "json", "list": "categorymembers",
             "cmtitle": cat, "cmnamespace": "0", "cmlimit": "500", "cmtype": "page"}
        p.update(cont)
        d = api(p)
        out += [(m["title"], m["pageid"]) for m in d["query"]["categorymembers"]]
        time.sleep(SLEEP)
        if "continue" not in d:
            return out
        cont = d["continue"]


def page_categories(titles):
    """제목 리스트(≤50) → {제목: [분류...]} — 범용 continue 루프."""
    acc = {t: [] for t in titles}
    cont = {}
    while True:
        p = {"action": "query", "format": "json", "prop": "categories",
             "titles": "|".join(titles), "cllimit": "500"}
        p.update(cont)
        d = api(p)
        for pg in d["query"]["pages"].values():
            t = pg.get("title")
            if t in acc:
                acc[t] += [c["title"] for c in pg.get("categories", [])]
        time.sleep(SLEEP)
        if "continue" not in d:
            return acc
        cont = d["continue"]


def check_pv(d):
    """조항 59 검사 ㄱ~ㅂ (wikidaily941 자구 승계). 통과 못 하면 사유 문자열."""
    if not isinstance(d, dict):
        return "ㄴ JSON 아님"
    if "items" not in d:
        return "ㄷ items 없음"
    if len(d["items"]) < 1:
        return "ㄹ 항목 0"
    ts = [it.get("timestamp", "") for it in d["items"]]
    if ts != sorted(ts):
        return "ㅁ 날짜 비오름차순"
    for it in d["items"]:
        v = it.get("views")
        if not isinstance(v, int) or v < 0:
            return "ㅂ views 비정수/음수"
    return None


def main():
    assert os.path.exists(os.path.join(EXP, "DONE_TRAIN")), \
        "🔴 DONE_TRAIN 없음 — B-앙상블 학습이 먼저다(사전등록 §3 · 누수 원리 차단)"
    os.makedirs(os.path.join(DRAMA, "raw"), exist_ok=True)
    t0 = time.time()
    log = {"수집 시작": time.strftime("%Y-%m-%dT%H:%M:%S")}

    # ① 명단
    members = {}
    percat = {}
    for c in CATS:
        ms = cat_members(c)
        percat[c] = len(ms)
        for t, pid in ms:
            members.setdefault(t, {"pageid": pid, "분류원천": []})
            members[t]["분류원천"].append(c)
    titles = sorted(members)
    log["후보(합집합)"] = len(titles)
    log["분류별"] = percat

    # 문서 분류(배치 50)
    cats_of = {}
    for i in range(0, len(titles), 50):
        cats_of.update(page_categories(titles[i:i + 50]))

    # ② 선정 규칙(§2 — 결정론 · 인기 비의존)
    kept, excluded = [], {}
    for t in titles:
        cs = cats_of.get(t, [])
        if "목록" in t:
            excluded[t] = "제목에 목록"
        elif any("동음이의" in c for c in cs):
            excluded[t] = "동음이의"
        elif not any("대한민국" in c for c in cs):
            excluded[t] = "대한민국 분류 없음(비한국)"
        else:
            kept.append(t)
    log["선정 전"] = len(kept)
    kept_hash = sorted(kept, key=lambda t: hashlib.md5(t.encode("utf-8")).hexdigest())
    selected = kept_hash[:CAP]
    n_unseen = max(0, len(kept) - CAP)          # 「못 봤다」
    log["선정(60 컷)"] = len(selected)
    log["못 봤다(컷)"] = n_unseen

    # ③ 곡선 + 텍스트
    entities, fail = [], {"없다": [], "못 읽었다": []}
    H = ""
    for t in sorted(selected):
        pid = members[t]["pageid"]
        ent = {"제목": t, "pageid": pid, "분류원천": members[t]["분류원천"],
               "종영": any("종료한" in c for c in cats_of.get(t, []))}
        q = urllib.parse.quote(t.replace(" ", "_"), safe="")
        pv_url = PV.format(title=q)
        try:
            time.sleep(SLEEP)
            pv = http_json(pv_url)
            why = check_pv(pv)
            if why == "ㄹ 항목 0":
                ent["실패"] = "없다(항목 0)"
                fail["없다"].append({t: "항목 0"})
            elif why:
                ent["실패"] = "못 읽었다(%s)" % why
                fail["못 읽었다"].append({t: why})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                ent["실패"] = "없다(404 원천 무자료)"
                fail["없다"].append({t: "404"})
            else:
                ent["실패"] = "못 읽었다(HTTP %d)" % e.code
                fail["못 읽었다"].append({t: "HTTP %d" % e.code})
            pv = None
        except Exception as e:
            ent["실패"] = "못 읽었다(%s)" % type(e).__name__
            fail["못 읽었다"].append({t: type(e).__name__})
            pv = None
        summ, summ_url = "", SUMM.format(title=q)
        if not ent.get("실패"):
            try:
                time.sleep(SLEEP)
                sd = http_json(summ_url)
                summ = sd.get("extract", "") or ""
            except Exception as e:
                summ = ""
                ent["요약실패"] = type(e).__name__       # 텍스트만 실패 — 개체는 산다(제목 대체)
            items = pv["items"]
            first, last = items[0]["timestamp"][:8], items[-1]["timestamp"][:8]
            tot = sum(int(it["views"]) for it in items)
            ent.update({"첫날": first, "끝날": last, "항목수": len(items), "총조회": tot})
            H = max(H, last)
            raw = {"제목": t, "pageid": pid, "분류": cats_of.get(t, []),
                   "분류원천": members[t]["분류원천"], "종영": ent["종영"],
                   "pageviews": pv, "pv출처": pv_url,
                   "요약": summ, "요약출처": summ_url,
                   "수집시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
            rp = os.path.join(DRAMA, "raw", "%s.json" % pid)
            with open(rp, "w", encoding="utf-8") as f:
                json.dump(raw, f, ensure_ascii=False)
            ent["raw sha"] = sha16(rp)
        entities.append(ent)
        print("[fetch]", t, ent.get("실패", "ok %s~%s" % (ent.get("첫날"), ent.get("끝날"))),
              flush=True)

    hv = {"사전등록": "docs/탐색/1006.md §2", "러너 자신": sha16(os.path.abspath(__file__)),
          "UA": UA, "요청 간격(초)": SLEEP, "분류": CATS, "선정 규칙": "md5(제목) 정렬 상위 60",
          "H(원천 지평 · 최신 관측일)": H, "로그": log,
          "실패 3형(조항 59)": {"없다": fail["없다"], "못 봤다(컷 수)": n_unseen,
                            "못 읽었다": fail["못 읽었다"]},
          "제외(선정 전)": excluded, "개체": entities,
          "초": round(time.time() - t0, 1),
          "끝 시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    with open(os.path.join(DRAMA, "harvest.json"), "w", encoding="utf-8") as f:
        json.dump(hv, f, ensure_ascii=False, indent=1)

    ok_n = sum(1 for e in entities if not e.get("실패"))
    out = {"러너 자신": hv["러너 자신"], "사전등록": "docs/탐색/1006.md §2",
           "표A 수집(7칸)": {"후보 수": len(titles), "선정 수": len(selected),
                         "성공 수집": ok_n,
                         "없다": len(fail["없다"]), "못 봤다(컷)": n_unseen,
                         "못 읽었다": len(fail["못 읽었다"]),
                         "제외(선정 전 규칙)": len(excluded)},
           "H": H, "harvest.json sha": sha16(os.path.join(DRAMA, "harvest.json")),
           "개체 요약": [{"제목": e["제목"], "종영": e.get("종영"),
                      "첫날": e.get("첫날"), "끝날": e.get("끝날"),
                      "총조회": e.get("총조회"), "실패": e.get("실패")}
                     for e in entities]}
    with open(os.path.join(REPO, "runners/out1006_fetch.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("표A 수집(7칸)", "H")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
