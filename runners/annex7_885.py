# -*- coding: utf-8 -*-
# 노트 885 정 — **국적 팔 동결(annex7)**: 9/28 수확에서 채점될 전향·집 밖 시험대.
#
# 왜 지금인가. 첫 봉인작 개봉이 **2026-08-11** 이라 오늘(08-09) 이후엔 라벨이 생긴다.
# 예측은 라벨 이전에 얼어야 한다(844 지문 사슬 규율). 정본·기존 annex 는 **한 글자도**
# 안 고친다 — 새 파일만 만든다.
#
# 설계(seal844 관례 그대로 + 국적 1열):
#   · X/Mx 는 봉인 파일에 동결된 5축·마스크에서 그대로 — 재계산 없음
#   · 국적 코드는 **학습 구간(개봉 <2025)만으로** 집단 크기 순 0~1(전이 누출 차단 · 885 ⑤)
#   · 챔피언 F18_bagboost · T=2025 · 씨앗 0~11(seal844 와 동일)
#   · 대조: 같은 씨앗·같은 X 로 국적 없는 팔도 함께 예측(순위 이동을 볼 수 있게)
import datetime as dt
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
from lab import guards as G  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

ROOT = Path("/Users/ax/world_model")
SEAL = ROOT / "cycle_log/forward/kobis/seal_2026-08-08.json"
OUT = ROOT / "cycle_log/forward/kobis/annex7_2026-08-09.json"
ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
SEEDS = list(range(12))
T = 2025.0
MIN_GROUP = 20
AXIS = "film_nation"


