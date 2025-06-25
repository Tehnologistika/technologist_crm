from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse

# Base directory of the project (two levels up from this file)
BASE_DIR = Path(__file__).resolve().parents[1]
UPLOADS_DIR = BASE_DIR / "uploads"


def download_file(path: str):
    """Return FileResponse for files only inside ``UPLOADS_DIR``.

    Absolute paths are forbidden and any attempt to access files
    outside ``UPLOADS_DIR`` results in an error.
    """
    p = Path(path)

    if p.is_absolute():
        # absolute paths are not allowed
        raise HTTPException(status_code=400, detail="Absolute path not allowed")

    full_path = (UPLOADS_DIR / p).resolve()
    uploads_root = UPLOADS_DIR.resolve()

    if uploads_root not in full_path.parents and full_path != uploads_root:
        # Trying to escape uploads directory
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(str(full_path), filename=full_path.name)
