"""
Unit tests for Fluxion ZK proof utilities.
Tests the Python-side Poseidon hashing and Groth16 proof
input construction that feeds the price_commitment.circom circuit.
"""

from __future__ import annotations

import os
import sys


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.protocol.zk_proof_utils import (
    SNARK_SCALAR_FIELD,
    FieldElement,
    PoseidonHasher,
    ProofInputBuilder,
    build_commitment,
    verify_cr_inputs,
)

# ─── FieldElement ─────────────────────────────────────────────────────────────


class TestFieldElement:
    def test_from_int_in_field(self):
        fe = FieldElement(12345)
        assert int(fe) == 12345

    def test_from_int_wraps_modulo_field(self):
        fe = FieldElement(SNARK_SCALAR_FIELD + 7)
        assert int(fe) == 7

    def test_zero(self):
        fe = FieldElement(0)
        assert int(fe) == 0

    def test_equality(self):
        assert FieldElement(42) == FieldElement(42)
        assert FieldElement(42) != FieldElement(43)

    def test_add(self):
        a = FieldElement(SNARK_SCALAR_FIELD - 1)
        b = FieldElement(2)
        assert int(a + b) == 1  # wraps around

    def test_mul(self):
        a = FieldElement(3)
        b = FieldElement(7)
        assert int(a * b) == 21

    def test_mul_wraps(self):
        a = FieldElement(SNARK_SCALAR_FIELD - 1)
        b = FieldElement(2)
        result = int(a * b)
        assert result == (2 * (SNARK_SCALAR_FIELD - 1)) % SNARK_SCALAR_FIELD


# ─── PoseidonHasher ──────────────────────────────────────────────────────────


class TestPoseidonHasher:
    def test_hash_returns_field_element(self):
        h = PoseidonHasher.hash([FieldElement(1), FieldElement(2)])
        assert isinstance(h, FieldElement)
        assert 0 <= int(h) < SNARK_SCALAR_FIELD

    def test_deterministic(self):
        inputs = [FieldElement(100), FieldElement(999)]
        h1 = PoseidonHasher.hash(inputs)
        h2 = PoseidonHasher.hash(inputs)
        assert h1 == h2

    def test_different_inputs_different_hash(self):
        h1 = PoseidonHasher.hash([FieldElement(1), FieldElement(2)])
        h2 = PoseidonHasher.hash([FieldElement(1), FieldElement(3)])
        assert h1 != h2

    def test_salt_changes_hash(self):
        val = FieldElement(500_000)
        h1 = PoseidonHasher.hash([val, FieldElement(111)])
        h2 = PoseidonHasher.hash([val, FieldElement(222)])
        assert h1 != h2

    def test_single_input(self):
        h = PoseidonHasher.hash([FieldElement(42)])
        assert isinstance(h, FieldElement)

    def test_many_inputs(self):
        inputs = [FieldElement(i) for i in range(8)]
        h = PoseidonHasher.hash(inputs)
        assert isinstance(h, FieldElement)


# ─── build_commitment ────────────────────────────────────────────────────────


class TestBuildCommitment:
    def test_returns_tuple_of_hash_and_salt(self):
        commitment, salt = build_commitment(1_000_000)
        assert isinstance(commitment, FieldElement)
        assert isinstance(salt, int)
        assert 0 <= salt < SNARK_SCALAR_FIELD

    def test_different_calls_different_salt(self):
        _, salt1 = build_commitment(1_000_000)
        _, salt2 = build_commitment(1_000_000)
        # Very unlikely to collide with a 128-bit random salt
        assert salt1 != salt2

    def test_same_value_same_salt_same_commitment(self):
        fixed_salt = 42
        c1, _ = build_commitment(1_000_000, salt=fixed_salt)
        c2, _ = build_commitment(1_000_000, salt=fixed_salt)
        assert c1 == c2

    def test_zero_value(self):
        c, _ = build_commitment(0)
        assert isinstance(c, FieldElement)

    def test_large_value(self):
        large = 10**18  # 1e18 (like 1 ETH in wei)
        c, _ = build_commitment(large)
        assert isinstance(c, FieldElement)


