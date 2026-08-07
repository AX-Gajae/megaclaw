"""노트 774 — **두꺼운 도메인 원천에 안 쓰는 열이 있나.** 읽기만 한다.

판이 쓰는 36열(전 도메인 동일 · 게임만 +4)과 원천 키를 맞춘다. 그리고 **시간
게이트로 보수적으로 가른다** --- 결과성 이름(views·likes·rating·rank·score…)은
출시 뒤에 정해지므로 떨어뜨린다. 애매하면 떨어뜨리고 그 목록도 남긴다.
"""
import json
import re
from collections import Counter
from pathlib import Path

R = Path("/Users/ax/world_model/data/state")
#: 판이 쓰는 36열(노트 774 배선 확인) --- 게임은 +4
USED = {"target_breadth", "venue_prominence", "entry_friction", "media_push",
        "goods_scale", "trend_level", "trend_momentum", "trend_volatility",
        "cal_dow_sin", "cal_dow_cos", "cal_weekend", "cal_month_sin",
        "cal_month_cos", "cal_holiday_gap", "wiki_level", "wiki_momentum",
        "wiki_volatility", "fund_cat", "fund_maxprice", "gen", "grp",
        "mob_advisory", "mob_ngenre", "mob_nlang",
        "price", "age_rating", "ram_gb", "n_category"}
#: 유보 채점 두께 순(노트 767)
DOMS = [("웹툰", "webtoon_records.json", 650), ("애니", "anime_records.json", 606),
        ("펀딩", "funding_records.json", 529), ("모바일", "mobile_records.json", 441),
        ("세계애니", "wanime_records.json", 300), ("만화", "manga_records.json", 258),
        ("게임", "game_records.json", 180), ("도서", "book_records.json", 163)]
#: 🔴 **결과성** --- 출시 뒤에 정해진다(축으로 쓰면 누출). **첫 판이 느슨해서 조였다**:
#: `y_` 접두(라벨) · `favourite`(철자 둘) · `amount`(펀딩 라벨) · `label_basis` 를 더했다.
OUT = re.compile(r"(^y_|view|like|rating|rank|score|comment|favourite|favorite|"
                 r"review|popular|hit|count|total|sum|revenue|sales|sale$|"
                 r"backers|funded|pledge|member|subscriber|follower|award|"
                 r"status|^end|ending|complete|finish|label_basis|^amount$|"
                 # 🔴 **목록을 읽어 더 잡았다** --- 최종 편수는 결과다(오래 갈수록
                 # 성공). 사전등록이 *'애매하면 떨어뜨린다'* 를 적었다.
                 r"truncated|^n_episode$|^n_chapter$|^n_volume$)", re.I)
#: 식별자·군더더기 --- 축이 아니다
ID = re.compile(r"(^id$|_id$|^url|link|image|thumb|slug|key$|_key$|uuid|isbn|"
                r"appid|source|crawl|scrape|fetch|updated|created|_at$|note|raw$)",
                re.I)
#: 🔴 **텍스트·이름** --- T5 가 이미 '도메인 안 전용' 으로 확정했다(노트 719·729).
#: 새 후보로 세면 T5 의 결론을 잊는 것이다.
TXT = re.compile(r"(^title$|^name$|^native$|^english$|^synonyms$|^tags$|^genres$|"
                 r"^genre$|^artists?$|^authors?$|^creator$|^studios?$|"
                 r"^studio_name$|^publishers?$|^developers?$|^langs$|^days$|"
                 r"^category_name$)", re.I)
#: 🔴 **날짜** --- 이미 `cal_*` 여섯 열로 들어가 있다
DATE = re.compile(r"(date$|^air_quarter$|^age$)", re.I)
#: 🔴 **이미 쓰는 것과 같은 것** --- 이름만 다르다
SAME = {"max_price": "fund_maxprice", "min_price": "fund_maxprice(짝)",
        "category": "fund_cat", "n_lang": "mob_nlang", "n_genre": "mob_ngenre",
        "advisory": "mob_advisory", "price_krw": "price", "level": "trend_level(?)"}


