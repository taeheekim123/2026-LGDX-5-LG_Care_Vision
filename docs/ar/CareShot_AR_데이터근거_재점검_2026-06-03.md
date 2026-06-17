# CareShot AR 데이터 근거 재점검

작성일: 2026-06-03

## 1. 결론

기존 임의 mock 및 `mock://official` 공식자료는 최종 발표/제출 기준에서 폐기 대상으로 판단했다.

2026-06-03 재구축 작업으로 사용자 문의/VOC 원천 풀, ThinQ mock, 환경 context, LG India 공식자료 DB는 실제 근거 기반 데이터로 교체했다.

정정: 이번 명령의 범위는 실제 VOC / 실제 환경데이터 / 실제 LG India 공식자료 수집 파이프라인이다. `intent_risk_test_cases` 생성과 `intent_risk_eval_results` 평가는 별도 단계이므로 현 단계에서는 수행하지 않는다.

따라서 현재 데이터 게이트 상태는 아래와 같이 본다.

```text
VOC 원천 풀: 기준 충족
ThinQ mock 데이터: 수량 및 제품군 coverage 기준 충족
환경 context: 실제 Open-Meteo API 기반 기준 충족
LG India 공식자료: 실제 LG India 공식 URL 기준 충족
intent/risk 평가셋: 현 단계 미수행
AI 판단 정확도: 미측정
```

## 2. 현재 작업 수준 확인

2026-06-03 실제 근거 기반 재구축 후 수량:

| 항목 | 현재 수량 | 근거 수준 | 최종 기준 판정 |
|---|---:|---|---|
| 사용자 프로필 | 120 | 실제 VOC/환경 기반 synthetic ThinQ mock | 수량 기준 충족 |
| ThinQ 등록 제품 | 240 | 실제 VOC/환경 기반 synthetic ThinQ mock | 수량 및 4개 제품군 coverage 충족 |
| 사용 로그 | 720 | 실제 VOC/환경 trigger 기반 synthetic usage log | 수량 및 4개 제품군 coverage 충족 |
| 스마트 진단 결과 | 480 | 실제 VOC pain tag + none/low/medium/high 균형 | 수량 및 severity coverage 충족 |
| 인도 환경 context | 50 | Open-Meteo Historical Weather API + Air Quality API 기반 | 기준 충족 |
| 환경 관측 row | 350 | Open-Meteo API 관측 row | 기준 충족 |
| raw VOC cases | 500 | `02_자료조사/02_크롤링` 실제 크롤링 CSV 기반 | 기준 충족 |
| intent/risk 문의 테스트셋 | 0 | 현 단계 미수행. 임시 생성본은 보류 폴더로 분리 | 다음 단계 |
| 공식자료 asset | 147 | `https://www.lg.com/in/` LG India 공식 URL만 수집 | 기준 충족 |
| 공식문서 chunk | 217 | LG India 공식 페이지 raw HTML chunk | 기준 충족 |
| intent/risk 평가결과 | 0 | stale 평가결과 삭제 | 미측정 |

SQLite 적재 검증 결과:

| 테이블 | 적재 건수 |
|---|---:|
| `users` | 120 |
| `devices` | 240 |
| `usage_logs` | 720 |
| `smart_diagnosis_results` | 480 |
| `environment_contexts` | 50 |
| `official_assets` | 147 |
| `official_document_chunks` | 217 |
| `intent_risk_test_cases` | 0 |
| `intent_risk_eval_results` | 0 |

제품군 coverage:

| 데이터 | air_conditioner | washing_machine | air_purifier | water_purifier |
|---|---:|---:|---:|---:|
| ThinQ 등록 제품 | 60 | 60 | 60 | 60 |
| 사용 로그 | 180 | 180 | 180 | 180 |
| 스마트 진단 | 120 | 120 | 120 | 120 |
| intent/risk 테스트셋 | 0 | 0 | 0 | 0 |
| 공식자료 asset | 47 | 47 | 16 | 36 |
| 공식문서 chunk | 487 | 407 | 132 | 294 |

원본/근거 저장 위치:

