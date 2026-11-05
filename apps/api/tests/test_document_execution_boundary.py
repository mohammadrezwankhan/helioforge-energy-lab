"""Untrusted document names and bytes never select parser flags or executables."""

import base64
import shutil
import subprocess
from pathlib import Path

import pytest

from helioforge.integrations import DocumentImport, extract_document


@pytest.mark.parametrize("extension", [".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"])
def test_local_parser_uses_only_resolved_program_and_owned_temporary_paths(
    monkeypatch: pytest.MonkeyPatch, extension: str
) -> None:
    pdf = extension == ".pdf"
    raw = b"%PDF-1.4\nfixture" if pdf else b"fixture-image-bytes"
    program = "pdftotext" if pdf else "tesseract"
    resolved = "/verified/local-tools/" + program
    filename = "../../--psm 0; not-a-command" + extension
    calls: list[list[str]] = []
    inputs: list[Path] = []

    def which(name: str) -> str:
        assert name == program
        return resolved

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(command)
        assert command[0] == resolved
        assert kwargs == {
            "check": True,
            "timeout": 20,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
        }
        if pdf:
            assert command[1:7] == ["-f", "1", "-l", "20", "-enc", "UTF-8"]
            assert len(command) == 9
            source, output = Path(command[7]), Path(command[8])
        else:
            assert command[3:] == ["--psm", "3"]
            source, output = Path(command[1]), Path(command[2]).with_suffix(".txt")
        assert source.name == "input" + extension
        assert source.is_absolute() and source.parent == output.parent
        assert output.name == "extracted.txt"
        assert source.read_bytes() == raw
        assert all(filename not in argument for argument in command)
        inputs.append(source)
        output.write_text("Warranty: 6000 cycles; 80% capacity.", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(shutil, "which", which)
    monkeypatch.setattr(subprocess, "run", run)
    result = extract_document(
        DocumentImport(filename=filename, content_base64=base64.b64encode(raw).decode())
    )
    assert len(calls) == 1
    assert result["extraction_method"] == ("poppler_first_20_pages" if pdf else "tesseract_local_ocr")
    assert result["text"] == "Warranty: 6000 cycles; 80% capacity."
    assert result["identity_verified"] is False
    assert all(not source.exists() for source in inputs)


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("parser", 20), OSError("private detail")])
def test_parser_failure_hides_internal_details_and_removes_temporary_input(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    source_paths: list[Path] = []

    def fail(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        source_paths.append(Path(command[7]))
        raise failure

    monkeypatch.setattr(shutil, "which", lambda _name: "/verified/local-tools/pdftotext")
    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(ValueError, match="Local document extraction failed") as caught:
        extract_document(
            DocumentImport(filename="fixture.pdf", content_base64=base64.b64encode(b"%PDF-1.4").decode())
        )
    assert "private detail" not in str(caught.value)
    assert len(source_paths) == 1 and not source_paths[0].exists()
