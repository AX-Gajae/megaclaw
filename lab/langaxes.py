"""제목이 한글인가 --- 노트 $565 \\cdot 566$ 시험용 축. **기각됐다.**

**결론부터**: 짝 씨앗 $40$ 에서 비게임 앱이 $-0.0028$ 로 $0$ 밖 음수가 되어
관문 ③ 을 못 넘고, 노트 $426$ 거울(집 밖 짝 둘의 부호)도 미달이다. 검사
셋을 통과한 모바일의 이득은 씨앗 $12$ 의 $+0.0021(10/12)$ 에서 $40$ 의
$+0.0007(23/40)$ 으로 **사라졌다** --- 노트 $518$ 이 또 값을 했다.
그리고 이득이 **모바일 $\\cdot$ 게임 둘 다 있을 때만** 나는데(한쪽만 주면
판이 $-0.005$), 그것은 정보가 아니라 **도메인 지시자를 피하는 것**뿐이다.
챔피언에 안 붙인다.

노트 $563$ 이 게임에서 ``검색 관측-$0$ 은 전부 한글 제목''임을 찾다가
따라 나온 것이다. 제목 언어는 \\emph{작품의 성질}이고 출시 시점에 확정되므로
사전이며, 라벨을 한 번도 안 본다.

**뜻은 도메인을 가로질러 같고**(``제목에 한글이 있다'') **라벨과의 관계만
도메인마다 다르다** --- 노트 $544$ 의 조항(공유 축의 뜻은 도메인을 가로질러
같아야 한다)에 안 걸린다. 트리는 도메인 원핫과 함께 쓰므로 부호가 갈리는
것은 문제가 아니다.

**변하는 곳이 둘뿐이다.**

    모바일   한글 53%   학습 rho **+0.4362** · 유보 +0.2926
    게임     한글 33%   학습 rho $-0.0489$ · 부호 $[+,+,-,-,-]$
    나머지 아홉은 거의 상수(웹툰 $\\cdot$ 애니 $\\cdot$ 펀딩 $\\cdot$ 도서 99%
    한글, 만화 $\\cdot$ 세계애니 0%)

``tagaxes`` 채택 검사 셋(노트 $239 \\cdot 256 \\cdot 345)$:

    ①  연도 통제 학습 |rho| >= 0.10   모바일 **+0.4362** 통과 · 게임 실패
    ②  시간 다섯 조각 부호 일치        모바일 $[+,+,+,+,+]$ 통과 · 게임 실패
    ③  기존 축 최대 겹침 < 0.39        모바일 **0.371**(tag_c3_모바일) 통과

**게임은 못 넘는다** --- 부호가 갈리고 상관이 문턱 아래다. 게임의 언어 효과는
검색 마스크를 통해 이미 들어와 있고(노트 $564$ 가 그것을 고쳤다) 남은 직접
효과는 작다.

**왜 상수에 가까운 도메인이 많은데 넣나.** 마스크는 늘 $1$ 이다(제목은 언제나
있다) --- 그래서 **결측 무늬가 도메인 표지가 되지 않는다**(노트 $540$ 이 닫은
것은 *그 도메인에만 있는* 열이었다). 값이 도메인 안에서 상수면 트리가 거기서
안 쪼갤 뿐이다.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

D = Path("data/state")
HAN = re.compile(r"[가-힣]")

# 도메인 → (레코드 파일, 제목 칸). **칸 이름을 틀리면 조용히 상수가 된다** ---
# 처음에 모바일을 ``name`` 으로 읽어 제목 종류가 1 가지로 나왔고, 그때는
# ``모바일은 안 갈린다''로 읽힐 뻔했다. 실제 칸은 ``title`` 이고 +0.4362 다.
SRC = {"웹툰": ("webtoon_records.json", "title"),
       "애니": ("anime_records.json", "title"),
       "세계애니": ("wanime_records.json", "title"),
       "모바일": ("mobile_records.json", "title"),
       "만화": ("manga_records.json", "title"),
       "게임": ("game_records.json", "name"),
       "펀딩": ("funding_records.json", "title"),
       "도서": ("book_records.json", "title")}

MIN_VARY = 0.02      # 도메인 안에서 이만큼은 갈려야 축을 붙인다


def build(root: str = ".") -> dict:
    """{"lang_ko": {도메인: (값, 표시자)}} --- 값은 0/1, 표시자는 늘 1."""
    from .trendaxes import _ids
    ids_all = _ids()
    col = {}
    for dom, (rf, tf) in SRC.items():
        p = Path(root) / D / rf
        if not p.exists() or dom not in ids_all:
            continue
        rec = json.loads(p.read_text())
        by = {v["record_id"]: v for v in rec.values()
              if isinstance(v, dict) and "record_id" in v}
        ids = ids_all[dom]
        t = [str((by.get(i) or {}).get(tf) or "") for i in ids]
        if len(set(t)) < 3:
            # 칸 이름이 틀렸을 때 조용히 상수가 되는 것을 막는다.
            raise ValueError(f"langaxes: {dom} 제목 칸 {tf} 이 {len(set(t))}가지")
        v = np.array([1.0 if HAN.search(x) else 0.0 for x in t])
        if not (MIN_VARY < v.mean() < 1 - MIN_VARY):
            continue          # 거의 상수면 안 붙인다
        col[dom] = (v, np.ones(len(v)))
    return {"lang_ko": col} if col else {}
