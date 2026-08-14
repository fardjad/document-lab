from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Literal
from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt

try:
    from application.project_access.usecases.project_queries import ProjectQueries
    from model.project import ProjectNotFound
    from model.project import CropRectangle, RegionNotFound, RegionTrim
    from application.region_management.usecases.region_commands import RegionCommands
    from application.region_export.usecases.export_region import RegionExport, RegionRenderError
    from application.region_analysis.usecases.analyze_region import RegionAnalysis
    from application.region_analysis.results import AnalysisResult
except ImportError:
    from ..application.project_access.usecases.project_queries import ProjectQueries
    from ..model.project import ProjectNotFound
    from ..model.project import CropRectangle, RegionNotFound, RegionTrim
    from ..application.region_management.usecases.region_commands import RegionCommands
    from ..application.region_export.usecases.export_region import RegionExport, RegionRenderError
    from ..application.region_analysis.usecases.analyze_region import RegionAnalysis
    from ..application.region_analysis.results import AnalysisResult


class RectangleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    width: float
    height: float


class CreateRegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rectangle: RectangleRequest


class TrimRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    top: StrictInt
    right: StrictInt
    bottom: StrictInt
    left: StrictInt


class UpdateRegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    rectangle: RectangleRequest
    rotation: StrictInt
    straighten: StrictInt | StrictFloat
    trim: TrimRequest


class RegionAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: Literal["straighten", "trim"]


def _rectangle(request: RectangleRequest) -> CropRectangle:
    return CropRectangle(request.x, request.y, request.width, request.height)


def _region_response(item) -> dict:
    return {"id": item.id, "name": item.name, "rotation": item.rotation, "straighten": item.straighten, "trim": {"top": item.trim.top, "right": item.trim.right, "bottom": item.trim.bottom, "left": item.trim.left}, "rectangle": {"x": item.rectangle.x, "y": item.rectangle.y, "width": item.rectangle.width, "height": item.rectangle.height}}


def _analysis_response(result: AnalysisResult) -> dict:
    suggestion = result.suggestion
    if isinstance(suggestion, RegionTrim):
        suggestion = {"top": suggestion.top, "right": suggestion.right, "bottom": suggestion.bottom, "left": suggestion.left}
    return {"suggestion": suggestion, "confidence": result.confidence, "reason": result.reason}


def create_app(queries: ProjectQueries, cors_origins: list[str], region_commands: RegionCommands, region_export: RegionExport | None = None, region_analysis: RegionAnalysis | None = None) -> FastAPI:
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

    @application.get("/api/projects/{project_id}/regions")
    def regions(project_id: str) -> list[dict]:
        try:
            return [_region_response(item) for item in region_commands.list_regions(project_id).regions]
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @application.post("/api/projects/{project_id}/regions", status_code=201)
    def create_region(project_id: str, request: CreateRegionRequest) -> dict:
        try:
            item = region_commands.create_region(project_id, _rectangle(request.rectangle))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _region_response(item)

    @application.put("/api/projects/{project_id}/regions/{region_id}")
    def update_region(project_id: str, region_id: int, request: UpdateRegionRequest) -> dict:
        try:
            item = region_commands.update_region(project_id, region_id, request.name, _rectangle(request.rectangle), request.rotation, request.straighten, RegionTrim(request.trim.top, request.trim.right, request.trim.bottom, request.trim.left))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _region_response(item)

    @application.delete("/api/projects/{project_id}/regions/{region_id}", status_code=204)
    def delete_region(project_id: str, region_id: int) -> Response:
        try:
            region_commands.delete_region(project_id, region_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=204)

    @application.get("/api/projects/{project_id}/regions/{region_id}/download")
    def download_region(project_id: str, region_id: int) -> Response:
        if region_export is None:
            raise HTTPException(status_code=500, detail="Region export unavailable")
        try:
            content = region_export.export(project_id, region_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionRenderError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(content=content, media_type="image/png", headers={"Content-Disposition": f'attachment; filename="{project_id}-region-{region_id}.png"'})

    @application.post("/api/projects/{project_id}/regions/{region_id}/analysis")
    def analyze_region(project_id: str, region_id: int, request: RegionAnalysisRequest) -> dict:
        if region_analysis is None:
            raise HTTPException(status_code=500, detail="Region analysis unavailable")
        try:
            return _analysis_response(region_analysis.analyze(project_id, region_id, request.operation))
        except (ProjectNotFound, RegionNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return application
