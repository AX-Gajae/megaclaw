"""하네스 계층 --- **무엇이 무엇을 떠받치나.** 노트 911 팔 ㅅ.

`serve/registry.py` 가 *능력의* 척추라면 이 파일은 *제품의* 척추다. 등록소는
「부를 수 있는 것」을 목록으로 두지만, 그 능력들이 **사용자가 원하는 다섯 출력**
중 무엇을 떠받치는지는 어디에도 없었다. `docs/목표.md`(2026-08-11 신설)가 그
다섯을 처음 적었고 **셋(③④⑤)이 0** 이라고 수로 못 박았다.

    ① 우려사항   자 없음 --- 만들어야 한다
    ② 결과       판 ρ 0.47034 (12도메인 · 유보 3,775)
    ③ 언제 터질지 🔴 0 --- 상태 장은 전체 변동의 0.236%(노트 769) · 이벤트 표 없음
    ④ 개선       🔴 0 --- A등급 개입 효과가 위약 한복판(노트 903)
    ⑤ 파생       🔴 0 --- 합류점 0개(노트 897 · 파이썬 604개 전수 AST)

**그래서 이 파일의 목적은 다섯을 채우는 것이 아니다.** 다섯이 **고정된 자리**를
갖게 하고, 각 자리가 「측정값 + 자」 아니면 「못 잽니다 + 왜 + 무엇이 생기면
잽니다」 를 내게 하는 것이다. 0 인 절을 그럴듯하게 채우면 그 순간 실패다.

# 규율 --- 등록소의 규율 넷을 계층에 옮긴다

  ① 이름은 ASCII (등록소 규율 ①과 같은 이유 · 노트 693)
  ② **자 없는 계층·추정기는 등록할 수 없다.** 자가 없다는 것을 보인 노트도
     자다 --- ④ 의 자는 "노트 903: A등급 효과가 위약 한복판(0비트)" 이다.
  ③ 모든 자에 **노트 번호**가 붙는다.
  ④ 「못 잼」 을 낼 추정기는 **`왜 못 잼` 과 `무엇이 생기면 잰다` 를 둘 다**
     선언한다. 하나라도 없으면 **등록 시점에 죽는다**(런타임에 조용히 통과 금지).

# 세 갈래 --- 조항 59 의 서버 판본

    측정됨   값이 있고 자가 붙는다
    못 잼    재료는 읽혔는데 **잴 자가 없다**(또는 자가 0 이라고 이미 답했다)
    못 읽음  **재료 파일이 없거나 안 읽힌다**

🔴 **셋을 합치지 마라.** '없다' 와 '못 봤다' 와 '못 읽었다' 는 셋이다.
`못 잼` 을 `못 읽음` 으로 적으면 파일만 생기면 답이 나온다는 거짓말이 되고,
`못 읽음` 을 `못 잼` 으로 적으면 고칠 수 있는 배선 문제가 원리적 한계로 둔갑한다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: 사용자가 말한 다섯 출력 + 메타. **딱지는 이 여섯뿐이다.**
OUTPUTS = {
    "①우려": "무엇이 잘못될 수 있나",
    "②결과": "어떤 결과가 나오나",
    "③시점": "언제 어떤 불특정 이벤트가 터지나",
    "④개선": "어떻게 개선하나",
    "⑤파생": "각각이 어떤 파생효과를 부르나",
    "메타": "자 · 범위 · 무엇을 모르는지 (다섯 절 자체가 아니다)",
}

#: 절의 세 갈래. **이 셋뿐이고 합치지 않는다.**
STATUS = ("측정됨", "못 잼", "못 읽음")


class RegistrationError(Exception):
    """등록 규율 위반 --- **등록 시점에** 죽는다(런타임에 조용히 통과 금지)."""


# ── 층 ────────────────────────────────────────────────────────────
LAYERS: list[dict] = []


def register_layer(코드: str, 이름: str, 무엇: str, 입력: str, 출력: str,
                    자: list, 떠받치는_출력: list, 오늘: str) -> dict:
    """층 하나를 등록한다. **자 없는 층은 등록할 수 없다.**"""
    if not 코드.isascii() or not 코드.replace("_", "").isalnum():
        raise RegistrationError(f"{코드}: 층 코드가 ASCII 가 아니다(노트 693)")
    if not 자:
        raise RegistrationError(
            f"{코드}: **자가 없다** --- 자 없는 계층은 등록할 수 없다"
            " (등록소 규율 ②를 계층에 옮긴 것이다)")
    for note, what, _v in 자:
        if not isinstance(note, int) or note <= 0:
            raise RegistrationError(f"{코드}: 자 '{what}' 에 노트 번호가 없다")
    for o in 떠받치는_출력:
        if o not in OUTPUTS:
            raise RegistrationError(f"{코드}: 모르는 출력 딱지 '{o}'")
    L = {"층": 코드, "이름": 이름, "무엇": 무엇, "입력": 입력, "출력": 출력,
         "자": 자, "떠받치는 출력": 떠받치는_출력, "오늘": 오늘}
    LAYERS.append(L)
    return L


register_layer(
    "L0", "원천", "`data/ingest/**` · `data/records/**` 재고와 자기서술",
    "세상", "행 · 파일 · 스키마",
    [(646, "판 전체 행수", 21672),
     (691, "유보 채점 행수 --- 🔴 11도메인 시대(3,369) · 12도메인은 3,775", 3369),
     (694, "전향 봉인 행수 --- 이 저장소의 유일한 미래 방향 기록", 4132)],
    ["메타", "②결과"],
    "있음")

register_layer(
    "L1", "표현", "축 · 임베딩 · (장차) 자기지도 표현",
    "L0 행", "행마다의 벡터",
    [(695, "텍스트 열 신호 몫 (씨앗 12·40 재현)", 0.0119),
     (698, "공유 인코더 순 이득 --- ⚠ 댈 자가 미정이다(티처 #55 가 부호 오독으로 철회)",
      0.0040)],
    ["②결과"],
    "축은 있음 · 자기지도 표현은 노트 909 가 짓는 중")

register_layer(
    "L2", "이벤트", "이벤트 표(개체 · 시각 · 종류 · 값 전/후). "
                 "🔴 **이 팔이 만들지 않는다** --- 노트 910 팔이 만드는 중이다. "
                 "여기는 **인터페이스만** 두고 없으면 「못 읽음」으로 물러난다",
    "L0 행", "이벤트 행 (가 개체 · 나 도메인 · 다 시각 · 라 종류 · 마 값 전/후)",
    [(910, "이벤트 표 헤더가 적은 「행 수(이벤트 전량)」 --- 🔴 **이 팔이 다시 안 셌다** "
           "(노트 910 팔이 적은 수다 · 조항 60)", 589174),
     (769, "🔴 상태 장 g 가 전체 변동에서 차지하는 몫 --- ③ 이 0 인 이유", 0.00236)],
    ["③시점"],
    "🔴 2026-08-11 13:27 에 파일이 생겼다(노트 910 팔) --- 이 팔은 **헤더와 앞 행으로 "
    "인터페이스를 맞췄을 뿐**이다. **표가 생긴 것과 ③ 이 열린 것은 다른 문장이다**")

register_layer(
    "L3", "추정기", "다섯 출력별 추정기. 기존 13능력은 대부분 ②(결과) 밑으로 들어간다",
    "L1 표현 (+ 생기면 L2 이벤트)", "값 또는 「못 잼」",
    [(117, "판 챔피언 ρ (12도메인 · 씨앗 0~11 · 유보 3,775 · SD 0.0021 · SE 0.00060)",
      0.47034),
     (802, "8개 도메인 판 가중 자릿수 오차 (보정) 대 기후값 0.1675", 0.1430),
     (693, "선별 유보 AUC (위약 0.554 · 기저율 3.07%)", 0.9408)],
    ["②결과", "③시점"],
    "② 채워짐 · ①③④⑤ 는 껍데기+사유")

register_layer(
    "L4", "자·게이트", "모든 출력에 자를 붙이고 금지 꼴을 막는다",
    "L3 값", "값 + 자 · 또는 차단",
    [(691, "자릿수 오차 비율 (위약 0.4192 · 자 잡음 0.0058) --- 절대값을 막는 근거", 0.4195),
     (791, "**작품** 구간 실측 덮음 --- 이름 붙인 구간을 막는 근거", 0.4026),
     (792, "**도메인** 구간 실측 덮음 --- 이름값을 하는 유일한 구간", 0.8448),
     (692, "선별 격차 (각색/비각색 인기 중앙 차 · log10 자리)", 1.433)],
    ["메타"],
    "있음 --- 이 팔이 **조립 단계(L5) 게이트**를 새로 더했다")

register_layer(
    "L5", "조립", "이벤트 하나를 받아 **다섯 절**을 조립한다. 절마다 세 갈래",
    "이벤트 + L3 값", "다섯 절 (상태 · 값 · 자 · 왜 못 잼 · 무엇이 생기면 잰다)",
    [(903, "🔴 ④ 가 0 인 자 --- A등급 개입 효과가 위약 한복판(0비트)", 0.0),
     (897, "🔴 ⑤ 가 0 인 자 --- 합류점 수(파이썬 604개 전수 AST)", 0),
     (769, "🔴 ③ 이 0 인 자 --- 상태 장의 전체 변동 몫", 0.00236)],
    ["①우려", "②결과", "③시점", "④개선", "⑤파생"],
    "🔴 신설")

register_layer(
    "L6", "창구", "`web` · `agent` · `mcp` --- 사람과 CLI 가 닿는 자리",
    "다섯 절", "HTTP · SSE · JSON-RPC",
    [(706, "재갈을 물렸다가 뺀 자리 --- 막는 것은 *우리 모형의 정량 주장* 이지 "
           "일반 추론이 아니다", None),
     (697, "자기 검사 꼬리를 두 번 붙였던 자리 --- 창구가 스스로 그린다", None),
     (912, "🔴 학습 기록 창구(`/trainlog`)가 낸 응답 중 금지 꼴 게이트에 걸린 것 --- "
           "관측 창구의 자는 **주장하지 않음**이다", 0)],
    ["메타"],
    "있음(확장) --- 노트 912 가 **학습 기록 뷰어**(`/trainlog`)를 더했다")

LAYER_CODES = tuple(L["층"] for L in LAYERS)


# ── L2 인터페이스 --- 없으면 우아하게 물러난다 ─────────────────────
#
# 🔴 **이 팔은 이벤트 표를 만들지 않는다.** 노트 910 팔이 만드는 중이고
# 산출물 경로만 `docs/prereg_910_event.md` §8 에서 읽었다. 그래서 여기는
# **읽기만** 하고, 없으면 **「없다」·「비었다」·「못 읽었다」를 셋으로 갈라**
# 돌려준다(조항 59). 🔴 이 팔이 짓기 시작했을 때는 파일이 **없었고**, 짓는 도중
# (2026-08-11 13:27)에 생겼다 --- 그래서 **양쪽 갈래를 둘 다 실제로 밟았다**.
# 파일을 읽었으면 `검증됨: True` 를 단다.
EVENTLINE = ROOT / "data/state/eventline910.jsonl"

#: 이벤트 한 행의 다섯 칸(사전등록 §2). 헤더 줄과 가르는 데 쓴다.
EVENT_FIELDS = ("개체", "도메인", "시각", "종류", "값 전후")


#: 헤더에서 **꺼내 쓰는** 칸. 🔴 이 수들은 **노트 910 팔이 적은 것**이고 이 팔이
#: 다시 세지 않았다 --- 남의 수를 내 수인 양 옮기면 분모가 섞인다(조항 60).
HEADER_KEYS = ("노트", "UTC", "행 수(이벤트 전량)", "행 수(파일에 쓴 것)",
               "시간 게이트 통과", "시간 게이트 불통과(사후_동일시각)",
               "🔴 lag_days < 0", "도메인별", "종류별(전량)")


def eventline(path: Path | None = None, limit: int = 3) -> dict:
    """L2 이벤트 표를 읽는다 --- **넷으로 갈라 답한다.**

        없다        파일 자체가 없다 (노트 910 팔이 아직 안 냈다)
        비었다      파일은 있는데 0행이다
        읽었다      행이 있다
        못 읽었다   파일은 있는데 열다가 터졌다

    `"없다"` 를 `"0행"` 으로 뭉개면 **만들어지지 않은 것과 만들어졌는데 빈 것**이
    같아진다. 그것이 조항 59 가 막으려는 바로 그 길이다.
    """
    p = path or EVENTLINE
    out = {"경로": str(p.relative_to(ROOT)) if p.is_absolute() and
           str(p).startswith(str(ROOT)) else str(p),
           "검증됨": False,
           "단서": "꼴은 `docs/prereg_910_event.md` §2·§8 에서 읽었다"}
    if not p.exists():
        return {**out, "상태": "없다", "읽은 앞부분(행)": 0,
                "왜": "노트 910 팔이 만드는 중이고 아직 안 냈다"}
    try:
        rows, header = [], None
        with p.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception as e:
                    return {**out, "상태": "못 읽었다", "읽은 앞부분(행)": 0,
                            "왜": f"{i+1}번째 줄이 JSON 이 아니다: {e}"}
                if i == 0 and isinstance(o, dict) and not any(
                        k in o for k in EVENT_FIELDS):
                    header = o          # 자기서술 헤더(사전등록 §8)
                    continue
                rows.append(o)
                if len(rows) >= limit:
                    break
        hd = {k: header[k] for k in HEADER_KEYS
              if isinstance(header, dict) and k in header}
        if not rows:
            return {**out, "상태": "비었다", "읽은 앞부분(행)": 0,
                    "헤더가 적은 것": hd or None,
                    "왜": "파일은 있는데 이벤트 행이 0 이다"}
        return {**out, "상태": "읽었다", "검증됨": True,
                "읽은 앞부분(행)": len(rows),
                "헤더가 적은 것": hd or None,
                "🔴 헤더 수의 출처": "노트 910 팔이 적은 수다 --- **이 팔이 다시 세지 "
                               "않았다**(조항 60: 남의 분모를 내 분모로 쓰지 않는다)",
                "앞줄": rows[0],
                "단서": "이 인터페이스는 **실제 파일로 한 번 맞춰졌다**"
                      "(2026-08-11 · 헤더 + 앞 행). "
                      "🔴 **행을 읽었어도 ③ 은 여전히 「못 잼」이다** --- 표가 있다는 "
                      "것과 간격 예측이 기후값을 이긴다는 것은 다른 문장이다"}
    except Exception as e:
        return {**out, "상태": "못 읽었다", "읽은 앞부분(행)": 0,
                "왜": f"{type(e).__name__}: {e}"}


# ── L3 추정기 등록 ────────────────────────────────────────────────
#
# 각 추정기는 **어느 출력을 내는지 · 최대 어떤 상태까지 갈 수 있는지**를 선언한다.
# 🔴 `최대상태` 가 핵심이다. ③④⑤ 는 **"못 잼" 이 최대**이고, 그것을 넘는 값을
# 내면 `verify()` 가 죽인다 --- LLM 이든 사람이든 그럴듯한 값을 못 끼워 넣는다.
ESTIMATORS: list[dict] = []


def register_estimator(이름: str, 출력: str, 층: str, 최대상태: str, 자: list,
                       산출: str, 부르기, 왜_못_잼: str | None = None,
                       무엇이_생기면: str | None = None) -> dict:
    """추정기 하나를 등록한다. **규율을 어기면 여기서 죽는다.**"""
    if not 이름.isascii() or not 이름.replace("_", "").isalnum():
        raise RegistrationError(f"{이름}: 이름이 ASCII 가 아니다(노트 693)")
    if 출력 not in OUTPUTS:
        raise RegistrationError(f"{이름}: 모르는 출력 딱지 '{출력}'")
    if 층 not in LAYER_CODES:
        raise RegistrationError(f"{이름}: 모르는 층 '{층}'")
    if 최대상태 not in STATUS:
        raise RegistrationError(f"{이름}: 모르는 상태 '{최대상태}' --- {STATUS}")
    if not 자:
        raise RegistrationError(
            f"{이름}: **자가 없다** --- 자 없는 추정기는 등록할 수 없다. "
            "자가 0 이라는 것을 보인 노트도 자다(예: ④ 는 노트 903)")
    for note, what, _v in 자:
        if not isinstance(note, int) or note <= 0:
            raise RegistrationError(f"{이름}: 자 '{what}' 에 노트 번호가 없다")
    if 최대상태 != "측정됨":
        if not 왜_못_잼:
            raise RegistrationError(
                f"{이름}: 최대상태가 '{최대상태}' 인데 **`왜 못 잼` 이 없다** --- "
                "못 잰다고만 하고 이유를 안 적으면 다음 사람이 못 고친다")
        if not 무엇이_생기면:
            raise RegistrationError(
                f"{이름}: 최대상태가 '{최대상태}' 인데 **`무엇이 생기면 잰다` 가 "
                "없다** --- 그것이 없으면 이 절은 영원히 0 이다")
    if not callable(부르기):
        raise RegistrationError(f"{이름}: 부를 수 없다")
    if not 산출:
        raise RegistrationError(f"{이름}: `산출` 이 없다 --- 기록인지 지금 계산인지")
    e = {"이름": 이름, "출력": 출력, "층": 층, "최대상태": 최대상태, "자": 자,
         "산출": 산출, "왜 못 잼": 왜_못_잼, "무엇이 생기면 잰다": 무엇이_생기면,
         "부르기": 부르기}
    ESTIMATORS.append(e)
    return e


def _ensure_estimators() -> None:
    """다섯 추정기는 `serve/brief.py` 가 등록한다 --- **그것을 안 부르면 0개다.**

    등록을 조립 모듈에 둔 이유: 추정기의 `부르기` 가 조립 문맥을 쓰기 때문이다.
    대신 여기서 **반드시 한 번 끌어온다** --- 안 그러면 `verify()` 가 최대상태를
    모르고 0 인 절이 값을 내도 조용히 지나간다(그것이 이 파일이 막으려는 병이다).
    """
    if not ESTIMATORS:
        from . import brief          # noqa: F401  --- 등록 부작용을 쓴다
        _ = brief


def estimator(출력: str) -> dict | None:
    _ensure_estimators()
    for e in ESTIMATORS:
        if e["출력"] == 출력:
            return e
    return None


# ── L4 게이트 --- **조립 단계에서** 금지 꼴 다섯을 막는다 ───────────
#
# 🔴 읽어서 확인한 것(2026-08-11): `serve/capability.py:check()` 는 **다섯 중
# 둘만** 잡는다 --- 이름 붙인 구간(`LEVEL`+`RANGE`)과 전향 실적(`적중`). 나머지
# 셋(맨 절대값 · 인과 단정 · 선별 무시)에는 **탐지기가 저장소 어디에도 없었다**
# --- 시스템 프롬프트로 모형에게 말했을 뿐이다. 그리고 `check()` 가 불리는 자리는
# `serve/agent.py:run/stream/stream_cli` 와 `serve/web.py` 뿐, 즉 **L6 창구뿐**이다.
# 조립(L5)에는 아무 게이트도 없었다. 여기서 다섯을 다 건다.
#
# 각 게이트는 **자기를 발화시키는 미끼(`양성`)와 발화하면 안 되는 줄(`음성`)을
# 같이 들고 다닌다** --- "통과" 는 아무것도 말하지 않는다(노트 676).

ABS8 = ("게임", "만화", "모바일", "세계애니", "아이돌", "애니", "웹툰", "펀딩")

#: 사람 수 · 금액 꼴. 자릿수 오차를 같이 말하지 않으면 금지 꼴이다(노트 792·802).
BARE_ABS = re.compile(r"(?<![\d.])\d{1,3}(,\d{3})+\s*(명|원|관객|방문객|다운로드)"
                      r"|(?<![\d.])\d+\s*(만명|만원|억원|만 명)")
#: 레버를 인과로 읽는 꼴(노트 692). "…를 바꾸면 …가 오른다"
CAUSAL = re.compile(r"(바꾸|올리|낮추|늘리|줄이|교체하|넣으)[^\n]{0,10}(면|으면)"
                    r"[^\n]{0,40}(오릅|오른다|늘어납|늘어난다|증가|상승|개선됩|"
                    r"떨어집|떨어진다|감소)")
#: 조건부 답(각색 뒤 순위 등)을 선별 확률 없이 내는 꼴(노트 692)
COND = re.compile(r"(각색되면|애니로 만들면|만들면|하면)[^\n]{0,30}"
                  r"(상위|백분위|순위)")


def _text(o) -> str:
    return json.dumps(o, ensure_ascii=False, default=str)


def _lines(o) -> list:
    """조립물을 **사람 글 줄**로 편다 --- 게이트는 줄 단위로 본다(노트 697).

    🔴 **JSON 문자열을 그대로 검사하면 안 된다.** 처음에 그렇게 짰더니
    `capability._asserted` 의 *따옴표 안이면 인용이다* 규칙이 **JSON 의 따옴표**에
    걸려 전향 실적 게이트가 **한 번도 발화하지 않았다**(자가검사가 그것을 잡았다 ---
    이것이 노트 676 이 말한 *"통과는 아무것도 말하지 않는다"* 의 실례다).
    그래서 잎사귀를 꺼내 `키 : 값` 한 줄씩으로 편다.
    """
    out: list = []

    def rec(x, key: str = ""):
        if isinstance(x, dict):
            for k, v in x.items():
                rec(v, f"{key}{k} ")
        elif isinstance(x, (list, tuple)):
            for v in x:
                rec(v, key)
        elif x is None:
            return
        else:
            for part in str(x).splitlines():
                out.append(f"{key}: {part}" if key else part)
    rec(o)
    return out


def _neg(line: str) -> bool:
    from .capability import NEGATION
    return any(n in line for n in NEGATION)


def _g_bare_abs(b: dict) -> str | None:
    """① 맨 절대값 --- 자릿수 오차 없이 · 또는 보정 밖 도메인."""
    for 절 in b.get("절", []):
        if 절.get("상태") != "측정됨":
            continue
        s = _text(절.get("값"))
        if not BARE_ABS.search(s) and "절대값" not in s and "원자리" not in s:
            continue
        if "자릿수 오차" not in _text(절):
            return ("맨 절대값 --- 자릿수 오차(0.1430 · 노트 802)를 같이 안 냈다")
        dom = (b.get("이벤트") or {}).get("도메인")
        if dom not in ABS8:
            return (f"맨 절대값 --- '{dom}' 은 드리프트 보정이 없는 도메인이다"
                    f"(보정은 8개뿐 · 노트 802)")
    return None


def _g_item_band(b: dict) -> str | None:
    """② 그 **작품**의 80% 구간 (덮음 0.4026 · 노트 791)."""
    from .capability import LEVEL, RANGE
    for line in _lines(b):
        if "도메인 구간" in line:
            continue                     # 덮음 0.8448 --- 이름값을 하는 유일한 구간
        if _neg(line):
            continue
        if LEVEL.search(line) and (RANGE.search(line) or "구간" in line):
            return "작품 구간 --- 예보를 얹은 구간은 실측 덮음 0.4026 이다(노트 791)"
    for 절 in b.get("절", []):
        for k in (절.get("값") or {}) if isinstance(절.get("값"), dict) else {}:
            if "구간" in str(k) and "도메인 구간" not in str(k):
                return f"작품 구간 --- 값에 '{k}' 키가 있다(노트 791)"
    return None


def _g_causal(b: dict) -> str | None:
    """③ 인과 · 반사실 단정 (노트 692 --- 제작사 배정이 외생이 아니다)."""
    for line in _lines(b):
        if _neg(line):
            continue
        if CAUSAL.search(line):
            return ("인과 단정 --- 관측 계수를 레버로 읽었다(노트 692). "
                    "그리고 A등급 개입 효과는 위약 한복판이다(노트 903)")
    return None


def _g_selection(b: dict) -> str | None:
    """④ 선별을 무시한 조건부 답 (노트 692 --- 선별 격차 1.433 자리 = 27배)."""
    hit = False
    for line in _lines(b):
        if _neg(line):
            continue
        if COND.search(line):
            hit = True
    if hit and "선별" not in _text(b):
        return "선별 무시 --- 조건부 순위를 선별 확률 없이 냈다(격차 1.433 자리 · 노트 692)"
    return None


def _g_forward(b: dict) -> str | None:
    """⑤ 전향 실적 주장 --- 전향 기록 0건."""
    from .capability import check
    hits = [h for h in check("\n".join(_lines(b))) if "전향" in h]
    return hits[0] if hits else None


#: 다섯 게이트. **미끼와 음성 대조를 같이 든다**(노트 676 · 표의 절반은 통과해야 한다).
FORBIDDEN_GATES = [
    {"이름": "bare_absolute", "금지 꼴": "맨 절대값 · 사람 수 · 금액", "근거": 792,
     "잡기": _g_bare_abs,
     "양성": {"이벤트": {"도메인": "팝업"},
            "절": [{"절": "②결과", "상태": "측정됨",
                   "값": {"방문객": "12,000명"}, "자": []}]},
     "음성": {"이벤트": {"도메인": "게임"},
            "절": [{"절": "②결과", "상태": "측정됨",
                   "값": {"보정 절대값(log10)": 3.1, "원자리 값": 1259},
                   "자": ["[802] 8개 판 가중 자릿수 오차 = 0.143 (기후값 0.1675)"]}]}},
    {"이름": "item_band", "금지 꼴": "그 작품의 80% 구간", "근거": 791,
     "잡기": _g_item_band,
     "양성": {"절": [{"절": "②결과", "상태": "측정됨",
                   "값": {"80% 구간": "8천~2만명"}, "자": []}]},
     "음성": {"절": [{"절": "②결과", "상태": "측정됨",
                   "값": {"도메인 구간(학습 라벨 10~90분위)": [2.4, 3.9],
                         "실측 덮음": 0.8448}, "자": []}]}},
    {"이름": "causal_claim", "금지 꼴": "인과 · 반사실 단정", "근거": 692,
     "잡기": _g_causal,
     "양성": {"절": [{"절": "④개선", "상태": "측정됨",
                   "값": "제작사를 A 로 바꾸면 매출이 오릅니다", "자": []}]},
     "음성": {"절": [{"절": "④개선", "상태": "못 잼",
                   "값": None,
                   "왜 못 잼": "제작사를 바꾸면 매출이 오른다고 말할 수 없다 --- "
                            "배정이 외생이 아니다"}]}},
    {"이름": "selection_blind", "금지 꼴": "선별을 무시한 조건부 답", "근거": 692,
     "잡기": _g_selection,
     "양성": {"절": [{"절": "②결과", "상태": "측정됨",
                   "값": "애니로 만들면 상위 10% 입니다", "자": []}]},
     "음성": {"절": [{"절": "②결과", "상태": "측정됨",
                   "값": {"선별(각색) 확률": 0.511,
                         "각색되면 상위": "18%"}, "자": []}]}},
    {"이름": "forward_record", "금지 꼴": "전향 실적 주장", "근거": 0,
     "잡기": _g_forward,
     "양성": {"절": [{"절": "②결과", "상태": "측정됨",
                   "값": "지금까지 82% 적중했습니다", "자": []}]},
     "음성": {"절": [{"절": "②결과", "상태": "못 잼",
                   "값": None,
                   "왜 못 잼": "전향 기록이 0건이라 적중률은 못 냅니다"}]}},
]


def gate(b: dict) -> list:
    """조립물에 금지 꼴이 섞였나 --- **다섯을 다 건다.** 거친 자다."""
    out = []
    for g in FORBIDDEN_GATES:
        try:
            hit = g["잡기"](b)
        except Exception as e:                 # 게이트가 터지면 **막는 쪽**으로 튼다
            hit = f"게이트 자신이 터졌다: {type(e).__name__}: {e}"
        if hit:
            out.append({"게이트": g["이름"], "금지 꼴": g["금지 꼴"],
                        "근거 노트": g["근거"], "무엇": hit})
    return out


def gate_selftest() -> dict:
    """게이트가 **실제로 발화하나** --- 미끼와 음성 대조를 둘 다 돌린다.

    노트 676: *"통과는 아무것도 말하지 않는다."* 그래서 위반만 모으지 않고
    **통과해야 하는 줄을 같은 수로** 둔다 --- 안 그러면 "다 잡는" 게이트
    (항상 참)가 만점을 받는다.
    """
    rows = []
    for g in FORBIDDEN_GATES:
        pos = g["잡기"](g["양성"])
        neg = g["잡기"](g["음성"])
        rows.append({"게이트": g["이름"], "금지 꼴": g["금지 꼴"],
                     "양성에서 발화": bool(pos), "양성 메시지": pos,
                     "음성에서 발화(거짓 양성)": bool(neg), "음성 메시지": neg,
                     "통과": bool(pos) and not neg})
    return {"게이트 수": len(rows), "모두 통과": all(r["통과"] for r in rows),
            "줄": rows}


# ── 조립물 검사 --- 0 인 절이 값을 내면 죽인다 ─────────────────────
class BriefViolation(Exception):
    """조립물이 계약을 어겼다 --- **조용히 고치지 않고 터뜨린다**(노트 133)."""


def verify(b: dict) -> list:
    """다섯 절의 계약을 검사한다. 반환은 어긴 목록(비었으면 통과).

    검사하는 것:
      ① 다섯 절이 **다 있다**(하나라도 빠지면 위반)
      ② 상태가 세 갈래 안에 있다
      ③ `측정됨` 이면 값이 있고 자가 있다 · 아니면 값이 `None` 이다
      ④ 🔴 **최대상태가 「못 잼」인 절이 값을 내면 위반** --- ③④⑤ 가 그렇다
      ⑤ `못 잼`·`못 읽음` 이면 **왜**와 **무엇이 생기면 잰다**가 둘 다 있다
    """
    bad = []
    got = {s.get("절") for s in b.get("절", [])}
    want = [k for k in OUTPUTS if k != "메타"]
    for k in want:
        if k not in got:
            bad.append(f"{k}: 절이 통째로 없다 --- 다섯은 언제나 자리를 갖는다")
    for s in b.get("절", []):
        n = s.get("절")
        st = s.get("상태")
        if st not in STATUS:
            bad.append(f"{n}: 모르는 상태 '{st}' --- 세 갈래뿐이다 {STATUS}")
            continue
        cap = (estimator(n) or {}).get("최대상태")
        if st == "측정됨":
            if s.get("값") is None:
                bad.append(f"{n}: 상태가 '측정됨' 인데 값이 없다")
            if not s.get("자"):
                bad.append(f"{n}: 값을 내면서 **자를 안 붙였다**")
            if cap is not None and cap != "측정됨":
                bad.append(
                    f"🔴 {n}: 이 절의 최대상태는 '{cap}' 인데 '측정됨' 을 냈다 --- "
                    f"0 인 절을 채웠다({s.get('왜 못 잼') or ''})")
        else:
            if s.get("값") is not None:
                bad.append(f"🔴 {n}: 상태가 '{st}' 인데 **값이 있다** --- "
                           "못 잰다면서 숫자를 내면 그게 지어낸 것이다")
            if not s.get("왜"):
                bad.append(f"{n}: '{st}' 인데 **왜**가 없다")
            if not s.get("무엇이 생기면 잰다"):
                bad.append(f"{n}: '{st}' 인데 **무엇이 생기면 잰다**가 없다")
    return bad


# ── 인구조사 --- 층별 능력 수 · 출력별 상태 ────────────────────────
def census() -> dict:
    """층 × 능력 × 출력 매트릭스. `runners/out911_harness.json` 이 이것을 싣는다."""
    _ensure_estimators()
    from . import registry
    caps = registry.CAPS
    by_layer, by_out = {}, {}
    for L in LAYERS:
        by_layer[L["층"]] = [c["이름"] for c in caps if c.get("층") == L["층"]]
    for o in OUTPUTS:
        by_out[o] = [c["이름"] for c in caps
                     if o in (c.get("떠받치는 출력") or [])]
    미배치 = [c["이름"] for c in caps if c.get("층") not in LAYER_CODES]
    return {
        "층": [{"층": L["층"], "이름": L["이름"], "오늘": L["오늘"],
               "떠받치는 출력": L["떠받치는 출력"],
               "능력 수": len(by_layer[L["층"]]), "능력": by_layer[L["층"]],
               "자 줄 수": len(L["자"])} for L in LAYERS],
        "능력 총수": len(caps),
        "층에 안 붙은 능력": 미배치,
        "출력별 능력": {k: {"수": len(v), "능력": v} for k, v in by_out.items()},
        "출력별 최대상태": {e["출력"]: e["최대상태"] for e in ESTIMATORS},
        "추정기": [{"이름": e["이름"], "출력": e["출력"], "층": e["층"],
                 "최대상태": e["최대상태"], "산출": e["산출"],
                 "자 줄 수": len(e["자"])} for e in ESTIMATORS],
    }


def check() -> dict:
    """계층 자신을 검사한다 --- 등록소 `check()` 의 계층 판본."""
    _ensure_estimators()
    bad = []
    for L in LAYERS:
        if not L["자"]:
            bad.append(f"{L['층']}: 자가 없다")
    want = [k for k in OUTPUTS if k != "메타"]
    for o in want:
        if estimator(o) is None:
            bad.append(f"{o}: 추정기가 없다 --- 다섯은 언제나 자리를 갖는다")
    st = gate_selftest()
    if not st["모두 통과"]:
        bad.append(f"게이트 자가검사 실패: "
                   f"{[r['게이트'] for r in st['줄'] if not r['통과']]}")
    from . import registry
    for c in registry.CAPS:
        if c.get("층") not in LAYER_CODES:
            bad.append(f"{c['이름']}: 층 딱지가 없거나 모르는 층이다")
        if not (c.get("떠받치는 출력") or []):
            bad.append(f"{c['이름']}: 어느 출력을 떠받치는지 안 적혔다")
    return {"검사": "계층 규율", "층": len(LAYERS), "추정기": len(ESTIMATORS),
            "게이트": len(FORBIDDEN_GATES), "통과": not bad, "걸린 곳": bad or "없음"}


if __name__ == "__main__":
    print(json.dumps({"검사": check(), "인구조사": census(),
                      "게이트 자가검사": gate_selftest(),
                      "L2": eventline()}, ensure_ascii=False, indent=1))
