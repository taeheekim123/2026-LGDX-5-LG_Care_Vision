# CareShot AR 가전케어 AI 개발 방향 로드맵

## 1. 최종 개발 방향

CareShot AR 가전케어 AI는 ThinQ 앱 내에서 두 가지 진입 흐름을 통해 `self_care`, `self_as`, `expert_as` 세 가지 서비스 결과를 제공하는 서비스다.

```text
1. self care 예방 알림형
   ThinQ 등록 가전 사용 로그 + 회원가입 주소 기반 환경 API + 기존 care 이력 기반 Care Risk Score
   -> self care 알림
   -> 공식 콘텐츠와 AR Guide를 함께 제공

2. self A/S / expert A/S 사용자 문의형
   챗봇 자연어 문의
   -> 위험도와 공식자료 근거 확인
   -> Low/Medium은 self_as로 공식 콘텐츠와 AR Guide 함께 제공
   -> High Risk는 expert_as로 공식 A/S 연결
```

현재 로컬 개발 환경은 ThinQ 실제 앱에 접근할 수 없으므로 자체 챗봇 화면과 ThinQ mock 데이터를 사용한다. 단, 구조는 최종 서비스 방향과 맞춘다.

최종 흐름은 다음과 같다.

```text
self care 예방 알림형:
회원가입 주소 기반 환경 API + DB cache
→ ThinQ 등록 제품/사용 로그 조회
→ Care Risk Score 계산
→ self care 알림 생성
→ 공식 콘텐츠와 AR Guide 함께 제공

self A/S / expert A/S 사용자 문의형:
챗봇 문의 입력
→ 사용자/제품/사용로그/스마트진단/환경 데이터 조회
→ self_care / self_as / expert_as 분류
→ Low / Medium / High 위험도 판단
→ 공식자료 DB strict matching
→ Low/Medium이면 공식 콘텐츠와 AR Guide 함께 제공
→ Reference Image 기반 AR Overlay 표시
→ 공식 콘텐츠 열람/AR Session/care activity 저장
→ High Risk는 AR 차단 후 expert A/S 연결
```

AR 방식은 객체인식 AR이 아니라 `image-based reference overlay`다. ThinQ 등록 제품에서 `model_name`이 exact로 들어오므로, 백엔드는 모델명을 기준으로 `product_type`, `structure_type`, `reference_image`, `part_map_version`, `AR guide template`을 매핑한다.

최종 발표 시연은 에어컨 3개 구조 타입을 대상으로 한다.

```text
wall_mounted_ac: 벽걸이형
standing_ac: 스탠드형
window_ac: 창문형
```

개발 구조는 에어컨 3종만을 위한 하드코딩이 아니라, 에어컨/세탁기/공기청정기/정수기 전체 제품군과 다양한 모델명을 대상으로 확장 가능하게 만든다.

## 2. 현재 구현 상태

현재 `06_AR 가전케어 AI` 폴더 기준으로 다음까지 구현되어 있다.

| 영역 | 현재 상태 |
|---|---|
| 데이터 | 구현됨 / 고도화 필요: 고객, 제품, 사용로그, 스마트 진단, 환경, 공식자료, Part Map, AR Step mock 구축 |
| DB | 구현됨 / 고도화 필요: SQLite `careshot_ar_mock.db` 생성 및 seed 가능 |
| AI 판단 | 구현됨 / 고도화 필요: rule 기반 판단엔진 1차 구현 |
| 위험도 | 구현됨 / 고도화 필요: Low / Medium / High 판단 및 High Risk 차단 |
| 공식자료 | 구현됨 / 고도화 필요: exact model / alias / series / common strict matching |
| ARGuidePlan | 구현됨 / 고도화 필요: 판단 결과를 AR Guide Template과 연결 |
| 백엔드 API | 구현됨 / 고도화 필요: 챗봇, 분석, AR plan, AR session API 초안 구현 |
| 프론트 | 구현됨 / 고도화 필요: 자체 챗봇 + 실제 reference image 기반 AR overlay 1차 구현 |
| 이미지 | 구현됨 / 고도화 필요: AS-Q24ENXE open-cover reference image 1차 연결. 최종 시연용 에어컨 3구조 reference image 확장 필요 |
| 좌표 | 구현됨 / 고도화 필요: open-cover reference image 기준 Part Map 좌표 1차 보정. 구조 타입별 part map version 확장 필요 |

## 3. 백엔드 개발 방향

백엔드는 ThinQ mock Adapter, AI 판단 엔진, AR Guide Plan 생성기, AR Session 저장소를 연결하는 역할을 한다.

### 3.1 현재 API

