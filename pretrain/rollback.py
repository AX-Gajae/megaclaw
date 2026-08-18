# -*- coding: utf-8 -*-
"""배포 롤백 — 파운데이션 판 배포 사슬의 «복원 절차 정본» (사이클 1003 A부).

🔴 `docs/루프.md` 는 v5.3 으로 동결이라 롤백 조문을 제5장에 못 얹는다 —
   **배포 롤백 절차의 정본은 이 파일의 docstring 과 EPOCHS 레지스트리다**
   (티처 #139 ③ 주의 1 「롤백 절차 조문 부재」 · ⑦-8 발의 — 동결 규칙 3요건:
   ⓐ 티처 발의 #139 ⓑ 실측 근거 = #139 ③ 백업 목록 대조 「완전 복원 가능」 확인
   ⓒ 산문이 아니라 «코드» — 이 스크립트).

절차 (한 시대 = EPOCHS 의 한 항목):
  1. 백업 실재 + 기대 sha 대조 — 하나라도 어긋나면 복원하지 않고 중단 (조항 66).
  2. 시대 표지 파일 «비파괴 개명» — manifest(·conformal 등)를 지우지 않고
     `<이름>.rolledback.<ts>` 로 옮긴다. 소비자 분기는 정확한 파일명을 보므로
     개명만으로 꺼지고, 바이트는 증거로 남는다.
  3. 백업 → 정본 «복사» 복원 (백업은 남긴다 — 롤백 자체가 되돌릴 수 있어야 한다).
  4. 복원 후 각 파일 sha 를 백업 sha 와 대조해 출력.
  5. 소비자 4곳(transition·serve·council·scoreboard) 스모크 — 분기 술어
     (`os.path.exists(MANIFEST)`)가 단일 분기로 돌아왔는지 + 소스에 하위호환
     분기가 실재하는지(문자열 검사) + 복원 model.pt «적재만»(Transition 구성 +
     state_dict 적재 — forward·재학습·산출물 쓰기 없음).
  6. 🔴 창구 8899 무접촉 — 살아있는 프로세스는 메모리 적재분을 계속 서빙한다.
     재시작은 사용자 몫. 재시작 강요·접속 점검 금지 (불가침 조항).
  7. 롤백 뒤 판 재현 확인은 «사용자/조타수 몫»: 구판 채점기가 아니라 현행
     `pretrain/scoreboard.py` 를 그대로 돌리면 하위호환 분기가 단일 model.pt 를
     읽는다 — 복원 검증은 `--out` 으로 새 판을 찍어 전판 수치와 대조한다.

씀:
  python3 pretrain/rollback.py --to pre1002 --dry   # 드라이런 — 쓰기 0 · 검증만
  python3 pretrain/rollback.py --to pre1002         # 실제 복원 (위 1~5 집행)

git 코드 롤백(소비자 분기 자체를 물리는 것)은 이 스크립트 밖이다 — 하위호환
분기(manifest 없으면 단일)라 코드는 두 시대를 다 읽는다. 물리려면 새 커밋으로
(amend·reset 금지 — v5.2 부칙 2 · 철칙).
"""
import argparse
import hashlib
import json
import os
import shutil
import time

ART = "/Users/ax/wm_harvest/foundation"
TROUT = os.path.join(ART, "transition")
LODO = os.path.join(ART, "exp", "lodo")

