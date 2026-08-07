"""세계애니(AniList·로마자)에 한국어 제목을 붙인다.

**왜.** 노트 128--129의 검색 축은 한국어 검색이라 제목이 로마자뿐인
만화 · 세계애니는 덮음이 0\\%다. 세계애니는 후행 표본 300건으로 작지 않다.

**막힌 길 둘을 먼저 적는다.** AniList 동의어에 한국어가 있는 것은 2,988건
중 80건뿐이고, 방영 시작일로 붙이면 879건 중 585건이 후보 여럿이라 못
가른다(같은 날 시작한 작품이 흔하다).

**되는 길.** 애니 도메인이 라프텔이라 한국어 제목을 2,073건 들고 있다.
같은 작품이 두 저장소에 다 있으면 옮겨 오면 된다. 제목이 서로 다른
언어이므로 다국어 문장 임베딩으로 잇고, **날짜 창으로 후보를 좁힌 뒤**
유사도 문턱을 건다. AniList 쪽은 `native`(일본어 원제)를 쓰는 것이
로마자보다 낫다 --- 임베딩이 한자·가나와 한글을 잇지, 로마자와 한글을
잇지는 않는다.

**검증이 공짜로 있다.** `data/state/anime_match.json` 에 예전 세션이 만든
AniList$\\leftrightarrow$라프텔 짝 87개가 있다. 거기서 정확도를 재고 문턱을
정한 뒤 나머지에 적용한다.

    python3 -m ingest.ko_titles --check     87쌍으로 정확도만
    python3 -m ingest.ko_titles --emit      전체에 붙여 파일로
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

import numpy as np

D = Path("data/state")
OUT = D / "ko_titles.json"
MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DAY_WIN = 45          # 방영 시작일 창(일)
THRESH = 0.60         # 코사인 문턱 --- --check 로 정한다


def norm(s) -> str:
    s = unicodedata.normalize("NFKC", str(s or "")).strip()
    s = re.sub(r"^\((더빙|자막)\)\s*", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _days(s) -> int | None:
    s = str(s or "")[:10]
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return None
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d).toordinal()


def load_sides(root: str = ".") -> tuple:
    an = json.loads((Path(root) / D / "anime_records.json").read_text())
    wa = json.loads((Path(root) / D / "wanime_records.json").read_text())
    A = [{"id": k, "ko": norm(v.get("title")), "t": _days(v.get("start_date"))}
         for k, v in an.items() if norm(v.get("title"))]
    W = []
    for k, v in wa.items():
        # 일본어 원제가 있으면 그것을 쓴다 --- 로마자는 한글과 안 이어진다
        q = norm(v.get("native")) or norm(v.get("title"))
        if q:
            W.append({"id": k, "q": q, "romaji": norm(v.get("title")),
                      "t": _days(v.get("start_date"))})
    return A, W


def embed(texts: list, cache: str, root: str = "."):
    p = Path(root) / D / cache
    if p.exists():
        Z = np.load(p)
        if len(Z) == len(texts):
            return Z
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer(MODEL)
    Z = np.asarray(m.encode(texts, batch_size=64, normalize_embeddings=True,
                            show_progress_bar=False), float)
    np.save(p, Z)
    return Z


def match(root: str = ".", thresh: float = THRESH, win: int = DAY_WIN,
          mutual: bool = True) -> dict:
    """**상호 최적**만 받는다. 한쪽에서만 최고인 짝은 대개 오답이다 ---
    같은 분기에 나온 다른 작품이 우연히 가까운 경우가 흔하다."""
    A, W = load_sides(root)
    ZA = embed([a["ko"] for a in A], "kot_an.npy", root)
    ZW = embed([w["q"] for w in W], "kot_wa.npy", root)
    ta = np.array([a["t"] if a["t"] is not None else -10**9 for a in A], float)
    tw = np.array([w["t"] if w["t"] is not None else 10**9 for w in W], float)
    best_w = {}                       # 세계애니 → (애니 인덱스, 유사도)
    for i, w in enumerate(W):
        if w["t"] is None:
            continue
        idx = np.where(np.abs(ta - w["t"]) <= win)[0]
        if not len(idx):
            continue
        sims = ZA[idx] @ ZW[i]
        k = int(np.argmax(sims))
        best_w[i] = (int(idx[k]), float(sims[k]))
    best_a = {}                       # 애니 → (세계애니 인덱스, 유사도)
    for j, a in enumerate(A):
        if a["t"] is None:
            continue
        idx = np.where(np.abs(tw - a["t"]) <= win)[0]
        if not len(idx):
            continue
        sims = ZW[idx] @ ZA[j]
        k = int(np.argmax(sims))
        best_a[j] = (int(idx[k]), float(sims[k]))
    out = {}
    for i, (j, s) in best_w.items():
        if s < thresh:
            continue
        if mutual and best_a.get(j, (-1, 0))[0] != i:
            continue
        out[W[i]["id"]] = {"ko": A[j]["ko"], "an_id": A[j]["id"],
                           "sim": round(s, 4), "romaji": W[i]["romaji"]}
    return out


def check(root: str = ".") -> dict:
    """예전 세션의 짝 87개로 문턱을 정한다."""
    p = Path(root) / D / "anime_match.json"
    if not p.exists():
        return {"오류": "anime_match.json 없음"}
    gold = json.loads(p.read_text())
    A, W = load_sides(root)
    wa = json.loads((Path(root) / D / "wanime_records.json").read_text())
    al2w = {}
    for k, v in wa.items():
        al2w.setdefault(str(v.get("media_id")), k)
    truth = {}
    for an_id, g in gold.items():
        wid = al2w.get(str(g.get("al_id")))
        if wid and g.get("lf_title"):
            truth[wid] = norm(g["lf_title"])
    rows = []
    for th, wn in [(0.55, 45), (0.65, 45), (0.75, 45), (0.80, 45),
                   (0.65, 10), (0.75, 10), (0.85, 45), (0.90, 45)]:
        m = match(root, thresh=th, win=wn)
        cov = sum(1 for k in truth if k in m)
        ok = sum(1 for k, v in truth.items()
                 if k in m and norm(m[k]["ko"]) == v)
        rows.append({"문턱": th, "창": wn, "붙은 것": len(m),
                     "정답 중 붙음": f"{cov}/{len(truth)}",
                     "그중 맞음": f"{ok}/{max(cov,1)}",
                     "정확도": round(ok / cov, 3) if cov else None})
    return {"정답쌍": len(truth), "표": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--thresh", type=float, default=THRESH)
    a = ap.parse_args()
    if a.check:
        r = check()
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    m = match(thresh=a.thresh)
    OUT.write_text(json.dumps(m, ensure_ascii=False))
    print(json.dumps({"붙인 것": len(m), "저장": str(OUT),
                      "문턱": a.thresh}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
