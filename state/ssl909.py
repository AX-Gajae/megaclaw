# -*- coding: utf-8 -*-
"""팔 909-ㅁ — **자기지도 표현 학습**. 라벨 y 를 한 비트도 안 쓰는 프리텍스트.

사전등록: `docs/prereg_909_ssl.md` (측정 **전에** 저장소에 박혔다).

--------------------------------------------------------------------------
왜 이 파일이 있나
--------------------------------------------------------------------------
`state/masked_encoder.py`(노트 60~62·84~88)가 **마스크를 입력으로 받는 인코더**를
이미 지어 놓았다. 그런데 그 파일의 학습 루프는

    손실 = **라벨 MSE** + λ · 복원 MSE

라서 **지도학습이다.** 노트 897 이 그 파일을 *"아무도 안 부른다"* 로 닫았고,
노트 698·721 은 그 계열을 *"판을 못 움직인다"* 로 닫았다. 🔴 **판 ρ 는 라벨 있는
유보 3,775 위의 지도학습 순위 상관이므로, 그 자로 파운데이션을 재면 「덮음을 산 것」이
언제나 손실로 잡힌다.**

이 파일은 `masked_encoder` 의 **설계를 되살리되 라벨 머리를 통째로 뺀다**:

    입력   값 P열 + 마스크 P열 = 2P          (결측은 0, 마스크가 알린다)
    인코더 공유 MLP 2P → h → h/2 → k, GELU
    복호   k → h/2 → P
    손실   **가린 칸에서만** 낸 복원 MSE      ← 라벨이 없다

`masked_encoder.train_one` 의 `heads`·`Yt`·`Ridge(…, y)` 가 **여기에 없다**는 것을
`assert_no_labels()` 가 소스 대조로 단언한다(조항 59: '없다'와 '안 썼다'는 다르다 —
그래서 **코드로** 센다).

--------------------------------------------------------------------------
🔴 이 파일이 지키는 것
--------------------------------------------------------------------------
- **라벨 0비트** — 프리텍스트 함수에 `y` 가 인자로도 클로저로도 안 들어간다
- **누출 0** — LODO 에서 뺀 도메인의 행이 프리텍스트 학습 집합에 **0행**
- **표준화도 라벨을 안 본다** — (도메인, 축) 평균·표준편차는 **관측 칸**으로만,
  그리고 **자 (다) 로 떼어 둔 평가 칸을 빼고** 낸다
- **결정성** — 같은 씨앗 두 번이면 표현 행렬 sha256 이 비트 동일

읽기 전용 의존: `runners/ff753`(챔피언 축 구성) · `lab/harness`.
"""
from __future__ import annotations

import hashlib
import inspect
import re
from dataclasses import dataclass, field

import numpy as np
import torch
import torch.nn as nn

SEED = 909
EVAL_CELL_FRAC = 0.10      #: 자 (다) 로 떼어 두는 관측 칸의 비율
MASK_P = 0.30              #: 프리텍스트가 매 스텝 가리는 비율
MIN_OBS_PER_AXIS = 5       #: 이보다 적게 관측된 (도메인,축) 은 죽은 축으로 본다


# ── 자료 ────────────────────────────────────────────────────────────────
@dataclass
class Bank:
    """12도메인을 **하나의 열 공간**(축 이름 합집합)에 올린 것."""
    names: list                      #: 길이 P — 열 공간
    doms: list                       #: 도메인 순서
    V: dict = field(default_factory=dict)      #: dom → (n,P) 표준화된 값 (미관측 0)
    M: dict = field(default_factory=dict)      #: dom → (n,P) 학습에 보이는 관측 표시자
    Mall: dict = field(default_factory=dict)   #: dom → (n,P) 원 관측 표시자
    Meval: dict = field(default_factory=dict)  #: dom → (n,P) 자 (다) 평가 칸
    stats: dict = field(default_factory=dict)  #: (dom,j) → (mu, sd)
    Vraw: dict = field(default_factory=dict)   #: dom → (n,P) 원 값(표준화 전)

    def rows(self, dom):
        return self.V[dom].shape[0]

    def x(self, dom):
        """인코더 입력 [값 | 마스크] — 평가 칸은 **가려서** 넣는다."""
        return np.hstack([self.V[dom] * self.M[dom], self.M[dom]])


