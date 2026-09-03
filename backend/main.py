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
from src.api.AriesRoutes import router as aries_router
from src.api.AltairIntegrationRoutes import router as altair_integration_router
from src.api.templates import templates

from src.database.db_setup import engine
from src.database.models import Base

# Load Environment Variables
load_dotenv()

# Initialize SQLite database and create all tables
Base.metadata.create_all(bind=engine)

from pydantic import BaseModel
from fastapi import HTTPException

# Credentials from Environment
AUTH_USER = os.environ.get("AUTH_USER", "Aditya.raj")
AUTH_PASS = os.environ.get("AUTH_PASS", "Aditya@3205#")

class LoginPayload(BaseModel):
    username: str
    password: str

app = FastAPI(
    title="ALTAIR: Financial Fragility Gateway",
    version="1.0.0",
    description="Backend-AI for Ranking the Weakest Stocks"
)

@app.post("/api/v1/login")
def api_login(data: LoginPayload):
    if data.username.strip().lower() == AUTH_USER.lower() and data.password == AUTH_PASS:
        return {"status": "success", "authenticated": True, "user": data.username, "token": "altair-session-active"}
    raise HTTPException(status_code=401, detail="Invalid User ID or Password")

# Enable CORS for generic frontend access (Cloud hosting ready)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static assets (logo, etc.) — served at /static/...
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
app.mount("/static", StaticFiles(directory=os.path.join(TEMPLATES_DIR, "static")), name="static")

# Include Modular Routers
app.include_router(strike_router)
app.include_router(dashboard_router)
app.include_router(archive_router)
app.include_router(scenario_router)
app.include_router(egb_router)
app.include_router(detail_router)
app.include_router(market_router)
app.include_router(aries_router)
app.include_router(altair_integration_router)

# Mount ALTAIR Advisor Sub-Application (advisor.altair-engine.com) & Quant Lab
import sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_ROOT = os.path.dirname(ROOT_DIR)
if PARENT_ROOT not in sys.path:
    sys.path.insert(0, PARENT_ROOT)

advisor_app = None
quant_lab_app = None

try:
    from advisor.app import app as _adv
    advisor_app = _adv
    app.mount("/advisor", advisor_app)
except Exception as _adv_err:
    print("Advisor mount notice:", _adv_err)

try:
    ql_path = os.path.join(PARENT_ROOT, "quant_lab")
    if ql_path not in sys.path:
        sys.path.insert(0, ql_path)
    from quant_lab.app import app as _ql
    quant_lab_app = _ql
    app.mount("/quant_lab", quant_lab_app)
except Exception as _ql_err:
    print("Quant Lab mount notice:", _ql_err)

class SubdomainRoutingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            host = headers.get(b"host", b"").decode("latin1").lower()
            if advisor_app and host.startswith("advisor."):
                await advisor_app(scope, receive, send)
                return
            elif quant_lab_app and (host.startswith("quant.") or host.startswith("lab.")):
                await quant_lab_app(scope, receive, send)
                return
        await self.app(scope, receive, send)

app.add_middleware(SubdomainRoutingMiddleware)

# Mount React static files if built (Production configuration)
DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist"))
if os.path.exists(DIST_DIR):
    assets_dir = os.path.join(DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/favicon.ico")
    async def serve_favicon_ico():
        return FileResponse(os.path.join(DIST_DIR, "favicon.ico"))

    @app.get("/favicon.png")
    async def serve_favicon_png():
        return FileResponse(os.path.join(DIST_DIR, "favicon.png"))

    @app.get("/logo.png")
    async def serve_logo_png():
        return FileResponse(os.path.join(DIST_DIR, "logo.png"))

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
