from __future__ import annotations

import argparse
import csv
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


PATTERNS = ["keyboard", "phone", "laptop", "remote_control", "window_blinds"]


def jitter(value: int, amount: int) -> int:
    return value + random.randint(-amount, amount)


def random_color(base: tuple[int, int, int], spread: int = 24) -> tuple[int, int, int]:
    return tuple(max(0, min(255, jitter(channel, spread))) for channel in base)


def make_background(width: int, height: int) -> Image.Image:
    base = random.choice([(238, 238, 232), (220, 224, 226), (205, 200, 192), (245, 242, 235)])
    image = Image.new("RGB", (width, height), random_color(base, 8))
    draw = ImageDraw.Draw(image)
    for _ in range(random.randint(6, 18)):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=random_color(base, 18), width=random.randint(1, 4))
    return image


def draw_keyboard(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    x0 = random.randint(20, 70)
    y0 = random.randint(height // 3, height // 2)
    key_w = random.randint(28, 42)
    key_h = random.randint(22, 34)
    gap = random.randint(3, 8)
    rows = random.randint(4, 6)
    cols = random.randint(9, 14)
    outer_w = cols * (key_w + gap) + gap
    outer_h = rows * (key_h + gap) + gap
    draw.rounded_rectangle(
        (x0 - 12, y0 - 12, x0 + outer_w + 12, y0 + outer_h + 12),
        radius=10,
        fill=random_color((45, 45, 48), 18),
    )
    for r in range(rows):
        row_offset = random.randint(-4, 18)
        for c in range(cols - (1 if r > 2 else 0)):
            x = x0 + row_offset + c * (key_w + gap)
            y = y0 + r * (key_h + gap)
            shade = random.randint(70, 160)
            draw.rounded_rectangle((x, y, x + key_w, y + key_h), radius=4, fill=(shade, shade, shade))


def draw_phone(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    phone_w = random.randint(width // 4, width // 3)
    phone_h = random.randint(height // 2, int(height * 0.75))
    x0 = random.randint(40, max(41, width - phone_w - 40))
    y0 = random.randint(25, max(26, height - phone_h - 25))
    draw.rounded_rectangle((x0, y0, x0 + phone_w, y0 + phone_h), radius=28, fill=random_color((28, 29, 32), 8))
    inset = random.randint(10, 18)
    draw.rounded_rectangle(
        (x0 + inset, y0 + inset * 2, x0 + phone_w - inset, y0 + phone_h - inset * 2),
        radius=14,
        fill=random_color((55, 65, 75), 30),
    )
    for _ in range(random.randint(2, 5)):
        y = random.randint(y0 + 50, y0 + phone_h - 50)
        draw.line((x0 + 25, y, x0 + phone_w - 25, y), fill=random_color((180, 190, 200), 25), width=2)


def draw_laptop(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    x0 = random.randint(35, 80)
    y0 = random.randint(40, 90)
    screen_w = random.randint(width // 2, int(width * 0.78))
    screen_h = random.randint(height // 4, height // 3)
    draw.rounded_rectangle((x0, y0, x0 + screen_w, y0 + screen_h), radius=8, fill=random_color((35, 42, 50), 10))
    draw.rectangle((x0 + 12, y0 + 12, x0 + screen_w - 12, y0 + screen_h - 12), fill=random_color((100, 120, 135), 35))
    base_y = y0 + screen_h + random.randint(8, 20)
    draw.polygon(
        [
            (x0 - 20, base_y),
            (x0 + screen_w + 20, base_y),
            (x0 + screen_w - 10, base_y + 85),
            (x0 + 10, base_y + 85),
        ],
        fill=random_color((75, 76, 80), 16),
    )
    key_w = 24
    key_h = 12
    for r in range(4):
        for c in range(12):
            x = x0 + 18 + c * 28 + (r % 2) * 6
            y = base_y + 12 + r * 16
            draw.rounded_rectangle((x, y, x + key_w, y + key_h), radius=2, fill=random_color((120, 120, 124), 20))


def draw_remote(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    remote_w = random.randint(80, 130)
    remote_h = random.randint(height // 2, int(height * 0.8))
    x0 = random.randint(60, width - remote_w - 60)
    y0 = random.randint(30, height - remote_h - 30)
    draw.rounded_rectangle((x0, y0, x0 + remote_w, y0 + remote_h), radius=28, fill=random_color((38, 39, 42), 10))
    for r in range(random.randint(6, 9)):
        for c in range(random.randint(2, 3)):
            cx = x0 + 28 + c * 34 + random.randint(-2, 2)
            cy = y0 + 42 + r * 34 + random.randint(-2, 2)
            radius = random.randint(9, 13)
            color = random_color((120, 120, 120), 35)
            draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=color)


def draw_blinds(draw: ImageDraw.ImageDraw, width: int, height: int) -> None:
    x0 = random.randint(15, 45)
    y0 = random.randint(40, 110)
    w = random.randint(int(width * 0.65), int(width * 0.92))
    h = random.randint(int(height * 0.35), int(height * 0.65))
    draw.rectangle((x0, y0, x0 + w, y0 + h), fill=random_color((190, 195, 190), 20))
    slat_h = random.randint(10, 18)
    for y in range(y0, y0 + h, slat_h):
        draw.rectangle((x0, y, x0 + w, y + max(2, slat_h // 3)), fill=random_color((150, 155, 152), 18))
        draw.line((x0, y, x0 + w, y + random.randint(-3, 3)), fill=random_color((80, 85, 82), 20), width=1)


def apply_camera_noise(image: Image.Image) -> Image.Image:
    image = image.rotate(random.uniform(-5, 5), expand=False, fillcolor=random_color((220, 220, 220), 20))
    if random.random() < 0.7:
        image = image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.2)))
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for _ in range(random.randint(80, 180)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        gray = random.randint(0, 255)
        draw.point((x, y), fill=(gray, gray, gray))
    return image


def make_image(pattern: str, width: int, height: int) -> Image.Image:
    image = make_background(width, height)
    draw = ImageDraw.Draw(image)
    {
        "keyboard": draw_keyboard,
        "phone": draw_phone,
        "laptop": draw_laptop,
        "remote_control": draw_remote,
        "window_blinds": draw_blinds,
    }[pattern](draw, width, height)
    return apply_camera_noise(image)


def main() -> int:
    random.seed(20260616)
    dataset_root = Path(__file__).resolve().parents[1]
    default_output = dataset_root / "10_원천이미지_raw" / "91_하드네거티브_합성이미지_20260616"
    default_manifest = dataset_root / "02_매니페스트_CSV" / "hard_negative_synthetic_20260616_manifest.csv"
    parser = argparse.ArgumentParser(description="Generate synthetic hard-negative images for filter false-positive reduction.")
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--manifest", type=Path, default=default_manifest)
    parser.add_argument("--count", type=int, default=80)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    manifest_path = args.manifest.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if args.force:
        for image_path in output_dir.glob("*.jpg"):
            image_path.unlink()

    rows: list[dict[str, str]] = []
    for index in range(1, args.count + 1):
        pattern = PATTERNS[(index - 1) % len(PATTERNS)]
        width = random.choice([640, 720, 800, 960])
        height = random.choice([480, 540, 600, 720])
        image = make_image(pattern, width, height)
        filename = f"hardneg_synthetic_{pattern}_{index:04d}.jpg"
        image.save(output_dir / filename, quality=random.randint(72, 90))
        rows.append(
            {
                "filename": filename,
                "pattern": pattern,
                "width": str(width),
                "height": str(height),
                "label_policy": "empty_yolo_label_background",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    with manifest_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=["filename", "pattern", "width", "height", "label_policy", "created_at_utc"],
        )
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "output_dir": str(output_dir),
        "manifest": str(manifest_path),
        "count": len(rows),
        "patterns": PATTERNS,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
