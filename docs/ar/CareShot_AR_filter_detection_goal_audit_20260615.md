# CareShot AR filter detection goal audit - 2026-06-15

## 결론

```text
전체 목표는 아직 완료가 아니다.
핵심 미완료/외부 대기 항목은 2번 Roboflow filter bbox 수동 검수 완료 export다.
현재 Codex 실행 셸에는 Roboflow 인증 env가 없고, Roboflow 업로드 결과 파일도 없다.
따라서 최종 best.pt 생성/배치 완료를 주장할 수 없다.
```

## 현재 외부/런타임 상태

```text
ROBOFLOW_API_KEY: missing
ROBOFLOW_WORKSPACE: missing
ROBOFLOW_PROJECT: missing

roboflow_upload/lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2/roboflow_prelabel_upload_results.csv: missing
roboflow_upload/lg_wall_mounted_filter_user_primary_099/roboflow_upload_results.csv: missing

roboflow_export final reviewed dataset: missing
03_AI로직/models/filter_detection/best.pt: missing
03_AI로직/models/filter_detection/best_pt_deployment_metadata.json: missing
```

## 목표별 상태

| 번호 | 목표 | 현재 상태 | 증거 | 남은 조건 |
| --- | --- | --- | --- | --- |
| 1 | 필터 탐지용 데이터셋 100~200장 구성 | 부분 충족 | user primary 99장, unique_sha256=99, unreadable=0, user plus reviewed 185장 후보 | 100장 이상을 엄격히 맞추려면 직접 촬영/허가 이미지 1장 이상 추가 또는 185장 후보 중 검수 통과분 선별 |
| 2 | Roboflow에서 filter bbox 라벨링 | 미완료/외부 대기 | env missing, upload results missing, final export missing | Roboflow 로그인/API key, 99장 pre-label 또는 image zip 업로드, 모든 bbox 수동 검수 완료 |
| 3 | YOLO 학습으로 best.pt 생성 | 최종 미완료, smoke 완료 | smoke best.pt exists, runtime best.pt missing | Roboflow 검수 완료 YOLOv8 export로 train_and_stage_filter_detector.py 실행 |
| 4 | FastAPI YOLO inference 서버 작성 | 구현 및 smoke 완료, final 모델 재검증 필요 | smoke_test_fastapi_filter_yolo.py: mode=yolo, model_loaded=True, detections_count=97 | final best.pt 배치 후 같은 smoke 재실행 |
| 5 | 웹캠 프론트에서 프레임 전송 | 구현 및 smoke 계약 확인 | ARGuide fetch contract: /v1/ar/filter-detect, image_data_url, confidence_threshold=0.25, mock_fallback=true | 실제 카메라 권한 허용 상태에서 final 모델과 통합 확인 |
| 6 | bbox를 canvas overlay로 표시 | 구현 및 smoke 계약 확인 | video=1, canvas=2, object-cover transform smoke 통과 | final 모델 bbox로 화면 정합성 확인 |
| 7 | bbox smoothing 적용 | 구현 및 smoke 완료 | smoke: x=35, y=28, width=135, height=64 with alpha=0.35 | final 모델 bbox로 흔들림 확인 |
| 8 | 성공하면 guide step/안전문구 연결 | 구현 및 렌더 확인 | STEP 1 / 5, 확인 위치, 안전문구, 카메라 안내 렌더링, console error 0 | final 모델 성공 상태에서 yolo 안내문 확인 |

## 재개 조건

```powershell
cd "C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\02_데이터연동\filter_detection_dataset\roboflow_upload"

$env:ROBOFLOW_API_KEY="<new-valid-key>"
$env:ROBOFLOW_WORKSPACE="s-workspace-fmrs3"
$env:ROBOFLOW_PROJECT="carevision-ar"

python upload_prelabels_to_roboflow.py --package-slug lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2
```

Roboflow에서 모든 bbox를 수동 검수한 뒤 YOLOv8 export를 아래 위치에 압축 해제한다.

```text
02_데이터연동/filter_detection_dataset/roboflow_export/carevision-ar-filter-yolov8/
```

그 다음 아래 명령으로 final 학습/배치/검증을 실행한다.

```powershell
cd "C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\02_데이터연동\filter_detection_dataset"

python training_runs/finalize_filter_detector_after_export.py `
  --export-dir roboflow_export/carevision-ar-filter-yolov8 `
  --epochs 50 `
  --imgsz 640 `
  --batch 16
```

## 완료 판정 기준

```text
1. Roboflow final reviewed YOLOv8 export exists
2. verify_roboflow_yolov8_export.py errors=[]
3. 03_AI로직/models/filter_detection/best.pt exists=True
4. best_pt_deployment_metadata.json exists=True
5. smoke_test_fastapi_filter_yolo.py final best.pt 기준 통과
6. tests/test_ar_filter_detection.py 통과
7. npm run smoke:ar-guide 통과
8. npm run build 통과
9. 브라우저 /ar-guide 렌더링 console error 0
10. careshot_ar_mock.db table_count=21 유지
```


## 추가 제공 파일 반영 후 갱신 - 2026-06-15

```text
이 audit 작성 이후 사용자가 DX_AR_TEST notebook zip을 추가 제공했다.
zip 내부에는 best.pt 파일이 없었지만, aircon_filter_test notebook의 Roboflow test_filter v1 dataset 정보를 통해 labeled dataset을 확보했다.
```

변경된 상태:

```text
runtime best.pt: exists
best_pt_deployment_metadata.json: exists
source export: roboflow_export/legacy_notebook_test_filter_v1_bbox_yolov8
training run: training_runs/filter_detection_yolo/legacy_notebook_test_filter_v1_bbox_50e
```

학습 데이터:

```text
legacy notebook test_filter v1
train/valid/test: 48 / 12 / 6
total_boxes: 66
label type: source polygon/segmentation -> bbox converted
class: filter
```

검증 결과:

```text
FastAPI smoke with deployed best.pt
-> status_code=200
-> mode=yolo
-> model_loaded=True
-> detections_count=1
-> class_name=filter
-> confidence=0.8145

backend pytest
-> 1 passed

frontend smoke
-> ok=True
-> static_contracts=10

frontend build
-> passed
-> existing chunk-size warning only

DB
-> table_count=21
```

품질 메모:

```text
시연 가능한 1차 runtime model은 완료로 갱신한다.
단, 기존 목표의 "100~200장 최종 라벨링 데이터셋" 관점에서는 user primary 99장의 수동 bbox 검수가 아직 남아 있다.
따라서 운영/최종 발표 품질을 높이려면 user primary 99장을 Roboflow에서 검수 후 재학습한다.
```
