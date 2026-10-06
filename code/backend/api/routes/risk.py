from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from services.ml import MLError, get_ml_gateway

router = APIRouter()

ALERT_LEVELS = {"high": "high", "critical": "critical"}


async def _overview() -> Dict[str, Any]:
    return await get_ml_gateway().risk_overview()


def _alerts(overview: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts = []
    for item in overview["items"]:
        for factor, level in item["factor_levels"].items():
            if level in ALERT_LEVELS:
                alerts.append(
                    {
                        "alert_id": str(
                            uuid5(NAMESPACE_URL, f"{item['entity_id']}:{factor}")
                        ),
                        "severity": level,
                        "entity_type": item["entity_type"],
                        "entity_id": item["entity_id"],
                        "factor": factor,
                        "score": item["factors"][factor],
                        "message": f"{item['name'] or item['entity_id']}: "
                        f"{factor.replace('_', ' ')} is {level}",
                    }
                )
    return alerts


@router.get("/risk/assessment/{user_id}")
async def get_risk_assessment(user_id: str) -> JSONResponse:
    try:
        overview = await _overview()
    except MLError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
    return JSONResponse(
        {
            "user_id": user_id,
            "overall_risk_score": round(overview["overall_risk"], 4),
            "risk_level": overview["risk_level"],
            "risk_factors": overview["factors"],
            "portfolio_id": str(uuid5(NAMESPACE_URL, f"portfolio:{user_id}")),
            "data_source": overview["data_source"],
        }
    )


@router.post("/risk/monitor")
async def start_risk_monitoring(data: Dict[str, Any]) -> JSONResponse:
    return JSONResponse(
        {
            "monitoring_id": str(uuid4()),
            "portfolio_id": data.get("portfolio_id"),
            "status": "active",
        }
    )


@router.get("/risk/alerts")
async def get_risk_alerts() -> JSONResponse:
    try:
        overview = await _overview()
    except MLError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
    return JSONResponse(_alerts(overview))


@router.post("/risk/report")
async def generate_risk_report(data: Dict[str, Any]) -> JSONResponse:
    try:
        overview = await _overview()
    except MLError as exc:
        return JSONResponse({"detail": exc.message}, status_code=exc.status_code)
    alerts = _alerts(overview)
    top_factor = max(overview["factors"], key=overview["factors"].get)
    recommendations = []
    if overview["factor_levels"].get("liquidity_risk") in ALERT_LEVELS:
        recommendations.append("Reduce exposure to thinly capitalised pools")
    if overview["factor_levels"].get("credit_risk") in ALERT_LEVELS:
        recommendations.append("Increase collateral buffers on synthetic positions")
    if overview["factor_levels"].get("compliance_risk") in ALERT_LEVELS:
        recommendations.append("Prioritise verification of unverified pools")
    if not recommendations:
        recommendations.append("Risk metrics are within acceptable ranges")
    return JSONResponse(
        {
            "executive_summary": f"Portfolio shows {overview['risk_level']} risk profile, "
            f"driven mainly by {top_factor.replace('_', ' ')}",
            "risk_assessment": {
                "overall_risk_score": round(overview["overall_risk"], 4),
                "risk_level": overview["risk_level"],
                "factors": overview["factors"],
            },
            "recommendations": recommendations,
            "risk_metrics": overview["items"],
            "alerts": alerts,
            "data_source": overview["data_source"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