| Method | Path | 역할 |
|---|---|---|
| `GET` | `/api/health` | 서버 상태 확인 |
| `GET` | `/api/demo/context` | 기본 mock 사용자/제품/로그 조회 |
| `POST` | `/chat/messages` | 챗봇 메시지 입력 후 판단 + ARGuidePlan + overlay data 반환 |
| `POST` | `/ai/analyze` | AI 판단 결과만 반환 |
| `POST` | `/ar/guides/plan` | 분석 결과 또는 입력 메시지 기반 ARGuidePlan 생성 |
| `POST` | `/ar/sessions` | AR 세션 시작 로그 생성 |
| `GET` | `/ar/sessions/{session_id}` | AR 세션 조회 |
| `PATCH` | `/ar/sessions/{session_id}` | 완료 단계, 해결 여부, A/S 클릭 여부 저장 |

### 3.2 다음 백엔드 작업

1. API 응답 스키마 정리
   - `ChatMessageRequest`
   - `DecisionResult`
   - `ARGuidePlan`
   - `AROverlayData`
   - `ARSession`

2. ThinQ Adapter 분리
   - 현재는 mock DB에서 직접 조회
   - 이후 `ThinQMockAdapter` 클래스로 분리
   - 최종 구조에서는 ThinQ Connect MCP / ThinQ Open API로 대체 가능한 형태 유지

3. 공식자료 매칭 로직 강화
   - 모델명 exact
   - alias
   - series
   - product_type_common
   - 매칭 실패 시 AR Guide 차단

4. Model/Structure Resolver 분리
   - ThinQ 등록 제품의 `model_name` exact 조회
   - `product_type` 확인
   - `structure_type` 확인
   - reference image와 part map version 선택
   - exact 모델 resource가 없으면 approved structure-level generic resource 사용
   - structure_type도 없으면 AR Guide 차단 후 공식 매뉴얼/콘텐츠 제공

5. AR Session 저장 고도화
   - step별 완료 시각
   - 사용자가 중단한 단계
   - 해결 여부
   - A/S 연결 클릭 여부

## 4. 프론트엔드 개발 방향

프론트는 최종 ThinQ 앱 내부 화면을 가정하지만, 개발 환경에서는 자체 챗봇 + AR Guide 화면으로 구현한다.

### 4.1 현재 화면

현재 첫 화면은 다음 구조다.

```text
왼쪽: 챗봇 패널
오른쪽: AR Guide Session 패널
```

챗봇에서 문의를 입력하면 `/chat/messages` API를 호출하고, 응답으로 받은 `ar_overlay_data`를 기준으로 실제 reference image 위에 하이라이트를 표시한다.

### 4.2 다음 프론트 작업

1. 화면 상태 분리
   - `idle`
   - `analyzing`
   - `ar_ready`
   - `ar_running`
   - `completed`
   - `high_risk_service_route`

2. AR Guide UI polish
   - 상단에 프로세스 바가 존재하고, 원하는 단계를 터치하면 그 단계로 넘어갈 수 있는 구조이다.
   - 완료 화면
   - expert A/S 연결 CTA
   - 공식 콘텐츠 보기 버튼

3. 좌표 보정 UI 추가
   - Part Map 박스를 드래그/리사이즈
   - 변경된 좌표를 JSON으로 export
   - 발표 준비 시 overlay 위치 빠르게 수정 가능하게 함

4. 모바일 시연 최적화
   - 390px 모바일 화면 기준
   - 챗봇 → AR 화면 전환형 UI
   - 발표 시 시연 흐름을 짧게 유지

## 5. AI 판단 로직 개발 방향

AI 판단 로직은 영상 생성이 아니라 AR Guide 제공 가능 여부를 결정한다.

### 5.1 판단 기준

| 단계 | 판단 내용 |
|---|---|
| 문의 분류 | self_care / self_as / expert_as |
| 맥락 분석 | 제품, 모델명, 지역, 환경, 사용 로그, 스마트 진단 |
| 위험도 판단 | Low / Medium / High |
| 공식자료 매칭 | exact / alias / series / common |
| 제공 방식 결정 | 공식 콘텐츠+AR Guide 동시 제공 / expert A/S 연결 |

### 5.2 다음 AI 작업

1. 키워드 기반 규칙을 intent rule table로 분리
2. Smart Diagnosis severity와 자연어 위험 키워드 결합
3. 제품군별 procedure resolver 정리
4. AR Guide Template selector와 DB의 `ar_guide_steps`를 더 직접 연결
5. High Risk 차단 사유를 고객 표시 문구와 내부 로그 문구로 분리

## 6. 데이터베이스 개발 방향

현재 SQLite DB는 로컬 개발 환경용이다. 최종 발표에서는 DB 구조 설계와 mock 데이터 기반 작동을 설명한다.

