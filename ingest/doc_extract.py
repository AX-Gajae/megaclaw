"""드라이브 결과보고서에서 **텍스트를 뽑는다** — 판독 층만 담당한다.

라벨을 고르는 일(`counting_method` 판정)은 여기서 안 한다. 이유는 노트 633 —
정규식으로 고르면 재현율이 **24% 에서 천장**이고, 남은 실패가 전부 *스코프 판단*
이기 때문이다. 예: ``RTPU2447`` 의 결과보고서에는

    합계 약 29,561 명   약 2,400 명

이 한 줄에 같이 있다. 앞은 킨텍스 페스티벌 **전체 방문객**이고 뒤가 **우리 부스**다.
라벨은 2,400 을 골랐다. 어느 쪽인지는 숫자 모양이 아니라 **행사 구조**를 알아야
정해지므로 패턴으로는 못 가른다.

**그래서 이 모듈이 하는 일은 하나다 — 문서를 텍스트로 만든다.**
고르는 일은 LLM 판독기(``ingest/bulk_normalize``)나 사람이 한다.

두 가지를 고쳤고 그것이 이 모듈의 전부다:

  ① **Range 기반 부분 zip.** 결과보고서 pptx 가 68MB~330MB 다(대부분 이미지).
     필요한 것은 ``ppt/slides/*.xml`` 과 ``ppt/charts/*.xml`` 뿐이고 수백 KB다.
     전체를 받으면 1.2GB 짜리 하나가 배치를 멈춰 세운다 — 폴백에 상한을 둔다.

  ② **차트를 시리즈별로 가른다.** 기존 파이프라인은 슬라이드만 읽어
     차트 안의 일별 수치를 통째로 놓쳤다. 그런데 한 차트에 여러 계열이 들어
     있으므로 **통째로 합치면 안 된다** — ``RCPU2410`` 은 차트 총합이 22,181 인데
     그것은 웨이팅 12,614 와 방문 **9,567** 이 섞인 값이다. 시리즈로 가르면
     아는 답이 정확히 나온다.

효과(검증 22건, 라벨을 이미 아는 레코드):

    텍스트 확보   5%  →  **82%**

사용:
    from ingest.doc_extract import text_of, DriveText
    t = DriveText().pull("RTPU2447")
"""
from __future__ import annotations

import io
import re
import subprocess
import urllib.request

# 텍스트를 뽑을 수 있는 형식을 먼저 고른다. 숫자가 작을수록 먼저.
PRIO = {
    "application/vnd.google-apps.spreadsheet": 0,
    "text/plain": 1,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": 2,
    "application/vnd.google-apps.document": 3,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": 4,
    "application/pdf": 5,
}

#: RemoteZip 이 실패했을 때 전체를 받아도 되는 상한. 이보다 크면 포기한다.
FALLBACK_CAP = 150_000_000

_SLIDE_PAT = r"ppt/(slides/slide\d+|charts/chart\d+)\.xml"
_WORD_PAT = r"word/document\.xml"


def _token() -> str:
    return subprocess.check_output(["gcloud", "auth", "print-access-token"],
                                   text=True).strip()


