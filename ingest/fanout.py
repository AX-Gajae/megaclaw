"""수집 팬아웃 하네스 — **재개 가능한 병렬 크롤의 공통 뼈대** (노트 891).

**왜 필요한가.** 2026-08-10 실측: 이 저장소에서 `ThreadPoolExecutor` 를 쓰는
수집 모듈이 **`ingest/wiki_views.py` 하나뿐**이다. `ingest/social.py` 는
`SLEEP=1.5` 직렬이라 아이돌 173건 × 검색 × 창 90일을 돌리면 며칠이 걸린다.
그래서 *"유튜브를 제대로 긁자"* 가 매번 배관 앞에서 멈췄다.

`wiki_views.run_mt` 가 이미 옳은 모양을 갖고 있다 --- **재개 캐시 · 스레드풀 ·
잠금 · 진행 보고**. 그런데 그 함수 안에 위키 전용 로직이 섞여 있어 못 가져다
쓴다. 여기서 **일반형만 떼어 낸다.**

**설계 규칙 넷(전부 이 저장소가 다친 자리에서 나왔다).**

  ① **캐시가 곧 재개다.** 대상마다 `{cache}/{key}.json` 하나. 있으면 안 긁는다.
     중간에 죽어도 다시 돌리면 이어서 한다 --- `data/state/cache_*` 54,000여
     디렉터리가 이 관례로 서 있다.

  ② **실패를 성공과 같은 자리에 적는다.** 실패도 캐시 파일을 쓰되 `ok: false`
     와 사유를 남긴다. 안 그러면 **다음 실행이 같은 실패를 무한히 재시도**하고,
     더 나쁘게는 '아직 안 긁은 것'과 '긁어 봤는데 없는 것'을 못 가른다
     (노트 658: *"요청 실패는 None 이다 --- 0 으로 보고하면 '없음'과 안 갈린다"*).

  ③ **예의는 우리가 정한다.** `SLEEP` 은 워커마다 걸리므로 실효 속도는
     `workers/sleep` 이다. 기본값을 보수적으로 두고 호출자가 올리게 한다.

  ④ **진행은 flush 한다.** 노트 686 --- 리다이렉트된 stdout 은 블록 버퍼라
     진행이 안 보이고, 그러면 '멈춘 것'과 '버퍼에 갇힌 것'을 못 가른다.

쓰는 법::

    from ingest.fanout import fanout

    def one(item):                      # 대상 하나 → dict (예외를 던져도 된다)
        return {"n": len(social.yt_search(item["q"]))}

    fanout(items, key=lambda x: x["record_id"],
           cache="data/state/cache_ytsearch", work=one, workers=8, sleep=1.5)
"""
from __future__ import annotations

import json
import threading
import time
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fanout(items, key, cache, work, workers: int = 8, sleep: float = 1.5,
           limit: int | None = None, retry_failed: bool = False,
           report_every: int = 50) -> dict:
    """`items` 를 스레드 `workers` 개로 훑는다. 결과는 대상마다 캐시 파일 하나.

    key(item) -> str          캐시 파일 이름(대상 식별자)
    work(item) -> dict        실제 수집. 예외는 잡아서 실패로 적는다.
    retry_failed              True 면 `ok:false` 캐시도 다시 시도한다
    """
    from concurrent.futures import ThreadPoolExecutor

    cdir = Path(cache) if str(cache).startswith("/") else ROOT / cache
    cdir.mkdir(parents=True, exist_ok=True)

    def done(it) -> bool:
        p = cdir / f"{key(it)}.json"
        if not p.exists():
            return False
        if not retry_failed:
            return True
        try:                                  # 실패분만 다시 하고 싶을 때
            return bool(json.loads(p.read_text(encoding="utf-8")).get("ok", True))
        except Exception:
            return False

    todo = [it for it in items if not done(it)]
    if limit is not None:
        todo = todo[:limit]
    cnt = Counter()
    lock = threading.Lock()
    n = [0]
    t0 = time.time()

    def one(it):
        k = key(it)
        try:
            res = work(it)
            rec = {"ok": True, "key": k, **(res if isinstance(res, dict) else {"값": res})}
            cnt_key = "성공"
        except Exception as e:
            # ② 실패도 적는다 --- 안 적으면 '안 긁은 것'과 '없는 것'을 못 가른다
            rec = {"ok": False, "key": k, "사유": f"{type(e).__name__}: {e}"[:300],
                   "추적": traceback.format_exc()[-400:]}
            cnt_key = "실패"
        (cdir / f"{k}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
        time.sleep(sleep)                     # ③ 예의 --- 워커마다 걸린다
        with lock:
            cnt[cnt_key] += 1
            n[0] += 1
            if n[0] % report_every == 0:
                el = time.time() - t0
                print("  %d/%d (%s) %.0fs · 남은 예상 %.0fs"
                      % (n[0], len(todo), dict(cnt), el,
                         el / n[0] * (len(todo) - n[0])), flush=True)   # ④

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, todo))

    have = sum(1 for _ in cdir.glob("*.json"))
    out = {"대상": len(list(items)), "이번에 긁음": len(todo), **dict(cnt),
           "캐시 총": have, "초": round(time.time() - t0, 1)}
    print(json.dumps(out, ensure_ascii=False), flush=True)
    return out


def summarize(cache: str) -> dict:
    """캐시 디렉터리의 성공/실패 회계. **긁기 전에 무엇이 있는지 먼저 센다.**"""
    cdir = Path(cache) if str(cache).startswith("/") else ROOT / cache
    if not cdir.is_dir():
        return {"경로": str(cdir), "없음": True}
    ok = bad = broken = 0
    reasons = Counter()
    for p in cdir.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            broken += 1
            continue
        if d.get("ok", True):
            ok += 1
        else:
            bad += 1
            reasons[str(d.get("사유", ""))[:40]] += 1
    return {"경로": str(cdir), "성공": ok, "실패": bad, "깨짐": broken,
            "실패사유": dict(reasons.most_common(5))}


if __name__ == "__main__":
    import sys
    print(json.dumps(summarize(sys.argv[1] if len(sys.argv) > 1 else "data/state/cache_wiki"),
                     ensure_ascii=False, indent=1))
