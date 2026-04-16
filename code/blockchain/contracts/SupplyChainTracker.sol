// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "@openzeppelin/contracts/access/AccessControl.sol";
import "@openzeppelin/contracts/utils/Counters.sol";
import "@chainlink/contracts/src/v0.8/ChainlinkClient.sol";

/**
 * @title SupplyChainTracker
 * @dev Contract for tracking assets through a supply chain with Chainlink oracle integration
 */
contract SupplyChainTracker is AccessControl, ChainlinkClient {
    using Counters for Counters.Counter;
    using Chainlink for Chainlink.Request;

    bytes32 public constant TRACKER_ROLE = keccak256("TRACKER_ROLE");
    bytes32 public constant ORACLE_ROLE = keccak256("ORACLE_ROLE");

    Counters.Counter private _assetIdCounter;

    struct Asset {
        uint256 id;
        string metadata;
        address currentCustodian;
        uint256 timestamp;
        AssetStatus status;
        string location;
        mapping(uint256 => AssetTransfer) transfers;
        uint256 transferCount;
    }

    struct AssetTransfer {
        address from;
        address to;
        uint256 timestamp;
        string location;
        bytes32 proofHash;
    }

    enum AssetStatus {
        Created,
        InTransit,
        Delivered,
        Rejected,
        Recalled
    }

    mapping(uint256 => Asset) private _assets;
    mapping(address => uint256[]) private _custodianAssets;
    mapping(bytes32 => uint256) private _requestToAsset;

    event AssetCreated(
        uint256 indexed assetId,
        address indexed custodian,
        string metadata
    );
    event AssetTransferred(
        uint256 indexed assetId,
        address indexed from,
        address indexed to,
        string location
    );
    event AssetStatusUpdated(uint256 indexed assetId, AssetStatus status);
    event LocationUpdated(uint256 indexed assetId, string location);

    constructor(address _link) {
        _setupRole(DEFAULT_ADMIN_ROLE, msg.sender);
        _setupRole(TRACKER_ROLE, msg.sender);

        if (_link != address(0)) {
            setChainlinkToken(_link);
        }
    }

    /**
     * @dev Creates a new asset in the supply chain
     * @param _metadata IPFS hash or other identifier for asset metadata
     * @param _initialCustodian Address of the initial custodian
     * @param _location Initial location of the asset
     * @return id of the newly created asset
     */
    function createAsset(
        string calldata _metadata,
        address _initialCustodian,
        string calldata _location
    ) external onlyRole(TRACKER_ROLE) returns (uint256) {
        _assetIdCounter.increment();
        uint256 assetId = _assetIdCounter.current();

        Asset storage asset = _assets[assetId];
        asset.id = assetId;
        asset.metadata = _metadata;
        asset.currentCustodian = _initialCustodian;
        asset.timestamp = block.timestamp;
        asset.status = AssetStatus.Created;
        asset.location = _location;
        asset.transferCount = 0;

        _custodianAssets[_initialCustodian].push(assetId);

        emit AssetCreated(assetId, _initialCustodian, _metadata);

        return assetId;
    }

    /**
     * @dev Transfers an asset to a new custodian
     * @param _assetId ID of the asset to transfer
     * @param _to Address of the new custodian
     * @param _location Current location during transfer
     * @param _proofHash Hash of any transfer proof documentation
     */
    function transferAsset(
        uint256 _assetId,
        address _to,
        string calldata _location,
        bytes32 _proofHash
    ) external {
        Asset storage asset = _assets[_assetId];
        require(asset.id == _assetId, "Asset does not exist");
        require(
            asset.currentCustodian == msg.sender,
            "Only current custodian can transfer"
        );
        require(_to != address(0), "Cannot transfer to zero address");

        address from = asset.currentCustodian;

        // Record transfer
        uint256 transferId = asset.transferCount;
        asset.transfers[transferId] = AssetTransfer({
            from: from,
            to: _to,
            timestamp: block.timestamp,
            location: _location,
            proofHash: _proofHash
        });
        asset.transferCount++;

        // Update asset
        asset.currentCustodian = _to;
        asset.timestamp = block.timestamp;
        asset.status = AssetStatus.InTransit;
        asset.location = _location;

        // Update custodian mappings
        // Remove from old custodian's list
        uint256[] storage fromAssets = _custodianAssets[from];
        for (uint256 i = 0; i < fromAssets.length; i++) {
            if (fromAssets[i] == _assetId) {
                // Replace with last element and pop
                fromAssets[i] = fromAssets[fromAssets.length - 1];
                fromAssets.pop();
                break;
            }
        }

        // Add to new custodian's list
        // Check if already in the list (should not happen if logic is correct, but for safety)
        bool alreadyAdded = false;
        for (uint256 i = 0; i < _custodianAssets[_to].length; i++) {
            if (_custodianAssets[_to][i] == _assetId) {
                alreadyAdded = true;
                break;
            }
        }
        if (!alreadyAdded) {
            _custodianAssets[_to].push(_assetId);
        }

        emit AssetTransferred(_assetId, from, _to, _location);
    }

    /**
     * @dev Updates the status of an asset
     * @param _assetId ID of the asset
     * @param _status New status
     */
    function updateAssetStatus(uint256 _assetId, AssetStatus _status) external {
        Asset storage asset = _assets[_assetId];
        require(asset.id == _assetId, "Asset does not exist");
        require(
            asset.currentCustodian == msg.sender ||
                hasRole(TRACKER_ROLE, msg.sender),
            "Only current custodian or tracker can update status"
        );

        asset.status = _status;
        asset.timestamp = block.timestamp;

        emit AssetStatusUpdated(_assetId, _status);
    }

    /**
     * @dev Updates the location of an asset using Chainlink oracle
     * @param _assetId ID of the asset
     * @param _oracle Oracle address
     * @param _jobId Job ID for the location update request
     * @param _fee Fee for the Chainlink request
     */
    function requestLocationUpdate(
        uint256 _assetId,
        address _oracle,
        bytes32 _jobId,
        uint256 _fee
    ) external onlyRole(TRACKER_ROLE) {
        require(_assets[_assetId].id == _assetId, "Asset does not exist");

        Chainlink.Request memory req = buildChainlinkRequest(
            _jobId,
            address(this),
            this.fulfillLocationUpdate.selector
        );

        // Add asset ID as parameter
        req.addUint("assetId", _assetId);

        // Send request
        bytes32 requestId = sendChainlinkRequestTo(_oracle, req, _fee);
        _requestToAsset[requestId] = _assetId;
    }

    /**
     * @dev Callback function for Chainlink location update
     * @param _requestId Request ID
     * @param _location New location string
     */
    function fulfillLocationUpdate(
        bytes32 _requestId,
        string memory _location
    ) external recordChainlinkFulfillment(_requestId) {
        uint256 assetId = _requestToAsset[_requestId];
        require(_assets[assetId].id == assetId, "Asset does not exist");

        _assets[assetId].location = _location;
        _assets[assetId].timestamp = block.timestamp;

        emit LocationUpdated(assetId, _location);
    }

    /**
     * @dev Batch creates multiple assets
     * @param _metadataList List of metadata for each asset
     * @param _custodianList List of initial custodians
     * @param _locationList List of initial locations
     * @return List of created asset IDs
     */
    function batchCreateAssets(
        string[] calldata _metadataList,
        address[] calldata _custodianList,
        string[] calldata _locationList
    ) external onlyRole(TRACKER_ROLE) returns (uint256[] memory) {
        require(
            _metadataList.length == _custodianList.length &&
                _custodianList.length == _locationList.length,
            "Input arrays must have same length"
        );

        uint256[] memory assetIds = new uint256[](_metadataList.length);

        for (uint256 i = 0; i < _metadataList.length; i++) {
            assetIds[i] = createAsset(
                _metadataList[i],
                _custodianList[i],
                _locationList[i]
            );
        }

        return assetIds;
    }

    /**
     * @dev Gets asset details
     * @param _assetId ID of the asset
     * @return id Asset ID
     * @return metadata Asset metadata
     * @return currentCustodian Current custodian address
     * @return timestamp Last update timestamp
     * @return status Current status
     * @return location Current location
     * @return transferCount Number of transfers
     */
    function getAsset(
        uint256 _assetId
    )
        external
        view
        returns (
            uint256 id,
            string memory metadata,
            address currentCustodian,
            uint256 timestamp,
            AssetStatus status,
            string memory location,
            uint256 transferCount
        )
    {
        Asset storage asset = _assets[_assetId];
        require(asset.id == _assetId, "Asset does not exist");

        return (
            asset.id,
            asset.metadata,
            asset.currentCustodian,
            asset.timestamp,
            asset.status,
            asset.location,
            asset.transferCount
        );
    }

    /**
     * @dev Gets transfer details for an asset
     * @param _assetId ID of the asset
     * @param _transferId ID of the transfer
     * @return Transfer details
     */
    function getTransfer(
        uint256 _assetId,
        uint256 _transferId
    )
        external
        view
        returns (
            address from,
            address to,
            uint256 timestamp,
            string memory location,
            bytes32 proofHash
        )
    {
        Asset storage asset = _assets[_assetId];
        require(asset.id == _assetId, "Asset does not exist");
        require(_transferId < asset.transferCount, "Transfer does not exist");

        AssetTransfer storage transfer = asset.transfers[_transferId];

        return (
            transfer.from,
            transfer.to,
            transfer.timestamp,
            transfer.location,
            transfer.proofHash
        );
    }

    /**
     * @dev Gets all assets for a custodian
     * @param _custodian Address of the custodian
     * @return Array of asset IDs
     */
    function getCustodianAssets(
        address _custodian
    ) external view returns (uint256[] memory) {
        return _custodianAssets[_custodian];
    }

    /**
     * @dev Gets the total number of assets
     * @return Current asset count
     */
    function getAssetCount() external view returns (uint256) {
        return _assetIdCounter.current();
    }
}
