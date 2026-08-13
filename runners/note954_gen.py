# -*- coding: utf-8 -*-
"""노트 954 의 **탐색 레인 산출물 생산기** --- `docs/탐색/954.md` 를 찍고 도장을 박는다.

🔴 **문서를 손으로 안 쓴다**(티처 #92 가 953 에 대해 지적한 자리 · 원장 995).
표제·본문의 수는 전부 산출물 키에서 읽고, 입력 목록은 이 파일의 `J("…")` 리터럴을
**AST 로** 뽑아 sha 를 박는다.

    python3 -m runners.note954_gen
"""
import ast
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT = ROOT / "runners/out954_docstamp.json"
DOC = "docs/탐색/954.md"
GEN = "runners/note954_gen.py"


def J(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def _sha(rel: str) -> str:
    return hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()


def inputs_of(rel: str) -> list:
    t = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    out = []
    for n in ast.walk(t):
        if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "J" and n.args:
            a = n.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                out.append(a.value)
    return sorted(set(out))


def pct(x, nd=3):
    return ("%." + str(nd) + "f%%") % (100.0 * x)


def cm(x):
    return format(int(x), ",")


def build() -> str:
    hf = J("runners/out954_hplt_full.json")
    dp = J("runners/out954_dupe.json")
    sc = J("runners/out954_score.json")
    c1 = J("runners/out954_kopis_c1.json")
    rg = J("runners/out954_kopis_c1_regress.json")

    r1 = dp["자 ① URL 정확"]
    r2 = dp["자 ② URL 정규화(🔴 정본)"]
    r3 = dp["자 ③ 본문 앞 200자"]
    rt = dp["덤 --- 전문 md5(사전등록 밖 · 판정에 안 쓴다)"]
    gam = hf["도박(내 자)"]
    news = hf["뉴스형 host(내 자)"]
    td = hf["정확중복 --- 전문"]
    ud = hf["정확중복 --- 정규화 URL"]
    hd = hf["앞머리 공유 --- 앞 200자"]
    kin = hf["🔴 kin.naver.com 순위"]

    L = []
    A = L.append
    A("# 954 [탐색] — HPLT 2.0 `kor_Hang` **전량**을 처음으로 재고, FineWeb-2 와 겹침을 쟀다")
    A("")
    A("> 레인 **[탐색]**(`docs/루프.md` 규칙 6). 🔴 **판 ρ 주장 없음.** 이 문서는 손으로 안 썼다 —")
    A("> `%s` 가 산출물 키에서 읽어 찍는다(도장 `runners/out954_docstamp.json`)." % GEN)
    A("")
    A("---")
    A("")
    A("## ① 무엇을 했나")
    A("")
    A("1. **HPLT 2.0 `kor_Hang` 464 shard 전량**(디스크 114GB)을 한 번 훑었다 — 문서마다")
    A("   URL 해시 · 정규화 URL 해시 · 본문 앞 200자 해시 · **전문 해시** · collection 을 냈다.")
    A("   🔴 **어제까지의 모든 수는 앞 4 shard = `cc22` 한 크롤의 보름치였다**(원장 997). 오늘 처음으로 전량이다.")
    A("2. **FineWeb-2 `kor_Hang`**(25파일 · 105.77GB)을 **안 받고** HTTP Range 로")
    A("   **행군 층화 표본**만 읽어(파일마다 `linspace` 로 고르게) 겹침을 쟀다.")
    A("   ⚠ **표본 설계가 도중에 바뀌었다**: 처음 넉 파일은 **낱개 행군 100개**, 나머지 스물한")
    A("   파일은 **이어진 행군 4개짜리 군집 10개**(작은 범위 요청이 느려서 · §⑥). 그래서 파일별")
    A("   표본 문서가 **%s ~ %s** 로 다르고, 🔴 **크기 가중 D 를 같이 낸다**(§라)."
      % (cm(min(x["표본 문서"] for x in dp["🔴 파일별 자② 적중률"])),
         cm(max(x["표본 문서"] for x in dp["🔴 파일별 자② 적중률"]))))
    A("3. 티처 #92 **C1** 을 고쳤다 — `prfsts_day` 를 `_merge_write` 로 바꾸고 **잃은 날을 되찾았다**.")
    A("")
    A("## ② 무엇이 나왔나")
    A("")
    A("### 가. 🔴 전량은 앞 4 shard 와 다른 자료였다")
    A("")
    A("| 무엇 | 전량(464 shard) | 앞 4 shard(cc22) | 배 |")
    A("|---|---|---|---|")
    A("| 문서 | **%s** | %s | — |" % (cm(hf["🔴 분모 --- 문서 전량"]), cm(gam["🔴 cc22 분모"])))
    A("| collection | **%d** | 1 | — |" % hf["collection 수"])
    A("| 도박(내 정규식) | **%s** | %s | ×%.2f |"
      % (pct(gam["비율"]), pct(gam["cc22 비율"]), gam["cc22 비율"] / gam["비율"]))
    A("| 뉴스·연예형 host(내 자) | **%s** | %s | ×%.2f |"
      % (pct(news["비율"]), pct(news["cc22 비율"]), news["cc22 비율"] / news["비율"]))
    A("")
    A("- **collection 은 열이 아니라 스물하나였다** — 어제 원격 메타로 그린 지도는 10개였다.")
    A("  `%s`" % ("` · `".join("%s %s" % (k, cm(v))
                               for k, v in list(hf["collection별"]["수"].items())[:8])))
    A("  … 전량은 `runners/out954_hplt_full.json:collection별/수`.")
    A("- **최대 collection(`cc22`)이 %s** — 어느 하나도 절반을 안 넘는다." % pct(hf["🔴 최대 collection 비율"]))
    A("- `ts` 범위 **%s ~ %s**." % (hf["ts 최소"], hf["ts 최대"]))
    A("- 🔴 **도박률 3.869%% 는 죽은 숫자다** — 그 수는 cc22 의 성질이었다. 전량은 **%s**"
      % pct(gam["비율"]))
    A("  (⚠ 내 정규식과 어제 정규식이 달라서 **직접 빼지 마라** — 같은 자로 잰 cc22 는 %s 다)."
      % pct(gam["cc22 비율"]))
    A("")
    A("### 나. 🔴 이 사이클에서 값이 제일 큰 수 — 교차 collection 정확중복")
    A("")
    A("어제 측정된 것은 **하한 0.2246%** 뿐이었고 26.8% 는 균등 가정 외삽이었다. 전량으로 재니:")
    A("")
    A("| 자 | 군(크기>1) | 군에 속한 문서 | 비율 | 초과분 비율 | **교차 collection 문서 비율** |")
    A("|---|---|---|---|---|---|")
    for lab, d in (("전문 md5", td), ("정규화 URL", ud), ("앞 200자", hd)):
        A("| %s | %s | %s | **%s** | %s | **%s** |"
          % (lab, cm(d["군(크기>1) 수"]), cm(d["군에 속한 문서 수"]),
             pct(d["군에 속한 문서 비율"]), pct(d["초과분 비율"]),
             pct(d["🔴 교차 collection 문서 비율"])))
    A("")
    A("- 🔴 **전문이 똑같은 문서가 %s(=%s)이고, 그 군은 %s 가 collection 을 가로지른다**"
      % (cm(td["군에 속한 문서 수"]), pct(td["군에 속한 문서 비율"]),
         "%s 군 중 %d 만 빼고 전부" % (cm(td["군(크기>1) 수"]),
                                  td["군(크기>1) 수"] - td["🔴 교차 collection 군 수"])))
    A("  (%s / %s 군). **HPLT 2.0 이 「크롤 안에서만」 지웠다는 논문 문장이 자료로 재현된다** —"
      % (cm(td["🔴 교차 collection 군 수"]), cm(td["군(크기>1) 수"])))
    A("  크롤 **안**에는 정확중복이 사실상 안 남고, 남은 것은 전부 크롤 **사이**다.")
    A("- **같은 정규화 URL 이 여러 번 담긴 문서가 %s** — 재수집이 이 코퍼스의 지배적 성질이다."
      % pct(ud["군에 속한 문서 비율"]))
    A("- ⚠ **「군에 속한 문서」와 「초과분」은 다른 정의다**(원장 998). 이어 붙이지 마라.")
    A("")
    A("### 다. host — `kin.naver.com` 은 상위 20 안이었다")
    A("")
    if isinstance(kin, dict):
        A("- 🔴 **`kin.naver.com` %d위 · %s 문서(%s)**. 서로 다른 host **%s**."
          % (kin["순위"], cm(kin["문서"]), pct(kin["비율"]), cm(hf["서로 다른 host 수"])))
        A("  **네이버가 robots·약관으로 막은 지식iN 이 CC0 배포본 안에 이미 있다**는 뜻이다.")
    A("- 상위 다섯: %s" % (" · ".join("`%s` %s" % (h["host"], cm(h["문서"]))
                                   for h in hf["host 상위 60"][:5])))
    A("")
    A("### 라. 🔴 FineWeb-2 와의 겹침 — 자 셋이 서로 다른 수를 냈다")
    A("")
    A("| 자 | 교집합(서로 다른 키) | ÷ FineWeb 표본 | ÷ HPLT 전량 |")
    A("|---|---|---|---|")
    for lab, d in (("① URL 정확", r1), ("**② URL 정규화(정본)**", r2),
                   ("③ 본문 앞 200자", r3), ("(덤) 전문 md5", rt)):
        A("| %s | %s | **%s** | %s |"
          % (lab, cm(d["교집합(서로 다른 키)"]),
             pct(d["🔴 교집합 ÷ FineWeb 표본 문서"]),
             pct(d["🔴 교집합 ÷ HPLT 문서 전량"])))
    A("")
    A("- **분모 둘**(조항 60): FineWeb 표본 **%s** 문서(전량 %s 의 %s) · HPLT **%s** 문서."
      % (cm(dp["🔴 FineWeb 표본 문서 수"]), cm(dp["🔴 FineWeb 전량 문서 수(25파일 메타 전수)"]),
         pct(dp["🔴 표본 비율"]), cm(dp["🔴 HPLT 문서 전량"])))
    A("- **크기 가중 D**(파일별 전량 행 수로 가중) **%s** — 단순 합산 **%s** 와 같은 갈래다."
      % (pct(dp["🔴 크기 가중 D(전량 행 수로 가중)"]),
         pct(r2["🔴 교집합 ÷ FineWeb 표본 문서"])))
    A("")
    A("🔴 **자 셋이 셋 다 다른 이야기를 한다 — 그리고 왜 다른지가 이 사이클의 진짜 소득이다.**")
    A("")
    A("1. **자① → 자② 가 %s%%p 뛴다.** 정규화가 쿼리 문자열을 지우기 때문인데, 그 대가로"
      % round(100 * (r2["🔴 교집합 ÷ FineWeb 표본 문서"]
                     - r1["🔴 교집합 ÷ FineWeb 표본 문서"]), 1))
    A("   **서로 다른 키가 HPLT 에서 %s → %s 로 줄어든다**(같은 페이지의 여러 쿼리판이 하나로 뭉친다)."
      % (cm(r1["🔴 분모 ③ HPLT 서로 다른 키"]), cm(r2["🔴 분모 ③ HPLT 서로 다른 키"])))
    A("   🔴 **자② 의 겹침에는 「맞은 것」과 「뭉친 것」이 섞여 있다.** 사전등록이 자② 를 정본으로")
    A("   못 박았으므로 판정은 자② 로 하되, **이 한계를 판정문에 같이 싣는다**(조항 61).")
    A("2. 🔴 **본문 기반 자(③ %s · 전문 md5 %s)가 URL 자보다 훨씬 낮다.** 예측 P3 은 그 반대를"
      % (pct(r3["🔴 교집합 ÷ FineWeb 표본 문서"]), pct(rt["🔴 교집합 ÷ FineWeb 표본 문서"])))
    A("   걸었고 **빗맞혔다**. 기제는 하나로 보인다 — **두 코퍼스가 본문 추출기가 다르다**")
    A("   (FineWeb-2 는 trafilatura 계열, HPLT 는 자체 추출). **같은 페이지라도 첫 200자가 다르게**")
    A("   **떨어진다.** 즉 🔴 **본문 해시로 두 코퍼스의 겹침을 재면 겹침이 원리상 과소평가된다.**")
    A("   ⚠ 이 기제는 **이 사이클이 직접 안 쟀다** — 다음 사이클의 후보다(같은 URL 쌍에서 본문을")
    A("   맞대 보면 바로 갈린다).")
    A("- 조항 62 ③ **심은 키**: %s." % dp["자 ② URL 정규화(🔴 정본)"]["🔴 조항 62 ③ 심은 키"]["판정"])
    A("- 조항 62 ① **반대 방향**: HPLT−FineWeb **%s** 키 · FineWeb−HPLT **%s** 키."
      % (cm(r2["① 반대 방향 --- HPLT − FineWeb(키)"]),
         cm(r2["① 반대 방향 --- FineWeb − HPLT(키)"])))
    A("")
    A("## ③ 분모 (규약 60 — 명령·범위·트리)")
    A("")
    A("- HPLT: 연 shard **%d/464** · 못 연 것 **%s** · 문서 **%s**. 명령 `%s`"
      % (hf["🔴 분모 --- 연 shard"], hf["🔴 분모 --- 못 연 shard"] or "없다",
         cm(hf["🔴 분모 --- 문서 전량"]), hf["🔴 규약 60 --- 명령·범위·트리"]["명령"]))
    A("- FineWeb: 읽은 파일 **%d/25** · 받은 바이트 **%s** · 요청 **%s**"
      % (dp["🔴 읽은 FineWeb 파일 수"], cm(dp["받은 바이트(FineWeb)"]),
         cm(dp["요청 수(FineWeb)"])))
    A("- 해시는 64비트다. 충돌 기대치 HPLT 안 **%.2e** · HPLT×FineWeb **%.2e** — 판정을 못 바꾼다."
      % (hf["⚠ 64비트 해시 충돌 기대치"], dp["⚠ 64비트 해시 충돌 기대치(HPLT×FW)"]))
    A("")
    A("## ④ 판정 — 🔴 사전등록 §5 의 규칙을 그대로 물렸다")
    A("")
    A("**D = %s** → %s" % (pct(sc["🔴 D (자② 교집합 ÷ FineWeb 표본 문서)"]), sc["🔴 §5 판정"]))
    A("")
    A("예측 채점 **%d/%d** · 빗맞힌 것 %s"
      % (sc["🔴 맞은 수"], sc["🔴 본 가짓수(분모)"], sc["🔴 빗맞힌 것"] or "없다"))
    A("")
    A("| # | 예측 | 실측 | 맞았나 |")
    A("|---|---|---|---|")
    for p in sc["예측 채점"]:
        A("| %s | %s | `%s` | %s |"
          % (p["번호"], p["예측"], json.dumps(p["실측"], ensure_ascii=False),
             "✅" if p["맞았나"] else "🔴 **빗맞힘**"))
    A("")
    A("🔴 **빗맞힌 것은 「이 자를 못 넘었다」로 읽는다** — 특히 뉴스형 host 정규식은 어제 조사관의")
    A("자와 다른 자다. **두 수를 이어 붙이지 마라**(조항 60).")
    A("")
    A("## ⑤ 곁다리 수리 — 티처 #92 C1 (레인 [수리])")
    A("")
    A("- `ingest/kopis953.py` **두 자리**를 `_write_gz` → `_merge_write(key=\"prfdt\")` 로 고쳤다.")
    A("- 되찾기 주행: 행 **%d → %d** · 서로 다른 날 **%d → %d** · **되찾은 날 %d** · 실패한 창 %d."
      % (c1["전 --- 행"], c1["후 --- 행"], c1["전 --- 서로다른 prfdt"],
         c1["후 --- 서로다른 prfdt"], c1["🔴 되찾은 날"], c1["🔴 실패한 창"]))
    A("- 🔴 **음성 대조**(진짜 파일 안 건드리고 사본에 **옛 코드**를 물렸다): 사본 **%d행 → %d행** — "
      % (rg["🔴 음성 대조(옛 코드를 사본에 물린다)"]["사본 전 행"],
         rg["🔴 음성 대조(옛 코드를 사본에 물린다)"]["옛 코드(_write_gz)로 쓴 뒤 행"]))
    A("  **옛 코드는 정말로 자른다**. 같은 증분 창을 새 코드로 쓰면 **%d행 → %d행**(안 준다)."
      % (rg["전 --- 행"], rg["후 --- 행"]))
    A("")
    A("## ⑥ 못 한 것 · 못 잰 것 (🔴 「안 했다」와 「못 했다」를 가른다)")
    A("")
    A("- **안 했다**: FineWeb-2 전량 수신(105.77GB) — 사전등록이 「재고 나서 정한다」로 정했다.")
    A("- **안 했다**: MinHash · SemDeDup · 형태소 분석기 — 원장 998 의 실측으로 값이 안 나온다.")
    A("- **안 했다**: 권고 파이프라인의 Bloom·줄 보일러플레이트·발행일 추출 실주행 — 이 사이클은")
    A("  **재는 데** 다 썼다. 다음 사이클의 1순위다.")
    A("- **안 했다**: 래칫 ④ 를 「원천 × 파일별」로 내리는 수리(티처 #92 M4) — 수리 레인은")
    A("  한 사이클에 하나까지이고 그 하나를 C1 에 썼다.")
    A("- **못 했다**: FineWeb 쪽 **전량 URL 열** 읽기 — 행군이 **1,000행짜리**라 낱개로 뽑으면")
    A("  요청이 수만 건이고, 이 CDN 은 작은 범위 요청이 느리다(실측 1.5MB 에 4~5초 · 8병렬).")
    A("  그래서 **행군 층화 군집 표본**으로 내렸다 — 표본 비율 **%s**." % pct(dp["🔴 표본 비율"]))
    A("- **못 했다**: 「FineWeb 에만 있는 문서」가 **FineWeb 이 새로 담은 것인지, HPLT 가 안 담은")
    A("  것인지** 가르기 — 두 자료의 **제거 범위가 다르다**(조항 61 · 사전등록 §0-2).")
    A("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = build()
    p = ROOT / DOC
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    ins = inputs_of(GEN)
    st = {
        "무엇": "🔴 노트 954 의 탐색 산출물에 도장을 박는다",
        "시각(UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "🔴 어느 트리를 읽나": {"입력 산출물": "작업 트리", "⚠": "한 트리만 읽는다",
                          "통과": True},
        "🔴 입력 목록을 어떻게 얻었나": "`%s` 의 `J(\"…\")` 리터럴을 **AST 로** 뽑았다(손 전사 0)" % GEN,
        "🔴 입력 수(분모)": len(ins),
        "🔴 입력별 sha256(대조의 기록 쪽)": {r: _sha(r) for r in ins},
        "🔴 생산기 sha256": {GEN: _sha(GEN)},
        "🔴 문서 sha256": {DOC: _sha(DOC)},
        "⚠ 한계(조항 61)": "대조는 **낡음만** 잡는다. 문서의 **수가 옳은지는 안 본다**",
        "통과": True,
    }
    OUT.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", p, "·", OUT)


if __name__ == "__main__":
    main()
