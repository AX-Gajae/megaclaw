"""`Run` --- **세 줄로 붙는 학습 기록기.** 노트 912 팔 ㅇ.

    from trainlog import Run
    with Run("909-ssl", pushes="③", ruler="소수 라벨 곡선") as r:
        r.arch(model)                       # torch 모듈이면 자동 추출
        for step in ...:
            r.log(step=step, split="train", loss=..., acc=...)

저장 자리는 `data/trainlog/<run_id>/` 이고 파일은 셋이다.

    manifest.json   자기서술 --- 누가 · 언제 · 어떤 코드 · 어떤 자로
    metrics.jsonl   append-only 지표 스트림 (step · split · name · value)
    arch.json       아키텍처 그래프 (층 · 간선 · 파라미터 수 · 가중치)

# 규율 넷

1. 🔴 **덮어쓰기 금지.** 같은 이름이면 UTC 접미가 붙어 새 디렉터리가 된다.
   이 저장소의 규약이다 --- 지난 학습을 새 학습이 지우면 이력이 거짓이 된다.
2. 🔴 **학습을 못 느리게 한다.** `log()` 는 리스트에 튜플 하나를 붙일 뿐이고,
   실제 쓰기는 묶어서(`flush_every`) 한다.
3. 🔴 **실패해도 학습을 안 죽인다 --- 그러나 조용히 삼키지도 않는다.**
   쓰기가 터지면 `기록 실패 n건` 이 manifest 에 남고 앞 세 건은 사유까지 남는다.
   (조항 59: '안 썼다' 와 '못 썼다' 는 다르다.)
4. 🔴 **줄 단위로 흘린다.** 프로세스가 죽어도 그때까지 쓴 줄은 읽힌다.
"""
from __future__ import annotations

import atexit
import hashlib
import json
import os
import platform
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from . import arch as _arch
from .spec import (ARCH_SPEC, METRICS_SPEC, SPEC, SPEC_VERSION, SpecError,
                   ascii_id, norm_output)

ROOT = Path(__file__).resolve().parents[1]
#: 기본 저장 자리. 🔴 **데모도 진짜 run 도 여기 들어간다** --- 가르는 것은
#: 디렉터리가 아니라 manifest 의 `데모인가` 칸이다(경로로 가르면 옮기다 섞인다).
STORE = ROOT / "data/trainlog"

