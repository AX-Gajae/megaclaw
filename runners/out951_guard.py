# -*- coding: utf-8 -*-
"""노트 951 [수리] — **저장소 쓰기 가드가 여섯 채널 중 둘만 잡았다**(티처 #90 C1·C2).

사전등록: `docs/prereg_951_guard.md`(측정 전 커밋 · 파일 하나).

이 러너가 하는 일:

* 절 1 — 🔴 **채널을 심어서 센다**. 가짜 저장소에 채널 일곱을 심고 **950 판 가드**와
  **951 판 가드**를 각각 돌려 ① 가드가 발화했나 ② **파일이 실제로 생겼나** 를 잰다.
  🔴 950 판 드라이버는 **손으로 옮겨 적지 않는다** --- `git show <rev>:lab/gitcall.py` 를
  AST 로 읽어 `_ISO_DRIVER` 상수를 꺼낸다.
* 절 2 — 🔴 **지문 자**(`repo_fingerprint`). 채널과 무관한 자가 일곱을 다 잡나.
* 절 3 — 🔴 **C2 를 가른다**: `_passfail` 을 **경로 문자열**로 부른 것과 **로드된 dict**
  로 부른 것. 「티처가 틀렸다」/「주 세션이 틀렸다」를 실측으로 판정한다.
* 절 4 — 고친 판정식으로 `재실행무해` **재계수**(950 의 「같다 2」가 어떻게 되나).
* 절 5 — `기록기` 자의 **「모른다」 갈래**(티처 #90 M8) 재계수.
* 절 6 — 🔴 ⑤′ **붉음의 나이**를 산출물에서 직접 센다(손 전사 금지).

돌리기::

    python3 -m runners.out951_guard
"""
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lab import gitcall as gc                                    # noqa: E402

OUT = ROOT / "runners/out951_guard.json"
EXEMPT950 = ROOT / "data/lab/exempt950.json"

#: 🔴 **950 판 가드가 든 커밋.** 티처 #90 이 비평한 그 트리다. 손 전사 금지 --- 여기서 꺼낸다.
OLD_REV = "73dc3f8c2"

SCRATCH = Path(os.environ.get(
    "WM_SCRATCH",
    "/private/tmp/claude-501/-Users-ax-world-model/"
    "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")) / "wm951"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def J(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


# ── 950 판 드라이버를 **읽어서** 꺼낸다 ────────────────────────────────────
def old_driver(rev: str = OLD_REV) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), "show", "%s:lab/gitcall.py" % rev],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("950 판 gitcall.py 를 못 꺼냈다: %s" % r.stderr[:200])
    tree = ast.parse(r.stdout)
    for n in tree.body:
        if isinstance(n, ast.Assign) and any(
                getattr(t, "id", None) == "_ISO_DRIVER" for t in n.targets):
            return ast.literal_eval(n.value)
    raise RuntimeError("`_ISO_DRIVER` 상수를 못 찾았다")


