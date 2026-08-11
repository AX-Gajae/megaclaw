# -*- coding: utf-8 -*-
"""팔 909-ㅁ · **2단계 자 (가)(나) + 4단계 정직 표지 + 참고 판 ρ**.

사전등록 `docs/prereg_909_ssl.md`.

🔴 **판 ρ 는 판정에 안 쓴다.** 참고로 병기하고 **얼마나 내려가는지**를 찍는다.
🔴 **누출**: 도메인 하나를 프리텍스트에서 **완전히 뺀다**(행 0). 유보 라벨은
프로브 적합에 **안 쓴다**(학습 행에서만 뽑는다). 둘 다 코드로 단언한다.

산출: `runners/out909_probe.json` · 합본 `runners/out909_ssl.json`
"""
import datetime as dt
import hashlib
import json
import sys
import time
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import numpy as np                                          # noqa: E402
from scipy.stats import rankdata, spearmanr                 # noqa: E402
from sklearn.linear_model import Ridge                      # noqa: E402

ROOT = Path("/Users/ax/world_model")
PREREG = ROOT / "docs/prereg_909_ssl.md"
T = 2025.0
KS = (8, 16, 32, 64, 128)
SEEDS = (0, 1, 2)
DRAWS = 20
STEPS = 400


def stamp() -> dict:
    return {
        "코드 sha(이 파일)": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:16],
        "코드 sha(state/ssl909.py)": hashlib.sha256(
            (ROOT / "state/ssl909.py").read_bytes()).hexdigest()[:16],
        "시각": dt.datetime.now().isoformat(),
        "사전등록": {"파일": "docs/prereg_909_ssl.md",
                   "sha256": hashlib.sha256(PREREG.read_bytes()).hexdigest(),
                   "mtime": dt.datetime.fromtimestamp(
                       PREREG.stat().st_mtime).isoformat()},
    }


def sp(a, b) -> float:
    ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < 5 or len(np.unique(a[ok])) < 3 or len(np.unique(b[ok])) < 3:
        return float("nan")
    return float(spearmanr(a[ok], b[ok]).statistic)


def probe(X, y, idx, hold) -> float:
    """🔴 `idx` 는 **학습 행에서만** 온다. `hold` 는 유보 행이고 적합에 안 쓴다."""
    if len(np.unique(y[idx])) < 3:
        return float("nan")
    g = Ridge(alpha=1.0).fit(X[idx], y[idx])
    return sp(g.predict(X[hold]), y[hold])


