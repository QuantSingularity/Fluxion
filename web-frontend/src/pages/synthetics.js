import { ethers } from "ethers";
import { env, ZERO_ADDRESS as ZERO } from "../lib/env";

/**
 * ABI for SyntheticAssetFactory.sol.
 *
 * This must match code/blockchain/contracts/SyntheticAssetFactory.sol
 * exactly - asset ids are `bytes32` (not `string`), and every position
 * operation (mint/burn/liquidate) takes the numeric collateral/synthetic
 * amounts as raw uint256 (wei-scale, 18 decimals), not human-readable
 * numbers. Callers are responsible for converting with `ethers.parseUnits`
 * before calling these functions and `ethers.formatUnits` after reading
 * results back.
 */
export const SYNTHETIC_ABI = [
  // ── Events ──────────────────────────────────────────────────────────────
  "event SyntheticAssetRegistered(bytes32 indexed assetId, address syntheticToken, address collateralToken, address priceOracle)",
  "event Minted(bytes32 indexed assetId, address indexed user, uint256 collateralDeposited, uint256 syntheticMinted, uint256 collateralRatioBPS)",
  "event Burned(bytes32 indexed assetId, address indexed user, uint256 collateralReturned, uint256 syntheticBurned)",
  "event Liquidated(bytes32 indexed assetId, address indexed user, address indexed liquidator, uint256 debtRepaid, uint256 collateralSeized)",
  "event PriceUpdated(bytes32 indexed assetId, uint256 price, uint256 blockTimestamp)",

  // ── Admin (owner-only) ──────────────────────────────────────────────────
  "function createSynthetic(bytes32 assetId, address collateralToken, address priceOracle, address clOracle, bytes32 clJobId, uint256 clFee) external",
  "function owner() external view returns (address)",

  // ── Position management (any user) ──────────────────────────────────────
  "function mintSynthetic(bytes32 assetId, uint256 collateralAmount, uint256 syntheticAmount) external",
  "function burnSynthetic(bytes32 assetId, uint256 syntheticAmount) external",
  "function liquidate(bytes32 assetId, address user, uint256 syntheticRepaid) external",
  "function refreshPrice(bytes32 assetId) external",

  // ── Views ────────────────────────────────────────────────────────────────
  "function getPosition(bytes32 assetId, address user) external view returns (uint256 collateral, uint256 debt, uint256 ratioBPS, bool isLiquidatable)",
  "function getAssetCount() external view returns (uint256)",
  "function getOraclePrice(bytes32 assetId) external view returns (uint256 price18, uint256 updatedAt)",
  "function collateralOf(bytes32 assetId) external view returns (address)",
  "function syntheticOf(bytes32 assetId) external view returns (address)",
  "function assetIds(uint256 index) external view returns (bytes32)",
  "function syntheticAssets(bytes32 assetId) external view returns (address syntheticToken, address collateralToken, address priceOracle, address clOracle, bytes32 clJobId, uint256 clFee, uint256 price, uint256 priceTimestamp, bool active)",
];

function getFactoryContract(providerOrSigner) {
  const factoryAddress = env.FACTORY_ADDRESS();
  if (!factoryAddress || factoryAddress === ZERO) {
    throw new Error("VITE_FACTORY_ADDRESS not configured");
  }
  return new ethers.Contract(factoryAddress, SYNTHETIC_ABI, providerOrSigner);
}

/**
 * Register a new synthetic asset type. Owner-only on-chain - will revert
 * for any other caller.
 *
 * @param {ethers.BrowserProvider} provider
 * @param {{assetId: string, collateralToken: string, priceOracle: string, clOracle: string, clJobId: string, clFee: bigint|number|string}} params
 *   assetId/clJobId are bytes32 - pass a 32-byte hex string, or use
 *   ethers.encodeBytes32String(...) for short human-readable ids.
 */
export async function createSyntheticAsset(provider, params) {
  if (!provider || !params) {
    throw new Error("Missing provider or params for createSyntheticAsset");
  }

  const signer = await provider.getSigner();
  const factory = getFactoryContract(signer);

  try {
    const tx = await factory.createSynthetic(
      params.assetId,
      params.collateralToken,
      params.priceOracle,
      params.clOracle,
      params.clJobId,
      params.clFee,
    );
    return tx.wait();
  } catch (error) {
    console.error("Error creating synthetic asset:", error);
    throw error;
  }
}

/**
 * Deposit collateral and mint synthetic tokens against it.
 *
 * @param {ethers.BrowserProvider} provider
 * @param {string} assetId bytes32 asset id
 * @param {bigint|string} collateralAmount raw wei-scale amount (already
 *   scaled to the collateral token's decimals)
 * @param {bigint|string} syntheticAmount raw wei-scale amount to mint
 */
