# YOLO 필터 탐지 데이터셋 구성 계획

작성일: 2026-06-15

## 1. 목적

MindAR 기반 reference tracking을 사용하지 않고, 웹캠 프레임에서 에어컨 내부 필터 위치를 직접 탐지하는 YOLO 기반 Web AR POC를 진행한다.

1차 데이터셋의 목적은 에어컨 전체 탐지가 아니라, **에어컨으로 판단된 이후 화면 안에서 내부 필터 영역을 `filter` bbox로 찾는 것**이다.

## 2. 1차 데이터셋 범위

| 항목 | 기준 |
|---|---|
| 목표 이미지 수 | 100~200장 |
| 1차 클래스 | `filter` 1개 |
| 주요 대상 | 벽걸이형 split AC 전면 커버가 열려 있고 내부 필터가 보이는 이미지 |
| 제외 대상 | 에어컨 전체 외관만 보이는 이미지, 실외기, 차량 필터, 공기청정기 필터 단독 이미지 |
| 보조/검증용 | 필터가 보이지 않는 에어컨 내부/외관 이미지는 negative sample로 별도 관리 |

## 3. 수집 수량 배분

| 구분 | 목표 수량 | 사용 목적 | 비고 |
|---|---:|---|---|
| 직접 촬영/사용 허가 이미지 | 60~100장 | 실제 POC 학습 핵심 | 각도, 조명, 거리 변화 포함 |
| 공개 라이선스/오픈 데이터 후보 | 30~60장 | 다양성 보강 | 라이선스 확인 후 사용 |
| 로컬 reference 이미지 | 4장 내외 | 라벨링 기준/시연 기준 확인 | 학습 주력으로 쓰기에는 수량 부족 |
| negative sample | 20~40장 | 오탐 방지 | 에어컨 외관, 송풍구, 커버만 보이는 장면 |

## 4. 라벨링 기준

| 항목 | 기준 |
|---|---|
| 라벨명 | `filter` |
| bbox 범위 | 실제 탈착/청소 대상인 망 형태 필터 영역만 감싼다. |
| 포함 | 필터 프레임과 망이 함께 하나의 부품처럼 보이면 전체를 포함한다. |
| 제외 | 송풍구 루버, 전면 커버, 에어컨 외곽, 손/도구는 포함하지 않는다. |
| 가림 | 손이나 커버에 일부 가려져도 필터의 위치가 명확하면 보이는 필터 영역 기준으로 라벨링한다. |
| 애매한 이미지 | `review_needed`로 분리하고 1차 학습에는 넣지 않는다. |

## 5. 폴더 구조

```text
filter_detection_dataset/
  README.md
  candidate_sources.md
  dataset_inventory.md
  dataset_manifest.csv
  manifest_template.csv
  10_원천이미지_raw/
    01_직접제공_승인후보/
      lg_official_support_crawled/
      lg_official_support_crawled_round2/
      lg_official_filter_training_seed_accepted/
    04_오픈라이선스후보/
    10_웹크롤링후보/
      lg_filter_round3_product_and_guides/
      ifixit_lg_goldstar_filter/
    20_학습후보/
      filter_bbox_seed_final_reviewed_115/
    00_로컬기준이미지/
    02_공식매뉴얼페이지후보/
    99_부정샘플/
  30_Roboflow_내보내기_YOLO/
  40_학습실행결과/
```

## 6. 진행 순서

1. 직접 촬영/허가 이미지와 공개 라이선스 후보를 `10_원천이미지_raw/` 하위 폴더에 모은다.
2. 이미지별 출처, 라이선스, 사용 가능 여부를 `manifest_template.csv` 형식으로 기록한다.
3. Roboflow Object Detection 프로젝트를 만들고 `filter` 클래스 하나로 bbox 라벨링한다.
4. 학습용/검증용/test split을 나눈다.
5. YOLOv8 형식으로 export한다.
6. Google Colab T4 GPU에서 학습해 `best.pt`를 생성한다.
7. `best.pt`를 FastAPI inference 서버에 연결한다.