def main() -> int:
    t0 = time.time()
    import ff753 as FF
    from state import ssl909 as S
    import ssl909_pretext as PT

    data = FF.shell(FF.base())
    doms = list(data.dom)
    texts, _att = PT.row_texts(data)

    # 행 인덱스 — 학습/유보. 🔴 유보 라벨은 프로브 적합에 절대 안 들어간다
    tr, ho, Y = {}, {}, {}
    for d in doms:
        Y[d] = np.asarray(data.dom[d][2], float)
        tr[d] = np.where(data.rows(d, post=False, labeled=True, T=T))[0]
        ho[d] = np.where(data.rows(d, post=True, labeled=True, T=T))[0]
        assert len(np.intersect1d(tr[d], ho[d])) == 0, f"🔴 {d} 학습∩유보 != 0"

    out = {"무엇": "팔 909-ㅁ · 자 (가)(나) · 정직 표지 · 참고 판 ρ", **stamp(),
           "🔴 판 ρ 의 지위": "**판정에 안 쓴다.** 참고 병기 · 내림폭을 찍는 것이 목적",
           "설정": {"k": list(KS), "씨앗": list(SEEDS), "뽑기": DRAWS,
                   "프리텍스트 스텝": STEPS, "프로브": "Ridge(alpha=1.0) 고정"}}

    leak = {}
    arms = ("무텍스트", "텍스트")
    res = {a: {} for a in arms}
    curves_perm = {}
    randcheck = {}

    for tgt in doms:
        for arm in arms:
            b = S.build_bank(data, seed=S.SEED)
            if arm == "텍스트":
                b = S.attach_text(b, texts, k=64, exclude=tgt, seed=S.SEED)
            others = [d for d in doms if d != tgt]
            V = np.vstack([b.V[d] for d in others])
            M = np.vstack([b.M[d] for d in others])
            # 🔴 W3 누출 단언 ① — 뺀 도메인의 행이 프리텍스트 집합에 0행
            n_tgt = b.V[tgt].shape[0]
            n_all = sum(b.V[d].shape[0] for d in doms)
            leak.setdefault(arm, {})[tgt] = {
                "프리텍스트 행": int(V.shape[0]),
                "전체 행": int(n_all), "뺀 도메인 행": int(n_tgt),
                "🔴 뺀 도메인 행이 프리텍스트에 0행인가":
                    int(V.shape[0]) == int(n_all - n_tgt),
                "🔴 프로브 적합에 쓴 유보 라벨": 0,
                "학습∩유보": 0}
            assert V.shape[0] == n_all - n_tgt, f"🔴 누출: {tgt}/{arm}"

            Vt, Mt = b.V[tgt], b.M[tgt]
            live = np.where(Mt.sum(0) > 0)[0]
            Xraw = np.hstack([Vt[:, live] * Mt[:, live], Mt[:, live]])
            row = {"학습 행": int(len(tr[tgt])), "유보 행": int(len(ho[tgt])),
                   "살아 있는 열": int(len(live)), "k별": {}}
            Zs, Zd = [], []
            for sd in SEEDS:
                net, _ = S.pretrain(V, M, seed=sd, steps=STEPS)
                Zs.append(S.encode(net, Vt, Mt))
                netd, _ = S.pretrain(Vt, Mt, seed=sd, steps=STEPS)
                Zd.append(S.encode(netd, Vt, Mt))
            for k in KS:
                if len(tr[tgt]) < k:
                    row["k별"][k] = {"🔴 못 잰다": f"학습 행 {len(tr[tgt])} < k={k}"}
                    continue
                acc = {"SSL": [], "원축": [], "도메인만": [], "SSL(라벨순열)": [],
                       "SSL(난수표현)": []}
                for si, sd in enumerate(SEEDS):
                    rng = np.random.default_rng(90900 + 7 * sd + k)
                    Zr = rng.standard_normal(Zs[si].shape)
                    for r in range(DRAWS):
                        idx = rng.choice(tr[tgt], k, replace=False)
                        acc["SSL"].append(probe(Zs[si], Y[tgt], idx, ho[tgt]))
                        acc["원축"].append(probe(Xraw, Y[tgt], idx, ho[tgt]))
                        acc["도메인만"].append(probe(Zd[si], Y[tgt], idx, ho[tgt]))
                        acc["SSL(난수표현)"].append(probe(Zr, Y[tgt], idx, ho[tgt]))
                        yp = Y[tgt].copy()
                        yp[idx] = rng.permutation(yp[idx])
                        acc["SSL(라벨순열)"].append(
                            probe(Zs[si], yp, idx, ho[tgt]))
                row["k별"][k] = {m: round(float(np.nanmean(v)), 4)
                                 for m, v in acc.items()}
                row["k별"][k]["차(SSL-원축)"] = round(
                    float(np.nanmean(np.array(acc["SSL"]) - np.array(acc["원축"]))), 4)
                row["k별"][k]["뽑기 수"] = len(acc["SSL"])
                row["k별"][k]["_raw차"] = [
                    round(float(x), 5) for x in
                    (np.array(acc["SSL"]) - np.array(acc["원축"]))]
            # 판식 ρ — 전 학습 라벨
            row["참고 · 전 학습 라벨 프로브"] = {
                "SSL": round(float(np.nanmean(
                    [probe(Z, Y[tgt], tr[tgt], ho[tgt]) for Z in Zs])), 4),
                "원축": round(float(probe(Xraw, Y[tgt], tr[tgt], ho[tgt])), 4),
                "도메인만": round(float(np.nanmean(
                    [probe(Z, Y[tgt], tr[tgt], ho[tgt]) for Z in Zd])), 4)}
            res[arm][tgt] = row
        print(f"  {tgt} 끝 · {time.time()-t0:.0f}초", flush=True)

    out["🔴 W3 누출 단언"] = leak
    out["자 (가) 소수 라벨 곡선 — 도메인 전량"] = res

    # ── 도메인 가중 요약 (🔴 분모를 고정한다 · 조항 60) ────────────────
    W = data.weights(T)
    fixed8 = [d for d in doms if len(tr[d]) >= max(KS)]
    summ = {}
    for arm in arms:
        s = {"🔴 고정 분모(모든 k 에서 재는 도메인)": fixed8,
             "고정 분모 유보 행 합": int(sum(W[d] for d in fixed8)),
             "k별(고정 분모)": {}, "k별(그 k 에서 잴 수 있는 도메인 전부)": {}}
        for k in KS:
            for tag, dl in (("k별(고정 분모)", fixed8),
                            ("k별(그 k 에서 잴 수 있는 도메인 전부)",
                             [d for d in doms if len(tr[d]) >= k])):
                ww = np.array([W[d] for d in dl], float)
                cell = {}
                for m in ("SSL", "원축", "도메인만", "SSL(라벨순열)", "SSL(난수표현)"):
                    v = np.array([res[arm][d]["k별"][k].get(m, np.nan) for d in dl],
                                 float)
                    ok = np.isfinite(v)
                    cell[m] = round(float((v[ok] * ww[ok]).sum() / ww[ok].sum()), 4) \
                        if ok.any() else None
                # 뽑기 부트 — 도메인 가중 차의 백분위 구간
                mat = []
                for d in dl:
                    r = res[arm][d]["k별"][k].get("_raw차")
                    if r:
                        mat.append(r)
                lo = hi = None
                if len(mat) == len(dl) and mat:
                    A = np.array(mat)                     # (도메인, 뽑기)
                    rg = np.random.default_rng(9091 + k)
                    bs = []
                    for _ in range(2000):
                        j = rg.integers(0, A.shape[1], A.shape[1])
                        bs.append(float((A[:, j].mean(1) * ww).sum() / ww.sum()))
                    lo, hi = (round(float(np.percentile(bs, 2.5)), 4),
                              round(float(np.percentile(bs, 97.5)), 4))
                cell["차(SSL-원축)"] = (round(cell["SSL"] - cell["원축"], 4)
                                    if cell["SSL"] is not None
                                    and cell["원축"] is not None else None)
                cell["차 뽑기 부트 [2.5,97.5]"] = [lo, hi]
                cell["0 을 무나"] = (None if lo is None else (lo <= 0 <= hi))
                cell["도메인 수"] = len(dl)
                s[tag][k] = cell
        summ[arm] = s
    out["🔴 자 (가) 요약 (도메인 가중 = 유보 행수)"] = summ

    # 판정 (가)
    verdict = {}
    for arm in arms:
        win = [k for k in (8, 16, 32)
               if summ[arm]["k별(고정 분모)"][k]["0 을 무나"] is False
               and (summ[arm]["k별(고정 분모)"][k]["차(SSL-원축)"] or 0) > 0]
        verdict[arm] = {
            "사전등록 판정 규칙": "k∈{8,16,32} 중 하나에서 (SSL−원축) 가중 평균의 "
                            "뽑기 부트 [2.5,97.5] 가 0 을 안 물면 통과",
            "이긴 k": win,
            "🔴 판정": ("자 (가) 소수 라벨 곡선 **통과**" if win
                     else "🔴 **자 (가) 소수 라벨 곡선을 못 넘었다**")}
    out["🔴 자 (가) 판정"] = verdict

    # ── 자 (나) 집 밖 짝 ────────────────────────────────────────────
    print("자 (나) 집 밖 짝…", flush=True)
    pair = {}
    try:
        from lab import pairs
        b = S.build_bank(data, seed=S.SEED)
        Vall = np.vstack([b.V[d] for d in doms])
        Mall = np.vstack([b.M[d] for d in doms])
        nets = [S.pretrain(Vall, Mall, seed=sd, steps=STEPS)[0] for sd in SEEDS]
        idxname = {a: j for j, a in enumerate(b.names)}
        for nm in ("KR 만화", "CN 만화", "비게임 앱"):
            src = pairs.SRC_DOM[nm]
            rows = pairs.build(nm)
            names = list(data.names.get(src) or [])
            A, M, y, t = pairs.to_arrays(rows, names)
            P = len(b.names)
            Vp = np.zeros((len(y), P))
            Mp = np.zeros((len(y), P))
            for j0, a in enumerate(names):
                j = idxname[a]
                st = b.stats.get((src, j))
                if st is None:
                    continue
                mu, sd_ = st
                Vp[:, j] = np.where(M[:, j0] > 0, (A[:, j0] - mu) / sd_, 0.0)
                Mp[:, j] = (M[:, j0] > 0).astype(float)
            okp = np.isfinite(y)
            rs, rg = [], []
            for i, net in enumerate(nets):
                Zp = S.encode(net, Vp, Mp)
                Zs = S.encode(net, b.V[src], b.M[src])
                g = Ridge(alpha=1.0).fit(Zs[tr[src]], Y[src][tr[src]])
                rs.append(sp(g.predict(Zp)[okp], y[okp]))
                Xg = np.vstack([S.encode(net, b.V[d], b.M[d])[tr[d]] for d in doms])
                yg = np.concatenate([rankdata(Y[d][tr[d]]) / len(tr[d]) for d in doms])
                gg = Ridge(alpha=1.0).fit(Xg, yg)
                rg.append(sp(gg.predict(Zp)[okp], y[okp]))
            pair[nm] = {
                "행": len(rows), "기대 행": pairs.PAIRS[nm][2],
                "행수 일치(시험 ①)": len(rows) == pairs.PAIRS[nm][2],
                "채점 행": int(okp.sum()),
                "SSL 표현 + 원천 도메인 프로브 (씨앗 평균)":
                    round(float(np.nanmean(rs)), 4),
                "씨앗별": [round(float(x), 4) for x in rs],
                "SSL 표현 + 전역 프로브 (씨앗 평균)": round(float(np.nanmean(rg)), 4),
                "🔴 기준선(노트 696 기록)": {"KR 만화": 0.6831, "CN 만화": 0.3874,
                                     "비게임 앱": 0.4968}[nm],
                "🔴 기준선(오늘 챔피언 씨앗0 · out909_pairbase.json)":
                    {"KR 만화": 0.6835, "CN 만화": 0.3971, "비게임 앱": 0.4802}[nm]}
    except Exception as e:                                   # noqa: BLE001
        pair = {"🔴 못 쟀다": f"{type(e).__name__}: {e}"}
    out["자 (나) 집 밖 짝"] = pair
    out["🔴 자 (나) 판정"] = {
        "규칙": "셋 중 둘 이상에서 SSL 이 기준선을 씨앗SD 2배(KR 0.0150·앱 0.0138·"
              "CN 0.0132) 넘어 위로 가면 통과",
        "🔴 판정": ("🔴 **자 (나) 집 밖 짝을 못 넘었다**"
                 if not isinstance(pair, dict) or "🔴 못 쟀다" in pair or
                 sum(1 for nm, v in pair.items()
                     if isinstance(v, dict) and
                     v.get("SSL 표현 + 원천 도메인 프로브 (씨앗 평균)", -9) >
                     v["🔴 기준선(노트 696 기록)"] +
                     {"KR 만화": 0.0150, "비게임 앱": 0.0138, "CN 만화": 0.0132}[nm]) < 2
                 else "자 (나) 통과")}

    # ── 참고 판식 ρ (🔴 판정에 안 쓴다) ──────────────────────────────
    board = {}
    for arm in arms:
        for m in ("SSL", "원축", "도메인만"):
            num = den = 0.0
            per = {}
            for d in doms:
                v = res[arm][d]["참고 · 전 학습 라벨 프로브"][m]
                per[d] = v
                if v is not None and np.isfinite(v):
                    num += v * W[d]
                    den += W[d]
            board[f"{arm}/{m}"] = {"판식 ρ": round(num / den, 5),
                                   "분모(유보 행)": int(den), "도메인별": per}
    board["🔴 챔피언 판 ρ (노트 898 · 12도메인 · 유보 3,775 · 씨앗 0~11)"] = 0.47034
    for kk in list(board):
        if isinstance(board[kk], dict) and "판식 ρ" in board[kk]:
            board[kk]["🔴 챔피언 대비 내림폭"] = round(0.47034 - board[kk]["판식 ρ"], 5)
    out["참고 · 판식 ρ (🔴 판정에 안 쓴다)"] = board
    out["🔴 참고 판 ρ 를 읽는 법"] = (
        "이 표의 ρ 는 **판 자(12도메인·유보 3,775·유보수 가중 스피어만)로 잰 다른 "
        "모형**이다. 챔피언 0.47034 는 **부스팅 + 36축 + 전 학습 라벨**이고 여기 것은 "
        "**선형 프로브 + k차원 표현**이다. 내림폭을 **아키텍처 탓으로만 읽으면 조항 60 "
        "위반**이다 — '원축' 줄이 「선형 프로브 대 부스팅」의 몫을, 'SSL' 대 '원축' 이 "
        "「표현 대 원축」의 몫을 나눈다")

    out["벽시계(초)"] = round(time.time() - t0, 1)
    (ROOT / "runners/out909_probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1))

    # 합본
    merged = {"무엇": "팔 909-ㅁ 합본", **stamp()}
    for f, key in (("out909_fuel.json", "0단계 연료"),
                   ("out909_pretext.json", "1·3단계 프리텍스트·배선·자 (다)"),
                   ("out909_pairbase.json", "자 (나) 기준선(오늘 챔피언 씨앗0)"),
                   ("out909_probe.json", "2·4단계 자 (가)(나)·정직 표지·참고 판 ρ")):
        p = ROOT / "runners" / f
        merged[key] = (json.loads(p.read_text()) if p.exists()
                       else f"🔴 못 읽었다 — {f} 가 없다")
    (ROOT / "runners/out909_ssl.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=1))
    print(f"끝 · {time.time()-t0:.0f}초", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
