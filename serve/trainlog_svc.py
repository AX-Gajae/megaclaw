"""L6 창구 --- **학습 기록 뷰어의 서비스 층.** 노트 912 팔 ㅇ.

`trainlog/` 가 *기록하는 쪽*이라면 여기는 *보여 주는 쪽*이다. `serve/web.py` 의
`/api/trainlog/*` 가 이 파일만 부르고, `serve/static/trainlog.html` 이 그 JSON 을
그린다.

# 🔴 이 창구의 자

    **이 페이지는 모형 정량 주장을 내지 않는다.**

이 저장소의 등록 규율은 *자 없는 능력은 등록 불가* 다(`serve/registry.py` 규율 ②).
관측 창구에는 ρ 같은 성능 수치가 없다 --- 그러면 자가 없으니 등록도 못 한다.
그래서 자를 **주장하지 않음** 쪽에서 세운다. 창구가 내는 모든 응답이

  ① `serve/layers.py:gate()` 의 **금지 꼴 다섯**을 지나고 (걸리면 **내용을 안 보낸다**)
  ② 지표가 없으면 곡선을 **0개**로 낸다 (지어낸 선이 0개)

는 것이 이 창구의 자이고, `serve/test_trainlog.py` 가 **미끼와 음성 대조로**
그것을 잰다(노트 676 --- "통과는 아무것도 말하지 않는다").

# 🔴 이 창구가 안 하는 것

- 학습을 돌리지 않는다. **읽기만** 한다.
- 모형을 적합하지 않는다. 판 ρ 를 계산하지 않는다.
- 없는 점을 만들지 않는다. 보간·평활·외삽이 한 줄도 없다.
"""
from __future__ import annotations

import json

from trainlog import store
from trainlog.spec import SPEC, SPEC_VERSION

from . import layers

#: 🔴 등록소에 걸리는 이 창구의 자 --- **주장하지 않음**이 자다.
RULER = ("이 페이지는 **모형 정량 주장을 내지 않는다** --- 학습 run 이 스스로 적은 "
         "것을 그대로 읽어 보여 줄 뿐이고, 모든 응답이 금지 꼴 게이트 다섯을 지난다")

#: 뉴런 그림에서 층당 기본 최대 점 수. 넘으면 **자르고 잘랐다고 적는다.**
DEFAULT_MAX_NEURONS = 32
MAX_NEURONS_CAP = 256


def _gate(payload) -> list:
    """응답을 **금지 꼴 다섯**에 건다.

    `layers.gate()` 는 조립물(다섯 절) 꼴을 기대하므로 여기서 **한 절짜리 조립물**로
    싸서 넣는다. 상태를 `측정됨` 으로 두는 이유: `_g_bare_abs` 가 `측정됨` 인 절만
    보기 때문이다 --- 상태를 낮춰 두면 게이트 하나가 **조용히 잠든다**.
    """
    return layers.gate({"이벤트": {"도메인": None},
                        "절": [{"절": "②결과", "상태": "측정됨",
                               "값": payload, "자": [RULER]}]})


def gated(payload: dict, 무엇: str) -> dict:
    """게이트를 지난 응답만 내보낸다. **걸리면 내용을 안 보낸다.**

    조용히 고치지 않는다(노트 133) --- 무엇에 걸렸는지 그대로 실어 보낸다.
    """
    hit = _gate(payload)
    if hit:
        return {"차단됨": True, "무엇": 무엇,
                "금지 꼴 게이트": hit,
                "말": "🔴 **금지 꼴이 걸려 내용을 안 보냈다.** 이 창구는 관측 창구이지 "
                     "모형 주장 창구가 아니다 --- 걸린 run 의 기록에 우리 모형의 "
                     "정량 주장으로 읽힐 문장이 들어 있다",
                "어디를 고치나": "그 run 의 `manifest.json` / `metrics.jsonl` 의 "
                          "이름·메모를 고쳐 다시 기록해라(이 창구는 파일을 안 고친다)"}
    return {**payload, "금지 꼴 게이트": "걸린 것 없음"}


def _head() -> dict:
    return {"창구": "trainlog", "규격": SPEC, "규격 판": SPEC_VERSION,
            "층": "L6", "떠받치는 출력": ["메타"],
            "🔴 이 창구의 자": RULER}


