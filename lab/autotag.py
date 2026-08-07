"""과제 77 --- 기획서에서 축을 자동으로 매긴다.

**왜 지금인가.** 두 갈래가 같은 곳을 가리켰다. 노트 126의 F8은 ``같은 자질에
비선형을 얹어도 안 오른다''(병목은 축이다)고 했고, 같은 노트의 F11은
``한 도메인에만 있는 축은 도움이 안 된다''고 했다. 남는 처방은 하나다 ---
**전 도메인이 공유하는 축의 빈칸을 메운다.** 노트 124가 그 빈칸을 셌다.
팝업 레코드 380건 중 열 축이 매겨진 것은 95건이고 나머지는 전부 상수 2.0이다.

**규약(노트 87 · 117의 교훈).** 태거는 라벨을 **한 번도 보지 않는다.**
읽는 것은 ``intervention'' · ``conditions'' · ``entities'' 뿐이고 ``outcome''
은 열지 않는다. 코드로 강제한다(PLAN_ONLY).

    python3 -m lab.autotag --cv        95건으로 교차검증만
    python3 -m lab.autotag --emit      나머지에 축을 매겨 파일로
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

REC = Path("data/records")
MKT = Path("data/market_records")
OUT = Path("data/state/autotag_popup.json")
AXES = ["experience_density", "goods_scale", "photo_zones", "collab_strength",
        "ip_awareness", "target_breadth", "entry_friction", "media_push",
        "season_fit", "venue_prominence"]
PLAN_ONLY = ("intervention", "conditions", "entities", "docs")  # outcome 은 안 연다
DOC_KINDS = ("계약서", "정산", "견적", "기획", "제안", "리포트", "도면", "발주")
VENUE1 = ("더현대", "롯데월드몰", "스타필드", "코엑스", "신세계", "잠실")
VENUE2 = ("성수", "홍대", "강남", "한남", "명동", "압구정", "여의도")


def read_plan(p: Path) -> dict:
    """레코드에서 **기획 시점에 알 수 있는 것만** 꺼낸다.

    outcome 을 아예 딕셔너리에서 지우고 넘긴다 --- 실수로도 못 보게."""
    r = json.loads(p.read_text())
    return {k: r.get(k) for k in PLAN_ONLY} | {"record_id": r.get("record_id")}


def doc(pl: dict) -> str:
    iv = pl.get("intervention") or {}
    cd = pl.get("conditions") or {}
    lo = (cd.get("location") or {})
    bits = [iv.get("concept") or "", iv.get("brand_name") or "",
            " ".join(iv.get("experience_elements") or []),
            " ".join(iv.get("promotions") or []),
            " ".join(iv.get("staging_tags") or []),
            lo.get("venue_name") or "", lo.get("venue_type") or "",
            cd.get("season") or ""]
    # 문서 자체는 드라이브에 있고 여기엔 제목과 종류만 있다. 그래도
    # ``상품화권 계약서''와 ``견적서''는 기획의 규모를 말한다.
    for d in (pl.get("docs") or []):
        bits.append(f"{d.get('kind') or ''} {d.get('title') or ''}")
    return " · ".join(b for b in bits if b and b.strip())


def numeric(pl: dict) -> np.ndarray:
    """세는 것으로 되는 것들. 임베딩이 놓치는 규모 신호를 붙인다."""
    iv = pl.get("intervention") or {}
    cd = pl.get("conditions") or {}
    lo = (cd.get("location") or {})
    per = (cd.get("period") or {})
    vn = (lo.get("venue_name") or "")
    tier = 1.0 if any(v in vn for v in VENUE1) else (
        2.0 if any(v in vn for v in VENUE2) else 3.0)
    ar = cd.get("area_pyeong")
    txt = doc(pl)
    return np.array([
        len(iv.get("experience_elements") or []),
        len(iv.get("promotions") or []),
        len(iv.get("staging_tags") or []),
        np.log1p(float(ar)) if ar else 0.0, 1.0 if ar else 0.0,
        float(per.get("days") or 0), 1.0 if per.get("days") else 0.0,
        tier,
        len(txt), len(re.findall(r"[가-힣]{2,}", txt)),
        1.0 if ("콜라보" in txt or " X " in txt or "×" in txt) else 0.0,
        1.0 if "굿즈" in txt else 0.0,
        1.0 if ("포토" in txt or "포토존" in txt) else 0.0,
        1.0 if ("사전예약" in txt or "예약" in txt or "웨이팅" in txt) else 0.0,
        1.0 if ("무료" in txt or "누구나" in txt) else 0.0,
        len(pl.get("docs") or []),
        *[float(sum(1 for d in (pl.get("docs") or [])
                    if k in ((d.get("kind") or "") + (d.get("title") or ""))))
          for k in DOC_KINDS],
    ], float)


def read_market(p: Path) -> dict:
    """시장 레코드를 내부 레코드 모양으로 옮긴다.

    **여기가 이 태거의 한계다.** 학습은 내부 레코드(계약서에서 뽑은 것)로
    하고 적용은 시장 레코드(기사에서 뽑은 것)에 한다. 글의 결이 다르므로
    교차검증 수치가 그대로 옮겨간다고 볼 수 없다. 시장 레코드 쪽에는 매겨진
    축이 하나도 없어서 직접 잴 방법도 없다. 대신 하네스로 **간접**으로
    잰다 --- 축을 채운 것과 마스크로 비운 것을 나란히 붙여 본다."""
    r = json.loads(p.read_text())
    iv = r.get("intervention") or {}
    cd = r.get("conditions") or {}
    return {"record_id": r.get("market_record_id"),
            "intervention": {"concept": iv.get("concept_description"),
                             "brand_name": r.get("brand") or "",
                             "experience_elements": iv.get("experience_elements") or [],
                             "promotions": iv.get("promotions") or [],
                             "staging_tags": []},
            "conditions": {"location": {"venue_name": cd.get("venue"),
                                        "venue_type": cd.get("venue_type")},
                           "area_pyeong": cd.get("area_pyeong"),
                           "season": r.get("category") or "",
                           "period": {"days": _days(cd)}},
            "entities": {}, "docs": []}


def _days(cd: dict):
    a, b = cd.get("period_from"), cd.get("period_to")
    if not (a and b):
        return None
    try:
        from datetime import date
        f = lambda s: date(*[int(x) for x in str(s)[:10].split("-")])
        return (f(b) - f(a)).days + 1
    except Exception:
        return None


def load(root: str = ".", market: bool = True) -> tuple:
    """(레코드 id, 문서, 수치, 축값 또는 None)"""
    ids, docs, nums, ys = [], [], [], []
    src = [(p, read_plan) for p in sorted((Path(root) / REC).glob("*.json"))]
    if market:
        src += [(p, read_market)
                for p in sorted((Path(root) / MKT).glob("*.json"))]
    for p, rd in src:
        pl = rd(p)
        iv = pl.get("intervention") or {}
        at = iv.get("attributes") or {}
        d = doc(pl)
        if not d.strip():
            continue
        y = ([float(at[a]) for a in AXES]
             if all(isinstance(at.get(a), (int, float)) for a in AXES) else None)
        if not pl.get("record_id"):
            continue
        ids.append(pl["record_id"]); docs.append(d)
        nums.append(numeric(pl)); ys.append(y)
    return ids, docs, np.array(nums), ys


def embed(docs: list, root: str = ".", cache: str = "data/state/autotag_emb.npy"):
    cp = Path(root) / cache
    if cp.exists():
        Z = np.load(cp)
        if len(Z) == len(docs):
            return Z
    from sentence_transformers import SentenceTransformer
    m = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    Z = np.asarray(m.encode(docs, batch_size=32, show_progress_bar=False), float)
    cp.parent.mkdir(parents=True, exist_ok=True)
    np.save(cp, Z)
    return Z


def features(Z: np.ndarray, N: np.ndarray, k: int = 24, fit=None):
    """임베딩을 k 차원으로 줄이고 수치를 붙인다. n=95 에 384 차원은 못 쓴다."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler
    if fit is None:
        pca = PCA(n_components=min(k, Z.shape[1], len(Z) - 1)).fit(Z)
        sc = StandardScaler().fit(np.column_stack([pca.transform(Z), N]))
        fit = (pca, sc)
    pca, sc = fit
    return sc.transform(np.column_stack([pca.transform(Z), N])), fit


