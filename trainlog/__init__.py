"""`trainlog` --- **학습 실행 하나를 남기는 규격과 그 도구.** 노트 912 팔 ㅇ.

정본 문서: `docs/학습기록규격.md`. 뷰어: `serve/trainlog_svc.py` +
`serve/static/trainlog.html` (`http://127.0.0.1:<포트>/trainlog`).

세 줄로 쓴다:

    from trainlog import Run
    with Run("909-ssl", pushes="③", ruler="소수 라벨 곡선") as r:
        r.arch(model)                       # torch 모듈이면 자동 추출
        for step in ...:
            r.log(step=step, split="train", loss=..., acc=...)

🔴 **torch 는 필수가 아니다.** `r.arch()` 는 torch 모듈이면 introspect 하고,
dict 를 주면 그대로 받고, 아무것도 없으면 **「아키텍처 못 읽음」으로 기록**한다
(조항 59: '없다' 와 '못 봤다' 와 '못 읽었다' 는 셋이다).
"""
from .arch import extract as extract_arch          # noqa: F401
from .run import Run, sha256_file                  # noqa: F401
from .spec import (ARCH_SPEC, METRICS_SPEC, SPEC,  # noqa: F401
                   SPEC_VERSION, OUTPUTS, SpecError, check_manifest)
from .store import (graph, list_runs, liveness, neurons,  # noqa: F401
                    node_state, read_arch, read_manifest, read_metrics,
                    read_node_metrics, tail_metrics)

__all__ = ["Run", "SPEC", "SPEC_VERSION", "ARCH_SPEC", "METRICS_SPEC",
           "OUTPUTS", "SpecError", "check_manifest", "extract_arch",
           "sha256_file", "list_runs", "read_manifest", "read_metrics",
           "read_arch", "neurons", "graph", "tail_metrics", "liveness",
           "read_node_metrics", "node_state"]
