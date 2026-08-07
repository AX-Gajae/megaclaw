"""유동인구 장을 **기상도처럼** 지도에 올리고, 개입을 시험한다(노트 647).

사용자 요청: *"한국 지도 가져와서 그 위에 학습한 장을 올려서 기상 예보처럼
분석하는 걸 만들어 줘. 그리고 특정 위치에 특정 테스트 입력해서 테스트도
해볼 수 있게 서버 하나 띄워 줘."*

**무엇을 그리나.** 기상도의 색은 물리량(풍속·강수)이고 여기서는 **유동인구
이상치**다 --- log10 값에서 동네 평균 · 요일 · 그날 전국 평균을 뺀 나머지
(노트 644 와 같은 정의). 즉 *"이 동네가 오늘 평소보다 얼마나 붐비나"* 이고,
전국이 같이 움직인 몫은 이미 빠져 있어서 **국소 이상만** 남는다.

**기상도와 다른 점 하나를 분명히 해 둔다.** 기상도에는 유선(streamline)이
있고 그건 속도장이다. 우리에겐 속도장이 없다 --- 노트 644 가 쟀듯 하루 지연
확산항은 t=17 로 유의하지만 설명력 증분이 R² +0.0017 이라 **이동이 관측
간격보다 빠르다.** 없는 것을 화살표로 그리면 거짓이므로 안 그린다. 대신
**추세**(최근 7일 기울기)를 두 번째 모드로 둔다.

**개입 시험.** 한 동네에 충격을 넣고(예: 이상치 +0.3 을 최근 14일에) 사전학습
인코더(노트 645)로 30일 뒤 장을 예측해 **차이**를 그린다. 그것이 *"여기에
이걸 하면 한 달 뒤 어디가 어떻게 되나"* 다. 노트 645 의 인코더는 저계수 공간
혼합(264→8→264)을 배웠으므로 충격이 **같이 움직이는 무리**로 번진다.

**정직하게 붙일 경고.** 이 예측은 관측 자료에서 배운 연관이지 개입의 인과
효과가 아니다. `p(y|do(a))` 를 재려면 실제로 개입한 기록이 있어야 하고
(L4, 노트 632) 그건 아직 없다. 화면에도 그렇게 적는다.

쓰는 법::

    python3 -m viz.server            # http://127.0.0.1:8765
    python3 -m viz.server --port 9000
"""
from __future__ import annotations

import argparse
import json
import re
import threading
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
GEO = ROOT / "data/state/geo"
ENC = ROOT / "data/state/fieldmodel/enc.pt"

_LOCK = threading.Lock()
_CACHE: dict = {}


def _load():
    """장 · 지도 · 코드표를 한 번만 올린다."""
    with _LOCK:
        if _CACHE:
            return _CACHE
        from state.fieldmodel import field
        codes, days, X = field(stats_end="20241231")
        cmap = json.loads((GEO / "code_map.json").read_text())
        gj = json.loads((GEO / "sigungu.json").read_text())
        names = json.loads((ROOT / "data/state/visitors/_names.json").read_text())
        _CACHE.update(codes=codes, days=days, X=X, cmap=cmap, gj=gj, names=names,
                      ci={c: i for i, c in enumerate(codes)},
                      di={d: i for i, d in enumerate(days)})
        return _CACHE


def field_on(ymd: str, mode: str = "obs") -> dict:
    """그날의 장. mode: obs(이상치) | trend(최근 7일 기울기)."""
    C = _load()
    if ymd not in C["di"]:
        ymd = C["days"][-1]
    j = C["di"][ymd]
    out = {}
    for c, i in C["ci"].items():
        g = C["cmap"].get(c)
        if not g:
            continue
        if mode == "trend":
            a = C["X"][i, max(0, j - 6):j + 1]
            v = float(np.nanmean(a[-3:]) - np.nanmean(a[:3])) if np.isfinite(a).sum() >= 4 else np.nan
        else:
            v = float(C["X"][i, j])
        if np.isfinite(v):
            out[g] = round(v, 4)
    return {"date": ymd, "mode": mode, "values": out}


