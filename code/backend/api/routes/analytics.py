"""
Analytics routes for Fluxion Backend
"""

from typing import Any, Dict

from api.routes.auth import get_current_user
from fastapi import APIRouter, Depends, Query
from services.ml import MLError, get_ml_gateway

router = APIRouter()


@router.get("/overview", summary="Get analytics overview")
async def get_overview(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a high-level analytics overview for the user."""
    return {
        "success": True,
        "data": {
            "user_id": current_user["user_id"],
            "total_transactions": 0,
            "total_volume": 0.0,
            "active_portfolios": 0,
            "risk_score": "low",
        },
    }


@router.get("/risk", summary="Get risk analytics")
async def get_risk_analytics(
    days: int = Query(default=30, ge=1, le=365),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get risk analytics for the authenticated user."""
    risk_metrics: Dict[str, Any] = {}
    alerts: list = []
    ml_available = True
    try:
        overview = await get_ml_gateway().risk_overview()
        risk_metrics = {
            "overall_risk": overview["overall_risk"],
            "risk_level": overview["risk_level"],
            "factors": overview["factors"],
            "factor_levels": overview["factor_levels"],
            "data_source": overview["data_source"],
        }
        alerts = [
            {
                "entity_id": item["entity_id"],
                "name": item["name"],
                "factor": factor,
                "level": level,
            }
            for item in overview["items"]
            for factor, level in item["factor_levels"].items()
            if level in ("high", "critical")
        ]
    except MLError:
        ml_available = False
    return {
        "success": True,
        "data": {
            "user_id": current_user["user_id"],
            "period_days": days,
            "risk_metrics": risk_metrics,
            "alerts": alerts,
            "ml_available": ml_available,
        },
    }


@router.get("/compliance", summary="Get compliance analytics")
async def get_compliance_analytics(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get compliance analytics for the authenticated user."""
    return {
        "success": True,
        "data": {
            "user_id": current_user["user_id"],
            "kyc_status": "pending",
            "aml_status": "clear",
            "compliance_score": 100,
        },
    }
