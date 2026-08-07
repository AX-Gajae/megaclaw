"""전향 봉인 --- **이 실험실에 없던 것 하나.** 노트 694.

지금까지 모든 숫자가 T 유보 백테스트다. 전향 기록이 **0건**이고,
`serve/capability.py` 가 그것을 금지 꼴로 박아 뒀다("지금까지 ○○% 적중").
백테스트만 들고 협력 자리에 가면 첫 질문에서 걸린다.

**그래서 오늘 봉인한다.** 아직 각색 안 된 만화에 선별 확률을 적어 두고,
각색 발표가 나면 채점된다. 봉인은 되돌릴 수 없어야 값이 있으므로 규율이 넷이다.

    ① 모형 지문을 같이 적는다   특징 목록 · 하이퍼파라미터 · 학습 행수 ·
                                `serve/ipmodel.py` 의 sha256
    ② 오늘 날짜를 하드 컷오프로  봉인 시각과 자료 스냅샷 크기
    ③ 파일을 다시 쓰지 않는다   같은 날 두 번 부르면 **예외**를 낸다
    ④ 채점 규칙을 봉인 때 적는다 뒤에 정하면 그것이 체리피킹이다

④가 가장 중요하다. 노트 133 이 ``첫 양성을 그냥 채택하지 않는다''를 적었고
그보다 앞선 실패가 **결과를 보고 기준을 정한 것**이었다. 채점 규칙을 봉인
파일 안에 두면 다음 세션이 그것을 못 바꾼다.

    python3 -m serve.seal            # 봉인한다
    python3 -m serve.seal --score    # 봉인된 것을 지금 자료로 채점한다
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from pathlib import Path

FWD = Path("cycle_log/forward/ip")
TOP = 100          # 상위 몇을 판정 표본으로 볼 것인가 --- **봉인 때 정한다**
WINDOW_M = 24      # 몇 개월 창으로 볼 것인가 --- **봉인 때 정한다**

RULE = {
    "양성 정의": "`data/state/wanime_records.json` 에 `source=='MANGA'` 이고 "
              "제목 정규화가 이 만화와 같은 레코드가 **새로 나타나면** 양성. "
              "정규화는 `serve.ipmodel._norm` 을 쓴다(같은 함수여야 한다).",
    "판정 표본": f"봉인 당시 선별 확률 상위 {TOP}건",
    "창": f"봉인일로부터 {WINDOW_M}개월",
    "판정": f"상위 {TOP}건 중 창 안 양성이 **3건 이하면 AUC 0.9408 이 시간을 "
          "못 건넌 것**이고 배급물의 ① 단을 내린다. "
          "사전등록 예측은 **8~20건**이다(노트 694).",
    "대조": "같은 창에서 **하위 100건**의 양성 수도 센다. 상위와 하위가 같으면 "
          "순위가 시간에 안 옮겨간 것이다 --- 절대 수만 보면 기저율 변화와 "
          "구분이 안 된다.",
    "금지": "봉인 파일을 고치지 않는다. 모형을 바꿨으면 **새 봉인**을 만들고 "
          "둘을 따로 채점한다(노트 579·580: 어긋나면 새 자로 취급한다).",
}


def _fingerprint() -> dict:
    """모형 지문 --- 나중에 ``그때 무슨 모형이었나''를 답할 수 있게."""
    from . import ipmodel
    src = Path(ipmodel.__file__).read_bytes()
    mg, ad, pr = ipmodel.pairs()
    return {"코드 sha256": hashlib.sha256(src).hexdigest()[:16],
            "특징": list(ipmodel.SAFE),
            "버린 특징": ["화수", "권수", "완결", "인기", "즐겨찾기", "점수"],
            "시간 분할": f"만화 시작연도 >= {ipmodel.T_SPLIT}",
            "자료 스냅샷": {"만화 레코드": len(mg), "각색 제목": len(ad),
                       "각색 짝": len(pr)},
            "하이퍼": "HistGradientBoostingClassifier(max_iter=200, max_depth=4, "
                   "learning_rate=0.06, random_state=0)"}


def seal(day: str | None = None) -> dict:
    """아직 각색 안 된 유보 만화에 선별 확률을 봉인한다."""
    import numpy as np
    from . import ipmodel

    d = day or date.today().isoformat()
    FWD.mkdir(parents=True, exist_ok=True)
    out = FWD / f"seal_{d}.json"
    if out.exists():
        raise FileExistsError(
            f"{out} 이 이미 있다 --- **봉인은 다시 쓰지 않는다**(규율 ③). "
            "모형을 바꿨으면 새 날짜로 봉인하고 둘을 따로 채점한다")

    rp = ipmodel.report()
    s1 = rp["_s1"]
    mg, ad, _ = ipmodel.pairs()
    rows = []
    for r in mg:
        v, t = ipmodel.feats(r, dirty=False)
        if not np.isfinite(t) or t < ipmodel.T_SPLIT:
            continue
        n = ipmodel._norm(r.get("title"))
        if n in ad:
            continue                          # 이미 각색됐다 --- 봉인 대상 아님
        p = float(s1["_m"].predict_proba(
            v[list(ipmodel.SAFE_COLS)].reshape(1, -1))[0, 1])
        rows.append({"record_id": r.get("record_id"), "title": r.get("title"),
                     "정규화": n, "시작연도": int(t), "확률": round(p, 5)})
    rows.sort(key=lambda x: -x["확률"])

    # **배선 검사** --- 봉인 행수가 유보 비양성 수와 맞나
    expect = s1["유보"] - s1["유보양성"]
    doc = {"봉인일": d,
           "봉인 시각": datetime.now().isoformat(timespec="seconds"),
           "행": len(rows), "기대 행": expect, "배선일치": len(rows) == expect,
           "봉인 당시 유보 성능": {k: v for k, v in s1.items()
                          if not k.startswith("_") and k != "캘리브레이션"},
           "모형 지문": _fingerprint(),
           "채점 규칙": RULE,
           "예보": rows}
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1))
    return {"봉인": str(out), "행": len(rows), "기대": expect,
            "배선일치": doc["배선일치"],
            "상위5": [(r["title"], r["확률"]) for r in rows[:5]],
            "하위3": [(r["title"], r["확률"]) for r in rows[-3:]]}


def score(day: str | None = None) -> dict:
    """봉인된 것을 **지금 자료로** 채점한다. 규칙은 봉인 파일 안의 것을 쓴다."""
    from . import ipmodel
    files = sorted(FWD.glob("seal_*.json"))
    if not files:
        return {"오류": "봉인이 없다 --- `python3 -m serve.seal` 을 먼저"}
    f = (FWD / f"seal_{day}.json") if day else files[-1]
    doc = json.loads(f.read_text())
    _, ad, _ = ipmodel.pairs()
    top = doc["예보"][:TOP]
    bot = doc["예보"][-TOP:]
    hit_t = [r["title"] for r in top if r["정규화"] in ad]
    hit_b = [r["title"] for r in bot if r["정규화"] in ad]
    return {"봉인": f.name, "봉인일": doc["봉인일"],
            "경과일": (date.today() - date.fromisoformat(doc["봉인일"])).days,
            f"상위{TOP} 양성": len(hit_t), f"하위{TOP} 양성": len(hit_b),
            "상위 맞은 것": hit_t[:10],
            "판정": doc["채점 규칙"]["판정"],
            "말": ("**아직 아무것도 안 말한다** --- 봉인 당일이거나 창이 안 찼다. "
                 f"창은 {WINDOW_M}개월이다"
                 if (date.today() - date.fromisoformat(doc["봉인일"])).days < 30
                 else "창이 차기 시작했다")}


if __name__ == "__main__":
    import sys
    if "--score" in sys.argv:
        print(json.dumps(score(), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(seal(), ensure_ascii=False, indent=1))
