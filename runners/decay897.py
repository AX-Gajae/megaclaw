"""노트 897 · 1단계 — **표현 수준의 감쇠.** 1열이 아니라 `enc.pt` 의 dim 차원 전체.

노트 756 이 1열(`field_spread_ff` = 30일 앞 예보 Δ 의 동네 간 SD)에서 잰 무늬:
가장 해로운 둘이 **학습 +0.082 · +0.077 → 유보 +0.022 · +0.020** 으로
**뒤집히지 않고 4분의 1로 사라진다.** 노트 759·765 가 기제 후보 다섯을 다 지웠다.

여기서 묻는 것은 다르다 --- **그 감쇠가 자료의 성질인가, 1열로 눌러서 생긴
것인가.** 장 인코더의 표현은 dim 차원인데 판에는 **스칼라 하나**로 들어간다.
표현 전체를 쓰면 남는 것이 있나?

🔴 **여기서 0 이면 어떤 합류 구조(크로스 어텐션·게이팅·concat·late fusion)도
못 살린다.** 그것이 이 사이클의 제일 값진 결과일 수 있다.

**재구현이 아니다** --- `Enc` 는 `state/fieldmodel.py:265` 의 정본을 그대로
옮기고 `state_dict` 키 집합을 **대조**한다(노트 702 의 교훈: 재구현이 저계수
이웃 혼합을 빠뜨려 잴 대상을 지웠다). `runners/ff753.py` 를 반입하지 않는 이유는
그 파일을 지금 다른 에이전트가 고치고 있기 때문이다(이슈 #113).

쓰는 법::

    python3 -m runners.decay897 main       # 진짜 팔 + 순열 널
    python3 -m runners.decay897 placebo    # 위약 팔(날짜 연결을 끊는다)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners"

T = 2025.0
MIN_TR = 30          # 도메인이 통계에 들어갈 최소 학습 행
MIN_TE = 20          # 최소 유보 행
FOLDS = 5
ALPHA = 1.0
PERM = 1000
PERM_SEED = 897
PLACEBO_SEEDS = (8971, 8972, 8973)
BOOT_B = 2000        # 군집 부트(날짜 군집) --- 규약 47
K_SPATIAL = 8        # fieldmodel.pretrain 의 K


def stamp() -> dict:
    """🔴 내 파일의 sha 는 내가 박는다(티처 #59 M7 --- `stamp()` 가 `__file__` 을
    해싱하므로 남의 파일에서 부르면 틀린 sha 가 박힌다)."""
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(decay897.py)":
                hashlib.sha256(ME.read_bytes()).hexdigest()[:16],
            "scipy": __import__("scipy").__version__,
            "numpy": np.__version__}


# ── 장 표현 ────────────────────────────────────────────────────────────
def rep_series():
    """날짜마다 (표현 요약 8열, 1열 축).

    표현 요약은 **동네 축으로 눌러서** 낸다 --- 관측된 동네에 대해 dim 차원
    각각의 평균과 표준편차. 전국 평균은 구성상 0 이 아니게 될 수 있으므로
    (표현은 이상치가 아니라 tanh 출력이다) 평균도 같이 싣는다.
    1열 축은 노트 753 의 것 --- 예보 Δ 의 동네 간 SD.
    """
    import torch
    import torch.nn as nn
    from state import fieldmodel as F

    ck = torch.load(F.OUT / "enc.pt", map_location="cpu", weights_only=False)
    dim, lb, hz = ck["dim"], ck["lookback"], ck["horizon"]
    codes, days, X = F.field(stats_end=F.TRAIN_END)
    assert list(codes) == list(ck["codes"]), "동네 목록이 바뀌었다 --- 배선 중단"
    D = len(codes)

    class Enc(nn.Module):
        """`state/fieldmodel.py:265` 의 정본과 같은 구조. 키 집합을 대조한다."""

        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(D, dim)
            self.tconv = nn.Linear(lb, dim)
            self.down = nn.Linear(D, K_SPATIAL, bias=False)
            self.up = nn.Linear(K_SPATIAL, D, bias=False)
            self.mix = nn.Linear(dim * 3, dim)
            self.head = nn.Linear(dim, 1)

        def rep(self, w):
            e = self.emb.weight.unsqueeze(0).expand(w.shape[0], -1, -1)
            h = torch.tanh(self.tconv(w))
            g = self.up(self.down(h.transpose(1, 2))).transpose(1, 2)
            return torch.tanh(self.mix(torch.cat([h, e, g], -1)))

        def forward(self, w):
            return self.head(self.rep(w)).squeeze(-1)

    net = Enc()
    got, want = set(net.state_dict()), set(ck["state"])
    assert got == want, f"state_dict 키 불일치 --- 재구현 사고: {got ^ want}"
    net.load_state_dict(ck["state"])
    net.eval()

    Z = np.nan_to_num(X, nan=0.0)
    obs = np.isfinite(X)
    idx, feats, one = [], [], []
    with torch.no_grad():
        for t in range(lb, X.shape[1]):
            m = obs[:, t]
            if m.sum() < 30:
                continue
            w = torch.tensor(Z[:, t - lb:t][None, ...], dtype=torch.float32)
            h = net.rep(w).numpy()[0]                # (D, dim)
            p = net.head(torch.tensor(h)).numpy().squeeze(-1)
            hm = h[m]
            feats.append(np.concatenate([hm.mean(0), hm.std(0)]))
            one.append(float(np.std(p[m])))
            idx.append(t)
    yrs = np.array([int(days[i][:4]) + (int(days[i][4:6]) - 1) / 12
                    + (int(days[i][6:]) - 1) / 365 for i in idx])
    return {"yrs": yrs, "F": np.asarray(feats, float), "one": np.asarray(one, float),
            "idx": np.asarray(idx, int), "dim": dim, "lookback": lb, "horizon": hz,
            "동네": D, "날 수": len(idx),
            "저장물 키": sorted(ck)}


# ── 판 자료 ────────────────────────────────────────────────────────────
def board_rows():
    """도메인 → (시작 시각 yr, 라벨). 판 껍데기는 `lab.loop._idol` 정본."""
    from lab import loop as L
    d0 = L._idol(lambda: {}, mode="cut", with_wiki=True, with_trend=True,
                 wide_post=True, wide_pop="grades")
    out = {}
    for dm in sorted(d0.dom):
        y = np.asarray(d0.yr[dm], float)
        lab = np.asarray(d0.dom[dm][2], float)
        n = min(len(y), len(lab))
        out[dm] = (y[:n], lab[:n])
    return out, d0


# ── 표 ─────────────────────────────────────────────────────────────────
def table(rs, rows, jitter_rng=None):
    """도메인별 (학습/유보 · 8열 특성 · 1열 · 라벨 · 날짜군집).

    🔴 **라벨 유한을 먼저 거른다**(티처 #59 M11 --- `rankdata` 는 NaN 하나면
    배열 전체를 NaN 으로 만들고 도메인이 조용히 빠진다).
    `jitter_rng` 가 있으면 **행의 날짜 연결을 무작위로 끊는다**(위약 팔).
    """
    yrs, FT, ONE = rs["yrs"], rs["F"], rs["one"]
    tab = {}
    for dm, (y, lab) in rows.items():
        ok = np.isfinite(y) & np.isfinite(lab) & (y >= yrs[0])
        if ok.sum() < MIN_TR + MIN_TE:
            tab[dm] = {"제외": f"유한행 {int(ok.sum())} < {MIN_TR + MIN_TE}"}
            continue
        j = np.clip(np.searchsorted(yrs, y[ok]), 0, len(yrs) - 1)
        if jitter_rng is not None:
            j = jitter_rng.integers(0, len(yrs), len(j))
        tr = y[ok] < T
        te = ~tr
        if tr.sum() < MIN_TR or te.sum() < MIN_TE:
            tab[dm] = {"제외": f"학습 {int(tr.sum())} · 유보 {int(te.sum())}"}
            continue
        tab[dm] = {"y": y[ok], "lab": lab[ok], "j": j, "tr": tr, "te": te,
                   "X": FT[j], "one": ONE[j],
                   "학습": int(tr.sum()), "유보": int(te.sum()),
                   "학습 고유날": int(len(np.unique(j[tr]))),
                   "유보 고유날": int(len(np.unique(j[te]))),
                   "🔴 장 끝 넘어 앞채움된 행":
                       int((np.searchsorted(yrs, y[ok]) >= len(yrs)).sum())}
    return tab


def _sp(a, b):
    from scipy.stats import spearmanr
    if len(a) < 5 or np.std(a) < 1e-12 or np.std(b) < 1e-12:
        return np.nan
    return float(spearmanr(a, b).statistic)


def fit_preds(t):
    """도메인 하나에 대해 (학습 OOF 예보, 유보 예보). 능형 · 날짜 GroupKFold.

    🔴 학습 쪽도 **표본 밖**으로 만든다 --- 안 그러면 감쇠가 자동으로 크다.
    군집을 날짜로 두는 이유: 특성이 날짜만의 함수라 같은 날 행은 **완전히
    종속**이다. 무작위 분할은 그 사실을 못 본다.
    """
    from scipy.stats import rankdata
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import GroupKFold

    Xtr, Xte = t["X"][t["tr"]], t["X"][t["te"]]
    ytr = t["lab"][t["tr"]]
    r = rankdata(ytr)                      # 라벨 유한은 위에서 이미 걸렀다
    ztr = (r - r.mean()) / (r.std() + 1e-12)
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-9
    A, B = (Xtr - mu) / sd, (Xte - mu) / sd
    g = t["j"][t["tr"]]
    oof = np.full(len(A), np.nan)
    ng = len(np.unique(g))
    if ng >= 2:
        k = int(min(FOLDS, ng))
        for tri, tei in GroupKFold(n_splits=k).split(A, ztr, groups=g):
            m = Ridge(alpha=ALPHA).fit(A[tri], ztr[tri])
            oof[tei] = m.predict(A[tei])
    m = Ridge(alpha=ALPHA).fit(A, ztr)
    return oof, m.predict(B), {"학습 날 군집": ng}


def measure(tab):
    """도메인별 학습/유보 상관 --- 1열과 표현 둘 다."""
    per = {}
    for dm, t in tab.items():
        if "제외" in t:
            per[dm] = t
            continue
        oof, pte, info = fit_preds(t)
        ltr, lte = t["lab"][t["tr"]], t["lab"][t["te"]]
        o = np.isfinite(oof)
        per[dm] = {
            "학습": t["학습"], "유보": t["유보"],
            "학습 고유날": t["학습 고유날"], "유보 고유날": t["유보 고유날"],
            "앞채움 행": t["🔴 장 끝 넘어 앞채움된 행"],
            "1열 학습ρ": round(_sp(t["one"][t["tr"]], ltr), 4),
            "1열 유보ρ": round(_sp(t["one"][t["te"]], lte), 4),
            "표현 학습ρ(OOF)": round(_sp(oof[o], ltr[o]), 4),
            "표현 유보ρ": round(_sp(pte, lte), 4),
            **info,
        }
        for a, b, nm in (("1열 학습ρ", "1열 유보ρ", "1열 유지율"),
                         ("표현 학습ρ(OOF)", "표현 유보ρ", "표현 유지율")):
            x, z = per[dm][a], per[dm][b]
            per[dm][nm] = (round(z / x, 3) if np.isfinite(x) and abs(x) > 1e-6
                           and np.isfinite(z) else None)
    return per


def headline(tab, per, arm: str):
    """**판정 통계** --- 학습에서 배운 방향이 유보에서 얼마나 남나.

        S = Σ_d n_d · sign(ρ_학습,d) · ρ_유보,d / Σ_d n_d

    부호를 학습으로 고정하므로 *사후에 유리한 부호를 고르는* 일이 없다.
    """
    key_tr = "표현 학습ρ(OOF)" if arm == "표현" else "1열 학습ρ"
    key_te = "표현 유보ρ" if arm == "표현" else "1열 유보ρ"
    num = den = 0.0
    used = {}
    for dm, p in per.items():
        if "제외" in p:
            continue
        a, b = p[key_tr], p[key_te]
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        s = np.sign(a) if a != 0 else 1.0
        n = p["유보"]
        num += n * s * b
        den += n
        used[dm] = {"n": n, "sign": int(s), "유보ρ": b, "기여": round(n * s * b, 2)}
    return (num / den if den else np.nan), used, int(den)


def perm_null(tab, per, arm: str, draws: int = PERM, seed: int = PERM_SEED):
    """🔴 **널을 실측한다**(891 방식) --- 유보 라벨을 도메인 안에서 섞는다.

    예보(학습에서 적합)는 고정하고 라벨만 섞으므로, 널은 *'유보에서 이만한
    상관이 우연히 나오나'* 를 정확히 답한다."""
    from scipy.stats import rankdata
    rng = np.random.default_rng(seed)
    key_tr = "표현 학습ρ(OOF)" if arm == "표현" else "1열 학습ρ"
    cache = {}
    for dm, t in tab.items():
        if "제외" in t or "제외" in per[dm]:
            continue
        a = per[dm][key_tr]
        if not np.isfinite(a):
            continue
        if arm == "표현":
            _o, pte, _i = fit_preds(t)
        else:
            pte = t["one"][t["te"]]
        lte = t["lab"][t["te"]]
        cache[dm] = (np.sign(a) if a != 0 else 1.0, np.asarray(pte, float),
                     rankdata(lte), per[dm]["유보"])
    out = []
    for _ in range(draws):
        num = den = 0.0
        for dm, (s, pte, rl, n) in cache.items():
            num += n * s * _sp(pte, rng.permutation(rl))
            den += n
        out.append(num / den if den else np.nan)
    a = np.asarray(out, float)
    a = a[np.isfinite(a)]
    return {"뽑기": int(len(a)), "널 평균": round(float(a.mean()), 5),
            "널 SD": round(float(a.std(ddof=1)), 5),
            "널 2σ": round(float(2 * a.std(ddof=1)), 5),
            "널 백분위 2.5/97.5": [round(float(np.percentile(a, 2.5)), 5),
                                round(float(np.percentile(a, 97.5)), 5)]}


