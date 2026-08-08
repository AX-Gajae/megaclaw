# -*- coding: utf-8 -*-
# era 재동결 집행기(노트 874 · 티처 #38 경미 '집행기 부재' 봉합) — 규약(eracheck 문면)의 코드화.
# 기본 = 드라이런: 새 지문을 계산해 현 정본과 diff 만 낸다(파일 무변경).
# --execute <시대id>: 두 정본을 data/lab/eras/era_<시대id>.json · era_base_<시대id>.json 으로
# 이동한 뒤 새 정본 둘을 'x' 로 쓴다(덮어쓰기 금지 — git 과 이중 보존).
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
ERAS = ROOT / "data/lab/eras"


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
    print(json.dumps({"드라이런 diff": {"기저": diff_base, "챔피언": diff_champ},
                      "초": round(time.time() - t0, 1)}, ensure_ascii=False), flush=True)

    if "--execute" not in sys.argv:
        return
    era_id = sys.argv[sys.argv.index("--execute") + 1]
    ERAS.mkdir(exist_ok=True)
    for src, arc in ((CANON, ERAS / f"era_{era_id}.json"), (CANON_BASE, ERAS / f"era_base_{era_id}.json")):
        if arc.exists():
            raise SystemExit(f"거부: {arc.name} 기존재 — 시대 id 를 바꿔라")
        shutil.move(str(src), str(arc))
    head = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                          capture_output=True, text=True).stdout.strip()
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    with open(CANON, "x") as fh:
        json.dump({"시대": f"post-{era_id}", "git HEAD": head, "동결(UTC)": now,
                   "필자": "runners/erafreeze.py", "지문": fp_champ}, fh, ensure_ascii=False, indent=1)
    with open(CANON_BASE, "x") as fh:
        json.dump({"시대": f"post-{era_id}(기저 라벨 층 — 훅 전용)", "git HEAD": head, "동결(UTC)": now,
                   "필자": "runners/erafreeze.py", "지문": fp_base}, fh, ensure_ascii=False, indent=1)
    print(f"재동결 완료 — 구 시대 '{era_id}' 아카이브 · 새 정본 둘 'x'", flush=True)


if __name__ == "__main__":
    main()
