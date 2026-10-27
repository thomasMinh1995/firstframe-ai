from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.dataset_branches import router as dataset_branches_router
from app.api.routes.dataset_transfer import router as dataset_transfer_router
from app.api.routes.datasets import router as datasets_router
from app.api.routes.demo import router as demo_router
from app.api.routes.generate import router as generate_router
from app.api.routes.health import router as health_router
from app.api.routes.projects import router as projects_router
from app.api.routes.screenplays import router as screenplays_router
from app.api.routes.scene_sketches import router as scene_sketches_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="FirstFrame AI API",
        description="Backend foundation for the FirstFrame AI Creative Reasoning Harness.",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(demo_router)
    app.include_router(datasets_router)
    app.include_router(dataset_transfer_router)
    app.include_router(dataset_branches_router)
    app.include_router(generate_router)
    app.include_router(screenplays_router)
    app.include_router(scene_sketches_router)
    app.include_router(projects_router)
    return app


app = create_app()
