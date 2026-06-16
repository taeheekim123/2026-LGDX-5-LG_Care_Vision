import { build } from "esbuild";
import { mkdir, readFile, rm } from "node:fs/promises";
import { pathToFileURL } from "node:url";
import path from "node:path";

const root = process.cwd();
const helperSource = path.join(root, "src", "app", "pages", "arGuideDetection.ts");
const arGuideSource = path.join(root, "src", "app", "pages", "ARGuide.tsx");
const outDir = path.join(root, "runtime_logs", "ar_guide_smoke");
const bundledHelper = path.join(outDir, "arGuideDetection.bundle.mjs");

const assert = (condition, message) => {
  if (!condition) {
    throw new Error(message);
  }
};

await mkdir(outDir, { recursive: true });
await build({
  entryPoints: [helperSource],
  bundle: true,
  format: "esm",
  platform: "node",
  outfile: bundledHelper,
  logLevel: "silent",
});

const helper = await import(pathToFileURL(bundledHelper).href + `?t=${Date.now()}`);
const {
  smoothBox,
  getCaptureSizeFromDimensions,
  getObjectCoverTransform,
  getDetectionGuideText,
} = helper;

const first = { x: 0, y: 0, width: 100, height: 50, confidence: 0.2, class_name: "filter" };
const second = { x: 100, y: 80, width: 200, height: 90, confidence: 0.9, class_name: "filter" };
const smoothed = smoothBox(first, second, 0.35);
assert(Math.abs(smoothed.x - 35) < 0.0001, "smoothBox x should use EMA alpha");
assert(Math.abs(smoothed.y - 28) < 0.0001, "smoothBox y should use EMA alpha");
assert(Math.abs(smoothed.width - 135) < 0.0001, "smoothBox width should use EMA alpha");
assert(Math.abs(smoothed.height - 64) < 0.0001, "smoothBox height should use EMA alpha");
assert(smoothed.confidence === 0.9, "smoothBox should keep latest confidence");

const capture = getCaptureSizeFromDimensions(640, 480);
assert(capture.width === 416, "capture width should stay 416");
assert(capture.height === 312, "capture height should preserve 4:3 source ratio");

const cover = getObjectCoverTransform(390, 600, 416, 312);
assert(cover.offsetX < 0, "object-cover transform should crop horizontal overflow in tall viewport");
assert(cover.offsetY === 0, "object-cover transform should not crop vertical axis in tall viewport");
assert(Math.abs(cover.scaleX - cover.scaleY) < 0.0001, "object-cover scale should be uniform");

assert(
  getDetectionGuideText("ready", "yolo", second).includes("탐지된 필터 위치"),
  "YOLO guide text should reference detected filter position",
);
assert(
  getDetectionGuideText("denied", "none", null).includes("카메라 권한"),
  "Denied guide text should mention camera permission",
);

const arGuide = await readFile(arGuideSource, "utf8");
const staticContracts = [
  ["setInterval", "const interval = window.setInterval"],
  ["700ms frame interval", "}, 700);"],
  ["filter detect endpoint", "/v1/ar/filter-detect"],
  ["image_data_url payload", "image_data_url: imageDataUrl"],
  ["confidence threshold", "confidence_threshold: 0.25"],
  ["mock fallback disabled", "mock_fallback: false"],
  ["jpeg quality", "toDataURL(\"image/jpeg\", 0.72)"],
  ["canvas overlay ref", "overlayRef"],
  ["smoothing call", "smoothBox(smoothedBoxRef.current, detection)"],
  ["safety text", "stepSafetyText"],
];
for (const [name, needle] of staticContracts) {
  assert(arGuide.includes(needle), `ARGuide contract missing: ${name}`);
}

await rm(bundledHelper, { force: true });
console.log(
  JSON.stringify(
    {
      ok: true,
      checks: {
        smoothing: smoothed,
        capture,
        cover,
        static_contracts: staticContracts.length,
      },
    },
    null,
    2,
  ),
);
