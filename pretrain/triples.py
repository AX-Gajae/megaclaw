# -*- coding: utf-8 -*-
"""삼중쌍 (s, a, o) → 전이 모형 학습 자료.

원천: data/ingest/sao973_hplt/pairs.jsonl.gz — 이미 «상태 × 액션 → 결과» 꼴이다:
  s_상태.값  앞 90일 일별 위키 조회수
  a_액션     문서가 개체를 언급(언제·개체·문서 텍스트)
  o_결과.값  당일~뒤 91일 일별 조회수

처리:
  · (개체, 언제) 로 «중복 제거» — 같은 칸을 여러 문서가 언급하면 곡선이 복제된다
    (실측: 행 35,641 → 칸 10,654 · 상위 3 개체가 행의 31.1%)
  · 🔴 분할은 «위키 문서» 해시로 (1035 수리) — 아래 「분할 단위」 절
  · 텍스트(액션의 문자열 필드 전부)는 따로 저장 — LM 임베딩이 준비되면 꽂는다

🔴 분할 단위 (2026-08-25 · 사이클 1035 자 수리 · 사전등록 docs/탐색/1035.md §3)
  구판은 `md5(개체)%10==0 → val` 이었다. **틀렸다.** 곡선 (s,o)는 개체가 아니라 **위키
  문서**(`a_액션.문서`)의 조회수 시계열이고, 한 문서에 개체 ID 가 여럿 붙는다(실측: 개체
  2개 이상인 문서 **110** — `명탐정 코난` 13 · `나의 히어로 아카데미아` 13 · `짱구는
  못말려` 11). 개체로 가르면 **같은 곡선이 train 과 val 양쪽에 앉는다**.
  1035 실측(구판 npz `f120013017dcf512` 위에서): train/val 걸친 문서 **25** ·
  **val 1,129행 중 420행(37.2%)이 train 에 «비트 동일» (S,O) 쌍둥이를 가졌다** ·
  갈린 (문서,언제) 묶음 302 의 1,781행 전부 비트 동일(다른 곡선 0).
  대가: 누수 행의 핀볼 0.02797 대 무누수 행 0.09876 · 덮개율 0.9957 대 0.8708 —
  도메인 층화 Δ_str **−0.0657**(문서 클러스터 SE 0.0171 · 순열 p 0.021 · 8/8 도메인 음수).
  그래서 분할 키를 **문서**로 바꾼다. 「곡선의 주인」이 분할의 단위여야 한다.
  ⚠ `맞은 제목`(477)은 단위로 못 쓴다 — 표기 변형(`나의 히어로 아카데미아`/`my hero
  academia`)까지 뭉쳐 곡선을 못 가른다(실측: (맞은제목,언제) 묶음 7,444 중 107 이 곡선 2종).
  ⚠ 공동언급 연결성분도 못 쓴다 — 최대 성분이 개체 704 중 **479**(행 9,971)라 val 이 붕괴한다.

🔴 배포 정본 보호 (1035): 기본 출력 경로가 배포 디렉터리
  (`/Users/ax/wm_harvest/foundation/triples`)이면 «거부»한다. 구판 npz 는 1029 계열 판의
  역사 기록이라 이 스크립트가 조용히 덮어쓰면 그 판의 sha 사슬이 죽는다(조항 66).
  덮어쓰려면 `WM_ALLOW_DEPLOY_REBUILD=1` 을 «명시»하라 — 재학습·재배포 사이클 몫이다.

⚠ 「언제」는 크롤 시각이다(탐색 995 확정 · 사건일과 중앙 −808 일). 그래서 이 자료로는
  «조건부 예측»까지만 세우고 «언급의 인과 효과» 주장은 유보한다.

씀:  python3 pretrain/triples.py
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(_os.path.abspath(__file__)))))
import gzip
import hashlib
import json
import os

import numpy as np

SRC = "/Users/ax/world_model/data/ingest/sao973_hplt/pairs.jsonl.gz"
OUT_DIR = os.path.join(os.environ.get("WM_FOUNDATION_DIR",
                                      "/Users/ax/wm_harvest/foundation"), "triples")
# 1008 자 수리(조항 60 · docs/탐색/1008.md §3) — val 확장 명부. 여기 적힌 개체는 재빌드 시
# 해시 버킷과 무관하게 분할=val 로 강제한다(한 번 val 로 잰 개체가 train 으로 새는 것 금지).
# 파일이 없으면 기존 동작 그대로.
VAL_EXT_ROSTER = "/Users/ax/world_model/data/lab/val_ext_roster.json"


# 🔴 1035 §3 — 버킷 쇼핑 금지. 등록 정본은 구판과 «같은 자리»(0) 였고, 사전등록이 «미리»
# 지정한 대체 하나(val 하한 미달 시 {0,1} 로 확장)를 실측이 발동시켰다:
#   버킷 {0} → val 736행 · 웹툰 25행(하한 30 미달) · 🔴 **시장팝업 val 0행**(도메인 칸 소실)
#   버킷 {0,1} → val 1,943행 · 유일 문서 104 · 10 도메인 «전부» 살아있음 · 웹툰 330 · 시장팝업 359
# 그래서 인도된 분할은 {0,1} 이고 그 사실이 report.json 에 낙인으로 박힌다.
# `WM_VAL_BUCKETS` 는 그 전후를 재현하기 위한 손잡이다 — 임의의 버킷 집합을 시도해
# 좋은 쪽을 고르는 것은 사전등록 위반이다.
VAL_BUCKETS = tuple(sorted(int(x) for x in
                           os.environ.get("WM_VAL_BUCKETS", "0,1").split(",") if x != ""))


def val_ext_entities():
    if not os.path.exists(VAL_EXT_ROSTER):
        return frozenset()
    with open(VAL_EXT_ROSTER, encoding="utf-8") as f:
        return frozenset(json.load(f).get("개체", []))


def ent_bucket(ent):
    """🔴 구판 분할 키 (1035 이전) — **판정에 쓰지 마라.** 조항 66(자 수리 시 구판/신판
    전후 병기)을 위해 남긴다. 1029 계열 판 JSON 의 val 은 이 함수가 갈랐다."""
    return int(hashlib.md5(ent.encode("utf-8")).hexdigest()[:8], 16) % 10


def doc_bucket(doc):
    """신판 분할 키 (1035) — 곡선의 주인인 «위키 문서» 로 가른다."""
    return int(hashlib.md5(doc.encode("utf-8")).hexdigest()[:8], 16) % 10


def main():
    # 🔴 1035 — 배포 정본 보호. 구판 npz 는 1029 계열 판의 역사 기록이다(조항 66).
    if (os.path.abspath(OUT_DIR) == "/Users/ax/wm_harvest/foundation/triples"
            and os.environ.get("WM_ALLOW_DEPLOY_REBUILD") != "1"):
        raise SystemExit(
            "🔴 거부 — 배포 정본 %s 를 덮어쓰려 한다. 1035 이후 분할 단위가 «문서» 로 바뀌어\n"
            "   여기 쓰면 1029 계열 판(sao.npz f120013017dcf512)의 sha 사슬이 죽는다.\n"
            "   재빌드는 WM_FOUNDATION_DIR=<다른 경로> 로 하고, 배포 덮어쓰기는\n"
            "   WM_ALLOW_DEPLOY_REBUILD=1 을 «명시»한 재학습·재배포 사이클 몫이다." % OUT_DIR)
    os.makedirs(OUT_DIR, exist_ok=True)
    val_ext = val_ext_entities()               # 1008 — 명부 개체는 val 강제
    seen = set()
    S, O, meta = [], [], []
    n_rows = n_dupe = n_bad = 0
    with gzip.open(SRC, "rt", encoding="utf-8") as f:
        for line in f:
            n_rows += 1
            try:
                r = json.loads(line)
                a = r["a_액션"]
                key = (a["개체"], a["언제"])
                if key in seen:
                    n_dupe += 1
                    continue
                s = r["s_상태"]["값"]
                o = r["o_결과"]["값"]
                if len(s) != 90 or len(o) != 91:
                    n_bad += 1
                    continue
                seen.add(key)
                S.append(s)
                O.append(o)
                texts = [str(v) for k, v in sorted(a.items())
                         if isinstance(v, str) and k not in ("개체", "언제")]
                meta.append({"개체": a["개체"], "언제": a["언제"],
                             "문서": a["문서"],            # 1035 — 곡선의 주인
                             "도메인": r.get("도메인", "?"),
                             "텍스트": " · ".join(texts)[:2000]})
            except Exception:
                n_bad += 1
    # 🔴 1035 — 분할은 «문서» 단위. 두 번째 훑기라야 1008 명부(개체)를 문서로 넓힐 수 있다:
    #   명부 개체만 val 로 옮기면 그 문서의 «형제 개체» 가 train 에 남아 누수가 그대로 산다.
    val_ext_docs = frozenset(m["문서"] for m in meta if m["개체"] in val_ext)
    for m in meta:
        m["분할"] = ("val" if (doc_bucket(m["문서"]) in VAL_BUCKETS
                              or m["문서"] in val_ext_docs) else "train")
    S = np.asarray(S, dtype=np.float32)
    O = np.asarray(O, dtype=np.float32)
    doms = sorted(set(m["도메인"] for m in meta))
    year = np.asarray([float(m["언제"][:4]) + (float(m["언제"][5:7]) - 0.5) / 12.0
                       for m in meta], dtype=np.float32)
    doy = np.asarray([int(m["언제"][5:7]) * 30.4 + int(m["언제"][8:10])
                      for m in meta], dtype=np.float32)
    dom_id = np.asarray([doms.index(m["도메인"]) for m in meta], dtype=np.int64)
    split = np.asarray([0 if m["분할"] == "train" else 1 for m in meta], dtype=np.int64)

    np.savez_compressed(os.path.join(OUT_DIR, "sao.npz"),
                        S=S, O=O, year=year, doy=doy, dom_id=dom_id, split=split)
    with open(os.path.join(OUT_DIR, "meta.jsonl"), "w", encoding="utf-8") as f:
        for m in meta:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    # 🔴 1035 G3 — 「고쳤다」를 말로 안 쓰고 «세어서» 쓴다: 분할을 가로지르는 비트 동일
    #   (S,O) 쌍이 0 인가. 조항 59 — 0 이 아니면 0 이 아니라고 적는다.
    _sha = [hashlib.sha256(S[i].tobytes() + O[i].tobytes()).hexdigest()
            for i in range(len(S))]
    _tr = set(_sha[i] for i in range(len(S)) if split[i] == 0)
    _cross = int(sum(1 for i in range(len(S)) if split[i] == 1 and _sha[i] in _tr))
    _tr_docs = set(meta[i]["문서"] for i in range(len(S)) if split[i] == 0)
    _cross_doc = int(sum(1 for i in range(len(S))
                         if split[i] == 1 and meta[i]["문서"] in _tr_docs))
    rep = {"원천 행": n_rows, "중복(같은 개체×날)": n_dupe, "버림": n_bad,
           "표본": int(len(S)), "train": int((split == 0).sum()),
           "val(🔴 문서 분리 — 1035)": int((split == 1).sum()),
           "분할 단위": "문서(md5 버킷 %s) · 구판은 개체였다(1035 자 수리)" % (VAL_BUCKETS,),
           "🔴 낙인(1035 §3)": (
               "버킷 확장 «사전 지정 대체» 발동 — {0} 은 웹툰 val 25행(하한 30 미달)이고 "
               "시장팝업 val 이 0행이라 도메인 칸이 소실됐다. 등록이 «미리» 지정한 대체 "
               "{0,1} 하나만 썼다(추가 시도 0)."
               if tuple(VAL_BUCKETS) == (0, 1) else
               "등록 정본 버킷 {0} · 대체 미발동"),
           "유일 문서": len({m["문서"] for m in meta}),
           "유일 개체": len({m["개체"] for m in meta}),
           "val 유일 문서": len({meta[i]["문서"] for i in range(len(S)) if split[i] == 1}),
           "🔴 누수 검사 G3 — val 행 중 train 에 비트 동일 (S,O) 있는 행": _cross,
           "🔴 누수 검사 — val 행 중 문서가 train 에도 있는 행": _cross_doc,
           "val 확장 명부(1008)": ("없다(파일 %s 부재 — «못 읽었다» 아님)" % VAL_EXT_ROSTER
                                 if not os.path.exists(VAL_EXT_ROSTER)
                                 else {"개체": len(val_ext), "넓힌 문서": len(val_ext_docs)}),
           "도메인": {d: int((dom_id == i).sum()) for i, d in enumerate(doms)},
           "도메인×val": {d: int(((dom_id == i) & (split == 1)).sum())
                         for i, d in enumerate(doms)},
           "npz": os.path.join(OUT_DIR, "sao.npz")}
    with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "domains.json"), "w", encoding="utf-8") as f:
        json.dump(doms, f, ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
