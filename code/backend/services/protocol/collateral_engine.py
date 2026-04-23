"""
CollateralEngine
════════════════
Pure-Python implementation of the Fluxion synthetic-asset collateralisation
rules, mirroring the logic in SyntheticAssetFactory.sol.

This module is the authoritative back-end source of truth used by:
  • The risk-management service (real-time CR monitoring)
  • The liquidation keeper daemon (identifies liquidatable positions)
  • Unit tests (test_collateralization.py)
  • The API /risk and /portfolio endpoints

All financial arithmetic uses Python float (IEEE-754 double); for on-chain
amounts the Solidity contract uses uint256 with 18-decimal fixed-point.
The Python service keeps values as floats scaled to human-readable units
(e.g. USD, token units) and converts to wei-scale only when building txs.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# ─── Protocol constants (must match SyntheticAssetFactory.sol) ───────────────

BPS: int = 10_000  # Basis-point denominator
MIN_CR_BPS: int = 15_000  # 150 % minimum collateral ratio
LIQ_CR_BPS: int = 12_000  # 120 % liquidation threshold
LIQ_CR_HARD: int = 11_000  # 110 % hard-zone threshold
LIQ_CR_CRIT: int = 10_000  # 100 % critical-zone threshold

LIQ_BONUS_SOFT: int = 500  # 5 %
LIQ_BONUS_HARD: int = 800  # 8 %
LIQ_BONUS_CRIT: int = 1_000  # 10 %

STABILITY_FEE_BPS: int = 200  # 2 % annual stability fee
SECONDS_PER_YEAR: float = 365 * 24 * 3600

MAX_LIQUIDATION_RATIO: float = 0.50  # max 50 % of debt per liquidation call
ORACLE_STALENESS: float = 3_600.0  # 1 hour in seconds


# ─── Exceptions ───────────────────────────────────────────────────────────────


class CollateralEngineError(Exception):
    """Base class for collateral engine errors."""


class InsufficientCollateralError(CollateralEngineError):
    """Raised when a mint would result in CR < MIN_CR."""


class PriceStaleError(CollateralEngineError):
    """Raised when the stored oracle price is older than ORACLE_STALENESS."""


class PositionNotFoundError(CollateralEngineError):
    """Raised when accessing a position that does not exist."""


# ─── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class CollateralPosition:
    asset_id: str
    user_address: str
    collateral_deposited: float  # collateral token units
    synthetic_minted: float  # synthetic token units
    fee_timestamp: float  # unix timestamp of last stability-fee accrual


@dataclass
class LiquidationResult:
    asset_id: str
    user_address: str
    liquidator: str
    debt_repaid: float
    collateral_seized: float
    bonus_bps: int
    tier: str


@dataclass
class BurnResult:
    asset_id: str
    user_address: str
    synthetic_burned: float
    collateral_returned: float


# ─── CollateralEngine ─────────────────────────────────────────────────────────


class CollateralEngine:
    """
    In-memory collateral engine.

    In production the canonical state lives on-chain; this class is used by
    off-chain services that read on-chain events and maintain a local replica
    for fast queries and liquidation-candidate screening.
    """

    def __init__(self) -> None:
        # (asset_id, user_address) → CollateralPosition
        self._positions: Dict[Tuple[str, str], CollateralPosition] = {}
        # asset_id → oracle price (USD per 1 collateral token, float)
        self._prices: Dict[str, float] = {}
        # asset_id → unix timestamp of last price update
        self._price_timestamps: Dict[str, float] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Oracle
    # ──────────────────────────────────────────────────────────────────────────

    def update_price(
        self,
        asset_id: str,
        price: float,
        updated_at: Optional[float] = None,
    ) -> None:
        """Store a new oracle price for an asset."""
        if price <= 0:
            raise ValueError(f"Oracle price must be > 0, got {price}")
        self._prices[asset_id] = price
        self._price_timestamps[asset_id] = (
            updated_at if updated_at is not None else time.time()
        )

    def get_price(self, asset_id: str) -> float:
        """Return the current oracle price, raising if absent."""
        if asset_id not in self._prices:
            raise PriceStaleError(f"No price recorded for asset {asset_id}")
        return self._prices[asset_id]

    def _assert_price_fresh(self, asset_id: str) -> None:
        """Raise PriceStaleError when the price is older than ORACLE_STALENESS."""
        if asset_id not in self._price_timestamps:
            raise PriceStaleError(f"No price for {asset_id}")
        age = time.time() - self._price_timestamps[asset_id]
        if age > ORACLE_STALENESS:
            raise PriceStaleError(
                f"Oracle price for {asset_id} is {age:.0f}s old "
                f"(max {ORACLE_STALENESS}s)"
            )

    # ──────────────────────────────────────────────────────────────────────────
    # Collateral ratio
    # ──────────────────────────────────────────────────────────────────────────

    def get_collateral_ratio(self, asset_id: str, user: str) -> float:
        """
        Return the collateral ratio in BPS.
        Returns math.inf when no debt is outstanding.
        """
        key = (asset_id, user)
        if key not in self._positions:
            return math.inf
        pos = self._positions[key]
        if pos.synthetic_minted == 0:
            return math.inf

        price = self._prices.get(asset_id, 0.0)
        collateral_usd = pos.collateral_deposited * price
        return (collateral_usd / pos.synthetic_minted) * BPS

    def is_liquidatable(self, asset_id: str, user: str) -> bool:
        cr = self.get_collateral_ratio(asset_id, user)
        return 0 < cr < LIQ_CR_BPS

    # ──────────────────────────────────────────────────────────────────────────
    # Mint
    # ──────────────────────────────────────────────────────────────────────────

    def mint(
        self,
        asset_id: str,
        user: str,
        collateral: float,
        synthetic: float,
    ) -> CollateralPosition:
        """
        Deposit collateral and mint synthetic tokens.

        Raises
        ──────
        PriceStaleError            — oracle price too old.
        InsufficientCollateralError — resulting CR < MIN_CR.
        ValueError                 — zero amounts.
        """
        if collateral <= 0:
            raise ValueError("collateral must be > 0")
        if synthetic <= 0:
            raise ValueError("synthetic must be > 0")

        self._assert_price_fresh(asset_id)
        self._accrue_stability_fee(asset_id, user)

        key = (asset_id, user)
        if key not in self._positions:
            self._positions[key] = CollateralPosition(
                asset_id=asset_id,
                user_address=user,
                collateral_deposited=0.0,
                synthetic_minted=0.0,
                fee_timestamp=time.time(),
            )

        pos = self._positions[key]
        pos.collateral_deposited += collateral
        pos.synthetic_minted += synthetic
        pos.fee_timestamp = time.time()

        cr = self.get_collateral_ratio(asset_id, user)
        if cr < MIN_CR_BPS:
            # Rollback
            pos.collateral_deposited -= collateral
            pos.synthetic_minted -= synthetic
            raise InsufficientCollateralError(
                f"CR {cr:.0f} bps < MIN_CR {MIN_CR_BPS} bps — "
                f"deposit more collateral or mint fewer tokens"
            )
        return pos

    # ──────────────────────────────────────────────────────────────────────────
    # Burn
    # ──────────────────────────────────────────────────────────────────────────

    def burn(
        self,
        asset_id: str,
        user: str,
        synthetic_amount: float,
    ) -> BurnResult:
        """
        Burn synthetic tokens and return proportional collateral.

        Raises
        ──────
        PositionNotFoundError — position does not exist.
        ValueError            — burn exceeds minted amount.
        """
        key = (asset_id, user)
        if key not in self._positions:
            raise PositionNotFoundError(f"No position for {user} in {asset_id}")

        self._accrue_stability_fee(asset_id, user)
        pos = self._positions[key]

        if synthetic_amount > pos.synthetic_minted + 1e-9:
            raise ValueError(
                f"Burn amount {synthetic_amount} exceeds minted {pos.synthetic_minted}"
            )
        synthetic_amount = min(synthetic_amount, pos.synthetic_minted)

        if pos.synthetic_minted == 0:
            collateral_return = 0.0
        else:
            collateral_return = (
                pos.collateral_deposited * synthetic_amount
            ) / pos.synthetic_minted

        pos.collateral_deposited -= collateral_return
        pos.synthetic_minted -= synthetic_amount

        return BurnResult(
            asset_id=asset_id,
            user_address=user,
            synthetic_burned=synthetic_amount,
            collateral_returned=collateral_return,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Liquidate
    # ──────────────────────────────────────────────────────────────────────────

    def liquidate(
        self,
        asset_id: str,
        user: str,
        liquidator: str,
        debt_repaid: float,
    ) -> LiquidationResult:
        """
        Liquidate an undercollateralised position.

        Raises
        ──────
        PriceStaleError       — oracle price too old.
        ValueError            — position healthy, or debt_repaid > 50 % cap.
        PositionNotFoundError — position not found.
        """
        self._assert_price_fresh(asset_id)

        key = (asset_id, user)
        if key not in self._positions:
            raise PositionNotFoundError(f"No position for {user} in {asset_id}")

        if not self.is_liquidatable(asset_id, user):
            raise ValueError(
                f"Position {user}/{asset_id} is healthy (not liquidatable)"
            )

        pos = self._positions[key]
        max_repay = pos.synthetic_minted * MAX_LIQUIDATION_RATIO
        if debt_repaid > max_repay + 1e-9:
            raise ValueError(
                f"debt_repaid {debt_repaid} exceeds 50 % cap {max_repay:.4f}"
            )
        debt_repaid = min(debt_repaid, pos.synthetic_minted)

        # Determine bonus tier
        cr = self.get_collateral_ratio(asset_id, user)
        bonus_bps, tier = self._liquidation_bonus(cr)

        # Proportional collateral + bonus
        raw_share = (pos.collateral_deposited * debt_repaid) / pos.synthetic_minted
        bonus_amt = (raw_share * bonus_bps) / BPS
        seize = raw_share + bonus_amt

        # Cap at available collateral (bad-debt handling)
        if seize > pos.collateral_deposited:
            seize = pos.collateral_deposited

        pos.collateral_deposited -= seize
        pos.synthetic_minted -= debt_repaid

        return LiquidationResult(
            asset_id=asset_id,
            user_address=user,
            liquidator=liquidator,
            debt_repaid=debt_repaid,
            collateral_seized=seize,
            bonus_bps=bonus_bps,
            tier=tier,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Position query
    # ──────────────────────────────────────────────────────────────────────────

    def get_position(self, asset_id: str, user: str) -> CollateralPosition:
        key = (asset_id, user)
        if key not in self._positions:
            # Return an empty position rather than raising for convenience
            return CollateralPosition(
                asset_id=asset_id,
                user_address=user,
                collateral_deposited=0.0,
                synthetic_minted=0.0,
                fee_timestamp=time.time(),
            )
        return self._positions[key]

    def all_positions(self) -> list[CollateralPosition]:
        return list(self._positions.values())

    def liquidatable_positions(self) -> list[CollateralPosition]:
        return [
            pos
            for pos in self._positions.values()
            if self.is_liquidatable(pos.asset_id, pos.user_address)
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _accrue_stability_fee(self, asset_id: str, user: str) -> None:
        """Deduct the pro-rated stability fee from the position's collateral."""
        key = (asset_id, user)
        if key not in self._positions:
            return
        pos = self._positions[key]
        if pos.synthetic_minted == 0:
            pos.fee_timestamp = time.time()
            return

        elapsed = time.time() - pos.fee_timestamp
        if elapsed <= 0:
            return

        fee = (pos.collateral_deposited * STABILITY_FEE_BPS * elapsed) / (
            BPS * SECONDS_PER_YEAR
        )
        fee = min(fee, pos.collateral_deposited)
        pos.collateral_deposited -= fee
        pos.fee_timestamp = time.time()

    @staticmethod
    def _liquidation_bonus(cr_bps: float) -> Tuple[int, str]:
        """Return (bonus_bps, tier_label) based on the collateral ratio."""
        if cr_bps < LIQ_CR_CRIT:
            return (LIQ_BONUS_CRIT, "CRITICAL")
        elif cr_bps < LIQ_CR_HARD:
            return (LIQ_BONUS_HARD, "HARD")
        else:
            return (LIQ_BONUS_SOFT, "SOFT")