# 시대 레지스트리 — 각 배포 사이클이 «자기» 복원 항목을 새 커밋으로 더한다.
# 기대 sha 원천: docs/탐색/1002.md §8-2 (티처 #139 ③ 이 19/19 실측 재확인).
EPOCHS = {
    "pre1002": {
        "설명": "1002 앙상블 배포 «이전»(단일 model.pt · seed 997 시대)로 복원",
        "개명(비파괴 — 시대 표지 끄기)": [
            os.path.join(TROUT, "ensemble_manifest.json"),      # 필수 — 남기면 앙상블 분기가 산다
            os.path.join(TROUT, "conformal.json"),              # 있으면 — 1003 보정층은 manifest 시대에 묶인다
        ],
        "복원(백업 → 정본 · 복사)": [
            (os.path.join(TROUT, "model_pre1002.pt"), os.path.join(TROUT, "model.pt")),
            (os.path.join(TROUT, "leaderboard_pre1002.json"), os.path.join(TROUT, "leaderboard.json")),
            (os.path.join(TROUT, "report_pre1002.json"), os.path.join(TROUT, "report.json")),
            (os.path.join(LODO, "results_pre1002.json"), os.path.join(LODO, "results.json")),
        ],
        "백업 기대 sha (조항 66)": {
            os.path.join(TROUT, "model_pre1002.pt"): "5122c2eb3c21bfbd",
            os.path.join(TROUT, "leaderboard_pre1002.json"): "da73fed24780e355",
            os.path.join(TROUT, "report_pre1002.json"): "c4c37793a10b1bc5",
            os.path.join(LODO, "results_pre1002.json"): "6dad46f03f40be43",
        },
        "필수 개명": [os.path.join(TROUT, "ensemble_manifest.json")],
        # 티처 #140 ⑤ 주의 2 ㉮ — 스모크 ③ 이 쓸 모형 백업 키(없는 시대는 None →
        # 스모크 ③ 은 「복원 manifest 첫 구성원 적재」로 대체하거나 건너뛴다)
        "model 백업 키": os.path.join(TROUT, "model_pre1002.pt"),
    },
    "pre1004": {
        "설명": "1004 홀드아웃 재학습 + 등각 보정 배포 «이전»(1002 앙상블 1201~1205 시대)로 복원",
        "개명(비파괴 — 시대 표지 끄기)": [
            os.path.join(TROUT, "conformal.json"),              # 필수 — 1004 보정층 시대 표지
            os.path.join(TROUT, "ensemble_manifest.json"),      # 필수 — 1004 manifest (복원이 1002 판으로 갈아끼움)
        ],
        "복원(백업 → 정본 · 복사)": [
            (os.path.join(TROUT, "ensemble_manifest_pre1004.json"), os.path.join(TROUT, "ensemble_manifest.json")),
            (os.path.join(TROUT, "leaderboard_pre1004.json"), os.path.join(TROUT, "leaderboard.json")),
            (os.path.join(TROUT, "report_pre1004.json"), os.path.join(TROUT, "report.json")),
            (os.path.join(LODO, "results_pre1004.json"), os.path.join(LODO, "results.json")),
        ],
        "백업 기대 sha (조항 66)": {
            os.path.join(TROUT, "ensemble_manifest_pre1004.json"): "af7cebd02e77af9c",
            os.path.join(TROUT, "leaderboard_pre1004.json"): "332bda6caf87cee1",
            os.path.join(TROUT, "report_pre1004.json"): "a8de5293852b5d9a",
            os.path.join(LODO, "results_pre1004.json"): "5eb0c4a534606600",
        },
        "필수 개명": [os.path.join(TROUT, "conformal.json"),
                   os.path.join(TROUT, "ensemble_manifest.json")],
        # 모형 백업 = manifest 사본이 담당 — 구성원 pt(1201~1205)는 ensemble1002/ 에
        # 바이트 무변으로 남는다. 스모크 ③ 은 복원 manifest 첫 구성원(1201)을 적재한다.
        "model 백업 키": None,
    },
}

# 소비자 4곳 — 전부 «manifest 있으면 앙상블 · 없으면 단일 model.pt» 하위호환 분기.
CONSUMERS = {
    "pretrain/transition.py": ("MANIFEST", "model.pt"),
    "pretrain/serve.py": ("MANIFEST", "model.pt"),
    "pretrain/council.py": ("serve 경유", "serve 경유"),   # transition 열은 serve 의 TR 를 쓴다
    "pretrain/scoreboard.py": ("MANIFEST", "MODEL_PT"),
}
REPO = "/Users/ax/world_model"


