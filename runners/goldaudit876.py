# -*- coding: utf-8 -*-
# 노트 876 — 골드 위생 감사·채택 재판정·문 재개봉(사전등록 '876' · 티처 #41 제안 1)
# ko_titles.py 원본 불변(사본 로직) · 골드 파일 불변(정책별 truth 재구성).
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
ROOT = Path("/Users/ax/world_model")


def main():
    t0 = time.time()
    import importlib.util
    spec = importlib.util.spec_from_file_location("kt", ROOT / "ingest/ko_titles.py")
    kt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(kt)
    # wfail1 배선 버그: kt.norm 은 NFKC·더빙 접두 제거만(매칭 정규화 아님) — 겹침 계산의
    # 정규화기는 **titlekey.norm 으로 통일**(격자 채점만 ko_titles 내부 세계라 kt.norm 유지).
    from lab.titlekey import norm

    gold = json.loads((ROOT / "data/state/anime_match.json").read_text())
    wa = json.loads((ROOT / "data/state/wanime_records.json").read_text())
    al2w = {}
    for k, v in wa.items():
        al2w.setdefault(str(v.get("media_id")), k)

    # ── G: 정책별 truth ───────────────────────────────────────────
    al_cnt = Counter(str(g.get("al_id")) for g in gold.values())
    def truths(policy):
        t = {}
        for an_id, g in gold.items():
            wid = al2w.get(str(g.get("al_id")))
            if not (wid and g.get("lf_title")):
                continue
            if policy == "충돌배제" and al_cnt[str(g.get("al_id"))] > 1:
                continue
            t.setdefault(wid, set()).add(kt.norm(g["lf_title"]))
        return t
    T_ex, T_set = truths("충돌배제"), truths("집합값")

    grid = [(0.55, 45), (0.65, 45), (0.75, 45), (0.80, 45),
            (0.65, 10), (0.75, 10), (0.85, 45), (0.90, 45)]
    tables = {}
    for pol, T in (("충돌배제", T_ex), ("집합값", T_set)):
        rows = []
        for th, wn in grid:
            m = kt.match(thresh=th, win=wn)
            cov = sum(1 for k in T if k in m)
            ok = sum(1 for k, v in T.items() if k in m and kt.norm(m[k]["ko"]) in v)
            rows.append({"문턱": th, "창": wn, "정답 중 붙음": cov, "그중 맞음": ok,
                         "정확도": round(ok / cov, 3) if cov else None})
        tables[pol] = {"유효쌍": len(T), "표": rows}

    # ── A: 채택(주 = 충돌배제 · 전역 완비) ─────────────────────────
    cand = [r for r in tables["충돌배제"]["표"] if r["정확도"] is not None and r["정확도"] >= 0.90]
    if not cand:
        adopted = None
    else:
        mx = max(r["정답 중 붙음"] for r in cand)
        adopted = sorted([r for r in cand if r["정답 중 붙음"] == mx],
                         key=lambda r: -r["문턱"])[0]

    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                      capture_output=True, text=True).stdout.strip(),
           "kot 캐시 sha": {f: hashlib.sha256((ROOT / f"data/state/{f}").read_bytes()).hexdigest()[:12]
                          for f in ("kot_an.npy", "kot_wa.npy")},
           "격자": tables, "채택": adopted}
    if adopted is None:
        out["갈래"] = "A 공집합 — 골드 위생 후에도 자격 미달: 진짜 폐문"
        _save(out); return

    # ── O: 3원 합집합 + 눈 검증 목록 ──────────────────────────────
    from lab import sideaudit
    from lab.decay import AXD, AX
    data = sideaudit.champion_data()
    r_an = json.loads((AXD / f"{AX['애니']}.json").read_text())
    an_items = list(r_an.items())
    tl = [norm(v.get("name") or v.get("title") or "") for _k, v in an_items]
    yr = np.asarray(data.yr["애니"], float); y = np.asarray(data.dom["애니"][2], float)
    kho = np.isfinite(yr) & (yr >= 2025.0) & np.isfinite(y)
    ho_ix = np.flatnonzero(kho)
    r_wa = json.loads((AXD / f"{AX['세계애니']}.json").read_text())
    yr_w = np.asarray(data.yr["세계애니"], float); y_w = np.asarray(data.dom["세계애니"][2], float)
    ktr_w = np.isfinite(yr_w) & (yr_w < 2025.0) & np.isfinite(y_w)
    train_wids = {rid for (rid, _), k in zip(r_wa.items(), ktr_w) if k}

    # v1 겹침(874 재현 — 세 파트너)
    o874 = json.load(open(ROOT / "runners/out874_ipctl.json"))
    from lab.titlekey import keys_of
    rrec = json.loads((ROOT / "data/state/wanime_records.json").read_text())
    def train_titleset(dkey, expand=False):
        rr = json.loads((AXD / f"{AX[dkey]}.json").read_text())
        yrx = np.asarray(data.yr[dkey], float); yx = np.asarray(data.dom[dkey][2], float)
        ktrx = np.isfinite(yrx) & (yrx < 2025.0) & np.isfinite(yx)
        outk = set()
        for (rid, rec), k in zip(rr.items(), ktrx):
            if not k:
                continue
            b = {norm(rec.get("name") or rec.get("title") or "")} - {""}
            outk |= (keys_of(rrec[rid]) | b) if (expand and rid in rrec) else b
        return outk
    p_v1 = train_titleset("세계애니", True) | train_titleset("만화") | train_titleset("웹툰")
    v1_rows = {int(i) for i in ho_ix if tl[i] and tl[i] in p_v1}

    # 골드 유도 겹침(유보 애니 ↔ 세계애니 학습 — ID 경유 · 충돌배제 골드만)
    gold_ok = {an: g for an, g in gold.items()
               if al_cnt[str(g.get("al_id"))] == 1 and al2w.get(str(g.get("al_id")))}
    an_key = {an_id: i for i, (an_id, _v) in enumerate(an_items)}
    gold_rows = set()
    for an_id, g in gold_ok.items():
        wid = al2w[str(g.get("al_id"))]
        i = an_key.get(an_id)
        if i is not None and kho[i] and wid in train_wids:
            gold_rows.add(int(i))

    # v2 신규(채택 설정 · 눈 검증 목록)
    m2 = kt.match(thresh=adopted["문턱"], win=adopted["창"])
    rev = {}
    for wid, v in m2.items():
        k = norm(v.get("ko"))
        if k:
            rev.setdefault(k, set()).add(wid)
    v2_rows, eye = set(), []
    for i in ho_ix:
        i = int(i)
        wids = rev.get(tl[i]) or set()
        hit = wids & train_wids
        if hit:
            v2_rows.add(i)
            if i not in (v1_rows | gold_rows):
                wid = sorted(hit)[0]
                eye.append({"행": i, "라프텔": an_items[i][1].get("title"),
                            "AniList": rrec.get(wid, {}).get("title"), "wid": wid})
    union = v1_rows | gold_rows | v2_rows
    out["O"] = {"v1": len(v1_rows), "골드 유도": len(gold_rows), "v2": len(v2_rows),
                "v2 신규(눈 검증 대상)": eye, "합집합(눈 검증 전)": len(union),
                "서로소 검사": {"v1∩골드": len(v1_rows & gold_rows), "v1∩v2": len(v1_rows & v2_rows),
                            "골드∩v2": len(gold_rows & v2_rows)}}
    out["합집합 행"] = sorted(union)
    out["초"] = round(time.time() - t0, 1)
    _save(out)


def _save(out):
    p = ROOT / "runners/out876_goldaudit.json"
    with open(p, "x") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: v for k, v in out.items() if k not in ("격자", "합집합 행")},
                     ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
