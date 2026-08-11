"""🔴 **페이지 JS 를 실제로 돌려 도형을 센다**(node + 가짜 DOM). 노트 913 팔 ㅈ.

    python3 -m runners.trainlog913_viewer_check [run_id]

# 왜 이런 짓을 하나

**HTTP 200 을 성공으로 읽으면 안 된다**(조항 59). 200 은 서버가 답했다는 뜻이지
화면에 무엇이 그려졌다는 뜻이 아니다. 그래서 페이지의 `<script>` 를 통째로 꺼내
**node 에서 가짜 DOM · 가짜 canvas** 위에 돌리고, `arc` · `stroke` · `fillRect` 가
몇 번 불렸는지를 **센다**. 노트 912 가 쓴 방법 그대로다.

🔴 **브라우저 픽셀을 눈으로 본 것은 아니다.** 그것은 이 팔도 **못 했다**.

# 무엇을 재나

    ① 블록 박스 수 · 화살표 수 · **되돌아오는(잔차) 곡선 수**
    ② `N×` 접힘이 눌러서 **펴지나** (접었을 때 박스 수 < 폈을 때 박스 수)
    ③ 층별 상태 색이 **서로 다른가** (grad 막대 색 가짓수)
    ④ 곡선의 눈금을 옮기면 **색이 바뀌나** (다른 step 의 색 목록이 다른가)
    ⑤ 지표가 없는 run 에서 **아무것도 안 그리나**
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "serve/static/trainlog.html"

#: 가짜 DOM --- 페이지가 쓰는 것만 흉내 낸다(전부는 아니다).
SHIM = r"""
const REC = {arc:0, stroke:0, fill:0, fillRect:0, fillText:[], moveTo:0,
             bezier:0, quad:0, colors:[], bars:[], texts:[]};
function Ctx(){
  this.canvas = null;
  const noop = ()=>{};
  this.setTransform=noop; this.clearRect=noop; this.save=noop; this.restore=noop;
  this.translate=noop; this.rotate=noop; this.scale=noop; this.closePath=noop;
  this.setLineDash=noop; this.lineTo=noop;
  this.beginPath=()=>{}; this.moveTo=()=>{REC.moveTo++;};
  this.arc=()=>{REC.arc++;};
  this.stroke=()=>{REC.stroke++;};
  this.fill=()=>{REC.fill++;};
  this.bezierCurveTo=()=>{REC.bezier++;};
  this.quadraticCurveTo=()=>{REC.quad++;};
  this.fillRect=(x,y,w,h)=>{REC.fillRect++;
    REC.bars.push({c:this.fillStyle, w:Math.round(w)});};
  this.fillText=(t)=>{REC.fillText.push(String(t));};
  this.measureText=(t)=>({width: String(t).length*6});
  this.globalAlpha=1; this.fillStyle="#000"; this.strokeStyle="#000";
  this.lineWidth=1; this.font="";
}
function Node(tag){
  this.tagName=(tag||"div").toUpperCase(); this.children=[]; this.childNodes=[];
  this.style={}; this.className=""; this._text="";
  this.clientWidth=760; this.clientHeight=400; this.checked=false; this.value="";
  this.dataset={};
}
Node.prototype.appendChild=function(c){ this.children.push(c);
  this.childNodes.push(c); c.parentNode=this; return c; };
Node.prototype.replaceChild=function(n,o){
  const i=this.children.indexOf(o); if(i>=0){ this.children[i]=n; }
  this.childNodes=this.children; n.parentNode=this; return o; };
Node.prototype.removeChild=function(c){
  this.children=this.children.filter(x=>x!==c); this.childNodes=this.children; };
Node.prototype.getContext=function(){ this._ctx=this._ctx||new Ctx();
  this._ctx.canvas=this; return this._ctx; };
Node.prototype.getBoundingClientRect=function(){
  return {left:0, top:0, width:this.clientWidth, height:this.clientHeight}; };
Node.prototype.addEventListener=function(){};
Object.defineProperty(Node.prototype,"textContent",{
  get(){ return this._text; },
  set(v){ this._text=String(v); this.children=[]; this.childNodes=[]; }});
function findAll(n, out){
  out=out||[]; (n.children||[]).forEach(c=>{ out.push(c); findAll(c,out); });
  return out;
}
const IDS={};
function mk(tag){ const n=new Node(tag);
  Object.defineProperty(n,"id",{get(){return n._id||"";},
    set(v){ n._id=v; IDS[v]=n; }}); return n; }
const doc = {createElement: mk, body: mk("body"),
  createTextNode: (t)=>{ const n=mk("text"); n.textContent=String(t); return n; }};
