# -*- coding: utf-8 -*-
"""수집 1010 러너 — ft-v2 선행: 기획서 문체 코퍼스 수집·검증 (사전등록 docs/탐색/1010.md 에서 얼었다).

게이트 5칸(전부 등록 상수 문턱 · J/J‴/SE 유래 문턱 0):
  G1  토큰량 T ≥ 5,000,000 (base 토크나이저 · add_special_tokens=False)
  G2  주대비 — 코퍼스 표본 256문 OOD 중앙값 m 의 최근접 중심 = 기획서 (등록 상수 중심 셋)
  G3a 폐기 비율 ≤ 0.60 · G3b 최종 ≥40자 문단 정확 중복 0 · G4 장부 필수 칸 결측 0
앵커(«실행 간» 결정론 재현): A1 REF_NN · A2 기획서 24문 중앙값 · A3 분포-안 128 중앙값.
OOD 자 = serve.py 자구 미러(1009 러너와 같은 함수 자구 — 다른 자 발명 금지 · 조항 66).
콘텐츠 위생: 이 러너의 out JSON 에 수집 문서 제목·본문·개별 URL 을 싣지 않는다(집계·sha 만).
쓰는 법:  python3 runners/harvest1010.py    (CPU 전용 · MPS 0 · 네트워크 0)
"""
import glob
import hashlib
import json
import os
import re
import sys
import time
import traceback
import unicodedata

import numpy as np
import torch

torch.set_num_threads(4)

REPO = "/Users/ax/world_model"
ART = "/Users/ax/wm_harvest/foundation"
TRI = os.path.join(ART, "triples")
FW2 = "/Users/ax/wm_harvest/fineweb2_ko"
EXP = os.path.join(ART, "exp", "harvest1010")
CORP = os.path.join(ART, "ft2_corpus")
HF_DIR = os.path.join(ART, "ft", "ckpt", "ft-v1", "hf")
QUEUE = os.path.join(ART, "queue.txt")
QSTATE = os.path.join(ART, "queue.state")
OUT_JSON = os.path.join(REPO, "runners", "out1010_harvest.json")
SNAP = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
        "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
FT_SLIM = os.path.join(ART, "ft", "ckpt", "ft-v1", "model_slim_fp32.pt")
P_PLAN = os.path.join(REPO, "data", "probe1009_기획서.txt")
P_FAR = os.path.join(REPO, "data", "probe1009_원거리.txt")

sys.path.insert(0, REPO)
from pretrain.epoch_guard import assert_epoch                      # 부칙 4

# ── 등록 상수 (사전등록 §2·§4 — 전부 등록 상수 · 측정 뒤 수정 금지) ──
REG_EPOCH = "3a5c2543a55f1dab"
C_IND = 0.8964469231127604      # out1009 base05b 분포-안 128 중앙값
C_PLAN = 6.529804430324812      # out1009 base05b 기획서 24문 중앙값
C_FAR = 9.238869818491963       # out1009 base05b 원거리 20문 중앙값
REF_NN_REG = 19.733196          # out1009 base05b REF_NN
ANCHOR_TOL = 1e-4
G1_MIN_TOKENS = 5_000_000
G3A_MAX_DROP = 0.60
MIN_DOC_CHARS = 300             # R1 길이 하한(원문)
MIN_CLEAN_CHARS = 200           # 정제 후 하한
MIN_HANGUL = 0.30
PARA_DEDUP_MIN = 40
SENT_MIN, SENT_MAX = 20, 200
POOL_CAP = 200_000
N_SAMPLE = 256
WEB_EVERY = 200                 # 불통과 문서 매 200번째에서 대조군 문장
STAT_SEED = 11010               # 신규 스트림 — [·,0] 코퍼스 [·,1] 웹 [·,2~4] SE
IND_SEED = [11009, 0]           # 분포-안 «동일 표본 강제 재현» 전용(1009 자구)
N_BOOT = 10000
LOAD_GATE = 10.0
TOKENS_PER_STEP = 32768         # finetune.py 자구: seq1024 × micro2 × accum16

MARK_A = ("사업계획서", "제안서", "기획서", "기획안", "공모전", "지원사업", "제안요청서",
          "사업 계획", "사업공고", "모집공고", "입찰공고")
