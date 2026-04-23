// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";
import "@chainlink/contracts/src/v0.8/interfaces/AggregatorV3Interface.sol";

contract SyntheticAssetFactory is Ownable, ReentrancyGuard, ChainlinkClient {
    using SafeERC20 for IERC20;
    using Chainlink for Chainlink.Request;

    uint256 public constant BPS = 10_000;
    uint256 public constant MIN_CR = 15_000;
    uint256 public constant LIQ_CR = 12_000;
    uint256 public constant LIQ_BONUS = 500;
    uint256 public constant STABILITY_FEE = 200;
    uint256 public constant SECONDS_PER_YEAR = 31_536_000;
    uint256 public constant ORACLE_STALENESS = 3_600;

    struct SyntheticAsset {
        address syntheticToken;
        address collateralToken;
        address priceOracle;
        address clOracle;
        bytes32 clJobId;
        uint256 clFee;
        uint256 price;
        uint256 priceTimestamp;
        bool active;
    }

    struct Position {
        uint256 collateralDeposited;
        uint256 syntheticMinted;
        uint256 feeTimestamp;
    }

    mapping(bytes32 => SyntheticAsset) public syntheticAssets;
    bytes32[] public assetIds;
    mapping(bytes32 => mapping(address => Position)) public positions;
    mapping(bytes32 => uint256) public totalMinted;
    mapping(bytes32 => bytes32) private requestToAssetId;

    event SyntheticAssetRegistered(
        bytes32 indexed assetId,
        address syntheticToken,
        address collateralToken,
        address priceOracle
    );
    event Minted(
        bytes32 indexed assetId,
        address indexed user,
        uint256 collateralDeposited,
        uint256 syntheticMinted,
        uint256 collateralRatioBPS
    );
    event Burned(
        bytes32 indexed assetId,
        address indexed user,
        uint256 collateralReturned,
        uint256 syntheticBurned
    );
    event Liquidated(
        bytes32 indexed assetId,
        address indexed user,
        address indexed liquidator,
        uint256 debtRepaid,
        uint256 collateralSeized
    );
    event PriceUpdated(
        bytes32 indexed assetId,
        uint256 price,
        uint256 blockTimestamp
    );

    constructor() Ownable() {
        setPublicChainlinkToken();
    }

    function createSynthetic(
        bytes32 _assetId,
        address _collateral,
        address _priceOracle,
        address _clOracle,
        bytes32 _jobId,
        uint256 _fee
    ) external onlyOwner {
        require(
            syntheticAssets[_assetId].syntheticToken == address(0),
            "Asset already exists"
        );
        require(_collateral != address(0), "Invalid collateral");
        require(_priceOracle != address(0), "Invalid oracle");
        require(_clOracle != address(0), "Invalid CL oracle");

        SyntheticToken token = new SyntheticToken(
            string(abi.encodePacked("Fluxion Synthetic ", _b32str(_assetId))),
            string(abi.encodePacked("fs", _b32str(_assetId)))
        );

        syntheticAssets[_assetId] = SyntheticAsset({
            syntheticToken: address(token),
            collateralToken: _collateral,
            priceOracle: _priceOracle,
            clOracle: _clOracle,
            clJobId: _jobId,
            clFee: _fee,
            price: 0,
            priceTimestamp: 0,
            active: true
        });
        assetIds.push(_assetId);

        _pullAggregatorPrice(_assetId);

        emit SyntheticAssetRegistered(
            _assetId,
            address(token),
            _collateral,
            _priceOracle
        );
    }

    function mintSynthetic(
        bytes32 _assetId,
        uint256 _collateralAmount,
        uint256 _syntheticAmount
    ) external nonReentrant {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        require(asset.active, "Asset not active");
        require(_collateralAmount > 0, "Zero collateral");
        require(_syntheticAmount > 0, "Zero mint amount");
        require(_priceIsFresh(asset), "Price stale");

        _accrueStabilityFee(_assetId, msg.sender);

        IERC20(asset.collateralToken).safeTransferFrom(
            msg.sender,
            address(this),
            _collateralAmount
        );

        Position storage pos = positions[_assetId][msg.sender];
        pos.collateralDeposited += _collateralAmount;
        pos.syntheticMinted += _syntheticAmount;
        pos.feeTimestamp = block.timestamp;

        uint256 cr = _crBPS(_assetId, msg.sender);
        require(cr >= MIN_CR, "CR below 150% minimum");

        totalMinted[_assetId] += _syntheticAmount;
        SyntheticToken(asset.syntheticToken).mint(msg.sender, _syntheticAmount);

        emit Minted(
            _assetId,
            msg.sender,
            _collateralAmount,
            _syntheticAmount,
            cr
        );
    }

    function burnSynthetic(
        bytes32 _assetId,
        uint256 _syntheticAmount
    ) external nonReentrant {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        require(asset.active, "Asset not active");

        _accrueStabilityFee(_assetId, msg.sender);

        Position storage pos = positions[_assetId][msg.sender];
        require(pos.syntheticMinted >= _syntheticAmount, "Burn exceeds minted");

        uint256 collateralReturn =
            (pos.collateralDeposited * _syntheticAmount) / pos.syntheticMinted;

        pos.collateralDeposited -= collateralReturn;
        pos.syntheticMinted -= _syntheticAmount;
        totalMinted[_assetId] -= _syntheticAmount;

        SyntheticToken(asset.syntheticToken).forceBurn(
            msg.sender,
            _syntheticAmount
        );
        IERC20(asset.collateralToken).safeTransfer(
            msg.sender,
            collateralReturn
        );

        emit Burned(_assetId, msg.sender, collateralReturn, _syntheticAmount);
    }

    function liquidate(
        bytes32 _assetId,
        address _user,
        uint256 _syntheticRepaid
    ) external nonReentrant {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        require(_priceIsFresh(asset), "Price stale");

        _accrueStabilityFee(_assetId, _user);

        uint256 cr = _crBPS(_assetId, _user);
        require(cr < LIQ_CR, "Position is healthy");

        Position storage pos = positions[_assetId][_user];
        require(pos.syntheticMinted >= _syntheticRepaid, "Repaid exceeds debt");

        uint256 rawSeize =
            (pos.collateralDeposited * _syntheticRepaid) / pos.syntheticMinted;
        uint256 seize = rawSeize + (rawSeize * LIQ_BONUS) / BPS;
        if (seize > pos.collateralDeposited) {
            seize = pos.collateralDeposited;
        }

        pos.collateralDeposited -= seize;
        pos.syntheticMinted -= _syntheticRepaid;
        totalMinted[_assetId] -= _syntheticRepaid;

        SyntheticToken(asset.syntheticToken).forceBurn(
            msg.sender,
            _syntheticRepaid
        );
        IERC20(asset.collateralToken).safeTransfer(msg.sender, seize);

        emit Liquidated(_assetId, _user, msg.sender, _syntheticRepaid, seize);
    }

    function refreshPrice(bytes32 _assetId) external {
        _pullAggregatorPrice(_assetId);
    }

    function requestPriceUpdate(bytes32 _assetId) external {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        require(asset.active, "Asset not active");

        Chainlink.Request memory req = buildChainlinkRequest(
            asset.clJobId,
            address(this),
            this.fulfillPriceUpdate.selector
        );
        req.add("assetId", _b32str(_assetId));
        bytes32 reqId = sendChainlinkRequestTo(
            asset.clOracle,
            req,
            asset.clFee
        );
        requestToAssetId[reqId] = _assetId;
    }

    function fulfillPriceUpdate(
        bytes32 _requestId,
        uint256 _price
    ) external recordChainlinkFulfillment(_requestId) {
        bytes32 assetId = requestToAssetId[_requestId];
        require(assetId != 0, "Unknown request ID");
        syntheticAssets[assetId].price = _price;
        syntheticAssets[assetId].priceTimestamp = block.timestamp;
        emit PriceUpdated(assetId, _price, block.timestamp);
    }

    function getCollateralRatio(
        bytes32 _assetId,
        address _user
    ) external view returns (uint256) {
        return _crBPS(_assetId, _user);
    }

    function getPosition(
        bytes32 _assetId,
        address _user
    )
        external
        view
        returns (
            uint256 collateral,
            uint256 debt,
            uint256 ratioBPS,
            bool isLiquidatable
        )
    {
        Position storage pos = positions[_assetId][_user];
        collateral = pos.collateralDeposited;
        debt = pos.syntheticMinted;
        ratioBPS = _crBPS(_assetId, _user);
        isLiquidatable = (debt > 0) && (ratioBPS < LIQ_CR);
    }

    function getAssetCount() external view returns (uint256) {
        return assetIds.length;
    }

    function _pullAggregatorPrice(bytes32 _assetId) internal {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        if (asset.priceOracle == address(0)) return;

        AggregatorV3Interface feed = AggregatorV3Interface(asset.priceOracle);
        (, int256 answer, , uint256 updatedAt, ) = feed.latestRoundData();
        require(answer > 0, "Oracle answer <= 0");
        require(
            block.timestamp - updatedAt <= ORACLE_STALENESS,
            "Aggregator price stale"
        );

        uint8 dec = feed.decimals();
        uint256 p = uint256(answer);
        if (dec < 18) {
            p = p * (10 ** (18 - dec));
        } else if (dec > 18) {
            p = p / (10 ** (dec - 18));
        }

        asset.price = p;
        asset.priceTimestamp = block.timestamp;
        emit PriceUpdated(_assetId, p, block.timestamp);
    }

    function _crBPS(
        bytes32 _assetId,
        address _user
    ) internal view returns (uint256) {
        Position storage pos = positions[_assetId][_user];
        if (pos.syntheticMinted == 0) return type(uint256).max;
        uint256 collateralUSD =
            (pos.collateralDeposited * syntheticAssets[_assetId].price) / 1e18;
        return (collateralUSD * BPS) / pos.syntheticMinted;
    }

    function _accrueStabilityFee(bytes32 _assetId, address _user) internal {
        Position storage pos = positions[_assetId][_user];
        if (pos.syntheticMinted == 0 || pos.feeTimestamp == 0) {
            pos.feeTimestamp = block.timestamp;
            return;
        }
        uint256 elapsed = block.timestamp - pos.feeTimestamp;
        if (elapsed == 0) return;

        uint256 fee =
            (pos.collateralDeposited * STABILITY_FEE * elapsed) /
                (BPS * SECONDS_PER_YEAR);
        if (fee >= pos.collateralDeposited) {
            fee = pos.collateralDeposited;
        }
        pos.collateralDeposited -= fee;
        pos.feeTimestamp = block.timestamp;
    }

    function _priceIsFresh(
        SyntheticAsset storage asset
    ) internal view returns (bool) {
        return
            asset.price > 0 &&
            block.timestamp - asset.priceTimestamp <= ORACLE_STALENESS;
    }

    function _b32str(bytes32 b) internal pure returns (string memory) {
        uint256 len;
        for (uint256 i; i < 32; ++i) {
            if (b[i] == 0) break;
            len = i + 1;
        }
        bytes memory out = new bytes(len);
        for (uint256 i; i < len; ++i) {
            out[i] = b[i];
        }
        return string(out);
    }
}

contract SyntheticToken is ERC20Burnable, Ownable {
    constructor(
        string memory name,
        string memory symbol
    ) ERC20(name, symbol) Ownable() {}

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }

    function forceBurn(address from, uint256 amount) external onlyOwner {
        _burn(from, amount);
    }
}
