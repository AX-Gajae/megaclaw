"""오픈 전 검색 관심도를 **전 도메인**으로 넓힌다.

**왜 이 축인가.** 노트 126이 잰 법칙 --- 한 도메인의 이력만으로 정해지는
모수는 지평 너머에서 배신한다 --- 의 뒤집힌 따름은 ``전 도메인이 공유하는
축만 값어치가 있다''이다. 그리고 노트 126의 F8이 ``같은 자질에 비선형을
얹어도 안 오른다''(병목은 축)고 했다. 둘을 합치면 처방이 하나로 좁혀진다.
\\textbf{전 도메인이 공유하는 새 축을 만든다.}

오픈 전 검색 관심도가 그 조건을 셋 다 맞춘다.

    외부      라벨을 만든 계수기와 다른 곳에서 온다(노트 119--121의 결합 회피)
    사전      오픈 이전 창에서만 계산하므로 시간 마스크를 통과한다
    공통      팝업이든 웹툰이든 게임이든 ``나오기 전에 얼마나 찾아봤나''는 같은 뜻이다

`ingest/naver_trend.py` 가 팝업·아이돌에만 돌던 것을 도메인 여덟으로 넓힌다.
수집·정규화·상태 산출은 그 모듈을 그대로 쓴다(앵커 정규화가 요청 간 비교를
성립시키는 핵심이다).

**한계 하나를 미리 적는다.** 데이터랩은 한국어 검색이다. 만화·세계애니는
제목이 로마자·영문뿐이라 이 축을 못 만든다. 웹툰은 라벨이 네이버 즐겨찾기라
검색량과 **같은 플랫폼**이다 --- 따로 모아 누수 가드로 검정한다.

사용:
    python3 -m ingest.trend_all --plan                도메인별 대상 수만
    python3 -m ingest.trend_all --domain book         한 도메인 수집
    python3 -m ingest.trend_all --domain book --limit 40
"""
from __future__ import annotations

import argparse
import json
import random
import re
import time
from datetime import date, timedelta
from pathlib import Path

from .naver_trend import ANCHORS, MAX_GROUPS, OUT, anchored, creds, fetch, state_features

# 도메인 → (저장 파일, 제목 필드, 날짜 필드)
SPEC = {
    "book":    ("book_records.json",    "title", "pub_date"),
    "funding": ("funding_records.json", "title", "start_date"),
    "game":    ("game_records.json",    "name",  "release_date"),
    "mobile":  ("mobile_records.json",  "title", "release_date"),
    "anime":   ("anime_records.json",   "title", "start_date"),
    "webtoon": ("webtoon_records.json", "title", "start_date"),
    "manga":   ("manga_records.json",   "title", "start_date"),
    "wanime":  ("wanime_records.json",  "title", "start_date"),
}
DATALAB_FROM = "2016-01-01"      # 데이터랩 소급 한계
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()
MIN_HANGUL = 2                   # 한글이 이만큼도 없으면 한국어 검색이 무의미


SEP = r"[|\[\]\(\)<>{}:•~/]"
# 제목이 아니라 꼬리표인 조각. **위치가 아니라 목록으로 거른다** ---
# 애니는 ``(자막) 제목'' 이라 앞이 꼬리표인데 펀딩은 ``[제목] 설명'' 이라
# 앞이 제목이다. 앞머리를 무조건 떼면 펀딩이 망가진다(노트 221).
TAG = re.compile(r"^(더빙|자막|재더빙|무삭제|完|완결|단독|재공개|앵콜|앙코르|리뉴얼|"
                 r"한정|무료|영화원작|드라마원작|모아주문|예약|공식|신작|추천|이벤트|"
                 r"1\+1|NEW|new|HOT|hot|TV|OVA|극장판)$")


