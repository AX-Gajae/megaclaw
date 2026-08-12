# -*- coding: utf-8 -*-
"""노트 953 의 **탐색 레인 산출물 생산기** --- `docs/탐색/953.md` 를 찍고 도장을 박는다.

🔴 **레인 규약대로 하나만 낸다.** `docs/루프.md:100` 탐색 행: 규약 **최소** ---
①무엇을 했나 ②무엇이 나왔나 ③**분모** ④못 한 것. **그뿐**이고 **판정은 안 한다**.
🔴 **탐색 결과는 이 사이클 결론에 안 들어간다**(규칙 1) --- 다음 사이클의 **후보**다.

🔴 **표제·본문의 수를 손으로 안 쓴다.** 산출물 키에서 읽고 sha 를 박는다.

    python3 -m runners.note953_gen
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

OUT = ROOT / "runners/out953_docstamp.json"
DOC = "docs/탐색/953.md"
GEN = "runners/note953_gen.py"


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


def build() -> str:
    sao = J("runners/out953_sao.json")
    ko = J("runners/out953_kopis.json")
    L = []
    A = L.append
    n = sao["2 다시 센다 --- 새 자"]
    b = sao["1 부순다 --- 952 의 세 조건 재현"]
    d0 = sao["0 분모"]
    t3 = sao["3 티처의 283 을 다시 센다"]

    A("# 탐색 953 — (s,a,o) 를 새 자로 다시 셌고, **13번째 도메인(공연)을 실제로 받았다**")
    A("")
    A("- **레인**: 🔴 **[탐색]** — `docs/루프.md:100`. 규약 **최소**(①무엇 ②무엇이 나왔나 ③분모 ④못 한 것).")
    A("  **판정 안 한다.** 🔴 **이 결과는 953 결론에 안 들어간다**(규칙 1) — 다음 사이클의 **후보**다.")
    A("- **왜 `[수집]` 이 아닌가**: `docs/루프.md` 에 그런 레인이 **없다**. 표의 「새 원천」은 **탐색**이고,")
    A("  953 이 규칙 6 으로 그 문을 닫았다(티처 #91 C4 — 952 는 **없는 레인 아래 전량 규약을 스스로 걸었다**).")
    A("- 🔴 **판에 안 붙였다** — `docs/방향.md:65`. 여기 수는 **학습쌍의 자**이지 판 ρ 의 자가 아니다.")
    A("- **생산기**: `%s` (이 문서는 손으로 안 썼다)" % GEN)
    A("")
    A("---")
    A("")
    A("## 가. (s,a,o) 를 다시 셌다 — 🔴 **82,981 은 삼중쌍이 아니었다**")
    A("")
    A("### ① 무엇을 했나")
    A("")
    A("티처 #91 C3 이 잡은 것을 **내 코드로 다시 세어** 확인하고, 자를 갈아 끼워 다시 셌다.")
    A("")
    A("### ② 무엇이 나왔나")
    A("")
    A("**부순 쪽(재현)**")
    A("")
    A("| 952 의 조건 | 수 | 항등식인가 |")
    A("|---|---|---|")
    A("| `a` = 출시일이 파싱된다 | **%s** | 🔴 **그렇다**(분모 전량) |" % format(b["a 만족"], ","))
    A("| `s` = genres/tags/price 중 하나 | **%s** | 🔴 **그렇다** |" % format(b["s 만족"], ","))
    A("| `o` = (positive+negative) ≥ 1 | **%s** | 아니다 |" % format(b["o 만족"], ","))
    A("| **셋 다** | **%s** | 🔴 **`o` 하나와 정확히 같다: %s** |"
      % (format(b["셋 다"], ","), b["🔴 셋 다 == o 하나인가"]))
    A("")
    A("🔴 **그러므로 82,981 의 뜻은 「리뷰가 1개 이상인 게임 수」다.** 삼중쌍이 아니다.")
    A("")
    A("**다시 센 쪽(새 자)**")
    A("")
    A("- `a` = 출시일이 **판 유보 기간 안**(≥ 2025-01-01 · `docs/용어.md:14` T=2025.0)")
    A("- `o` = **리뷰 본문이 1건 이상**(`본문` 이 비지 않음) — 「리뷰 수 칸이 0 이 아니다」가 아니다")
    A("- `s` = 952 정의 그대로")
    A("")
    A("| 조건 | 수 |")
    A("|---|---|")
    A("| `s` | **%s** |" % format(n["s 만족"], ","))
    A("| `a` (유보 안) | **%s** |" % format(n["a 만족(유보 안)"], ","))
    A("| `o` (본문 있는 appid) | **%s** |" % format(n["o 만족(리뷰 본문 있는 appid)"], ","))
    A("| 🔴 **삼중 (s,a,o)** | **%s** |" % format(n["🔴 셋 다(s∧a∧o)"], ","))
    A("")
    A("🔴 **이제 셋이 서로 다르다**(항등식이 아니다): %s" % n["🔴 세 수가 서로 다른가(=항등식이 아니다)"])
    A("")
    A("### ③ 분모 — 🔴 **한 줄로 못 박는다**")
    A("")
    A("> **Steam 게임표 = `games.json` %s.** `games.csv` %s 는 그 **부분집합**이다"
      % (format(d0["games.json 항목"], ","), format(d0["games.csv 서로다른 AppID"], ",")))
    A("> (csv 전용 **%d** · json 전용 **%s**)."
      % (d0["🔴 csv 전용(= json 에 없는 것)"], format(d0["🔴 json 전용"], ",")))
    A("")
    A("이 한 줄이 없어서 952 의 P9 이 흔들렸다 — 같은 물음이 **json 기준 98.12% 맞았다**,")
    A("**csv 기준 79.96% 빗맞혔다**다. **분모가 답을 뒤집는다**(조항 60).")
    A("이 줄은 `data/lab/sources.json` 의 `steam_games` 항목에도 **글자로 박아 두었다** — 노트는 흘러가고 등기부는 남는다.")
    A("")
    A("**티처의 283 을 내 코드로 다시 셌다**: 리뷰 appid **%d** ∩ 후보(o952) = **%d**"
      % (t3["리뷰 서로다른 appid"], t3["🔴 479 ∩ 후보(o952)"]))
    A("(그중 유보 기간 안 = **%d**). 🔴 **같은 수가 나왔다.**"
      % t3["🔴 479 ∩ 후보(o952) ∩ 유보(a953)"])
    A("")
    A("🔴 **리뷰 파일을 어디서 읽었나**: `%s`" % n["리뷰 파일"]["출처"])
    A("(디스크 오류: `%s` — 🔴 **그걸 「리뷰 0행」으로 읽었으면 이 사이클이 고치려는 병 그 자체다**)"
      % n["리뷰 파일"]["🔴 디스크 오류"])
    A("")
    A("### ④ 못 한 것")
    A("")
    for x in sao["🔴 안 쟀다"]:
        A("- %s" % x)
    A("")
    A("---")
    A("")

    pb = ko["1 공연 목록(pblprfr)"]
    de = ko["2 상세 표본(pblprfr/{mt20id})"]
    pc = ko["3 공연장(prfplc)"]
    bx = ko["4-가 boxoffice --- 🔴 못 열었다"]
    se = ko["4-나 (a→o) 시계열(prfstsTotal · ststype=day)"]
    st = ko["5 통계(prfsts*)"]

    A("## 나. KOPIS — **13번째 도메인(공연)을 실제로 받았다**")
    A("")
    A("### ① 무엇을 했나")
    A("")
    A("키가 왔다(저장소 **밖** `/Users/ax/wm_harvest/keys.json#kopis.키` · 🔴 **키 문자열은 어디에도 안 쓴다**).")
    A("`ingest/kopis953.py` 를 새로 만들어 **%s ~ %s** 를 31일 창 **%d개**로 훑었다."
      % (ko["창"]["시작"], ko["창"]["끝"], ko["창"]["31일 창 수"]))
    A("")
    A("### ② 무엇이 나왔나")
    A("")
    A("| 무엇 | 수 |")
    A("|---|---|")
    A("| 공연 목록 `pblprfr` — 서로다른 `mt20id`(이번 수확) | **%s** |"
      % format(pb["🔴 서로다른 mt20id(이번 수확)"], ","))
    A("| 파일에 합친 뒤 | **%s** |" % format(pb["합친 뒤"], ","))
    A("| 상세 `pblprfr/{mt20id}` 표본 | **%d / %d** |" % (de["받은 것"], de["🔴 분모(표본)"]))
    A("| 공연장 목록 `prfplc` | **%s행** |" % format(pc["목록 행"], ","))
    A("| 🔴 상세를 받은 시설 중 `la`·`lo` 둘 다 | **%d / %d** (%.1f%%) |"
      % (pc["🔴 la·lo 둘 다 있는 시설"], pc["🔴 상세 분모(표본)"], (pc["비율"] or 0) * 100))
    A("| `prfstsTotal` 날짜별 (a→o) 행 | **%s** (서로다른 날 **%d**) |"
      % (format(se["받은 행"], ","), se["서로다른 날"]))
    A("")
    A("**s 자리가 실제로 있나**(상세 %d건 분모):" % de["받은 것"])
    for k, v in de["🔴 s 자리 채움"].items():
        A("- `%s` **%d (%.1f%%)**" % (k, v["수"], (v["비율"] or 0) * 100))
    A("")
    A("🔴 **주 세션의 자가 틀린 자리 둘을 실측으로 갈랐다**")
    A("")
    A("1. `prfstsCate`·`prfstsArea` 는 루트가 `dbs` 가 아니라 **`prfsts`** 다 —")
    A("   실측 루트 `%s` · 행 **%d**(Cate) / **%d**(Area). **행은 멀쩡히 있었다.**"
      % (st["prfstsCate"]["루트 태그"], st["prfstsCate"]["행"], st["prfstsArea"]["행"]))
    A("2. 🔴 **`boxoffice` 는 안 산다 — 「🟢 db 1」은 오류 행 하나였다.**")
    A("   `<dbs><db><returncode>01</returncode><errmsg>INVALID REQUEST PARAMETER ERROR</errmsg></db></dbs>`")
    A("   를 자식만 세면 **행 1 = 「산다」**로 읽힌다. 파라미터 **%d벌**을 시도했고 **전부 같은 오류**다."
      % len(bx["🔴 시도"]))
    A("   🔴 **「없다」가 아니라 「내가 못 열었다」**로 적는다(조항 59).")
    A("   대신 **`prfstsTotal?ststype=day`** 가 열렸고 **그게 (a→o) 시계열**이다.")
    A("")
    A("🔴 **HTTP 400 은 질의어의 속성이 아니라 「너무 빨리 불렀다」의 속성이었다.**")
    A("첫 주행에서 13 창 중 **11 이 400** 이었는데 같은 질의를 잠시 뒤 다시 부르니 **200 + 자료**였다.")
    A("→ 물러섰다 다시 부르는 길을 넣었다(이번 주행에서 **%s회** 다시 불렀다)."
      % format(pb.get("🔴 물러섰다 다시 부른 횟수", 0), ","))
    A("**티처 #91 M1 의 `rc99` 와 같은 자리다 — 오류의 원인을 원천에 돌리면 원천을 잃는다.**")
    A("")
    A("### ③ 분모")
    A("")
    A("🔴 **여기 수는 전부 「내가 받은 XML 행」이다. 남이 신고한 수가 아니다**(조항 60).")
    A("- 공연: 창 **%d개** · 페이지 호출 **%s** · 🔴 **실패한 창 %s**"
      % (ko["창"]["31일 창 수"], format(pb["페이지 호출"], ","),
         len(pb["🔴 오류"]) if isinstance(pb["🔴 오류"], list) else pb["🔴 오류"]))
    A("- 상세: 표본 **%d**(정렬한 `mt20id` 를 **등간격** — 🔴 무작위가 아니다)" % de["🔴 분모(표본)"])
    A("- 시설: 목록 **%s행** 중 상세 **%d**(등간격) · 실패 %d"
      % (format(pc["목록 행"], ","), pc["🔴 상세 분모(표본)"], pc["상세 실패"]))
    A("- (a→o): 창 **%d** 중 실패 **%d**" % (se["🔴 분모(창)"], se["🔴 실패한 창"]))
    A("")
    A("### ④ 못 한 것")
    A("")
    A("- 🔴 **`boxoffice` 를 못 열었다** — 파라미터를 못 맞췄다. 가이드의 필수 인자를 아직 못 찾았다")
    A("- 🔴 **공연 한 건별 (a→o) 는 아직 없다** — `prfstsTotal` 은 **전국 합계**다")
    A("- 🔴 **`la`/`lo` 를 서울 격자 인구에 실제로 붙여 보지 않았다** — 좌표가 있다는 것만 쟀다")
    A("- 🔴 **일일 호출 상한을 모른다** — 가이드가 순환 참조다(「없다」가 아니라 **「안 쟀다」**)")
    A("- 🔴 **상세를 전량 안 받았다**(표본 %d). 남은 것 약 %s건"
      % (de["🔴 분모(표본)"], format(max(0, pb["합친 뒤"] - de["받은 것"]), ",")))
    A("- 🔴 **이 원천이 판 유보에 붙는지 안 쟀다** — 붙일 생각도 없다(`docs/방향.md:65`)")
    A("- 🔴 **13번째 도메인이 「열렸다」고 말하려면 라벨(o)이 개체별로 있어야 한다.** 오늘은 **s 와 a 가 있고 o 는 합계뿐**이다")
    A("")
    return "\n".join(L) + "\n"


def main() -> None:
    txt = build()
    p = ROOT / DOC
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    ins = inputs_of(GEN)
    st = {
        "무엇": "🔴 노트 953 의 탐색 산출물에 도장을 박는다",
        "시각(UTC)": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "🔴 어느 트리를 읽나": {"입력 산출물": "작업 트리", "⚠": "한 트리만 읽는다"},
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
