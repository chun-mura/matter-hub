from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from matter_hub.webapp.api_routes import _cors_origin_regex, _cors_origins, router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="Matter Hub")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_origin_regex=_cors_origin_regex(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)

    @app.get("/")
    def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": "matter-hub-api",
                "message": "JSON API のみです。フロントは Vite（既定 http://localhost:5173）を起動してください。",
            }
        )

    return app


app = create_app()