def clean_kw(t: str) -> str:
    """제목에서 검색어를 뽑는다.

    ``태양 아래 올리브 | Untold Originals (언톨드...'' 를 그대로 넣으면
    검색량이 0이 나온다. 부제·괄호·시즌 표기를 떼고 조각으로 가른다.

    **앞머리만 쓰면 안 된다**(노트 221). 옛 판은 ``re.split(...)[0]'' 였는데
    두 가지로 무너졌다. ① ``Palworld / 팰월드'' 는 영문 쪽을 집고 한글 쪽을
    버려 한글 문턱에 걸려 통째로 빠진다. ② ``(자막) 도굴왕'' 처럼 괄호로
    시작하면 첫 조각이 \emph{빈 문자열}이라 역시 빠진다. **애니 2,073건 중
    486건이 ②로 빠져 있었다.**

    고침은 조각을 다 만들고 **한글이 있는 첫 조각**을 고르는 것이다. 전
    도메인에서 대상이 5,959 에서 **6,595** 로 는다(애니 $+$486 · 모바일
    $+$81 · 펀딩 $+$53 · 게임 $+$9 · 웹툰 $+$6 · 도서 $+$1).

    한글 덩어리만 남기는 규칙은 여전히 안 넣는다 --- ``Apex 레전드''를
    ``레전드''로 줄이면 전혀 다른 검색어가 된다. **검색량 0은 결측이 아니라
    측정값이다** --- 아무도 안 찾았다는 뜻이고 그것도 신호다."""
    s = re.sub(r"[\u2122\u00ae\u00a9]", "", str(t or ""))
    segs = []
    for p in re.split(SEP, s):
        p = re.sub(r"\s*(시즌|season|Season|part|Part)\s*\d+.*$", "", p)
        p = re.sub(r"\s+", " ", p).strip(" -–—·,.'\"")
        if len(p) >= 2 and not TAG.match(p):
            segs.append(p)
    if not segs:
        return ""
    han = [c for c in segs if len(re.findall(r"[가-힣]", c)) >= MIN_HANGUL]
    return _cap(han[0] if han else segs[0])


def _cap(p: str, n: int = 20) -> str:
    """길이 한도를 **낱말 경계에서** 지킨다(노트 491).

    옛 판은 ``[:20]`` 이라 조각을 낱말 한가운데서 잘랐다 --- ``Family Go!
    - 대를 잇는 인생게임'' 이 ``Family Go! - 대를 잇는 인'' 이 되고, 그런
    질의는 데이터랩이 아무것도 안 돌려준다.

    회귀 불연속으로 쟀다. 자르기 **전** 조각 길이로 붙는 비율을 그리면
    20자까지는 매끄러운 로짓 직선인데(기울기 $-0.132$/자) 넘는 순간
    떨어진다 --- **정확히 20자 164행이 18.3%, 정확히 21자 165행이 0.6%**
    로 한 자 차이에 서른 배다(피셔 $p = 1.1\\times10^{-22}$ · 승산비 29.2).
    20자 이상 전체로는 실제 2.8% 대 직선 예측 11.2% 로 **-8.4%p**.

    그 자료는 판 $-0.0283$ 짜리다(노트 490) --- 두 해 동안 채택한 어떤
    모형 변경보다 여섯 배 크다. 되찾을 양은 **+152행**(만화 $+60$ ·
    세계애니 $+42$ · 펀딩 $+20$ · 모바일 $+18$ · 애니 $+10$).

    **한도 자체는 남긴다** --- 20이 API 제약인지 우리 선택인지 기록이
    없어서, 어느 쪽이든 안전한 쪽으로 고친다."""
    p = str(p or "")
    if len(p) <= n:
        return p
    cut = p[:n].rsplit(" ", 1)[0].strip(" -–—·,.'\"")
    return cut if len(cut) >= 2 else p[:n]


def hangul(s: str) -> int:
    return len(re.findall(r"[가-힣]", str(s)))


def targets(domain: str, root: str = ".") -> list[dict]:
    f, tf, df = SPEC[domain]
    j = json.loads((Path(root) / "data/state" / f).read_text())
    out, seen = [], set()
    for rid, v in j.items():
        kw = clean_kw(v.get(tf))
        d = str(v.get(df) or "")[:10]
        # **한글 문턱은 우리 선택이지 API 제약이 아니었다**(노트 237).
        # 데이터랩은 영문 질의를 그대로 받고 값도 나온다 --- 게임 영문
        # 제목 291건을 받아 195건이 산출됐고, 그 level 이 라벨과 +0.443
        # 으로 한글 질의(+0.381)보다 오히려 세다. 규모는 10분의 1이지만
        # 판정치가 순위 기반이라 상관없다. 덮음이 24.4% → 56.7% 로 오르고
        # F21 이 +0.0027(t=2.37) 얻는다.
        if len(kw) < 2:
            continue
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d) or d < DATALAB_FROM:
            continue
        if kw in seen:                      # 같은 검색어를 두 번 사지 않는다
            continue
        seen.add(kw)
        out.append({"id": rid, "kw": kw, "open": d})
    return out


