"""판을 서빙에 얹는다 --- **11 도메인 전부.** 노트 701.

지금까지 서버에 얹힌 것은 만화 IP 2단 모형 하나였다. 판(21,672행 · 11 도메인 ·
ρ 0.4689 --- **11도메인 시대 값이고 837 재기선으로 은퇴했다** · 정본은
0.4710 ± 0.0021)은 안 얹혀 있었다. 판이 이 저장소의 본체인데 창구에서 못 불렀다.

**왜 서비스 층이 따로 필요한가.** 판은 부를 때마다 적합하면 안 된다 --- 챔피언
설정 한 씨앗이 몇 분 걸린다. 그래서 **띄울 때 한 번 적합해 캐시**하고, 캐시가
아직 없으면 그렇다고 말한다(추측으로 메우지 않는다).

**가장 중요한 규율: 기록된 숫자와 지금 계산한 숫자를 갈라 표시한다.**
이 저장소에는 노트에 적힌 값이 많고(짝 자 넷 · 능력 자 · 봉인) 그것을 다시
계산하려면 수십 분이 든다. 서버가 그 둘을 섞어 내면 **기록을 실시간인 양
세탁하게 된다** --- 노트 683 이 잡은 '자가 장부에만 있다' 와 같은 층의 위험이다.
그래서 모든 반환에 ``산출`` 을 붙인다:

    "지금 계산"       이 프로세스가 방금 적합해서 낸 값
    "디스크 캐시"     **같은 지문**의 앞선 적합을 그대로 읽은 값(노트 795).
                      입력이 한 글자라도 바뀌면 지문이 달라져 다시 굽는다 ---
                      그래서 '지금 계산' 과 값은 같고 시각만 다르다
    "기록(노트 N)"    노트에 적힌 값 --- 다시 재지 않았다
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import threading
import time
from pathlib import Path

import numpy as np

T = 2025.0
SEED = 0
FORM = "F18_bagboost"

ROOT = Path(__file__).resolve().parents[1]
#: 데운 결과를 디스크에 둔다. **실측 335초**(2026-08-07) --- 프로세스가 뜰
#: 때마다 그걸 다시 내면 재시작할 때마다 5분 넘게 *"판이 아직 안 데워졌다"* 다.
CACHE = ROOT / "data/state/_boardsvc_warm.npz"

#: 지문의 **자료 쪽**. 코드 쪽은 아래 `_code_files()` 가 *실제로 적재된 모듈*로
#: 정한다 --- 처음엔 `lab/*.py` 를 통째로 넣었는데, 그러면 예보 경로에 없는
#: 파일(`lab/calib.py` · `lab/decay.py` · `paper/*`)만 고쳐도 340초 굽기가
#: 날아간다. 이 저장소는 매 사이클 그런 파일이 생긴다.
DATA_GLOBS = ("data/state/*.json",)

#: 코드 지문에서 **빼는** 것. 재는 도구·논문·짝 진단은 예보를 안 바꾼다.
#: 🔴 `lab/calib.py` 는 노트 809 부터 **서빙 경로다**(drift_corrected) --- 빼면
#: 보정 공식이 바뀌어도 캐시가 낡은 채 산다.
CODE_SKIP = ("paper/", "serve/", "lab/decay.py",
             "lab/pairs.py", "lab/sideaudit.py")

_LOCK = threading.Lock()
_S: dict = {"상태": "안 데웠다", "판": None, "도메인": {}, "적합초": None,
            "오류": None, "시작": None, "산출": None}


def _code_files() -> list:
    """**지금 적재된 저장소 모듈** 중 예보 경로에 있는 것.

    `warm()` 이 적합을 마친 뒤에 부르면 `champion_data()`·정식화·축 빌더가
    전부 `sys.modules` 에 올라와 있다 --- 그것을 그대로 지문으로 쓴다.
    손으로 적은 목록은 낡지만 이건 안 낡는다.
    """
    import sys
    out = set()
    for m in list(sys.modules.values()):
        f = getattr(m, "__file__", None)
        if not f or not f.endswith(".py"):
            continue
        #: **절대경로여야 한다.** 상대 `__file__` 을 가진 바깥 모듈
        #: (`_classes.py`·`_ops.py`)이 `relpath` 를 타고 목록에 새어 든다.
        if not os.path.isabs(f):
            f = os.path.abspath(f)
        try:
            rel = os.path.relpath(f, ROOT)
        except ValueError:
            continue
        if not (ROOT / rel).is_file():
            continue
        if rel.startswith("..") or any(rel.startswith(x) for x in CODE_SKIP):
            continue
        out.add(rel)
    return sorted(out)


def _data_files() -> list:
    return sorted(os.path.relpath(p, ROOT)
                  for g in DATA_GLOBS for p in glob.glob(str(ROOT / g)))


def _stamp(paths) -> str:
    """(경로·크기·mtime) 요약. **내용은 안 읽는다**(자료가 1.6GB 다).

    이 저장소의 반복되는 병이 *"파일로 두면 낡는다"* 다(노트 669: 자료가 자라
    R² 가 0.1639 → 0.1098 · 노트 672: 색인이 100노트 넘게 죽은 수치를 이고
    있었다 · `lab/pairs.py` 가 축 파일을 일부러 저장 안 하는 이유). 그래서
    **의심스러우면 버리는 쪽**으로 튼다 --- stat 은 파일 천 개에 6ms 다.
    """
    h = hashlib.sha256()
    h.update(f"{FORM}|{T}|{SEED}|v3".encode())   # v3: 드리프트 보정(809)
    for rel in paths:
        try:
            st = os.stat(ROOT / rel)
        except OSError:
            h.update(f"{rel}|없음".encode())
            continue
        h.update(f"{rel}|{st.st_size}|{int(st.st_mtime)}".encode())
    return h.hexdigest()[:16]


def fingerprint(paths=None) -> tuple:
    """``(지문, 경로목록)``. `paths` 를 주면 **그 목록으로** 다시 찍는다."""
    ps = list(paths) if paths is not None else (_data_files() + _code_files())
    return _stamp(ps), ps


def _save_cache(fp: str, paths: list) -> None:
    blob, meta = {}, {}
    for d, v in _S["도메인"].items():
        for k in ("_p", "_y", "_pct", "_ok"):
            blob[f"{d}\x1f{k}"] = np.asarray(v[k])
        meta[d] = {"유보": v["유보"], "채점": v["채점"], "rho": v["rho"],
                   "_t": v["_t"]}
    dmeta = {}
    for d, v in (_S.get("드리프트") or {}).items():
        blob[f"{d}\x1fdrift_ptr"] = np.asarray(v["ptr"])
        blob[f"{d}\x1fdrift_ytr"] = np.asarray(v["ytr"])
        dmeta[d] = {"shift": v["shift"]}
    try:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        #: 🔴 **끝이 `.npz` 여야 한다.** `np.savez_compressed` 는 그렇지 않으면
        #: 이름에 `.npz` 를 **덧붙인다** --- 처음에 `.npz.tmp` 로 뒀더니
        #: `...npz.tmp.npz` 로 저장되고 `os.replace` 가 없는 파일을 찾아 죽었다.
        #: 그리고 그때 `except: pass` 가 그것을 통째로 숨겼다(5분 39초를 굽고도
        #: 캐시가 안 생겼는데 아무 말이 없었다).
        tmp = CACHE.with_name(CACHE.stem + ".tmp.npz")
        np.savez_compressed(
            tmp, __meta__=np.array(json.dumps(
                {"지문": fp, "경로": paths, "판": _S["판"],
                 "적합초": _S["적합초"], "도메인": meta, "드리프트": dmeta},
                ensure_ascii=False)), **blob)
        os.replace(tmp, CACHE)          # 반쯤 쓴 파일을 남기지 않는다
    except Exception as e:
        #: **조용히 넘기지 않는다.** 캐시 실패는 치명적이지 않지만 *안 보이면*
        #: 재시작마다 5분을 다시 굽게 된다.
        with _LOCK:
            _S["캐시 오류"] = f"{type(e).__name__}: {e}"
        print(f"  판 캐시 저장 실패: {type(e).__name__}: {e}", flush=True)


def _load_cache():
    """지문이 **정확히** 같을 때만 쓴다. 아니면 None --- 낡은 값을 안 낸다.

    🔴 **캐시가 적어 둔 경로 목록으로 다시 찍는다.** 지금 적재된 모듈로 찍으면
    아직 안 불린 모듈이 빠져 *다른 지문* 이 나온다 --- 그러면 캐시가 영영 안
    맞고 매번 340초를 다시 굽는다(고쳐 놓고 안 도는 캐시가 가장 나쁘다).
    """
    if not CACHE.exists():
        return None
    try:
        z = np.load(CACHE, allow_pickle=False)
        m = json.loads(str(z["__meta__"]))
        paths = m.get("경로") or []
        if not paths or _stamp(paths) != m.get("지문"):
            return None
        #: 자료 파일이 **늘거나 줄었으면** 목록 자체가 달라진다
        if sorted(x for x in paths if x.startswith("data/")) != _data_files():
            return None
        doms = {}
        for d, mm in m["도메인"].items():
            doms[d] = {**mm,
                       **{k: z[f"{d}\x1f{k}"] for k in ("_p", "_y", "_pct", "_ok")}}
        drift = {}
        for d, mm in (m.get("드리프트") or {}).items():
            drift[d] = {"shift": mm["shift"],
                        "ptr": z[f"{d}\x1fdrift_ptr"],
                        "ytr": z[f"{d}\x1fdrift_ytr"]}
        return {"상태": "데움", "판": m["판"], "도메인": doms,
                "드리프트": drift,
                "적합초": m["적합초"], "오류": None, "시작": None,
                "산출": "디스크 캐시"}
    except Exception:
        return None


# ── 데우기 ────────────────────────────────────────────────────────
def warm(force: bool = False) -> dict:
    """챔피언 판을 한 번 적합하고 도메인마다 유보 예보·라벨·제목을 캐시한다.

    🔴 **디스크 캐시를 먼저 본다**(2026-08-07). 적합이 실측 **335초**라 프로세스가
    뜰 때마다 다시 내면 재시작마다 5분 넘게 창구가 *"안 데워졌다"* 고 말한다.
    지문(`fingerprint`)이 한 글자라도 다르면 캐시를 버리고 다시 굽는다.

    `force=True` 면 캐시를 무시하고 다시 굽는다.
    """
    global _S
    if not force:
        with _LOCK:
            if _S["상태"] == "데움":
                return status()
        hit = _load_cache()
        if hit is not None:
            with _LOCK:
                _S = hit
            return status()
    with _LOCK:
        if _S["상태"] == "데움":
            return status()
        if _S["상태"] == "데우는 중":       # 이미 다른 실이 굽고 있다 --- 두 번 안 굽는다
            return status()
        _S["상태"] = "데우는 중"
        _S["시작"] = time.time()
        _S["오류"] = None                   # **실패해도 다음 호출이 다시 시도한다**
    t0 = time.time()
    try:
        from lab import forms, guards as G
        from lab.sideaudit import champion_data
        from ingest.news_counts import titles
        from scipy.stats import spearmanr, rankdata

        data = champion_data()
        cls = forms.REGISTRY[FORM]["cls"]
        f = G._fit_on(lambda: cls(seed=SEED), data, T, seed=SEED)
        doms = {}
        for d in data.dom:
            post = data.rows(d, post=True, T=T)
            if post.sum() < 20:
                continue
            A, M, y, t = data.slice(d, post)
            try:
                p = np.asarray(f.predict(d, A, M, t), float)
            except Exception:
                continue
            ok = np.isfinite(p) & np.isfinite(y)
            if ok.sum() < 20:
                continue
            # 도메인 안 백분위 --- 예보를 사람이 읽는 꼴로
            pct = np.full(len(p), np.nan)
            r = rankdata(p[ok]) - 1.0
            pct[ok] = r / max(ok.sum() - 1, 1)
            ts = titles(d)
            names = None
            if ts is not None:
                full = list(ts)
                idx = np.flatnonzero(post)
                names = [str(full[i]) if i < len(full) else "" for i in idx]
            doms[d] = {"유보": int(post.sum()), "채점": int(ok.sum()),
                       "rho": round(float(spearmanr(p[ok], y[ok]).statistic), 4),
                       "_p": p, "_y": y, "_pct": pct, "_ok": ok, "_t": names}
        #: 🔴 노트 809 --- **드리프트 보정 재료를 같이 굽는다**(능력 802).
        #: 안 옮김은 T=2023 적합에서(노트 800) · ptr/ytr 는 챔피언(T=2025)의
        #: 학습 예보·라벨(되돌림 분위표 · 노트 645 --- 학습에서만).
        from lab import calib as _cal
        f23 = G._fit_on(lambda: cls(seed=SEED), data, 2023.0, seed=SEED)
        drift = {}
        for d in data.dom:
            yrd = np.asarray(data.yr[d], float)
            y_all = np.asarray(data.dom[d][2], float)
            ktr = np.isfinite(yrd) & (yrd < T) & np.isfinite(y_all)
            if ktr.sum() < 15:
                continue
            A2, M2, _y2, t2 = data.dom[d]
            try:
                ptr = np.asarray(f.predict(d, A2[ktr], M2[ktr],
                                           np.asarray(t2, float)[ktr]), float)
            except Exception:
                continue
            okp = np.isfinite(ptr)
            ent = {"ytr": y_all[ktr][okp], "ptr": ptr[okp], "shift": None}
            if d in _cal.DRIFT_DOMAINS:
                ent["shift"] = _cal.inshift(f23, data, d)
            drift[d] = ent
        w = {d: doms[d]["채점"] for d in doms}
        tot = sum(w.values()) or 1
        pooled = sum(doms[d]["rho"] * w[d] for d in doms) / tot
        with _LOCK:
            _S = {"상태": "데움", "판": round(float(pooled), 4), "도메인": doms,
                  "드리프트": drift,
                  "적합초": round(time.time() - t0, 1), "오류": None,
                  "시작": None, "산출": "지금 계산"}
        fp, paths = fingerprint()      # **적합 뒤에** 찍는다 --- 그래야 예보
        _save_cache(fp, paths)         # 경로의 모듈이 전부 적재돼 있다
    except Exception as e:
        import traceback
        with _LOCK:
            #: 🔴 **"안 데웠다" 로 되돌린다** --- "실패" 로 못박아 두면 다음 호출이
            #: 다시 시도를 못 하고 창구가 영영 *"안 데워졌다"* 만 말한다.
            _S["상태"] = "안 데웠다"
            _S["시작"] = None
            _S["오류"] = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    return status()


def warm_async() -> None:
    threading.Thread(target=warm, daemon=True).start()


def status() -> dict:
    """**얼마나 걸리는지도 같이 낸다.** 맨 '안 데워졌다' 는 기다릴 수가 없다."""
    with _LOCK:
        st, t0 = _S["상태"], _S.get("시작")
        out = {"상태": st, "판 rho": _S["판"], "적합초": _S["적합초"],
               "캐시 오류": _S.get("캐시 오류"),
               "도메인 수": len(_S["도메인"]), "오류": _S["오류"],
               "산출": _S.get("산출") or "지금 계산",
               "설정": f"{FORM} · T={T} · 씨앗 {SEED}"}
    if st == "데우는 중" and t0:
        el = int(time.time() - t0)
        out["경과초"] = el
        out["대략 남은초"] = max(0, 340 - el)     # 실측 335초(2026-08-07)
    return out


ABS_RULER = ("이 방식은 자릿수(10배)를 **14% 확률로 틀립니다**"
             " (같은 도메인에서 평균만 말하면 17%) --- 노트 802 · 8개 도메인 판 가중"
             " 0.1430 대 기후값 0.1675")


def absolute(domain: str, query: str = "") -> dict:
    """🔴 **드리프트 보정 절대값**(능력 802) --- 자 문구를 항상 붙인다.

    보정이 없는 도메인(도서·시장팝업·팝업)은 **거부하고 기후값 대안**을 낸다 ---
    능력 카드의 금지 꼴('맨 절대값 · 보정 밖 도메인')을 서빙이 그대로 시행한다.
    """
    _ensure()
    s = status()
    if s["상태"] != "데움":
        return {"준비": False, **s, "말": _notyet(s)}
    from lab import calib as _cal
    with _LOCK:
        v = _S["도메인"].get(domain)
        dr = (_S.get("드리프트") or {}).get(domain)
    if v is None:
        return {"오류": f"'{domain}' 은 판에 없다"}
    if dr is None or dr.get("shift") is None:
        clim = None
        if dr is not None and len(dr.get("ytr", ())) >= 20:
            lo, hi = np.percentile(dr["ytr"], [10, 90])
            clim = {"도메인 구간(학습 라벨 10~90분위 · log10)":
                        [round(float(lo), 3), round(float(hi), 3)],
                    "원자리로(라벨 정의는 도메인마다 다름)":
                        [int(10 ** lo), int(10 ** hi)],
                    "실측 덮음": 0.8448, "근거": "노트 792"}
        return {"가능": False, "도메인": domain,
                "왜": "이 도메인은 드리프트 보정이 없다(안 옮김 측정 불가 · 노트 800) "
                     "--- **개별 작품의 절대값은 내지 않는다**(능력 카드 금지 꼴)",
                "대안": clim, "산출": "지금 계산"}
    ts, ok, p_all = v["_t"], v["_ok"], v["_p"]
    if not query or not ts:
        return {"오류": "query(제목 일부)가 필요하다",
                "예": "absolute('게임', 'PUBG')"}
    q = query.strip().lower()
    hits = [i for i in range(len(ts)) if q in (ts[i] or "").lower() and ok[i]]
    if not hits:
        return {"찾음": False, "말": f"'{query}' 를 {domain} 유보에서 못 찾았다"}
    i = hits[0]
    yh = float(_cal.drift_corrected(dr["ptr"], dr["ytr"],
                                    np.array([p_all[i]], float),
                                    dr["shift"])[0])
    return {"찾음": True, "도메인": domain, "제목": ts[i],
            "보정 절대값(log10)": round(yh, 3),
            #: ⚠️ 라벨의 뜻은 도메인마다 다르다(팝업=방문객 · 게임=리뷰 창 ·
            #: 만화=인기 지표 …) --- '사람 수' 로 뭉뚱그리면 오표기다
            "원자리 값(10^x · 라벨 정의는 도메인마다 다름)": int(round(10 ** yh)),
            "🔴 자(반드시 함께 전달)": ABS_RULER,
            "산출": s["산출"], "근거": [800, 801, 802]}


def _notyet(s: dict) -> str:
    """**왜 못 내는지와 얼마나 걸리는지를 같이 말한다.**

    전에는 어디서나 맨 *"판이 아직 안 데워졌다"* 였다. 그러면 부르는 쪽이
    ① 기다리면 되는지 ② 터진 건지 ③ 얼마나 남았는지를 못 가른다 --- 그리고
    적합이 실패해 있으면 그 사실이 통째로 숨는다.
    """
    if s.get("오류"):
        return (f"판 데우기가 **실패했다**: {s['오류']} --- 다시 부르면 재시도한다. "
                "추측으로 답하지 않는다")
    if s["상태"] == "데우는 중":
        left = s.get("대략 남은초")
        return (f"판을 **데우는 중**이다({s.get('경과초', 0)}초 지남 · 대략 "
                f"{left}초 남음). 추측으로 답하지 않는다")
    return ("판이 아직 **안 데워졌다**(적합 약 340초). `warm_status` 로 진행을 "
            "볼 수 있다 --- 추측으로 답하지 않는다")


def _ensure() -> None:
    """**캐시가 있으면 읽는다**(0.05초). 적합은 절대 안 건다.

    노트 797 --- 오토리서치의 조사 팔이 MCP 자식 프로세스에서 `board_overview`
    를 불렀는데 그 프로세스는 `warm()` 을 거친 적이 없어 *"판이 안 데워졌다"*
    를 받았다. **캐시를 구워 놓고도 읽는 길이 창구( `_warm` 스레드) 하나뿐이라
    다른 진입점이 전부 눈이 멀어 있었다.** 낼 것들의 입구마다 이것을 건다.
    """
    global _S
    with _LOCK:
        if _S["상태"] != "안 데웠다":
            return
    hit = _load_cache()
    if hit is not None:
        with _LOCK:
            if _S["상태"] == "안 데웠다":     # 그 사이 다른 실이 데웠으면 양보
                _S = hit


# ── 낼 것들 ───────────────────────────────────────────────────────
def board() -> dict:
    """판 전체 --- **지금 이 프로세스가 적합한 값**이다."""
    _ensure()
    s = status()
    if s["상태"] != "데움":
        return {"준비": False, **s, "말": _notyet(s)}
    with _LOCK:
        per = {d: {"유보": v["유보"], "채점": v["채점"], "rho": v["rho"]}
               for d, v in _S["도메인"].items()}
    return {"준비": True, "판 rho": s["판 rho"], "산출": s["산출"],
            "설정": s["설정"], "적합초": s["적합초"], "도메인별": per,
            "단서": "씨앗 하나다 --- 씨앗 SD 는 재현성이지 일반화가 아니다(노트 613). "
                  "기록된 챔피언 판은 **0.47034 ± 0.0021(SD · SE 0.00060) · 12도메인 · "
                  "유보 3,775 · 씨앗 0~11**(2026-08-10 재측정 · 이슈 #112 · 재현 "
                  "`python3 -m runners.rerun112`). 옛 0.4689 는 11도메인 시대 값이라 "
                  "은퇴했고, 옛 0.4710 은 **837 시대 값**이라 판정에서 뺐다 --- 은퇴한 두 "
                  "규약(① 라벨 배치 채점 ② 스피어만 구현: 동률 평균 대 서수) 위의 수여서 "
                  "오늘 **챔피언 경로로는** 안 나온다(837 경로로는 오늘도 재현된다 --- "
                  "0.4709970 ± 0.0021019 · 이슈 #117)"}


def rank(domain: str, query: str = "", top: int = 8) -> dict:
    """도메인 안 순위 --- 제목으로 찾거나 상위를 낸다."""
    _ensure()
    s = status()
    if s["상태"] != "데움":
        return {"준비": False, **s, "말": _notyet(s)}
    with _LOCK:
        v = _S["도메인"].get(domain)
        if v is None:
            return {"오류": f"'{domain}' 은 판에 없다",
                    "있는 도메인": sorted(_S["도메인"])}
        pct, ok, ts = v["_pct"], v["_ok"], v["_t"]
        rho = v["rho"]
        n = v["채점"]
    if query and ts:
        q = query.strip().lower()
        hits = [(i, ts[i]) for i in range(len(ts))
                if q in (ts[i] or "").lower() and ok[i]]
        if not hits:
            return {"찾음": False,
                    "말": f"'{query}' 를 {domain} 유보 {n}행에서 못 찾았다. "
                        "판은 유보 행만 채점한다 --- 학습 행은 순위를 안 낸다"}
        return {"찾음": True, "도메인": domain, "산출": s["산출"],
                "자": f"이 도메인 유보 rho {rho} (채점 {n}행 · 씨앗 1)",
                "결과": [{"제목": t, "백분위": round(float(pct[i]), 3),
                        "상위": f"{(1-pct[i])*100:.1f}%"} for i, t in hits[:top]],
                "단서": "백분위는 **우리 표본 안에서**의 순위다(시장 전수가 아니다)"}
    order = np.argsort(-np.where(ok, pct, -1))[:top]
    return {"도메인": domain, "산출": s["산출"],
            "자": f"이 도메인 유보 rho {rho} (채점 {n}행 · 씨앗 1)",
            "상위": [{"제목": (ts[i] if ts else f"행 {i}"),
                    "백분위": round(float(pct[i]), 3)} for i in order if ok[i]],
            "단서": "백분위는 우리 표본 안에서의 순위다"}


#: 짝 자 --- **기록이다.** 다시 재려면 `lab.pairs.score` 로 짝마다 몇 분 든다.
PAIRS_RECORDED = {
    "KR 만화": {"행": 1716, "rho": 0.6831, "기록 기준선": 0.6841, "노트": 696,
              "문턱": 0.025, "판정": "맞는다(차 −0.001 · 씨앗SD 0.0075)"},
    "비게임 앱": {"행": 1600, "rho": 0.4968, "기록 기준선": 0.5053, "노트": 696,
               "문턱": 0.024, "판정": "맞는다(차 −0.0085 · 씨앗SD 0.0106)"},
    "CN 만화": {"행": 352, "rho": 0.3874, "기록 기준선": 0.3094, "노트": 696,
              "문턱": 0.022,
              "판정": "**어긋난다 → 새 자**(차 +0.078 · 원인은 판 학습 성장)"},
}


def pairs() -> dict:
    """집 밖 짝 자 --- 판이 한 줄도 학습하지 않은 행에서 잰 L2 전이."""
    from lab import pairs as PR
    try:
        cnt = PR.counts()
    except Exception as e:
        cnt = {"오류": f"{type(e).__name__}: {e}"}
    return {"산출": "기록(노트 696)", "자": PAIRS_RECORDED,
            "행수 시험(지금 계산)": cnt,
            "단서": "rho 값은 **노트 696 의 기록**이고 이 프로세스가 다시 재지 않았다. "
                  "행수만 지금 확인한다 --- 그것은 결정론적이라 싸다"}


def rulers() -> dict:
    """능력 자 --- 순위를 절대값으로 되돌릴 때 무엇이 깨지나(노트 691)."""
    return {"산출": "기록(노트 691)",
            "자릿수 오차 비율": {"진짜": 0.4195, "위약": 0.4192,
                          "자 잡음(씨앗4 SD)": 0.0058},
            "중앙 절대오차(라벨 자리)": {"진짜": 0.9322, "위약": 0.9450},
            "'80% 구간' 실측 덮음": {"진짜": 0.5016, "위약": 0.4978,
                              "만화": 0.0000},
            "기울기": {"진짜": "도메인별로만 읽는다", "위약": 0.332,
                    "왜": "만화 99.8 · 세계애니 8.09 로 발산해 판 평균이 무의미하다"},
            "결론": "**이 판의 예보는 순위 전용이다.** 자 넷 중 셋이 위약과 구분되지 "
                  "않는다 --- 등백분위 사상을 통과하면 순위 정보가 절대값으로 거의 "
                  "번역되지 않는다. 기울기만 10/10 도메인에서 갈린다"}


def seal() -> dict:
    """전향 봉인 --- 이 실험실의 유일한 미래 방향 기록."""
    from . import seal as SL
    try:
        return {"산출": "지금 계산(봉인 파일을 읽는다)", **SL.score()}
    except Exception as e:
        return {"오류": f"{type(e).__name__}: {e}"}


#: 시군구 코드 → 이름. `_names.json` 이 코드표다.
_NAMES: dict | None = None


def _names() -> dict:
    global _NAMES
    if _NAMES is None:
        try:
            from ingest.visitors import CACHE
            import json as J
            f = CACHE / "_names.json"
            _NAMES = J.loads(f.read_text()) if f.exists() else {}
        except Exception:
            _NAMES = {}
    return _NAMES


_FIELD: tuple | None = None


def field(sgg: str = "", day: str = "") -> dict:
    """상태 장 g(x,t) --- 261 시군구 × 2,349일. 공휴일까지 뺀 잔차다(노트 690).

    **`div` 를 잘못 넘겨 고장나 있었다.** `fieldmodel.field(div="2", ...)` 의
    첫 인자는 **방문자 갈래**(2 = 외지인)인데 `"sgg"` 를 넣어 IndexError 가
    났다. 더 나쁜 것은 그때 내가 붙인 오류 문구였다 --- *"방문자 자료가 없으면
    못 낸다"* 고 적었는데 **자료는 있었고 인자가 틀렸다.** 없는 원인을 지어내는
    진단은 다음 사람을 엉뚱한 데로 보낸다. 그래서 이제 **예외를 그대로 낸다.**

    이름으로도 찾는다 --- 사람은 `11200` 이 아니라 '성동' 이라고 말한다.
    """
    global _FIELD
    try:
        from state.fieldmodel import field as _f, TRAIN_END
        if _FIELD is None:
            _FIELD = _f(stats_end=TRAIN_END)      # div 는 기본값(외지인)
        codes, days, X = _FIELD
    except Exception as e:
        import traceback
        return {"오류": f"{type(e).__name__}: {e}",
                "어디서": traceback.format_exc().strip().splitlines()[-3:],
                "단서": "**원인을 지어내지 않는다** --- 위 예외가 실제로 난 것이다"}
    out = {"산출": "지금 계산", "동네": len(codes), "날": len(days),
           "빼낸 것": ["동네 평균", "요일 평균", "전국 일평균(정확히 0)",
                    "공휴일 --- 명절/그밖/평일 갈래 셋(노트 690)"],
           "단서": "이것은 **잔차**다. 큰 값이 곧 '사람이 많다' 가 아니라 "
                 "'그 동네의 그 요일에서 벗어났다' 는 뜻이다"}
    if sgg:
        nm = _names()
        q = sgg.strip()
        hit = [i for i, c in enumerate(codes)
               if q in str(c) or q in str(nm.get(str(c), ""))]
        if not hit:
            out["찾음"] = False
            out["보기"] = [f"{c} {nm.get(str(c), '')}".strip() for c in codes[:10]]
            out["말"] = f"'{sgg}' 를 {len(codes)}개 시군구에서 못 찾았다"
            return out
        i = hit[0]
        out["이름"] = str(nm.get(str(codes[i]), ""))
        row = X[i]
        out["찾음"] = True
        out["동네코드"] = str(codes[i])
        if day:
            j = [k for k, d in enumerate(days) if str(d).startswith(day.replace("-", ""))]
            out["그 날"] = ({"날": str(days[j[0]]), "g": round(float(row[j[0]]), 4)}
                          if j else f"'{day}' 이 자료에 없다")
        fin = np.isfinite(row)
        out["요약"] = {"SD": round(float(np.nanstd(row)), 4),
                     "최대": round(float(np.nanmax(row[fin])), 4) if fin.any() else None,
                     "최소": round(float(np.nanmin(row[fin])), 4) if fin.any() else None}
    return out


if __name__ == "__main__":
    #: 배포 전에 **미리 구워 두는** 자리. 서버를 띄우기 전에 한 번 돌리면
    #: 창구가 처음부터 데워진 채로 뜬다(적합 약 340초 · 캐시 적중 0.05초).
    #:
    #:     python3 -m serve.boardsvc            # 캐시 있으면 그대로 쓴다
    #:     python3 -m serve.boardsvc --force    # 무시하고 다시 굽는다
    #:     python3 -m serve.boardsvc --check    # 굽지 않고 캐시 상태만 본다
    import sys
    if "--check" in sys.argv:
        hit = _load_cache()
        print(json.dumps(
            {"캐시 파일": str(CACHE), "있나": CACHE.exists(),
             "쓸 수 있나": hit is not None,
             "왜": ("맞는다" if hit else
                   "없다" if not CACHE.exists() else "지문이 다르다 --- 다시 굽는다"),
             "판 rho": (hit or {}).get("판")}, ensure_ascii=False, indent=1))
        raise SystemExit(0)
    t0 = time.time()
    st = warm(force="--force" in sys.argv)
    print(json.dumps({**st, "걸린초": round(time.time() - t0, 2)},
                     ensure_ascii=False, indent=1), flush=True)
    print(json.dumps(board(), ensure_ascii=False, indent=1)[:1200], flush=True)
