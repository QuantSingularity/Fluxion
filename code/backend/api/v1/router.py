"""
API v1 Router for Fluxion Backend
Aggregates all API routes for version 1 of the API
"""

from api.routes import (
    analytics,
    auth,
    compliance,
    health,
    markets,
    ml,
    portfolio,
    risk,
    transactions,
    users,
)
from fastapi import APIRouter

api_router = APIRouter()

# Health routes (no auth required)
api_router.include_router(health.router, prefix="/health", tags=["Health"])

# Authentication routes
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User management routes (auth required)
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Portfolio routes (auth required)
api_router.include_router(portfolio.router, prefix="/portfolio", tags=["Portfolio"])

# Transaction routes (auth required)
api_router.include_router(
    transactions.router, prefix="/transactions", tags=["Transactions"]
)

# Analytics routes (auth required)
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

# Market data routes (pools, synthetics, assets) - public read access
api_router.include_router(markets.router, prefix="/markets", tags=["Markets"])

api_router.include_router(ml.router, tags=["ML"])

# Compliance and KYC routes
api_router.include_router(compliance.router, tags=["Compliance"])

# Risk management routes
api_router.include_router(risk.router, tags=["Risk"])
