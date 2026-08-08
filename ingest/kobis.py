"""KOBIS 일별 박스오피스 --- 12번째 도메인(영화)의 문 (노트 829).

**역사.** 사용자 로드맵(2026-08-07)의 수집 1순위였고, 여섯 노트(808 · 813 ·
814 · 818 · 819 · 822)가 "KOBIS 합류 시 재개"를 문패로 걸었는데 아무도 문을
안 두드렸다(티처 #5). 노트 829 가 두드렸다:

    robots.txt   전체 허용
    노크 A       공개 통계 페이지(findDailyBoxOfficeList.do) --- **키 없이
                 실데이터**(2026-08-01 에 114편 · POST 폼)
    노크 B       오픈API --- 문 있음(faultInfo · 키만 필요 · 사람 게이트는
                 이제 '편의 옵션')

**예의.** robots 허용이어도 SLEEP 1.5초(social.py 관례) · 백필은 하루 1회
폴링과 분리해 천천히.

돌리기:  python3 -m ingest.kobis --date 2026-08-01        # 1일 스냅샷
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "data/ingest/kobis"
URL = ("https://www.kobis.or.kr/kobis/business/stat/boxs/"
       "findDailyBoxOfficeList.do")
SLEEP = 1.5

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9"}


def fetch_daily(date: str) -> list[dict]:
    """YYYY-MM-DD 하루의 일별 박스오피스 표. **읽기만 한다.**

    반환 행: {제목, 개봉일, 숫자 셀(원본 순서)} --- 숫자 셀의 자리는
    [순위 · 일매출 · 누적매출 · 일관객 · 누적관객 · 스크린 · 상영횟수]다
    (2026-08-01 실측 순서 · 노트 830 이 명명 · **불변식**: 누적류는 단조).
    시간 게이트 주의: 관객수는 **라벨**(사후)이고, 축으로 쓸 수 있는 것은
    개봉일 이전 정보뿐이다(배급사·장르·이력 --- 합류 사전등록에서 확정).
    """
    data = urllib.parse.urlencode({
        "loadEnd": "0", "searchType": "search",
        "sSearchFrom": date, "sSearchTo": date,
        "sMultiMovieYn": "", "sRepNationCd": "", "sWideAreaCd": "",
    }).encode()
    req = urllib.request.Request(
        URL, data=data,
        headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    body = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    rows = []
    #: 행 = <tr> ... title="제목" ... 셀들. **셀 안에 태그(span·a)가 있으므로
    #: 태그를 벗기고 읽는다**(첫 판이 이걸 놓쳐 114편 중 1편만 잡았다 — 노트 829).
    for tr in re.split(r"<tr[^>]*>", body)[1:]:
        #: 첫 title= 은 순위 앵커일 수 있다 --- 숫자만인 것은 건너뛴다(노트 829)
        m_title = None
        for mt in re.finditer(r'title="([^"]{1,80})"', tr):
            if not re.fullmatch(r"[\d,.]+", mt.group(1).strip()):
                m_title = mt
                break
        if not m_title:
            continue
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        nums = [c.replace(",", "") for c in cells
                if re.fullmatch(r"[\d,.]+", c.replace(",", "").strip() or "x") and
                re.search(r"\d", c)]
        m_date = re.search(r"(20\d{2}-\d{2}-\d{2})", tr)
        if len(nums) < 2:
            continue
        rows.append({
            "제목": m_title.group(1),
            "개봉일": m_date.group(1) if m_date else None,
            "숫자 셀(원본 순서)": [int(float(x)) for x in nums[:8]],
        })
    return rows


#: 🔴 노트 884 — 무명 위치 배열의 열 이름 핀(티처 #48 e4). 비숫자 셀이 하나 끼면
#: 위치가 조용히 밀린다. 셀 수를 assert 하고 이름을 붙여 앞으로 자라는 자산에 이름을 준다.
CELLS = ["순위", "매출액", "누적매출액", "관객수", "누적관객수", "스크린수", "상영횟수"]


def _named(nums: list[int]) -> dict:
    """셀 수가 관례(7)와 다르면 이름을 붙이지 않고 사실을 남긴다."""
    if len(nums) == len(CELLS):
        return dict(zip(CELLS, nums))
    return {"⚠ 셀 수 이탈": len(nums), "기대": len(CELLS)}


def snapshot(date: str | None = None) -> dict:
    date = date or (_dt.date.today() - _dt.timedelta(days=1)).isoformat()
    rows = fetch_daily(date)
    if not rows:
        return {"⛔": "행 0 — 파싱 실패 또는 자료 없음", "date": date}
    for r in rows:
        r["셀"] = _named(r["숫자 셀(원본 순서)"])
    OUTDIR.mkdir(parents=True, exist_ok=True)
    p = OUTDIR / f"{date}.json"
    prev = json.loads(p.read_text()) if p.exists() else None
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    body = {
        "date": date,
        "시각(UTC)": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": head,
        "입력 지문": hashlib.sha256(
            json.dumps(rows, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12],
        "열 이름 핀": CELLS,
        "셀 수 이탈 행": sum(1 for r in rows if "⚠ 셀 수 이탈" in r["셀"]),
        "개봉일 null": sum(1 for r in rows if not r.get("개봉일")),
        "rows": rows,
    }
    if prev:                       # 🔴 덮어쓰기 금지(티처 #48 M8) — 이전 판을 이력으로 보존
        body["이전 판 이력"] = (prev.get("이전 판 이력") or []) + [
            {k: prev.get(k) for k in ("시각(UTC)", "git HEAD", "입력 지문", "보수")
             if prev.get(k) is not None} | {"행": len(prev.get("rows") or [])}]
        for k in ("보수",):
            if prev.get(k) and k not in body:
                body[k] = prev[k]
    p.write_text(json.dumps(body, ensure_ascii=False, indent=1))
    return {"저장": str(p), "행": len(rows), "셀 수 이탈": body["셀 수 이탈 행"],
            "개봉일 null": body["개봉일 null"], "이전 판 보존": bool(prev)}


def movie_detail(code: str) -> dict:
    """영화 상세 --- **개봉일 이전 확정 축 재료**(노트 831 노크로 확인).

    요약정보 dd 는 파이프 구분: 형태 | 구분 | 장르 | 상영시간 | ... | 국적.
    배급사는 dt/dd(+링크). 등급은 관람등급 블록. 전부 키 불요.
    """
    import urllib.parse as _up
    data = _up.urlencode({"code": code, "titleYN": "Y", "isOuterReq": "false"}).encode()
    req = urllib.request.Request(
        "https://www.kobis.or.kr/kobis/business/mast/mvie/searchMovieDtl.do",
        data=data, headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    out = {"code": code}
    m = re.search(r"요약정보</dt>\s*<dd>(.*?)</dd>", h, re.S)
    if m:
        parts = [re.sub(r"<[^>]+>", "", x).strip() for x in m.group(1).split("|")]
        parts = [x for x in parts if x]
        out["요약"] = parts
        if len(parts) >= 3:
            out["장르"] = re.sub(r"\s+", "", parts[2])
        for x in parts:
            if re.fullmatch(r"[가-힣]{2,10}", x) and x not in ("장편", "단편", "일반영화", "독립예술영화"):
                out["국적 후보"] = x
    m = re.search(r"관람등급[^가-힣]{0,200}?([가-힣0-9]{2,15}관람가)", h, re.S)
    if m:
        out["등급"] = m.group(1)
    m = re.search(r"배급사\s*</dt>\s*<dd[^>]*>(.*?)</dd>", h, re.S)
    if m:
        nm = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        out["배급사"] = re.sub(r"\s+", " ", nm)[:60]
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    a = ap.parse_args()
    print(json.dumps(snapshot(a.date), ensure_ascii=False))
