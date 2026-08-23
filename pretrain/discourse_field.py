# -*- coding: utf-8 -*-
"""L1 담론 장 인코더 — 개체 장 Φ_ent · 배경 장 Φ_bg · 망각 상태 s_disc · 관심 점유율 SoV.

정본: docs/아키텍처_결정기.md §L1 (L1-1~L1-4) · 사전등록 docs/탐색/1019.md §2.
  · L1-3 망각: s_disc(e,t,τ) = Σ w(t−pub)·emb / Σw · w(Δ)=2^(−Δ/τ) ·
    τ 격자 {30,90,180,365} 사전 고정 · 정본 τ=90.
  · L1-2 SoV(e,t,τ) = W_ent / (W_ent + W_bg) — 가중 계수(전 매칭 문서 · 임베딩 표본 아님).
  · 🔴 매 호출 leak_guard 내장(L0-3): as_of 이전 발행 문서만 선택한 «뒤에도» 선택 전수를
    `assert_no_leak` 에 통과시킨다 — 관문이 실측 스탬프를 반환해야 값이 선다.

저장소(store) 계약 — /Users/ax/wm_harvest/foundation/l1_discourse/:
  docs_ent.jsonl.gz : {"key","published_at","원천","names":[…],"emb":int(-1=미임베딩)}
  docs_bg.jsonl.gz  : {"key","published_at","원천","kw":[…],"emb":int}
  emb_ent.npz / emb_bg.npz : "emb" float32 (n×896) — 행 번호 = docs 의 emb 필드.

씀(L3 백도어·해저드가 임포트하는 API):
    from pretrain.discourse_field import DiscourseField, TAUS, TAU_CANON
    f = DiscourseField.load()                          # 기본 store
    vec, meta = f.s_disc("이름", "2025-03-01", 90)      # vec: (896,) float32 | None(문서 0)
    sov, meta = f.sov("이름", "2025-03-01", 90)         # sov: float | None(분모 0)
    bgv, meta = f.s_bg("2025-03-01", 90)
meta["누수관문(L0-3)"] 이 실측 스탬프다(부칙 4 미러 — 게재는 이 반환값으로).

임베딩 규약(«같은 자» — text_emb_qwen05b.config.json 미러): Qwen2.5-0.5B base 스냅숏 ·
last_hidden_state attention-mask 평균 · 최대 96토큰 · 배치 32 · float32 · CPU
(threads 는 사이클 제약으로 4). `embed_texts()` 가 이 규약의 유일한 구현이다.

자기시험: python3 pretrain/discourse_field.py   (가중·SoV·누수 참/거짓 — 합성 store)
"""
import datetime as _dt
import gzip
import json
import math
import os

import numpy as np

from pretrain.leak_guard import assert_no_leak, LeakDetected  # noqa: F401 (재수출)

TAUS = (30, 90, 180, 365)          # L1-3 사전 고정 격자
TAU_CANON = 90                     # 정본 τ (사전 지정)
STORE_DEFAULT = "/Users/ax/wm_harvest/foundation/l1_discourse"
QWEN_SNAPSHOT = ("/Users/ax/.cache/huggingface/hub/models--Qwen--Qwen2.5-0.5B/"
                 "snapshots/060db6499f32faf8b98477b0a26969ef7d8b9987")
EMB_DIM = 896
EMB_MAX_TOKENS = 96
EMB_BATCH = 32
EMB_TEXT_CHARS = 500               # §1-4 텍스트 구성(앞 500자)


def weight(delta_days, tau):
    """L1-3 망각 가중 w(Δ)=2^(−Δ/τ). Δ ≥ 1 (published_at < as_of 자격 뒤에만 호출)."""
    return 2.0 ** (-float(delta_days) / float(tau))


def _pdate(s):
    if isinstance(s, _dt.date):
        return s
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except ValueError:
        return None


def _read_jsonl_gz(path):
    out = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