def keys_of(obj, out, pre=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            nm = f"{pre}{k}"
            if isinstance(v, dict):
                keys_of(v, out, nm + ".")
            else:
                out[nm] += 1 if (v not in (None, "", [], {})) else 0
                out[nm + "\t전체"] += 1
    elif isinstance(obj, list):
        for x in obj[:400]:
            keys_of(x, out, pre)


def main():
    rep, miss = {}, []
    for dm, fn, w in DOMS:
        p = R / fn
        if not p.exists():
            miss.append(dm)
            continue
        try:
            d = json.loads(p.read_text())
        except Exception as e:
            miss.append(f"{dm}({type(e).__name__})")
            continue
        recs = d if isinstance(d, list) else (
            d.get("records") or d.get("rows") or
            [v for v in d.values() if isinstance(v, dict)])
        if not isinstance(recs, list) or not recs:
            miss.append(f"{dm}(꼴 모름)")
            continue
        cnt = Counter()
        keys_of(recs, cnt)
        cols = {}
        for k in list(cnt):
            if k.endswith("\t전체"):
                continue
            n = cnt.get(k + "\t전체", 0)
            if n:
                cols[k] = round(cnt[k] / n, 3)
        thick = {k: f for k, f in cols.items() if f >= 0.10}
        unused = {k: f for k, f in thick.items()
                  if k.split(".")[-1] not in USED and k not in USED}
        def last(k):
            return k.split(".")[-1]
        loose = {k: f for k, f in unused.items()
                 if not OUT.search(k) and not ID.search(last(k))}
        gated = {k: f for k, f in loose.items()
                 if not TXT.search(last(k)) and not DATE.search(last(k))
                 and last(k) not in SAME}
        dropped_out = sorted(k for k in unused if OUT.search(k))
        dropped_id = sorted(k for k in unused
                            if not OUT.search(k) and ID.search(last(k)))
        dropped_txt = sorted(k for k in loose if TXT.search(last(k)))
        dropped_date = sorted(k for k in loose if not TXT.search(last(k))
                              and DATE.search(last(k)))
        dropped_same = sorted(k for k in loose if not TXT.search(last(k))
                              and not DATE.search(last(k)) and last(k) in SAME)
        rep[dm] = {"유보 가중": w, "레코드": len(recs),
                   "원천 열(채움≥10%)": len(thick), "안 쓰는 열": len(unused),
                   "느슨한 통과(첫 판)": len(loose),
                   "**조인 통과**": len(gated),
                   "**통과 열**": dict(sorted(gated.items(), key=lambda x: -x[1])),
                   "떨어뜨림 결과성": dropped_out[:14],
                   "떨어뜨림 텍스트(T5 확정)": dropped_txt[:12],
                   "떨어뜨림 날짜(cal_*)": dropped_date[:6],
                   "떨어뜨림 이미쓰는것": dropped_same[:8],
                   "떨어뜨림 식별자": dropped_id[:8]}
        print(f"[{dm}] 열 {len(thick)} · 안 씀 {len(unused)} · 느슨 {len(loose)} · "
              f"**조임 {len(gated)}** → {sorted(gated)}", flush=True)
    ok = [d for d in rep if rep[d]["**조인 통과**"] >= 3]
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "🔴 판 주장 아님": "수집 물음이다",
        "원천 미확인": miss or "없음",
        "도메인별": rep,
        "🔴 첫 게이트가 느슨했다": "라벨(y_*·favourites·amount) · 텍스트(T5 가 도메인 안 "
            "전용으로 확정) · 날짜(cal_* 에 있다) · 이미 쓰는 것(max_price=fund_maxprice 등)이 "
            "섞여 있었다 --- 조여서 다시 셌다",
        "**조인 통과 3개 이상인 도메인**": f"{len(ok)}/{len(rep)}",
        "그 목록": ok,
        "판정 (가) 4개 이상": bool(len(ok) >= 4),
        "판정 (나) 1~3개": bool(1 <= len(ok) <= 3),
        "판정 (다) 0개 → 원천이 말랐다": bool(len(ok) == 0),
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
