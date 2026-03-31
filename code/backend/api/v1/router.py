"""
API v1 Router for Fluxion Backend
Aggregates all API routes for version 1 of the API
"""

from api.routes import auth
from fastapi import APIRouter

api_router = APIRouter()

# Include authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# Add other route inclusions here as they are created:
# api_router.include_router(users.router, prefix="/users", tags=["Users"])
# api_router.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
# api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])
# api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
# api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
