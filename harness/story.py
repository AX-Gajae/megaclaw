# -*- coding: utf-8 -*-
"""스토리 파이프라인 v0 — 「이 상황이면 무슨 일이 일어나나」 (사이클 1043).

🔴 **설계 전환**: 유사 사례를 «문서 임베딩»이 아니라 «궤적 상태 h64»로 찾는다.

  문서 임베딩 검색은 이미 실패했다 — 상위20 유사사례의 급등률 10% vs 기저 26%
  (동음이의어 오염: 웹툰 「인피니티」 질의에 자동차 인피니티 문서가 올라왔다).
  원인은 문서↔개체 링크 오염(개체명이 본문에 0회 20.2% · 1회 46.9%)이고
  1041 P2 가 그 오염을 걷어도 텍스트는 안 산다고 판정했다.

  그러므로 «예측 경로»에서 텍스트를 뺀다:
      검색 열쇠 = h64 궤적 상태   (오염 없음 · 1042 에서 결정층 증분 검증됨)
      후속 사실 = 실제 91일 곡선   (오염 없음 · 진짜 일어난 일 — 시뮬레이션 아님)
      서사     = 문서 + LLM       (오염 있음 · 그러나 «설명»이지 «예측»이 아니다)

  이것이 이 대화에서 합의한 형태다 — **시뮬레이션이 아니라 인용**. 실제 궤적을 읽으므로
  단계마다 오차가 곱해지지 않는다. 불확실성은 「이 사례가 내 상황과 비슷한가」 한 번뿐이다.

## 사전등록 (측정 전 고정)
  · 게이트 G1 — 검색이 기저를 넘는가:
      상위 K 유사사례의 «실제 급등률»이 전체 기저율보다 높은가.
      붓스트랩 개체 클러스터 · CI95 가 0 을 포함하면 **파이프라인을 안 판다**.
  · 표적 라벨: 1039~1042 정본 (뒤 91일에 앞 90일 중앙값의 3배 이상)
  · K = 20 을 정본으로 «미리» 고정. K∈{10,50} 은 [관찰].
  · 검증: 인코더 val 개체(seed 1041)로만 — 궤적 누수 차단(1042 자구 승계)
  · 🔴 서사(LLM)는 게이트를 넘은 «뒤에만» 만든다. 못 넘으면 만들지 않고 그렇게 적는다.

## 안 주장하는 것
  · 인과 아님. 유사 사례는 무작위 배정이 아니다.
  · 「이 IP 도 그렇게 된다」가 아니라 「비슷했던 N건 중 M건이 그랬다」이다.
  · 서사의 문서 링크는 오염돼 있을 수 있다 — LLM 출력에 그 경고를 함께 낸다.

씀:
    python3 -m harness.story gate            # G1 판정만
    python3 -m harness.story ask --i 42      # 한 질의의 스토리 (게이트 통과 시)
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
TRAJ = os.path.join(ART, "traj")
PANEL = "/Users/ax/world_model/data/ingest/wiki_daily959"
DOMS = ("팝업", "시장팝업", "웹툰", "애니", "게임", "도서", "만화", "모바일",
        "아이돌", "세계애니", "펀딩")
CTX, LAB_H, STRIDE = 90, 91, 91
K_CANON, BOOT, SEED, ENC_SEED = 20, 1000, 1039, 1041


def sha16(p):
    if not os.path.exists(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]


def _enc_class(d):
    import torch.nn as nn
    import torch

    class Enc(nn.Module):
        def __init__(s_):
            super().__init__()
            s_.c = nn.ModuleList([nn.Conv1d(1, 16, k, padding=k // 2) for k in (3, 7, 15, 31)])
            s_.g = nn.GRU(64, d, batch_first=True)
            s_.head = nn.Linear(d, 30)

        def enc(s_, x):
            h = torch.cat([torch.relu(c(x.unsqueeze(1))[:, :, :x.shape[1]]) for c in s_.c], 1)
            o, _ = s_.g(h.transpose(1, 2))
            return o[:, -1]
    return Enc


def build_pool():
    """인코더 val 개체의 «겹치지 않는» 창 + h64 + 실제 후속 곡선."""
    import torch
    z = np.load(os.path.join(TRAJ, "windows.npz"), allow_pickle=True)
    ents_all = np.unique(z["ENT"])
    rng = np.random.default_rng(ENC_SEED)
    va_e = set(rng.choice(ents_all, max(1, len(ents_all) // 5), replace=False).tolist())
    ser = {}
    for dom in DOMS:
        p = os.path.join(PANEL, "%s.jsonl.gz" % dom)
        if not os.path.exists(p):
            continue
        for line in gzip.open(p, "rt", encoding="utf-8"):
            r = json.loads(line)
            ser.setdefault((dom, r["문서"]), {}).update(
                dict(zip([str(x) for x in r["날짜"]], r["조회수"])))
    days = sorted({d for s in ser.values() for d in s})
    dix = {d: i for i, d in enumerate(days)}
    keys = sorted(ser)
    W, ENT, T0 = [], [], []
    for i, k in enumerate(keys):
        if i not in va_e:
            continue
        row = np.full(len(days), np.nan, np.float32)
        for d, v in ser[k].items():
            row[dix[d]] = v
        for t0 in range(0, len(days) - CTX - LAB_H, STRIDE):
            w = row[t0:t0 + CTX + LAB_H]
            if np.isnan(w).any():
                continue
            W.append(w); ENT.append(i); T0.append(t0)
    W = np.asarray(W, np.float32); ENT = np.asarray(ENT); T0 = np.asarray(T0)
    S = W[:, :CTX].astype(np.float64)
    F = W[:, CTX:].astype(np.float64)
    L = np.log1p(S)
    base = np.median(L, axis=1, keepdims=True)
    y = ((np.log1p(F) - base).max(axis=1) >= np.log(3)).astype(int)
    peak = np.exp((np.log1p(F) - base).max(axis=1))
    ck = __import__("torch").load(os.path.join(TRAJ, "traj_v0.pt"), map_location="cpu")
    net = _enc_class(ck["d"])(); net.load_state_dict(ck["sd"]); net.eval()
    Ln = (L - L.mean(1, keepdims=True)) / (L.std(1, keepdims=True) + 1e-6)
    with torch.no_grad():
        H = net.enc(torch.tensor(Ln, dtype=torch.float32)).numpy().astype(np.float64)
    H = H - H.mean(0)
    H = H / np.maximum(np.linalg.norm(H, axis=1, keepdims=True), 1e-9)
    names = np.array(["%s|%s" % keys[i] for i in ENT])
    return {"S": S, "F": F, "y": y, "peak": peak, "H": H, "ENT": ENT,
            "T0": T0, "days": np.array(days), "names": names}


def neighbors(P, i, K):
    """🔴 같은 개체는 뺀다 — 자기 궤적을 이웃으로 세면 누수다."""
    sim = P["H"] @ P["H"][i]
    sim[P["ENT"] == P["ENT"][i]] = -9
    return np.argsort(-sim)[:K], sim


def gate(P, Ks=(10, 20, 50)):
    y = P["y"]
    n = len(y)
    rng = np.random.default_rng(SEED)
    out = {}
    for K in Ks:
        rate = np.zeros(n)
        for i in range(n):
            nb, _ = neighbors(P, i, K)
            rate[i] = y[nb].mean()
        # 이웃 급등률이 «내» 결과를 맞히는가 — 상위 10% 로 찍었을 때
        o = np.argsort(-rate)
        top = o[:max(1, n // 10)]
        prec = y[top].mean()
        u = np.unique(P["ENT"])
        idx = {c: np.where(P["ENT"] == c)[0] for c in u}
        d = []
        for _ in range(BOOT):
            sel = np.concatenate([idx[c] for c in rng.choice(u, len(u))])
            yy = y[sel]; rr = rate[sel]
            if yy.sum() == 0:
                continue
            oo = np.argsort(-rr)[:max(1, len(sel) // 10)]
            d.append(yy[oo].mean() - yy.mean())
        d = np.array(d)
        lo, hi = np.percentile(d, [2.5, 97.5])
        out[K] = {"P@10%": round(float(prec), 4), "기저율": round(float(y.mean()), 4),
                  "배수": round(float(prec / max(y.mean(), 1e-9)), 3),
                  "Δ": round(float(d.mean()), 4), "SE": round(float(d.std()), 4),
                  "CI95": [round(float(lo), 4), round(float(hi), 4)],
                  "판정": "✅ 0 배제" if not (lo <= 0 <= hi) else "🔴 이 자를 못 넘었다"}
    return out


def ask(P, i, K=K_CANON):
    """한 질의 → 유사 사례 + «실제로 무슨 일이 있었나»."""
    nb, sim = neighbors(P, i, K)
    days = P["days"]
    rows = []
    for j in nb:
        t0 = int(P["T0"][j])
        rows.append({"사례": str(P["names"][j]), "시점": str(days[t0 + CTX]),
                     "유사도": round(float(sim[j]), 3),
                     "실제 최대배수": round(float(P["peak"][j]), 2),
                     "3배 급등": bool(P["y"][j])})
    hit = sum(r["3배 급등"] for r in rows)
    return {"질의": {"개체": str(P["names"][i]), "시점": str(days[int(P["T0"][i]) + CTX]),
                   "실제 결과(참고 — 예측에 안 씀)": round(float(P["peak"][i]), 2)},
            "유사 사례": rows,
            "요약": {"K": K, "급등한 사례": hit,
                   "비율": round(hit / K, 3), "전체 기저율": round(float(P["y"].mean()), 3),
                   "배수": round((hit / K) / max(float(P["y"].mean()), 1e-9), 2)}}



# ── 서사 층 (게이트를 넘은 «뒤에만») ───────────────────────────────────
DOC_SRC = "/Users/ax/world_model/data/ingest/sao973_hplt/pairs.jsonl.gz"
TFX = os.path.join(ART, "textfix1036")


def _doc_index():
    """개체(위키문서) → [(문서id, 언제)]. 🔴 덮개가 낮다 — val 개체의 18.6% 뿐."""
    from collections import defaultdict
    idx = defaultdict(list)
    for line in gzip.open(DOC_SRC, "rt", encoding="utf-8"):
        a = json.loads(line)["a_액션"]
        idx[a.get("문서", "")].append((a["문서id"], a["언제"]))
    return idx


def _texts():
    t = {}
    for line in gzip.open(os.path.join(TFX, "doc_text.jsonl.gz"), "rt", encoding="utf-8"):
        d = json.loads(line)
        t[d["문서id"]] = d["text"]
    return t


def _llm(prompt, system, model="qwen3.6:35b-a3b", npred=380):
    import urllib.request
    body = {"model": model, "prompt": prompt, "system": system, "stream": False,
            "think": False, "options": {"temperature": 0.2, "num_predict": npred}}
    req = urllib.request.Request("http://localhost:11434/api/generate",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read()).get("response", "").strip()



REL_SYS = ("문서가 지정된 대상을 «실제로» 다루는지 판단한다. JSON 한 줄만. 설명 금지.\n"
           '{"관련":true/false,"이유":"10자 이내"}\n'
           "· 동음이의어를 조심하라 — 같은 이름의 «다른» 것이면 false.\n"
           "  (예: 웹툰 「인피니티」 ↔ 자동차 인피니티 · 게임 「Stellaris」 ↔ 의료기기 Stellaris)\n"
           "· 이름이 스쳐 지나가기만 하고 그 대상이 주제가 아니면 false.\n"
           "· 확신 없으면 false. 🔴 틀린 문서를 넣는 것이 빠뜨리는 것보다 나쁘다.")


def _relevant(name, dom, text):
    """🔴 질의 시점 오염 필터. 전량 배치(30,428쌍=14시간) 대신 «보여줄 것만» 판별한다."""
    try:
        r = _llm("대상: %s (분야: %s)\n---\n%s" % (name, dom, (text or "")[:1200]),
                 REL_SYS, npred=60)
        j = json.loads(r[r.find("{"):r.rfind("}") + 1])
        return bool(j.get("관련")), str(j.get("이유", ""))[:14]
    except Exception as e:
        return False, "판별실패"          # 🔴 실패는 «뺀다» (조항 59 — 모르면 안 쓴다)


NAR_SYS = ("팝업·IP 분석가다. 아래는 «과거에 실제로 일어난» 사례들이다. 지어내지 마라.\n"
           "주어진 문서에 «있는 내용만» 쓴다. 없으면 「문서에 단서 없음」이라 적는다.\n"
           "출력 형식(마크다운, 300자 이내):\n"
           "**공통점** — 급등한 사례들이 공유한 것\n"
           "**갈린 지점** — 급등한 쪽과 안 한 쪽이 달랐던 것\n"
           "**조심할 것** — 위 둘에서 나오는 경고 한 줄\n"
           "🔴 문서가 그 개체를 실제로 다루지 않을 수 있다. 의심되면 그렇게 적어라.")


def narrate(P, i, K=K_CANON, maxdoc=3, chars=700):
    nb, sim = neighbors(P, i, K)
    idx = _doc_index()
    txt = _texts()
    days = P["days"]
    have, blocks, seen, kept, dropped = 0, [], 0, 0, []
    for j in nb:
        full = str(P["names"][j]); dom, name = full.split("|", 1)
        pool = idx.get(name, [])
        if not pool:
            continue
        have += 1
        keep = []
        for d, _w in pool[:maxdoc]:
            seen += 1
            ok, why = _relevant(name, dom, txt.get(d, ""))
            if ok:
                keep.append(d); kept += 1
            else:
                dropped.append("%s:%s" % (name[:14], why))
        if not keep:
            continue
        body = "\n".join((txt.get(d, "") or "")[:chars] for d in keep)
        blocks.append("### %s (%s) — 실제 최대배수 ×%.2f %s\n%s"
                      % (name, str(days[int(P["T0"][j]) + CTX]), float(P["peak"][j]),
                         "[3배 급등]" if P["y"][j] else "[급등 없음]", body))
    q = ask(P, i, K)
    out = {"질의": q["질의"], "요약": q["요약"],
           "🔴 서사 덮개": {"유사사례": K, "문서 있는 사례": have,
                        "비율": round(have / K, 3),
                        "오염필터": {"검사한 문서": seen, "통과": kept,
                                 "버림": seen - kept,
                                 "통과율": round(kept / max(seen, 1), 3),
                                 "버린 예": dropped[:6]},
                        "서사 낸 사례": len(blocks),
                        "경고": "덮개가 낮다. 서사는 이 %d건에서만 나온 것이다" % len(blocks)}}
    if not blocks:
        out["서사"] = "🔴 문서가 있는 유사 사례가 0건 — 서사를 «만들지 않는다»(조항 59)"
        return out
    prompt = ("질의: %s (%s)\n유사 사례 %d건 중 문서가 있는 %d건:\n\n%s"
              % (q["질의"]["개체"], q["질의"]["시점"], K, have, "\n\n".join(blocks[:6])))
    out["서사"] = _llm(prompt, NAR_SYS)
    return out


def risk(P, i, K=K_CANON):
    """🔴 위험 요소 — 급등한 이웃과 «안» 한 이웃이 무엇이 달랐나.
    LLM 없이 궤적 통계만으로 낸다(오염 무관). 급등/비급등 두 무리의 사전 90일을 대조한다."""
    nb, sim = neighbors(P, i, K)
    up = nb[P["y"][nb] == 1]
    dn = nb[P["y"][nb] == 0]
    if len(up) < 3 or len(dn) < 3:
        return {"🔴 못 낸다": "급등/비급등 어느 쪽이 3건 미만 (up=%d dn=%d)" % (len(up), len(dn))}
    L = np.log1p(P["S"])
    def feats(ix):
        Z = (L[ix] - L[ix].mean(1, keepdims=True)) / (L[ix].std(1, keepdims=True) + 1e-9)
        return {"수준(log 평균)": L[ix].mean(1), "변동성(log SD)": L[ix].std(1),
                "최근7일 기울기": L[ix][:, -7:].mean(1) - L[ix][:, -30:].mean(1),
                "직전30일 대 첫30일": L[ix][:, -30:].mean(1) - L[ix][:, :30].mean(1),
                "고저 폭": L[ix].max(1) - L[ix].min(1),
                "막바지 튐(Z 최대)": Z[:, -14:].max(1)}
    fu, fd = feats(up), feats(dn)
    me = L[[i]]
    Zme = (me - me.mean()) / (me.std() + 1e-9)
    mine = {"수준(log 평균)": float(me.mean()), "변동성(log SD)": float(me.std()),
            "최근7일 기울기": float(me[:, -7:].mean() - me[:, -30:].mean()),
            "직전30일 대 첫30일": float(me[:, -30:].mean() - me[:, :30].mean()),
            "고저 폭": float(me.max() - me.min()),
            "막바지 튐(Z 최대)": float(Zme[:, -14:].max())}
    rows = []
    for k in fu:
        mu, md = float(np.median(fu[k])), float(np.median(fd[k]))
        sd = float(np.std(np.r_[fu[k], fd[k]])) + 1e-9
        d = (mu - md) / sd                      # 표준화 격차
        pos = (mine[k] - md) / sd               # 내가 어느 쪽에 가까운가
        rows.append({"축": k, "급등 무리": round(mu, 3), "비급등 무리": round(md, 3),
                     "격차(SD)": round(d, 2), "질의 위치(SD)": round(pos, 2),
                     "질의가 기운 쪽": "급등" if abs(mine[k] - mu) < abs(mine[k] - md) else "비급등"})
    rows.sort(key=lambda r: -abs(r["격차(SD)"]))
    return {"급등 이웃": int(len(up)), "비급등 이웃": int(len(dn)), "축": rows,
            "🔴 안 주장": "인과 아님 · 무작위 배정 아님 · K=%d 의 이웃 안에서만" % K}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gate", "ask", "narrate", "risk"])
    ap.add_argument("--i", type=int, default=0)
    ap.add_argument("--k", type=int, default=K_CANON)
    a = ap.parse_args()
    P = build_pool()
    print("풀: 창 %d · 개체 %d · 기저율 %.3f  (인코더 val 개체만 · 겹침 없음)"
          % (len(P["y"]), len(np.unique(P["ENT"])), P["y"].mean()))
    if a.cmd == "gate":
        g = gate(P)
        print("\n[게이트 G1 — 이웃 급등률로 상위10%% 를 찍었을 때]")
        for K, v in g.items():
            mark = "🔴 정본" if K == K_CANON else "  [관찰]"
            print("  %s K=%-3d P@10%% %.4f (기저 %.4f · %.2f배)  Δ %+.4f SE %.4f CI95 [%+.4f,%+.4f]  %s"
                  % (mark, K, v["P@10%"], v["기저율"], v["배수"], v["Δ"], v["SE"],
                     v["CI95"][0], v["CI95"][1], v["판정"]))
        rep = {"판": "1043 스토리 파이프라인 게이트", "창": int(len(P["y"])),
               "개체": int(len(np.unique(P["ENT"]))), "K정본": K_CANON, "게이트": g,
               "🔴 설계": "검색 열쇠 = h64 궤적(오염 없음) · 후속 = 실제 곡선 · 서사만 문서",
               "출처": {"self": sha16(os.path.abspath(__file__)),
                      "ckpt": sha16(os.path.join(TRAJ, "traj_v0.pt"))}}
        json.dump(rep, open(os.path.join(ART, "story1043_gate.json"), "w"),
                  ensure_ascii=False, indent=1)
        print("\n→ %s/story1043_gate.json" % ART)
    elif a.cmd == "risk":
        q = ask(P, a.i, a.k)
        r = risk(P, a.i, a.k)
        print("\n질의: %s (%s)" % (q["질의"]["개체"], q["질의"]["시점"]))
        s_ = q["요약"]
        print("   %d건 중 %d건(%.0f%%) 급등 — 기저 %.0f%% 의 %.2f배"
              % (s_["K"], s_["급등한 사례"], 100 * s_["비율"], 100 * s_["전체 기저율"], s_["배수"]))
        if "🔴 못 낸다" in r:
            print("\n[위험 요소] %s" % r["🔴 못 낸다"]); return
        print("\n[위험 요소 — 급등 %d건 대 비급등 %d건이 «사전 90일»에서 뭐가 달랐나]"
              % (r["급등 이웃"], r["비급등 이웃"]))
        print("   %-20s %9s %9s %9s   %s" % ("축", "급등", "비급등", "격차SD", "질의가 기운 쪽"))
        for x in r["축"]:
            print("   %-20s %9.3f %9.3f %+9.2f   %s"
                  % (x["축"], x["급등 무리"], x["비급등 무리"], x["격차(SD)"], x["질의가 기운 쪽"]))
        print("\n   🔴 %s" % r["🔴 안 주장"])
    elif a.cmd == "narrate":
        r = narrate(P, a.i, a.k)
        print("\n질의: %s (%s)" % (r["질의"]["개체"], r["질의"]["시점"]))
        s_ = r["요약"]
        print("\n[수치 — 유사사례 «전부» 덮는다]")
        print("   %d건 중 %d건(%.0f%%)이 3배 급등 — 기저 %.0f%% 의 %.2f배"
              % (s_["K"], s_["급등한 사례"], 100 * s_["비율"], 100 * s_["전체 기저율"], s_["배수"]))
        c = r["🔴 서사 덮개"]
        f = c["오염필터"]
        print("\n[오염 필터 — 질의 시점]")
        print("   문서 %d편 검사 → 통과 %d (%.0f%%) · 버림 %d"
              % (f["검사한 문서"], f["통과"], 100 * f["통과율"], f["버림"]))
        if f["버린 예"]:
            print("   버린 예: %s" % " · ".join(f["버린 예"]))
        print("\n[서사 — 🔴 사례 %d/%d · 문서 있는 사례 %d]"
              % (c["서사 낸 사례"], c["유사사례"], c["문서 있는 사례"]))
        print(r["서사"])
        json.dump(r, open(os.path.join(ART, "story1043_ask.json"), "w"),
                  ensure_ascii=False, indent=1)
    else:
        r = ask(P, a.i, a.k)
        print("\n질의: %s  (%s)" % (r["질의"]["개체"], r["질의"]["시점"]))
        print("\n유사 사례 %d건 — «실제로» 그 뒤 91일에 무슨 일이 있었나:" % a.k)
        for x in r["유사 사례"][:12]:
            print("   %.3f  %-28s %s  ×%-6.2f %s"
                  % (x["유사도"], x["사례"][:28], x["시점"], x["실제 최대배수"],
                     "🔴 3배 급등" if x["3배 급등"] else ""))
        s = r["요약"]
        print("\n▶ %d건 중 %d건(%.0f%%)이 3배 급등 — 전체 기저 %.0f%% 의 %.2f배"
              % (s["K"], s["급등한 사례"], 100 * s["비율"], 100 * s["전체 기저율"], s["배수"]))
        print("   (질의의 실제 결과 ×%.2f — 참고용이며 예측에 안 썼다)"
              % r["질의"]["실제 결과(참고 — 예측에 안 씀)"])


if __name__ == "__main__":
    main()