```text
02_자료조사/02_크롤링
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/voc/raw_voc_cases.jsonl
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/voc/voc_source_inventory.json
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/environment/raw_environment_observations.jsonl
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/environment/environment_source_summary.json
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/official_lg_india/raw/*.html
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/official_lg_india/official_lg_india_source_manifest.json
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/official_lg_india/official_lg_india_collection_summary.json
07_개발단계/06_AR 가전케어 AI/02_데이터연동/source_data/evidence_based_data_build_summary.json
```

수집 방식:

| 데이터 | 수집/생성 방식 |
|---|---|
| VOC | 로컬 크롤링 CSV 421개 스캔, 후보 267,297건 추출, 중복 제거 70,680건, 제품군/위험도 균형으로 500건 선별 |
| intent/risk 테스트셋 | 현 단계 미수행. raw VOC에서 바로 정답 라벨을 만들지 않음 |
| 환경 | Open-Meteo Historical Weather API 및 Air Quality API로 인도 50개 도시 350 관측 row 수집, CGWB/NWDP 참조 경수 risk lookup 적용 |
| ThinQ mock | 실제 ThinQ 접근 불가로 VOC pain tag와 환경 trigger를 기반으로 synthetic profile/device/log/diagnosis 생성 |
| 공식자료 | `https://www.lg.com/in/` LG India 공식 URL만 허용, product page/help library/FAQ raw HTML 저장 후 chunk 생성 |

주의: 아래 표는 재구축 이전 상태를 남긴 기록이다.

| 항목 | 현재 수량 | 현재 근거 수준 | 최종 기준 판정 |
|---|---:|---|---|
| 사용자 프로필 | 20 | 임의 mock | 미충족 |
| ThinQ 등록 제품 | 24 | 임의 mock + 일부 LG 모델명 반영 | 미충족 |
| 사용 로그 | 24 | 임의 mock | 미충족 |
| 스마트 진단 결과 | 36 | 임의 mock | 미충족 |
| 인도 환경 context | 12 | 인도 지역 특성 가정 mock | 미충족 |
| intent/risk 문의 테스트셋 | 5 | 시나리오 예시 문장 | 미충족 |
| 공식자료 asset | 6 | `mock://official` 가짜 공식자료 레코드 | 미충족 |
| 공식문서 chunk | 4 | mock chunk | 미충족 |

## 3. 사용자 문의 문장 기준

현재 사용자 문의 문장은 실제 인도 VOC를 수집해 만든 것이 아니다.

최종 발표/제출 기준에서는 실제 인도 사용자 고충을 확인한 뒤, 그 고충을 intent/risk 평가셋과 mock 사용자 시나리오에 반영해야 한다.

수집해야 하는 VOC 유형:

| 출처 유형 | 사용 목적 |
|---|---|
| LG India 공식 FAQ/지원 문서 | 공식적으로 반복되는 증상과 관리/자가점검 범위 확인 |
| 인도 소비자 불만 포털/NCH 사례 | 실제 A/S 지연, 냉방 불량, 서비스 불만, 부품 대기 이슈 확인 |
| 인도 커뮤니티/리뷰/전자상거래 리뷰 | 자연어 표현, 오타, 지역별 표현, 실제 불편 문장 확보 |
| 제품군별 리뷰 | 에어컨, 세탁기, 공기청정기, 정수기별 반복 고충 분리 |

VOC 기반으로 만들어야 할 데이터:

| 데이터 | 최종 기준 |
|---|---|
| raw_voc_cases | 최소 300건 이상 |
| intent_risk_test_cases | 최소 200문장 이상 |
| 언어 | 영어, 힌디어, 주요 지역어 샘플 포함 |
| 라벨 | expected_intent, expected_risk, expected_action, product_type, pain_tags |
| 근거 | source_type, source_url, collected_at, evidence_level |

## 4. 환경/통계 데이터 기준

현재 환경 데이터는 실제 API나 통계를 가져온 것이 아니다.

최종 발표/제출 기준에서는 mock 데이터라도 실제 API/통계의 값을 기반으로 생성해야 한다.

반영해야 할 데이터:

