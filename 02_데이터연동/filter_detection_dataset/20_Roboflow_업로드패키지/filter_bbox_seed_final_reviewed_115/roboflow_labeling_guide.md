# Roboflow Filter BBox Labeling Guide

작성일: 2026-06-15

## 1. Project 설정

| 항목 | 값 |
|---|---|
| Project Type | Object Detection |
| Project Name | `careshot-lg-ac-filter-detection` |
| Annotation Class | `filter` |
| Upload Package | `filter_bbox_seed_final_reviewed_115_images.zip` |
| Primary Goal | 에어컨 화면 안에서 필터 위치 bbox 탐지 |
| Export Target | YOLOv8 |

## 2. 업로드 대상

```text
images: 115
zip: filter_bbox_seed_final_reviewed_115_images.zip
manifest: roboflow_upload_manifest.csv
checklist: roboflow_labeling_checklist.csv
```

Roboflow에는 `images/` 폴더 전체 또는 zip 파일을 업로드한다. manifest와 checklist는 Roboflow 업로드용 이미지가 아니라 출처/검수 기록용이다.

## 3. Label 기준

| 항목 | 기준 |
|---|---|
| class name | `filter` |
| bbox 대상 | 실제 탈착/청소 대상인 망 형태 필터 또는 필터 케이스의 필터 영역 |
| 포함 | 필터 프레임과 망이 하나의 부품처럼 보이면 전체 포함 |
| 제외 | 송풍구 루버, 전면 커버, 손, 드라이버, 리모컨, 글자 안내, 빨간 화살표 |
| 가림 | 손이나 커버에 일부 가려져도 필터 위치가 명확하면 보이는 필터 영역만 라벨링 |
| 복수 필터 | 한 이미지에 여러 필터가 분리되어 보이면 각각 bbox |
| 애매한 컷 | checklist `qa_status=review_needed`로 표시하고 1차 학습에서 제외 |

## 4. 이미지 유형별 기준

### LG 공식 도식 이미지

- 빨간 원/화살표는 bbox에 포함하지 않는다.
- 도식 안의 실제 필터 망 또는 필터 부품만 감싼다.
- 확대 원 안에 같은 필터가 중복으로 보이면, 실제 조작 대상이 되는 본체 쪽 필터를 우선 라벨링한다.
- 확대 원이 더 명확하고 본체 쪽 필터가 너무 작으면 확대 원의 필터도 별도 `filter` bbox로 라벨링할 수 있다.

### 실사진 이미지

- 손은 제외하고 필터 프레임/망만 감싼다.
- 창문형 에어컨에서 필터가 반쯤 빠져 있으면 보이는 필터 전체를 감싼다.
- 필터가 제품 내부에 장착된 상태면 격자/망이 보이는 필터 영역만 감싼다.

### 필터 단독 이미지

- 배경은 제외하고 필터 외곽만 tight하게 감싼다.
- 여러 필터가 겹쳐 있으면 하나의 묶음이 아니라 보이는 필터별로 bbox를 나눈다.

## 5. Split 권장

Roboflow에서 split을 직접 지정할 수 있으면 아래 기준을 사용한다.

| split | 비율 | 수량 기준 |
|---|---:|---:|
| train | 80% | 약 92장 |
| valid | 10% | 약 11장 |
| test | 10% | 약 12장 |

도식 이미지와 실사진이 한 split에 몰리지 않도록 섞는다.

## 6. Export 기준

1. 모든 이미지에 `filter` bbox 라벨링 완료
2. Dataset > Generate Version
3. Preprocessing은 기본값 유지
4. Augmentation은 1차 학습에서는 과하게 넣지 않음
5. Export Format: YOLOv8
6. Export 결과를 `30_Roboflow_내보내기_YOLO/`에 저장

## 7. 완료 기준

```text
roboflow_labeling_checklist.csv 기준:
- bbox_labeled=Y: 115장 또는 review 제외 후 사용 장수
- qa_status=pass: 학습 투입 이미지 전체
- class_name=filter 외 class 없음

Roboflow export 기준:
- data.yaml 존재
- train/images, valid/images, test/images 존재
- labels txt 파일 존재
```

## 8. 주의

이 패키지는 라벨링 작업을 시작하기 위한 seed다. 일부 이미지는 LG 공식 공개 지원 콘텐츠 또는 iFixit 공개 가이드 기반 후보이므로, 최종 산출물/배포 전에는 `roboflow_upload_manifest.csv`의 `license_status`를 확인한다.
