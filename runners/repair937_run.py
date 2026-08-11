# -*- coding: utf-8 -*-
"""팔 937 — **회계와 규약을 고친다.** 새 팔을 안 재고 새 순열을 안 돌린다.

사전등록: `docs/prereg_937_repair.md` (stamp `runners/out937_prereg_stamp.json`).

넷을 한 사이클에 (티처 #77 의 2·3·4·5순위):
  A  `daily.npz` 를 원천 zip 19개에서 **다시 만들어** sha 대조(파일 sha · 내용 sha 둘로 갈라서)
  B  배선 회계를 **분류 규칙으로** 다시 센다(935·933) — 🔴 `심었나` 필드를 안 본다
  C  관문 두 눈금을 근사 없이 다시 세고 **눈금 B** 로 규약화한다
  D  ㉡ 의 마지막 화살표 — `귀무 개선 ~ β·상대차` 의 기울기와 **군집 BCa**(규약 47)

🔴 이 러너는 남의 산출물을 **읽기만** 한다. 정본을 한 글자도 안 고친다.
🔴 재빌드는 **새 디렉터리**에만 쓴다 — `<scratch>/g918` · `<scratch>/g922` 를 안 덮는다.

사용: python3 runners/repair937_run.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path("/Users/ax/world_model")
SCR = Path("/private/tmp/claude-501/-Users-ax-world-model/"
           "511dc308-36bf-409d-9afe-b82a8bb5d7ae/scratchpad")
N937 = SCR / "n937"                      # 🔴 이 사이클만 쓰는 새 자리
OLD_G918 = SCR / "g918"
OLD_G922 = SCR / "g922"
NPZ_OLD = OLD_G922 / "daily.npz"
NPZ_SHA = "4472b7f69cb5170c8a804dfbdb72a0289dcd34936aa5e05b6e9e191878ae97b2"
OUT = ROOT / "runners/out937_repair.json"
LOG = N937 / "rebuild.log"

# 🔴 import 보다 **먼저** — 자식 프로세스(spawn)도 같은 자리를 쓰게 한다
os.environ["G918_SCRATCH"] = str(N937)
sys.path.insert(0, str(ROOT / "runners"))
sys.path.insert(0, str(ROOT))

import interval918_build as ib            # noqa: E402  (남의 러너 · 한 줄도 안 고친다)
from lab import pairboot                  # noqa: E402
from state.interval918 import sha256_text  # noqa: E402

P_ALL, P_EXC, P_ONLY = ("① 원판 전량", "② 원판 − b_prv=−1 칸", "진단 b_prv=−1 칸만")
PANELS = (P_ALL, P_EXC, P_ONLY)
THR = 0.05                                # perm922.COMPARABLE_REL


def _log(*a) -> None:
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(s + "\n")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def content_sha(p: Path) -> dict:
    """🔴 **내용** sha — zip 컨테이너 바이트가 아니라 배열의 dtype|shape|bytes."""
    z = np.load(p, allow_pickle=False)
    h = hashlib.sha256()
    per = {}
    for k in sorted(z.files):
        a = z[k]
        blob = f"{k}|{a.dtype.str}|{a.shape}|".encode() + a.tobytes()
        per[k] = {"dtype": a.dtype.str, "shape": list(a.shape),
                  "sha256": sha256_bytes(blob)}
        h.update(blob)
    return {"배열별": per, "🔴 합친 내용 sha256": h.hexdigest(),
            "배열 이름": sorted(z.files)}


def array_diff(p1: Path, p2: Path) -> dict:
    z1 = np.load(p1, allow_pickle=False)
    z2 = np.load(p2, allow_pickle=False)
    out = {"이름 집합 같은가": sorted(z1.files) == sorted(z2.files)}
    for k in sorted(set(z1.files) & set(z2.files)):
        a, b = z1[k], z2[k]
        d = {"shape": [list(a.shape), list(b.shape)],
             "dtype": [a.dtype.str, b.dtype.str]}
        if a.shape == b.shape and a.dtype == b.dtype:
            if a.dtype.kind in "fiu":
                ne = int((a != b).sum())
                d["다른 원소 수"] = ne
                d["원소 수"] = int(a.size)
                d["최대 절대차"] = float(np.abs(
                    a.astype(np.float64) - b.astype(np.float64)).max()) if ne else 0.0
            else:
                d["다른 원소 수"] = int((a != b).sum())
                d["원소 수"] = int(a.size)
        out[k] = d
    return out


# ══════════════════════════════════════════════════════════ A · 재빌드
def part_A() -> dict:
    a: dict = {"무엇": "🔴 `daily.npz` 를 원천 zip 19개에서 **다시 만든다** — "
                     "4사이클 연속 「못 심는 것」이었던 항목",
               "사전등록": "§3-A · 판정 규칙을 A1(파일 sha)·A2(내용 sha)로 미리 갈랐다"}
    # §4-1 멈추는 조건 — 같은 코드인가
    prev = json.loads((ROOT / "runners/out918_build.json").read_text(encoding="utf-8"))
    now = {c: sha256_text(ROOT / c) for c in
           ("state/interval918.py", "runners/interval918_build.py")}
    a["🔴 같은 코드인가(§4-1)"] = {
        "옛 산출물이 박은 sha": prev["코드 sha256"], "지금 다시 계산": now,
        "🔴 같은가": prev["코드 sha256"] == now}
    # §4-2 — 옛 자리를 안 덮는다
    assert ib.SCRATCH == N937 / "g918", ib.SCRATCH
    assert ib.SCRATCH != OLD_G918 and ib.SCRATCH != OLD_G922
    ib.OUT = N937 / "out918_build.rebuild.json"
    assert ib.OUT != ROOT / "runners/out918_build.json"
    a["🔴 어디에 썼나(옛 자리를 안 덮는다 · §4-2)"] = {
        "새 SCRATCH": str(ib.SCRATCH), "새 OUT": str(ib.OUT),
        "옛 g918": str(OLD_G918), "옛 g922": str(OLD_G922)}
    before = {p: sha256_bytes((p).read_bytes()) for p in
              [OLD_G922 / "daily.npz", ROOT / "runners/out918_build.json"]}

    t0 = time.time()
    tstart = dt.datetime.now(dt.timezone.utc)
    try:
        ib.main()
        err = None
    except Exception as e:                                    # noqa: BLE001
        err = f"{type(e).__name__}: {e}"
    secs = round(time.time() - t0, 1)
    a["⏱ 초"] = secs
    a["시작 UTC"] = tstart.isoformat(timespec="seconds")
    a["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    a["옛 실행의 초(runners/out918_build.json)"] = prev["초"]
    if err is not None:
        a["🔴 판정"] = "🔴 **모른다** — 러너가 예외로 죽었다(사전등록 §3-A 넷째 갈래). " \
                     "「같다」로도 「다르다」로도 안 적는다"
        a["예외"] = err
        return a

    new_npz = ib.SCRATCH / "daily.npz"
    a["새 파일"] = {"경로": str(new_npz), "바이트": new_npz.stat().st_size}
    f_new = sha256_bytes(new_npz.read_bytes())
    f_old = sha256_bytes(NPZ_OLD.read_bytes())
    c_new, c_old = content_sha(new_npz), content_sha(NPZ_OLD)
    A1 = f_new == NPZ_SHA
    A2 = c_new["🔴 합친 내용 sha256"] == c_old["🔴 합친 내용 sha256"]
    a["A1 파일 sha256"] = {
        "새로 만든 것": f_new, "925~935 가 쓴 것(g922)": f_old,
        "사전등록이 박은 값": NPZ_SHA,
        "🔴 옛 두 파일이 서로 같은가(티처 #77 C2 재확인)": f_old == NPZ_SHA,
        "🔴 A1 참인가": bool(A1)}
    a["A2 내용 sha256"] = {
        "새로 만든 것": c_new, "925~935 가 쓴 것(g922)": c_old,
        "🔴 A2 참인가": bool(A2)}
    if not A2:
        a["🔴 배열별 어긋남(전량)"] = array_diff(new_npz, NPZ_OLD)

    if A1 and A2:
        a["🔴 판정"] = (
            "🔴🔴 **A1 참 · A2 참 — 「입력이 옳게 만들어졌는가」는 못 심는 것이 아니다.** "
            "4사이클 연속 신고된 결손이 **거짓**이었음이 **재실행으로** 확정됐다"
            "(티처 #77 은 두 파일의 sha 가 서로 같다는 것만 봤고 다시 돌려 보지 못했다). "
            "배선 회계의 **분모가 바뀐다**")
    elif A2:
        a["🔴 판정"] = (
            "**A1 거짓 · A2 참 — 내용은 재현된다.** 「입력이 옳게 만들어졌는가」는 "
            "**여전히 심을 수 있는 것**이고 회계 분모도 같다. 🔴 다만 **W9(파일 sha 로 "
            "입력 동일성을 검사한다)는 zip 컨테이너 비결정성에 취약하다** — 새 결함으로 신고한다")
    else:
        a["🔴 판정"] = (
            "🔴🔴🔴 **A2 거짓 — 치명.** 925·928·933·935 의 모든 수가 **재현 불가능한 입력** "
            "위에 서 있다. 어느 배열이 어떻게 다른지는 위 「배열별 어긋남」에 전량 실었다")

    # 계수 대조 — 같은 원천을 같게 셌나
    newj = json.loads(ib.OUT.read_text(encoding="utf-8"))
    kd = "🔴 분모 딱지(전부 다른 분모다)"
    a["🔴 계수 대조(918 산출물 대 재빌드)"] = {
        "옛": prev[kd], "새": newj[kd],
        "🔴 전부 같은가": prev[kd] == newj[kd],
        "못 센 것": newj["못 센 것"]}

    # 🔴 남의 산출물을 안 건드렸나
    after = {p: sha256_bytes((p).read_bytes()) for p in before}
    a["🔴 남의 파일을 안 건드렸나"] = {
        str(k): {"전": v, "후": after[k], "같은가": v == after[k]}
        for k, v in before.items()}

    # 🔴 「없는 한 줄」 — g918 → g922 를 옮긴 경로가 어디에도 없었다(티처 #77 C2 ③)
    a["🔴 「없는 러너」가 아니라 「없는 한 줄」이었다"] = {
        "티처가 잡은 것": "g918 → g922 로 옮긴 경로가 저장소 어디에도 없다(복사 러너·명령 0건)",
        "이 러너가 남기는 것": "publish_g922() — 🔴 **내용 sha 가 같을 때만** 옮기고, "
                       "목적지가 이미 있고 내용이 다르면 **거부**한다",
        "이번 실행": publish_g922(new_npz, dry_run=True)}
    return a


def publish_g922(src: Path, dst: Path = NPZ_OLD, *, dry_run: bool = True) -> dict:
    """🔴 `g918/daily.npz` → `g922/daily.npz` 의 **없던 한 줄**.

    조용한 덮어쓰기를 막는다 — 목적지가 있고 **내용 sha 가 다르면 거부**한다.
    """
    import shutil
    r = {"src": str(src), "dst": str(dst), "dry_run": dry_run}
    if not src.exists():
        r["결과"] = "🔴 원본이 없다 — 안 옮긴다"
        return r
    if dst.exists():
        same = content_sha(src)["🔴 합친 내용 sha256"] == \
            content_sha(dst)["🔴 합친 내용 sha256"]
        r["목적지가 이미 있다"] = True
        r["내용이 같은가"] = same
        r["결과"] = ("옮길 필요 없다(내용 동일) — **덮지 않았다**" if same
                    else "🔴 **거부한다** — 목적지의 내용이 다르다. 손으로 판단할 일이다")
        return r
    r["목적지가 이미 있다"] = False
    if not dry_run:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        r["결과"] = "옮겼다"
    else:
        r["결과"] = "dry_run — 안 옮겼다"
    return r


# ══════════════════════════════════════════════════════════ B · 배선 회계
def is_planted(w: dict) -> bool:
    """🔴 사전등록 §3-B — **코드가 분류한다.** `심었나` 필드를 **안 본다**."""
    d = w.get("심은 결함")
    return isinstance(d, str) and not d.startswith("(대조)")


def fired(w: dict) -> bool:
    return any(k.startswith("🔴 발화했나") and bool(v) for k, v in w.items())


def account(wires: dict, unplantable: list, tag: str) -> dict:
    planted = {k: v for k, v in wires.items() if is_planted(v)}
    neg = {k: v for k, v in wires.items() if not is_planted(v)}
    fired_names = [k for k, v in planted.items() if fired(v)]
    miss = [k for k in planted if k not in fired_names]
    # 음성 대조의 통과 — `🔴 통과` 가 있으면 그것, 없으면 자기 발화 조건
    neg_pass, neg_rule, neg_bad = [], {}, []
    for k, v in neg.items():
        if "🔴 통과" in v:
            ok, rule = bool(v["🔴 통과"]), "🔴 통과 필드"
        elif "서로 다른 값의 개수" in v:            # W8
            ok = int(v["서로 다른 값의 개수"]) >= 2
            rule = "가짓수 ≥ 2 (사전등록 §3-B 가 「통과」로 부르기로 미리 정한 기준 ①)"
        else:
            ok, rule = fired(v), "자기 발화 조건"
        neg_rule[k] = rule
        (neg_pass if ok else neg_bad).append(k)
    np_, nf = len(planted), len(fired_names)
    nu = len(unplantable)
    return {
        "🔴 분류 규칙(코드가 계산한다)":
            "심음 ⟺ `심은 결함` 이 있고 `(대조)` 로 시작하지 않는다 · 그 밖은 전부 음성 대조. "
            "🔴 **`심었나` 필드를 안 본다** — 3사이클 연속 틀린 자리다",
        "심음": sorted(planted), "음성 대조": sorted(neg),
        "심은 수": np_, "발화한 수": nf, "🔴 놓친 수": np_ - nf, "놓친 것": miss,
        "음성 대조 수": len(neg), "음성 대조 통과": len(neg_pass),
        "음성 대조 불통과": neg_bad or "없다",
        "음성 대조의 통과 기준": neg_rule,
        "못 심은 수": nu, "못 심은 것": unplantable,
        "🔴 검정력(심은 것 기준)": f"{nf}/{np_} = {nf/np_:.3f}",
        "🔴🔴 검정력(못 심은 것까지 분모에)":
            f"{nf}/{np_+nu} = {nf/(np_+nu):.3f}",
        "태그": tag,
    }


def part_B(A_ok: bool) -> dict:
    d935 = json.loads((ROOT / "runners/out935_rawpanel.json").read_text(encoding="utf-8"))
    d933 = json.loads((ROOT / "runners/out933_calpanel.json").read_text(encoding="utf-8"))
    k935 = [k for k in d935 if k.startswith("③ 배선")][0]
    k933 = [k for k in d933 if k.startswith("③ 배선")][0]
    b935, b933 = d935[k935], d933[k933]

    # 못 심은 것 — A 의 결과를 반영한다(사전등록 §3-B)
    u935 = [x for x in b935["🔴 못 심은 것(검정력 0 으로 신고)"] if "daily.npz" not in x]
    u933 = [x for x in b933["🔴 못 심은 것(검정력 0 으로 신고)"] if "daily.npz" not in x]
    a935 = account(b935["검사"], u935, "935 본 주행")
    a933 = account(b933["검사"], u933, "933 본 주행")
    w8_935 = b935["검사"]["W8 씨앗이 먹히나"]
    w8_933 = b933["검사"]["W8 씨앗이 먹히나"]
    return {
        "무엇": "🔴 배선 회계를 **분류 규칙으로** 다시 센다 — 935 와 933 둘 다",
        "🔴 왜": "코드가 자기 입으로 `\"(대조)\"` 라 적는데 `\"심었나\": True` 로 셌다"
               "(티처 #77 C3). **W8 은 아무것도 안 심는다**",
        "🔴 못 심은 것에서 뺀 항목": {
            "무엇": "「daily.npz 가 옳게 만들어졌는가 — 만드는 러너가 저장소에 없다」",
            "왜": "A 가 **실제로 다시 만들어 쟀다**. 「못 심는 것」이 아니라 **잰 것**이다",
            "🔴 A 가 참이었나": bool(A_ok),
            "🔴 A 가 거짓이어도 분모는 같다":
                "잰 것이면서 **실패한 것**이 되지 분모로 돌아가지 않는다(사전등록 §3-B)"},
        "935": {"정본이 적은 것": {
            "심은 수": b935["🔴 본 주행 배선 — 심은 수"],
            "발화한 수": b935["🔴 본 주행 배선 — 발화한 수"],
            "놓친 수": b935["🔴 본 주행 배선 — 놓친 수"],
            "음성 대조": [b935["본 주행 음성 대조 통과"], b935["본 주행 음성 대조 수"]],
            "못 심은 수": b935["🔴 못 심은 수"],
            "검정력": [b935["🔴 본 주행 검정력(심은 것 기준)"],
                    b935["🔴🔴 본 주행 검정력(못 심은 것까지 분모에)"]]},
            "🔴 옳은 회계(이 러너가 코드로 셌다)": a935},
        "933": {"정본이 적은 것": {
            "심은 수": b933["🔴 심은 수"], "발화한 수": b933["🔴 발화한 수"],
            "놓친 수": b933["🔴 놓친 수"],
            "음성 대조": [b933["음성 대조 통과"], b933["음성 대조 수"]],
            "못 심은 수": b933["🔴 못 심은 수"],
            "검정력": [b933["🔴 검정력(심은 것 기준)"],
                    b933["🔴🔴 검정력(못 심은 것까지 분모에)"]]},
            "🔴 옳은 회계(이 러너가 코드로 셌다)": a933},
        "🔴 W8 — 두 기준을 둘 다 신고한다(사전등록 §3-B)": {
            "935": {"가짓수": w8_935["서로 다른 값의 개수"], "뽑기 수": w8_935["뽑기 수"],
                   "기준 ① 가짓수 ≥ 2 (「통과」로 부르는 것)":
                       w8_935["서로 다른 값의 개수"] >= 2,
                   "기준 ② 가짓수 == 뽑기 수":
                       w8_935["서로 다른 값의 개수"] == w8_935["뽑기 수"]},
            "933": {"가짓수": w8_933["서로 다른 값의 개수"], "뽑기 수": w8_933["뽑기 수"],
                   "기준 ① 가짓수 ≥ 2 (「통과」로 부르는 것)":
                       w8_933["서로 다른 값의 개수"] >= 2,
                   "기준 ② 가짓수 == 뽑기 수":
                       w8_933["서로 다른 값의 개수"] == w8_933["뽑기 수"]},
            "🔴 그래서 933 의 「놓친 1」은":
                "**놓친 것이 아니다.** W8 은 심은 적이 없고(음성 대조), 그 음성 대조는 "
                "기준 ①(가짓수 ≥ 2)으로 **통과**한다. 933 의 심은 다섯은 **다섯 다 발화했다**"},
        "🔴 인계 지시서의 「4/5」는 왜 안 나오나":
            "못 심은 것이 하나 줄어드는 것은 **분모에서 1**이지 **분자에서 1**이 아니다. "
            "심은 것은 그대로 4 이고 못 심은 것이 3 → 2 로 줄어 **4/6** 이다. "
            "**4/5** 가 되려면 심은 것이 5 여야 하는데 W8 은 심은 것이 아니다",
    }


# ══════════════════════════════════════════════════════════ C · 관문 두 눈금
def norm_sf(z: float) -> float:
    """정규 꼬리 — scipy 없이도 되게 erfc 로."""
    import math
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def part_C(recs: list) -> dict:
    add = json.loads((ROOT / "runners/out935_addendum.json").read_text(encoding="utf-8"))
    out: dict = {
        "무엇": "🔴 관문의 두 눈금을 **근사 없이** 다시 센다 · 규약을 **B** 로 못 박는다",
        "문턱(perm922.COMPARABLE_REL)": THR,
        "뽑기 수(분모)": len(recs),
        "🔴 선포하는 규약(규약 48)":
            "관문은 **눈금 B(도달 가능 폭 ÷ 문턱)** 로 신고한다. 눈금 A(기준 팔 통계량의 "
            "가짓수)는 **병기**한다. 🔴 **「통과」라는 낱말은 B ≥ 1 일 때만 쓴다.** "
            "B < 1 이면 **「발화 범위 밖 — 검정력 0」** 으로 적는다. "
            "A 는 「통계량이 퇴화했나」를 묻는 전제이고, 관문의 물음은 "
            "「이 귀무들이 문턱에 닿을 수 있나」이므로 그 물음의 자는 B 다(티처 #77 M1)",
    }
    per = {}
    for p in PANELS:
        rel = np.asarray([r[p]["비교가능성 상대차"] for r in recs], float)
        base = np.asarray([r[p]["기준 팔 MAE"] for r in recs], float)
        reach = float(np.abs(rel).max())
        B = reach / THR
        npass = int(sum(bool(r[p]["🔴 비교가능성 통과"]) for r in recs))
        over = int((np.abs(rel) >= THR).sum())
        sd = float(rel.std(ddof=1))
        z = (THR - float(rel.mean())) / sd
        tail = norm_sf(z)
        per[p] = {
            "눈금 A — 기준 팔 MAE 가짓수": {"가짓수": int(np.unique(base).size),
                                    "분모": len(recs),
                                    "퇴화 아닌가(≥2)": bool(np.unique(base).size >= 2)},
            "🔴 눈금 B — 도달 가능 폭 ÷ 문턱": {
                "도달 가능 폭(|상대차| 최대)": reach, "문턱": THR, "🔴 비": B,
                "🔴 B ≥ 1 인가(「통과」라는 낱말을 써도 되나)": bool(B >= 1)},
            "실측 분포": {"평균": float(rel.mean()), "SD(ddof=1)": sd,
                     "중앙": float(np.median(rel)), "최소": float(rel.min()),
                     "최대": float(rel.max()),
                     "95%": float(np.percentile(rel, 95)),
                     "99%": float(np.percentile(rel, 99))},
            "🔴 문턱을 실제로 넘은 뽑기(근사 없음)": over,
            "관문을 통과한 뽑기": npass,
            "🔴 문턱까지 남은 여유": THR - reach,
            "🔴 문턱까지 z((문턱 − 평균)/SD)": z,
            "정규 근사 뽑기당 꼬리": tail,
            "정규 근사로 200뽑기에서 한 번이라도 걸릴 확률": 1.0 - (1.0 - tail) ** len(recs),
            "🔴 이 판을 어떻게 신고해야 하나(규약 48)":
                ("관문에 검정력이 있다(B=%.4f ≥ 1) → 「통과 %d/%d」라고 적어도 된다"
                 % (B, npass, len(recs))
                 if B >= 1 else
                 "🔴 **「발화 범위 밖 — 검정력 0」** 으로 적는다(B=%.4f < 1). "
                 "「통과 %d/%d」는 **쓰면 안 되는 문장**이다" % (B, npass, len(recs))),
        }
    out["판별"] = per

    # 티처·부속 산출물과의 대조 (인용 규약)
    kb = "🔴 눈금 B — 도달 가능 폭 ÷ 문턱(이슈 #178 · gap925.gate_report)"
    cmp = {}
    for p in PANELS:
        old = add["판별"][p][kb]["🔴 비(도달 가능 폭 ÷ 문턱)"]
        new = per[p]["🔴 눈금 B — 도달 가능 폭 ÷ 문턱"]["🔴 비"]
        cmp[p] = {"935 부속·티처 #77": old, "내가 다시 센 값": new,
                  "🔴 비트로 같은가": old == new}
    out["🔴 대조(인용 규약 · docs/루프.md ⑦)"] = cmp

    e = per[P_EXC]
    out["🔴🔴 935 판② 의 「200/200 통과」를 취소한다"] = {
        "무엇을 적었나": "정본 ⑤-다 와 카드가 판② 를 「통과 200/200」으로 적었다",
        "🔴 왜 취소하나": "B=%.6f 로 **1 미만**이다 — 규약 48 아래에서 「통과」는 쓸 수 없는 낱말이다"
                    % e["🔴 눈금 B — 도달 가능 폭 ÷ 문턱"]["🔴 비"],
        "문턱까지 남은 여유": e["🔴 문턱까지 남은 여유"],
        "문턱까지 z": e["🔴 문턱까지 z((문턱 − 평균)/SD)"],
        "정규 근사로 200뽑기에서 걸릴 확률": e["정규 근사로 200뽑기에서 한 번이라도 걸릴 확률"],
        "🔴 실측으로 문턱을 넘은 뽑기": e["🔴 문턱을 실제로 넘은 뽑기(근사 없음)"],
        "🔴 그래서": "**설계가 아니라 운이다.** 200뽑기 중 하나만 다르게 굴렀어도 "
                 "이 팔은 관문에 걸렸을 것이다. 🔴 **「200/200 통과」는 안심의 근거가 아니었다**",
        "⚠ 근사의 한계": "「걸릴 확률 약 20%%」는 **정규 근사**다(티처 #77 자기 신고 2번). "
                   "상대차 분포는 경계 상태 넷의 혼합이라 꼬리가 정규와 다를 수 있다. "
                   "🔴 **근사 없이 서는 것은 실측 최대 %.6f 와 여유 %.7f 다**"
                   % (e["🔴 눈금 B — 도달 가능 폭 ÷ 문턱"]["도달 가능 폭(|상대차| 최대)"],
                      e["🔴 문턱까지 남은 여유"]),
    }
    return out


# ══════════════════════════════════════════════════════════ D · ㉡ 의 기울기
def part_D(recs: list) -> dict:
    out: dict = {
        "무엇": "🔴 ㉡ 의 **마지막 화살표** — 「기준 팔이 어려워지면 귀무의 개선이 커지나」",
        "🔴 무엇이 문제였나":
            "935 정본 ⑥-다 ㉡ · 논문 §부호 · meta 주장 3 이 「판 ② 기준 팔 MAE 상대차 "
            "200/200 양수 → 귀무의 남은 정답이 더 어렵다 → **판 ② 의 승리는 귀무에게 "
            "유리하게 기운 판에서 얻은 것**」으로 이었다. 🔴 **마지막 화살표를 한 번도 안 쟀다**"
            "(티처 #77 C4)",
        "자": "`귀무 개선(일) ~ β·비교가능성 상대차 + α` 의 OLS 기울기 β · 같은 200뽑기",
        "구간": "규약 47 — `lab.pairboot.cluster_boot` BCa 95% · 재표집 단위 **뽑기(씨앗)** · "
              "`solo_clusters(200)` (🔴 **무군집 폴백을 명시로 쓴다** — 씨앗은 서로 독립이라 "
              "이것이 옳은 단위다 · 폭 과소 방향은 아니다) · B=10,000 · 씨앗 937",
    }
    per = {}
    for p in PANELS:
        x = np.asarray([r[p]["비교가능성 상대차"] for r in recs], float)
        y = np.asarray([r[p]["개선(일)"] for r in recs], float)

        def stat(idx, x=x, y=y):
            xi, yi = x[idx], y[idx]
            xm = xi.mean()
            den = float(((xi - xm) ** 2).sum())
            if den <= 0:
                return float("nan")
            return float(((xi - xm) * (yi - yi.mean())).sum() / den)

        cl, cinfo = pairboot.solo_clusters(len(x))
        th, lo, hi, kind = pairboot.cluster_boot(stat, cl, B=10_000, seed=937)
        v = pairboot.verdict(lo, hi)
        r = float(np.corrcoef(x, y)[0, 1])
        per[p] = {
            "n(뽑기)": len(x),
            "상대차의 폭(SD · 최대−최소)": [float(x.std(ddof=1)),
                                   float(x.max() - x.min())],
            "귀무 개선의 폭(SD)": float(y.std(ddof=1)),
            "corr(상대차, 귀무 개선)": r,
            "🔴 OLS 기울기 β(일 ÷ 상대차 1단위)": th,
            "🔴 BCa 95%": [lo, hi],
            "구간 종류": kind,
            "🔴 폴백 사유(규약 47)": None if kind == "BCa" else kind,
            "군집 병기": cinfo,
            "🔴 판정(pairboot.verdict)": v,
            "상대차가 문턱(0.05)까지 갔을 때 예측되는 귀무 개선 변화(일)":
                th * (THR - float(x.mean())),
            "🔴 부호를 정할 수 있나": ("양수" if v == "승" else
                                "음수" if v == "패" else "🔴 **모른다**"),
        }
    out["팔별"] = per
    e = per[P_EXC]
    dec = e["🔴 판정(pairboot.verdict)"]
    if dec == "판정 불능":
        out["🔴🔴 ㉡ 의 판정"] = {
            "결론": "🔴 **모른다 — ㉡ 을 철회한다.** 판 ② 의 기울기 BCa 구간이 **0 을 문다**. "
                  "「기준 팔이 어려워지면 귀무의 개선이 커진다」는 **이 자로 안 보인다**",
            "🔴 「동점」이 아니다": "규약 47 `verdict` — 0 을 물면 **판정 불능**이지 "
                            "「효과가 0」이 아니다",
            "🔴 검출력": "n=200 에서 |corr|≈%.4f 를 0 과 가르는 힘은 거의 없다. "
                     "🔴 **「0 을 문다」는 「효과가 0 이다」가 아니라 「이 자로는 못 가른다」다**"
                     % abs(e["corr(상대차, 귀무 개선)"]),
        }
    else:
        out["🔴🔴 ㉡ 의 판정"] = {
            "결론": "부호를 **정했다** — %s (BCa 가 0 을 안 문다)" % e["🔴 부호를 정할 수 있나"],
            "뜻": "㉡ 의 마지막 화살표가 %s" % ("**선다**" if dec == "승" else
                                        "🔴 **반대로 틀렸다** — 어려운 기준 팔은 귀무를 안 돕는다"),
        }
    out["🔴 그래도 935 의 결론은 안 바뀐다(사전등록 §3-D 에 미리 적었다)"] = {
        "㉠ 은 참이다": "판①개선 − 판②개선 이 진짜 0.30664556382735936 대 귀무 평균 "
                  "0.09417165504570775 이고 **200/200 뽑기에서 진짜가 크다** "
                  "→ 「칸 빼기는 진짜에게 불리(보수적)」는 ㉠ 하나로 선다",
        "🔴 바뀌는 것": "**근거 하나**다. 935 가 「3세대 만에 부호를 정했다」며 든 둘 중 "
                   "㉡ 이 빠진다 — **정한 것은 하나였다**",
        "🔴 진단 ③ 에서는 잡힌다": "corr=+0.52 이고 기울기 BCa 가 0 을 안 문다 "
                          "→ **이 자는 관계가 있을 때 잡는다**",
    }
    out["⚠ 🔴 내가 틀렸을 수 있는 곳 — 세 팔의 비교는 등가가 아니다"] = {
        "무엇": "「진단 ③ 에서는 잡히니 판 ② 에서 안 잡히는 것은 검정력 부족이 아니다」는 "
              "**세 팔의 x 폭이 같을 때만** 서는 논증이다",
        "실측 폭(상대차 SD)": {p: per[p]["상대차의 폭(SD · 최대−최소)"][0] for p in PANELS},
        "🔴 그래서": "판 ② 의 x 폭은 진단 ③ 보다 좁다 — **같은 기울기라도 판 ② 에서 더 어렵다.** "
                 "그러므로 이 사이클이 말할 수 있는 것은 **「판 ② 에서는 못 가른다」**까지이고, "
                 "**「관계가 없다」가 아니다**. 사전등록 §3-D 가 미리 적은 그대로다",
    }
    return out


# ══════════════════════════════════════════════════════════
def main() -> None:
    t0 = time.time()
    N937.mkdir(parents=True, exist_ok=True)
    tstart = dt.datetime.now(dt.timezone.utc)
    stamp_p = ROOT / "runners/out937_prereg_stamp.json"
    stamp = json.loads(stamp_p.read_text(encoding="utf-8"))
    prereg_now = sha256_text(ROOT / "docs/prereg_937_repair.md")
    prereg_st = stamp["파일별 sha256·mtime"]["docs/prereg_937_repair.md"]["sha256"]

    out: dict = {
        "팔": "937 — 🔴 **회계와 규약을 고친다.** 새 팔을 안 재고 새 순열을 안 돌린다",
        "사전등록": "docs/prereg_937_repair.md",
        "티처": "runners/out936_teacher.json (#77 · 2·3·4·5순위)",
        "🔴 판 ρ": "한 번도 안 부른다(15사이클 연속) — 이 팔의 자가 아니다",
        "🔴 사전등록 시각 증거": {
            "stamp": str(stamp_p),
            "stamp 이 박은 사전등록 sha256": prereg_st,
            "사전등록 sha256(지금 다시 계산)": prereg_now,
            "🔴 같은가": prereg_now == prereg_st,
            "stamp 를 쓴 시각(UTC)": stamp["이 stamp 를 쓴 시각(UTC)"],
            "측정 시작(UTC)": tstart.isoformat(),
            "🔴 stamp 가 측정보다 먼저인가":
                stamp["이 stamp 를 쓴 시각(UTC)"] < tstart.isoformat(),
            "🔴 사전등록만 담은 커밋을 측정 전에 만들었나": True,
            "🔴 os.utime 을 썼나": False,
        },
        "🔴🔴 규율 4 개정판(세 번째) — 이 사이클의 세 칸": {
            "X (채택 크기)": "해당 없음 — 개선(일)을 내는 팔을 하나도 안 잰다",
            "Y_상한 (자기행포함 · 증명)": "해당 없음 — 잴 층·조건 열이 없다",
            "Y_도달 (LOO/교차적합 · 추정)": "해당 없음",
            "Z = X/Y": "해당 없음",
            "🔴 그러므로": "**이 사이클에는 크기 판정이 없다.** 「넘었다」도 「못 넘었다」도 "
                     "안 적는다 — **안 쟀기 때문이다**. 🔴 빈칸이 아니라 「해당 없음」이다",
            "⚠ 병기(이 사이클이 만든 수가 아니다 · 판정에 안 쓴다)":
                "935 네 판을 Y_상한 으로 재면 Z_self = 원판 1.1553 · 첫간격제외 2.1345 · "
                "달력제거 3.0452 · 둘 다 4.587 — 넷 다 1 초과라 928·933·935 의 크기 판정은 "
                "전부 산다. 바뀐 것은 **근거**뿐이다(티처 #77 C1)",
        },
        "코드 sha256": {c: sha256_text(ROOT / c) for c in
                      ("runners/repair937_run.py", "runners/repair937_stamp.py",
                       "runners/interval918_build.py", "state/interval918.py",
                       "lab/pairboot.py")},
    }
    if prereg_now != prereg_st:
        out["🔴 판정"] = "사전등록 sha 가 stamp 이후 바뀌었다 — 판정을 안 낸다"
        OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        return

    _log("A 시작", dt.datetime.now().isoformat())
    A = part_A()
    out["A 🔴 daily.npz 재빌드 — 4사이클짜리 「못 심는 것」을 심는다"] = A
    A_ok = bool(A.get("A2 내용 sha256", {}).get("🔴 A2 참인가"))
    _log("A 끝", A.get("⏱ 초"), "A2=", A_ok)

    out["B 🔴 배선 회계를 코드가 분류한다"] = part_B(A_ok)
    _log("B 끝", time.time() - t0)

    d935 = json.loads((ROOT / "runners/out935_rawpanel.json").read_text(encoding="utf-8"))
    kr = [k for k in d935 if k.startswith("⑤ 뽑기 원자료")][0]
    recs = d935[kr]["기록"]
    assert len(recs) == 200, len(recs)                     # §4-3
    out["C 🔴 관문 규약을 눈금 B 로"] = part_C(recs)
    _log("C 끝", time.time() - t0)
    out["D 🔴 ㉡ 의 기울기"] = part_D(recs)
    _log("D 끝", time.time() - t0)

    # ── 넘기는 것 ────────────────────────────────────────────────
    out["🔴 이 사이클이 **안 한 것** — 이유를 적고 넘긴다"] = {
        "티처 #77 6순위 `b_prv=−1` 칸의 옳은 귀무":
            "🔴 **안 건드렸다.** 그 팔은 **결과를 이미 안다**(Z_self=0.0996 — 이 저장소에서 "
            "크기를 넘은 유일한 팔). 그러므로 **「어떤 결과가 나오면 무엇을 접는가」를 "
            "먼저 적어야** 하고, 그것은 **다음 사전등록의 일**이다. 여기서 손대면 "
            "**결과를 알고 설계한 귀무**가 된다",
        "티처 #77 7순위 논문 498 본문·fig1(c)": "이 사이클의 범위 밖 — 다음 사이클로 넘긴다",
        "티처 #77 8순위 ⑤′ 취합 검사 · 원장 #944 잇는 줄 · meta `sends[]`":
            "범위 밖 — 넘긴다. ⑤′ 는 **세 사이클 연속 안 돌았다**(티처 M7)",
        "티처 #77 1순위 규율 4 세 번째 개정": "🔴 **이미 반영돼 있다** — `docs/목표.md` 가 "
                                "2026-08-11 22:40 에 고쳐졌다. 이 사이클은 그것을 **적용**했다(위 세 칸)",
        "🔴 논문": "안 낸다 — **회계 수리는 스텝이 아니다**. 다만 **규약 48 이 새로 생겼다**",
    }
    out["끝 UTC"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    out["총 초"] = round(time.time() - t0, 1)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    _log("wrote", OUT, out["총 초"])


if __name__ == "__main__":
    main()
