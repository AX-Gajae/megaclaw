# -*- coding: utf-8 -*-
"""로컬 질의 창구 — http://localhost:8899  (표준 라이브러리만 · 로컬 전용 바인딩)

판 셋:
  ① 이어쓰기   — LM 샘플링 (지금은 스모크 체크포인트 = 옹알이 단계임을 화면에 명시)
  ② 놀람도     — 문장 nll. 두 문장 비교
  ③ 90일 예측  — 전이 모형: 검증 개체 조회 + «직접 입력»(곡선·도메인·기준일)

체크포인트는 «가장 많이 학습된 것»을 자동 선택(tiny-v1 > smoke-tiny).
⚠ 8791·8792·3001 은 사용자 서버 — 이 창구는 8899 · 127.0.0.1 전용.

씀:  nohup python3 pretrain/serve.py > /Users/ax/wm_harvest/foundation/serve.log 2>&1 & disown
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
import json
import math
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np
import torch
import torch.nn.functional as F

from pretrain.config import ART_DIR, CKPT_DIR, TOKENIZER_DIR, ModelConfig
from pretrain.model import GPT
from pretrain.transition import Transition, SAO, TRI, OUT as TROUT, MANIFEST, load_ensemble, load_conformal, ConformalWrap

PORT = 8899
LOCK = threading.Lock()
torch.set_num_threads(2)                      # 옆에서 도는 학습과 안 싸운다


# ── 적재 ──────────────────────────────────────────────────────────────
def newest_lm():
    best, best_step = None, -1
    if os.path.isdir(CKPT_DIR):
        for name in os.listdir(CKPT_DIR):
            p = os.path.join(CKPT_DIR, name, "latest.pt")
            if os.path.exists(p):
                try:
                    st = torch.load(p, map_location="cpu", weights_only=False).get("step", 0)
                except Exception:
                    continue
                if st > best_step:
                    best, best_step = p, st
    return best


LM_PATH = newest_lm()
LM = TOKC = LMCFG = None
if LM_PATH:
    ck = torch.load(LM_PATH, map_location="cpu", weights_only=False)
    LMCFG = ModelConfig.from_dict(ck["cfg"])
    LM = GPT(LMCFG)
    LM.load_state_dict(ck["model"])
    LM.eval()
    from tokenizers import Tokenizer
    TOKC = Tokenizer.from_file(os.path.join(TOKENIZER_DIR, "tokenizer.json"))
    LM_STEP = ck.get("step", 0)

TR = DATA = DOMS = META = None
TEXT_DIM, DOM_EMB, GLOB_EMB = 0, {}, None
QWEN_SNAP = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
             "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
# 배포 정본 적재 — manifest 있으면 앙상블(사이클 1002 배포), 없으면 단일 model.pt (하위호환)
tr_path = os.path.join(TROUT, "model.pt")
TR_SRC = None
if os.path.exists(MANIFEST):
    TR, _man, _shas = load_ensemble(MANIFEST)        # 구성원 sha 실측 대조(조항 66)
    DATA = SAO(text_emb=_man.get("text_emb"))
    TR_SRC = "앙상블 manifest(구성원 %d · 분위수 텐서 산술 평균)" % len(_shas)
    _cf = load_conformal(MANIFEST)                   # 사이클 1004 — 유효 조건 sha 대조 포함
    if _cf is not None:
        TR = ConformalWrap(TR, _cf[0])
        TR_SRC += " + 등각 보정(1004 · δ=%.4f · 무누수 홀드아웃 98 개체)" % _cf[0]
elif os.path.exists(tr_path):
    tck = torch.load(tr_path, map_location="cpu", weights_only=False)
    TR = Transition(tck["d_in"], hidden=tck["hidden"])
    TR.load_state_dict(tck["model"])
    TR.eval()
    DATA = SAO(text_emb=tck.get("text_emb"))
    TR_SRC = "단일 model.pt"
if DATA is not None:
    DOMS = json.load(open(os.path.join(TRI, "domains.json"), encoding="utf-8"))
    META = [json.loads(l) for l in open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")]
    if DATA.E is not None:
        # 텍스트 조건 모형 — 직접 입력엔 ⑴ 라이브 임베딩 ⑵ 없으면 도메인 평균으로 채운다
        TEXT_DIM = DATA.E.shape[1]
        for d_i, d_name in enumerate(DOMS):
            ii = [i for i in DATA.tr if DATA.C[i][d_i] == 1.0]
            if ii:
                DOM_EMB[d_name] = DATA.E[ii].mean(axis=0)
        GLOB_EMB = DATA.E[DATA.tr].mean(axis=0)
        # OOD 자: 학습 임베딩끼리의 최근접 거리 분포(표본 512)를 기준으로 삼는다
        _E_TR = DATA.E[DATA.tr]
        _samp = _E_TR[np.random.default_rng(0).choice(len(_E_TR), size=min(512, len(_E_TR)), replace=False)]
        _d = np.sqrt(((_samp[:, None, :] - _samp[None, :, :]) ** 2).sum(-1))
        np.fill_diagonal(_d, np.inf)
        REF_NN = float(np.median(_d.min(axis=1)))
        E_TRAIN = _E_TR

_QW = {}


def _perf_note():
    """성적을 «지금 배포된» report.json 에서 읽는다 — 숫자 하드코딩이 낡는 병 방지
    (wm_tools._caveat 과 같은 원리 · 사이클 1002 수리: 리터럴 59.6%/8.5% 는 옛 시대 값이었다)."""
    try:
        e = json.load(open(os.path.join(TROUT, "report.json"), encoding="utf-8"))["평가"]
        return ("개체 분리 검증 MdAPE %.1f%% · 90%% 구간 실측 덮개율 %.1f%%(목표 90 — 미달분은 보수적으로)"
                % (e["누적90일 MdAPE"] * 100, e["90% 구간 덮개율(목표 0.90)"] * 100))
    except Exception:
        return "성적표(report.json) read 실패 — wm_model_card 로 확인하라"


PERF_NOTE = _perf_note()


def _embed_text_live(text):
    """기획서·소개문 «텍스트»를 임베딩 — 학습 때와 «같은» 설정을 미러링한다:
    Qwen2.5-0.5B base · AutoModel 마지막 은닉층 · attention-mask 평균 · 96 토큰 · fp32."""
    if "m" not in _QW:
        from transformers import AutoModel, AutoTokenizer
        _QW["t"] = AutoTokenizer.from_pretrained(QWEN_SNAP)
        _QW["m"] = AutoModel.from_pretrained(QWEN_SNAP, dtype=torch.float32).eval()
    enc = _QW["t"]([str(text)], truncation=True, max_length=96,
                   return_tensors="pt", padding=True)
    with torch.no_grad():
        h = _QW["m"](**enc).last_hidden_state[0]         # (T, 896)
    mask = enc["attention_mask"][0].unsqueeze(-1).float()
    return ((h * mask).sum(0) / mask.sum()).numpy().astype(np.float32)


# ── 질의 구현 ─────────────────────────────────────────────────────────
def q_generate(prompt, n=48, temp=0.8, topk=50):
    ids = TOKC.encode(prompt).ids or [0]
    x = torch.tensor([ids])
    with LOCK, torch.no_grad():
        for _ in range(int(n)):
            logits, _ = LM(x[:, -LMCFG.seq_len:])
            v, ix = torch.topk(logits[0, -1] / max(0.1, float(temp)), int(topk))
            nxt = ix[torch.multinomial(torch.softmax(v, -1), 1)]
            x = torch.cat([x, nxt.view(1, 1)], dim=1)
    return {"본문": TOKC.decode(x[0].tolist()), "학습 스텝": LM_STEP}


def q_surprisal(text):
    ids = TOKC.encode(text).ids
    if len(ids) < 2:
        return {"오류": "너무 짧다"}
    x = torch.tensor([ids])
    with LOCK, torch.no_grad():
        logits, _ = LM(x)
    nll = F.cross_entropy(logits[0, :-1], x[0, 1:], reduction="mean")
    return {"nll/token": round(float(nll), 4), "토큰": len(ids),
            "ppl": round(math.exp(min(20.0, float(nll))), 1)}


def _predict_quantiles(sc, cond, base):
    x = torch.from_numpy(np.concatenate([sc, cond], axis=0)[None].astype(np.float32))
    with LOCK, torch.no_grad():
        q = TR(x).numpy()[0] + base                      # (91,5) log 눈금
    cum = np.expm1(q).cumsum(axis=0)
    day = np.expm1(q)
    def cell(t):
        return {"q05": int(cum[t, 0]), "q50": int(cum[t, 2]), "q95": int(cum[t, 4])}
    return {"누적": {"7일": cell(6), "30일": cell(29), "90일": cell(90)},
            "일별 q50(1·7·30·90일째)": [round(float(day[i, 2]), 1) for i in (0, 6, 29, 90)]}


def q_entity(i):
    i = int(i) % len(DATA.va)
    gi = DATA.va[i]
    m = META[gi]
    out = _predict_quantiles(DATA.Sc[gi], DATA.C[gi], float(DATA.base[gi]))
    true_cum = np.expm1(DATA.O[gi]).cumsum()
    out.update({"개체": m["개체"], "도메인": m["도메인"], "기준일": m["언제"],
                "직전 90일 일평균": round(float(np.expm1(DATA.S[gi]).mean()), 1),
                "실제(누적)": {"7일": int(true_cum[6]), "30일": int(true_cum[29]),
                            "90일": int(true_cum[90])},
                "텍스트(액션)": m["텍스트"][:160]})
    return out


def q_custom(curve, domain, date, text=None):
    vals = [float(v) for v in str(curve).replace(",", " ").split() if v.strip()]
    if len(vals) == 1:
        vals = vals * 90
    if len(vals) != 90:
        return {"오류": "곡선은 숫자 90 개(또는 평탄 가정용 1 개)여야 한다 — 지금 %d 개" % len(vals)}
    if domain not in DOMS:
        return {"오류": "도메인은 %s 중 하나" % DOMS}
    info = {}
    sc, cond, base = _features_from_raw(vals, domain, date, text=text, info=info)
    out = _predict_quantiles(sc, cond, base)
    out.update(info)
    # 🔴 구간 붕괴 감지 — q95/q05 폭이 상식 밖으로 좁으면 그 자체가 경고다
    w = out["누적"]["90일"]
    if w["q95"] <= w["q05"] * 1.05:
        out["🔴 구간 붕괴"] = "q05~q95 폭 5% 미만 — 과신 신호. 이 값 신뢰 금지"
    out.update({"도메인": domain, "기준일": date,
                "직전 90일 일평균": round(float(np.mean(vals)), 1),
                "⚠": PERF_NOTE + " · 조건부 예측이지 인과가 아니다"})
    return out


def _features_from_raw(vals, domain, date, text=None, info=None):
    s_log = np.log1p(np.asarray(vals, dtype=np.float64)).astype(np.float32)
    base = float(s_log.mean())
    sc = s_log - base
    onehot = np.zeros(len(DOMS), dtype=np.float32)
    onehot[DOMS.index(domain)] = 1.0
    mth, day = float(date[5:7]), float(date[8:10])
    doy = mth * 30.4 + day
    cond = np.concatenate([onehot,
                           [np.sin(2 * np.pi * doy / 365.0)],
                           [np.cos(2 * np.pi * doy / 365.0)],
                           [(float(date[:4]) + (mth - 0.5) / 12.0 - 2013.0) / 10.0],
                           [base]]).astype(np.float32)
    if TEXT_DIM:                                         # 텍스트 조건 모형과 차원 정합
        if text:
            emb = _embed_text_live(text)
            # 🔴 OOD 자 — 학습 분포(웹 언급 문구)에서 얼마나 먼가
            dmin = float(np.sqrt(((E_TRAIN - emb[None]) ** 2).sum(-1)).min())
            ratio = dmin / max(REF_NN, 1e-9)
            if info is not None:
                info["텍스트 OOD 비율(1≈분포 안 · 3+ 경고 · 5+ 대체)"] = round(ratio, 2)
            if ratio > 5.0:
                emb = DOM_EMB.get(domain, GLOB_EMB)
                if info is not None:
                    info["텍스트 조건"] = ("🔴 극단 OOD — 텍스트를 «버리고» 도메인 평균으로 대체. "
                                       "이 모형의 텍스트는 «웹 언급 문구» 분포로 학습됐다 — "
                                       "기획서 문체는 아직 밖이다")
            elif info is not None:
                info["텍스트 조건"] = ("제공됨(라이브 임베딩)" if ratio <= 3.0 else
                                   "⚠ OOD 경계(비율 %.1f) — 값을 신중히" % ratio)
        else:
            emb = DOM_EMB.get(domain, GLOB_EMB)          # 미제공 → 도메인 평균 대체
            if info is not None:
                info["텍스트 조건"] = "미제공 → 도메인 평균 임베딩 대체"
        cond = np.concatenate([cond, emb]).astype(np.float32)
    return sc, cond, base


def _quant_curves(sc, cond, base):
    x = torch.from_numpy(np.concatenate([sc, cond], axis=0)[None].astype(np.float32))
    with LOCK, torch.no_grad():
        q = TR(x).numpy()[0] + base
    return q                                                   # (91,5) log 눈금


def q_report(curve, domain, date, text=None):
    """리스크 창 · 민감도 · 유사 사례 — ①③④ 의 «오늘 되는» 판."""
    vals = [float(v) for v in str(curve).replace(",", " ").split() if v.strip()]
    if len(vals) == 1:
        vals = vals * 90
    if len(vals) != 90:
        return {"오류": "곡선은 90 개(또는 1 개=평탄)"}
    if domain not in DOMS:
        return {"오류": "도메인은 %s 중" % DOMS}
    info_r = {}
    sc, cond, base = _features_from_raw(vals, domain, date, text=text, info=info_r)
    q = _quant_curves(sc, cond, base)
    day50 = np.expm1(q[:, 2]); day05 = np.expm1(q[:, 0]); day95 = np.expm1(q[:, 4])
    now = float(np.mean(vals))

    # ── ③ 리스크 창: «언제» 흔들리나 ──────────────────────────────────
    under = np.where(day05 < 0.5 * now)[0]                    # 하방 분위가 현 수준 절반 밑
    fog = np.log(np.maximum(day95, 1e-9) / np.maximum(day05, 1e-9))
    fog_week = int(np.argmax([fog[i:i+7].mean() for i in range(0, 84, 7)]))
    risk = {
        "🔴 하방 위험이 열리는 첫 날": (int(under[0]) + 1) if len(under) else "90일 안 없음",
        "하방 시나리오(q05)가 현 수준의 절반 밑인 날 수": int(len(under)),
        "불확실성이 가장 큰 주": "%d~%d일째" % (fog_week * 7 + 1, fog_week * 7 + 7),
        "뜻": "그 주가 모니터링·재판단 시점이다 — 예측이 거기서 제일 흐리다"}

    # ── ④ 민감도: «어딜 바꾸면» 예측이 얼마나 움직이나 ────────────────
    def cum90(vv, dd, tt):
        sc2, c2, b2 = _features_from_raw(vv, dd, tt, text=text)
        qq = _quant_curves(sc2, c2, b2)
        return float(np.expm1(qq[:, 2]).sum())
    ref = float(day50.sum())
    def shift_date(months):
        y, m, d = int(date[:4]), int(date[5:7]), int(date[8:10])
        m2 = m + months
        y2 = y + (m2 - 1) // 12
        m2 = (m2 - 1) % 12 + 1
        return "%04d-%02d-%02d" % (y2, m2, min(d, 28))
    sens = {
        "초기 관심 +20% (곡선×1.2)": round(cum90([v * 1.2 for v in vals], domain, date) / ref - 1, 3),
        "초기 관심 −20%": round(cum90([v * 0.8 for v in vals], domain, date) / ref - 1, 3),
        "시점 +1달": round(cum90(vals, domain, shift_date(1)) / ref - 1, 3),
        "시점 +3달": round(cum90(vals, domain, shift_date(3)) / ref - 1, 3),
        "막판 상승 추세(마지막 30일 +30%)":
            round(cum90(vals[:60] + [v * 1.3 for v in vals[60:]], domain, date) / ref - 1, 3),
        "🔴 라벨": "모형 «민감도»다 — 인과 검증 안 됨(노트 903: A급 개입 효과가 위약 한복판). "
                  "「이 입력이 다르면 예측이 이렇게 다르다」까지만"}

    # ── ① 유사 사례: 근거를 «실제 궤적»으로 ──────────────────────────
    dom_idx = DOMS.index(domain)
    pool = [i for i in DATA.tr if DATA.C[i][dom_idx] == 1.0] or list(DATA.tr)
    P = DATA.Sc[pool]
    dist = np.linalg.norm(P - sc[None], axis=1)
    order = np.argsort(dist)                      # 같은 개체 반복을 걸러 «서로 다른» 사례 3 개
    cases, seen_ent = [], set()
    for j in order:
        gi = pool[int(j)]
        if META[gi]["개체"] in seen_ent:
            continue
        seen_ent.add(META[gi]["개체"])
        if len(cases) >= 3:
            break
        m = META[gi]
        tc = float(np.expm1(DATA.O[gi]).sum())
        s90 = float(np.expm1(DATA.S[gi]).mean())
        cases.append({"개체": m["개체"], "기준일": m["언제"],
                      "당시 일평균": round(s90, 1),
                      "실제 90일 누적": int(tc),
                      "현 수준 대비 배율": round(tc / max(now * 90.0, 1e-9), 2)})

    return {"입력": dict({"도메인": domain, "기준일": date, "직전 90일 일평균": round(now, 1)}, **info_r),
            "예측(누적 90일)": {"q05": int(np.expm1(q[:, 0]).sum()),
                             "q50": int(ref), "q95": int(np.expm1(q[:, 4]).sum())},
            "③ 언제 — 리스크 창": risk,
            "④ 어딜 — 민감도(전략 수정 후보)": sens,
            "① 근거 — 유사 사례(같은 도메인 · 학습 표본)": cases,
            "⚠": PERF_NOTE + " · 조건부 예측 · ⑤(여론)은 이 판이 아니다"}


# ── HTML ──────────────────────────────────────────────────────────────
PAGE = """<!doctype html><meta charset=utf-8>
<title>월드모델 창구</title>
<style>
 body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;background:#111;color:#ddd;
      max-width:860px;margin:24px auto;padding:0 16px}
 h1{font-size:20px} h2{font-size:15px;color:#8fb;margin:26px 0 8px}
 textarea,input,select{background:#1c1c1c;color:#eee;border:1px solid #444;border-radius:6px;
      padding:8px;font-size:14px;width:100%;box-sizing:border-box}
 button{background:#2a6;border:0;color:#fff;padding:8px 18px;border-radius:6px;cursor:pointer;margin-top:6px}
 pre{background:#181818;border:1px solid #333;border-radius:8px;padding:12px;white-space:pre-wrap;
     font-size:13px;min-height:20px}
 .warn{color:#fa5;font-size:12px} .row{display:flex;gap:8px} .row>*{flex:1}
</style>
<h1>월드모델 창구 <span class=warn>· 로컬 전용(127.0.0.1:8899)</span></h1>

<h2>① LM 이어쓰기 <span class=warn id=lmstep></span></h2>
<textarea id=g_p rows=2>이 웹툰은 </textarea>
<div class=row><input id=g_n value=48 title=토큰수><input id=g_t value=0.8 title=온도></div>
<button onclick="api('generate',{prompt:v('g_p'),n:v('g_n'),temp:v('g_t')},'g_o')">생성</button>
<pre id=g_o></pre>

<h2>② 놀람도 (문장 비교)</h2>
<textarea id=s_a rows=2>서울에서 열린 팝업스토어에 사람들이 모였다</textarea>
<textarea id=s_b rows=2>서울에서 열린 팝업스토어에 바나나가 헤엄쳤다</textarea>
<button onclick="cmp()">비교</button>
<pre id=s_o></pre>

<h2>③ 90일 예측 — 검증 개체 (모형이 학습에서 못 본 IP)</h2>
<div class=row><input id=e_i value=42 title="0~1128"><button onclick="api('entity',{i:v('e_i')},'e_o')">조회</button></div>
<pre id=e_o></pre>

<h2>③′ 90일 예측 — 직접 입력</h2>
<textarea id=c_c rows=2 placeholder="직전 90일 일별 값 90개(쉼표/공백 구분) — 숫자 하나면 평탄 가정">150</textarea>
<textarea id=c_tx rows=2 placeholder="(선택) 기획서·소개 텍스트 — 넣으면 텍스트 조건 예측"></textarea>
<div class=row><select id=c_d></select><input id=c_dt type=date value=2024-01-15></div>
<button onclick="api('custom',{curve:v('c_c'),domain:v('c_d'),date:v('c_dt'),text:v('c_tx')},'c_o')">예측</button>
<pre id=c_o></pre>

<h2>④ 리포트 — 리스크 창 · 민감도 · 유사 사례</h2>
<textarea id=r_c rows=2 placeholder="직전 90일 곡선(90개 또는 1개)">150</textarea>
<textarea id=r_tx rows=2 placeholder="(선택) 기획서·소개 텍스트"></textarea>
<div class=row><select id=r_d></select><input id=r_dt type=date value=2024-01-15></div>
<button onclick="api('report',{curve:v('r_c'),domain:v('r_d'),date:v('r_dt'),text:v('r_tx')},'r_o')">리포트</button>
<pre id=r_o></pre>

<script>
const v=id=>document.getElementById(id).value;
async function api(ep,body,out){
 document.getElementById(out).textContent='…';
 const r=await fetch('/api/'+ep,{method:'POST',body:JSON.stringify(body)});
 document.getElementById(out).textContent=JSON.stringify(await r.json(),null,1);}
async function cmp(){
 document.getElementById('s_o').textContent='…';
 const a=await (await fetch('/api/surprisal',{method:'POST',body:JSON.stringify({text:v('s_a')})})).json();
 const b=await (await fetch('/api/surprisal',{method:'POST',body:JSON.stringify({text:v('s_b')})})).json();
 document.getElementById('s_o').textContent=
   'A: '+JSON.stringify(a)+'\\nB: '+JSON.stringify(b)+
   '\\n→ 모형이 A 를 더 자연스럽다고 본다: '+(a['nll/token']<b['nll/token']);}
fetch('/api/info').then(r=>r.json()).then(d=>{
 document.getElementById('lmstep').textContent='(체크포인트 스텝 '+d.lm_step+' — 완주 전 옹알이 단계)';
 const s=document.getElementById('c_d');
 d.domains.forEach(x=>{const o=document.createElement('option');o.textContent=x;s.appendChild(o);});
 s.value='팝업';
 const s2=document.getElementById('r_d');
 d.domains.forEach(x=>{const o=document.createElement('option');o.textContent=x;s2.appendChild(o);});
 s2.value='팝업';});
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode("utf-8"))

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if self.path == "/api/manifest":                 # 외부 하네스(채팅 서버 등)용 도구 계약
            from pretrain import wm_tools
            return self._send(200, json.dumps(
                [{"name": t["name"], "description": t["description"],
                  "inputSchema": t["inputSchema"]} for t in wm_tools.MANIFEST],
                ensure_ascii=False))
        return self._send(404, "{}")

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/generate":
                out = q_generate(body.get("prompt", ""), body.get("n", 48),
                                 body.get("temp", 0.8))
            elif self.path == "/api/surprisal":
                out = q_surprisal(body.get("text", ""))
            elif self.path == "/api/entity":
                out = q_entity(body.get("i", 0))
            elif self.path == "/api/custom":
                out = q_custom(body.get("curve", ""), body.get("domain", ""),
                               body.get("date", "2024-01-15"), body.get("text"))
            elif self.path == "/api/report":
                out = q_report(body.get("curve", ""), body.get("domain", ""),
                               body.get("date", "2024-01-15"), body.get("text"))
            elif self.path == "/api/tool":
                from pretrain import wm_tools           # 지연 적재(순환 회피)
                out = wm_tools.call(body.get("name"), body.get("args") or {})
            elif self.path == "/api/info":
                out = {"lm_step": LM_STEP if LM else None, "lm_ckpt": LM_PATH,
                       "transition 정본": TR_SRC,
                       "domains": DOMS or [], "val_n": len(DATA.va) if DATA is not None else 0}
            else:
                return self._send(404, "{}")
            return self._send(200, json.dumps(out, ensure_ascii=False))
        except Exception as e:                                     # noqa: BLE001
            return self._send(500, json.dumps({"오류": "%s: %s" % (type(e).__name__, e)},
                                              ensure_ascii=False))


if __name__ == "__main__":
    assert LM is not None, "🔴 LM 체크포인트가 없다"
    assert TR is not None, "🔴 전이 모형이 없다 — python3 pretrain/transition.py train 먼저"
    print("창구: http://127.0.0.1:%d  (LM %s · step %s)" % (PORT, LM_PATH, LM_STEP), flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
