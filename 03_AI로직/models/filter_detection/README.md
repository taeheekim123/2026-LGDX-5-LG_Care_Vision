# Filter Detection Model

This folder is the FastAPI runtime location for the trained filter detector.

Expected model file:

```text
best.pt
```

Runtime path:

```text
03_AI로직/models/filter_detection/best.pt
```

The backend loads this path by default. If `best.pt` is missing, `/api/v1/ar/filter-detect` returns a mock fallback bbox when `mock_fallback=true`.

Do not place a model here until Roboflow bbox review is complete and the YOLOv8 export passes verification.
