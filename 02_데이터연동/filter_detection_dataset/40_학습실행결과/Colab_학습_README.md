# YOLO Filter Training Runbook

작성일: 2026-06-15

## 현재 상태

```text
Dataset seed: user-provided LG wall-mounted primary 99 images
Roboflow upload package: ready
Pre-label package: ready, manual review required
Roboflow bbox labeling: not completed
YOLOv8 export: not available yet
Training: blocked until labeled export exists
```

기존 `DX_AR_TEST` zip의 `aircon_filter_test.ipynb`는 `epochs=50`, `imgsz=640` 기준의 filter 1클래스 학습 기록이다.
다만 실제 `best.pt` 가중치는 zip에 포함되지 않았으므로, 현재 프로젝트에서는 아래 99장 primary 데이터셋을 Roboflow에서 검수한 뒤 새로 export/train한다.

주의:

```text
30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_review_only/ 는 pre-label 형식 검증용이다.
Roboflow_YOLOv8_내보내기_검증.py errors=[]는 통과했지만, Roboflow 수동 검수 완료 데이터가 아니므로 최종 best.pt 학습 입력으로 사용하지 않는다.
30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_refined_v2_review_only/ 도 동일하게 형식 검증용이며, refined v2가 우선 업로드 후보일 뿐 최종 학습 데이터는 아니다.
```

## 1. Roboflow export 배치

Roboflow에서 YOLOv8 format으로 export한 zip을 다운로드한 뒤 아래 위치에 압축 해제한다.

```text
filter_detection_dataset/
  30_Roboflow_내보내기_YOLO/
    carevision-ar-filter-yolov8/
      data.yaml
      train/
        images/
        labels/
      valid/
        images/
        labels/
      test/
        images/
        labels/
```

## 2. Export 검증

로컬 또는 Colab에서 다음을 실행한다.

```powershell
cd "C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX\07_개발단계\06_AR 가전케어 AI\02_데이터연동\filter_detection_dataset"

python 30_Roboflow_내보내기_YOLO\Roboflow_YOLOv8_내보내기_검증.py `
  30_Roboflow_내보내기_YOLO\carevision-ar-filter-yolov8 `
  --summary-json 30_Roboflow_내보내기_YOLO\carevision-ar-filter-yolov8_summary.json
```

통과 조건:

```text
errors=[]
names=["filter"]
total_images > 0
total_boxes > 0
train/valid/test images and labels present
all class ids = 0
all bbox coordinates normalized 0..1
```

## 3. Colab 학습

Colab T4 런타임에서 아래를 실행한다.

```python
!pip install ultralytics

!python 40_학습실행결과/YOLO_필터_Colab_학습.py \
  --data 30_Roboflow_내보내기_YOLO/carevision-ar-filter-yolov8/data.yaml \
  --model yolov8n.pt \
  --epochs 50 \
  --imgsz 640 \
  --batch 16 \
  --project 40_학습실행결과/filter_detection_yolo \
  --name yolov8n_filter_wall_primary_099
```

예상 산출물:

```text
40_학습실행결과/filter_detection_yolo/yolov8n_filter_wall_primary_099/weights/best.pt
```

## 4. 학습 + 배치 자동화

Roboflow 검수 완료 export를 받은 뒤에는 아래 통합 스크립트를 우선 사용한다.

```powershell
python 40_학습실행결과/필터검출기_학습및배포스테이징.py `
  --export-dir 30_Roboflow_내보내기_YOLO/carevision-ar-filter-yolov8 `
  --epochs 50 `
  --imgsz 640 `
  --batch 16
```

이 스크립트는 다음 순서로 동작한다.

```text
1. Roboflow_YOLOv8_내보내기_검증.py 기준 export 검증
2. review_only export이면 기본 차단
3. YOLO 학습 실행
4. 40_학습실행결과/filter_detection_yolo/.../weights/best.pt 확인
5. 기존 배치 모델이 있으면 백업
6. FastAPI 기본 경로로 best.pt 복사
7. best_pt_deployment_metadata.json 기록
```

학습 완료 후 최종 `best.pt` 위치:

```text
03_AI로직/models/filter_detection/best.pt
```

FastAPI는 위 경로에 `best.pt`가 있으면 mock fallback 대신 실제 YOLO 모델을 로드한다.

### 4.1 Non-final smoke 학습