def build_bank(data, seed: int = SEED) -> Bank:
    """챔피언 `Data` → `Bank`. **라벨 y 를 안 읽는다**(`data.dom[d][2]` 를 안 만진다)."""
    doms = list(data.dom)
    names = []
    for d in doms:
        for a in (data.names.get(d) or []):
            if a not in names:
                names.append(a)
    P = len(names)
    idx = {a: j for j, a in enumerate(names)}
    rng = np.random.default_rng(seed)
    b = Bank(names=names, doms=doms)
    for d in doms:
        A, M, _y, _t = data.dom[d]                    # _y 는 **안 쓴다**
        nm = list(data.names.get(d) or [])
        n = A.shape[0]
        Vr = np.zeros((n, P))
        Mo = np.zeros((n, P))
        for j0, a in enumerate(nm):
            j = idx[a]
            Vr[:, j] = A[:, j0]
            Mo[:, j] = (M[:, j0] > 0).astype(float)
        # 자 (다) 평가 칸 — 관측 칸의 EVAL_CELL_FRAC
        Me = (rng.random((n, P)) < EVAL_CELL_FRAC) & (Mo > 0)
        Mtr = (Mo > 0) & ~Me
        Vz = np.zeros((n, P))
        for j in range(P):
            sel = Mtr[:, j]
            if sel.sum() < MIN_OBS_PER_AXIS:
                Mtr[:, j] = False
                Me[:, j] = False
                continue
            mu = float(Vr[sel, j].mean())
            sd = float(Vr[sel, j].std())
            if sd < 1e-9:                              # 상수 축 — 정보가 0
                Mtr[:, j] = False
                Me[:, j] = False
                continue
            b.stats[(d, j)] = (mu, sd)
            col = (Vr[:, j] - mu) / sd
            Vz[:, j] = np.where(Mo[:, j] > 0, col, 0.0)
        b.Vraw[d] = Vr
        b.V[d] = Vz
        b.Mall[d] = Mo
        b.M[d] = Mtr.astype(float)
        b.Meval[d] = Me.astype(float)
    return b


def attach_text(b: Bank, T: dict, k: int = 64, exclude: str | None = None,
                seed: int = SEED) -> Bank:
    """문자 n-gram 해싱 → TF-IDF → SVD(k) 를 **블록으로 덧붙인다**(라벨 0비트).

    `T` = dom → 길이 n 의 문자열 리스트. 빈 문자열은 텍스트 없음이다.
    `exclude` 도메인의 행은 **SVD 적합에서 뺀다**(자 (가) 의 누출 검사).
    """
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import HashingVectorizer, TfidfTransformer
    docs, owner = [], []
    for d in b.doms:
        for i, s in enumerate(T.get(d) or []):
            if s:
                docs.append(s)
                owner.append((d, i))
    if len(docs) < 50:
        return b
    hv = HashingVectorizer(analyzer="char_wb", ngram_range=(3, 4),
                           n_features=2 ** 18, alternate_sign=False, norm=None)
    X = hv.transform(docs)
    X = TfidfTransformer().fit_transform(X)
    fit_rows = np.array([o[0] != exclude for o in owner])
    kk = int(min(k, max(2, min(X.shape) - 1)))
    svd = TruncatedSVD(n_components=kk, random_state=seed)
    svd.fit(X[fit_rows])
    Z = svd.transform(X)
    Z = (Z - Z[fit_rows].mean(0)) / (Z[fit_rows].std(0) + 1e-9)
    P0 = len(b.names)
    b.names = list(b.names) + [f"txt{j:02d}" for j in range(kk)]
    for d in b.doms:
        n = b.V[d].shape[0]
        b.V[d] = np.hstack([b.V[d], np.zeros((n, kk))])
        b.M[d] = np.hstack([b.M[d], np.zeros((n, kk))])
        b.Mall[d] = np.hstack([b.Mall[d], np.zeros((n, kk))])
        b.Meval[d] = np.hstack([b.Meval[d], np.zeros((n, kk))])
        b.Vraw[d] = np.hstack([b.Vraw[d], np.zeros((n, kk))])
    for (d, i), z in zip(owner, Z):
        b.V[d][i, P0:] = z
        b.M[d][i, P0:] = 1.0
        b.Mall[d][i, P0:] = 1.0
    return b


