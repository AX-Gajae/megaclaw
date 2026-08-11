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
#: 🔴 판 1.1.0 부터 이것은 **상한**이고, 실제로 몇 개를 그릴지는 층마다
#: `trainlog.store._caps` 가 **화면 높이와 가독 밀도에서 역산**한다.
DEFAULT_MAX_NEURONS = 32
MAX_NEURONS_CAP = 256
#: 뉴런 그림의 기본 세로 픽셀(화면이 제 크기를 보내면 그것을 쓴다).
DEFAULT_PX_HEIGHT = 620
MAX_PX_HEIGHT = 1600


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
        #: 🔴 **읽는 쪽이 직접 잰 생사**를 붙인다 --- manifest 의 「도는 중」은
        #: 쓴 쪽이 적은 것이라 프로세스가 조용히 죽으면 그대로 남는다.
        try:
            row = {**row, "생사": store.liveness(row["run_id"])}
        except Exception as e:
            row = {**row, "생사": {"뱃지": "🔴 못 쟀다",
                                 "말": f"{type(e).__name__}: {e}"}}
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


def detail(run_id: str, max_neurons: int = DEFAULT_MAX_NEURONS,
           px_height: int = DEFAULT_PX_HEIGHT, 접기: bool = True,
           펼침=None, step=None, 지표: str = "grad_norm") -> dict:
    """run 하나 --- manifest · 곡선 · **블록 그림** · 노드 상태 · 뉴런 그림."""
    try:
        m = store.read_manifest(run_id)
        cur = store.read_metrics(run_id)
        arch = store.read_arch(run_id)
        blk = store.graph(run_id, 접기=bool(접기), 펼침=펼침)
        neu = store.neurons(run_id, max_per_layer=_cap(max_neurons),
                            px_height=_px(px_height))
        live = store.liveness(run_id)
        st = store.node_state(run_id, step=step, name=지표)
    except ValueError as e:                    # 경로 탈출 등
        return {**_head(), "오류": str(e)}
    payload = {
        "run_id": run_id,
        "manifest": m,
        "곡선": cur,
        "살아 있나": live,
        "구조만 있나": _structure_only(m, cur),
        "블록 그림": blk,
        #: 🔴 그래프 위에 얹을 **한 시점의 노드 상태**. 없으면 「못 잼」이다.
        "노드 상태": st,
        "아키텍처": _slim(arch),
        "뉴런": neu,
        #: 🔴 세는 것은 **이 창구**다. manifest 가 적은 수를 그대로 옮기지 않는다.
        "🔴 이 창구가 직접 센 것": {
            "곡선 수": cur.get("곡선 수", 0),
            "곡선 점 수": cur.get("점 수", 0),
            "아키텍처 층 수": len(arch.get("층") or []),
            "아키텍처 간선 수": len(arch.get("간선") or []),
            "블록 수(접은 뒤)": len(blk.get("블록") or []),
            "화살표 수(접은 뒤)": len(blk.get("화살표") or []),
            "🔴 건너뛴 화살표(잔차·우회)": (blk.get("요약") or {}).get(
                "🔴 건너뛴 화살표(잔차·우회)"),
            "뉴런 그림 점 수": sum(int(L.get("그린 뉴런") or 0)
                            for L in neu.get("층", [])),
            "뉴런 전체 수(자르기 전)": sum(int(L.get("전체 뉴런") or 0)
                                for L in neu.get("층", [])),
            "잘린 층 수": len(neu.get("잘린 층") or []),
            "뉴런 간선 선 수": sum(int(e.get("그린 선") or 0)
                            for e in neu.get("간선", [])),
        },
    }
    return {**_head(), **gated(payload, f"run `{run_id}` 의 상세")}


