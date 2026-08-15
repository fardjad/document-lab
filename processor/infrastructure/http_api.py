from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict

try:
    from application.auto_processing.usecases.auto_straighten_view import AutoStraightenView
    from application.auto_processing.usecases.auto_trim_view import AutoTrimView
    from application.project.usecases.create_project import CreateProject
    from application.project.usecases.delete_project import DeleteProject
    from application.project.usecases.import_project import ImportProject
    from application.project.usecases.list_projects import ListProjects
    from application.project.usecases.read_project_image import ReadProjectImage
    from application.project.usecases.update_project import UpdateProject
    from application.view.usecases.delete_view import DeleteView
    from application.view.usecases.list_views import ListViews
    from application.view.usecases.create_view import CreateView
    from application.view.usecases.update_view import UpdateView
    from application.view.usecases.render_view import ViewRenderError, RenderView
    from model.operation import Operation
    from model.pipeline import Pipeline
    from model.project import ProjectImage, ProjectNotFound
    from model.view import ViewNotFound
except ImportError:
    from ..application.auto_processing.usecases.auto_straighten_view import AutoStraightenView
    from ..application.auto_processing.usecases.auto_trim_view import AutoTrimView
    from ..application.project.usecases.create_project import CreateProject
    from ..application.project.usecases.delete_project import DeleteProject
    from ..application.project.usecases.import_project import ImportProject
    from ..application.project.usecases.list_projects import ListProjects
    from ..application.project.usecases.read_project_image import ReadProjectImage
    from ..application.project.usecases.update_project import UpdateProject
    from ..application.view.usecases.delete_view import DeleteView
    from ..application.view.usecases.list_views import ListViews
    from ..application.view.usecases.create_view import CreateView
    from ..application.view.usecases.update_view import UpdateView
    from ..application.view.usecases.render_view import ViewRenderError, RenderView
    from ..model.operation import Operation
    from ..model.pipeline import Pipeline
    from ..model.project import ProjectImage, ProjectNotFound
    from ..model.view import ViewNotFound


class OperationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    options: dict


class PipelineRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operations: list[OperationRequest]


class CreateViewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    pipeline: PipelineRequest | None = None


class UpdateViewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    pipeline: PipelineRequest


def _pipeline(request: PipelineRequest) -> Pipeline:
    return Pipeline(tuple(Operation(op.kind, dict(op.options)) for op in request.operations))


def _view_response(item) -> dict:
    return {
        "id": item.id,
        "name": item.name,
        "pipeline": [{"kind": op.kind, "options": dict(op.options)} for op in item.pipeline.operations],
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
    list_views: ListViews,
    create_view: CreateView,
    update_view: UpdateView,
    delete_view: DeleteView,
    render_view: RenderView,
    auto_straighten: AutoStraightenView,
    auto_trim: AutoTrimView,
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

    @application.get("/api/projects/{project_id}/views")
    def views(project_id: str) -> list[dict]:
        try:
            return [_view_response(item) for item in list_views.list(project_id).views]
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @application.post("/api/projects/{project_id}/views", status_code=201)
    def create_view_endpoint(project_id: str, request: CreateViewRequest) -> dict:
        try:
            item = create_view.create(project_id, request.name, _pipeline(request.pipeline) if request.pipeline else None)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _view_response(item)

    @application.put("/api/projects/{project_id}/views/{view_id}")
    def update_view_endpoint(project_id: str, view_id: int, request: UpdateViewRequest) -> dict:
        try:
            item = update_view.update(project_id, view_id, request.name, _pipeline(request.pipeline))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ViewNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _view_response(item)

    @application.delete("/api/projects/{project_id}/views/{view_id}", status_code=204)
    def delete_view_endpoint(project_id: str, view_id: int) -> Response:
        try:
            delete_view.delete(project_id, view_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ViewNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return Response(status_code=204)

    @application.get("/api/projects/{project_id}/views/{view_id}/render")
    def render(project_id: str, view_id: int) -> Response:
        try:
            content = render_view.render(project_id, view_id)
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ViewNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ViewRenderError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(content=content, media_type="image/png", headers={"Content-Disposition": f'attachment; filename="{project_id}-view-{view_id}.png"'})

    @application.post("/api/projects/{project_id}/views/{view_id}/render")
    def preview_view(project_id: str, view_id: int, request: PipelineRequest) -> Response:
        try:
            content = render_view.preview(project_id, view_id, _pipeline(request))
        except ProjectNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ViewNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ViewRenderError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return Response(content=content, media_type="image/png")

    @application.post("/api/projects/{project_id}/views/{view_id}/auto/straighten")
    def auto_straighten_view(project_id: str, view_id: int) -> dict:
        try:
            return _analysis_response(auto_straighten.suggest(project_id, view_id))
        except (ProjectNotFound, ViewNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @application.post("/api/projects/{project_id}/views/{view_id}/auto/trim")
    def auto_trim_view(project_id: str, view_id: int) -> dict:
        try:
            return _analysis_response(auto_trim.suggest(project_id, view_id))
        except (ProjectNotFound, ViewNotFound) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    return application