doc.querySelector = (s)=>{
  if(s[0]==="#") return IDS[s.slice(1)] || null;
  return null;
};
// 🔴 HTML 에 **미리 박혀 있는** 자리들 --- 없으면 페이지가 즉시 터진다
//    (그것도 알고 싶은 것이므로 다른 것은 안 만든다).
["head","runs","detail","hideDemo","reload","cmp","archview",
 "tabArch","tabCmp","tabnote"].forEach(id=>{ const n=mk("div"); n.id=id; });
IDS["archview"].style = {}; IDS["cmp"].style = {};
global.document = doc;
global.window = {devicePixelRatio:1, innerHeight:900, innerWidth:1400,
                 addEventListener:()=>{}};
global.location = {hash:"", replace:(h)=>{ global.location.hash=h; }};
global.setTimeout = (f,ms)=>{ REC.timers=(REC.timers||0)+1; return 0; };
global.clearTimeout = ()=>{};
global.encodeURIComponent = encodeURIComponent;
"""


def _page_js() -> str:
    src = PAGE.read_text(encoding="utf-8")
    m = re.search(r"<script>(.*)</script>", src, re.S)
    if not m:
        raise SystemExit("페이지에서 <script> 를 못 찾았다")
    js = m.group(1)
    #: 🔴 "use strict" 아래에서 `$("#id")` 가 element 를 못 찾으면 터진다 ---
    #: 그것이 **알고 싶은 것**이므로 안 감싼다(터지면 터졌다고 적는다).
    return js


def snapshot(rid: str) -> dict:
    """API 응답을 **실제 창구에서** 떠 온다(가짜 자료를 안 만든다)."""
    sys.path.insert(0, str(ROOT))
    from serve import trainlog_svc as tl
    from trainlog import store
    S = store.node_state(rid)
    단계 = S.get("단계") or []
    본 = {"runs": tl.runs(), "compare": tl.compare()}
    변형 = {}

    def key(fold, expand, step):
        return f"{1 if fold else 0}|{expand}|{'' if step is None else step}"

    for fold, expand, step in [(True, "", None), (False, "", None),
                               (True, "", 단계[0] if 단계 else None)]:
        변형[key(fold, expand, step)] = tl.detail(
            rid, 32, 620, fold, [x for x in expand.split(",") if x], step,
            "grad_norm")
    #: 접힌 대표 하나를 눌러 펴 본다
    대표 = [f["대표"] for f in (변형[key(True, "", None)]
                             .get("블록 그림", {}).get("접은 것") or [])]
    if 대표:
        변형[key(True, 대표[0], None)] = tl.detail(
            rid, 32, 620, True, [대표[0]], None, "grad_norm")
    return {"본": 본, "변형": 변형, "run_id": rid, "단계": 단계,
            "접힌 대표": 대표}


DRIVER = r"""
const DATA = require(DATAFILE);
function pick(u){
  if(u.indexOf("/api/trainlog/runs")===0) return DATA["본"]["runs"];
  if(u.indexOf("/api/trainlog/compare")===0) return DATA["본"]["compare"];
  if(u.indexOf("/api/trainlog/run?")===0){
    const q = new URLSearchParams(u.split("?")[1]);
    const k = (q.get("fold")==="0"?"0":"1") + "|" + (q.get("expand")||"")
            + "|" + (q.get("step")||"");
    return DATA["변형"][k] || DATA["변형"]["1||"];
  }
  if(u.indexOf("/api/trainlog/tail")===0)
    return {"새 점":[], "다음 바이트":0, "살아 있나":{"뱃지":"끝남"}};
  return {};
}
global.fetch = async (u)=> ({ json: async ()=> pick(u) });
"""


def run_js(snap: dict, 시나리오: str) -> dict:
    """페이지 JS 를 node 에서 돌리고 **도형을 센다**."""
    d = Path(tempfile.mkdtemp(prefix="tl913_"))
    (d / "data.json").write_text(json.dumps(snap, ensure_ascii=False),
                                 encoding="utf-8")
    #: 🔴 페이지 JS 뒤에 시나리오를 **비동기로** 붙인다(top-level await 은 CJS 에서
    #: 안 된다). 시나리오가 끝난 뒤에만 센다 --- 안 그러면 fetch 전에 세게 된다.
    js = (SHIM
          + 'const DATAFILE = ' + json.dumps(str(d / "data.json")) + ";\n"
          + DRIVER + "\n" + _page_js() + "\n" + REC2
          + "(async ()=>{ try{\n" + 시나리오
          + "\n}catch(e){ console.log('@@@'+JSON.stringify("
            "{터짐:true, 예외:String(e && e.stack || e)})); return; }\n"
            "console.log('@@@'+JSON.stringify(REC2())); })();\n")
    (d / "run.js").write_text(js, encoding="utf-8")
    p = subprocess.run(["node", str(d / "run.js")], capture_output=True,
                       text=True, timeout=120)
    out = p.stdout
    if "@@@" not in out:
        return {"터짐": True, "stderr": (p.stderr or "")[-1500:],
                "stdout": out[-800:]}
    return json.loads(out.split("@@@")[-1].strip())


#: 시나리오 --- 페이지를 띄우고, 색·도형을 센 뒤 결과를 낸다.
def scenario(run_id: str, 지시: str = "") -> str:
    return f"""
