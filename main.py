import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from src.api.StrikeRoutes import router as strike_router
from src.api.DashboardRoutes import router as dashboard_router
from src.api.ArchiveRoutes import router as archive_router
from src.api.ScenarioRoutes import router as scenario_router
from src.api.EGBRoutes import router as egb_router
from src.api.DetailRoutes import router as detail_router
from src.api.MarketRoutes import router as market_router
from src.api.templates import templates

# Load Environment Variables
load_dotenv()

app = FastAPI(
    title="ALTAIR: Financial Fragility Gateway",
    version="1.0.0",
    description="Backend-AI for Ranking the Weakest Stocks"
)

# Enable CORS for PHOENIX (Django)
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
    # Defaulting to 8001 to avoid conflict with standard dev servers
    uvicorn.run(app, host="127.0.0.1", port=8001)
