# -*- coding: utf-8 -*-
"""프로브 오염 검사 1010 — 티처 #143 ⑥-1 ㉰ 이행 (등록-후 추가 검사 — 조타수 지시 · 관찰 전용).

정의(이 파일이 실행 «전» 커밋된다 — 값 보고 규칙 못 바꾼다):
  · 대상: ft2_corpus/corpus.jsonl (sha 실측 게재) ↔ probe1009_기획서.txt 24문 ·
    probe1009_원거리.txt 20문 (sha 대조).
  · 검사 1 「원문 포함」: NFC 정규화 후 프로브 문장 «그대로» 를 부분문자열로 담은 문서 수.
  · 검사 2 「10-gram 공유」: 프로브의 문자 10-gram(정확 일치 · NFC)을 하나라도 담은 문서 수 ·
    공유 gram 종수 · 프로브별 공유 gram 수.
  · 🔴 행동 규칙(사전 고정): 검사 1 > 0 이면 그 문서를 코퍼스에서 «제거»하고 parquet 재생성 +
    토큰 재계수 후 두 판(제거 전/후)을 나란히 게재. 검사 2 만 걸린 문서는 유지(우연 공유 —
    수만 게재). ft-v2 판정용 «새» 프로브는 아직 없다 — 그 검사는 ft-v2 판정 사이클 몫(승계 조건).
쓰는 법: python3 runners/probeclean1010.py   → runners/out1010_probeclean.json
"""
import hashlib, json, os, time, unicodedata
import numpy as np

REPO = "/Users/ax/world_model"
CORP = "/Users/ax/wm_harvest/foundation/ft2_corpus"
P_PLAN = os.path.join(REPO, "data", "probe1009_기획서.txt")
P_FAR = os.path.join(REPO, "data", "probe1009_원거리.txt")
OUT = os.path.join(REPO, "runners", "out1010_probeclean.json")
N = 10

def sha16(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()[:16]

def grams_of(s):
    return {s[i:i + N] for i in range(len(s) - N + 1)} if len(s) >= N else set()

def main():
    t0 = time.time()
    plan = [unicodedata.normalize("NFC", l.strip()) for l in open(P_PLAN, encoding="utf-8") if l.strip()]
    far = [unicodedata.normalize("NFC", l.strip()) for l in open(P_FAR, encoding="utf-8") if l.strip()]
    sets = {"기획서": plan, "원거리": far}
    gram2probe = {}
    for name, ps in sets.items():
        for pi, p in enumerate(ps):
            for g in grams_of(p):
                gram2probe.setdefault(g, []).append((name, pi))
    G = sorted(gram2probe)
    P = (np.uint64(1099511628211) ** np.arange(N, dtype=np.uint64))
    def h64(txt):
        a = np.frombuffer(txt.encode("utf-32-le"), dtype=np.uint32)
        if len(a) < N:
            return None, None
        W = np.lib.stride_tricks.sliding_window_view(a, N).astype(np.uint64)
        return (W * P[None, :]).sum(axis=1, dtype=np.uint64), a
    Hs = np.sort(np.array([h64(g)[0][0] for g in G], dtype=np.uint64))
    res = {n: {"원문 포함 문서": 0, "원문 포함 프로브(중복 없이)": set(),
               "10gram 공유 문서": 0, "공유 gram 종수": set(),
               "프로브별 공유 gram 수": [0] * len(sets[n])} for n in sets}
    bad_doc_idx = []
    n_docs = 0
    with open(os.path.join(CORP, "corpus.jsonl"), encoding="utf-8") as f:
        for li, line in enumerate(f):
            d = json.loads(line)
            txt = unicodedata.normalize("NFC", d["text"])
            n_docs += 1
            hv, _ = h64(txt)
            if hv is None:
                continue
            idx = np.searchsorted(Hs, hv)
            idx[idx >= len(Hs)] = len(Hs) - 1
            cand = np.nonzero(Hs[idx] == hv)[0]
            hit_names = set()
            for ci in cand:
                g = txt[int(ci):int(ci) + N]
                if g in gram2probe:
                    for (name, pi) in gram2probe[g]:
                        if g not in res[name]["공유 gram 종수"]:
                            res[name]["프로브별 공유 gram 수"][pi] += 0  # 종수는 아래서
                        res[name]["공유 gram 종수"].add(g)
                        hit_names.add(name)
            for name in hit_names:
                res[name]["10gram 공유 문서"] += 1
            for name, ps in sets.items():
                for pi, p in enumerate(ps):
                    if p in txt:
                        res[name]["원문 포함 문서"] += 1
                        res[name]["원문 포함 프로브(중복 없이)"].add(pi)
                        bad_doc_idx.append(li)
    for name, ps in sets.items():
        cnt = [0] * len(ps)
        for g in res[name]["공유 gram 종수"]:
            for (n2, pi) in gram2probe[g]:
                if n2 == name:
                    cnt[pi] += 1
        res[name]["프로브별 공유 gram 수"] = cnt
        res[name]["공유 gram 종수"] = len(res[name]["공유 gram 종수"])
        res[name]["원문 포함 프로브(중복 없이)"] = sorted(res[name]["원문 포함 프로브(중복 없이)"])
    out = {"러너 자신": sha16(os.path.abspath(__file__)),
           "정의": "문자 10-gram 정확 일치(NFC) · 원문 포함 = 프로브 문장 부분문자열",
           "대상 sha": {"corpus.jsonl": sha16(os.path.join(CORP, "corpus.jsonl")),
                      "probe1009_기획서": sha16(P_PLAN), "probe1009_원거리": sha16(P_FAR)},
           "문서 수": n_docs, "검사": res,
           "행동 규칙 발화(원문 포함 문서 목록 — 제거 대상)": sorted(set(bad_doc_idx)),
           "초": round(time.time() - t0, 1), "시각": time.strftime("%Y-%m-%dT%H:%M:%S")}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ("문서 수", "검사", "초")}, ensure_ascii=False))

if __name__ == "__main__":
    main()
