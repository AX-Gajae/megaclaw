"""2차 수집 병합 — Kimi 파이프라인의 중복제거 로직 이식 + 기존 시장 층과 통합.

입력: data/market_raw/crawl2_rows.jsonl (수집 에이전트 산출 병합본)
처리: ① 행 정합성 필터(수치 있는데 출처 3종 없으면 폐기) ② 웨이브 내 중복제거(토큰 유사도
  +기간 겹침+장소 키워드 — Kimi are_dup 이식) ③ 기존 408건과 대조(겹치면 기존 유지, 새 수치만
  alt_figures로 보강) ④ 신규는 MKT2- 접두 ID로 data/market_records/ 편입(단일이벤트 필터 동일)
⑤ internal_code가 있는 행은 cycle_log/crawl2_internal_hits.jsonl로 별도 기록(내부 라벨 충전 후보).

사용: python3 -m ingest.market_merge
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

RAW = Path("data/market_raw/crawl2_rows.jsonl")
MK_DIR = Path("data/market_records")

GENERIC = {'팝업', '팝업스토어', '스토어', 'popup', 'store', 'the', 'at', 'in', 'x', '서울', '오픈', '공식',
           '국내', '첫', '개최', '진행', '기념', '개봉', 'with', '위드', '2023', '2024', '2025', '2026',
           '페스타', '페스티벌', '시리즈', '회차', '시즌', '팝업전시', '오프라인', '브랜드'}
VENUE_KEY = ['성수', '여의도', '더현대', '잠실', '월드몰', '용산', '아이파크', '강남', '홍대', '한남', '압구정',
             '도산', '코엑스', '판교', '수원', '하남', '고양', '부산', '센텀', '대구', '대전', '광주', '을지로',
             '연남', '타임스퀘어', '스타필드', '신세계', '롯데', '명동', '에버랜드', '킨텍스', 'ddp', '동대문']


def parse_d(d):
    try:
        return date.fromisoformat(d)
    except (ValueError, TypeError):
        return None


def tokens(s):
    if not s:
        return set()
    s = re.sub(r'[^0-9a-z가-힣\s]', ' ', str(s).lower())
    return {t for t in s.split() if len(t) >= 2 and t not in GENERIC}


def venue_keys(r):
    v = str(r.get('venue') or '') + str(r.get('city') or '')
    return {k for k in VENUE_KEY if k in v.lower() or k in v}


def are_dup(a, b):
    ta, tb = tokens(a.get('event_name')), tokens(b.get('event_name'))
    ba, bb = tokens(a.get('brand')), tokens(b.get('brand'))
    if not ta or not tb:
        return False
    sim = len(ta & tb) / max(1, min(len(ta), len(tb)))
    brand_shared = bool(ba & bb)
    a1, a2 = parse_d(a.get('period_from')), parse_d(a.get('period_to'))
    b1, b2 = parse_d(b.get('period_from')), parse_d(b.get('period_to'))
    if a1 and a2 and b1 and b2:
        if not (a1 <= b2 and b1 <= a2):
            return False
        return sim >= 0.5 or (brand_shared and sim >= 0.34)
    if sim < 0.6 or not brand_shared:
        return False
    return bool(venue_keys(a) & venue_keys(b))


def mk_shape(m):
    """기존 market_records 파일을 dup 비교용 평면 행으로."""
    c = m['conditions']
    return {'event_name': m.get('event_name'), 'brand': m.get('brand'),
            'venue': c.get('venue'), 'city': c.get('city'),
            'period_from': c.get('period_from'), 'period_to': c.get('period_to')}


def valid(r):
    if r.get('found') is False:
        return False
    if not (r.get('event_name') and r.get('brand')):
        return False
    if r.get('visitors_total') and not (r.get('visitors_source_quote') and r.get('visitors_source_url')):
        return False  # 수치는 삼중 출처 필수
    if r.get('sales_krw') and not (r.get('sales_source_quote') and r.get('sales_source_url')):
        r['sales_krw'] = None
    # 'unknown' 문자열은 신호 부재를 뜻하므로 신호로 치지 않는다
    sig = [x for x in (r.get('waiting'), r.get('sold_out'))
           if x and str(x).strip().lower() not in ('unknown', 'none', 'null', '')]
    return bool(r.get('visitors_total') or r.get('sales_krw') or sig
                or '수치 미보도' in str(r.get('notes') or ''))


def main() -> int:
    rows, bad = [], 0
    for line in RAW.read_text().splitlines():
        line = line.strip().strip('`')
        if not line or line.startswith('{') is False:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if r.get('internal_code'):
            # 우리가 수행한 팝업 — 내부 뱅크에 이미 있으므로 시장 층 편입 대상이 아니다
            # (apply_external_labels 가 별도로 라벨 충전 처리)
            with open('cycle_log/crawl2_internal_hits.jsonl', 'a') as f:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
            continue
        if valid(r):
            rows.append(r)
    print(f"입력 파싱: 유효 {len(rows)} / 파싱실패 {bad}")

    # 웨이브 내 중복제거 (풍부한 행 우선)
    def rich(r):
        return (r.get('visitors_total') is not None) * 3 + (r.get('sales_krw') is not None) * 3 + \
               bool(r.get('period_from')) * 2 + bool(r.get('counting_basis_note'))
    rows.sort(key=rich, reverse=True)
    kept = []
    for r in rows:
        if not any(are_dup(r, k) for k in kept):
            kept.append(r)
    print(f"웨이브 내 dedup: {len(rows)} → {len(kept)}")

    # 기존 408건과 대조
    existing = [json.loads(p.read_text()) for p in MK_DIR.glob('*.json')]
    ex_shapes = [(m, mk_shape(m)) for m in existing]
    new_rows, dup_ex = [], 0
    for r in kept:
        hit = next((m for m, s in ex_shapes if are_dup(r, s)), None)
        if hit:
            dup_ex += 1
            if r.get('visitors_total') and r['visitors_total'] != hit['outcome'].get('visitors_total'):
                hit.setdefault('outcome', {}).setdefault('alt_figures', []).append(
                    {'metric': 'visitors_total', 'figure': r['visitors_total'],
                     'scope_note': f"2차수집 대안치: {str(r.get('counting_basis_note') or '')[:60]}",
                     'source_url': r.get('visitors_source_url'), 'source_date': r.get('visitors_source_date')})
                (MK_DIR / f"{hit['market_record_id']}.json").write_text(json.dumps(hit, ensure_ascii=False, indent=2))
        else:
            new_rows.append(r)
    print(f"기존과 중복 {dup_ex} (대안치 보강) / 신규 {len(new_rows)}")

    # 신규 편입
    seq = 0
    for r in new_rows:
        seq += 1
        y = (r.get('period_from') or '0000')[:4]
        rid = f"MKT2-{y}-{seq:04d}"
        rec = {
            'market_record_id': rid,
            'event_name': r.get('event_name'), 'brand': r.get('brand'),
            'ip_or_collab': r.get('ip_or_collab'), 'category': r.get('category') or 'other',
            'intervention': {'concept_description': str(r.get('notes') or '')[:200] or None,
                              'experience_elements': [], 'promotions': [],
                              'is_free_entry': None, 'reservation_required': None},
            'conditions': {'venue': r.get('venue'), 'venue_type': 'other',
                            'neighborhood': None, 'city': r.get('city'),
                            'period_from': r.get('period_from'), 'period_to': r.get('period_to'),
                            'area_pyeong': None, 'multi_store': False},
            'outcome': {'visitors_total': r.get('visitors_total'), 'visitors_period_days': None,
                         'counting_basis': r.get('counting_basis') or 'unknown',
                         'counting_basis_note': r.get('counting_basis_note'),
                         'visitors_source_quote': r.get('visitors_source_quote'),
                         'visitors_source_url': r.get('visitors_source_url'),
                         'visitors_source_date': r.get('visitors_source_date'),
                         'sales_krw': r.get('sales_krw'), 'sales_source_quote': r.get('sales_source_quote'),
                         'sales_source_url': r.get('sales_source_url'), 'sales_source_date': r.get('sales_source_date'),
                         'demand_signals': {'waiting_time_reported': r.get('waiting'),
                                             'sold_out': r.get('sold_out'), 'reservation_fill': None,
                                             'signal_quotes': []},
                         'conflict': False, 'alt_figures': []},
            'extraction_confidence': 'medium',
            'notes': (str(r.get('notes') or '') + ' | 2차 수집(2026-07-27)').strip(' |'),
        }
        (MK_DIR / f"{rid}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    print(f"신규 편입: {seq}건 (MKT2- 접두)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
