"""서울 생활인구 250m 격자(OA-22784) — **공식 다운로드 폼**으로 파일을 받는다.

노트 899 지평. 898 탐색이 *"규모를 알았으므로 이제 받을 수 있다"* 로 남긴 것을
실물로 확인하는 자리다. 🔴 **이것은 크롤이 아니다** --- 서울 열린데이터광장의
데이터셋 페이지가 브라우저에서 누르는 그 폼(`frmFile`)을 그대로 POST 한다.

**메커니즘**(2026-08-10 실측):

    페이지  https://data.seoul.go.kr/dataList/OA-22784/S/1/datasetView.do
    폼      <form name="frmFile"> infId=OA-22784 · seqNo(빈칸) · seq=<파일키> · infSeq=1
    보내는 곳 POST https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false

`seq` 는 행 번호가 **아니다** --- 월별은 `YYMM`(2607), 일별은 `YYMMDD`(260806)다.
페이지의 `downloadFile('...')` 인자에서 읽는다. 여기서는 **파일 목록을 페이지에서
파싱**하되 URL 을 손으로 지어내지 않는다.

🔴 **조항 59 --- 종료 코드 0 을 성공으로 읽지 마라.** 이 엔드포인트는 `seq` 가
틀리거나 `Referer` 가 없으면 **HTTP 200 · text/html 183바이트**로

    alert('잘못된 접근입니다. 파일 목록에서 다시 선택하세요.');

를 돌려준다. 그래서 이 스크립트는 받은 뒤 **매직바이트(PK)** 와 크기를 확인하고,
아니면 예외를 던진다.

라이선스: **공공누리 제1유형**(출처표시) --- 상업 이용·변경·재배포 가능.
🔴 **받은 파일은 저장소에 커밋하지 않는다**(월 1개 ≈ 440MB).

쓰는 법::

    python3 -m ingest.seoul_lifepop --list                # 받을 수 있는 파일 목록
    python3 -m ingest.seoul_lifepop --get 2607            # 월별 한 달
    python3 -m ingest.seoul_lifepop --get 260806          # 하루치
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/ingest/seoul_lifepop"

INF_ID = "OA-22784"
PAGE = f"https://data.seoul.go.kr/dataList/{INF_ID}/S/1/datasetView.do"
DOWNLOAD = "https://datafile.seoul.go.kr/bigfile/iot/inf/nio_download.do?&useCache=false"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _get(url: str, data: bytes | None = None, referer: str | None = None):
    h = {"User-Agent": UA}
    if referer:
        h["Referer"] = referer
    return urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h),
                                  timeout=900)


def catalog() -> list[dict]:
    """페이지의 파일 표를 그대로 읽는다. **URL 을 짓지 않는다.**"""
    html = _get(PAGE).read().decode("utf-8", "ignore")
    out = []
    for _n, body in re.findall(r'<tr id="fileTr_(\d+)">(.*?)</tr>', html, re.S):
        seq = re.search(r"downloadFile\('([^']+)'\)", body)
        name = re.search(r'title="([^"]+\.zip)"', body)
        tds = [re.sub(r"<[^>]+>", "", t).strip()
               for t in re.findall(r"<td[^>]*>(.*?)</td>", body, re.S)]
        if seq and name:
            out.append({"seq": seq.group(1), "파일": name.group(1),
                        "포털표기 MB": tds[3] if len(tds) > 3 else None,
                        "등록": tds[4] if len(tds) > 4 else None})
    return out


def fetch(seq: str, outdir: Path = OUT) -> dict:
    """한 파일을 받는다. **매직바이트로 확인한다**(조항 59)."""
    outdir.mkdir(parents=True, exist_ok=True)
    body = urllib.parse.urlencode(
        {"infId": INF_ID, "seqNo": "", "seq": seq, "infSeq": "1"}).encode()
    t0 = datetime.now(timezone.utc)
    r = _get(DOWNLOAD, data=body, referer=PAGE)
    cd = r.headers.get("Content-Disposition") or ""
    m = re.search(r'filename="([^"]+)"', cd)
    fname = m.group(1) if m else f"OA-22784_{seq}.zip"
    dest = outdir / fname
    n = 0
    with open(dest, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            n += len(chunk)
    head = dest.open("rb").read(2)
    if head != b"PK":                       # 🔴 200 껍데기 잡기
        peek = dest.open("rb").read(400).decode("utf-8", "replace")
        dest.unlink()
        raise RuntimeError(f"zip 이 아니다 — 서버가 HTML 을 줬다: {peek!r}")
    h = hashlib.sha256()
    with dest.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return {"seq": seq, "파일": str(dest), "바이트": n,
            "MB": round(n / 1e6, 2), "sha256": h.hexdigest(),
            "Content-Length": r.headers.get("Content-Length"),
            "받은 시각(UTC)": t0.isoformat(timespec="seconds"),
            "라이선스": "공공누리 제1유형(출처표시)"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--get", metavar="SEQ")
    a = ap.parse_args()
    if a.get:
        print(json.dumps(fetch(a.get), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(catalog(), ensure_ascii=False, indent=1))