MARK_B = ("추진 배경", "추진배경", "사업 목적", "사업목적", "사업 개요", "사업개요",
          "기대효과", "기대 효과", "추진 전략", "추진전략", "세부 과제", "지원 대상",
          "지원대상", "지원 내용", "지원내용", "신청 자격", "신청자격", "평가 기준",
          "선정 기준", "사업 기간", "사업기간", "소요 예산", "추진 체계", "추진체계",
          "성과 지표", "성과지표", "KPI", "타깃", "포지셔닝", "차별화 전략", "시장 분석",
          "수익 모델", "마케팅 전략", "런칭", "신청 방법", "신청방법", "접수 기간",
          "접수기간", "사업 내용", "사업내용", "추진 계획", "추진계획", "제출 서류",
          "제출서류")
QUICK = ("사업", "제안", "기획", "공모", "공고")   # A마커 전부의 부분문자열 — 손실 0 선검사

EXPECT_SHA = {
    os.path.join(TRI, "sao.npz"): "f120013017dcf512",
    os.path.join(TRI, "meta.jsonl"): "f74f94235bc5f032",
    os.path.join(TRI, "text_emb_qwen05b.npz"): "c4128e73c8ea52ca",
    P_PLAN: "0cda661219f9443c",
    P_FAR: "9a27d24f1aa7a5c7",
    os.path.join(REPO, "runners/out1009_embed.json"): "d1ecd4b56235a4f9",
    os.path.join(REPO, "data/lab/1009_판_후.json"): "bc06842266584bb3",
    "/Users/ax/wm_harvest/fineweb955_fetch.jsonl": "533e952a616c8db4",
}

