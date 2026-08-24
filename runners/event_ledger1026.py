# -*- coding: utf-8 -*-
"""사이클 1026 — 사건 원장 v0: 1021 후보 41.7만 → 유일 사건 단위 병합·정규화.

사전등록 docs/탐색/1026.md — 이 러너는 사전등록 커밋에서 언다(조항 66 — 주행 중 수정 금지).
단계:
  --stage selftest   방향 탐침(G1·G2·G3 · v5.3-2) + 병합·전개·해소 합성 검사 8 — 실패면 중단
  --stage build      유일화·G2·개체 배정(E1/E2/E3)·병합·events/merged_view 산출(파트 체크포인트)
  --stage g1         층화 표본 · 원문 표적 재조회 · N1~N3 기계 검사 · 층 격리 판정
  --stage report     사다리·게이트·집계 확정(meta1026.json)

위생: CPU ≤5스레드(pyarrow 4·OMP 4) · 파트/샤드 전 load1>10 → 60초 재잼(until) · MPS 0 ·
      전 입력 읽기 전용 · 산출물은 wm_harvest(조항 73-마) · 콘텐츠 위생(실명은 파일 안).
"""
import argparse
import ast
import bisect
import collections
import datetime as dt
import gzip
import hashlib
import json
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
from runners import pubdate1021 as p21          # noqa: E402  (읽기 전용 — 정규식·해소 상수 재사용)
import pyarrow as pa                             # noqa: E402
import pyarrow.compute as pc                     # noqa: E402
import pyarrow.parquet as pq                     # noqa: E402
pa.set_cpu_count(4)

FND = Path("/Users/ax/wm_harvest/foundation")
EVC = FND / "event_candidates"
ENT = FND / "entity_docs"
LEDGER = FND / "ledger_interventions/ledger.jsonl"
OUT = FND / "event_ledger"
OUT.mkdir(parents=True, exist_ok=True)
STATE = OUT / "state1026.json"
EVENTS = OUT / "events.jsonl.gz"
MERGED = OUT / "merged_view.jsonl.gz"
G1S = OUT / "g1_samples.jsonl.gz"
META = OUT / "meta1026.json"
ATTIDX = OUT / "attach_index1026.json.gz"
PROG = OUT / "progress1026.jsonl"

CAND = {"fineweb2": EVC / "fineweb2.events.jsonl.gz",
        "sao973": EVC / "sao973.events.jsonl.gz",
        "discourse1017": EVC / "discourse1017.events.jsonl.gz"}
ISO_1024 = {("fineweb", 2), ("fineweb", 3), ("fresh", 3), ("sao", 3)}   # fp_gate1024 격리층
FW_DIR = Path("/Users/ax/wm_harvest/fineweb2_ko")
DISC_DIR = Path("/Users/ax/wm_harvest/discourse")

# ── 등록 상수(§2~§4) ─────────────────────────────────────────────────────
MERGE_K = 3                      # 병합 반경(일) — 군집 최소일 앵커
TYPE_MAP = {"개최": "개최", "개막": "개최",
            "출시": "출시", "발매": "출시", "런칭": "출시", "론칭": "출시",
            "발간": "출시", "개통": "출시", "오픈": "출시",
            "개봉": "개봉", "방영": "방영", "공개": "공개", "발표": "발표",
            "시작": "시작", "컴백": "컴백", "데뷔": "데뷔",
            "종영": "종영", "콜라보": "콜라보"}
TYPE_GROUP = {"개최": "개최군", "출시": "출시군", "공개": "공표군", "발표": "공표군",
              "개봉": "상영군", "방영": "상영군",
              "시작": "시작군", "컴백": "시작군", "데뷔": "시작군"}
