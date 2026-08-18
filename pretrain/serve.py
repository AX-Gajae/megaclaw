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
from pretrain.transition import Transition, SAO, TRI, OUT as TROUT

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
tr_path = os.path.join(TROUT, "model.pt")
if os.path.exists(tr_path):
    tck = torch.load(tr_path, map_location="cpu", weights_only=False)
    TR = Transition(tck["d_in"], hidden=tck["hidden"])
    TR.load_state_dict(tck["model"])
    TR.eval()
    DATA = SAO(text_emb=tck.get("text_emb"))
    DOMS = json.load(open(os.path.join(TRI, "domains.json"), encoding="utf-8"))
    META = [json.loads(l) for l in open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")]


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


def q_custom(curve, domain, date):
    vals = [float(v) for v in str(curve).replace(",", " ").split() if v.strip()]
    if len(vals) == 1:
        vals = vals * 90
    if len(vals) != 90:
        return {"오류": "곡선은 숫자 90 개(또는 평탄 가정용 1 개)여야 한다 — 지금 %d 개" % len(vals)}
    if domain not in DOMS:
        return {"오류": "도메인은 %s 중 하나" % DOMS}
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
    out = _predict_quantiles(sc, cond, base)
    out.update({"도메인": domain, "기준일": date,
                "직전 90일 일평균": round(float(np.mean(vals)), 1),
                "⚠": "개체 분리 검증 MdAPE 8.5% · 90% 구간 실측 덮개율 59.6%(미보정) · "
                     "조건부 예측이지 인과가 아니다"})
    return out


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
<div class=row><select id=c_d></select><input id=c_dt type=date value=2024-01-15></div>
<button onclick="api('custom',{curve:v('c_c'),domain:v('c_d'),date:v('c_dt')},'c_o')">예측</button>
<pre id=c_o></pre>

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
 s.value='팝업';});
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
                               body.get("date", "2024-01-15"))
            elif self.path == "/api/info":
                out = {"lm_step": LM_STEP if LM else None, "lm_ckpt": LM_PATH,
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