def boot_ci(tab, per, arm: str):
    """규약 47 --- **날짜 군집** BCa. 특성이 날짜만의 함수라 날짜가 군집이다.

    `franchise_key` 가 아니라 날짜를 쓰는 이유를 산출물에 병기한다(규약 47 은
    재표집 단위를 프랜차이즈로 정의하는데, 이 자에서는 **같은 날 행이 완전히
    종속**이므로 프랜차이즈보다 날짜가 상위 군집이다).
    """
    from lab import pairboot as PB
    from scipy.stats import rankdata
    key_tr = "표현 학습ρ(OOF)" if arm == "표현" else "1열 학습ρ"
    doms, sgn, preds, labs, days, dcol = [], [], [], [], [], []
    for dm, t in tab.items():
        if "제외" in t or "제외" in per[dm]:
            continue
        a = per[dm][key_tr]
        if not np.isfinite(a):
            continue
        if arm == "표현":
            _o, pte, _i = fit_preds(t)
        else:
            pte = t["one"][t["te"]]
        k = len(pte)
        doms.append(dm); sgn.append(np.sign(a) if a != 0 else 1.0)
        preds.append(np.asarray(pte, float)); labs.append(rankdata(t["lab"][t["te"]]))
        days.append(t["j"][t["te"]])
        dcol.append(np.full(k, len(doms) - 1))
    P = np.concatenate(preds); Lb = np.concatenate(labs)
    DY = np.concatenate(days); DC = np.concatenate(dcol)
    S = np.asarray(sgn, float)

    key = {}
    for i, d in enumerate(DY):
        key.setdefault(int(d), []).append(i)
    cl = [np.asarray(v, int) for v in key.values()]
    wire = {"행": len(P), "군집(날짜)": len(cl), "병합": len(P) - len(cl),
            "병합률": round(1 - len(cl) / len(P), 4),
            "군집 정의": "날짜 --- 특성이 날짜만의 함수라 같은 날 행은 완전 종속. "
                     "규약 47 의 프랜차이즈보다 상위 군집이다(병기)"}

    def stat(idx):
        num = den = 0.0
        for c in range(len(doms)):
            m = DC[idx] == c
            if m.sum() < 5:
                continue
            r = _sp(P[idx][m], Lb[idx][m])
            if not np.isfinite(r):
                continue
            num += m.sum() * S[c] * r
            den += m.sum()
        return num / den if den else np.nan

    th, lo, hi, kind = PB.cluster_boot(stat, cl, B=BOOT_B, seed=897)
    return {"점추정": round(float(th), 5), "lo": round(float(lo), 5),
            "hi": round(float(hi), 5), "종류": kind,
            "판정(0 을 무나)": PB.verdict(lo, hi), "군집 병기": wire,
            "폴백 사유": (None if kind == "BCa" else "cluster_boot 이 BCa 실패/유실을 보고")}


