# -*- coding: utf-8 -*-
"""노트 899 · 갈래 ㄱ — **유보에서 축이 죽는다**를 12도메인 전량으로 다시 세고,
**왜 죽는지**를 ⓐ원천 / ⓑ전처리 / ⓒ분할 세 갈래로 가른다.

사전등록: `docs/prereg_899_axesdie.md` (커밋 `ee2436a43` · 2026-08-10T23:22:56+09:00)

🔴 이 사이클은 **자를 뗐다** — 채택/기각을 안 낸다. 서술 통계만 낸다.

산출물: `runners/out899_axesdie.json`
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                    # noqa: E402
from lab import forms as FORMS                        # noqa: E402
from lab import fixaxes as FX                         # noqa: E402
from lab.harness import Data, MIN_TRAIN               # noqa: E402
import ruler890 as R890                               # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out899_axesdie.json"
T = 2025.0
ALL5 = ("target_breadth", "venue_prominence", "entry_friction",
        "media_push", "goods_scale")

#: 도메인 → (축 json, 날짜 키). `state/tri_domain.py:load_all` 에서 **읽어서** 옮겼다.
SRC = {
    "아이돌":   ("data/state/idol_axes.json",    "debut_date",  "year"),
    "게임":     ("data/state/game_axes.json",    "release_date", "elapsed"),
    "도서":     ("data/state/book_axes.json",    "pub_date",     "elapsed"),
    "펀딩":     ("data/state/funding_axes.json", "start_date",   "year"),
    "웹툰":     ("data/state/webtoon_axes.json", "start_date",   "elapsed"),
    "애니":     ("data/state/anime_axes.json",   "start_date",   "elapsed"),
    "모바일":   ("data/state/mobile_axes.json",  "release_date", "elapsed"),
    "만화":     ("data/state/manga_axes.json",   "start_date",   "elapsed"),
    "세계애니": ("data/state/wanime_axes.json",  "start_date",   "elapsed"),
    "영화":     ("data/state/kobis_axes.json",   "release_date", "year"),
    "시장팝업": ("data/state/market_axes.json",  "period_from",  "year"),
    # 팝업은 `state/slots.load_popup` 이라 파일 한 개가 아니다 --- 따로 처리
}


def sha(p) -> str:
    p = Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else None


def nuniq(v) -> int:
    a = np.asarray(v, float)
    fin = a[np.isfinite(a)]
    n = len(np.unique(fin))
    return n + (1 if (~np.isfinite(a)).any() else 0)


def uniq_rows(X) -> int:
    if X.size == 0:
        return 0
    B = np.ascontiguousarray(np.nan_to_num(np.asarray(X, float), nan=-9.87e18))
    return len(np.unique(B, axis=0))


def build(with_fixaxes: bool):
    """`FF.shell(FF.base())`. with_fixaxes=False 면 fixaxes 단계를 항등으로 만든다."""
    if with_fixaxes:
        return FF.shell(FF.base())
    ap, orient = FX.apply, FX.orient
    FX.apply = lambda d: d
    FX.orient = lambda d: d
    try:
        return FF.shell(FF.base())
    finally:
        FX.apply, FX.orient = ap, orient


def raw_src(d):
    """원천 축 json 에서 ALL5 값/마스크와 날짜 문자열을 **행 순서 그대로** 읽는다."""
    if d not in SRC:
        return None
    p, dkey, _tr = SRC[d]
    p = ROOT / p
    if not p.exists():
        return None
    rows = list(json.loads(p.read_text()).values())
    out = {"n": len(rows), "date_key": dkey,
           "date": [str((r.get(dkey) or ""))[:10] for r in rows]}
    for a in ALL5:
        out[f"v:{a}"] = np.array([float(r["axes"][a]) if a in r.get("axes", {})
                                  else np.nan for r in rows], float)
        out[f"m:{a}"] = np.array([float(r["mask"][a]) if a in r.get("mask", {})
                                  else np.nan for r in rows], float)
    return out


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    res = {
        "노트": 899, "갈래": "ㄱ · 유보에서 축이 죽는다",
        "사전등록": {"파일": "docs/prereg_899_axesdie.md",
                     "커밋": "ee2436a43b35b06a2ae4156afaf346f55efa599d",
                     "시각": "2026-08-10T23:22:56+09:00"},
        "HEAD": head, "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha": {f: sha(ROOT / f) for f in
                     ("runners/axesdie899.py", "lab/forms.py", "lab/harness.py",
                      "lab/fixaxes.py", "state/rank_test.py", "runners/ff753.py",
                      "state/tri_domain.py")},
        "🔴 자": "뗐다 — 채택 문턱 0.00353 을 이번 판정에 쓰지 않는다. 채택/기각 없음",
    }

    print("자료 build (fixaxes 포함) ...", flush=True)
    d0 = build(True)
    doms = sorted(d0.dom)
    W = d0.weights(T)

    # ── 배선 W1·W2 ────────────────────────────────────────────────────
    ref = json.load(open(ROOT / "runners/out890_ruler.json", encoding="utf-8"))
    dig = R890.digest_data(d0)
    wire = {"W1 자료 sha256": dig,
            "W1 890 과 동일": dig == ref["배선"]["ㄱ 자료 sha256"],
            "W2 도메인 수": len(W), "W2 가중 합": int(sum(W.values())),
            "W2 가중 합 == 3775": int(sum(W.values())) == 3775}
    print(json.dumps(wire, ensure_ascii=False), flush=True)
    assert wire["W1 890 과 동일"] and wire["W2 가중 합 == 3775"], "🔴 배선 중단"

    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}

    # ── 씨앗 0 챔피언 적합(board898 의 deploy 갈래를 글자 그대로) ────────
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T)
             & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k)
            tmask[d] = k
    print(f"학습 도메인 {len(train)} · 적합 시작 ...", flush=True)
    f = FF.CLS(seed=0)
    f.fit(Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train}))
    order = list(f.order)
    print(f"🔴 axis_order(common) = {len(order)}열: {order}", flush=True)

    # ── fixaxes 없는 판(ⓑ 판별용) ──────────────────────────────────────
    print("자료 build (fixaxes 없이) ...", flush=True)
    dpre = build(False)

    # ── 도메인별 ──────────────────────────────────────────────────────
    table, why, verdicts = {}, {}, {}
    for d in doms:
        A, M, y, t = d0.dom[d]
        nm = list(d0.names.get(d) or [])
        hold = post[d].copy()
        p = np.asarray(f.predict(d, *d0.slice(d, hold)[:2],
                                 d0.slice(d, hold)[3]), float)
        yh = np.asarray(y, float)[hold]
        ok = np.isfinite(p) & np.isfinite(yh)
        # 채점행 인덱스(전 행 좌표)
        hidx = np.where(hold)[0][ok]
        n = len(hidx)

        Ah, Mh = A[hidx], M[hidx]
        # 모형이 실제로 보는 설계행렬(도메인 원핫 제외)
        F_all = FORMS.DirectPool._feat(Ah, Mh, nm, order)
        Fv = F_all[:, 0::2]        # 값 열
        Fi = F_all[:, 1::2]        # 표시자 열

        nzA = [nm[j] for j in range(A.shape[1]) if nuniq(Ah[:, j]) > 1]
        nzM = [nm[j] for j in range(M.shape[1]) if nuniq(Mh[:, j]) > 1]
        live_feat = [order[j] for j in range(len(order))
                     if nuniq(Fv[:, j]) > 1 or nuniq(Fi[:, j]) > 1]

        table[d] = {
            "채점행": n, "판 가중": int(W.get(d, 0)),
            "채점행 == 판 가중(W3)": n == int(W.get(d, 0)),
            "축 이름 수(티처의 36)": len(nm),
            "고유 특성행 uniq(A)": uniq_rows(Ah),
            "고유 특성행 uniq(A,M)": uniq_rows(np.hstack([Ah, Mh])),
            "🔴 고유 설계행 uniq(_feat)": uniq_rows(F_all),
            "비상수 열 A/이름수": f"{len(nzA)}/{len(nm)}",
            "비상수 열 A": len(nzA), "비상수 열 M": len(nzM),
            "🔴 설계행렬에 닿는 축(order)": len(order),
            "🔴 유보에서 살아 있는 축(order 중)": len(live_feat),
            "살아 있는 축 이름": live_feat,
            "비상수 A 열 이름": nzA,
            "라벨 고유": nuniq(yh[ok]), "예측 고유(씨앗0)": nuniq(p[ok]),
            "동률 비율(씨앗0)": round(1 - nuniq(p[ok]) / n, 4) if n else None,
        }

        # ── 세 갈래 배정 ─────────────────────────────────────────────
        rs = raw_src(d)
        raw_ok = bool(rs and rs["n"] == len(y))
        Ap = dpre.dom[d][0] if d in dpre.dom else None
        Mp = dpre.dom[d][1] if d in dpre.dom else None
        nmp = list(dpre.names.get(d) or []) if d in dpre.dom else []
        buckets = {"ⓐ-0 축 없음(중립 채움)": [], "ⓐ 원천 무변이": [],
                   "ⓑ 전처리(BLOCK)": [], "ⓑ 전처리(그 밖)": [],
                   "ⓒ 유보 분할": [], "모른다": []}
        for j, a in enumerate(nm):
            vcol = np.where(Mh[:, j] > 0, Ah[:, j], 0.5)
            icol = (Mh[:, j] > 0).astype(float)
            if nuniq(vcol) > 1 or nuniq(icol) > 1:
                continue                       # 살아 있다
            allA, allM = A[:, j], M[:, j]
            if (d, a) in FX.BLOCK:
                buckets["ⓑ 전처리(BLOCK)"].append(a); continue
            if np.all(allM == 0) and np.all(allA == 0.5):
                buckets["ⓐ-0 축 없음(중립 채움)"].append(a); continue
            if nuniq(allA) > 1 or nuniq(allM) > 1:
                buckets["ⓒ 유보 분할"].append(a); continue
            # 전 행에서도 상수 --- 전처리인가 원천인가
            if a in nmp:
                jp = nmp.index(a)
                if nuniq(Ap[:, jp]) > 1 or nuniq(Mp[:, jp]) > 1:
                    buckets["ⓑ 전처리(그 밖)"].append(a); continue
            if raw_ok and a in ALL5:
                if nuniq(rs[f"v:{a}"]) > 1 or nuniq(rs[f"m:{a}"]) > 1:
                    buckets["ⓑ 전처리(그 밖)"].append(a); continue
                buckets["ⓐ 원천 무변이"].append(a); continue
            if a in ALL5:
                buckets["모른다"].append(a); continue
            # 원천이 곧 제공자 산출인 파생 열 --- 갈라 낼 원천이 없다
            buckets["모른다"].append(a)
        dead = len(nm) - sum(
            1 for j, a in enumerate(nm)
            if nuniq(np.where(Mh[:, j] > 0, Ah[:, j], 0.5)) > 1
            or nuniq((Mh[:, j] > 0).astype(float)) > 1)
        tot = sum(len(v) for v in buckets.values())
        why[d] = {"죽은 열(모형 관점)": dead, "배정 합": tot,
                  "배정 일치": dead == tot,
                  "원천 json 행 맞음(W4)": raw_ok,
                  "원천 json": SRC.get(d, ("없음(팝업은 slots)",))[0],
                  **{k: {"수": len(v), "이름": v} for k, v in buckets.items()}}
        print(f"  {d}: n={n} 죽은열 {dead}/{len(nm)} · 살아있는축 "
              f"{len(live_feat)}/{len(order)} · 고유설계행 "
              f"{table[d]['🔴 고유 설계행 uniq(_feat)']}", flush=True)

    res["배선"] = wire
    res["배선"]["W3 채점행 == 판 가중 전 도메인"] = all(
        v["채점행 == 판 가중(W3)"] for v in table.values())
    res["배선"]["W4 원천 json 행 맞음"] = {d: why[d]["원천 json 행 맞음(W4)"]
                                          for d in doms}
    res["🔴 axis_order(common)"] = {"열 수": len(order), "이름": order,
                                    "AXIS_MODE": FORMS.AXIS_MODE}
    res["12도메인 축퇴 표"] = table
    res["왜 죽는가 — 세 갈래"] = why

    # ── 판 기여와의 관계 (⚠ 조항 60 — 표본 12 · 회귀선 없음) ────────────
    b898 = json.load(open(ROOT / "runners/out898_board.json", encoding="utf-8"))
    per = b898.get("도메인별", {})
    tot_w = sum(W.values())
    rel = {}
    for d in doms:
        e = per.get(d)
        rel[d] = {
            "살아 있는 축(order 중)": table[d]["🔴 유보에서 살아 있는 축(order 중)"],
            "비상수 A 열": table[d]["비상수 열 A"],
            "고유 설계행/채점행": round(
                table[d]["🔴 고유 설계행 uniq(_feat)"] / table[d]["채점행"], 4),
            "판 가중 w/Σw": round(W[d] / tot_w, 5),
            "도메인 ρ(898 B팔 평균)": e.get("B 평균") if e else "못 읽었다",
            "898 판 기여 Δ": e.get("판 기여 Δ") if e else "못 읽었다",
            "동률 비율(씨앗0)": table[d]["동률 비율(씨앗0)"],
        }
    res["판 기여와의 관계(표·산점만 · 🔴 회귀선 없음 — 조항 60 · n=12)"] = rel
    res["⚠ 조항 60"] = ("표본이 12 다. 회귀선·기울기·R²·p 를 내지 않는다. "
                        "위 표의 좌표만 산점으로 읽는다.")

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n→ {OUT}", flush=True)


if __name__ == "__main__":
    main()
