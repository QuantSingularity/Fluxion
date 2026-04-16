// SPDX-License-Identifier: AGPL-3.0
pragma solidity 0.8.19;

import "forge-std/Test.sol";
import "../contracts/LiquidityPoolManager.sol";

contract LiquidityPoolTest is Test {
    LiquidityPoolManager pool;
    address[] assets;
    uint256[] weights;

    function setUp() public {
        pool = new LiquidityPoolManager();
        assets = [address(1), address(2)];
        weights = [5e17, 5e17]; // 50/50 weights
    }

    function testPoolCreation() public {
        pool.createPool(assets, weights, 0.003e18, 100);
        bytes32 poolId = keccak256(abi.encode(assets, weights));
        assertEq(pool.pools(poolId).fee, 0.003e18);
    }
}
