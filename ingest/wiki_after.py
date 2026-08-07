"""출시 **이후** 위키 조회수 — **법칙 학습 전용. 축으로 쓰면 누출이다**(노트 656).

노트 655 가 T3(소셜 법칙)를 처음 재고 닫았는데, 닫힌 이유가 **자료**였다.
`ingest/wiki_views` 의 창이 노트 149 규약대로 **오픈 이전 90일**뿐이라
사용자가 지목한 *"조회수가 올라간다"* 를 한 번도 못 봤다. 출시 전 램프는
`wiki_momentum` 의 재인코딩이었고(|r| 0.89~0.94) 부호도 도메인 6:3 으로
갈렸다. 성장 곡선은 **출시 후**에 있다.

──────────────────────────────────────────────────────────────
**이 파일이 만드는 자료는 축이 될 수 없다.**

오픈 이후 값은 정의상 **오픈 시점에 관측 불가**다. 판은 2025년으로 잘라
채점하므로 이것을 축으로 넣으면 미래를 보는 것이고, 판이 오르더라도 그것은
누출이다. 이 실험실이 460노트 동안 반복해서 당한 모양이다(타깃 분모 오염 ·
공간 링크 36% 오연결 · 유보 날짜 오염).

그래서 셋을 걸어 둔다.

  ① 캐시를 **다른 디렉토리**에 둔다(`data/state/wiki_after/`). `wiki_views`
     를 읽는 코드가 실수로 집어 갈 수 없다.
  ② ``LAW_ONLY = True`` 를 모듈 상수로 둔다.
  ③ `ingest/audit.py` 가 **`lab/*axes.py` 가 이 모듈을 참조하면 잡는다.**
     사람 기억이 아니라 감사가 막는다 — 노트 598 이 '가드는 불려야 가드다'
     로 적은 자리.

**쓰는 데는 하나뿐이다** --- 성장 곡선의 모수가 도메인을 넘는지(L2) 재는 것.
넘으면 법칙 후보이고, 그 법칙은 *예측 축* 이 아니라 **모형 구조에 대한 근거**
로 쓴다.

──────────────────────────────────────────────────────────────
**제목을 다시 안 푼다.** 기존 캐시에 `page` 가 이미 풀려 있고, 오픈일은
**기존 창의 마지막 날 + 1** 로 복원된다(창이 `d0-90 ~ d0-1` 이므로).
그래서 이 수집기는 위키 해석 단계를 통째로 건너뛴다.

쓰는 법::

    python3 -m ingest.wiki_after --limit 200
    python3 -m ingest.wiki_after --report
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

#: **이 자료는 법칙 학습 전용이다.** 축으로 쓰면 시간 게이트 위반이다.
LAW_ONLY = True

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/state/wiki_views"      # 오픈 **이전** 창(축으로 씀)
CACHE = ROOT / "data/state/wiki_after"    # 오픈 **이후** 창(축으로 안 씀)
WINDOW = 90


#: 레코드 접두 → 위키 언어판. **캐시에 `lang` 이 없어서 복원해야 한다.**
#:
#: 실행 전에 코드를 읽다가 잡았다 --- `wiki_views` 가 남긴 파일은
#: ``{record_id, page, days, n}`` 이고 **`lang` 필드가 없다.** 그런데
#: `wiki_views.SRC` 는 애니 · 웹툰 · 팝업 · 도서 · 펀딩 · 아이돌을 **한국어
#: 위키**에서 긁는다. `j.get("lang") or "en"` 으로 두면 그 여섯 도메인이
#: 한국어 문서 제목을 **영문 위키**에 물어 전부 빈 응답이 된다 --- 조용히
#: 절반이 사라지는 종류의 실패다.
LANG = {"WA": "en", "MG": "en", "GAME": "en", "MB": "en",
        "AN": "ko", "WT": "ko", "BOOK": "ko", "FUND": "ko", "IDOL": "ko",
        "MKT": "ko", "MKT2": "ko"}


def _lang_of(rid: str) -> str:
    """레코드 id → 언어판. 팝업 계열(`R...`)은 전부 한국어다."""
    if rid.startswith("R"):
        return "ko"
    for k in sorted(LANG, key=len, reverse=True):
        if rid.startswith(k):
            return LANG[k]
    return "en"


def _open_date(days: list) -> date | None:
    """오픈일을 복원한다 — 이전 창의 마지막 날 + 1.

    `wiki_views` 가 `d0-WINDOW ~ d0-1` 을 담으므로 마지막 날이 `d0-1` 이다.
    직접 저장된 오픈일이 없어도 이렇게 되찾을 수 있다.
    """
    if not days:
        return None
    s = str(days[-1][0])
    if len(s) < 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8])) + timedelta(days=1)
    except ValueError:
        return None


def pending(limit: int | None = None) -> list:
    """아직 안 받은 것. (레코드, 위키 문서, 오픈일, 언어)."""
    out = []
    for p in sorted(SRC.glob("*.json")):
        if (CACHE / p.name).exists():
            continue
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue
        page, days = j.get("page"), (j.get("days") or [])
        if not page or len(days) < 30:
            continue
        d0 = _open_date(days)
        if d0 is None or d0 >= date.today() - timedelta(days=WINDOW + 5):
            continue                      # 창이 아직 안 찼다
        out.append((p.stem, page, d0, j.get("lang") or _lang_of(p.stem)))
        if limit and len(out) >= limit:
            break
    return out


def run(limit: int | None = None, sleep: float = 0.08) -> dict:
    import time
    from .wiki_views import views
    CACHE.mkdir(parents=True, exist_ok=True)
    todo = pending(limit)
    ok, fail = 0, {}
    for rid, page, d0, lang in todo:
        try:
            v = views(page, d0, d0 + timedelta(days=WINDOW - 1), lang=lang)
        except Exception as e:
            fail[rid] = type(e).__name__
            continue
        (CACHE / f"{rid}.json").write_text(json.dumps(
            {"record_id": rid, "page": page, "open": d0.isoformat(),
             "lang": lang, "days": v or [], "n": len(v or []),
             "law_only": True}, ensure_ascii=False))
        ok += 1
        time.sleep(sleep)
    return {"대상": len(todo), "받음": ok, "실패": fail,
            "주의": "법칙 학습 전용 — 축으로 쓰면 시간 게이트 위반"}


def report() -> None:
    fs = list(CACHE.glob("*.json")) if CACHE.exists() else []
    n30 = 0
    for p in fs:
        try:
            if len(json.loads(p.read_text()).get("days") or []) >= 30:
                n30 += 1
        except Exception:
            pass
    print(json.dumps({"받은 파일": len(fs), "30일 이상": n30,
                      "남은 대상": len(pending()),
                      "용도": "법칙 학습 전용(LAW_ONLY)"}, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    else:
        print(json.dumps(run(a.limit), ensure_ascii=False, indent=1))
        report()
