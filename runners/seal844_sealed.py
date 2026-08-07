# 노트 844 — 영화 전향 봉인 (사전등록 '844' · 갑 = 개봉일람의 개봉 전 작품)
# 규약(티처 #10): 이 러너는 판정과 같은 커밋에 들어간다.
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

sys.path.insert(0, "/Users/ax/world_model")
from ingest.kobis import movie_detail  # noqa: E402
from lab import guards as G, sideaudit  # noqa: E402
from lab.forms import REGISTRY  # noqa: E402

t0 = time.time()
TODAY = "2026-08-08"
OPEN_MAX = "2026-09-30"
SEEDS = list(range(12))
T = 2025.0
ROOT = Path("/Users/ax/world_model")
SEALDIR = ROOT / "cycle_log/forward/kobis"

UA = {"User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"),
      "Accept-Language": "ko-KR,ko;q=0.9"}
SLEEP = 1.5


def post(url, data):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(),
                                 headers={**UA, "Content-Type": "application/x-www-form-urlencoded"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


# ── ① 개봉일람 — 개봉 전(갑) 작품 명단 ────────────────────────────
def open_schedule(month):
    out = {}
    for page in range(1, 6):
        b = post("https://www.kobis.or.kr/kobis/business/mast/mvie/findOpenScheduleList.do",
                 {"openDt": month, "viewEa": "100", "pageIndex": str(page)})
        items = re.findall(
            r"mstView\('movie','(\d+)'\);return false;\" >([^<]+)</a>.*?"
            r"개봉예정일\s*</dt>\s*<dd>\s*<span>\s*([\d-]+)", b, re.S)
        new = 0
        for code, title, od in items:
            if code not in out:
                out[code] = {"code": code, "제목": html.unescape(title).strip(), "개봉일": od}
                new += 1
        if new == 0:
            break
        time.sleep(SLEEP)
    return out


movies = {}
for month in ("2026-08", "2026-09"):
    movies.update(open_schedule(month))
pool = [m for m in movies.values() if TODAY < m["개봉일"] <= OPEN_MAX]
print(f"개봉일람 수집 {len(movies)} · 개봉 전 풀({TODAY} 초과~{OPEN_MAX}) {len(pool)}", flush=True)

# ── ② 상세(등급·장르·배급 — 전부 개봉 전 정보) ──────────────────
for i, m in enumerate(pool):
    try:
        m.update(movie_detail(m["code"]))
    except Exception as e:
        m["⛔상세"] = str(e)[:80]
    time.sleep(SLEEP)
    if (i + 1) % 20 == 0:
        print(f"  상세 {i+1}/{len(pool)} ({time.time()-t0:.0f}s)", flush=True)

# ── ③ 축 사상 — 836 빌더의 규칙 그대로(배급 사전은 학습 구간만) ──
def grade_val(g):
    g = str(g or "")
    if "전체" in g:
        return 0.0
    if "12" in g:
        return 0.33
    if "15" in g:
        return 0.67
    if "청소년" in g or "제한" in g or "18" in g or "불가" in g:
        return 1.0
    return None


def clean_dist(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"\s+", " ", s).strip()
    s = re.split(r"\s+(?:제공|수입사|공동제공|공동 제공|배급|투자)\b", s)[0].strip()
    s = re.split(r"\s*(?:제공|배급)\s*$", s)[0].strip()
    m = re.match(r"([가-힣0-9()주식회사㈜\s]+)", s)
    cand = m.group(1).strip() if m else ""
    core = re.sub(r"[()㈜\s]|주식회사", "", cand)
    out = cand if len(core) >= 2 else s
    return out.rstrip("( ").strip()[:30]


raw = [json.loads(l) for l in open(ROOT / "data/ingest/kobis/axes_raw_897.jsonl")]
train_count = {}
for r in raw:
    if "⛔" not in r and r.get("code") and r["개봉일"] < "2025-01-01" and r.get("배급사"):
        d_ = clean_dist(r["배급사"])
        train_count[d_] = train_count.get(d_, 0) + 1
ranked = sorted(train_count.values())


def dist_pct(name):
    d_ = clean_dist(name) if name else None
    if not d_ or d_ not in train_count:
        return None
    return float(np.searchsorted(ranked, train_count[d_], side="right") / len(ranked))


ALL5 = ["target_breadth", "venue_prominence", "entry_friction", "media_push", "goods_scale"]
for m in pool:
    genres = [g for g in str(m.get("장르") or "").split(",") if g.strip()]
    tb = min(len(genres), 4) / 4 if genres else None
    vp = dist_pct(m.get("배급사")) if m.get("배급사") else None
    ef = grade_val(m.get("등급"))
    m["axes"] = {"target_breadth": tb if tb is not None else 0.5,
                 "venue_prominence": vp if vp is not None else 0.5,
                 "entry_friction": ef if ef is not None else 0.5,
                 "media_push": 0.5, "goods_scale": 0.5}
    m["mask"] = {"target_breadth": float(tb is not None), "venue_prominence": float(vp is not None),
                 "entry_friction": float(ef is not None), "media_push": 0.0, "goods_scale": 0.0}
cov = {k: round(float(np.mean([m["mask"][k] for m in pool])), 3) for k in ALL5[:3]}
live_cov = float(np.mean([np.mean([m["mask"][k] for k in ALL5[:3]]) for m in pool]))
print(f"축 확보율(살아있는 3축) {cov} · 평균 {live_cov:.3f}", flush=True)

# ── ④ 챔피언 적합(12도메인 · T=2025 · 씨앗 12)과 예측 ────────────
data12 = sideaudit.champion_data()
common = list(data12.names["영화"])
X = np.full((len(pool), len(common)), 0.5)
Mx = np.zeros((len(pool), len(common)))
for j, a in enumerate(common):
    if a in ALL5:
        X[:, j] = [m["axes"][a] for m in pool]
        Mx[:, j] = [m["mask"][a] for m in pool]
tx = np.array([float(m["개봉일"][:4]) for m in pool])

cls = REGISTRY["F18_bagboost"]["cls"]
yr_f = np.asarray(data12.yr["영화"], float)
y_f = np.asarray(data12.dom["영화"][2], float)
kho = np.isfinite(yr_f) & (yr_f >= T) & np.isfinite(y_f)
preds_new, preds_eval = [], []
for s in SEEDS:
    f = G._fit_on(lambda s=s: cls(seed=s), data12, T, seed=s)
    preds_new.append(np.asarray(f.predict("영화", X, Mx, tx), float))
    Ah, Mh, yh, th = data12.slice("영화", kho)
    preds_eval.append(np.asarray(f.predict("영화", Ah, Mh, th), float))
    print(f"  씨앗 {s} 적합·예측 ({time.time()-t0:.0f}s)", flush=True)
yhat = np.nanmean(preds_new, axis=0)
pe = np.nanmean(preds_eval, axis=0)
_, _, yh, _ = data12.slice("영화", kho)
ok = np.isfinite(pe) & np.isfinite(yh)
rho_ref = float(spearmanr(pe[ok], yh[ok])[0])

# 판정 밴드: 판-내 영화 유보에서 m 뽑기 부트스트랩(B=2000)
m_seal = len(pool)
rng = np.random.default_rng(844)
idx_all = np.flatnonzero(ok)
bs = []
for _ in range(2000):
    pick = rng.choice(idx_all, size=min(m_seal, len(idx_all)), replace=False)
    bs.append(spearmanr(pe[pick], yh[pick])[0])
sd_m = float(np.nanstd(bs, ddof=1))
print(f"판-내 영화 유보 ρ {rho_ref:.4f} · m={m_seal} 뽑기 2σ {2*sd_m:.4f}", flush=True)

# ── ⑤ 봉인(재작성 금지 · 채점 규칙 동결) ─────────────────────────
order = np.argsort(-yhat)
rank = np.empty(len(pool), int)
rank[order] = np.arange(1, len(pool) + 1)
code_sha = hashlib.sha256(open(__file__, "rb").read()).hexdigest()[:16]
git_sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                         cwd=ROOT).stdout.strip()[:12]
seal = {
    "봉인일": TODAY, "층": "갑(개봉 전 청정 — 예측 시점에 라벨 창 관측 0)",
    "작품": [{"code": m["code"], "제목": m["제목"], "개봉일": m["개봉일"],
              "장르": m.get("장르"), "국적": m.get("국적 후보"), "등급": m.get("등급"),
              "배급사": m.get("배급사"), "axes": m["axes"], "mask": m["mask"],
              "yhat_log10_21일누적": round(float(yhat[i]), 4), "예측 순위": int(rank[i])}
             for i, m in enumerate(pool)],
    "모형 지문": {"form": "F18_bagboost 합동(12도메인)", "T": T, "씨앗": SEEDS,
                 "공유 축": len(common), "배급 사전(학습)": len(train_count),
                 "코드 sha256": code_sha, "git": git_sha},
    "채점 규칙(동결)": {
        "라벨": "836 규칙 그대로 — 개봉일~+20일 창의 마지막 누적관객 log10(일별 표 소급 fetch)",
        "검열": "마지막 관측 < 개봉+14일 → 제외(검열 행 수 병기)",
        "수확 시각": "모든 작품 개봉+21일 경과 후 +7일 여유(최장 개봉일 " +
                    max(m["개봉일"] for m in pool) + " 기준)",
        "판정": {"전향 재현": f"ρ ≥ {rho_ref:.4f} − {2*sd_m:.4f}",
                 "붕괴": "그 미만 — 드리프트/누출 조사 개시",
                 "보류": "유효 편수(검열 제외) < 10"},
        "대조 밴드 산출": f"판-내 영화 유보 {int(ok.sum())}행 · m={m_seal} 뽑기 · B=2000 · 2σ={2*sd_m:.4f}",
    },
}
SEALDIR.mkdir(parents=True, exist_ok=True)
sealp = SEALDIR / f"seal_{TODAY}.json"
with open(sealp, "x") as fh:  # "x" — 이미 있으면 FileExistsError(694 규율)
    json.dump(seal, fh, ensure_ascii=False, indent=1)
try:
    with open(sealp, "x") as fh:
        pass
    rewrite_guard = "⛔ 재작성이 막히지 않았다"
except FileExistsError:
    rewrite_guard = "FileExistsError — 재작성 금지 작동"

out = {"봉인": str(sealp), "편수": m_seal, "층": "갑",
       "축 확보율": cov, "살아있는 3축 평균 확보": round(live_cov, 3),
       "판-내 ρ(재적합 실측)": round(rho_ref, 4), "밴드 2σ(m)": round(2 * sd_m, 4),
       "재작성 금지": rewrite_guard,
       "갈래": ("1.배선 실패" if (m_seal == 0 or live_cov < 0.5)
                else "2.봉인 완료 — 갑(개봉 전 청정)"),
       "초": round(time.time() - t0, 1)}
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
json.dump(out, open(ROOT / "runners/out844_seal.json", "w"), ensure_ascii=False, indent=1)
