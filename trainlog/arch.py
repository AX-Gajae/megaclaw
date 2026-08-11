"""아키텍처 그래프 --- **뉴럴넷을 있는 그대로 적는다.** 노트 912 팔 ㅇ.

층마다 (이름 · 종류 · 입력/출력 모양 · 파라미터 수 · 활성함수)를 적고 층 사이를
**간선**으로 잇는다. 그림(`serve/static/trainlog.html`)은 이 파일만 읽는다.

# 🔴 torch 는 **선택**이다

`r.arch(model)` 은 셋 중 하나를 한다.

    torch 모듈이면   introspect 한다            출처 = "torch introspect"
    dict 를 주면     그대로 받는다              출처 = "준 dict"
    아무것도 없으면   **「아키텍처 못 읽음」으로 기록**   출처 = "못 읽음"

조항 59: **'없다' 와 '못 봤다' 와 '못 읽었다' 는 셋이다.** 그래서 셋째 갈래를
빈 그래프로 뭉개지 않고 `읽음: false` + `왜 못 읽음` 으로 남긴다.

# 🔴 간선은 어디서 왔나를 적는다

`torch.fx.symbolic_trace` 가 되면 **실제 호출 그래프**를 쓰고, 안 되면 **모듈
등록 순서로 이은 가정**을 쓴다. 둘은 다른 물건이고 두 번째는 틀릴 수 있다
(`nn.Module` 이 forward 에서 순서를 바꾸거나 건너뛸 수 있다). 그러므로
`간선 출처` 칸에 어느 쪽인지 **반드시** 적고 화면에도 띄운다.

# 🔴 가중치는 못 담을 수 있다

행렬이 크면 안 담는다. 그때는 `가중치.담음 = false` 와 이유를 적고, 그림은
**「구조만 그렸다」**로 표시한다. 세기를 못 읽었는데 굵기를 그리면 그것이 지어낸
그림이다.
"""
from __future__ import annotations

from .spec import ARCH_SPEC, EDGE_SOURCES

#: 이 크기를 넘는 가중치 행렬은 **값을 안 담는다**(파일이 학습보다 무거워진다).
MAX_WEIGHT_ELEMS = 4096
#: 행 노름은 값보다 훨씬 싸다 --- 이만큼까지는 담아 뉴런 고르기에 쓴다.
MAX_NORM_ROWS = 8192

#: 활성함수로 볼 모듈 이름. 층 목록에서 **앞 층의 활성함수 칸**으로 접는다.
ACTIVATIONS = {
    "ReLU", "LeakyReLU", "GELU", "SiLU", "ELU", "SELU", "CELU", "Tanh",
    "Sigmoid", "Softmax", "LogSoftmax", "Hardtanh", "Mish", "PReLU",
    "Softplus", "Hardswish", "Hardsigmoid", "GLU", "ReLU6",
}


def _fail(why: str, 무엇: str = "") -> dict:
    """🔴 **못 읽음** --- 빈 그래프가 아니다."""
    return {"규격": ARCH_SPEC, "읽음": False, "출처": "못 읽음",
            "왜 못 읽음": why, "무엇을 받았나": 무엇,
            "층": [], "간선": [], "간선 출처": "없음",
            "총 파라미터": None, "가중치를 읽었나": False,
            "말": "**아키텍처를 못 읽었다** --- 「없다」가 아니다(조항 59). "
                 "그림은 이 run 에 대해 아무것도 그리지 않는다"}


def _shape(x):
    if x is None:
        return None
    try:
        return [None if v is None else int(v) for v in x]
    except Exception:
        return None


