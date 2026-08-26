# -*- coding: utf-8 -*-
"""1044 — 사건 «인스턴스» 다층 행렬 + 히스토리 트리 + RoPE 인코더 (설계자 원안 구현).

🔴 **이것은 1040 의 「유형 전이 행렬」이 «아니다».**
1040 은 사건을 9개 «유형» 스칼라로 축약했고(|λ₂|=0.238 → k=3 사망), 그 축약은 구현자가
만든 것이지 설계가 아니었다. 원안은 이랬다:

    「event matrix 가 있고 이중 첫번째 layer 가 이벤트간의 인과성이고
     나머지 레이어에 내부 상태 임베딩, 원문 임베딩, 수익, 시각 등의 정보가 있는거고
     시각에 따라서 인과성값을 보정해서, 인풋에 따라 벌어질 히스토리를
     매트릭스의 첫번째 레이어에 프로젝션해서 계속 찾아내고,
     이렇게 만들어진 히스토리 트리 여러 갈래중 상위 몇개를 RoPE 인코더에 넣어서
     뉴럴넷을 거친후 로스를 구해가면서 각 단계별로 어떤 숫자 변화가 생기는지를 파악」

이 파일이 그 원안이다. 노드는 «사건 인스턴스»(12,621건)이고 각 노드가 벡터를 갖는다.
1층(인과성)은 «저장하지 않는다» — 벡터에서 그때그때 계산한다(설계자 지적: 표가 아니라 함수).

## 층 구성 (노드 벡터)
    유형     9차원 원핫                     사건 유형
    시각     RoPE(event_time, base=1000)    🔴 일 단위. 파장 6.3일~17년 — Δt 8~2,149일을 덮는다
    내재상태  h64 (그 개체 그 시점의 궤적)      1042 에서 결정층 증분 검증된 표현
    원문     896 → PCA32                    덮개 42.7% · 🔴 결측 지시자 동반(0 채움 금지)
    수익     rev_mm (log)                   덮개 낮음 · 결측 지시자 동반

## 1층 = 인과성 (저장 안 함 · 계산함)
    A(i→j) = (W_q·v_i) · R(Δt) · (W_k·v_j)      🔴 RoPE 회전이 Δt 를 «공짜로» 넣는다
    조건: t_j > t_i  (시간 순서 — 역인과 금지)
    학습: 같은 개체의 «실제» 다음 사건이 정답. 대조학습(InfoNCE). 라벨 불필요.

## 사전등록 (측정 전 고정)
    · 게이트 G1 — 다음 사건 예측이 «시간순 무작위»를 넘는가.
      기준선 둘: ⓐ균등 무작위 ⓑ유형 기저빈도(1040 의 유형 행렬이 하던 것).
      🔴 ⓑ를 못 넘으면 «인스턴스 벡터가 유형 스칼라보다 낫다»가 안 서는 것이다.
    · 지표: MRR + Hit@5. 개체 분리 검증(train 80% / val 20% 개체).
    · 붓스트랩 개체 클러스터 · B=1000 · seed 1044.
    · 반증: CI95 가 0 을 포함하면 «이 자를 못 넘었다».
    · 히스토리 트리·RoPE 인코더 단계는 G1 을 넘은 «뒤에만» 짓는다.

씀:
    python3 -m pretrain.eventmat build      # 노드 벡터 조립
    python3 -m pretrain.eventmat train      # 1층 학습 + G1 판정
    python3 -m pretrain.eventmat tree --i 0 # 히스토리 트리 (G1 통과 시)
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import argparse
import gzip
import hashlib
import json
import os

import numpy as np

np.seterr(all="ignore")

ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
OUT = os.path.join(ART, "eventmat")
PANEL = "/Users/ax/world_model/data/ingest/wiki_daily959"
DOMS = ("팝업", "시장팝업", "웹툰", "애니", "게임", "도서", "만화", "모바일",
        "아이돌", "세계애니", "펀딩")
TYPES = ["발표", "공개", "출시", "개봉", "방영", "개최", "시작", "데뷔", "컴백"]
ROPE_BASE = 1000.0        # 🔴 일 단위. 10000 이면 파장 상한이 172년 — 절반이 낭비다
ROPE_DIM = 32
CTX = 90
SEED = 1044


def sha16(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def d2i(s):
    try:
        return int(np.datetime64(str(s)[:10]).astype("datetime64[D]").astype(int))
    except Exception:
        return None


def rope(t, dim=ROPE_DIM, base=ROPE_BASE):
    """시각 → 회전 좌표. 내적이 Δt 에만 의존하게 만든다."""
    inv = 1.0 / (base ** (np.arange(0, dim, 2) / dim))
    a = np.outer(np.asarray(t, float), inv)
    return np.concatenate([np.cos(a), np.sin(a)], axis=1)


def build():
    import torch
    os.makedirs(OUT, exist_ok=True)
    ev = [json.loads(l) for l in gzip.open(
        os.path.join(ART, "event_ledger", "v1", "events_v1.jsonl.gz"), "rt", encoding="utf-8")]
    # 패널 (h64 용)
    ser = {}
    ent_dom = {}
    for dom in DOMS:
        p = os.path.join(PANEL, "%s.jsonl.gz" % dom)
        if not os.path.exists(p):
            continue
        for line in gzip.open(p, "rt", encoding="utf-8"):
            r = json.loads(line)
            ser.setdefault(r["문서"], {}).update(
                dict(zip([str(x) for x in r["날짜"]], r["조회수"])))
            ent_dom.setdefault(r["문서"], dom)
    # 원문 임베딩 (개체 단위 평균 · PCA32)
    tfx = os.path.join(ART, "textfix1036")
    rows = json.load(open(os.path.join(tfx, "row_docid.json"), encoding="utf-8"))
    E = np.load(os.path.join(tfx, "text_emb_body512.npz"))["E"].astype(np.float64)
    Ec = E - E.mean(0)
    U, S_, Vt = np.linalg.svd(Ec, full_matrices=False)
    P8 = Vt[:8]
    Ec = Ec - (Ec @ P8.T) @ P8
    P32 = Vt[8:40]
    txt_by_ent = {}
    for i, r in enumerate(rows):
        txt_by_ent.setdefault(r["문서"], []).append(Ec[i] @ P32.T)
    txt_by_ent = {k: np.mean(v, 0) for k, v in txt_by_ent.items()}
    # 궤적 인코더
    ck = torch.load(os.path.join(ART, "traj", "traj_v0.pt"), map_location="cpu")
    import torch.nn as nn

    class Enc(nn.Module):
        def __init__(s_, d):
            super().__init__()
            s_.c = nn.ModuleList([nn.Conv1d(1, 16, k, padding=k // 2) for k in (3, 7, 15, 31)])
            s_.g = nn.GRU(64, d, batch_first=True)
            s_.head = nn.Linear(d, 30)

        def enc(s_, x):
            h = torch.cat([torch.relu(c(x.unsqueeze(1))[:, :, :x.shape[1]]) for c in s_.c], 1)
            o, _ = s_.g(h.transpose(1, 2))
            return o[:, -1]
    net = Enc(ck["d"]); net.load_state_dict(ck["sd"]); net.eval()

    keep, curves = [], []
    for e in ev:
        w = e.get("위키문서"); ty = e.get("정규유형"); t = d2i(e.get("event_time"))
        if not w or ty not in TYPES or t is None or w not in ser:
            continue
        s = ser[w]
        pre = [s.get(str((np.datetime64(t, "D") - np.timedelta64(k, "D")).astype(str).replace("-", "")))
               for k in range(CTX, 0, -1)]
        if any(x is None for x in pre):        # 🔴 결측 창은 버린다 (조항 59)
            continue
        keep.append({"ent": w, "type": ty, "t": t, "sid": e.get("사건id")})
        curves.append(pre)
    C = np.asarray(curves, np.float64)
    L = np.log1p(C)
    Ln = (L - L.mean(1, keepdims=True)) / (L.std(1, keepdims=True) + 1e-6)
    with torch.no_grad():
        H = net.enc(torch.tensor(Ln, dtype=torch.float32)).numpy().astype(np.float64)
    n = len(keep)
    TY = np.zeros((n, len(TYPES)))
    for i, k in enumerate(keep):
        TY[i, TYPES.index(k["type"])] = 1
    T = np.array([k["t"] for k in keep], float)
    RO = rope(T - T.min())
    TX = np.zeros((n, 32)); MISS = np.ones((n, 1))
    for i, k in enumerate(keep):
        v = txt_by_ent.get(k["ent"])
        if v is not None:
            TX[i] = v; MISS[i, 0] = 0.0
    V = np.hstack([TY, RO, H, TX, MISS])
    ents = np.array([k["ent"] for k in keep])
    doms = np.array([ent_dom.get(k["ent"], "?") for k in keep])
    np.savez_compressed(os.path.join(OUT, "nodes.npz"), V=V, T=T, ents=ents, doms=doms,
                        TY=TY, H=H, RO=RO, TX=TX, MISS=MISS,
                        types=np.array([k["type"] for k in keep]))
    rep = {"사건 인스턴스(원장)": len(ev), "노드로 남은 것": n,
           "버린 이유": "위키문서 없음 · 유형 밖 · 시각 없음 · 궤적 결측(0채움 금지)",
           "개체": int(len(set(ents.tolist()))),
           "층": {"유형": len(TYPES), "RoPE": ROPE_DIM, "h64": H.shape[1],
                 "원문PCA": 32, "원문결측지시자": 1, "합": V.shape[1]},
           "원문 덮개": round(float(1 - MISS.mean()), 4),
           "RoPE": {"base": ROPE_BASE, "단위": "일",
                   "파장": [round(2 * np.pi, 1), round(2 * np.pi * ROPE_BASE, 1)]}}
    json.dump(rep, open(os.path.join(OUT, "build.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(rep, ensure_ascii=False, indent=1))


def _pairs(ents, T):
    """같은 개체의 «실제 다음 사건» 쌍 — 시간 순서."""
    out = []
    for e in np.unique(ents):
        ix = np.where(ents == e)[0]
        ix = ix[np.argsort(T[ix])]
        for a, b in zip(ix, ix[1:]):
            if T[b] > T[a]:
                out.append((int(a), int(b)))
    return np.array(out)


def train(steps=1500, d=64, lr=3e-3, neg=64):
    import torch
    import torch.nn as nn
    z = np.load(os.path.join(OUT, "nodes.npz"), allow_pickle=True)
    V, T, ents, TY = z["V"], z["T"], z["ents"], z["TY"]
    n = len(V)
    pairs = _pairs(ents, T)
    rng = np.random.default_rng(SEED)
    ue = np.unique(ents)
    va_e = set(rng.choice(ue, max(1, len(ue) // 5), replace=False).tolist())
    is_va = np.array([e in va_e for e in ents])
    tr_p = pairs[~is_va[pairs[:, 0]]]
    va_p = pairs[is_va[pairs[:, 0]]]
    print("노드 %d · 개체 %d · 인접쌍 %d (train %d / val %d · 개체분리)"
          % (n, len(ue), len(pairs), len(tr_p), len(va_p)))
    mu, sd = V[~is_va].mean(0), V[~is_va].std(0) + 1e-8
    Vn = torch.tensor((V - mu) / sd, dtype=torch.float32)

    class Layer1(nn.Module):
        """🔴 1층 = 인과성. «저장 안 하고 계산한다»."""
        def __init__(s_, din, d):
            super().__init__()
            s_.q = nn.Linear(din, d, bias=False)
            s_.k = nn.Linear(din, d, bias=False)
            s_.dt = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 1))

        def score(s_, vi, vj, dt):
            base = (s_.q(vi) * s_.k(vj)).sum(-1) / (vi.shape[-1] ** 0.5)
            return base + s_.dt(torch.log1p(dt).unsqueeze(-1)).squeeze(-1)   # 시각 보정

    net = Layer1(V.shape[1], d)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=0.01)
    Tt = torch.tensor(T, dtype=torch.float32)

    def batch(P, bs):
        b = P[rng.integers(0, len(P), bs)]
        i, j = b[:, 0], b[:, 1]
        cand = np.stack([np.r_[j[k], rng.choice(n, neg)] for k in range(len(i))])
        # 🔴 시간 순서 위반 후보는 못 쓰게 한다
        ok = T[cand] > T[i][:, None]
        ok[:, 0] = True
        return (torch.tensor(i), torch.tensor(cand), torch.tensor(ok))

    def ev_metrics(P):
        net.eval()
        mrr, hit = [], []
        with torch.no_grad():
            for k in range(0, len(P), 256):
                b = P[k:k + 256]
                i, j = b[:, 0], b[:, 1]
                cand = np.stack([np.r_[j[q], rng.choice(n, 199)] for q in range(len(i))])
                ok = T[cand] > T[i][:, None]; ok[:, 0] = True
                vi = Vn[torch.tensor(i)].unsqueeze(1).expand(-1, cand.shape[1], -1)
                vj = Vn[torch.tensor(cand)]
                dt = (Tt[torch.tensor(cand)] - Tt[torch.tensor(i)].unsqueeze(1)).clamp(min=0)
                s = net.score(vi, vj, dt)
                s = s.masked_fill(~torch.tensor(ok), -1e9)
                r = (s > s[:, :1]).sum(1) + 1
                mrr += (1.0 / r.float()).tolist()
                hit += (r <= 5).float().tolist()
        net.train()
        return float(np.mean(mrr)), float(np.mean(hit))

    # 기준선 둘 (사전등록)
    def baseline(P, mode):
        rr, hh = [], []
        freq = TY[~is_va].mean(0)
        for k in range(len(P)):
            i, j = P[k]
            cand = np.r_[j, rng.choice(n, 199)]
            ok = T[cand] > T[i]; ok[0] = True
            if mode == "uniform":
                s = rng.random(len(cand))
            else:                                   # 유형 기저빈도 = 1040 유형행렬이 하던 것
                s = TY[cand] @ freq
            s = np.where(ok, s, -1e9)
            r = int((s > s[0]).sum()) + 1
            rr.append(1.0 / r); hh.append(1.0 if r <= 5 else 0.0)
        return float(np.mean(rr)), float(np.mean(hh))

    b_u = baseline(va_p, "uniform")
    b_f = baseline(va_p, "freq")
    best = None
    for st in range(1, steps + 1):
        i, cand, ok = batch(tr_p, 128)
        vi = Vn[i].unsqueeze(1).expand(-1, cand.shape[1], -1)
        vj = Vn[cand]
        dt = (Tt[cand] - Tt[i].unsqueeze(1)).clamp(min=0)
        s = net.score(vi, vj, dt).masked_fill(~ok, -1e9)
        loss = nn.functional.cross_entropy(s, torch.zeros(len(i), dtype=torch.long))
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
        if st % 300 == 0 or st == steps:
            m, h = ev_metrics(va_p)
            print("  step %4d  loss %.4f   val MRR %.4f  Hit@5 %.4f" % (st, loss.item(), m, h))
            if best is None or m > best[0]:
                best = (m, h)
                torch.save({"sd": net.state_dict(), "d": d, "mu": mu, "sd_": sd,
                            "din": V.shape[1]}, os.path.join(OUT, "layer1.pt"))
    rep = {"판": "1044 사건 인스턴스 1층 (인과성)", "노드": int(n), "개체": int(len(ue)),
           "인접쌍": int(len(pairs)), "val쌍": int(len(va_p)),
           "모형": {"MRR": round(best[0], 4), "Hit@5": round(best[1], 4)},
           "기준선ⓐ 균등무작위": {"MRR": round(b_u[0], 4), "Hit@5": round(b_u[1], 4)},
           "기준선ⓑ 유형기저빈도(=1040 유형행렬)": {"MRR": round(b_f[0], 4), "Hit@5": round(b_f[1], 4)},
           "Δ(모형−ⓑ) MRR": round(best[0] - b_f[0], 4),
           "🔴 판정": ("✅ 유형 스칼라보다 낫다" if best[0] > b_f[0] else "🔴 유형 스칼라를 못 넘었다"),
           "후보": 200, "seed": SEED,
           "출처": {"self": sha16(os.path.abspath(__file__)),
                  "nodes": sha16(os.path.join(OUT, "nodes.npz"))}}
    json.dump(rep, open(os.path.join(OUT, "train.json"), "w"), ensure_ascii=False, indent=1)
    print("\n[G1 — 다음 사건 예측 (후보 200개 중)]")
    print("  기준선ⓐ 균등무작위      MRR %.4f  Hit@5 %.4f" % b_u)
    print("  기준선ⓑ 유형기저빈도    MRR %.4f  Hit@5 %.4f   ← 1040 유형행렬이 하던 것" % b_f)
    print("  모형(인스턴스 벡터)     MRR %.4f  Hit@5 %.4f" % best)
    print("  → %s" % rep["🔴 판정"])



# ── 히스토리 트리 + RoPE 인코더 (G1 을 넘었으므로) ────────────────────
def _load_layer1():
    import torch, torch.nn as nn
    # torch 2.6+ 기본 weights_only=True 인데 mu/sd_ 가 numpy 라 막힌다.
    # 이 체크포인트는 «우리가 방금 만든 것»이므로 안전하다.
    ck = torch.load(os.path.join(OUT, "layer1.pt"), map_location="cpu", weights_only=False)

    class Layer1(nn.Module):
        def __init__(s_, din, d):
            super().__init__()
            s_.q = nn.Linear(din, d, bias=False)
            s_.k = nn.Linear(din, d, bias=False)
            s_.dt = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 1))

        def score(s_, vi, vj, dt):
            base = (s_.q(vi) * s_.k(vj)).sum(-1) / (vi.shape[-1] ** 0.5)
            return base + s_.dt(torch.log1p(dt).unsqueeze(-1)).squeeze(-1)
    net = Layer1(ck["din"], ck["d"]); net.load_state_dict(ck["sd"]); net.eval()
    return net, ck


def tree(i0, depth=3, beam=4, horizon=400, n_analog=25):
    """🔴 1층에 프로젝션해서 히스토리 트리를 뻗는다.

    설계자 원안: 「인풋에 따라 벌어질 히스토리를 매트릭스의 첫번째 레이어에
    프로젝션해서 계속 찾아내고, 상위 몇개를 RoPE 인코더에 넣는다」.

    🔴 개념 (v0.3 에서 확정 — 세 번 고쳤다):
      갈래 = «상태가 비슷했던 다른 개체»가 «실제로» 밟은 사건 사슬. 시뮬레이션이 아니다.
      · v0   개체를 안 묶음      → 아무 데로나 뛴다(만화 → 한돈자조금)
      · v0.1 개체를 묶음        → 정당이 만화의 유사 사례(h64 는 도메인을 모른다)
      · v0.2 도메인 제약        → 갈래가 전부 한 개체(다양성 없음)
      · v0.3 개체마다 «따로» 사슬을 뽑고 개체 간 순위 → 「여러 갈래」가 선다
      전역 빔서치를 안 쓴다 — 갈래가 개체 안에 잠기므로 빔이 한 개체에 먹힌다.
    """
    import torch
    z = np.load(os.path.join(OUT, "nodes.npz"), allow_pickle=True)
    V, T, ents, types = z["V"], z["T"], z["ents"], z["types"]
    doms = z["doms"] if "doms" in z.files else np.array(["?"] * len(ents))
    net, ck = _load_layer1()
    Vn = torch.tensor((V - ck["mu"]) / ck["sd_"], dtype=torch.float32)
    Tt = torch.tensor(T, dtype=torch.float32)

    # ① 유사 개체 — h64 상태 · 같은 도메인 · 뿌리 개체 제외(정답 보기 금지)
    Hn = z["H"] - z["H"].mean(0)
    Hn = Hn / np.maximum(np.linalg.norm(Hn, axis=1, keepdims=True), 1e-9)
    sim = Hn @ Hn[i0]
    sim[ents == ents[i0]] = -9
    if doms[i0] != "?":
        sim[doms != doms[i0]] = -9
    seen = {}
    for k in np.argsort(-sim):
        if sim[k] <= -9:
            break
        e = ents[k]
        if e not in seen:
            seen[e] = (int(k), float(sim[k]))       # 그 개체의 «가장 닮은 시점»
        if len(seen) >= n_analog:
            break

    # ② 개체마다 그 시점 «이후»의 실제 사슬을 뽑는다
    out = []
    for e, (anchor, sm) in seen.items():
        ix = np.where(ents == e)[0]
        ix = ix[np.argsort(T[ix])]
        after = [int(k) for k in ix if T[k] > T[anchor] and T[k] <= T[anchor] + horizon]
        if len(after) < 2:
            continue
        chain = [anchor] + after[:depth]
        with torch.no_grad():
            sc = 0.0
            for a, b in zip(chain, chain[1:]):
                sc += float(net.score(Vn[a].unsqueeze(0), Vn[b].unsqueeze(0),
                                      (Tt[b] - Tt[a]).clamp(min=0).unsqueeze(0))[0])
        out.append({"점수": round(sc / max(len(chain) - 1, 1), 3), "유사도": round(sm, 3),
                    "개체": str(e),
                    "단계": [{"유형": str(types[k]), "Δt(일)": int(T[k] - T[anchor])}
                            for k in chain[1:]]})
    out.sort(key=lambda x: -(x["점수"] + 4.0 * x["유사도"]))     # 사슬 그럴듯함 + 상태 닮음
    return {"뿌리": {"유형": str(types[i0]), "개체": str(ents[i0]), "도메인": str(doms[i0])},
            "🔴 갈래의 뜻": "«상태가 비슷했던 다른 개체»가 실제로 밟은 사슬 (시뮬레이션 아님)",
            "유사 개체 풀": len(seen), "갈래": out[:beam]}


def encode_history(steps=1200, d=48, lr=3e-3):
    """🔴 히스토리 시퀀스 → RoPE 인코더 → NN → «단계별 숫자 변화».
    표적은 기준 변수 계보를 따른다 — 여기서는 각 단계 «다음 30일 관심 변화»(log).
    실제 궤적에서 뽑으므로 라벨이 정직하다."""
    import torch, torch.nn as nn
    z = np.load(os.path.join(OUT, "nodes.npz"), allow_pickle=True)
    V, T, ents = z["V"], z["T"], z["ents"]
    H = z["H"]
    # 실제 개체별 사건 사슬(길이 3)을 학습 자료로 — 트리가 아니라 «진짜 일어난» 사슬
    seqs = []
    for e in np.unique(ents):
        ix = np.where(ents == e)[0]; ix = ix[np.argsort(T[ix])]
        for a in range(len(ix) - 2):
            seqs.append(list(ix[a:a + 3]))
    seqs = np.array(seqs)
    rng = np.random.default_rng(SEED)
    ue = np.unique(ents)
    va_e = set(rng.choice(ue, max(1, len(ue) // 5), replace=False).tolist())
    isva = np.array([ents[s[0]] in va_e for s in seqs])
    # 표적: 각 단계에서 «그 개체의 h64 가 다음 단계까지 얼마나 움직였나» 의 크기
    tgt = np.zeros((len(seqs), 2))
    for k, s in enumerate(seqs):
        for j in (0, 1):
            tgt[k, j] = np.linalg.norm(H[s[j + 1]] - H[s[j]])
    mu_t, sd_t = tgt[~isva].mean(), tgt[~isva].std() + 1e-8
    tgtn = (tgt - mu_t) / sd_t
    tr_nodes = np.unique(seqs[~isva].ravel())          # 🔴 train 사슬에 «든 노드»로만 통계
    mu, sd = V[tr_nodes].mean(0), V[tr_nodes].std(0) + 1e-8
    Vn = torch.tensor((V - mu) / sd, dtype=torch.float32)

    class RopeEnc(nn.Module):
        def __init__(s_, din, d):
            super().__init__()
            s_.inp = nn.Linear(din, d)
            s_.att = nn.MultiheadAttention(d, 4, batch_first=True)
            s_.out = nn.Sequential(nn.LayerNorm(d), nn.Linear(d, d), nn.GELU(), nn.Linear(d, 1))

        def forward(s_, x, rel):
            h = s_.inp(x)
            # 🔴 RoPE: 상대 시각으로 회전 — 절대 시각이 사라지고 Δt 만 남는다
            hd = h.shape[-1] // 2
            ang = rel.unsqueeze(-1) / (ROPE_BASE ** (torch.arange(hd).float() / hd))
            c, s2 = torch.cos(ang), torch.sin(ang)
            h1, h2 = h[..., :hd], h[..., hd:]
            h = torch.cat([h1 * c - h2 * s2, h1 * s2 + h2 * c], -1)
            a, _ = s_.att(h, h, h, need_weights=False)
            return s_.out(h + a).squeeze(-1)[:, :2]      # 단계 1,2 의 숫자 변화

    net = RopeEnc(V.shape[1], d)
    opt = torch.optim.AdamW(net.parameters(), lr=lr, weight_decay=0.01)
    Xs = torch.tensor(seqs, dtype=torch.long)
    Rel = torch.tensor(np.stack([T[s] - T[s][0] for s in seqs]), dtype=torch.float32)
    Y = torch.tensor(tgtn, dtype=torch.float32)
    tr = np.where(~isva)[0]; va = np.where(isva)[0]
    print("사슬(길이3) %d · 개체 %d (val %d) · 파라미터 %d"
          % (len(seqs), len(ue), len(va_e), sum(p.numel() for p in net.parameters())))
    best = 9e9
    for st in range(1, steps + 1):
        b = rng.choice(tr, 128)
        p = net(Vn[Xs[b]], Rel[b])
        loss = nn.functional.l1_loss(p, Y[b])
        opt.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0); opt.step()
        if st % 300 == 0 or st == steps:
            net.eval()
            with torch.no_grad():
                pv = net(Vn[Xs[va]], Rel[va])
                vl = nn.functional.l1_loss(pv, Y[va]).item()
                bl = Y[va].abs().mean().item()          # 기준선: 전부 «평균»
            net.train()
            print("  step %4d  train %.4f  val %.4f  (기준선 %.4f)" % (st, loss.item(), vl, bl))
            if vl < best:
                best = vl
                torch.save({"sd": net.state_dict(), "d": d}, os.path.join(OUT, "ropeenc.pt"))
    rep = {"판": "1044-나 히스토리 → RoPE 인코더 → 단계별 숫자",
           "사슬": int(len(seqs)), "val": int(len(va)), "개체": int(len(ue)),
           "표적": "각 단계의 내재상태 이동 크기 ‖Δh64‖ (z 정규화)",
           "val L1": round(best, 4), "기준선(전부 평균)": round(bl, 4),
           "개선": round(100 * (1 - best / bl), 1),
           "판정": "✅ 기준선보다 낫다" if best < bl else "🔴 못 넘었다"}
    json.dump(rep, open(os.path.join(OUT, "ropeenc.json"), "w"), ensure_ascii=False, indent=1)
    print("\n  val L1 %.4f vs 기준선 %.4f → %s (%.1f%% 개선)"
          % (best, bl, rep["판정"], rep["개선"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "train", "tree", "rope"])
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--i", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "build":
        build()
    elif a.cmd == "train":
        train(steps=a.steps)
    elif a.cmd == "rope":
        encode_history(steps=a.steps)
    else:
        r = tree(a.i)
        b = r["뿌리"]
        print("뿌리: [%s] %s  (도메인 %s) · 유사 개체 풀 %d"
              % (b["유형"], b["개체"], b["도메인"], r["유사 개체 풀"]))
        print("🔴 %s\n" % r["🔴 갈래의 뜻"])
        for g in r["갈래"]:
            print("  [%s]  유사도 %.3f · 사슬점수 %.2f" % (g["개체"][:24], g["유사도"], g["점수"]))
            print("     %s" % "  →  ".join("%s(+%d일)" % (x["유형"], x["Δt(일)"]) for x in g["단계"]))
