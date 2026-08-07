import json, sys, re
from pathlib import Path
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
import paper.figs  # noqa: F401,E402
D = Path(__file__).resolve().parent

# 그림 1 — 사후 태그가 아래쪽을 다 차지한다
r = json.loads(Path("data/state/webtoon_records.json").read_text())
rows = []
for v in r.values():
    m = re.match(r"(\d{4})", str(v.get("start_date") or ""))
    if not m or int(m.group(1)) >= 2025:
        continue
    rows.append((list(v.get("tags") or []),
                 float(np.log10(max(v.get("y_favorite") or 1, 1)))))
C = Counter(t for ts, _ in rows for t in ts)
ybar = np.mean([y for _, y in rows])
eff = [(np.mean([y for ts, y in rows if t in ts]) - ybar, t)
       for t, n in C.items() if n >= 30]
eff.sort()
POST = re.compile(r"완결|원작웹툰|드라마&영화")
lo = eff[:9]; hi = eff[-9:]
fig, ax = plt.subplots(figsize=(7.0, 3.6))
sel = lo + hi
y = np.arange(len(sel))[::-1]
cs = ["#a33b3b" if POST.search(t) else "#2f5fa3" for _, t in sel]
ax.barh(y, [d for d, _ in sel], color=cs, height=0.66)
ax.axvline(0, color="#333", lw=0.9)
ax.set_yticks(y); ax.set_yticklabels([t for _, t in sel], fontsize=7)
ax.set_xlabel("학습 구간 $\\log_{10}$ 즐겨찾기 편차")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color="#a33b3b", label="사후 표지 (걸러냄)"),
                   Patch(color="#2f5fa3", label="쓸 수 있는 태그")],
          fontsize=7.2, frameon=False, loc="lower right")
ax.set_title("아래쪽이 전부 ``완결''이다 --- 끝나야 붙는 표지", fontsize=10, pad=8)
fig.tight_layout(); fig.savefig(D / "tags.pdf"); plt.close(fig)

# 그림 2 — 판 이동
fig, ax = plt.subplots(figsize=(7.0, 2.6))
STEPS = [("노트 242\n겹말 뺌", 0.4569, "#8a8f98"),
         ("노트 255\n태그 내용", 0.4623, "#2f6f4f")]
DOM = [("웹툰", 0.3805, 0.4018), ("애니", 0.4873, 0.4873),
       ("모바일", 0.5374, 0.5379), ("세계애니", 0.5199, 0.5199),
       ("게임", 0.6397, 0.6397)]
x = np.arange(len(DOM)); w = 0.34
ax.bar(x - w / 2, [d[1] for d in DOM], width=w, color="#8a8f98", label="17축")
ax.bar(x + w / 2, [d[2] for d in DOM], width=w, color="#2f6f4f", label="19축 (태그 내용)")
for i, d in enumerate(DOM):
    if abs(d[2] - d[1]) > 0.002:
        ax.annotate(f"{d[2]-d[1]:+.3f}\n$t{{=}}2.75$", (i, d[2] + 0.012),
                    ha="center", fontsize=7.4, color="#2f6f4f")
ax.set_xticks(x); ax.set_xticklabels([d[0] for d in DOM], fontsize=8)
ax.set_ylabel("도메인 $\\rho$"); ax.set_ylim(0, 0.76)
ax.legend(fontsize=7.4, frameon=False, ncol=2, loc="upper left")
ax.set_title("웹툰만 오르고 남은 안 흔들린다 --- 전용 이름이라서(노트 250)",
             fontsize=10, pad=7)
fig.tight_layout(); fig.savefig(D / "board.pdf"); plt.close(fig)
print("ok")