def main():
    t0 = time.time()
    seal = json.loads(SEAL.read_text())
    pool = seal["작품"]
    assert len(pool) == 30, f"봉인 편수 {len(pool)} ≠ 30"

    # ── 국적 코드: 학습 구간(개봉 <2025)만으로 만든다 ─────────────
    ax = json.loads((ROOT / "data/state/kobis_axes.json").read_text())
    ids = list(ax)
    yrs = [(ax[k].get("release_date") or "")[:4] for k in ids]
    JUNK = {"전체관람가", "청소년관람불가", "예술영화", "드라마",
            "12세이상관람가", "15세이상관람가"}
    raw = [None if (ax[k].get("국적") in JUNK) else ax[k].get("국적") for k in ids]
    train_pool = [x for x, y in zip(raw, yrs) if y and int(y) < T]
    c = Counter(x for x in train_pool if x not in (None, ""))
    order = [u for u, n in sorted(c.items(), key=lambda kv: -kv[1]) if n >= MIN_GROUP]
    pos = {u: i / max(1, len(order) - 1) for i, u in enumerate(order)}
    v_all = np.array([pos.get(x, 0.5) for x in raw], np.float32)
    m_all = np.array([1.0 if x in pos else 0.0 for x in raw], np.float32)

    sys.path.insert(0, str(ROOT / "runners"))
    import ff753 as FF
    d_probe = FF.shell(FF.base())
    doms = list(d_probe.dom)
    n_film = len(d_probe.dom["영화"][2])
    assert len(v_all) == n_film, f"배선 {len(v_all)} ≠ 판 영화 {n_film}"
    extra = {AXIS: {d: ((v_all, m_all) if d == "영화" else
                        (np.full(len(d_probe.dom[d][2]), 0.5, np.float32),
                         np.zeros(len(d_probe.dom[d][2]), np.float32))) for d in doms}}
    d_base = d_probe
    d_nat = FF.shell({**FF.base(), **extra})

    def feats(d):
        common = list(d.names["영화"])
        X = np.full((len(pool), len(common)), 0.5)
        Mx = np.zeros((len(pool), len(common)))
        for j, a in enumerate(common):
            if a in ALL5:
                X[:, j] = [p["axes"][a] for p in pool]
                Mx[:, j] = [p["mask"][a] for p in pool]
            elif a == AXIS:
                X[:, j] = [pos.get(p.get("국적"), 0.5) for p in pool]
                Mx[:, j] = [1.0 if p.get("국적") in pos else 0.0 for p in pool]
        return X, Mx, common

    tx = np.array([float(p["개봉일"][:4]) for p in pool])
    cls = REGISTRY["F18_bagboost"]["cls"]
    res = {}
    for tag, d in (("대조(국적 없음)", d_base), ("국적 팔", d_nat)):
        X, Mx, common = feats(d)
        preds = []
        for s in SEEDS:
            f = G._fit_on(lambda s=s: cls(seed=s), d, T, seed=s)
            preds.append(np.asarray(f.predict("영화", X, Mx, tx), float))
            if s % 4 == 0:
                print(f"  {tag} 씨앗 {s} ({time.time()-t0:.0f}s)", flush=True)
        yhat = np.nanmean(preds, axis=0)
        rank = (-yhat).argsort().argsort() + 1     # 큰 값 = 1위
        res[tag] = {"열 수": len(common), "yhat": [round(float(x), 4) for x in yhat],
                    "순위": {p["code"]: int(r) for p, r in zip(pool, rank)}}
        print(f"  {tag} 완료 · 열 {len(common)}", flush=True)

    a, b = res["대조(국적 없음)"]["순위"], res["국적 팔"]["순위"]
    moved = {k: b[k] - a[k] for k in a if b[k] != a[k]}
    out = {
        "작성일": dt.date.today().isoformat(),
        "성격": ("🔴 **국적 팔 동결(annex7)** — 노트 885 (가) 의 의무. 9/28 수확에서 채점될 "
               "**전향·집 밖 시험대**. 첫 봉인작 개봉 2026-08-11 이전에 언다. "
               "정본·기존 annex 불변(새 파일만)."),
        "왜 이 팔인가": ("영화는 집 밖 짝이 없어 규약 12(집 밖 ≥2)를 만족할 길이 없다(티처 #49 실측: "
                    "세계애니 country 98.7% JP · 만화는 판 안 상수 · 게임 열 없음). "
                    "그래서 **전향 봉인**이 유일한 집 밖 시험대다."),
        "설계": {"X/Mx": "봉인 파일 동결 5축·마스크 그대로(재계산 없음)",
               "국적 코드": f"학습 구간(개봉 <{int(T)})만으로 집단 크기 순 0~1 · MIN_GROUP {MIN_GROUP} "
                        f"→ 범주 {order} · **전이 누출 차단**(885 ⑤: 학습만이 오히려 +0.0168 강했다)",
               "모형": "F18_bagboost · T=2025 · 씨앗 0~11(seal844 동일)",
               "파싱 쓰레기": "등급 문자열이 국적 칸에 들어간 값은 None 처리(885 병③)"},
        "봉인 30편 국적 분포": dict(Counter(p.get("국적") for p in pool)),
        "마스크 밖(코드 0.5·마스크 0)": [p["제목"] for p in pool if p.get("국적") not in pos],
        "예측 팔(자루 평균 순위)": [
            {"code": p["code"], "제목": p["제목"], "개봉일": p["개봉일"], "국적": p.get("국적"),
             "국적 팔 순위": b[p["code"]], "대조 순위": a[p["code"]],
             "이동": b[p["code"]] - a[p["code"]]} for p in pool],
        "순위 이동 요약": {"바뀐 편수": len(moved), "최대 이동": (max(abs(x) for x in moved.values())
                                                     if moved else 0)},
        "🔴 9/28 채점 규칙(지금 못박는다)": {
            "자": "봉인 정본과 **같은 자**(spearman · 검열 제외 · 유효 <10 이면 보류) — 문턱 0.2046 불가침",
            "판정": ("**국적 팔 ρ > 대조 팔 ρ** 이고 그 차가 대조 밴드 밖이면 **영화 국적은 전향에서도 산다** "
                   "→ 그때 규약 12 의 '집 밖'을 전향 봉인으로 대체 채택할지 별도 사전등록. "
                   "차가 밴드 안이면 **집안 전용**으로 확정하고 국적은 서빙에 안 올린다. "
                   "국적 팔이 **더 낮으면** 885 의 집안 통과를 '판 안 과적합'으로 재분류한다."),
            "금지": "이 파일 수정 금지(수정은 지문 사슬 위반 — 고치려면 annex8 + 정오 사이드카)"},
        "지문": {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                          capture_output=True, text=True).stdout.strip(),
               "봉인 파일 sha": hashlib.sha256(SEAL.read_bytes()).hexdigest()[:12],
               "kobis_axes sha": hashlib.sha256(
                   (ROOT / "data/state/kobis_axes.json").read_bytes()).hexdigest()[:12],
               "초": round(time.time() - t0, 1)},
    }
    with open(OUT, "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "예측 팔(자루 평균 순위)"},
                     ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
