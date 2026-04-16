// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/utils/math/Math.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

/**
 * @title FluxionLiquidityPoolManager
 * @dev LiquidityPoolManager with improved security, governance, and cross-chain capabilities
 */
contract FluxionLiquidityPoolManager is AccessControl, ReentrancyGuard {
    using SafeERC20 for IERC20;

    bytes32 public constant POOL_ADMIN_ROLE = keccak256("POOL_ADMIN_ROLE");
    bytes32 public constant FEE_MANAGER_ROLE = keccak256("FEE_MANAGER_ROLE");
    bytes32 public constant EMERGENCY_ROLE = keccak256("EMERGENCY_ROLE");

    struct PoolConfig {
        address[] assets;
        uint256[] weights;
        uint256 fee;
        uint256 amplification;
        bool active;
        uint256 totalLiquidity;
        mapping(address => uint256) providerLiquidity;
        mapping(address => PriceOracle) priceOracles;
    }

    struct PriceOracle {
        address oracle;
        uint256 heartbeat;
        uint256 lastUpdate;
    }

    struct CrossChainConfig {
        uint256 destChainId;
        address remotePoolManager;
        uint256 bridgeFee;
        bool enabled;
    }

    mapping(bytes32 => PoolConfig) public pools;
    mapping(address => bytes32[]) public userPools;
    mapping(uint256 => CrossChainConfig) public crossChainConfigs;

    uint256 public constant MAX_FEE = 0.01 ether; // 1%
    uint256 public constant ORACLE_STALENESS_THRESHOLD = 1 hours;
    uint256 public governanceTimelock = 2 days;

    mapping(bytes32 => uint256) public pendingGovernanceActions;
    mapping(bytes32 => bool) public executedActions;

    event PoolCreated(
        bytes32 indexed poolId,
        address[] assets,
        uint256[] weights
    );
    event LiquidityAdded(
        bytes32 indexed poolId,
        address indexed provider,
        uint256 amount
    );
    event LiquidityRemoved(
        bytes32 indexed poolId,
        address indexed provider,
        uint256 amount
    );
    event PoolActivated(bytes32 indexed poolId);
    event PoolDeactivated(bytes32 indexed poolId);
    event GovernanceActionProposed(
        bytes32 indexed actionId,
        bytes data,
        uint256 executeAfter
    );
    event GovernanceActionExecuted(bytes32 indexed actionId);
    event CrossChainConfigUpdated(
        uint256 indexed chainId,
        address remotePoolManager,
        uint256 bridgeFee,
        bool enabled
    );

    constructor() {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(POOL_ADMIN_ROLE, msg.sender);
        _setupRole(FEE_MANAGER_ROLE, msg.sender);
        _setupRole(EMERGENCY_ROLE, msg.sender);
    }

    /**
     * @dev Creates a new liquidity pool
     * @param _assets Array of asset addresses
     * @param _weights Array of asset weights
     * @param _fee Pool fee
     * @param _amplification Amplification parameter
     * @param _oracles Array of price oracle addresses
     * @param _heartbeats Array of oracle heartbeats
     */
    function createPool(
        address[] calldata _assets,
        uint256[] calldata _weights,
        uint256 _fee,
        uint256 _amplification,
        address[] calldata _oracles,
        uint256[] calldata _heartbeats
    ) external onlyRole(POOL_ADMIN_ROLE) {
        require(_fee <= MAX_FEE, "Fee too high");
        require(
            _assets.length == _weights.length,
            "Assets and weights length mismatch"
        );
        require(_assets.length >= 2, "Minimum 2 assets required");
        require(
            _assets.length == _oracles.length,
            "Assets and oracles length mismatch"
        );
        require(
            _oracles.length == _heartbeats.length,
            "Oracles and heartbeats length mismatch"
        );

        // Generate pool ID from assets and sender
        bytes32 poolId = keccak256(
            abi.encodePacked(_assets, msg.sender, block.timestamp)
        );

        // Store pool configuration
        PoolConfig storage pool = pools[poolId];
        pool.assets = _assets;
        pool.weights = _weights;
        pool.fee = _fee;
        pool.amplification = _amplification;
        pool.active = true;
        pool.totalLiquidity = 0;

        // Set up price oracles
        for (uint256 i = 0; i < _assets.length; i++) {
            pool.priceOracles[_assets[i]] = PriceOracle({
                oracle: _oracles[i],
                heartbeat: _heartbeats[i],
                lastUpdate: block.timestamp
            });
        }

        // Add pool to user's pools
        userPools[msg.sender].push(poolId);

        // Emit event
        emit PoolCreated(poolId, _assets, _weights);
    }

    /**
     * @dev Adds liquidity to a pool
     * @param _poolId ID of the pool
     * @param _amounts Array of token amounts to add
     */
    function addLiquidity(
        bytes32 _poolId,
        uint256[] calldata _amounts
    ) external nonReentrant {
        PoolConfig storage pool = pools[_poolId];
        require(pool.active, "Pool not active");
        require(
            _amounts.length == pool.assets.length,
            "Amounts length mismatch"
        );

        uint256 liquidityValue = 0;

        // Transfer tokens and calculate liquidity value
        for (uint256 i = 0; i < pool.assets.length; i++) {
            if (_amounts[i] > 0) {
                IERC20(pool.assets[i]).safeTransferFrom(
                    msg.sender,
                    address(this),
                    _amounts[i]
                );

                // Get price from oracle
                uint256 price = getAssetPrice(pool.assets[i], _poolId);
                // Price is scaled from 1e8 (Chainlink default) to 1e18 for consistent calculation
                uint256 scaledPrice = (price * 1e10);
                liquidityValue += (_amounts[i] * scaledPrice) / 1e18;
            }
        }

        // Update liquidity records
        pool.providerLiquidity[msg.sender] += liquidityValue;
        pool.totalLiquidity += liquidityValue;

        // Add pool to user's pools if not already there
        bool hasPool = false;
        for (uint256 i = 0; i < userPools[msg.sender].length; i++) {
            if (userPools[msg.sender][i] == _poolId) {
                hasPool = true;
                break;
            }
        }

        if (!hasPool) {
            userPools[msg.sender].push(_poolId);
        }

        emit LiquidityAdded(_poolId, msg.sender, liquidityValue);
    }

    /**
     * @dev Removes liquidity from a pool
     * @param _poolId ID of the pool
     * @param _percentage Percentage of liquidity to remove (1-100)
     */
    function removeLiquidity(
        bytes32 _poolId,
        uint256 _percentage
    ) external nonReentrant {
        require(_percentage > 0 && _percentage <= 100, "Invalid percentage");

        PoolConfig storage pool = pools[_poolId];
        require(pool.active, "Pool not active");

        uint256 userLiquidity = pool.providerLiquidity[msg.sender];
        require(userLiquidity > 0, "No liquidity provided");

        uint256 amountToRemove = (userLiquidity * _percentage) / 100;

        // Calculate token amounts to return based on weights
        uint256 totalWeight = 0;
        for (uint256 i = 0; i < pool.weights.length; i++) {
            totalWeight += pool.weights[i];
        }

        // Return tokens proportionally
        for (uint256 i = 0; i < pool.assets.length; i++) {
            uint256 price = getAssetPrice(pool.assets[i], _poolId);
            // Price is scaled from 1e8 (Chainlink default) to 1e18 for consistent calculation
            uint256 scaledPrice = (price * 1e10);
            uint256 tokenAmount =
                (((amountToRemove * pool.weights[i]) / totalWeight) * 1e18) /
                    scaledPrice;

            if (tokenAmount > 0) {
                IERC20(pool.assets[i]).safeTransfer(msg.sender, tokenAmount);
            }
        }

        // Update liquidity records
        pool.providerLiquidity[msg.sender] -= amountToRemove;
        pool.totalLiquidity -= amountToRemove;

        emit LiquidityRemoved(_poolId, msg.sender, amountToRemove);
    }

    /**
     * @dev Gets the current price of an asset from its oracle
     * @param _asset Asset address
     * @param _poolId Pool ID
     * @return Current price
     */
    function getAssetPrice(
        address _asset,
        bytes32 _poolId
    ) public view returns (uint256) {
        PriceOracle storage oracle = pools[_poolId].priceOracles[_asset];
        require(oracle.oracle != address(0), "Oracle not set");

        AggregatorV3Interface priceFeed = AggregatorV3Interface(oracle.oracle);

        (, int256 price, , uint256 updatedAt, ) = priceFeed.latestRoundData();
        require(price > 0, "Invalid price");
        require(
            block.timestamp - updatedAt <= oracle.heartbeat,
            "Oracle data too old"
        );

        return uint256(price);
    }

    /**
     * @dev Activates a pool
     * @param _poolId ID of the pool
     */
    function activatePool(bytes32 _poolId) external onlyRole(POOL_ADMIN_ROLE) {
        require(!pools[_poolId].active, "Pool already active");
        pools[_poolId].active = true;
        emit PoolActivated(_poolId);
    }

    /**
     * @dev Deactivates a pool
     * @param _poolId ID of the pool
     */
    function deactivatePool(bytes32 _poolId) external {
        require(
            hasRole(POOL_ADMIN_ROLE, msg.sender) ||
                hasRole(EMERGENCY_ROLE, msg.sender),
            "Not authorized"
        );
        require(pools[_poolId].active, "Pool already inactive");
        pools[_poolId].active = false;
        emit PoolDeactivated(_poolId);
    }

    /**
     * @dev Updates the fee for a pool
     * @param _poolId ID of the pool
     * @param _newFee New fee value
     */
    function updatePoolFee(
        bytes32 _poolId,
        uint256 _newFee
    ) external onlyRole(FEE_MANAGER_ROLE) {
        require(_newFee <= MAX_FEE, "Fee too high");
        pools[_poolId].fee = _newFee;
    }

    /**
     * @dev Proposes a governance action
     * @param _data Encoded function call data
     * @return actionId ID of the proposed action
     */
    function proposeGovernanceAction(
        bytes calldata _data
    ) external onlyRole(DEFAULT_ADMIN_ROLE) returns (bytes32) {
        bytes32 actionId = keccak256(
            abi.encodePacked(_data, block.timestamp, msg.sender)
        );
        pendingGovernanceActions[actionId] =
            block.timestamp + governanceTimelock;

        emit GovernanceActionProposed(
            actionId,
            _data,
            pendingGovernanceActions[actionId]
        );

        return actionId;
    }

    /**
     * @dev Executes a governance action after timelock period
     * @param _actionId ID of the action
     * @param _data Encoded function call data
     */
    function executeGovernanceAction(
        bytes32 _actionId,
        bytes calldata _data
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(pendingGovernanceActions[_actionId] > 0, "Action not proposed");
        require(
            block.timestamp >= pendingGovernanceActions[_actionId],
            "Timelock not expired"
        );
        require(!executedActions[_actionId], "Action already executed");

        executedActions[_actionId] = true;

        // Execute the function call
        (bool success, ) = address(this).call(_data);
        require(success, "Execution failed");

        emit GovernanceActionExecuted(_actionId);
    }

    /**
     * @dev Updates cross-chain configuration
     * @param _chainId Destination chain ID
     * @param _remotePoolManager Address of pool manager on destination chain
     * @param _bridgeFee Fee for cross-chain operations
     * @param _enabled Whether cross-chain operations are enabled
     */
    function updateCrossChainConfig(
        uint256 _chainId,
        address _remotePoolManager,
        uint256 _bridgeFee,
        bool _enabled
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        crossChainConfigs[_chainId] = CrossChainConfig({
            destChainId: _chainId,
            remotePoolManager: _remotePoolManager,
            bridgeFee: _bridgeFee,
            enabled: _enabled
        });

        emit CrossChainConfigUpdated(
            _chainId,
            _remotePoolManager,
            _bridgeFee,
            _enabled
        );
    }

    /**
     * @dev Gets pool configuration
     * @param _poolId ID of the pool
     * @return assets Array of asset addresses
     * @return weights Array of asset weights
     * @return fee Pool fee
     * @return amplification Amplification parameter
     * @return active Whether the pool is active
     * @return totalLiquidity Total liquidity in the pool
     */
    function getPool(
        bytes32 _poolId
    )
        external
        view
        returns (
            address[] memory assets,
            uint256[] memory weights,
            uint256 fee,
            uint256 amplification,
            bool active,
            uint256 totalLiquidity
        )
    {
        PoolConfig storage pool = pools[_poolId];

        return (
            pool.assets,
            pool.weights,
            pool.fee,
            pool.amplification,
            pool.active,
            pool.totalLiquidity
        );
    }

    /**
     * @dev Gets user's liquidity in a pool
     * @param _poolId ID of the pool
     * @param _user User address
     * @return User's liquidity amount
     */
    function getUserLiquidity(
        bytes32 _poolId,
        address _user
    ) external view returns (uint256) {
        return pools[_poolId].providerLiquidity[_user];
    }

    /**
     * @dev Gets the number of pools created by a user
     * @param _user User address
     * @return Number of pools
     */
    function getUserPoolCount(address _user) external view returns (uint256) {
        return userPools[_user].length;
    }

    /**
     * @dev Gets a pool ID at a specific index for a user
     * @param _user User address
     * @param _index Index
     * @return Pool ID
     */
    function getUserPoolAtIndex(
        address _user,
        uint256 _index
    ) external view returns (bytes32) {
        require(_index < userPools[_user].length, "Index out of bounds");
        return userPools[_user][_index];
    }

    /**
     * @dev Updates the governance timelock period
     * @param _newTimelock New timelock period in seconds
     */
    function updateGovernanceTimelock(
        uint256 _newTimelock
    ) external onlyRole(DEFAULT_ADMIN_ROLE) {
        require(_newTimelock > 0, "Timelock must be positive");
        governanceTimelock = _newTimelock;
    }

    /**
     * @dev Emergency function to recover tokens sent to the contract
     * @param _token Token address
     * @param _amount Amount to recover
     * @param _recipient Recipient address
     */
    function emergencyRecoverTokens(
        address _token,
        uint256 _amount,
        address _recipient
    ) external onlyRole(EMERGENCY_ROLE) {
        IERC20(_token).safeTransfer(_recipient, _amount);
    }
}