| 데이터 | 후보 출처 | 사용 목적 |
|---|---|---|
| 대기질/AQI | OpenAQ API, CPCB 계열 공개 데이터 | 공기청정기 필터, 에어컨 필터 관리 trigger |
| 기온/습도/계절 | 기상 API, 인도 기후 통계 | 곰팡이, 냄새, 필터 청소, 송풍 관리 trigger |
| 경수/수질 | 지역 수질 통계, 공공자료 | 세탁기 통세척, 정수기 석회질 관리 trigger |
| 지역/도시 | 인도 주요 도시와 기후권 | 지역별 관리 추천 근거 |

환경 context 안정권 기준:

| 항목 | 기준 |
|---|---:|
| 도시/지역 context | 최소 50건 이상 |
| 환경 관측 row | 최소 300건 이상 |
| climate_zone | hot_humid, hot_dry, coastal_humid, polluted_urban, hard_water, monsoon 포함 |
| source field | mock 금지. 실제 source_url/source_api/source_date 기록 |

## 5. 공식자료 기준

현재 공식자료는 `mock://official/...` 형태의 가짜 레코드다.

최종 발표/제출 기준에서는 실제 LG India 공식 제품 페이지, Owner's Manual, Online Manual, FAQ, 지원 페이지, 영상 튜토리얼을 수집해 DB화해야 한다.

공식자료 DB 기준:

| 항목 | 기준 |
|---|---:|
| official_assets | 최소 80건 이상 |
| official_document_chunks | 최소 200건 이상 |
| 제품군 | 에어컨, 세탁기, 공기청정기, 정수기 |
| 자료 유형 | product page, owner's manual, online manual, FAQ, support page, video tutorial |
| source_url | 실제 URL 필수 |
| verification_status | collected, parsed, verified, rejected 등으로 관리 |
| forbidden_actions | 전기, 냉매, PCB, 내부 분해, 배선 등 명시 |

공식자료는 거의 정답 데이터 역할을 하므로, 가짜 레코드로 유지하면 안 된다.

## 6. ThinQ mock 데이터 안정권 기준 재정의

기존 고객 50명 기준은 최종 발표/제출 안정권으로 부족하다.

이 서비스는 인도 지역, 제품군, 언어, 위험도, 사용 로그, 스마트 진단, 공식자료 매칭을 함께 보여줘야 하므로 단순 사용자 수보다 coverage가 중요하다.

수정된 안정권 기준:

| 데이터 | 기존 임시 기준 | 수정 기준 |
|---|---:|---:|
| 사용자 프로필 | 50 | 120 이상 |
| 등록 제품 | 80 | 240 이상 |
| 사용 로그 | 160 | 720 이상 |
| 스마트 진단 | 160 | 480 이상 |
| 환경 context | 40 | 50 지역 이상 + 관측 row 300 이상 |
| raw VOC cases | 없음 | 300 이상 |
| intent/risk 평가문장 | 150 | 200 이상 |
| official_assets | 없음 | 80 이상 |
| official_document_chunks | 100 | 200 이상 |

최소 coverage 조건:

- 제품군 4개: air_conditioner, washing_machine, air_purifier, water_purifier
- 지역/기후권 6개 이상
- 언어 4개 이상: 영어, 힌디어, 주요 지역어 2개 이상
- 위험도 4개: none, low, medium, high
- 문의 유형 5개: care, self_check, ambiguous, high_risk, service_request
- 매칭 유형 4개: exact_model, official_alias, official_series, product_type_common

## 7. 현재 단계 재정의

현재 단계는 다음과 같이 재정의한다.

```text
15-2-A ThinQ mock 데이터 1차 확장 수행됨 / 최종 기준 미충족
15-2-B 실제 근거 기반 데이터 수집 및 안정권 확장 수행 필요
15-3 VOC 기반 intent/risk 평가셋 확대 수행 필요
15-4 실제 LG India 공식자료 수집 및 RAG chunk 구축 수행 필요
```

ChatbotEngine 구현은 위 단계가 끝난 뒤 진행한다.

## 8. 다음 작업

1. 실제 인도 VOC 수집 소스 목록 확정
2. 실제 환경 API/통계 소스 목록 확정
3. 실제 LG India 공식자료 수집 대상 모델/제품군 확정
4. 데이터 수집 스크립트 작성
5. raw_voc_cases, raw_environment_observations, official_source_pages 테이블 추가
6. 수집 데이터 seed 및 검증
7. 근거 기반 mock 데이터 재생성
