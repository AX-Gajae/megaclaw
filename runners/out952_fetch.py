# -*- coding: utf-8 -*-
"""③ 측정 — 원천을 **실제로 내려받는다** (노트 952 [수집]).

🔴 원본은 git 에 안 들어간다(`.gitignore`). 이 러너는 **바이트와 sha256 만** JSON 에 남긴다.
🔴 「받았다」와 「쓸 수 있다」는 둘이다(조항 59) — 계수는 `out952_count.py` 가 따로 한다.

    python3 runners/out952_fetch.py hplt      # 464 shard 중 4개만
    python3 runners/out952_fetch.py steam     # Kaggle 무인증 zip
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UA = "world_model-lab/952 (research; contact alexlee@sweetspot.co.kr)"

HPLT_DIR = ROOT / "data/ingest/hplt_ko"
STEAM_DIR = ROOT / "data/ingest/steam_games"
HPLT_URL = ("https://huggingface.co/datasets/HPLT/HPLT2.0_cleaned/resolve/main/"
            "kor_Hang/train-%05d-of-00464.parquet")
KAGGLE = ("https://www.kaggle.com/api/v1/datasets/download/"
          "fronkongames/steam-games-dataset")

#: 🔴 **손으로 고르지 않았다** — 464 중 앞 4개. 무작위가 아니라 **결정적**이고,
#: 그래서 「어느 shard 를 골랐나」가 재현된다. 편향 가능성은 산출물에 적는다.
SHARDS = [0, 1, 2, 3]


def _dl(url: str, dest: Path, timeout: int = 3600) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = dt.datetime.now()
    h = hashlib.sha256()
    n = 0
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, dest.open("wb") as f:
            declared = r.headers.get("Content-Length")
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
                h.update(b)
                n += len(b)
        sec = (dt.datetime.now() - t0).total_seconds()
        return {"url": url[:120], "파일": str(dest.relative_to(ROOT)),
                "받은바이트": n, "신고바이트": declared,
                "🔴 같은가": (declared is not None and int(declared) == n),
                "sha256": h.hexdigest(), "초": round(sec, 1),
                "MB/s": round(n / 2**20 / max(sec, 1e-9), 2)}
    except Exception as e:                                        # noqa: BLE001
        return {"url": url[:120], "파일": str(dest), "🔴 실패": "%s: %s" % (type(e).__name__, e),
                "받은바이트": n}


def hplt() -> dict:
    out = {"시각": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "원천": "HF HPLT/HPLT2.0_cleaned · config kor_Hang",
           "라이선스": "CC0-1.0 (데이터셋 카드 신고)",
           "🔴 전량이 아니다": "464 shard 중 %d 개 = %s" % (len(SHARDS), SHARDS),
           "🔴 표본 편향": "무작위가 아니라 **앞에서 4개**다. 문서 순서가 원천에서 "
                          "정렬돼 있으면 이 표본은 전체를 대표하지 않는다 — 안 쟀다",
           "파일": []}
    for i in SHARDS:
        d = _dl(HPLT_URL % i, HPLT_DIR / ("train-%05d-of-00464.parquet" % i))
        out["파일"].append(d)
        print(json.dumps(d, ensure_ascii=False), flush=True)
    out["합계바이트"] = sum(f.get("받은바이트", 0) for f in out["파일"])
    out["실패수"] = sum(1 for f in out["파일"] if "🔴 실패" in f)
    return out


def steam() -> dict:
    out = {"시각": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "원천": "Kaggle fronkongames/steam-games-dataset (무인증 api/v1 다운로드)",
           "라이선스": "MIT — 🔴 **업로더 자기신고**다. Valve 가 준 것이 아니다",
           "파일": []}
    d = _dl(KAGGLE, STEAM_DIR / "archive.zip")
    out["파일"].append(d)
    print(json.dumps(d, ensure_ascii=False), flush=True)
    out["합계바이트"] = d.get("받은바이트", 0)
    out["실패수"] = 1 if "🔴 실패" in d else 0
    return out


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = {"코드sha": subprocess.run(["shasum", "-a", "256", __file__],
                                     capture_output=True, text=True).stdout.split()[0]}
    if what in ("hplt", "all"):
        res["hplt"] = hplt()
    if what in ("steam", "all"):
        res["steam"] = steam()
    res["끝시각"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    p = ROOT / ("runners/out952_fetch_%s.json" % what)
    p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", p)
