/**
 * Token / price-feed registry for pool creation and synthetic asset UI.
 *
 * IMPORTANT: this app's contracts (FACTORY_ADDRESS, POOL_MANAGER_ADDRESS in
 * env.js) can be deployed to any network - mainnet, a testnet, or a local
 * Anvil/Hardhat chain - and that choice isn't hardcoded anywhere else in
 * this codebase. Hardcoding real Ethereum mainnet token addresses as the
 * *default* registry would be actively wrong (and dangerous - silent calls
 * to unrelated contracts at those addresses) on any other network. So:
 *
 *   - `getAssetRegistry()` first checks VITE_ASSET_REGISTRY_JSON, a
 *     deployment-specific JSON array the operator provides (same pattern
 *     as VITE_FACTORY_ADDRESS / VITE_POOL_MANAGER_ADDRESS in env.js).
 *   - If unset, it falls back to `MAINNET_REFERENCE_ASSETS` below, but only
 *     as an opt-in convenience surfaced in the UI as "Ethereum Mainnet
 *     reference - verify these match your connected network" - never
 *     silently assumed to be correct for whatever chain the wallet is
 *     actually on.
 *
 * Each entry: { symbol, address, decimals, oracle, oracleHeartbeatSeconds }
 *   - address: ERC-20 token contract address (used as the `assets[]` entry
 *     for LiquidityPoolManager.createPool / as collateralToken for
 *     SyntheticAssetFactory.createSynthetic)
 *   - oracle: Chainlink AggregatorV3Interface price feed address for that
 *     token, used as the `oracles[]` entry for createPool
 *   - oracleHeartbeatSeconds: that feed's staleness threshold, used as the
 *     `heartbeats[]` entry for createPool
 *
 * MAINNET_REFERENCE_ASSETS only includes entries independently verified
 * against Etherscan (tokens) and Chainlink's own data.chain.link pages
 * (price feeds) at the time this was written - deliberately incomplete
 * rather than including anything unverified.
 */

export const MAINNET_REFERENCE_ASSETS = [
  {
    symbol: "WETH",
    address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    decimals: 18,
    oracle: "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419", // Chainlink ETH/USD
    oracleHeartbeatSeconds: 3600,
  },
  {
    symbol: "WBTC",
    address: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
    decimals: 8,
    oracle: "0xF4030086522a5beEa4988F8ca5B36dbC97BeE88c", // Chainlink BTC/USD
    oracleHeartbeatSeconds: 3600,
  },
  {
    symbol: "USDC",
    address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    decimals: 6,
    // No independently-verified Chainlink USDC/USD feed address on hand;
    // leave unset rather than guess. A pool/synthetic using USDC needs a
    // real oracle address supplied manually until this is filled in.
    oracle: null,
    oracleHeartbeatSeconds: null,
  },
  {
    symbol: "DAI",
    address: "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    decimals: 18,
    // Same caveat as USDC above.
    oracle: null,
    oracleHeartbeatSeconds: null,
  },
];

function readRegistryEnvVar() {
  const raw =
    (typeof process !== "undefined" &&
      process.env &&
      process.env.VITE_ASSET_REGISTRY_JSON) ||
    undefined;
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return null;
    return parsed;
  } catch {
    console.error(
      "VITE_ASSET_REGISTRY_JSON is set but is not valid JSON; ignoring it.",
    );
    return null;
  }
}

/**
 * Returns the asset registry to use for this deployment.
 *
 * @param {{ warnIfFallback?: boolean }} [options]
 * @returns {{ assets: Array, isMainnetReference: boolean }}
 */
export function getAssetRegistry(options = {}) {
  const configured = readRegistryEnvVar();
  if (configured) {
    return { assets: configured, isMainnetReference: false };
  }
  if (options.warnIfFallback !== false) {
    console.warn(
      "VITE_ASSET_REGISTRY_JSON is not configured for this deployment; " +
        "falling back to Ethereum Mainnet reference addresses. These will " +
        "be WRONG if this app is connected to a testnet or local chain - " +
        "set VITE_ASSET_REGISTRY_JSON to your deployment's real token and " +
        "oracle addresses before creating pools or synthetic assets.",
    );
  }
  return { assets: MAINNET_REFERENCE_ASSETS, isMainnetReference: true };
}
