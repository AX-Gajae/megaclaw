"""노트 770 — **L(g,event) 를 재기 전에 판정력을 잰다.** 판 적합 없음.

노트 688 이 사각 ①에 *'라벨이 얇다 --- 라벨 있는 행수를 먼저 찍고 그 수로 판정력을
적는다'* 를 적었다. 행수를 찍었더니 방문객 라벨 66 건이다. **그래서 회귀보다 판정력이
먼저다.**

시군구는 손으로 표를 쓰지 않고 기존 해석기(`ingest.visitors.sgg_index` ·
`hood_sgg` · `city_sgg`)를 쓴다 --- 노트 661·662 가 시장팝업에서 쓴 것과 같은 길이다.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from state import fieldmodel as F

REC = Path("/Users/ax/world_model/data/records")
WIN = 30            # 오픈 이전 30일
FB = 90             # 되먹임 통제: 직전 90일 같은 동네 팝업 수
BOOT = 400
RNG = np.random.default_rng(770)
#: 노트 648 이 잰 event → g 자국의 중앙값(장 눈금) --- 비교 기준
FOOT = 0.0087


def resolve(idx, loc):
    """시군구 코드. **기존 해석기만 쓴다**(손 표 없음)."""
    from ingest.visitors import city_sgg, hood_sgg
    dist = loc.get("district") or ""
    city = loc.get("city") or ""
    ven = loc.get("venue_name") or ""
    # ① 시군구 이름이 문자열에 직접 있나
    for txt in (dist, ven, city):
        if not isinstance(txt, str):
            continue
        for (_sd, nm), cd in idx.items():
            if nm and len(nm) >= 2 and nm in txt:
                return cd, "시군구이름"
    # ② 동 이름 표
    for txt in (dist, ven):
        c = hood_sgg(txt, city, idx)
        if c:
            return c, "동이름"
    # ③ city 만으로 정해지는 곳(광역시는 안 붙인다 --- 노트 662)
    c = city_sgg(city, idx)
    if c:
        return c, "city만"
    return None, "위치없음"


def main():
    from ingest.visitors import sgg_index
    idx = sgg_index()
    codes, days, X = F.field(stats_end=F.TRAIN_END)
    ci = {c: i for i, c in enumerate(codes)}
    dnum = np.array([int(d) for d in days])

    rows, why = [], {}
    for p in sorted(REC.glob("*.json")):
        d = json.loads(p.read_text())
        cond = d.get("conditions") or {}
        loc = cond.get("location") or {}
        per = cond.get("period") or {}
        tot = (d.get("outcome") or {}).get("totals") or {}
        vis, frm = tot.get("visitors"), per.get("from")
        cd, how = resolve(idx, loc)
        why[how] = why.get(how, 0) + 1
        if not (vis and frm and cd and cd in ci):
            continue
        f = int(frm.replace("-", ""))
        m = (dnum < f) & (dnum >= f - WIN * 100 // 100 - 0)   # 자리표시
        rows.append({"id": d.get("record_id"), "cd": cd, "frm": f,
                     "vis": float(vis), "how": how,
                     "brand": (d.get("intervention") or {}).get("brand_name"),
                     "days": (per.get("days") or 0),
                     "store": ((cond.get("scale") or {}).get("store_count") or 0)})
    # g = 오픈 이전 30일 그 동네 장의 평균 (그 동네 안 편차는 뒤에서 뺀다)
    for r in rows:
        i = ci[r["cd"]]
        sel = (dnum < r["frm"]) & (dnum >= r["frm"] - 100 * 0 - 0)
        # 날짜 인덱스로 30일 창을 잡는다
        pos = np.searchsorted(dnum, r["frm"])
        lo = max(0, pos - WIN)
        v = X[i, lo:pos]
        r["g"] = float(np.nanmean(v)) if np.isfinite(v).sum() >= 10 else np.nan
        # 되먹임 통제: 직전 90일 같은 동네 팝업 수
        # **날짜 산술을 제대로 한다** --- YYYYMMDD 정수 차는 날 수가 아니다
        import datetime as _dt
        def _d(x):
            x = int(x)
            return _dt.date(x // 10000, (x // 100) % 100, x % 100)
        me = _d(r["frm"])
        r["prior"] = sum(1 for q in rows if q["cd"] == r["cd"]
                         and 0 < (me - _d(q["frm"])).days <= FB)
    good = [r for r in rows if np.isfinite(r["g"])]
    from collections import Counter
    cnt = Counter(r["cd"] for r in good)
    fe = [r for r in good if cnt[r["cd"]] >= 2]          # 동네 고정이 가능한 행
    print(json.dumps({
        "해석 방법 분포": why,
        "라벨+시군구+기간": len(rows), "**g 까지 있는 행**": len(good),
        "**동네 고정 가능(같은 시군구 2건+)**": len(fe),
        "시군구 수": len({r["cd"] for r in fe}),
        "시군구별": {c: n for c, n in cnt.most_common() if n >= 2},
    }, ensure_ascii=False), flush=True)
    if len(fe) < 12:
        print(json.dumps({"중단": f"행 {len(fe)} --- 회귀 불가"},
                         ensure_ascii=False), flush=True)
        return

    # ── 설계행렬 --- 명세 둘(갑=사전등록 · 을=축소)
    y = np.log10(np.array([r["vis"] for r in fe]))
    g = np.array([r["g"] for r in fe])
    sc = np.log10(1 + np.array([max(r["store"], 1) for r in fe], float))
    mo = np.array([(r["frm"] // 100) % 100 for r in fe])
    cds = sorted({r["cd"] for r in fe})
    pri = np.array([r["prior"] for r in fe], float)
    gd = g.copy()
    for c in cds:
        m = np.array([r["cd"] == c for r in fe])
        gd[m] = g[m] - g[m].mean()
    sdg = float(np.std(gd))
    FE = [np.ones(len(fe))] + [np.array([1.0 if r["cd"] == c else 0.0 for r in fe])
                               for c in cds[1:]]
    MO = [(mo == mm).astype(float) for mm in sorted(set(mo.tolist()))[1:]]
    TAIL = [pri, gd, gd * (sc - sc.mean())]

    def build(idxs, use_mo):
        """**뽑기마다 설계를 다시 짓는다** --- 빠진 시군구의 더미를 넣으면 계급이 떤다."""
        sub = [fe[i] for i in idxs]
        cs = sorted({r["cd"] for r in sub})
        cols = [np.ones(len(idxs))]
        for c in cs[1:]:
            cols.append(np.array([1.0 if r["cd"] == c else 0.0 for r in sub]))
        if use_mo:
            ms = sorted({(r["frm"] // 100) % 100 for r in sub})
            for mm in ms[1:]:
                cols.append(np.array([1.0 if (r["frm"] // 100) % 100 == mm else 0.0
                                      for r in sub]))
        cols += [pri[idxs], gd[idxs], (gd * (sc - sc.mean()))[idxs]]
        return np.column_stack(cols)

    def fit(use_mo, tag):
        allid = np.arange(len(fe))
        A = build(allid, use_mo)
        k = A.shape[1]; rank = int(np.linalg.matrix_rank(A))
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        res = y - A @ beta
        dof = len(fe) - rank
        s2 = float(res @ res) / max(dof, 1)
        bs, skipped = [], 0
        for _ in range(BOOT):
            pick = RNG.choice(cds, size=len(cds), replace=True)
            ii = np.concatenate([np.flatnonzero([r["cd"] == c for r in fe])
                                 for c in pick])
            Ai = build(ii, use_mo)
            if len(ii) <= Ai.shape[1] + 1 or int(np.linalg.matrix_rank(Ai)) < Ai.shape[1]:
                skipped += 1
                continue
            try:
                b2, *_ = np.linalg.lstsq(Ai, y[ii], rcond=None)
            except Exception:
                skipped += 1
                continue
            if np.all(np.isfinite(b2)):
                bs.append([b2[-2], b2[-1]])
        bs = np.array(bs) if bs else np.zeros((0, 2))
        sa = float(np.std(bs[:, 0], ddof=1)) if len(bs) > 20 else float("nan")
        # 🔴 **폭발한 뽑기가 SD 를 지배하므로 강건 통계도 같이 낸다**(규약 25 계열).
        if len(bs) > 20:
            q = np.percentile(bs[:, 0], [5, 25, 50, 75, 95])
            iqr = float(q[3] - q[1])
            rob = {"부트 a 중앙": round(float(q[2]), 3),
                   "부트 a 5~95%": [round(float(q[0]), 2), round(float(q[4]), 2)],
                   "**부트 a IQR**": round(iqr, 3),
                   "**MDE 강건(1.35×IQR×SD(g))**": round(1.35 * iqr * sdg, 4)}
        else:
            rob = {}
        return {"명세": tag, **rob, "모수": k, "**계급**": rank,
                "**계급 부족**": int(k - rank), "자유도": int(dof),
                "a": round(float(beta[-2]), 3), "b": round(float(beta[-1]), 3),
                "**a × SD(g)**": round(float(beta[-2]) * sdg, 4),
                "클러스터 부트 SE(a)": round(sa, 3) if np.isfinite(sa) else None,
                "**MDE(a × SD(g)) = 2×SE×SD(g)**":
                    round(2 * sa * sdg, 4) if np.isfinite(sa) else None,
                "부트 표본": int(len(bs)), "버린 뽑기": skipped,
                "잔차 SD": round(float(np.sqrt(s2)), 4)}

    gap = fit(True, "갑 --- 사전등록(월 더미 포함)")
    eul = fit(False, "을 --- 축소(월 더미 없음)")
    PRAC = 0.041                     # 실무 문턱: 방문객 10% 차 = 0.041 log10
    mde = eul["**MDE(a × SD(g)) = 2×SE×SD(g)**"]
    need = (mde / PRAC) ** 2 * len(fe) if mde else None
    print("=== 모아서 ===", flush=True)
    print(json.dumps({
        "🔴 판 주장 아님": "팝업 도메인만 --- 장소가 있는 유일한 곳",
        "행": len(fe), "시군구": len(cds), "g 동네안 SD": round(sdg, 4),
        "라벨 SD(log10)": round(float(np.std(y)), 4),
        "**갑(사전등록)**": gap, "**을(축소 · 판정용)**": eul,
        "**실무 문턱(방문객 10% = log10)**": PRAC,
        "**MDE / 실무 문턱**": round(mde / PRAC, 1) if mde else None,
        "**MDE 강건 / 실무 문턱**":
            round(eul["**MDE 강건(1.35×IQR×SD(g))**"] / PRAC, 1)
            if eul.get("**MDE 강건(1.35×IQR×SD(g))**") else None,
        "판정 (가) MDE ≤ 0.041 → 회귀로 결론": bool(mde is not None and mde <= PRAC),
        "판정 (나) MDE > 0.041 → 판정 불가": bool(mde is not None and mde > PRAC),
        "판정 강건 --- MDE 강건 > 실무 문턱":
            bool(eul.get("**MDE 강건(1.35×IQR×SD(g))**", 0) > PRAC),
        "**실무 문턱에서 가르려면 필요한 행수(강건 MDE 로)**":
            int((eul["**MDE 강건(1.35×IQR×SD(g))**"] / PRAC) ** 2 * len(fe))
            if eul.get("**MDE 강건(1.35×IQR×SD(g))**") else None,
        "클러스터 크기": {c: int(sum(1 for r in fe if r["cd"] == c)) for c in cds},
        "**g 동네안 SD 가 0.005 미만인 시군구**":
            [c for c in cds
             if float(np.std([r["g"] for r in fe if r["cd"] == c])) < 0.005],
        "🔴 (나) 면 이 회귀 숫자는 결론이 아니다": True,
    }, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
