"""수집 대장 — **수집 자체를 잰다**(노트 643).

이 실험실은 판을 재는 장치는 두 번 고쳐 세웠는데(노트 613~617) **수집을 재는
장치는 없었다.** 덮음은 축을 만들 때마다 따로 찍혔고, 절단은 만든 사람 머릿속에
있었고, 어떤 원천이 앞으로만 쌓이는지는 노트에 흩어져 있었다. 그래서 *"자료가
얼마나 정교한가"* 라는 질문에 매번 새로 파야 했다.

**자료를 재는 것 다섯.**

  덮음      대상 행 중 값이 있는 비율. 축마다 따로 찍던 것을 한자리에 모은다.
  출처      값이 **어느 경로로** 왔나(주소 · district · city 같은 폴백 분포).
            폴백이 많이 섞일수록 같은 이름의 축이 실은 다른 것을 재고 있다.
  절단      상한에 닿아 잘린 값. 뉴스 RSS 는 100 건, 블로그 크롤은 쪽수만큼
            잘린다. **잘린 걸 모르면 '많음' 이 전부 같은 값이 된다.**
  신선도    마지막 자료 날짜. 앞으로만 쌓이는 원천은 백테스트에 못 쓴다.
  대조      같은 값을 **다른 두** 원천에서 얻어 맞춰 본다 --- 수집 품질의
            유일한 직접 증거다. **원천이 진짜 둘인지 먼저 확인한다**(노트 673):
            RCPU2631 의 5,960 대 5,962 는 대조이고, 노트 636 이 대조라고 적은
            RCPU2636 의 7,614 = 7,614 는 **같은 PDF 를 두 번 읽은 것**이었다.

**저장소와 기록 자신을 재는 것 넷** --- 자료가 아니라 우리를 잰다.

  법칙전용   축으로 쓰면 누출인 자료가 축 모듈에 새어 들었나(노트 656).
  주장한고침 대장이 '고쳤다' 고 적은 고침이 코드에 남아 있나(노트 670).
  T 전파     `T` 를 받는 함수가 `T` 를 안 넘기는 자리(노트 668·671).
  죽은숫자   정정된 숫자가 **살아 있는 문서**에 남아 있나(노트 672).

**왜 이게 축 하나 더 만드는 것보다 값이 큰가.** 노트 634~635 가 전수로 밝힌 것:
결과보고서라고 태그된 파일 77건 중 **56건(73%)이 실은 요건정의서**였다.
메타데이터가 틀린 것이다. 그런 자료 위에서 판을 0.001 단위로 다투는 것은
저울을 안 보고 무게를 재는 일이다.

쓰는 법::

    python3 -m ingest.audit            # 표로 찍는다
    python3 -m ingest.audit --json     # program.py 가 읽을 형태
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "data/state"
RECS = ROOT / "data/records"


def _pop_ids() -> list:
    from lab import trendaxes as ta
    ta.set_wide(False)
    ta.set_grades(("A", "B", "C", "D", "E"))
    return (ta._ids() or {}).get("팝업") or []


def _n(p: Path) -> int:
    try:
        d = json.loads(p.read_text())
        return len(d)
    except Exception:
        return 0


def coverage() -> list:
    """대상 행(팝업) 위에서 원천별 덮음과 출처 분포."""
    ids = _pop_ids()
    out = []
    # ① 날씨
    try:
        from lab.weatheraxes import build as wb
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            wb(report=True)
        rep = json.loads(buf.getvalue())
        out.append({"원천": "날씨(ERA5)", "대상": len(ids),
                    "덮음": rep.get("덮음"), "출처": rep.get("좌표출처"),
                    "빠진사유": rep.get("빠진사유")})
    except Exception as e:
        out.append({"원천": "날씨(ERA5)", "오류": f"{type(e).__name__}"})
    # ② 방문자
    try:
        from lab.visitoraxes import build as vb
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            vb(report=True)
        rep = json.loads(buf.getvalue())
        out.append({"원천": "지역방문자(KT)", "대상": len(ids),
                    "덮음": rep.get("덮음"), "출처": rep.get("코드출처"),
                    "빠진사유": rep.get("빠진사유")})
    except Exception as e:
        out.append({"원천": "지역방문자(KT)", "오류": f"{type(e).__name__}"})
    # ③ 브랜드 질의 (뉴스·블로그가 쓰는 키)
    have = 0
    for r in ids:
        p = RECS / f"{r}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text())
        bk = ((d.get("entities") or {}).get("brand_key")
              or (d.get("intervention") or {}).get("brand_name"))
        have += bool(bk)
    out.append({"원천": "브랜드 질의", "대상": len(ids),
                "덮음": round(have / max(len(ids), 1), 3),
                "출처": {"entities.brand_key/intervention.brand_name": have}})
    return out


def freshness() -> list:
    """마지막 자료 날짜. **앞으로만 쌓이는 것은 백테스트에 못 쓴다.**"""
    out = []
    vis = S / "visitors"
    if vis.exists():
        ms = sorted(p.stem for p in vis.glob("[0-9]*.json"))
        out.append({"원천": "지역방문자(KT)", "범위": [ms[0], ms[-1]] if ms else None,
                    "역사": "있음", "쓸모": "백테스트 가능"})
    wx = S / "weather"
    if wx.exists():
        out.append({"원천": "날씨(ERA5)", "범위": ["2013-01", "현재-10일"],
                    "역사": "있음", "쓸모": "백테스트 가능"})
    out.append({"원천": "popup_visitor_daily(BQ)",
                "범위": ["2026-06-12", "2026-08-04 (방문일)"],
                "역사": "**앞으로만** --- 다만 *쌓이는 것* 은 아직 안 봤다",
                "적재": "48행 전부 **2026-08-05 04:47~05:08 UTC 의 20분 창**."
                      " 이후 다음 적재 **없음**(2026-08-05 22:34 UTC 확인 · 17.4시간)",
                "출처": "slack 28행(65% 방문객) · gdrive_sheet 13 · gdrive_pdf 7"
                      " --- 계측 파이프라인이 아니라 **사람이 옮기는 채널**",
                "쓸모": "백테스트 불가(노트 636). **'앞으로 쌓이는 자산' 은 미확인**(노트 673) ---"
                      " 한 번의 소급 적재는 흐름이 아니다. 둘째 적재를 보고 다시 판정한다"})
    out.append({"원천": "유튜브 조회수", "범위": ["읽은 시점", "읽은 시점"],
                "역사": "**없음**",
                "쓸모": "상태 축으로는 개수만 --- 세기는 오픈 이후가 섞인다(노트 639)"})
    out.append({"원천": "웨이백 궤적", "범위": ["2009", "현재"],
                "역사": "있음(큰 것만)",
                "쓸모": "긴 꼬리 덮음 0 --- 모양 학습 전용(노트 639)"})
    return out


#: 상한이 있는 수집기. **잘린 걸 모르면 '많음' 이 전부 같은 값이 된다.**
CENSOR = [
    {"수집기": "구글 뉴스 RSS", "상한": "질의당 100건",
     "확인": "'성수 팝업' 90일 창에서 100건 = 상한 도달. 브랜드 질의는 5건으로 안 닿음",
     "대응": "상한 도달 여부를 값과 함께 저장한다(`news_rss` 의 `상한도달`)"},
    {"수집기": "네이버 블로그 크롤", "상한": "쪽당 30건 × 요청 쪽수 (기본 **20쪽**)",
     "확인": "**쟀다**(노트 658) — 6쪽 대 20쪽 순위 상관 **0.7745**(요청 실패 제외 n=11), "
             "상한에 닿은 여덟 건만 보면 **0.4072**. 6쪽으로는 산리오 154 · 바이탈뷰티 172 · "
             "플라워노즈 181 이 거의 동률인데 20쪽으로는 520 · 582 · 594 다. "
             "절단 안 된 셋은 두 조건이 완전 일치 → 진짜 절단이다",
     "대응": "**고쳤다** — 기본 쪽수 6→20, 반환에 `상한도달`·`쪽`·`실패쪽` 을 같이 낸다. "
             "그리고 **요청 실패를 0 이 아니라 None** 으로 돌린다(그 한 건이 상관을 "
             "0.7745 → 0.4413 으로 끌어내렸다). 20쪽에서도 상한에 닿는 것은 남으므로 "
             "`상한도달` 표시자를 축에 같이 넣어야 한다"},
    {"수집기": "네이버 검색 API", "상한": "start 1,000건 · 기간 파라미터 없음",
     "확인": "브랜드 total 이 65,016 이면 최근 1,000건이 전부 2026년이라 2024 창에 못 닿는다(창안 0)",
     "대응": "과거 창은 크롤로만. API 는 total 이 작은 니치 질의에만"},
    {"수집기": "웨이백 CDX", "상한": "아카이브가 찍은 것만",
     "확인": "popga 목록 0 · 상세 2 · 소형 영상 0 · 유명 영상 다수",
     "대응": "표본을 고르는 데 쓰면 생존 편의. 모양 학습에만"},
]

#: 대조 --- 같은 값을 **다른 두 원천**에서 얻어 맞춰 본 기록.
#:
#: **원천이 진짜 둘인지 확인해야 대조다**(노트 673). 노트 636 의 RCPU2636
#: 7,614 = 7,614 는 BQ 의 `source_record_id` 를 보니 **우리가 읽은 그 PDF**
#: 였다 --- 같은 파일을 두 번 읽은 것이라 대조가 아니다. 노트 579·580 의
#: *'분자와 분모가 같은 것을 보는지 확인한다'* 가 여기서 세 번째로 발동했다.
CROSS = [
    {"대상": "RCPU2631", "원천A": "고객사 최종 마감 실적 5,960(6/27 크랙 공유)",
     "원천B": "core.popup_visitor_daily 일별 합 5,962(구글 시트 원천)",
     "결과": "**0.03% 안에서 일치**",
     "독립성": "BQ 원천 시트 `15kmc-…` 가 **우리 문서목록에 없다** --- 원천이 진짜 둘이다",
     "덤": "`total_visitor_count = actual_entry + walkin` 이 47/48 행에서 성립(노트 673)"},
    {"대상": "~~RCPU2636~~ **무효**", "원천A": "손으로 캔 결과보고서 라벨 7,614",
     "원천B": "core.popup_visitor_daily 합계 7,614",
     "결과": "**대조가 아니다**",
     "왜": "BQ `source_record_id` 가 `1meC7L41tG88Z-…` 이고 우리 레코드 문서목록의 "
           "`FlowerKnows_팝업_운영결과보고서.pdf` 와 **같은 ID** 다 --- 같은 PDF 를 두 번 읽었다(노트 673)"},
    {"대상": "RCPU2410", "원천A": "알려진 라벨 9,567",
     "원천B": "pptx 차트 시리즈 합", "결과": "**일치**",
     "덤": "시리즈를 안 가르면 22,181(웨이팅 12,614 섞임)이 나온다(노트 633)"},
]

#: 메타데이터를 믿으면 안 된다는 **측정된** 증거. 오류가 **양방향**이다.
META_TRUST = {
    "확인": "결과보고서로 태그된 파일 77건 중 **56건(73%)이 요건정의서**였다(노트 635)",
    "반대 방향도 쟀다": "결과보고서 파일에 붙은 `kind` 태그가 **`운영일지`** 다"
                  " --- `(sweetspot)포켓몬고_결과보고서.pptx` → kind=운영일지(노트 667)."
                  " 즉 태그로 **거르면 100% 놓친다**. 있는 것을 없다고 하는 오류다",
    "함의": "파일명 · 태그 · 폴더 이름은 수집의 근거가 못 된다. 내용을 열어야 한다."
          " **거르는 데도 쓸 수 없다** --- 제목으로 훑고 내용으로 판정한다",
    "지금 대응": "`ingest/doc_extract` 가 내용을 읽고, 비전으로 이미지 PDF 를 훑는다."
             " 후보를 고를 때는 `kind` 가 아니라 **제목 문자열**로 훑는다(노트 667)",
    "안 한 것": "태그 오류율을 **주기적으로 다시 재지 않는다** --- 두 번 쟀을 뿐이다",
    "플레이스홀더": "운영일지 72건 중 **29건이 `결과보고서_내용없음.txt`(0바이트)** 다."
              " 문서 목록에 항목이 있는 것과 문서가 있는 것은 다르다(노트 667)",
}


def pending() -> dict:
    """사람 승인을 기다리는 것. **자동으로 레코드에 안 쓴다.**"""
    p = ROOT / "data/mining/vision_scan_2026-08-05.json"
    return {"라벨 후보": [
        "RTPU2501 35,900", "RXPU2407 23,823", "RTPU2452 18,600",
        "RIPU2504 14,520", "RIPU2521 7,647",
        "RCPU2639 15,360(레코드 있음·라벨 없음)",
        "RCPU2641 6,305 · RCPU2640 1,556 · RCPU2642 976 · RCPU2637 755(레코드 없음)",
        "RXPU2417 **하한 818**(만족도 설문 응답자 · 참가자 746+483 — 노트 667)",
        "RCPU2639 15,360 은 **BQ 표에서도 확인됐다**(노트 673) — 원천 둘이 아니라 표 하나뿐이다",
        "**레코드가 없는 4건**: RCPU2637 755 · RCPU2640 1,556 · RCPU2641 6,305 · RCPU2642 976"
        " --- 라벨이 아니라 **행** 이다(노트 673)",
        "**RCPU2631 기간이 하루 어긋난다** — 레코드 2026-06-11~06-24 대 표 방문일 06-12~06-25."
        " 노트 552: 날짜는 축 하나가 아니라 **자를 만드는 것** 이라 라벨보다 무겁다(노트 673)"],
        "원본": str(p) if p.exists() else "없음",
        "규약": "사람 확인 전에는 레코드에 안 쓴다",
        "하한값 취급": "실측이 아니라 **하한**이므로 값으로 쓰면 편의가 생긴다."
                 " 노트 635 가 하한값을 라벨로 안 쓴 선례를 따른다 --- 사람이 정한다"}


#: **축으로 쓰면 누출인 자료.** 감사가 막는다 — 사람 기억이 아니라(노트 598).
LAW_ONLY_SOURCES = ["wiki_after", "data/state/wiki_after"]


def law_only_leak() -> dict:
    """법칙 학습 전용 자료가 **축 모듈에 새어 들어갔나**(노트 656).

    `ingest/wiki_after` 는 출시 **이후** 조회수라 오픈 시점에 관측 불가다.
    축으로 쓰면 판이 올라도 미래를 본 것이다. 이 검사는 `lab/*axes.py` 와
    챔피언 조립 지점(`lab/loop.py`)이 그 이름을 참조하는지 훑는다.

    **왜 감사가 하나.** 노트 598 이 '가드는 불려야 가드다' 를 적었고, 노트
    546·549 가 '장부와 코드가 따로 자란다' 를 두 번 적었다. 주석으로 적은
    금지는 다음 사람이 안 읽는다.
    """
    hits = []
    for p in sorted(list((ROOT / "lab").glob("*axes.py"))
                    + [ROOT / "lab/loop.py", ROOT / "lab/harness.py"]):
        if not p.exists():
            continue
        try:
            t = p.read_text()
        except Exception:
            continue
        for s in LAW_ONLY_SOURCES:
            if s in t:
                hits.append(f"{p.name} → {s}")
    return {"검사": "법칙 전용 자료가 축에 새었나",
            "통과": not hits, "걸린 곳": hits or "없음",
            "왜": "출시 이후 값은 오픈 시점에 관측 불가 — 축으로 쓰면 시간 게이트 위반"}


#: **대장이 '고쳤다' 고 주장하는 고침 — 코드에 실제로 있나**(노트 670).
#:
#: 노트 650 대장에 *"갈래 합집합 결함을 잡아 갈래별 평균으로 고쳤고 누적합으로
#: 만들었다"* 고 적혀 있었는데 `git log --all -p` 에 `cumsum` 이 **0회**였다.
#: 그 고침은 존재한 적이 없고, **뒤따른 두 노트가 결함 있는 축을 쟀다.**
#:
#: 노트 546·549 의 *'장부와 코드가 따로 자란다'* 세 번째 자리인데 앞의 둘과
#: 달리 **감사가 못 잡는 모양**이었다 --- 감사는 "무엇이 등록됐나" 를 보고
#: "적어 둔 고침이 코드에 있나" 는 안 봤다. 그래서 표로 만든다.
#:
#: (파일, 있어야 하는 문자열, 없으면 무엇이 깨지나, 노트)
CLAIMED_FIXES = [
    ("lab/pairboot.py", "def check(",
     "규약 47 의 자는 자기시험이 코드에 있어야 한다 --- 829 가 '내장' 을 "
     "문안으로만 주장했다(티처 #6 · 노트 830)", 830),
    ("ingest/kobis.py", "숫자 셀의 자리는",
     "무명 위치 셀은 마크업이 바뀌면 관객수와 매출이 자리를 바꾼다 --- "
     "셀 명명이 코드에 있어야 한다(노트 830)", 830),
    ("lab/pairs.py", '"CN 만화": None',
     "CN 기준선 0.3094 는 세 시도(씨앗·열·채택 되돌림)로도 재현 불가 --- "
     "값을 되살리면 통과할 수 없는 시험이 부활한다(노트 796 · 규약 44)", 796),
    ("serve/research.py", "def select_best(",
     "선발 기준이 코드에 없으면 결과를 보고 고르게 된다 --- "
     "봉인·강등·선발이 이 모듈의 뼈다(노트 797)", 797),
    ("serve/boardsvc.py", "def _ensure(",
     "MCP 자식 프로세스가 warm() 을 거친 적 없어 캐시를 두고도 "
     "'판이 안 데워졌다' 를 냈다(노트 797)", 797),
    ("serve/boardsvc.py", "def _load_cache(",
     "판 데우기가 **매 프로세스마다 335초** 걸려 재시작할 때마다 창구가 "
     "'판이 아직 안 데워졌다' 만 말한다(노트 795)", 795),
    ("serve/boardsvc.py", "if not os.path.isabs(f):",
     "저장소 밖 모듈이 상대 `__file__` 로 지문 목록에 새어 들면 "
     "캐시가 영영 안 맞는다(노트 795)", 795),
    ("ingest/news_counts.py", "from lab.idolset import _rows",
     "아이돌 제목 id 순서가 idol_axes(81)로 돌아가면 창구가 다시 "
     "틀린 이름을 내보낸다(노트 810 --- 값은 옳고 이름이 틀렸던 하루)", 810),
    ("serve/boardsvc.py", "def absolute(",
     "승격(802)이 카드 문장으로만 남으면 창구가 그 능력을 못 쓴다 --- "
     "보정 재료(f23 안 옮김·ptr·ytr)가 캐시에 함께 구워진다(노트 809)", 809),
    ("serve/boardsvc.py", "ABS_RULER",
     "자 문구 없이 절대값 숫자만 나가면 금지 꼴로 돌아간다(노트 802·809)", 809),
    ("lab/challenger.py", "def rerun(",
     "챌린저 장부가 코드 없이 표만 남으면 다음 세션이 재현 못 한다"
     " --- 656·691 의 병(규약 41 · 노트 804)", 804),
    ("lab/calib.py", "def drift_corrected(",
     "승격된 능력(802)의 계산이 저장소에 없으면 다음 세션이 재현 못 한다"
     " --- 656·691 이 그렇게 고아가 됐다(규약 41)", 802),
    ("serve/capability.py", "드리프트 보정 절대값",
     "승격 조건(8개 도메인·자와 함께)을 카드에서 빼면 맨 절대값 금지가"
     " 승격에 삼켜진다(노트 802)", 802),
    ("lab/calib.py", "def climatology(",
     "절대 자를 기준선 없이 읽으면 **되돌림만 바꿔 판정이 뒤집힌다**"
     " --- 41.95% ↔ 18.80% 인데 둘 다 기후값과 비긴다(규약 43)", 792),
    ("serve/capability.py", "그 도메인의** 80% 구간",
     "**도메인 구간(덮음 0.8448)과 작품 구간(0.40)을 이름으로 안 가르면**"
     " 정직한 구간까지 못 쓰거나 거짓 구간을 쓰게 된다(노트 791·792)", 792),
    ("lab/decay.py", "E_log90",
     "복원된 정의가 코드에서 빠지면 656·657 각주가 다시 고아가 된다"
     "(노트 811 · 규약 41)", 811),
    ("lab/decay.py", "def transfer(",
     "법칙을 재는 코드가 저장소에 없으면 **결론만 남고 재현이 안 된다**"
     " --- 노트 656·657 이 그렇게 됐다(규약 41)", 789),
    ("paper/harness.py", "개에 걸린다:",
     "슬러그가 겹치면 사전순 마지막을 골라 **엉뚱한 논문이 DM 으로 나간다**"
     " --- 반환값은 {전송: true} 라 티가 안 난다(규약 40)", 788),
    ("lab/crowdaxes.py", "cum[x][j1]",
     "갈래 합집합 → 축이 혼잡도가 아니라 갈래 개수를 잰다", 670),
    ("lab/guards.py", "_drop_mode(a, b)",
     "결측 최빈 블록을 안 떼면 백분위가 유령 상관을 만든다", 653),
    ("ingest/social.py", "BLOG_PAGES = 20",
     "6쪽이면 절단이 순위를 망가뜨린다(상관 0.7745 → 0.4072)", 658),
    ("ingest/news_counts.py", '"n": None',
     "요청 실패를 0 으로 읽으면 없는 것과 못 읽은 것이 섞인다", 658),
    ("ingest/wiki_after.py", "LAW_ONLY = True",
     "출시 이후 조회수가 축으로 새면 미래를 본다", 656),
    ("lab/natsaxes.py", 'STATS_END = "20241231"',
     "정규화 통계를 전 구간으로 계산하면 유보가 새어든다", 645),
    ("serve/agent.py", "--bare",
     "--bare 는 OAuth·키체인을 안 읽는다 — auth 로 돌리려면 쓰면 안 된다", 713),
    ("serve/agent.py", '"--resume", session',
     "세션을 안 넘기면 매 요청이 새 세션이라 창구가 앞 턴을 못 기억한다", 713),
    ("serve/mcp.py", "def _tools()",
     "MCP 도구 목록도 등록소에서 온다 — 손으로 두 벌 적지 않는다", 713),
    ("serve/registry.py", "그 R2 를 전체 변동으로 환산한 값",
     "state_field 자가 노트 703 의 죽은 숫자를 이고 있었다 — 정정하고 번역 실패 경고를 박았다", 769),
    ("ingest/audit.py", "쓰레기 3열",
     "죽은 숫자 문맥을 낱말이 아니라 어구로 적는다 — '3열' 이 비용과 흔들림 두 뜻이었다", 758),
    ("state/fieldmodel.py", "def field",
     "축의 관측 구간이 유보 끝보다 먼저 끝나면 판 비용이 4.2배다 — 유보를 축의 끝까지로 자른다(노트 752)", 752),
    ("ingest/audit.py", "문맥은 그 줄에서 찾고 표시는 문단에서 찾는다",
     "같은 숫자열이 두 뜻이라 오탐이 났다 — 문맥 조건을 넣고 창 방향을 갈랐다", 743),
    ("lab/forms.py", "REGISTRY",
     "쓰레기·위약 열 측정은 최소 6 뽑기 — 뽑기 하나면 3.7σ 이상치를 참값으로 보고한다(노트 742)", 742),
    ("ingest/audit.py", "표시는 문단에서 찾는다",
     "죽은 숫자 검사가 줄 단위여서 HTML 산문의 정정 표시가 줄바꿈에 끊겼다 — 앞뒤 두 줄까지 본다", 736),
    ("state/fieldmodel.py", "기본으로 두는 이유는 예보가 아니라 식별이다",
     "공휴일 항을 빼면 유보 R2 가 오르는데 그 이득이 달력 재흡수다 — 기본값을 안 바꾼 이유", 736),
    ("state/fieldmodel.py", "걸음 수를 고정하지 않는다",
     "epochs=60 고정이 덜 배운 자리였다(씨앗 SD 0.2735) — 학습구간 검증으로 최선 지점을 고른다", 735),
    ("state/fieldmodel.py", "최선 지점으로 되돌린다",
     "600 걸음 이후 과적합으로 무너진다 — 최선 가중을 복원해 저장한다", 735),
    ("paper/program.py", "상태는 값으로만 읽는다",
     "트랙 상태를 산문에서 추론했다 — 고치려 문자열을 더하자 T7 곁설명을 오탐했다. 값으로만 읽는다", 730),
    ("paper/program.py", "OK_ST = {",
     "상태 값이 없으면 next 가 트랙 고르기를 망친다 — check 가 규약 위반으로 잡는다", 730),
    ("serve/capability.py", "층 셋",
     "가드가 재갈이 됐다 — 일반 추론·기획까지 거절했다. 층 셋으로 갈랐다", 706),
    ("serve/boardsvc.py", "원인을 지어내지 않는다",
     "state_field 가 div 인자 오류였는데 '자료가 없다' 는 없는 원인을 오류 문구로 지어냈다", 706),
    ("state/fieldmodel.py", "if placebo:",
     "위약 설계가 글로만 있어서 다음 사람이 모형을 재구현하다 기제(K=8 이웃 혼합)를 지웠다", 702),
    ("serve/registry.py", "CAPS: list[dict[str, Any]]",
     "능력 카드와 도구를 손으로 두 벌 적어 갈라질 수 있었다 — 등록소 하나에서 만든다", 701),
    ("serve/boardsvc.py", "def warm(",
     "판(11도메인)이 서버에 안 얹혀 있었다 — 만화 IP 모형 하나뿐이었다", 701),
    ("serve/capability.py", "def _asserted(",
     "check 가 '못 낸다' 는 카드를 지키는 문장을 위반으로 셌다 — 줄 단위 문맥으로 가른다", 697),
    ("serve/capability.py", "LEVEL = re.compile(",
     "이름 붙인 구간은 낱말 하나로 안 잡힌다 — '80% 확률로 8천~2만명' 이 새 나갔다", 697),
    ("serve/agent.py", "if not annotate:",
     "웹이 자기 검사를 그리는데 run 이 또 꼬리를 붙여 경고가 두 번 떴다", 697),
    ("ingest/audit.py", "local: dict = {}",
     "t_propagation 이 이름만으로 전역 표를 맞춰 모듈 다른 동명 함수를 잡았다 — 모듈 안 정의 우선", 693),
    ("serve/ipmodel.py", "SAFE_COLS = (0, 3, 4, 5, 7, 8, 9)",
     "화수·권수·완결은 오늘 값이라 배급 팔에서 뺐다(비용 1.2%p)", 693),
    # 노트 701 이 도구를 등록소로 옮겼으므로 앵커를 옮긴다 --- 규율이 사는
    # 자리가 바뀌면 앵커도 옮겨야 하고, **감사가 그것을 잡았다**(이 표의 값이다).
    ("serve/registry.py", "isascii()",
     "도구 이름은 ASCII 여야 한다 — 한글 함수명은 API 400. 등록소 check() 가 검사한다", 693),
    ("state/fieldmodel.py", "if holiday:",
     "공휴일을 안 빼면 g 의 큰 움직임 87% 가 달력이고 cal_* 축의 재발견이 된다", 690),
    ("state/fieldmodel.py", "stats_end=TRAIN_END",
     "동네 고르기·지평 고르기가 유보 덮음을 본다", 669),
    ("lab/board.py", "data.pooled(sc, T=T)",
     "T 를 가중에 안 넘기면 평가와 가중이 어긋난다", 668),
    ("ingest/doc_extract.py", "supportsAllDrives=true",
     "공유 드라이브 메타 조회가 404 로 와서 파일이 없는 것처럼 보인다", 667),
    ("lab/textnn.py", "self.emb = nn.Embedding",
     "학습된 도메인 토큰이 없으면 사용자 제안의 핵심을 시험할 수 없다", 685),
    ("lab/textaxes.py", "def build_shared(data",
     "공유 인코더 팔이 없으면 파운데이션 주장을 시험할 수 없다", 685),
    ("lab/textaxes.py", "indent=1), flush=True)",
     "함수 안 보고가 블록 버퍼에 갇혀 진행을 잘못 읽는다", 686),
    ("lab/pairs.py", "np.log10(max(dd, 1))",
     "짝의 t 를 연도로 넣으면 years() 가 연도로 읽어 판과 다른 자가 된다", 684),
    ("lab/pairs.py", "def build(name: str",
     "집 밖 짝을 만들 수 없으면 채택에 쓸 자가 판 하나뿐이다", 683),
    ("ingest/news_counts.py", "def titles(dom: str)",
     "제목 원천이 여덟 도메인만 덮어 팝업 계열이 T1 측정에서 빠진다", 680),
    ("lab/guards.py", "predictions(make, data, T=T)",
     "T=2026 으로 부른 가드가 2025 유보의 덮음을 본다", 671),
]


def claimed_fixes() -> dict:
    """대장이 주장하는 고침이 **코드에 남아 있나**(노트 670).

    되돌아간 고침을 잡는다. 표에 없는 고침은 검사되지 않으므로 --- **대장에
    '고쳤다' 를 적을 때 이 표에 한 줄을 같이 넣는다.** 그것이 규약이다.
    """
    miss = []
    for rel, needle, why, note in CLAIMED_FIXES:
        p = ROOT / rel                      # ROOT 는 저장소 뿌리다
        try:
            t = p.read_text()
        except Exception:
            miss.append({"파일": rel, "왜": "파일을 못 읽었다", "노트": note})
            continue
        if needle not in t:
            miss.append({"파일": rel, "없는 것": needle, "깨지는 것": why, "노트": note})
    return {"검사": "대장이 주장하는 고침이 코드에 있나",
            "표 크기": len(CLAIMED_FIXES),
            "통과": not miss, "사라진 고침": miss or "없음",
            "왜": "노트 670 — 유령 고침 하나가 두 노트를 헛돌게 했다"}


#: `T` 를 안 넘겨도 **기본값이라 조용한** 자리(노트 671). 오탐은 여기 적는다.
T_OK = {("by_obs", "pooled"),          # rank.pooled 은 T 를 안 받는다(이름만 같다)
        ("g_accrual", "rows"),         # post=None 이라 T 가 안 쓰인다
        ("pooled", "weights")}         # 위치 인자로 넘긴다


def t_propagation() -> dict:
    """`T` 를 받는 함수가 **`T` 를 받는 다른 함수에 안 넘기는** 자리(노트 671).

    노트 668 이 `lab/board.board()` 에서 이 결함을 하나 잡았다 ---
    `evaluate(T=T)` 는 넘기고 `data.pooled(sc)` 는 안 넘겨서, 평가는 T 유보로
    하고 가중은 2025 유보 수로 하는 어긋남이 있었다. **기본값이 있으므로
    예외가 안 나고 숫자만 이상해진다.** 노트 273·328 도 같은 병이었다.

    그래서 훑기를 상시 검사로 만든다. 위치 인자로 넘기는 것을 오탐으로 세지
    않도록 **각 함수에서 `T` 가 몇 번째 인자인지**를 보고 판정한다.
    """
    import ast
    files = sorted(list((ROOT / "lab").glob("*.py")))
    # 함수 이름 → T 의 위치 인자 번호. **키워드 전용이면 `None`** ---
    # `Data.rows(self, d, *, post, labeled, axis, T)` 가 그 꼴이고, 처음 쓴
    # 검사는 위치 인자만 봐서 **이 함수를 통째로 놓쳤다**(노트 671).
    # **이름만으로 맞추면 모듈이 다른 동명 함수를 잡는다**(노트 693). `pairs.build`
    # 는 `T` 를 안 받는데 `textaxes.build` 는 받아서, 검사가 `pairs.score → build`
    # 를 결함으로 신고했다. 노트 674(`hood_sgg` 부분 문자열)·677(숫자 경계) 과
    # **같은 계열의 다섯째**다 --- 문자열/이름으로 찾는 검사는 범위를 정해야 한다.
    #
    # 그래서 **모듈 안 정의를 먼저 본다.** 같은 파일에 그 이름이 있으면 그
    # 서명이 진실이고, 없을 때만 전역 표로 떨어진다.
    def _tidx(fn: ast.FunctionDef):
        """이 함수가 `T` 를 몇 번째 인자로 받나. 안 받으면 `False`, 키워드전용은 `None`."""
        names = [a.arg for a in fn.args.args]
        if "T" in names:
            return names.index("T")
        if any(a.arg == "T" for a in fn.args.kwonlyargs):
            return None
        return False

    idx: dict = {}          # 전역 --- 모듈 밖 호출을 위한 되떨어짐
    local: dict = {}        # 파일 → {이름: T 위치}  **이쪽이 우선이다**
    trees = {}
    for p in files:
        try:
            t = ast.parse(p.read_text())
        except Exception:
            continue
        trees[p] = t
        loc = {}
        for fn in ast.walk(t):
            if not isinstance(fn, ast.FunctionDef):
                continue
            loc[fn.name] = _tidx(fn)
            if loc[fn.name] is not False:
                idx[fn.name] = loc[fn.name]
        local[p] = loc
    hits = []
    for p, t in trees.items():
        loc = local[p]
        for fn in ast.walk(t):
            if not isinstance(fn, ast.FunctionDef) or fn.name not in idx:
                continue
            for node in ast.walk(fn):
                if not isinstance(node, ast.Call):
                    continue
                nm = (node.func.attr if isinstance(node.func, ast.Attribute)
                      else getattr(node.func, "id", None))
                if nm is None or nm == fn.name or (fn.name, nm) in T_OK:
                    continue
                # **모듈 안 정의가 있으면 그것이 진실이다** --- 없을 때만 전역
                if nm in loc:
                    if loc[nm] is False:
                        continue                      # 이 모듈의 그 함수는 T 를 안 받는다
                    want = loc[nm]
                elif nm in idx:
                    want = idx[nm]
                else:
                    continue
                if any(k.arg == "T" for k in node.keywords):
                    continue
                if want is not None and len(node.args) > want:
                    continue                          # 위치로 넘겼다
                hits.append({"파일": p.name, "줄": node.lineno,
                             "부르는 쪽": fn.name, "불리는 쪽": nm})
    return {"검사": "T 를 받는 함수가 T 를 안 넘기나",
            "통과": not hits, "걸린 곳": hits or "없음",
            "오탐 목록 크기": len(T_OK),
            "왜": "기본값 2025 로 조용히 떨어진다 — 예외가 안 나고 숫자만 틀린다(노트 668·671)"}


#: **정정된 숫자.** (죽은 값, 산 값, 무엇, 정정한 노트) --- 노트 672.
#:
#: 대장은 역사이므로 죽은 숫자가 남아 있는 것이 옳다. 문제는 **살아 있는
#: 문서**다 --- 메모리 색인 · 인계 카드 · 트랙 · 리포트. 그것을 다음 세션이
#: 읽고 결정을 내린다.
DEAD_NUMBERS = [
    # 🔴 노트 885(티처 #49 C1) — 이 표 자신이 죽은 숫자를 '산 값'으로 이고 있었다(4세대 재발).
    # 837 이 12도메인 재기선으로 0.4689/3,369 를 은퇴시켰다: 새 정본은 **0.4710 ± 0.0021 · 유보 3,775**.
    ("0.4932", "0.4710 ± 0.0021(12도메인 · 씨앗 0~11)", "판 rho", 556),
    ("0.4689", "0.4710 ± 0.0021(12도메인 · 씨앗 0~11)",
     "판 rho — 11도메인 시대(영화 합류 전) 값. 837 재기선으로 은퇴", 837),
    # 🔴 895 --- `LIVE_GLOBS` 에 저장소 루트 `*.md` 를 넣자마자(티처 #57 m1) 이 줄이
    # `social-world-model-research.md:102` 의 **MPIIGroupInteraction 26시간**(그룹토론
    # 자료 크기)을 잡았다. 문맥 없는 맨 수량은 **딴 뜻과 충돌한다** --- 노트 677 이
    # 숫자 경계로 고친 것과 같은 계열의 구멍이 **자릿수가 아니라 뜻** 쪽에 남아 있었다.
    # 그래서 5번째 칸(문맥어)을 채운다. **시야를 넓히면 검사의 구멍이 먼저 드러난다.**
    ("26시간", "17.4시간", "popup_visitor_daily 적재 후 무증가 관측 창", 676,
     ("popup", "팝업", "무증가", "적재")),
    # **산 값은 깨끗한 숫자여야 한다** --- 설명을 섞으면 매처가 깨진다(직접 겪었다).
    # 단서는 `무엇` 칸에 적는다.
    ("0.1639", "0.1098",
     "장 사전학습 검증 R2 (옛 g · holiday=False). 자료 성장으로 낡았고 노트 703 이 "
     "**소수 넷째 자리까지 재현**했다. 다만 그 값도 60걸음 · 씨앗 0 이다(노트 735)", 669),
    ("0.134", "0.1200",
     "장 사전학습 R2. 노트 703 이 적은 0.134 는 **60걸음 · 씨앗 0** 이고 그 자리 씨앗 SD 가 "
     "0.2735 였다. 산 값은 **검증으로 걸음을 고른 뒤의 진짜 유보 R2**(씨앗 4 평균)", 735),
    # **문맥 조건(다섯째 칸)** --- 같은 숫자열이 다른 뜻일 때 쓴다(노트 743).
    # `0.0043` 은 '연속 쓰레기 3열 비용'(죽음)이기도 하고 '웹툰 도메인 흔들림'(살아 있음)
    # 이기도 하다. 문맥 낱말이 근처에 있을 때만 잡는다.
    ("0.0043", "0.0153",
     "판에서 연속 쓰레기 3열 비용. 노트 738 이 적은 0.0043 은 **뽑기 하나**의 값이고 여섯 뽑기 "
     "평균에서 3.7σ 아래 이상치였다. 산 값은 뽑기 6 평균(범위 0.0094~0.0212 · 문턱의 2.1~4.7배)",
     742, ("쓰레기 3열", "연속 3열", "문턱 하나")),
    ("+0.024", "-0.0648",
     "공휴일 항의 이득. 노트 703 은 학습에 도움이라 적었는데 유보에서는 해롭다(2σ 밖 · 씨앗 8/8). "
     "**그러나 항을 빼지는 않는다** — 그 이득이 달력 재흡수다(노트 736)", 736),
    # 🔴 894: ctx 를 건다. 맥락 없이 `0.037` 만 보면 **웹툰 곡선의 폭**(`lab/forms.py:1293`)과
    # **정규식 경계 시험의 예시**(이 파일 아래)까지 잡는다 --- 둘 다 장 지속성이 아니다.
    # 자를 좁히는 것이므로 적어 둔다: 이제 이 행은 **`지속성`·`R2`·`R²` 가 같은 줄에
    # 있을 때만** 발화한다. 좁힌 만큼 못 보는 자리가 생겼다.
    ("0.037", "0.0696", "장 지속성 R2 h=30 (같은 이유)", 669, ("지속성", "R2", "R²")),
    ("두 번 연속", "다섯 번(671·672·674·676·677)", "자기 검사 결함 횟수", 677),
    ("3,430", "3,775", "채점 분모", 552),
    ("3,369", "3,775", "채점 분모(유보) — 11도메인 시대 값. 837 재기선으로 은퇴", 837),
    # 노트 886 후속(티처 #51 F5) — 인계 카드 20행이 *"0.4689/**0.4697**·유보 3,369 는 전부
    # 11도메인 시대 값"* 이라 **선언해 놓고** 검출기에는 0.4689·3,369 만 넣었다. 0.4697 은
    # 씨앗 40 짝 회계값이고 12도메인 짝 회계는 0.4699 다 --- 둘 다 은퇴.
    ("0.4697", "0.4710 ± 0.0021(12도메인 · 씨앗 0~11)",
     "판 rho — 11도메인 시대 씨앗 40 값. 837 재기선으로 은퇴", 837),
    ("67.4", "66.4", "쌍 정확도(%)", 556),
]

#: 죽은 숫자를 찾을 **살아 있는 문서**. 대장(`denominator.json`)은 일부러 뺀다.
#: 노트 736 --- **입문서도 산 문서다.** 11면이 0.134 를 일곱 번 이고 있었는데 검사 밖이었다.
#: 🔴 노트 892 --- `serve/capability.py` 가 빠져 있었다. 그 파일은 **사용자에게 무엇을
#: 말해도 되는지**를 정하는 표이고, 거기 붙은 '자' 칸이 837 로 은퇴한 0.4689 · 3,369 ·
#: 11 도메인 셋을 그대로 발행하고 있었다. 티처 #49 C1(*'검출기 자신이 옛 값을 이고
#: 있었다'*)의 사촌 --- 이번엔 **검출기의 시야 밖**이었다. 검출기를 세울 때는
#: **무엇을 안 보는지**를 같이 적어야 한다.
#: 🔴 **손 나열을 버린다(티처 #55 C4 · 노트 893).** 위 문단이 *"검출기를 세울 때는
#: 무엇을 안 보는지를 같이 적어야 한다"* 고 적어 놓고 **목록은 아홉 줄 손 나열**이었다.
#: 티처가 같은 매처를 274 파일에 대니 목록 **밖에서 27건 / 12파일**이 걸렸고 그중
#: 살아 있는 발행물이 **20건 / 6파일**이다 --- `docs/용어.md:19` 판 `0.4932`(**은퇴** · 인계 카드
#: 13행이 모든 프레시 세션을 그 파일로 보낸다) · `serve/boardsvc.py:423`(사용자 응답
#: 본문) · `docs/investor-deck.html:610`(**투자자 대면**) · `docs/worldmodel-primer.html`
#: · `docs/primer/05·06.html`(옛 목록은 `index·07·11` 만 짚어 **05·06 이 원리상 안 걸렸다**).
#: 손 나열은 새 발행물이 생길 때마다 조용히 시야 밖을 만든다 --- 노트 886(`paper/` 누락)
#: 과 티처 #55 M8(표시 루프 손 나열)이 같은 병이고, 이것이 **세 번째 자리**다.
#:
#: **무엇을 안 보는지**(여기 적는 것이 이 상수의 절반이다):
#:   · `paper/` --- 발행물은 개작하지 않는다. `paper_dead()` 가 따로 본다(빚 래칫).
#:   · `runners/` --- 그 노트의 역사다. 옛 자로 잰 값이 남아 있는 게 정상이다.
#:   · `data/lab/denominator.json` --- 대장. 판정 원문을 고치면 역사 왜곡이다.
#:   · 메모리 아카이브(`project-world-model-lab.md`) --- 노트 108~540 의 **이력**이라
#:     같은 이유로 뺀다. 살아 있는 것은 색인(MEMORY.md)과 인계 카드다.
#:   · 🔴 **코드 트리의 하위 디렉터리**(`lab/**`·`ingest/**` 의 깊은 곳) · `tests/` ·
#:     `notebooks/` --- 위 glob 은 **비재귀**다. 894 가 넣은 것은 네 디렉터리의 **첫 켜**뿐이다.
#:   · `data/state/*.json` --- 측정 산출물이다. 옛 값이 남아 있는 게 정상이다.
#: 🔴 **네 번째 자리 --- 코드 트리 전부가 시야 밖이었다(티처 #56 M5 · 노트 894).**
#: 893 이 손 나열을 버리고 glob 으로 갔는데 glob 이 `serve/*.py` 하나뿐이라 라이브
#: 라이브러리가 통째로 안 보였다. 같은 매처를 3,233 파일에 대니 진짜가 셋 --- 전부
#: **머리말**이다: `lab/textaxes.py:3`(0.4689 **은퇴**) · `lab/calib.py:239`(3,369 **은퇴**) ·
#: `ingest/news_counts.py:58`(3,369 **은퇴**). 그리고 🔴 **`audit.py` 자신이 표시 없는 0.4932 를
#: 이고 있었다**(티처 #49 C1 의 *'검출기가 옛 값을 이고 있다'* 가 이 파일에서 재발).
#: 그래서 `lab/`·`ingest/`·`core/`·`state/` 를 시야에 넣는다. **비재귀**다 --- 하위
#: 디렉터리는 아직 안 본다(그것도 여기 적어 둔다).
LIVE_GLOBS = ("docs/**/*.html", "docs/**/*.md", "serve/*.py",
              "lab/*.py", "ingest/*.py", "core/*.py", "state/*.py",
              "data/lab/program.json", "*.md",   # 🔴 티처 #57 m1 --- 저장소 루트의
              # `*.md` 가 통째로 시야 밖이었다(`social-world-model-research.md`).
              # `README.md` 만 손으로 박아 둔 것이 **손 나열 병의 마지막 잔재**였다.
              "../.claude/projects/-Users-ax-world-model/memory/MEMORY.md",
              "../.claude/projects/-Users-ax-world-model/memory/project-lab-state.md")

#: 위 glob 이 쓸어 오되 **역사**라서 빼는 것(이름으로만 뺀다 --- 경로 규칙이 아니다).
LIVE_SKIP = ("project-world-model-lab.md",)


def live_docs() -> list[str]:
    """살아 있는 발행물 목록을 **glob 으로 모은다**(손 나열 금지).

    ROOT 기준 상대 경로 문자열을 정렬해 돌려준다. 상수처럼 쓰이지만 함수인
    이유는 하나 --- **새 문서가 생기면 자동으로 시야에 들어와야 한다.**
    """
    out = []
    for pat in LIVE_GLOBS:
        if "*" in pat:
            for p in sorted(ROOT.glob(pat)):
                if p.is_file() and p.name not in LIVE_SKIP:
                    out.append(str(p.relative_to(ROOT)))
        else:
            p = (ROOT / pat)
            if p.exists() and p.name not in LIVE_SKIP:
                out.append(pat)
    return sorted(dict.fromkeys(out))


#: 논문은 **발행물**이지 살아 있는 문서가 아니다 --- 지난 것을 고쳐 쓰면 역사 왜곡이다.
#: 그래서 `LIVE_DOCS` 에 넣지 않고 따로 본다. 규칙은 둘:
#:   · 아직 유통 중인 것만 본다(최근 `PAPER_WINDOW_D` 일)
#:   · `meta.json` 의 `errata` 가 그 숫자를 언급하면 넘어간다(471 선례)
#: 노트 886 --- 티처 #50 M7: `LIVE_DOCS` 에 `paper/` 가 없어서 논문 473 이 은퇴 숫자
#: 3,369 을 **정정을 명령한 바로 그 사이클에** 인쇄하고도 검사를 통과했다.
#: 처음엔 "최근 30일 논문만 본다"로 짰는데 **자가 무력화**였다 --- 논문 전량(677편)이
#: 2026-07~08 에 만들어져 창이 아무것도 거르지 않았다(886 실측: 창 밖 0). 대신 둘로 나눈다:
#:   · **신선**(`FRESH_D` 일 이내 = 이번 사이클이 낸 논문)은 **경성 실패**. 지금 고친다.
#:   · 나머지는 **등록된 빚**(`PAPER_DEBT`)을 넘을 때만 실패 --- 래칫이다.
#: 85편 112곳을 오늘 일괄 수정하는 것은 발행물 개작이라 안 한다. 새 논문이 죽은 숫자를
#: 인쇄하는 것만 막고, 빚은 세어서 들고 간다.
#: 🔴 **알려진 약점(티처 #51 F9)**: 표시를 **문단(앞뒤 2줄)** 에서 찾으므로 같은 줄의 이웃 숫자에
#: 표시를 달면 표시 없는 숫자까지 사면된다. 실물: 인계 카드 366행(살아 있는 `## 현재 챔피언` 블록)이
#: `판 ρ 0.4697`(표시 없음) 옆에 `0.4689(11도메인·은퇴)` 를 달아 0.4697 이 검출을 피했다.
#: 창을 좁히면 노트 736 이 고친 결함(HTML 산문 줄바꿈)이 되살아나므로 **방향이 반대인 두 요구**다.
#: 지금은 약점을 적어 두고, 표시를 **숫자에 붙여 다는 것**(사용처 표시)으로 대응한다.
#:
#: 정정 표시. 노트 886 --- `은퇴` 를 넣는다. 티처 #50 M7 은 논문 473 이 3,369 을
#: *"면제 창 없이"* 인쇄했다고 했는데 **틀렸다**: 그 문장은 *"자의 분모가 **은퇴한**
#: 숫자(11도메인 시대 유보 3,369)였다"* 이다. 구멍은 논문이 아니라 **표시 목록**에 있었다.
OK_MARKS = ("죽은 숫자", "정정", "철회", "은퇴")

#: 날짜 창으로 가르려던 두 번째 시도도 실패했다 --- 3일 이내 논문이 **113편**이다
#: (두 계열이 동시에 쓰이는 중이라 118~230 번대가 지금도 나온다). 나이는 자가 못 된다.
#: 그래서 **기준선 시각**으로 가른다: 이 검사가 생긴 뒤에 나온 논문은 경성 실패,
#: 그 전 것은 등록된 빚(래칫). 정확하고 재량이 없다.
PAPER_BASELINE_AT = "2026-08-09T08:40:00"
PAPER_DEBT = 127        # 886 등록(실측). 111 → 127 은 0.4697(**은퇴**) 등재분(티처 #51 F5 · 9편 16곳). 이 수를 **넘으면** 실패한다(줄어드는 건 언제나 통과).


def paper_dead(baseline_at: str = PAPER_BASELINE_AT, debt: int = PAPER_DEBT) -> dict:
    """죽은 숫자가 논문에 인쇄돼 있나(노트 886 · 티처 #50 M7).

    논문은 발행물이라 옛것을 고쳐 쓰면 역사 왜곡이다. 그래서 **새로 내는 것만**
    막고 이미 인쇄된 것은 세어서 들고 간다.
    """
    import re as _re
    from datetime import datetime as _dt

    cut = _dt.fromisoformat(baseline_at)
    fresh, aged = [], []
    for meta_p in sorted((ROOT / "paper/steps").glob("*/meta.json")):
        try:
            meta = json.loads(meta_p.read_text())
            tex = (meta_p.parent / "main.tex").read_text()
        except Exception:
            continue
        errata = str(meta.get("errata", ""))
        # 🔴 894 수리(티처 #56 M6). 옛 코드는 `meta["created"]` **하나**를 봤는데 그건
        # 저자가 손으로 적는 문자열이다 --- 480 의 `created`(15:05:00 · 초가 00)가
        # `sent_at`(15:00:18)보다 **5분 늦다**. 자동 생성이 아니라는 뜻이고, 기준선보다
        # 이른 값을 적으면 **경성 실패가 조용히 래칫으로 내려간다**. 손으로 적는 값이
        # 관문을 여는 자리에 있으면 그건 관문이 아니다.
        # → `created` · `sent_at` · 파일 mtime **셋 중 제일 늦은 것**을 쓴다. 손으로
        #   이르게 적어도 mtime 이 안 속는다.
        stamps = []
        for k in ("created", "sent_at"):
            try:
                stamps.append(_dt.fromisoformat(str(meta.get(k, ""))))
            except Exception:
                pass
        for q in (meta_p, meta_p.parent / "main.tex"):
            try:
                stamps.append(_dt.fromtimestamp(q.stat().st_mtime))
            except Exception:
                pass
        is_fresh = bool(stamps) and max(stamps) >= cut
        lines = tex.splitlines()
        for i, ln in enumerate(lines, 1):
            near = "\n".join(lines[max(0, i - 1 - 2):i + 2])
            for row in DEAD_NUMBERS:
                dead, live, what, note = row[:4]
                ctx = row[4] if len(row) > 4 else None
                if not any(not (ln[m.end():m.end() + 1].isdigit()
                                or (m.start() and ln[m.start() - 1].isdigit()))
                           for m in _re.finditer(_re.escape(dead), ln)):
                    continue
                if ctx and not any(w in ln for w in ctx):
                    continue
                if live.split("(")[0] in near or any(m in near for m in
                                                     OK_MARKS):
                    continue
                if dead in errata:
                    continue
                rec = {"논문": meta_p.parent.name, "줄": i, "죽은 값": dead,
                       "산 값": live, "무엇": what, "정정 노트": note,
                       "errata 있나": bool(errata)}
                (fresh if is_fresh else aged).append(rec)
    over = len(aged) > debt
    from collections import Counter as _C
    return {"검사": "죽은 숫자가 논문에 인쇄돼 있나",
            "논문 수": len(list((ROOT / "paper/steps").glob("*/meta.json"))),
            "기준선": baseline_at,
            "🔴 기준선 뒤 논문(경성 실패)": fresh or "없음",
            "빚 내역(죽은 값별)": dict(_C(r["죽은 값"] for r in aged).most_common()),
            "묵은 빚": len(aged), "등록된 빚": debt, "빚이 늘었나": over,
            "빚진 논문 수": len({r["논문"] for r in aged}),
            "통과": (not fresh) and (not over),
            "왜": ("노트 886 티처 #50 M7 — LIVE_DOCS 에 paper/ 가 없어 473 이 은퇴 숫자 3,369 을 "
                  "**정정을 명령한 바로 그 사이클에** 인쇄하고도 통과했다. "
                  "발행물은 개작하지 않으므로 새 논문만 막고 빚은 래칫으로 든다.")}


def dead_numbers() -> dict:
    """정정된 숫자가 **살아 있는 문서**에 남아 있나(노트 672).

    노트 518 이 판 0.4932 를 적고 노트 556 이 그것을 정정했는데, 메모리 색인이
    **100노트 넘게 0.4932 를 이고 있었다.** 그 줄이 *"새 세션은 여기부터"* 라고
    적힌 줄이다. 🔴 **그리고 이 docstring 자신이 그 뒤로 두 번 낡았다**(티처 #57 m2):
    556 의 정정값을 적어 두었는데 837 재기선이 그것을 은퇴시켰고, 같은 파일
    `DEAD_NUMBERS` 표(528행)는 **0.4710** 을 이고 있었다. 검출기가 자기 문서에서
    옛 값을 이고 있는 것은 티처 #49 C1 의 **네 번째 재발**이라 아예 수를 뺀다 ---
    정본 판 rho 는 표에서 읽어라(현재 **0.4710 ± 0.0021 · 12도메인**).

    노트 670·671 과 같은 층이다 --- 자료가 아니라 **기록**을 잰다. 다만
    앞의 둘은 코드를 보고 이것은 **문서**를 본다.

    죽은 숫자가 *정정 문맥에서* 언급되는 것은 정상이므로(`0.4932 는 죽은
    숫자다`) 같은 줄에 **산 값**이나 **정정 표시**(`죽은 숫자` · `정정`)가
    있으면 넘어간다. 첫 판에는 그 예외가 없어서 **내가 방금 쓴 설명 문장을
    잡았다** --- 검사를 세울 때마다 회귀 시험이 그 검사의 구멍을 먼저 찾는다
    (노트 671 에서도 그랬다).
    """
    # **숫자 경계를 본다**(노트 677). 처음 판은 부분 문자열로 맞아서 `0.037` 이
    # `+0.0374`(팝업 이웃 효과) · `+0.0373`(goods_scale) 안에서 잡혔다 --- 노트
    # 674 가 `hood_sgg` 에서 진단한 것과 **같은 기제가 내 검사 안에 있었다.**
    import re as _re

    def _found(dead: str, line: str) -> bool:
        for m in _re.finditer(_re.escape(dead), line):
            nxt = line[m.end():m.end() + 1]
            prv = line[m.start() - 1:m.start()] if m.start() else ""
            if nxt.isdigit() or prv.isdigit():
                continue                      # 더 긴 숫자의 일부다
            return True
        return False

    # **표시는 문단에서 찾는다 --- 줄에서 찾으면 안 된다**(노트 736).
    #
    # 첫 판은 *같은 줄*에 산 값이나 정정 표시가 있나만 봤다. 그런데 HTML 산문은
    # 줄바꿈으로 끊기므로 *"처음에 적었던 0.134 는 ... 노트 735 가 **정정**했다"*
    # 가 **두 줄에 걸치면** 앞줄만 보고 걸린다. 노트 693(이름 범위) · 697(문맥)과
    # 같은 **범위** 결함이고, 이번엔 내 검사 안에 있었다.
    #
    # 그래서 앞뒤 두 줄까지 함께 본다. `철회` 도 표시로 인정한다 --- 숫자를
    # 죽었다고 밝히는 말이다.
    ok_marks = OK_MARKS
    SPAN = 2
    hits = []
    docs = live_docs()
    for rel in docs:
        p = (ROOT / rel).resolve()
        try:
            lines = p.read_text().splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines, 1):
            near = "\n".join(lines[max(0, i - 1 - SPAN):i + SPAN])
            for row in DEAD_NUMBERS:
                dead, live, what, note = row[:4]
                ctx = row[4] if len(row) > 4 else None
                if not _found(dead, ln):
                    continue
                # **문맥은 그 줄에서 찾고 표시는 문단에서 찾는다**(노트 743).
                # 창을 넓히면(`near`) 옆줄의 '3열' 이 딴 뜻의 0.0043 을 잡는다 ---
                # 표시는 산문이 줄바꿈으로 끊기니 넓혀야 하고(노트 736) 문맥은
                # 그 숫자가 무엇인지를 가르니 좁혀야 한다. **방향이 반대다.**
                if ctx and not any(w in ln for w in ctx):
                    continue
                if live.split("(")[0] in near or any(m in near for m in ok_marks):
                    continue
                hits.append({"문서": rel, "줄": i, "죽은 값": dead,
                             "산 값": live, "무엇": what, "정정 노트": note})
    return {"검사": "정정된 숫자가 살아 있는 문서에 남아 있나",
            "표 크기": len(DEAD_NUMBERS), "문서": len(docs),
            "통과": not hits, "걸린 곳": hits or "없음",
            "왜": "노트 672 — 메모리 색인이 100노트 넘게 죽은 판 수치를 이고 있었다"}


def audit() -> dict:
    return {"생성": date.today().isoformat(),
            "덮음": coverage(), "신선도": freshness(),
            "절단": CENSOR, "대조": CROSS, "메타 신뢰": META_TRUST,
            "법칙전용 누출": law_only_leak(),
            "주장한 고침": claimed_fixes(),
            "T 전파": t_propagation(),
            "죽은 숫자": dead_numbers(),
            "죽은 숫자(논문)": paper_dead(),
            "승인 대기": pending()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    d = audit()
    if a.json:
        print(json.dumps(d, ensure_ascii=False, indent=1))
    else:
        for k in ("덮음", "신선도", "절단", "대조"):
            print(f"\n══ {k}")
            for r in d[k]:
                print(" ", json.dumps(r, ensure_ascii=False))
        print("\n══ 메타 신뢰\n ", json.dumps(d["메타 신뢰"], ensure_ascii=False))
        # **검사 둘을 기본 출력에 낸다**(노트 670). `법칙전용 누출` 은 노트 656
        # 이 세운 가드인데 `--json` 없이는 **한 번도 화면에 안 찍혔다** ---
        # '가드는 불려야 가드다'(노트 598)의 다음 층이다: **불려도 안 보이면
        # 안 불린 것과 같다.** 실패는 앞에 표시를 달아 눈에 걸리게 한다.
        # 🔴 **손 나열을 버린다(티처 #55 M8 · 2026-08-10).** 위 문단이 *'불려도 안
        # 보이면 안 불린 것과 같다'* 를 적어 놓고 **목록을 손으로 넷 적었고**, 노트 886
        # 이 `죽은 숫자(논문)` 을 신설하면서 여기에 안 넣었다. 그래서 그 검사는
        # `--json` 없이는 **한 줄도 안 찍혔고**, 노트 892 사이클에서 실제로
        # `통과=False` 인 채 기본 화면이 전부 초록이었다. **자기가 진단한 병에
        # 자기가 걸린 것이고, 원인은 목록이 손 나열이었다는 것 하나다.**
        # 이제 `통과` 키를 가진 항목을 **전부 자동 수집**한다 --- 새 검사를 넣는
        # 사람이 이 줄을 몰라도 화면에 뜬다.
        _shown = {"덮음", "신선도", "절단", "대조", "메타 신뢰", "승인 대기"}
        for k, v in d.items():
            if k in _shown or not isinstance(v, dict) or "통과" not in v:
                continue
            mark = "" if v["통과"] else "  ⛔ 실패"
            print(f"\n══ {k}{mark}\n ", json.dumps(v, ensure_ascii=False))
        print("\n══ 승인 대기\n ", json.dumps(d["승인 대기"], ensure_ascii=False))
