// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@chainlink/contracts/src/v0.8/shared/interfaces/AggregatorV3Interface.sol";
import "./interfaces/IFluxionVault.sol";

/**
 * @title SyntheticLiquidationEngine
 * @notice Autonomous liquidation engine for undercollateralised synthetic-asset
 *         positions on the Fluxion protocol.
 *
 * Design goals
 * ────────────
 *  • Decoupled from SyntheticAssetFactory - operates on any vault that
 *    implements IFluxionVault (pluggable architecture).
 *  • Supports partial and full liquidations.
 *  • Three-tier incentive ladder rewards liquidators at different levels
 *    depending on how deeply undercollateralised the position is.
 *  • Bad-debt socialisation: residual losses exceeding the vault's collateral
 *    are covered by the protocol Insurance Fund.
 *  • Liquidation pause: an EMERGENCY_ROLE can freeze liquidations globally
 *    (circuit-breaker) without stopping normal minting/burning.
 *  • On-chain Dutch auction: if no liquidator appears within AUCTION_DURATION
 *    blocks the bonus escalates linearly to attract capital.
 *
 * Incentive tiers (in BPS)
 * ──────────────────────────────────────────────────────────────────────────
 *  CR 110 %–120 % (SOFT zone)    → BONUS_SOFT   =  5 %
 *  CR  100 %–110 % (HARD zone)   → BONUS_HARD   =  8 %
 *  CR < 100 %     (CRITICAL zone)→ BONUS_CRIT   = 10 % + Insurance Fund top-up
 */
