from fastapi import APIRouter, Request

from src.api.templates import templates

router = APIRouter(tags=["Dashboard"])


@router.get("/dashboard")
async def dashboard(request: Request):
    """Serves the local, backend-only ALTAIR dashboard (Tailwind + Alpine.js + Chart.js).

    This is the primary way to interact with ALTAIR during local development —
    the Astro frontend under astro/ is not ready yet (see project README).
    """
    return templates.TemplateResponse(request, "core/dashboard.html")
