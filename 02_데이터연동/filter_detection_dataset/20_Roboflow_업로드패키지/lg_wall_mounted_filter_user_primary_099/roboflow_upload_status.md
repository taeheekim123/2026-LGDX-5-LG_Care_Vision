# Roboflow Upload Status - lg_wall_mounted_filter_user_primary_099

- Primary user-provided images: 99
- Class: `filter`
- Project target: `s-workspace-fmrs3/carevision-ar`
- Recommended first training package: yes
- DB schema impact: none.

## 2026-06-15 current execution check

```text
Roboflow SDK: installed
ROBOFLOW_API_KEY: missing in current process
ROBOFLOW_WORKSPACE: missing in current process
ROBOFLOW_PROJECT: missing in current process
Actual upload: not executed
Reason: Roboflow credentials are not set in the active shell.
```

## Recommended upload modes

```text
Mode A - image-only upload:
python upload_to_roboflow.py

Mode B - pre-label upload for Roboflow review:
cd ..
python Roboflow_사전라벨_업로드.py --package-slug lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2
```

Mode B uploads 99 image/YOLO label pairs as predictions. Every bbox must still be reviewed in Roboflow before training.

## Dry-run verification

```text
python Roboflow_사전라벨_업로드.py --dry-run
-> package_slug=lg_wall_mounted_filter_user_primary_099_prelabel_yolov8_refined_v2
-> split=train
-> as_predictions=True
-> image_label_pairs=99
-> dry_run=true; no upload attempted
```

## Required env before real upload

```powershell
$env:ROBOFLOW_API_KEY="<new-valid-key>"
$env:ROBOFLOW_WORKSPACE="s-workspace-fmrs3"
$env:ROBOFLOW_PROJECT="carevision-ar"
```