def runs() -> dict:
    """run 목록. **행마다 따로** 게이트를 건다 --- 한 run 이 나머지를 가리지 않게."""
    L = store.list_runs()
    out, 차단 = [], 0
    for row in L.get("run", []):
        hit = _gate(row)
        if hit:
            차단 += 1
            out.append({"run_id": row.get("run_id"), "차단됨": True,
                        "금지 꼴 게이트": hit,
                        "말": "🔴 이 run 의 기록이 금지 꼴에 걸려 내용을 안 보낸다"})
        else:
            out.append(row)
    return {**_head(), "상태": L.get("상태"), "경로": L.get("경로"),
            "왜": L.get("왜"),
            "run 수": len(out),
            "데모 수": sum(1 for r in L.get("run", []) if r.get("데모인가")),
            "진짜 run 수": sum(1 for r in L.get("run", [])
                          if not r.get("데모인가")),
            "차단된 run 수": 차단,
            "run": out, "🔴 단서": L.get("🔴 단서")}


def detail(run_id: str, max_neurons: int = DEFAULT_MAX_NEURONS) -> dict:
    """run 하나 --- manifest · 곡선 · 아키텍처 · 뉴런 그림을 **한 번에** 낸다."""
    try:
        m = store.read_manifest(run_id)
        cur = store.read_metrics(run_id)
        arch = store.read_arch(run_id)
        neu = store.neurons(run_id, max_per_layer=_cap(max_neurons))
    except ValueError as e:                    # 경로 탈출 등
        return {**_head(), "오류": str(e)}
    payload = {
        "run_id": run_id,
        "manifest": m,
        "곡선": cur,
        "아키텍처": _slim(arch),
        "뉴런": neu,
        #: 🔴 세는 것은 **이 창구**다. manifest 가 적은 수를 그대로 옮기지 않는다.
        "🔴 이 창구가 직접 센 것": {
            "곡선 수": cur.get("곡선 수", 0),
            "곡선 점 수": cur.get("점 수", 0),
            "아키텍처 층 수": len(arch.get("층") or []),
            "아키텍처 간선 수": len(arch.get("간선") or []),
            "뉴런 그림 점 수": sum(int(L.get("그린 뉴런") or 0)
                            for L in neu.get("층", [])),
            "뉴런 전체 수(자르기 전)": sum(int(L.get("전체 뉴런") or 0)
                                for L in neu.get("층", [])),
            "잘린 층 수": len(neu.get("잘린 층") or []),
        },
    }
    return {**_head(), **gated(payload, f"run `{run_id}` 의 상세")}


def _cap(n) -> int:
    try:
        n = int(n)
    except Exception:
        n = DEFAULT_MAX_NEURONS
    return max(1, min(MAX_NEURONS_CAP, n))


def _slim(a: dict) -> dict:
    """아키텍처에서 **가중치 값 덩어리를 뺀** 판본 --- 층 표가 쓸 것만 남긴다.

    값은 `뉴런` 쪽 `간선.세기` 로 이미 나가므로 두 번 실어 보낼 이유가 없다
    (한 run 의 응답이 수 MB 가 되면 화면이 안 뜬다). **뺐다는 사실을 적는다.**
    """
    if not a.get("읽음"):
        return a
    층 = []
    for L in a.get("층") or []:
        w = dict(L.get("가중치") or {})
        w.pop("값", None)
        w.pop("행 노름", None)
        층.append({**L, "가중치": {**w, "이 응답에서 뺀 것":
                                "값·행 노름은 크기 때문에 뺐다 --- 세기는 `뉴런.간선.세기` 에 있다"}})
    return {**a, "층": 층}


def neurons(run_id: str, max_neurons: int = DEFAULT_MAX_NEURONS) -> dict:
    try:
        n = store.neurons(run_id, max_per_layer=_cap(max_neurons))
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated(n, f"run `{run_id}` 의 뉴런 그림")}


def metrics(run_id: str) -> dict:
    try:
        c = store.read_metrics(run_id)
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated(c, f"run `{run_id}` 의 곡선")}