# ─── ProofInputBuilder ───────────────────────────────────────────────────────


class TestProofInputBuilder:
    def _builder(
        self,
        collateral: float = 1500.0,
        price_18: int = 1_000_000_000_000_000_000,  # 1.0 USD with 18 dec
        debt: int = 1000,
        min_cr: int = 15_000,
    ) -> ProofInputBuilder:
        return ProofInputBuilder(
            collateral_amount=int(collateral * 1_000_000),  # USDC 6-dec
            oracle_price_18=price_18,
            synthetic_debt=debt,
            min_cr_bps=min_cr,
        )

    def test_build_returns_dict(self):
        b = self._builder()
        inp = b.build()
        assert isinstance(inp, dict)

    def test_public_inputs_present(self):
        b = self._builder()
        inp = b.build()
        for key in ("commitCollateral", "commitPrice", "syntheticDebt", "minCRbps"):
            assert key in inp, f"Missing public input: {key}"

    def test_private_inputs_present(self):
        b = self._builder()
        inp = b.build()
        for key in ("collateralAmount", "oraclePrice18", "saltCollateral", "saltPrice"):
            assert key in inp, f"Missing private input: {key}"

    def test_commitment_verifiable(self):
        """Public commitment must match Poseidon(value, salt)."""
        b = self._builder()
        inp = b.build()
        recomputed = PoseidonHasher.hash(
            [
                FieldElement(inp["collateralAmount"]),
                FieldElement(inp["saltCollateral"]),
            ]
        )
        assert int(recomputed) == inp["commitCollateral"]

    def test_price_commitment_verifiable(self):
        b = self._builder()
        inp = b.build()
        recomputed = PoseidonHasher.hash(
            [
                FieldElement(inp["oraclePrice18"]),
                FieldElement(inp["saltPrice"]),
            ]
        )
        assert int(recomputed) == inp["commitPrice"]

    def test_all_values_in_field(self):
        b = self._builder()
        inp = b.build()
        for k, v in inp.items():
            assert isinstance(v, int), f"{k} is not an int"
            assert 0 <= v < SNARK_SCALAR_FIELD, f"{k}={v} out of field"


# ─── verify_cr_inputs ────────────────────────────────────────────────────────


class TestVerifyCRInputs:
    def test_healthy_position_passes(self):
        # collateral = 1500 USDC (6-dec = 1_500_000_000), price = 1 USD (18 dec)
        # collateralUSD = 1_500_000_000 × 1e18 / 1e18 = 1_500_000_000
        # debt = 1000 USDC-scale = 1_000_000_000
        # CR = 1_500_000_000 / 1_000_000_000 × 10000 = 15 000 bps → passes
        assert verify_cr_inputs(
            collateral_amount=1_500_000_000,  # 1500 ×10^6
            oracle_price_18=1_000_000_000_000_000_000,  # 1 USD ×10^18
            synthetic_debt=1_000_000_000,  # 1000 ×10^6 (same scale)
            min_cr_bps=15_000,
        )

    def test_undercollateralised_fails(self):
        # collateral = 1100 ×10^6, price = 1 USD ×10^18, debt = 1000 ×10^6
        # CR = 1100 / 1000 × 10000 = 11 000 bps < 15 000 → fails
        assert not verify_cr_inputs(
            collateral_amount=1_100_000_000,
            oracle_price_18=1_000_000_000_000_000_000,
            synthetic_debt=1_000_000_000,
            min_cr_bps=15_000,
        )

    def test_exactly_at_min_cr_passes(self):
        # CR = 1500 / 1000 × 10000 = 15 000 bps — boundary should pass
        assert verify_cr_inputs(
            collateral_amount=1_500_000_000,
            oracle_price_18=1_000_000_000_000_000_000,
            synthetic_debt=1_000_000_000,
            min_cr_bps=15_000,
        )

    def test_zero_debt_always_passes(self):
        assert verify_cr_inputs(
            collateral_amount=1_000,
            oracle_price_18=1_000_000_000_000_000_000,
            synthetic_debt=0,
            min_cr_bps=15_000,
        )