class DriveText:
    """드라이브 파일을 텍스트로. 토큰은 한 번만 받는다."""

    def __init__(self, token: str | None = None):
        self._tok = token

    def token(self) -> str:
        if self._tok is None:
            self._tok = _token()
        return self._tok

    #: **공유 드라이브라 이게 없으면 404 다**(노트 667). 다운로드(`alt=media`)는
    #: 없어도 되지만 **메타 조회는 반드시 필요**하다 --- 그걸 몰라 43개 문서가
    #: 전부 `메타실패:HTTPError` 로 찍혔고 파일이 없는 것처럼 보였다.
    ALL_DRIVES = "supportsAllDrives=true"

    def _url(self, fid: str) -> str:
        return (f"https://www.googleapis.com/drive/v3/files/{fid}"
                f"?alt=media&{self.ALL_DRIVES}")

    def meta(self, fid: str, fields: str = "mimeType,size,name") -> dict:
        """`text_of` 가 요구하는 mime·size 를 준다. **호출자가 직접 짜지 말 것** ---
        `supportsAllDrives` 를 빼먹으면 있는 파일이 404 로 온다(노트 667)."""
        import json as _json
        u = (f"https://www.googleapis.com/drive/v3/files/{fid}"
             f"?fields={fields}&{self.ALL_DRIVES}")
        return _json.loads(self._get(u, timeout=90))

    def _get(self, url: str, timeout: int = 300) -> bytes:
        req = urllib.request.Request(
            url, headers={"Authorization": f"Bearer {self.token()}"})
        return urllib.request.urlopen(req, timeout=timeout).read()

    def _export(self, fid: str, mime: str) -> bytes:
        return self._get(
            f"https://www.googleapis.com/drive/v3/files/{fid}/export"
            f"?mimeType={mime}&{self.ALL_DRIVES}")

    # ── zip XML ────────────────────────────────────────────────
    @staticmethod
    def _zip_texts(z, mime: str) -> str:
        """슬라이드는 태그를 벗기고, **차트는 시리즈별로** 값을 낸다."""
        pat = _SLIDE_PAT if "presentationml" in mime else _WORD_PAT
        out = []
        for n in sorted(z.namelist()):
            if not re.fullmatch(pat, n):
                continue
            try:
                raw = z.read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            if "charts/" in n:
                # **한 차트에 여러 계열이 들어 있다.** 통째로 합치면 방문객과
                # 웨이팅이 섞인다(RCPU2410: 12,614 + 9,567 = 22,181).
                sers = re.split(r"<c:ser>", raw)[1:] or [raw]
                for si, sr in enumerate(sers):
                    nm = re.search(r"<c:tx>.*?<c:v>([^<]{0,60})</c:v>", sr, re.S)
                    vals = re.findall(r"<c:v>([^<]{1,20})</c:v>", sr)
                    out.append("### CHART %s#%d %s\n%s"
                               % (n, si, nm.group(1) if nm else "", " ".join(vals)))
            else:
                out.append(re.sub(r"<[^>]+>", " ", raw))
        return "\n".join(out)

    def text_of(self, mime: str, fid: str, size: int) -> tuple[str, str]:
        """(텍스트, 방법) 을 낸다. 실패는 빈 문자열과 사유."""
        try:
            if mime.startswith("application/vnd.google-apps.spreadsheet"):
                return self._export(fid, "text/csv").decode("utf-8", "ignore"), "gsheet"
            if mime.startswith("application/vnd.google-apps"):
                return self._export(fid, "text/plain").decode("utf-8", "ignore"), "gdoc"

            if any(k in mime for k in ("presentationml", "wordprocessingml")):
                try:
                    from remotezip import RemoteZip
                    with RemoteZip(self._url(fid),
                                   headers={"Authorization": f"Bearer {self.token()}"}) as z:
                        return self._zip_texts(z, mime), "rzip"
                except Exception:
                    if size > FALLBACK_CAP:
                        return "", "rzip실패·큼(%dMB)" % (size // 1_000_000)

            b = self._get(self._url(fid))
            if "pdf" in mime:
                from pypdf import PdfReader
                pages = PdfReader(io.BytesIO(b)).pages
                return "\n".join((p.extract_text() or "") for p in pages), "pdf"
            if "spreadsheetml" in mime:
                import openpyxl
                wb = openpyxl.load_workbook(io.BytesIO(b), data_only=True)
                out = []
                for ws in wb.worksheets:
                    out.append("### " + ws.title)
                    for row in ws.iter_rows(values_only=True):
                        out.append("\t".join("" if v is None else str(v) for v in row))
                return "\n".join(out), "xlsx"
            if any(k in mime for k in ("presentationml", "wordprocessingml")):
                import zipfile
                with zipfile.ZipFile(io.BytesIO(b)) as z:
                    return self._zip_texts(z, mime), "zipfull"
            if mime.startswith("text/"):
                return b.decode("utf-8", "ignore"), "text"
        except Exception as e:
            return "", "실패:" + type(e).__name__
        return "", "미지원:" + mime[:30]


def best_first(files: list[dict]) -> list[dict]:
    """텍스트가 잘 나오는 형식부터, 같은 형식이면 큰 것부터."""
    return sorted(files, key=lambda x: (PRIO.get(x["mime_type"], 9),
                                        -int(x.get("size_bytes") or 0)))


# ── 이미지 PDF — 사람(또는 비전 모형)이 훑을 연락지 ──────────
def contact_sheet(pdf_path: str, out_path: str, pages: int = 12,
                  dpi: int = 72, cols: int = 4) -> int:
    """PDF 앞쪽을 격자로 붙여 **한 장으로 훑게** 한다(노트 634).

    결과보고서의 절반 이상이 **이미지 PDF** 라 텍스트가 안 나온다. 그런데
    보는 것은 된다 — 문제는 27~35쪽짜리에서 방문객 표가 몇 쪽인지 모른다는
    것이다. 연락지로 훑으면 **한 번 보고 그 쪽을 찾는다**. 실제로
    ``RTPU2423``(27쪽)에서 5쪽의 참여자 표를 그렇게 찾았다.

    찾은 뒤에는 그 쪽만 높은 해상도로 다시 렌더해서 읽는다.
    """
    import fitz
    d = fitz.open(pdf_path)
    n = min(len(d), pages)
    pgs = [d[i].get_pixmap(dpi=dpi) for i in range(n)]
    w = max(p.width for p in pgs)
    h = max(p.height for p in pgs)
    rows = (n + cols - 1) // cols
    out = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, w * cols, h * rows))
    out.clear_with(255)
    for i, p in enumerate(pgs):
        r, c = divmod(i, cols)
        p.set_origin(c * w, r * h)
        out.copy(p, p.irect)
    out.save(out_path)
    return n


def render_page(pdf_path: str, page: int, out_path: str, dpi: int = 110) -> None:
    """연락지에서 찾은 쪽 하나를 읽을 만한 해상도로."""
    import fitz
    fitz.open(pdf_path)[page].get_pixmap(dpi=dpi).save(out_path)
