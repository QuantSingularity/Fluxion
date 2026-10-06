"""
Market data routes for Fluxion Backend.

Exposes read endpoints for liquidity pools, synthetic assets, and tradable
assets. These power the web and mobile frontends (pools/synthetics/assets
screens). The underlying domain models already exist in models/blockchain.py
(LiquidityPool, SyntheticAsset); these routes provide the HTTP surface the
frontends were written against.

The handlers return representative data from an in-memory snapshot so the
integrated stack works end to end without a populated database. Swap
``_POOLS`` / ``_SYNTHETICS`` for real queries against the LiquidityPool /
SyntheticAsset tables when the persistence layer is wired up.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from services.market.market_data import POOLS, SYNTHETICS

router = APIRouter()


_POOLS = POOLS
_SYNTHETICS = SYNTHETICS


def _paginate(
    items: List[Dict[str, Any]], limit: int, offset: int
) -> List[Dict[str, Any]]:
    return items[offset : offset + limit]


def _search(items: List[Dict[str, Any]], q: Optional[str]) -> List[Dict[str, Any]]:
    if not q:
        return items
    ql = q.lower()
    return [
        i
        for i in items
        if ql in str(i.get("name", "")).lower()
        or ql in str(i.get("symbol", "")).lower()
        or ql in str(i.get("pair", "")).lower()
        or ql in str(i.get("id", "")).lower()
    ]


# ── Pools ────────────────────────────────────────────────────────────────────


@router.get("/pools", summary="List liquidity pools")
async def list_pools(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
):
    pools = _search(_POOLS, search)
    return {
        "success": True,
        "data": _paginate(pools, limit, offset),
        "total": len(pools),
    }


@router.get("/pools/{pool_id}", summary="Get a pool by ID")
async def get_pool(pool_id: str):
    for p in _POOLS:
        if p["id"] == pool_id:
            return {"success": True, "data": p}
    raise HTTPException(status_code=404, detail="Pool not found")


# ── Synthetic assets ─────────────────────────────────────────────────────────


@router.get("/synthetics", summary="List synthetic assets")
async def list_synthetics(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
):
    synths = _search(_SYNTHETICS, search)
    return {
        "success": True,
        "data": _paginate(synths, limit, offset),
        "total": len(synths),
    }


@router.get("/synthetics/{asset_id}", summary="Get a synthetic asset by ID")
async def get_synthetic(asset_id: str):
    for s in _SYNTHETICS:
        if s["id"] == asset_id or s["symbol"].lower() == asset_id.lower():
            return {"success": True, "data": s}
    raise HTTPException(status_code=404, detail="Synthetic asset not found")


# ── Assets (alias used by the mobile app) ────────────────────────────────────


@router.get("/assets", summary="List tradable assets")
async def list_assets(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None),
):
    # Mobile's Assets screen consumes the synthetic-asset catalogue.
    assets = _search(_SYNTHETICS, search)
    return {
        "success": True,
        "data": _paginate(assets, limit, offset),
        "total": len(assets),
    }


@router.get("/assets/{asset_id}", summary="Get an asset by ID")
async def get_asset(asset_id: str):
    for s in _SYNTHETICS:
        if s["id"] == asset_id or s["symbol"].lower() == asset_id.lower():
            return {"success": True, "data": s}
    raise HTTPException(status_code=404, detail="Asset not found")
