"""The documented installer and launcher must agree on the runtime contract."""
import importlib.util
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("helioforge_launcher", ROOT / "launch.py")
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def installed_project_dependencies(monkeypatch):
    project = tomllib.loads((ROOT / "apps/api/pyproject.toml").read_text())
    installed = dict(value.split("==") for value in project["project"]["dependencies"])
    monkeypatch.setattr(launcher.importlib.metadata, "version", installed.__getitem__)
    return installed


def test_documented_install_passes_launcher_preflight(monkeypatch):
    installed_project_dependencies(monkeypatch)
    assert launcher.check() == []


def test_launcher_rejects_a_mismatched_runtime_dependency(monkeypatch):
    installed = installed_project_dependencies(monkeypatch)
    installed["starlette"] = "0.0.0"
    problems = launcher.check()
    assert len(problems) == 1
    assert "starlette" in problems[0] and "found 0.0.0" in problems[0]