# ── 자가검사 --- 🔴 미끼와 음성 대조를 같이 든다(노트 676) ──────────
#: 게이트를 **발화시켜야 하는** 가짜 run 행. 하나라도 안 걸리면 자가 죽은 것이다.
미끼 = [
    {"run_id": "bait-forward", "이름": "우리 모델은 지금까지 82% 적중했습니다",
     "자": None, "미는 출력": ["②결과"]},
    {"run_id": "bait-band", "이름": "이 팝업은 80% 확률로 8천~2만명",
     "자": None, "미는 출력": ["②결과"]},
    {"run_id": "bait-causal", "이름": "제작사를 A 로 바꾸면 매출이 오릅니다",
     "자": None, "미는 출력": ["④개선"]},
]
#: 발화하면 **안 되는** 줄 --- 진짜 run 행과 같은 꼴이다.
음성 = [
    {"run_id": "912-demo-mlp", "이름": "912-demo-mlp", "상태": "끝남",
     "지표 줄 수(읽어 센 것)": 240, "자": "합성 자료 3분류 정확도",
     "미는 출력": ["해당 없음"], "총 파라미터": 1387},
]


def selftest() -> dict:
    """🔴 **이 창구의 자를 실제로 잰다.**

    넷을 센다.
      ① 미끼가 게이트를 **발화시키나** (양성 --- 하나도 안 걸리면 자가 죽었다)
      ② 진짜 run 행이 **조용한가** (음성 --- 다 잡는 게이트는 만점이 아니다)
      ③ 지금 저장된 run 중 게이트에 걸린 것 수 (0 이어야 한다)
      ④ 🔴 **지표가 없는 run 에서 곡선 점이 0 인가** (지어낸 선 0개)
    """
    양성 = [{"미끼": b["이름"][:30], "걸렸나": bool(_gate(b)),
           "무엇": [h["게이트"] for h in _gate(b)]} for b in 미끼]
    음성줄 = [{"줄": n["run_id"], "걸렸나": bool(_gate(n)),
            "무엇": [h["게이트"] for h in _gate(n)]} for n in 음성]
    L = store.list_runs()
    걸린, 점없음, 총점 = [], [], 0
    for row in L.get("run", []):
        rid = row["run_id"]
        if _gate(row):
            걸린.append(rid)
        c = store.read_metrics(rid)
        총점 += int(c.get("점 수") or 0)
        if c.get("상태") in ("없다", "비었다", "못 읽었다"):
            #: 🔴 지표가 없는 run 은 **곡선이 0개여야 한다.** 1개라도 있으면
            #: 그것은 이 창구가 **지어낸 선**이다 --- 즉시 실패다.
            점없음.append({"run_id": rid, "상태": c.get("상태"),
                        "곡선 수": c.get("곡선 수"), "점 수": c.get("점 수")})
    지어냄 = [x for x in 점없음 if (x["곡선 수"] or 0) or (x["점 수"] or 0)]
    통과 = (all(r["걸렸나"] for r in 양성)
          and not any(r["걸렸나"] for r in 음성줄)
          and not 걸린 and not 지어냄)
    return {
        **_head(),
        "통과": 통과,
        "① 미끼에서 발화하나(양성)": 양성,
        "② 진짜 run 행에서 조용한가(음성 대조)": 음성줄,
        "③ 저장된 run 중 게이트에 걸린 것": 걸린 or "없음",
        "④ 지표 없는 run": 점없음 or "없음",
        "🔴 지어낸 곡선": 지어냄 or "0건",
        "센 것": {"run 수": L.get("run 수"), "곡선 점 총수": 총점,
                "지표 없는 run 수": len(점없음)},
        "🔴 무엇을 잰 것인가": "이 창구가 **모형 정량 주장을 안 낸다**는 것과 "
                      "**없는 곡선을 안 그린다**는 것. 통과는 아무것도 말하지 "
                      "않으므로(노트 676) 미끼와 음성 대조를 같이 든다",
    }


def index() -> dict:
    """등록소가 부르는 자리 --- **한 눈에 보이는 요약.**"""
    r = runs()
    return {**_head(),
            "무엇": "등록된 학습 run 의 목록과 이 창구의 자가검사",
            "run 수": r.get("run 수"), "데모 수": r.get("데모 수"),
            "진짜 run 수": r.get("진짜 run 수"),
            "차단된 run 수": r.get("차단된 run 수"),
            "자가검사 통과": selftest()["통과"],
            "화면": "/trainlog",
            "규격 문서": "docs/학습기록규격.md",
            "🔴 이 창구가 안 하는 것": "학습을 돌리지 않는다 · 모형을 적합하지 "
                            "않는다 · 없는 점을 만들지 않는다"}


def main() -> None:
    import sys
    if len(sys.argv) > 1:
        print(json.dumps(detail(sys.argv[1]), ensure_ascii=False, indent=1))
    else:
        print(json.dumps({"목록": runs(), "자가검사": selftest()},
                         ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
