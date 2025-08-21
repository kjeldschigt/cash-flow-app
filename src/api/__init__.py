"""
API package for the Cash Flow Dashboard.

This package contains all API endpoints and routes for the application.
"""
from fastapi import APIRouter

# Import all routers
from .zapier_test_endpoints import router as zapier_test_router

# Create main API router
api_router = APIRouter()

# Include all routers
api_router.include_router(zapier_test_router)

# Expose a generic name for convenience
router = api_router

# This makes the router(s) available when importing the package
__all__ = ['api_router', 'router']
