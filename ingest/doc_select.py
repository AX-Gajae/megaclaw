"""사전 문서 선별 — "예측 시점에 존재했던 문서"의 단일 정의.

태거·자극 생성·백테스트가 각자 다른 규칙으로 문서를 골라 왔다. 규칙이 갈리면 어떤
실험이 누출됐는지 사후에 판정할 수 없으므로 여기 한 곳으로 모은다.

발견 루프 1라운드가 배관 결함 두 개를 지목했다:

  ① kind='정산'에 견적서가 섞여 있다. 정산서는 사후 문서지만 **견적서는 오픈 전에
     쓰인 사전 문서**다. 라벨 보유 95건 중 20개 레코드·56건이 이 경로로 통째로
     배제되고 있었다. 최다 지지 후보 plan_capacity_per_day가 바로 견적서 비고란
     ('1일 예상 식수 사용량 900명 기준')에서 나온다.
  ② attr_tagger가 docs[:4]로 앞에서 잘랐다. 기획서·계약서가 4건을 넘는 레코드가
     16건이고, 정렬 순서는 의미가 없으므로 무엇이 잘리는지는 우연이었다.

■ 문서 접근 — MCP Drive 리더로는 안 열리는 포맷이 있다

MCP `read_file_content`가 한컴 저장본(`application/haansoftpptx`, `haansoftdoc`)과
대용량 pptx를 거부한다. 이전 태깅 라운드들이 "제안서 열람 실패 / 계약서 미확인"으로
남긴 문서가 대부분 이것이었고, 정작 그 안에 계획 인원·운영일수가 들어 있었다.

우회 경로(T1c 배치8이 실증, 16건 중 15건 열람 성공):
  1) gcloud 토큰으로 Drive REST 읽기 전용 다운로드 — `files/<ID>?alt=media`
  2) pptx는 로컬에서 zip 풀어 slide XML 직접 파싱
  3) doc/hwp 계열은 `textutil`로 추출
  4) 초대용량 pptx(139MB·216MB 사례)는 remotezip으로 필요한 slide XML만 범위 요청

**MCP는 대용량 PDF를 ~80쪽에서 자른다.** 이건 실패가 아니라 조용한 절단이라 더 위험하다 —
읽힌 것처럼 보이는데 뒤가 없다. RTPU2519의 137쪽 제안서(28.9MB)에서 팝업스토어
섹션(p120~131)과 BUDGET(p136)이 통째로 누락됐고, 그 안에 리워드 굿즈 일별/총 수량표가
있었다. REST 다운로드 후 `pdftotext -layout` 전문 추출로 회수했다.

스캔 PDF는 또 다른 경로가 필요하다. pdftotext가 6바이트를 뱉고 MCP OCR은 표를 숫자
파편으로 깨뜨린다 → REST 다운로드 후 PyMuPDF 300dpi 렌더 → 이미지 직독.
CID 폰트 PDF는 한글이 공백으로 나오므로 200dpi PNG 렌더가 필요하다(RTPU2521).

현재 사전 문서 1,157건 중 pptx 79 + doc 73 + xls 12 = 164건(14%)이 REST 경로가 필요한
포맷이고, PDF 664건 중 대용량·스캔본은 별도 판독이 필요하다.

시간 마스크는 **파일명 날짜가 오픈일 이하**인 것만 통과시켜 강제한다. 날짜를 못 읽는
견적서는 통과시키지 않는다 — 사후 정산서일 위험이 실익보다 크다.
반면 기획서·계약서는 정의상 사전 문서이므로 날짜가 없어도 통과시킨다.
"""
from __future__ import annotations

import re
from datetime import date

from .calendar_features import _doc_dates

PRE_KINDS = ("기획서", "계약서")            # 정의상 사전 문서
QUOTE_PAT = re.compile(r"견적|산출내역|원가")  # kind='정산' 안에 섞인 사전 문서
# 사후 문서 — 이름에 견적이 있어도 이게 걸리면 배제
POST_PAT = re.compile(r"결과보고|정산서|최종정산|실적|완료보고")


def _title(d: dict) -> str:
    return d.get("title") or d.get("name") or ""


def is_pre_open(d: dict, open_from: str | None) -> bool:
    """이 문서가 예측 시점에 존재했는가."""
    t = _title(d)
    if POST_PAT.search(t):
        return False
    if d.get("kind") in PRE_KINDS:
        # 기획서·계약서라도 파일명 날짜가 오픈 이후면 사후 문서다 — 변경계약·부속합의서·
        # 정산합의서가 이 경로로 샌다(RIPU2604 부속합의서는 행사 종료 8일 뒤 작성분이었다).
        # 날짜를 못 읽으면 통과시킨다: 이 두 종류는 정의상 사전 문서이고,
        # 날짜 없는 것까지 막으면 대부분의 기획서를 잃는다.
        if open_from:
            ds = _doc_dates([{"name": t}])
            try:
                if ds and min(ds) > date.fromisoformat(open_from):
                    return False
            except ValueError:
                pass
        return True
    if d.get("kind") == "정산" and QUOTE_PAT.search(t) and open_from:
        try:
            f = date.fromisoformat(open_from)
        except ValueError:
            return False
        return any(x <= f for x in _doc_dates([{"name": t}]))   # 날짜 없으면 불통과
    return False


# 제안서 — 숙주 몰·행사의 입객 실적을 인용하는 거의 유일한 장표.
# T1c 1차 태깅에서 host_daily_traffic이 전 건 null로 나온 원인이 여기 있었다.
PROPOSAL_PAT = re.compile(r"제안|提案|proposal|소개서|브리프", re.IGNORECASE)


def select(rec: dict, per_kind: int = 3, cap: int = 10) -> list[dict]:
    """kind별 층화 샘플. 앞에서 자르지 않고 종류를 고루 담는다.

    같은 kind 안에서는 **제안서를 먼저**, 그다음 오픈일에 가까운 것부터.
      · 제안서: 숙주 입객·시장 규모 같은 '표에 없는 숫자'가 여기 실린다.
      · 최신본: 마지막 개정본이 실제 실행안에 가깝다.
    """
    open_from = (rec.get("conditions", {}).get("period") or {}).get("from")
    pool = [d for d in (rec.get("docs") or []) if is_pre_open(d, open_from)]

    def rank(d):
        t = _title(d)
        ds = _doc_dates([{"name": t}])
        ds = [x for x in ds if not open_from or x <= date.fromisoformat(open_from)]
        return (bool(PROPOSAL_PAT.search(t)),                 # 제안서 우선
                max(ds).toordinal() if ds else -1)            # 그다음 최신순

    buckets: dict[str, list] = {}
    for d in pool:
        k = "견적서" if d.get("kind") == "정산" else d.get("kind")
        buckets.setdefault(k, []).append(d)
    out = []
    for k, n in (("기획서", per_kind + 1), ("계약서", per_kind), ("견적서", per_kind)):
        out += sorted(buckets.get(k, []), key=rank, reverse=True)[:n]
    return out[:cap]


def describe(rec: dict, **kw) -> list[str]:
    """프롬프트에 넣을 문서 목록 줄. 종류 표기를 견적서로 교정해 준다."""
    lines = []
    for d in select(rec, **kw):
        k = "견적서" if d.get("kind") == "정산" else d.get("kind")
        lines.append(f"  - [{k}] {_title(d)[:70]} {d.get('uri','')}")
    return lines
