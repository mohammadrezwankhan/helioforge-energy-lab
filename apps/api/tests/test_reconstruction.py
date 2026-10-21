import importlib.util
from pathlib import Path

import pytest


def module():
    path = Path(__file__).resolve().parents[3] / "scripts" / "reconstruct-pilot.py"
    spec = importlib.util.spec_from_file_location("pilot_reconstruction", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_reconstruction_adapter_preserves_arbitrary_scale_and_never_overwrites(tmp_path, monkeypatch):
    m = module()
    images = tmp_path / "images"
    images.mkdir()
    out = tmp_path / "result"
    for i in range(3):
        (images / f"{i}.jpg").write_bytes(b"fixture-not-a-photo")
    monkeypatch.setattr(m.shutil, "which", lambda _: "colmap")
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        if command[1] == "model_converter":
            (out / "text" / "points3D.txt").write_text(
                "# header\n1 1 2 3 0 0 0 0\n2 3 4 5 0 0 0 0\n3 5 6 7 0 0 0 0"
            )

    monkeypatch.setattr(m.subprocess, "run", run)
    result = m.reconstruct(images, out, "1000,1000,500,500")
    assert result["point_cloud_xyz"] == [[1, 2, 3], [3, 4, 5], [5, 6, 7]]
    assert result["scale"] == "arbitrary_until_surveyed_control_registration"
    assert len(calls) == 4
    assert "--image_list_path" in calls[0]
    with pytest.raises(ValueError):
        m.reconstruct(images, out, "1000,1000,500,500")


def test_reconstruction_does_not_claim_success_without_tool_or_photos(tmp_path, monkeypatch):
    m = module()
    images = tmp_path / "images"
    images.mkdir()
    with pytest.raises(ValueError, match="3–200"):
        m.reconstruct(images, tmp_path / "out", "1000,1000,500,500")
    for i in range(3):
        (images / f"{i}.jpg").write_bytes(b"fixture")
    monkeypatch.setattr(m.shutil, "which", lambda _: None)
    with pytest.raises(ValueError, match="Install COLMAP"):
        m.reconstruct(images, tmp_path / "out", "1000,1000,500,500")
    assert not (tmp_path / "out").exists()
