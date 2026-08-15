from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

try:
    from application.auto_processing.usecases.auto_straighten_region import AutoStraightenRegion
    from application.auto_processing.usecases.auto_trim_region import AutoTrimRegion
    from application.project.usecases.create_project import CreateProject
    from application.project.usecases.delete_project import DeleteProject
    from application.project.usecases.import_project import ImportProject
    from application.project.usecases.list_projects import ListProjects
    from application.project.usecases.read_project_image import ReadProjectImage
    from application.project.usecases.update_project import UpdateProject
    from application.region.usecases.delete_region import DeleteRegion
    from application.region.usecases.list_regions import ListRegions
    from application.region.usecases.create_region import CreateRegion
    from application.region.usecases.update_region import UpdateRegion
    from application.region.usecases.render_region import RegionRenderError, RenderRegion
    from model.operation import Operation
    from model.pipeline import Pipeline
    from model.project import ProjectImage, ProjectNotFound
    from model.region import CropRectangle, RegionNotFound
except ImportError:
    from ..application.auto_processing.usecases.auto_straighten_region import AutoStraightenRegion
    from ..application.auto_processing.usecases.auto_trim_region import AutoTrimRegion
    from ..application.project.usecases.create_project import CreateProject
    from ..application.project.usecases.delete_project import DeleteProject
    from ..application.project.usecases.import_project import ImportProject
    from ..application.project.usecases.list_projects import ListProjects
    from ..application.project.usecases.read_project_image import ReadProjectImage
    from ..application.project.usecases.update_project import UpdateProject
    from ..application.region.usecases.delete_region import DeleteRegion
    from ..application.region.usecases.list_regions import ListRegions
    from ..application.region.usecases.create_region import CreateRegion
    from ..application.region.usecases.update_region import UpdateRegion
    from ..application.region.usecases.render_region import RegionRenderError, RenderRegion
    from ..model.operation import Operation
    from ..model.pipeline import Pipeline
    from ..model.project import ProjectImage, ProjectNotFound
    from ..model.region import CropRectangle, RegionNotFound


class RectangleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    width: float
    height: float


class CreateRegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rectangle: RectangleRequest


class OperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    options: dict


class PipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operations: list[OperationRequest]


class UpdateRegionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    rectangle: RectangleRequest
    pipeline: PipelineRequest


def _rectangle(request: RectangleRequest) -> CropRectangle:
    return CropRectangle(request.x, request.y, request.width, request.height)


def _pipeline(request: PipelineRequest) -> Pipeline:
    return Pipeline(tuple(Operation(op.kind, dict(op.options)) for op in request.operations))


def _region_response(item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "pipeline": [{"kind": op.kind, "options": dict(op.options)} for op in item.pipeline.operations],
        "rectangle": {"x": item.rectangle.x, "y": item.rectangle.y, "width": item.rectangle.width, "height": item.rectangle.height},
    }


def _analysis_response(result) -> dict:
    suggestion = result.suggestion
    if isinstance(suggestion, Operation):
        suggestion = {"kind": suggestion.kind, "options": dict(suggestion.options)}
    return {"suggestion": suggestion, "confidence": result.confidence, "reason": result.reason}


def create_app(
    list_projects: ListProjects,
    read_project_image: ReadProjectImage,
    cors_origins: list[str],
    create_project: CreateProject,
    update_project: UpdateProject,
    delete_project: DeleteProject,
    import_project: ImportProject,
    list_regions: ListRegions,
    create_region: CreateRegion,
    update_region: UpdateRegion,
    delete_region: DeleteRegion,
    render_region: RenderRegion,
    auto_straighten: AutoStraightenRegion,
    auto_trim: AutoTrimRegion,
) -> FastAPI:
    application = FastAPI(title="Document Cropper Processor")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    @application.get("/api/projects", response_model=list[str])
    def projects() -> list[str]:
        return list_projects.list()

    @application.post("/api/projects", status_code=201)
    def create_project_endpoint(project_id: str, image: UploadFile) -> dict:
        data = image.file.read()
        try:
            created = create_project.create(project_id, ProjectImage.from_png(data))
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return {"id": str(created)}

    @application.put("/api/projects/{project_id}")
    def update_project_endpoint(project_id: str, image: UploadFile) -> Response:
        data = image.file.read()
        try:
            update_project.update(project_id, ProjectImage.from_png(data))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(status_code=204)

    @application.delete("/api/projects/{project_id}", status_code=204)
    def delete_project_endpoint(project_id: str) -> Response:
        try:
            delete_project.delete(project_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=204)

    @application.post("/api/projects/import", status_code=501)
    def import_project_endpoint(image: UploadFile) -> dict:
        raise HTTPException(status_code=501, detail="Project import is not available yet")

    @application.get("/api/projects/{project_id}/image")
    def project_image(project_id: str) -> Response:
        try:
            image = read_project_image.read(project_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(content=image.data, media_type="image/png")

    @application.get("/api/projects/{project_id}/regions")
    def regions(project_id: str) -> list[dict]:
        try:
            return [_region_response(item) for item in list_regions.list(project_id).regions]
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @application.post("/api/projects/{project_id}/regions", status_code=201)
    def create_region_endpoint(project_id: str, request: CreateRegionRequest) -> dict:
        try:
            item = create_region.create(project_id, _rectangle(request.rectangle))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _region_response(item)

    @application.put("/api/projects/{project_id}/regions/{region_id}")
    def update_region_endpoint(project_id: str, region_id: int, request: UpdateRegionRequest) -> dict:
        try:
            item = update_region.update(project_id, region_id, request.name, _rectangle(request.rectangle), _pipeline(request.pipeline))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _region_response(item)

    @application.delete("/api/projects/{project_id}/regions/{region_id}", status_code=204)
    def delete_region_endpoint(project_id: str, region_id: int) -> Response:
        try:
            delete_region.delete(project_id, region_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=204)

    @application.get("/api/projects/{project_id}/regions/{region_id}/render")
    def render(project_id: str, region_id: int) -> Response:
        try:
            content = render_region.render(project_id, region_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionRenderError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(content=content, media_type="image/png", headers={"Content-Disposition": f'attachment; filename="{project_id}-region-{region_id}.png"'})

    @application.post("/api/projects/{project_id}/regions/{region_id}/render")
    def preview_region(project_id: str, region_id: int, request: PipelineRequest) -> Response:
        try:
            content = render_region.preview(project_id, region_id, _pipeline(request))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except RegionRenderError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(content=content, media_type="image/png")

    @application.post("/api/projects/{project_id}/regions/{region_id}/auto/straighten")
    def auto_straighten_region(project_id: str, region_id: int) -> dict:
        try:
            return _analysis_response(auto_straighten.suggest(project_id, region_id))
        except (ProjectNotFound, RegionNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @application.post("/api/projects/{project_id}/regions/{region_id}/auto/trim")
    def auto_trim_region(project_id: str, region_id: int) -> dict:
        try:
            return _analysis_response(auto_trim.suggest(project_id, region_id))
        except (ProjectNotFound, RegionNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return application
