"""
DEV-ONLY Wiring Audit Routes
Exposes mounted FastAPI routes for frontend/backend wiring verification.

SECURITY: This endpoint is ONLY available when ENV != "production"
In production, this router is not mounted at all.
"""
from fastapi import APIRouter, Request, HTTPException
from typing import List, Dict
import os

router = APIRouter(prefix="/dev/wiring", tags=["Dev - Wiring Audit"])

# Environment check - this module should not be imported in production
# but we add a runtime check as well
IS_PRODUCTION = os.environ.get("ENV", "development").lower() == "production"


def get_all_routes(app) -> List[Dict[str, str]]:
    """
    Extract all mounted routes from FastAPI application.
    Returns list of {method, path} dicts.
    """
    routes = []
    
    def extract_routes(router, prefix=""):
        for route in router.routes:
            # Skip internal routes
            if hasattr(route, 'path'):
                path = prefix + route.path
                
                # Skip OpenAPI/docs routes
                if any(skip in path for skip in ['/openapi', '/docs', '/redoc', '/favicon']):
                    continue
                
                # Get methods
                methods = getattr(route, 'methods', None)
                if methods:
                    for method in methods:
                        if method not in ['HEAD', 'OPTIONS']:
                            routes.append({
                                "method": method,
                                "path": path
                            })
                
                # Recurse into sub-routers
                if hasattr(route, 'routes'):
                    extract_routes(route, path)
    
    # Start from the main app
    extract_routes(app)
    
    return sorted(routes, key=lambda x: (x['path'], x['method']))


@router.get("/routes", summary="Get all mounted API routes (DEV ONLY)")
async def get_mounted_routes(request: Request):
    """
    Returns a list of all mounted FastAPI routes.
    
    This endpoint is ONLY available in development mode.
    In production, this router is not mounted.
    """
    # Double-check: fail if somehow called in production
    if IS_PRODUCTION:
        raise HTTPException(status_code=404, detail="Not found")
    
    # Get the FastAPI app instance from the request
    app = request.app
    
    routes = get_all_routes(app)
    
    # Filter to only /api/v1 routes
    api_routes = [r for r in routes if r['path'].startswith('/api/v1')]
    
    return {
        "success": True,
        "environment": os.environ.get("ENV", "development"),
        "total_routes": len(api_routes),
        "routes": api_routes
    }


@router.get("/health", summary="Dev wiring health check")
async def wiring_health():
    """Simple health check for dev wiring endpoint"""
    if IS_PRODUCTION:
        raise HTTPException(status_code=404, detail="Not found")
    
    return {
        "status": "ok",
        "environment": os.environ.get("ENV", "development"),
        "message": "Wiring audit endpoint available"
    }
