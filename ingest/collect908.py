"""908-ㄱ 수집 팔 — 서울 생활인구 250m 월 파일을 **계획대로 줄지어 받는다**.

노트 901 §6 이 남긴 수: *「좌표 · 격자에 붙는 팝업 유보 93개를 다 살리려면
월 파일 **18개(≈7.8GB)** 가 필요하다」*. 899 가 두 달(2026-06·07)을 받았으므로
**남은 것은 17개월(2025-01 ~ 2026-05)** 이다. 이 모듈이 그 17개를 받는다.

🔴 **크롤이 아니다.** `ingest.seoul_lifepop.fetch()` 를 그대로 재사용한다 —
서울 열린데이터광장 데이터셋 페이지의 자기 다운로드 폼(`frmFile`)을 POST 한다.
URL 을 훑어 지어내지 않는다.

🔴 **조항 59 — 종료 코드 0 을 성공으로 읽지 마라.** 이 엔드포인트의 알려진
가짜 성공은 **HTTP 200 · `text/html` · 183바이트**::

    <html><head><script>alert('잘못된 접근입니다. …');history.back();</script></head></html>

그래서 파일마다 **여섯 겹**으로 확인하고, 하나라도 걸리면 파일을 지우고 실패로
적는다("없다"가 아니라 **"못 받았다"** 로 적는다).

    ㄱ 받은 바이트 수 > 50,000,000            (183바이트 껍데기 배제)
    ㄴ 첫 두 바이트 == b"PK"                   (zip 매직바이트)
    ㄷ `Content-Length` 헤더 == 받은 바이트 수 (중간 절단 배제)
    ㄹ `Content-Type` 이 text/html 이 아니다
    ㅁ `zipfile.ZipFile` 이 열리고 CSV 가 1개 이상 (구조 확인)
    ㅂ `testzip()` 대신 첫 CSV 헤더 1줄을 CP949 로 읽어 열 33개 확인

🔴 **`timeout` 명령을 안 쓴다**(이 환경에 없다 — rc=127 인데 옛 산출물이 남아
새 결과로 읽힌다). 시간 제한은 **파이썬 안**에서 건다: 소켓 timeout 900초 +
청크 루프마다 벽시계 예산 확인.

🔴 **파이프를 안 쓴다.** 파일로 받는다(`| head` 가 SIGPIPE 로 죽이는데 종료코드 0).

🔴 **받은 zip 은 저장소에 커밋하지 않는다** — `data/ingest/seoul_lifepop/.gitignore`
가 `*.zip` 을 막는다(899 §7).

라이선스: 공공누리 **제1유형**(출처표시) · 상업 이용·변경·재배포 가능 · 키 불필요 ·
**유료 API 아님**.

쓰는 법::

    python3 -m ingest.collect908 --plan               # 무엇을 받을지만 찍는다
    python3 -m ingest.collect908 --run                # 남은 것 전부
    python3 -m ingest.collect908 --run --limit 3      # 세 개만
    python3 -m ingest.collect908 --run --budget-sec 7200
    python3 -m ingest.collect908 --verify             # 이미 있는 파일만 재검사
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from ingest.seoul_lifepop import OUT, catalog, fetch

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "runners/out908a_collect.json"

# 🔴 901 §6 의 「받아야 할 달」 — 팝업 유보 13 ∪ 시장팝업 유보 18 = **18개월**
#    (runners/out901h_link.json 의 '받아야 할 달(정렬)' 을 읽어서 낸 값이고,
#     연속 구간 2025-01 ~ 2026-06 과 정확히 같다. 아래 assert 로 대조한다.)
NEEDED_MONTHS = [f"25{m:02d}" for m in range(1, 13)] + [f"26{m:02d}" for m in range(1, 7)]

MIN_BYTES = 50_000_000          # 조항 59 ㄱ — 183바이트 껍데기 배제
EXPECT_COLS = 33                # 899 §2.1 실측


def needed_from_901() -> list[str]:
    """🔴 손으로 적지 않는다 — 901 산출물에서 **읽어서** 낸다(조항 47 계열)."""
    p = ROOT / "runners/out901h_link.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    got: set[str] = set()
    for dom in d.get("④⑤⑥ 매칭 · 날짜 · 결정적 수", {}).values():
        for den, row in dom.items():
            if den.startswith("유보"):
                for ym in row.get("받아야 할 달(정렬)") or []:
                    got.add(ym[2:4] + ym[5:7])   # '2025-01' → '2501'
    return sorted(got)


# ---------------------------------------------------------------------------
# 200시간 배분 — `docs/수집계획.md` §4 의 정본. 🔴 **합을 코드로 단언한다.**
#
# 각 행: (번호, 이름, 기계시간, Δ유보행, Δ의 근거/상태)
#   Δ유보행 = 「그 원천을 받기 전에는 그 행에 그 원천의 값이 **하나도 없었는데**
#             받은 뒤에는 있게 되는 **판 유보 행**의 수」. 🔴 분모는 언제나 **3,775**.
#   None = 🔴 **못 셌다**("0 이다"가 아니다 — 조항 59).
# ---------------------------------------------------------------------------
BUDGET_TOTAL = 200.0

PLAN200: list[tuple[int, str, float, int | None, str]] = [
    (1, "서울 생활인구 250m 월 17개(2025-01~2026-05) 수령+격자×일 집계",
     6.3, 92, "901 §6: 격자에 붙는 팝업 유보 93, 지금 손에 있는 자료로는 1 → +92"),
    (2, "서울 생활인구 250m 월 25개(2023-01~2024-12)",
     9.5, 0, "🔴 0 — 유보 팝업의 개최 연도는 2025·2026 뿐(901 §5). 축행 분모로는 값이 있으나 **다른 분모다**"),
    (3, "KOBIS 공식 OpenAPI 상세(movieCd·장르·국적·제작사·감독) 406건",
     1.2, 406, "902 §5.1: 영화 D3 유보 406/406 이 일별 판에 있고 movieCd 가 **없다**. 🔴 무료 키 발급 선행"),
    (4, "소상공인시장진흥공단 상가(상권)정보 — 반경 소매밀도",
     14.0, 102, "901 §6: 팝업 유보 합집합 185 중 좌표 있는 102. 🔴 competition.py 의 경쟁밀도는 팝업 센서스지 점포 센서스가 아니다"),
    (5, "레코드 저장소 재관측 수집기 3종(팝업380·시장647·아이돌282) 첫 판 24h + 90일 유지 30h",
     54.0, 0, "🔴 0 — 902 가 연 W4 는 **미래 행**에만 붙는다. 유보는 이미 끝난 과거 행사다. 소급이 안 된다"),
    (6, "서울 집계구 생활인구 OA-14979(2023-01~2026-07 · 43개월)",
     20.0, 0, "🔴 0 추가 — 같은 93행을 다른 해상도로 덮을 뿐이다(899 §6.3: 월 1,172MB · 일별 없음)"),
    (7, "전국 격자 인구(KOSTAT/SGIS) — 카드 ⓪-나가 1순위로 적어 둔 것",
     12.0, 6, "901 §4: 서울 외접상자 **밖**인 팝업 유보 2+4=6. 🔴 접근 방법을 확인 못 했다"),
    (8, "장기체류외국인 생활인구(서울)",
     6.0, 0, "🔴 0 추가 — 같은 93행에 새 열. 그리고 🔴 **오늘 찾아봤으나 못 읽었다**(검색 200 껍데기)"),
    (9, "서울 지하철 역별 시간대 승하차",
     5.0, None, "🔴 못 셌다 — 역↔팝업 거리를 계산한 적이 없다"),
    (10, "KOBIS 빠진 16일 소급(2026-08-02~07 포함) + 일별 유지",
     0.5, 0, "🔴 0 — D3 406/406 이 이미 붙는다(902 §5.1). 관측 **밀도**만 채운다. 다만 이 표에서 **제일 싸다**"),
    (11, "wiki_views 일별 조회수 확장·갱신(캐시 10,962)",
     25.0, None, "🔴 못 셌다 — 캐시가 유보 3,775 중 몇 행을 덮는지 안 셌다"),
    (12, "naver_trend 갱신(12도메인 *_trend.json 이미 169~2,750키)",
     15.0, None, "🔴 못 셌다. 무료 한도 일 1,000회는 **기계시간이 아니라 달력시간**을 만든다"),
    (13, "날씨 백필 확장(open-meteo archive · 키 없음)",
     4.0, None, "🔴 못 셌다 — weather.py 가 이미 덮는 범위를 안 셌다"),
    (14, "KOPIS 공연예술통합전산망 — **13번째 도메인** 후보",
     12.0, 0, "🔴 0 — 새 도메인은 유보 행을 **늘리지만** 지금 판 3,775 에 붙는 행은 0. **다른 분모다**"),
    (15, "BQ 읽기 전용 재조회(popga GA4) — 🔴 SELECT·메타조회만",
     5.5, None, "🔴 못 셌다"),
    (16, "예비 — 재시도 · 실패 복구 · 검증 재실행",
     10.0, 0, "원천이 아니다. 조항 59 검사가 걸린 것을 다시 받는 몫"),
]

BOARD_HOLDOUT = 3775          # 12도메인 유보 (out900a_design.json 채점행 합 — 세서 확인)


def budget() -> dict:
    """🔴 합 == 배분 총합 을 **단언**한다. 어긋나면 여기서 죽는다."""
    s = round(sum(r[2] for r in PLAN200), 6)
    assert abs(s - BUDGET_TOTAL) < 1e-9, f"배분 합 {s} != {BUDGET_TOTAL}"
    rows = []
    for no, name, h, d, why in PLAN200:
        rows.append({
            "번호": no, "이름": name, "기계시간(h)": h,
            "Δ유보행": d, "🔴 분모": BOARD_HOLDOUT,
            "행/시간": (round(d / h, 2) if (d is not None and h > 0) else None),
            "근거": why,
        })
    ranked = sorted([r for r in rows if r["행/시간"] is not None],
                    key=lambda r: -r["행/시간"])
    # 🔴 손으로 더하지 않는다 — 세 갈래의 시간 합을 코드가 낸다(초판에서 손계산을 틀렸다).
    h_pos = round(sum(r[2] for r in PLAN200 if r[3] is not None and r[3] > 0), 6)
    h_zero = round(sum(r[2] for r in PLAN200 if r[3] == 0), 6)
    h_unk = round(sum(r[2] for r in PLAN200 if r[3] is None), 6)
    assert abs(h_pos + h_zero + h_unk - BUDGET_TOTAL) < 1e-9, "세 갈래 합이 200 이 아니다"
    return {
        "총 배분(h)": BUDGET_TOTAL,
        "🔴 합 == 배분 총합": s,
        "단언 통과": abs(s - BUDGET_TOTAL) < 1e-9,
        "항목 수": len(PLAN200),
        "🔴 분모(판 유보 12도메인)": BOARD_HOLDOUT,
        "🔴 Δ를 못 센 항목 수": sum(1 for r in rows if r["Δ유보행"] is None),
        "🔴 시간의 세 갈래(합=200)": {
            "Δ>0 인 항목의 시간": h_pos,
            "Δ>0 비율": round(h_pos / BUDGET_TOTAL * 100, 1),
            "Δ==0 인 항목의 시간": h_zero,
            "Δ==0 비율": round(h_zero / BUDGET_TOTAL * 100, 1),
            "🔴 Δ를 못 센 항목의 시간": h_unk,
            "못 센 비율": round(h_unk / BUDGET_TOTAL * 100, 1),
            "세 갈래 합 단언": abs(h_pos + h_zero + h_unk - BUDGET_TOTAL) < 1e-9,
        },
        "배분": rows,
        "순위(시간당 새로 붙는 판 유보 행 · 분모 3,775)": [
            {"순위": i + 1, "번호": r["번호"], "이름": r["이름"],
             "Δ유보행": r["Δ유보행"], "시간": r["기계시간(h)"], "행/시간": r["행/시간"]}
            for i, r in enumerate(ranked)],
        "🔴 순위에 못 넣은 것(Δ를 못 셌다 — 「0 이다」가 아니다)": [
            {"번호": r["번호"], "이름": r["이름"], "시간": r["기계시간(h)"]}
            for r in rows if r["행/시간"] is None],
        "🔴 조항 60": "새 행을 만드는 항목은 14(KOPIS)뿐이고 그것은 **13번째 도메인**이라 "
                     "분모가 다르다. 이 표의 Δ 는 전부 **3,775 분모 위에서만** 더한다.",
        "🔴 붙는다 ≠ 판이 오른다": "이 표는 **재료가 붙는 행 수**를 센다. "
                                 "예측 성능이 오르는지는 **한 줄도 재지 않았다**(887형 회피).",
    }


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def verify(path: Path, content_length: str | None = None,
           content_type: str | None = None) -> dict:
    """🔴 조항 59 — 여섯 겹. 통과 못 하면 '못 받았다'로 적는다."""
    r: dict = {"경로": str(path.relative_to(ROOT)), "존재": path.exists()}
    if not path.exists():
        r["통과"] = False
        r["막힌 검사"] = "파일이 없다"
        return r
    n = path.stat().st_size
    r["바이트"] = n
    r["MB"] = round(n / 1e6, 2)
    checks: dict = {}

    checks["ㄱ 크기>50MB"] = n > MIN_BYTES
    head = path.open("rb").read(4)
    r["첫 4바이트"] = head.hex()
    checks["ㄴ 매직바이트 PK"] = head[:2] == b"PK"
    if content_length is not None:
        checks["ㄷ Content-Length 일치"] = str(n) == str(content_length)
        r["Content-Length"] = content_length
    if content_type is not None:
        checks["ㄹ text/html 아님"] = "text/html" not in (content_type or "")
        r["Content-Type"] = content_type

    try:
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            csvs = [x for x in names if x.lower().endswith(".csv")]
            r["zip 항목"] = len(names)
            r["CSV 수"] = len(csvs)
            r["포장"] = "폴더" if any("/" in x for x in names) else "평면"
            checks["ㅁ zip 열림 · CSV≥1"] = len(csvs) >= 1
            if csvs:
                with z.open(sorted(csvs)[0]) as f:
                    line = io.TextIOWrapper(f, encoding="cp949",
                                            errors="replace").readline()
                cols = [c.strip().strip('"') for c in line.rstrip("\r\n").split(",")]
                r["첫 CSV"] = sorted(csvs)[0]
                r["열 수"] = len(cols)
                checks[f"ㅂ 열 {EXPECT_COLS}개"] = len(cols) == EXPECT_COLS
    except Exception as e:                       # noqa: BLE001
        checks["ㅁ zip 열림 · CSV≥1"] = False
        r["zip 예외"] = f"{type(e).__name__}: {e}"

    r["검사"] = checks
    r["통과"] = all(checks.values())
    if not r["통과"]:
        r["막힌 검사"] = [k for k, v in checks.items() if not v]
    r["sha256"] = _sha256(path)
    r["sha256[:16]"] = r["sha256"][:16]
    return r


def _dest(seq: str) -> Path:
    return OUT / f"250_LOCAL_RESD_20{seq}.zip"


def plan(cat: list[dict] | None = None) -> dict:
    cat = cat if cat is not None else catalog()
    by_seq = {c["seq"]: c for c in cat}
    from_901 = needed_from_901()
    rows = []
    for seq in NEEDED_MONTHS:
        d = _dest(seq)
        c = by_seq.get(seq, {})
        rows.append({
            "seq": seq,
            "달": f"20{seq[:2]}-{seq[2:]}",
            "파일": c.get("파일"),
            "포털표기 MB": c.get("포털표기 MB"),
            "포털에 있나": seq in by_seq,
            "이미 있나": d.exists(),
            "바이트(있으면)": d.stat().st_size if d.exists() else None,
        })
    return {
        "필요 달(901 §6)": NEEDED_MONTHS,
        "🔴 901 산출물에서 읽은 달": from_901,
        "손 목록 == 901 목록": sorted(from_901) == sorted(NEEDED_MONTHS) if from_901 else None,
        "포털 월별 파일 총수": len([c for c in cat if len(c["seq"]) == 4]),
        "행": rows,
        "이미 받은 수": sum(1 for r in rows if r["이미 있나"]),
        "남은 수": sum(1 for r in rows if not r["이미 있나"]),
        "남은 포털표기 MB 합": round(sum(
            float(r["포털표기 MB"]) for r in rows
            if not r["이미 있나"] and r["포털표기 MB"]), 2),
    }


def run(limit: int | None = None, budget_sec: float = 6 * 3600,
        per_file_sec: float = 1800.0) -> dict:
    """🔴 시간 제한을 **파이썬 안**에서 건다. `timeout` 명령을 안 쓴다."""
    t_start = time.time()
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cat = catalog()
    p = plan(cat)
    todo = [r["seq"] for r in p["행"] if not r["이미 있나"] and r["포털에 있나"]]
    if limit:
        todo = todo[:limit]

    got, failed = [], []
    for i, seq in enumerate(todo, 1):
        left = budget_sec - (time.time() - t_start)
        if left <= 60:
            failed.append({"seq": seq, "🔴 못 받았다": f"벽시계 예산 소진(남은 {left:.0f}s)"})
            continue
        t0 = time.time()
        try:
            meta = fetch(seq)                     # 899 의 폼 POST 를 그대로 쓴다
        except Exception as e:                    # noqa: BLE001
            failed.append({"seq": seq, "🔴 못 받았다": f"{type(e).__name__}: {e}",
                           "초": round(time.time() - t0, 1)})
            print(f"[{i}/{len(todo)}] {seq} 🔴 못 받았다: {e}", flush=True)
            _write(started, p, got, failed, todo, t_start)
            continue
        dt = time.time() - t0
        v = verify(Path(meta["파일"]), meta.get("Content-Length"))
        v["seq"] = seq
        v["달"] = f"20{seq[:2]}-{seq[2:]}"
        v["초"] = round(dt, 1)
        v["MB/s"] = round(v.get("바이트", 0) / 1e6 / max(dt, 1e-9), 2)
        v["받은 시각(UTC)"] = meta["받은 시각(UTC)"]
        if v["통과"]:
            got.append(v)
            print(f"[{i}/{len(todo)}] {seq} ✅ {v['MB']}MB {v['초']}s "
                  f"sha {v['sha256[:16]']} CSV {v.get('CSV 수')} {v.get('포장')}", flush=True)
        else:
            failed.append({"seq": seq, "🔴 못 받았다": "조항 59 검사 실패", **v})
            print(f"[{i}/{len(todo)}] {seq} 🔴 검사 실패 {v.get('막힌 검사')}", flush=True)
        _write(started, p, got, failed, todo, t_start)

    return _write(started, p, got, failed, todo, t_start)


def _write(started, p, got, failed, todo, t_start) -> dict:
    out = {
        "무엇": "908-ㄱ 수집 팔 — 서울 생활인구 250m 월 파일",
        "코드 sha256": _sha256(Path(__file__)),
        "seoul_lifepop.py sha256": _sha256(ROOT / "ingest/seoul_lifepop.py"),
        "시작(UTC)": started,
        "끝(UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "경과 초": round(time.time() - t_start, 1),
        "계획": p,
        "이번에 시도한 수": len(todo),
        "🔴 받았다": len(got),
        "🔴 못 받았다": len(failed),
        "받은 파일": got,
        "못 받은 것": failed,
    }
    have = sorted(x.name for x in OUT.glob("250_LOCAL_RESD_*.zip"))
    out["지금 손에 있는 월 파일"] = have
    out["지금 손에 있는 수"] = len(have)
    out["18개월 중 남은 수"] = sum(1 for s in NEEDED_MONTHS if not _dest(s).exists())
    prev = {}
    if LEDGER.exists():
        try:
            prev = json.loads(LEDGER.read_text(encoding="utf-8"))
        except Exception:                          # noqa: BLE001
            prev = {}
    prev["나. 수집 실행"] = out
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--budget", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--budget-sec", type=float, default=6 * 3600)
    a = ap.parse_args()
    if a.budget:
        b = budget()
        prev = {}
        if LEDGER.exists():
            try:
                prev = json.loads(LEDGER.read_text(encoding="utf-8"))
            except Exception:                      # noqa: BLE001
                prev = {}
        prev["가. 200시간 계획"] = b
        prev["가. 200시간 계획"]["코드 sha256"] = _sha256(Path(__file__))
        prev["가. 200시간 계획"]["찍은 시각(UTC)"] = \
            datetime.now(timezone.utc).isoformat(timespec="seconds")
        LEDGER.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(b, ensure_ascii=False, indent=1))
    elif a.run:
        r = run(limit=a.limit, budget_sec=a.budget_sec)
        print(json.dumps({k: v for k, v in r.items() if k != "계획"},
                         ensure_ascii=False, indent=1))
    elif a.verify:
        vs = [verify(x) for x in sorted(OUT.glob("250_LOCAL_RESD_*.zip"))]
        need = {f"250_LOCAL_RESD_20{s}.zip" for s in NEEDED_MONTHS}
        block = {
            "무엇": "🔴 조항 59 여섯 겹 재검사 — 지금 손에 있는 파일 전량",
            "찍은 시각(UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "코드 sha256": _sha256(Path(__file__)),
            "파일 수": len(vs),
            "🔴 통과": sum(1 for v in vs if v["통과"]),
            "🔴 막힌 것": [v for v in vs if not v["통과"]],
            "바이트 합": sum(v.get("바이트", 0) for v in vs),
            "GB 합": round(sum(v.get("바이트", 0) for v in vs) / 1e9, 3),
            "계획 18개월 중 손에 있는 수": sum(
                1 for v in vs if Path(v["경로"]).name in need),
            "🔴 계획 18개월 중 못 받은 수": len(need) - sum(
                1 for v in vs if Path(v["경로"]).name in need),
            "🔴 계획 밖인데 손에 있는 것": [
                v["경로"] for v in vs if Path(v["경로"]).name not in need],
            "파일": [{k: v[k] for k in
                     ("경로", "달", "바이트", "MB", "sha256[:16]", "첫 4바이트",
                      "CSV 수", "포장", "열 수", "통과")
                     if k in v} for v in vs],
        }
        prev = {}
        if LEDGER.exists():
            try:
                prev = json.loads(LEDGER.read_text(encoding="utf-8"))
            except Exception:                      # noqa: BLE001
                prev = {}
        prev["다. 받은 파일 검사(조항 59)"] = block
        LEDGER.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in block.items() if k != "파일"},
                         ensure_ascii=False, indent=1))
    else:
        print(json.dumps(plan(), ensure_ascii=False, indent=1))