### 6.1 현재 주요 테이블

| 테이블 | 역할 |
|---|---|
| `users` | 고객 프로필, 언어, 선호 형태 |
| `devices` | ThinQ 등록 제품 mock |
| `usage_logs` | 제품 사용 로그 |
| `smart_diagnosis_results` | 스마트 진단 결과 |
| `environment_contexts` | 인도 지역 환경 데이터 |
| `official_assets` | 공식 매뉴얼/FAQ/제품 이미지 |
| `care_videos` | 공식 관리 콘텐츠 재사용 DB |
| `product_models` | 제품 모델과 reference image |
| `part_maps` | 구조 타입별 AR 부품 좌표 |
| `ar_guide_steps` | AR 안내 단계 |
| `ar_session_logs` | 사용자 AR 세션 이력 |

### 6.2 다음 DB 작업

1. `official_contents` 테이블 분리 검토
   - 현재는 `care_videos` 이름이 남아 있음
   - AR 방향에서는 영상뿐 아니라 매뉴얼, FAQ, 공식 안내 콘텐츠까지 포괄해야 함

2. Part Map 버전 관리
   - `structure_type`
   - `reference_image_id`
   - `part_map_version`
   - `calibrated_by`
   - `calibrated_at`

3. AR session 상세 로그
   - step별 완료 시간
   - 고객이 멈춘 단계
   - 해결 여부
   - A/S 연결 여부

## 7. AR Guide 개발 방향

현재 AR은 실제 카메라 인식이 아니라 reference image 기반 overlay다. 발표 시연에서는 이 방식이 가장 안정적이다.

### 7.1 현재 AR 방식

```text
실제 제품 reference image
→ Part Map 정규화 좌표
→ 현재 step의 target_part 확인
→ overlay box / arrow / label 표시
```

### 7.2 다음 AR 작업

1. 에어컨 3개 구조 타입 reference image 준비
   - 벽걸이형
   - 스탠드형
   - 창문형

2. 구조 타입별 Part Map 좌표 보정 UI
   - `wall_mounted_ac`
   - `standing_ac`
   - `window_ac`

3. Model/Structure Resolver와 ARGuidePlan 연결
   - model_name exact
   - product_type
   - structure_type
   - reference_image
   - part_map_version

4. Part Map 좌표 보정 UI
5. 단계별 overlay type 개선
   - pulse highlight
   - glow outline
   - direction arrow
   - forbidden dim
6. 완료 화면
7. self A/S 진행 후 “해결됨 / expert A/S 연결” 선택
8. 실제 카메라 화면처럼 보이도록 UI polish

## 8. 발표용 시연 시나리오

### 8.1 정상 관리 문의

```text
사용자: Please help me clean the AC filter.
→ Low Risk
→ 공식자료 exact model match
→ model_name exact로 product_type/structure_type 확인
→ 구조 타입에 맞는 aircon_filter_cleaning template 선택
→ AR Guide Session 활성화
→ 전원 영역 → 전면 커버 → 필터 → 송풍구 → 재조립 안내
```

### 8.2 에어컨 3구조 시연

```text
벽걸이형 에어컨
→ wall_mounted_ac reference image
→ 전면 커버/필터/송풍구 overlay

스탠드형 에어컨
→ standing_ac reference image
→ 전면 패널/필터/흡입구/토출구 overlay

창문형 에어컨
→ window_ac reference image
→ 전면 그릴/필터 슬롯/송풍구 overlay
```

### 8.3 High Risk 문의

```text
사용자: There is smoke and a burning smell from the AC.
→ High Risk
→ AR Guide 차단
→ expert A/S 연결 카드 표시
```

## 9. 다음 작업 우선순위

현재까지 만든 기능은 최종 기준 `완료`가 아니라 `구현됨 / 고도화 필요` 상태다.

최종 산출물 기준 다음 우선순위:

1. `ChatbotEngine` 구현
2. `ConversationState` / `chat_sessions` DB 추가
3. `LLMServiceMock` 구현
4. `official_document_chunks` DB 추가
5. `RAGService` 구현
6. AI 판단엔진 v2 구현
7. `/chat/messages`를 multi-turn 구조로 변경
8. 프론트 챗봇 UI를 추가 질문/근거 카드 구조로 변경
9. 안전검증 로그와 High Risk 차단 근거 저장
10. 발표용 demo script 작성

## 10. 현재 실행 방법

```powershell
python "C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\04_AR가이드\backend\server.py"
```

브라우저:

```text
http://127.0.0.1:8787/
```

현재 `/chat/messages` API 하나로 챗봇 → 판단엔진 → ARGuidePlan → AR overlay data까지 실행된다.