QLINE_PREFIX = "# [의뢰 · 사이클 1009 불통과 갈래] ft-v2"


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def prog(rec):
    rec = dict(rec)
    rec["t"] = now()                                   # 부칙 4 ㉰ — 전 행 시각 칸
    os.makedirs(EXP, exist_ok=True)
    with open(os.path.join(EXP, "progress.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False), flush=True)


def load_gate(tag):
    n = 0
    while os.getloadavg()[0] > LOAD_GATE:
        n += 1
        prog({"load 관문": tag, "load1": round(os.getloadavg()[0], 2), "대기": n})
        time.sleep(60)
    return n


# ── 게이트 (부호 서명 · v5.3) ─────────────────────────────────────────
def g1_pass(T):
    return T >= G1_MIN_TOKENS

def g2_pass(m):
    dp = abs(m - C_PLAN)
    return dp < abs(m - C_IND) and dp < abs(m - C_FAR)

def g3a_pass(r):
    return r <= G3A_MAX_DROP

def g3b_pass(n):
    return n <= 0

def g4_pass(n):
    return n <= 0


def presynth_probe():
    """v5.3-2 — 측정 «전» 합성 방향 탐침(t=1). 어긋나면 측정 없이 중단."""
    checks = {
        "G1(적을수록− 나쁨)": (not g1_pass(G1_MIN_TOKENS - 2)) and g1_pass(G1_MIN_TOKENS + 2),
        "G2(양쪽 — 분포-안 극값 거짓)": not g2_pass(C_IND),
        "G2(양쪽 — 원거리 극값 거짓)": not g2_pass(C_FAR),
        "G2(중심 참)": g2_pass(C_PLAN),
        "G3a(오르면+ 나쁨)": (not g3a_pass(G3A_MAX_DROP + 2)) and g3a_pass(G3A_MAX_DROP - 2),
        "G3b(오르면+ 나쁨)": (not g3b_pass(2)) and g3b_pass(0),
        "G4(오르면+ 나쁨)": (not g4_pass(2)) and g4_pass(0),
    }
    return all(checks.values()), checks


# ── 텍스트 유틸 (사전등록 §2 자구) ────────────────────────────────────
def hangul_ratio(s):
    ns = [c for c in s if not c.isspace()]
    if not ns:
        return 0.0
    return sum(1 for c in ns if "가" <= c <= "힣") / len(ns)


def sentences_of(text):
    out = []
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        for seg in re.split(r"(?<=[.!?])\s+", para):
            seg = seg.strip()
            if SENT_MIN <= len(seg) <= SENT_MAX and hangul_ratio(seg) >= MIN_HANGUL:
                out.append(seg)
    return out


def hash_keep(s, mod=7):
    return int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16) % mod == 0


def marker_hits(text):
    if not any(q in text for q in QUICK):
        return 0, 0
    a = sum(1 for m in MARK_A if m in text)
    if a == 0:
        return 0, 0
    b = sum(1 for m in MARK_B if m in text)
    return a, b


def clean_doc(text, para_seen):
    """NFC · \r 제거 · 문단 전역 정확 중복 제거(≥40자). 반환 (정제문, 중복으로 뺀 문자수)."""
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    kept, dup_chars = [], 0
    for para in text.split("\n"):
        para = para.strip()
        if not para:
            continue
        if len(para) >= PARA_DEDUP_MIN:
            h = hashlib.sha1(para.encode("utf-8")).hexdigest()
            if h in para_seen:
                dup_chars += len(para)
                continue
            para_seen.add(h)
        kept.append(para)
    return "\n".join(kept), dup_chars


# ── OOD 자 — serve.py 자구 미러 (runners/embed1009.py 자구) ──────────
def embed_texts_live(model, tok, texts, bs=16):
    outs = []
    for b0 in range(0, len(texts), bs):
        batch = texts[b0:b0 + bs]
        enc = tok(batch, padding=True, truncation=True, max_length=96, return_tensors="pt")
        with torch.no_grad():
            h = model(**enc).last_hidden_state
        mask = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
        outs.append(((h * mask).sum(1) / mask.sum(1).clamp(min=1.0)).numpy().astype(np.float32))
    return np.concatenate(outs)


def ref_nn(E_tr):
    samp = E_tr[np.random.default_rng(0).choice(len(E_tr), size=min(512, len(E_tr)), replace=False)]
    d = np.sqrt(((samp[:, None, :] - samp[None, :, :]) ** 2).sum(-1))
    np.fill_diagonal(d, np.inf)
    return float(np.median(d.min(axis=1)))


def ood_ratios(embs, E_tr, refnn, chunk=1024):
    out = np.empty(len(embs))
    for i, e in enumerate(embs):
        dmin = np.inf
        for k in range(0, len(E_tr), chunk):
            d = np.sqrt(((E_tr[k:k + chunk] - e[None]) ** 2).sum(-1)).min()
            dmin = min(dmin, float(d))
        out[i] = dmin / max(refnn, 1e-9)
    return out


def pctiles(v):
    qs = (1, 5, 10, 25, 50, 75, 90, 95, 99)
    return {("p%02d" % q): round(float(np.percentile(v, q)), 4) for q in qs}


def boot_se_median(vals, seed_key, B=N_BOOT):
    rng = np.random.default_rng(seed_key)
    v = np.asarray(vals, dtype=np.float64)
    idx = rng.integers(0, len(v), size=(B, len(v)))
    return float(np.std(np.median(v[idx], axis=1)))


def ood_summary(r, se):
    return {"중앙값": float(np.median(r)), "SE(문장 붓스트랩)": round(se, 5),
            "분위수": pctiles(r), "n": int(len(r)),
            "경고선(3.0) 밖 비율": round(float(np.mean(np.asarray(r) >= 3.0)), 4)}


def main():
    t_all = time.time()
    시작 = now()
    out = {"러너": "runners/harvest1010.py", "사전등록": "docs/탐색/1010.md §0~§6",
           "러너 자신": sha16(os.path.abspath(__file__)), "시작 시각": 시작,
           "표적": "전역 — ft-v2 선행(기획서 문체 코퍼스 수집·검증) · 판 무접촉"}
    os.makedirs(EXP, exist_ok=True)
    os.makedirs(CORP, exist_ok=True)

    # 0) 합성 방향 탐침 — 측정 «전»
    ok, pre = presynth_probe()
    out["합성 방향 탐침(측정 전 · v5.3-2)"] = pre
    if not ok:
        out["판정어"] = "중단 — 합성 방향 탐침 어긋남(등록 결함 · 측정 없이 중단 · 승격 0)"
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    # 문턱 성분 낙인(§4): 전부 등록 상수 — J/J‴/SE 유래 0 · 퇴화 판정 대상 아님
    out["문턱 성분(#141 ⑥ 유)"] = {"G1": "등록상수 5e6", "G2": "등록상수 중심 3(out1009 인용)",
                                "G3a": "등록상수 0.60", "G3b": "등록상수 계수 0",
                                "G4": "등록상수 계수 0", "J/J‴/SE 유래": 0,
                                "퇴화 규칙": "대상 아님(전부 등록 상수 — §4 사전 신고)"}

    # 1) 시대 + 원천 sha 실측 대조 — 불일치면 측정 없이 중단
    out["시대(부칙 4 — assert_epoch 반환값)"] = assert_epoch(REG_EPOCH)
    shas, bad = {}, []
    for p, want in sorted(EXPECT_SHA.items()):
        got = sha16(p)
        shas[p] = {"등록": want, "실측": got, "일치": got == want}
        if got != want:
            bad.append(p)
    out["잰 소스(조항 66)"] = shas
    if bad:
        out["판정어"] = "중단 — 원천 sha 불일치(측정 없이 중단 · 승격 0): %s" % bad
        json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        return
    prog({"국면": "sha 대조", "통과": True})

    # 2) 스캔 — FineWeb2-ko 25 샤드 전량 (파일명 정렬 · 조기 중단 없음)
    import pyarrow as pa
    import pyarrow.parquet as pq
    try:
        pa.set_cpu_count(4)
        pa.set_io_thread_count(4)
    except Exception:
        pass
    files = sorted(glob.glob(os.path.join(FW2, "*.parquet")))
    assert len(files) == 25, "🔴 샤드 수 %d ≠ 25" % len(files)
    hits = []                     # (id,url,date,dump,text) — 원문은 저장소 밖으로만
    web_pool = []                 # 무작위 웹 대조군 문장 풀(관찰)
    shard_table = {}
    rej_cnt = 0                   # R1 불통과 ∧ ≥300자 문서 계수(웹 대조군 분모)
    n_rg_fail, rg_fail_why = 0, {}
    for fp in files:
        w = load_gate("스캔 " + os.path.basename(fp))
        s_sha = sha16(fp)
        pf = pq.ParquetFile(fp)
        rows = hit_d = hit_c = fail = 0
        for rg in range(pf.metadata.num_row_groups):
            try:
                tbl = pf.read_row_group(rg, columns=["text", "url", "id", "date", "dump"])
                cols = {c: tbl.column(c).to_pylist()
                        for c in ("text", "url", "id", "date", "dump")}
            except Exception as e:
                fail += 1
                n_rg_fail += 1
                rg_fail_why[type(e).__name__] = rg_fail_why.get(type(e).__name__, 0) + 1
                continue
            for x, u, i_, dt, dp in zip(cols["text"], cols["url"], cols["id"],
                                        cols["date"], cols["dump"]):
                rows += 1
                if not x or len(x) < MIN_DOC_CHARS:
                    continue
                a, b = marker_hits(x)
                if a >= 1 and b >= 3:
                    hits.append((i_ or "", u or "", dt or "", dp or "", x))
                    hit_d += 1
                    hit_c += len(x)
                else:
                    rej_cnt += 1
                    if rej_cnt % WEB_EVERY == 0 and len(web_pool) < POOL_CAP:
                        for s in sentences_of(x):
                            if len(web_pool) >= POOL_CAP:
                                break
                            if hash_keep(s):
                                web_pool.append(s)
        shard_table[os.path.basename(fp)] = {
            "sha256/16": s_sha, "bytes": os.path.getsize(fp), "행": rows,
            "히트 문서": hit_d, "히트 문자": hit_c, "못 읽었다(행그룹)": fail,
            "load 대기": w}
        prog({"국면": "스캔", "샤드": os.path.basename(fp), "행": rows, "히트": hit_d,
              "누적 히트": len(hits), "웹풀": len(web_pool)})
    out["수집 표(25샤드 · 관찰 100칸)"] = shard_table
    raw_docs = len(hits)
    raw_chars = sum(len(h[4]) for h in hits)

    # 3) 정제 (사전등록 §2 순서 동결)
    load_gate("정제")
    doc_seen, para_seen = set(), set()
    n_docdup = docdup_chars = paradup_chars = n_lowq = lowq_chars = 0
    final = []                    # (id,url,date,dump,정제문)
    for i_, u, dt, dp, x in hits:
        h = hashlib.sha256(x.encode("utf-8")).hexdigest()
        if h in doc_seen:
            n_docdup += 1
            docdup_chars += len(x)
            continue
        doc_seen.add(h)
        cx, dupc = clean_doc(x, para_seen)
        paradup_chars += dupc
        if len(cx) < MIN_CLEAN_CHARS or hangul_ratio(cx) < MIN_HANGUL:
            n_lowq += 1
            lowq_chars += len(cx)
            continue
        final.append((i_, u, dt, dp, cx))
    final_chars = sum(len(f[4]) for f in final)
    drop_rate = (raw_chars - final_chars) / max(raw_chars, 1)
    out["정제 계수(관찰 8칸)"] = {
        "원시 히트 문서": raw_docs, "원시 히트 문자": raw_chars,
        "문서 정확 중복": n_docdup, "문서 중복 문자": docdup_chars,
        "문단 중복 제거 문자": paradup_chars, "저품질 폐기 문서": n_lowq,
        "최종 문서": len(final), "최종 문자": final_chars}
    prog({"국면": "정제", "원시": raw_docs, "최종": len(final),
          "폐기 비율": round(drop_rate, 4)})

    # 4) 토큰량 (base 토크나이저 — finetune.py 즉석 토큰화 미러)
    load_gate("토큰")
    from transformers import AutoModel, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(SNAP)
    T = 0
    doc_tokens = []
    for b0 in range(0, len(final), 128):
        ids = tok([f[4] for f in final[b0:b0 + 128]], add_special_tokens=False)["input_ids"]
        for x in ids:
            doc_tokens.append(len(x))
            T += len(x)
    out["토큰 계수(관찰 4칸)"] = {
        "합계 T": T, "문서 수": len(final),
        "문서당 중앙값": int(np.median(doc_tokens)) if doc_tokens else 0,
        "자/토큰 비": round(final_chars / max(T, 1), 4)}
    prog({"국면": "토큰", "T": T})

    # 5) G2 — 문장 표본 · OOD (serve 자구 미러 · base 공간)
    load_gate("임베딩")
    corp_pool = []
    for f in final:
        if len(corp_pool) >= POOL_CAP:
            break
        for s in sentences_of(f[4]):
            if len(corp_pool) >= POOL_CAP:
                break
            if hash_keep(s):
                corp_pool.append(s)
    out["문장 풀"] = {"코퍼스": len(corp_pool), "웹 대조군": len(web_pool)}
    g2_measured = len(corp_pool) >= N_SAMPLE
    web_measured = len(web_pool) >= N_SAMPLE

    z = np.load(os.path.join(TRI, "sao.npz"))
    split = z["split"]
    E = np.load(os.path.join(TRI, "text_emb_qwen05b.npz"))["E"].astype(np.float32)
    E_tr = E[np.where(split == 0)[0]]
    meta = [json.loads(l) for l in open(os.path.join(TRI, "meta.jsonl"), encoding="utf-8")]
    va = np.where(split == 1)[0]
    va_txts = sorted({(meta[int(i)].get("텍스트") or "").strip() for i in va} - {""})
    ind_idx = np.random.default_rng(IND_SEED).choice(len(va_txts), size=128, replace=False)
    ind_txt = [va_txts[int(j)] for j in ind_idx]
    plan_txt = [l.strip() for l in open(P_PLAN, encoding="utf-8") if l.strip()]
    far_txt = [l.strip() for l in open(P_FAR, encoding="utf-8") if l.strip()]

    enc = AutoModel.from_pretrained(SNAP, dtype=torch.float32).eval()
    refnn = ref_nn(E_tr)
    r_plan = ood_ratios(embed_texts_live(enc, tok, plan_txt), E_tr, refnn)
    r_ind = ood_ratios(embed_texts_live(enc, tok, ind_txt), E_tr, refnn)
    r_far = ood_ratios(embed_texts_live(enc, tok, far_txt), E_tr, refnn)

    a1 = abs(refnn - REF_NN_REG)
    a2 = abs(float(np.median(r_plan)) - C_PLAN)
    a3 = abs(float(np.median(r_ind)) - C_IND)
    anchors = {"A1 REF_NN": {"실측": refnn, "등록": REF_NN_REG, "|Δ|": a1, "통과": a1 <= ANCHOR_TOL},
               "A2 기획서 24문 중앙값": {"실측": float(np.median(r_plan)), "등록": C_PLAN,
                                     "|Δ|": a2, "통과": a2 <= ANCHOR_TOL},
               "A3 분포-안 128 중앙값": {"실측": float(np.median(r_ind)), "등록": C_IND,
                                     "|Δ|": a3, "통과": a3 <= ANCHOR_TOL}}
    anchors_ok = all(v["통과"] for v in anchors.values())
    out["앵커(자 재현 3칸 · «실행 간»)"] = anchors
    out["재현 관찰(앵커 아님)"] = {
        "원거리 20문 중앙값": float(np.median(r_far)),
        "기획서 SE": round(boot_se_median(r_plan, [STAT_SEED, 4]), 5),
        "분포-안 SE": round(boot_se_median(r_ind, [STAT_SEED, 4, 1]), 5)}
    prog({"국면": "앵커", "통과": anchors_ok,
          "REF_NN": round(refnn, 6), "기획서": round(float(np.median(r_plan)), 4)})

    m = m_web = None
    if g2_measured:
        rng_c = np.random.default_rng([STAT_SEED, 0])
        samp_c = [corp_pool[int(j)] for j in
                  rng_c.choice(len(corp_pool), size=N_SAMPLE, replace=False)]
        r_c = ood_ratios(embed_texts_live(enc, tok, samp_c), E_tr, refnn)
        m = float(np.median(r_c))
        out["코퍼스 표본 OOD(관찰 11칸)"] = ood_summary(r_c, boot_se_median(r_c, [STAT_SEED, 2]))
    if web_measured:
        rng_w = np.random.default_rng([STAT_SEED, 1])
        samp_w = [web_pool[int(j)] for j in
                  rng_w.choice(len(web_pool), size=N_SAMPLE, replace=False)]
        r_w = ood_ratios(embed_texts_live(enc, tok, samp_w), E_tr, refnn)
        m_web = float(np.median(r_w))
        out["무작위 웹 대조군 OOD(관찰 11칸)"] = ood_summary(r_w, boot_se_median(r_w, [STAT_SEED, 3]))
    if m is not None and m_web is not None:
        out["특이성 Δ_spec(관찰)"] = {
            "값": abs(m_web - C_PLAN) - abs(m - C_PLAN),
            "읽기": "> 0 이어야 필터가 문체를 갈랐다 — ≤ 0 이면 「특이성 없음」 낙인(게이트 아님)"}
    del enc
    prog({"국면": "OOD", "m": None if m is None else round(m, 4),
          "m_web": None if m_web is None else round(m_web, 4)})

    # 6) G3b 재검 — 최종 코퍼스 재주사(기계 검사)
    seen2, dup2 = set(), 0
    for f in final:
        for para in f[4].split("\n"):
            if len(para) >= PARA_DEDUP_MIN:
                h = hashlib.sha1(para.encode("utf-8")).hexdigest()
                if h in seen2:
                    dup2 += 1
                else:
                    seen2.add(h)

    # 7) 산출물 — corpus.jsonl · parquet · ledger (저장소 밖 · 원문은 여기에만)
    load_gate("산출")
    corp_jsonl = os.path.join(CORP, "corpus.jsonl")
    with open(corp_jsonl, "w", encoding="utf-8") as f:
        for i_, u, dt, dp, cx in final:
            f.write(json.dumps({"id": i_, "url": u, "date": dt, "dump": dp, "text": cx},
                               ensure_ascii=False) + "\n")
    pq_dir = os.path.join(CORP, "parquet")
    os.makedirs(pq_dir, exist_ok=True)
    corp_pq = os.path.join(pq_dir, "part-000.parquet")
    pq.write_table(pa.table({"text": [f[4] for f in final],
                             "url": [f[1] for f in final],
                             "id": [f[0] for f in final]}),
                   corp_pq, row_group_size=1000)
    rule_sha = hashlib.sha256(json.dumps(
        {"MARK_A": MARK_A, "MARK_B": MARK_B, "MIN_DOC_CHARS": MIN_DOC_CHARS,
         "MIN_CLEAN_CHARS": MIN_CLEAN_CHARS, "MIN_HANGUL": MIN_HANGUL,
         "PARA_DEDUP_MIN": PARA_DEDUP_MIN, "규칙": "A>=1 and B>=3"},
        ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    ledger = {
        "사전등록": "docs/탐색/1010.md", "러너": out["러너 자신"],
        "원천": [{
            "이름": "FineWeb2-ko (HuggingFaceFW/fineweb-2 · kor_Hang)",
            "종류": "공개 웹 코퍼스 로컬 미러(전량 스캔 · 신규 네트워크 요청 0)",
            "원천": "https://huggingface.co/datasets/HuggingFaceFW/fineweb-2",
            "라이선스": "ODC-By 1.0 (+ CommonCrawl Terms of Use)",
            "robots_이용규약_확인": ("CommonCrawl 크롤 시점 robots 존중(CC 규약) · 로컬 재사용 "
                                "· fetch 로그 fineweb955_fetch.jsonl sha 533e952a616c8db4 "
                                "(2026-08-13 25/25 검증 · 실패 0)"),
            "파일 sha 목록": {k: {"sha256/16": v["sha256/16"], "bytes": v["bytes"]}
                          for k, v in shard_table.items()},
            "수집 시각": {"원 다운로드": "2026-08-13 (fineweb955_fetch.jsonl)",
                      "이번 스캔": {"시작": 시작, "끝": now()}},
            "규칙 sha": rule_sha}],
        "불채택 후보(§0-㉱ 정찰 실측)": [
            {"이름": "bizinfo.go.kr 공개 RSS", "사유": "무열쇠 항목 0(「없다」 · 2026-08-23 15:30 실측)"},
            {"이름": "k-startup.go.kr", "사유": "robots Disallow: /webFSBIPBANC.do(공고 게시판) — 준수"},
            {"이름": "korea.kr", "사유": "「못 봤다」 — 보도자료체(표적 밖) · 규칙상 조회 안 함"}],
        "실패 3형(조항 59)": {
            "없다": {"R1 통과 0 샤드": sum(1 for v in shard_table.values() if v["히트 문서"] == 0),
                   "bizinfo 무열쇠 항목": 0},
            "못 봤다": {"불채택 라이브 후보": 3, "건너뛴 행그룹": 0},
            "못 읽었다": {"행그룹 오류": n_rg_fail, "사유별": rg_fail_why}},
        "정제": out["정제 계수(관찰 8칸)"], "토큰": out["토큰 계수(관찰 4칸)"]}
    ledger_p = os.path.join(CORP, "ledger.json")
    json.dump(ledger, open(ledger_p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    art_shas = {"corpus.jsonl": sha16(corp_jsonl), "parquet/part-000.parquet": sha16(corp_pq),
                "ledger.json": sha16(ledger_p)}
    with open(os.path.join(CORP, "sha256.txt"), "w", encoding="utf-8") as f:
        for k, v in sorted(art_shas.items()):
            f.write("%s  %s\n" % (v, k))
    out["산출물 sha(조항 73-마)"] = art_shas
    # G4 — 장부 필수 칸 기계 검사
    req = ("이름", "종류", "원천", "라이선스", "robots_이용규약_확인",
           "파일 sha 목록", "수집 시각", "규칙 sha")
    g4_missing = sum(1 for src in ledger["원천"] for k in req if not src.get(k))
    g4_missing += 0 if art_shas.get("corpus.jsonl") else 1

    # 관찰 — 도메인 상위 20 (집계만 · 제목·본문·개별 URL 없음)
    from urllib.parse import urlparse
    dom = {}
    for f in final:
        try:
            h = urlparse(f[1]).netloc
        except Exception:
            h = "(파싱 불가)"
        dom[h] = dom.get(h, 0) + 1
    out["도메인 상위 20(관찰)"] = dict(sorted(dom.items(), key=lambda kv: -kv[1])[:20])
    out["실패 3형(조항 59)"] = ledger["실패 3형(조항 59)"]

    # 8) 판정 — 비반올림 · 여유 게재(v5.3-4)
    gates = {}
    gates["G1 토큰량"] = {"실측": T, "문턱": ">= %d" % G1_MIN_TOKENS,
                       "여유": T - G1_MIN_TOKENS, "판": g1_pass(T)}
    if g2_measured:
        dp, di, df = abs(m - C_PLAN), abs(m - C_IND), abs(m - C_FAR)
        gates["G2 문체(주대비)"] = {
            "실측 m": m, "중심 거리": {"기획서": dp, "분포-안": di, "원거리": df},
            "문턱": "최근접 중심 = 기획서(동률 불통과)",
            "여유": min(di - dp, df - dp), "판": g2_pass(m)}
    else:
        gates["G2 문체(주대비)"] = {"판": False, "실측": "미측정(문장 풀 %d < %d)"
                                % (len(corp_pool), N_SAMPLE)}
    gates["G3a 폐기 비율"] = {"실측": drop_rate, "문턱": "<= %.2f" % G3A_MAX_DROP,
                          "여유": G3A_MAX_DROP - drop_rate, "판": g3a_pass(drop_rate)}
    gates["G3b 최종 중복 0"] = {"실측": dup2, "문턱": "== 0", "여유": -dup2, "판": g3b_pass(dup2)}
    gates["G4 장부 결측 0"] = {"실측": g4_missing, "문턱": "== 0", "여유": -g4_missing,
                           "판": g4_pass(g4_missing)}
    out["판정 게이트(5칸 · 비반올림)"] = gates
    out["연역 계수"] = {"값 연역 가능 칸": 0, "총 판정 칸": 5, "등록 시점 기대": "미지 — 판정 사이클"}

    allpass = all(g["판"] for g in gates.values())
    if not anchors_ok:
        verdict = "관찰 강등(승격 0) — 앵커 불통과(자 재현 실패 · 귀속은 §관찰)"
    elif allpass:
        verdict = "성공 — 코퍼스 성립 · ft-v2 큐 승격(§6 집행)"
    elif not gates["G2 문체(주대비)"]["판"]:
        verdict = "실패 — 문체 불성립(승격 0)"
    else:
        verdict = "부분(승격 0) — G2 통과 · 나머지 일부 불통과"

    # 9) 집행 (성공 시에만 · 사전등록 §6)
    집행 = {"hf 빌드": "미집행", "큐 승격": "미집행"}
    if verdict.startswith("성공"):
        try:
            load_gate("hf 빌드")
            got = sha16(FT_SLIM)
            assert got == "a9f55691c1acf83f", "🔴 slim sha 불일치: %s" % got
            from transformers import AutoModelForCausalLM
            sl = torch.load(FT_SLIM, map_location="cpu", weights_only=False)
            if not os.path.exists(os.path.join(HF_DIR, "config.json")):
                lm = AutoModelForCausalLM.from_pretrained(SNAP, dtype=torch.float32)
                lm.load_state_dict(sl["model"])
                lm.save_pretrained(HF_DIR, safe_serialization=True)
                tok.save_pretrained(HF_DIR)
                del lm
            lm2 = AutoModelForCausalLM.from_pretrained(HF_DIR, dtype=torch.float32)
            sd2 = lm2.state_dict()
            names = sorted(sl["model"].keys())[::30]
            eq = all(torch.equal(sd2[k], sl["model"][k]) for k in names)
            del lm2, sl
            집행["hf 빌드"] = {"경로": HF_DIR, "slim sha": got,
                           "재적재 검증(매 30번째 %d텐서 bitwise)" % len(names): eq}
            if not eq:
                raise RuntimeError("hf 재적재 검증 실패")
            steps = int(min(3000, max(500, round((4.0 * T / TOKENS_PER_STEP) / 50.0) * 50)))
            qcmd = ("cd /Users/ax/world_model && python3 pretrain/finetune.py "
                    "--model-dir %s --data-dir %s --name ft-v2 --steps %d "
                    "--micro-batch 2 --accum 16 --device mps" % (HF_DIR, pq_dir, steps))
            if m is not None and m_web is not None and \
                    (abs(m_web - C_PLAN) - abs(m - C_PLAN)) <= 0:
                qcmd = qcmd + "   # ⚠ 특이성 없음(§6-ⓐ 낙인)"
            lines = open(QUEUE, encoding="utf-8").read().split("\n")
            tgt = [i for i, l in enumerate(lines) if l.startswith(QLINE_PREFIX)]
            qstate = int(open(QSTATE).read().strip() or 0)
            if len(tgt) == 1 and (tgt[0] + 1) > qstate + 1:
                lines[tgt[0]] = qcmd
                tmp = QUEUE + ".tmp1010"
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                os.replace(tmp, QUEUE)
                집행["큐 승격"] = {"줄 번호": tgt[0] + 1, "queue.state": qstate,
                              "steps": steps, "명령": qcmd}
            else:
                집행["큐 승격"] = {"미집행 사유": "대상 줄 %d개 · state %d(검문 §6-2 위배)"
                              % (len(tgt), qstate)}
                verdict = "부분(집행 보류) — 코퍼스 성립 · 큐 검문 실패"
        except Exception as e:
            집행["오류"] = "%s: %s" % (type(e).__name__, e)
            verdict = "부분(빌드 실패) — 코퍼스 성립 · hf/큐 집행 실패(§6-1 재기재)"
    out["집행(관찰 3칸)"] = 집행

    # 조항 78 — 양쪽 신고
    out["조항 78(양쪽 신고)"] = {
        "원리상 못 통과시키는 입력": "E_tr 과 문자 그대로 중복인 문장 — 비율 0 → 분포-안 중심",
        "원리상 못 떨어뜨리는 입력": ("기획서가 아니어도 학습분포에서 6.5급 거리인 임의 한국어 "
                              "산문 — 무작위 웹 대조군 관찰이 이 결계를 잰다(Δ_spec)")}
    out["관찰 — 외삽 대 실측"] = {"§0-㉰ 외삽 문자(1샤드 50k 표본)": "약 55M",
                            "실측 원시 히트 문자": raw_chars}
    out["판정어"] = verdict
    out["총소요초"] = round(time.time() - t_all, 1)
    out["끝 시각"] = now()
    json.dump(out, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    prog({"국면": "끝", "판정어": verdict, "초": out["총소요초"]})


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = {"판정어": "중단 — 러너 예외(사유를 값으로 · 조항 59)",
               "예외": traceback.format_exc()[-3000:], "시각": now()}
        try:
            json.dump(err, open(OUT_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        finally:
            print(json.dumps(err, ensure_ascii=False), flush=True)
        raise