def from_dict(d: dict) -> dict:
    """사람이 손으로 준 그래프 --- **그대로 받되 칸은 채운다.**"""
    층 = []
    for i, L in enumerate(d.get("층") or d.get("layers") or []):
        L = dict(L)
        층.append({
            "id": str(L.get("id") or L.get("이름") or L.get("name") or f"L{i}"),
            "이름": str(L.get("이름") or L.get("name") or L.get("id") or f"L{i}"),
            "종류": str(L.get("종류") or L.get("kind") or L.get("type") or "모름"),
            "입력 모양": _shape(L.get("입력 모양") or L.get("in_shape")),
            "출력 모양": _shape(L.get("출력 모양") or L.get("out_shape")),
            "파라미터 수": L.get("파라미터 수", L.get("params")),
            "활성함수": L.get("활성함수") or L.get("act"),
            "뉴런 수": L.get("뉴런 수", L.get("units")),
            "입력 뉴런 수": L.get("입력 뉴런 수", L.get("in_units")),
            "가중치": L.get("가중치") or {"있나": False, "담음": False,
                                    "왜": "준 dict 에 가중치가 없다"},
        })
    간선 = [{"from": str(e[0]), "to": str(e[1])} if isinstance(e, (list, tuple))
          else {"from": str(e.get("from")), "to": str(e.get("to"))}
          for e in (d.get("간선") or d.get("edges") or [])]
    tot = d.get("총 파라미터")
    if tot is None:
        vals = [L["파라미터 수"] for L in 층 if isinstance(L["파라미터 수"], int)]
        tot = sum(vals) if vals else None
    return {"규격": ARCH_SPEC, "읽음": True, "출처": "준 dict",
            "왜 못 읽음": None, "층": 층, "간선": 간선,
            "간선 출처": "준 dict",
            "총 파라미터": tot,
            "가중치를 읽었나": any((L.get("가중치") or {}).get("담음") for L in 층),
            "말": "사람이 준 그래프를 그대로 받았다 --- **이 저장소가 introspect 한 "
                 "것이 아니다**"}


# ── torch introspection ───────────────────────────────────────────
def _weights(mod, keep: bool) -> dict:
    """가중치를 담을 수 있나 --- **못 담으면 못 담았다고 적는다.**"""
    w = getattr(mod, "weight", None)
    if w is None:
        return {"있나": False, "담음": False, "왜": "이 모듈에 weight 가 없다"}
    try:
        shape = [int(v) for v in w.shape]
        n = 1
        for v in shape:
            n *= v
        out = {"있나": True, "모양": shape, "요소 수": n, "담음": False}
        flat = w.detach().reshape(shape[0], -1) if len(shape) >= 2 else None
        if flat is not None and shape[0] <= MAX_NORM_ROWS:
            out["행 노름"] = [round(float(v), 6)
                           for v in flat.norm(dim=1).tolist()]
            out["행 노름 뜻"] = ("출력 뉴런 하나가 입력 전체에 대해 가진 가중치의 "
                            "L2 노름 --- **큰 층에서 뉴런을 고를 때 이것으로 고른다**")
        elif flat is not None:
            out["행 노름"] = None
            out["행 노름 없는 이유"] = f"행이 {shape[0]:,}개로 {MAX_NORM_ROWS:,} 를 넘는다"
        if not keep:
            out["왜"] = "부르는 쪽이 `weights=False` 로 껐다"
        elif n > MAX_WEIGHT_ELEMS:
            out["왜"] = (f"요소 {n:,}개가 한도 {MAX_WEIGHT_ELEMS:,} 를 넘어 **값을 "
                       f"안 담았다** --- 그림은 「구조만」이 된다")
        elif len(shape) != 2:
            out["왜"] = (f"{len(shape)}차 텐서라 뉴런×뉴런 간선으로 못 편다 --- "
                       f"값을 안 담았다(그림은 「구조만」)")
        else:
            out["담음"] = True
            out["값"] = [[round(float(x), 6) for x in row]
                        for row in w.detach().tolist()]
        return out
    except Exception as e:
        return {"있나": True, "담음": False,
                "왜": f"가중치를 읽다가 터졌다: {type(e).__name__}: {e}"}