def series(n: int = 120, mode: str = "obs", end: str | None = None) -> dict:
    """마지막 ``n`` 일의 장을 통째로 준다 — **애니메이션용**.

    프레임마다 서버를 때리면 흐르는 것처럼 안 보인다. 한 번에 받아서
    브라우저가 날 사이를 보간한다.
    """
    C = _load()
    days = C["days"]
    j1 = C["di"].get(end or "", len(days) - 1)
    j0 = max(0, j1 - n + 1)
    sel = days[j0:j1 + 1]
    out = {}
    for c, i in C["ci"].items():
        g = C["cmap"].get(c)
        if not g:
            continue
        row = C["X"][i, j0:j1 + 1]
        out[g] = [None if not np.isfinite(v) else round(float(v), 4) for v in row]
    return {"days": sel, "values": out, "mode": mode}


def intervene(code: str, amp: float = 0.3, span: int = 14,
              horizon: int = 30) -> dict:
    """한 동네에 충격을 넣고 30일 뒤 장의 **차이**를 예측한다."""
    import torch
    import torch.nn as nn
    C = _load()
    if not ENC.exists():
        return {"오류": "인코더가 없다 — `python3 -m state.fieldmodel pretrain` 먼저"}
    ck = torch.load(ENC, map_location="cpu", weights_only=False)
    dim, L = ck["dim"], ck["lookback"]
    tr_codes = ck["codes"]
    D = len(tr_codes)
    K = 8

    class Enc(nn.Module):
        def __init__(s):
            super().__init__()
            s.emb = nn.Embedding(D, dim); s.tconv = nn.Linear(L, dim)
            s.down = nn.Linear(D, K, bias=False); s.up = nn.Linear(K, D, bias=False)
            s.mix = nn.Linear(dim * 3, dim); s.head = nn.Linear(dim, 1)

        def forward(s, w):
            e = s.emb.weight.unsqueeze(0).expand(w.shape[0], -1, -1)
            h = torch.tanh(s.tconv(w))
            g = s.up(s.down(h.transpose(1, 2))).transpose(1, 2)
            return s.head(torch.tanh(s.mix(torch.cat([h, e, g], -1)))).squeeze(-1)

    net = Enc(); net.load_state_dict(ck["state"]); net.eval()

    # 학습 때 쓴 동네 순서로 최근 창을 만든다
    idx = {c: i for i, c in enumerate(tr_codes)}
    W = np.zeros((D, L), np.float32)
    for c, i in idx.items():
        j = C["ci"].get(c)
        if j is not None:
            W[i] = np.nan_to_num(C["X"][j, -L:], nan=0.0)
    W2 = W.copy()
    if code in idx:
        W2[idx[code], -span:] += amp
    with torch.no_grad():
        a = net(torch.tensor(W[None])).numpy()[0]
        b = net(torch.tensor(W2[None])).numpy()[0]
    d = b - a
    out = {}
    for c, i in idx.items():
        g = C["cmap"].get(c)
        if g and abs(float(d[i])) > 1e-9:
            out[g] = round(float(d[i]), 5)
    src = C["cmap"].get(code)
    return {"충격": {"코드": code, "이름": C["names"].get(code), "지도코드": src,
                   "크기": amp, "일수": span},
            "지평": horizon, "values": out,
            "주의": "관측에서 배운 연관이지 개입의 인과 효과가 아니다(L4 미측정)"}



