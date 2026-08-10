# -*- coding: utf-8 -*-
"""노트 895 · 2~3단계 --- **자 후보 셋을 재는 자**. 사전등록은 `docs/prereg_895_textmass.md` v3.

🔴 **이 파일이 지키는 것 셋(894 가 어긴 것들)**

  ① **회계를 손으로 안 적는다.** 라이브 요청은 전부 `_get()` 을 지나고 그때마다
     `runners/out895_reqlog.jsonl` 에 **한 줄**이 쌓인다. 총계는 `wc -l` 이다.
  ② **실행 가드가 긍정 조건이다.** 조각마다 `runners/.done895_<조각>` 표시 파일을
     만들고 **있으면 건너뛴다**(894 는 부정 조건으로만 걸어 27건을 재요청했다).
  ③ **양성 통제 없이 점수를 안 매긴다.** 원천마다 알려진 양성을 먼저 치고,
     0 이면 그 자는 **전부 판정 불가**로 적는다(F4). 파싱 실패는 **결측**이지 0 이 아니다.

쓰는 법::

    python3 runners/ruler895.py control      # 양성 통제만 (원천당 2요청)
    python3 runners/ruler895.py r1           # 네이버 오픈API 정확 구문
    python3 runners/ruler895.py r2           # 로컬 베이스 모델 탐침 (요청 0)
    python3 runners/ruler895.py r3           # 문서 존재·본문 길이
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")

ROOT = Path("/Users/ax/world_model")
REQLOG = ROOT / "runners/out895_reqlog.jsonl"
TRUTH = ROOT / "runners/out895_truth.json"
POLITE = 1.2
UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/126.0 Safari/537.36")}


def _env(k: str) -> str | None:
    v = os.environ.get(k)
    if v:
        return v
    p = ROOT / ".env"
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            if ln.strip().startswith(k + "="):
                return ln.split("=", 1)[1].strip().strip('"').strip("'")
    return None


# ── ① 요청 계기 --- 모든 라이브 요청이 여기를 지난다 ────────────────
def _get(url: str, src: str, headers=None, timeout: int = 20) -> dict:
    """반환 {ok, code, bytes, text}. **예외를 삼키지 않고 판정 불가로 옮긴다.**"""
    h = dict(UA)
    h.update(headers or {})
    rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "src": src, "url": url[:300]}
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)
        b = r.read()
        rec.update({"code": r.getcode(), "bytes": len(b), "ok": True})
        out = {"ok": True, "code": r.getcode(), "bytes": len(b),
               "text": b.decode("utf-8", "ignore")}
    except Exception as e:
        code = getattr(e, "code", None)
        rec.update({"code": code, "bytes": 0, "ok": False,
                    "err": f"{type(e).__name__}: {e}"[:200]})
        out = {"ok": False, "code": code, "bytes": 0, "text": "",
               "err": f"{type(e).__name__}: {e}"[:200]}
    with REQLOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    time.sleep(POLITE)
    return out


def n_requests() -> int:
    """🔴 손으로 세지 않는다."""
    return sum(1 for _ in REQLOG.open(encoding="utf-8")) if REQLOG.exists() else 0


# ── ② 실행 가드 --- **긍정 조건** ────────────────────────────────
def done(tag: str) -> bool:
    return (ROOT / f"runners/.done895_{tag}").exists()


def mark(tag: str, info: dict) -> None:
    (ROOT / f"runners/.done895_{tag}").write_text(
        json.dumps(info, ensure_ascii=False), encoding="utf-8")


def guard(tag: str):
    """조각을 한 번만 돌린다. 이미 돌았으면 표시 파일 내용을 돌려준다."""
    if done(tag):
        print(f"[가드] {tag} 는 이미 돌았다 --- 건너뛴다 "
              f"({(ROOT / f'runners/.done895_{tag}').read_text(encoding='utf-8')[:120]})")
        return True
    return False


# ── 자 후보 ─────────────────────────────────────────────────────
NAVER_OPENAPI = "https://openapi.naver.com/v1/search/{svc}.json?query={q}&display=1"


#: 🔴 규모 측정은 **news 만** 쓴다. 이유는 양성 통제 --- `blog` 는 체인소맨에 **0** 을
#: 주는데 귀멸의 칼날에는 359,862 를 준다(같은 호출·같은 키). 즉 blog 채널은 **작품마다
#: 조용히 0 을 낼 수 있고**, 그 0 은 '확인된 0' 과 구별이 안 된다(조항 59). F4 대로
#: **blog 는 이 사이클에서 판정 불가**로 적고 점수를 안 매긴다.
R1_SVCS = ("news",)


def r1_naver(phrase: str, svcs=R1_SVCS) -> dict:
    """정확 구문 검색 **총량**. 🔴 웹 검색이 아니라 `openapi.naver.com` 이다(다른 채널).

    반환 {상태, total, 사유}. 상태는 **잼 / 판정 불가** 둘 --- 0 도 값이지만
    호출자가 양성 통제를 통과했을 때만 값으로 쓴다.
    """
    cid, sec = _env("NAVER_SEARCH_ID"), _env("NAVER_SEARCH_SECRET")
    if not (cid and sec):
        return {"상태": "판정 불가", "사유": "키 없음", "total": None}
    tot, detail = 0, {}
    for svc in svcs:
        q = urllib.parse.quote(f'"{phrase}"')
        r = _get(NAVER_OPENAPI.format(svc=svc, q=q), f"naver_openapi_{svc}",
                 headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": sec})
        if not r["ok"]:
            detail[svc] = {"판정 불가": r.get("err"), "code": r.get("code")}
            continue
        try:
            d = json.loads(r["text"])
        except Exception as e:
            detail[svc] = {"판정 불가": f"JSON 실패: {e}"[:120]}
            continue
        if "total" not in d:
            detail[svc] = {"판정 불가": f"total 없음: {str(d)[:120]}"}
            continue
        detail[svc] = {"total": d["total"]}
        tot += int(d["total"])
    ok = [k for k, v in detail.items() if "total" in v]
    if not ok:
        return {"상태": "판정 불가", "사유": detail, "total": None}
    return {"상태": "잼", "total": tot, "상세": detail,
            "부분": None if len(ok) == len(svcs) else f"{ok} 만 잼"}


WIKI_API = ("https://ko.wikipedia.org/w/api.php?action=query&list=search"
            "&srsearch={q}&srlimit=1&srprop=size&format=json&utf8=1")
NAMU_URL = "https://namu.wiki/w/{q}"


def _norm(s: str) -> str:
    """제목 대조용 정규화 --- 공백·문장부호를 떼고 소문자로."""
    return "".join(ch for ch in str(s).lower() if ch.isalnum())


def r3_wiki(phrase: str) -> dict:
    """ko.wikipedia --- **제목이 맞을 때만** 1위 문서 바이트를 값으로 준다.

    🔴 배선 검사가 잡은 것: `list=search` 의 `totalhits` 는 **전문 OR 검색의 잡음**이다.
    양성 통제에서 체인소맨 4,183 > 귀멸의 칼날 260 으로 **순서가 뒤집혔고**, 음성
    질의 '주인공의 춤추고' 가 412건에 1위 문서가 「너의 이름은.」(63KB)이었다.
    총건수를 그대로 쓰면 **정답지가 앓던 어절 잡음병을 자가 그대로 앓는다.**
    → 1위 문서의 **정규화 제목이 질의와 같을 때만** 그 바이트를 값으로 쓰고,
    아니면 **0**(문서 없음)이다. 총건수는 진단용으로만 남긴다.
    """
    # 🔴 위키미디어는 **일반 브라우저 UA** 에 429 를 준다(초판 84요청 중 52가 429).
    # 정책대로 **연락처가 든 서술형 UA** 를 쓴다. 429 는 그대로 판정 불가다.
    r = _get(WIKI_API.format(q=urllib.parse.quote(phrase)), "kowiki",
             headers={"User-Agent": "world-model-lab/895 (research; alexlee@sweetspot.co.kr)"},
             )
    if not r["ok"]:
        return {"상태": "판정 불가", "사유": r.get("err"), "code": r.get("code")}
    try:
        d = json.loads(r["text"])
        si = d["query"]["searchinfo"]["totalhits"]
        hits = d["query"]["search"]
    except Exception as e:
        return {"상태": "판정 불가", "사유": f"파싱 실패: {e}"[:140]}
    top = hits[0] if hits else None
    hit = bool(top and _norm(top.get("title")) == _norm(phrase))
    return {"상태": "잼", "총건수(진단용)": si,
            "1위 제목": (top.get("title") if top else None),
            "제목 일치": hit,
            "바이트": (top.get("size", 0) if hit else 0)}


def r3_namu(phrase: str) -> dict:
    """나무위키 --- 문서 존재와 원본 바이트.

    🔴 배선 검사가 잡은 것: 나무위키는 **없는 문서에 HTTP 404** 를 준다. 초판은
    그 404 를 `_get` 의 실패로 받아 **판정 불가**로 옮겼다 --- **확인된 0 을 '모른다'
    로 강등하는 것**(894 가 디시에서 고친 바로 그 병의 재발). 그래서 404 만 따로
    **확인된 0** 으로 받고 나머지 상태 코드(403·429·망 예외)는 판정 불가로 둔다.

    ⚠ 한계: 나무위키 URL 은 **정확 제목**이라 404 는 *'문서가 없다'* 와
    *'우리가 가진 이름이 나무위키 표제어와 다르다'* 를 못 가른다. 병기한다.
    """
    r = _get(NAMU_URL.format(q=urllib.parse.quote(phrase)), "namu")
    if r["ok"]:
        return {"상태": "잼", "존재": True, "바이트": r["bytes"], "code": r["code"]}
    if r.get("code") == 404:
        return {"상태": "잼", "존재": False, "바이트": 0, "code": 404,
                "⚠": "404 = 문서 없음 **또는** 표제어 불일치"}
    return {"상태": "판정 불가", "사유": r.get("err"), "code": r.get("code")}


R2_PROMPT = ("아래는 어떤 만화/작품의 제목일 수 있는 문자열이다. 너는 이 작품을 아는가?\n"
             "제목: {q}\n\n"
             "규칙: 안다면 첫 줄에 '안다' 만 쓰고 둘째 줄에 그 작품을 한 문장으로 설명하라. "
             "모르거나 실재하지 않는 것 같으면 첫 줄에 '모름' 만 써라. "
             "추측해서 지어내지 마라.")


def r2_probe(phrase: str) -> dict:
    """베이스 모델 탐침. **요청 0건**(로컬 ollama). 안다 / 모름 / **판정 불가** 셋."""
    from core.probe import ask
    r = ask(R2_PROMPT.format(q=phrase), num_predict=120)
    if not r["쓸만한가"]:
        return {"상태": "판정 불가", "사유": r["사유"]}
    head = r["본문"].strip().splitlines()[0].strip()
    if head.startswith("모름") or "모름" in head[:6]:
        return {"상태": "잼", "안다": 0, "본문": r["본문"][:200]}
    if head.startswith("안다") or "안다" in head[:6]:
        return {"상태": "잼", "안다": 1, "본문": r["본문"][:200]}
    return {"상태": "판정 불가", "사유": f"첫 줄이 셋 중 어느 것도 아니다: {head[:60]!r}"}


# ── 양성 통제 ───────────────────────────────────────────────────
POS = ["체인소맨", "귀멸의 칼날"]          # 알려진 양성(한국어 텍스트가 확실히 두껍다)
NEG_KNOWN = "주인공의 춤추고"               # 음성 통제 질의 하나(FAKE-00)


def controls() -> dict:
    """원천마다 양성 2 + 항등 통제. 🔴 **여기서 0 이면 그 자는 점수를 안 매긴다.**"""
    out = {"양성 질의": POS, "음성 예시": NEG_KNOWN}
    out["R1 · 네이버 오픈API(blog+news 둘 다 · 통제에서만)"] = {
        q: r1_naver(q, ("blog", "news")) for q in POS}
    out["R1 · 음성 예시"] = r1_naver(NEG_KNOWN, ("blog", "news"))
    out["R3 · ko.wikipedia"] = {q: r3_wiki(q) for q in POS}
    out["R3 · 나무위키"] = {q: r3_namu(q) for q in POS}
    out["R2 · 베이스 모델(요청 0)"] = {q: r2_probe(q) for q in POS}
    out["R2 · 음성 예시"] = r2_probe(NEG_KNOWN)
    return out


# ── 채점 모집단 ─────────────────────────────────────────────────
def population() -> list[dict]:
    """🔴 정본 채점 모집단 --- 한글 질의 실물 + 음성 20. 사전등록 그대로."""
    d = json.loads(TRUTH.read_text(encoding="utf-8"))
    KO = ("AniList native(한글)", "AniList synonyms(한글)")
    return [w for w in d["작품"] if w["음성"] or w["질의출처"] in KO]


def measure(tag: str, fn, key: str) -> None:
    if guard(tag):
        return
    pop = json.loads(TRUTH.read_text(encoding="utf-8"))["작품"] if tag == "r2full" else population()
    res = {}
    for i, w in enumerate(pop):
        res[w["key"]] = fn(w["질의"])
        if i % 10 == 0:
            print(f"  {tag} {i}/{len(pop)} 요청누계={n_requests()}", flush=True)
    p = ROOT / f"runners/out895_{key}.json"
    p.write_text(json.dumps({"자": tag, "n": len(res), "요청 누계": n_requests(),
                             "값": res}, ensure_ascii=False, indent=1), encoding="utf-8")
    mark(tag, {"n": len(res), "요청 누계": n_requests(), "산출물": p.name})
    print(f"[완료] {tag} n={len(res)} 요청누계={n_requests()}")


def controls2() -> dict:
    """🔴 **수리한 코드로 다시 치는 통제**(티처 #57 M8 --- 수리 효과를 수리된 코드로 재라).

    r3 둘의 정의가 배선 검사 때문에 바뀌었다(위키 제목 대조 · 나무 404=확인된 0).
    그러니 통제도 **출하될 함수 그대로** 다시 친다. 4요청.
    """
    return {"R3 · ko.wikipedia(제목 대조판)": {q: r3_wiki(q) for q in POS + [NEG_KNOWN]},
            "R3 · 나무위키(404=확인된 0 판)": {q: r3_namu(q) for q in POS + [NEG_KNOWN]}}


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "control"
    if what == "control":
        if guard("control"):
            return
        c = controls()
        p = ROOT / "runners/out895_control.json"
        p.write_text(json.dumps({"요청 누계": n_requests(), "통제": c},
                                ensure_ascii=False, indent=1), encoding="utf-8")
        mark("control", {"요청 누계": n_requests()})
        print(json.dumps(c, ensure_ascii=False, indent=1))
    elif what == "control2":
        if guard("control2"):
            return
        c = controls2()
        (ROOT / "runners/out895_control2.json").write_text(
            json.dumps({"요청 누계": n_requests(), "통제": c}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        mark("control2", {"요청 누계": n_requests()})
        print(json.dumps(c, ensure_ascii=False, indent=1))
    elif what == "r1":
        measure("r1", r1_naver, "r1")
    elif what == "r2":
        measure("r2", r2_probe, "r2")
    elif what == "r3":
        measure("r3", r3_wiki, "r3wiki")
    elif what == "r3retry":
        # 🔴 **판정 불가만** 다시 친다. 잰 것은 다시 안 친다(요청을 아끼고 캐시를 안 흔든다).
        if guard("r3retry"):
            return
        global POLITE
        POLITE = 2.5
        p = ROOT / "runners/out895_r3wiki.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        todo = [k for k, v in d["값"].items() if v["상태"] == "판정 불가"]
        pop = {w["key"]: w["질의"] for w in population()}
        print(f"재시도 대상 {len(todo)}건")
        for i, k in enumerate(todo):
            d["값"][k] = r3_wiki(pop[k])
            if i % 10 == 0:
                print(f"  재시도 {i}/{len(todo)} 요청누계={n_requests()}", flush=True)
        d["재시도"] = {"대상": len(todo), "요청 누계": n_requests(),
                    "남은 판정 불가": sum(1 for v in d["값"].values() if v["상태"] == "판정 불가")}
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        mark("r3retry", d["재시도"])
        print(json.dumps(d["재시도"], ensure_ascii=False))
    elif what == "r3namu":
        measure("r3namu", r3_namu, "r3namu")
    elif what == "r2full":
        measure("r2full", r2_probe, "r2full")
    else:
        raise SystemExit(f"모르는 조각: {what}")
    print(f"🔴 총 요청(세어서) = {n_requests()}")


if __name__ == "__main__":
    main()