class DiscourseField(object):
    """담론 장 — 문서 메타 + 임베딩 위의 s_disc·SoV·s_bg (매 호출 leak_guard)."""

    def __init__(self, ent_docs, bg_docs, emb_ent, emb_bg):
        self.emb_ent = emb_ent
        self.emb_bg = emb_bg
        self.by_name = {}
        for d in ent_docs:
            pub = _pdate(d.get("published_at"))
            if pub is None:
                continue          # 발행일 없는 문서는 장에 못 선다(적재 단계에서 걸렀어야 함)
            row = (pub, d.get("key"), int(d.get("emb", -1)))
            for nm in d.get("names") or ():
                self.by_name.setdefault(nm, []).append(row)
        for rows in self.by_name.values():
            rows.sort()
        self.bg_rows = []
        for d in bg_docs:
            pub = _pdate(d.get("published_at"))
            if pub is None:
                continue
            self.bg_rows.append((pub, d.get("key"), int(d.get("emb", -1))))
        self.bg_rows.sort()

    # ── 적재 ──────────────────────────────────────────────────────────
    @classmethod
    def load(cls, store=STORE_DEFAULT):
        ent = _read_jsonl_gz(os.path.join(store, "docs_ent.jsonl.gz"))
        bg = _read_jsonl_gz(os.path.join(store, "docs_bg.jsonl.gz"))
        ee = np.load(os.path.join(store, "emb_ent.npz"))["emb"]
        eb = np.load(os.path.join(store, "emb_bg.npz"))["emb"]
        return cls(ent, bg, ee, eb)

    # ── 내부: as_of 로 자르고 관문 통과 ───────────────────────────────
    @staticmethod
    def _cut(rows, as_of_d, tag):
        sel = [r for r in rows if r[0] < as_of_d]
        stamp = assert_no_leak(
            [{"id": k, "published_at": p.isoformat()} for (p, k, _e) in sel],
            as_of_d, tag)
        return sel, stamp

    # ── L1-3 s_disc ───────────────────────────────────────────────────
    def s_disc(self, entity, as_of, tau=TAU_CANON):
        as_of_d = _pdate(as_of)
        if as_of_d is None:
            raise ValueError("as_of 를 날짜로 못 읽었다: %r" % (as_of,))
        rows = self.by_name.get(entity, [])
        sel, stamp = self._cut(rows, as_of_d, "L1-3 s_disc e=%s as_of=%s τ=%s"
                               % (entity, as_of_d, tau))
        emb_rows = [(p, e) for (p, _k, e) in sel if e >= 0]
        meta = {"n_pre": len(sel), "n_emb": len(emb_rows),
                "W_pre": sum(weight((as_of_d - p).days, tau) for (p, _k, _e) in sel),
                "누수관문(L0-3)": stamp}
        if not emb_rows:
            return None, meta                     # «없음» — 0 벡터 저장 금지(조항 59 형)
        w = np.array([weight((as_of_d - p).days, tau) for (p, _e) in emb_rows],
                     dtype=np.float64)
        V = self.emb_ent[[e for (_p, e) in emb_rows]].astype(np.float64)
        vec = (w[:, None] * V).sum(axis=0) / w.sum()
        meta["W_emb"] = float(w.sum())
        return vec.astype(np.float32), meta

    # ── 배경 장 s_bg ──────────────────────────────────────────────────
    def s_bg(self, as_of, tau=TAU_CANON):
        as_of_d = _pdate(as_of)
        sel, stamp = self._cut(self.bg_rows, as_of_d, "L1-1 s_bg as_of=%s τ=%s"
                               % (as_of_d, tau))
        emb_rows = [(p, e) for (p, _k, e) in sel if e >= 0]
        meta = {"n_pre": len(sel), "n_emb": len(emb_rows), "누수관문(L0-3)": stamp}
        if not emb_rows:
            return None, meta
        w = np.array([weight((as_of_d - p).days, tau) for (p, _e) in emb_rows],
                     dtype=np.float64)
        V = self.emb_bg[[e for (_p, e) in emb_rows]].astype(np.float64)
        vec = (w[:, None] * V).sum(axis=0) / w.sum()
        meta["W_emb"] = float(w.sum())
        return vec.astype(np.float32), meta

    # ── L1-2 SoV ──────────────────────────────────────────────────────
    def sov(self, entity, as_of, tau=TAU_CANON):
        as_of_d = _pdate(as_of)
        rows = self.by_name.get(entity, [])
        sel_e, st_e = self._cut(rows, as_of_d, "L1-2 SoV(ent) e=%s as_of=%s τ=%s"
                                % (entity, as_of_d, tau))
        sel_b, st_b = self._cut(self.bg_rows, as_of_d, "L1-2 SoV(bg) as_of=%s τ=%s"
                                % (as_of_d, tau))
        W_e = sum(weight((as_of_d - p).days, tau) for (p, _k, _x) in sel_e)
        W_b = sum(weight((as_of_d - p).days, tau) for (p, _k, _x) in sel_b)
        meta = {"W_ent": W_e, "W_bg": W_b, "n_ent": len(sel_e), "n_bg": len(sel_b),
                "누수관문(L0-3)": {"ent": st_e, "bg": st_b}}
        if W_e + W_b <= 0.0:
            return None, meta                     # 분모 0 = null + 지시자(조항 59 형)
        return W_e / (W_e + W_b), meta


# ── 임베딩 (규약 미러 — text_emb_qwen05b.config.json «같은 자») ──────────

