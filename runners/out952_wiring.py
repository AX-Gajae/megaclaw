# -*- coding: utf-8 -*-
"""② 배선 검사 — 노트 952 [수집].

🔴 **측정이 아니다.** 「받을 수 있는 상태인가」만 본다. 여기서 붉으면 ③ 측정을 시작하지 않는다.

조항 59: HTTP 200 을 성공으로 읽지 않는다. **바이트가 오는가**를 본다.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "runners/out952_wiring.json"

HPLT_TREE = "https://huggingface.co/api/datasets/HPLT/HPLT2.0_cleaned/tree/main/kor_Hang?limit=8"
HPLT_FILE = ("https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned/resolve/main/"
             "kor_Hang/train-00000-of-00464.parquet")
KAGGLE = ("https://www.kaggle.com/api/v1/datasets/download/"
          "fronkongames/steam-games-dataset")
KOPIS = "https://www.kopis.or.kr/openApi/restful/pblprfr"

UA = "world_model-lab/952 (research; contact alexlee@sweetspot.co.kr)"


def _get(url, method="GET", nbytes=0, timeout=60, allow_redirect=True):
    """🔴 헤더 위장 안 한다 — 우리 정체를 밝히는 UA 하나만 쓴다."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    op = urllib.request.build_opener() if allow_redirect else \
        urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        r = op.open(req, timeout=timeout)
        body = r.read(nbytes) if nbytes else b""
        return {"코드": r.status, "헤더길이": r.headers.get("Content-Length"),
                "받은바이트": len(body), "최종url": r.url[:120],
                "머리": body[:16].hex() if body else ""}
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        return {"코드": e.code, "리다이렉트": (loc or "")[:110],
                "본문머리": (e.read(300) or b"").decode("utf-8", "ignore")[:200]}
    except Exception as e:                                       # noqa: BLE001
        return {"코드": None, "🔴 예외": "%s: %s" % (type(e).__name__, e)}


def main() -> int:
    res = {}
    res["시각"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    res["코드sha"] = subprocess.run(
        ["shasum", "-a", "256", __file__], capture_output=True, text=True
    ).stdout.split()[0]

    # ㄱ 도구
    try:
        import pyarrow                                            # noqa: F401
        import pyarrow.parquet                                    # noqa: F401
        pa = pyarrow.__version__
    except Exception as e:                                        # noqa: BLE001
        pa = "🔴 없다: %s" % e
    res["ㄱ 도구"] = {
        "python": sys.version.split()[0],
        "pyarrow": pa,
        "여유디스크GB": round(shutil.disk_usage(str(ROOT)).free / 2**30, 1),
    }

    # ㄴ HPLT — 목록과 **첫 1MB 가 실제로 오는가**
    res["ㄴ HPLT"] = {"목록": _get(HPLT_TREE, nbytes=200),
                     "첫파일 1MB": _get(HPLT_FILE, nbytes=1 << 20, timeout=180)}

    # ㄷ Kaggle — 🔴 리다이렉트를 **안 따라가고** 302 인지 본다(전량 안 받는다)
    res["ㄷ Kaggle"] = {"무인증 302": _get(KAGGLE, allow_redirect=False)}

    # ㄹ KOPIS — 키 없이 부른다. 404 인가 「키 없음」인가
    res["ㄹ KOPIS"] = {"키없이": _get(KOPIS + "?service=&stdate=20260101&eddate=20260131"
                                    "&cpage=1&rows=1", nbytes=600)}

    # ㅁ bq 절대경로 (데몬의 popupsnap 이 매 회차 죽는 자리)
    bq = shutil.which("bq")
    cands = [bq] + [p for p in ("/Users/ax/.local/bin/bq",
                                "/opt/homebrew/bin/bq",
                                "/usr/local/bin/bq",
                                str(Path.home() / "google-cloud-sdk/bin/bq")) if p]
    found = [p for p in cands if p and Path(p).exists()]
    res["ㅁ bq"] = {"which(PATH)": bq, "존재하는후보": found,
                   "🔴 PATH": os.environ.get("PATH", "")[:200]}

    # ㅂ 기존 재고 — 붙일 상대가 실제로 읽히는가
    import gzip
    rev = ROOT / "data/ingest/steam_reviews/reviews.jsonl.gz"
    sao = ROOT / "data/ingest/sao941/pairs.jsonl.gz"
    def _n(p):
        if not p.exists():
            return "🔴 없다"
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception as e:                                    # noqa: BLE001
            return "🔴 못 읽었다: %s" % e
    res["ㅂ 기존재고"] = {"steam_reviews 행": _n(rev), "sao941 쌍": _n(sao)}

    # 판정 — 🔴 코드 200 이 아니라 **바이트**로 본다
    ok_hplt = res["ㄴ HPLT"]["첫파일 1MB"].get("받은바이트", 0) > 500_000
    ok_kag = res["ㄷ Kaggle"]["무인증 302"].get("코드") in (301, 302, 307, 308)
    ok_kop = res["ㄹ KOPIS"]["키없이"].get("코드") is not None
    ok_tool = not str(pa).startswith("🔴")
    res["판정"] = {
        "HPLT 바이트가 온다": ok_hplt,
        "Kaggle 이 서명URL 로 넘긴다": ok_kag,
        "KOPIS 호스트가 응답한다(내용은 ③ 에서 본다)": ok_kop,
        "parquet 을 읽을 도구가 있다": ok_tool,
        "🔴 측정 시작 가능": bool(ok_hplt and ok_kag and ok_tool),
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["판정"]["🔴 측정 시작 가능"] else 1


if __name__ == "__main__":
    sys.exit(main())
