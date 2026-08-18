# -*- coding: utf-8 -*-
"""합의체(council) — 하네스 «안»의 연구 루프.

같은 질문을 «서로 다른 방법론 넷»으로 풀고, 「어느 방법이 이 도메인에서
실제로 맞아 왔나」(검증 성적 리더보드)로 채택한다. 불일치가 크면 그 폭을
답에 «붉게» 싣는다 — 방법들이 갈리는 질문은 그 자체가 정보다.

방법 넷:
  transition   학습된 전이 모형(분위수) — 유일하게 «구간»을 낸다
  knn          같은 도메인 최근접 k 사례의 실제 잔차 곡선 평균 (사례 기반)
  climatology  도메인 평균 잔차 곡선 (계절·도메인 기후값)
  persistence  현 수준 유지 (모든 방법이 이겨야 하는 바닥)

리더보드: 검증(개체 분리 · 1,129) 에서 방법별 «누적 90일 MdAPE» 를 도메인별로
미리 재서 leaderboard.json 에 둔다 — 채택은 «주장»이 아니라 «성적»이다.

씀:
  python3 pretrain/council.py build     # 리더보드 생성(1 회 · 수 초)
  python3 pretrain/council.py ask --curve 150 --domain 웹툰 --date 2026-09-01
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import json
import os

import numpy as np

import pretrain.serve as S

LB_PATH = os.path.join(S.TROUT, "leaderboard.json")
K_NN = 8


# ── 방법 구현 — 전부 «잔차 곡선(log)» 을 낸다 (91,) ───────────────────
def _dom_pools():
    """도메인 → (학습 인덱스 배열)."""
    pools = {}
    for d_i, d in enumerate(S.DOMS):
        pools[d] = np.asarray([i for i in S.DATA.tr if S.DATA.C[i][d_i] == 1.0])
    return pools


def m_persistence(sc, domain, pools):
    return np.zeros(91, dtype=np.float32)


def m_climatology(sc, domain, pools):
    ii = pools[domain]
    if len(ii) == 0:
        return np.zeros(91, dtype=np.float32)
    return S.DATA.R[ii].mean(axis=0)


def m_knn(sc, domain, pools, k=K_NN):
    ii = pools[domain]
    if len(ii) == 0:
        return np.zeros(91, dtype=np.float32)
    d = np.linalg.norm(S.DATA.Sc[ii] - sc[None], axis=1)
    top = ii[np.argsort(d)[:k]]
    return S.DATA.R[top].mean(axis=0)


def m_transition(sc, cond, base):
    q = S._quant_curves(sc, cond, base)          # (91,5) log — base 포함
    return q[:, 2] - base                        # 잔차 q50


def _cum(resid, base):
    return float(np.expm1(resid + base).sum())


# ── 리더보드 ─────────────────────────────────────────────────────────
def build():
    pools = _dom_pools()
    per = {}                                     # domain → method → [ape…]
    for i in S.DATA.va:
        m = S.META[i]
        dom = m["도메인"]
        sc, base = S.DATA.Sc[i], float(S.DATA.base[i])
        true = _cum(S.DATA.R[i], base)
        preds = {
            "transition": _cum(m_transition(sc, S.DATA.C[i], base), base),
            "knn": _cum(m_knn(sc, dom, pools), base),
            "climatology": _cum(m_climatology(sc, dom, pools), base),
            "persistence": _cum(m_persistence(sc, dom, pools), base),
        }
        for k, p in preds.items():
            per.setdefault(dom, {}).setdefault(k, []).append(
                abs(p - true) / max(true, 1.0))
    board = {}
    for dom, methods in sorted(per.items()):
        row = {k: round(float(np.median(v)), 4) for k, v in methods.items()}
        row["n_val"] = len(methods["transition"])
        row["🏆 채택"] = min((k for k in row if k not in ("n_val",)), key=row.get)
        board[dom] = row
    overall = {k: round(float(np.median(
        [a for dom in per.values() for a in dom[k]])), 4)
        for k in ("transition", "knn", "climatology", "persistence")}
    out = {"기준": "검증(개체 분리) 누적 90일 MdAPE — 낮을수록 좋다",
           "전체": overall, "도메인별": board}
    with open(LB_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return out


# ── 질의 — 하네스가 부르는 합의체 ────────────────────────────────────
def ask(curve, domain, date):
    if not os.path.exists(LB_PATH):
        return {"오류": "리더보드가 없다 — 먼저 python3 pretrain/council.py build"}
    lb = json.load(open(LB_PATH, encoding="utf-8"))
    if domain not in S.DOMS:
        return {"오류": "도메인은 %s 중" % S.DOMS}
    vals = [float(v) for v in str(curve).replace(",", " ").split() if v.strip()]
    if len(vals) == 1:
        vals = vals * 90
    if len(vals) != 90:
        return {"오류": "곡선은 90 개(또는 1 개=평탄)"}
    sc, cond, base = S._features_from_raw(vals, domain, str(date))
    pools = _dom_pools()
    preds = {
        "transition": _cum(m_transition(sc, cond, base), base),
        "knn": _cum(m_knn(sc, domain, pools), base),
        "climatology": _cum(m_climatology(sc, domain, pools), base),
        "persistence": _cum(m_persistence(sc, domain, pools), base),
    }
    row = lb["도메인별"].get(domain, {})
    champ = row.get("🏆 채택", "transition")
    vals_only = [v for v in preds.values()]
    spread = (max(vals_only) - min(vals_only)) / max(preds[champ], 1.0)
    # 구간은 transition 만 낸다 — 채택이 다른 방법이면 «점 + transition 구간 참고»
    q = S._quant_curves(sc, cond, base)
    cum = np.expm1(q).cumsum(axis=0)
    return {
        "방법별 예측(누적 90일)": {k: int(v) for k, v in preds.items()},
        "🏆 채택": {"방법": champ, "값": int(preds[champ]),
                  "근거(이 도메인 검증 MdAPE)": {k: row.get(k) for k in preds}},
        "구간(transition · 참고)": {"q05": int(cum[90, 0]), "q95": int(cum[90, 4])},
        "🔴 불일치 폭": round(spread, 3),
        "불일치 읽는 법": ("0.15 넘으면 방법들이 갈리는 질문이다 — 답을 넓게 잡고 "
                       "재판단 시점(wm_risk)을 꼭 확인하라"),
        "⚠": __import__("pretrain.wm_tools", fromlist=["CAVEAT"]).CAVEAT}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build")
    q = sub.add_parser("ask")
    q.add_argument("--curve", required=True)
    q.add_argument("--domain", required=True)
    q.add_argument("--date", required=True)
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    else:
        print(json.dumps(ask(a.curve, a.domain, a.date), ensure_ascii=False, indent=1))