def embed_texts(texts, threads=4, snapshot=QWEN_SNAPSHOT, log=None):
    """텍스트 목록 → (n×896) float32. last_hidden_state attention-mask 평균 ·
    최대 96토큰 · 배치 32 · CPU float32 (규약 미러 — threads 만 사이클 제약 4)."""
    import torch
    from transformers import AutoModel, AutoTokenizer
    torch.set_num_threads(int(threads))
    tok = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
    model = AutoModel.from_pretrained(snapshot, local_files_only=True,
                                      torch_dtype=torch.float32)
    model.eval()
    out = np.zeros((len(texts), EMB_DIM), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(texts), EMB_BATCH):
            chunk = [t[:EMB_TEXT_CHARS] if t else " " for t in texts[i:i + EMB_BATCH]]
            enc = tok(chunk, padding=True, truncation=True,
                      max_length=EMB_MAX_TOKENS, return_tensors="pt")
            h = model(**enc).last_hidden_state                     # (b, L, 896)
            m = enc["attention_mask"].unsqueeze(-1).to(h.dtype)    # (b, L, 1)
            v = (h * m).sum(dim=1) / m.sum(dim=1).clamp(min=1.0)
            out[i:i + len(chunk)] = v.numpy().astype(np.float32)
            if log and (i // EMB_BATCH) % 40 == 0:
                log("  임베딩 %d/%d" % (i, len(texts)))
    return out


# ── 자기시험 (합성 store — 참/거짓 양쪽 · 조항 66 방향 탐침 형) ──────────

def selftest():
    d0 = _dt.date(2025, 1, 1)
    ent = [{"key": "a", "published_at": "2024-12-02", "names": ["갑"], "emb": 0},   # Δ=30
           {"key": "b", "published_at": "2024-10-03", "names": ["갑"], "emb": 1},   # Δ=90
           {"key": "c", "published_at": "2025-06-01", "names": ["갑"], "emb": 2},   # 미래(잘려야)
           {"key": "d", "published_at": "2024-12-22", "names": ["을"], "emb": -1}]  # 미임베딩
    bg = [{"key": "x", "published_at": "2024-12-02", "kw": ["웹툰"], "emb": 0},
          {"key": "y", "published_at": "2024-07-05", "kw": ["굿즈"], "emb": 1}]
    ee = np.zeros((3, EMB_DIM), dtype=np.float32)
    ee[0, 0] = 1.0
    ee[1, 1] = 1.0
    ee[2, 2] = 100.0
    eb = np.zeros((2, EMB_DIM), dtype=np.float32)
    f = DiscourseField(ent, bg, ee, eb)
    r = {"자기시험": "pretrain/discourse_field.py", "경우": []}
    ok = True

    def case(name, good, detail=""):
        nonlocal ok
        ok = ok and bool(good)
        r["경우"].append({"이름": name, "기대대로": bool(good), "상세": str(detail)[:160]})

    # ① 가중 산식 — τ=30: w(30)=1/2 · w(90)=1/8 → s_disc[0]=(1/2)/(5/8)=0.8
    vec, meta = f.s_disc("갑", d0, 30)
    case("① s_disc 가중(τ=30)", vec is not None and abs(vec[0] - 0.8) < 1e-6
         and abs(vec[1] - 0.2) < 1e-6, vec[:3] if vec is not None else None)
    # ② 미래 문서(c)가 잘렸는가 — 성분 2 는 0 이어야
    case("② as_of 이후 문서 배제", vec is not None and abs(vec[2]) < 1e-9)
    # ③ 스탬프가 실측인가
    case("③ 누수 스탬프", meta["누수관문(L0-3)"]["판정"] == "통과"
         and meta["누수관문(L0-3)"]["n_입력"] == 2)
    # ④ 문서 0 개체 → None + 지시자 재료
    v2, m2 = f.s_disc("병", d0, 90)
    case("④ 무문서 = None", v2 is None and m2["n_pre"] == 0)
    # ⑤ 을 — 매칭 1·임베딩 0 → None 인데 n_pre=1
    v3, m3 = f.s_disc("을", d0, 90)
    case("⑤ 미임베딩만 = None·n_pre=1", v3 is None and m3["n_pre"] == 1)
    # ⑥ SoV — τ=30: W_ent(갑)=0.625 · W_bg=0.5+2^(-180/30)=0.515625
    s, m4 = f.sov("갑", d0, 30)
    exp = 0.625 / (0.625 + 0.515625)
    case("⑥ SoV 산식", s is not None and abs(s - exp) < 1e-9, s)
    # ⑦ 거짓 쪽 — 손상 store(발행일 null 이 잘림 단계 뒤 침투)를 관문이 막는가
    try:
        assert_no_leak([{"id": "z", "published_at": None}], d0, "selftest-거짓")
        case("⑦ null 침투 시 LeakDetected", False)
    except LeakDetected:
        case("⑦ null 침투 시 LeakDetected", True)
    r["전부_기대대로"] = ok
    return r


if __name__ == "__main__":
    import sys
    res = selftest()
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if res["전부_기대대로"] else 1)
