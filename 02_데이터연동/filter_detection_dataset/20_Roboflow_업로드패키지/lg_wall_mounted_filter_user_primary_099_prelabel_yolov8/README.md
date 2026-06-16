# lg_wall_mounted_filter_user_primary_099_prelabel_yolov8

- Source package: `lg_wall_mounted_filter_user_primary_099`
- Images: 99
- Label class: `filter`
- This is a heuristic pre-label package, not final ground truth.
- Import into Roboflow only as an annotation starting point, then review every bbox before training.

## Roboflow import rule

Use this package only when Roboflow can import YOLOv8 annotations from the zip.

```text
Upload target:
- workspace: s-workspace-fmrs3
- project: carevision-ar
- project type: Object Detection
- class: filter

Recommended file:
- lg_wall_mounted_filter_user_primary_099_prelabel_yolov8.zip
```

API upload helper:

```powershell
cd "C:\Users\TAEHEE\Documents\2026 LGDX\프로젝트\lgdx_DX"

$env:ROBOFLOW_API_KEY="YOUR_PRIVATE_API_KEY"
$env:ROBOFLOW_WORKSPACE="s-workspace-fmrs3"
$env:ROBOFLOW_PROJECT="carevision-ar"

python "07_개발단계\06_AR 가전케어 AI\02_데이터연동\filter_detection_dataset\20_Roboflow_업로드패키지\lg_wall_mounted_filter_user_primary_099_prelabel_yolov8\Roboflow_사전라벨_업로드.py" --dry-run
python "07_개발단계\06_AR 가전케어 AI\02_데이터연동\filter_detection_dataset\20_Roboflow_업로드패키지\lg_wall_mounted_filter_user_primary_099_prelabel_yolov8\Roboflow_사전라벨_업로드.py"
```

The helper uses Roboflow Python SDK `single_upload` with the matching image and YOLO txt file.
By default it uploads the labels as predictions so Roboflow review is still required.

After import, every image must be opened in Roboflow and checked manually.

```text
Keep:
- bbox tightly covers the visible filter mesh or removable filter part.

Fix:
- bbox includes too much AC body/front panel.
- bbox is shifted from the actual filter.
- bbox covers a guide sticker, grille, shadow, hand, or background.

Delete/skip:
- filter is not visible.
- only the AC exterior or vague intake slot is visible.
```

Do not export/train until all 99 pre-labels are reviewed.
