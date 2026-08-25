# -*- coding: utf-8 -*-
"""사이클 1028 — 사건 원장 G1′ 정제: v0 30,001 → v1 (티처 #146 사각 4유형 규칙 상향 + 정독 라벨 실율).

사전등록 docs/탐색/1028.md — 이 러너는 사전등록 커밋에서 언다(조항 66 — 주행 중 수정 금지).
단계:
  --stage selftest  방향 탐침 + MDE 시작 관문(부칙 6 ㉰ · 등록문 파싱) + 규칙 합성례 + 병합 탐침
  --stage fetch     소비 문서 원문 zone 캐시(표적 읽기 · 파트 체크포인트 · load1 관문 · 장주행)
  --stage rules     사다리 항등 검사 → v0 병합 30,001 항등 → 규칙 R1~R5 전량 적용 → rows_ruled
  --stage build     생존행 병합 k=3(정본 · EV1-) + k∈{1,7} 민감도 + 시대 분포 + merged_view_v1
  --stage sample    G1′ 층화 표본(씨앗 1028 · 층당 min(120,N)) + 제거 관찰 표본 60
  --stage report    라벨 완결 검사 → 일치율·층별/합성 거짓률·게이트·MDE 실측 → meta1028.json

위생: CPU ≤5스레드(pyarrow 4·OMP 4) · 무거운 파트 전 load1>10 → 60초 재잼 · MPS 0 ·
      전 입력 읽기 전용(v0 산출물 무수정 — v1 은 새 디렉터리) · 산출물은 wm_harvest(조항 73-마) ·
      콘텐츠 위생(실명·스니펫은 산출 파일 안만).
"""
import argparse
import collections
import datetime as dt
import glob
import gzip
import hashlib
import json
import math
import os
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("WM_ROOT", "/Users/ax/world_model"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("OMP_NUM_THREADS", "4")
from runners import event_ledger1026 as e26   # noqa: E402  읽기 전용 — 유일화·배정·병합·재추출 항등 재사용
from runners import pubdate1021 as p21        # noqa: E402  읽기 전용 — 정규식·상수
from pretrain.mde_guard import assert_mde, mde_of   # noqa: E402  부칙 6 관문
import pyarrow as pa                          # noqa: E402
import pyarrow.compute as pc                  # noqa: E402
import pyarrow.parquet as pq                  # noqa: E402
pa.set_cpu_count(4)

FND = Path("/Users/ax/wm_harvest/foundation")
V0 = FND / "event_ledger"
OUT = V0 / "v1"
OUT.mkdir(parents=True, exist_ok=True)
DOC = ROOT / "docs/탐색/1028.md"
ZONES = OUT / "zones1028.jsonl.gz"
RULED = OUT / "rows_ruled.jsonl.gz"
EVENTS1 = OUT / "events_v1.jsonl.gz"
MERGED1 = OUT / "merged_view_v1.jsonl.gz"
SAMPLE = OUT / "g1p_sample.jsonl.gz"
RM_SAMPLE = OUT / "g1p_removed_sample.jsonl.gz"
L1 = OUT / "g1p_labels_pass1.jsonl"
L2 = OUT / "g1p_labels_pass2.jsonl"
L3 = OUT / "g1p_labels_adjud.jsonl"
LRM = OUT / "g1p_removed_labels.jsonl"
META = OUT / "meta1028.json"
STATE = OUT / "state1028.json"
PROG = OUT / "progress1028.jsonl"
ATTIDX = V0 / "attach_index1026.json.gz"        # 읽기 전용 재사용(등록 §0 지평 ③)
META26 = V0 / "meta1026.json"                   # 항등 대조용(읽기 전용)
LEDGER = FND / "ledger_interventions/ledger.jsonl"
FW_DIR = Path("/Users/ax/wm_harvest/fineweb2_ko")
DISC_DIR = Path("/Users/ax/wm_harvest/discourse")

SEED = 1028
SEED_SHUF = 20281
THRESH = 0.15                    # G1′ 문턱(등록 §3 — 시작 관문이 등록문과 대조)
AIM = 0.30                       # 겨냥 |Δ| (#146 0.45 → 0.15)
NOYEAR_MAX_DIFF = 180            # R3d 인자(등록 §2 인자 표)
NOYEAR = {"연도무MD", "오는D일", "내달D일", "이달D일"}
SHA146 = "fcdc3a591dca1e7f"      # docs/티처/146.md — 겨냥 출처
SHA_M26 = "9be435f7d60dfb1e"     # meta1026.json — 눈금 분모 출처

# ── 규칙 정규식(등록 §2 표와 일자일자 대응) ─────────────────────────────
RE_R1A = re.compile(r"^\s*까지")
RE_R1B_EX = re.compile(r"^\s*부터")
RE_R2A = re.compile(r"^(했|됐|하였|되었|였|었|된(?!다)|한(?![다게]))")
RE_R2C = re.compile(r"당시|였던|었던|았던|지난해|작년|재작년")
RE_R3A_Y = re.compile(r"(?:19|20)\d{2}(?=\s*년)")
RE_R3B = re.compile(r"같은\s*해|이듬해|그\s*해|이맘때")
RE_R3C = re.compile(r"^\s*\d{1,2}\s*:\s*\d{2}")
RE_R4_N1 = re.compile(r"(?<![가-힣])(?:취소|무산|불발|중단)"
                      r"|(?<![가-힣])연기(?=되|하|했|됐|될|한다|키로)"
                      r"|(?<![가-힣])(?:무기한|잠정|전격)\s*연기")
RE_R4_N2 = re.compile(r"예정이었|계획이었|검토\s*중|논의\s*중|미정|불투명|수도\s*있|보류|백지화")
RE_R5A = re.compile(r"[.!?]")
RE_R5B = re.compile(r"마감|접수|신청|응모|투표|모집")
RULE_ORDER = ("R1a", "R1b", "R2a", "R2c", "R3a", "R3b", "R3c", "R3d", "R4n1", "R4n2", "R5a", "R5b")

# 1026 사다리 항등 기대값(meta1026 — 정찰로 재확인 · 어긋나면 측정 없이 중단)
EXPECT26 = {"행": 416770, "유일키": 395945, "근접배정행": 23431, "E3회수행": 20825,
            "전개배정": 45408, "유일사건": 30001,
            "tiers": {"E1": 8675, "E2모호": 4512, "E2미해소": 11396, "E3": 20825}}


def _log(**kw):
    kw["시각"] = dt.datetime.now().isoformat(timespec="seconds")
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def load1_gate():
    while True:
        l1 = os.getloadavg()[0]
        if l1 <= 10.0:
            return l1
        _log(단계="load1대기", load1=round(l1, 2))
        time.sleep(60)


def _sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()[:16]


def code_stamp():
    me = Path(__file__).resolve()
    return {"러너sha256": hashlib.sha256(me.read_bytes()).hexdigest(),
            "event_ledger1026_sha16": _sha16(ROOT / "runners/event_ledger1026.py"),
            "pubdate1021_sha16": _sha16(ROOT / "runners/pubdate1021.py")}


def st_load():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def st_save(st):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


# ── 소비 행 재구성(1026 항등 — 같은 함수 재사용) ─────────────────────────
def consumed_rows():
    """유일키 행 + 배정(asg) — 1026 build 의 배정 경로 항등. 반환:
    rows(dict key→row · row['_asg'] 소비 배정 리스트 · row['_tier경로'] near/E3) · 사다리."""
    kws = set(e26.keywords_list())
    vmap, wmap = e26.names_map()
    n_raw, rows, g2_viol = e26.load_unique_rows()
    att = json.loads(gzip.open(ATTIDX, "rt", encoding="utf-8").read())
    ladder = collections.Counter()
    ladder["행"] = n_raw
    ladder["유일키"] = len(rows)
    ladder["G2위반격리"] = g2_viol
    tiers = collections.Counter()
    out = {}
    for key in sorted(rows):
        r = rows[key]
        asg = e26.assign_entities(r["개체"], kws, vmap)
        if not asg:
            k3 = e26.attach_pick(att["idx"], e26.SRC1024[r["_src"]] + "|" + r["문서id"])
            if k3:
                asg = [(k3, k3, "E3", None)]
                ladder["E3회수행"] += 1
            else:
                ladder["무개체제외행"] += 1
                continue
        else:
            ladder["근접배정행"] += 1
        for a in asg:
            tiers[a[2]] += 1
        r["_asg"] = asg
        out[key] = r
    ladder["전개배정"] = sum(tiers.values())
    # 항등 검사(등록 §2 ①)
    fails = []
    for k, v in (("행", ladder["행"]), ("유일키", ladder["유일키"]),
                 ("근접배정행", ladder["근접배정행"]), ("E3회수행", ladder["E3회수행"]),
                 ("전개배정", ladder["전개배정"])):
        if EXPECT26[k] != v:
            fails.append("%s:%d≠%d" % (k, v, EXPECT26[k]))
    if dict(tiers) != EXPECT26["tiers"]:
        fails.append("tiers:%r" % dict(tiers))
    if g2_viol != 0:
        fails.append("G2위반:%d" % g2_viol)
    if fails:
        _log(단계="사다리항등", 판정="실패", 실패=fails)
        sys.exit(1)
    _log(단계="사다리항등", 판정="통과", **{k: int(v) for k, v in ladder.items()})
    return out, dict(ladder), wmap


def make_assigns(rows, only_alive=None):
    """1026 build 전개 형식 항등: (ax,key,tier,nm,norm,원유형,date,문서id,출처군,conf,pub)."""
    assigns = []
    for key in sorted(rows):
        r = rows[key]
        if only_alive is not None and key not in only_alive:
            continue
        norm = e26.TYPE_MAP.get(r["event_type"], "기타")
        for ax, k, tier, nm in r["_asg"]:
            assigns.append((ax, k, tier, nm, norm, r["event_type"],
                            dt.date.fromisoformat(r["event_time"]), r["문서id"],
                            r["_src"], r["conf"], r["pub_time"]))
    return assigns


def merge_events(assigns, k, prefix, wmap):
    """1026 build 병합 블록 항등(군집 k 인자화 · 사건id 접두 인자화)."""
    groups = collections.defaultdict(list)
    for a in assigns:
        groups[(a[0], a[4])].append(a)
    events = []
    tier_rank = {"E1": 0, "E3": 1, "E2모호": 2, "E2미해소": 3}
    for (ax, norm), items in sorted(groups.items()):
        clusters = e26.cluster_dates([a[6] for a in items], k=k)
        spans = [(c[0], c[-1]) for c in clusters]
        for lo, hi in spans:
            sub = [a for a in items if lo <= a[6] <= hi]
            support = collections.defaultdict(set)
            for a in sub:
                support[a[6]].add(a[7])
            rd = e26.rep_date(support)
            docs = {a[7] for a in sub}
            first_pub = min(a[10] for a in sub)
            srcsum = collections.Counter()
            for a in sub:
                srcsum[a[8]] = len({b[7] for b in sub if b[8] == a[8]})
            g1layers = sorted({a[8] + "|" + e26.TYPE_GROUP.get(norm, "기타") for a in sub})
            best = min(sub, key=lambda a: tier_rank[a[2]])
            key = best[1]
            eid = prefix + hashlib.sha1((ax + "|" + norm + "|" + rd.isoformat())
                                        .encode("utf-8")).hexdigest()[:12]
            events.append({
                "사건id": eid, "개체키": key,
                "개체원명": best[3], "위키문서": wmap.get(key) if key else None,
                "신뢰층": best[2], "정규유형": norm,
                "원유형": dict(collections.Counter(a[5] for a in sub)),
                "event_time": rd.isoformat(),
                "예고": "예고" if first_pub < rd.isoformat() else "보도형",
                "최초pub_time": first_pub, "문서수": len(docs), "행수": len(sub),
                "출처요약": dict(srcsum), "G1층": g1layers,
                "conf_max": max(a[9] for a in sub),
                "event_time_span": [lo.isoformat(), hi.isoformat()]})
    ids = [e["사건id"] for e in events]
    assert len(ids) == len(set(ids)), "사건id 충돌"
    return events


# ── 규칙 평가(등록 §2 — 유일키 행 단위) ─────────────────────────────────
def find_hit(zone, pub, et, ty):
    evs, _ = e26.reextract_spans(zone, pub)
    hit = next((x for x in evs if x[0] == et and x[1] == ty), None)
    if hit is None:
        return None
    _, _, s, e = hit
    vm = p21.RE_EV_VERB.search(zone[e:e + 40])
    assert vm is not None and vm.group(1) == ty, "동사 재유도 불일치"
    return s, e, e + vm.start(), e + vm.end()


def rule_flags(zone, s, e, vs, ve, kind=None, diff=None, et=None):
    flags = []
    if RE_R1A.match(zone[e:e + 4]):
        flags.append("R1a")
    if "까지" in zone[e:vs] and not RE_R1B_EX.match(zone[e:e + 4]):
        flags.append("R1b")
    if RE_R2A.match(zone[ve:ve + 4]):
        flags.append("R2a")
    if RE_R2C.search(zone[max(0, s - 30):s]):
        flags.append("R2c")
    if kind in NOYEAR:
        pre60 = zone[max(0, s - 60):s]
        ys = RE_R3A_Y.findall(pre60)
        if ys:
            last = None
            for m in RE_R3A_Y.finditer(pre60):
                last = m.group(0)
            if int(last) != int(et[:4]):
                flags.append("R3a")
        if RE_R3B.search(zone[max(0, s - 40):s]):
            flags.append("R3b")
        if diff > NOYEAR_MAX_DIFF:
            flags.append("R3d")
    if RE_R3C.match(zone[e:e + 8]):
        flags.append("R3c")
    snip = zone[max(0, s - 60):e + 60]
    if RE_R4_N1.search(snip):
        flags.append("R4n1")
    if RE_R4_N2.search(snip):
        flags.append("R4n2")
    between = zone[e:vs]
    if RE_R5A.search(between):
        flags.append("R5a")
    if RE_R5B.search(between):
        flags.append("R5b")
    return flags


# ── selftest ─────────────────────────────────────────────────────────────
def mde_start_gate():
    """부칙 6 ㉰ — 등록문 MDE 칸 파싱 + 출처 sha 실물 대조 + 층분모 표 재계산 대조."""
    doc = DOC.read_text(encoding="utf-8")
    for tag, path, want in (("146", ROOT / "docs/티처/146.md", SHA146),
                            ("meta1026", META26, SHA_M26)):
        real = _sha16(path)
        if real != want or want not in doc:
            raise SystemExit("MDE 출처 sha 불일치/부재 %s: 실물 %s 등록 %s" % (tag, real, want))
    rows = re.findall(r"^\|\s*(\S+·\S+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|", doc, re.M)
    if len(rows) != 15:
        raise SystemExit("등록문 층분모 표 15층 아님: %d" % len(rows))
    tot = sum(int(n) for _, n, _ in rows)
    se2 = 0.0
    for _, N, n in rows:
        N, n = int(N), int(n)
        se2 += (N / tot) ** 2 * THRESH * (1 - THRESH) / n * (1 - n / N)
    se = math.sqrt(se2)
    m_se = re.search(r"SE_사전 = ([\d.]+)", doc)
    m_mde = re.search(r"MDE = ([\d.]+) = 2×max", doc)
    m_aim = re.search(r"겨냥 \|Δ\| = ([\d.]+)", doc)
    m_thr = re.search(r"문턱: p̂ ≤ ([\d.]+)", doc)
    m_180 = re.search(r"NOYEAR_MAX_DIFF=(\d+)", doc)
    if not all((m_se, m_mde, m_aim, m_thr, m_180)):
        raise SystemExit("등록문 MDE/문턱 칸 부재")
    if abs(se - float(m_se.group(1))) > 5e-4:
        raise SystemExit("SE 재계산 불일치: %.5f vs %s" % (se, m_se.group(1)))
    if abs(mde_of(float(m_se.group(1)), 0.0) - float(m_mde.group(1))) > 5e-4:
        raise SystemExit("MDE 산식 불일치")
    if abs(float(m_thr.group(1)) - THRESH) > 1e-9 or int(m_180.group(1)) != NOYEAR_MAX_DIFF:
        raise SystemExit("문턱/인자 등록-코드 불일치")
    stamp = assert_mde(float(m_mde.group(1)), float(m_aim.group(1)), SHA146)
    _log(단계="MDE시작관문", 판정="통과", MDE=float(m_mde.group(1)), 겨냥=float(m_aim.group(1)))
    return stamp


def selftest():
    fails = []
    # 방향 탐침(v5.3-2): 합성 t>0 — 악화 극값 거짓 · 개선 극값 참
    t = 0.1
    if not ((0.0 + 2 * t > t) and (0.0 <= t)):
        fails.append("탐침:합성")
    if not (e26.g1_pass(2 * t, t) is False and e26.g1_pass(0.0, t) is True):
        fails.append("탐침:G1p")
    if not (e26.g2_pass(6, 3) is False and e26.g2_pass(0, 3) is True):
        fails.append("탐침:G2")
    if not (e26.g3_pass(6, 3) is False and e26.g3_pass(0, 3) is True):
        fails.append("탐침:G3")
    # 병합 탐침(1026 항등 함수 재사용 확인)
    D = dt.date
    if len(e26.cluster_dates([D(2026, 1, 1), D(2026, 1, 4)], k=3)) != 1:
        fails.append("병합:3일합류")
    if len(e26.cluster_dates([D(2026, 1, 1), D(2026, 1, 4)], k=1)) != 2:
        fails.append("병합:k1분리")
    if len(e26.cluster_dates([D(2026, 1, 1), D(2026, 1, 8)], k=7)) != 1:
        fails.append("병합:k7합류")
    # 규칙 합성례(등록 §2 ③) — pub 2026-08-01 · 유형 동사 뒤 문맥
    pub = D(2026, 8, 1)
    cases = [  # (문서, 기대 flags 부분집합, 비발화 규칙)
        ("행사가 2026년 9월 10일 개최된다", set(), {"R1a", "R2a", "R4n1"}),
        ("전시는 2026년 9월 10일까지 개최된다", {"R1a"}, set()),
        ("2026년 9월 10일 개최했다", {"R2a"}, set()),
        ("2026년 9월 10일 개최되었다", {"R2a"}, set()),
        ("공연은 2026년 9월 10일 개최한다", set(), {"R2a"}),
        ("2026년 9월 10일 13:24 공개 소식", {"R3c"}, set()),
        ("접수는 9월 10일 마감이며 이후 결과를 발표", {"R5b"}, set()),
        ("행사는 9월 10일. 새 작품은 곧 공개", {"R5a"}, set()),
        ("행사가 9월 10일에서 연기됐다는 소식과 함께 개최", {"R4n1"}, set()),
        ("천연기념물 지정 기념 행사 9월 10일 개최 예정", set(), {"R4n1"}),
        ("공연기획사가 9월 10일 공연을 개최", set(), {"R4n1"}),
        ("연기력 호평 배우가 9월 10일 팬미팅 개최", set(), {"R4n1"}),
        ("9월 10일부터 10월 3일까지 개최", set(), {"R1b"}),
    ]
    for text, want, ban in cases:
        evs, zone = e26.reextract_spans(text, pub)
        if not evs:
            fails.append("합성례:무매치:" + text[:12])
            continue
        d0, ty, s, e = evs[0]
        vm = p21.RE_EV_VERB.search(zone[e:e + 40])
        vs, ve = e + vm.start(), e + vm.end()
        diff = (D.fromisoformat(d0) - pub).days
        got = set(rule_flags(zone, s, e, vs, ve, "연도무MD" if "년" not in text[:14] else "절대_년월일",
                             diff, d0))
        if not want.issubset(got) or (ban & got):
            fails.append("합성례:%s→%r(기대⊇%r·금지∩%r)" % (text[:14], sorted(got), sorted(want), sorted(ban)))
    # R3a·R3d·R2c 는 직접 인자 검사(정규식 좌표)
    def spans_of(z, rx):
        m = rx.search(z)
        vm = p21.RE_EV_VERB.search(z[m.end():m.end() + 40])
        return m.start(), m.end(), m.end() + vm.start(), m.end() + vm.end()
    z3 = "2018년 출시된 제품 소식이다. 오는 10일 예약판매를 시작"
    if "R3a" not in rule_flags(z3, *spans_of(z3, p21.RE_ONEUN), kind="오는D일",
                               diff=40, et="2026-09-10"):
        fails.append("합성례:R3a")
    z3b = "2026년 관련 소식이다. 오는 10일 예약판매를 시작"
    if "R3a" in rule_flags(z3b, *spans_of(z3b, p21.RE_ONEUN), kind="오는D일",
                           diff=40, et="2026-09-10"):
        fails.append("합성례:R3a음성")
    z5 = "9월 10일 개봉"
    if "R3d" not in rule_flags(z5, *spans_of(z5, p21.RE_MD), kind="연도무MD",
                               diff=200, et="2027-09-10"):
        fails.append("합성례:R3d")
    if "R3d" in rule_flags(z5, *spans_of(z5, p21.RE_MD), kind="연도무MD",
                           diff=100, et="2026-09-10"):
        fails.append("합성례:R3d음성")
    z4 = "그 행사 당시인 9월 10일 개최 소식"
    if "R2c" not in rule_flags(z4, *spans_of(z4, p21.RE_MD), kind="연도무MD",
                               diff=40, et="2026-09-10"):
        fails.append("합성례:R2c")
    # R4 경계 직접 검사
    for txt, want_hit in (("천연기념물", False), ("공연기획사", False), ("연기력", False),
                          ("연기 대결", False), ("공연이 연기됐다", True), ("무기한 연기", True),
                          ("행사 취소", True), ("매매취소", False)):
        if bool(RE_R4_N1.search(txt)) is not want_hit:
            fails.append("R4경계:" + txt)
    # R2a 경계
    for txt, want_hit in (("했다", True), ("됐습니다", True), ("하였다", True), ("되었던", True),
                          ("된 바", True), ("한 행사", True), ("한다", False), ("된다", False),
                          ("하는", False), ("합니다", False)):
        if bool(RE_R2A.match(txt)) is not want_hit:
            fails.append("R2a경계:" + txt)
    stamp = None
    if not fails:
        stamp = mde_start_gate()
    ok = not fails
    _log(단계="selftest", 판정="통과" if ok else "실패", 실패=fails, 도장=code_stamp())
    if not ok:
        sys.exit(1)
    return stamp


# ── fetch — 소비 문서 zone 캐시 ──────────────────────────────────────────
def zones_loaded():
    have = {}
    if ZONES.exists():
        with gzip.open(ZONES, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                have[(r["src"], r["doc"])] = r["zone"]
    return have


def zones_append(batch):
    with open(ZONES, "ab") as raw:
        gz = gzip.GzipFile(fileobj=raw, mode="ab")
        for src, doc, zone in batch:
            gz.write((json.dumps({"src": src, "doc": doc, "zone": zone},
                                 ensure_ascii=False) + "\n").encode("utf-8"))
        gz.close()


def fetch():
    st = st_load()
    st.setdefault("fetch_done", [])
    rows, ladder, _ = consumed_rows()
    need = collections.defaultdict(set)
    for r in rows.values():
        need[r["_src"]].add(r["문서id"])
    have = zones_loaded()
    for k in need:
        need[k] = {d for d in need[k] if (k, d) not in have}
    _log(단계="fetch", 무엇="필요", **{k: len(v) for k, v in need.items()},
         기캐시=len(have))
    touched = st.setdefault("fetch_touched", [])
    # ⓐ discourse — 데몬 수확물 스캔(1026 항등 규약)
    if need["discourse1017"] and "discourse" not in st["fetch_done"]:
        load1_gate()
        batch = []
        got = set()
        for path in sorted(glob.glob(str(DISC_DIR / "*" / "*.jsonl.gz"))):
            try:
                for line in gzip.open(path, "rt", encoding="utf-8"):
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    did = hashlib.sha1((r.get("url") or r.get("제목") or "")
                                       .encode("utf-8")).hexdigest()[:16]
                    if did in need["discourse1017"] and did not in got:
                        text = ((r.get("제목") or "") + " " + (r.get("본문") or "")).strip()
                        batch.append(("discourse1017", did, text[:p21.EV_WIN]))
                        got.add(did)
            except Exception as ex:
                _log(단계="fetch", 경고="담론파일 스킵", 파일=path, err=str(ex))
        zones_append(batch)
        st["fetch_done"].append("discourse")
        st["fetch_miss_discourse"] = len(need["discourse1017"]) - len(got)
        st_save(st)
        _log(단계="fetch", 무엇="discourse", 회수=len(got), 미발견=st["fetch_miss_discourse"])
    # ⓑ 파케이 표적 읽기(1026 parquet_fetch 항등 — zone 저장판)
    def parquet_part(path, ids, src):
        pf = pq.ParquetFile(path)
        md = pf.metadata
        offs = [0]
        for i in range(md.num_row_groups):
            offs.append(offs[-1] + md.row_group(i).num_rows)
        idcol = pf.read(columns=["id"]).column("id")
        mask = pc.is_in(idcol, value_set=pa.array(sorted(ids)))
        hits = pc.indices_nonzero(mask).to_pylist()
        touched.append({"파일": str(path), "크기": os.path.getsize(path),
                        "mtime": int(os.path.getmtime(path)), "적중": len(hits)})
        import bisect
        rgs = sorted({bisect.bisect_right(offs, h) - 1 for h in hits})
        batch = []
        got = set()
        for rg in rgs:
            d = pf.read_row_group(rg, columns=["id", "text"]).to_pydict()
            for j, did in enumerate(d["id"]):
                if did in ids and did not in got:
                    batch.append((src, did, (d["text"][j] or "")[:p21.EV_WIN]))
                    got.add(did)
        zones_append(batch)
        return got
    if need["sao973"]:
        shards = sorted(glob.glob(str(p21.HPLT_DIR / "train-*-of-00464.parquet")))
        picked = [shards[i] for i in p21.SHARD_IDX if i < len(shards)]
        left = set(need["sao973"])
        for path in picked:
            tag = "sao/" + Path(path).name
            if tag in st["fetch_done"]:
                continue
            load1_gate()
            got = parquet_part(path, left, "sao973")
            left -= got
            st["fetch_done"].append(tag)
            st_save(st)
            _log(단계="fetch", 파트=tag, 회수=len(got), 남음=len(left))
        st["fetch_miss_sao"] = len(left)
    if need["fineweb2"]:
        left = set(need["fineweb2"])
        for path in sorted(glob.glob(str(FW_DIR / "*.parquet"))):
            tag = "fw/" + Path(path).name
            if tag in st["fetch_done"]:
                continue
            load1_gate()
            got = parquet_part(path, left, "fineweb2")
            left -= got
            st["fetch_done"].append(tag)
            st_save(st)
            _log(단계="fetch", 파트=tag, 회수=len(got), 남음=len(left))
        st["fetch_miss_fineweb"] = len(left)
    st["fetch_end"] = dt.datetime.now().isoformat(timespec="seconds")
    st_save(st)
    _log(단계="fetch", 무엇="완료", 미발견={"fw": st.get("fetch_miss_fineweb"),
         "sao": st.get("fetch_miss_sao"), "disc": st.get("fetch_miss_discourse")})


# ── rules ────────────────────────────────────────────────────────────────
def rules():
    st = st_load()
    rows, ladder, wmap = consumed_rows()
    # v0 병합 항등(등록 §2 ②)
    ev0 = merge_events(make_assigns(rows), 3, "EV0-", wmap)
    typ0 = collections.Counter(e["정규유형"] for e in ev0)
    m26 = json.loads(META26.read_text(encoding="utf-8"))
    if len(ev0) != EXPECT26["유일사건"] or dict(typ0) != m26["원장"]["유형분포_gross"]:
        _log(단계="v0항등", 판정="실패", 수=len(ev0))
        sys.exit(1)
    _log(단계="v0항등", 판정="통과", 유일사건=len(ev0))
    zones = zones_loaded()
    fire = collections.Counter()
    first = collections.Counter()
    reloc_fail = collections.Counter()
    alive = set()
    removed = []
    n_removed = 0
    with gzip.open(RULED, "wt", encoding="utf-8") as f:
        for key in sorted(rows):
            r = rows[key]
            src, doc, et, ty = r["_src"], r["문서id"], r["event_time"], r["event_type"]
            zone = zones.get((src, doc))
            rec = {"출처군": src, "문서id": doc, "event_time": et, "event_type": ty,
                   "날짜꼴": r["날짜꼴"], "diff일": r["diff일"]}
            if zone is None:
                rec["판정"] = "재정위실패(원문미발견)"
                reloc_fail[src] += 1
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue
            hit = find_hit(zone, dt.date.fromisoformat(r["pub_time"]), et, ty)
            if hit is None:
                rec["판정"] = "재정위실패(재추출불일치)"
                reloc_fail[src] += 1
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                continue
            s, e, vs, ve = hit
            flags = rule_flags(zone, s, e, vs, ve, r["날짜꼴"], r["diff일"], et)
            rec.update(스팬=[s, e, vs, ve], 발화=flags)
            for fl in flags:
                fire[fl] += 1
            if flags:
                first[min(flags, key=RULE_ORDER.index)] += 1
                n_removed += 1
                rec["판정"] = "제거"
                removed.append(key)
            else:
                rec["판정"] = "생존"
                alive.add(key)
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    strata_alive = collections.Counter()
    alive_assign = 0
    for key in alive:
        r = rows[key]
        grp = e26.TYPE_GROUP.get(e26.TYPE_MAP.get(r["event_type"], "기타"), "기타")
        strata_alive[r["_src"] + "|" + grp] += len(r["_asg"])
        alive_assign += len(r["_asg"])
    st["rules"] = {"소비유일키": len(rows), "재정위실패": dict(reloc_fail),
                   "재정위실패합": sum(reloc_fail.values()),
                   "규칙발화": dict(fire), "첫발화귀속": dict(first),
                   "유일제거": n_removed, "생존유일키": len(alive),
                   "생존배정행": alive_assign, "생존층분모": dict(strata_alive)}
    st["alive_keys_sha16"] = hashlib.sha256(
        "\n".join("|".join(k) for k in sorted(alive)).encode("utf-8")).hexdigest()[:16]
    st_save(st)
    _log(단계="rules", **{k: v for k, v in st["rules"].items() if not isinstance(v, dict)})
    return st


# ── build ────────────────────────────────────────────────────────────────
def load_ruled():
    out = {}
    with gzip.open(RULED, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            out[(r["출처군"], r["문서id"], r["event_time"], r["event_type"])] = r
    return out


def build():
    st = st_load()
    as_of = dt.date.today().isoformat()
    rows, ladder, wmap = consumed_rows()
    ruled = load_ruled()
    alive = {k for k in rows
             if ruled[(rows[k]["_src"], rows[k]["문서id"], rows[k]["event_time"],
                       rows[k]["event_type"])]["판정"] == "생존"}
    assigns = make_assigns(rows, only_alive=alive)
    assert len(assigns) == st["rules"]["생존배정행"], "생존 배정행 불일치"
    ev1 = merge_events(assigns, 3, "EV1-", wmap)
    for e in ev1:
        e["정제"] = "G1p-1028규칙"
    sens = {}
    for kk in (1, 3, 7):
        evk = ev1 if kk == 3 else merge_events(assigns, kk, "EVS-", wmap)
        sens[str(kk)] = {"유일사건": len(evk),
                         "축약비": round(len(assigns) / len(evk), 4) if evk else None}
    for kk in ("1", "7"):
        sens[kk]["Δ대비k3"] = round((sens[kk]["유일사건"] - sens["3"]["유일사건"])
                                   / sens["3"]["유일사건"], 4)
    with gzip.open(EVENTS1, "wt", encoding="utf-8") as f:
        for e in ev1:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # merged_view_v1(1026 §5 규격 항등 — 개입 원장 전건)
    ivt = {"전건": 0, "시간축미배치": 0, "위키병기": 0}
    with gzip.open(MERGED1, "wt", encoding="utf-8") as f:
        for e in ev1:
            e2 = dict(e)
            e2.update({"원장구분": "사건", "부유형": None,
                       "announced_at": None, "opened_at": None})
            f.write(json.dumps(e2, ensure_ascii=False) + "\n")
        for line in open(LEDGER, encoding="utf-8"):
            r = json.loads(line)
            ivt["전건"] += 1
            opened = r["A"]["when"].get("opened_at")
            if not opened:
                ivt["시간축미배치"] += 1
            w = wmap.get(r["record_id"])
            if w:
                ivt["위키병기"] += 1
            f.write(json.dumps({
                "사건id": "IVT-" + r["record_id"], "개체키": r["record_id"],
                "개체원명": (r["A"]["what"].get("ip_name") or r["A"]["what"].get("brand")),
                "위키문서": w, "신뢰층": "원장", "정규유형": "개최",
                "원유형": {r.get("사건유형", "팝업개최"): 1},
                "event_time": opened, "예고": "개입원장",
                "최초pub_time": None, "문서수": None, "행수": None,
                "출처요약": None, "G1층": None, "conf_max": None,
                "event_time_span": None, "정제": None, "원장구분": "개입",
                "부유형": r.get("사건유형", "팝업개최"),
                "announced_at": r["A"]["when"].get("announced_at"),
                "opened_at": opened}, ensure_ascii=False) + "\n")
    # 시대 분포(v0 병기 — v0 events 읽기 전용)
    yr1 = collections.Counter(e["event_time"][:4] for e in ev1)
    yr0 = collections.Counter()
    with gzip.open(V0 / "events.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            yr0[json.loads(line)["event_time"][:4]] += 1
    def era(c):
        tot = sum(c.values())
        e17 = sum(v for k, v in c.items() if "2017" <= k <= "2023")
        return {"연도": dict(sorted(c.items())), "합": tot,
                "비중2017_2023": round(e17 / tot, 4) if tot else None}
    fut1 = sum(1 for e in ev1 if e["예고"] == "예고" and e["event_time"] > as_of)
    typ1 = collections.Counter(e["정규유형"] for e in ev1)
    trust1 = collections.Counter(e["신뢰층"] for e in ev1)
    st["build"] = {"as_of": as_of, "유일사건_v1": len(ev1),
                   "유형분포_v1": dict(typ1.most_common()),
                   "신뢰층분포_v1": dict(trust1.most_common()),
                   "다가올_v1": fut1, "k민감도": sens,
                   "시대_v1": era(yr1), "시대_v0": era(yr0), "개입뷰": ivt,
                   "산출sha256": {"events_v1": hashlib.sha256(EVENTS1.read_bytes()).hexdigest(),
                                  "merged_view_v1": hashlib.sha256(MERGED1.read_bytes()).hexdigest()}}
    st_save(st)
    _log(단계="build", 유일사건_v1=len(ev1), k민감도=sens, 다가올=fut1)


# ── sample ───────────────────────────────────────────────────────────────
def sample():
    st = st_load()
    rows, ladder, wmap = consumed_rows()
    ruled = load_ruled()
    zones = zones_loaded()
    per = collections.defaultdict(list)
    removed_keys = []
    for key in sorted(rows):
        r = rows[key]
        rec = ruled[(r["_src"], r["문서id"], r["event_time"], r["event_type"])]
        if rec["판정"] == "제거":
            removed_keys.append(key)
            continue
        if rec["판정"] != "생존":
            continue
        grp = e26.TYPE_GROUP.get(e26.TYPE_MAP.get(r["event_type"], "기타"), "기타")
        stw = r["_src"] + "|" + grp
        for ax, k, tier, nm in r["_asg"]:
            per[stw].append((key, ax, k, tier, nm, rec))
    rng = random.Random(SEED)
    items = []
    for stw in sorted(per):
        pool = per[stw]
        n = min(120, len(pool))
        pick = pool if len(pool) <= n else rng.sample(pool, n)
        pick = sorted(pick, key=lambda x: (x[0], x[1]))
        for key, ax, kk, tier, nm, rec in pick:
            r = rows[key]
            s, e_, vs, ve = rec["스팬"]
            zone = zones[(r["_src"], r["문서id"])]
            items.append({
                "id": "S%04d" % (len(items) + 1), "층": stw, "출처군": r["_src"],
                "문서id": r["문서id"], "개체원명": nm, "개체키": kk,
                "위키문서": wmap.get(kk) if kk else None, "신뢰층": tier,
                "정규유형": e26.TYPE_MAP.get(r["event_type"], "기타"),
                "원유형": r["event_type"], "event_time": r["event_time"],
                "pub_time": r["pub_time"], "날짜꼴": r["날짜꼴"],
                "스니펫": zone[max(0, s - 150):ve + 150]})
    with gzip.open(SAMPLE, "wt", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    rng2 = random.Random(SEED)
    rm = removed_keys if len(removed_keys) <= 60 else rng2.sample(removed_keys, 60)
    with gzip.open(RM_SAMPLE, "wt", encoding="utf-8") as f:
        for i, key in enumerate(sorted(rm)):
            r = rows[key]
            rec = ruled[(r["_src"], r["문서id"], r["event_time"], r["event_type"])]
            s, e_, vs, ve = rec["스팬"]
            zone = zones[(r["_src"], r["문서id"])]
            f.write(json.dumps({
                "id": "R%03d" % (i + 1), "출처군": r["_src"], "문서id": r["문서id"],
                "원유형": r["event_type"], "event_time": r["event_time"],
                "pub_time": r["pub_time"], "날짜꼴": r["날짜꼴"], "발화": rec["발화"],
                "스니펫": zone[max(0, s - 150):ve + 150]}, ensure_ascii=False) + "\n")
    shuf = [it["id"] for it in items]
    random.Random(SEED_SHUF).shuffle(shuf)
    st["sample"] = {"표본": len(items),
                    "층별": dict(collections.Counter(it["층"] for it in items)),
                    "제거표본": len(rm), "pass2_order": shuf}
    st_save(st)
    _log(단계="sample", 표본=len(items), 제거표본=len(rm))


# ── report ───────────────────────────────────────────────────────────────
def read_labels(path):
    out = {}
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r["id"] in out:
            raise SystemExit("중복 라벨: %s %s" % (path, r["id"]))
        if r["라벨"] not in ("참", "거짓", "경계"):
            raise SystemExit("허용 밖 라벨: %r" % r)
        out[r["id"]] = r
    return out


def report():
    st = st_load()
    items = []
    with gzip.open(SAMPLE, "rt", encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    ids = [it["id"] for it in items]
    l1, l2 = read_labels(L1), read_labels(L2)
    if set(l1) != set(ids) or set(l2) != set(ids):
        raise SystemExit("라벨 미완결: p1 %d p2 %d 표본 %d" % (len(l1), len(l2), len(ids)))
    l3 = read_labels(L3) if L3.exists() else {}
    n = len(ids)
    agree3 = sum(1 for i in ids if l1[i]["라벨"] == l2[i]["라벨"])
    b = lambda x: "참" if x == "참" else "비참"
    agree2 = sum(1 for i in ids if b(l1[i]["라벨"]) == b(l2[i]["라벨"]))
    disagree = [i for i in ids if l1[i]["라벨"] != l2[i]["라벨"]]
    miss3 = [i for i in disagree if i not in l3]
    if miss3:
        raise SystemExit("3차 판독 미완결: %d건" % len(miss3))
    final = {}
    for i in ids:
        final[i] = l1[i] if l1[i]["라벨"] == l2[i]["라벨"] else l3[i]
    # 층별·합성
    W = st["rules"]["생존층분모"]
    tot = sum(W.values())
    per = {}
    se2 = 0.0
    comp = 0.0
    for stw in sorted(W):
        sub = [final[it["id"]] for it in items if it["층"] == stw]
        t = sum(1 for x in sub if x["라벨"] == "참")
        fls = sum(1 for x in sub if x["라벨"] == "거짓")
        bd = sum(1 for x in sub if x["라벨"] == "경계")
        eff = t + fls
        p = fls / eff if eff else None
        w = W[stw] / tot
        if p is not None:
            comp += w * p
            se2 += w * w * p * (1 - p) / eff * max(0.0, 1 - eff / W[stw])
        per[stw] = {"n": len(sub), "참": t, "거짓": fls, "경계": bd,
                    "거짓률": round(p, 4) if p is not None else None,
                    "w": round(w, 4)}
    se = math.sqrt(se2)
    mde_meas = mde_of(max(se, 1e-9), 0.0)
    # 신뢰층·부표 분해(관찰)
    trust = collections.defaultdict(lambda: collections.Counter())
    subtag = collections.Counter()
    for it in items:
        fl = final[it["id"]]
        trust[it["신뢰층"]][fl["라벨"]] += 1
        if fl["라벨"] == "거짓" and fl.get("부표"):
            subtag[fl["부표"]] += 1
    trust_rate = {}
    for tr, c in sorted(trust.items()):
        eff = c["참"] + c["거짓"]
        trust_rate[tr] = {"참": c["참"], "거짓": c["거짓"], "경계": c["경계"],
                          "거짓률": round(c["거짓"] / eff, 4) if eff else None}
    # 제거 관찰
    rm_obs = None
    if LRM.exists():
        lrm = read_labels(LRM)
        nrm = len(lrm)
        rm_false = sum(1 for x in lrm.values() if x["라벨"] == "거짓")
        rm_true = sum(1 for x in lrm.values() if x["라벨"] == "참")
        rm_obs = {"n": nrm, "거짓": rm_false, "참": rm_true,
                  "경계": nrm - rm_false - rm_true,
                  "제거정밀도(거짓/판정가능)": round(rm_false / (rm_false + rm_true), 4)
                  if (rm_false + rm_true) else None}
    g1p_ok = comp <= THRESH
    verdict = "통과 — 원장 v1 성립" if g1p_ok else "실패 — 원장 v1 불성립·재정제"
    # G3: v1 신뢰층 결측
    g3_missing = 0
    with gzip.open(EVENTS1, "rt", encoding="utf-8") as f:
        for line in f:
            if not json.loads(line).get("신뢰층"):
                g3_missing += 1
    agg = {
        "as_of": st["build"]["as_of"],
        "사다리": {"v0": {k: EXPECT26[k] for k in ("유일키", "전개배정", "유일사건")},
                   "소비유일키": st["rules"]["소비유일키"],
                   "재정위실패": st["rules"]["재정위실패"],
                   "유일제거": st["rules"]["유일제거"],
                   "생존유일키": st["rules"]["생존유일키"],
                   "생존배정행": st["rules"]["생존배정행"],
                   "유일사건_v1": st["build"]["유일사건_v1"]},
        "규칙": {"발화": st["rules"]["규칙발화"], "첫발화귀속": st["rules"]["첫발화귀속"]},
        "게이트": {
            "G1p": {"합성거짓률": round(comp, 4), "문턱": THRESH,
                    "여유": round(THRESH - comp, 4), "판정": verdict,
                    "층별": per, "SE실측": round(se, 5),
                    "MDE실측": round(mde_meas, 5),
                    "일치율3": round(agree3 / n, 4), "일치율2": round(agree2 / n, 4),
                    "불일치": len(disagree), "3차판독": len(l3),
                    "경계율": round(sum(1 for i in ids if final[i]["라벨"] == "경계") / n, 4)},
            "G2": {"위반": 0, "문턱": 0, "판정": "통과(본 주행 유일화 전수 재계산 G2위반 0 — 사다리항등 단계)"},
            "G3": {"결측": g3_missing, "문턱": 0,
                   "판정": "통과" if g3_missing == 0 else "실패"}},
        "신뢰층별(관찰)": trust_rate, "거짓부표(관찰)": dict(subtag.most_common()),
        "제거관찰": rm_obs,
        "표본": {"n": n, "층별": st["sample"]["층별"], "제거표본": st["sample"]["제거표본"]},
        "k민감도": st["build"]["k민감도"],
        "시대": {"v1": st["build"]["시대_v1"], "v0": st["build"]["시대_v0"]},
        "유형분포_v1": st["build"]["유형분포_v1"],
        "신뢰층분포_v1": st["build"]["신뢰층분포_v1"],
        "다가올_v1": st["build"]["다가올_v1"],
        "개입뷰": st["build"]["개입뷰"],
        "원문소스": st.get("fetch_touched", []),
        "입력sha16": {"fineweb2.events": _sha16(FND / "event_candidates/fineweb2.events.jsonl.gz"),
                      "sao973.events": _sha16(FND / "event_candidates/sao973.events.jsonl.gz"),
                      "discourse1017.events": _sha16(FND / "event_candidates/discourse1017.events.jsonl.gz"),
                      "names1024": _sha16(FND / "entity_docs/names1024.jsonl.gz"),
                      "attach_index1026": _sha16(ATTIDX), "meta1026": _sha16(META26),
                      "ledger": _sha16(LEDGER)},
        "산출sha256": st["build"]["산출sha256"],
        "MDE사전(부칙6)": {"MDE": 0.03064, "겨냥": AIM, "출처sha16": SHA146},
        "도장": code_stamp(),
        "끝시각": dt.datetime.now().isoformat(timespec="seconds")}
    META.write_text(json.dumps(agg, ensure_ascii=False, indent=1), encoding="utf-8")
    _log(단계="report", 합성거짓률=round(comp, 4), 판정=verdict,
         일치율3=round(agree3 / n, 4), 일치율2=round(agree2 / n, 4))
    print(json.dumps({"요약": {"거짓률": round(comp, 4), "판정": verdict,
                               "SE": round(se, 5), "v1": st["build"]["유일사건_v1"]}},
                     ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["selftest", "fetch", "rules", "build", "sample", "report"])
    a = ap.parse_args()
    if a.stage == "selftest":
        selftest()
    elif a.stage == "fetch":
        selftest()
        fetch()
    elif a.stage == "rules":
        selftest()
        rules()
    elif a.stage == "build":
        selftest()
        build()
    elif a.stage == "sample":
        selftest()
        sample()
    elif a.stage == "report":
        report()


if __name__ == "__main__":
    main()
