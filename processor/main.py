from pathlib import Path
import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECTS_ROOT = (PACKAGE_DIR.parent / "projects").resolve()
PROJECT_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _cors_origins() -> list[str]:
    configured = os.getenv("CORS_ORIGINS")
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173"]


app = FastAPI(title="Document Cropper Processor")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _image_path(project_id: str) -> Path:
    if not PROJECT_ID.fullmatch(project_id):
        raise HTTPException(status_code=404, detail="Project not found")

    project = (PROJECTS_ROOT / project_id).resolve()
    if project.parent != PROJECTS_ROOT or not project.is_dir():
        raise HTTPException(status_code=404, detail="Project not found")

    image = (project / "image.png").resolve()
    if image.parent != project or not image.is_file():
        raise HTTPException(status_code=404, detail="Project image not found")
    return image


@app.get("/api/projects", response_model=list[str])
def projects() -> list[str]:
    if not PROJECTS_ROOT.is_dir():
        return []

    result: list[str] = []
    for project in PROJECTS_ROOT.iterdir():
        if project.is_dir() and PROJECT_ID.fullmatch(project.name):
            try:
                _image_path(project.name)
            except HTTPException:
                continue
            result.append(project.name)
    return sorted(result)


@app.get("/api/projects/{project_id}/image")
def project_image(project_id: str) -> FileResponse:
    return FileResponse(_image_path(project_id), media_type="image/png")
