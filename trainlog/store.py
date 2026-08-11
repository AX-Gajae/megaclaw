"""저장된 run 을 **읽는다** --- 뷰어가 보는 유일한 문. 노트 912 팔 ㅇ.

여기서 지키는 규율은 하나다.

🔴 **없는 것을 만들지 않는다.** 지표가 없으면 곡선은 **0개**이고 「못 읽음」이다.
그럴듯한 선을 그리는 순간 이 창구는 실패다(`serve/test_trainlog.py ②`).

읽는 쪽은 쓰는 쪽을 **믿지 않는다**. `manifest.json` 이 적은 「지표 줄 수」와
파일을 실제로 세어 나온 수를 **둘 다** 낸다(조항 60 --- 남이 적은 분모를 내
분모로 쓰지 않는다). 둘이 어긋나면 그 사실이 화면에 보인다.
"""
from __future__ import annotations

import json
from pathlib import Path

from .run import STORE

#: 한 계열에 담을 점의 최대 수. 넘으면 **솎되 솎았다고 적는다**.
MAX_POINTS = 2000

# ── 🔴 판 1.1.0 --- 그림을 짜는 데 쓰는 상수들 (노트 913 팔 ㅈ) ────────
#: 뉴런 점 하나에 주는 세로 픽셀. **가독 밀도**이고, 자르기는 여기서 역산된다.
NEURON_PX = 9
#: 노드 하나가 이름표에 쓰는 세로 픽셀(점과 별도).
LABEL_PX = 26
#: 그림 위아래 여백 합.
PAD_PX = 70
#: 한 노드에 최소 이만큼은 점을 준다(이보다 좁으면 그림 높이를 늘린다).
MIN_DOTS = 8
#: 그림 높이의 위아래 한도.
MIN_CANVAS, MAX_CANVAS = 320, 1600
#: 뉴런 그림에서 **선으로 그릴 간선의 총 예산**. 넘으면 골라 그리고 **골랐다고 적는다**.
EDGE_BUDGET = 1500
#: 간선 하나(층↔층)에 최소한 주는 선 수.
MIN_EDGE_LINES = 40
#: 세기 행렬을 통째로 실어 보낼 수 있는 최대 요소 수(넘으면 고른 선만 보낸다).
MAX_STRENGTH_ELEMS = 4096

#: 🔴 **진짜 복제 그릇**만 `N×` 로 접는다. 사람이 짠 클래스(`Head` 같은) 안의
#: 형제(q·k·v)는 모양이 같아도 **다른 물건**이라 접으면 거짓말이 된다.
REPLICA_CONTAINERS = ("ModuleList", "ModuleDict", "Sequential")

#: 종류 → 색 갈래. 🔴 **색은 여기서 정한다**(화면이 제 맘대로 칠하지 않게).
KIND_GROUP = {
    "입력": "입력", "Embedding": "임베딩", "EmbeddingBag": "임베딩",
    "Linear": "선형", "LazyLinear": "선형", "Bilinear": "선형",
    "MultiheadAttention": "어텐션", "Attention": "어텐션",
    "TransformerEncoderLayer": "어텐션", "TransformerDecoderLayer": "어텐션",
    "LayerNorm": "정규화", "BatchNorm1d": "정규화", "BatchNorm2d": "정규화",
    "GroupNorm": "정규화", "RMSNorm": "정규화", "InstanceNorm1d": "정규화",
    "Dropout": "드롭아웃", "Dropout1d": "드롭아웃", "Dropout2d": "드롭아웃",
    "Conv1d": "합성곱", "Conv2d": "합성곱", "Conv3d": "합성곱",
    "ConvTranspose2d": "합성곱",
    "LSTM": "순환", "GRU": "순환", "RNN": "순환",
    "Softmax": "출력", "LogSoftmax": "출력",
}
#: 갈래 → 색(파스텔 · 글자는 검정). 🔴 *Attention Is All You Need* 그림 1 의 결.
GROUP_COLOR = {
    "입력": "#cfd4da", "임베딩": "#bfe3d0", "선형": "#b9d4f2",
    "어텐션": "#e2c6f0", "정규화": "#f7d9a8", "활성": "#cfe8b4",
    "드롭아웃": "#d9d9d9", "합성곱": "#f6c6c6", "순환": "#c9d6f5",
    "출력": "#f5c2d8", "기타": "#e0ded8",
}


def kind_group(kind: str, act=None) -> str:
    """모듈 종류를 **색 갈래**로 접는다 --- 모르면 「기타」다(지어내지 않는다)."""
    k = str(kind or "")
    if k in KIND_GROUP:
        return KIND_GROUP[k]
    from .arch import ACTIVATIONS
    if k in ACTIVATIONS:
        return "활성"
    return "기타"