# ── 글로 쓴 주석 → 충격 (노트 648) ────────────────────────────
#
# **숫자 입력을 없앤 이유.** 처음엔 사용자가 진폭을 직접 넣었는데, 기본값으로
# 박아 둔 **+0.3 이 근거가 없었다.** 레코드 43건으로 실측하니 팝업이 그 동네
# 이상치에 남기는 자국은 **중앙 +0.0087**(90분위 +0.052 · SD 0.055)이다.
# 즉 화면이 **35배 과장된 충격**을 보여 주고 있었다.
#
# 산술로도 맞는다 --- 팝업 1만 명을 20일에 나누면 하루 500명이고 성동구
# 외지인은 하루 36만이라 0.14%, log10 으로 0.0006 이다. 관측된 +0.0087 은
# 그보다 크고 **그 차이는 팝업이 이미 뜨는 동네에 열린다는 교란**이지 인과가
# 아니다. 그래서 화면에도 '연관' 이라고 적는다.
#
# 표는 **팝업만 측정값**이고 나머지는 **가정**이다. 그 구분을 응답에 실어
# 화면이 같이 보여 준다 --- 안 그러면 가정이 측정처럼 읽힌다.
SHOCK = {
    "팝업":   (0.0087, "측정 (레코드 43건 중앙값)"),
    "대형팝업": (0.052, "측정 (레코드 43건 90분위)"),
    "축제":   (0.052, "가정 — 대형 팝업과 같게 뒀다. 축제는 안 쟀다"),
    "공연":   (0.030, "가정 — 안 쟀다"),
    "콘서트":  (0.052, "가정 — 안 쟀다"),
    "전시":   (0.0087, "가정 — 팝업과 같게 뒀다"),
    "공사":   (-0.030, "가정 — 안 쟀다"),
    "폐쇄":   (-0.052, "가정 — 안 쟀다"),
}
SIZE = {"거대": 4.0, "대형": 3.0, "큰": 3.0, "중형": 1.0, "소형": 0.4, "작은": 0.4}
_NUM = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*(일|주|주일|개월|달|배|%)?")


def annotate(text: str) -> dict:
    """글 → (진폭, 일수). **해석한 결과를 같이 돌려준다.**

    무엇으로 읽었는지 화면에 보여 주지 않으면 사용자가 숫자를 못 검증한다.
    """
    t = (text or "").strip()
    flat = t.replace(" ", "")
    kind, amp, src = None, None, None
    # **긴 열쇳말부터 본다.** 안 그러면 ``대형팝업`` 이 ``팝업`` 에 먼저 걸려
    # 배수만 곱해진 다른 값이 나온다.
    for k in sorted(SHOCK, key=len, reverse=True):
        if k in flat:
            kind, (amp, src) = k, SHOCK[k]
            break
    # **크기말이 열쇳말에 이미 들어 있으면 배수를 또 곱하지 않는다.**
    # ``대형 팝업`` 이 ``대형팝업``(0.052) 에 걸린 뒤 ×3 까지 먹으면 0.156 이
    # 되어 실측 90분위를 세 배 넘는다 --- 같은 정보를 두 번 세는 것이다.
    mult = 1.0
    for k, m in SIZE.items():
        if k in t and (kind is None or k not in kind):
            mult = m
            break
    span = 14
    # 숫자 없는 한국어 수량 --- ``한 달`` · ``두 주``
    for w, v in (("한", 1), ("두", 2), ("세", 3), ("네", 4), ("다섯", 5)):
        for u, mday in (("달", 30), ("개월", 30), ("주", 7), ("주일", 7), ("일", 1)):
            if w + u in flat or w + " " + u in t:
                span = int(min(120, v * mday))
    for num, unit in _NUM.findall(t):
        v = float(num)
        if unit in ("일",):
            span = int(max(1, min(120, v)))
        elif unit in ("주", "주일"):
            span = int(max(1, min(120, v * 7)))
        elif unit in ("개월", "달"):
            span = int(max(1, min(120, v * 30)))
        elif unit == "배":
            mult *= v
    # 진폭을 글에 직접 적었으면 그것이 이긴다
    m = re.search(r"([+-]\d*\.\d+)", t)
    if m:
        amp, kind, src = float(m.group(1)), "직접 입력", "사용자가 적은 값"
    if amp is None:
        amp, kind, src = SHOCK["팝업"][0], "팝업(기본)", SHOCK["팝업"][1]
    return {"amp": round(amp * mult, 5), "span": span,
            "읽음": f"{kind}" + (f" × {mult:g}" if mult != 1 else ""),
            "근거": src,
            "주의": "팝업만 측정값이고 나머지는 가정이다"}


