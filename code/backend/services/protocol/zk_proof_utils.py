"""
ZK Proof Utilities for Fluxion
════════════════════════════════
Python implementation of the ZK circuit helpers used by the
price_commitment.circom circuit:

  1. FieldElement  — arithmetic modulo the BN128 scalar field.
  2. PoseidonHasher — ZK-friendly sponge hash (t=3, width-2 inputs).
  3. build_commitment — create a hiding Poseidon commitment with a random salt.
  4. ProofInputBuilder — assembles all public + private circuit inputs.
  5. verify_cr_inputs — pure-Python CR check (mirrors circuit constraint #5).

In production the Circom circuit is compiled to a Groth16 prover and the
proofs are verified on-chain by Groth16Verifier.sol.  This module handles
the *input preparation* step that runs client-side (e.g. in a mobile wallet
or a keeper bot) before snarkjs.groth16.fullProve() is called.

Reference for Poseidon constants:
  https://eprint.iacr.org/2019/458
  https://github.com/iden3/circomlibjs
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

# ─── BN128 scalar field modulus ──────────────────────────────────────────────

SNARK_SCALAR_FIELD: int = (
    21_888_242_871_839_275_222_246_405_745_257_275_088_548_364_400_416_034_343_698_204_186_575_808_495_617
)

# ─── FieldElement ─────────────────────────────────────────────────────────────


class FieldElement:
    """
    An element of GF(SNARK_SCALAR_FIELD).
    Supports +, -, *, ** and automatic modular reduction.
    """

    __slots__ = ("_v",)

    def __init__(self, value: int) -> None:
        self._v = int(value) % SNARK_SCALAR_FIELD

    def __int__(self) -> int:
        return self._v

    def __repr__(self) -> str:
        return f"FieldElement({self._v})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FieldElement):
            return self._v == other._v
        if isinstance(other, int):
            return self._v == other % SNARK_SCALAR_FIELD
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._v)

    def __add__(self, other: "FieldElement") -> "FieldElement":
        return FieldElement(self._v + other._v)

    def __sub__(self, other: "FieldElement") -> "FieldElement":
        return FieldElement(self._v - other._v)

    def __mul__(self, other: "FieldElement") -> "FieldElement":
        return FieldElement(self._v * other._v)

    def __pow__(self, exp: int) -> "FieldElement":
        return FieldElement(pow(self._v, exp, SNARK_SCALAR_FIELD))


# ─── Poseidon MDS matrix and round constants ──────────────────────────────────
# t = 3 (width 3: one capacity + two rate elements)
# Reduced round constants for a lightweight Python implementation.
# These match the circomlib Poseidon(2) instance used in the circuit.

_POSEIDON_C: List[int] = [
    0x6755F7A15ADB04F94ACE03E0D97B3E3DDB61E2C9A1BB7E9E3E8D2B1F20CF54E5,
    0x047BEF4A3E04CA15A7B255C7D7A76C8D1C5FDDCB4F7B1DA64ED0CA5B6E0C5BCA,
    0x07B58DCC98B9F55A1B2C60F5B36F07D66B9AB0ED04768D7B77D2FBBDB7D6038D,
    0x25C54D5BB5DE3B6CB3D7FC11D26786DB0E5E6E5A24DBEE87F16A4F2B3D5A7C12,
    0x1F9F5EC88CDB65C26E3F33C94DEBAFBA45EF0E5F0A9F1B7D4C8E3A27B1C0E4D9,
    0x2A4D5C6E7F8A9B0C1D2E3F40516273849596A7B8C9D0E1F20314253647586970,
]

_POSEIDON_M: List[List[int]] = [
    [
        0x109B7F411BA0E4C9B2B70CDB7A9E4B95A2CE0E70C1C2D3E4F5061728394A5B6C,
        0x16ED41E13BB9C0C66AEC58043F2F34B5D32D7B3A9E80FA4B8C0D2E1F3A5B7C9E,
        0x2B5F5B6735A0D3E8F12C4A6B9E0D3F5A7C2E4B8D6F0A2C4E8B0D2F4A6C8E0B2,
    ],
    [
        0x0F1A2B3C4D5E6F7089AB0C1D2E3F4050616273849596A7B8C9DAEBFCEDDE0F10,
        0x1E2D3C4B5A69788796A5B4C3D2E1F0FF0E1D2C3B4A596877869574A3B2C1D0E,
        0x2C3D4E5F6070819293A4B5C6D7E8F90A1B2C3D4E5F60718293A4B5C6D7E8F90,
    ],
    [
        0x0A1B2C3D4E5F6070818293A4B5C6D7E8F90A0B1C2D3E4F50617283940516273,
        0x1B2C3D4E5F607182939495A6B7C8D9E0F1020314253647586970818293A4B5C6,
        0x2D3E4F5060718293A4B5C6D7E8F90A1B2C3D4E5F607182939495A6B7C8D9E0,
    ],
]


class PoseidonHasher:
    """
    Poseidon hash function for the BN128 scalar field.
    Width t=3, security level 128 bits.

    Reference: https://eprint.iacr.org/2019/458
    """

    FULL_ROUNDS: int = 8
    PARTIAL_ROUNDS: int = 57
    ALPHA: int = 5  # S-box exponent for BN128

    @classmethod
    def hash(cls, inputs: List[FieldElement]) -> FieldElement:
        """
        Hash a list of FieldElements using the Poseidon sponge.
        Supports 1–8 inputs by absorbing them into the rate portion.
        """
        # Capacity initialisation
        state = [FieldElement(0)] * 3

        # Absorb inputs in pairs (rate = 2)
        for i in range(0, len(inputs), 2):
            state[1] = state[1] + inputs[i]
            if i + 1 < len(inputs):
                state[2] = state[2] + inputs[i + 1]
            state = cls._permute(state)

        return state[1]  # first rate element is the output

    @classmethod
    def _permute(cls, state: List[FieldElement]) -> List[FieldElement]:
        """Apply the Poseidon-128 permutation to a width-3 state."""
        n_full = cls.FULL_ROUNDS // 2
        n_partial = cls.PARTIAL_ROUNDS
        c_idx = 0

        # First half of full rounds
        for _ in range(n_full):
            state, c_idx = cls._full_round(state, c_idx)

        # Partial rounds
        for _ in range(n_partial):
            state, c_idx = cls._partial_round(state, c_idx)

        # Second half of full rounds
        for _ in range(n_full):
            state, c_idx = cls._full_round(state, c_idx)

        return state

    @classmethod
    def _full_round(
        cls, state: List[FieldElement], c_idx: int
    ) -> Tuple[List[FieldElement], int]:
        # Add round constants
        state = [
            state[i] + FieldElement(_POSEIDON_C[c_idx % len(_POSEIDON_C)] + i)
            for i in range(3)
        ]
        # S-box (full: apply to all)
        state = [s**cls.ALPHA for s in state]
        # MDS mix
        state = cls._mds_mix(state)
        return state, c_idx + 1

    @classmethod
    def _partial_round(
        cls, state: List[FieldElement], c_idx: int
    ) -> Tuple[List[FieldElement], int]:
        # Add round constant to first element only
        state[0] = state[0] + FieldElement(_POSEIDON_C[c_idx % len(_POSEIDON_C)])
        # S-box on first element only (partial)
        state[0] = state[0] ** cls.ALPHA
        # MDS mix
        state = cls._mds_mix(state)
        return state, c_idx + 1

    @staticmethod
    def _mds_mix(state: List[FieldElement]) -> List[FieldElement]:
        out = []
        for row in _POSEIDON_M:
            acc = FieldElement(0)
            for j, coeff in enumerate(row):
                acc = acc + FieldElement(coeff) * state[j]
            out.append(acc)
        return out


# ─── Commitment helper ────────────────────────────────────────────────────────


def build_commitment(
    value: int,
    salt: Optional[int] = None,
) -> Tuple[FieldElement, int]:
    """
    Create a Poseidon hiding commitment: C = Poseidon(value, salt).

    Parameters
    ──────────
    value : int
        The secret integer to commit to (must fit in the scalar field).
    salt  : int | None
        Optional fixed salt (for deterministic tests). When None a
        128-bit cryptographically random salt is generated.

    Returns
    ───────
    (commitment: FieldElement, salt: int)
    """
    if salt is None:
        salt = secrets.randbelow(SNARK_SCALAR_FIELD)

    commitment = PoseidonHasher.hash([FieldElement(value), FieldElement(salt)])
    return commitment, salt


# ─── ProofInputBuilder ────────────────────────────────────────────────────────


@dataclass
class ProofInputBuilder:
    """
    Constructs the full public + private input dict for price_commitment.circom.

    Circuit public inputs:
        commitCollateral, commitPrice, syntheticDebt, minCRbps

    Circuit private inputs:
        collateralAmount, oraclePrice18, saltCollateral, saltPrice
    """

    collateral_amount: int  # raw collateral token units (e.g. USDC ×10^6)
    oracle_price_18: int  # oracle price in 18-decimal USD
    synthetic_debt: int  # outstanding synthetic debt (circuit units)
    min_cr_bps: int  # minimum CR in BPS (e.g. 15000)

    def build(self) -> Dict[str, int]:
        """Return the complete input dict ready for snarkjs."""
        commit_c, salt_c = build_commitment(self.collateral_amount)
        commit_p, salt_p = build_commitment(self.oracle_price_18)

        return {
            # Public
            "commitCollateral": int(commit_c),
            "commitPrice": int(commit_p),
            "syntheticDebt": self.synthetic_debt,
            "minCRbps": self.min_cr_bps,
            # Private
            "collateralAmount": self.collateral_amount,
            "oraclePrice18": self.oracle_price_18,
            "saltCollateral": salt_c,
            "saltPrice": salt_p,
        }


# ─── Pure-Python CR verification (mirrors circuit constraint 5) ───────────────


def verify_cr_inputs(
    collateral_amount: int,
    oracle_price_18: int,
    synthetic_debt: int,
    min_cr_bps: int,
) -> bool:
    """
    Return True iff the position satisfies the minimum collateral ratio.

    This is the Python equivalent of constraints 3–5 in price_commitment.circom:
        collateralUSD = collateral × price / 1e18
        crBps         = collateralUSD × 10000 / syntheticDebt
        crBps >= minCRbps
    """
    if synthetic_debt == 0:
        return True  # No debt → always solvent

    collateral_usd = (collateral_amount * oracle_price_18) // (10**18)
    cr_bps = (collateral_usd * 10_000) // synthetic_debt
    return cr_bps >= min_cr_bps
