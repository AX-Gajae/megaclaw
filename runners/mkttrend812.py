"""노트 812 — 시장팝업 검색 트렌드 수집(데이터랩 · 앵커 정규화 · 오픈 이전 창).

trend_all.collect 를 그대로 쓰되 SPEC 에 market 갈래만 메모리로 더한다 ---
market 엔티티는 data/market_records/*.json (event_name · period_from) 이라
targets() 를 시장팝업용으로 바꿔 끼운다. 출력 스키마는 기존과 동일.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, "/Users/ax/world_model")
from ingest import trend_all as TA

def market_targets(domain, root="."):
    #: id·오픈일은 판의 원천(market_axes.json) · 이름은 market_records 조인
    ax=json.loads(Path(root,"data/state/market_axes.json").read_text())
    out=[]
    for rid, v in ax.items():
        op=str(v.get("period_from") or "")[:10]
        q=Path(root,"data/market_records",f"{rid}.json")
        if not q.exists() or len(op)!=10:
            continue
        try: d=json.loads(q.read_text())
        except Exception: continue
        kw=TA.clean_kw(d.get("event_name"))
        if kw:
            out.append({"id": rid, "kw": kw, "open": op})
    return out

TA.targets_orig = TA.targets
TA.targets = lambda domain, root=".": (market_targets(domain, root)
                                        if domain=="market" else TA.targets_orig(domain, root))
r = TA.collect("market")
print(json.dumps(r, ensure_ascii=False)[:400])
