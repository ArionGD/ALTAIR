import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from src.api.StrikeRoutes import router as strike_router

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

# Include Modular Routers
app.include_router(strike_router)

@app.get("/")
async def root():
    return {
        "engine": "ALTAIR V1.0 - Operational",
        "objective": "High-Precision Financial Predation",
        "api_v1_docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    # Defaulting to 8001 to avoid conflict with standard dev servers
    uvicorn.run(app, host="127.0.0.1", port=8001)