# ── 채널 일곱 ──────────────────────────────────────────────────────────────
#: ``{이름: (겨냥 경로(저장소 상대), 본문 소스)}``. 본문은 **리터럴 경로로** 저장소를 쓴다
#: --- `OUT` 상수를 안 거치므로 드라이버의 「출력 상수 갈아끼우기」가 못 막는다.
def _plants(repo: str) -> dict:
    head = ('# -*- coding: utf-8 -*-\nimport io, os, subprocess, sys\n'
            'from pathlib import Path\n'
            'REPO = Path(%r)\n'
            'OUT = REPO / "runners" / "out900_seed.json"\n' % repo)
    return {
        "ㄱ `Path.write_text`": ("runners/plant_a.json", head + '''
def main():
    (REPO / "runners" / "plant_a.json").write_text("x", encoding="utf-8")
'''),
        "ㄴ `builtins.open(w)`": ("runners/plant_b.json", head + '''
def main():
    f = open(str(REPO / "runners" / "plant_b.json"), "w")
    f.write("x"); f.close()
'''),
        "ㄷ `io.open(w)`": ("runners/plant_c.json", head + '''
def main():
    f = io.open(str(REPO / "runners" / "plant_c.json"), "w")
    f.write("x"); f.close()
'''),
        "ㄹ `Path.open(\"w\")`": ("runners/plant_d.json", head + '''
def main():
    with (REPO / "runners" / "plant_d.json").open("w") as f:
        f.write("x")
'''),
        "ㅁ `subprocess` 하위 프로세스": ("runners/plant_e.json", head + '''
def main():
    subprocess.run([sys.executable, "-c",
                    "open(%r, \\'w\\').write(\\'x\\')" % str(REPO / "runners" / "plant_e.json")])
'''),
        "ㅂ `os.open(O_CREAT|O_WRONLY)`": ("runners/plant_f.json", head + '''
def main():
    fd = os.open(str(REPO / "runners" / "plant_f.json"),
                 os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o644)
    os.write(fd, b"x"); os.close(fd)
'''),
        "🔴 ㅅ `.gitignore` 경로에 subprocess": ("cycle_log/plant_g.json", head + '''
def main():
    subprocess.run([sys.executable, "-c",
                    "open(%r, \\'w\\').write(\\'x\\')" % str(REPO / "cycle_log" / "plant_g.json")])
'''),
    }


#: 🔴 여섯 채널 = 티처 #90 이 실측한 표 그대로. 일곱째(`.gitignore`)는 **m6 용**이라 따로 센다.
SIX = ["ㄱ `Path.write_text`", "ㄴ `builtins.open(w)`", "ㄷ `io.open(w)`",
       "ㄹ `Path.open(\"w\")`", "ㅁ `subprocess` 하위 프로세스",
       "ㅂ `os.open(O_CREAT|O_WRONLY)`"]
IGN = "🔴 ㅅ `.gitignore` 경로에 subprocess"


