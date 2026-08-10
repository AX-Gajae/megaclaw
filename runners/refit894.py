# -*- coding: utf-8 -*-
"""노트 894 갑 --- **수리의 효과를 캐시로 다시 재는 자**. 요청 0건.

티처 #56 이 893 에서 잡아낸 것 둘을 고쳤고(`runners/pilot893.py`), 여기서 그 효과를
**옛 캐시를 다시 접어** 잰다.

  ① `dcin()` 의 무결과 가드가 **반대 방향**이었다 --- `sch_result` **부재**를 '판정 불가'
     로 읽어 **'확인된 0' 을 '모른다' 로 강등**했다.
  ② 네이버 블로그 `제목` 이 3,568/3,568 전부 UI 문자열이었다.

🔴 **이 자의 한계를 먼저 적는다(사전등록에 그대로 있다).** `data/state/cache_p893` 은
**파싱된 결과만** 담고 **원본 HTML 을 안 담는다.** 그러므로 여기서 하는 것은 원본
재파싱이 **아니다**:

  ㄱ 디시: 실패 **사유 문자열**의 재분류다. 옛 가드가 던진 `ValueError` 는 **정의상**
    `sch_result` 부재를 뜻하므로 새 가드에서 어디로 가는지가 결정된다 --- 다만 새
    가드가 그것을 '확인된 0' 으로 보내려면 **그 응답에 `검색 결과가 없` 표지가 있었어야**
    하고, 그 전제는 캐시로는 못 본다. → `runners/knock894.py` 의 **P4 재요청 12건**이
    그 전제를 실측 검증한다. 검증 전까지 이 수는 **상한**이다.
  ㄴ 블로그: 잘린 120자 UI 문자열에서의 **제목 복구**다. 새 파서가 라이브에서 낼 제목과
    같다는 보장은 없다(잘림이 제목을 삼킨 항목이 있다) --- **복구 성공률을 병기**한다.

정밀도 대용의 정의는 `runners/diag893.py:115` 의 `prec()` 를 **글자 그대로** 가져왔다.
정의를 바꾸면 0.2087 과 비교할 수 없다.
"""
from __future__ import annotations

import datetime as dt
import json
import random
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")

ROOT = Path("/Users/ax/world_model")
CACHE = ROOT / "data/state/cache_p893"
OUT = ROOT / "runners/out894_refit.json"
DC_STEPS = ("디시최신", "디시정확")
ALL_STEPS = ("뉴스사전", "뉴스사후", "블로그사전", "블로그사후", "디시최신", "디시정확")

# 옛 가드가 던진 문장 --- 이 문장이면 `sch_result` 부재가 원인이다(코드가 그것만 검사했다)
OLD_DC_GUARD = "결과 컨테이너 없음"


# ── 정밀도 대용: diag893.prec() 와 **같은 정의** ──────────────────
def prec_one(q: str, title: str) -> bool:
    toks = [t for t in str(q).split() if len(t) >= 2]
    return bool(q in title or (toks and all(k in title for k in toks)))


# ── 블로그 제목 복구(캐시 전용) ─────────────────────────────────
KEEP, NEWWIN = "Keep에 바로가기", "새 창 열림"


def recover_title(ui: str) -> tuple[str, str]:
    s = ui
    src = "복구 실패(표지 없음)"
    if KEEP in s:
        s = s.split(KEEP)[-1]
        src = "복구"
    parts = [p.strip() for p in s.replace(NEWWIN, "\x00").split("\x00") if p.strip()]
    if not parts:
        return "", "복구 실패(표지 뒤가 빔)"
    return parts[0][:120], src