def _rd(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def run_dir(run_id: str, root=None) -> Path:
    """run_id → 디렉터리. **경로 탈출을 막는다**(`../` 로 밖을 못 본다)."""
    base = Path(root or STORE)
    d = (base / run_id).resolve()
    if not str(d).startswith(str(base.resolve())):
        raise ValueError(f"run_id 가 저장소 밖을 가리킨다: {run_id!r}")
    return d


def read_manifest(run_id: str, root=None) -> dict:
    d = run_dir(run_id, root)
    p = d / "manifest.json"
    if not p.exists():
        return {"run_id": run_id, "상태": "못 읽었다",
                "왜": f"`{p.name}` 이 없다"}
    try:
        return _rd(p)
    except Exception as e:
        return {"run_id": run_id, "상태": "못 읽었다",
                "왜": f"{type(e).__name__}: {e}"}


def read_arch(run_id: str, root=None) -> dict:
    d = run_dir(run_id, root)
    p = d / "arch.json"
    if not p.exists():
        return {"읽음": False, "출처": "못 읽음", "층": [], "간선": [],
                "왜 못 읽음": "`arch.json` 이 없다 --- 이 run 은 아키텍처를 "
                          "한 번도 안 적었다"}
    try:
        return _rd(p)
    except Exception as e:
        return {"읽음": False, "출처": "못 읽음", "층": [], "간선": [],
                "왜 못 읽음": f"`arch.json` 을 못 읽었다: {type(e).__name__}: {e}"}


def read_metrics(run_id: str, root=None) -> dict:
    """지표 스트림 → **곡선.** 🔴 없으면 곡선 0개다(빈 차트가 정답이다).

    네 갈래로 답한다(조항 59):

        없다        `metrics.jsonl` 이 없다
        비었다      파일은 있는데 **지표 줄이 0** 이다 (헤더만 있는 것도 여기다)
        읽었다      점이 있다
        못 읽었다    파일은 있는데 줄이 JSON 이 아니다
    """
    d = run_dir(run_id, root)
    p = d / "metrics.jsonl"
    base = {"run_id": run_id, "경로": f"data/trainlog/{run_id}/metrics.jsonl",
            "곡선": [], "곡선 수": 0, "점 수": 0}
    if not p.exists():
        return {**base, "상태": "없다",
                "왜": "`metrics.jsonl` 이 없다 --- 이 run 은 지표를 한 줄도 안 남겼다",
                "말": "**곡선을 그리지 않는다.** 지어낸 선을 그리면 그 순간 실패다"}
    series, bad, nline, 헤더 = {}, [], 0, None
    try:
        with p.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception as e:
                    return {**base, "상태": "못 읽었다",
                            "왜": f"{i+1}번째 줄이 JSON 이 아니다: {e}",
                            "말": "**곡선을 그리지 않는다**"}
                if "name" not in o:
                    헤더 = 헤더 or o          # 자기서술 헤더
                    continue
                nline += 1
                v = o.get("value")
                k = (str(o.get("split") or "?"), str(o.get("name")))
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    series.setdefault(k, []).append([o.get("step"), float(v)])
                else:
                    if len(bad) < 20:
                        bad.append({"step": o.get("step"), "split": k[0],
                                    "name": k[1], "value": v})
    except Exception as e:
        return {**base, "상태": "못 읽었다", "왜": f"{type(e).__name__}: {e}",
                "말": "**곡선을 그리지 않는다**"}
    if nline == 0:
        return {**base, "상태": "비었다", "헤더": 헤더,
                "왜": "파일은 있는데 **지표 줄이 0** 이다 --- 「없다」와 다르다(조항 59)",
                "말": "**곡선을 그리지 않는다.** 빈 차트가 정답이다"}
    곡선, 총점 = [], 0
    for (split, name), pts in sorted(series.items()):
        pts.sort(key=lambda x: (x[0] is None, x[0]))
        n0 = len(pts)
        솎음 = None
        if n0 > MAX_POINTS:
            k = (n0 + MAX_POINTS - 1) // MAX_POINTS
            pts = pts[::k]
            솎음 = (f"🔴 {n0:,}점 중 {len(pts):,}점만 보냈다 --- {k}점마다 "
                  f"하나씩 골랐다(맨 뒤 점이 남는다는 보장이 없다)")
        총점 += len(pts)
        곡선.append({"split": split, "name": name, "점 수": len(pts),
                    "원래 점 수": n0, "솎음": 솎음, "점": pts})
    return {**base, "상태": "읽었다", "헤더": 헤더,
            "곡선": 곡선, "곡선 수": len(곡선), "점 수": 총점,
            "지표 줄 수(읽어 센 것)": nline,
            "수가 아닌 값": bad or None,
            "말": "점은 전부 `metrics.jsonl` 에서 왔다 --- 보간·평활·외삽을 안 한다"}


def read_node_metrics(run_id: str, root=None, max_steps: int = 400) -> dict:
    """🔴 **노드별 시계열** --- 그래프 위에 얹을 상태(판 1.1.0).

    없으면 **「안 잼」**이다(「0」이 아니다 · 조항 59). 화면은 그때 노드를 **회색**으로
    두고 「이 run 은 그 지표를 안 기록했다」를 적는다 --- **추정도 보간도 안 한다.**

    돌려주는 꼴:

        {"상태": "읽었다", "지표 이름": ["grad_norm"],
         "단계": [10, 20, …],                       # 실제로 **기록된** step 만
         "값": {"grad_norm": {"block.ff1": {"10": 0.004, …}}},
         "노드 수": 19, "줄 수": 3800}

    🔴 **단계 목록은 기록된 것만** 들어간다. 화면의 눈금이 그 위에서만 움직이므로
    「그 시점의 값」이 언제나 **실측**이다(사이를 메우지 않는다).
    """
    d = run_dir(run_id, root)
    p = d / "node_metrics.jsonl"
    base = {"run_id": run_id, "값": {}, "지표 이름": [], "단계": [],
            "노드 수": 0, "줄 수": 0,
            "경로": f"data/trainlog/{run_id}/node_metrics.jsonl"}
    if not p.exists():
        return {**base, "상태": "안 잼",
                "왜": "`node_metrics.jsonl` 이 없다 --- 이 run 은 노드별 상태를 "
                     "**한 줄도 안 적었다**",
                "말": "🔴 **「0」이 아니라 「못 잼」이다.** 화면은 노드를 회색으로 "
                     "두고 값을 지어내지 않는다"}
    값: dict = {}
    steps: set = set()
    nodes: set = set()
    n, 나쁨 = 0, 0
    try:
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    나쁨 += 1
                    continue
                if "node" not in o or "name" not in o:
                    continue
                v = o.get("value")
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    continue
                n += 1
                nm, nd, st = str(o["name"]), str(o["node"]), o.get("step")
                steps.add(st)
                nodes.add(nd)
                값.setdefault(nm, {}).setdefault(nd, {})[str(st)] = float(v)
    except Exception as e:
        return {**base, "상태": "못 읽었다", "왜": f"{type(e).__name__}: {e}"}
    단계 = sorted(s for s in steps if s is not None)
    솎음 = None
    if len(단계) > max_steps:
        k = (len(단계) + max_steps - 1) // max_steps
        남길 = set(단계[::k]) | {단계[-1]}
        단계 = sorted(남길)
        솎음 = (f"🔴 기록된 단계 {len(steps):,}개 중 {len(단계):,}개만 보냈다 "
              f"({k}개마다 하나 + 마지막) --- **값을 만든 것이 아니라 뺀 것이다**")
        for nm in 값:
            for nd in 값[nm]:
                값[nm][nd] = {s: v for s, v in 값[nm][nd].items()
                             if int(float(s)) in 남길}
    return {**base, "상태": "읽었다" if n else "비었다",
            "지표 이름": sorted(값), "단계": 단계, "값": 값,
            "노드 수": len(nodes), "줄 수": n,
            "JSON 이 아닌 줄 수": 나쁨, "단계 솎음": 솎음,
            "말": "🔴 값은 전부 `node_metrics.jsonl` 에서 왔다 --- 보간·추정을 안 한다"}


def node_state(run_id: str, step=None, name: str = "grad_norm",
               root=None) -> dict:
    """🔴 **한 시점의 그래프 상태** --- 곡선에서 고른 step 을 그래프에 얹는다.

    🔴 **고른 step 은 기록된 step 중 하나여야 한다.** 사이 값을 만들어 내면 그것이
    지어낸 상태다. 그래서 요청한 step 에 기록이 없으면 **가장 가까운 기록 step 으로
    옮기고 옮겼다고 적는다**(값을 만들지 않는다).
    """
    S = read_node_metrics(run_id, root)
    if S["상태"] != "읽었다" or not S["단계"]:
        return {"run_id": run_id, "잴 수 있나": False,
                "상태": S["상태"], "왜": S.get("왜") or "노드 지표가 비었다",
                "지표 이름": S.get("지표 이름") or [],
                "값": {}, "단계": [], "고른 단계": None,
                "말": "🔴 **이 run 은 노드 상태를 안 기록했다** --- 노드를 회색으로 "
                     "두고 아무 값도 얹지 않는다(추정 금지)"}
    이름 = name if name in S["값"] else (S["지표 이름"][0])
    단계 = S["단계"]
    고름, 옮김 = 단계[-1], None
    if step is not None:
        try:
            want = int(step)
            고름 = min(단계, key=lambda s: abs(int(s) - want))
            if int(고름) != want:
                옮김 = (f"🔴 요청한 step {want:,} 에는 기록이 없다 --- 가장 가까운 "
                      f"**기록된** step {int(고름):,} 로 옮겼다(값을 만들지 않았다)")
        except Exception:
            옮김 = f"🔴 step 을 못 읽었다({step!r}) --- 마지막 기록 단계를 썼다"
    표 = S["값"].get(이름, {})
    값 = {nd: v[str(고름)] for nd, v in 표.items() if str(고름) in v}
    못잼 = sorted(set(표) - set(값))
    vals = sorted(값.values())
    return {"run_id": run_id, "잴 수 있나": True, "상태": "읽었다",
            "지표 이름": S["지표 이름"], "고른 지표": 이름,
            "단계": 단계, "고른 단계": 고름, "🔴 단계를 옮겼나": 옮김,
            "값": 값, "노드 수(값 있는)": len(값),
            "🔴 이 단계에 값이 없는 노드": 못잼 or None,
            "최소": (vals[0] if vals else None),
            "최대": (vals[-1] if vals else None),
            "단계 솎음": S.get("단계 솎음"),
            "말": (f"step {고름} 의 `{이름}` 을 노드 {len(값)}개에 얹었다 --- "
                  f"**값은 전부 기록에서 왔다**(보간·추정 없음)")}


def list_runs(root=None, limit: int = 200) -> dict:
    """run 목록. **읽는 쪽이 직접 센 수**를 manifest 의 수와 나란히 낸다."""
    base = Path(root or STORE)
    if not base.exists():
        return {"상태": "없다", "경로": "data/trainlog", "run 수": 0, "run": [],
                "왜": "`data/trainlog/` 가 아직 없다 --- 학습 기록이 0건이다"}
    rows = []
    for d in sorted(base.iterdir(), reverse=True):
        if not d.is_dir():
            continue
        m = read_manifest(d.name, base)
        mp = d / "metrics.jsonl"
        센줄 = 0
        if mp.exists():
            try:
                with mp.open(encoding="utf-8") as f:
                    #: 🔴 `'"name"'` 로 세면 **헤더 줄의 `칸` 목록**에도 걸린다
                    #: (한 번 걸렸다 --- 240 을 241 로 셌다). `:` 까지 봐야 한다.
                    센줄 = sum(1 for ln in f if ln.strip() and '"name":' in ln)
            except Exception:
                센줄 = None
        a = m.get("아키텍처") or {}
        rows.append({
            "run_id": d.name,
            "이름": m.get("이름(원래)"),
            "데모인가": bool(m.get("데모인가")),
            "상태": m.get("상태"),
            "시작 UTC": m.get("시작 UTC"), "끝 UTC": m.get("끝 UTC"),
            "초": m.get("초"),
            "미는 출력": m.get("미는 출력"),
            "자": m.get("자"), "자 없음": bool(m.get("자 없음", not m.get("자"))),
            "지표 줄 수(manifest)": m.get("지표 줄 수"),
            "지표 줄 수(읽어 센 것)": 센줄,
            "🔴 수가 어긋나나": (m.get("지표 줄 수") != 센줄),
            "아키텍처 읽음": bool(a.get("읽음")),
            "아키텍처 출처": a.get("출처"),
            "층 수": a.get("층 수"), "총 파라미터": a.get("총 파라미터"),
            "씨앗": m.get("씨앗"),
            "규격 판": m.get("규격 판"),
            #: 🔴 판 1.1.0 --- 구조만 있는 run 을 「지표를 못 남겼다」로 안 보이게
            "학습 돌렸나": m.get("학습 돌렸나"),
            "노드 지표 줄 수": m.get("노드 지표 줄 수"),
            "노드 지표 이름": m.get("노드 지표 이름"),
            "모형 클래스": a.get("모형 클래스"),
        })
        if len(rows) >= limit:
            break
    return {"상태": "읽었다" if rows else "비었다", "경로": "data/trainlog",
            "run 수": len(rows), "run": rows,
            "🔴 단서": "「지표 줄 수(manifest)」는 **쓴 쪽이 적은 수**이고 "
                   "「읽어 센 것」은 **이 창구가 직접 센 수**다. 어긋나면 "
                   "`수가 어긋나나` 가 참이 된다(조항 60)"}


# ── 🔴 임의 DAG --- 층을 차례로 잇지 않는다(판 1.1.0 · 노트 913) ─────
def _base_graph(a: dict) -> dict:
    """`arch.json` 을 **노드 + 간선**으로 편다 --- 🔴 *간선을 실제로 쓴다*.

    판 1.0.0 의 그림은 층을 **차례로** 이었다(`층[i] → 층[i+1]`). 그래서 잔차·분기가
    있는 그래프는 **그림이 거짓**이었다. 여기서는 `간선` 목록을 그대로 쓴다.

    입력 노드는 둘 중 하나로 생긴다 —
      ① `간선` 에 이미 `__입력__` 이 있다(`torch.fx` 가 placeholder 를 냈다) → **실측**
      ② 없는데 첫 층에 `입력 뉴런 수` 가 있다 → **가정으로 하나 세우고 그렇게 적는다**
    """
    src = a.get("층") or []
    by = {str(L.get("id")): L for L in src}
    raw = [{"from": str(e.get("from")), "to": str(e.get("to"))}
           for e in (a.get("간선") or [])]
    입력참조 = any(e["from"] == "__입력__" or e["to"] == "__입력__" for e in raw)
    nodes, 입력가정 = [], None
    if src and (입력참조 or src[0].get("입력 뉴런 수")):
        nodes.append({"id": "__입력__", "이름": "입력", "종류": "입력",
                      "뉴런 수": src[0].get("입력 뉴런 수"),
                      "입력 뉴런 수": None, "파라미터 수": 0,
                      "활성함수": None, "묶음": None, "묶음 종류": None,
                      "헤드 수": None, "가중치": {}})
        if not 입력참조:
            raw = [{"from": "__입력__", "to": str(src[0]["id"])}] + raw
            입력가정 = ("🔴 `간선` 에 입력 노드가 없어 **첫 층 앞에 하나를 가정**했다 "
                     "--- 실제 호출 그래프에서 온 것이 아니다")
    for L in src:
        nodes.append({**L, "id": str(L["id"])})
    known = {n["id"] for n in nodes}
    edges, 버린 = [], []
    seen = set()
    for e in raw:
        if e["from"] not in known or e["to"] not in known:
            버린.append(e)
            continue
        if e["from"] == e["to"]:
            버린.append({**e, "왜": "자기 자신으로 가는 간선(고리)"})
            continue
        key = (e["from"], e["to"])
        if key in seen:
            continue
        seen.add(key)
        edges.append(dict(e))
    return {"노드": nodes, "간선": edges, "버린 간선": 버린, "입력 가정": 입력가정,
            "층 표": by}


def _layer_depths(ids, edges) -> dict:
    """위상 정렬 → **가장 긴 경로 깊이**. 🔴 고리가 있으면 「못 폈다」고 적는다."""
    indeg = {i: 0 for i in ids}
    succ = {i: [] for i in ids}
    for e in edges:
        succ[e["from"]].append(e["to"])
        indeg[e["to"]] += 1
    depth = {i: 0 for i in ids}
    q = [i for i in ids if indeg[i] == 0]
    순서 = []
    while q:
        v = q.pop(0)
        순서.append(v)
        for w in succ[v]:
            depth[w] = max(depth[w], depth[v] + 1)
            indeg[w] -= 1
            if indeg[w] == 0:
                q.append(w)
    남은 = [i for i in ids if i not in set(순서)]
    if 남은:
        d = (max(depth.values()) if depth else 0) + 1
        for i in 남은:
            depth[i] = d
    return {"깊이": depth, "순서": 순서, "고리에 남은 노드": 남은,
            "고리 있나": bool(남은)}


def _sig(n: dict) -> tuple:
    return (str(n.get("종류")), n.get("입력 뉴런 수"), n.get("뉴런 수"),
            str(n.get("활성함수")), n.get("파라미터 수"))


def _fold_replicas(nodes, edges, 묶음표: dict) -> dict:
    """🔴 **같은 꼴이 여러 번 쌓인 것을 `N×` 로 접는다**(그림 1 의 `Nx`).

    접는 자리는 **진짜 복제 그릇**(`ModuleList` · `ModuleDict` · `Sequential`)의
    형제뿐이고, 그것도 **이웃(앞·뒤 간선)이 똑같을 때만** 접는다. 사람이 짠 클래스
    안의 q·k·v 는 모양이 같아도 **다른 물건**이므로 안 접는다.

    두 켜로 접는다 —
      가. **잎 형제**   `heads.popup` … `heads.idol` (ModuleDict 12개) → 하나 + `12×`
      나. **묶음 형제** `heads.0` … `heads.3` (ModuleList 안의 작은 블록) → 하나 + `4×`

    🔴 접은 사실 · 배수 · 접힌 id 를 **전부 남긴다**(조항 59 --- 조용히 접지 않는다).
    """
    by = {n["id"]: n for n in nodes}
    pred, succ = {i: set() for i in by}, {i: set() for i in by}
    for e in edges:
        pred[e["to"]].add(e["from"])
        succ[e["from"]].add(e["to"])
    대표: dict = {}                     # 접힌 id → 대표 id
    접힘: dict = {}                     # 대표 id → {배수, 접힌 id, 무엇}

    def 그릇인가(path) -> bool:
        return str(묶음표.get(path) or "") in REPLICA_CONTAINERS

    # ── 가. 잎 형제 ────────────────────────────────────────────────
    후보: dict = {}
    for n in nodes:
        g = n.get("묶음")
        if not g or not 그릇인가(g):
            continue
        후보.setdefault(g, []).append(n)
    for g, mem in 후보.items():
        buckets: dict = {}
        ids = {m["id"] for m in mem}
        for m in mem:
            key = (_sig(m), frozenset(pred[m["id"]] - ids),
                   frozenset(succ[m["id"]] - ids))
            buckets.setdefault(key, []).append(m["id"])
        for key, group in buckets.items():
            if len(group) < 2:
                continue
            group = sorted(group)
            head = group[0]
            접힘[head] = {"배수": len(group), "접힌 id": group[1:],
                        "무엇": "잎 형제", "그릇": g,
                        "그릇 종류": 묶음표.get(g)}
            for x in group[1:]:
                대표[x] = head

    # ── 나. 묶음 형제 ──────────────────────────────────────────────
    묶음별: dict = {}
    for n in nodes:
        g = n.get("묶음")
        if g and "." in g and 그릇인가(g.rsplit(".", 1)[0]):
            묶음별.setdefault(g, []).append(n)
    부모별: dict = {}
    for g in 묶음별:
        부모별.setdefault(g.rsplit(".", 1)[0], []).append(g)
    for parent, gs in 부모별.items():
        if len(gs) < 2:
            continue
        buckets: dict = {}
        for g in gs:
            mem = 묶음별[g]
            ids = {m["id"] for m in mem}
            sig = (tuple(sorted(_sig(m) for m in mem)),
                   frozenset().union(*[pred[m["id"]] - ids for m in mem]),
                   frozenset().union(*[succ[m["id"]] - ids for m in mem]))
            buckets.setdefault(sig, []).append(g)
        for sig, group in buckets.items():
            if len(group) < 2:
                continue
            group = sorted(group)
            head, rest = group[0], group[1:]
            hm = sorted(묶음별[head], key=lambda m: m["id"])
            for other in rest:
                om = sorted(묶음별[other], key=lambda m: m["id"])
                if len(om) != len(hm):
                    continue
                for a1, b1 in zip(hm, om):
                    if b1["id"] not in 대표:
                        대표[b1["id"]] = 대표.get(a1["id"], a1["id"])
            for a1 in hm:
                n_folded = sum(1 for x in 대표 if 대표[x] == a1["id"])
                if n_folded:
                    접힘[a1["id"]] = {
                        "배수": n_folded + 1,
                        "접힌 id": sorted(x for x in 대표 if 대표[x] == a1["id"]),
                        "무엇": "묶음 형제", "그릇": parent,
                        "그릇 종류": 묶음표.get(parent)}
    return {"대표": 대표, "접힘": 접힘}


def _apply_fold(nodes, edges, 대표: dict) -> tuple:
    """접힌 노드를 지우고 간선을 대표로 **다시 이어** 겹치는 것을 셈한다."""
    keep = [n for n in nodes if n["id"] not in 대표]
    m = lambda i: 대표.get(i, i)                                    # noqa: E731
    합침: dict = {}
    for e in edges:
        a, b = m(e["from"]), m(e["to"])
        if a == b:
            합침.setdefault((a, b), []).append(e)
            continue
        합침.setdefault((a, b), []).append(e)
    out = []
    for (a, b), grp in 합침.items():
        if a == b:
            continue
        out.append({"from": a, "to": b, "합쳐진 간선 수": len(grp)})
    return keep, out


def _expand(F: dict, 펼침) -> dict:
    """🔴 **누른 자리만 펼친다** --- 접힌 대표 id 를 주면 그 뭉치만 안 접는다."""
    if not 펼침:
        return F
    want = {str(x) for x in 펼침}
    대표 = dict(F["대표"])
    접힘 = dict(F["접힘"])
    for head in list(접힘):
        if head not in want:
            continue
        for x in 접힘[head]["접힌 id"]:
            대표.pop(x, None)
        접힘.pop(head, None)
    return {"대표": 대표, "접힘": 접힘}


def graph(run_id: str, root=None, 접기: bool = True, 펼침=None) -> dict:
    """🔴 **블록 다이어그램 계획** --- *Attention Is All You Need* 그림 1 의 결.

    뉴런 점이 아니라 **연산 블록 하나 = 박스 하나**다. 박스에는 이름 · 종류 · 모양 ·
    파라미터 수가 적히고, 색은 종류로 갈린다. 잔차·분기·합류는 **깊이를 건너뛴
    간선**으로 나오며(화면이 곡선 화살표로 돌린다), 같은 꼴이 여러 번 쌓인 곳은
    `N×` 로 접는다.

    🔴 이 함수는 **아무것도 지어내지 않는다.** 간선은 `arch.json` 의 `간선` 이고,
    접은 것은 접었다고 적고, 못 읽은 것은 못 읽었다고 적는다.
    """
    a = read_arch(run_id, root)
    if not a.get("읽음"):
        return {"run_id": run_id, "그릴 수 있나": False,
                "왜": a.get("왜 못 읽음") or "아키텍처를 못 읽었다",
                "블록": [], "화살표": [], "접은 것": [],
                "말": "**아무것도 그리지 않는다** --- 아키텍처를 못 읽었다"}
    G = _base_graph(a)
    nodes, edges = G["노드"], G["간선"]
    묶음표 = a.get("묶음 표") or {}
    F = _fold_replicas(nodes, edges, 묶음표) if 접기 else {"대표": {}, "접힘": {}}
    전체접힘 = dict(F["접힘"])
    F = _expand(F, 펼침)
    kept, e2 = _apply_fold(nodes, edges, F["대표"])
    ids = [n["id"] for n in kept]
    lay = _layer_depths(ids, e2)
    depth = lay["깊이"]
    # 레인 --- 같은 깊이에 여럿이면 앞 노드의 레인 평균으로 정렬해 선이 덜 꼬이게
    by_depth: dict = {}
    for i in ids:
        by_depth.setdefault(depth[i], []).append(i)
    pred: dict = {i: [] for i in ids}
    for e in e2:
        pred[e["to"]].append(e["from"])
    lane: dict = {}
    order = {i: k for k, i in enumerate(ids)}
    for d in sorted(by_depth):
        rows = by_depth[d]
        def key(i):
            ps = [lane[p] for p in pred[i] if p in lane]
            return (sum(ps) / len(ps) if ps else 0.0, order[i])
        for k, i in enumerate(sorted(rows, key=key)):
            lane[i] = k
        by_depth[d] = sorted(rows, key=lambda i: lane[i])
    블록 = []
    for n in kept:
        i = n["id"]
        f = F["접힘"].get(i)
        모양 = None
        if n.get("입력 뉴런 수") and n.get("뉴런 수"):
            모양 = f"{n['입력 뉴런 수']:,} → {n['뉴런 수']:,}"
        elif n.get("뉴런 수"):
            모양 = f"→ {n['뉴런 수']:,}"
        블록.append({
            "id": i, "이름": i.rsplit(".", 1)[-1], "전체 이름": n.get("이름") or i,
            "종류": n.get("종류"), "색 갈래": kind_group(n.get("종류")),
            "모양": 모양, "입력 뉴런 수": n.get("입력 뉴런 수"),
            "뉴런 수": n.get("뉴런 수"), "파라미터 수": n.get("파라미터 수"),
            "활성함수": n.get("활성함수"), "헤드 수": n.get("헤드 수"),
            "묶음": n.get("묶음"), "묶음 종류": n.get("묶음 종류"),
            "깊이": depth[i], "레인": lane[i],
            "접힘 배수": (f or {}).get("배수"),
            "접힌 id": (f or {}).get("접힌 id"),
            "접힘 말": (f"🔴 같은 꼴 {f['배수']}개를 **하나로 접었다**(`{f['배수']}×`) "
                     f"--- {f['그릇']}({f['그릇 종류']}) 의 형제다. "
                     f"접힌 것: {', '.join(f['접힌 id'][:6])}"
                     + (" …" if len(f["접힌 id"]) > 6 else "")) if f else None,
        })
    화살표 = []
    for e in e2:
        d0, d1 = depth[e["from"]], depth[e["to"]]
        건너뜀 = d1 - d0
        화살표.append({
            "from": e["from"], "to": e["to"], "건너뜀": 건너뜀,
            "종류": "차례" if 건너뜀 <= 1 else "🔴 건너뜀(잔차·우회)",
            "합쳐진 간선 수": e.get("합쳐진 간선 수", 1)})
    indeg: dict = {i: 0 for i in ids}
    outdeg: dict = {i: 0 for i in ids}
    for e in e2:
        outdeg[e["from"]] += 1
        indeg[e["to"]] += 1
    #: 🔴 **묶음 상자** --- 그림 1 의 `Nx` 처럼 블록 여럿을 상자 하나로 둘러 준다.
    묶음상자 = []
    for g in sorted({b["묶음"] for b in 블록 if b["묶음"]}):
        mem = [b for b in 블록 if b["묶음"] == g]
        if len(mem) < 2 and not any(b["접힘 배수"] for b in mem):
            continue
        배수 = {b["접힘 배수"] for b in mem}
        n배 = 배수.pop() if len(배수) == 1 else None
        묶음상자.append({
            "경로": g, "종류": 묶음표.get(g) or (mem[0].get("묶음 종류")),
            "블록": [b["id"] for b in mem],
            "배수": n배,
            "라벨": (f"{g} ({묶음표.get(g) or '?'})"
                   + (f"  {n배}×" if n배 and n배 > 1 else "")),
            "🔴 말": (f"같은 꼴 묶음이 {n배}벌 있었고 **한 벌만 그리고 `{n배}×` 로 "
                    f"적었다** --- 나머지 {n배 - 1}벌은 화면에 없다"
                    if n배 and n배 > 1 else None)})
    접은것 = [{"대표": k, "배수": v["배수"], "접힌 id": v["접힌 id"],
            "무엇": v["무엇"], "그릇": v["그릇"], "그릇 종류": v["그릇 종류"]}
           for k, v in sorted(F["접힘"].items())]
    return {
        "run_id": run_id, "그릴 수 있나": bool(블록),
        "블록": 블록, "화살표": 화살표, "묶음 상자": 묶음상자,
        "색": GROUP_COLOR,
        "레이아웃": {"방식": "위상 정렬(가장 긴 경로) + 레인",
                 "깊이 수": (max(depth.values()) + 1) if depth else 0,
                 "최대 레인": (max(lane.values()) + 1) if lane else 0,
                 "🔴 고리 있나": lay["고리 있나"],
                 "고리에 남은 노드": lay["고리에 남은 노드"] or None},
        "접었나": bool(접은것), "접은 것": 접은것,
        "펼친 것": sorted({str(x) for x in (펼침 or [])} & set(전체접힘)) or None,
        "🔴 접기 결과": (
            f"같은 부분그래프가 되풀이되는 자리 {len(전체접힘)}곳을 **구조로** 찾았다"
            + (f" · 그중 {len({str(x) for x in (펼침 or [])} & set(전체접힘))}곳은 "
               f"눌러서 펼친 상태다" if 펼침 else "")
            if 전체접힘 else
            "🔴 **되풀이를 못 찾았다** --- 같은 꼴이 여럿인 자리가 없거나, 있어도 "
            "진짜 복제 그릇(ModuleList·ModuleDict)이 아니어서 접지 않았다. "
            "**접을 게 없는 것과 못 찾은 것을 합치지 않는다**"),
        "요약": {
            "블록 수": len(블록), "접기 전 블록 수": len(nodes),
            "화살표 수": len(화살표), "접기 전 간선 수": len(edges),
            "🔴 건너뛴 화살표(잔차·우회)": sum(1 for x in 화살표 if x["건너뜀"] > 1),
            "분기 노드(나가는 간선 2개 이상)": sum(1 for i in ids if outdeg[i] > 1),
            "합류 노드(들어오는 간선 2개 이상)": sum(1 for i in ids if indeg[i] > 1),
            "묶음 수": len({n.get("묶음") for n in kept if n.get("묶음")}),
        },
        "간선 출처": a.get("간선 출처"),
        "🔴 간선 단서": a.get("🔴 간선 단서"),
        "🔴 입력 노드": G["입력 가정"] or "간선 목록에 있던 입력 노드를 그대로 썼다",
        "🔴 버린 간선": G["버린 간선"] or None,
        "총 파라미터": a.get("총 파라미터"),
        "모형 클래스": a.get("모형 클래스"),
        "말": ("블록 " + f"{len(블록):,}개 · 화살표 {len(화살표):,}개"
              + (f" · 🔴 같은 꼴 {len(접은것)}자리를 `N×` 로 접었다"
                 if 접은것 else " · 접은 것 없음")
              + (f" · 🔴 건너뛴 화살표 "
                 f"{sum(1 for x in 화살표 if x['건너뜀'] > 1)}개(잔차·우회)"
                 if any(x["건너뜀"] > 1 for x in 화살표) else "")),
    }


# ── 뉴런 단위 그림 --- 🔴 자를 때 무엇을 몇 개로 잘랐는지 적는다 ────
def _pick(n: int, k: int, norms) -> tuple:
    """뉴런 `n` 개에서 `k` 개를 고른다 --- **고른 기준을 같이 낸다.**"""
    if n <= k:
        return list(range(n)), f"전부 그렸다({n}개)", False
    if norms and len(norms) >= n:
        idx = sorted(range(n), key=lambda i: -abs(norms[i]))[:k]
        return (sorted(idx),
                f"🔴 **가중치 행 L2 노름이 큰 순으로 {k}개**를 골랐다 "
                f"(노름은 그 출력 뉴런이 입력 전체에 대해 가진 가중치의 크기다). "
                f"인덱스는 원래 자리를 그대로 썼다", True)
    step = n / k
    idx = sorted({min(n - 1, int(i * step)) for i in range(k)})
    return (idx,
            f"🔴 **고른 간격으로 {len(idx)}개**를 골랐다 --- "
            f"**가중치를 못 읽어서 세기로 고를 수 없었다**", True)


def _caps(층수_깊이별: dict, 사용자max: int, 요청px: int) -> dict:
    """🔴 **자를 개수를 화면 높이와 가독 밀도에서 역산한다**(판 1.1.0).

    판 1.0.0 은 층마다 **고정 32개**로 잘랐다. 그래서 12짜리 층과 1,024짜리 층이
    화면에서 같은 크기로 보였다 --- **크기 정보가 사라졌다**.

    여기서 정하는 것은 층마다의 **상한**이고, 그 상한은 이렇게 나온다.

        필요 높이 = 여백 + (한 깊이에 몰린 노드 수) × (최소 점 수 × 점당 픽셀 + 이름표)
        그림 높이 = clamp(max(요청 높이, 사용자 상한이 요구하는 높이, 필요 높이), 320, 1600)
        레인 몫   = (그림 높이 - 여백) ÷ (그 깊이의 노드 수) - 이름표
        상한      = clamp(레인 몫 ÷ 점당 픽셀, 4, 사용자 상한)

    그래서 **한 깊이에 노드가 몰릴수록 그 깊이의 상한이 작아진다**(자리가 좁으니까).
    실제로 자를지는 층마다 다르다 --- `n ≤ 상한` 이면 **전부 그린다**.
    """
    L최대 = max(층수_깊이별.values()) if 층수_깊이별 else 1
    필요 = PAD_PX + L최대 * (MIN_DOTS * NEURON_PX + LABEL_PX)
    원함 = PAD_PX + L최대 * (사용자max * NEURON_PX + LABEL_PX)
    px = int(max(요청px, min(원함, MAX_CANVAS), min(필요, MAX_CANVAS)))
    px = max(MIN_CANVAS, min(MAX_CANVAS, px))
    cap: dict = {}
    for d, L in 층수_깊이별.items():
        몫 = (px - PAD_PX) / max(1, L) - LABEL_PX
        cap[d] = max(4, min(int(사용자max), int(몫 // NEURON_PX)))
    return {"그림 높이": px, "깊이별 상한": cap, "최대 레인": L최대,
            "점당 픽셀": NEURON_PX, "이름표 픽셀": LABEL_PX,
            "🔴 어떻게 정했나": (
                f"그림 높이 {px}px 에서 역산했다 --- 한 깊이에 최대 {L최대}개가 "
                f"몰리고, 점 하나에 {NEURON_PX}px · 이름표에 {LABEL_PX}px 를 준다. "
                f"층 크기가 상한보다 작으면 **전부 그린다**")}


def neurons(run_id: str, max_per_layer: int = 32, root=None,
            px_height: int = 620, max_edges: int = EDGE_BUDGET) -> dict:
    """아키텍처를 **뉴런 하나 = 점 하나**로 펴 놓은 그림 계획(드릴다운).

    판 1.1.0 에서 셋이 바뀌었다.

      ① 🔴 **간선을 `arch.json` 의 `간선` 에서 가져온다** --- 층을 차례로 잇지 않는다.
         잔차·분기·합류가 그림에 **실제로** 나온다.
      ② 🔴 **자르는 개수를 화면에서 역산한다**(`_caps`) --- 고정 32가 아니다.
      ③ 🔴 **간선도 자른다.** 전결합을 다 그으면 흰 안개가 되고 정보가 0 이다.
         가중치가 있으면 **세기 상위**만, 없으면 **연결 띠 하나**로 그린다.
         무엇을 몇 개 중 몇 개 그렸는지 **간선마다 적는다.**
    """
    a = read_arch(run_id, root)
    if not a.get("읽음"):
        return {"run_id": run_id, "그릴 수 있나": False,
                "왜": a.get("왜 못 읽음") or "아키텍처를 못 읽었다",
                "층": [], "간선": [], "잘린 층": [],
                "말": "**아무것도 그리지 않는다** --- 아키텍처를 못 읽었다"}
    G = _base_graph(a)
    nodes, edges = G["노드"], G["간선"]
    가중치읽음 = bool(a.get("가중치를 읽었나"))
    ids = [n["id"] for n in nodes]
    lay = _layer_depths(ids, edges)
    깊이 = lay["깊이"]
    깊이별: dict = {}
    for i in ids:
        깊이별[깊이[i]] = 깊이별.get(깊이[i], 0) + 1
    C = _caps(깊이별, int(max_per_layer), int(px_height))
    n_max = max([int(n.get("뉴런 수") or 0) for n in nodes] or [1]) or 1
    import math
    층 = []
    for N in nodes:
        n = N.get("뉴런 수")
        w = N.get("가중치") or {}
        cap = C["깊이별 상한"][깊이[N["id"]]]
        공통 = {"id": N["id"], "이름": N.get("이름") or N["id"],
              "종류": N.get("종류"), "파라미터 수": N.get("파라미터 수"),
              "활성함수": N.get("활성함수"), "깊이": 깊이[N["id"]],
              "색 갈래": kind_group(N.get("종류")), "이 층의 상한": cap}
        if not n:
            층.append({**공통, "전체 뉴런": None, "그린 뉴런": 0, "인덱스": [],
                      "잘림": False, "크기 눈금": 0.0,
                      "고른 기준": "🔴 **뉴런 수를 못 읽었다** --- 이 층은 점으로 "
                              "안 그리고 상자로만 그린다",
                      "말": "🔴 **뉴런 수를 못 읽었다**(0개가 아니다 · 조항 59)"})
            continue
        n = int(n)
        idx, 기준, cut = _pick(n, cap, w.get("행 노름"))
        층.append({**공통, "전체 뉴런": n, "그린 뉴런": len(idx), "인덱스": idx,
                  "잘림": cut,
                  #: 🔴 잘린 층도 **크기가 보이게** --- 열 높이를 로그 눈금으로 준다
                  "크기 눈금": round(math.log2(n + 1) / math.log2(n_max + 1), 4),
                  "고른 기준": (기준 + f" (이 깊이의 상한 {cap}개 --- {C['🔴 어떻게 정했나']})"
                            if cut else 기준),
                  "말": (f"🔴 **{n:,}개 중 {len(idx):,}개만 그렸다** --- {기준}"
                        if cut else f"{n:,}개를 전부 그렸다")})
    by_layer = {L["id"]: L for L in 층}
    src_by_id = {str(L["id"]): L for L in (a.get("층") or [])}
    indeg: dict = {i: 0 for i in ids}
    for e in edges:
        indeg[e["to"]] += 1
    예산 = max(MIN_EDGE_LINES, int(max_edges) // max(1, len(edges)))
    간선 = []
    for e in edges:
        앞, 뒤 = by_layer.get(e["from"]), by_layer.get(e["to"])
        L = src_by_id.get(e["to"])
        w = (L or {}).get("가중치") or {}
        val = w.get("값") if w.get("담음") else None
        a_idx = (앞 or {}).get("인덱스") or []
        b_idx = (뒤 or {}).get("인덱스") or []
        전체쌍 = ((앞 or {}).get("전체 뉴런") or 0) * ((뒤 or {}).get("전체 뉴런") or 0)
        그릴쌍 = len(a_idx) * len(b_idx)
        row = {"from": e["from"], "to": e["to"],
               "건너뜀": 깊이[e["to"]] - 깊이[e["from"]],
               "세기": None, "세기 있나": False, "왜": None,
               "전체 뉴런쌍": 전체쌍 or None, "그릴 수 있는 뉴런쌍": 그릴쌍,
               "그린 선": 0, "그리기 방식": "못 그림", "선": None,
               "고른 기준": None}
        if not a_idx or not b_idx:
            row["왜"] = "한쪽 층의 뉴런을 못 그려서 간선도 못 그린다"
            row["고른 기준"] = row["왜"]
            간선.append(row)
            continue
        if val is not None and indeg[e["to"]] > 1:
            #: 🔴 **자가 적발.** 합류 노드에서는 가중치 행렬을 **어느 간선에 붙일지**
            #: 규격이 정하지 않는다. 판 1.0.0 은 사슬만 가정했기에 이 자리가 없었다.
            #: 아무 간선에나 붙이면 **없는 세기를 지어내는 것**이라 안 붙인다.
            val = None
            row["왜"] = (f"🔴 이 층에 들어오는 간선이 {indeg[e['to']]}개다(합류) --- "
                        f"가중치 행렬을 **어느 간선에 붙일지 규격이 정하지 않았다**. "
                        f"아무 데나 붙이면 지어내는 것이라 **구조만 그렸다**")
        elif val is None:
            row["왜"] = ("🔴 **가중치를 못 읽어 구조만 그렸다** --- "
                        + str(w.get("왜") or "이 층에 가중치가 없다"))
        elif len(val) < max(b_idx) + 1 or (
                (앞 or {}).get("전체 뉴런") and len(val[0]) != 앞["전체 뉴런"]):
            row["왜"] = (f"🔴 가중치 모양 {w.get('모양')} 이 앞 층 뉴런 수 "
                        f"{앞.get('전체 뉴런')} 과 안 맞아 **구조만 그렸다**")
            val = None
        if val is None:
            #: 🔴 세기를 모르면 **선을 다 긋지 않는다** --- 전결합은 흰 안개다.
            row["그리기 방식"] = "띠"
            row["그린 선"] = 0
            row["고른 기준"] = (
                f"🔴 **선을 하나도 안 그리고 연결 띠 하나로 묶었다** --- "
                f"뉴런쌍 {전체쌍:,}개(그릴 수 있는 것 {그릴쌍:,}개)를 다 그으면 "
                f"흰 안개가 되고 **읽을 수 있는 정보가 0** 이다. "
                f"세기를 모르므로 굵기에도 뜻이 없다")
            간선.append(row)
            continue
        # 세기가 있다 --- 상위만 고른다
        M = [[round(float(val[o][i2]), 6) for i2 in a_idx] for o in b_idx]
        if 그릴쌍 <= MAX_STRENGTH_ELEMS:
            row["세기"] = M
            row["세기 있나"] = True
            row["세기 뜻"] = "행 = 뒤 층의 그린 뉴런 · 열 = 앞 층의 그린 뉴런"
        else:
            row["왜"] = (f"세기 {그릴쌍:,}개가 한도 {MAX_STRENGTH_ELEMS:,} 를 넘어 "
                        f"행렬은 안 보내고 **고른 선만** 보낸다")
        pairs = [(abs(M[b][c]), b, c) for b in range(len(b_idx))
                 for c in range(len(a_idx))]
        if len(pairs) <= 예산:
            선 = [[b, c, M[b][c]] for _v, b, c in pairs]
            row["그리기 방식"] = "선(전부)"
            row["고른 기준"] = (f"그릴 수 있는 뉴런쌍 {그릴쌍:,}개를 **전부** 그렸다"
                            f"(예산 {예산:,}개 안에 든다)")
        else:
            pairs.sort(key=lambda t: -t[0])
            top = pairs[:예산]
            선 = [[b, c, M[b][c]] for _v, b, c in top]
            row["그리기 방식"] = "선(세기 상위)"
            row["고른 기준"] = (
                f"🔴 뉴런쌍 {전체쌍:,}개 중 그릴 수 있는 {그릴쌍:,}개에서 다시 "
                f"**|세기| 상위 {len(선):,}개**만 그렸다(간선 예산 {int(max_edges):,} ÷ "
                f"간선 {len(edges)}개 = {예산:,}). 나머지는 **화면에 없다**")
        row["그린 선"] = len(선)
        row["선"] = 선
        간선.append(row)
    잘린 = [L for L in 층 if L.get("잘림")]
    총전체쌍 = sum(int(e["전체 뉴런쌍"] or 0) for e in 간선)
    총그린선 = sum(int(e["그린 선"] or 0) for e in 간선)
    띠 = sum(1 for e in 간선 if e["그리기 방식"] == "띠")
    return {
        "run_id": run_id, "그릴 수 있나": bool(층),
        "층": 층, "간선": 간선,
        "층당 최대": max_per_layer,
        "자르기 역산": C,
        "레이아웃": {"방식": "위상 정렬(가장 긴 경로) + 레인",
                 "깊이 수": (max(깊이.values()) + 1) if 깊이 else 0,
                 "깊이별 노드 수": {str(k): v for k, v in sorted(깊이별.items())},
                 "🔴 고리 있나": lay["고리 있나"]},
        "가중치를 읽었나": 가중치읽음,
        "간선 출처": a.get("간선 출처"),
        "🔴 간선 단서": a.get("🔴 간선 단서"),
        "🔴 이 그림의 가정": (
            "🔴 판 1.1.0 --- 간선은 **`arch.json` 의 `간선` 그대로**다(층을 차례로 "
            "잇지 않는다). 잔차·분기·합류가 있으면 그대로 나온다. 다만 `간선 출처` 가 "
            "「모듈 등록 순서(가정)」이면 **그 간선 자체가 가정**이다"),
        "잘린 층": [{"층": L["이름"], "전체": L["전체 뉴런"],
                 "그린 것": L["그린 뉴런"], "기준": L["고른 기준"]} for L in 잘린],
        "🔴 간선 표": [{"from": e["from"], "to": e["to"],
                   "전체 뉴런쌍": e["전체 뉴런쌍"],
                   "그릴 수 있는 뉴런쌍": e["그릴 수 있는 뉴런쌍"],
                   "그린 선": e["그린 선"], "방식": e["그리기 방식"],
                   "기준": e["고른 기준"] or e["왜"]} for e in 간선],
        "🔴 간선을 몇 개 중 몇 개 그렸나": (
            f"뉴런쌍 {총전체쌍:,}개 중 **선 {총그린선:,}개**를 그렸다"
            + (f" · 세기를 모르는 간선 {띠}개는 **연결 띠 하나**로 묶었다" if 띠 else "")),
        "말": (("🔴 " + " · ".join(
            f"{L['이름']}: {L['전체 뉴런']:,}개 중 {L['그린 뉴런']:,}개만 그렸다"
            for L in 잘린)) if 잘린 else "모든 층을 뉴런 하나까지 다 그렸다")
        + (" · 세기는 가중치에서 왔다" if 가중치읽음
           else " · 🔴 **가중치를 못 읽어 구조만 그렸다**"),
    }


# ── 🔴 실시간 --- append-only 를 **이어 읽는다**(판 1.1.0 · 노트 913) ──
#: 마지막 지표 이후 이만큼 지나면 「도는 중」이 아니라 **「멈춘 지 오래됨」**이다.
STALE_SECS = 20


def tail_metrics(run_id: str, since_bytes: int = 0, root=None,
                 max_new: int = 20000) -> dict:
    """🔴 **새로 붙은 줄만** 읽는다 --- 매번 전량 재전송을 안 한다.

    `metrics.jsonl` 은 append-only 다. 그래서 **바이트 오프셋**으로 이어 읽으면
    되고, 그것이 「지금까지 몇 줄이었나」를 쓰는 것보다 싸다(앞을 안 훑는다).

    🔴 **마지막 줄이 반쯤 쓰였을 수 있다.** 개행으로 끝나지 않는 꼬리는 **안 읽고**
    오프셋도 안 옮긴다 --- 다음에 다시 읽는다. 반쯤 쓰인 줄을 파싱해서 값을
    만들어 내면 그것이 **지어낸 점**이다.
    """
    d = run_dir(run_id, root)
    p = d / "metrics.jsonl"
    if not p.exists():
        return {"run_id": run_id, "상태": "없다", "새 점": [], "새 줄 수": 0,
                "다음 바이트": 0, "파일 바이트": 0,
                "왜": "`metrics.jsonl` 이 없다 --- 이 run 은 지표를 한 줄도 안 남겼다"}
    size = p.stat().st_size
    off = int(since_bytes or 0)
    되감음 = None
    if off > size:
        되감음 = (f"🔴 준 오프셋 {off:,} 이 파일 크기 {size:,} 보다 크다 --- "
               f"파일이 줄었거나 다른 run 이다. **처음부터 다시 읽는다**")
        off = 0
    if off < 0:
        off = 0
    try:
        with p.open("rb") as f:
            f.seek(off)
            buf = f.read()
    except Exception as e:
        return {"run_id": run_id, "상태": "못 읽었다", "새 점": [], "새 줄 수": 0,
                "다음 바이트": off, "파일 바이트": size,
                "왜": f"{type(e).__name__}: {e}"}
    end = buf.rfind(b"\n")
    if end < 0:
        return {"run_id": run_id, "상태": "읽었다", "새 점": [], "새 줄 수": 0,
                "다음 바이트": off, "파일 바이트": size, "되감음": 되감음,
                "말": "🔴 아직 **줄이 다 안 쓰였다** --- 반쯤 쓰인 줄은 안 읽는다"}
    full = buf[:end + 1]
    새점, 나쁨, n, 수아님 = [], 0, 0, 0
    마지막t = None
    for line in full.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception:
            나쁨 += 1
            continue
        if "name" not in o:
            continue
        n += 1
        마지막t = o.get("t") or 마지막t
        v = o.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if len(새점) < max_new:
                새점.append({"step": o.get("step"),
                            "split": str(o.get("split") or "?"),
                            "name": str(o.get("name")), "value": float(v)})
        else:
            수아님 += 1
    return {"run_id": run_id, "상태": "읽었다", "새 점": 새점, "새 줄 수": n,
            "수가 아닌 줄 수": 수아님,
            "JSON 이 아닌 줄 수": 나쁨,
            "다음 바이트": off + len(full), "파일 바이트": size,
            "되감음": 되감음, "마지막 지표 UTC": 마지막t,
            "말": "🔴 **새로 붙은 줄만** 읽었다 --- 앞의 점은 다시 안 보낸다"}


def liveness(run_id: str, root=None, stale: int = STALE_SECS) -> dict:
    """🔴 **「도는 중」과 「멈춘 지 오래됨」과 「끝남」을 가른다**(조항 59).

    `manifest.json` 의 `상태` 는 **쓴 쪽이 적은 것**이라 프로세스가 조용히 죽으면
    「도는 중」인 채로 남는다. 그래서 읽는 쪽이 **마지막 지표가 언제였나**를 직접
    재서 셋을 가른다. 🔴 프로세스가 살아 있는지는 **이 창구가 모른다** --- 그래서
    「죽었다」가 아니라 「멈춘 지 오래됨」이라고 적는다.
    """
    import time as _t
    m = read_manifest(run_id, root)
    d = run_dir(run_id, root)
    p = d / "metrics.jsonl"
    상태 = m.get("상태")
    마지막, 어떻게 = None, "지표 파일이 없다"
    if p.exists():
        try:
            마지막 = p.stat().st_mtime
            어떻게 = "`metrics.jsonl` 이 마지막으로 쓰인 시각(파일 mtime)"
        except Exception:
            마지막 = None
    나이 = None if 마지막 is None else max(0.0, _t.time() - 마지막)
    if 상태 == "끝남":
        뱃지, 말 = "끝남", "쓴 쪽이 `finish()` 로 정상 종료를 적었다"
    elif 상태 == "터짐":
        뱃지, 말 = "🔴 터짐", (m.get("터진 이유")
                          or "쓴 쪽이 「터짐」으로 적었다")
    elif 상태 == "도는 중":
        if 나이 is None:
            뱃지, 말 = "🔴 도는 중인데 지표가 없다", (
                "「도는 중」이라고 적혀 있는데 `metrics.jsonl` 이 없다")
        elif 나이 > stale:
            뱃지, 말 = "🔴 멈춘 지 오래됨", (
                f"「도는 중」인데 마지막 지표가 **{나이:.0f}초 전**이다(문턱 {stale}초). "
                f"🔴 **「끝났다」가 아니다** --- 프로세스가 살아 있는지 이 창구는 "
                f"모른다. 학습이 느린 것일 수도, 조용히 죽은 것일 수도 있다")
        else:
            뱃지, 말 = "● 도는 중", f"마지막 지표가 {나이:.0f}초 전이다"
    else:
        뱃지, 말 = "🔴 상태를 못 읽었다", f"모르는 상태 `{상태}`"
    return {"run_id": run_id, "뱃지": 뱃지, "상태(manifest)": 상태,
            "마지막 지표 이후 초": (None if 나이 is None else round(나이, 1)),
            "문턱 초": stale, "무엇으로 쟀나": 어떻게, "말": 말,
            "파일 바이트": (p.stat().st_size if p.exists() else 0)}
