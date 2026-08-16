import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from src.api.StrikeRoutes import router as strike_router
from src.api.DashboardRoutes import router as dashboard_router
from src.api.ArchiveRoutes import router as archive_router
from src.api.ScenarioRoutes import router as scenario_router
from src.api.EGBRoutes import router as egb_router
from src.api.DetailRoutes import router as detail_router
from src.api.MarketRoutes import router as market_router
from src.api.templates import templates

from src.database.db_setup import engine
from src.database.models import Base

# Load Environment Variables
load_dotenv()

# Initialize SQLite database and create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ALTAIR: Financial Fragility Gateway",
    version="1.0.0",
    description="Backend-AI for Ranking the Weakest Stocks"
)

# Enable CORS for generic frontend access (Cloud hosting ready)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets (logo, etc.) — served at /static/...
app.mount("/static", StaticFiles(directory="templates/static"), name="static")

# Include Modular Routers
app.include_router(strike_router)
app.include_router(dashboard_router)
app.include_router(archive_router)
app.include_router(scenario_router)
app.include_router(egb_router)
app.include_router(detail_router)
app.include_router(market_router)

# Mount React static files if built (Production configuration)
DIST_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Serve index.html for root and React internal SPA router paths
    @app.get("/")
    @app.get("/dashboard")
    @app.get("/overview")
    @app.get("/strikes")
    @app.get("/astro_scanner")
    @app.get("/swing")
    @app.get("/archives")
    @app.get("/guide")
    async def serve_react_app(request: Request):
        return FileResponse(os.path.join(DIST_DIR, "index.html"))
else:
    # Fallback to server-rendered Jinja2 templates (Local Dev configuration)
    @app.get("/")
    async def root(request: Request):
        """Landing page. For the raw engine status JSON, see /api/v1/health."""
        return templates.TemplateResponse(request, "landing/home.html")

    @app.get("/features")
    async def features(request: Request):
        return templates.TemplateResponse(request, "landing/features.html")

    @app.get("/support")
    async def support(request: Request):
        return templates.TemplateResponse(request, "landing/support.html")

if __name__ == "__main__":
    import uvicorn
    # Defaulting to 8001 (configurable via environment variable PORT for Cloud Run)
    port = int(os.environ.get("PORT", 8001))
    # On Cloud Run, bind to 0.0.0.0
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    uvicorn.run(app, host=host, port=port)
