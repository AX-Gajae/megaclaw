# -*- coding: utf-8 -*-
"""노트 942(수리) — **robots 대조기를 RFC 9309 로 고치고 18호스트를 다시 매긴다.**

티처 #81 C2: `ingest/robots941.py:90-99` 의 `hits()` 가

```python
pat = d.split("*")[0]
if pat and path.startswith(pat): ...
```

규칙을 **첫 `*` 에서 잘라 접두사 비교**한다. 그래서 `/*?*EventId=201357` · `/*.swf$`
같은 규칙이 전부 `/` 로 축약돼 **모든 경로에 걸린다**. 그리고 `Allow` 는 941 의
`parse()` 가 뽑아 놓기까지 하고서 **대조에 안 쓴다**.

RFC 9309 §2.2 를 구현한다:
  · `*` = 아무 문자열 (와일드카드)          · `$` = 경로 끝 앵커
  · **Allow / Disallow 최장일치**(패턴 길이) · 길이 동률이면 **Allow 승**
  · 걸리는 규칙이 없으면 **허용**            · 빈 `Disallow:` 는 규칙이 아니다
  · 그룹은 **연속된 `User-agent:` 줄을 모두** 묶는다(941 은 마지막 하나만 봤다)

🔴 **새로 크롤하지 않는다.** `data/ingest/robots941/` 에 **이미 받아 둔 16파일**만 읽는다.
🔴 **941 산출물은 동결물** — `runners/out941_robots.json` 은 **읽기만** 한다.
🔴 옛 `hits()` 를 **`ingest.robots941` 에서 그대로 import** 해서 같은 입력에 둘 다 물린다
    (베껴 쓰면 「내가 고친 것과 비교했다」가 아니라 「내가 쓴 두 함수를 비교했다」가 된다).

쓰는 법::  python3 runners/out942_robots.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/Users/ax/world_model")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from ingest.robots941 import HOSTS, hits as hits_941, parse as parse_941  # noqa: E402

SAVED = ROOT / "data/ingest/robots941"
OLD = ROOT / "runners/out941_robots.json"
OUT = ROOT / "runners/out942_robots.json"

#: 우리가 쓰는 UA 의 product token (`ingest/robots941.py:31`)
UA_TOKEN = "sweetspot-world-model"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ── RFC 9309 파서 ────────────────────────────────────────────────────────
def groups(txt: str) -> list:
    """robots.txt → 그룹 목록. 🔴 **연속된 `User-agent:` 줄을 한 그룹으로 묶는다.**

    941 의 `parse()` 는 `cur = (v == "*")` 라서

        User-agent: *
        User-agent: Bingbot
        Disallow: /x

    같은 형태에서 `*` 그룹의 규칙을 **통째로 놓친다**(마지막 UA 만 남는다).
    """
    out: list = []
    cur_ua: list = []
    cur_rules: list = []
    last_was_ua = False
    for raw in txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip().lower()
        v = v.strip()
        if k == "user-agent":
            if not last_was_ua and cur_ua:
                out.append({"ua": cur_ua, "rules": cur_rules})
                cur_ua, cur_rules = [], []
            cur_ua.append(v)
            last_was_ua = True
            continue
        last_was_ua = False
        if not cur_ua:
            continue                       # 그룹 밖의 줄(Sitemap 등)은 버린다
        if k in ("allow", "disallow"):
            cur_rules.append({"종류": k, "값": v})
        elif k == "crawl-delay":
            cur_rules.append({"종류": "crawl-delay", "값": v})
    if cur_ua:
        out.append({"ua": cur_ua, "rules": cur_rules})
    return out


def pick(gs: list, ua_token: str) -> dict:
    """RFC 9309 §2.2.1 — UA 토큰에 맞는 그룹, 없으면 `*` 그룹. 같은 UA 그룹은 합친다."""
    tok = ua_token.lower()
    for want in (tok, "*"):
        rules: list = []
        uas: list = []
        for g in gs:
            if any(u.lower() == want for u in g["ua"]):
                rules += g["rules"]
                uas += g["ua"]
        if uas:
            return {"고른 UA": want, "합친 그룹의 UA 줄": uas, "규칙": rules}
    return {"고른 UA": None, "합친 그룹의 UA 줄": [], "규칙": []}


def _rx(pat: str):
    """규칙 패턴 → 정규식. `*` 는 아무 문자열, 끝의 `$` 는 끝 앵커."""
    anchored = pat.endswith("$")
    body = pat[:-1] if anchored else pat
    rx = "".join(".*" if c == "*" else re.escape(c) for c in body)
    return re.compile("^" + rx + ("$" if anchored else ""))


def rfc9309(path: str, rules: list) -> dict:
    """RFC 9309 §2.2.2 — **최장일치 · 동률이면 Allow 승**.

    반환: 판정 · 이긴 규칙 · 걸린 규칙 전량(종류별).
    """
    matched = []
    for r in rules:
        if r["종류"] not in ("allow", "disallow"):
            continue
        v = r["값"]
        if v == "":
            continue                       # 빈 Disallow 는 「막는 것 없음」 = 규칙 아님
        if _rx(v).match(path):
            matched.append(r)
    if not matched:
        return {"막힘": False, "이긴 규칙": None, "사유": "걸리는 규칙이 없다 → 허용",
                "걸린 규칙 전량": []}
    # 길이는 패턴 그대로의 옥텟 수. 동률이면 allow 가 이긴다.
    best = max(matched, key=lambda r: (len(r["값"]), r["종류"] == "allow"))
    return {"막힘": best["종류"] == "disallow",
            "이긴 규칙": f'{best["종류"]}: {best["값"]}',
            "사유": f'최장일치 (길이 {len(best["값"])})',
            "걸린 규칙 전량": [f'{r["종류"]}: {r["값"]}' for r in matched]}


#: 🔴 **RFC 9309 §2.2.2 의 예제를 그대로 옮긴 자가 검사.**
#: 「다르게 짰다」와 「맞게 짰다」는 다르다 — 옛 대조기와 새 대조기가 서로 다르다는 것만으로는
#: 새 것이 옳다는 증거가 안 된다(조항 59). 규격이 답을 적어 준 자리로 검사한다.
SPEC_CASES = [
    # (규칙 목록, 경로, 막혀야 하나)
    ([("disallow", "/")], "/anything", True),
    ([("disallow", "/*")], "/anything", True),
    ([("disallow", "/fish")], "/fish", True),
    ([("disallow", "/fish")], "/fish.html", True),
    ([("disallow", "/fish")], "/fish/salmon.html", True),
    ([("disallow", "/fish")], "/fishheads", True),
    ([("disallow", "/fish")], "/Fish.asp", False),
    ([("disallow", "/fish")], "/catfish", False),
    ([("disallow", "/fish*")], "/fishheads", True),
    ([("disallow", "/fish/")], "/fish/salmon.htm", True),
    ([("disallow", "/fish/")], "/fish", False),
    ([("disallow", "/fish/")], "/fish.html", False),
    ([("disallow", "/*.php")], "/index.php", True),
    ([("disallow", "/*.php")], "/folder/filename.php?parameters", True),
    ([("disallow", "/*.php")], "/", False),
    ([("disallow", "/*.php")], "/windows.PHP", False),
    ([("disallow", "/*.php$")], "/filename.php", True),
    ([("disallow", "/*.php$")], "/filename.php?parameters", False),
    ([("disallow", "/*.php$")], "/filename.php5", False),
    ([("disallow", "/fish*.php")], "/fishheads/catfish.php?parameters", True),
    ([("disallow", "/fish*.php")], "/Fish.PHP", False),
    # 최장일치 · 동률이면 Allow 승
    ([("allow", "/example/page/"), ("disallow", "/example/*")],
     "/example/page/index.html", False),
    ([("allow", "/p"), ("disallow", "/")], "/page", False),
    ([("allow", "/"), ("disallow", "/")], "/x", False),
    ([("allow", "/folder"), ("disallow", "/folder")], "/folder/page", False),
    ([("disallow", "/folder/sub"), ("allow", "/folder")], "/folder/sub/x", True),
    ([("disallow", "")], "/x", False),          # 빈 Disallow 는 규칙이 아니다
    ([], "/x", False),                           # 규칙 없음 → 허용
    # 🔴 941 이 걸려 넘어진 형태
    ([("allow", "/"), ("disallow", "/*?*EventId=201357"), ("disallow", "/*.swf$")],
     "/shop/wproduct.aspx", False),
    ([("disallow", "/*?*EventId=201357")], "/shop/x.aspx?a=1&EventId=201357", True),
    ([("disallow", "/*.swf$")], "/a/b.swf", True),
    ([("disallow", "/*.swf$")], "/a/b.swf?x", False),
]


def selftest() -> dict:
    """규격 예제 통과표. 🔴 옛 대조기도 같은 표에 물려 **몇 개를 틀리는지** 센다."""
    ok = bad = 0
    old_ok = old_bad = 0
    fails: list = []
    old_fails: list = []
    for rules, path, want in SPEC_CASES:
        rr = [{"종류": k, "값": v} for k, v in rules]
        got = rfc9309(path, rr)["막힘"]
        if got == want:
            ok += 1
        else:
            bad += 1
            fails.append({"규칙": rules, "경로": path, "규격": want, "942": got})
        dis = [v for k, v in rules if k == "disallow" and v]
        og = bool(hits_941(path, dis))
        if og == want:
            old_ok += 1
        else:
            old_bad += 1
            old_fails.append({"규칙": rules, "경로": path, "규격": want, "941": og})
    return {
        "🔴 규격 예제 수": len(SPEC_CASES),
        "🔴 942(RFC 9309) 맞음": ok, "942 틀림": bad, "942 틀린 것": fails,
        "🔴 941(옛 대조기) 맞음": old_ok, "941 틀림": old_bad,
        "941 틀린 것": old_fails,
        "🔴 뜻": ("941 이 틀리는 자리가 있어야 「고쳤다」가 성립한다. "
                "🔴 그리고 942 가 규격을 하나라도 틀리면 이 사이클의 재판정표는 무효다."),
    }


# ── 대조 ─────────────────────────────────────────────────────────────────
def main() -> dict:
    t0 = time.time()
    st = selftest()
    old = json.loads(OLD.read_text())
    old_rows = {r["호스트"]: r for r in old["전수"]}

    rows = []
    n_saved = 0
    for host, path, dom, memo in HOSTS:
        f = SAVED / f"{host}.robots.txt"
        r = {"호스트": host, "노리는 경로": path, "도메인": dom,
             "941 HTTP": old_rows.get(host, {}).get("HTTP"),
             "941 판정": old_rows.get(host, {}).get("🔴 노리는 경로가 막히나"),
             "941 걸린 규칙": old_rows.get(host, {}).get("걸린 규칙"),
             "메모": memo}
        if not f.exists():
            r["942 판정"] = None
            r["사유"] = (f"robots.txt 를 못 받았다(941 에서 HTTP "
                        f"{old_rows.get(host, {}).get('HTTP')}) — "
                        "🔴 **모른다**이지 「안 막힘」이 아니다")
            rows.append(r)
            continue
        n_saved += 1
        txt = f.read_text()
        r["파일 sha256"] = sha(f)
        r["바이트"] = f.stat().st_size
        gs = groups(txt)
        g = pick(gs, UA_TOKEN)
        rules = g["규칙"]
        dis = [x["값"] for x in rules if x["종류"] == "disallow" and x["값"]]
        alw = [x["값"] for x in rules if x["종류"] == "allow" and x["값"]]
        delay = [x["값"] for x in rules if x["종류"] == "crawl-delay"]
        v = rfc9309(path, rules)

        # 🔴 옛 함수를 **import 해서** 같은 입력에 물린다
        old_parsed = parse_941(txt)
        old_hit = hits_941(path, old_parsed["Disallow(*)"])

        r.update({
            "그룹 수(파일 전체)": len(gs),
            "고른 UA 그룹": g["고른 UA"],
            "그 그룹의 UA 줄": g["합친 그룹의 UA 줄"],
            "Disallow 수": len(dis), "Allow 수": len(alw),
            "Crawl-delay": delay or None,
            "🔴 942 판정(RFC 9309)": v["막힘"],
            "🔴 942 이긴 규칙(원문)": v["이긴 규칙"],
            "942 사유": v["사유"],
            "942 걸린 규칙 전량": v["걸린 규칙 전량"],
            "🔴 941 재현(같은 파일에 옛 hits())": bool(old_hit),
            "941 재현 걸린 규칙": old_hit,
            "🔴 뒤집혔나": bool(old_hit) != v["막힘"],
            "🔴 941 이 본 Disallow 수(UA * 블록)": len(old_parsed["Disallow(*)"]),
            "🔴 941 이 파싱만 하고 안 쓴 Allow 수": len(old_parsed["Allow(*)"]),
        })
        r["942 판정"] = v["막힘"]
        rows.append(r)

    judged = [r for r in rows if r["942 판정"] is not None]
    blocked = [r["호스트"] for r in judged if r["942 판정"]]
    openh = [r["호스트"] for r in judged if not r["942 판정"]]
    unk = [r["호스트"] for r in rows if r["942 판정"] is None]
    flip = [{"호스트": r["호스트"], "941": r["🔴 941 재현(같은 파일에 옛 hits())"],
             "942": r["942 판정"], "942 이긴 규칙": r["🔴 942 이긴 규칙(원문)"],
             "941 걸린 규칙": r["941 재현 걸린 규칙"]}
            for r in judged if r["🔴 뒤집혔나"]]
    repro = [r["호스트"] for r in judged
             if r["🔴 941 재현(같은 파일에 옛 hits())"] != r["941 판정"]]

    tree = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True).stdout

    res = {
        "노트": 942, "레인": "수리",
        "무엇": "robots 대조기를 RFC 9309 로 고치고 재판정 (티처 #81 C2) — 🔴 새 크롤 0",
        "시각": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "초": round(time.time() - t0, 1),
        "🔴 조항 60 — 명령·범위·트리": {
            "명령": "python3 runners/out942_robots.py",
            "범위": f"{SAVED.relative_to(ROOT)} 의 저장된 robots.txt (새로 안 받았다)",
            "트리": tree, "작업 트리 깨끗함": dirty.strip() == "",
            "🔴 깨끗하지 않으면 여기 전량": dirty.splitlines(),
        },
        "🔴 호스트 분모 — 941 이 18 과 16 을 섞어 쓴 자리": {
            "시도한 호스트": len(HOSTS),
            "robots.txt 를 실제로 받아 저장한 파일": n_saved,
            "🔴 판정 대상(= 저장된 파일)": len(judged),
            "🔴 모른다(파일 없음)": len(unk),
            "모른다 목록": [{"호스트": r["호스트"], "941 HTTP": r["941 HTTP"]}
                       for r in rows if r["942 판정"] is None],
            "🔴 합 == 시도": len(judged) + len(unk) == len(HOSTS),
            "🔴 뜻": ("**18 = 물어본 호스트** · **16 = 답을 받아 판정할 수 있는 호스트**. "
                    "막힘/안 막힘 비율의 분모는 **16** 이고, 「후보 호스트」의 분모는 **18** 이다."),
        },
        "🔴 배선·정확도 검사(RFC 9309 규격 예제)": st,
        "🔴 941 → 942": {
            "941 원문 산출물의 막힘": old["수"]["막힘"],
            "941 대조기를 저장 파일에 다시 물린 막힘":
                sum(1 for r in judged if r["🔴 941 재현(같은 파일에 옛 hits())"]),
            "🔴 942(RFC 9309) 막힘": len(blocked),
            "안 막힘": len(openh), "모른다": len(unk),
            "🔴 941 산출물과 941 재현이 다른 호스트": repro,
            "🔴 뒤집힌 호스트": flip,
            "🔴 반증 조건 5 — 하나도 안 뒤집히면 고친 게 아니다": len(flip) > 0,
        },
        "🔴 942 막힌 호스트": blocked,
        "🔴 942 안 막힌 호스트": openh,
        "🔴 모른다": unk,
        "🔴 robots 가 허용해도 이용약관은 따로다": (
            "이 표는 robots.txt 만 읽은 것이다. 약관·로그인 담벼락은 호스트마다 따로 "
            "확인해야 하고 **941 도 942 도 안 했다**."),
        "전수": rows,
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k != "전수"},
                     ensure_ascii=False, indent=1))
    return res


if __name__ == "__main__":
    main()
