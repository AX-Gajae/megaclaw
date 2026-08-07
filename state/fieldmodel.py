"""장 사전학습 — 110만 관측으로 표현을 배우고, 팝업 89건은 **읽어내기만** 한다(노트 645).

**왜 이 설계가 나왔나.** 노트 638·640 이 같은 벽을 두 번 쳤다 --- 팝업 89행에
열을 더하면 성적이 내려간다. 그것도 **값을 섞은 위약이 진짜 날씨보다 더**
내려갔다(−0.0344 대 −0.0283). 즉 문제는 신호의 질이 아니라 **89행에 열을
더한다는 행위 자체**다. 축을 아무리 잘 만들어도 이 길로는 못 간다.

노트 644 가 다른 길을 열었다. 유동인구가 **장**이라는 것이 측정됐다 ---
이상치의 같은 날 상관이 거리에 따라 매끄럽게 감쇠한다(0~10km +0.787 ·
10~25km +0.656 · 25~50km +0.488 · 50~100km +0.236, 전국 공통 충격을 뺀 뒤).
그리고 그 장은 **264 시군구 × 1,375일 × 3구분 ≈ 110만 관측**이다.

    89건은 동역학을 배우기엔 너무 적다. 그런데 110만은 충분하다.
    그러니 **동역학은 장에서 배우고, 89건은 그 표현을 읽어내는 데만 쓴다.**

GraphCast 가 나비에-스토크스를 안 넣고 ERA5 만 먹여서 물리 모델을 이긴 것과
같은 구조다. 방정식을 몰라도 된다 --- 다만 **조밀한 장 · 같은 변수의 반복 ·
충분한 시간 스텝**이 있어야 하고, 우리는 이제 그 셋을 갖췄다.

──────────────────────────────────────────────────────────────
**설계 결정 다섯. 전부 측정에서 나왔다.**

**① 목표를 '다음날' 로 두면 안 된다.**
   노트 644: 어제만 봐도 R² = **0.6387** 이다. 다음날 맞히기를 목표로 하면
   신경망이 배우는 것은 *"어제를 베껴라"* 하나다. 표현이 안 생긴다.
   → 지속성이 무너지는 지평을 재서 고른다(``horizons()``). 그리고 손실은
     **지속성 잔차** 위에서 잰다 --- 베끼기로는 0점인 과제로 만든다.

**② 확산을 하루 격자로 배우려 하지 않는다.**
   노트 644: 같은 날 0~10km 상관이 0.787 인데 하루 지연 증분은 R² +0.0017
   이다(이웃 계수 0.071 · t=17 --- **유의하지만 실익이 없다**). 이동이 관측
   간격보다 빠르다. 일 단위 자료로 확산항을 배우게 하는 것은 없는 것을
   배우라는 것이다.
   → 이웃 정보는 **같은 날 공간 구조**로 준다(공간 인접을 모형이 쓰게 하되
     시간 지연 확산을 목표로 삼지 않는다).

**③ 인코더는 2025년 이전만 본다. 그리고 얼린다.**
   판은 2025년 이후를 유보로 채점한다. 인코더가 2022~2026 전체를 보면
   **유보가 표현에 새어든다** --- 축을 잘 만든 것처럼 보이지만 미래를 본
   것이다. 이 실험실이 460노트 동안 반복해서 당한 모양이다(타깃 분모 오염 ·
   공간 링크 36% 오연결). 그래서 학습 구간을 하드코딩하고, 읽어내기 단계에서
   가중치를 **동결**한다.

**④ 모형을 작게 한다.**
   자료가 110만 스칼라다. 파라미터가 그것에 근접하면 외운다. 목표는
   **10만 이하**. 큰 트랜스포머는 여기서 쓸 자리가 없다.

**⑤ 읽어내기는 기존 판에 꽂는다.**
   표현을 새 지표로 재면 이전 641개 노트와 비교가 안 된다. 얼린 인코더가 낸
   벡터를 **팝업 축으로** 넣고 `lab/board` 로 잰다 --- 같은 자, 같은 씨앗 12,
   같은 문턱.

──────────────────────────────────────────────────────────────
**반증 조건.** 얼린 표현 축이 원시 축(`vis_out`)을 팝업 도메인 문턱만큼 못
이기면 **사전학습은 산 것이 없다.** 그때는 이 파일을 버린다.

**미리 적는 위험.** ⑤ 가 다시 "89행에 열을 더하는" 일이다 --- 노트 640 이
막은 바로 그 길. 그래서 표현을 **저차원으로 압축해서** 넣는다(기본 d=4).
열 넷도 위약 −0.0344 를 피할 수 있다는 보장이 없다. 만약 여기서도 같은
벽이면, 남은 길은 **팝업을 예측 대상에서 빼고 장 자체를 제품으로 삼는 것**
이다(어느 동네가 뜨는지 예보). 그것도 결과로 적는다.

쓰는 법::

    python3 -m state.fieldmodel horizons     # ① 지평 고르기 (측정)
    python3 -m state.fieldmodel pretrain     # ③④ 학습 (2025 이전만)
    python3 -m state.fieldmodel readout      # ⑤ 축으로 뽑기
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/state/fieldmodel"

#: 인코더가 볼 수 있는 마지막 날. **판의 유보(2025+)를 안 본다.**
TRAIN_END = "20241231"
#: 표현 차원. 작게 --- 노트 640 이 열 셋에 −0.0344 를 봤다.
DIM = 4
#: 과거 몇 날을 입력으로 보나
LOOKBACK = 56


# ── 자료 ───────────────────────────────────────────────────────
def field(div: str = "2", stats_end: str | None = None,
          holiday: bool = True):
    """(동네코드, 날짜, 이상치행렬).

    **정규화 통계도 누출이다.** 처음 돌렸을 때 동네 평균과 요일 평균을 전
    구간(2022~2026)으로 계산했는데, 그러면 검증·유보 기간의 값이 그 평균에
    섞여 들어간다. 판이 460노트 동안 당한 것이 정확히 이런 모양이라(타깃
    분모 오염 · 공간 링크 오연결) 여기서 막는다.

    ``stats_end`` 를 주면 **그 날짜까지로만** 평균을 계산해서 전 구간에
    적용한다. 날마다 빼는 전국 공통 충격은 그날 안에서만 계산하므로 시간
    누출이 아니다 --- 그건 그대로 둔다.
    """
    import datetime
    from ingest.visitors import series
    ser = series(div)
    days = sorted({d for v in ser.values() for d in v})
    # **어느 동네가 판에 드는지도 학습 구간으로만 정한다**(노트 669).
    # 예전에는 덮음을 **전 구간**으로 재서, 2025~2026 에만 자료가 있는 동네가
    # *미래 덮음 덕에* 뽑혔다. 정규화 통계 누출(노트 645)과 같은 병이고 층만
    # 다르다 --- 그쪽은 *값*이 새고 이쪽은 **표본 구성**이 샌다.
    pick = days if stats_end is None else [d for d in days if d <= stats_end]
    pset = set(pick)
    codes = sorted(c for c in ser
                   if sum(1 for d in ser[c] if d in pset) > len(pick) * 0.9)
    M = np.full((len(codes), len(days)), np.nan)
    di = {d: i for i, d in enumerate(days)}
    for r, c in enumerate(codes):
        for d, v in ser[c].items():
            M[r, di[d]] = v
    X = np.log10(np.where(M > 0, M, np.nan))
    fit = np.array([True] * len(days)) if stats_end is None else \
        np.array([d <= stats_end for d in days])
    X = X - np.nanmean(X[:, fit], axis=1, keepdims=True)      # 동네 수준
    dow = np.array([datetime.date(int(d[:4]), int(d[4:6]), int(d[6:8])).weekday()
                    for d in days])
    for w in range(7):                                        # 요일
        m = dow == w
        X[:, m] -= np.nanmean(X[:, m & fit], axis=1, keepdims=True)
    X = X - np.nanmean(X, axis=0, keepdims=True)              # 전국 공통 충격(날 안)
    if holiday:
        # **공휴일을 동네마다 따로 뺀다**(노트 689).
        #
        # 노트 689 가 g 의 큰 이상치를 귀속했더니 **광역 52/60 · 동네 52/60 이
        # 공휴일±3일 또는 자료 끝단** 이었다(추석 33 · 설 14). 전국 공통항을
        # 이미 뺐는데도 남은 이유는 **명절이 전국 균일이 아니기** 때문이다 ---
        # 귀성으로 20251006 에 경북 **+6.2** · 서울 **−6.0** · 경기 **−6.0** 으로
        # 부호가 정확히 반대다. 전국 평균을 빼면 그 **지역 편차가 그대로 남는다.**
        #
        # 그래서 요일과 같은 방식으로, **동네마다** 세 갈래의 평균을 뺀다 ---
        # 명절(설·추석 ±2일) · 그밖 공휴일 · 평일. 명절을 따로 두는 이유는
        # 귀성이 어린이날 같은 공휴일과 다른 물건이라서다.
        #
        # 안 빼면 g 는 사실상 달력 축의 재발견이고, 달력은 이미 `cal_*` 로
        # 판에 들어 있다.
        from ingest.derive_features import HOLIDAYS
        hs = {date(*(int(x) for x in h.split("-"))) for h in HOLIDAYS}
        big = {h for h in hs if _is_big_holiday(h, hs)}
        kind = np.zeros(len(days), np.int8)
        for i, d in enumerate(days):
            dd = date(int(d[:4]), int(d[4:6]), int(d[6:8]))
            if any(dd + timedelta(days=o) in big for o in range(-2, 3)):
                kind[i] = 2                       # 명절
            elif dd in hs:
                kind[i] = 1                       # 그밖 공휴일
        for kk in (1, 2):
            m = kind == kk
            if m.sum() >= 5:
                X[:, m] -= np.nanmean(X[:, m & fit], axis=1, keepdims=True)
    return codes, days, X


def _is_big_holiday(h, hs) -> bool:
    """설·추석인가 --- **사흘 연속 공휴일의 가운데**로 알아낸다.

    공휴일 표에 이름이 없으므로(날짜만 있다) 구조로 판정한다. 한국에서 사흘
    연속으로 공휴일인 것은 설과 추석뿐이다(연휴가 주말과 겹쳐 늘어난 것은
    표에 안 들어 있다)."""
    return ((h - timedelta(days=1)) in hs) and ((h + timedelta(days=1)) in hs)


# ── ① 지평 고르기 ─────────────────────────────────────────────
def horizons(hs=(1, 3, 7, 14, 30, 60, 90, 180)) -> dict:
    """**지속성이 어디서 무너지나.**

    이걸 먼저 재는 이유가 설계의 핵심이다. h=1 에서 R²=0.64 라면 그 지평의
    과제는 *베끼기* 다 --- 신경망을 붙일 자리가 아니다. 지속성이 낮아지는
    지평에서 비로소 배울 것이 남는다.

    **`stats_end` 를 채점 경로와 같게 준다**(노트 669). 예전에는 여기서만
    `field()` 를 맨몸으로 불러 **전 구간 통계**로 지속성을 쟀다. 지평 고르기는
    채점이 아니라 설계 판단이지만, *그 판단이 유보를 보고 내려졌다*면 h=30 이
    왜 골라졌는지를 나중에 못 변호한다.
    """
    _c, _d, X = field(stats_end=TRAIN_END)
    out = {}
    for h in hs:
        a, b = X[:, :-h].ravel(), X[:, h:].ravel()
        ok = np.isfinite(a) & np.isfinite(b)
        out[h] = {"지속성 R2": round(float(np.corrcoef(a[ok], b[ok])[0, 1] ** 2), 4),
                  "표본": int(ok.sum())}
    return out


# ── ③④ 사전학습 ──────────────────────────────────────────────
def pretrain(dim: int = DIM, lookback: int = LOOKBACK, horizon: int = 30,
             epochs: int = 600, seed: int = 0, holiday: bool = True,
             placebo: bool = False, save: bool = True, every: int = 20) -> dict:
    """장에서 표현을 배운다. **손실은 지속성 잔차 위에서 잰다.**

    베끼기가 0점이 되도록 과제를 만든다 --- 목표는 `X[t+h]` 가 아니라
    `X[t+h] − 지속성예측` 이다. 그러면 모형이 이길 수 있는 유일한 길은
    **다른 동네와 과거 무늬에서 정보를 얻는 것**이다.

    구현은 작게 간다(설계 ④). 동네 임베딩 + 과거 창의 선형 사영 두 층.

    **`placebo=True` --- 목표를 동네 안에서 시간축으로 섞는다**(노트 702).
    노트 669 가 위약 설계를 정의했지만 **손잡이가 코드에 없어서** 다음 사람이
    모형을 재구현하게 됐고, 그 재구현이 **저계수 이웃 혼합(`down`/`up`)을
    빠뜨렸다** --- 즉 잴 대상을 지운 채로 쟀다. 그래서 손잡이를 여기 둔다:
    **위약은 같은 코드에서 나와야 한다.**

    `holiday=False` 는 노트 690 이전 g 를 재현한다.

    🔴 **`holiday=True` 를 기본으로 두는 이유는 예보가 아니라 식별이다**(노트 736).
    공휴일 항을 빼면 **유보 R² 가 +0.1200 → +0.1848 로 오른다**(짝 차 −0.0648 ·
    2σ 밖 · 씨앗 8/8 일치). 그런데 노트 690 이 그 항을 넣은 이유는 g 의 큰
    이상치 **87% 가 달력**이었던 것을 **48%** 로 떨어뜨리는 것이었다 --- 즉 그
    +0.065 는 **명절을 다시 먹어서** 나오고, 그러면 `g_지역` 이 대부분 명절이라
    `cal_*` 축의 재발견이 된다. **한 층의 예보가 오르는 것이 다른 층의 식별을
    깨면 개선이 아니다.** 그래서 **장의 자는 유보 R² 하나가 아니라 (유보 R²,
    달력 귀속률) 짝**이다. 노트 703 이 R² 만 보고 '공휴일 항이 학습에 도움' 이라
    적은 것을 **노트 736 이 철회했다.**
    `save=False` 면 `enc.pt` 를 안 덮는다 --- 위약 팔이 진짜 가중을 밀어내면 안 된다.
    """
    try:
        import torch
        import torch.nn as nn
    except ImportError:
        return {"오류": "torch 없음 — pip install torch 하거나 numpy 판을 쓴다"}
    torch.manual_seed(seed)
    # 정규화 통계도 학습 구간까지로만 잡는다(누출 차단)
    codes, days, X = field(stats_end=TRAIN_END, holiday=holiday)
    end = next((i for i, d in enumerate(days) if d > TRAIN_END), len(days))
    Xtr = X[:, :end]                                  # ③ 유보를 안 본다
    D, T = Xtr.shape
    Z = np.nan_to_num(Xtr, nan=0.0)
    obs = np.isfinite(Xtr).astype(np.float32)

    xs, ys, ds = [], [], []
    for t in range(lookback, T - horizon):
        win = Z[:, t - lookback:t]
        tgt = Z[:, t + horizon]
        base = Z[:, t]                                # 지속성 예측
        m = obs[:, t + horizon] * obs[:, t]
        xs.append(win); ys.append(tgt - base); ds.append(m)
    Yarr = np.stack(ys)
    if placebo:
        # **동네 안에서 시간축으로만 섞는다.** 관측 무늬(`Mw`)는 그대로 두므로
        # 결측 구조와 분포는 안 바뀌고 '이웃·과거가 나르는 정보' 만 사라진다.
        rng = np.random.default_rng(702 + seed)
        for j in range(Yarr.shape[1]):
            rng.shuffle(Yarr[:, j])
    Xw = torch.tensor(np.stack(xs), dtype=torch.float32)      # (N, D, L)
    Yw = torch.tensor(Yarr, dtype=torch.float32)              # (N, D)
    Mw = torch.tensor(np.stack(ds), dtype=torch.float32)

    # **이웃 요약을 전체 평균으로 두면 안 된다.** 이상치를 만들 때 날마다
    # 전국 평균을 이미 뺐으므로(노트 644 의 통제 ③) 동네 전체 평균은 **항상
    # 0 이다.** 그 항은 아무것도 안 나른다. 대신 저계수 공간 혼합을 배우게
    # 한다 --- 264개를 k개 축으로 모았다가 되돌리면 모형이 스스로 '어느
    # 동네들이 같이 움직이나' 를 찾는다. D×D 를 다 두면 7만 파라미터라
    # 설계 ④(10만 이하)를 잡아먹지만, k=8 이면 4천이다.
    K = 8

    class Enc(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb = nn.Embedding(D, dim)
            self.tconv = nn.Linear(lookback, dim)      # 과거 창 → 표현
            self.down = nn.Linear(D, K, bias=False)    # 동네 → 잠재 무리
            self.up = nn.Linear(K, D, bias=False)      # 잠재 무리 → 동네
            self.mix = nn.Linear(dim * 3, dim)         # 자기 + 임베딩 + 이웃
            self.head = nn.Linear(dim, 1)

        def rep(self, w):
            e = self.emb.weight.unsqueeze(0).expand(w.shape[0], -1, -1)
            h = torch.tanh(self.tconv(w))              # (N, D, dim)
            g = self.up(self.down(h.transpose(1, 2))).transpose(1, 2)  # 저계수 혼합
            return torch.tanh(self.mix(torch.cat([h, e, g], -1)))

        def forward(self, w):
            return self.head(self.rep(w)).squeeze(-1)

    net = Enc()
    nparam = sum(p.numel() for p in net.parameters())
    opt = torch.optim.Adam(net.parameters(), lr=3e-3)
    n = len(Xw)
    cut = int(n * 0.8)
    hist = []
    # **걸음 수를 고정하지 않는다 --- 검증으로 최선 지점을 잡는다**(노트 735).
    #
    # 원래는 `epochs=60` 고정이었다. 노트 734 가 걸음을 갈라 재니 60 은 **덜
    # 배운 자리**여서 어디에 앉나가 초기값이 정했고(씨앗 SD **0.2735**), 200
    # 걸음에서 씨앗 넷이 모이며(SD **0.0123** · 유보 R² **+0.1154**), 600 이후는
    # **학습 손실이 계속 내려가는데 검증이 무너지는 과적합**이다(유보 −0.363 →
    # −1.768). **즉 노트 703 의 0.134 는 60 걸음 · 씨앗 0 이 우연히 좋았던
    # 값이다.**
    #
    # 그래서 최선 가중을 **학습 구간 검증으로만** 고른다 --- 유보를 보고 고르면
    # 그 순간 유보가 아니다. 검증은 학습 창을 시간순 8:2 로 가른 뒤쪽이고 전부
    # `TRAIN_END` 이전이다.
    best = {"R2": -float("inf"), "epoch": 0, "state": None}
    for ep in range(epochs):
        net.train()
        opt.zero_grad()
        p = net(Xw[:cut])
        loss = (((p - Yw[:cut]) ** 2) * Mw[:cut]).sum() / Mw[:cut].sum().clamp(min=1)
        loss.backward()
        opt.step()
        if ep % every == every - 1 or ep == epochs - 1:
            net.eval()
            with torch.no_grad():
                pv = net(Xw[cut:])
                mv = Mw[cut:]
                mse = (((pv - Yw[cut:]) ** 2) * mv).sum() / mv.sum().clamp(min=1)
                var = ((Yw[cut:] ** 2) * mv).sum() / mv.sum().clamp(min=1)
            r2 = float(1 - mse / var)
            hist.append({"epoch": ep + 1,
                         "학습 MSE": round(float(loss.detach()), 5),
                         "검증 R2(지속성 대비)": round(r2, 4)})
            if r2 > best["R2"]:
                best = {"R2": r2, "epoch": ep + 1,
                        "state": {k: v.detach().clone()
                                  for k, v in net.state_dict().items()}}
    if best["state"] is not None:
        net.load_state_dict(best["state"])     # **최선 지점으로 되돌린다**
    if save and not placebo:
        OUT.mkdir(parents=True, exist_ok=True)
        import torch as _t
        _t.save({"state": net.state_dict(), "codes": codes, "dim": dim,
                 "lookback": lookback, "horizon": horizon}, OUT / "enc.pt")
    return {"동네": D, "학습 날": T, "표본": n, "파라미터": nparam,
            "공휴일 뺌": holiday, "위약": placebo,
            "학습 구간 끝": TRAIN_END, "이력": hist,
            "**최선 걸음**": best["epoch"],
            "**최선 검증 R2**": round(best["R2"], 4),
            "고른 자": "학습 구간 검증(유보 아님) --- 노트 735",
            "해석": "검증 R2 는 **지속성을 이미 뺀 잔차 위에서** 잰 것이다. "
                    "0 이면 베끼기보다 나은 게 없다는 뜻이다."}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "horizons"
    if cmd == "horizons":
        print(json.dumps(horizons(), ensure_ascii=False, indent=1))
    elif cmd == "pretrain":
        print(json.dumps(pretrain(), ensure_ascii=False, indent=1))
    else:
        print("horizons | pretrain")