PAGE = r"""<!doctype html><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>유동인구 장 — 대한민국</title>
<style>
:root{--bg:#07090c;--fg:#eef1f4;--mut:#7f8894;--line:#1b2028;--acc:#68d8cd}
*{box-sizing:border-box;margin:0}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--fg);
 font:13px/1.5 ui-sans-serif,system-ui,"Apple SD Gothic Neo",sans-serif}
#stage{position:fixed;inset:0}
canvas,svg{position:absolute;inset:0;width:100%;height:100%}
svg{pointer-events:none}
path.b{fill:none;stroke:rgba(255,255,255,.16);stroke-width:.5;vector-effect:non-scaling-stroke}
path.coast{stroke:rgba(255,255,255,.42);stroke-width:1}
#hit{position:absolute;inset:0;cursor:crosshair}
.hud{position:absolute;z-index:5;background:rgba(10,13,17,.82);
 border:1px solid var(--line);border-radius:.5rem;backdrop-filter:blur(10px)}
#title{top:1rem;left:1rem;padding:.7rem .9rem}
#title h1{font-size:.95rem;font-weight:650;letter-spacing:-.01em}
#title p{color:var(--mut);font-size:.74rem;margin-top:.15rem}
#legend{bottom:1rem;left:1rem;padding:.6rem .75rem}
#lbar{display:flex;width:13rem;height:9px;border-radius:2px;overflow:hidden}
#lbar i{flex:1}
#lrng{display:flex;justify-content:space-between;font-size:.68rem;
 color:var(--mut);margin-top:.25rem;font-variant-numeric:tabular-nums}
#time{bottom:1rem;left:50%;transform:translateX(-50%);padding:.55rem .8rem;
 display:flex;align-items:center;gap:.7rem}
#time button{background:none;border:1px solid var(--line);color:var(--fg);
 width:1.9rem;height:1.9rem;border-radius:50%;cursor:pointer;font-size:.8rem}
#scrub{width:min(46vw,30rem);accent-color:var(--acc)}
#day{font-variant-numeric:tabular-nums;font-size:.8rem;min-width:5.4rem}
#note{position:absolute;z-index:6;width:17.5rem;padding:.55rem;display:none;
 box-shadow:0 12px 40px rgba(0,0,0,.55);transform:translate(-50%,0)}
#note::before{content:'';position:absolute;top:-5px;left:50%;margin-left:-5px;
 width:10px;height:10px;background:rgba(10,13,17,.82);border-left:1px solid var(--line);
 border-top:1px solid var(--line);transform:rotate(45deg)}
#nname{font-size:.72rem;color:var(--mut);padding:.1rem .25rem .35rem;
 display:flex;align-items:center;gap:.35rem}
#nname i{width:5px;height:5px;border-radius:50%;background:var(--acc);font-style:normal}
#ann{width:100%;background:#0d1116;color:var(--fg);border:1px solid var(--line);
 border-radius:.35rem;padding:.5rem .55rem;font:inherit;line-height:1.45;resize:none;
 min-height:3.6rem}
#ann:focus{outline:none;border-color:var(--acc)}
#nrow{display:flex;justify-content:flex-end;gap:.4rem;margin-top:.45rem}
#nrow button{border:1px solid var(--line);background:none;color:var(--mut);
 padding:.28rem .6rem;border-radius:.3rem;font:inherit;font-size:.76rem;cursor:pointer}
#nrow button.go{background:var(--acc);color:#04211e;border-color:var(--acc);font-weight:650}
#nread,#nstat{color:var(--mut);font-size:.71rem;padding:.35rem .25rem 0;line-height:1.45}
#note table{width:100%;border-collapse:collapse;font-size:.71rem;margin-top:.4rem}
#note td{padding:.13rem .25rem;border-bottom:1px solid var(--line)}
#note td:last-child{text-align:right;font-variant-numeric:tabular-nums}
#hint{bottom:4.6rem;left:50%;transform:translateX(-50%);color:var(--mut);
 font-size:.74rem;z-index:5;text-shadow:0 1px 3px #000}
</style>
<div id=stage>
 <canvas id=field></canvas><svg id=lines viewBox="0 0 1000 1000" preserveAspectRatio="none"></svg>
 <div id=hit></div>
</div>
<div class=hud id=title><h1>유동인구 장</h1><p id=cap>불러오는 중…</p></div>
<div class=hud id=legend><div id=lbar></div><div id=lrng></div></div>
<div class=hud id=time>
 <button id=play>▶</button><input type=range id=scrub min=0 max=0 value=0>
 <span id=day></span>
</div>
<div id=hint>지도를 찍고 <b>무슨 일이 일어나는지 글로 쓰면</b> 30일 뒤를 예측한다</div>
<div class=hud id=note>
 <div id=nname><i></i><span></span></div>
 <textarea id=ann placeholder="여기서 무슨 일이 일어나나 — 예: 대형 팝업 2주"></textarea>
 <div id=nrow><button id=close>취소</button><button class=go id=go>반영</button></div>
 <div id=nread></div><div id=nstat></div><div id=ntop></div>
</div>
<script>
const $=s=>document.querySelector(s);
const CV=$('#field'), CX=CV.getContext('2d');
let GJ,SER,NAMES,CENT=[],BB,W=0,H=0,frame=0,playing=true,delta=null,pin=null;
// 발산 색. 기상도처럼 단계가 보이되 사이는 부드럽게.
const ST=[[-.45,[24,58,120]],[-.22,[38,118,166]],[-.08,[110,186,196]],
          [0,[236,234,226]],[.08,[240,196,110]],[.22,[224,120,52]],[.45,[150,34,28]]];
function col(v){ if(v==null||!isFinite(v))return [22,26,32];
 if(v<=ST[0][0])return ST[0][1]; if(v>=ST[ST.length-1][0])return ST[ST.length-1][1];
 for(let i=0;i<ST.length-1;i++){const[a,ca]=ST[i],[b,cb]=ST[i+1];
  if(v<=b){const t=(v-a)/(b-a);return ca.map((x,k)=>x+(cb[k]-x)*t);}}}
function rings(f){const g=f.geometry;if(!g)return[];
 return g.type==='Polygon'?g.coordinates:g.type==='MultiPolygon'?g.coordinates.flat():[];}
function bbox(){let a=[180,90,-180,-90];
 GJ.features.forEach(f=>rings(f).forEach(r=>r.forEach(p=>{
  a[0]=Math.min(a[0],p[0]);a[1]=Math.min(a[1],p[1]);
  a[2]=Math.max(a[2],p[0]);a[3]=Math.max(a[3],p[1]);})));return a;}
function P(lon,lat){ // 화면 좌표 (여백 5%)
 const[x0,y0,x1,y1]=BB, s=Math.min(W*.9/(x1-x0), H*.9/(y1-y0));
 return [(lon-x0)*s+(W-(x1-x0)*s)/2, H-((lat-y0)*s+(H-(y1-y0)*s)/2)];}
// ── 격자: 셀마다 가까운 구역 k개와 가중치를 **한 번만** 계산한다
let GRID=null, GW=0, GH=0, CELL=7;
function buildGrid(){
 GW=Math.ceil(W/CELL); GH=Math.ceil(H/CELL);
 const pts=CENT.map(c=>({i:c.i,xy:P(c.lon,c.lat)}));
 GRID=new Array(GW*GH);
 for(let gy=0;gy<GH;gy++)for(let gx=0;gx<GW;gx++){
  const x=gx*CELL+CELL/2, y=gy*CELL+CELL/2;
  const d=pts.map(p=>({i:p.i,d:(p.xy[0]-x)**2+(p.xy[1]-y)**2}));
  d.sort((a,b)=>a.d-b.d); const k=d.slice(0,6);
  let s=0; const w=k.map(o=>{const v=1/Math.pow(o.d+40,1.35);s+=v;return v;});
  GRID[gy*GW+gx]={i:k.map(o=>o.i),w:w.map(v=>v/s)};}
}
function clipPath(ctx){ctx.beginPath();
 GJ.features.forEach(f=>rings(f).forEach(r=>{
  r.forEach((p,j)=>{const q=P(p[0],p[1]); j?ctx.lineTo(q[0],q[1]):ctx.moveTo(q[0],q[1]);});
  ctx.closePath();}));}
function paint(vals){
 CX.clearRect(0,0,W,H); CX.save(); clipPath(CX); CX.clip();
 const img=CX.createImageData(GW,GH), D=img.data;
 for(let n=0;n<GW*GH;n++){const g=GRID[n];let v=0,wt=0;
  for(let k=0;k<g.i.length;k++){const x=vals[g.i[k]];
   if(x!=null&&isFinite(x)){v+=x*g.w[k];wt+=g.w[k];}}
  const c=col(wt>0?v/wt:null); const o=n*4;
  D[o]=c[0];D[o+1]=c[1];D[o+2]=c[2];D[o+3]=255;}
 const off=document.createElement('canvas'); off.width=GW; off.height=GH;
 off.getContext('2d').putImageData(img,0,0);
 CX.imageSmoothingEnabled=true; CX.imageSmoothingQuality='high';
 CX.drawImage(off,0,0,W,H); CX.restore();
}
function outlines(){
 const svg=$('#lines'); svg.setAttribute('viewBox',`0 0 ${W} ${H}`);
 let d='';
 GJ.features.forEach(f=>rings(f).forEach(r=>{
  d+='M'+r.map(p=>P(p[0],p[1]).map(n=>n.toFixed(1)).join(',')).join('L')+'Z';}));
 svg.innerHTML=`<path class="b coast" d="${d}"></path>`;
}
// ── 프레임 값: 날 사이를 보간해 **흐르게** 한다
function at(t){
 const i=Math.floor(t), f=t-i, a=SER.frames[Math.min(i,SER.frames.length-1)],
       b=SER.frames[Math.min(i+1,SER.frames.length-1)], out=new Float32Array(a.length);
 for(let k=0;k<a.length;k++){
  const x=a[k],y=b[k];
  out[k]= (x==null||isNaN(x)) ? (y==null?NaN:y) : (y==null||isNaN(y)? x : x+(y-x)*f);}
 return out;}
function render(){
 if(delta){paint(delta);return;}
 const v=at(frame);
 paint(v);
 const di=Math.min(Math.round(frame),SER.days.length-1);
 $('#day').textContent=SER.days[di].replace(/(\d{4})(\d\d)(\d\d)/,'$1-$2-$3');
 $('#scrub').value=di;
}
let last=0;
function loop(ts){
 if(playing&&!delta&&SER){const dt=(ts-last)/1000; last=ts;
  frame+=dt*3.5; if(frame>SER.frames.length-1)frame=0; render();}
 else last=ts;
 requestAnimationFrame(loop);}
function resize(){
 const r=CV.getBoundingClientRect(); W=Math.round(r.width); H=Math.round(r.height);
 const dpr=Math.min(devicePixelRatio||1,2);
 CV.width=W*dpr; CV.height=H*dpr; CX.setTransform(dpr,0,0,dpr,0,0);
 buildGrid(); outlines(); render();}
// ── 찍으면 시험한다
function toLonLat(x,y){
 const[x0,y0,x1,y1]=BB, s=Math.min(W*.9/(x1-x0), H*.9/(y1-y0));
 return [ (x-(W-(x1-x0)*s)/2)/s + x0, ((H-y)-(H-(y1-y0)*s)/2)/s + y0 ];}
async function test(cx,cy){
 const[lon,lat]=toLonLat(cx,cy);
 let best=null,bd=1e9;
 CENT.forEach(c=>{const d=(c.lon-lon)**2+(c.lat-lat)**2; if(d<bd){bd=d;best=c;}});
 if(!best)return;
 pin={x:cx,y:cy,c:best};
 document.querySelectorAll('.pin').forEach(e=>e.remove());
 const el=document.createElement('div'); el.className='pin';
 el.style.left=cx+'px'; el.style.top=cy+'px';
 el.innerHTML=`<b>${best.name}</b><s></s>`; $('#stage').appendChild(el);
 const nt=$('#note'); nt.style.display='block';
 nt.style.left=Math.max(150,Math.min(W-150,cx))+'px'; nt.style.top=(cy+14)+'px';
 $('#nname').querySelector('span').textContent=best.name;
 $('#ann').value=''; $('#ann').focus();
 $('#nread').innerHTML=''; $('#nstat').textContent='쓰고 ⌘↵ 또는 반영';
 $('#ntop').innerHTML='';
}
async function run(){
 if(!pin)return;
 $('#nstat').textContent='계산 중…'; $('#ntop').innerHTML='';
 const q=new URLSearchParams({code:pin.c.api,text:$('#ann').value});
 const r=await (await fetch('/api/annotate?'+q)).json();
 if(r['오류']){$('#nstat').textContent=r['오류'];return;}
 const a=r['해석'];
 $('#nread').innerHTML=`<b style="color:var(--acc)">${a['읽음']}</b> → 이상치 ${a.amp>0?'+':''}${a.amp} × ${a.span}일<br>
  <span style="opacity:.75">${a['근거']}</span>`;
 delta=new Float32Array(CENT.length).fill(NaN);
 let mx=0; CENT.forEach(c=>{const v=r.values[c.code]; if(v!=null){delta[c.i]=v;mx=Math.max(mx,Math.abs(v));}});
 // 색 눈금을 자동으로 맞춘다 --- 실측 충격은 작아서 고정 눈금이면 안 보인다
 const g=mx>0?0.45/mx:1; for(let i=0;i<delta.length;i++)delta[i]*=g;
 $('#nstat').innerHTML=`30일 뒤 <b>차이</b> · 색 눈금 ×${g.toFixed(0)}<br>
  <span style="opacity:.75">관측에서 배운 연관이지 인과가 아니다</span>`;
 const top=Object.entries(r.values).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1])).slice(0,6);
 const nm={}; CENT.forEach(c=>nm[c.code]=c.name);
 $('#ntop').innerHTML='<table>'+top.map(([c,v])=>
  `<tr><td>${nm[c]||c}</td><td>${v>0?'+':''}${v.toFixed(5)}</td></tr>`).join('')+'</table>';
 $('#cap').textContent=`개입: ${pin.c.name} — ${$('#ann').value||a['읽음']}`;
 render();
}
$('#hit').onclick=e=>{const r=CV.getBoundingClientRect();test(e.clientX-r.left,e.clientY-r.top);};
$('#close').onclick=()=>{delta=null;pin=null;$('#note').style.display='none';
 document.querySelectorAll('.pin').forEach(e=>e.remove());
 $('#cap').textContent=CAP; render();};
$('#go').onclick=run;
$('#ann').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();run();}};
$('#play').onclick=()=>{playing=!playing;$('#play').textContent=playing?'▶':'❚❚';};
$('#scrub').oninput=e=>{playing=false;$('#play').textContent='❚❚';
 frame=+e.target.value;delta=null;render();};
let CAP='';
async function boot(){
 GJ=await (await fetch('/api/geo')).json();
 const places=await (await fetch('/api/places')).json();
 const s=await (await fetch('/api/series?n=180')).json();
 BB=bbox();
 // 구역 무게중심 — 보간의 앵커
 const byGeo={}; places.forEach(p=>byGeo[p.map]=p);
 GJ.features.forEach(f=>{const code=f.properties.code; const rs=rings(f);
  if(!rs.length)return; let sx=0,sy=0,n=0;
  rs.forEach(r=>r.forEach(p=>{sx+=p[0];sy+=p[1];n++;}));
  const pl=byGeo[code];
  CENT.push({code,name:f.properties.name,lon:sx/n,lat:sy/n,
             api:pl?pl.code:null,i:CENT.length});});
 // 시계열을 프레임 배열로
 SER={days:s.days,frames:s.days.map((_,j)=>{
  const a=new Float32Array(CENT.length).fill(NaN);
  CENT.forEach(c=>{const row=s.values[c.code]; if(row&&row[j]!=null)a[c.i]=row[j];});
  return a;})};
 $('#scrub').max=SER.days.length-1;
 $('#lbar').innerHTML=ST.map(x=>`<i style="background:rgb(${x[1].join(',')})"></i>`).join('');
 $('#lrng').innerHTML=`<span>${ST[0][0]}</span><span>평소</span><span>+${ST[ST.length-1][0]}</span>`;
 CAP=`시군구 ${CENT.filter(c=>c.api).length} · ${SER.days[0]}~${SER.days[SER.days.length-1]} · 이상치(요일·전국공통 제거)`;
 $('#cap').textContent=CAP;
 addEventListener('resize',resize); resize(); requestAnimationFrame(loop);
}
boot();
</script>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, body: bytes, ctype: str):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == "/":
                return self._send(PAGE.encode(), "text/html; charset=utf-8")
            if u.path == "/api/geo":
                return self._send((GEO / "sigungu.json").read_bytes(),
                                  "application/json")
            if u.path == "/api/places":
                C = _load()
                ps = [{"code": c, "name": C["names"].get(c, c), "map": C["cmap"][c]}
                      for c in C["ci"] if c in C["cmap"]]
                ps.sort(key=lambda x: x["name"])
                return self._send(json.dumps(ps, ensure_ascii=False).encode(),
                                  "application/json")
            if u.path == "/api/series":
                r = series(int(q.get("n", 120)), q.get("mode", "obs"), q.get("end"))
                return self._send(json.dumps(r, ensure_ascii=False).encode(),
                                  "application/json")
            if u.path == "/api/field":
                r = field_on(q.get("date") or "", q.get("mode", "obs"))
                return self._send(json.dumps(r, ensure_ascii=False).encode(),
                                  "application/json")
            if u.path == "/api/annotate":
                a = annotate(q.get("text", ""))
                r = intervene(q.get("code", ""), a["amp"], a["span"])
                r["해석"] = a
                return self._send(json.dumps(r, ensure_ascii=False).encode(),
                                  "application/json")
            if u.path == "/api/intervene":
                r = intervene(q.get("code", ""), float(q.get("amp", 0.3)),
                              int(q.get("span", 14)))
                return self._send(json.dumps(r, ensure_ascii=False).encode(),
                                  "application/json")
        except Exception as e:
            return self._send(json.dumps({"오류": f"{type(e).__name__}: {e}"},
                                         ensure_ascii=False).encode(),
                              "application/json")
        self.send_response(404); self.end_headers()


def serve(port: int = 8765):
    _load()
    print(json.dumps({"주소": f"http://127.0.0.1:{port}"}, ensure_ascii=False),
          flush=True)
    HTTPServer(("127.0.0.1", port), H).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    serve(ap.parse_args().port)