def _structure_only(m: dict, cur: dict) -> dict:
    """🔴 **「구조만 있는 run」과 「지표를 못 읽은 run」을 가른다**(조항 59).

    아키텍처만 뽑아 남긴 run(학습을 안 돌린 것)은 지표가 **원래 없다**. 그것을
    「곡선을 못 읽었다」로 보이면 거짓말이다 --- 쓴 쪽이 `학습 돌렸나: false` 로
    적었으면 화면이 **「이 run 은 구조만 있다」**를 적는다.
    """
    돌림 = m.get("학습 돌렸나")
    점 = int(cur.get("점 수") or 0)
    if 돌림 is False and 점 == 0:
        return {"구조만": True,
                "말": "🔴 **이 run 은 구조만 있다 --- 학습을 안 돌렸다.** 곡선이 "
                     "없는 것이 정상이고, 없는 곡선을 그리지 않는다",
                "왜 아나": "쓴 쪽이 `학습 돌렸나: false` 로 **적었다**"}
    if 돌림 is None and 점 == 0:
        return {"구조만": None,
                "말": "🔴 지표가 0점인데 **학습을 돌렸는지 안 돌렸는지 안 적혀 있다** "
                     "--- 「구조만 있다」와 「지표를 못 남겼다」를 이 창구는 못 가른다"
                     "(판 1.0.0 으로 적힌 옛 run 에 그 칸이 없다)",
                "왜 아나": "`학습 돌렸나` 칸이 없다"}
    return {"구조만": False, "말": None, "왜 아나": None}


def _cap(n) -> int:
    try:
        n = int(n)
    except Exception:
        n = DEFAULT_MAX_NEURONS
    return max(1, min(MAX_NEURONS_CAP, n))


def _px(n) -> int:
    try:
        n = int(n)
    except Exception:
        n = DEFAULT_PX_HEIGHT
    return max(240, min(MAX_PX_HEIGHT, n))


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


def neurons(run_id: str, max_neurons: int = DEFAULT_MAX_NEURONS,
            px_height: int = DEFAULT_PX_HEIGHT) -> dict:
    try:
        n = store.neurons(run_id, max_per_layer=_cap(max_neurons),
                          px_height=_px(px_height))
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated(n, f"run `{run_id}` 의 뉴런 그림")}


def blocks(run_id: str, 접기: bool = True, 펼침=None) -> dict:
    """🔴 **블록 다이어그램만** --- 박스와 화살표. 배치는 그래프에서 계산한다."""
    try:
        g = store.graph(run_id, 접기=bool(접기), 펼침=펼침)
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated(g, f"run `{run_id}` 의 블록 그림")}


def nodestate(run_id: str, step=None, 지표: str = "grad_norm") -> dict:
    """🔴 **한 시점의 노드 상태만** --- 곡선의 눈금을 옮길 때 이것만 다시 부른다."""
    try:
        s = store.node_state(run_id, step=step, name=지표)
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated(s, f"run `{run_id}` 의 노드 상태")}


def tail(run_id: str, since_bytes: int = 0) -> dict:
    """🔴 **실시간** --- 새로 붙은 지표 줄만 낸다(전량 재전송 금지).

    화면이 1~2초마다 이것을 때리고 **점을 이어 붙인다**. 없는 점은 안 만든다 ---
    새 줄이 없으면 `새 점` 이 **빈 목록**이고 그것이 정직한 답이다.
    """
    try:
        t = store.tail_metrics(run_id, since_bytes=since_bytes)
        live = store.liveness(run_id)
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated({**t, "살아 있나": live},
                               f"run `{run_id}` 의 새 지표")}


def metrics(run_id: str) -> dict:
    try:
        c = store.read_metrics(run_id)
    except ValueError as e:
        return {**_head(), "오류": str(e)}
    return {**_head(), **gated(c, f"run `{run_id}` 의 곡선")}


# ── 🔴 런 비교 --- run 여럿을 나란히 (판 1.1.0 · 노트 913) ──────────
#: 🔴 **중요도·상관을 내려면 run 이 최소 이만큼 있어야 한다.**
#:
#: 근거: 이 창구가 쓰는 중요도는 **스피어만 상관의 절댓값**이고, 상관은 표본이
#: 작으면 아무 값이나 낸다. n=10 에서 |ρ|≥0.65 여야 5% 수준이 되고(양측),
#: n=5 면 |ρ|=1.0 이어도 5% 를 못 넘긴다 --- 즉 **n<10 이면 어떤 막대도 잡음과
#: 구별이 안 된다**. 그래서 10 을 문턱으로 두고, 못 넘으면 **막대를 안 그리고
#: 「못 잼」이라고 적는다**(조항 60 --- 표본 1~2 로 비율을 말하지 않는다).
MIN_RUNS_FOR_IMPORTANCE = 10
#: 곡선을 겹쳐 그릴 run 수 한도. 넘으면 **자르고 잘랐다고 적는다.**
MAX_OVERLAY_RUNS = 10
#: 한 계열에 실어 보낼 점 수 한도(겹쳐 보기용 --- 솎으면 솎았다고 적는다).
MAX_OVERLAY_POINTS = 300


