"""노트 897 · **§9 배선 검사의 NN 판본** — `docs/아키텍처.md` 9.1 을 그대로 돌린다.

🔴 **이것은 측정 뒤에 들어온 지시다**(주 세션이 `docs/아키텍처.md` 를 커밋
`029536069` 로 박았고, 그때 1단계 측정은 이미 끝나 있었다). 그러므로 이 파일의
결과는 **사전등록된 판정에 안 들어간다** — 사다리 L1 을 열기 전에 통과해야 하는
**전제 검사**로 남긴다.

**여덟 중 이 사이클에서 돌 수 있는 것과 못 도는 것을 갈라 적는다**(조항 59 —
안 한 것을 한 것처럼 적지 않는다). 이 사이클은 **새 구조를 학습하지 않으므로**
학습에 붙는 검사 셋은 **얼린 인코더 위에서 「한 배치 과적합」으로 대신** 돌린다.

    ① 한 배치 과적합    ✅ 돈다(새로 초기화한 같은 구조로 16창을 외우게 한다)
    ② 모양·dtype 단언   ✅ 돈다
    ③ 층별 ‖Δθ‖         ✅ ① 안에서 함께
    ④ 기울기 노름       ✅ ① 안에서 함께
    ⑤ 항등 붕괴         ❌ 못 돈다 — **새 블록이 없다**(L1 을 안 열었다)
    ⑥ 입력 지우기       ✅ 돈다 — 🔴 이 실험실 배선 검사의 직역
    ⑦ 라벨 순열         ✅ 이미 `decay897.perm_null` 로 했다(1,000 뽑기)
    ⑧ 결정성            ✅ 돈다(두 번 돌려 바이트 대조)
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

from runners import decay897 as D           # noqa: E402

ROOT = Path("/Users/ax/world_model")
ME = Path(__file__).resolve()
OUT = ROOT / "runners/out897_nnchk.json"
K_SPATIAL = 8


def stamp() -> dict:
    h = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                       capture_output=True, text=True).stdout.strip()
    return {"git HEAD": h, "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "코드 sha(nnchk897.py)": hashlib.sha256(ME.read_bytes()).hexdigest()[:16],
            "🔴 지위": "측정 뒤 들어온 지시(docs/아키텍처.md · 029536069)의 이행. "
                     "사전등록된 판정에 안 들어간다 — L1 전제 검사"}


def _build(dim, lb, D_):
    import torch
    import torch.nn as nn

    class Enc(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(D_, dim)
            self.tconv = nn.Linear(lb, dim)
            self.down = nn.Linear(D_, K_SPATIAL, bias=False)
            self.up = nn.Linear(K_SPATIAL, D_, bias=False)
            self.mix = nn.Linear(dim * 3, dim)
            self.head = nn.Linear(dim, 1)

        def parts(self, w):
            e = self.emb.weight.unsqueeze(0).expand(w.shape[0], -1, -1)
            h = torch.tanh(self.tconv(w))
            g = self.up(self.down(h.transpose(1, 2))).transpose(1, 2)
            return h, e, g

        def rep(self, w, kill: str | None = None):
            h, e, g = self.parts(w)
            if kill == "h":
                h = torch.zeros_like(h)
            elif kill == "e":
                e = torch.zeros_like(e)
            elif kill == "g":
                g = torch.zeros_like(g)
            return torch.tanh(self.mix(torch.cat([h, e, g], -1)))

        def forward(self, w, kill=None):
            return self.head(self.rep(w, kill)).squeeze(-1)

    return Enc


# ── ⑥ 입력 지우기 · ⑧ 결정성 · ② 모양 ────────────────────────────────
def ablate_and_determinism():
    import torch
    from state import fieldmodel as F

    ck = torch.load(F.OUT / "enc.pt", map_location="cpu", weights_only=False)
    dim, lb = ck["dim"], ck["lookback"]
    codes, days, X = F.field(stats_end=F.TRAIN_END)
    D_ = len(codes)
    Enc = _build(dim, lb, D_)
    net = Enc()
    net.load_state_dict(ck["state"])
    net.eval()

    Z = np.nan_to_num(X, nan=0.0)
    obs = np.isfinite(X)
    ts = [t for t in range(lb, X.shape[1]) if obs[:, t].sum() >= 30]

    shapes = {}

    def feats(kill=None):
        out, one = [], []
        with torch.no_grad():
            for t in ts:
                w = torch.tensor(Z[:, t - lb:t][None, ...], dtype=torch.float32)
                if not shapes:
                    shapes["창 w"] = list(w.shape)
                    shapes["창 dtype"] = str(w.dtype)
                h = net.rep(w, kill)
                if "표현 h" not in shapes:
                    shapes["표현 h"] = list(h.shape)
                    shapes["표현 dtype"] = str(h.dtype)
                a = h.numpy()[0]
                p = net.head(h).numpy()[0].squeeze(-1)
                m = obs[:, t]
                out.append(np.concatenate([a[m].mean(0), a[m].std(0)]))
                one.append(float(np.std(p[m])))
        return np.asarray(out, float), np.asarray(one, float)

    base, base1 = feats(None)
    res = {"모양·dtype": shapes,
           "🔴 단언": {"창 = (1, 동네, lookback)": shapes["창 w"] == [1, D_, lb],
                     "표현 = (1, 동네, dim)": shapes["표현 h"] == [1, D_, dim],
                     "float32": shapes["표현 dtype"] == "torch.float32"}}

    # ⑧ 결정성 — 두 번 돌려 **바이트 대조**
    again, _ = feats(None)
    res["⑧ 결정성"] = {
        "sha256 1회": hashlib.sha256(base.tobytes()).hexdigest()[:16],
        "sha256 2회": hashlib.sha256(again.tobytes()).hexdigest()[:16],
        "비트 동일": bool(hashlib.sha256(base.tobytes()).digest()
                      == hashlib.sha256(again.tobytes()).digest())}

    # ⑥ 입력 지우기 — 갈래를 0 으로 넣고 표현이 **바뀌나**
    res["⑥ 입력 지우기"] = {"뜻": "mix 로 들어가는 세 갈래를 하나씩 0 으로 만든다. "
                                "표현이 안 바뀌면 그 갈래는 출력에 안 닿는다(887형)"}
    for kill, nm in (("h", "h 과거창 사영"), ("e", "e 동네 임베딩"),
                     ("g", "g 저계수 이웃혼합")):
        a, a1 = feats(kill)
        res["⑥ 입력 지우기"][nm] = {
            "‖Δ표현‖/‖표현‖": round(float(np.linalg.norm(a - base)
                                     / (np.linalg.norm(base) + 1e-12)), 5),
            "1열축 스피어만(원본 대 지운 것)": round(D._sp(base1, a1), 4),
            "🔴 닿나": bool(np.linalg.norm(a - base) > 1e-8)}
    return res, (base, base1, ts, days)


# ── ① 한 배치 과적합 · ③ 층별 ‖Δθ‖ · ④ 기울기 노름 ─────────────────
def overfit_one_batch(nb: int = 16, steps: int = 400, seed: int = 897):
    import torch
    from state import fieldmodel as F

    ck = torch.load(F.OUT / "enc.pt", map_location="cpu", weights_only=False)
    dim, lb, hz = ck["dim"], ck["lookback"], ck["horizon"]
    codes, days, X = F.field(stats_end=F.TRAIN_END)
    end = next((i for i, d in enumerate(days) if d > F.TRAIN_END), len(days))
    Xtr = X[:, :end]
    D_, T = Xtr.shape
    Z = np.nan_to_num(Xtr, nan=0.0)
    obs = np.isfinite(Xtr).astype(np.float32)
    xs, ys, ms = [], [], []
    for t in range(lb, min(lb + nb, T - hz)):
        xs.append(Z[:, t - lb:t]); ys.append(Z[:, t + hz] - Z[:, t])
        ms.append(obs[:, t + hz] * obs[:, t])
    Xw = torch.tensor(np.stack(xs), dtype=torch.float32)
    Yw = torch.tensor(np.stack(ys), dtype=torch.float32)
    Mw = torch.tensor(np.stack(ms), dtype=torch.float32)

    torch.manual_seed(seed)
    net = _build(dim, lb, D_)()
    theta0 = {k: v.detach().clone() for k, v in net.state_dict().items()}
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    hist, gn = [], {}
    l0 = None
    for s in range(steps):
        opt.zero_grad()
        p = net(Xw)
        loss = (((p - Yw) ** 2) * Mw).sum() / Mw.sum().clamp(min=1)
        loss.backward()
        if s == 0:
            l0 = float(loss)
            gn = {n: round(float(q.grad.norm()), 6)
                  for n, q in net.named_parameters() if q.grad is not None}
        opt.step()
        if s % 50 == 49 or s == steps - 1:
            hist.append({"step": s + 1, "loss": round(float(loss), 7)})
    lf = hist[-1]["loss"]
    d = {n: round(float((net.state_dict()[n] - theta0[n]).norm()), 6) for n in theta0}
    return {"표본": nb, "걸음": steps, "첫 손실": round(l0, 7), "끝 손실": lf,
            "🔴 외웠나(끝/첫 < 0.05)": bool(lf / max(l0, 1e-12) < 0.05),
            "비율": round(lf / max(l0, 1e-12), 5),
            "이력": hist,
            "③ 층별 ‖Δθ‖": d,
            "🔴 죽은 층(‖Δθ‖ == 0)": [n for n, v in d.items() if v == 0.0],
            "④ 첫 스텝 층별 기울기 노름": gn,
            "🔴 NaN/Inf 기울기": [n for n, v in gn.items()
                              if not np.isfinite(v)]}


def cost_note(dim=4, lb=56, Dn=261, K=8):
    """§4 비용 — 파라미터·시간 복잡도·**KV cache 가 되는가**."""
    p = {"emb": Dn * dim, "tconv": lb * dim + dim, "down": Dn * K, "up": K * Dn,
         "mix": 3 * dim * dim + dim, "head": dim + 1}
    return {
        "파라미터(층별)": p, "파라미터 합": int(sum(p.values())),
        "한 날짜 전방 FLOPs(대략)":
            f"tconv {Dn*lb*dim} + down/up {2*Dn*K*dim} + mix {Dn*3*dim*dim} "
            f"≈ {Dn*lb*dim + 2*Dn*K*dim + Dn*3*dim*dim}",
        "시간 복잡도": {
            "현행 인코더": "O(D · (L·d + K·d + d²)) — **lookback L 에 선형**. "
                       "자기주의가 없으므로 L² 항이 없다",
            "동네 자기주의를 넣으면": "O(D²·d) = 261²·d ≈ 6.8e4·d (노트북에서 감당됨)",
            "이벤트 질의 크로스 어텐션": "🔴 **질의가 하나**이므로 O(D·d) — "
                                "L² 도 D² 도 아니다. 「어텐션은 비싸다」가 "
                                "이 자리에서는 틀린 말이다"},
        "🔴 KV cache": {
            "판정": "**구조상 불가**",
            "근거": "KV cache 는 **인과 마스크 + 자기회귀 복호**일 때만 뜻이 있다. "
                  "이 인코더는 고정 56일 창을 한 번에 먹는 **비자기회귀 양방향** "
                  "인코더이고 복호 단계가 없다. 재사용할 과거 K/V 가 없다.",
            "⚠ 셋을 가른다(조항 59)":
                "「쓸 수 있다」/「안 써 봤다」/「구조상 불가」 — 여기는 셋째다",
            "다만 다른 캐시는 가능하다":
                "날짜 t 와 t+1 의 창이 56 중 55 를 공유하므로 **창 캐시**는 "
                "원리상 가능하다. 그런데 `tconv` 가 창 전체에 대한 조밀 Linear 라 "
                "증분 갱신이 안 된다 — **인과 합성곱이나 순환으로 바꿔야** 열린다. "
                "이것은 KV cache 가 아니다"}}


def main():
    t0 = time.time()
    ab, _ = ablate_and_determinism()
    of = overfit_one_batch()
    out = {"stamp": stamp(),
           "§9.1 배선 검사 여덟 — 이 사이클에서 돈 것": {
               "① 한 배치 과적합": of,
               "② 모양·dtype": {k: ab[k] for k in ("모양·dtype", "🔴 단언")},
               "③ 층별 ‖Δθ‖": of["③ 층별 ‖Δθ‖"],
               "④ 기울기 노름": of["④ 첫 스텝 층별 기울기 노름"],
               "⑤ 항등 붕괴": "❌ 못 돈다 — 새 블록이 없다(L1 을 안 열었다). "
                          "L1 을 여는 사이클의 첫 검사로 남긴다",
               "⑥ 입력 지우기": ab["⑥ 입력 지우기"],
               "⑦ 라벨 순열": "✅ decay897.perm_null — 유보 라벨 도메인 안 순열 "
                          "1,000 뽑기. 널 평균 −0.00008 · SD 0.01626(표현 팔)",
               "⑧ 결정성": ab["⑧ 결정성"]},
           "§4 비용": cost_note(),
           "벽시계(초)": round(time.time() - t0, 1)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str))
    print(json.dumps({"과적합": {k: of[k] for k in
                              ("첫 손실", "끝 손실", "비율", "🔴 외웠나(끝/첫 < 0.05)",
                               "🔴 죽은 층(‖Δθ‖ == 0)")},
                      "결정성": ab["⑧ 결정성"]["비트 동일"],
                      "입력 지우기": {k: v for k, v in ab["⑥ 입력 지우기"].items()
                                 if k != "뜻"}}, ensure_ascii=False, indent=1))
    print("→", OUT)


if __name__ == "__main__":
    main()
