// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";

contract SyntheticAssetFactory is Ownable, ChainlinkClient {
    using Chainlink for Chainlink.Request;

    struct SyntheticAsset {
        address token;
        address oracle;
        bytes32 jobId;
        uint256 fee;
        bool active;
        uint256 price;
    }

    mapping(bytes32 => SyntheticAsset) public syntheticAssets;
    bytes32[] public assetIds;
    mapping(bytes32 => bytes32) private requestToAssetId;

    event SyntheticAssetCreated(
        bytes32 indexed assetId,
        address token,
        address oracle,
        bytes32 jobId
    );

    constructor() Ownable() {
        setPublicChainlinkToken();
    }

    function createSynthetic(
        bytes32 _assetId,
        address _oracle,
        bytes32 _jobId,
        uint256 _fee
    ) external onlyOwner {
        require(
            syntheticAssets[_assetId].token == address(0),
            "Asset already exists"
        );

        // Deploy new ERC20 token for the synthetic asset
        SyntheticToken token = new SyntheticToken(
            string(abi.encodePacked("Synthetic ", bytes32ToString(_assetId))),
            string(abi.encodePacked("s", bytes32ToString(_assetId)))
        );

        // Store synthetic asset configuration
        syntheticAssets[_assetId] = SyntheticAsset({
            token: address(token),
            oracle: _oracle,
            jobId: _jobId,
            fee: _fee,
            active: true
        });

        // Add asset ID to list
        assetIds.push(_assetId);

        // Emit event
        emit SyntheticAssetCreated(_assetId, address(token), _oracle, _jobId);
    }

    function mintSynthetic(bytes32 _assetId, uint256 _amount) external {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        require(asset.active, "Asset not active");
        require(asset.price > 0, "Price not available");

        // Simple minting logic: 1 unit of collateral for 1 unit of synthetic asset
        // In a real system, this would involve collateral and price feed logic
        SyntheticToken(asset.token).mint(msg.sender, _amount);
    }

    function burnSynthetic(bytes32 _assetId, uint256 _amount) external {
        SyntheticAsset storage asset = syntheticAssets[_assetId];
        require(asset.active, "Asset not active");

        // Simple burning logic
        SyntheticToken(asset.token).burn(msg.sender, _amount);
    }

    function requestPriceUpdate(bytes32 _assetId) external {
        SyntheticAsset memory asset = syntheticAssets[_assetId];
        require(asset.active, "Asset not active");

        Chainlink.Request memory req = buildChainlinkRequest(
            asset.jobId,
            address(this),
            this.fulfillPriceUpdate.selector
        );

        // Add asset ID as parameter
        req.add("assetId", bytes32ToString(_assetId));

        // Send request
        bytes32 requestId = sendChainlinkRequestTo(
            asset.oracle,
            req,
            asset.fee
        );
        requestToAssetId[requestId] = _assetId;
    }

    function fulfillPriceUpdate(
        bytes32 _requestId,
        uint256 _price
    ) external recordChainlinkFulfillment(_requestId) {
        bytes32 assetId = requestToAssetId[_requestId];
        require(assetId != 0, "Request not found");
        syntheticAssets[assetId].price = _price;
    }

    function deactivateAsset(bytes32 _assetId) external onlyOwner {
        require(
            syntheticAssets[_assetId].token != address(0),
            "Asset does not exist"
        );
        syntheticAssets[_assetId].active = false;
    }

    function reactivateAsset(bytes32 _assetId) external onlyOwner {
        require(
            syntheticAssets[_assetId].token != address(0),
            "Asset does not exist"
        );
        syntheticAssets[_assetId].active = true;
    }

    function getAssetCount() external view returns (uint256) {
        return assetIds.length;
    }

    // Helper function to convert bytes32 to string
    function bytes32ToString(
        bytes32 _bytes32
    ) internal pure returns (string memory) {
        // If the bytes32 is a valid string (e.g., a short name), convert it.
        // Otherwise, return a hex representation.
        uint256 charCount = 0;
        for (uint256 i = 0; i < 32; i++) {
            if (uint8(_bytes32[i]) != 0) {
                charCount = i + 1;
            }
        }

        if (charCount > 0) {
            bytes memory bytesArray = new bytes(charCount);
            for (uint256 i = 0; i < charCount; i++) {
                bytesArray[i] = _bytes32[i];
            }
            return string(bytesArray);
        } else {
            // Fallback to hex representation if it's not a simple string
            return string(abi.encodePacked("0x", bytes32(uint256(_bytes32))));
        }
    }
}

// Synthetic token contract
contract SyntheticToken is ERC20Burnable, Ownable {
    constructor(
        string memory name,
        string memory symbol
    ) ERC20(name, symbol) Ownable() {}

    function mint(address to, uint256 amount) external onlyOwner {
        _mint(to, amount);
    }
}
