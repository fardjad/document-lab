from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, StrictInt

try:
    from application.project_access.usecases.project_queries import ProjectQueries
    from model.project import ProjectNotFound
    from model.project import CropRectangle, SliceNotFound
    from application.slice_management.usecases.slice_commands import SliceCommands
except ImportError:
    from ..application.project_access.usecases.project_queries import ProjectQueries
    from ..model.project import ProjectNotFound
    from ..model.project import CropRectangle, SliceNotFound
    from ..application.slice_management.usecases.slice_commands import SliceCommands


class RectangleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    width: float
    height: float


class CreateSliceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rectangle: RectangleRequest


class UpdateSliceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    rectangle: RectangleRequest
    rotation: StrictInt


def _rectangle(request: RectangleRequest) -> CropRectangle:
    return CropRectangle(request.x, request.y, request.width, request.height)


def _slice_response(item) -> dict:
    return {"id": item.id, "name": item.name, "rotation": item.rotation, "rectangle": {"x": item.rectangle.x, "y": item.rectangle.y, "width": item.rectangle.width, "height": item.rectangle.height}}


def create_app(queries: ProjectQueries, cors_origins: list[str], slice_commands: SliceCommands) -> FastAPI:
    application = FastAPI(title="Document Cropper Processor")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    @application.get("/api/projects", response_model=list[str])
    def projects() -> list[str]:
        return queries.list_projects()

    @application.get("/api/projects/{project_id}/image")
    def project_image(project_id: str) -> Response:
        try:
            image = queries.read_project_image(project_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(content=image.data, media_type="image/png")

    @application.get("/api/projects/{project_id}/slices")
    def slices(project_id: str) -> list[dict]:
        try:
            return [_slice_response(item) for item in slice_commands.list_slices(project_id).slices]
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @application.post("/api/projects/{project_id}/slices", status_code=201)
    def create_slice(project_id: str, request: CreateSliceRequest) -> dict:
        try:
            item = slice_commands.create_slice(project_id, _rectangle(request.rectangle))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _slice_response(item)

    @application.put("/api/projects/{project_id}/slices/{slice_id}")
    def update_slice(project_id: str, slice_id: int, request: UpdateSliceRequest) -> dict:
        try:
            item = slice_commands.update_slice(project_id, slice_id, request.name, _rectangle(request.rectangle), request.rotation)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SliceNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _slice_response(item)

    @application.delete("/api/projects/{project_id}/slices/{slice_id}", status_code=204)
    def delete_slice(project_id: str, slice_id: int) -> Response:
        try:
            slice_commands.delete_slice(project_id, slice_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except SliceNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=204)

    return application
