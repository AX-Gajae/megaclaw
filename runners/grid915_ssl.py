# -*- coding: utf-8 -*-
"""팔 915-ㅋ · 3단계 — **격자 시공간 장에서 라벨 0비트로 표현을 배운다. 층 1·2·4·8.**

🔴 사전등록 `docs/prereg_915_grid.md` §4.1~4.2
  · 프리텍스트 = **가림 복원**. 한 격자의 하루 24시 + 공간 이웃 8칸(9×24=216)에서
    임의의 칸을 가리고 복원한다. **판 라벨을 한 비트도 안 쓴다**(코드로 단언).
  · 🔴 **프로브가 쓸 격자 93개는 사전학습에서 통째로 뺀다** — 그 격자가 **이웃으로도**
    들어가는 표본을 전부 뺀다. 「사전학습에서도 뺀다」를 공간까지 지킨다.
  · 층 수만 바꾸고 폭·최적화·스텝·씨앗을 고정한다. **층별 그래디언트 노름**을 남긴다.

산출물: runners/out915_ssl.json · <scratch>/g915/rep_L{층}_s{씨앗}.npz · data/trainlog/<run_id>/
사용: python3 runners/grid915_ssl.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

ROOT = Path("/Users/ax/world_model")
sys.path.insert(0, str(ROOT))
from state.grid915 import SCR, load  # noqa: E402

OUT = ROOT / ("runners/out915_ssl%s.json" % os.environ.get("G915_TAG", ""))
ATT = ROOT / "data/state/grid915_attach.json"

DEPTHS = [int(x) for x in os.environ.get("G915_DEPTHS", "1,2,4,8").split(",")]
SEEDS = [int(x) for x in os.environ.get("G915_SEEDS", "0,1,2").split(",")]
STEPS = int(os.environ.get("G915_STEPS", "3000"))
BATCH = int(os.environ.get("G915_BATCH", "256"))
WIDTH = 256
MASK_P = 0.25
#: 🔴 갈래 딱지 — 스텝을 늘린 수렴 확인은 **다른 이름**으로 낸다(프로브가 안 섞이게)
TAG = os.environ.get("G915_TAG", "")
torch.set_num_threads(int(os.environ.get("G915_THREADS", "4")))


def sha16(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "🔴 파일 없음"


class Net(nn.Module):
    """입력 432(값 216 + 관측·비가림 표시 216) → 폭 256 × L 블록 → 출력 216."""

    def __init__(self, L: int, W: int = WIDTH):
        super().__init__()
        self.inp = nn.Linear(432, W)
        self.blocks = nn.ModuleList([nn.Linear(W, W) for _ in range(L)])
        self.out = nn.Linear(W, 216)
        self.act = nn.GELU()

    def rep(self, x):
        h = self.act(self.inp(x))
        for b in self.blocks:
            h = h + self.act(b(h))
        return h

    def forward(self, x):
        return self.out(self.rep(x))


def main() -> None:
    t00 = time.time()
    meta, F, OB, NB = load()
    G, D = meta["격자 수"], meta["날짜 수"]
    gidx = {g: i for i, g in enumerate(meta["격자"])}
    didx = {d: i for i, d in enumerate(meta["날짜"])}

    # ── 프로브 표본(93행) — 🔴 **라벨은 안 읽는다.** 격자·날짜만 읽는다 ──────
    att = json.loads(ATT.read_text())
    prow = []
    for r in att["행"]:
        gi = gidx.get(r["격자"])
        if gi is None:
            continue
        dd = r["from"].replace("-", "")
        # 개최 시작일이 지평 밖이면 개최 기간과 지평의 **겹치는 첫날**을 쓴다
        if dd not in didx:
            dd = max(dd, meta["날짜"][0])
            dd = min(dd, meta["날짜"][-1])
        ti = didx.get(dd)
        if ti is None or not OB[gi, ti]:
            cand = [t for t in range(D) if OB[gi, t]]
            if not cand:
                continue
            ti = min(cand, key=lambda t: abs(t - (didx.get(dd) or 0)))
        prow.append({"id": r["id"], "gi": gi, "ti": ti, "격자": r["격자"], "날짜": meta["날짜"][ti]})
    PG = sorted({p["gi"] for p in prow})

    # ── 값 표준화(격자별 · log1p) — 라벨 0비트 ─────────────────────────────
    Z = np.array(F, dtype=np.float32)                    # 492MB
    np.log1p(Z, out=Z)
    mu = Z.reshape(G, -1).mean(1, dtype=np.float64).astype(np.float32)
    sd = Z.reshape(G, -1).std(1, dtype=np.float64).astype(np.float32)
    sd[sd < 1e-3] = 1e-3
    Z -= mu[:, None, None]
    Z /= sd[:, None, None]
    Z[~OB] = 0.0

    NB9 = np.concatenate([np.arange(G, dtype=np.int32)[:, None], NB], 1)   # (G,9)
    OB9 = np.zeros((G, D, 9), np.float32)
    for j in range(9):
        nz = NB9[:, j]
        ok = nz >= 0
        OB9[ok, :, j] = OB[nz[ok], :]

    # ── 🔴 사전학습 표본 — 프로브 격자를 **이웃으로도** 건드리면 뺀다 ────────
    touch = np.zeros(G, bool)
    pgset = set(PG)
    for i in range(G):
        if i in pgset or any(int(n) in pgset for n in NB9[i] if n >= 0):
            touch[i] = True
    ok = OB & (~touch)[:, None]
    gi_all, ti_all = np.nonzero(ok)
    rng0 = np.random.default_rng(915)
    perm = rng0.permutation(len(gi_all))
    nval = 20000
    VA = (gi_all[perm[:nval]], ti_all[perm[:nval]])
    TR = (gi_all[perm[nval:]], ti_all[perm[nval:]])

    facts = {
        "장": {k: meta[k] for k in ("격자 수", "날짜 수", "시각 수", "칸 = 격자×날짜×시각",
                                   "🔴 관측된 (격자,날짜)", "관측 비율")},
        "🔴 프로브 격자(사전학습에서 뺐다)": len(PG),
        "🔴 프로브 격자를 이웃으로라도 건드려 뺀 격자": int(touch.sum()),
        "사전학습 표본 (격자,날짜)": int(len(TR[0])),
        "사전학습 검증 표본": nval,
        "🔴 라벨 0비트": ("이 러너가 연 파일: <scratch>/g915/*.npz · index.json · "
                     "data/state/grid915_attach.json(격자·날짜만 읽는다 · y 칸이 없다). "
                     "판 라벨(popup_v2.npz · market_axes.json)을 안 열었다"),
    }
    assert all("y" not in r for r in att["행"]), "🔴 grid915_attach.json 에 라벨 칸이 있다"

    def batch(idx, n, rng, mask=True):
        k = rng.integers(0, len(idx[0]), n)
        gi, ti = idx[0][k], idx[1][k]
        nb = NB9[gi]                                       # (n,9)
        v = Z[np.clip(nb, 0, None), ti[:, None], :]        # (n,9,24)
        o = OB9[gi, ti]                                    # (n,9)
        o = np.repeat(o[:, :, None], 24, 2).reshape(n, 216)
        v = v.reshape(n, 216) * o
        if not mask:
            x = np.concatenate([v, o], 1)
            return torch.from_numpy(x), None, None
        m = (rng.random((n, 216)) > MASK_P).astype(np.float32)   # 1=보임
        x = np.concatenate([v * m, m * o], 1)
        w = (1.0 - m) * o                                   # 가려졌고 관측된 칸
        return torch.from_numpy(x), torch.from_numpy(v), torch.from_numpy(w)

    runs = []
    for L in DEPTHS:
        for s in SEEDS:
            t0 = time.time()
            torch.manual_seed(s)
            rng = np.random.default_rng(1000 + s)
            net = Net(L)
            nparam = sum(p.numel() for p in net.parameters())
            opt = torch.optim.Adam(net.parameters(), lr=1e-3)

            # 🔴 잡음 바닥 A — 학습 **전** 표현을 먼저 뜬다(같은 아키텍처 · 난수 초기화)
            pgi = np.array([p["gi"] for p in prow])
            pti = np.array([p["ti"] for p in prow])

            def prep():
                nb = NB9[pgi]
                v = Z[np.clip(nb, 0, None), pti[:, None], :]
                o = np.repeat(OB9[pgi, pti][:, :, None], 24, 2).reshape(len(pgi), 216)
                v = v.reshape(len(pgi), 216) * o
                return torch.from_numpy(np.concatenate([v, o], 1)), v

            xp, vraw = prep()
            with torch.no_grad():
                rep_rand = net.rep(xp).numpy().copy()

            R = None
            try:
                from trainlog import Run
                R = Run(f"915-grid{TAG}-L{L}-s{s}", pushes=["②결과", "③시점"],
                        ruler="소수 라벨 곡선(프로브는 runners/grid915_probe.py)",
                        seed=s, trained=True,
                        hparams={"층": L, "폭": WIDTH, "스텝": STEPS, "배치": BATCH,
                                 "가림률": MASK_P, "lr": 1e-3, "최적화": "Adam",
                                 "프리텍스트": "가린 격자·시각 값 복원(라벨 0비트)"},
                        data=[str(SCR / "index.json")],
                        code=[str(ROOT / "runners/grid915_ssl.py"),
                              str(ROOT / "state/grid915.py"),
                              str(ROOT / "ingest/lifepop915.py")],
                        note=("서울 생활인구 250m 격자 · 8,880격자 × 577일 × 24시. "
                              "프로브 격자는 이웃으로도 안 들어간다"))
                R.arch(net)
            except Exception as e:                          # noqa: BLE001
                facts.setdefault("🔴 trainlog", []).append(f"못 썼다: {type(e).__name__}: {e}")

            gnorm: dict[str, list] = {}
            for st in range(1, STEPS + 1):
                x, y, w = batch(TR, BATCH, rng)
                p = net(x)
                loss = (((p - y) ** 2) * w).sum() / w.sum().clamp(min=1)
                opt.zero_grad()
                loss.backward()
                if st % 50 == 0 or st == 1:
                    for nm, mod in [("inp", net.inp)] + \
                            [(f"block{j}", b) for j, b in enumerate(net.blocks)] + [("out", net.out)]:
                        gn = float(mod.weight.grad.norm())
                        gnorm.setdefault(nm, []).append(gn)
                        if R is not None:
                            try:
                                R.log_node(step=st, node=nm, grad_norm=gn)
                            except Exception:               # noqa: BLE001
                                pass
                opt.step()
                if st % 50 == 0 or st == 1:
                    if R is not None:
                        R.log(step=st, split="train", loss=float(loss.detach()))
                if st % 500 == 0 or st == STEPS:
                    with torch.no_grad():
                        xv, yv, wv = batch(VA, 4096, np.random.default_rng(7))
                        vl = float((((net(xv) - yv) ** 2) * wv).sum() / wv.sum().clamp(min=1))
                    if R is not None:
                        R.log(step=st, split="val", loss=vl)

            with torch.no_grad():
                rep_tr = net.rep(xp).numpy().copy()
                xv, yv, wv = batch(VA, 20000, np.random.default_rng(7))
                vfin = float((((net(xv) - yv) ** 2) * wv).sum() / wv.sum().clamp(min=1))
                # 🔴 자명한 바닥: 다 0 으로 찍었을 때
                vzero = float(((yv ** 2) * wv).sum() / wv.sum().clamp(min=1))

            np.savez_compressed(SCR / f"rep{TAG}_L{L}_s{s}.npz",
                                rep=rep_tr, rep_rand=rep_rand, raw=vraw,
                                ids=np.array([p["id"] for p in prow]),
                                grids=np.array([p["격자"] for p in prow]),
                                days=np.array([p["날짜"] for p in prow]))
            med = {k: float(np.median(v[len(v) // 2:])) for k, v in gnorm.items()}
            first = med.get("block0", float("nan"))
            dead = [k for k, v in med.items()
                    if k.startswith("block") and first > 0 and v < first / 100
                    and np.median(gnorm[k][:3]) >= np.median(gnorm[k][-3:])]
            rr = {"층": L, "씨앗": s, "파라미터": nparam,
                  "프리텍스트 검증 MSE": round(vfin, 5),
                  "🔴 자명 바닥(다 0 으로 찍기) MSE": round(vzero, 5),
                  "설명한 몫 1-MSE/바닥": round(1 - vfin / vzero, 5),
                  "층별 그래디언트 노름 중앙값(뒤 절반)": {k: round(v, 6) for k, v in med.items()},
                  "🔴 안 배우는 층(첫 블록의 1/100 미만 + 증가 없음)": dead or "없다",
                  "초": round(time.time() - t0, 1)}
            runs.append(rr)
            if R is not None:
                R.log(step=STEPS, split="val", 설명한_몫=rr["설명한 몫 1-MSE/바닥"])
                R.finish()
                rr["trainlog run_id"] = R.run_id
            print(json.dumps(rr, ensure_ascii=False), flush=True)

    out = {"팔": "915-ㅋ", "단계": "3 — 자기지도 사전학습(라벨 0비트) · 층 1·2·4·8",
           "사전등록": "docs/prereg_915_grid.md",
           "코드 sha256": {c: sha16(ROOT / c) for c in
                          ("runners/grid915_ssl.py", "state/grid915.py", "ingest/lifepop915.py")},
           "사실": facts, "갈래": runs,
           "🔴 자": "여기선 판정 안 한다 — 프리텍스트 손실은 자가 아니다. 자는 grid915_probe.py",
           "초": round(time.time() - t00, 1),
           "끝 UTC": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
