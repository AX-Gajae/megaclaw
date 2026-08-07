"""재발굴 결과 적용 — 라벨을 고칠 때는 고치기 전 값을 반드시 남긴다.

라벨은 이 프로젝트에서 유일한 정답지다. 한 번 덮어쓰면 무엇이 원래 값이었는지
복원할 방법이 없고, 그러면 '언제부터 이 숫자였나'를 물을 수 없게 된다.
그래서 outcome.label_history에 매 변경을 append하고, 되돌릴 수 있게 한다.

처리 규칙:
  resolved=false          아무것도 바꾸지 않는다. 미해결로 남기고 무엇이 부족한지 기록.
  scope='event_wide'      라벨 철회(visitors=None). 부스 라벨이 아니라 행사 전체를
                          센 숫자이므로 부스 예측의 정답지가 될 수 없다.
                          단, 원문에 부스 단위 숫자가 따로 있으면 그것으로 교체.
  scope='multi_store_sum' 유지하되 scale.store_count를 확인 대상으로 표시.
                          합계 자체는 유효한 라벨이다 — 분모만 맞으면 된다.
  counting 변경           counting_method 갱신. 단위가 바뀌면 신뢰등급도 재평가한다.
  visitors 변경           값 교체 + 이전 값을 history에.

사용:
  python3 -m ingest.apply_relabel            # 무엇이 어떻게 바뀌는지만
  python3 -m ingest.apply_relabel --write    # 적용
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

RESULTS = Path("cycle_log/relabel")
ADJ = Path("cycle_log/relabel/_adjudication.json")
RECORDS = Path("data/records")
STAMP = "relabel R1 (2026-07-28)"

# 재발굴이 확정한 세분 단위 → 뱅크 원-핫 어휘(entry/participation/exposure/purchase/mixed/unknown).
# 뱅크 어휘에는 순방문/연방문 구분이 없다. 원-핫을 넓히면 n=74에서 표본이 쪼개지므로
# 세분 단위는 counting_detail에 따로 보존한다 — 발견 루프의 counting_scope 후보(7건 지지)가
# 지적한 '서로 다른 물리량을 같은 토큰으로 덮는' 문제를, 채점 쪽에서만 먼저 푼다.
UNIT_MAP = {"unique_entry": "entry", "visits": "entry", "participation": "participation",
            "exposure": "exposure", "purchase": "purchase", "digital_proxy": "unknown"}


def adjudicate(res: dict) -> dict:
    """판정층을 얹는다 — 에이전트 산출은 원문 사실, 판정은 우리 판단. 둘을 섞지 않는다.

    에이전트가 원문에서 확정한 값이라도 우리 채점 풀에 넣을 수 없는 경우가 있다.
    RIPU2519의 28,701은 8개 존 카운터의 합이라 1인이 존마다 중복 계수되고,
    다른 레코드의 participation 라벨과 물리량이 다르다. 그런 판단을 여기서 명시한다.
    """
    if not ADJ.exists():
        return res
    adj = json.loads(ADJ.read_text()).get(res["code"])
    if not adj:
        return res
    out = dict(res)
    out.update(adj.get("override") or {})
    out["_adjudicated"] = adj.get("reason", "")
    out["_trust_grade"] = adj.get("trust_grade")
    out["_keeps"] = adj.get("keeps")
    out["_period_fix"] = adj.get("period_fix")
    out["_detail_override"] = adj.get("counting_detail_override")
    out["_uncaptured"] = adj.get("note_uncaptured")
    return out


def plan(res: dict, rec: dict) -> dict:
    """무엇을 어떻게 바꿀지 결정. 실제 쓰기는 하지 않는다."""
    o = rec["outcome"]
    cur_v = o["totals"].get("visitors")
    cur_u = o.get("counting_method")
    act: dict = {"code": res["code"], "changes": [], "retract": False,
                 "resolved": bool(res.get("resolved"))}
    if not res.get("resolved"):
        act["note"] = res.get("missing") or "원문에서 확정 실패"
        return act

    if res.get("scope") == "event_wide" and res.get("visitors") in (None, cur_v):
        act["retract"] = True
        act["changes"].append(f"라벨 철회 — 행사 전체를 센 숫자({cur_v:,})라 부스 정답지가 아님")
        return act

    nv = res.get("visitors")
    if nv is not None and cur_v is not None and abs(nv - cur_v) > max(1, cur_v * 0.005):
        act["changes"].append(f"visitors {cur_v:,} → {nv:,.0f}")
        act["visitors"] = nv
    # 판정층이 세분 단위를 지정했으면 그것이 최종이다. 이걸 안 보면 에이전트 값과
    # 판정 값 사이를 매 실행마다 왕복한다.
    fine = res.get("_detail_override") or res.get("counting")
    nu = UNIT_MAP.get(res.get("counting") or "")
    if fine and fine != (o.get("counting_detail")):
        act["counting_detail"] = fine
        if nu == cur_u:
            act["changes"].append(f"집계 세분 {o.get('counting_detail') or '미지정'} → {fine} "
                                  f"(뱅크 단위는 {cur_u} 유지)")
    if nu and nu != cur_u:
        act["changes"].append(f"counting_method {cur_u} → {nu} (세분: {fine})")
        act["counting"] = nu
    if res.get("active_days"):
        ls = o.get("label_scope") or {}
        if ls.get("label_active_days") != res["active_days"]:
            act["changes"].append(
                f"운영일수 {ls.get('label_active_days')} → {res['active_days']:g}")
            act["active_days"] = res["active_days"]
    if res.get("_period_fix"):
        act["changes"].append(f"period 교정 {res['_period_fix']} (계획 문서 근거)")
    if res.get("scope") and res["scope"] != "this_booth":
        act["changes"].append(f"범위 표시: {res['scope']}")
        act["scope"] = res["scope"]
    return act


def apply(rec: dict, act: dict, res: dict) -> None:
    o = rec["outcome"]
    hist = o.setdefault("label_history", [])
    hist.append({"at": STAMP, "prev_visitors": o["totals"].get("visitors"),
                 "prev_counting": o.get("counting_method"),
                 "action": "retract" if act["retract"] else "revise",
                 "changes": act["changes"], "evidence": res.get("evidence", "")[:400],
                 "verdict": res.get("verdict", "")[:300]})
    if res.get("_period_fix"):
        per = rec["conditions"].setdefault("period", {})
        hist[-1]["period_prev"] = dict(per)
        per.update(res["_period_fix"])
        per["source"] = "재발굴 판정 — 계획 문서로 교정"
    if res.get("_adjudicated"):
        hist[-1]["adjudication"] = res["_adjudicated"]
        if res.get("_trust_grade"):
            o.setdefault("label_trust", {})["grade"] = res["_trust_grade"]
            o["label_trust"]["note"] = "재발굴 판정으로 조정 — " + res["_adjudicated"][:160]
        if res.get("_keeps"):
            o["label_alternates"] = res["_keeps"]
    if act["retract"]:
        o["totals"]["visitors"] = None
        o["label_retracted"] = {"reason": "행사 전체 집계 — 부스 라벨 아님", "at": STAMP}
        return
    if "visitors" in act:
        o["totals"]["visitors"] = act["visitors"]
    if "counting" in act:
        o["counting_method"] = act["counting"]
    if "counting_detail" in act:
        o["counting_detail"] = act["counting_detail"]
    if res.get("_detail_override"):
        o["counting_detail"] = res["_detail_override"]
    if res.get("_uncaptured"):
        o["uncaptured_sibling"] = res["_uncaptured"]
    if "active_days" in act:
        o.setdefault("label_scope", {})["label_active_days"] = act["active_days"]
        o["label_scope"]["source"] = f"재발굴 확정 ({STAMP})"
    if "scope" in act:
        o["label_scope_kind"] = act["scope"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    files = sorted(RESULTS.glob("*.result.json"))
    if not files:
        print("재발굴 결과 없음 — 에이전트 산출을 기다린다")
        return 0
    done, unresolved, nochange = [], [], []
    for f in files:
        res = adjudicate(json.loads(f.read_text()))
        p = RECORDS / f"{res['code']}.json"
        if not p.exists():
            continue
        rec = json.loads(p.read_text())
        act = plan(res, rec)
        if not act["resolved"]:
            unresolved.append((act["code"], act.get("note", "")))
            continue
        if not act["changes"]:
            nochange.append(act["code"])
            continue
        done.append(act)
        if a.write:
            apply(rec, act, res)
            p.write_text(json.dumps(rec, ensure_ascii=False, indent=1))

    print(json.dumps({"결과 파일": len(files), "변경": len(done),
                      "확정했으나 변경 없음": len(nochange),
                      "미해결": len(unresolved), "철회": sum(1 for x in done if x["retract"]),
                      "기록": bool(a.write)}, ensure_ascii=False))
    for act in done:
        print(f"\n■ {act['code']}")
        for ch in act["changes"]:
            print(f"   {ch}")
    if nochange:
        print(f"\n■ 원문 확인 결과 현재 값이 맞음: {', '.join(nochange)}")
    if unresolved:
        print("\n■ 미해결 (라벨 그대로 두고 결함 표시 유지)")
        for c, n in unresolved:
            print(f"   {c}: {n[:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
