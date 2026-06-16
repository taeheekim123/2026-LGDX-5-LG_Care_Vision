from __future__ import annotations

import csv
import hashlib
import sys
from pathlib import Path

import cv2
import yt_dlp
from PIL import Image, ImageDraw


DATASET_SLUG = "lg_wall_mounted_filter_video_frame_candidates"

VIDEOS = [
    {
        "video_id": "O0uiIC3tIpE",
        "url": "https://www.youtube.com/watch?v=O0uiIC3tIpE",
        "title": "LG WHISEN wall-mounted air-conditioner filter cleaning method",
    },
    {
        "video_id": "tWeUd8F8ado",
        "url": "https://www.youtube.com/shorts/tWeUd8F8ado",
        "title": "LG wall-mounted air-conditioner filter cleaning and replacement method",
    },
    {
        "video_id": "6xXHrk14884",
        "url": "https://www.youtube.com/watch?v=6xXHrk14884",
        "title": "LG Whisen wall-mounted air-conditioner disassembly and cleaning",
    },
    {
        "video_id": "CUmOa18MvX0",
        "url": "https://www.youtube.com/watch?v=CUmOa18MvX0",
        "title": "LG Whisen dual inverter wall-mounted air-conditioner disassembly",
    },
    {
        "video_id": "t1x8lhYUtJ8",
        "url": "https://www.youtube.com/watch?v=t1x8lhYUtJ8",
        "title": "LG dual inverter AC filter cleaning",
    },
    {
        "video_id": "gp8CqK-uP5M",
        "url": "https://www.youtube.com/watch?v=gp8CqK-uP5M",
        "title": "LG air conditioner air filter cleaning",
    },
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def save_contact_sheet(files: list[Path], out_path: Path) -> None:
    thumb_w, thumb_h, label_h, cols = 180, 135, 34, 5
    rows = max(1, (len(files) + cols - 1) // cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(files):
        row, col = divmod(i, cols)
        x, y = col * thumb_w, row * (thumb_h + label_h)
        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((thumb_w, thumb_h))
            sheet.paste(img, (x + (thumb_w - img.width) // 2, y + (thumb_h - img.height) // 2))
        except Exception as exc:
            draw.text((x + 4, y + 4), f"ERR {exc}"[:40], fill=(255, 0, 0))
        draw.rectangle((x, y + thumb_h, x + thumb_w, y + thumb_h + label_h), outline=(180, 180, 180), fill=(245, 245, 245))
        draw.text((x + 4, y + thumb_h + 4), f"{i + 1:03d} {path.name[:28]}", fill=(0, 0, 0))
    sheet.save(out_path, quality=90)


def get_stream_url(page_url: str) -> str | None:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "format": "best[height<=720][ext=mp4]/best[height<=720]/best",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(page_url, download=False)
    return info.get("url") if info else None


def extract_frames(video: dict[str, str], out_dir: Path, start_index: int) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    try:
        stream_url = get_stream_url(video["url"])
    except Exception as exc:
        print(f"stream failed {video['video_id']}: {exc}")
        return rows, start_index
    if not stream_url:
        print(f"stream missing {video['video_id']}")
        return rows, start_index

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        print(f"open failed {video['video_id']}")
        return rows, start_index

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    duration = frame_count / fps if frame_count else 0
    if duration <= 0:
        duration = 180
    sample_seconds = []
    sec = 5.0
    while sec < min(duration, 360):
        sample_seconds.append(sec)
        sec += 4.0

    last_hashes: set[str] = set()
    idx = start_index
    kept_for_video = 0
    for sec in sample_seconds:
        cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
        ok, frame = cap.read()
        if not ok or frame is None:
            continue
        h, w = frame.shape[:2]
        if w < 240 or h < 180:
            continue
        # Basic crop is intentionally not applied; Roboflow labeling should see the full AR camera context.
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dest = out_dir / f"video_frame_candidate_{idx:03d}_{video['video_id']}_{int(sec):04d}s.jpg"
        Image.fromarray(rgb).save(dest, quality=88)
        digest = sha256_file(dest)
        if digest in last_hashes:
            dest.unlink(missing_ok=True)
            continue
        last_hashes.add(digest)
        rows.append(
            {
                "candidate_relative_path": "",
                "candidate_index": str(idx),
                "source_page": video["url"],
                "url": video["url"],
                "alt": video["title"],
                "sha256": digest,
                "bytes": str(dest.stat().st_size),
                "source_type": "youtube_video_frame_wall_mounted_lg_candidate",
                "license_status": "unknown_verify_before_training",
                "appliance_form": "wall_mounted_candidate",
                "target_class": "filter",
                "label_status": "needs_human_filter_bbox_labeling",
                "visual_review_status": "candidate_review_needed",
                "notes": f"Extracted frame at {sec:.1f}s; keep only if actual wall-mounted LG indoor unit and filter/filter slot is visible.",
                "path_obj": dest,
            }
        )
        idx += 1
        kept_for_video += 1
        if kept_for_video >= 30:
            break
    cap.release()
    return rows, idx


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python extract_wall_mounted_video_frame_candidates.py <dataset_root>")
        return 2

    dataset_root = Path(sys.argv[1]).resolve()
    out_dir = dataset_root / "10_원천이미지_raw" / "20_학습후보" / DATASET_SLUG
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, str]] = []
    idx = 1
    for video in VIDEOS:
        video_rows, idx = extract_frames(video, out_dir, idx)
        rows.extend(video_rows)

    fieldnames = [
        "candidate_relative_path",
        "candidate_index",
        "source_page",
        "url",
        "alt",
        "sha256",
        "bytes",
        "source_type",
        "license_status",
        "appliance_form",
        "target_class",
        "label_status",
        "visual_review_status",
        "notes",
    ]
    for row in rows:
        path = row.pop("path_obj")
        row["candidate_relative_path"] = str(path.relative_to(dataset_root)).replace("\\", "/")

    manifest_path = dataset_root / f"{DATASET_SLUG}_manifest.csv"
    with manifest_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    files = sorted(out_dir.iterdir())
    save_contact_sheet(files, dataset_root / f"{DATASET_SLUG}_contact_sheet.jpg")
    print(f"candidate_count={len(files)}")
    print(f"manifest={manifest_path}")
    print(f"candidate_dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