STATE.sel = {json.dumps(run_id)};
{지시}
"""


#: 무엇을 셌나 --- 🔴 **도형과 글자를 실제로 센다**(200 을 성공으로 안 읽는다).
REC2 = """
function REC2(){
  const bars = REC.bars.filter(b=>b.w>2);
  const cols = {}; bars.forEach(b=> cols[b.c]=(cols[b.c]||0)+1);
  const D = document.querySelector("#detail") || new Node("div");
  const 글 = findAll(D).map(n=>n._text).filter(Boolean);
  return {
    "arc(뉴런 점)": REC.arc,
    "stroke(선)": REC.stroke,
    "bezier(곡선 화살표)": REC.bezier,
    "fillRect(막대)": REC.fillRect,
    "박스 채움(fill)": REC.fill,
    "글자 수": REC.fillText.length,
    "🔴 상태 막대 색 가짓수": Object.keys(cols).length,
    "상태 막대 색": Object.keys(cols).sort(),
    "「못 잼」 글자": REC.fillText.filter(t=>String(t).indexOf("못 잼")>=0).length,
    "「N×」 글자": REC.fillText.filter(t=>/[0-9]+×/.test(String(t))).length,
    "카드 수": D.children.length,
    "화면 글(요약)": 글.filter(t=>/개 중|접었다|못 잼|그린 박스|자른|잘림/.test(t))
                  .slice(0,12),
  };
}
"""


def main(rid: str = "") -> int:
    sys.path.insert(0, str(ROOT))
    from trainlog import list_runs
    rows = list_runs()["run"]
    if not rid:
        cand = [r for r in rows if (r.get("노드 지표 줄 수") or 0) > 0]
        rid = (cand or rows)[0]["run_id"]
    snap = snapshot(rid)
    단계 = snap["단계"]
    본 = {}
    본["① 접은 채로"] = run_js(snap, scenario(rid, "await loadDetail();"))
    본["② 전부 펼쳐서"] = run_js(snap, scenario(
        rid, "STATE.fold=false; await loadDetail();"))
    if snap["접힌 대표"]:
        본["③ 한 자리만 눌러 펼쳐서"] = run_js(snap, scenario(
            rid, f"STATE.expand=[{json.dumps(snap['접힌 대표'][0])}];"
                 " await loadDetail();"))
    if 단계:
        본["④ 첫 step 의 상태"] = run_js(snap, scenario(
            rid, f"STATE.step={json.dumps(단계[0])}; await loadDetail();"))
    #: 🔴 **곡선 눈금을 옮기면 색이 정말 바뀌나** --- 색 목록을 대조한다.
    판정 = {}
    a = 본.get("① 접은 채로", {})
    b = 본.get("④ 첫 step 의 상태", {})
    if a.get("상태 막대 색") and b.get("상태 막대 색"):
        s1, s2 = set(a["상태 막대 색"]), set(b["상태 막대 색"])
        판정["④ step 을 옮기면 색이 바뀌나"] = {
            "마지막 step 색 수": len(s1), "첫 step 색 수": len(s2),
            "달라진 색 수": len(s1 ^ s2),
            "바뀌었나": bool(s1 ^ s2),
            "🔴 뜻": ("같은 그래프에 **다른 step 의 grad 를 얹으니 색이 달라졌다** "
                   "--- 상태가 진짜로 얹혀 있다는 뜻이다"
                   if s1 ^ s2 else "🔴 색이 하나도 안 바뀌었다 --- 얹히지 않았다")}
    c1 = 본.get("① 접은 채로", {}).get("박스 채움(fill)")
    c2 = 본.get("② 전부 펼쳐서", {}).get("박스 채움(fill)")
    if c1 and c2:
        판정["② N× 가 펴지나"] = {
            "접었을 때 박스 채움": c1, "폈을 때 박스 채움": c2,
            "펴졌나": c2 > c1}
    print(json.dumps({"run_id": rid, "단계 수": len(단계),
                      "접힌 대표": snap["접힌 대표"],
                      "🔴 판정": 판정, "본 것": 본},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
