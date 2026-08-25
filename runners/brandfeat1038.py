# 1038-다 — 「누가 여는가」를 concept 텍스트에서 LLM 으로 뽑는다 (결과 누수 없음: 개최 전 정보만)
import json,glob,os,urllib.request,time,sys
OUT="/Users/ax/wm_harvest/foundation"
SYS=("팝업스토어 기획 설명을 읽고 «개최 전에 알 수 있는 것»만 판단한다. JSON 한 줄. 설명 금지.\n"
 '{"인지도":1-5,"유명IP결합":true/false,"카테고리":"패션|식음료|캐릭터|게임|뷰티|생활|엔터|기타","체험형":true/false}\n'
 "· 인지도 = 이 브랜드/IP 를 «일반 대중»이 아는 정도. 1=전혀 모름(신생 소브랜드) 3=업계에선 앎 5=전국민이 앎.\n"
 "· 유명IP결합 = 널리 알려진 캐릭터·작품·연예인과의 콜라보인가.\n"
 "· 방문자 수를 «추측하지 마라». 설명에 있는 것만 본다.")
recs=[]
for p in sorted(glob.glob('data/records/*.json')):
    try: d=json.load(open(p,encoding='utf-8'))
    except Exception: continue
    o=d.get('outcome') or {}; t=o.get('totals') or {}
    dl=[r for r in (o.get('daily') or []) if isinstance(r,dict) and r.get('visitors') is not None]
    per=(d.get('conditions') or {}).get('period') or {}
    if dl: v=sum(float(r['visitors']) for r in dl); days=len(dl)
    elif t.get('visitors') is not None: v=float(t['visitors']); days=per.get('days')
    else: continue
    if not v or not days or v<=0: continue
    iv=d.get('intervention') or {}
    recs.append((os.path.basename(p)[:-5], (iv.get('concept') or '')[:900],
                 iv.get('brand_name') or '', ' '.join(iv.get('staging_tags') or [])))
done={}
fp=f"{OUT}/brandfeat1038.jsonl"
if os.path.exists(fp):
    for l in open(fp,encoding='utf-8'):
        try: d=json.loads(l); done[d['code']]=d
        except Exception: pass
todo=[r for r in recs if r[0] not in done]
sys.stderr.write(f"대상 {len(recs)} · 남은 {len(todo)}\n")
t0=time.time()
for i,(code,concept,brand,tags) in enumerate(todo):
    p=f"브랜드: {brand}\n기획태그: {tags}\n설명: {concept}"
    body={"model":"qwen3.6:35b-a3b","prompt":p,"system":SYS,"stream":False,"think":False,
          "options":{"temperature":0.0,"num_predict":120}}
    try:
        req=urllib.request.Request("http://localhost:11434/api/generate",
            data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=300) as r: resp=json.loads(r.read()).get("response","")
        s=resp[resp.find("{"):resp.rfind("}")+1]
        j=json.loads(s) if s else {}
    except Exception as e:
        j={"오류":str(e)[:60]}
    j['code']=code
    with open(fp,"a",encoding="utf-8") as w: w.write(json.dumps(j,ensure_ascii=False)+"\n")
    if (i+1)%20==0: sys.stderr.write(f"  {i+1}/{len(todo)} · {time.time()-t0:.0f}s\n"); sys.stderr.flush()
print(json.dumps({"완료":len(todo),"초":round(time.time()-t0,1)},ensure_ascii=False))