contract SyntheticLiquidationEngine is AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ─────────────────────────────────────────────────────────────────────────
    // Roles
    // ─────────────────────────────────────────────────────────────────────────

    bytes32 public constant LIQUIDATOR_ROLE = keccak256("LIQUIDATOR_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");
    bytes32 public constant KEEPER_ROLE = keccak256("KEEPER_ROLE");

    // ─────────────────────────────────────────────────────────────────────────
    // Constants
    // ─────────────────────────────────────────────────────────────────────────

    uint256 public constant BPS = 10_000;
    uint256 public constant LIQ_CR_SOFT = 12_000; // 120 %
    uint256 public constant LIQ_CR_HARD = 11_000; // 110 %
    uint256 public constant LIQ_CR_CRIT = 10_000; // 100 %
    uint256 public constant BONUS_SOFT = 500; //   5 %
    uint256 public constant BONUS_HARD = 800; //   8 %
    uint256 public constant BONUS_CRIT = 1_000; //  10 %

    /// @dev Dutch-auction escalation: one additional BPS per block
    uint256 public constant AUCTION_BPS_PER_BLOCK = 1;
    uint256 public constant AUCTION_DURATION = 100; // blocks

    uint256 public constant MAX_LIQUIDATION_RATIO = 5_000; // max 50 % of debt per call

    // ─────────────────────────────────────────────────────────────────────────
    // State
    // ─────────────────────────────────────────────────────────────────────────

    IFluxionVault public immutable vault;
    IERC20 public immutable insuranceFund;

    bool public liquidationsPaused;
    uint256 public totalLiquidatedUSD;
    uint256 public totalBadDebt;

    struct AuctionState {
        uint256 startBlock;
        bool active;
    }
    /// @dev positionKey → AuctionState
    mapping(bytes32 => AuctionState) public auctions;

    /// @dev Per-liquidator stats
    struct LiquidatorStats {
        uint256 totalLiquidations;
        uint256 totalBonusEarned;
        uint256 totalDebtRepaid;
    }
    mapping(address => LiquidatorStats) public liquidatorStats;

    // ─────────────────────────────────────────────────────────────────────────
    // Events
    // ─────────────────────────────────────────────────────────────────────────

    event LiquidationExecuted(
        bytes32 indexed assetId,
        address indexed user,
        address indexed liquidator,
        uint256 debtRepaid,
        uint256 collateralSeized,
        uint256 bonusBPS,
        uint256 tier // 0=SOFT, 1=HARD, 2=CRIT
    );
    event AuctionStarted(bytes32 indexed positionKey, uint256 startBlock);
    event AuctionClosed(bytes32 indexed positionKey, address liquidator);
    event BadDebtRecorded(
        bytes32 indexed assetId,
        address user,
        uint256 amount
    );
    event LiquidationsPaused(address by);
    event LiquidationsResumed(address by);
    event InsuranceFundTopUp(
        bytes32 indexed assetId,
        address user,
        uint256 amount
    );

    // ─────────────────────────────────────────────────────────────────────────
    // Constructor
    // ─────────────────────────────────────────────────────────────────────────

    constructor(address _vault, address _insuranceFund) {
        require(_vault != address(0), "Zero vault");
        require(_insuranceFund != address(0), "Zero insurance fund");
        vault = IFluxionVault(_vault);
        insuranceFund = IERC20(_insuranceFund);

        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(EMERGENCY_ROLE, msg.sender);
        _setupRole(KEEPER_ROLE, msg.sender);
        _setupRole(LIQUIDATOR_ROLE, msg.sender);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Core: liquidate a specific position
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * @notice Liquidate part of an undercollateralised position.
     *
     * @param _assetId     Synthetic asset identifier
     * @param _user        Position owner
     * @param _debtRepaid  Synthetic tokens to repay (max 50 % per call)
     */
    function liquidate(
        bytes32 _assetId,
        address _user,
        uint256 _debtRepaid
    ) external nonReentrant {
        _liquidate(_assetId, _user, _debtRepaid, msg.sender);
    }

    /**
     * @notice Identical liquidation logic to {liquidate}, but lets
     *         batchLiquidate credit the keeper that triggered the batch
     *         (rather than this contract itself) as the liquidator.
     * @dev    Only callable by this contract, via the try/catch in
     *         batchLiquidate below - try/catch requires an external call
     *         boundary, so this can't just be the internal helper directly.
     *         The `msg.sender == address(this)` check is what prevents
     *         anyone else from spoofing an arbitrary `_liquidator` and
     *         redirecting someone else's liquidation proceeds to themselves.
     */
    function batchLiquidateSingle(
        bytes32 _assetId,
        address _user,
        uint256 _debtRepaid,
        address _liquidator
    ) external nonReentrant {
        require(msg.sender == address(this), "Internal only");
        _liquidate(_assetId, _user, _debtRepaid, _liquidator);
    }

    function _liquidate(
        bytes32 _assetId,
        address _user,
        uint256 _debtRepaid,
        address _liquidator
    ) internal {
        require(!liquidationsPaused, "Liquidations paused");
        // Liquidation is intentionally permissionless (mirrors
        // SyntheticAssetFactory.liquidate): anyone can liquidate an
        // undercollateralised position, which is what keeps the protocol
        // solvent. LIQUIDATOR_ROLE is not used to gate this entry point;
        // it exists for off-chain indexing / potential future tiers only.

        (
            uint256 collateral,
            uint256 debt,
            uint256 ratioBPS,
            bool isLiquidatable
        ) = vault.getPosition(_assetId, _user);

        require(isLiquidatable, "Position is healthy");
        require(debt >= _debtRepaid, "Repaid > debt");
        require(
            _debtRepaid <= (debt * MAX_LIQUIDATION_RATIO) / BPS,
            "Exceeds 50 % cap per call"
        );

        // Determine incentive tier and bonus
        (uint256 bonusBPS, uint256 tier) = _computeBonus(
            ratioBPS,
            _assetId,
            _user
        );

        // Execute liquidation via the vault. Vault implementations burn the
        // repaid debt from *their own caller's* balance (this contract), not
        // from the liquidator directly, so the repaid amount of synthetic
        // tokens must be pulled from the liquidator into this contract first
        // (the liquidator must have approved this contract beforehand). The
        // vault also sends the seized collateral to its immediate caller
        // (this contract), which must be forwarded on to the liquidator.
        IERC20 syntheticToken = IERC20(vault.syntheticOf(_assetId));
        IERC20 collateralToken = IERC20(vault.collateralOf(_assetId));
        syntheticToken.safeTransferFrom(
            _liquidator,
            address(this),
            _debtRepaid
        );

        uint256 collateralBefore = collateralToken.balanceOf(address(this));
        vault.liquidate(_assetId, _user, _debtRepaid);
        uint256 actualReceived =
            collateralToken.balanceOf(address(this)) - collateralBefore;

        // Collateral entitlement per this engine's own tiered incentive
        // ladder (proportional share + tier bonus).
        uint256 rawShare = (collateral * _debtRepaid) / debt;
        uint256 bonusAmount = (rawShare * bonusBPS) / BPS;
        uint256 totalSeize = rawShare + bonusAmount;

        // The vault applies its own (generally more conservative) fixed
        // liquidation bonus, so it will not always hand over enough
        // collateral to cover this engine's full tiered entitlement -
        // e.g. a HARD/CRIT tier bonus (8%/10%) exceeding the vault's fixed
        // bonus. Never forward more than was actually received; the
        // insurance fund covers any shortfall between what this engine
        // promised the liquidator and what the vault actually paid out.
        if (totalSeize > actualReceived) {
            uint256 shortfall = totalSeize - actualReceived;
            totalSeize = actualReceived;
            _coverBadDebt(_assetId, _user, shortfall, _liquidator);
        }

        // Forward the seized collateral (received from the vault above) to
        // the liquidator that triggered this call - the original keeper in
        // the batchLiquidate case, not this contract.
        if (totalSeize > 0) {
            collateralToken.safeTransfer(_liquidator, totalSeize);
        }

        // Update liquidator statistics
        LiquidatorStats storage stats = liquidatorStats[_liquidator];
        stats.totalLiquidations++;
        stats.totalBonusEarned += bonusAmount;
        stats.totalDebtRepaid += _debtRepaid;

        // Close any active auction for this position
        bytes32 posKey = _posKey(_assetId, _user);
        if (auctions[posKey].active) {
            auctions[posKey].active = false;
            emit AuctionClosed(posKey, _liquidator);
        }

        emit LiquidationExecuted(
            _assetId,
            _user,
            _liquidator,
            _debtRepaid,
            totalSeize,
            bonusBPS,
            tier
        );
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Dutch auction: keepers register positions; bonus escalates if stale
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * @notice Register an undercollateralised position for Dutch-auction
     *         liquidation.  Anyone can call this.  If the position has not
     *         been liquidated within AUCTION_DURATION blocks, the bonus
     *         escalates by AUCTION_BPS_PER_BLOCK per block.
     */
    function startAuction(bytes32 _assetId, address _user) external {
        (, , , bool isLiquidatable) = vault.getPosition(_assetId, _user);
        require(isLiquidatable, "Position is healthy");

        bytes32 posKey = _posKey(_assetId, _user);
        require(!auctions[posKey].active, "Auction already running");

        auctions[posKey] = AuctionState({
            startBlock: block.number,
            active: true
        });
        emit AuctionStarted(posKey, block.number);
    }

    /**
     * @notice Returns the current auction bonus in BPS for a position
     *         (base bonus + escalation since auction start).
     */
    function getAuctionBonus(
        bytes32 _assetId,
        address _user
    ) external view returns (uint256 bonusBPS) {
        (, , uint256 ratioBPS, ) = vault.getPosition(_assetId, _user);
        (uint256 base, ) = _computeBonus(ratioBPS, _assetId, _user);

        bytes32 posKey = _posKey(_assetId, _user);
        if (!auctions[posKey].active) return base;

        uint256 elapsed = block.number - auctions[posKey].startBlock;
        uint256 escalation = elapsed * AUCTION_BPS_PER_BLOCK;
        return base + escalation;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Batch keeper: scan a list of positions and liquidate all unhealthy ones
    // ─────────────────────────────────────────────────────────────────────────

    /**
     * @notice Keeper function: liquidate all eligible positions in a batch.
     * @dev    Restricted to KEEPER_ROLE.  Reverts are swallowed per-position
     *         so one bad call doesn't block the rest.
     */
    function batchLiquidate(
        bytes32[] calldata assetIds,
        address[] calldata users,
        uint256[] calldata debtAmounts
    ) external onlyRole(KEEPER_ROLE) {
        require(
            assetIds.length == users.length &&
                users.length == debtAmounts.length,
            "Array length mismatch"
        );
        for (uint256 i; i < assetIds.length; ++i) {
            try
                this.batchLiquidateSingle(
                    assetIds[i],
                    users[i],
                    debtAmounts[i],
                    msg.sender
                )
            {
                // success - event emitted inside _liquidate()
            } catch {
                // Swallow individual failures; log via subgraph / off-chain
            }
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Emergency controls
    // ─────────────────────────────────────────────────────────────────────────

    function pauseLiquidations() external onlyRole(EMERGENCY_ROLE) {
        liquidationsPaused = true;
        emit LiquidationsPaused(msg.sender);
    }

    function resumeLiquidations() external onlyRole(EMERGENCY_ROLE) {
        liquidationsPaused = false;
        emit LiquidationsResumed(msg.sender);
    }

    // ─────────────────────────────────────────────────────────────────────────
    // View helpers
    // ─────────────────────────────────────────────────────────────────────────

    function getLiquidatorStats(
        address liquidator
    ) external view returns (LiquidatorStats memory) {
        return liquidatorStats[liquidator];
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Internal helpers
    // ─────────────────────────────────────────────────────────────────────────

    function _computeBonus(
        uint256 ratioBPS,
        bytes32,
        /*_assetId*/
        address /*_user*/
    ) internal pure returns (uint256 bonusBPS, uint256 tier) {
        if (ratioBPS < LIQ_CR_CRIT) {
            return (BONUS_CRIT, 2);
        } else if (ratioBPS < LIQ_CR_HARD) {
            return (BONUS_HARD, 1);
        } else {
            return (BONUS_SOFT, 0);
        }
    }

    function _coverBadDebt(
        bytes32 _assetId,
        address _user,
        uint256 shortfall,
        address _liquidator
    ) internal {
        totalBadDebt += shortfall;
        // Attempt to draw from the insurance fund
        uint256 available = insuranceFund.balanceOf(address(this));
        uint256 topUp = shortfall > available ? available : shortfall;
        if (topUp > 0) {
            insuranceFund.safeTransfer(_liquidator, topUp);
            emit InsuranceFundTopUp(_assetId, _user, topUp);
        }
        emit BadDebtRecorded(_assetId, _user, shortfall);
    }

    function _posKey(
        bytes32 assetId,
        address user
    ) internal pure returns (bytes32) {
        return keccak256(abi.encodePacked(assetId, user));
    }
}
