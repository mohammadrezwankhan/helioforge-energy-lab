"""Reconstruct supplied survey photographs with a locally installed COLMAP.

Writes a new work directory only. Results have arbitrary scale until independently
registered against surveyed ground control. No bundled photographs or fake cloud.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def reconstruct(images: Path, output: Path, camera_params: str) -> dict:
    images, output = images.resolve(strict=True), output.resolve()
    if (
        not images.is_dir()
        or output.exists()
        or images == output
        or images in output.parents
    ):
        raise ValueError(
            "Use a real image directory and a new output directory outside it."
        )
    photos = sorted(
        p for p in images.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    if not 3 <= len(photos) <= 200 or any(
        p.is_symlink() or "\n" in p.name or p.stat().st_size > 30_000_000
        for p in photos
    ):
        raise ValueError(
            "Supply 3–200 original images, each at most 30 MB; no symlinks."
        )
    params = [float(value) for value in camera_params.split(",")]
    if len(params) != 4 or any(not 0 < value < 100000 for value in params):
        raise ValueError(
            "PINHOLE camera parameters must be positive fx,fy,cx,cy in pixels."
        )
    program = shutil.which("colmap")
    if not program:
        raise ValueError(
            "Install COLMAP and put it on PATH. Supply calibrated overlapping survey photographs."
        )
    output.mkdir(parents=True)
    database, sparse, text = output / "features.db", output / "sparse", output / "text"
    sparse.mkdir()
    text.mkdir()
    image_list = output / "images.txt"
    image_list.write_text("\n".join(p.name for p in photos), encoding="utf-8")
    commands = [
        [
            "feature_extractor",
            "--database_path",
            str(database),
            "--image_path",
            str(images),
            "--ImageReader.camera_model",
            "PINHOLE",
            "--ImageReader.camera_params",
            camera_params,
            "--ImageReader.single_camera",
            "1",
            "--image_list_path",
            str(image_list),
            "--FeatureExtraction.use_gpu",
            "0",
            "--FeatureExtraction.max_image_size",
            "2400",
            "--FeatureExtraction.num_threads",
            "4",
        ],
        [
            "exhaustive_matcher",
            "--database_path",
            str(database),
            "--FeatureMatching.use_gpu",
            "0",
        ],
        [
            "mapper",
            "--database_path",
            str(database),
            "--image_path",
            str(images),
            "--output_path",
            str(sparse),
        ],
        [
            "model_converter",
            "--input_path",
            str(sparse / "0"),
            "--output_path",
            str(text),
            "--output_type",
            "TXT",
        ],
    ]
    with (output / "reconstruction.log").open("w", encoding="utf-8") as log:
        for args in commands:
            subprocess.run(
                [program, *args],
                check=True,
                timeout=1800,
                stdout=log,
                stderr=log,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
    points = []
    for line in (text / "points3D.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        cells = line.split()
        xyz = [float(value) for value in cells[1:4]]
        if len(xyz) != 3 or any(not -1e12 < value < 1e12 for value in xyz):
            raise ValueError("COLMAP output has invalid coordinates.")
        points.append(xyz)
    if len(points) < 3:
        raise ValueError(
            "Reconstruction produced fewer than three points; inspect image overlap and calibration."
        )
    result = {
        "schema": "helioforge-colmap-v1",
        "photos_supplied": len(photos),
        "sparse_point_count": len(points),
        "camera_model": "PINHOLE",
        "camera_params": params,
        "point_cloud_xyz": points,
        "data_kind": "user_photographs_unverified",
        "scale": "arbitrary_until_surveyed_control_registration",
        "notice": "Sparse structure-from-motion, not dense reconstruction or an approved survey. Inspect reprojection residuals and register surveyed control before converting to metres.",
    }
    (output / "reconstruction.json").write_text(
        json.dumps(result, allow_nan=False, indent=2), encoding="utf-8"
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--camera-params",
        required=True,
        help="fx,fy,cx,cy in pixels from calibrated camera",
    )
    args = parser.parse_args()
    result = reconstruct(args.images, args.output, args.camera_params)
    print(json.dumps({k: v for k, v in result.items() if k != "point_cloud_xyz"}))
