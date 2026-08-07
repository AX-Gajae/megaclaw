"""노트 684 — 집 밖 짝 채점기가 기록된 기준선을 재현하나. **셋을 다 잰다.**"""
import json
from lab import pairs as P
from lab.sideaudit import champion_data

print(json.dumps({"짝 행수(시험 ①)": P.counts()}, ensure_ascii=False, indent=1), flush=True)
data = champion_data()
print(json.dumps({"판 도메인": sorted(data.dom),
                  "만화 열 수": len(data.names.get("만화") or []),
                  "모바일 열 수": len(data.names.get("모바일") or [])},
                 ensure_ascii=False), flush=True)
out = {}
for nm in ("KR 만화", "비게임 앱", "CN 만화"):
    try:
        out[nm] = P.score(nm, data=data, seeds=(0, 1, 2))
    except Exception as e:
        out[nm] = {"오류": f"{type(e).__name__}: {e}"}
    print(json.dumps({nm: out[nm]}, ensure_ascii=False, indent=1), flush=True)
ok = [v for v in out.values() if isinstance(v.get("차"), float)]
print(json.dumps({
    "**시험 ② 종합**": {k: v.get("**시험 ② 판정**") for k, v in out.items()},
    "맞은 수": sum(1 for v in ok if abs(v["차"]) <= 0.02), "잰 수": len(ok),
    "문턱": "|차| ≤ 0.02"}, ensure_ascii=False, indent=1), flush=True)
