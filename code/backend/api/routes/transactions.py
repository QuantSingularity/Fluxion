"""
Transaction routes for Fluxion Backend
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from api.routes.auth import get_current_user
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from services.ml import MLError, get_ml_gateway

router = APIRouter()
logger = logging.getLogger(__name__)

SCREENING_FIELDS = (
    "avg_amount_30d",
    "tx_count_24h",
    "tx_count_30d",
    "account_age_days",
    "kyc_score",
    "country_risk",
    "counterparties_30d",
    "cross_border",
)


class CreateTransactionRequest(BaseModel):
    transaction_type: str = Field(..., description="Type of transaction")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(default="USD", description="Currency code")
    recipient_address: Optional[str] = Field(
        None, description="Recipient wallet address"
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


async def _screen(request: CreateTransactionRequest) -> Dict[str, Any]:
    metadata = request.metadata or {}
    record: Dict[str, Any] = {
        "amount": request.amount,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    for field in SCREENING_FIELDS:
        if field in metadata:
            record[field] = metadata[field]
    try:
        result = await get_ml_gateway().screen_transactions([record])
    except MLError as exc:
        logger.warning("Transaction screening unavailable: %s", exc.message)
        return {"available": False, "requires_review": False, "reason": exc.message}
    item = result["result"][0]
    return {
        "available": True,
        "requires_review": item["requires_review"],
        "flags": item["flags"],
        "anomaly_score": item["anomaly"]["anomaly_score"],
        "is_anomaly": item["anomaly"]["is_anomaly"],
        "violation_probabilities": item["compliance"]["probabilities"],
        "model_versions": result["model_versions"],
    }


@router.get("/", summary="List transactions")
async def list_transactions(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """List all transactions for the authenticated user."""
    return {
        "success": True,
        "data": [],
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": 0,
            "pages": 0,
        },
    }


@router.post("/", summary="Create transaction")
async def create_transaction(
    request: CreateTransactionRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a new transaction."""
    screening = await _screen(request)
    flagged = bool(screening.get("requires_review"))
    return {
        "success": True,
        "data": {
            "transaction_type": request.transaction_type,
            "amount": request.amount,
            "currency": request.currency,
            "status": "pending_review" if flagged else "pending",
            "user_id": current_user["user_id"],
            "screening": screening,
        },
        "message": (
            "Transaction flagged for review" if flagged else "Transaction initiated"
        ),
    }


@router.get("/{transaction_id}", summary="Get transaction by ID")
async def get_transaction(
    transaction_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Get a specific transaction by ID."""
    return {
        "success": True,
        "data": {"transaction_id": transaction_id},
    }


@router.post("/{transaction_id}/cancel", summary="Cancel transaction")
async def cancel_transaction(
    transaction_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Cancel a pending transaction."""
    return {
        "success": True,
        "data": {"transaction_id": transaction_id, "status": "cancelled"},
        "message": "Transaction cancelled",
    }
