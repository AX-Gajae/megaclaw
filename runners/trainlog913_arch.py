"""🔴 **이 저장소에 실재하는 모형**을 `data/trainlog/` 에 세운다. 노트 913 팔 ㅈ.

    python3 -m runners.trainlog913_arch

노트 897 이 파이썬 604개를 전수 AST 로 훑어 `state/masked_encoder` ·
`shared_encoder` · `fewshot` · `transfer_eval` **넷을 아무도 안 부른다**는 것을
찾았다. 학습이 돌아도 **어디에도 안 남아서** 조각들이 조용히 죽었다.
이 러너가 하는 일은 그 조각들을 **화면에 세우는 것**이다.

# 규율 넷

1. 🔴 **`state/` · `lab/` 을 한 글자도 안 고친다.** import 해서 **인스턴스만** 만든다.
2. 🔴 **학습을 안 돌린다.** 그래서 만든 run 은 `학습 돌렸나: false` 이고 지표가
   0점이다 --- 그것이 **정상**이고 화면이 「구조만 있다」를 적는다.
   가짜 곡선은 한 줄도 안 만든다.
3. 🔴 **못 세운 것은 「없다」가 아니라 「못 세웠다 + 왜」**로 적는다.
   분모(후보 클래스 수)와 분자(세운 수)를 **센다**.
4. 🔴 **데모가 아니다.** `데모인가: false` --- 실물 코드에서 뽑은 구조다.

# 생성자 인자를 어디서 얻나

클래스마다 인자가 다르고 **코드가 그 값을 안 들고 있는 경우가 있다**(예:
`DomainHead(act_dim)` 의 `act_dim` 은 자료에서 온다). 그럴 때는 **우리가 고른 값**
이라고 `하이퍼파라미터` 와 `메모` 에 적는다 --- 실제 학습 때 쓰인 값이라고
주장하지 않는다(조항 59).
"""
from __future__ import annotations

import importlib
import inspect
import json
import sys
import traceback

from trainlog import Run

#: 세울 후보 --- (모듈, 클래스, 인자, 왜 이 인자인가)
#: 🔴 인자는 **우리가 고른 것**이다. 코드가 그 값을 안 들고 있으면 그렇게 적는다.
TARGETS = [
    ("state.masked_encoder", "Net", {"d_in": 12, "k": 2, "h": 32},
     "d_in=12 는 그 파일의 설계 주석 그대로다(값 여섯 + 마스크 여섯). "
     "k=2·h=32 는 생성자 기본값"),
    ("state.shared_encoder", "Model",
     {"doms": ["popup", "idol", "game", "movie", "anime", "webtoon",
               "drama", "music", "book", "kbo", "concert", "exhibit"],
      "d_in": 10, "d_lat": 2, "hidden": 32},
     "🔴 `doms` 는 **우리가 준 12도메인 이름표**다 --- 도메인마다 머리가 하나씩 "
     "생기는 `nn.ModuleDict` 라서 이름 목록이 있어야 세워진다. 나머지는 기본값"),
    ("state.encoder", "SharedEncoder", {},
     "인자 전부 그 파일의 기본값(STATE_DIM=7 · LATENT=8)"),
    ("state.encoder", "DomainHead", {"act_dim": 3},
     "🔴 `act_dim` 은 자료에서 오는 값이라 코드에 없다 --- **우리가 3 으로 골랐다**"),
    ("state.foundation", "Enc", {"d_in": 8, "n_slot": 2},
     "🔴 `d_in` 은 도메인 피처 수라 자료에서 온다 --- **우리가 8 로 골랐다**. "
     "n_slot=2 는 기본값"),
    ("state.foundation", "SharedHead", {"n_slot": 2}, "n_slot=2 는 기본값"),
    ("state.ssl909", "MaskedAE", {"P": 6, "k": 8, "h": 64},
     "🔴 `P` 는 축 수라 자료에서 온다 --- **우리가 6 으로 골랐다**(그 파일의 "
     "슬롯 여섯과 맞췄다). k=8·h=64 는 기본값"),
    ("state.slots", "Encoder", {"in_dim": 8, "latent": 2},
     "🔴 in_dim·latent 는 자료에서 온다 --- **우리가 골랐다**"),
    ("state.slots", "Head", {"latent": 2}, "🔴 latent 는 **우리가 골랐다**"),
    ("state.slots", "LinHead", {"latent": 2}, "🔴 latent 는 **우리가 골랐다**"),
    ("state.slots", "LinEncoder", {"in_dim": 8, "latent": 2},
     "🔴 in_dim·latent 는 **우리가 골랐다**"),
]