export async function mintSynthetic(
  provider,
  assetId,
  collateralAmount,
  syntheticAmount,
) {
  if (!provider) throw new Error("Missing provider for mintSynthetic");
  const signer = await provider.getSigner();
  const factory = getFactoryContract(signer);

  try {
    const tx = await factory.mintSynthetic(
      assetId,
      collateralAmount,
      syntheticAmount,
    );
    return tx.wait();
  } catch (error) {
    console.error("Error minting synthetic:", error);
    throw error;
  }
}

/**
 * Burn synthetic tokens and reclaim proportional collateral.
 *
 * @param {ethers.BrowserProvider} provider
 * @param {string} assetId bytes32 asset id
 * @param {bigint|string} syntheticAmount raw wei-scale amount to burn
 */
export async function burnSynthetic(provider, assetId, syntheticAmount) {
  if (!provider) throw new Error("Missing provider for burnSynthetic");
  const signer = await provider.getSigner();
  const factory = getFactoryContract(signer);

  try {
    const tx = await factory.burnSynthetic(assetId, syntheticAmount);
    return tx.wait();
  } catch (error) {
    console.error("Error burning synthetic:", error);
    throw error;
  }
}

/**
 * Liquidate part of another user's undercollateralised position. The
 * caller must hold (and have approved the factory to spend) at least
 * `syntheticRepaid` of the asset's synthetic token.
 *
 * @param {ethers.BrowserProvider} provider
 * @param {string} assetId bytes32 asset id
 * @param {string} user address of the position owner being liquidated
 * @param {bigint|string} syntheticRepaid raw wei-scale debt amount to repay
 */
export async function liquidatePosition(
  provider,
  assetId,
  user,
  syntheticRepaid,
) {
  if (!provider) throw new Error("Missing provider for liquidatePosition");
  const signer = await provider.getSigner();
  const factory = getFactoryContract(signer);

  try {
    const tx = await factory.liquidate(assetId, user, syntheticRepaid);
    return tx.wait();
  } catch (error) {
    console.error("Error liquidating position:", error);
    throw error;
  }
}

/**
 * Read a user's position for a given synthetic asset.
 *
 * @param {ethers.BrowserProvider} provider
 * @param {string} assetId bytes32 asset id
 * @param {string} user address to look up
 * @returns {Promise<{collateral: bigint, debt: bigint, ratioBPS: bigint, isLiquidatable: boolean}>}
 */
export async function getSyntheticPosition(provider, assetId, user) {
  if (!provider) throw new Error("Missing provider for getSyntheticPosition");
  const factory = getFactoryContract(provider);

  const [collateral, debt, ratioBPS, isLiquidatable] =
    await factory.getPosition(assetId, user);
  return { collateral, debt, ratioBPS, isLiquidatable };
}

/**
 * Read the current oracle price for a synthetic asset (18-decimal USD) and
 * when it was last updated (unix seconds).
 *
 * @param {ethers.BrowserProvider} provider
 * @param {string} assetId bytes32 asset id
 * @returns {Promise<{price18: bigint, updatedAt: bigint}>}
 */
export async function getSyntheticOraclePrice(provider, assetId) {
  if (!provider)
    throw new Error("Missing provider for getSyntheticOraclePrice");
  const factory = getFactoryContract(provider);
  const [price18, updatedAt] = await factory.getOraclePrice(assetId);
  return { price18, updatedAt };
}

/**
 * Attempts to decode a bytes32 asset id back into the short human-readable
 * string it was likely created from via `ethers.encodeBytes32String`. Not
 * every assetId is guaranteed to be a valid encoded string (an id could
 * just as easily be a keccak256 hash), so this falls back to the raw hex.
 *
 * @param {string} assetId bytes32 hex string
 * @returns {string}
 */
export function decodeAssetIdLabel(assetId) {
  try {
    const decoded = ethers.decodeBytes32String(assetId);
    return decoded || assetId;
  } catch {
    return assetId;
  }
}

/**
 * Enumerate every synthetic asset actually registered on-chain, using the
 * factory's public `assetIds` array and `syntheticAssets` mapping - no
 * subgraph or off-chain indexer needed. This is real on-chain state, unlike
 * any hardcoded/demo asset list a page might otherwise show.
 *
 * @param {ethers.BrowserProvider} provider
 * @returns {Promise<Array<{assetId: string, label: string, syntheticToken: string, collateralToken: string, price18: bigint, priceTimestamp: bigint, active: boolean}>>}
 */
export async function listSyntheticAssets(provider) {
  if (!provider) throw new Error("Missing provider for listSyntheticAssets");
  const factory = getFactoryContract(provider);

  const count = await factory.getAssetCount();
  const ids = await Promise.all(
    Array.from({ length: Number(count) }, (_, i) => factory.assetIds(i)),
  );

  return Promise.all(
    ids.map(async (assetId) => {
      const [
        syntheticToken,
        collateralToken,
        ,
        ,
        ,
        ,
        price,
        priceTimestamp,
        active,
      ] = await factory.syntheticAssets(assetId);
      return {
        assetId,
        label: decodeAssetIdLabel(assetId),
        syntheticToken,
        collateralToken,
        price18: price,
        priceTimestamp,
        active,
      };
    }),
  );
}