#: 실패 사유를 몇 건까지 남기나(전부 남기면 실패가 폭주할 때 파일이 커진다).
KEEP_FAILS = 5


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(p) -> dict:
    """파일 하나의 sha256 --- **못 읽으면 못 읽었다고 적는다.**"""
    p = Path(p)
    try:
        h, n = hashlib.sha256(), 0
        with p.open("rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                n += len(b)
                h.update(b)
        return {"경로": _rel(p), "sha256": h.hexdigest(), "바이트": n}
    except Exception as e:
        return {"경로": _rel(p), "sha256": None, "바이트": None,
                "못 읽음": f"{type(e).__name__}: {e}"}


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return str(p)


#: 코드 sha256 을 고를 때 **건너뛰는** 자리 --- 표준 라이브러리와 실행 껍데기.
#: 🔴 안 건너뛰면 `python3 -m foo` 로 돌린 run 의 코드 해시가 **`runpy.py`** 가 된다
#: (실제로 데모에서 그렇게 나왔다 --- 학습 코드가 아니라 파이썬 자신을 해시했다).
SKIP_DIRS = ("/lib/python", "/site-packages/", "/importlib/")
SKIP_NAMES = ("runpy.py", "_bootstrap.py", "_bootstrap_external.py")


def _caller_file() -> str | None:
    """이 `Run` 을 만든 **바깥 파일** --- 코드 sha256 의 기본값이다."""
    here = str(Path(__file__).resolve().parent)
    f = sys._getframe(1)
    while f is not None:
        fn = f.f_code.co_filename
        if fn and not fn.startswith("<"):
            p = str(Path(fn).resolve())
            if (not p.startswith(here) and Path(p).name not in SKIP_NAMES
                    and not any(s in p for s in SKIP_DIRS)):
                return fn
        f = f.f_back
    return None


class Run:
    """학습 실행 하나. **컨텍스트 매니저로 쓰는 것이 정석이다.**"""

    def __init__(self, name: str, pushes=None, ruler: str | None = None,
                 seed=None, hparams: dict | None = None,
                 data=None, code=None, demo: bool = False,
                 note: str | None = None, root=None,
                 flush_every: int = 50, flush_secs: float = 1.0):
        self.이름 = str(name)
        self.run_id = None
        self.미는출력 = norm_output(pushes)
        self.자 = str(ruler).strip() if ruler else None
        self.씨앗 = seed
        self.하이퍼 = dict(hparams or {})
        self.데모 = bool(demo)
        self.메모 = note
        self.상태 = "도는 중"
        self._buf: list = []
        self._n = 0
        self._fails: list = []
        self._nfail = 0
        self._fh = None
        self._t0 = time.time()
        self._last_flush = self._t0
        self.flush_every = int(flush_every)
        self.flush_secs = float(flush_secs)
        self._arch = None
        self._closed = False
        self.시작 = _utc()
        self.끝 = None

        #: 코드 sha256 --- 기본은 **나를 부른 파일**. 여러 개면 목록으로 준다.
        cs = code if code is not None else _caller_file()
        if cs is None:
            self.코드 = [{"경로": None, "sha256": None,
                       "못 읽음": "부른 파일을 못 찾았다(대화형 셸일 수 있다)"}]
        else:
            self.코드 = [sha256_file(p) for p in
                       ([cs] if isinstance(cs, (str, Path)) else list(cs))]
        self.데이터 = [sha256_file(p) for p in
                    ([data] if isinstance(data, (str, Path)) else list(data or []))]
        if not self.데이터:
            self.데이터 = [{"경로": None, "sha256": None,
                        "없음": "이 run 은 입력 데이터 파일을 안 적었다 --- "
                              "**「없다」이지 「못 읽었다」가 아니다**"}]

        base = Path(root) if root else STORE
        rid = f"{ascii_id(self.이름)}-{_stamp()}"
        d = base / rid
        k = 2
        while d.exists():                    # 🔴 덮어쓰기 금지 --- 새 자리를 판다
            rid = f"{ascii_id(self.이름)}-{_stamp()}-{k}"
            d, k = base / rid, k + 1
        self.run_id = rid
        self.dir = d
        self.dir.mkdir(parents=True, exist_ok=True)
        self._metrics = self.dir / "metrics.jsonl"
        self._manifest = self.dir / "manifest.json"
        self._archp = self.dir / "arch.json"
        try:
            self._fh = self._metrics.open("a", encoding="utf-8")
            self._fh.write(json.dumps(
                {"규격": METRICS_SPEC, "run_id": self.run_id, "UTC": self.시작,
                 "칸": ["step", "split", "name", "value"]},
                ensure_ascii=False) + "\n")
            self._fh.flush()
        except Exception as e:
            self._fail("metrics.jsonl 을 못 열었다", e)
        #: 아키텍처를 **한 번도 안 적으면** 「못 읽음」이 남는다(빈 그래프가 아니다).
        self._write_arch(_arch.extract(None))
        self._write_manifest()
        atexit.register(self._atexit)

    # ── 기록 ──────────────────────────────────────────────────────
    def arch(self, model=None, weights: bool = True) -> dict:
        """아키텍처를 적는다 --- torch 모듈 · dict · 아무것도 아닌 것 셋 다 받는다."""
        a = _arch.extract(model, weights=weights)
        self._arch = a
        self._write_arch(a)
        return a

    def log(self, step=None, split: str = "train", **metrics) -> None:
        """지표를 적는다. `r.log(step=3, split="train", loss=0.2, acc=0.9)`.

        **싸야 한다** --- 여기서 하는 일은 튜플을 리스트에 붙이는 것뿐이고,
        파일 쓰기는 묶어서 한다. `metrics` 의 값 중 수가 아닌 것은 버리지 않고
        **문자열로** 적는다(버리면 조용히 사라진다).
        """
        t = _utc()
        for k, v in metrics.items():
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    self._buf.append((step, split, f"{k}.{k2}", v2, t))
            else:
                self._buf.append((step, split, k, v, t))
        if (len(self._buf) >= self.flush_every
                or (time.time() - self._last_flush) >= self.flush_secs):
            self.flush()

    def log_metric(self, step, split: str, name: str, value) -> None:
        self._buf.append((step, split, str(name), value, _utc()))
        if len(self._buf) >= self.flush_every:
            self.flush()

    def flush(self) -> int:
        """버퍼를 **줄 단위로** 흘린다 --- 프로세스가 죽어도 여기까지는 읽힌다."""
        if not self._buf:
            return 0
        buf, self._buf = self._buf, []
        try:
            if self._fh is None:
                self._fh = self._metrics.open("a", encoding="utf-8")
            for step, split, name, value, t in buf:
                if not isinstance(value, (int, float)) or isinstance(value, bool):
                    value = str(value)
                self._fh.write(json.dumps(
                    {"step": step, "split": split, "name": name,
                     "value": value, "t": t}, ensure_ascii=False) + "\n")
            self._fh.flush()
            self._n += len(buf)
            return len(buf)
        except Exception as e:                # 🔴 학습을 죽이지 않는다
            self._fail(f"지표 {len(buf)}건을 못 썼다", e)
            return 0

    def _fail(self, 무엇: str, e: Exception) -> None:
        """실패를 **센다.** 조용히 삼키는 것이 이 함수가 막는 병이다."""
        self._nfail += 1
        if len(self._fails) < KEEP_FAILS:
            self._fails.append({"무엇": 무엇, "예외": f"{type(e).__name__}: {e}",
                                "UTC": _utc()})

    # ── 파일 ──────────────────────────────────────────────────────
    def _write_arch(self, a: dict) -> None:
        try:
            self._archp.write_text(json.dumps(a, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        except Exception as e:
            self._fail("arch.json 을 못 썼다", e)

    def manifest(self) -> dict:
        a = self._arch or {}
        return {
            "규격": SPEC, "규격 판": SPEC_VERSION,
            "run_id": self.run_id, "이름(원래)": self.이름,
            "데모인가": self.데모,
            "메모": self.메모,
            "상태": self.상태,
            "시작 UTC": self.시작, "끝 UTC": self.끝,
            "초": round(time.time() - self._t0, 3),
            "씨앗": self.씨앗,
            "하이퍼파라미터": self.하이퍼 or None,
            "코드 sha256": self.코드,
            "입력 데이터 sha256": self.데이터,
            #: 🔴 `docs/목표.md` 의 다섯 출력 중 무엇을 미나 --- 「해당 없음」도 값이다
            "미는 출력": self.미는출력,
            #: 🔴 어느 자로 판정하나 --- **자 없는 run 도 기록은 되되 보이게 한다**
            "자": self.자,
            "자 없음": not bool(self.자),
            "🔴 자 없음 단서": (None if self.자 else
                          "이 run 은 **어느 자로 판정하는지 안 적혔다** --- "
                          "기록은 되지만 이 값으로 무엇을 주장할 수는 없다"),
            "지표 줄 수": self._n,
            "기록 실패 n건": self._nfail,
            "기록 실패(앞 몇 건)": self._fails or None,
            "아키텍처": {"읽음": bool(a.get("읽음")), "출처": a.get("출처"),
                    "층 수": len(a.get("층") or []),
                    "간선 수": len(a.get("간선") or []),
                    "간선 출처": a.get("간선 출처"),
                    "총 파라미터": a.get("총 파라미터"),
                    "가중치를 읽었나": bool(a.get("가중치를 읽었나")),
                    "왜 못 읽음": a.get("왜 못 읽음")},
            "파일": {"manifest": "manifest.json", "지표": "metrics.jsonl",
                   "아키텍처": "arch.json"},
            "환경": {"python": platform.python_version(),
                   "platform": platform.platform(),
                   "torch": _torch_ver(), "pid": os.getpid(),
                   "cwd": _rel(Path.cwd())},
        }

    def _write_manifest(self) -> None:
        try:
            self._manifest.write_text(
                json.dumps(self.manifest(), ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception as e:
            self._fail("manifest.json 을 못 썼다", e)

    # ── 생애 ──────────────────────────────────────────────────────
    def finish(self, 상태: str = "끝남", 오류: str | None = None) -> dict:
        if self._closed:
            return self.manifest()
        self.flush()
        self.상태 = 상태
        self.끝 = _utc()
        m = self.manifest()
        if 오류:
            m["터진 이유"] = 오류
        try:
            self._manifest.write_text(json.dumps(m, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
        except Exception as e:
            self._fail("manifest.json 을 못 썼다", e)
        try:
            if self._fh is not None:
                self._fh.close()
        except Exception:
            pass
        self._fh, self._closed = None, True
        return m

    def _atexit(self) -> None:
        """프로세스가 그냥 끝나도 **적어도 「도는 중」으로 남지는 않게** 한다."""
        if not self._closed:
            self.finish("터짐", "프로세스가 `finish()` 없이 끝났다 --- "
                              "**「끝남」이 아니다**(조항 59)")

    def __enter__(self):
        return self

    def __exit__(self, et, ev, tb):
        if et is None:
            self.finish("끝남")
        else:
            self.finish("터짐", "".join(
                traceback.format_exception_only(et, ev)).strip())
        return False                          # 예외를 삼키지 않는다


def _torch_ver():
    try:
        import torch
        return torch.__version__
    except Exception:
        return "torch 없음"
