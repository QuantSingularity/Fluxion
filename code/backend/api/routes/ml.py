from typing import Any, Dict, List, Optional

from api.routes.auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from pydantic import BaseModel, Field
from services.ml import MLError, MLGateway, get_ml_gateway

router = APIRouter(prefix="/ml")

ADMIN_ROLES = {"admin", "super_admin", "risk_manager"}
MAX_RECORDS = 5000
MAX_TRANSACTIONS = 500


def _gateway() -> MLGateway:
    return get_ml_gateway()


def _request_id(request: Request) -> Optional[str]:
    return request.headers.get("x-request-id")


def _http(exc: MLError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.message)


def require_ml_admin(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    roles = current_user.get("roles") or []
    if isinstance(roles, str):
        roles = [roles]
    if not ADMIN_ROLES.intersection(roles):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user


class LiquidityRequest(BaseModel):
    horizon: int = Field(default=3, ge=1, le=6)
    records: Optional[List[Dict[str, Any]]] = Field(
        default=None, max_length=MAX_RECORDS
    )


class SupplyChainRequest(BaseModel):
    horizon: int = Field(default=3, ge=1, le=5)
    records: List[Dict[str, Any]] = Field(..., min_length=1, max_length=MAX_RECORDS)


class RiskRequest(BaseModel):
    records: Optional[List[Dict[str, Any]]] = Field(
        default=None, max_length=MAX_RECORDS
    )


class ScreenRequest(BaseModel):
    transactions: List[Dict[str, Any]] = Field(
        ..., min_length=1, max_length=MAX_TRANSACTIONS
    )


class TrainRequest(BaseModel):
    models: Optional[List[str]] = None
    profile: str = Field(default="full", pattern="^(full|quick)$")


@router.get("/status", summary="ML model status")
async def ml_status(current_user: Dict[str, Any] = Depends(get_current_user)):
    try:
        return {"success": True, "data": await _gateway().status()}
    except MLError as exc:
        raise _http(exc)


@router.get("/risk/overview", summary="Market-wide ML risk overview")
async def risk_overview(request: Request):
    try:
        data = await _gateway().risk_overview(_request_id(request))
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.get("/pools/{pool_id}/risk", summary="ML risk assessment for a pool")
async def pool_risk(request: Request, pool_id: str = Path(..., max_length=100)):
    try:
        data = await _gateway().entity_risk("pool", pool_id, rid=_request_id(request))
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.get("/assets/{asset_id}/risk", summary="ML risk assessment for an asset")
async def asset_risk(request: Request, asset_id: str = Path(..., max_length=100)):
    try:
        data = await _gateway().entity_risk(
            "synthetic", asset_id, rid=_request_id(request)
        )
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.get("/pools/{pool_id}/forecast", summary="Liquidity forecast for a pool")
async def pool_forecast(
    request: Request,
    pool_id: str = Path(..., max_length=100),
    horizon: int = Query(default=3, ge=1, le=6),
):
    try:
        data = await _gateway().liquidity_forecast(
            pool_id, horizon, rid=_request_id(request)
        )
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.post(
    "/pools/{pool_id}/forecast", summary="Liquidity forecast from supplied history"
)
async def pool_forecast_custom(
    request: Request,
    body: LiquidityRequest,
    pool_id: str = Path(..., max_length=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        data = await _gateway().liquidity_forecast(
            pool_id, body.horizon, body.records, _request_id(request)
        )
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.post("/risk/assess", summary="Risk assessment from supplied market history")
async def assess_custom(
    request: Request,
    body: RiskRequest,
    entity_id: str = Query(default="custom", max_length=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not body.records:
        raise HTTPException(status_code=422, detail="records are required")
    try:
        data = await _gateway().entity_risk(
            "pool", entity_id, body.records, _request_id(request)
        )
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.post("/supply-chain/forecast", summary="Supply chain demand forecast")
async def supply_chain_forecast(
    request: Request,
    body: SupplyChainRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        data = await _gateway().supply_chain_forecast(
            body.records, body.horizon, _request_id(request)
        )
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.post("/transactions/screen", summary="Anomaly and compliance screening")
async def screen_transactions(
    request: Request,
    body: ScreenRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    try:
        data = await _gateway().screen_transactions(
            body.transactions, _request_id(request)
        )
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}


@router.post("/models/train", status_code=202, summary="Start model training")
async def train_models(
    body: TrainRequest,
    current_user: Dict[str, Any] = Depends(require_ml_admin),
):
    try:
        data = await _gateway().train(body.models, body.profile)
    except MLError as exc:
        raise _http(exc)
    return {"success": True, "data": data}
