from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Fusion Engine", version="0.1.0")

    # CORS for front-end Streamlit Cockpit
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global state initialization
    app.state.status = {"state": "IDLE", "error": None, "models_ready": False}
    app.state.manager = None

    # Include routers (added later)
    from .routers import system, files, stream, webrtc
    app.include_router(system.router, prefix="/system", tags=["system"])
    app.include_router(files.router, prefix="/files", tags=["files"])
    app.include_router(stream.router, prefix="/stream", tags=["stream"])
    app.include_router(webrtc.router, prefix="/webrtc", tags=["webrtc"])

    # Register startup events
    from .events import register_startup_events
    register_startup_events(app)

    return app


app = create_app()