#: 🔴 **후보이지만 못 세우는 것** --- 「없다」가 아니라 「못 세웠다」다.
#: (여기 적힌 이유는 러너가 실제로 확인한 것이고, `_census()` 가 다시 센다.)
CANDIDATE_MODULES = ("state.masked_encoder", "state.shared_encoder",
                     "state.encoder", "state.foundation", "state.ssl909",
                     "state.slots", "state.fieldmodel", "lab.textnn",
                     "lab.semtoken908")


def _census() -> dict:
    """🔴 **분모를 센다** --- 후보 모듈에서 `nn.Module` 하위 클래스가 몇 개인가.

    모듈 **바깥**(module level)에 있는 것만 셀 수 있다. 함수 안에 정의된 클래스는
    밖에서 못 부르므로 **「못 세운다」**로 따로 적는다(소스를 읽어 센다).
    """
    import ast
    from pathlib import Path
    import torch.nn as nn
    바깥, 안쪽, 못읽음 = [], [], []
    for mod in CANDIDATE_MODULES:
        p = Path(mod.replace(".", "/") + ".py")
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception as e:
            못읽음.append({"모듈": mod, "왜": f"{type(e).__name__}: {e}"})
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            bases = [ast.unparse(b) for b in node.bases]
            if not any("Module" in b for b in bases):
                continue
            top = any(node is c for c in tree.body)
            (바깥 if top else 안쪽).append(f"{mod}.{node.name}")
    return {"후보 모듈 수": len(CANDIDATE_MODULES),
            "모듈 바깥 nn.Module 클래스": sorted(바깥),
            "🔴 함수 안에 있어 못 세우는 클래스": sorted(안쪽),
            "소스를 못 읽은 모듈": 못읽음 or None,
            "🔴 뜻": ("함수 안에 정의된 클래스는 그 함수를 부르지 않고는 "
                   "인스턴스를 못 만든다 --- 그 함수는 학습을 돌리므로 "
                   "**세우려면 학습을 돌려야 한다**. 이 팔은 안 돌린다")}


def build_one(mod: str, cls: str, kwargs: dict, 왜: str) -> dict:
    """모듈 하나를 세워 run 하나로 남긴다 --- **터지면 터졌다고 적는다.**"""
    try:
        M = importlib.import_module(mod)
        C = getattr(M, cls)
        model = C(**kwargs)
    except Exception as e:
        return {"대상": f"{mod}.{cls}", "세웠나": False,
                "🔴 왜 못 세웠나": f"{type(e).__name__}: {e}",
                "역추적": traceback.format_exc().splitlines()[-3:]}
    src = None
    try:
        src = inspect.getsourcefile(C)
    except Exception:
        pass
    with Run(f"{mod}.{cls}", pushes="⑤파생", ruler=None, demo=False,
             trained=False, code=[src] if src else None,
             hparams={**kwargs, "🔴 인자 출처": 왜},
             note=("노트 913 팔 ㅈ --- **이 저장소에 실재하는 모형**의 구조를 "
                   "그대로 뽑아 남겼다. 🔴 **학습을 안 돌렸다** --- 지표가 0점인 "
                   "것이 정상이다. 노트 897 이 「아무도 안 부른다」고 찾은 "
                   "조각들을 화면에 세우는 것이 이 기록의 목적이다")) as r:
        a = r.arch(model)
        rid = r.run_id
    return {"대상": f"{mod}.{cls}", "세웠나": True, "run_id": rid,
            "층 수": len(a.get("층") or []), "간선 수": len(a.get("간선") or []),
            "간선 출처": a.get("간선 출처"),
            "총 파라미터": a.get("총 파라미터"),
            "소스": src}


def main() -> int:
    out = {"무엇": "🔴 이 저장소에 **실재하는** 모형의 구조를 trainlog 에 세운다",
           "🔴 데모가 아니다": "전부 `데모인가: false` · `학습 돌렸나: false`",
           "인구조사": _census(), "결과": []}
    for mod, cls, kw, 왜 in TARGETS:
        out["결과"].append(build_one(mod, cls, kw, 왜))
    세움 = [r for r in out["결과"] if r["세웠나"]]
    out["센 것"] = {
        "시도한 클래스 수": len(TARGETS),
        "세운 수": len(세움),
        "🔴 못 세운 것": [{"대상": r["대상"], "왜": r["🔴 왜 못 세웠나"]}
                     for r in out["결과"] if not r["세웠나"]],
    }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
