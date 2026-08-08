# -*- coding: utf-8 -*-
# era 재동결 집행기 v2(노트 874·875 — 원자성 수리·픽스처 시험 가능) — 규약(eracheck 문면)의 코드화.
# 기본 = 드라이런: 새 지문 계산 → 현 정본과 diff → --save 시 산출물 'x'(875: 산출물 없는 실측 주장 0건).
# --execute <시대id>: ① 두 아카이브 경로 **일괄 선검사** ② 새 정본을 임시 파일로 먼저 쓰고
# ③ 구 정본 이동 ④ 임시 → 정본 개명(마지막 단계 실패에도 구 정본은 eras/ 에 보존 · git 이중).
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/ax/world_model")
sys.path.insert(0, "/Users/ax/world_model/runners")

ROOT = Path("/Users/ax/world_model")


def execute(era_id: str, canon: Path, canon_base: Path, eras: Path,
            fp_champ: dict, fp_base: dict) -> None:
    """재동결 본체 — 픽스처 시험 가능(경로 주입). 순서가 원자성의 핵심."""
    eras.mkdir(exist_ok=True)
    arcs = [(canon, eras / f"era_{era_id}.json"), (canon_base, eras / f"era_base_{era_id}.json")]
    for _src, arc in arcs:                               # ① 일괄 선검사(이동 전)
        if arc.exists():
            raise SystemExit(f"거부: {arc.name} 기존재 — 시대 id 를 바꿔라")
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    tmps = []
    for path, fp, tag in ((canon, fp_champ, ""), (canon_base, fp_base, "(기저 라벨 층 — 훅 전용)")):
        tmp = path.with_suffix(".neweraTMP")             # ② 새 정본 임시 쓰기
        json.dump({"시대": f"post-{era_id}{tag}", "git HEAD": head, "동결(UTC)": now,
                   "필자": "runners/erafreeze.py", "지문": fp}, open(tmp, "w"),
                  ensure_ascii=False, indent=1)
        tmps.append((path, tmp))
    for src, arc in arcs:                                # ③ 구 정본 아카이브
        shutil.move(str(src), str(arc))
    for path, tmp in tmps:                               # ④ 임시 → 정본
        tmp.replace(path)


def main():
    t0 = time.time()
    import ff753 as FF
    from lab import harness as H
    from lab.eracheck import fingerprint, fingerprint_labels, CANON, CANON_BASE

    base = H.load()
    champ = FF.shell(FF.base())
    fp_base, fp_champ = fingerprint_labels(base), fingerprint(champ)
    cur_base = json.loads(CANON_BASE.read_text())["지문"]
    cur_champ = json.loads(CANON.read_text())["지문"]
    diff_base = sorted(d for d in set(cur_base) | set(fp_base) if cur_base.get(d) != fp_base.get(d))
    diff_champ = sorted(d for d in set(cur_champ) | set(fp_champ) if cur_champ.get(d) != fp_champ.get(d))
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    out = {"시각(UTC)": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "git HEAD": head, "드라이런 diff": {"기저": diff_base, "챔피언": diff_champ},
           "초": round(time.time() - t0, 1)}
    print(json.dumps(out, ensure_ascii=False), flush=True)
    if "--save" in sys.argv:
        p = ROOT / f"runners/out_erafreeze_{dt.date.today()}.json"
        with open(p, "x") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
        print(f"동결: {p.name}", flush=True)
    if "--execute" in sys.argv:
        era_id = sys.argv[sys.argv.index("--execute") + 1]
        from lab.eracheck import CANON as C, CANON_BASE as CB
        execute(era_id, C, CB, ROOT / "data/lab/eras", fp_champ, fp_base)
        print(f"재동결 완료 — 구 시대 '{era_id}' 아카이브 · 새 정본 둘", flush=True)


if __name__ == "__main__":
    main()