Roboflow 수동 검수 전 pre-label export는 최종 학습에 사용하지 않는다.
다만 학습 파이프라인 검증 목적이면 아래처럼 `--allow-review-only-training --no-deploy`를 함께 사용한다.

```powershell
python 40_학습실행결과/필터검출기_학습및배포스테이징.py `
  --export-dir 30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_refined_v2_review_only `
  --epochs 1 `
  --imgsz 320 `
  --batch 4 `
  --name smoke_review_only_no_deploy_test `
  --allow-review-only-training `
  --no-deploy
```

검증 결과:

```text
ultralytics=8.4.67
torch=2.12.0+cpu
numpy=1.26.4
opencv=4.10.0
pip check -> No broken requirements found.

review-only export verify_errors=[]
train/valid/test = 88/7/4 images
total_images=99
total_boxes=99

smoke best.pt:
40_학습실행결과/filter_detection_yolo/smoke_review_only_no_deploy_test/weights/best.pt
size=6,218,033 bytes

runtime deployed best.pt:
03_AI로직/models/filter_detection/best.pt
exists=False
```

1차 실패 및 수정:

```text
실패:
- Ultralytics가 data.yaml의 `path: .`를 현재 작업 디렉터리 기준으로 해석해 valid/images를 찾지 못했다.

수정:
- 필터검출기_학습및배포스테이징.py가 학습 전 `_ultralytics_data.yaml`을 생성하도록 보정했다.
- 생성된 yaml은 export_dir 절대경로를 `path`로 사용한다.
```

### 4.2 FastAPI YOLO inference smoke

학습된 smoke 모델을 실제 앱 모델 경로에 배치하지 않고,
FastAPI `/api/v1/ar/filter-detect` 라우터가 YOLO 모델을 로드하고 bbox 응답을 반환할 수 있는지만 격리 검증한다.

```powershell
python 40_학습실행결과/FastAPI_필터_YOLO_스모크테스트.py
```

검증 결과:

```text
status_code=200
mode=yolo
model_loaded=True
detections_count=97
first_detection.class_name=filter
first_detection.confidence=0.015029818750917912

model_path:
40_학습실행결과/filter_detection_yolo/smoke_review_only_no_deploy_test/weights/best.pt

runtime deployed best.pt:
03_AI로직/models/filter_detection/best.pt
exists=False
```

주의:

```text
이 smoke는 검수 전 pre-label 기반 모델을 사용하므로 정확도 지표가 아니다.
목적은 FastAPI가 YOLO 모델을 실제로 로드하고 schema-compatible bbox를 반환하는지 확인하는 것이다.
```

## 5. 진행 금지 조건

아래 중 하나라도 해당하면 학습하지 않는다.

```text
Roboflow bbox labeling incomplete
data.yaml missing
class name is not exactly filter
labels missing
label files contain class id other than 0
bbox coordinate validation failed
```

## 6. Final export 이후 원클릭 검증/배치

Roboflow에서 수동 bbox 검수 완료 YOLOv8 export를 받은 뒤에는 아래 wrapper를 사용한다.

```powershell
python 40_학습실행결과/내보내기후_필터검출기_최종배포.py `
  --export-dir 30_Roboflow_내보내기_YOLO/carevision-ar-filter-yolov8 `
  --epochs 50 `
  --imgsz 640 `
  --batch 16
```

동작 순서:

```text
1. review_only export 기본 차단
2. 필터검출기_학습및배포스테이징.py 실행
3. best.pt를 03_AI로직/models/filter_detection/best.pt로 배치
4. FastAPI /api/v1/ar/filter-detect YOLO smoke 실행
5. backend tests/test_ar_filter_detection.py 실행
6. frontend npm run smoke:ar-guide 실행
7. frontend npm run build 실행
8. careshot_ar_mock.db table_count=21 확인
```

검증된 안전장치:

```text
review-only export로 실행:
-> blocked=True
-> reason=review-only export detected; complete Roboflow bbox review and export a final YOLOv8 dataset first

review-only smoke dry-run:
python 40_학습실행결과/내보내기후_필터검출기_최종배포.py `
  --export-dir 30_Roboflow_내보내기_YOLO/local_prelabel_yolov8_refined_v2_review_only `
  --dry-run `
  --allow-review-only-smoke `
  --epochs 1 `
  --imgsz 320 `
  --batch 4 `
  --name wrapper_review_only_dry_run
-> 필터검출기_학습및배포스테이징.py dry-run 통과
-> no_deploy=True
```
