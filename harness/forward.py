"""블록 2 — 전향 사이클 정례 패스. 주 1회 실행 설계 (수동: python3 -m harness.forward).

한 번의 패스가 하는 일:
  1. P&L 재추출 → 비완결 레코드의 rev_mm·완결상태 갱신
  2. 다가오는/진행 중 팝업 발굴(기획서·계약서가 Drive에 태깅된 것) → 정규화 → 뱅크 투입
  3. 아직 커밋 없는 미래 팝업에 A' 구성으로 예측 봉인 (cycle_log/forward/)
  4. 기존 전향 커밋 중 실측(방문 or 완결 rev)이 도착한 것 자동 채점
BQ는 읽기 전용(SELECT만). 예측 봉인은 오픈 전 팝업만 — 오픈 후엔 봉인 금지(무결성).
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

INGEST = Path("data/ingest")  # 2026-07-27 스크래치패드(휘발성 임시폴더) 탈출 — 리포 내로 이관
FWD = Path("cycle_log/forward")
SNAP_QUERY = ('SELECT project_code, ROUND(SUM(amount)/1e6,1) revenue_mm, MAX(close_period) last_p '
              'FROM `sweetspot-ax.ods.amaranth_project_pnl` '
              'WHERE grain_type="MONTHLY" AND section_name="매출액" AND line_type="detail" GROUP BY 1')


def bq_json(sql: str) -> list:
    out = subprocess.run(["bq", "query", "--project_id=sweetspot-ax", "--use_legacy_sql=false",
                          "--format=json", "--max_rows=2000", sql],
                         capture_output=True, text=True, check=True).stdout
    line = [l for l in out.strip().splitlines() if l.startswith("[")]
    return json.loads(line[-1]) if line else []


def step1_refresh_pnl() -> int:
    rows = bq_json(SNAP_QUERY)
    pnl = {r["project_code"]: (float(r["revenue_mm"]), r["last_p"]) for r in rows if r.get("revenue_mm")}
    updated = 0
    for p in Path("data/records").glob("*.json"):
        r = json.loads(p.read_text())
        comp = r["outcome"].get("rev_mm_completion", {})
        if comp.get("status") == "complete":
            continue
        code = r["record_id"]
        if code not in pnl:
            continue
        rev, last_p = pnl[code]
        old = r["outcome"]["totals"].get("rev_mm_recognized")
        ct = comp.get("contract_total_mm")
        if old == rev and comp.get("last_recognition_period") == last_p:
            continue
        r["outcome"]["totals"]["rev_mm_recognized"] = rev
        if ct and abs(rev - ct) / ct <= 0.10:
            comp.update({"status": "complete", "rule": f"인식 {rev} ≈ 계약총액 {ct} (전향 갱신)"})
        else:
            comp.update({"status": comp.get("status", "unknown"), "rule": f"갱신: 인식 {rev}, 총액 {ct}"})
        comp["last_recognition_period"] = last_p
        r["outcome"]["rev_mm_completion"] = comp
        p.write_text(json.dumps(r, ensure_ascii=False, indent=2))
        updated += 1
    print(f"[1] P&L 갱신: {updated}건 rev_mm/완결상태 변경")
    return updated


def step2_discover_and_normalize() -> list[str]:
    today = date.today().isoformat()
    horizon = (date.today() + timedelta(days=150)).isoformat()
    have = {p.stem for p in Path("data/records").glob("*.json")} | \
           {p.stem for p in Path("data/records_incomplete").glob("*.json")} | \
           {p.stem for p in Path("data/records_draft").glob("*.json")}
    rows = bq_json(f'''
      SELECT e.engagement_code AS project_code, CAST(e.start_date AS STRING) AS operating_from,
             CAST(e.end_date AS STRING) AS operating_to,
             (SELECT COUNT(*) FROM `sweetspot-ax.stg_drive.file_objects_dedup` d
              WHERE d.project_code = e.engagement_code
                AND d.document_type IN ("contract","proposal","event_plan","estimate")) AS key_docs
      FROM `sweetspot-ax.core.engagement` e
      WHERE e.start_date BETWEEN "{today}" AND "{horizon}"''')
    cands = [r for r in rows if int(r["key_docs"] or 0) >= 1 and r["project_code"] not in have]

    # 폴백: Drive 문서 미태깅 단계(계약 전)의 팝업 — 리서치 테이블(기획 요약)로 발굴.
    # 전향 예측은 그 시점에 존재하는 정보로 하는 것이 정직하다(계약서 없으면 없는 대로).
    research = bq_json(f'''
      SELECT project_code, project_name, client_name, venue, category,
             operating_from, operating_to, SUBSTR(report_md, 1, 8000) report_md
      FROM `sweetspot-ax.curated.pu26_project_research`
      WHERE operating_from BETWEEN "{today}" AND "{horizon}"''')
    drive_codes = {r["project_code"] for r in cands}
    research_cands = [r for r in research if r["project_code"] not in have and r["project_code"] not in drive_codes]

    if not cands and not research_cands:
        print("[2] 신규 발굴: 0건")
        return []
    codes = [r["project_code"] for r in cands] + [r["project_code"] for r in research_cands]
    print(f"[2] 신규 발굴: Drive문서 {len(cands)}건 + 리서치기반 {len(research_cands)}건 → {', '.join(codes)}")
    proj_path = INGEST / "projects_forward.json"
    proj_path.write_text(json.dumps(
        [{**r, "project_name": None} for r in cands] + research_cands, ensure_ascii=False))
    docs = bq_json('SELECT project_code, document_type, file_name, drive_file_id, mime_type, size_bytes '
                   'FROM `sweetspot-ax.stg_drive.file_objects_dedup` WHERE document_type != "other" '
                   f'AND project_code IN ({",".join(chr(34)+c+chr(34) for c in codes)})')
    docs_path = INGEST / "docs_forward.json"
    docs_path.write_text(json.dumps(docs, ensure_ascii=False))
    # 🔴 **종량제 API 를 안 부른다**(2026-08-09 · 노트 888). 옛 코드는 `--agent-dir`
    # 없이 불렀고 그러면 `bulk_normalize` 가 `anthropic.Anthropic()` 경로로 간다.
    # 2026-08-09 실행에서 그것이 이렇게 끝났다 ---
    #   [2] ROPU2616 실패: 400 'Your credit balance is too low'  → 뱅크 투입 0건
    # 그런데 **종료 코드는 0** 이라 크론 로그만 보면 성공이다.
    #
    # `core/agent_task.py` 가 이 문제를 위해 이미 존재한다 --- 그 독스트링:
    #   *"배경(2026-07-27): 인제스트·예측을 종량제 API로 돌려 하루 $297 발생.
    #     무인 크론이 아닌 작업은 세션 에이전트가 처리하면 추가 비용이 0이다."*
    # 이 패스는 이제 **무인 크론이 아니라 연구 루프의 스텝**이므로(사용자 지시
    # 2026-08-09: *"크론 돌려두면 테스트 주기도 길고 틀렸을 때 대처가 안 된다"*)
    # 에이전트 경로가 맞다. 비용 0 이고, 실패하면 그 자리에서 고친다.
    #
    # **2패스다.** 1패스는 `{AGENT_DIR}/*.req.json` 을 덤프하고 그 항목을 스킵한다
    # (그래서 첫 패스의 '투입 0건' 은 실패가 아니다). 에이전트가 `.res.json` 을
    # 채우고 같은 명령을 다시 돌리면 적용된다. `res.json` 이 있으면 항상 그것을
    # 쓰므로 몇 번 재실행해도 안전하다.
    AGENT_DIR = "cycle_log/agent_tasks/forward"
    subprocess.run([sys.executable, "-m", "ingest.bulk_normalize",
                    "--projects", str(proj_path), "--docs", str(docs_path),
                    "--agent-dir", AGENT_DIR], check=True)
    # 이름 규칙은 `AgentTask`: `{task_id}.req.json` / `{task_id}.res.json`.
    # `with_suffix` 를 쓰면 task_id 에 점이 있을 때 조용히 어긋나므로 문자열로 짝짓는다.
    ad = Path(AGENT_DIR)
    pend = [p for p in sorted(ad.glob("*.req.json")) if ad.is_dir()
            and not (ad / (p.name[:-len(".req.json")] + ".res.json")).exists()]
    if pend:
        print(f"[2] ⏳ 에이전트 대기 {len(pend)}건 — {AGENT_DIR}/*.req.json 을 읽고 "
              f"같은 이름의 .res.json 을 쓴 뒤 이 패스를 다시 돌린다")
    # 리서치 기반 레코드는 Drive 문서가 없으므로 Notion 페이지를 docs로 연결
    research_codes = {r["project_code"]: r for r in research_cands}
    notion_links = {}
    if research_codes:
        names = []
        for r in research_codes.values():
            nm = (r.get("project_name") or "").split("(")[0].strip()
            if len(nm) >= 2:
                names.append((r["project_code"], nm))
        if names:
            pat = "|".join(n.replace('"', "") for _, n in names)
            pages = bq_json('SELECT title, url FROM `sweetspot-ax.stg_notion.objects_dedup` '
                            f'WHERE object_type="page" AND REGEXP_CONTAINS(title, r"{pat}") LIMIT 100')
            for code, nm in names:
                notion_links[code] = [{"doc_id": f"notion-{i}", "kind": "기획서", "uri": p["url"],
                                        "title": p["title"]} for i, p in enumerate(pages) if nm in p["title"]][:4]

    moved = []
    for c in codes:
        d = Path(f"data/records_draft/{c}.json")
        if d.exists():
            r = json.loads(d.read_text())
            if not r.get("docs") and notion_links.get(c):
                r["docs"] = notion_links[c]
                r["provenance"]["notes"] += " | 전향 리서치 기반(계약 전 단계) — Drive 원문 태깅 후 재정규화 대상"
            if not r.get("docs"):
                d.rename(f"data/records_incomplete/{c}.json"); continue
            # 🔴 **팝업이 아닌 것을 뱅크에 넣지 않는다**(2026-08-09 · 노트 888).
            # 여기 게이트는 오래 **"문서가 있나" 하나뿐**이었다. 그래서 전향 발굴이
            # 물어 온 `ROPU2616`(= SDT 양자체험관 리뉴얼 **시공** · 문서 3건)이
            # 그대로 통과해 `data/records/` 로 들어가고 step3 가 **방문객이 없는
            # 것에 방문 예측을 봉인**할 참이었다. 추출 스키마가 필드를 강제하므로
            # 추출기는 없는 방문객도 뭐라도 채워 넣는다 --- 조용히.
            kind = (r.get("provenance", {}).get("record_kind")
                    or r.get("record_kind") or "unknown")
            if kind != "popup":
                r.setdefault("provenance", {})["notes"] = (
                    r.get("provenance", {}).get("notes", "")
                    + f" | 전향 발굴에서 record_kind={kind} 로 판정되어 뱅크 투입 보류")
                Path(f"data/records_incomplete/{c}.json").write_text(
                    json.dumps(r, ensure_ascii=False, indent=2))
                d.unlink()
                print(f"[2] ⛔ {c}: record_kind={kind} — 팝업이 아니라 뱅크에 안 넣는다")
                continue
            r["provenance"]["reviewed_by"] = "전향 자동투입(미검수)"
            Path(f"data/records/{c}.json").write_text(json.dumps(r, ensure_ascii=False, indent=2))
            d.unlink(); moved.append(c)
    if moved:
        # 🔴 **후처리는 아직 유료 전용이다**(2026-08-10 · 노트 889).
        # `ingest/postprocess.py` 에는 `--agent-dir` 가 없다 --- `bulk_normalize`
        # 와 달리 무료 경로가 **아예 없다**. 그래서 `core.noapi` 가 여기를 막는다.
        # 옛 코드는 `check=True` 라 막히는 순간 **전향 패스 전체가 죽었다**;
        # 사용자 지시가 *"루프 안 끊어지게"* 이므로 **막힘을 결과로 바꿔 계속한다**.
        # 숨기지 않는다 --- `⏳` 로 찍어 사이클 할 일에 올라가게 한다.
        r = subprocess.run([sys.executable, "-m", "ingest.postprocess"],
                           capture_output=True, text=True)
        if r.returncode:
            tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-3:]
            print(f"[2] ⏳ 후처리 보류({len(moved)}건) — 무료 경로 없음(노트 889). "
                  f"에이전트 모드 신설이 필요하다: " + " / ".join(t[:120] for t in tail))
        else:
            print("[2] 후처리 완료")
    print(f"[2] 뱅크 투입: {len(moved)}건 (+후처리)")
    return moved


def step3_seal_upcoming() -> int:
    """챔피언(A' 무상태) + 챌린저(B'' 잠재 상태) 병렬 봉인 — 실측이 승자를 가린다.

    🔴 **예측기가 `llm` → `agent` 로 바뀌었다**(2026-08-09 · 노트 888).
    옛 코드는 `--predictor llm --auto --ensemble 3` 이었고 그것은 레코드당 종량제
    API 를 **3회** 부른다 --- 2026-07-27 에 하루 $297 을 낸 바로 그 경로다.
    2026-08-09 현재 크레딧이 없어 step2 가 400 으로 죽었으므로 이 경로는 **작동
    자체를 안 한다**.

    `--auto` 를 뗀 것은 실수가 아니다 --- 에이전트 경로는 구조상 2패스라 사람/
    에이전트가 예측을 쓰는 단계가 이미 있고, `--auto` 는 `LLMPredictor` 의
    검토 건너뛰기 플래그다.

    **바뀐 것을 숨기지 않는다.** 예측기 ID 가 `llm:claude-opus-4-8@prompt-…` 에서
    `agent:session-agent@prompt-…` 로 간다. 프롬프트 해시와 `+median3` 꼬리표는
    **글자 그대로 같게** 맞췄지만(검증 완료) **모델이 다르므로 두 경로의 성적을
    합산하면 안 된다**(`predictor_agent` 무결성 조항). 이미 봉인된 커밋 2건은
    `llm:` 이므로 이후 봉인과 **따로 집계**한다.

    이 경로에 median-of-3 이 없어서 옮기면 챔피언 정의가 조용히 K=1 로 바뀌는
    문제가 있었다 --- `AgentPredictor(ensemble=)` 를 새로 붙여 막았다.
    """
    sys.path.insert(0, ".")
    from harness.records import load_records
    CHAL = Path("cycle_log/forward_challenger")
    FWD.mkdir(parents=True, exist_ok=True)
    CHAL.mkdir(parents=True, exist_ok=True)
    today = date.today()
    upcoming = [r for r in load_records("data/records") if r.start > today]
    sealed = 0
    todo_champ = [r for r in upcoming if not (FWD / f"{r.record_id}.commit.json").exists()]
    todo_chal = [r for r in upcoming if not (CHAL / f"{r.record_id}.commit.json").exists()]
    if todo_chal:
        from harness.latent_state import build_state
        state = build_state([r.record_id for r in todo_chal])
        Path("cycle_log/forward_state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1))
        # 잠재 상태가 실제로 있는 타깃만 챌린저 봉인 (팝가 페이지 미개설이면 스킵 —
        # 상태 없는 챌린저는 챔피언의 중복 샘플일 뿐)
        todo_chal = [r for r in todo_chal if state.get(r.record_id, {}).get("latent_neighbors")]
    # median-of-3 (2026-07-24 run variance 실측 후 챔피언 재정의). 챌린저에도 동일 적용 —
    # 한쪽만 앙상블이면 상태 유무 비교가 앙상블 효과와 교락된다.
    for r in todo_champ:
        print(f"[3] 챔피언 봉인(median-of-3): {r.record_id} (오픈 {r.start})")
        subprocess.run([sys.executable, "-m", "harness.backtest", "--records", "data/records",
                        "--cycle-dir", str(FWD), "--holdout", r.record_id,
                        "--forward", "--predictor", "agent", "--ensemble", "3"], check=True)
        sealed += 1
    for r in todo_chal:
        print(f"[3] 챌린저 봉인(잠재, median-of-3): {r.record_id}")
        subprocess.run([sys.executable, "-m", "harness.backtest", "--records", "data/records",
                        "--cycle-dir", str(CHAL), "--holdout", r.record_id,
                        "--forward", "--predictor", "agent", "--ensemble", "3",
                        "--state-file", "cycle_log/forward_state.json"], check=True)
    print(f"[3] 신규 봉인: 챔피언 {sealed} / 챌린저 {len(todo_chal)}")
    return sealed


def step4_score_arrived() -> int:
    """실측 도착분 채점 — 챔피언(v2 봉인)뿐 아니라 챌린저·v3스택 사전등록 커밋도 같이 채점
    (2026-07-27: KIOF/TWS에 v2 단발 봉인과 v3 스택 median-of-3 봉인이 병행 사전등록됨 — 실전 대조)."""
    sys.path.insert(0, ".")
    from harness.records import load_records
    by_id = {r.record_id: r for r in load_records("data/records")}
    scored = 0
    dirs = [FWD, Path("cycle_log/forward_challenger"), Path("cycle_log/forward_v3stack")]
    for d in dirs:
        for cf in sorted(d.glob("*.commit.json")):
            rid = cf.stem.replace(".commit", "")
            if (d / f"{rid}.report.md").exists():
                continue
            rec = by_id.get(rid)
            if not rec:
                continue
            o = rec.data["outcome"]
            has_vis = bool(o["totals"].get("visitors"))
            has_rev = (o.get("rev_mm_completion", {}).get("status") == "complete")
            if has_vis or has_rev:
                print(f"[4] 실측 도착 → 채점: {rid} ({d.name})")
                subprocess.run([sys.executable, "-m", "harness.backtest", "--records", "data/records",
                                "--cycle-dir", str(d), "--holdout", rid,
                                "--predictor", "llm", "--auto"], check=True)
                scored += 1
    print(f"[4] 신규 채점: {scored}건")
    return scored


def main() -> int:
    print(f"===== 전향 패스 {date.today()} =====")
    step1_refresh_pnl()
    step2_discover_and_normalize()
    step3_seal_upcoming()
    step4_score_arrived()
    commits = len(list(FWD.glob("*.commit.json")))
    reports = len(list(FWD.glob("*.report.md")))
    print(f"===== 전향 현황: 봉인 {commits} / 채점 완료 {reports} / 대기 {commits - reports} =====")
    return 0


if __name__ == "__main__":
    sys.exit(main())
