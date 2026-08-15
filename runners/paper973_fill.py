# -*- coding: utf-8 -*-
import json, re
from pathlib import Path
LED = json.loads(Path('/Users/ax/wm_harvest/973/out973_ledger.json').read_text(encoding='utf-8'))
SUB = LED["🔴🔴🔴 §T 치환표 --- **판정문·카드·논문은 이 값만 쓴다**"]
B = json.loads(Path('/Users/ax/wm_harvest/973/out973_build.json').read_text(encoding='utf-8'))
G = B["🔴 게이트 G1~G8"]
M = {
 "ROWS": SUB["🔴🔴 HPLT 삼중쌍 행"],
 "DOMS": SUB["🔴🔴 그 행이 덮는 도메인"],
 "SHARE_B": SUB["최대 도메인 점유율 before"],
 "SHARE_A": SUB["🔴🔴 최대 도메인 점유율 after"],
 "SHARDS": SUB["읽은 shard"],
 "SHARDS_ALL": SUB["분모: HPLT shard 전량"],
 "DOCS": SUB["읽은 HPLT 문서"],
 "G4DROP": SUB["도박 게이트에서 떨어진 문서"],
 "G6DROP": SUB["URL 정규화 중복으로 떨어진 문서"],
 "G7DROP": SUB["본문 중복으로 떨어진 문서"],
 "G8": SUB["개체를 언급한 문서"],
 "G9DROP": SUB["위키 창을 못 덮어 떨어진 짝"],
 "ROWS_B": SUB["코퍼스 행 before"], "ROWS_A": SUB["코퍼스 행 after"],
 "DOMS_B": SUB["코퍼스 도메인 before"], "DOMS_A": SUB["코퍼스 도메인 after"],
 "LOSO_DOM": SUB["leave-one-source-out(도메인 수 Δ)"]["hplt_ko"],
 "LOSO_SHARE": SUB["leave-one-source-out(최대 점유율 Δ)"]["hplt_ko"],
 "TAIL_S": SUB["치④ 작은 꼬리 실측 줄 수"][0],
 "TAIL_L": SUB["치④ 큰 꼬리 실측 줄 수"][0],
 "TAIL_C": SUB["치④ 주석만 갈래 실측 줄 수"][0],
 "SHAKE": SUB["치② 낙하가 흔들린 자리"],
 "COMMON": SUB["일반어 의심 제목"],
}
src = Path('/Users/ax/world_model/paper/steps/973_hpltc3/main.tex.tmpl').read_text(encoding='utf-8')
def fmt(v):
    if isinstance(v, int): return "{:,}".format(v)
    return str(v)
for k, v in M.items():
    src = src.replace("@@%s@@" % k, fmt(v)).replace("@@%s\\_" % k.split("_")[0], "@@%s\\_" % k.split("_")[0])
# 이스케이프된 밑줄 판도 바꾼다
for k, v in M.items():
    src = src.replace("@@%s@@" % k.replace("_", "\\_"), fmt(v))
left = re.findall(r"@@[A-Z_\\]+@@", src)
assert not left, left
Path('/Users/ax/world_model/paper/steps/973_hpltc3/main.tex').write_text(src, encoding='utf-8')
print("채운 자리", len(M), "· 남은 자리", len(left))
