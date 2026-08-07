"""피처 발견 루프 — 실패에서 변수를 찾아내는 과정 자체를 하네스로.

지금까지는 매번 수동이었다: 미스를 눈으로 고르고 → 워크플로를 손으로 짜고 → 피처를 정의하고
→ 재측정. 그 반복이 곧 이 프로젝트의 학습 방식이므로 절차로 고정한다.

루프 5단계 (각 단계가 다음 단계의 입력을 파일로 남긴다):

  1) SELECT   채점 장부에서 조사할 실패를 자동 선별
              — 오차 상위 + 과대/과소 균형 + 이미 조사한 건 제외(중복 방지)
  2) PROBE    사례별 조사 요청 생성 (원문 + 당시 맥락). 실행은 에이전트(2패스, API $0)
  3) HARVEST  조사 결과에서 변수 후보를 수집·정규화, 사례 지지 수로 랭킹
  4) TAG      채택된 변수를 전 레코드에 태깅하는 요청 생성 (역시 에이전트 2패스)
  5) VERIFY   페어드 절제로 기여 검정 → 채택/기각을 장부에 기록

핵심 규율:
  · 사후 정보 금지 — 추출 경로에 사전 문서가 없으면 'scoring'으로 강등해 피처로 못 쓴다
  · 조사 대상은 소모 처리 — 같은 폴드를 반복 조사해 과적합하지 않도록 ledger에 기록
  · 기각도 기록 — 시도했으나 기여 없던 변수를 남겨 재시도를 막는다
  · 선별은 위생 게이트를 통과한 채점만 본다(label_hygiene) — 철회·스코프이탈 라벨의
    오차는 모델 오차가 아니라 측정 오차이므로 조사해도 나오는 게 없다

사용:
  python3 -m harness.discovery select [n]              # 이번 라운드 조사 대상 선정
  python3 -m harness.discovery probe [라운드]           # 조사 요청서 생성(에이전트 투입용)
  python3 -m harness.discovery harvest <결과.json>      # 조사 결과 → 통합 변수 후보
  python3 -m harness.discovery verify <접두어> [레인] [축]  # 페어드 절제로 기여 검정
  python3 -m harness.discovery ledger                  # 발견·채택·기각 이력
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

LEDGER = Path("cycle_log/discovery_ledger.json")
ROUNDS = Path("cycle_log/discovery")


def _ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"rounds": [], "probed": [], "features": {}}


def _save(led: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(led, ensure_ascii=False, indent=1))


def collect_scores(gated: bool = True) -> list[dict]:
    """채점 장부 전체에서 (코드, 예측, 실측, 오차) 수집.

    gated=True면 label_hygiene을 통과한 건만 반환한다. 리포트 파일은 채점 시점의
    스냅샷이라 라벨이 그 뒤 철회·수정돼도 남는다(1라운드에서 RIPU2518이 이 경로로
    조사 대상에 다시 뽑혔다). 살아 있는 레코드를 진실로 삼아 대조한다.
    """
    from .label_hygiene import _unit_counts, eligible

    unit_n = _unit_counts() if gated else None
    rows, seen, dropped = [], set(), Counter()
    for f in sorted(Path("cycle_log").rglob("*.report.md")):
        code = f.stem.replace(".report", "")
        if code in seen:
            continue
        m = re.search(r"visitors.*?예측 ([\d,]+) / 실측 ([\d,]+) / APE ([\d.]+)%", f.read_text())
        if not m:
            continue
        p, a = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
        if gated:
            rp = Path(f"data/records/{code}.json")
            if not rp.exists():
                dropped["레코드 없음"] += 1
                continue
            rec = json.loads(rp.read_text())
            cur = rec["outcome"]["totals"].get("visitors")
            if cur is None:                       # 라벨 철회 후 남은 stale 리포트
                dropped["라벨 철회"] += 1
                continue
            if cur != a:                          # 라벨 수정됨 — 옛 값 채점은 무효
                dropped["라벨 변경"] += 1
                continue
            ok, why = eligible(rec, unit_n)
            if not ok:
                dropped[f"위생 탈락"] += 1
                continue
        seen.add(code)
        rows.append({"code": code, "pred": p, "actual": a, "ape": float(m.group(3)),
                     "dir": "over" if p > a else "under", "dir_kr": "과대" if p > a else "과소",
                     "cycle": str(f.parent.name)})
    if gated and dropped:
        print(f"  [위생 게이트] 제외 {sum(dropped.values())}건 — {dict(dropped)}", file=sys.stderr)
    return rows


def select(n: int = 12) -> list[dict]:
    """조사 대상 선별 — 오차 상위, 과대/과소 균형, 기조사 제외."""
    led = _ledger()
    done = set(led["probed"])
    rows = [r for r in collect_scores() if r["code"] not in done]
    rows.sort(key=lambda r: -r["ape"])
    over = [r for r in rows if r["dir"] == "over"][: n // 2]
    under = [r for r in rows if r["dir"] == "under"][: n - len(over)]
    picked = over + under
    # 레코드 메타 부착
    for r in picked:
        p = Path(f"data/records/{r['code']}.json")
        if p.exists():
            rec = json.loads(p.read_text())
            per = rec["conditions"].get("period") or {}
            r.update({"from": per.get("from"),
                      "brand": rec["entities"].get("brand_key")
                               or rec["intervention"].get("brand_name"),
                      "space": rec["entities"].get("space_key")})
    rnd = len(led["rounds"]) + 1
    ROUNDS.mkdir(parents=True, exist_ok=True)
    (ROUNDS / f"round{rnd}_targets.json").write_text(json.dumps(picked, ensure_ascii=False, indent=1))
    print(json.dumps({"라운드": rnd, "선정": len(picked),
                       "과대": sum(1 for r in picked if r["dir"] == "over"),
                       "과소": sum(1 for r in picked if r["dir"] == "under"),
                       "오차 범위": [round(min(r["ape"] for r in picked), 1),
                                     round(max(r["ape"] for r in picked), 1)],
                       "저장": str(ROUNDS / f"round{rnd}_targets.json")}, ensure_ascii=False))
    return picked


PROBE_TMPL = """대형 예측 실패 원인 규명 — **원문을 직접 읽고 무엇을 봤어야 했는지 발견하라.**

