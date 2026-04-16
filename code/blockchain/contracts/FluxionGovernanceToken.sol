// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Votes.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

/**
 * @title FluxionGovernanceToken
 * @dev Governance token with advanced features for financial applications for financial applications
 * Features:
 * - Voting power delegation and checkpointing
 * - Staking rewards and yield farming
 * - Vesting schedules for team and investors
 * - Treasury management and fee distribution
 * - Emergency pause functionality
 * - Compliance and regulatory features
 */
contract FluxionGovernanceToken is
    ERC20,
    ERC20Votes,
    ERC20Permit,
    AccessControl,
    ReentrancyGuard,
    Pausable
{
    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant BURNER_ROLE = keccak256("BURNER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant TREASURY_ROLE = keccak256("TREASURY_ROLE");
    bytes32 public constant COMPLIANCE_ROLE = keccak256("COMPLIANCE_ROLE");

    // Token economics
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10 ** 18; // 1 billion tokens
    uint256 public constant INITIAL_SUPPLY = 100_000_000 * 10 ** 18; // 100 million initial

    // Staking and rewards
    struct StakingInfo {
        uint256 stakedAmount;
        uint256 stakingTimestamp;
        uint256 lastRewardClaim;
        uint256 lockPeriod;
        bool isLocked;
    }

    mapping(address => StakingInfo) public stakingInfo;
    uint256 public totalStaked;
    uint256 public rewardRate = 1000; // 10% APY (basis points)
    uint256 public constant REWARD_PRECISION = 10000;

    // Vesting schedules
    struct VestingSchedule {
        uint256 totalAmount;
        uint256 releasedAmount;
        uint256 startTime;
        uint256 duration;
        uint256 cliffDuration;
        bool revocable;
        bool revoked;
    }

    mapping(address => VestingSchedule[]) public vestingSchedules;
    uint256 public totalVestingAmount;

    // Treasury and fee distribution
    address public treasury;
    uint256 public treasuryFeeRate = 500; // 5% (basis points)
    uint256 public totalFeesCollected;

    // Compliance features
    mapping(address => bool) public blacklisted;
    mapping(address => bool) public whitelisted;
    bool public whitelistEnabled = false;
    uint256 public maxTransferAmount;
    uint256 public dailyTransferLimit;
    mapping(address => mapping(uint256 => uint256)) public dailyTransfers; // user => day => amount

    // Governance parameters
    uint256 public proposalThreshold = 1000000 * 10 ** 18; // 1M tokens to create proposal
    uint256 public votingDelay = 1 days;
    uint256 public votingPeriod = 7 days;
    uint256 public quorumPercentage = 4; // 4% of total supply

    // Events
    event Staked(address indexed user, uint256 amount, uint256 lockPeriod);
    event Unstaked(address indexed user, uint256 amount);
    event RewardsClaimed(address indexed user, uint256 amount);
    event VestingScheduleCreated(
        address indexed beneficiary,
        uint256 amount,
        uint256 duration
    );
    event VestingTokensReleased(address indexed beneficiary, uint256 amount);
    event VestingRevoked(address indexed beneficiary, uint256 index);
    event TreasuryUpdated(
        address indexed oldTreasury,
        address indexed newTreasury
    );
    event FeesDistributed(uint256 amount);
    event BlacklistUpdated(address indexed account, bool blacklisted);
    event WhitelistUpdated(address indexed account, bool whitelisted);
    event ComplianceLimitsUpdated(uint256 maxTransfer, uint256 dailyLimit);

    constructor(
        string memory name,
        string memory symbol,
        address _treasury
    ) ERC20(name, symbol) ERC20Permit(name) {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(MINTER_ROLE, msg.sender);
        _setupRole(BURNER_ROLE, msg.sender);
        _setupRole(PAUSER_ROLE, msg.sender);
        _setupRole(TREASURY_ROLE, msg.sender);
        _setupRole(COMPLIANCE_ROLE, msg.sender);

        treasury = _treasury;
        maxTransferAmount = MAX_SUPPLY; // No limit initially
        dailyTransferLimit = MAX_SUPPLY; // No limit initially

        // Mint initial supply to deployer
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    // Staking functions

    /**
     * @dev Stake tokens for rewards
     * @param amount Amount to stake
     * @param lockPeriod Lock period in seconds (0 for no lock)
     */
    function stake(
        uint256 amount,
        uint256 lockPeriod
    ) external nonReentrant whenNotPaused {
        require(amount > 0, "Amount must be greater than 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");

        // Claim existing rewards before updating stake
        if (stakingInfo[msg.sender].stakedAmount > 0) {
            _claimRewards(msg.sender);
        }

        // Transfer tokens to contract
        _transfer(msg.sender, address(this), amount);

        // Update staking info
        stakingInfo[msg.sender].stakedAmount += amount;
        stakingInfo[msg.sender].stakingTimestamp = block.timestamp;
        stakingInfo[msg.sender].lastRewardClaim = block.timestamp;
        stakingInfo[msg.sender].lockPeriod = lockPeriod;
        stakingInfo[msg.sender].isLocked = lockPeriod > 0;

        totalStaked += amount;

        emit Staked(msg.sender, amount, lockPeriod);
    }

    /**
     * @dev Unstake tokens
     * @param amount Amount to unstake
     */
    function unstake(uint256 amount) external nonReentrant whenNotPaused {
        StakingInfo storage info = stakingInfo[msg.sender];
        require(info.stakedAmount >= amount, "Insufficient staked amount");

        // Check lock period
        if (info.isLocked) {
            require(
                block.timestamp >= info.stakingTimestamp + info.lockPeriod,
                "Tokens are still locked"
            );
        }

        // Claim rewards before unstaking
        _claimRewards(msg.sender);

        // Update staking info
        info.stakedAmount -= amount;
        totalStaked -= amount;

        // Transfer tokens back to user
        _transfer(address(this), msg.sender, amount);

        emit Unstaked(msg.sender, amount);
    }

    /**
     * @dev Claim staking rewards
     */
    function claimRewards() external nonReentrant whenNotPaused {
        _claimRewards(msg.sender);
    }

    /**
     * @dev Calculate pending rewards for a user
     * @param user User address
     * @return Pending reward amount
     */
    function pendingRewards(address user) external view returns (uint256) {
        StakingInfo storage info = stakingInfo[user];
        if (info.stakedAmount == 0) {
            return 0;
        }

        uint256 stakingDuration = block.timestamp - info.lastRewardClaim;
        uint256 rewards =
            (info.stakedAmount * rewardRate * stakingDuration) /
                (365 days * REWARD_PRECISION);

        return rewards;
    }

    // Vesting functions

    /**
     * @dev Create a vesting schedule
     * @param beneficiary Beneficiary address
     * @param amount Total vesting amount
     * @param startTime Vesting start time
     * @param duration Vesting duration
     * @param cliffDuration Cliff duration
     * @param revocable Whether the vesting is revocable
     */
    function createVestingSchedule(
        address beneficiary,
        uint256 amount,
        uint256 startTime,
        uint256 duration,
        uint256 cliffDuration,
        bool revocable
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(beneficiary != address(0), "Invalid beneficiary");
        require(amount > 0, "Amount must be greater than 0");
        require(duration > 0, "Duration must be greater than 0");
        require(
            cliffDuration <= duration,
            "Cliff duration cannot exceed total duration"
        );
        require(
            startTime >= block.timestamp,
            "Start time cannot be in the past"
        );

        // Check if there are enough tokens to vest
        require(
            totalSupply() + amount <= MAX_SUPPLY,
            "Would exceed maximum supply"
        );

        // Create vesting schedule
        vestingSchedules[beneficiary].push(
            VestingSchedule({
                totalAmount: amount,
                releasedAmount: 0,
                startTime: startTime,
                duration: duration,
                cliffDuration: cliffDuration,
                revocable: revocable,
                revoked: false
            })
        );

        totalVestingAmount += amount;

        // Mint tokens to contract for vesting
        _mint(address(this), amount);

        emit VestingScheduleCreated(beneficiary, amount, duration);
    }

    /**
     * @dev Release vested tokens
     * @param beneficiary Beneficiary address
     * @param scheduleIndex Vesting schedule index
     */
    function releaseVestedTokens(
        address beneficiary,
        uint256 scheduleIndex
    ) external nonReentrant {
        require(
            scheduleIndex < vestingSchedules[beneficiary].length,
            "Invalid schedule index"
        );

        VestingSchedule storage schedule = vestingSchedules[beneficiary][
            scheduleIndex
        ];
        require(!schedule.revoked, "Vesting schedule revoked");

        uint256 releasableAmount = _calculateReleasableAmount(schedule);
        require(releasableAmount > 0, "No tokens to release");

        schedule.releasedAmount += releasableAmount;
        totalVestingAmount -= releasableAmount;

        // Transfer tokens to beneficiary
        _transfer(address(this), beneficiary, releasableAmount);

        emit VestingTokensReleased(beneficiary, releasableAmount);
    }

    /**
     * @dev Revoke vesting schedule (only if revocable)
     * @param beneficiary Beneficiary address
     * @param scheduleIndex Vesting schedule index
     */
    function revokeVesting(
        address beneficiary,
        uint256 scheduleIndex
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(
            scheduleIndex < vestingSchedules[beneficiary].length,
            "Invalid schedule index"
        );

        VestingSchedule storage schedule = vestingSchedules[beneficiary][
            scheduleIndex
        ];
        require(schedule.revocable, "Vesting schedule not revocable");
        require(!schedule.revoked, "Vesting schedule already revoked");

        // Calculate and release any vested tokens first
        uint256 releasableAmount = _calculateReleasableAmount(schedule);
        if (releasableAmount > 0) {
            schedule.releasedAmount += releasableAmount;
            _transfer(address(this), beneficiary, releasableAmount);
            emit VestingTokensReleased(beneficiary, releasableAmount);
        }

        // Revoke remaining tokens
        uint256 remainingAmount =
            schedule.totalAmount - schedule.releasedAmount;
        if (remainingAmount > 0) {
            totalVestingAmount -= remainingAmount;
            // Burn remaining tokens or return to treasury
            _transfer(address(this), treasury, remainingAmount);
        }

        schedule.revoked = true;

        emit VestingRevoked(beneficiary, scheduleIndex);
    }

    /**
     * @dev Get vesting schedule count for beneficiary
     * @param beneficiary Beneficiary address
     * @return Number of vesting schedules
     */
    function getVestingScheduleCount(
        address beneficiary
    ) external view returns (uint256) {
        return vestingSchedules[beneficiary].length;
    }

    /**
     * @dev Calculate releasable amount for vesting schedule
     * @param beneficiary Beneficiary address
     * @param scheduleIndex Schedule index
     * @return Releasable amount
     */
    function calculateReleasableAmount(
        address beneficiary,
        uint256 scheduleIndex
    ) external view returns (uint256) {
        require(
            scheduleIndex < vestingSchedules[beneficiary].length,
            "Invalid schedule index"
        );
        return
            _calculateReleasableAmount(
                vestingSchedules[beneficiary][scheduleIndex]
            );
    }

    // Treasury and fee functions

    /**
     * @dev Update treasury address
     * @param newTreasury New treasury address
     */
    function updateTreasury(
        address newTreasury
    ) external onlyRole(TREASURY_ROLE) {
        require(newTreasury != address(0), "Invalid treasury address");
        address oldTreasury = treasury;
        treasury = newTreasury;
        emit TreasuryUpdated(oldTreasury, newTreasury);
    }

    /**
     * @dev Update treasury fee rate
     * @param newRate New fee rate in basis points
     */
    function updateTreasuryFeeRate(
        uint256 newRate
    ) external onlyRole(TREASURY_ROLE) {
        require(newRate <= 1000, "Fee rate cannot exceed 10%"); // Max 10%
        treasuryFeeRate = newRate;
    }

    /**
     * @dev Withdraw collected fees to the treasury
     */
    function withdrawFeesToTreasury()
        external
        onlyRole(TREASURY_ROLE)
        nonReentrant
    {
        uint256 feesToDistribute = totalFeesCollected;
        require(feesToDistribute > 0, "No fees to distribute");
        totalFeesCollected = 0;

        // Transfer collected fees to the treasury
        _transfer(address(this), treasury, feesToDistribute);

        emit FeesDistributed(feesToDistribute);
    }

    // Compliance functions

    /**
     * @dev Update blacklist status
     * @param account Account address
     * @param isBlacklisted Blacklist status
     */
    function updateBlacklist(
        address account,
        bool isBlacklisted
    ) external onlyRole(COMPLIANCE_ROLE) {
        blacklisted[account] = isBlacklisted;
        emit BlacklistUpdated(account, isBlacklisted);
    }

    /**
     * @dev Update whitelist status
     * @param account Account address
     * @param isWhitelisted Whitelist status
     */
    function updateWhitelist(
        address account,
        bool isWhitelisted
    ) external onlyRole(COMPLIANCE_ROLE) {
        whitelisted[account] = isWhitelisted;
        emit WhitelistUpdated(account, isWhitelisted);
    }

    /**
     * @dev Enable/disable whitelist requirement
     * @param enabled Whitelist enabled status
     */
    function setWhitelistEnabled(
        bool enabled
    ) external onlyRole(COMPLIANCE_ROLE) {
        whitelistEnabled = enabled;
    }

    /**
     * @dev Update compliance limits
     * @param maxTransfer Maximum transfer amount
     * @param dailyLimit Daily transfer limit
     */
    function updateComplianceLimits(
        uint256 maxTransfer,
        uint256 dailyLimit
    ) external onlyRole(COMPLIANCE_ROLE) {
        maxTransferAmount = maxTransfer;
        dailyTransferLimit = dailyLimit;
        emit ComplianceLimitsUpdated(maxTransfer, dailyLimit);
    }

    // Governance functions

    /**
     * @dev Update governance parameters
     * @param newProposalThreshold New proposal threshold
     * @param newVotingDelay New voting delay
     * @param newVotingPeriod New voting period
     * @param newQuorumPercentage New quorum percentage
     */
    function updateGovernanceParameters(
        uint256 newProposalThreshold,
        uint256 newVotingDelay,
        uint256 newVotingPeriod,
        uint256 newQuorumPercentage
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newQuorumPercentage <= 20, "Quorum cannot exceed 20%");
        require(newVotingPeriod >= 1 days, "Voting period too short");

        proposalThreshold = newProposalThreshold;
        votingDelay = newVotingDelay;
        votingPeriod = newVotingPeriod;
        quorumPercentage = newQuorumPercentage;
    }

    // Admin functions

    /**
     * @dev Mint tokens (only minter role)
     * @param to Recipient address
     * @param amount Amount to mint
     */
    function mint(address to, uint256 amount) external onlyRole(MINTER_ROLE) {
        require(
            totalSupply() + amount <= MAX_SUPPLY,
            "Would exceed maximum supply"
        );
        _mint(to, amount);
    }

    /**
     * @dev Burn tokens (only burner role)
     * @param amount Amount to burn
     */
    function burn(uint256 amount) external onlyRole(BURNER_ROLE) {
        _burn(msg.sender, amount);
    }

    /**
     * @dev Pause contract (only pauser role)
     */
    function pause() external onlyRole(PAUSER_ROLE) {
        _pause();
    }

    /**
     * @dev Unpause contract (only pauser role)
     */
    function unpause() external onlyRole(PAUSER_ROLE) {
        _unpause();
    }

    /**
     * @dev Update reward rate
     * @param newRate New reward rate in basis points
     */
    function updateRewardRate(
        uint256 newRate
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(newRate <= 5000, "Reward rate cannot exceed 50%"); // Max 50% APY
        rewardRate = newRate;
    }

    // Internal functions

    function _claimRewards(address user) internal {
        StakingInfo storage info = stakingInfo[user];
        if (info.stakedAmount == 0) {
            return;
        }

        uint256 stakingDuration = block.timestamp - info.lastRewardClaim;
        uint256 rewards =
            (info.stakedAmount * rewardRate * stakingDuration) /
                (365 days * REWARD_PRECISION);

        if (rewards > 0) {
            info.lastRewardClaim = block.timestamp;

            // Mint rewards
            _mint(user, rewards);

            emit RewardsClaimed(user, rewards);
        }
    }

    function _calculateReleasableAmount(
        VestingSchedule storage schedule
    ) internal view returns (uint256) {
        if (block.timestamp < schedule.startTime + schedule.cliffDuration) {
            return 0;
        }

        uint256 elapsedTime = block.timestamp - schedule.startTime;
        if (elapsedTime >= schedule.duration) {
            return schedule.totalAmount - schedule.releasedAmount;
        }

        uint256 vestedAmount =
            (schedule.totalAmount * elapsedTime) / schedule.duration;
        return vestedAmount - schedule.releasedAmount;
    }

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20) whenNotPaused {
        // Skip compliance checks for minting, burning, and contract operations
        if (
            from == address(0) ||
            to == address(0) ||
            from == address(this) ||
            to == address(this)
        ) {
            super._beforeTokenTransfer(from, to, amount);
            return;
        }

        // Blacklist check
        require(
            !blacklisted[from] && !blacklisted[to],
            "Address is blacklisted"
        );

        // Whitelist check (if enabled)
        if (whitelistEnabled) {
            require(
                whitelisted[from] && whitelisted[to],
                "Address not whitelisted"
            );
        }

        // Transfer amount limits
        if (maxTransferAmount > 0) {
            require(
                amount <= maxTransferAmount,
                "Transfer amount exceeds limit"
            );
        }

        // Daily transfer limits
        if (dailyTransferLimit > 0) {
            uint256 currentDay = block.timestamp / 1 days;
            uint256 dailyTransferred = dailyTransfers[from][currentDay];
            require(
                dailyTransferred + amount <= dailyTransferLimit,
                "Daily transfer limit exceeded"
            );
            dailyTransfers[from][currentDay] = dailyTransferred + amount;
        }

        // Collect treasury fee on transfers (excluding staking operations)
        if (
            treasuryFeeRate > 0 && from != address(this) && to != address(this)
        ) {
            uint256 fee = (amount * treasuryFeeRate) / REWARD_PRECISION;
            if (fee > 0) {
                totalFeesCollected += fee;
                // Fee is deducted from the transfer amount
                super._beforeTokenTransfer(from, treasury, fee);
                amount -= fee;
            }
        }

        super._beforeTokenTransfer(from, to, amount);
    }

    function _afterTokenTransfer(
        address from,
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._afterTokenTransfer(from, to, amount);
    }

    function _mint(
        address to,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._mint(to, amount);
    }

    function _burn(
        address account,
        uint256 amount
    ) internal override(ERC20, ERC20Votes) {
        super._burn(account, amount);
    }

    /**
     * @dev Returns the current voting power of a user.
     * @param account The address of the user.
     * @return The current voting power.
     */
    function getVotes(address account) external view returns (uint256) {
        return super.getVotes(account);
    }

    // View functions

    /**
     * @dev Get current day for daily limits
     * @return Current day timestamp
     */
    function getCurrentDay() external view returns (uint256) {
        return block.timestamp / 1 days;
    }

    /**
     * @dev Get daily transfer amount for user
     * @param user User address
     * @param day Day timestamp
     * @return Daily transfer amount
     */
    function getDailyTransferAmount(
        address user,
        uint256 day
    ) external view returns (uint256) {
        return dailyTransfers[user][day];
    }

    /**
     * @dev Check if address can transfer amount
     * @param from From address
     * @param to To address
     * @param amount Transfer amount
     * @return Whether transfer is allowed
     */
    function canTransfer(
        address from,
        address to,
        uint256 amount
    ) external view returns (bool) {
        // Blacklist check
        if (blacklisted[from] || blacklisted[to]) {
            return false;
        }

        // Whitelist check
        if (whitelistEnabled && (!whitelisted[from] || !whitelisted[to])) {
            return false;
        }

        // Amount limit check
        if (maxTransferAmount > 0 && amount > maxTransferAmount) {
            return false;
        }

        // Daily limit check
        if (dailyTransferLimit > 0) {
            uint256 currentDay = block.timestamp / 1 days;
            uint256 dailyTransferred = dailyTransfers[from][currentDay];
            if (dailyTransferred + amount > dailyTransferLimit) {
                return false;
            }
        }

        return true;
    }
}
