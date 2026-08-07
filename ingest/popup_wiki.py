"""팝업 IP의 외부 인지도를 위키백과에서 잰다 --- 사람 태깅을 객관 지표로 바꾼다.

노트 45와 48에서 배선이 두 번 소진됐다(새 눈금에서도 후보 63개 중 문턱 통과 0).
남은 것은 새 측정뿐이고, 가장 값진 자리가 **팝업**이다.

  · 유일한 실제 대상이다. 다른 다섯 도메인은 팝업을 예측하려고 있다.
  · 표본이 75건으로 가장 작고 귀무분포가 가장 넓다(노트 43).
  · 다섯 축이 전부 사람이 기획서를 읽고 매긴 것이다. 객관 지표로 바꾸면
    태깅 비용이 줄고 새 레코드를 자동으로 채울 수 있다.

메타에 IP 이름이 75건 전부 있다(`신카이마코토`, `보노보노`, `용과같이`...).
위키백과 API는 키가 필요 없고 셋을 준다.

    존재 여부   문서가 있나
    문서 크기   바이트
    언어판 수   몇 개 언어로 문서가 있나 --- 국제적 인지도

**시간 인과를 지킨다.** 현재 문서 크기를 쓰면 안 된다 --- 팝업이 흥행하면
문서가 늘어나므로 노트 21의 DLC 수와 같은 역인과가 된다. 위키백과는 특정
시점의 판을 조회할 수 있으므로 **개장일 직전 판의 크기**를 쓴다.

    action=query&prop=revisions&rvstart=<개장일>&rvdir=older&rvlimit=1&rvprop=size

언어판 수는 시점 조회가 안 되므로 현재 값을 쓰되, 그 한계를 기록한다.

**미상 처리.** IP 이름이 '미상'인 레코드가 있다. 0으로 채우지 않고 마스크 0으로
남긴다(노트 35·37에서 두 번 당한 실수).

사용: python3 -m ingest.popup_wiki
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

OUT = Path("data/state/popup_wiki.json")
CACHE = Path("data/state/cache_wiki")
UA = {"User-Agent": "worldmodel-research/1.0 (research; contact via github)"}
DELAY = 0.35
SKIP = {"미상", "없음", "-", ""}


def _api(lang: str, params: dict, key: str) -> dict | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (key + ".json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except json.JSONDecodeError:
            f.unlink()
    url = (f"https://{lang}.wikipedia.org/w/api.php?"
           + urllib.parse.urlencode({**params, "format": "json"}))
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=20) as r:
                d = json.loads(r.read().decode("utf-8", "ignore"))
            time.sleep(DELAY)
            f.write_text(json.dumps(d, ensure_ascii=False))
            return d
        except (urllib.error.HTTPError, urllib.error.URLError, OSError,
                TimeoutError, json.JSONDecodeError):
            time.sleep(DELAY * (4 ** attempt))
    return None


def _pages(d):
    return list((((d or {}).get("query") or {}).get("pages") or {}).items())


def lookup(name: str, on_date: str) -> dict:
    """IP 하나. 개장일 직전 판의 크기와 현재 언어판 수를 낸다."""
    slug = urllib.parse.quote(name.replace(" ", "_"))[:80]
    out = {"ip": name, "exists": False, "size_at": None, "size_now": None,
           "langs": None, "lang": None}
    for lang in ("ko", "en"):
        d = _api(lang, {"action": "query", "titles": name,
                        "prop": "info|langlinks", "lllimit": "500"},
                 f"{lang}_{slug}")
        pg = _pages(d)
        if not pg:
            continue
        for pid, v in pg:
            if pid == "-1":
                continue
            out.update({"exists": True, "lang": lang, "title": v.get("title"),
                        "size_now": v.get("length"),
                        "langs": len(v.get("langlinks") or [])})
            # 개장일 직전 판
            r = _api(lang, {"action": "query", "titles": name, "prop": "revisions",
                            "rvstart": f"{on_date}T00:00:00Z", "rvdir": "older",
                            "rvlimit": "1", "rvprop": "size|timestamp"},
                     f"{lang}rev_{slug}_{on_date}")
            rp = _pages(r)
            for _, rv in (rp or []):
                revs = rv.get("revisions") or []
                if revs:
                    out["size_at"] = revs[0].get("size")
                    out["rev_ts"] = revs[0].get("timestamp")
            return out
    return out


def main() -> int:
    import glob

    from state.own_axes import _popup_keep
    d = np.load("data/state/popup_v2.npz", allow_pickle=True)
    cols = [str(c) for c in d["names"]]
    keep = _popup_keep(d, cols)
    meta = json.loads(Path("data/state/popup_v2_meta.json").read_text())
    sel = [m for m, k in zip(meta, keep) if k]

    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    for i, m in enumerate(sel, 1):
        rid, ip, dt = m["id"], (m.get("ip") or "").strip(), (m.get("date") or "")[:10]
        if rid in prev:
            continue
        if not ip or ip in SKIP or not dt:
            prev[rid] = {"ip": ip, "exists": False, "skip": True}
            continue
        prev[rid] = lookup(ip, dt)
        if i % 15 == 0:
            OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))
            print(f"  {i}/{len(sel)} · 문서 있음 "
                  f"{sum(1 for v in prev.values() if v.get('exists'))}")
    OUT.write_text(json.dumps(prev, ensure_ascii=False, indent=1))

    ex = [v for v in prev.values() if v.get("exists")]
    print(f"\n팝업 {len(prev)}건 중 위키백과 문서 있음 {len(ex)}건 "
          f"({len(ex)/max(1,len(prev)):.0%})")
    sa = [v["size_at"] for v in ex if v.get("size_at")]
    print(f"  개장 시점 판 크기 확보 {len(sa)}건  "
          f"중앙 {int(np.median(sa)) if sa else 0:,}바이트")
    lg = [v["langs"] for v in ex if v.get("langs") is not None]
    print(f"  언어판 수 중앙 {int(np.median(lg)) if lg else 0}개  "
          f"최대 {max(lg) if lg else 0}개")
    print(f"  한국어판 {sum(1 for v in ex if v.get('lang')=='ko')} · "
          f"영어판만 {sum(1 for v in ex if v.get('lang')=='en')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