## 7. 현재 판단

1번부터 진행하는 것이 맞다.

단, 공개 웹 이미지/블로그/유튜브 캡처를 무단으로 학습 데이터에 넣는 방식은 발표/산출물 리스크가 있다. 따라서 1차 성공률을 빠르게 보려면 직접 촬영 또는 사용 허가 이미지를 중심으로 구성하고, 공개 데이터는 라이선스 확인이 가능한 것만 보강한다.

2026-06-15 현재 최종 라벨링 후보는 `filter_bbox_seed_final_reviewed_115_manifest.csv` 기준 115장이다.

| 구분 | 수량 |
|---|---:|
| 로컬 reference seed | 4 |
| LG 공식 매뉴얼 렌더링 페이지 | 19 |
| LG 공식 지원 이미지 1차 원본 | 100 |
| LG 공식 지원 이미지 2차 신규 | 27 |
| LG 공식/웹 실사진 round3 partial | 94 |
| iFixit LG/Goldstar 실사진 후보 | 36 |
| 최종 Roboflow bbox 라벨링 seed | 115 |

최종 115장은 contact sheet 기준으로 필터/필터케이스/필터 분리 장면 위주로 선별했다.
다만 일부는 LG 공식 공개 지원 콘텐츠 또는 iFixit 공개 가이드 기반 후보이므로,
학습/배포 사용권은 manifest의 `license_status`를 기준으로 별도 확인해야 한다.
실제 웹캠 품질을 높이려면 직접 촬영/명시 허가 실사진 30장 이상과 negative sample을 추가하는 것이 좋다.

## 8. 벽걸이 시연 기준 재정의

2026-06-15 사용자 피드백에 따라 최종 시연 대상을 벽걸이형 LG 에어컨으로 고정했다.

따라서 기존 `filter_bbox_seed_final_reviewed_115`는 창문형/도식/공식 안내 이미지가 섞인 broad reference 후보로 내리고, Roboflow 1차 업로드 대상은 아래 벽걸이 전용 패키지를 우선한다.

| 항목 | 값 |
|---|---:|
| 벽걸이 전용 raw 후보 | 208장 |
| 벽걸이 영상 프레임 후보 | 105장 |
| 벽걸이 reviewed Roboflow 후보 | 86장 |

주요 위치:

```text
10_원천이미지_raw/20_학습후보/lg_wall_mounted_filter_real_photo_reviewed_086/
lg_wall_mounted_filter_real_photo_reviewed_086_manifest.csv
lg_wall_mounted_filter_real_photo_reviewed_086_contact_sheet.jpg
20_Roboflow_업로드패키지/lg_wall_mounted_filter_real_photo_reviewed_086/
```

주의:

```text
86장은 벽걸이 시연 맥락 후보이며, 일부는 필터 그물망 자체보다 필터 접근부/슬롯이 보이는 화면이다.
Roboflow 라벨링 시 filter mesh가 명확한 경우만 bbox를 그리고, 애매한 프레임은 skip 또는 negative 후보로 분리한다.
블로그/영상 프레임은 license_status=unknown_verify_before_training 이므로 최종 발표/배포 전 직접 촬영 또는 사용 허가 이미지로 대체하는 것이 안전하다.
```

## 9. 사용자 제공 이미지/1차 학습 노트북 반영

2026-06-15 사용자가 추가 제공한 벽걸이 필터 이미지 zip 2개와 `DX_AR_TEST` zip을 반영했다.

| 구분 | 수량/상태 | 위치 |
|---|---:|---|
| 사용자 제공 원본 이미지 | 100장 | `10_원천이미지_raw/01_직접제공_승인후보/user_provided_wall_filter_20260615/` |
| 중복 제거 후 normalized 이미지 | 99장 | `10_원천이미지_raw/01_직접제공_승인후보/user_provided_wall_filter_20260615_normalized/` |
| 1차 학습 권장 primary 패키지 | 99장 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099/` |
| 기존 벽걸이 reviewed 86장 포함 extended 패키지 | 185장 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_plus_reviewed_185/` |
| 사용자 제공 학습 노트북 | 3개 | `40_학습실행결과/user_provided_dx_ar_test_20260615/notebooks_with_extension/` |