def cv(root: str = ".", alpha: float = 12.0, k: int = 24, folds: int = 5) -> dict:
    """95건으로 교차검증. **축마다** 얼마나 맞는지 정직하게 본다."""
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import KFold
    from scipy.stats import spearmanr
    ids, docs, N, ys = load(root)
    Z = embed(docs, root)
    lab = [i for i, y in enumerate(ys) if y is not None]
    Y = np.array([ys[i] for i in lab])
    Zl, Nl = Z[lab], N[lab]
    out = {}
    kf = KFold(folds, shuffle=True, random_state=20260729)
    P = np.zeros_like(Y)
    for tr, te in kf.split(Zl):
        X, ft = features(Zl[tr], Nl[tr], k)
        Xt, _ = features(Zl[te], Nl[te], k, ft)
        for j in range(len(AXES)):
            P[te, j] = Ridge(alpha=alpha).fit(X, Y[tr, j]).predict(Xt)
    for j, a in enumerate(AXES):
        r = spearmanr(P[:, j], Y[:, j]).correlation
        out[a] = {"rho": float(r) if np.isfinite(r) else 0.0,
                  "mae": float(np.mean(np.abs(np.clip(P[:, j], 0, 4) - Y[:, j]))),
                  "sd": float(Y[:, j].std()),
                  "const": bool(Y[:, j].std() < 1e-9)}
    out["_n"] = len(lab)
    out["_mean_rho"] = float(np.mean([v["rho"] for a, v in out.items()
                                      if not a.startswith("_")]))
    return out


