import os
from pathlib import Path
import types
import importlib
import pytest

from fastapi import HTTPException

import utils.file_service as fs


def setup_upload_dir(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    monkeypatch.setattr(fs, "UPLOADS_DIR", uploads)
    return uploads


def test_absolute_path_denied(tmp_path, monkeypatch):
    setup_upload_dir(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        fs.download_file("/etc/passwd")
    assert exc.value.status_code == 400


def test_outside_uploads_denied(tmp_path, monkeypatch):
    setup_upload_dir(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        fs.download_file("../secret.txt")
    assert exc.value.status_code == 403


def test_nonexistent_file(tmp_path, monkeypatch):
    setup_upload_dir(tmp_path, monkeypatch)
    with pytest.raises(HTTPException) as exc:
        fs.download_file("missing.txt")
    assert exc.value.status_code == 404


def test_success(tmp_path, monkeypatch):
    uploads = setup_upload_dir(tmp_path, monkeypatch)
    file = uploads / "hello.txt"
    file.write_text("ok")
    resp = fs.download_file("hello.txt")
    assert resp.path == str(file)
    assert resp.filename == "hello.txt"