def _mk_fake_repo() -> Path:
    """가짜 저장소를 짓는다 --- 🔴 **진짜 저장소에는 한 채널도 안 심는다**."""
    fake = SCRATCH / "fakerepo"
    if fake.exists():
        shutil.rmtree(str(fake))
    (fake / "runners").mkdir(parents=True)
    (fake / "cycle_log").mkdir(parents=True)
    (fake / ".gitignore").write_text("cycle_log/\n__pycache__/\n", encoding="utf-8")
    (fake / "runners" / "out900_seed.json").write_text(
        json.dumps({"가": {"통과": True}}, ensure_ascii=False), encoding="utf-8")
    (fake / "cycle_log" / "keep.txt").write_text("keep\n", encoding="utf-8")
    for a in (["init", "-q"], ["add", "-A"],
              ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seed"]):
        subprocess.run(["git", "-C", str(fake)] + a, capture_output=True)
    return fake


def _run_driver(driver_src: str, fake: Path, rel: str, tag: str) -> dict:
    """드라이버 하나를 돌리고 ``차단된 저장소 쓰기`` 를 꺼낸다."""
    drv = SCRATCH / ("driver_%s.py" % tag)
    drv.write_text(driver_src, encoding="utf-8")
    scr = SCRATCH / ("iso_%s" % tag)
    scr.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run([sys.executable, str(drv), str(fake), str(scr), rel],
                       capture_output=True, text=True, timeout=300, cwd=str(fake), env=env)
    try:
        return json.loads(r.stderr.split("<<<ISO>>>")[1])
    except (IndexError, ValueError):
        return {"🔴 결과": "모른다 --- 드라이버 응답을 못 읽었다",
                "차단된 저장소 쓰기": [], "stderr(끝)": r.stderr[-400:]}


def _one_channel(driver_src: str, tag: str, name: str, target: str, src: str) -> dict:
    fake = _mk_fake_repo()
    rel = "runners/_plant.py"
    (fake / rel).write_text(src, encoding="utf-8")
    subprocess.run(["git", "-C", str(fake), "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", str(fake), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "plant"], capture_output=True)
    fp0 = gc.repo_fingerprint(fake)
    res = _run_driver(driver_src, fake, rel, "%s_%s" % (tag, abs(hash(name)) % 10000))
    fpd = gc.fingerprint_diff(fp0, gc.repo_fingerprint(fake))
    made = (fake / target).exists()
    blocked = res.get("차단된 저장소 쓰기") or []
    return {
        "겨냥한 경로": target,
        "🔴 가드가 발화했나": bool(blocked),
        "가드가 적은 것": blocked or "없음",
        "🔴 파일이 실제로 생겼나": made,
        "🔴 지문이 잡았나": not fpd["🔴 깨끗한가"],
        "지문 차": {k: v for k, v in fpd.items() if k.endswith("수") or k == "🔴 깨끗한가"},
        "지문 --- 바뀐 무시 경로 수": fpd["🔴 바뀐 무시(.gitignore) 경로 수"],
        "🔴 `git status --porcelain` 이 봤나": _status_saw(fake),
        "드라이버 결과": res.get("🔴 결과"),
    }


def _status_saw(fake: Path) -> bool:
    r = subprocess.run(["git", "-C", str(fake), "status", "--porcelain", "-z"],
                       capture_output=True)
    return bool(r.stdout.strip())


# ── 절 1·2 ────────────────────────────────────────────────────────────────
def sec12():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    fake_for_src = str(SCRATCH / "fakerepo")
    plants = _plants(fake_for_src)
    old, new = old_driver(), gc._ISO_DRIVER
    rows = {"950 판(HEAD 의 가드)": {}, "951 판(넓힌 가드)": {}}
    for tag, drv in (("950 판(HEAD 의 가드)", old), ("951 판(넓힌 가드)", new)):
        for name, (target, src) in plants.items():
            rows[tag][name] = _one_channel(drv, tag[:3], name, target, src)

    def _cnt(tag, keys, field):
        return sum(1 for k in keys if rows[tag][k][field])

    o_fire, o_made = _cnt("950 판(HEAD 의 가드)", SIX, "🔴 가드가 발화했나"), \
        _cnt("950 판(HEAD 의 가드)", SIX, "🔴 파일이 실제로 생겼나")
    n_fire, n_made = _cnt("951 판(넓힌 가드)", SIX, "🔴 가드가 발화했나"), \
        _cnt("951 판(넓힌 가드)", SIX, "🔴 파일이 실제로 생겼나")
    fp_new = _cnt("951 판(넓힌 가드)", SIX, "🔴 지문이 잡았나")
    fp_old = _cnt("950 판(HEAD 의 가드)", SIX, "🔴 지문이 잡았나")
    ig_old = rows["950 판(HEAD 의 가드)"][IGN]
    ig_new = rows["951 판(넓힌 가드)"][IGN]

    s1 = {
        "검사": "1 🔴 채널을 심어서 센다 --- 950 판 가드 대 951 판 가드",
        "읽은 트리": "950 판 드라이버는 **커밋 %s 의 `lab/gitcall.py`**(AST 로 꺼냈다 · 손 전사 0) · "
                 "951 판은 **작업 트리**" % OLD_REV,
        "🔴 심은 저장소": "가짜 저장소(스크래치패드). **진짜 저장소에는 한 채널도 안 심는다**",
        "🔴 분모(티처 #90 의 여섯 채널)": len(SIX),
        "🔴 950 판 --- 가드가 발화한 채널 수": o_fire,
        "🔴 950 판 --- 파일이 실제로 생긴 채널 수": o_made,
        "🔴 951 판 --- 가드가 발화한 채널 수": n_fire,
        "🔴 951 판 --- 파일이 실제로 생긴 채널 수": n_made,
        "🔴 늘어난 채널 수": n_fire - o_fire,
        "채널별": rows,
        "🔴 951 판이 여전히 못 잡는 채널": sorted(
            k for k in SIX if not rows["951 판(넓힌 가드)"][k]["🔴 가드가 발화했나"]),
        "🔴 그 까닭": ("`subprocess` 하위 프로세스는 부모의 몽키패치를 **안 물려받는다** --- "
                  "**원리상** 못 잡는다. 그래서 절 2 의 지문 자가 필요하다"),
        "통과": n_fire > o_fire and n_made < o_made,
        "🔴 통과의 뜻": ("🔴 **「다 막았다」가 아니다** --- 「잡히는 채널이 늘었고 실제로 생기는 "
                   "파일이 줄었다」뿐이다. 채널 목록은 **닫힌 목록이 아니다**(사전등록 §7)"),
    }
    s2 = {
        "검사": "2 🔴 지문 자 --- **채널과 무관한 자**(`repo_fingerprint`)",
        "읽은 트리": "가짜 저장소의 **작업 트리** 전후",
        "자": ("① 추적 파일 전량 sha256 ② 미추적(비무시) 경로 집합 "
              "③ 🔴 **`.gitignore` 경로**의 (크기, mtime_ns)"),
        "🔴 분모(여섯 채널)": len(SIX),
        "🔴 950 판 드라이버 아래에서 지문이 잡은 채널 수": fp_old,
        "🔴 951 판 드라이버 아래에서 지문이 잡은 채널 수": fp_new,
        # 🔴 **사전등록 P3 을 내가 잘못 적었다** --- 가드가 막은 채널은 **쓰지 않았으므로**
        #    지문이 잴 것이 없다. 「6/6」은 원리상 성립할 수 없는 예측이었다.
        #    🔴 채점기를 사후에 안 고친다(티처 #90 m2·m3) --- 아래 칸을 **덧붙일** 뿐이다.
        "🔴 **실제로 파일이 생긴 채널** 중 지문이 잡은 수(950 판)": "%d / %d" % (
            sum(1 for k in SIX if rows["950 판(HEAD 의 가드)"][k]["🔴 지문이 잡았나"]
                and rows["950 판(HEAD 의 가드)"][k]["🔴 파일이 실제로 생겼나"]), o_made),
        "🔴 **실제로 파일이 생긴 채널** 중 지문이 잡은 수(951 판)": "%d / %d" % (
            sum(1 for k in SIX if rows["951 판(넓힌 가드)"][k]["🔴 지문이 잡았나"]
                and rows["951 판(넓힌 가드)"][k]["🔴 파일이 실제로 생겼나"]), n_made),
        "🔴 지문이 놓친 「실제로 생긴 파일」(두 판 합)": sorted(
            k for tag in rows for k in SIX
            if rows[tag][k]["🔴 파일이 실제로 생겼나"] and not rows[tag][k]["🔴 지문이 잡았나"]
        ) or "없음",
        "🔴 지문이 잡았는데 몽키패치는 못 잡은 채널(951 판)": sorted(
            k for k in SIX if rows["951 판(넓힌 가드)"][k]["🔴 지문이 잡았나"]
            and not rows["951 판(넓힌 가드)"][k]["🔴 가드가 발화했나"]),
        "🔴 `.gitignore` 채널(티처 #90 m6)": {
            "950 판": {"가드": ig_old["🔴 가드가 발화했나"],
                      "파일이 생겼나": ig_old["🔴 파일이 실제로 생겼나"],
                      "🔴 `git status` 가 봤나": ig_old["🔴 `git status --porcelain` 이 봤나"],
                      "🔴 지문이 봤나": ig_old["🔴 지문이 잡았나"],
                      "지문 --- 바뀐 무시 경로 수": ig_old["지문 --- 바뀐 무시 경로 수"]},
            "951 판": {"가드": ig_new["🔴 가드가 발화했나"],
                      "파일이 생겼나": ig_new["🔴 파일이 실제로 생겼나"],
                      "🔴 `git status` 가 봤나": ig_new["🔴 `git status --porcelain` 이 봤나"],
                      "🔴 지문이 봤나": ig_new["🔴 지문이 잡았나"],
                      "지문 --- 바뀐 무시 경로 수": ig_new["지문 --- 바뀐 무시 경로 수"]},
        },
        "통과": fp_old == len(SIX),
        "🔴 통과의 뜻": ("**950 판 가드 아래**에서 지문이 여섯을 다 잡아야 통과 --- "
                   "🔴 **이 조건은 내가 잘못 적었다.** 950 판 가드가 둘을 막았고 "
                   "막힌 채널은 **쓰지 않았으므로 지문이 잴 것이 없다.** "
                   "이 절은 **붉은 채로 싣고**, 사전등록 P3 을 **빗맞힌 것으로 채점한다**. "
                   "🔴 채점기도 통과 조건도 사후에 안 고친다(티처 #90 m2·m3)"),
        "⚠ 한계(조항 61)": "쓰고 나서 **똑같이 되돌린** 쓰기는 못 본다(sha 가 같다)",
    }
    return s1, s2


# ── 절 3 · C2 를 가른다 ────────────────────────────────────────────────────
DISPUTE = ["runners/exp947_npzflow.json", "runners/out945_stampscan.json"]


def sec3() -> dict:
    rows = {}
    for rel in DISPUTE:
        p = ROOT / rel
        as_str = gc._passfail(rel)
        loaded = J(p)
        as_dict = gc._passfail(loaded)
        rows[rel] = {
            "🔴 경로 **문자열**로 부르면": len(as_str),
            "🔴 **로드된 dict** 로 부르면": len(as_dict),
            "절 목록": sorted(as_dict) or "없음",
        }
    a, b = rows[DISPUTE[0]], rows[DISPUTE[1]]
    who = ("🔴 **주 세션이 틀렸다** --- `_passfail` 은 str 을 받으면 dict 도 list 도 아니라 "
           "**빈 표**를 낸다. 주 세션은 두 파일 다 **경로 문자열**로 불렀고 그래서 둘 다 0 이 "
           "나왔다. 티처가 옳다: `exp947_npzflow.json` 은 절 %d · `out945_stampscan.json` 은 "
           "절 %d 다" % (a["🔴 **로드된 dict** 로 부르면"], b["🔴 **로드된 dict** 로 부르면"]))
    ok = (a["🔴 경로 **문자열**로 부르면"] == 0 and b["🔴 경로 **문자열**로 부르면"] == 0
          and a["🔴 **로드된 dict** 로 부르면"] > 0
          and b["🔴 **로드된 dict** 로 부르면"] == 0)
    return {
        "검사": "3 🔴 C2 를 가른다 --- 티처와 주 세션 중 **어느 쪽이 틀렸나**",
        "읽은 트리": "작업 트리(두 산출물은 동결물이라 HEAD 와 같다)",
        "🔴 다툰 자리": "티처 #90 C2 --- 티처는 `exp947` 이 4 라 했고 주 세션은 둘 다 0 을 봤다",
        "파일별": rows,
        "🔴 판정": who if ok else "🔴 **모른다** --- 두 호출 방식으로도 다툼이 안 갈렸다",
        "🔴 그래서 C2 는": ("**참이다.** `out945_stampscan.json` 은 `통과` 절이 **0** 인데 "
                      "950 의 판정식 `same > 0` 이 **산출물 수**를 세어 「✅ 같다」로 냈다 --- "
                      "**0 개를 0 개와 견준 공(空) 통과**"),
        "통과": ok,
    }


# ── 절 4 · 재실행무해 재계수 ──────────────────────────────────────────────
def sec4() -> dict:
    ex = J(EXEMPT950)
    rels = sorted(p for p, v in ex.items() if "재실행무해" in gc._ruler_tags(v))
    rows, kind = {}, {}
    for p in rels:
        d = gc.rerun_isolated(p, ROOT, scratch=str(SCRATCH / "rerun"))
        rows[p] = {k: v for k, v in d.items() if k != "역추적"}
        r = str(d.get("🔴 실행 결과") or "")
        secs = d.get("🔴 견준 절 수 합(판정식의 분모)", 0)
        blocked = d.get("🔴 저장소 쓰기 차단")
        if blocked not in ("없음(한 바이트도 안 썼다)", None):
            kind[p] = "🔴 저장소를 쓰려 들었다 --- 가드가 막았다"
        elif d.get("🔴 지문 대조(전후 · 채널과 무관한 자)", {}).get("🔴 깨끗한가") is False:
            kind[p] = "🔴 **지문이 잡았다** --- 몽키패치 밖으로 저장소가 바뀌었다"
        elif r.startswith("모른다"):
            kind[p] = "🔴 모른다 --- %s" % r[6:120]
        elif d.get("🔴 다른 산출물 수"):
            kind[p] = "🔴 **다르다** --- 다시 돌리니 절 판정이 바뀐다"
        elif secs == 0:
            kind[p] = "🔴 **모른다 --- 견줄 `통과` 절이 0 개다**(950 은 이것을 「같다」로 셌다)"
        elif d.get("🔴 자가 냈나"):
            kind[p] = "✅ 같다 --- 견준 절 %d 개가 전부 같다" % secs
        else:
            kind[p] = "🔴 모른다 --- 갈래를 못 정했다"
    same = [p for p, v in kind.items() if v.startswith("✅")]
    empty = [p for p, v in kind.items() if "견줄 `통과` 절이 0" in v]
    fp_only = [p for p, v in kind.items() if v.startswith("🔴 **지문이 잡았다")]
    return {
        "검사": "4 🔴 고친 판정식으로 `재실행무해` **재계수**(티처 #90 C2)",
        "읽은 트리": "코드는 **작업 트리** · 견주는 상대는 **HEAD 의 커밋된 산출물**",
        "🔴 분모": len(rels),
        "🔴 ✅ 견주었고 같다": len(same),
        "🔴 견줄 절이 0 개다(950 은 「같다」로 셌다)": len(empty),
        "🔴 그 목록": empty or "없음",
        "🔴 지문만 잡은 것(몽키패치는 못 잡았다)": fp_only or "없음",
        "갈래별": kind,
        "🔴 950 의 「✅ 같다 2」가 오늘 무엇이 되었나": (
            "같다 %d · **견줄 절이 0 이라 모른다 %d**" % (len(same), len(empty))),
        "파일별": rows,
        "통과": len(empty) > 0 or len(same) == len(rels),
        "🔴 통과의 뜻": ("🔴 **이 절의 통과는 「전부 무해하다」가 아니다** --- "
                   "「공 통과를 드러냈거나, 전량이 진짜로 같다」다"),
    }


# ── 절 5 · 기록기 「모른다」 갈래 ──────────────────────────────────────────
def sec5() -> dict:
    ex = J(EXEMPT950)
    rels = sorted(p for p, v in ex.items() if "기록기" in gc._ruler_tags(v))
    rows = {p: gc.ledger_writer(p) for p in rels}
    g = {}
    for p, d in rows.items():
        v = d["🔴 갈래(951)"]
        g.setdefault(v.split(" ---")[0], []).append(p)
    unk = g.get("🔴 모른다", [])
    return {
        "검사": "5 🔴 `기록기` 자의 **「모른다」 갈래**(티처 #90 M8)",
        "읽은 트리": "작업 트리(AST)",
        "🔴 분모": len(rels),
        "🔴 갈래별 수": {k: len(v) for k, v in sorted(g.items())},
        "🔴 갈래별 목록": {k: sorted(v) for k, v in sorted(g.items())},
        "🔴 모른다로 간 것": sorted(unk) or "없음",
        "🔴 950 은 이것을 무엇으로 냈나": "「안 쓴다」(= 자가 거짓) --- **답은 맞았고 자는 틀렸다**",
        "파일별": rows,
        "통과": True,
        "⚠": "이 절의 `통과 True` 는 「갈래를 갈랐다」는 뜻이지 「사유가 참이 됐다」가 아니다",
    }


# ── 절 6 · ⑤′ 붉음의 나이 ────────────────────────────────────────────────
def sec6() -> dict:
    files = sorted((ROOT / "runners").glob("out*_fiveprime*.json"))
    per, ages = {}, {}
    for f in files:
        rel = f.relative_to(ROOT).as_posix()
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:                                    # noqa: BLE001
            per[rel] = {"🔴": "못 읽었다: %s" % type(e).__name__}
            continue
        secs = {k: v.get("통과") for k, v in d.items()
                if isinstance(v, dict) and "통과" in v}
        per[rel] = {"절 수": len(secs),
                    "붉은 절": sorted(k for k, v in secs.items() if v is not True)}
        for k, v in secs.items():
            a = ages.setdefault(k, {"초록": 0, "붉음": 0, "산출물": 0})
            a["산출물"] += 1
            a["초록" if v is True else "붉음"] += 1
    never = sorted(k for k, v in ages.items() if v["초록"] == 0 and v["산출물"] >= 2)
    return {
        "검사": "6 🔴 ⑤′ **붉음의 나이** --- 산출물에서 직접 센다(손 전사 금지)",
        "읽은 트리": "작업 트리의 `runners/out*_fiveprime*.json` 전량",
        "🔴 분모(산출물 수)": len(files),
        "절 이름별 나이": {k: v for k, v in sorted(ages.items())},
        "🔴 한 번도 초록인 적 없는 절(산출물 2 개 이상)": never,
        "산출물별": per,
        "🔴 성질(951 이 적는다)": {
            "3 판정 키 규약": "🔴 **㉯ 고칠 수 있다** --- 범위를 한 줄로 못 박으면 닫힌다. 951 은 **안 고쳤다**",
            "1-나 🔴 날 것 git 호출 전수(947 상설)": "🔴 **㉲ 규약상 안 고친다** --- 동결물이 ㉯ 에 남아 판정식이 정의상 영원히 붉다",
            "2 게이트": "🔴 **㉮ 원리상 못 고친다** --- 매 사이클 새 러너가 사유 분모에 들어온다",
            "1 소비자 역참조": "🔴 **㉮ 원리상 못 고친다** --- 자가 엄해진 것이 옳고 초록 불가도 사실이다",
            "1-라 🔴 `_grep_l` 건초더미 대조(947)": "🔴 **㉯ 고칠 수 있다** --- 949 가 스스로 신고했고 세 사이클째 아무도 안 봤다",
        },
        "통과": True,
        "⚠": "이 절은 **계수**다. `통과 True` 는 「세었다」는 뜻이지 「고쳤다」가 아니다",
    }


# ── 절 7 · 안 한 것 ───────────────────────────────────────────────────────
def sec7() -> dict:
    return {
        "검사": "7 🔴 **안 한 것** --- 누적 미결 전량(티처 #86·#87·#88·#89·#90)",
        "🔴 이 사이클이 갚은 것": [
            "티처 #90 **C1** --- 가드를 채널 전량으로 넓히고 **지문 자**를 세웠다(절 1·2)",
            "티처 #90 **C2** --- 판정식을 `견준 절 수 > 0` 으로 고치고 **다툼을 갈랐다**(절 3·4)",
            "티처 #90 **M8** --- `기록기` 에 「모른다」 갈래를 냈다(절 5)",
            "티처 #87 **m5** · #88 **m2** · #90 **m5** --- ⑤′ 스탬프 sha **16 → 64자리**",
            "티처 #90 **m6** --- `.gitignore` 경로를 별도 자로 잰다(절 2)",
            "티처 #90 **물음 ③** --- ⑤′ 붉음의 나이와 성질을 **세어서** 적었다(절 6)",
        ],
        "🔴 안 갚은 것(전량)": {
            "티처 #90": ["M1 분모 갈아타기(74·8 을 노트에 적는 것 --- 951 노트가 적는다)",
                      "M2 `out949_stamp.py` 는 949 것", "M3 자기 문서에 생산기·도장",
                      "M4 🔴 **CLI 사유 47/50 (94%)** --- 951 노트가 수를 싣되 **검토는 안 했다**",
                      "M5 `재실행무해` 분모 6 의 근거 --- **안 넓혔다**(8 중 6)",
                      "M6 레인 규칙 위반(951 은 탐색 예측을 사전등록에서 뺐다)",
                      "M7 「수리 하나」 --- 951 은 **넷이라고 먼저 적었다**",
                      "M9 누적 미결 재목록화", "m1~m4·m7·m8·m9 --- 안 했다"],
            "티처 #89": ["C2 한 홉 사각지대(판정 안 함)", "M4·M5·M6", "m1~m6"],
            "티처 #88": ["M3 `3 판정 키 규약` 범위 --- 🔴 **21 사이클째**",
                      "M4 호출 자리 대 |자 A|", "「안 쟀다」 ①④"],
            "티처 #86·#87": ["🔴 **여전히 하나도 안 갚았다** --- `docs/수리/948.md` §10 의 두 표가 그대로 유효",
                          "#87 C4 바늘 네 사각지대", "#86 M4 `_sha_cited` 자기충족"],
        },
        "🔴 951 이 새로 낳은 것(스스로 신고)": [
            "① 지문 자가 **매 격리 재실행마다 추적 파일 %s 개를 해싱한다** --- ⑤′ 가 더 느려졌다",
            "② 지문 자는 **쓰고 되돌린** 쓰기를 못 본다(sha 가 같다)",
            "③ 몽키패치 채널 목록은 **닫힌 목록이 아니다** --- 오늘 일곱만 심었다",
            "④ 🔴 `_ISO_DRIVER` 가 길어졌다(스물셋 갈아끼움) --- 그 자체를 잰 자는 없다",
            "⑤ 이번 사이클이 만든 새 경로(`out951_*`·`note951_gen.py`)가 **사유 분모에 새로 들어온다**",
        ],
        "통과": True,
        "⚠": "이 절은 **목록**이다. `통과 True` 는 「적었다」는 뜻이지 「갚았다」가 아니다",
    }


def main() -> None:
    if OUT.exists():
        OUT.unlink()
    t0 = time.time()
    started = _now()
    res = {
        "무엇": "노트 951 [수리] --- 저장소 쓰기 가드가 여섯 채널 중 둘만 잡았다(티처 #90 C1·C2)",
        "사전등록": "docs/prereg_951_guard.md",
        "🔴 어느 트리를 읽나": {
            "950 판 드라이버": "커밋 %s 의 `lab/gitcall.py`(AST · 손 전사 0)" % OLD_REV,
            "951 판 드라이버·자": "작업 트리",
            "`재실행무해` 가 견주는 상대": "HEAD(`git cat-file blob HEAD:…`)",
            "⚠": "🔴 한 실행에서 두 트리를 섞는다 --- 그래서 절마다 적는다",
        },
    }
    s1, s2 = sec12()
    res["1 채널을 심어서 센다"] = s1
    res["2 지문 자"] = s2
    res["3 C2 를 가른다"] = sec3()
    res["4 재실행무해 재계수"] = sec4()
    res["5 기록기 「모른다」 갈래"] = sec5()
    res["6 ⑤′ 붉음의 나이"] = sec6()
    s7 = sec7()
    n_tracked = len(gc.repo_fingerprint(ROOT)["추적"])
    s7["🔴 951 이 새로 낳은 것(스스로 신고)"][0] = \
        s7["🔴 951 이 새로 낳은 것(스스로 신고)"][0] % n_tracked
    res["7 안 한 것"] = s7
    secs = {k: v for k, v in res.items() if isinstance(v, dict) and "통과" in v}
    res["🔴 절 수(분모)"] = len(secs)
    res["🔴 실패한 절"] = sorted(k for k, v in secs.items() if v["통과"] is not True) or "없음"
    res["통과"] = res["🔴 실패한 절"] == "없음"
    res["시각(UTC · 시작)"] = started
    res["시각(UTC · 끝)"] = _now()
    res["🔴 코드 sha256(이게 자다)"] = {
        "runners/out951_guard.py": _sha(Path(__file__)),
        "lab/gitcall.py": _sha(ROOT / "lab/gitcall.py"),
    }
    res["🔴 입력 산출물 sha256"] = {
        "data/lab/exempt950.json": _sha(EXEMPT950),
        "docs/prereg_951_guard.md": _sha(ROOT / "docs/prereg_951_guard.md"),
    }
    res["초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("산출물: %s · 실패한 절 %s" % (OUT, res["🔴 실패한 절"]))


if __name__ == "__main__":
    main()