def collect(domain: str, limit: int | None = None, root: str = ".",
            sleep: float = 0.25) -> dict:
    if not creds():
        return {"오류": "네이버 키 없음"}
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{domain}_trend.json"
    store = json.loads(f.read_text()) if f.exists() else {}
    tg = targets(domain, root)
    todo = [t for t in tg if t["id"] not in store]
    # **수집 대상은 라벨과 무관한 순서로 뽑는다**(노트 554 · 379).
    #
    # ``targets`` 는 레코드 파일 순서대로 돌고 여기서 ``todo[:limit]`` 로
    # 앞을 잘랐다. 그런데 **manga_records.json 은 ``y_popularity`` 로
    # 정렬돼 있다**(파일 순서 ↔ 라벨 순위상관 $-1.0000$) --- 그래서 만화에서
    # ``긁혔나''가 사실상 ``라벨 상위 27\% 인가''가 됐고, 그 마스크가 학습
    # $16\%$ 대 유보 $3\%$ 로 갈려 결측 갈래를 망쳤다(노트 553 이 그 도메인의
    # 검색 축을 통째로 가리는 것으로 끝났다). **wanime 도 완전 단조 정렬**이라
    # 다음 수집이 앞자락을 자르면 같은 일이 벌어진다.
    #
    # 노트 379 가 펀딩에서 같은 것을 이미 겪었다 --- 옛 배치가 목록 상위
    # $19\%$ 라 ``관측됐나''가 곧 ``후원자가 많은가''가 됐고,
    # ``fixaxes.BLOCK`` 으로 축 셋을 통째로 막아야 했다.
    #
    # **씨앗 고정 섞기**로 막는다. 도메인마다 다른 씨앗을 쓰되 재현 가능하게
    # 두어, 중간에 멈췄다 이어 받아도 같은 순서가 나온다.
    if limit:
        rng = random.Random(f"trend_all::{domain}")
        rng.shuffle(todo)
        todo = todo[:limit]
    per = MAX_GROUPS - len(ANCHORS)
    print(f"[{domain}] 대상 {len(tg)} · 남은 {len(todo)} · 요청 {(len(todo)+per-1)//per}회",
          flush=True)
    bad = 0
    for i in range(0, len(todo), per):
        batch = todo[i:i + per]
        lo = min(t["open"] for t in batch)
        start = max(DATALAB_FROM,
                    (date.fromisoformat(lo) - timedelta(days=210)).isoformat())
        # 데이터랩은 미래 날짜를 거부한다("Invalid Date Range"). 아직 안 나온
        # 작품(오픈일이 내일 이후)은 창을 어제까지로 자른다 --- 사전 창이므로
        # 잘려도 뜻은 그대로다.
        end = min(max(t["open"] for t in batch), YESTERDAY)
        if end <= start:
            continue
        # 읽기 타임아웃은 일시적이다. 처음엔 다섯 번에 중단했더니 모바일이
        # 813건 중 260건에서 멈췄다 --- 물러섰다가 세 번까지 다시 친다.
        res, err = None, None
        for attempt in range(3):
            try:
                res = fetch([t["kw"] for t in batch], start, end)
                err = None
                break
            except Exception as e:
                err = e
                time.sleep(1.5 * (attempt + 1))
        if err is not None:
            print(f"  요청 실패 {type(err).__name__} (3회 재시도 후)", flush=True)
            bad += 1
            if bad > 25:
                print("  실패 누적 — 중단", flush=True)
                break
            continue
        if res is None:
            bad += 1
            if bad > 20:
                print("  실패 누적 — 중단(할당량 소진 가능)", flush=True)
                break
            continue
        ar = anchored(res)
        for t in batch:
            store[t["id"]] = {"kw": t["kw"], "open": t["open"],
                              "state": state_features(ar.get(t["kw"], {}), t["open"])}
        f.write_text(json.dumps(store, ensure_ascii=False))
        if (i // per) % 25 == 0:
            ok = sum(1 for v in store.values() if v.get("state"))
            print(f"  {i}/{len(todo)}  상태 산출 {ok}", flush=True)
        time.sleep(sleep)
    ok = sum(1 for v in store.values() if v.get("state"))
    return {"도메인": domain, "수집": len(store), "상태 산출": ok, "저장": str(f)}


def plan(root: str = ".") -> dict:
    per = MAX_GROUPS - len(ANCHORS)
    out = {}
    for d in SPEC:
        tg = targets(d, root)
        f = OUT / f"{d}_trend.json"
        have = len(json.loads(f.read_text())) if f.exists() else 0
        out[d] = {"쓸 수 있는 대상": len(tg), "이미": have,
                  "남은 요청": max(0, (len(tg) - have + per - 1) // per)}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--domain")
    ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    if a.plan or not a.domain:
        p = plan()
        tot = sum(v["남은 요청"] for v in p.values())
        print(json.dumps(p, ensure_ascii=False, indent=1))
        print(f"합계 요청 {tot}회 (일 한도 1,000)")
        return 0
    print(json.dumps(collect(a.domain, a.limit), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
