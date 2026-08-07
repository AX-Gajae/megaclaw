"""개입 텍스트 임베딩 — NN이 '무엇을 하는 팝업인가'를 볼 수 있게 하는 층.

진단(2026-07-27): 구조화 피처 15개만 쓴 NN은 배수오차 3.4배(R²=0.01)로 LLM(1.2배)에 완패.
쌍둥이 해부의 결론("개입이 지배 변수")과 정확히 일치 — NN은 기획서 텍스트를 못 보기 때문.

방법: 문자 n-gram TF-IDF → TruncatedSVD (popga 인코더의 PPMI+SVD와 같은 철학, 추가 비용 0).
한국어 형태소 분석기 없이도 char 2~4gram이면 브랜드·컨셉·체험요소를 충분히 포착한다.

시간 일관성: 벡터라이저는 **학습 폴드에서만 fit** 해야 하나, 여기서는 비지도 어휘 학습이라
라벨 누출이 없다(타깃값을 쓰지 않음). 전체 코퍼스로 fit 후 고정한다.

사용: python3 -m state.text_embed --dim 24
산출: data/state/text_emb_{domain}.npz (record_id 정렬 순서와 dataset.py 순서 일치)
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

OUT = Path("data/state")


def popup_texts() -> tuple[list[str], list[str]]:
    """dataset.popup_rows() 와 **같은 순서·같은 필터**로 텍스트를 낸다."""
    ids, txts = [], []
    for p in sorted(Path("data/records").glob("*.json")):
        r = json.loads(p.read_text())
        if not r["outcome"]["totals"].get("visitors"):
            continue
        iv = r["intervention"]
        c = r["conditions"]
        txts.append(" ".join(str(x) for x in [
            iv.get("concept"), iv.get("brand_name"),
            " ".join(iv.get("experience_elements") or []),
            " ".join(iv.get("promotions") or []),
            " ".join(iv.get("staging_tags") or []),
            (c.get("location") or {}).get("venue_name"),
            (c.get("location") or {}).get("foot_traffic_context"),
        ] if x))
        ids.append(r["record_id"])
    for p in sorted(Path("data/market_records").glob("*.json")):
        m = json.loads(p.read_text())
        if not m["outcome"].get("visitors_total") or m.get("single_event") is False:
            continue
        iv = m.get("intervention") or {}
        c = m["conditions"]
        txts.append(" ".join(str(x) for x in [
            m.get("event_name"), m.get("brand"), m.get("ip_or_collab"), m.get("category"),
            iv.get("concept_description"),
            " ".join(iv.get("experience_elements") or []),
            c.get("venue"), c.get("city"),
        ] if x))
        ids.append(m["market_record_id"])
    return ids, txts


def idol_texts() -> tuple[list[str], list[str]]:
    ids, txts = [], []
    d = Path("data/idol_records")
    if not d.exists():
        return ids, txts
    for p in sorted(d.glob("*.json")):
        r = json.loads(p.read_text())
        if not r.get("chodong"):
            continue
        txts.append(" ".join(str(x) for x in [
            r.get("group_name"), r.get("agency"), r.get("debut_album"),
            r.get("survival_show"), r.get("pre_debut_note"), r.get("notes"),
        ] if x))
        ids.append(r.get("record_id") or p.stem)
    return ids, txts


def build(domain: str, dim: int = 24) -> dict:
    ids, txts = popup_texts() if domain == "popup" else idol_texts()
    if not txts:
        print(json.dumps({"도메인": domain, "표본": 0, "상태": "데이터 없음"}, ensure_ascii=False))
        return {}
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, max_features=30000,
                          sublinear_tf=True)
    M = vec.fit_transform(txts)
    k = min(dim, M.shape[1] - 1, len(txts) - 1)
    svd = TruncatedSVD(n_components=k, random_state=20260727)
    Z = svd.fit_transform(M)
    Z = Z / (np.linalg.norm(Z, axis=1, keepdims=True) + 1e-9)
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(OUT / f"text_emb_{domain}.npz", Z=Z, ids=np.array(ids))
    info = {"도메인": domain, "표본": len(ids), "어휘": M.shape[1], "차원": k,
            "설명분산": round(float(svd.explained_variance_ratio_.sum()), 3)}
    print(json.dumps(info, ensure_ascii=False))
    return info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dim", type=int, default=24)
    ap.add_argument("--domain", default="both", choices=["popup", "idol", "both"])
    args = ap.parse_args()
    for d in (["popup", "idol"] if args.domain == "both" else [args.domain]):
        build(d, args.dim)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
