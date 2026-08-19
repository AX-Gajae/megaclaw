# -*- coding: utf-8 -*-
"""시대 고정 관문 — 배포물을 «여는 시점»의 sha 실측 대조 (루프 v5.3 부칙 4 · 티처 #142 발의).

왜 있는가(#142 0절 2 실측): 병행 3팔의 시대 단일성은 규율이 아니라 «운»이었다 — 1006 eval 은
배포 manifest 의 sha 를 재실측하지 않고 등록 «상수»를 out 에 게재했고, 1005 가 성공해 그 사이
배포했다면 조용히 새 시대를 읽으며 옛 시대 sha 를 찍었을 것이다(이번엔 1005 실패 = 배포 0 이라
단일 시대가 «결과적으로» 성립했을 뿐).

규격(부칙 4):
  · 배포물(manifest·conformal·리더보드·report)을 여는 모든 러너 phase 는 여는-시점에
    `assert_epoch(등록 sha)` 를 불러 실측 대조한다 — 불일치면 EpochMismatch 예외로
    **측정 없이 중단**(v5.3-2 방향 탐침과 같은 원리: 값을 보고 판정을 고치는 길을 막는다)
  · out/progress 게재는 등록 상수가 아니라 이 함수의 «반환값»(실측 sha + 여는 시각)으로 한다
  · torch 무의존(numpy 무의존) — 언 러너(torch 미사용 형)도 그대로 임포트한다. 배포물 경로는
    `pretrain/transition.py` 의 정의를 미러한다(다른 «목적»의 상수 물려쓰기가 아니라 같은
    실물의 같은 주소다 — 조항 66)

씀:  from pretrain.epoch_guard import assert_epoch, EpochMismatch
     stamp = assert_epoch("3a5c2543a55f1dab")          # 등록 기재값 — 불일치면 예외
     out["시대(부칙 4)"] = stamp                          # 게재는 실측 반환값으로
자기시험: python3 pretrain/epoch_guard.py               # 참/거짓 양쪽
"""
import hashlib
import os
import time

ART = os.environ.get("WM_FOUNDATION_DIR", "/Users/ax/wm_harvest/foundation")
MANIFEST = os.path.join(ART, "transition", "ensemble_manifest.json")


class EpochMismatch(RuntimeError):
    """등록 시대 ≠ 실측 시대 — 측정 없이 중단 규격."""


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def assert_epoch(expected_manifest_sha, path=MANIFEST):
    """여는-시점 시대 검사 — path(기본: 배포 manifest)의 sha256/16 을 «지금» 실측해
    등록 기재값과 대조한다. 불일치면 EpochMismatch — 측정 없이 중단하라.

    반환(게재용 실측 스탬프): {"실측 sha", "등록 sha", "여는 시각", "경로"}
    """
    t_open = time.strftime("%Y-%m-%dT%H:%M:%S")
    got = sha16(path)
    if got != str(expected_manifest_sha):
        raise EpochMismatch(
            "🔴 시대 불일치 — 등록 %s ≠ 실측 %s (%s · 여는 시각 %s) — 측정 없이 중단"
            % (expected_manifest_sha, got, path, t_open))
    return {"실측 sha": got, "등록 sha": str(expected_manifest_sha),
            "여는 시각": t_open, "경로": path}


if __name__ == "__main__":
    import json
    # 자기시험 ① 참 쪽 — 현 manifest 실측 sha 로 통과해야 한다
    cur = sha16(MANIFEST)
    stamp = assert_epoch(cur)
    print("참 쪽 통과:", json.dumps(stamp, ensure_ascii=False))
    # 자기시험 ② 거짓 쪽 — 틀린 등록값은 예외가 나야 한다
    try:
        assert_epoch("0" * 16)
    except EpochMismatch as e:
        print("거짓 쪽 예외 OK:", e)
    else:
        print("🔴 결함 — 거짓 쪽에서 예외가 안 났다")
        raise SystemExit(1)
