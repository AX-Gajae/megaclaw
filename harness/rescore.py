"""라벨이 교정된 뒤 옛 채점 리포트를 다시 쓴다.

채점 리포트는 채점 시점의 스냅샷이라 라벨이 나중에 바뀌어도 남는다. 지금까지는
discovery의 위생 게이트가 그런 리포트를 **버려서** 처리했는데, 버리면 그 폴드의
예측이 통째로 사라진다. 예측값은 리포트에 남아 있으므로 실측만 갈아 끼우면 된다.

이게 왜 중요한지는 RIPU2519가 보여준다. 라벨이 28,701(8개 존 카운터 합)에서
5,754(부스 입장)로 교정되자 v5와 v6의 순위가 뒤집혔다:
    v5  예측  4,200   APE 85.4% 구간 이탈  →  27.0% 적중
    v6  예측 18,000   APE 37.3% 구간 적중  → 212.8% 이탈
v6가 나아 보였던 것은 오염된 라벨을 맞춘 결과였다. 리포트를 그대로 두면 이 사실이
장부에 남지 않고, 버리면 비교 자체가 사라진다.

원본은 .report.md.orig 로 보존한다.

사용:
  python3 -m harness.rescore            # 무엇이 어떻게 바뀌는지
  python3 -m harness.rescore --write    # 적용
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

LINE = re.compile(r"(- \*\*visitors\*\*: 예측 )([\d,]+)( / 실측 )([\d,]+)( / APE )([\d.]+)(%)"
                  r"(?: 구간 \[(\d+), (\d+)\] → (적중|이탈))?")


def rescore_text(text: str, cur: int) -> tuple[str, dict] | None:
    m = LINE.search(text)
    if not m:
        return None
    pred, old = int(m.group(2).replace(",", "")), int(m.group(4).replace(",", ""))
    if old == cur:
        return None
    ape = abs(pred - cur) / cur * 100
    seg = f"- **visitors**: 예측 {pred:,} / 실측 {cur:,} / APE {ape:.1f}%"
    info = {"pred": pred, "old": old, "new": cur,
            "old_ape": float(m.group(6)), "new_ape": round(ape, 1)}
    if m.group(8):
        lo, hi = int(m.group(8)), int(m.group(9))
        hit = lo <= cur <= hi
        seg += f" 구간 [{lo}, {hi}] → {'적중' if hit else '이탈'}"
        info["old_cov"], info["new_cov"] = m.group(10), "적중" if hit else "이탈"
    out = text[:m.start()] + seg + text[m.end():]
    note = (f"\n\n> 라벨 교정으로 재채점됨 — 실측 {old:,} → {cur:,}. "
            f"예측값은 채점 시점 그대로다(재예측이 아니다). "
            f"APE {info['old_ape']:.1f}% → {info['new_ape']:.1f}%")
    if "old_cov" in info and info["old_cov"] != info["new_cov"]:
        note += f", 구간 {info['old_cov']} → {info['new_cov']}"
    return out.rstrip() + note + "\n", info


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    rows = []
    for f in sorted(Path("cycle_log").rglob("*.report.md")):
        code = f.stem.replace(".report", "")
        p = Path(f"data/records/{code}.json")
        if not p.exists():
            continue
        cur = json.loads(p.read_text())["outcome"]["totals"].get("visitors")
        if cur is None:
            continue                       # 철회된 라벨은 재채점 대상이 아니다
        text = f.read_text()
        if "라벨 교정으로 재채점됨" in text:
            continue
        r = rescore_text(text, cur)
        if not r:
            continue
        new_text, info = r
        info.update({"cycle": f.parent.name, "code": code})
        rows.append(info)
        if a.write:
            orig = f.with_suffix(".md.orig")
            if not orig.exists():
                orig.write_text(text)
            f.write_text(new_text)

    print(json.dumps({"재채점": len(rows), "기록": bool(a.write)}, ensure_ascii=False))
    for x in rows:
        cov = ""
        if "old_cov" in x and x["old_cov"] != x["new_cov"]:
            cov = f"  구간 {x['old_cov']} → {x['new_cov']}"
        print(f"   {x['cycle']}/{x['code']}  예측 {x['pred']:,}  "
              f"실측 {x['old']:,} → {x['new']:,}  "
              f"APE {x['old_ape']:.1f}% → {x['new_ape']:.1f}%{cov}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
