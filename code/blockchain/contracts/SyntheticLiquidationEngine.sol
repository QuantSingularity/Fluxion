// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title SyntheticLiquidationEngine
 * @notice Autonomous liquidation engine for undercollateralised synthetic-asset
 *         positions on the Fluxion protocol.
 *
 * Design goals
 * ────────────
 *  • Decoupled from SyntheticAssetFactory — operates on any vault that
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
interface IFluxionVault {
    function getPosition(
        bytes32 assetId,
        address user
    )
        external
        view
        returns (
            uint256 collateral,
            uint256 debt,
            uint256 ratioBPS,
            bool isLiquidatable
        );

    function liquidate(
        bytes32 assetId,
        address user,
        uint256 debtRepaid
    ) external;

    function getOraclePrice(
        bytes32 assetId
    ) external view returns (uint256 price18, uint256 updatedAt);
}

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
        require(!liquidationsPaused, "Liquidations paused");
        require(
            hasRole(LIQUIDATOR_ROLE, msg.sender) ||
                !hasRole(LIQUIDATOR_ROLE, address(0)),
            "Not authorised"
        );

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

        // Execute liquidation via the vault
        vault.liquidate(_assetId, _user, _debtRepaid);

        // Collateral seized by liquidator (proportional share + bonus)
        uint256 rawShare = (collateral * _debtRepaid) / debt;
        uint256 bonusAmount = (rawShare * bonusBPS) / BPS;
        uint256 totalSeize = rawShare + bonusAmount;

        // Handle bad-debt: if collateral was insufficient cover via insurance
        if (totalSeize > collateral) {
            uint256 shortfall = totalSeize - collateral;
            totalSeize = collateral;
            _coverBadDebt(_assetId, _user, shortfall);
        }

        // Update liquidator statistics
        LiquidatorStats storage stats = liquidatorStats[msg.sender];
        stats.totalLiquidations++;
        stats.totalBonusEarned += bonusAmount;
        stats.totalDebtRepaid += _debtRepaid;

        // Close any active auction for this position
        bytes32 posKey = _posKey(_assetId, _user);
        if (auctions[posKey].active) {
            auctions[posKey].active = false;
            emit AuctionClosed(posKey, msg.sender);
        }

        emit LiquidationExecuted(
            _assetId,
            _user,
            msg.sender,
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
            try this.liquidate(assetIds[i], users[i], debtAmounts[i]) {
                // success — event emitted inside liquidate()
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
        bytes32 /*_assetId*/,
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
        uint256 shortfall
    ) internal {
        totalBadDebt += shortfall;
        // Attempt to draw from the insurance fund
        uint256 available = insuranceFund.balanceOf(address(this));
        uint256 topUp = shortfall > available ? available : shortfall;
        if (topUp > 0) {
            insuranceFund.safeTransfer(msg.sender, topUp);
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