판단:

```text
사용자 제공 99장은 기존 웹/영상 후보보다 훨씬 일관적이고 필터 mesh가 잘 보인다.
따라서 Roboflow 1차 재라벨링/재학습은 lg_wall_mounted_filter_user_primary_099를 우선 사용한다.
lg_wall_mounted_filter_user_plus_reviewed_185는 recall 보강용 2차 학습 후보로 둔다.
DX_AR_TEST zip에는 실제 best.pt 가중치가 없고 Jupyter Notebook 기록만 있으므로, 모델 배치는 아직 진행하지 않는다.
```

## 10. 사용자 제공 99장 사전 라벨 패키지

2026-06-15 기준 Roboflow 검수 시간을 줄이기 위해 사용자 제공 primary 99장에 대해 YOLOv8 형식 사전 라벨 패키지를 생성했다.

| 구분 | 수량/상태 | 위치 |
|---|---:|---|
| 사전 라벨 이미지 | 99장 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/images/` |
| YOLO 라벨 txt | 99개 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/labels/` |
| Roboflow import zip | 생성 완료 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8.zip` |
| bbox 확인용 contact sheet | 생성 완료 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/prelabel_overlay_contact_sheet.jpg` |
| API upload helper | dry-run 검증 완료 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8/Roboflow_사전라벨_업로드.py` |
| 로컬 YOLOv8 검증 export | errors=[] 통과 | `30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_review_only/` |
| 다음 단계 runbook | 생성 완료 | `20_Roboflow_업로드패키지/Roboflow_다음단계_20260615.md` |

주의:

```text
사전 라벨은 이미지 처리 기반 heuristic bbox이며 정답 라벨이 아니다.
일부 bbox는 필터 mesh보다 넓게 AC 전면부까지 포함한다.
Roboflow에서 99장 전체 bbox를 직접 열어 수정/삭제/확정한 뒤에만 YOLOv8 export와 학습으로 넘어간다.
현재 유효한 ROBOFLOW_API_KEY가 없어 Roboflow 업로드/라벨링 완료 상태로 보지 않는다.
로컬 검증 export는 total_images=99, total_labels=99, total_boxes=99, errors=[]로 통과했지만,
이는 라벨 포맷 검증이지 bbox 정답성 검증이 아니다.
```

## 11. refined v2 사전 라벨 우선 패키지

2026-06-15 추가 검수에서 v1 bbox가 실제 필터 mesh보다 넓게 잡히는 문제가 확인되어, projection 기반으로 bbox를 줄인 refined v2 패키지를 생성했다.

| 구분 | 수량/상태 | 위치 |
|---|---:|---|
| refined v2 YOLO 이미지 | 99장 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2/images/` |
| refined v2 YOLO 라벨 | 99개 | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2/labels/` |
| refined v2 Roboflow zip | 201 entries | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2.zip` |
| refined v2 COCO fallback | 99 images / 99 annotations | `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099_prelabel_refined_v2_coco/` |
| refined v2 로컬 검증 export | errors=[] 통과 | `30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_refined_v2_review_only/` |
| 공용 업로드 helper | dry-run 검증 완료 | `20_Roboflow_업로드패키지/Roboflow_사전라벨_업로드.py` |

판단:

```text
v1 high_priority_review=92
refined_v2 high_priority_review=45
refined_v2는 97장 bbox를 더 타이트하게 줄였다.
하지만 일부 bbox는 여전히 너무 좁거나 다른 전면부를 잡을 수 있으므로 Roboflow 수동 검수 전 학습 금지 기준은 유지한다.
우선 업로드 후보는 refined v2 YOLO zip이며, YOLO txt import가 불안정하면 refined v2 COCO zip을 사용한다.
```
