from __future__ import annotations

import csv
import os
from pathlib import Path


def mask_secret(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return value[0] + "***"
    return f"{value[:4]}...{value[-4:]}"


def main() -> int:
    try:
        from roboflow import Roboflow
    except ModuleNotFoundError:
        print("roboflow SDK is not installed. Install it first: pip install roboflow")
        return 1

    api_key = os.getenv("ROBOFLOW_API_KEY")
    workspace_name = os.getenv("ROBOFLOW_WORKSPACE")
    project_name = os.getenv("ROBOFLOW_PROJECT")
    batch_name = os.getenv("ROBOFLOW_BATCH_NAME", "lg_wall_mounted_filter_user_primary_099")
    split = os.getenv("ROBOFLOW_SPLIT", "train")
    list_projects_only = os.getenv("ROBOFLOW_LIST_PROJECTS_ONLY", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    missing = [
        name
        for name, value in {
            "ROBOFLOW_API_KEY": api_key,
            "ROBOFLOW_WORKSPACE": workspace_name,
            "ROBOFLOW_PROJECT": project_name,
        }.items()
        if not value
    ]
    if missing:
        print("Missing environment variables: " + ", ".join(missing))
        return 1

    print("Roboflow upload config:")
    print(f"- ROBOFLOW_API_KEY={mask_secret(api_key)}")
    print(f"- ROBOFLOW_WORKSPACE={workspace_name}")
    print(f"- ROBOFLOW_PROJECT={project_name}")
    print(f"- ROBOFLOW_BATCH_NAME={batch_name}")
    print(f"- ROBOFLOW_SPLIT={split}")

    images_dir = Path(__file__).resolve().parent / "images"
    results_csv = Path(__file__).resolve().parent / "roboflow_upload_results.csv"
    image_paths = sorted(
        path
        for path in images_dir.iterdir()
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )
    if not image_paths:
        print(f"No images found: {images_dir}")
        return 1

    rf = Roboflow(api_key=api_key)
    try:
        workspace = rf.workspace(workspace_name)
    except Exception as exc:
        print(f"Failed to open workspace '{workspace_name}': {exc}")
        print("Check that ROBOFLOW_WORKSPACE is the URL slug, not the display name.")
        return 1

    if list_projects_only:
        try:
            projects = workspace.projects()
            print("Workspace projects:")
            print(projects)
            return 0
        except Exception as exc:
            print(f"Failed to list projects: {exc}")
            return 1

    try:
        project = workspace.project(project_name)
    except Exception as exc:
        print(f"Failed to open project '{project_name}': {exc}")
        print("ROBOFLOW_PROJECT must be the project URL slug / project id.")
        print("If the project does not exist yet, create an Object Detection project in Roboflow first.")
        print("You can list visible projects with:")
        print("$env:ROBOFLOW_LIST_PROJECTS_ONLY='1'; python upload_to_roboflow.py")
        return 1

    uploaded = 0
    failed: list[tuple[str, str]] = []
    with results_csv.open("w", newline="", encoding="utf-8") as results_file:
        writer = csv.DictWriter(
            results_file,
            fieldnames=["filename", "status", "split", "batch_name", "message"],
        )
        writer.writeheader()
        for image_path in image_paths:
            try:
                result = project.upload(
                    str(image_path),
                    split=split,
                    batch_name=batch_name,
                    num_retry_uploads=2,
                )
                uploaded += 1
                message = str(result)
                writer.writerow(
                    {
                        "filename": image_path.name,
                        "status": "uploaded",
                        "split": split,
                        "batch_name": batch_name,
                        "message": message[:1000],
                    }
                )
                print(f"uploaded {uploaded}/{len(image_paths)} {image_path.name}")
            except Exception as exc:
                failed.append((image_path.name, str(exc)))
                writer.writerow(
                    {
                        "filename": image_path.name,
                        "status": "failed",
                        "split": split,
                        "batch_name": batch_name,
                        "message": str(exc)[:1000],
                    }
                )
                print(f"failed {image_path.name}: {exc}")

    print(f"done uploaded={uploaded} failed={len(failed)} total={len(image_paths)}")
    print(f"results_csv={results_csv}")
    if failed:
        print("failed files:")
        for name, reason in failed:
            print(f"- {name}: {reason}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
