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
#note{top:1rem;right:1rem;padding:.7rem .9rem;width:16rem;display:none}
#note h2{font-size:.8rem;font-weight:650}
#note .k{color:var(--mut);font-size:.72rem;margin-top:.5rem}
#note input{width:100%;background:#0d1116;color:var(--fg);border:1px solid var(--line);
 border-radius:.3rem;padding:.35rem .45rem;font:inherit;margin-top:.15rem}
#note table{width:100%;border-collapse:collapse;font-size:.73rem;margin-top:.45rem}
#note td{padding:.13rem 0;border-bottom:1px solid var(--line)}
#note td:last-child{text-align:right;font-variant-numeric:tabular-nums}
#note .x{position:absolute;top:.5rem;right:.6rem;color:var(--mut);cursor:pointer}
.pin{position:absolute;z-index:4;transform:translate(-50%,-100%);pointer-events:none}
.pin b{display:block;background:var(--acc);color:#04211e;font-size:.7rem;
 padding:.1rem .4rem;border-radius:.25rem;white-space:nowrap;font-weight:650}
.pin s{display:block;width:1px;height:14px;background:var(--acc);margin:0 auto;
 text-decoration:none}
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
<div id=hint>지도를 찍으면 그 자리에 개입을 넣고 30일 뒤를 예측한다</div>
<div class=hud id=note><span class=x id=close>✕</span>
 <h2 id=nname></h2>
 <div class=k>충격 크기 (log10)</div><input id=amp type=number value=0.3 step=.05>
 <div class=k>며칠 동안</div><input id=span type=number value=14 min=1 max=56>
 <div class=k id=nstat>계산 중…</div>
 <div id=ntop></div>
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
 $('#note').style.display='block'; $('#nname').textContent=best.name;
 await run();
}
async function run(){
 if(!pin)return;
 $('#nstat').textContent='계산 중…'; $('#ntop').innerHTML='';
 const q=new URLSearchParams({code:pin.c.api,amp:$('#amp').value,span:$('#span').value});
 const r=await (await fetch('/api/intervene?'+q)).json();
 if(r['오류']){$('#nstat').textContent=r['오류'];return;}
 delta=new Float32Array(CENT.length).fill(NaN);
 CENT.forEach(c=>{const v=r.values[c.code]; if(v!=null)delta[c.i]=v*6;});
 $('#nstat').innerHTML=`30일 뒤 <b>차이</b> · 색은 6배 확대<br>
  <span style="color:var(--mut)">관측에서 배운 연관이지 인과가 아니다</span>`;
 const top=Object.entries(r.values).sort((a,b)=>Math.abs(b[1])-Math.abs(a[1])).slice(0,6);
 const nm={}; CENT.forEach(c=>nm[c.code]=c.name);
 $('#ntop').innerHTML='<table>'+top.map(([c,v])=>
  `<tr><td>${nm[c]||c}</td><td>${v>0?'+':''}${v.toFixed(4)}</td></tr>`).join('')+'</table>';
 $('#cap').textContent=`개입: ${pin.c.name} +${$('#amp').value} × ${$('#span').value}일`;
 render();
}
$('#hit').onclick=e=>{const r=CV.getBoundingClientRect();test(e.clientX-r.left,e.clientY-r.top);};
$('#close').onclick=()=>{delta=null;pin=null;$('#note').style.display='none';
 document.querySelectorAll('.pin').forEach(e=>e.remove());
 $('#cap').textContent=CAP; render();};
$('#amp').onchange=run; $('#span').onchange=run;
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
