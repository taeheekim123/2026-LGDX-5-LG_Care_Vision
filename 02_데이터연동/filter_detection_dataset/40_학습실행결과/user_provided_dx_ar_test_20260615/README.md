# User Provided DX_AR_TEST Import

작성일: 2026-06-15

## 정리

`DX_AR_TEST-20260615T073404Z-3-001.zip` 안의 3개 파일은 실제 `best.pt` 가중치가 아니라 Jupyter Notebook 파일이다.
원본 파일에는 확장자가 없어서 `notebooks_with_extension/` 아래에 `.ipynb` 사본을 생성했다.

| 원본 파일 | 변환 파일 | 판단 |
|---|---|---|
| `aircon_filter_test` | `notebooks_with_extension/aircon_filter_test.ipynb` | 필터 1클래스 학습 기록. 이번 작업의 참고 노트북 |
| `aircon_test` | `notebooks_with_extension/aircon_test.ipynb` | 에어컨 전체 탐지 테스트 기록 |
| `aircon_top_bottom_test` | `notebooks_with_extension/aircon_top_bottom_test.ipynb` | 상/하단 2클래스 테스트 기록 |

## 현재 결론

- 실제 배포 가능한 `best.pt`는 zip에 포함되지 않았다.
- 따라서 백엔드 모델 경로에는 아직 배치하지 않는다.
- 이번 벽걸이 필터 POC에서는 `aircon_filter_test.ipynb`의 Roboflow/YOLO 학습 흐름만 참고한다.

## 다음 실행 기준

1. `20_Roboflow_업로드패키지/lg_wall_mounted_filter_user_primary_099/`를 Roboflow에 업로드한다.
2. class는 `filter` 1개로 유지한다.
3. 필터 mesh 또는 필터 부품이 명확한 영역만 bbox 라벨링한다.
4. Roboflow YOLOv8 export를 받은 뒤 `30_Roboflow_내보내기_YOLO/Roboflow_YOLOv8_내보내기_검증.py`로 검증한다.
5. 검증 통과 후 Colab에서 학습하고 `best.pt`를 내려받는다.
6. `best.pt` 확보 후에만 FastAPI YOLO model path에 배치한다.