def _io(mod) -> tuple:
    """모듈에서 입력/출력 폭을 읽는다 --- **모르면 `None` 이지 0 이 아니다.**"""
    for a, b in (("in_features", "out_features"),
                 ("in_channels", "out_channels"),
                 ("input_size", "hidden_size"),
                 ("num_embeddings", "embedding_dim")):
        if hasattr(mod, a) and hasattr(mod, b):
            return int(getattr(mod, a)), int(getattr(mod, b))
    if hasattr(mod, "normalized_shape"):
        try:
            n = int(list(mod.normalized_shape)[-1])
            return n, n
        except Exception:
            pass
    if hasattr(mod, "num_features"):
        n = int(mod.num_features)
        return n, n
    return None, None


def _fx_edges(model, fold: dict) -> tuple:
    """`torch.fx` 로 **실제 호출 그래프**를 뜬다 --- 안 되면 `(None, 이유)`.

    `fold` 는 *모듈 이름 → 그림에 남은 층 id* 다(활성함수는 앞 층으로 접혔으므로
    앞 층 id 를 가리킨다). 🔴 **이름이 없는 노드**(`F.relu` 같은 call_function ·
    `getattr` · `add`)는 **투명하게 통과**시킨다 --- 안 그러면 그 자리에서 사슬이
    끊겨 간선이 사라지고, 사라진 간선은 화면에서 **없는 연결**로 보인다.
    """
    try:
        import torch.fx as fx
        g = fx.symbolic_trace(model).graph
        alias = {}
        for node in g.nodes:
            if node.op == "call_module":
                alias[node.name] = fold.get(str(node.target))
            elif node.op == "placeholder":
                alias[node.name] = "__입력__"
            else:
                alias[node.name] = None
        memo: dict = {}

        def upstream(node) -> set:
            """이 노드가 **실질적으로** 어느 층에서 왔나(이름 없는 노드는 통과)."""
            if node.name in memo:
                return memo[node.name]
            memo[node.name] = set()           # 순환 방어
            a = alias.get(node.name)
            if a:
                memo[node.name] = {a}
            else:
                s: set = set()
                for p in node.all_input_nodes:
                    s |= upstream(p)
                memo[node.name] = s
            return memo[node.name]

        edges, seen = [], set()
        for node in g.nodes:
            dst = alias.get(node.name)
            if not dst:
                continue
            for p in node.all_input_nodes:
                for s in upstream(p):
                    if s != dst and (s, dst) not in seen:
                        seen.add((s, dst))
                        edges.append({"from": s, "to": dst})
        return (edges, None) if edges else (None, "fx 가 간선을 하나도 안 냈다")
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def from_torch(model, weights: bool = True) -> dict:
    """`nn.Module` 을 층 목록 + 간선으로 편다.

    **잎 모듈만** 층으로 센다(컨테이너는 층이 아니다). 활성함수 모듈은 별도 층으로
    두지 않고 **앞 층의 `활성함수` 칸**으로 접는다 --- 뉴런 그림에서 같은 뉴런
    집합을 두 번 그리게 되기 때문이다. 접었다는 사실은 `접은 활성함수` 에 남긴다.
    """
    leaves = [(n, m) for n, m in model.named_modules()
              if n and not list(m.children())]
    if not leaves:
        #: 🔴 `nn.Linear(4,4)` 하나를 그냥 준 경우 --- `named_modules()` 가 이름 없는
        #: 자기 자신만 낸다. **「잎이 없다」가 아니라 「잎이 자기 자신이다」** 이므로
        #: 그렇게 적고 계속 간다(한 번 IndexError 로 시험이 터져서 알았다).
        if not list(model.children()):
            leaves = [(type(model).__name__, model)]
        else:
            return _fail("torch 모듈인데 **잎 모듈이 하나도 없다** --- 층을 못 셌다",
                         type(model).__name__)
    #: 모듈 이름 → **그림에 남은 층 id**. 접힌 활성함수는 앞 층을 가리킨다.
    fold: dict = {}
    층, 접음, prev = [], [], None
    for n, m in leaves:
        kind = type(m).__name__
        if kind in ACTIVATIONS and prev is not None:
            prev["활성함수"] = kind
            fold[n] = prev["id"]
            접음.append({"모듈": n, "종류": kind, "붙인 층": prev["id"]})
            continue
        i, o = _io(m)
        p = sum(int(x.numel()) for x in m.parameters(recurse=False))
        row = {
            "id": n, "이름": n, "종류": kind,
            "입력 모양": [None, i] if i else None,
            "출력 모양": [None, o] if o else None,
            "파라미터 수": p,
            "활성함수": kind if kind in ACTIVATIONS else None,
            "뉴런 수": o, "입력 뉴런 수": i,
            "가중치": _weights(m, weights),
        }
        층.append(row)
        fold[n] = row["id"]
        prev = row
    edges, why = _fx_edges(model, fold)
    if edges:
        src = "torch.fx 추적"
    else:
        src = "모듈 등록 순서(가정)"
        edges = ([{"from": "__입력__", "to": 층[0]["id"]}] if 층[0].get("입력 뉴런 수")
                 else [])
        edges += [{"from": 층[i]["id"], "to": 층[i + 1]["id"]}
                  for i in range(len(층) - 1)]
    tot = sum(int(x.numel()) for x in model.parameters())
    train = sum(int(x.numel()) for x in model.parameters() if x.requires_grad)
    assert src in EDGE_SOURCES
    return {
        "규격": ARCH_SPEC, "읽음": True, "출처": "torch introspect",
        "왜 못 읽음": None,
        "모형 클래스": type(model).__name__,
        "층": 층, "간선": edges, "간선 출처": src,
        "🔴 간선 단서": ("실제 호출 그래프다(`torch.fx`)" if src == "torch.fx 추적"
                   else f"🔴 **가정이다** --- `torch.fx` 가 실패해서"
                        f"(`{why}`) 모듈 **등록 순서**로 이었다. forward 가 순서를 "
                        f"바꾸거나 건너뛰면 이 간선은 틀린다"),
        "접은 활성함수": 접음 or None,
        "총 파라미터": tot, "학습 가능 파라미터": train,
        "가중치를 읽었나": any(L["가중치"].get("담음") for L in 층),
        "말": ("가중치까지 읽었다" if any(L["가중치"].get("담음") for L in 층)
              else "🔴 **구조만 읽었다** --- 가중치 값을 안 담았다(층마다 `가중치.왜`)"),
    }


def extract(model=None, weights: bool = True) -> dict:
    """무엇이 오든 셋 중 하나로 답한다 --- **셋째가 「못 읽음」이다.**"""
    if model is None:
        return _fail("`arch()` 에 아무것도 안 줬다 --- 이 run 은 아키텍처를 "
                     "**기록하지 않았다**", "None")
    if isinstance(model, dict):
        try:
            return from_dict(model)
        except Exception as e:
            return _fail(f"준 dict 를 못 읽었다: {type(e).__name__}: {e}", "dict")
    try:
        import torch.nn as nn
    except Exception as e:
        return _fail(f"torch 가 없어서 introspect 를 못 한다({type(e).__name__}) --- "
                     f"dict 로 주면 그대로 받는다", type(model).__name__)
    if isinstance(model, nn.Module):
        try:
            return from_torch(model, weights=weights)
        except Exception as e:
            return _fail(f"torch 모듈을 읽다가 터졌다: {type(e).__name__}: {e}",
                         type(model).__name__)
    return _fail(f"torch 모듈도 dict 도 아니다 --- `{type(model).__name__}` 을 "
                 f"어떻게 층으로 펴야 하는지 모른다", type(model).__name__)