def sha16(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def smoke(epoch, dry, log):
    """소비자 4곳 단일 분기 스모크 — 모형 «적재만» · 창구 무접촉 · 산출물 쓰기 0."""
    manifest = os.path.join(TROUT, "ensemble_manifest.json")
    # 복원 «후» manifest 실재 여부는 시대가 정한다: 복원 목록에 manifest 가 있으면 실재(앙상블 분기)
    restores_manifest = any(d == manifest
                            for _b, d in EPOCHS[epoch]["복원(백업 → 정본 · 복사)"])
    단일 = (not restores_manifest) if dry else (not os.path.exists(manifest))
    log("스모크① 분기 술어",
        ("🔴 가정(드라이런 — 실측 아님): 이 시대 복원 «후» manifest %s → 소비자 4곳 전부 %s 분기"
         % ("실재(복원 목록에 있음)" if restores_manifest else "부재",
            "단일" if 단일 else "앙상블")
         if dry else "manifest %s → 소비자 4곳 전부 %s 분기(실측)"
         % ("부재" if 단일 else "실재", "단일" if 단일 else "앙상블")))
    for rel, needles in CONSUMERS.items():
        src = open(os.path.join(REPO, rel), encoding="utf-8").read()
        has = all((n in src) for n in needles if n != "serve 경유")
        log("스모크② 분기 실재(%s)" % rel,
            "하위호환 분기 문자열 확인 %s" % ("✔" if (has or needles[0] == "serve 경유") else "🔴 없음"))
    # 모형 적재만(스모크 ③) — 시대별 「model 백업 키」로 일반화 (티처 #140 ⑤ 주의 2 ㉮:
    # 하드코딩 dict 조회는 model 백업 없는 시대(pre1003 형)에서 KeyError 로 죽는다).
    ep = EPOCHS[epoch]
    mkey = ep.get("model 백업 키")
    if mkey is None:
        mp = None
        # model 백업이 없는 시대 — 복원 manifest 의 첫 구성원을 적재 대상으로 삼는다
        man_bak = next((b for b, d in ep["복원(백업 → 정본 · 복사)"]
                        if d.endswith("ensemble_manifest.json")), None)
        if man_bak and os.path.exists(man_bak):
            _man = json.load(open(man_bak, encoding="utf-8"))
            _first = sorted(_man["구성원"].items())[0][1]["경로"]
            if os.path.exists(_first):
                mp = _first
        if mp is None:
            log("스모크③ 모형 적재만", "건너뜀 — 이 시대는 model 백업 키가 없고 "
                "복원 manifest 구성원도 못 찾았다(파일 안전과 무관 · 로그만)")
            log("스모크④ 창구 8899", "무접촉 — 재시작은 사용자 몫")
            return
    else:
        mp = (mkey if dry else dict(ep["복원(백업 → 정본 · 복사)"]).get(mkey, mkey))
    import torch
    torch.set_num_threads(4)
    import sys
    sys.path.insert(0, REPO)
    from pretrain.transition import Transition
    ck = torch.load(mp, map_location="cpu", weights_only=False)
    m = Transition(ck["d_in"], hidden=ck["hidden"])
    m.load_state_dict(ck["model"])
    m.eval()
    n_par = sum(p.numel() for p in m.parameters())
    log("스모크③ 모형 적재만", "%s → Transition(d_in=%d, hidden=%d) 적재 ✔ · params %d · forward 0 · 쓰기 0"
        % (os.path.basename(mp), ck["d_in"], ck["hidden"], n_par))
    log("스모크④ 창구 8899", "무접촉 — 재시작은 사용자 몫 (메모리 적재분은 롤백과 무관하게 옛 그대로)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, choices=sorted(EPOCHS))
    ap.add_argument("--dry", action="store_true", help="쓰기 0 — 검증·계획 출력만")
    a = ap.parse_args()
    ep = EPOCHS[a.to]
    lines = []

    def log(k, v):
        line = "[%s] %s: %s" % ("드라이런" if a.dry else "집행", k, v)
        lines.append(line)
        print(line)

    log("시대", "%s — %s" % (a.to, ep["설명"]))
    # 1. 백업 실재 + 기대 sha 대조 (조항 66) — 어긋나면 복원 없이 중단
    ok = True
    for p, want in ep["백업 기대 sha (조항 66)"].items():
        got = sha16(p) if os.path.exists(p) else "없음"
        match = got == want
        ok = ok and match
        log("① 백업 대조", "%s 기대 %s 실측 %s %s"
            % (os.path.basename(p), want, got, "✔" if match else "🔴 불일치"))
    if not ok:
        log("중단", "🔴 백업 sha 불일치 — 복원하지 않는다 (조항 66)")
        return 1
    # 2. 시대 표지 비파괴 개명
    ts = time.strftime("%Y%m%dT%H%M%S")
    for p in ep["개명(비파괴 — 시대 표지 끄기)"]:
        exists = os.path.exists(p)
        필수 = p in ep.get("필수 개명", [])
        if not exists:
            log("② 개명", "%s — 없음 (%s)" % (os.path.basename(p),
                "🔴 필수인데 없다 — 이미 롤백됐거나 시대가 다르다" if 필수 else "선택 — 건너뜀"))
            continue
        dst = p + ".rolledback." + ts
        if a.dry:
            log("② 개명(예정)", "%s → %s (바이트 보존 · sha %s)"
                % (os.path.basename(p), os.path.basename(dst), sha16(p)))
        else:
            shutil.move(p, dst)
            log("② 개명", "%s → %s ✔" % (os.path.basename(p), os.path.basename(dst)))
    # 3~4. 복원(복사) + 복원 후 sha 대조 출력
    for bak, dst in ep["복원(백업 → 정본 · 복사)"]:
        want = sha16(bak)
        if a.dry:
            cur = sha16(dst) if os.path.exists(dst) else "없음"
            log("③ 복원(예정)", "%s → %s (백업 sha %s · 현 정본 %s)"
                % (os.path.basename(bak), os.path.basename(dst), want, cur))
        else:
            shutil.copy2(bak, dst)
            got = sha16(dst)
            log("④ 복원 후 대조", "%s sha %s = 백업 %s %s"
                % (os.path.basename(dst), got, want, "✔" if got == want else "🔴 불일치"))
    # 5. 소비자 스모크
    smoke(a.to, a.dry, log)
    log("끝", ("드라이런 — 파일 쓰기 0" if a.dry else "복원 집행 완료") +
        " · 판 재현 확인은 scoreboard.py --out 새 판으로 (docstring 7)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
