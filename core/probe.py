"""로컬 모델 탐침 — **빈 응답을 성공으로 읽지 않는다** (노트 891).

**왜 이 파일이 있나.** 2026-08-10 하루에 같은 병을 **세 번** 앓았다.

  ① 크론이 `400 credit balance is too low` 를 내고도 **종료 코드 0** 으로 끝났다.
  ② 텀블벅·네이버웹툰이 **HTTP 200** 을 내는데 4,579바이트 JS 껍데기였다.
  ③ 그리고 이 모듈이 생긴 이유 --- ollama 탐침에서 **11/11 이 "안다"** 로 나왔는데
     `response` 가 **전부 빈 문자열**이었다. `thinking` 이 별도 필드로 나가면서
     `num_predict` 를 사고에 다 써 본문이 잘렸고(`done_reason: "length"`),
     내 판정이 *"빈 문자열에 '모름'이 없으니 안다"* 였다. 고쳐서 다시 재니 **5/11**.

셋 다 **성공 신호를 작업의 성공으로 읽은 것**이다. 신호는 층마다 이름이 다르다 ---
종료 코드 · HTTP 상태 · `done` 플래그. **전부 거짓말할 수 있다.**

**그래서 이 모듈의 규칙은 하나다 --- 판정하기 전에 응답이 쓸 만한지 먼저 본다.**

  · `response` 가 비었으면 **판정 불가**(모름이 아니다 --- 그 둘을 섞으면 미지율이 0 이 된다)
  · `done_reason != "stop"` 이면 **잘린 것**이다. 특히 `"length"` 는 예산 부족이지 답이 아니다
  · thinking 모델은 `think=False` 로 끄거나 예산을 따로 준다

쓰는 법::

    from core.probe import ask, knows
    r = ask("만화 'Wonder 3' 을 아는가? 모르면 '모름'.")
    r["쓸만한가"], r["본문"], r["사유"]
"""
from __future__ import annotations

import json
import urllib.request

HOST = "http://127.0.0.1:11434"
#: 사고를 별도 필드로 내보내는 모델들. `think=False` 를 안 주면 본문이 빈다.
DEFAULT_MODEL = "qwen3.6:35b-a3b"


def ask(prompt: str, model: str = DEFAULT_MODEL, think: bool = False,
        num_predict: int = 200, temperature: float = 0.0,
        timeout: int = 240) -> dict:
    """한 번 묻는다. **판정은 안 한다** --- 쓸 만한지와 본문만 돌려준다."""
    body = {"model": model, "prompt": prompt, "stream": False, "think": think,
            "options": {"temperature": temperature, "num_predict": num_predict}}
    try:
        req = urllib.request.Request(
            f"{HOST}/api/generate", data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"})
        d = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    except Exception as e:
        return {"쓸만한가": False, "사유": f"{type(e).__name__}: {e}"[:200],
                "본문": "", "done_reason": None}

    txt = (d.get("response") or "").strip()
    dr = d.get("done_reason")
    # 🔴 **여기가 이 파일의 전부다.** 셋을 갈라서 낸다 ---
    #    쓸 만한 응답 / 잘린 응답 / 빈 응답. 뒤 둘을 '모름' 과 섞으면 안 된다.
    if not txt:
        return {"쓸만한가": False, "본문": "", "done_reason": dr,
                "사유": ("본문이 비었다(`thinking` 이 예산을 다 썼을 수 있다 --- "
                        "`think=False` 로 다시 물어라)" if dr == "length"
                        else f"본문이 비었다(done_reason={dr})"),
                "생각": (d.get("thinking") or "")[:300]}
    if dr != "stop":
        return {"쓸만한가": False, "본문": txt, "done_reason": dr,
                "사유": f"응답이 잘렸다(done_reason={dr}) --- 예산을 늘려라"}
    return {"쓸만한가": True, "본문": txt, "done_reason": dr, "사유": ""}


def knows(title: str, kind: str = "만화", **kw) -> dict:
    """'이 작품을 아는가' 를 묻는다. **셋으로 답한다 --- 안다 / 모른다 / 판정 불가.**

    `모름` 과 `판정 불가` 를 갈라야 미지율이 뜻을 갖는다. 2026-08-10 의 실수가
    정확히 이 둘을 합친 것이었고, 그 결과 미지율이 **0%** 로 나왔다(참값 55%).
    """
    r = ask(f"{kind} '{title}' 을 아는가? 안다면 줄거리를 한 문장으로, "
            f"모르면 정확히 '모름' 한 단어로만 답하라. 추측 금지.", **kw)
    if not r["쓸만한가"]:
        return {**r, "판정": "판정 불가"}
    body = r["본문"].replace("\n", " ")
    return {**r, "본문": body,
            "판정": "모른다" if "모름" in body[:12] else "안다"}


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "Wonder 3"
    print(json.dumps(knows(t), ensure_ascii=False, indent=1))