def run(arm_rows, rs, tag: str, rng=None) -> dict:
    tab = table(rs, arm_rows, jitter_rng=rng)
    per = measure(tab)
    res = {"태그": tag, "도메인": per}
    for arm in ("1열", "표현"):
        S, used, n = headline(tab, per, arm)
        res[arm] = {"헤드라인 S": round(float(S), 5) if np.isfinite(S) else None,
                    "유보 총행": n, "도메인별 기여": used}
    return res, tab, per


def main():
    rs = rep_series()
    rows, d0 = board_rows()
    out = {"stamp": stamp(),
           "장": {k: rs[k] for k in ("dim", "lookback", "horizon", "동네",
                                    "날 수", "저장물 키")},
           "장 기간": [round(float(rs["yrs"][0]), 3), round(float(rs["yrs"][-1]), 3)]}
    res, tab, per = run(rows, rs, "진짜")
    out["진짜"] = res
    for arm in ("1열", "표현"):
        out["진짜"][arm]["순열 널"] = perm_null(tab, per, arm)
        out["진짜"][arm]["군집 BCa"] = boot_ci(tab, per, arm)
        S = out["진짜"][arm]["헤드라인 S"]
        nl = out["진짜"][arm]["순열 널"]
        out["진짜"][arm]["🔴 널 2σ 밖인가"] = bool(
            S is not None and abs(S - nl["널 평균"]) > nl["널 2σ"])
    (OUT / "out897_decay.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({a: {k: out["진짜"][a][k]
                          for k in ("헤드라인 S", "유보 총행", "🔴 널 2σ 밖인가")}
                      for a in ("1열", "표현")}, ensure_ascii=False, indent=1))
    print("→", OUT / "out897_decay.json")


def placebo():
    """위약 팔 --- 행의 **날짜 연결만** 끊는다. 특성 주변분포는 그대로다.

    이것이 0 이 아니면 잰 것은 장이 아니라 표본 구성이다."""
    rs = rep_series()
    rows, _d0 = board_rows()
    out = {"stamp": stamp(), "팔": []}
    for s in PLACEBO_SEEDS:
        res, tab, per = run(rows, rs, f"위약 {s}", rng=np.random.default_rng(s))
        for arm in ("1열", "표현"):
            res[arm].pop("도메인별 기여", None)
        out["팔"].append(res)
        print(json.dumps({"위약": s,
                          "1열 S": res["1열"]["헤드라인 S"],
                          "표현 S": res["표현"]["헤드라인 S"]}, ensure_ascii=False),
              flush=True)
    (OUT / "out897_placebo.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print("→", OUT / "out897_placebo.json")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "main"
    {"main": main, "placebo": placebo}.get(cmd, main)()
