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
        })
        if len(rows) >= limit:
            break
    return {"상태": "읽었다" if rows else "비었다", "경로": "data/trainlog",
            "run 수": len(rows), "run": rows,
            "🔴 단서": "「지표 줄 수(manifest)」는 **쓴 쪽이 적은 수**이고 "
                   "「읽어 센 것」은 **이 창구가 직접 센 수**다. 어긋나면 "
                   "`수가 어긋나나` 가 참이 된다(조항 60)"}


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


def neurons(run_id: str, max_per_layer: int = 32, root=None) -> dict:
    """아키텍처를 **뉴런 하나 = 점 하나**로 펴 놓은 그림 계획.

    🔴 **큰 층은 다 못 그린다.** 그때 잘랐다는 사실과 **무엇을 기준으로 골랐는지**를
    층마다 `말` 로 낸다 --- 화면이 그 문장을 그대로 띄운다. 조용히 자르면 그것이
    조항 59 위반이다.
    """
    a = read_arch(run_id, root)
    if not a.get("읽음"):
        return {"run_id": run_id, "그릴 수 있나": False,
                "왜": a.get("왜 못 읽음") or "아키텍처를 못 읽었다",
                "층": [], "간선": [], "잘린 층": [],
                "말": "**아무것도 그리지 않는다** --- 아키텍처를 못 읽었다"}
    src = a.get("층") or []
    가중치읽음 = bool(a.get("가중치를 읽었나"))
    층 = []
    #: 첫 층의 입력을 **가짜 층 하나**로 세운다 --- 입력 뉴런도 점이어야 한다
    if src and src[0].get("입력 뉴런 수"):
        n = int(src[0]["입력 뉴런 수"])
        idx, 기준, cut = _pick(n, max_per_layer, None)
        층.append({"id": "__입력__", "이름": "입력", "종류": "입력",
                  "전체 뉴런": n, "그린 뉴런": len(idx), "인덱스": idx,
                  "잘림": cut, "고른 기준": 기준, "파라미터 수": 0,
                  "활성함수": None,
                  "말": (f"🔴 **{n:,}개 중 {len(idx):,}개만 그렸다** --- {기준}"
                        if cut else f"{n:,}개를 전부 그렸다")})
    for L in src:
        n = L.get("뉴런 수")
        w = L.get("가중치") or {}
        if not n:
            층.append({"id": L["id"], "이름": L["이름"], "종류": L["종류"],
                      "전체 뉴런": None, "그린 뉴런": 0, "인덱스": [],
                      "잘림": False,
                      "고른 기준": "🔴 **뉴런 수를 못 읽었다** --- 이 층은 점으로 "
                              "안 그리고 상자로만 그린다",
                      "파라미터 수": L.get("파라미터 수"),
                      "활성함수": L.get("활성함수"),
                      "말": "🔴 **뉴런 수를 못 읽었다**(0개가 아니다 · 조항 59)"})
            continue
        n = int(n)
        idx, 기준, cut = _pick(n, max_per_layer, w.get("행 노름"))
        층.append({"id": L["id"], "이름": L["이름"], "종류": L["종류"],
                  "전체 뉴런": n, "그린 뉴런": len(idx), "인덱스": idx,
                  "잘림": cut, "고른 기준": 기준,
                  "파라미터 수": L.get("파라미터 수"),
                  "활성함수": L.get("활성함수"),
                  "말": (f"🔴 **{n:,}개 중 {len(idx):,}개만 그렸다** --- {기준}"
                        if cut else f"{n:,}개를 전부 그렸다")})
    #: 간선 --- 이웃한 두 층 사이. 가중치가 있으면 세기를, 없으면 **구조만**.
    간선 = []
    by_id = {L["id"]: L for L in src}
    for i in range(1, len(층)):
        앞, 뒤 = 층[i - 1], 층[i]
        L = by_id.get(뒤["id"])
        w = (L or {}).get("가중치") or {}
        val = w.get("값") if w.get("담음") else None
        row = {"from": 앞["id"], "to": 뒤["id"], "세기": None, "세기 있나": False,
               "왜": None}
        if not 앞["인덱스"] or not 뒤["인덱스"]:
            row["왜"] = "한쪽 층의 뉴런을 못 그려서 간선도 못 그린다"
        elif val is None:
            row["왜"] = ("🔴 **가중치를 못 읽어 구조만 그렸다** --- "
                        + str(w.get("왜") or "이 층에 가중치가 없다"))
        elif len(val) < max(뒤["인덱스"]) + 1 or (
                앞["전체 뉴런"] and len(val[0]) != 앞["전체 뉴런"]):
            row["왜"] = (f"🔴 가중치 모양 {w.get('모양')} 이 앞 층 뉴런 수 "
                        f"{앞['전체 뉴런']} 과 안 맞아 **구조만 그렸다**")
        else:
            row["세기"] = [[round(float(val[o][i2]), 6) for i2 in 앞["인덱스"]]
                         for o in 뒤["인덱스"]]
            row["세기 있나"] = True
            row["세기 뜻"] = "행 = 뒤 층의 그린 뉴런 · 열 = 앞 층의 그린 뉴런"
        간선.append(row)
    잘린 = [L for L in 층 if L.get("잘림")]
    return {
        "run_id": run_id, "그릴 수 있나": bool(층),
        "층": 층, "간선": 간선,
        "층당 최대": max_per_layer,
        "가중치를 읽었나": 가중치읽음,
        "간선 출처": a.get("간선 출처"),
        "🔴 간선 단서": a.get("🔴 간선 단서"),
        "🔴 이 그림의 가정": "뉴런 간선은 층을 **차례로** 이은 것이다. 실제 그래프가 "
                     "갈래(잔차·분기)를 가지면 **이 그림은 그 갈래를 안 보여 준다** "
                     "--- 층 사이 진짜 연결은 `arch.json` 의 `간선` 을 봐라",
        "잘린 층": [{"층": L["이름"], "전체": L["전체 뉴런"],
                 "그린 것": L["그린 뉴런"], "기준": L["고른 기준"]} for L in 잘린],
        "말": (("🔴 " + " · ".join(
            f"{L['이름']}: {L['전체 뉴런']:,}개 중 {L['그린 뉴런']:,}개만 그렸다"
            for L in 잘린)) if 잘린 else "모든 층을 뉴런 하나까지 다 그렸다")
        + (" · 세기는 가중치에서 왔다" if 가중치읽음
           else " · 🔴 **가중치를 못 읽어 구조만 그렸다**"),
    }