대상: {code} / 브랜드 {brand} / 장소 {space} / 오픈 {open_from}
결과: **예측 {pred:,}명 vs 실측 {actual:,}명 (오차 {ape}%)**
→ {direction}

조사 순서:
1. Read로 `data/records/{code}.json` 전체 — 기획·조건·결과·근거.
2. 사전 문서를 직접 열어라. 다음 명령이 이 레코드의 **오픈 전 작성 문서만** 골라 준다:
     python3 -c "import json;from ingest.doc_select import describe;\\
       print(chr(10).join(describe(json.load(open('data/records/{code}.json')))))"
   ToolSearch로 mcp__claude_ai_Google_Drive__read_file_content 를 로드하고
   uri의 /file/d/<ID>/view 에서 ID를 뽑아 읽는다.
   결과보고서도 이번엔 읽어도 된다 — **사후 분석이므로**. 다만 무엇이 사전에 알 수
   있었는지는 엄격히 구분하라.
3. **당시 맥락을 조사하라** (여기가 핵심): WebSearch로
   - 그 IP/브랜드가 {open_from} 시점에 어떤 상태였나 (신작·컴백·논란·인기 정점/하락)
   - 그 상권/장소에 같은 시기 다른 대형 팝업이나 행사가 있었나
   - 시기 요인 (연휴·방학·폭염·한파·수능·명절·경쟁 이벤트)
   - 그 팝업 자체의 화제성 보도나 SNS 반응
4. 판정:
   - missed_signals: 못 본 신호들. 각각 where_found / direction(위·아래) /
     generalizable(다른 팝업에도 적용 가능한 변수인가)
   - observable_now: **예측 시점에 알 수 있었는가**. 되었다면 어느 소스에서.
   - verdict: feature_missing(기획서에 있었는데 안 뽑음) / state_missing(외부 상태) /
     label_problem(라벨 자체가 이상) / unpredictable(사전에 알 길 없음)

정직하게: 사후에야 알 수 있는 것을 "예측 가능했다"고 하지 마라. 그 구분이 이 조사의 값이다.

