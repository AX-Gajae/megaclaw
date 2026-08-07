"""노트 703 — **정보 전이장이 잘 학습되고 있나.** 실제 `pretrain` 으로 네 팔."""
import json, sys
sys.path.insert(0, "/Users/ax/world_model")
import state.fieldmodel as F

ARMS = [("공휴일 뺀 g · 진짜", True, False),
        ("공휴일 뺀 g · 위약", True, True),
        ("옛 g(holiday=False) · 진짜", False, False),
        ("옛 g(holiday=False) · 위약", False, True)]
out = {}
for tag, hol, pl in ARMS:
    r = F.pretrain(holiday=hol, placebo=pl, seed=0, save=False)
    if "오류" in r:
        print(json.dumps({tag: r}, ensure_ascii=False), flush=True); out[tag]=r; continue
    last = r["이력"][-1]
    out[tag] = {"파라미터": r["파라미터"], "표본": r["표본"], "동네": r["동네"],
                "검증 R2": last["검증 R2(지속성 대비)"],
                "학습 MSE": last["학습 MSE"],
                "이력": [h["검증 R2(지속성 대비)"] for h in r["이력"]]}
    print(json.dumps({tag: out[tag]}, ensure_ascii=False), flush=True)
a, b = out.get("공휴일 뺀 g · 진짜", {}), out.get("공휴일 뺀 g · 위약", {})
c, d = out.get("옛 g(holiday=False) · 진짜", {}), out.get("옛 g(holiday=False) · 위약", {})
if "검증 R2" in a and "검증 R2" in b:
    out["판정"] = {
        "새 g 신호 몫(진짜−위약)": round(a["검증 R2"] - b["검증 R2"], 4),
        "옛 g 신호 몫": (round(c["검증 R2"] - d["검증 R2"], 4)
                     if "검증 R2" in c and "검증 R2" in d else None),
        "새 g 검증 R2": a["검증 R2"], "옛 g 검증 R2": c.get("검증 R2"),
        "노트 669 가 적은 값": 0.1098,
        "장이 지속성을 이기나": "**이긴다**" if a["검증 R2"] > 0 else "**못 이긴다**",
        "장이 위약을 이기나": "**이긴다**" if a["검증 R2"] > b["검증 R2"] else "못 이긴다",
        "공휴일 항이 학습에": ("도움" if a["검증 R2"] > (c.get("검증 R2") or -9)
                        else "해로움")}
print("=== 모아서 ===", flush=True)
print(json.dumps(out, ensure_ascii=False, indent=1), flush=True)