# ── 프리텍스트 ──────────────────────────────────────────────────────────
class MaskedAE(nn.Module):
    """`state/masked_encoder.Net` 의 꼴 그대로. **라벨 머리가 없다.**"""

    def __init__(self, P: int, k: int = 8, h: int = 64):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(2 * P, h), nn.GELU(),
                                 nn.Linear(h, h // 2), nn.GELU(),
                                 nn.Linear(h // 2, k))
        self.dec = nn.Sequential(nn.Linear(k, h // 2), nn.GELU(),
                                 nn.Linear(h // 2, P))

    def forward(self, x):
        z = self.enc(x)
        return z, self.dec(z)


def pretrain(V: np.ndarray, M: np.ndarray, *, k: int = 8, h: int = 64,
             steps: int = 400, lr: float = 3e-3, wd: float = 1e-4,
             p_mask: float = MASK_P, seed: int = 0, record_every: int = 20,
             fixed_hide: bool = False):
    """🔴 **라벨 y 가 인자에도 본문에도 없다.** 가린 칸 복원만 한다.

    V — (N,P) 표준화된 값(미관측 0) · M — (N,P) 관측 표시자.
    돌려주는 것: (net, 손실 곡선). 손실 곡선은 **가린 칸에서만** 낸 MSE.
    """
    torch.manual_seed(seed)
    g = torch.Generator().manual_seed(seed)
    N, P = V.shape
    Vt = torch.tensor(V, dtype=torch.float32)
    Mt = torch.tensor(M, dtype=torch.float32)
    net = MaskedAE(P, k=k, h=h)
    opt = torch.optim.Adam(net.parameters(), lr=lr, weight_decay=wd)
    curve = []
    #: `fixed_hide` — 가림 무늬를 **한 번만** 뽑아 고정한다. 아키텍처.md §9.1 의
    #: 「한 배치 과적합」은 표적이 고정일 때만 뜻이 있는 검사이기 때문이다
    #: (표적이 매 스텝 바뀌면 「못 외운다」가 배선 고장을 뜻하지 않는다).
    hide0 = ((torch.rand(N, P, generator=g) < p_mask) * Mt) if fixed_hide else None
    for s in range(steps):
        hide = hide0 if fixed_hide else (torch.rand(N, P, generator=g) < p_mask) * Mt
        keep = Mt * (1 - hide)
        x = torch.cat([Vt * keep, keep], dim=1)
        _z, rec = net(x)
        num = (((rec - Vt) ** 2) * hide).sum()
        den = hide.sum().clamp(min=1.0)
        loss = num / den
        opt.zero_grad()
        loss.backward()
        opt.step()
        if s % record_every == 0 or s == steps - 1:
            curve.append([s, round(float(loss.item()), 6)])
    net.eval()
    return net, curve


def encode(net, V: np.ndarray, M: np.ndarray) -> np.ndarray:
    x = torch.tensor(np.hstack([V * M, M]), dtype=torch.float32)
    with torch.no_grad():
        return net(x)[0].numpy()


def reconstruct(net, V: np.ndarray, M: np.ndarray) -> np.ndarray:
    x = torch.tensor(np.hstack([V * M, M]), dtype=torch.float32)
    with torch.no_grad():
        return net(x)[1].numpy()


# ── 단언 ────────────────────────────────────────────────────────────────
_LABEL_PAT = re.compile(r"\b(y|Y|label|labels|라벨|Yt|heads)\b")


def _code_only(src: str) -> str:
    """주석·docstring 을 지우고 **실행되는 토큰만** 남긴다.

    🔴 이 함수가 없으면 *"라벨 y 를 안 쓴다"* 라고 적은 **설명문 자체**가
    검사에 걸린다. 실제로 초판이 그렇게 걸렸다 — 검사가 일하고 있다는 증거다.
    """
    import io
    import tokenize
    out = []
    prev_type = tokenize.INDENT
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                continue
            if tok.type == tokenize.STRING and prev_type in (
                    tokenize.INDENT, tokenize.NEWLINE, tokenize.NL,
                    tokenize.DEDENT, tokenize.ENCODING):
                prev_type = tok.type            # docstring — 버린다
                continue
            out.append(tok.string)
            prev_type = tok.type
    except (tokenize.TokenError, IndentationError):
        return src
    return " ".join(out)


def assert_no_labels() -> dict:
    """🔴 프리텍스트 학습 루프에 라벨이 **한 비트도** 없음을 소스로 대조한다.

    `masked_encoder.train_one` 과 나란히 세워 **차이를 수로 낸다** —
    '안 썼다' 를 말이 아니라 대조로 적기 위해서다(조항 59).
    """
    mine = _code_only(inspect.getsource(pretrain))
    hits = sorted(set(_LABEL_PAT.findall(mine)))
    try:
        from . import masked_encoder as ME
        theirs = _code_only(inspect.getsource(ME.train_one))
        their_hits = sorted(set(_LABEL_PAT.findall(theirs)))
    except Exception as e:                                   # noqa: BLE001
        their_hits = [f"못 읽었다: {type(e).__name__}"]
    sig = list(inspect.signature(pretrain).parameters)
    return {
        "pretrain 서명": sig,
        "🔴 서명에 라벨 인자": [p for p in sig if _LABEL_PAT.fullmatch(p)],
        "🔴 pretrain 본문의 라벨 토큰": hits,
        "대조 · masked_encoder.train_one 본문의 라벨 토큰": their_hits,
        "판정": "라벨 0비트" if not hits and not [p for p in sig if _LABEL_PAT.fullmatch(p)]
                else "🔴 라벨 토큰이 발견됐다 — 측정 중단",
    }


def sha_of(Z: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(
        np.round(Z.astype(np.float64), 6)).tobytes()).hexdigest()[:16]