이미 기각된 변수는 다시 제안하지 마라 — {rejected}
"""

PROBE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["code", "root_cause", "missed_signals", "observable_now", "verdict"],
    "properties": {
        "code": {"type": "string"},
        "root_cause": {"type": "string", "description": "왜 틀렸는지 한 문장"},
        "missed_signals": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["signal", "where_found", "direction", "generalizable"],
            "properties": {"signal": {"type": "string"}, "where_found": {"type": "string"},
                           "direction": {"type": "string"},
                           "generalizable": {"type": "boolean"}}}},
        "observable_now": {"type": "string"},
        "verdict": {"type": "string", "enum": ["feature_missing", "state_missing",
                                                "label_problem", "unpredictable"]},
        "notes": {"type": "string"}},
}


def probe(round_no: int | None = None) -> str:
    """[2단계 PROBE] 선정된 대상별 조사 요청서를 파일로 낸다.

    지금까지 매 라운드 워크플로를 손으로 짰다. 프롬프트가 라운드마다 미묘하게
    달라지면 라운드 간 비교가 불가능해지므로 템플릿으로 고정한다.
    기각된 변수 목록을 프롬프트에 실어 같은 제안이 반복되는 것을 막는다.
    """
    led = _ledger()
    rnd = round_no or len(led["rounds"]) + 1
    tgt_f = ROUNDS / f"round{rnd}_targets.json"
    if not tgt_f.exists():
        raise SystemExit(f"{tgt_f} 없음 — 먼저 select를 돌려라")
    targets = json.loads(tgt_f.read_text())
    rejected = [k for k, v in led["features"].items() if not v["adopted"]] or ["(없음)"]

    out_dir = ROUNDS / f"round{rnd}_probes"
    out_dir.mkdir(parents=True, exist_ok=True)
    for t in targets:
        body = PROBE_TMPL.format(
            code=t["code"], brand=t.get("brand"), space=t.get("space"),
            open_from=t.get("from"), pred=t["pred"], actual=t["actual"], ape=t["ape"],
            direction=("과대예측: 왜 생각보다 안 왔나" if t["pred"] > t["actual"]
                       else "과소예측: 왜 생각보다 많이 왔나"),
            rejected=", ".join(sorted(set(re.sub(r"\[.*?\]", "", x) for x in rejected))))
        (out_dir / f"{t['code']}.probe.md").write_text(body)
    (out_dir / "_schema.json").write_text(json.dumps(PROBE_SCHEMA, ensure_ascii=False, indent=1))
    print(json.dumps({"라운드": rnd, "조사 요청": len(targets), "디렉토리": str(out_dir),
                       "기각 변수 안내": len(rejected)}, ensure_ascii=False))
    print(f"\n각 .probe.md 를 에이전트에 주고, 결과를 스키마대로 모아 "
          f"round{rnd}_forensics.json 의 forensics 배열로 저장한 뒤 harvest 를 돌려라.")
    return str(out_dir)


# 예측 시점에 존재하지 않는 출처 — 여기서만 뽑히면 채점용이지 예측 피처가 아니다.
LEAK_SRC = re.compile(r"outcome\.|결과보고서|정산서|사후")
# 오픈 전에 존재하는 출처 — 하나라도 있으면 누출 없는 추출 경로가 있다는 뜻
PRE_SRC = re.compile(r"기획서|계약서|견적서|운영안|제안서|파일명|docs\[|웹\s*검색|달력|"
                     r"학사일정|공휴일|conditions\.|보도자료|사전")


def _usable(how: str, leak_ok: bool = True) -> str:
    """추출 경로가 예측 시점에 성립하는가. 사후 출처만 있으면 'scoring'."""
    if PRE_SRC.search(how):
        return "feature"
    return "scoring" if LEAK_SRC.search(how) else "feature"


def harvest(result_path: str) -> dict:
    """조사 결과 → 변수 후보 랭킹.

    원시 missed_signals를 그대로 세면 에이전트마다 표현이 달라 전부 '1건 지지'가 된다
    (1라운드: 153개 후보 전부 단일 지지). 종합 단계가 이미 개념 단위로 통합해 두므로
    그것을 후보로 삼고, 원시 신호는 근거로만 붙인다.

    각 후보에 `usable` 판정을 단다:
      feature  — 사전 문서에서 뽑히는 예측 피처
      scoring  — 사후 출처(outcome·결과보고서)에서만 나옴. 라벨 교정에만 쓸 수 있다.
      blocked  — 예측 시점 관측 불가(time_maskable=false)
    """
    data = json.loads(Path(result_path).read_text())
    forensics = data.get("forensics") or data
    design = data.get("design") or {}
    led = _ledger()
    rnd = len(led["rounds"]) + 1

    verdicts, raw_by_code = Counter(), {}
    for f in forensics:
        verdicts[f.get("verdict", "?")] += 1
        led["probed"].append(f.get("code"))
        raw_by_code[f.get("code")] = [s for s in (f.get("missed_signals") or [])
                                      if s.get("generalizable")]
    n_raw = sum(len(v) for v in raw_by_code.values())

    cands = []
    for f in design.get("new_features") or []:
        how = str(f.get("how_to_extract", ""))
        cands.append({"name": f["name"], "kind": "doc_feature",
                      "cases": int(f.get("cases_supporting") or 0),
                      "usable": _usable(how),
                      "definition": f.get("definition", ""), "extract": how,
                      "expected": f.get("expected_impact", "")})
    for s in design.get("state_variables") or []:
        cands.append({"name": s["name"], "kind": "state_var",
                      "cases": 0,
                      "usable": "feature" if s.get("time_maskable") else "blocked",
                      "definition": s.get("definition", ""),
                      "extract": s.get("source", ""), "expected": ""})
    cands.sort(key=lambda c: (-c["cases"], c["usable"] != "feature", c["name"]))

    led["rounds"].append({"round": rnd, "n_probed": len(forensics),
                           "verdicts": dict(verdicts), "raw_signals": n_raw,
                           "candidates": len(cands),
                           "usable": Counter(c["usable"] for c in cands)})
    led["probed"] = sorted(set(led["probed"]))
    _save(led)
    out = ROUNDS / f"round{rnd}_candidates.json"
    out.write_text(json.dumps({"candidates": cands, "raw_signals": raw_by_code},
                              ensure_ascii=False, indent=1))
    u = Counter(c["usable"] for c in cands)
    print(json.dumps({"라운드": rnd, "조사": len(forensics), "판정": dict(verdicts),
                       "원시 신호": n_raw, "통합 후보": len(cands),
                       "가용": dict(u), "저장": str(out)}, ensure_ascii=False))
    mark = {"feature": "✅", "scoring": "⚠️ 채점전용", "blocked": "🚫 사후정보"}
    for c in cands:
        sup = f"{c['cases']}건" if c["cases"] else "  — "
        print(f"  {mark[c['usable']]:>10s} {sup:>5s} 지지 · {c['name']}")
    return {"candidates": cands, "verdicts": dict(verdicts)}


def verify(prefix: str, domain: str = "popup", axis: str = "per_day",
           lane: str = "gbdt", grades: tuple = ("A", "B"), only: str | None = None) -> dict:
    """[5단계 VERIFY] 컬럼 접두어로 절제해 페어드 부트스트랩. 같은 폴드·같은 시드.

    피처를 넣은 레인과 뺀 레인이 **같은 분할·같은 표본**을 보므로 차이의 CI가
    0을 넘지 않으면 기여가 있다고 본다. 기각도 장부에 남긴다 — 재시도를 막기 위해.

    `only`로 도메인을 좁힌다. 이게 없으면 무의미한 널이 나온다: t1_ 첫 검정에서
    Δ가 정확히 0.0(CI[0,0])이었는데, 학습 표본 53개 중 t1_ 값이 있는 행이 3개라
    트리가 그 컬럼으로 분기할 수조차 없었기 때문이다. 시장 레코드에는 T1 태깅이
    없으므로 내부 레코드 피처는 내부 풀에서 검정해야 한다.

    적용 가능 표본이 얇으면 결과를 '기각'이 아니라 '검정불가'로 낸다 —
    없는 기여와 잴 수 없는 기여는 다르다.
    """
    import numpy as np

    from state.evaluate import LANES, _col, group_time_folds, paired_bootstrap

    d = np.load(f"data/state/{domain}_v2.npz", allow_pickle=True)
    X, cols = d["X"], list(d["names"])
    y = d["y_perday"] if axis == "per_day" else d["y_total"]
    w = d["w"]
    meta = json.loads(Path(f"data/state/{domain}_v2_meta.json").read_text())
    keep = np.zeros(len(y), bool)
    for g in grades:
        i = _col(cols, f"trust_{g}")
        if i is not None:
            keep |= X[:, i] > 0.5
    ok = np.isfinite(y) & keep
    if only:                                   # 도메인 한정 (예: popup_internal)
        ok &= np.array([str(m.get("domain", "")).startswith(only) for m in meta])
    X, y, w = X[ok], y[ok], w[ok]
    meta = [m for m, k in zip(meta, ok) if k]

    tgt = [i for i, c in enumerate(cols) if str(c).startswith(prefix)]
    if not tgt:
        raise SystemExit(f"'{prefix}' 로 시작하는 컬럼 없음")
    rest = [i for i in range(X.shape[1]) if i not in set(tgt)]
    n_applic = int((np.abs(X[:, tgt]).sum(1) > 0).sum())    # 값이 실제로 있는 행
    cols_on, cols_off = cols, [cols[i] for i in rest]

    folds = group_time_folds(np.array([m.get("ip") or m["id"] for m in meta]),
                             np.array([m.get("date") or "9999" for m in meta]))
    e_on, e_off = [], []
    for tr, te in folds:
        e_on.append(np.abs(LANES[lane](X[tr], y[tr], w[tr], X[te], cols_on) - y[te]))
        e_off.append(np.abs(LANES[lane](X[np.ix_(tr, rest)], y[tr], w[tr],
                                        X[np.ix_(te, rest)], cols_off) - y[te]))
    a, b = np.concatenate(e_on), np.concatenate(e_off)
    m, lo, hi = paired_bootstrap(a, b)                    # 음수면 '넣은 쪽'이 낫다
    testable = n_applic >= 20 and n_applic / max(1, len(y)) >= 0.15
    res = {"feature": prefix, "lane": lane, "axis": axis, "n": int(len(y)),
           "적용가능": n_applic, "검정가능": testable,
           "folds": len(folds), "cols": len(tgt),
           "mae_on": round(float(a.mean()), 4), "mae_off": round(float(b.mean()), 4),
           "delta": round(m, 4), "ci95": [round(lo, 4), round(hi, 4)],
           "adopted": bool(hi < 0 and testable)}
    print(json.dumps(res, ensure_ascii=False))
    if not testable:
        print(f"  ⚠️ 검정불가 — 값이 있는 행 {n_applic}/{len(y)}. "
              f"없는 기여와 잴 수 없는 기여는 다르다. 장부에 기록하지 않는다.")
        return res
    record_verdict(f"{prefix}[{lane}/{axis}{'/' + only if only else ''}]", res["adopted"],
                   res["delta"], res["ci95"],
                   f"n={res['n']} 적용{n_applic} 컬럼{len(tgt)} "
                   f"MAE {res['mae_off']:.4f}→{res['mae_on']:.4f}")
    return res


def record_verdict(feature: str, adopted: bool, delta: float, ci: list, note: str = "") -> None:
    """VERIFY 결과를 장부에 — 기각도 남겨 재시도를 막는다."""
    led = _ledger()
    led["features"][feature] = {"adopted": adopted, "delta_log10": delta, "ci95": ci,
                                 "note": note, "round": len(led["rounds"])}
    _save(led)
    print(json.dumps({feature: led["features"][feature]}, ensure_ascii=False))


def show_ledger() -> None:
    led = _ledger()
    print(f"발견 라운드: {len(led['rounds'])} / 조사한 폴드: {len(led['probed'])}")
    for r in led["rounds"]:
        print(f"  R{r['round']}: {r['n_probed']}건 조사 → 후보 {r['candidates']} / 판정 {r['verdicts']}")
    if led["features"]:
        print("\n검정된 변수:")
        for k, v in led["features"].items():
            mark = "✅ 채택" if v["adopted"] else "❌ 기각"
            print(f"  {mark} {k}: Δ{v['delta_log10']:+.4f} CI{v['ci95']} {v['note'][:50]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ledger"
    if cmd == "select":
        select(int(sys.argv[2]) if len(sys.argv) > 2 else 12)
    elif cmd == "harvest":
        harvest(sys.argv[2])
    elif cmd == "probe":
        probe(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "verify":
        verify(sys.argv[2], lane=sys.argv[3] if len(sys.argv) > 3 else "gbdt",
               axis=sys.argv[4] if len(sys.argv) > 4 else "per_day",
               only=sys.argv[5] if len(sys.argv) > 5 else None)
    elif cmd == "ledger":
        show_ledger()
    else:
        print(__doc__)