def _flat_hp(m: dict) -> dict:
    """manifest 의 `하이퍼파라미터` 를 **평평하게** 편다 --- 축은 여기서 자동으로 온다."""
    out = {}
    for k, v in (m.get("하이퍼파라미터") or {}).items():
        if isinstance(v, dict):
            for k2, v2 in v.items():
                out[f"{k}.{k2}"] = v2
        elif isinstance(v, (list, tuple)):
            out[k] = ", ".join(str(x) for x in v)
        else:
            out[k] = v
    if m.get("아키텍처", {}).get("총 파라미터") is not None:
        out["총 파라미터"] = m["아키텍처"]["총 파라미터"]
    if m.get("씨앗") is not None:
        out["씨앗"] = m["씨앗"]
    return out


def _spearman(a: list, b: list):
    """스피어만 --- 동률은 **평균 순위**로(판과 자를 맞춘 규약 · 노트 898)."""
    n = len(a)
    if n < 3:
        return None

    def rank(x):
        idx = sorted(range(n), key=lambda i: x[i])
        r = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and x[idx[j + 1]] == x[idx[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                r[idx[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = sum((ra[i] - ma) ** 2 for i in range(n)) ** 0.5
    db = sum((rb[i] - mb) ** 2 for i in range(n)) ** 0.5
    if da == 0 or db == 0:
        return None
    return num / (da * db)


def compare(target: str = "", limit: int = 200) -> dict:
    """🔴 **런 비교 패널** --- 사이드바 · 겹친 곡선 · 평행좌표 · 중요도 · 으뜸.

    다섯 중 **run 이 모자라서 못 세우는 것**은 자리를 만들고 **「못 잼 + 몇 개
    필요」**를 숫자로 적는다. 반쯤 만든 패널을 그럴듯하게 채우지 않는다.
    """
    L = store.list_runs(limit=limit)
    행, 지표이름 = [], {}
    for row in L.get("run", []):
        rid = row["run_id"]
        m = store.read_manifest(rid)
        cur = store.read_metrics(rid)
        끝값, 계열 = {}, []
        for s in (cur.get("곡선") or []):
            pts = s.get("점") or []
            if not pts:
                continue
            nm = f"{s['split']}/{s['name']}"
            끝값[nm] = pts[-1][1]
            지표이름[nm] = 지표이름.get(nm, 0) + 1
            계열.append({"이름": nm, "점 수": len(pts), "점": pts})
        행.append({
            "run_id": rid, "이름": m.get("이름(원래)") or rid,
            "데모인가": bool(m.get("데모인가")),
            "상태": m.get("상태"), "학습 돌렸나": m.get("학습 돌렸나"),
            "모형 클래스": (m.get("아키텍처") or {}).get("모형 클래스"),
            "자 없음": bool(m.get("자 없음", not m.get("자"))),
            "하이퍼파라미터(평평하게)": _flat_hp(m),
            "최종 지표": 끝값, "계열": 계열,
            "지표 줄 수": row.get("지표 줄 수(읽어 센 것)"),
        })
    후보 = sorted(지표이름, key=lambda k: -지표이름[k])
    tgt = target if target in 지표이름 else (후보[0] if 후보 else None)
    # ── ④ 겹친 곡선 --- 🔴 **몇 개 중 몇 개를 그리는지 적는다**
    있는 = [r for r in 행 if tgt and tgt in r["최종 지표"]]
    겹칠 = 있는[:MAX_OVERLAY_RUNS]
    곡선 = []
    for r in 겹칠:
        s = next((x for x in r["계열"] if x["이름"] == tgt), None)
        if not s:
            continue
        pts, 솎음 = s["점"], None
        if len(pts) > MAX_OVERLAY_POINTS:
            k = (len(pts) + MAX_OVERLAY_POINTS - 1) // MAX_OVERLAY_POINTS
            pts = pts[::k]
            솎음 = f"🔴 {len(s['점']):,}점 중 {len(pts):,}점만 보냈다({k}점마다 하나)"
        곡선.append({"run_id": r["run_id"], "점": pts, "솎음": 솎음,
                     "원래 점 수": s["점 수"]})
    # ── ② 평행좌표 축 --- 🔴 **손으로 안 적는다.** manifest 에서 뽑는다
    축카운트: dict = {}
    for r in 행:
        for k, v in r["하이퍼파라미터(평평하게)"].items():
            if v is None:
                continue
            축카운트.setdefault(k, []).append(v)
    축, 버린축 = [], []
    for k, vs in sorted(축카운트.items()):
        수치 = [v for v in vs if isinstance(v, (int, float))
                and not isinstance(v, bool)]
        종류 = "수치" if len(수치) == len(vs) and len(set(수치)) > 1 else "범주"
        if len(set(map(str, vs))) < 2:
            continue                        # 값이 하나뿐인 축은 축이 아니다
        if 종류 == "범주" and max(len(str(v)) for v in vs) > 40:
            버린축.append({"축": k, "왜": "범주 값이 40자를 넘어 축으로 못 쓴다"})
            continue
        축.append({"이름": k, "종류": 종류, "run 수": len(vs),
                  "최소": (min(수치) if 종류 == "수치" else None),
                  "최대": (max(수치) if 종류 == "수치" else None),
                  "값 가짓수": len(set(map(str, vs))),
                  "값 목록": (sorted({str(v) for v in vs})[:12]
                          if 종류 == "범주" else None)})
    # ── ③ 중요도 --- 🔴 run 이 모자라면 **막대를 안 그린다**
    n_t = len(있는)
    중요도 = {"잴 수 있나": False, "지금 run 수": n_t,
           "최소 필요": MIN_RUNS_FOR_IMPORTANCE, "표": [],
           "🔴 왜": (f"이 지표(`{tgt}`)를 가진 run 이 **{n_t}개**뿐이다 --- "
                  f"중요도·상관을 내려면 **{MIN_RUNS_FOR_IMPORTANCE}개**가 필요하다. "
                  f"표본 {n_t}개로 막대를 그리면 그것이 조항 60 위반이다"),
           "계산법": ("스피어만 |ρ| (동률 평균 순위) --- 랜덤포레스트 중요도가 "
                   "아니다. 자기 널(대상을 200번 순열)을 같이 낸다"),
           }
    if tgt and n_t >= MIN_RUNS_FOR_IMPORTANCE:
        import random
        y = [r["최종 지표"][tgt] for r in 있는]
        표 = []
        for A in 축:
            if A["종류"] != "수치":
                continue
            x = [r["하이퍼파라미터(평평하게)"].get(A["이름"]) for r in 있는]
            if any(v is None or not isinstance(v, (int, float)) for v in x):
                continue
            rho = _spearman(x, y)
            if rho is None:
                continue
            rnd = random.Random(0)
            널 = []
            for _ in range(200):
                yy = list(y)
                rnd.shuffle(yy)
                v = _spearman(x, yy)
                널.append(abs(v) if v is not None else 0.0)
            널.sort()
            p = sum(1 for v in 널 if v >= abs(rho))
            표.append({"축": A["이름"], "중요도(|ρ|)": round(abs(rho), 4),
                      "상관(ρ)": round(rho, 4),
                      "널 95분위": round(널[int(0.95 * len(널))], 4),
                      "널보다 큰가": abs(rho) > 널[int(0.95 * len(널))],
                      "순열 p": round((1 + p) / (1 + len(널)), 4)})
        표.sort(key=lambda r: -r["중요도(|ρ|)"])
        중요도 = {"잴 수 있나": True, "지금 run 수": n_t,
               "최소 필요": MIN_RUNS_FOR_IMPORTANCE, "표": 표,
               "계산법": 중요도["계산법"],
               "🔴 단서": "🔴 **인과가 아니다.** 설정과 결과의 순위 상관일 뿐이고, "
                       "run 들이 같은 실험 설계에서 나온 것도 아니다"}
    # ── ⑤ 으뜸 --- 🔴 무엇이 「좋은」 값인지 이 창구는 모른다
    으뜸 = {"잴 수 있나": False,
          "🔴 왜": "이 지표를 가진 run 이 없다"}
    if 있는:
        hi = max(있는, key=lambda r: r["최종 지표"][tgt])
        lo = min(있는, key=lambda r: r["최종 지표"][tgt])
        으뜸 = {"잴 수 있나": True, "지표": tgt,
              "가장 큰 값": {"run_id": hi["run_id"], "값": hi["최종 지표"][tgt]},
              "가장 작은 값": {"run_id": lo["run_id"], "값": lo["최종 지표"][tgt]},
              "🔴 어느 쪽이 좋은가": (
                  "🔴 **이 창구는 모른다.** 손실이면 작은 쪽이, 정확도면 큰 쪽이 "
                  "좋지만 지표 이름만으로 단정하지 않는다 --- 그리고 이 run 들은 "
                  "대부분 **자가 없다**(자 없는 값으로는 아무것도 주장 못 한다)")}
    return {**_head(),
            "무엇": "run 여럿을 나란히 보는 패널(사이드바 · 겹친 곡선 · 평행좌표 · "
                  "중요도 · 으뜸)",
            "run 수": len(행),
            "지표 후보": [{"이름": k, "run 수": v}
                     for k, v in sorted(지표이름.items(), key=lambda kv: -kv[1])],
            "고른 지표": tgt,
            "🔴 지표 없는 run 수": sum(1 for r in 행 if not r["최종 지표"]),
            "run": [{k: v for k, v in r.items() if k != "계열"} for r in 행],
            "겹친 곡선": {
                "지표": tgt, "곡선": 곡선,
                "🔴 몇 개 중 몇 개": (
                    f"이 지표를 가진 run {len(있는)}개 중 **{len(곡선)}개만** 그린다"
                    + (f" (한도 {MAX_OVERLAY_RUNS}개)"
                       if len(있는) > MAX_OVERLAY_RUNS else "")),
            },
            "평행좌표": {
                "축": 축, "🔴 축은 어디서 왔나":
                    "manifest 의 `하이퍼파라미터` 를 평평하게 펴서 **자동으로** 뽑았다 "
                    "--- 손으로 축 목록을 적지 않았다. 값이 하나뿐인 축은 뺐다",
                "🔴 못 한 것": "축 순서 드래그와 브러시 거르기는 **못 했다**",
                "🔴 버린 축": 버린축 or None,
                "그릴 수 있나": len(축) >= 2 and len(행) >= 2,
                "왜": (None if len(축) >= 2 and len(행) >= 2 else
                      f"축 {len(축)}개 · run {len(행)}개 --- 선을 그으려면 "
                      f"축 2개와 run 2개가 필요하다"),
            },
            "중요도": 중요도,
            "으뜸": 으뜸,
            "🔴 이 패널이 안 하는 것": "설정을 바꾸면 결과가 어떻게 된다는 말을 "
                              "하지 않는다(관측된 run 들의 순위 상관일 뿐이다)"}


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
#: 🔴 **저장소에 있는 진짜 run 행과 같은 꼴**로 쓴다(옛 데모 run 은 지웠다).
음성 = [
    {"run_id": "state.masked_encoder.Net", "이름": "state.masked_encoder.Net",
     "상태": "끝남", "지표 줄 수(읽어 센 것)": 0, "자": None,
     "학습 돌렸나": False, "미는 출력": ["⑤파생"], "총 파라미터": 1230},
    {"run_id": "popup-tblock", "이름": "popup 표를 토큰열로 본 트랜스포머 블록 하나",
     "상태": "끝남", "지표 줄 수(읽어 센 것)": 640, "자": None,
     "학습 돌렸나": True, "미는 출력": ["해당 없음"], "총 파라미터": 9121},
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
