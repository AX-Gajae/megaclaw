"""경계 이동의 **가능성 계수** — 실험이 아니다. 학습/유보 행 수만 센다."""
import json
import numpy as np
from lab import loop as L

def data():
    e = {**L._trendsub(zero_is_data=True), **L._calsub(), **L._wikisub(),
         **L._tag(), **L._fund(), **L._rawsub(), **L._grp(), **L._gen()}
    from lab import visitoraxes as V
    e.update(V.build(axes=("vis_out",)))
    return L._idol(lambda: e, mode="cut", with_wiki=True, with_trend=True,
                   wide_post=True, wide_pop="grades")

d = data()
rows = {}
for dom in d.dom:
    r = {}
    for T in (2025.0, 2026.0, 2026.5):
        tr = int(d.rows(dom, post=False, labeled=True, T=T).sum())
        ho = int(d.rows(dom, post=True, labeled=True, T=T).sum())
        r[str(T)] = (tr, ho)
    rows[dom] = r
print(json.dumps(rows, ensure_ascii=False, indent=1))
for T in (2025.0, 2026.0, 2026.5):
    w = d.weights(T=T)
    print(f"\nT={T}: 판에 남는 도메인 {len(w)}개 · 채점 유보 {sum(w.values())}행")
    print("  ", json.dumps(w, ensure_ascii=False))