G1_CAP = 0.15                    # G1: 층별 강 오탐률 상한(악화 = +쪽)
G1_K = 120                       # 층당 표본
G1_MINN = 30                     # 판정 최소 n
G1_RELOC_CAP = 0.30              # 재정위 실패율 상한(초과 = 미판정)
G2_CAP = 0                       # G2: 행 위반 상한(악화 = +쪽)
G3_CAP = 0                       # G3: 신뢰층 결측 상한(악화 = +쪽)
SEED = 1026
RE_N1 = re.compile(r"연기|취소|무산|불발|중단")
RE_N2 = re.compile(r"예정이었|계획이었|검토\s*중|논의\s*중|미정|불투명|수도\s*있")
RE_N3 = re.compile(r"당시|였던|었던|았던|지난해|작년|재작년")


def load1_gate():
    """load1>10 이면 60초 재잼(until 관문) — 1021 로그 파일 무접촉(자체 게재)."""
    while True:
        l1 = os.getloadavg()[0]
        if l1 <= 10.0:
            return l1
        _log(단계="load1대기", load1=round(l1, 2))
        time.sleep(60)


def _log(**kw):
    kw["시각"] = dt.datetime.now().isoformat(timespec="seconds")
    with open(PROG, "a", encoding="utf-8") as f:
        f.write(json.dumps(kw, ensure_ascii=False) + "\n")
    print(json.dumps(kw, ensure_ascii=False), flush=True)


def _sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()[:16]


def code_stamp():
    me = Path(__file__).resolve()
    return {"러너sha256": hashlib.sha256(me.read_bytes()).hexdigest(),
            "pubdate1021_sha16": _sha16(ROOT / "runners/pubdate1021.py"),
            "discourse1017_sha16": _sha16(ROOT / "runners/discourse1017.py")}


