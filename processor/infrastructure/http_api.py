from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

try:
    from application.project_access.usecases.project_queries import ProjectQueries
    from model.project import ProjectNotFound
except ImportError:
    from ..application.project_access.usecases.project_queries import ProjectQueries
    from ..model.project import ProjectNotFound


def create_app(queries: ProjectQueries, cors_origins: list[str]) -> FastAPI:
    application = FastAPI(title="Document Cropper Processor")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["GET"],
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

    return application