def emit(root: str = ".", alpha: float = 12.0, k: int = 24) -> dict:
    """95건으로 학습해 나머지에 매긴다. 라벨은 여전히 안 본다."""
    from sklearn.linear_model import Ridge
    ids, docs, N, ys = load(root)
    Z = embed(docs, root)
    lab = [i for i, y in enumerate(ys) if y is not None]
    un = [i for i, y in enumerate(ys) if y is None]
    Y = np.array([ys[i] for i in lab])
    X, ft = features(Z[lab], N[lab], k)
    Xu, _ = features(Z[un], N[un], k, ft)
    pred = {}
    for j, a in enumerate(AXES):
        p = Ridge(alpha=alpha).fit(X, Y[:, j]).predict(Xu)
        pred[a] = np.clip(p, 0, 4)
    res = {"axes": AXES, "n_train": len(lab), "n_pred": len(un),
           "alpha": alpha, "k": k,
           "cv": cv(root, alpha, k),
           "pred": {ids[i]: {a: float(pred[a][r]) for a in AXES}
                    for r, i in enumerate(un)},
           "train": {ids[i]: {a: float(Y[r, j]) for j, a in enumerate(AXES)}
                     for r, i in enumerate(lab)}}
    (Path(root) / OUT).write_text(json.dumps(res, ensure_ascii=False))
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", action="store_true")
    ap.add_argument("--emit", action="store_true")
    ap.add_argument("--alpha", type=float, default=12.0)
    ap.add_argument("--k", type=int, default=24)
    a = ap.parse_args()
    if a.emit:
        r = emit(alpha=a.alpha, k=a.k)
        print(json.dumps({"학습": r["n_train"], "매김": r["n_pred"],
                          "교차검증 평균 rho": round(r["cv"]["_mean_rho"], 4)},
                         ensure_ascii=False), flush=True)
    else:
        c = cv(alpha=a.alpha, k=a.k)
        for ax in AXES:
            v = c[ax]
            print(f"{ax:20s} rho {v['rho']:+.3f}  MAE {v['mae']:.3f}"
                  f"  라벨 표준편차 {v['sd']:.3f}")
        print(f"\nn={c['_n']}  평균 rho {c['_mean_rho']:+.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