def st_load():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def st_save(st):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def keywords_list():
    """discourse1017 소스의 KEYWORDS 를 실행 없이 AST 로 읽는다(등록 §3)."""
    src = (ROOT / "runners/discourse1017.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "KEYWORDS":
                    return list(ast.literal_eval(node.value))
    raise RuntimeError("KEYWORDS 미발견")


def names_map():
    """names1024 변형(tier≤2) casefold → 키 집합 · 키 → 위키문서."""
    vmap, wmap = {}, {}
    with gzip.open(ENT / "names1024.jsonl.gz", "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            wmap[r["키"]] = r.get("w")
            for v in r.get("vars", []):
                if v["tier"] <= 2:
                    vmap.setdefault(v["v"].casefold(), set()).add(r["키"])
    return vmap, wmap


# ── 게이트 함수(v5.3 부호 서명 — 셋 다 악화 = +쪽) ───────────────────────
def g1_pass(rate, cap=G1_CAP):
    return rate <= cap


def g2_pass(viol, cap=G2_CAP):
    return viol <= cap


def g3_pass(missing, cap=G3_CAP):
    return missing <= cap


def probe_gates():
    """v5.3-2 방향 탐침 — 합성 문턱 t>0: 악화 극값(+2t) 거짓 · 개선 극값(0) 참."""
    out = []
    out.append(("G1", g1_pass(0.2, 0.1) is False, g1_pass(0.0, 0.1) is True))
    out.append(("G2", g2_pass(6, 3) is False, g2_pass(0, 3) is True))
    out.append(("G3", g3_pass(6, 3) is False, g3_pass(0, 3) is True))
    return out


# ── 병합(§2) ─────────────────────────────────────────────────────────────
def cluster_dates(dates, k=MERGE_K):
    """오름차순 날짜 리스트 → 군집 리스트(앵커=군집 최소일 · 표류 없음)."""
    clusters = []
    for d in sorted(dates):
        if clusters and (d - clusters[-1][0]).days <= k:
            clusters[-1].append(d)
        else:
            clusters.append([d])
    return clusters


def rep_date(support):
    """대표 event_time = 지지 유일 문서 수 최다 날짜(동률 → 최초일).
    support: {date: set(문서id)}"""
    best = None
    for d in sorted(support):
        n = len(support[d])
        if best is None or n > best[1]:
            best = (d, n)
    return best[0]


def selftest():
    fails = []
    # 방향 탐침(v5.3-2)
    for name, worse_false, better_true in probe_gates():
        if not (worse_false and better_true):
            fails.append("탐침:" + name)
    D = dt.date
    # ① k 경계: 0·3일 병합
    if len(cluster_dates([D(2026, 1, 1), D(2026, 1, 4)])) != 1:
        fails.append("병합:3일합류")
    # ② k 경계: 0·4일 분리
    if len(cluster_dates([D(2026, 1, 1), D(2026, 1, 5)])) != 2:
        fails.append("병합:4일분리")
    # ③ 앵커 비표류: 0·3·6 → {0,3}·{6}
    cl = cluster_dates([D(2026, 1, 1), D(2026, 1, 4), D(2026, 1, 7)])
    if not (len(cl) == 2 and len(cl[0]) == 2):
        fails.append("병합:앵커비표류")
    # ④ 대표 최빈(동률 최초)
    if rep_date({D(2026, 1, 1): {"a"}, D(2026, 1, 2): {"b", "c"}}) != D(2026, 1, 2):
        fails.append("대표:최빈")
    if rep_date({D(2026, 1, 1): {"a"}, D(2026, 1, 2): {"b"}}) != D(2026, 1, 1):
        fails.append("대표:동률최초")
    # ⑤ 다개체 전개 · ⑥ 키워드 제외 · ⑦ 모호 비배정 · E3 유일키만
    kws = set(keywords_list())
    vmap = {"뉴진스".casefold(): {"K1", "K2"}, "단독키".casefold(): {"K9"}}
    row_ents = ["단독키", "뉴진스", sorted(kws)[0]]
    asg = assign_entities(row_ents, kws, vmap)
    kinds = sorted(a[2] for a in asg)
    if not (len(asg) == 2 and kinds == ["E1", "E2모호"]):
        fails.append("전개·키워드·모호")
    if attach_pick({"d1": ["K1"]}, "d1") != "K1" or attach_pick({"d2": ["K1", "K2"]}, "d2") is not None:
        fails.append("E3유일키")
    # ⑧ 유형 사전 전사: 1021 동사 16 전항이 비「기타」로
    for v in p21.EV_VERBS:
        if TYPE_MAP.get(v, "기타") == "기타":
            fails.append("유형사전:" + v)
    ok = not fails
    _log(단계="selftest", 판정="통과" if ok else "실패", 실패=fails,
         키워드수=len(kws), 도장=code_stamp())
    if not ok:
        sys.exit(1)
    return True


def assign_entities(names, kws, vmap):
    """근접 이름 → [(개체축값, 키 or None, 신뢰층, 원명)] · 키워드 제외."""
    out = []
    for nm in names:
        if nm in kws:
            continue
        ks = vmap.get(nm.casefold())
        if ks and len(ks) == 1:
            k = next(iter(ks))
            out.append((k, k, "E1", nm))
        elif ks:
            out.append(("raw:" + nm.casefold(), None, "E2모호", nm))
        else:
            out.append(("raw:" + nm.casefold(), None, "E2미해소", nm))
    return out


def attach_pick(idx, doc):
    ks = idx.get(doc)
    if ks and len(ks) == 1:
        return ks[0]
    return None


# ── build ────────────────────────────────────────────────────────────────
def load_unique_rows():
    """후보 3파일 → 유일키 (출처,문서id,event_time,event_type) 유일화 + G2 행 검사."""
    seen = {}
    n_raw = 0
    g2_viol = 0
    for src, path in CAND.items():
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                n_raw += 1
                key = (r["출처"], r["문서id"], r["event_time"], r["event_type"])
                if key in seen:
                    continue
                et = dt.date.fromisoformat(r["event_time"])
                pt = dt.date.fromisoformat(r["pub_time"])
                diff = (et - pt).days
                if diff != r["diff일"] or diff < 1 or diff > p21.EV_MAX_DIFF:
                    g2_viol += 1
                    continue
                r["_src"] = src
                seen[key] = r
    return n_raw, seen, g2_viol


def build_attach_index(need):
    """1024 색인에서 무개체 문서의 부착 회수(엔진층·비카탈로그·비격리) — 파트 체크포인트."""
    st = {"done": [], "idx": {}, "amb": 0, "hit": 0}
    if ATTIDX.exists():
        st = json.loads(gzip.open(ATTIDX, "rt", encoding="utf-8").read())
    tasks = [("sao", ENT / "docs_sao.jsonl.gz"), ("fresh", ENT / "docs_fresh.jsonl.gz")]
    for p in sorted((ENT / "fineweb_parts").iterdir()):
        tasks.append(("fineweb", p))
    for src, path in tasks:
        tag = src + "/" + path.name
        if tag in st["done"]:
            continue
        load1_gate()
        for line in gzip.open(path, "rt", encoding="utf-8"):
            r = json.loads(line)
            d = r["doc"]
            if d not in need.get(src, ()):
                continue
            if r.get("층") != "엔진" or r.get("catalog"):
                continue
            ks = sorted({e[0] for e in r["부착"] if (src, e[1]) not in ISO_1024})
            if not ks:
                continue
            st["hit"] += 1
            if len(ks) == 1:
                st["idx"][src + "|" + d] = ks
            else:
                st["amb"] += 1
        st["done"].append(tag)
        with gzip.open(ATTIDX, "wt", encoding="utf-8") as f:
            f.write(json.dumps(st, ensure_ascii=False))
        _log(단계="build/부착색인", 파트=tag, 회수=len(st["idx"]), 모호=st["amb"])
    return st


SRC1024 = {"fineweb2": "fineweb", "sao973": "sao", "discourse1017": "fresh"}


def build():
    t0 = time.time()
    st = st_load()
    st.setdefault("as_of", dt.date.today().isoformat())
    st["build_start"] = dt.datetime.now().isoformat(timespec="seconds")
    kws = set(keywords_list())
    vmap, wmap = names_map()
    n_raw, rows, g2_viol = load_unique_rows()
    _log(단계="build", 무엇="유일화", 행=n_raw, 유일키=len(rows), G2위반=g2_viol)
    # E3 대상: 근접 배정 0 인 행의 문서
    need = {"fineweb": set(), "sao": set(), "fresh": set()}
    for r in rows.values():
        asg = assign_entities(r["개체"], kws, vmap)
        r["_asg"] = asg
        if not asg:
            need[SRC1024[r["_src"]]].add(r["문서id"])
    _log(단계="build", 무엇="E3대상", **{k: len(v) for k, v in need.items()})
    att = build_attach_index(need)
    # 전개
    ladder = collections.Counter()
    ladder["행"] = n_raw
    ladder["유일키"] = len(rows)
    ladder["G2위반격리"] = g2_viol
    assigns = []          # (축값, 키, 층, 원명, 정규유형, 원유형, date, 문서id, 출처군, conf, pub)
    for r in rows.values():
        norm = TYPE_MAP.get(r["event_type"], "기타")
        asg = r["_asg"]
        if not asg:
            k3 = attach_pick(att["idx"], SRC1024[r["_src"]] + "|" + r["문서id"])
            if k3:
                asg = [(k3, k3, "E3", None)]
                ladder["E3회수행"] += 1
            else:
                ladder["무개체제외행"] += 1
                continue
        else:
            ladder["근접배정행"] += 1
        kwn = len([nm for nm in r["개체"] if nm in kws])
        if kwn:
            ladder["키워드제외건"] += kwn
        for ax, k, tier, nm in asg:
            ladder["배정_" + tier] += 1
            assigns.append((ax, k, tier, nm, norm, r["event_type"],
                            dt.date.fromisoformat(r["event_time"]), r["문서id"],
                            r["_src"], r["conf"], r["pub_time"]))
    ladder["전개배정"] = len(assigns)
    # 병합
    groups = collections.defaultdict(list)
    for a in assigns:
        groups[(a[0], a[4])].append(a)
    events = []
    tier_rank = {"E1": 0, "E3": 1, "E2모호": 2, "E2미해소": 3}
    for (ax, norm), items in sorted(groups.items()):
        clusters = cluster_dates([a[6] for a in items])
        spans = [(c[0], c[-1]) for c in clusters]
        for lo, hi in spans:
            sub = [a for a in items if lo <= a[6] <= hi]
            support = collections.defaultdict(set)
            for a in sub:
                support[a[6]].add(a[7])
            rd = rep_date(support)
            docs = {a[7] for a in sub}
            first_pub = min(a[10] for a in sub)
            srcsum = collections.Counter()
            for a in sub:
                srcsum[a[8]] = len({b[7] for b in sub if b[8] == a[8]})
            g1layers = sorted({a[8] + "|" + TYPE_GROUP.get(norm, "기타") for a in sub})
            best = min(sub, key=lambda a: tier_rank[a[2]])
            key = best[1]
            eid = "EV0-" + hashlib.sha1((ax + "|" + norm + "|" + rd.isoformat())
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
    ladder["유일사건"] = len(events)
    g3_missing = sum(1 for e in events if not e.get("신뢰층"))
    with gzip.open(EVENTS, "wt", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    # 병합 뷰(개입 원장 포함 — 한 표)
    ivt = {"전건": 0, "시간축미배치": 0, "위키병기": 0}
    with gzip.open(MERGED, "wt", encoding="utf-8") as f:
        for e in events:
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
                "event_time_span": None, "원장구분": "개입",
                "부유형": r.get("사건유형", "팝업개최"),
                "announced_at": r["A"]["when"].get("announced_at"),
                "opened_at": opened}, ensure_ascii=False) + "\n")
    st["build"] = {"사다리": dict(ladder), "G2위반": g2_viol, "G3결측": g3_missing,
                   "부착색인": {"회수문서": len(att["idx"]), "모호문서": att["amb"],
                                "부착적중": att["hit"]},
                   "개입뷰": ivt, "초": round(time.time() - t0, 1)}
    st_save(st)
    _log(단계="build", 무엇="완료", 유일사건=len(events), 초=st["build"]["초"])
    return st


# ── g1 ───────────────────────────────────────────────────────────────────
def g1_strata_sample():
    """소비 유일키 행에서 층화 저수지 표본(층 = 출처군×유형군 · 층당 K · 씨앗 고정)."""
    _, rows, _ = load_unique_rows()
    rng = random.Random(SEED)
    res = collections.defaultdict(list)
    cnt = collections.Counter()
    for key in sorted(rows):
        r = rows[key]
        norm = TYPE_MAP.get(r["event_type"], "기타")
        grp = TYPE_GROUP.get(norm, "기타")
        stw = r["_src"] + "|" + grp
        cnt[stw] += 1
        it = {"층": stw, "출처군": r["_src"], "문서id": r["문서id"],
              "event_time": r["event_time"], "event_type": r["event_type"],
              "pub_time": r["pub_time"]}
        if len(res[stw]) < G1_K:
            res[stw].append(it)
        else:
            j = rng.randrange(cnt[stw])
            if j < G1_K:
                res[stw][j] = it
    return res, cnt


def fetch_texts(samples):
    """표본 문서 원문 표적 재조회 — 반환 {(출처군,문서id): text}."""
    need = collections.defaultdict(set)
    for its in samples.values():
        for it in its:
            need[it["출처군"]].add(it["문서id"])
    texts = {}
    touched = []
    # ⓒ discourse — 데몬 수확물 스캔(sha1(url|제목)[:16])
    if need["discourse1017"]:
        import glob as _g
        for path in sorted(_g.glob(str(DISC_DIR / "*" / "*.jsonl.gz"))):
            try:
                for line in gzip.open(path, "rt", encoding="utf-8"):
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    did = hashlib.sha1((r.get("url") or r.get("제목") or "")
                                       .encode("utf-8")).hexdigest()[:16]
                    if did in need["discourse1017"] and ("discourse1017", did) not in texts:
                        texts[("discourse1017", did)] = ((r.get("제목") or "") + " "
                                                        + (r.get("본문") or "")).strip()
            except Exception as e:
                _log(단계="g1", 경고="담론파일 스킵", 파일=path, err=str(e))
    # 파케이 표적 읽기(id 열 → 행→rg 사상 → 해당 rg 만 text)
    def parquet_fetch(paths, ids, src):
        left = set(ids)
        for path in paths:
            if not left:
                break
            load1_gate()
            pf = pq.ParquetFile(path)
            md = pf.metadata
            offs = [0]
            for i in range(md.num_row_groups):
                offs.append(offs[-1] + md.row_group(i).num_rows)
            idcol = pf.read(columns=["id"]).column("id")
            mask = pc.is_in(idcol, value_set=pa.array(sorted(left)))
            hits = pc.indices_nonzero(mask).to_pylist()
            touched.append({"파일": str(path), "크기": os.path.getsize(path),
                            "mtime": int(os.path.getmtime(path)), "적중": len(hits)})
            rgs = sorted({bisect.bisect_right(offs, h) - 1 for h in hits})
            for rg in rgs:
                d = pf.read_row_group(rg, columns=["id", "text"]).to_pydict()
                for j, did in enumerate(d["id"]):
                    if did in left:
                        texts[(src, did)] = d["text"][j] or ""
                        left.discard(did)
        return left
    import glob as _g
    if need["sao973"]:
        shards = sorted(_g.glob(str(p21.HPLT_DIR / "train-*-of-00464.parquet")))
        picked = [shards[i] for i in p21.SHARD_IDX if i < len(shards)]
        miss = parquet_fetch(picked, need["sao973"], "sao973")
        _log(단계="g1", 무엇="sao 재조회", 필요=len(need["sao973"]), 미발견=len(miss))
    if need["fineweb2"]:
        shards = sorted(_g.glob(str(FW_DIR / "*.parquet")))
        miss = parquet_fetch(shards, need["fineweb2"], "fineweb2")
        _log(단계="g1", 무엇="fineweb 재조회", 필요=len(need["fineweb2"]), 미발견=len(miss))
    return texts, touched


def reextract_spans(text, pub):
    """1021 extract_events 의 스팬 포착판 — 정규식·해소·우선순위·제외 규칙 항등 미러."""
    zone = text[:p21.EV_WIN]
    matches = []
    for rx, kind in ((p21.RE_B_KO, "절대_년월일"), (p21.RE_B_SEP, "절대_구분자")):
        for m in rx.finditer(zone):
            d = p21._mkdate(*m.groups())
            if d:
                matches.append((m.start(), m.end(), kind, d))
    for m in p21.RE_ONEUN.finditer(zone):
        day = int(m.group(1))
        d = p21._try_date(pub.year, pub.month, day)
        if d is None or d < pub:
            y2, m2 = p21._add_months(pub.year, pub.month, 1)
            d = p21._try_date(y2, m2, day)
        if d:
            matches.append((m.start(), m.end(), "오는D일", d))
    for m in p21.RE_NAEDAL.finditer(zone):
        y2, m2 = p21._add_months(pub.year, pub.month, 1)
        d = p21._try_date(y2, m2, int(m.group(1)))
        if d:
            matches.append((m.start(), m.end(), "내달D일", d))
    for m in p21.RE_IDAL.finditer(zone):
        d = p21._try_date(pub.year, pub.month, int(m.group(1)))
        if d:
            matches.append((m.start(), m.end(), "이달D일", d))
    taken = [(s, e) for s, e, *_ in matches]
    for m in p21.RE_MD.finditer(zone):
        s, e = m.start(), m.end()
        if any(not (e <= ts or s >= te) for ts, te in taken):
            continue
        pre = zone[max(0, s - 8):s]
        if re.search(r"(19|20)\d{2}\s*년\s*$", pre):
            continue
        d = p21._try_date(pub.year, int(m.group(1)), int(m.group(2)))
        if d is not None and (d - pub).days < -45:
            d = p21._try_date(pub.year + 1, int(m.group(1)), int(m.group(2)))
        if d:
            matches.append((s, e, "연도무MD", d))
    out, used = [], []
    matches.sort(key=lambda x: ({"절대_년월일": 0, "절대_구분자": 0, "오는D일": 1,
                                 "내달D일": 1, "이달D일": 1, "연도무MD": 2}[x[2]], x[0]))
    for s, e, kind, d in matches:
        if any(not (e <= us or s >= ue) for us, ue in used):
            continue
        used.append((s, e))
        if zone[max(0, s - 6):s].find("지난") >= 0:
            continue
        vm = p21.RE_EV_VERB.search(zone[e:e + 40])
        if not vm:
            continue
        diff = (d - pub).days
        if diff <= 0 or diff > p21.EV_MAX_DIFF:
            continue
        if len(out) >= p21.EV_CAP:
            continue
        out.append((d.isoformat(), vm.group(1), s, e))
    return out, zone


def g1():
    st = st_load()
    samples, strata_n = g1_strata_sample()
    _log(단계="g1", 무엇="표본", 층수=len(samples),
         표본합=sum(len(v) for v in samples.values()))
    texts, touched = fetch_texts(samples)
    layers = collections.defaultdict(lambda: collections.Counter())
    with gzip.open(G1S, "wt", encoding="utf-8") as f:
        for stw, its in sorted(samples.items()):
            for it in its:
                L = layers[stw]
                L["n"] += 1
                text = texts.get((it["출처군"], it["문서id"]))
                if text is None:
                    L["재정위실패"] += 1
                    f.write(json.dumps(dict(it, 재정위="원문미발견"),
                                       ensure_ascii=False) + "\n")
                    continue
                pub = dt.date.fromisoformat(it["pub_time"])
                evs, zone = reextract_spans(text, pub)
                hit = next((x for x in evs if x[0] == it["event_time"]
                            and x[1] == it["event_type"]), None)
                if hit is None:
                    L["재정위실패"] += 1
                    f.write(json.dumps(dict(it, 재정위="재추출불일치"),
                                       ensure_ascii=False) + "\n")
                    continue
                _, _, s, e = hit
                snip = zone[max(0, s - 60):e + 60]
                pre30 = zone[max(0, s - 30):s]
                n1 = 1 if RE_N1.search(snip) else 0
                n2 = 1 if RE_N2.search(snip) else 0
                n3 = 1 if RE_N3.search(pre30) else 0
                L["판정n"] += 1
                L["N1"] += n1
                L["N2"] += n2
                L["N3"] += n3
                if n1 or n2 or n3:
                    L["강오탐"] += 1
                f.write(json.dumps(dict(it, 스니펫=snip, N1=n1, N2=n2, N3=n3),
                                   ensure_ascii=False) + "\n")
    table, iso, und = {}, [], []
    for stw in sorted(layers):
        L = layers[stw]
        n, jn = L["n"], L["판정n"]
        reloc_fail = (L["재정위실패"] / n) if n else 0.0
        rate = (L["강오탐"] / jn) if jn else 0.0
        if n < G1_MINN:
            verdict = "미판정(n<30)"
            und.append(stw)
        elif reloc_fail > G1_RELOC_CAP:
            verdict = "미판정(재정위)"
            und.append(stw)
        elif not g1_pass(rate):
            verdict = "격리"
            iso.append(stw)
        else:
            verdict = "통과"
        table[stw] = {"n": n, "판정n": jn, "N1": L["N1"], "N2": L["N2"], "N3": L["N3"],
                      "강오탐": L["강오탐"], "오탐률": round(rate, 4),
                      "재정위실패율": round(reloc_fail, 4),
                      "여유": round(G1_CAP - rate, 4), "판정": verdict}
    st["g1"] = {"층표": table, "격리": iso, "미판정": und,
                "층분모": dict(strata_n), "원문소스": touched,
                "자료탐침": {"악화극값참": 0, "개선극값거짓": 0}}
    for name, worse_false, better_true in probe_gates():
        if not worse_false:
            st["g1"]["자료탐침"]["악화극값참"] += 1
        if not better_true:
            st["g1"]["자료탐침"]["개선극값거짓"] += 1
    st_save(st)
    _log(단계="g1", 무엇="완료", 격리=iso, 미판정=und)
    return st


# ── report ───────────────────────────────────────────────────────────────
def report():
    st = st_load()
    iso = set(st["g1"]["격리"])
    as_of = st["as_of"]
    events = [json.loads(l) for l in gzip.open(EVENTS, "rt", encoding="utf-8")]
    def is_net(e):
        return any(l not in iso for l in e["G1층"])
    net = [e for e in events if is_net(e)]
    fut = [e for e in net if e["예고"] == "예고" and e["event_time"] > as_of]
    fut_src = collections.Counter()
    for e in fut:
        for s in e["출처요약"]:
            fut_src[s] += 1
    dens = collections.Counter()
    for e in net:
        if e["개체키"]:
            dens[e["개체키"]] += 1
    dv = sorted(dens.values())
    def q(v, p):
        return v[min(len(v) - 1, int(p * len(v)))] if v else 0
    typ_g = collections.Counter(e["정규유형"] for e in events)
    typ_n = collections.Counter(e["정규유형"] for e in net)
    trust = collections.Counter(e["신뢰층"] for e in net)
    agg = {
        "as_of": as_of,
        "사다리": st["build"]["사다리"],
        "게이트": {
            "G1": {"층표": st["g1"]["층표"], "격리": sorted(iso),
                   "미판정": st["g1"]["미판정"], "문턱": G1_CAP},
            "G2": {"위반": st["build"]["G2위반"], "문턱": G2_CAP,
                   "여유": G2_CAP - st["build"]["G2위반"],
                   "판정": "통과" if g2_pass(st["build"]["G2위반"]) else "실패"},
            "G3": {"결측": st["build"]["G3결측"], "문턱": G3_CAP,
                   "여유": G3_CAP - st["build"]["G3결측"],
                   "판정": "통과" if g3_pass(st["build"]["G3결측"]) else "실패"},
            "자료탐침": st["g1"]["자료탐침"]},
        "원장": {"유일사건_gross": len(events), "유일사건_net": len(net),
                 "유형분포_gross": dict(typ_g.most_common()),
                 "유형분포_net": dict(typ_n.most_common()),
                 "신뢰층분포_net": dict(trust.most_common()),
                 "예고형_net": sum(1 for e in net if e["예고"] == "예고"),
                 "보도형_net": sum(1 for e in net if e["예고"] == "보도형"),
                 "다가올사건_net": len(fut), "다가올사건_출처별": dict(fut_src),
                 "개체밀도_net": {"키개체수": len(dens),
                                  "중앙": q(dv, 0.5), "q90": q(dv, 0.9),
                                  "최대": dv[-1] if dv else 0,
                                  "사건합": sum(dv)},
                 "병합축약": {"전개배정": st["build"]["사다리"]["전개배정"],
                              "사건_gross": len(events)}},
        "개입뷰": st["build"]["개입뷰"],
        "입력sha16": {k: _sha16(p) for k, p in
                      [("fineweb2.events", CAND["fineweb2"]),
                       ("sao973.events", CAND["sao973"]),
                       ("discourse1017.events", CAND["discourse1017"]),
                       ("ledger", LEDGER),
                       ("names1024", ENT / "names1024.jsonl.gz")]},
        "산출sha256": {"events": hashlib.sha256(EVENTS.read_bytes()).hexdigest(),
                       "merged_view": hashlib.sha256(MERGED.read_bytes()).hexdigest()},
        "도장": code_stamp(),
        "끝시각": dt.datetime.now().isoformat(timespec="seconds")}
    META.write_text(json.dumps(agg, ensure_ascii=False, indent=1), encoding="utf-8")
    _log(단계="report", 무엇="완료", 유일사건_net=len(net), 다가올=len(fut))
    print(json.dumps({"요약": {"gross": len(events), "net": len(net),
                               "다가올": len(fut), "G2위반": st["build"]["G2위반"],
                               "G1격리": sorted(iso)}}, ensure_ascii=False))
    return agg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["selftest", "build", "g1", "report"])
    a = ap.parse_args()
    if a.stage == "selftest":
        selftest()
    elif a.stage == "build":
        selftest()
        build()
    elif a.stage == "g1":
        selftest()
        g1()
    elif a.stage == "report":
        report()


if __name__ == "__main__":
    main()
