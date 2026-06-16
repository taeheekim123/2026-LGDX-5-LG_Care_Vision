# Roboflow Upload Status

작성일: 2026-06-15

## 현재 상태

```text
Roboflow upload package: ready
Images: 115
Zip entries: 115
Local upload by API: not executed
Reason: ROBOFLOW_API_KEY / ROBOFLOW_WORKSPACE / ROBOFLOW_PROJECT not configured
Roboflow Python SDK: not installed
```

## 패키지 파일

```text
images/
filter_bbox_seed_final_reviewed_115_images.zip
roboflow_upload_manifest.csv
roboflow_labeling_checklist.csv
roboflow_labeling_guide.md
upload_to_roboflow.py
```

## Roboflow Web UI 진행

1. Roboflow dashboard에서 새 Project 생성
2. Project Type: Object Detection
3. Project Name: `careshot-lg-ac-filter-detection`
4. Class: `filter`
5. Upload Data에서 `filter_bbox_seed_final_reviewed_115_images.zip` 업로드
6. Annotate에서 모든 이미지에 `filter` bbox 라벨링
7. 라벨링 완료 후 Generate Version
8. Export Format: YOLOv8
9. Export 결과를 `30_Roboflow_내보내기_YOLO/` 아래에 저장

## API 업로드 준비

API 업로드를 쓰려면 아래 환경변수가 필요하다.

```powershell
$env:ROBOFLOW_API_KEY="..."
$env:ROBOFLOW_WORKSPACE="..."
$env:ROBOFLOW_PROJECT="careshot-lg-ac-filter-detection"
pip install roboflow
python upload_to_roboflow.py
```

API 키는 저장소나 문서에 기록하지 않는다.

## 업로드 실패 시 진단

Roboflow 프로젝트에 이미지가 보이지 않으면 먼저 같은 PowerShell 창에서 아래를 실행한다.

```powershell
$env:ROBOFLOW_LIST_PROJECTS_ONLY="1"
python upload_to_roboflow.py
Remove-Item Env:\ROBOFLOW_LIST_PROJECTS_ONLY
```

확인할 것:

```text
1. ROBOFLOW_WORKSPACE는 app.roboflow.com/<workspace-slug>/... 의 workspace slug여야 한다.
2. ROBOFLOW_PROJECT는 프로젝트 표시 이름이 아니라 project URL slug / project id여야 한다.
3. 프로젝트는 Roboflow에 먼저 Object Detection으로 생성되어 있어야 한다.
4. 업로드된 이미지는 Version 페이지가 아니라 Annotate/Unassigned 또는 Dataset 이미지 목록에 먼저 보일 수 있다.
5. 실행 후 roboflow_upload_results.csv에서 uploaded/failed 상태를 확인한다.
```

## 2026-06-15 API 인증 실패 기록

```text
Workspace slug: s-workspace-fmrs3
Project slug: carevision-ar
Upload attempted: yes
Images transmitted: no
Failure stage: Roboflow SDK authentication
HTTP/status: 401
Message: API key does not exist or has been revoked
roboflow_upload_results.csv: not created
```

다음 재시도에는 Roboflow Dashboard의 Account > Roboflow Keys에서 새 API key를 발급받아 같은 명령을 실행한다.
API key는 문서나 저장소에 기록하지 않는다.

## 다음 진행 조건

YOLO 학습으로 넘어가려면 아래 증거가 필요하다.

```text
1. Roboflow에서 115장 업로드 완료
2. class가 filter 하나만 존재
3. 모든 사용 이미지 bbox 라벨링 완료
4. review_needed 또는 rejected 이미지는 train/valid/test에서 제외
5. YOLOv8 export zip 또는 data.yaml 확보
```
