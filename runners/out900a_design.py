# -*- coding: utf-8 -*-
"""노트 900 · 갈래 A(수리) — 티처 #62 **C1** + **C2 의 ⓓ 갈래**.

🔴 **정정 대상 1 (C1)**: `docs/prereg_899_axesdie.md` §2.1 이 `uniqF` 를
*"모형이 실제로 보는 설계행렬 `forms.DirectPool._feat(...)`"* 라 정의했고
`runners/axesdie899.py:170-171` 이 그대로 쟀다. **틀렸다.** 챔피언
`F18_bagboost` 가 실제로 보는 설계행렬은 `lab/forms.py:1101-1130 Boost._design()`
이다(`_feat` + `_season(t)` + `_spec_col` + `_domdrop`/`_domperm` + 도메인 원핫).
그 결과 899 자기 표가 네 도메인에서 **`예측 고유 > 설계행`** 이라는 원리상
불가능한 값을 이고 있었다.

🔴 **정정 대상 2 (C2 의 ⓓ)**: 899 의 죽은 칸 배정은 **도메인 자기 이름(`names[d]`)**
기준이라, `union` 에만 있고 `common` 에 없는 **게임 전용 축 넷**은 유보에서
살아 있어서 「살아 있다」로 분류돼 죽은 칸에 **한 칸도 안 들어간다**. 그런데
`axis_order(mode="common")` 이 그 넷을 떨구므로 **모형에는 한 칸도 안 닿는다**.
→ 다섯째 갈래 **ⓓ 「정식화가 안 본다」**.

⚠ `docs/prereg_899_axesdie.md` 는 **증거물이라 안 고친다.** 이 파일이 정정문이다.
⚠ `runners/out899_axesdie.json` 도 **안 덮는다** — 옛 열은 여기서 그 파일을
**읽어서** 나란히 놓는다(조항 60 · 손 전사 금지).

산출물: `runners/out900a_design.json`
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

import ff753 as FF                                    # noqa: E402
from lab import forms as FORMS                        # noqa: E402
from lab import fixaxes as FX                         # noqa: E402
from lab.harness import Data, MIN_TRAIN               # noqa: E402
import ruler890 as R890                               # noqa: E402
import axesdie899 as A899                             # noqa: E402

ROOT = Path("/Users/ax/world_model")
OUT = ROOT / "runners/out900a_design.json"
OLD = ROOT / "runners/out899_axesdie.json"
T = 2025.0

nuniq = A899.nuniq
uniq_rows = A899.uniq_rows
sha = A899.sha
build = A899.build

#: 🔴 심어서 확인하는 스위치(조항 59). 켜면 설계행 수를 일부러 1 로 낮춰
#: `예측 고유 <= 설계행` assert 가 **발화하는지** 본다.
PLANT_FAULT = "--plant-fault" in sys.argv


def main():
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    res = {
        "노트": 900, "갈래": "A(수리) · 티처 #62 C1 + C2 의 ⓓ",
        "정정 대상": {
            "C1": ("docs/prereg_899_axesdie.md §2.1 의 uniqF 정의와 "
                   "runners/axesdie899.py:170-171 — `_feat` 를 설계행렬이라 불렀다"),
            "C2-ⓓ": ("runners/axesdie899.py:206-230 의 배정 체계 — "
                      "`order` 에 없는 축(게임 전용 넷)을 볼 갈래가 없다"),
        },
        "🔴 증거물": ["docs/prereg_899_axesdie.md (읽기만 · 안 고쳤다)",
                     "runners/out899_axesdie.json (읽기만 · 안 덮었다)"],
        "HEAD": head, "시각": dt.datetime.now().isoformat(timespec="seconds"),
        "코드 sha": {f: sha(ROOT / f) for f in
                     ("runners/out900a_design.py", "runners/axesdie899.py",
                      "lab/forms.py", "lab/harness.py", "lab/fixaxes.py",
                      "runners/ff753.py", "state/tri_domain.py")},
        "🔴 자": "뗐다 — 서술 통계만. 채택/기각 없음",
    }

    print("자료 build (fixaxes 포함) ...", flush=True)
    d0 = build(True)
    doms = sorted(d0.dom)
    W = d0.weights(T)

    ref = json.load(open(ROOT / "runners/out890_ruler.json", encoding="utf-8"))
    dig = R890.digest_data(d0)
    wire = {"W1 자료 sha256": dig,
            "W1 890 과 동일": dig == ref["배선"]["ㄱ 자료 sha256"],
            "W2 도메인 수": len(W), "W2 가중 합": int(sum(W.values())),
            "W2 가중 합 == 3775": int(sum(W.values())) == 3775}
    print(json.dumps(wire, ensure_ascii=False), flush=True)
    assert wire["W1 890 과 동일"] and wire["W2 가중 합 == 3775"], "🔴 배선 중단"

    post = {d: (np.isfinite(np.asarray(d0.yr[d], float))
                & (np.asarray(d0.yr[d], float) >= T)) for d in doms}

    # ── 씨앗 0 챔피언 적합(899 와 글자 그대로 같다) ─────────────────────
    train, tmask = {}, {}
    for d in d0.dom:
        k = (np.isfinite(d0.yr[d]) & (d0.yr[d] < T)
             & np.isfinite(d0.dom[d][2]))
        if k.sum() >= MIN_TRAIN:
            train[d] = d0.slice(d, k)
            tmask[d] = k
    tr = Data(train, d0.names, {d: d0.yr[d][tmask[d]] for d in train})
    print(f"학습 도메인 {len(train)} · 적합 시작 ...", flush=True)
    f = FF.CLS(seed=0)
    f.fit(tr)
    order = list(f.order)

    # ── ① common / union 을 **내가 센다**(티처: 36 / 40) ────────────────
    common = FORMS.axis_order(tr, "common")
    union = FORMS.axis_order(tr, "union")
    only_union = [a for a in union if a not in common]
    res["🔴 C2 · common/union 실측"] = {
        "AXIS_MODE(현행)": FORMS.AXIS_MODE,
        "common 열 수": len(common), "union 열 수": len(union),
        "common == 36": len(common) == 36, "union == 40": len(union) == 40,
        "🔴 union 에만 있는 축": only_union,
        "「common 이 union 으로 퇴화」인가": len(common) == len(union),
        "축 이름 수(도메인별)": {d: len(list(d0.names.get(d) or []))
                                for d in doms},
        "union 전용 축을 가진 도메인": {
            a: [d for d in doms if a in list(d0.names.get(d) or [])]
            for a in only_union},
        "f.order == common": list(f.order) == common,
    }
    print(f"🔴 common={len(common)} · union={len(union)} · "
          f"union 전용={only_union}", flush=True)

    print("자료 build (fixaxes 없이) ...", flush=True)
    dpre = build(False)

    table, why, season = {}, {}, {}
    viol = []
    for d in doms:
        A, M, y, t = d0.dom[d]
        nm = list(d0.names.get(d) or [])
        hold = post[d].copy()
        sl = d0.slice(d, hold)
        p = np.asarray(f.predict(d, sl[0], sl[1], sl[3]), float)
        yh = np.asarray(y, float)[hold]
        ok = np.isfinite(p) & np.isfinite(yh)
        hidx = np.where(hold)[0][ok]
        n = len(hidx)

        Ah, Mh, th = A[hidx], M[hidx], np.asarray(t, float)[hidx]

        # 옛 열(899) --- `_feat` 만. **설계행렬이 아니다.**
        F_feat = FORMS.DirectPool._feat(Ah, Mh, nm, order)
        Fv, Fi = F_feat[:, 0::2], F_feat[:, 1::2]
        # 🔴 진짜 설계행렬 --- 챔피언이 `predict` 에서 그대로 부르는 것
        X = f._design(d, Ah, Mh, th)

        u_feat = uniq_rows(F_feat)
        u_design = uniq_rows(X)
        u_pred = nuniq(p[ok])
        if PLANT_FAULT and d == doms[0]:
            u_design = 1                      # 심는다 --- assert 가 우나?

        # 🔴 조항 59 — 부등호를 **기계가 본다**
        if not (u_pred <= u_design):
            viol.append({"도메인": d, "예측 고유": int(u_pred),
                         "설계행": int(u_design), "채점행": int(n)})

        # season 이 상수인가 --- 헤드라인 둘의 이유
        S = FORMS.BagBoost._season(th)
        season[d] = {
            "trend": A899.SRC.get(d, (None, None, "year(팝업=slots)"))[2],
            "t 표본(앞 5)": [None if not np.isfinite(v) else float(v)
                             for v in th[:5]],
            "season 값열 고유": int(nuniq(S[:, 0])),
            "season 표시자열 고유": int(nuniq(S[:, 1])),
            "🔴 season 이 상수인가": bool(nuniq(S[:, 0]) <= 1
                                         and nuniq(S[:, 1]) <= 1),
            "spec 열 고유(값/표시자)": [
                int(nuniq(f._spec_col(d, Ah, Mh, nm)[:, 0])),
                int(nuniq(f._spec_col(d, Ah, Mh, nm)[:, 1]))],
            "설계행렬 열 수": int(X.shape[1]),
            "_feat 열 수": int(F_feat.shape[1]),
        }

        live_feat = [order[j] for j in range(len(order))
                     if nuniq(Fv[:, j]) > 1 or nuniq(Fi[:, j]) > 1]
        nzA = [nm[j] for j in range(A.shape[1]) if nuniq(Ah[:, j]) > 1]

        table[d] = {
            "채점행": int(n), "판 가중": int(W.get(d, 0)),
            "채점행 == 판 가중(W3)": n == int(W.get(d, 0)),
            "축 이름 수": len(nm),
            "옛(899) 고유 `_feat` 행": int(u_feat),
            "🔴 고유 설계행 uniq(_design)": int(u_design),
            "예측 고유(씨앗0)": int(u_pred),
            "🔴 예측 고유 <= 설계행": bool(u_pred <= u_design),
            "옛 열에서 부등호가 깨졌나": bool(u_pred > u_feat),
            "_design − _feat": int(u_design - u_feat),
            "동률(설계행 기준) 채점행−설계행": int(n - u_design),
            "동률 비율(씨앗0)": round(1 - u_pred / n, 4) if n else None,
            "🔴 동률이 설계행렬에서 닫히나(예측==설계행)": bool(u_pred == u_design),
            "유보에서 살아 있는 축(order 중)": len(live_feat),
            "비상수 열 A": len(nzA),
        }

        # ── 배정: 다섯째 갈래 ⓓ 를 넣는다 ───────────────────────────
        rs = A899.raw_src(d)
        raw_ok = bool(rs and rs["n"] == len(y))
        Ap = dpre.dom[d][0] if d in dpre.dom else None
        Mp = dpre.dom[d][1] if d in dpre.dom else None
        nmp = list(dpre.names.get(d) or []) if d in dpre.dom else []
        buckets = {"ⓐ-0 축 없음(중립 채움)": [], "ⓐ 원천 무변이": [],
                   "ⓑ 전처리(BLOCK)": [], "ⓑ 전처리(그 밖)": [],
                   "ⓒ 유보 분할": [], "🔴 ⓓ 정식화가 안 본다": [],
                   "모른다": []}
        alive_899 = []
        for j, a in enumerate(nm):
            vcol = np.where(Mh[:, j] > 0, Ah[:, j], 0.5)
            icol = (Mh[:, j] > 0).astype(float)
            alive = (nuniq(vcol) > 1 or nuniq(icol) > 1)
            if a not in order:
                # 🔴 다섯째 갈래 --- 살아 있든 죽었든 **모형에 안 닿는다**
                buckets["🔴 ⓓ 정식화가 안 본다"].append(a)
                if alive:
                    alive_899.append(a)
                continue
            if alive:
                continue                       # 899 기준으로 살아 있다
            allA, allM = A[:, j], M[:, j]
            if (d, a) in FX.BLOCK:
                buckets["ⓑ 전처리(BLOCK)"].append(a); continue
            if np.all(allM == 0) and np.all(allA == 0.5):
                buckets["ⓐ-0 축 없음(중립 채움)"].append(a); continue
            if nuniq(allA) > 1 or nuniq(allM) > 1:
                buckets["ⓒ 유보 분할"].append(a); continue
            if a in nmp:
                jp = nmp.index(a)
                if nuniq(Ap[:, jp]) > 1 or nuniq(Mp[:, jp]) > 1:
                    buckets["ⓑ 전처리(그 밖)"].append(a); continue
            if raw_ok and a in A899.ALL5:
                if nuniq(rs[f"v:{a}"]) > 1 or nuniq(rs[f"m:{a}"]) > 1:
                    buckets["ⓑ 전처리(그 밖)"].append(a); continue
                buckets["ⓐ 원천 무변이"].append(a); continue
            buckets["모른다"].append(a)

        dead899 = sum(
            1 for j, a in enumerate(nm)
            if not (nuniq(np.where(Mh[:, j] > 0, Ah[:, j], 0.5)) > 1
                    or nuniq((Mh[:, j] > 0).astype(float)) > 1))
        d_cnt = len(buckets["🔴 ⓓ 정식화가 안 본다"])
        tot = sum(len(v) for v in buckets.values())
        # 새 분모: 「모형에 안 닿는 칸」 = 899 의 죽은 칸 + ⓓ 중 899 가 살아 있다 한 것
        untouched = dead899 + len(alive_899)
        why[d] = {
            "축 이름 수": len(nm),
            "899 죽은 열(모형 관점)": int(dead899),
            "🔴 ⓓ 칸": d_cnt,
            "🔴 ⓓ 중 899 가 '살아 있다'로 셌던 것": alive_899,
            "🔴 새 분자(모형에 안 닿는 칸)": int(untouched),
            "배정 합": int(tot), "배정 일치": tot == untouched,
            "원천 json 행 맞음(W4)": raw_ok,
            **{k: {"수": len(v), "이름": v} for k, v in buckets.items()},
        }
        print(f"  {d}: n={n} · _feat {u_feat} → _design {u_design} · "
              f"예측 {u_pred} · 부등호 {'OK' if u_pred <= u_design else '🔴깨짐'}"
              f" · ⓓ {d_cnt} · season상수 "
              f"{season[d]['🔴 season 이 상수인가']}", flush=True)

    # ── 🔴 조항 59 — 부등호를 assert 로 박는다 ──────────────────────────
    res["🔴 C1 · 부등호 검사"] = {
        "규칙": "결정적 함수 — 예측 고유 <= 설계행 uniq(_design). 위반은 정지",
        "위반": viol, "위반 수": len(viol),
        "심은 결함(PLANT_FAULT)": PLANT_FAULT,
    }
    assert not viol, f"🔴 예측 고유 > 설계행 — 설계행렬이 모형의 것이 아니다: {viol}"

    # ── 옛 표(899)를 **읽어서** 나란히 놓는다 --- 손 전사 금지(조항 60) ──
    old = json.load(open(OLD, encoding="utf-8"))
    oldt = old["12도메인 축퇴 표"]
    side = {}
    for d in doms:
        o = oldt.get(d, {})
        side[d] = {
            "채점행": table[d]["채점행"],
            "예측 고유(씨앗0)": table[d]["예측 고유(씨앗0)"],
            "899 파일이 적은 「고유 설계행 uniq(_feat)」": o.get(
                "🔴 고유 설계행 uniq(_feat)"),
            "🔴 진짜 설계행 uniq(_design)": table[d][
                "🔴 고유 설계행 uniq(_design)"],
            "🔴 899 표에서 예측>설계행 이었나": (
                None if o.get("🔴 고유 설계행 uniq(_feat)") is None else
                bool(o["예측 고유(씨앗0)"] > o["🔴 고유 설계행 uniq(_feat)"])),
            "예측 고유 재현(899 파일과 같나)": (
                o.get("예측 고유(씨앗0)") == table[d]["예측 고유(씨앗0)"]),
        }
    res["🔴 C1 · 12도메인 표(옛 `_feat` 대 진짜 `_design`)"] = side
    retro = [d for d in doms if side[d]["🔴 899 표에서 예측>설계행 이었나"]]
    res["🔴 C1 · 이 assert 를 899 초판에 걸었다면"] = {
        "발화했을 도메인": retro, "수": len(retro),
        "설명": ("옛 `_feat` 열로 부등호를 걸었으면 이 도메인들에서 즉시 죽는다 "
                 "--- 부등호는 표에 인쇄돼 있었고 기계만 안 봤다"),
        "🔴 조항 59 · 심어서 확인": {
            "이 파일": "python runners/out900a_design.py --plant-fault "
                       "→ 설계행을 1 로 심으면 AssertionError · 종료 1 "
                       "(산출물은 안 써진다 --- assert 가 write 앞에 있다)",
            "899 러너": "runners/axesdie899.py:219 의 assert 를 uniq_rows(88열) 만 "
                        "1 로 낮춰 심으면 AssertionError · 종료 1",
        },
    }
    res["12도메인 표(전량)"] = table
    res["🔴 season 상수 검사"] = season
    res["🔴 C2-ⓓ · 배정 다시"] = why

    tot_dead899 = sum(v["899 죽은 열(모형 관점)"] for v in why.values())
    tot_d = sum(v["🔴 ⓓ 칸"] for v in why.values())
    tot_new = sum(v["🔴 새 분자(모형에 안 닿는 칸)"] for v in why.values())
    names_tot = sum(v["축 이름 수"] for v in why.values())
    agg = {"ⓐ-0 축 없음(중립 채움)": 0, "ⓐ 원천 무변이": 0,
           "ⓑ 전처리(BLOCK)": 0, "ⓑ 전처리(그 밖)": 0, "ⓒ 유보 분할": 0,
           "🔴 ⓓ 정식화가 안 본다": 0, "모른다": 0}
    for v in why.values():
        for k in agg:
            agg[k] += v[k]["수"]
    res["🔴 C2-ⓓ · 305 의 새 분해"] = {
        "축 칸 총수(Σ 도메인별 축 이름 수)": names_tot,
        "899 죽은 칸(재현)": tot_dead899,
        "899 죽은 칸 == 305": tot_dead899 == 305,
        "🔴 ⓓ 칸": tot_d,
        "🔴 새 분자(모형에 안 닿는 칸)": tot_new,
        "갈래별": agg,
        "갈래별 비율(새 분자 기준)": {k: round(v / tot_new, 4) for k, v in
                                     agg.items()},
        "배정 합 == 새 분자": sum(agg.values()) == tot_new,
        "배정 일치 12/12": all(v["배정 일치"] for v in why.values()),
    }

    head2 = {d: {"채점행": table[d]["채점행"],
                 "예측 고유": table[d]["예측 고유(씨앗0)"],
                 "설계행(_design)": table[d]["🔴 고유 설계행 uniq(_design)"],
                 "동률이 닫히나": table[d][
                     "🔴 동률이 설계행렬에서 닫히나(예측==설계행)"],
                 "season 상수": season[d]["🔴 season 이 상수인가"]}
             for d in ("시장팝업", "영화") if d in table}
    res["🔴 헤드라인 둘 — 진짜 설계행렬에서도 서나"] = head2

    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n→ {OUT}", flush=True)
    print(json.dumps(res["🔴 C2-ⓓ · 305 의 새 분해"], ensure_ascii=False,
                     indent=1), flush=True)
    print(json.dumps(head2, ensure_ascii=False, indent=1), flush=True)


if __name__ == "__main__":
    main()
