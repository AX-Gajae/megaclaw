"""노트 674 — 아이돌에 장소가 붙나. **판을 안 돈다.** 기존 매처만 쓴다."""
import json, collections
from pathlib import Path
from ingest.visitors import sgg_index, hood_sgg, city_sgg

RAW = Path("data/idol_raw")
# 자유 텍스트에서 장소를 담을 수 있는 필드 — **키워드가 아니라 전수에서 골랐다**
TXT = ("showcase_scale", "notes", "pre_debut_note", "chodong_note",
       "chodong_source_quote", "showcase_note", "debut_note")

def rows():
    """group_name → {필드: 텍스트}. 여러 wave 를 합친다."""
    out = {}
    for p in sorted(RAW.glob("*.jsonl")):
        for ln in p.open():
            try: d = json.loads(ln)
            except Exception: continue
            g = d.get("group_name")
            if not g: continue
            cur = out.setdefault(g, {"date": None, "txt": {}})
            cur["date"] = cur["date"] or d.get("debut_date")
            for f in TXT:
                v = d.get(f)
                if isinstance(v, str) and v.strip():
                    cur["txt"][f] = (cur["txt"].get(f, "") + " " + v)[:4000]
    return out

def match(txt: str, idx: dict):
    """(시군구코드, 경로). 팝업과 **같은 함수**를 쓴다."""
    for (_sd, nm), cd in idx.items():
        if nm and len(nm) >= 2 and nm in txt:
            return cd, "시군구이름"
    c = hood_sgg(txt, "서울" if "서울" in txt else None, idx)
    if c: return c, "동이름"
    c = city_sgg(txt, idx)
    if c: return c, "city만"
    return None, "없음"

idx = sgg_index()
R = rows()
have_txt = collections.Counter(); path = collections.Counter()
n_place = 0; n_date = 0; both = 0; per_field = collections.Counter()
examples = []
for g, v in R.items():
    if v["date"]: n_date += 1
    for f in v["txt"]: have_txt[f] += 1
    code = None; how = "없음"; src = None
    for f in TXT:                     # 우선순위: showcase_scale 먼저
        t = v["txt"].get(f)
        if not t: continue
        code, how = match(t, idx)
        if code: src = f; break
    path[how] += 1
    if code:
        n_place += 1; per_field[src] += 1
        if v["date"]: both += 1
        if len(examples) < 8:
            examples.append((g, src, how, code))

N = len(R)
print(json.dumps({
    "그룹 수": N,
    "장소 붙음": n_place, "**덮음**": round(n_place / max(N,1), 3),
    "데뷔일 있음": n_date,
    "장소+날짜 둘 다": both, "**둘 다 덮음**": round(both / max(N,1), 3),
    "경로 분포": dict(path.most_common()),
    "붙인 필드": dict(per_field.most_common()),
    "필드 보유": dict(have_txt.most_common()),
}, ensure_ascii=False, indent=1))
print("\n표본:")
for e in examples: print("  ", e)
