# -*- coding: utf-8 -*-
"""삼중쌍 (s, a, o) → 전이 모형 학습 자료.

원천: data/ingest/sao973_hplt/pairs.jsonl.gz — 이미 «상태 × 액션 → 결과» 꼴이다:
  s_상태.값  앞 90일 일별 위키 조회수
  a_액션     문서가 개체를 언급(언제·개체·문서 텍스트)
  o_결과.값  당일~뒤 91일 일별 조회수

처리:
  · (개체, 언제) 로 «중복 제거» — 같은 칸을 여러 문서가 언급하면 곡선이 복제된다
    (실측: 행 35,641 → 칸 10,654 · 상위 3 개체가 행의 31.1%)
  · 분할은 «개체» 해시로 — 같은 개체의 반복 언급이 학습/검증에 갈라 새는 것을 막는다
  · 텍스트(액션의 문자열 필드 전부)는 따로 저장 — LM 임베딩이 준비되면 꽂는다

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


def val_ext_entities():
    if not os.path.exists(VAL_EXT_ROSTER):
        return frozenset()
    with open(VAL_EXT_ROSTER, encoding="utf-8") as f:
        return frozenset(json.load(f).get("개체", []))


def ent_bucket(ent):
    return int(hashlib.md5(ent.encode("utf-8")).hexdigest()[:8], 16) % 10


def main():
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
                             "도메인": r.get("도메인", "?"),
                             "분할": ("val" if (ent_bucket(a["개체"]) == 0
                                             or a["개체"] in val_ext) else "train"),
                             "텍스트": " · ".join(texts)[:2000]})
            except Exception:
                n_bad += 1
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
    rep = {"원천 행": n_rows, "중복(같은 개체×날)": n_dupe, "버림": n_bad,
           "표본": int(len(S)), "train": int((split == 0).sum()),
           "val(개체 분리)": int((split == 1).sum()),
           "val 확장 명부 개체(1008 강제)": len(val_ext),
           "도메인": {d: int((dom_id == i).sum()) for i, d in enumerate(doms)},
           "npz": os.path.join(OUT_DIR, "sao.npz")}
    with open(os.path.join(OUT_DIR, "report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT_DIR, "domains.json"), "w", encoding="utf-8") as f:
        json.dump(doms, f, ensure_ascii=False)
    print(json.dumps(rep, ensure_ascii=False))


if __name__ == "__main__":
    main()