def boot_ratio(hit: int, n: int, B: int = 10000, seed: int = 894) -> list:
    """비율의 부트 구간(티처 #56 M4 --- 점추정만 내지 마라)."""
    if not n:
        return [None, None]
    rng = random.Random(seed)
    xs = [1] * hit + [0] * (n - hit)
    es = sorted(sum(xs[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return [round(es[int(0.025 * B)], 4), round(es[int(0.975 * B)], 4)]


def main():
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(CACHE.glob("*.json"))]
    ok = [r for r in rows if r.get("ok")]
    real = [r for r in ok if not r["key"].startswith("FAKE")]
    fake = [r for r in ok if r["key"].startswith("FAKE")]

    # ── ① 디시 가드 재해석 ──────────────────────────────────────
    old = Counter()
    new = Counter()
    dc_fail = Counter()
    reclass_q = []                       # P4 재요청 후보(질의·정렬)
    for r in real:
        st = r.get("단계별", {})
        er = r.get("실패단계", {})
        for s in ALL_STEPS:
            v = st.get(s)
            lab = "항목" if isinstance(v, int) else str(v)
            old[(s, lab)] += 1
            if s in DC_STEPS and lab == "판정 불가":
                why = er.get(s, "")
                dc_fail[why.split(":")[0]] += 1
                if OLD_DC_GUARD in why:
                    new[(s, "확인된 0(894 재분류)")] += 1
                    reclass_q.append({"질의": r["질의"], "정렬": s})
                else:
                    new[(s, "판정 불가")] += 1
            else:
                new[(s, lab)] += 1

    def acc(c):
        n_undec = sum(v for (s, l), v in c.items() if l == "판정 불가")
        return {"총 단계": sum(c.values()), "판정 불가": n_undec,
                "잰 것": sum(c.values()) - n_undec,
                "판정 불가 비율": round(n_undec / max(1, sum(c.values())), 4)}

    dc_old = sum(v for (s, l), v in old.items() if s in DC_STEPS and l == "판정 불가")
    dc_new = sum(v for (s, l), v in new.items() if s in DC_STEPS and l == "판정 불가")
    guard = {
        "🔴 디시 판정 불가": {"수리 전": dc_old, "수리 후": dc_new,
                       "재분류된 것(확인된 0 으로)": len(reclass_q),
                       "남은 판정 불가의 사유": dict(dc_fail)},
        "실물 1,200 단계 회계": {"수리 전": acc(old), "수리 후": acc(new)},
        "단계별(수리 후)": {s: {l: v for (ss, l), v in sorted(new.items()) if ss == s}
                     for s in ALL_STEPS},
        # 🔴 895 정정(티처 #57 C4). 이 칸은 **사전등록 시점의 문장**이었고 그 뒤 P4 가
        # 실측했는데 산출물이 갱신되지 않아 **반대로 적힌 채 남아 있었다**. 원장·논문·
        # 카드는 '실측' 이라 적었다 --- 산출물만 옛말을 이고 있었다.
        "🔴 이 수의 지위": ("**검증됐다(단 하한이 있다).** 사전등록 시점엔 상한이었다 --- 옛 "
                     "`ValueError` 가 새 가드에서 '확인된 0' 이 되려면 그 응답에 `검색 결과가 "
                     "없` 표지가 있었어야 하는데 캐시에 원본 HTML 이 없었기 때문이다. "
                     "`knock894.py` 의 P4 가 재요청 **12건 → 무결과 표지 12/12** 로 그 전제를 "
                     "실측했다. 🔴 다만 `boot_ratio(12,12)=[1.0,1.0]` 은 **퇴화**이므로 "
                     "정직한 구간은 **Clopper-Pearson 하한 0.7354**(Wilson 0.7575)이고, "
                     "그것을 옮기면 디시 판정 불가 **3 [3, 39]** · 실물 1,200단계 "
                     "**236 [236, 272] = 19.67% [19.67%, 22.67%]** 다."),
    }

    # ── ② 실패 회계에서 상태 코드 되찾기 ────────────────────────
    codes = Counter()
    for r in real + fake:
        for s, why in r.get("실패단계", {}).items():
            m = re.search(r"HTTP Error (\d{3})", why)
            src = ("뉴스" if s.startswith("뉴스") else
                   "블로그" if s.startswith("블로그") else "디시")
            codes[f"{src}:{m.group(1) if m else why.split(':')[0]}"] += 1

    # ── ③ 블로그 제목 복구 + 정밀도 대용 ────────────────────────
    def prec_table(rs, use_recovered):
        num, den = Counter(), Counter()
        for r in rs:
            q = r["질의"]
            for x in r["항목"]:
                src = x["원천"]
                t = x.get("제목", "")
                if use_recovered and src == "블로그":
                    t, _ = recover_title(t)
                den[src] += 1
                if prec_one(q, t):
                    num[src] += 1
        tab = {k: {"항목": den[k], "질의 전부 포함": num[k],
                   "비율": round(num[k] / den[k], 4),
                   "부트 95%": boot_ratio(num[k], den[k])} for k in sorted(den)}
        N, H = sum(den.values()), sum(num.values())
        tab["전체"] = {"항목": N, "질의 전부 포함": H, "비율": round(H / N, 4),
                     "부트 95%": boot_ratio(H, N)}
        return tab

    blog_items = [x for r in real for x in r["항목"] if x["원천"] == "블로그"]
    rec = [recover_title(x["제목"]) for x in blog_items]
    recov = {"분모(실물 블로그 항목)": len(blog_items),
             "복구 출처": dict(Counter(s for _, s in rec)),
             "복구 성공률": round(sum(1 for t, s in rec if s == "복구" and t) / max(1, len(rec)), 4),
             "복구 제목 길이 중앙값": sorted(len(t) for t, _ in rec)[len(rec) // 2] if rec else None,
             "옛 제목 길이 중앙값": sorted(len(x["제목"]) for x in blog_items)[len(blog_items) // 2],
             "예시": [{"옛": x["제목"][:110], "복구": recover_title(x["제목"])[0]}
                    for x in blog_items[:4]]}

    p_before, p_after = prec_table(real, False), prec_table(real, True)
    f_before, f_after = prec_table(fake, False), prec_table(fake, True)

    # ── ④ 유효 수확(= 정밀도 통과 항목 수) --- 🔴 **사후 탐색**이다(사전등록에 없다)
    # 893 의 G2 는 '수확' 을 셌고 음성 통제가 그것을 무효로 만들었다. 다음 관문은
    # 「매칭 자」이므로, 제목을 고친 지금 **유효 수확**이 실물과 음성을 가르는지 본다.
    def eff(rs, use_recovered):
        per = []
        for r in rs:
            q, n = r["질의"], 0
            for x in r["항목"]:
                t = x.get("제목", "")
                if use_recovered and x["원천"] == "블로그":
                    t, _ = recover_title(t)
                n += prec_one(q, t)
            per.append((r.get("질의출처"), n))
        xs = sorted(n for _, n in per)
        med = xs[len(xs) // 2] if xs else None
        by = {}
        for s in sorted({s for s, _ in per if s}):
            ys = sorted(n for ss, n in per if ss == s)
            by[s] = {"n": len(ys), "중앙값": ys[len(ys) // 2], "0건": sum(1 for y in ys if y == 0)}
        return {"n": len(xs), "중앙값": med, "평균": round(sum(xs) / len(xs), 2) if xs else None,
                "75분위": xs[int(0.75 * len(xs))] if xs else None,
                "0건": sum(1 for x in xs if x == 0), "질의출처별": by}

    effect = {
        "🔴 이것은 사후 탐색이다": "사전등록에 없다. 다음 사이클의 「매칭 자」 사전등록 재료로만 쓴다.",
        "실물 · 수리 전": eff(real, False), "실물 · 수리 후": eff(real, True),
        "음성 · 수리 전": eff(fake, False), "음성 · 수리 후": eff(fake, True),
    }
    mr = effect["실물 · 수리 후"]["중앙값"]
    mf = effect["음성 · 수리 후"]["중앙값"]
    effect["🔴 음성/실물 비(유효 수확 · 수리 후)"] = {
        "중앙값 비": (round(mf / mr, 4) if mr else None),
        "🔴 왜 None 인가": ("**실물의 중앙값도 0** 이기 때문이다(200 중 136 작품이 유효 수확 0). "
                     "분모가 0 이면 비는 없다 --- '0 이다' 라고 적으면 거짓말이다."),
        "평균 비": (round(effect["음성 · 수리 후"]["평균"] / effect["실물 · 수리 후"]["평균"], 4)
                 if effect["실물 · 수리 후"]["평균"] else None),
    }
    effect["읽는 법"] = ("893 의 G2 는 **날 수확**을 셌고 음성 통제가 실물의 74% 를 긁어 "
                     "무효가 됐다. 제목을 고치고 **유효 수확**으로 다시 세면 이 비가 어떻게 "
                     "되는지가 다음 사이클 「매칭 자」의 출발점이다.")

    out = {
        "무엇": "노트 894 --- 수리 둘의 효과를 옛 캐시로 다시 잰다. **요청 0건**",
        "🔴 ④ 유효 수확(사후 탐색)": effect,
        "시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "git HEAD": subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "분모": {"캐시 파일": len(rows), "ok": len(ok), "실물": len(real), "음성": len(fake)},
        "🔴 ① 디시 가드 뒤집기": guard,
        "🔴 ② 실패 회계 --- 되찾은 상태 코드(캐시 사유 문자열에서)": dict(codes),
        "🔴 ③ 블로그 제목 복구": recov,
        "🔴 ③ 정밀도 대용(정의는 diag893.prec 그대로)": {
            "실물 · 수리 전": p_before, "실물 · 수리 후": p_after,
            "음성 · 수리 전": f_before, "음성 · 수리 후": f_after,
        },
        "재분류 후보(P4 표본 모집단)": {"n": len(reclass_q),
                              "서로 다른 질의": len({d["질의"] for d in reclass_q})},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in out if k.startswith("🔴")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
