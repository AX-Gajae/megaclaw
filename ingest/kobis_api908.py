"""KOBIS **공식 오픈API** 상세 수집 — 노트 908 팔 ㄹ.

**왜 새 파일인가.** `ingest/kobis.py` 는 키 없는 **웹 검색 폼**(일별 박스오피스
표)이라 `movieCd` 를 못 받는다. 이 모듈은 KOFIC 오픈API
(`kobisopenapi.kofic.or.kr`)를 쓴다 — **무료 키 · 일 3,000회**.
🔴 `ingest/kobis.py` 는 **안 고쳤다**(읽기만).

🔴 **키는 코드에 없다.** `.env` 의 `KOBIS_API_KEY` 에서만 읽고,
저장·로그·산출물에는 **절대 안 적는다**(URL 은 언제나 `key=***` 로 가린다).

🔴 **조항 59** — KOBIS 는 키가 틀려도 **HTTP 200** 에
`{"faultInfo":{...}}` 를 담아 준다. 그러므로 이 모듈은
`(HTTP 200 · 종료 0 · 빈 응답)` 을 성공으로 읽지 않는다:

    ㄱ HTTP 상태 == 200
    ㄴ 본문이 JSON 으로 파싱된다
    ㄷ `faultInfo` 키가 **없다**
    ㄹ 기대 최상위 키가 **있다**(`movieListResult` / `movieInfoResult`)
    ㅁ 응답 본문의 sha256 을 남긴다 — 「못 읽었다」와 「없다」를 가르기 위해

🔴 `timeout` 명령을 안 쓴다(이 환경에 없다). 제한은 **파이썬 안**이다
(소켓 타임아웃 + 벽시계 예산).

돌리기:
    python3 -m ingest.kobis_api908 --selftest      # 호출 2회로 문 확인
    python3 -m ingest.kobis_api908 --run           # 전량 수집 → runners/out908d_kobis.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data/ingest/kobis"
#: 🔴 **호스트 주의.** 문서가 흔히 적는 `kobisopenapi.kofic.or.kr` 은 **DNS 가 안 뜬다**
#: (2026-08-11 실측 — `gaierror`). 실제로 응답하는 것은 `www.kobis.or.kr` 아래의
#: 같은 경로다. 「없다」가 아니라 **「그 이름으로는 못 찾았다」**다(조항 59).
BASE = "https://www.kobis.or.kr/kobisopenapi/webservice/rest"
LIST_URL = f"{BASE}/movie/searchMovieList.json"
INFO_URL = f"{BASE}/movie/searchMovieInfo.json"

SLEEP = 0.8          # 예의 간격(초)
SOCK_TIMEOUT = 25    # 소켓 타임아웃(초)
RETRY = 2            # 재시도 횟수
DAILY_CAP = 3000     # KOFIC 무료 한도 — 이 모듈은 절대 안 넘긴다

#: 🔴 원천·자물쇠. 분모를 여기서 **직접 센다**(인용하지 않는다).
D1_PATH = ROOT / "data/ingest/kobis/axes_raw_897.jsonl"
AXES_PATH = ROOT / "data/state/kobis_axes.json"
HOLDOUT_T = 2025.0   # 902 의 D3 되짚기가 쓴 시간 분할(post=True · T=2025.0)


# ── 키 ────────────────────────────────────────────────────────────────
def _load_key() -> str:
    """`.env` 에서만 읽는다. 🔴 반환값을 **절대 인쇄하지 않는다.**"""
    k = os.environ.get("KOBIS_API_KEY", "").strip()
    if not k:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("KOBIS_API_KEY="):
                    k = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not k:
        raise SystemExit("KOBIS_API_KEY 가 없다 — .env 를 확인하라 (🔴 못 읽었다)")
    return k


def _redact(url: str) -> str:
    """URL 에서 키를 지운다. 저장·로그에는 **이것만** 쓴다."""
    return re.sub(r"key=[^&]*", "key=***", url)


# ── 한 번의 호출 ──────────────────────────────────────────────────────
class Counter:
    """실제 호출 수를 센다 — 산출물에 찍기 위해."""

    def __init__(self, cap: int = DAILY_CAP):
        self.calls = 0
        self.http_ok = 0
        self.http_bad = 0
        self.net_err = 0
        self.fault = 0
        self.parse_err = 0
        self.cap = cap

    def spend(self, n: int = 1):
        if self.calls + n > self.cap:
            raise SystemExit(f"일 한도 {self.cap} 초과 직전 — 멈춘다(호출 {self.calls})")
        self.calls += n


def call(url_base: str, params: dict, key: str, ctr: Counter,
         expect: str) -> dict:
    """오픈API 한 번. **성공/실패를 다섯 겹으로 가른다**(조항 59).

    반환: {ok, why, status, sha256, url(가림), json?}
    🔴 `ok=False` 는 언제나 **왜 못 읽었는지**를 `why` 에 담는다.
    """
    q = dict(params)
    q["key"] = key
    url = f"{url_base}?{urllib.parse.urlencode(q, encoding='utf-8')}"
    safe = _redact(url)
    last = None
    for attempt in range(RETRY + 1):
        ctr.spend()
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "world_model/908d (research; read-only)"})
            with urllib.request.urlopen(req, timeout=SOCK_TIMEOUT) as r:
                status = r.status
                raw = r.read()
        except urllib.error.HTTPError as e:            # noqa: PERF203
            status, raw, last = e.code, e.read() or b"", f"HTTPError {e.code}"
        except Exception as e:                          # 네트워크 · 타임아웃
            ctr.net_err += 1
            last = f"{type(e).__name__}: {e}"
            time.sleep(SLEEP * (attempt + 1))
            continue
        sha = hashlib.sha256(raw).hexdigest()
        if status != 200:
            ctr.http_bad += 1
            last = f"HTTP {status}"
            time.sleep(SLEEP * (attempt + 1))
            continue
        ctr.http_ok += 1
        try:
            j = json.loads(raw.decode("utf-8", "replace"))
        except Exception as e:
            ctr.parse_err += 1
            return {"ok": False, "why": f"JSON 파싱 실패: {e}", "status": status,
                    "sha256": sha, "url": safe, "bytes": len(raw)}
        # 🔴 ㄷ — faultInfo 는 HTTP 200 에 실려 온다
        if isinstance(j, dict) and "faultInfo" in j:
            ctr.fault += 1
            return {"ok": False, "why": "faultInfo", "status": status,
                    "sha256": sha, "url": safe, "bytes": len(raw),
                    "faultInfo": j.get("faultInfo")}
        # 🔴 ㄹ — 기대 키의 부재도 실패다(「행 0건」과 모양이 같다)
        if not isinstance(j, dict) or expect not in j:
            return {"ok": False, "why": f"기대 키 `{expect}` 부재", "status": status,
                    "sha256": sha, "url": safe, "bytes": len(raw)}
        return {"ok": True, "why": None, "status": status, "sha256": sha,
                "url": safe, "bytes": len(raw), "json": j}
    return {"ok": False, "why": f"재시도 소진 — {last}", "status": None,
            "sha256": None, "url": safe, "bytes": 0}


# ── 분모 — 🔴 직접 센다 ───────────────────────────────────────────────
def _yearfrac(ds: str) -> float:
    y, m, d = (int(x) for x in ds.split("-"))
    a = _dt.date(y, 1, 1)
    b = _dt.date(y + 1, 1, 1)
    return y + (_dt.date(y, m, d) - a).days / ((b - a).days)


def denominators() -> dict:
    """D1 원천 · D2 축 · D3 판 채점 유보를 **각각** 센다(조항 60 — 딱지를 붙인다)."""
    # 🔴 `splitlines()` 를 쓰면 안 된다 — 유니코드 줄바꿈(  등)에서도 쪼개져
    #    JSONDecodeError 가 난다(2026-08-11 실측). 줄 구분은 `\n` 하나뿐이다.
    d1_rows = [json.loads(l) for l in D1_PATH.read_text(encoding="utf-8").split("\n") if l.strip()]
    axes = json.loads(AXES_PATH.read_text(encoding="utf-8"))
    hold = [k for k, v in axes.items()
            if v.get("release_date") and _yearfrac(v["release_date"]) >= HOLDOUT_T]
    return {
        "D1(원천 레코드 · data/ingest/kobis/axes_raw_897.jsonl)": len(d1_rows),
        "D2(축 파일 키 · data/state/kobis_axes.json)": len(axes),
        "D3(판 채점 유보 · post=True · T=2025.0)": len(hold),
        "_d1_rows": d1_rows,
        "_axes": axes,
        "_hold": hold,
    }


# ── 제목 정규화 ───────────────────────────────────────────────────────
_PUNCT = re.compile(r"[\s:：,，.·・ㆍ!?'\"“”‘’\-–—_()\[\]{}<>《》〈〉/\\|]+")


def norm_title(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("&nbsp;", " ")
    return _PUNCT.sub("", s)


def _nonempty(x) -> bool:
    return x not in (None, "", [], {}) and not (isinstance(x, str) and not x.strip())


def recover(key: str, ctr: Counter) -> int:
    """🔴 897 이 `code` 를 **못 받은** D1 레코드를 오픈API 로 되찾는다.

    897 의 웹 상세 긁기가 `ConnectionResetError`·`코드 미매핑` 으로 **10건**을 놓쳤고,
    그 10건은 축 파일(D2 887)에 **아예 안 들어갔다**(897 - 887 = 10). 그래서 그중
    개봉일이 유보 창(>= 2025-01-01)인 것들은 **유보 406 에도 없다.**
    🔴 이것은 「그런 영화가 없다」가 아니라 **「897 이 못 읽었다」**다(조항 59).

    🔴 이 함수는 **아무것도 안 고친다** — 되찾을 수 있는지만 세서 산출물에 적는다.
    축 파일·판·원장은 주 세션 몫이다.
    """
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rows = [json.loads(l) for l in D1_PATH.read_text(encoding="utf-8").split("\n") if l.strip()]
    miss = [r for r in rows if not r.get("code")]
    f = OUTDIR / f"api908d_recover_{stamp}.jsonl"
    if f.exists():
        raise SystemExit(f"덮어쓰기 금지 — 이미 있다: {f}")
    got, fail = [], []
    with f.open("w", encoding="utf-8") as fh:
        for r in miss:
            title, rd = r.get("제목") or "", r.get("개봉일") or ""
            yr = rd[:4]
            resp = call(LIST_URL, {"movieNm": title, "openStartDt": yr, "openEndDt": yr,
                                   "itemPerPage": "50"}, key, ctr, "movieListResult")
            rec = {"제목": title, "개봉일": rd, "897 이 적은 실패 사유": r.get("⛔"),
                   "ok": resp["ok"], "why": resp["why"], "sha256": resp["sha256"],
                   "url": resp["url"]}
            if resp["ok"]:
                lst = resp["json"]["movieListResult"].get("movieList") or []
                nt = norm_title(title)
                c = [m for m in lst if norm_title(m.get("movieNm", "")) == nt]
                rec["후보 수"], rec["일치 후보"] = len(lst), [m.get("movieCd") for m in c]
                if len(c) == 1:
                    rec["되찾은 movieCd"] = c[0]["movieCd"]
                    got.append({"제목": title, "개봉일": rd, "movieCd": c[0]["movieCd"],
                                "897 실패 사유": r.get("⛔")})
                else:
                    fail.append({"제목": title, "개봉일": rd,
                                 "왜": f"제목 일치 후보 {len(c)}건 — 🔴 못 맞췄다"})
            else:
                fail.append({"제목": title, "개봉일": rd, "왜": f"🔴 못 읽었다 — {resp['why']}"})
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            time.sleep(SLEEP)
    assert len(got) + len(fail) == len(miss), "되찾음+못 되찾음 != 대상"
    in_win = [g for g in got if g["개봉일"] >= "2025-01-01"]
    outp = ROOT / "runners/out908d_kobis.json"
    out = json.loads(outp.read_text(encoding="utf-8"))
    out["사. 🔴 897 이 못 받은 10건을 오픈API 로 되찾았다 — 「없다」가 아니라 「못 읽었다」였다"] = {
        "분모(D1 897 중 code 가 빈 레코드)": len(miss),
        "🔴 D1 897 - D2 887 = 10 과 같나": len(miss) == 897 - 887,
        "되찾았다(movieCd 를 얻었다)": len(got),
        "🔴 못 되찾았다": len(fail),
        "🔴 합 == 분모": len(got) + len(fail) == len(miss),
        "897 이 적은 실패 사유별": {s: sum(1 for r in miss if r.get("⛔") == s)
                          for s in sorted({r.get("⛔") for r in miss})},
        "🔴 그중 유보 창(개봉일 >= 2025-01-01)에 드는 것": len(in_win),
        "🔴 뜻": ("이 행들은 **유보 406 에도 축 887 에도 없다** — 897 의 웹 긁기가 실패해서 "
                "레코드가 통째로 빠졌기 때문이다. 오픈API 로 되찾을 수 있음을 확인했다. "
                "🔴 **분모를 바꾸는 일이므로 이 팔은 축 파일·판·원장을 안 건드렸다** — 주 세션 몫이다"),
        "되찾은 것 전량": got,
        "🔴 못 되찾은 것 전량": fail,
        "파일": {"경로": str(f.relative_to(ROOT)), "바이트": f.stat().st_size,
               "sha256[:16]": hashlib.sha256(f.read_bytes()).hexdigest()[:16]},
        "이 절의 호출 수": ctr.calls,
        "faultInfo 건수": ctr.fault,
    }
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["사. 🔴 897 이 못 받은 10건을 오픈API 로 되찾았다 — 「없다」가 아니라 「못 읽었다」였다"],
                     ensure_ascii=False, indent=1))
    return 0


def annex() -> int:
    """🔴 **호출 0회.** 받아 둔 `api908d_movieinfo_*.jsonl` 만 읽어
    「이 열이 유보 몇 행을 **새로** 채우나」를 센다.

    🔴 **판정하지 않는다.** ρ 를 안 돌린다. 「붙는다」까지만 적는다.

    왜 이 절이 필요한가: `data/ingest/kobis/axes_raw_897.jsonl` 은 노트 897 이
    **이미** 장르·국적·등급·배급사·요약(상영시간)을 긁어 두었다. 그래서 오픈API 의
    「채움률 100%」를 곧바로 「새로 열린 열」로 읽으면 **이미 있던 것을 새 것으로 센다**.
    이 절은 그 둘을 가른다: **채움률**과 **순증(새로 채우는 행)**은 다른 수다.
    """
    outp = ROOT / "runners/out908d_kobis.json"
    out = json.loads(outp.read_text(encoding="utf-8"))
    cands = sorted(OUTDIR.glob("api908d_movieinfo_*.jsonl"))
    if not cands:
        raise SystemExit("받아 둔 movieinfo jsonl 이 없다 — 🔴 못 읽었다")
    src = cands[-1]
    detail, det_keys = {}, []
    for line in src.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        r = json.loads(line)
        det_keys.append(r["키"])
        if r.get("ok") and r.get("movieInfo"):
            detail[r["키"]] = r["movieInfo"]

    axes = json.loads(AXES_PATH.read_text(encoding="utf-8"))
    hold = [k for k, v in axes.items()
            if v.get("release_date") and _yearfrac(v["release_date"]) >= HOLDOUT_T]
    d1 = {}
    for line in D1_PATH.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            r = json.loads(line)
            if r.get("code"):
                d1["KOBIS-" + r["code"]] = r

    # (새 열, 897 원천에서 같은 뜻인 옛 열 — 없으면 None)
    PAIRS = [
        ("장르(genres)", lambda m: m.get("genres"), lambda o: o.get("장르")),
        ("국적(nations)", lambda m: m.get("nations"), lambda o: o.get("국적 후보")),
        ("관람등급(audits.watchGradeNm)",
         lambda m: [x.get("watchGradeNm") for x in (m.get("audits") or []) if x.get("watchGradeNm")],
         lambda o: o.get("등급")),
        ("상영시간(showTm)", lambda m: m.get("showTm"), None),
        ("제작사(companys)", lambda m: m.get("companys"), None),
        ("감독(directors)", lambda m: m.get("directors"), None),
        ("배우(actors)", lambda m: m.get("actors"), None),
        ("제작연도(prdtYear)", lambda m: m.get("prdtYear"), None),
        ("유형(typeNm)", lambda m: m.get("typeNm"), None),
        ("상영형태(showTypes)", lambda m: m.get("showTypes"), None),
        ("스태프(staffs)", lambda m: m.get("staffs"), None),
    ]
    tbl = {}
    for name, newf, oldf in PAIRS:
        has_new = {k for k in hold if k in detail and _nonempty(newf(detail[k]))}
        if oldf is None:
            tbl[name] = {
                "값 있는 유보 행(API)": len(has_new),
                "분모(D3 유보)": len(hold),
                "채움률": round(len(has_new) / len(hold), 4),
                "🔴 897 원천에 같은 뜻의 열": "없다 — 전부 순증",
                "🔴 순증(새로 채우는 유보 행)": len(has_new),
            }
        else:
            has_old = {k for k in hold if k in d1 and _nonempty(oldf(d1[k]))}
            tbl[name] = {
                "값 있는 유보 행(API)": len(has_new),
                "분모(D3 유보)": len(hold),
                "채움률": round(len(has_new) / len(hold), 4),
                "🔴 897 원천이 이미 갖고 있던 행": len(has_old),
                "🔴 순증(옛 열이 비었는데 API 가 채운 행)": len(has_new - has_old),
                "🔴 API 가 못 준 행 중 옛 열엔 있던 행": len(has_old - has_new),
            }
    # movieCd 자체는 유보 키에 **이미 박혀 있다** — 오픈API 가 새로 여는 것이 아니다
    tbl["🔴 movieCd"] = {
        "값 있는 유보 행": len(hold),
        "분모(D3 유보)": len(hold),
        "채움률": 1.0,
        "🔴 주의": ("`docs/수집계획.md` 후보 3 은 「일별 표에 movieCd 가 없다」로 Δ=406 을 매겼다. "
                  "일별 표(`data/ingest/kobis/YYYY-MM-DD.json`)에는 실제로 없다. 그러나 판이 쓰는 "
                  "축 파일 `data/state/kobis_axes.json` 의 키가 `KOBIS-<movieCd>` 라 "
                  "**유보 406/406 이 이미 movieCd 를 갖고 있다** — 이 열의 순증은 **0** 이다"),
    }
    out["바. 🔴 무엇이 **새로** 열리나 — 채움률과 순증은 다른 수다(호출 0회 · 판정 없음)"] = {
        "읽은 파일": str(src.relative_to(ROOT)),
        "🔴 이 절은 ρ 를 안 돌렸다": "「이 열이 유보 N행을 채운다」까지다. 효과는 다음 사이클로 넘긴다",
        "옛 원천": "data/ingest/kobis/axes_raw_897.jsonl (노트 897 이 KOBIS 웹 상세에서 이미 긁어 둔 것)",
        "옛 원천이 유보 406 중 덮는 행": len([k for k in hold if k in d1]),
        "열": tbl,
    }
    # ── 아. 🔴 못 한 것 · 확인 못 한 것 ────────────────────────────────
    lists = sorted(OUTDIR.glob("api908d_list_*.jsonl"))
    unmatched = []
    if lists:
        for line in lists[-1].read_text(encoding="utf-8").split("\n"):
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("일치 후보"):
                cd = r["키"].replace("KOBIS-", "")
                mi = detail.get(r["키"], {})
                unmatched.append({
                    "키": r["키"], "897 이 적은 제목": r.get("제목"),
                    "🔴 오픈API 의 진짜 제목": mi.get("movieNm"),
                    "왜 못 맞췄나": ("897 의 제목이 **잘려 있다** — 일별 박스오피스 표의 "
                                "제목 문자열이 원제보다 짧다. 🔴 「그 영화가 없다」가 아니다"),
                    "🔴 그래도 상세는 받았다(키에 박힌 movieCd 로)": bool(mi), "movieCd": cd})
    nondigit = [k for k in hold if not re.fullmatch(r"\d{8}", k.replace("KOBIS-", ""))]
    out["아. 🔴 못 한 것 · 확인 못 한 것 — 「없다」가 아니라 「못 했다」"] = {
        "🔴 못 맞춘 1건의 정체": unmatched,
        "🔴 판을 안 쟀다": "ρ 를 한 번도 안 돌렸다. 다른 두 에이전트가 lab/·runners/nn908* 를 쓰는 중이라 안 건드렸다",
        "🔴 축 파일에 안 붙였다": ("받은 상세를 `data/state/kobis_axes.json` 에 **안 합쳤다.** "
                          "새 열을 축으로 만드는 것은 다음 사이클이다"),
        "🔴 원장·커밋": "`data/lab/denominator.json` 을 안 건드렸다. `git add`·커밋도 안 했다",
        "🔴 `ingest/kobis.py`": "읽기만 했다 — 한 글자도 안 고쳤다",
        "🔴 후보 10(빠진 16일 소급)": "이 팔의 임무가 아니다 — **안 했다**",
        "🔴 movieCd 가 전부 숫자는 아니다": (
            f"되찾은 10건 중 `2022B512` 처럼 **영문자가 섞인 movieCd** 가 있다. "
            f"유보 406 중 8자리 숫자 꼴이 아닌 키는 {len(nondigit)}건이지만, "
            f"`\\d{{8}}` 정규식을 movieCd 검증에 쓰면 **다른 표본에서 조용히 깨진다**"),
        "🔴 KOFIC 오픈API 의 그 밖의 엔드포인트": "일별/주간 박스오피스·영화사 목록은 **안 불러봤다**",
        "🔴 개봉 전 정보인가": ("장르·국적·제작사·감독·상영시간·등급·제작연도는 개봉 전에 확정되는 것으로 "
                       "**보이나**, 오픈API 응답에 관측 시점이 없어 **시간 게이트를 확인 못 했다**"),
    }
    out["코드 sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16]
    out["🔴 두 판으로 나눠 썼다"] = ("`--run`(수집)이 가~마 를 쓰고 `--annex`(호출 0회)가 바 를 덧붙였다. "
                             "위의 코드 sha256 은 **덧붙인 시점**의 것이다")
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["바. 🔴 무엇이 **새로** 열리나 — 채움률과 순증은 다른 수다(호출 0회 · 판정 없음)"],
                     ensure_ascii=False, indent=1))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--budget-sec", type=float, default=3600.0)
    ap.add_argument("--limit", type=int, default=0, help="0 = 전량")
    ap.add_argument("--recover", action="store_true",
                    help="🔴 897 이 code 를 **못 받은** D1 레코드를 오픈API 로 되찾는다")
    ap.add_argument("--annex", action="store_true",
                    help="🔴 호출 0회 — 이미 받은 jsonl 만 읽어 「무엇이 새로 열리나」를 센다")
    a = ap.parse_args()
    key = _load_key()
    ctr = Counter()

    if a.selftest:
        r1 = call(LIST_URL, {"itemPerPage": "1"}, key, ctr, "movieListResult")
        print("list ok=", r1["ok"], "why=", r1["why"], "sha=", (r1["sha256"] or "")[:16])
        if r1["ok"]:
            print("totCnt=", r1["json"]["movieListResult"].get("totCnt"))
        time.sleep(SLEEP)
        r2 = call(INFO_URL, {"movieCd": "19848027"}, key, ctr, "movieInfoResult")
        print("info ok=", r2["ok"], "why=", r2["why"], "sha=", (r2["sha256"] or "")[:16])
        if r2["ok"]:
            print("필드=", len(r2["json"]["movieInfoResult"]["movieInfo"]))
        print("호출 수=", ctr.calls, "faultInfo=", ctr.fault)
        return 0 if (r1["ok"] and r2["ok"]) else 1

    if a.recover:
        return recover(key, ctr)

    if a.annex:
        return annex()

    if not a.run:
        ap.print_help()
        return 2

    t0 = time.time()
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    den = denominators()
    d1_rows, axes, hold = den.pop("_d1_rows"), den.pop("_axes"), den.pop("_hold")
    n_hold = len(hold)
    print(f"[분모] D1={den['D1(원천 레코드 · data/ingest/kobis/axes_raw_897.jsonl)']} "
          f"D2={den['D2(축 파일 키 · data/state/kobis_axes.json)']} D3유보={n_hold}", flush=True)

    if a.limit:
        hold = hold[: a.limit]

    # 🔴 유보 키에서 movieCd 를 뗀다(902 의 「KOBIS- 정규화」). 되돌리면 0 이 된다.
    keycode = {k: k.replace("KOBIS-", "") for k in hold}
    bad_shape = [k for k, c in keycode.items() if not re.fullmatch(r"\d{8}", c)]

    # 🔴 902 가 기록한 함정을 **심어서 확인한다**: 정규화를 되돌리면(`KOBIS-` 를
    #    안 떼면) movieCd 꼴이 하나도 안 남는다 = 매칭 0. 조용히 넘어가면 안 된다.
    plant = {k: k for k in hold}      # normalize=False 인 경우
    plant_bad = sum(1 for c in plant.values() if not re.fullmatch(r"\d{8}", c))
    trap = {
        "무엇": "902 §W-H — 영화 키 정규화(`KOBIS-` 제거)를 되돌리면 매칭이 조용히 0 이 된다",
        "정규화 O — movieCd 꼴이 아닌 키": len(bad_shape),
        "🔴 정규화 X(심은 결함) — movieCd 꼴이 아닌 키": plant_bad,
        "🔴 심은 결함이 발화하나": plant_bad == len(hold) and len(bad_shape) == 0,
    }

    list_f = OUTDIR / f"api908d_list_{stamp}.jsonl"
    info_f = OUTDIR / f"api908d_movieinfo_{stamp}.jsonl"
    for f in (list_f, info_f):
        if f.exists():
            raise SystemExit(f"덮어쓰기 금지 — 이미 있다: {f}")

    # ── 가-2. 제목·개봉연도로 movieCd 를 **맞춘다**(매칭률을 센다) ──────
    match = {"맞음": [], "못 맞춤": [], "모호": []}
    match_why = {}
    tried = []          # 🔴 실제로 눌러 본 키 — 「안 눌렀다」와 「눌렀는데 0」을 가른다
    lf = list_f.open("w", encoding="utf-8")
    for i, k in enumerate(hold):
        if time.time() - t0 > a.budget_sec:
            print(f"🔴 벽시계 예산 소진 — {i}/{len(hold)} 에서 멈춘다", flush=True)
            break
        tried.append(k)
        v = axes[k]
        title = v.get("name") or ""
        rd = v.get("release_date") or ""
        yr = rd[:4]
        r = call(LIST_URL, {"movieNm": title, "openStartDt": yr, "openEndDt": yr,
                            "itemPerPage": "50"}, key, ctr, "movieListResult")
        rec = {"키": k, "제목": title, "개봉일": rd, "ok": r["ok"], "why": r["why"],
               "sha256": r["sha256"], "url": r["url"], "bytes": r["bytes"]}
        if r["ok"]:
            lst = r["json"]["movieListResult"].get("movieList") or []
            rec["totCnt"] = r["json"]["movieListResult"].get("totCnt")
            rec["후보 수"] = len(lst)
            nt = norm_title(title)
            cands = [m for m in lst
                     if norm_title(m.get("movieNm", "")) == nt
                     and (m.get("openDt") or "")[:4] == yr]
            if not cands:      # 개봉연도 조건을 떼고 제목만
                cands = [m for m in lst if norm_title(m.get("movieNm", "")) == nt]
                rec["연도 완화"] = bool(cands)
            rec["일치 후보"] = [m.get("movieCd") for m in cands]
            if len(cands) == 1:
                match["맞음"].append(k)
                match_why[k] = cands[0].get("movieCd")
            elif len(cands) > 1:
                match["모호"].append(k)
                match_why[k] = [m.get("movieCd") for m in cands]
            else:
                match["못 맞춤"].append(k)
                match_why[k] = None
        else:
            match["못 맞춤"].append(k)
            match_why[k] = None
            rec["🔴"] = "못 읽었다 — 「없다」가 아니다"
        lf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if (i + 1) % 25 == 0:
            print(f"  list {i+1}/{len(hold)} 호출={ctr.calls} fault={ctr.fault}", flush=True)
        time.sleep(SLEEP)
    lf.close()

    n_seen = len(match["맞음"]) + len(match["못 맞춤"]) + len(match["모호"])
    # 🔴 셋의 합 == 눌러 본 수 (분류가 새는 길을 막는다)
    assert n_seen == len(tried), f"셋의 합 {n_seen} != 눌러 본 수 {len(tried)}"
    # 🔴 셋의 합 == 분모 — 예산에 걸려 덜 눌렀으면 여기서 갈린다(감추지 않는다)
    sum_eq_den = (n_seen == len(hold))

    # 🔴 조항 59 · 902 의 함정 — 매칭이 조용히 0/저조하면 **멈춘다**
    rate = len(match["맞음"]) / n_seen if n_seen else 0.0
    halted = None
    if n_seen and rate < 0.50:
        halted = (f"🔴 매칭률 {rate:.4f} < 0.50 — 902 가 기록한 「키 정규화 되돌림 → 매칭 0」 "
                  f"함정과 같은 모양이다. 성공으로 읽지 않고 멈춘다(조항 59)")
        print(halted, flush=True)

    # ── 가-1'. 상세를 받는다(키에 박힌 movieCd 로) ────────────────────
    detail, det_fail = {}, []
    inf = info_f.open("w", encoding="utf-8")
    if not halted:
        for i, k in enumerate(hold):
            if time.time() - t0 > a.budget_sec:
                print(f"🔴 벽시계 예산 소진 — info {i}/{len(hold)} 에서 멈춘다", flush=True)
                break
            cd = keycode[k]
            r = call(INFO_URL, {"movieCd": cd}, key, ctr, "movieInfoResult")
            rec = {"키": k, "movieCd": cd, "ok": r["ok"], "why": r["why"],
                   "sha256": r["sha256"], "url": r["url"], "bytes": r["bytes"]}
            if r["ok"]:
                mi = r["json"]["movieInfoResult"].get("movieInfo") or {}
                rec["필드 수"] = len(mi)
                rec["movieInfo"] = mi
                detail[k] = mi
            else:
                det_fail.append({"키": k, "movieCd": cd, "why": r["why"]})
                rec["🔴"] = "못 받았다 — 「없다」가 아니다"
            inf.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if (i + 1) % 25 == 0:
                print(f"  info {i+1}/{len(hold)} 호출={ctr.calls} fault={ctr.fault}", flush=True)
            time.sleep(SLEEP)
    inf.close()

    # ── 다. 열별 채움률 — 분모는 **D3 유보** ──────────────────────────
    def nonempty(x):
        return x not in (None, "", [], {}) and not (isinstance(x, str) and not x.strip())

    COLS = {
        "장르(genres)": lambda m: m.get("genres"),
        "국적(nations)": lambda m: m.get("nations"),
        "제작사(companys)": lambda m: m.get("companys"),
        "감독(directors)": lambda m: m.get("directors"),
        "배우(actors)": lambda m: m.get("actors"),
        "상영시간(showTm)": lambda m: m.get("showTm"),
        "관람등급(audits.watchGradeNm)": lambda m: [a.get("watchGradeNm") for a in (m.get("audits") or []) if a.get("watchGradeNm")],
        "제작연도(prdtYear)": lambda m: m.get("prdtYear"),
        "개봉일(openDt)": lambda m: m.get("openDt"),
        "제작상태(prdtStatNm)": lambda m: m.get("prdtStatNm"),
        "유형(typeNm)": lambda m: m.get("typeNm"),
        "상영형태(showTypes)": lambda m: m.get("showTypes"),
        "스태프(staffs)": lambda m: m.get("staffs"),
    }
    fill = {}
    for name, fn in COLS.items():
        n = sum(1 for k in hold if k in detail and nonempty(fn(detail[k])))
        fill[name] = {"값 있는 유보 행": n, "분모(D3 유보)": len(hold),
                      "채움률": round(n / len(hold), 4) if hold else None}

    # ── 나. 저장 파일 목록 ────────────────────────────────────────────
    files = []
    for f in (list_f, info_f):
        b = f.read_bytes()
        files.append({"경로": str(f.relative_to(ROOT)), "바이트": len(b),
                      "sha256[:16]": hashlib.sha256(b).hexdigest()[:16]})

    manifest = OUTDIR / f"api908d_manifest_{stamp}.json"
    man = {
        "무엇": "KOBIS 공식 오픈API 상세 — 노트 908 팔 ㄹ",
        "UTC 시각": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "원천": "kobisopenapi.kofic.or.kr (KOFIC 오픈API · 무료 · 일 3,000회)",
        "🔴 키": "`.env` 의 KOBIS_API_KEY 에서만 읽었다 — 산출물·로그에 안 적었다(URL 은 key=*** 로 가림)",
        "입력 지문": {
            "data/ingest/kobis/axes_raw_897.jsonl": hashlib.sha256(D1_PATH.read_bytes()).hexdigest(),
            "data/state/kobis_axes.json": hashlib.sha256(AXES_PATH.read_bytes()).hexdigest(),
            "ingest/kobis_api908.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "분모": den,
        "🔴 --limit(0 = 전량)": a.limit,
        "이 판이 다룬 유보 행": len(hold),
        "실제 호출 수": ctr.calls,
        "faultInfo 건수": ctr.fault,
        "파일": files,
    }
    manifest.write_text(json.dumps(man, ensure_ascii=False, indent=2), encoding="utf-8")
    files.append({"경로": str(manifest.relative_to(ROOT)),
                  "바이트": manifest.stat().st_size,
                  "sha256[:16]": hashlib.sha256(manifest.read_bytes()).hexdigest()[:16]})

    # ── 산출물 ────────────────────────────────────────────────────────
    code_agree = sum(1 for k in match["맞음"] if match_why.get(k) == keycode[k])
    out = {
        "노트": "908 팔 ㄹ — KOBIS 공식 오픈API 상세(수집)",
        "🔴 이 팔은 판을 안 쟀다": "ρ 를 한 번도 안 돌렸다. 「이 열이 유보 N행을 채운다」까지만 적었다",
        "UTC 시각": man["UTC 시각"],
        "코드 sha256": man["입력 지문"]["ingest/kobis_api908.py"][:16],
        "가. 분모 — 🔴 내가 직접 셌다(조항 60 · 딱지 병기)": {
            **den,
            "🔴 `docs/수집계획.md` 가 인용한 수": 406,
            "🔴 내가 센 D3 유보와 같나": n_hold == 406,
            "🔴 D1 과 D3 는 다른 분모다": "897(원천 레코드) 대 406(판 채점 유보) — 이어 붙이지 않는다",
            "D3 유보 규칙(902 재현)": "data/state/kobis_axes.json 의 release_date 연분수 >= 2025.0",
            "🔴 유보 키가 8자리 movieCd 꼴이 아닌 것": len(bad_shape),
            "🔴 902 함정 — 심어서 확인": trap,
        },
        "나. 매칭 — 제목·개봉연도로 searchMovieList 에 맞췄다": {
            "분모(D3 유보)": len(hold),
            "맞음(정확히 1건)": len(match["맞음"]),
            "못 맞춤(0건)": len(match["못 맞춤"]),
            "모호(2건 이상)": len(match["모호"]),
            "실제로 눌러 본 수": len(tried),
            "🔴 셋의 합": n_seen,
            "🔴 셋의 합 == 눌러 본 수(assert)": n_seen == len(tried),
            "🔴 셋의 합 == 분모": sum_eq_den,
            "🔴 안 눌러 본 유보 행(예산·중단)": len(hold) - len(tried),
            "매칭률": round(rate, 4),
            "🔴 제목 매칭 결과가 유보 키에 박힌 movieCd 와 일치한 수": code_agree,
            "🔴 일치율(맞음 분모)": round(code_agree / len(match["맞음"]), 4) if match["맞음"] else None,
            "🔴 조항 59 정지": halted or "안 걸렸다",
        },
        "다. 상세 수령": {
            "실제 호출 수(list + info + 재시도 전부)": ctr.calls,
            "일 한도": DAILY_CAP,
            "HTTP 200": ctr.http_ok,
            "HTTP 비200": ctr.http_bad,
            "네트워크 오류": ctr.net_err,
            "🔴 faultInfo 건수": ctr.fault,
            "JSON 파싱 실패": ctr.parse_err,
            "상세를 받은 유보 행": len(detail),
            "🔴 상세를 못 받은 유보 행": len(hold) - len(detail),
            "🔴 못 받은 것 전량": det_fail[:50],
        },
        "라. 열별 채움률 — 🔴 분모는 D3 유보다": fill,
        "마. 저장 파일(덮어쓰기 안 했다 · 새 이름)": files,
    }
    outp = ROOT / "runners/out908d_kobis.json"
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "마. 저장 파일(덮어쓰기 안 했다 · 새 이름)"},
                     ensure_ascii=False, indent=2)[:4000])
    print(f"\n벽시계 {time.time()-t0:.1f}s · 호출 {ctr.calls} · → {outp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
