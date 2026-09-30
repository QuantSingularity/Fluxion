import { ethers } from "ethers";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { env } from "./env";

/**
 * ABI for LiquidityPoolManager.sol.
 *
 * Must match code/blockchain/contracts/LiquidityPoolManager.sol exactly.
 * `createPool` is gated by POOL_ADMIN_ROLE on-chain - calls from a wallet
 * that doesn't hold that role will revert; see createPool() below for how
 * that's surfaced to the caller.
 */
const POOL_MANAGER_ABI = [
  "event PoolCreated(bytes32 indexed poolId, address[] assets, uint256[] weights)",
  "event LiquidityAdded(bytes32 indexed poolId, address indexed provider, uint256 amount)",
  "event LiquidityRemoved(bytes32 indexed poolId, address indexed provider, uint256 amount)",
  "event PoolActivated(bytes32 indexed poolId)",
  "event PoolDeactivated(bytes32 indexed poolId)",

  "function createPool(address[] assets, uint256[] weights, uint256 fee, uint256 amplification, address[] oracles, uint256[] heartbeats) external",
  "function addLiquidity(bytes32 poolId, uint256[] amounts) external",
  "function removeLiquidity(bytes32 poolId, uint256 percentage) external",
  "function activatePool(bytes32 poolId) external",
  "function deactivatePool(bytes32 poolId) external",
  "function updatePoolFee(bytes32 poolId, uint256 newFee) external",

  "function getPool(bytes32 poolId) external view returns (address[] assets, uint256[] weights, uint256 fee, uint256 amplification, bool active, uint256 totalLiquidity)",
  "function getUserLiquidity(bytes32 poolId, address user) external view returns (uint256)",
  "function getUserPoolCount(address user) external view returns (uint256)",
  "function getUserPoolAtIndex(address user, uint256 index) external view returns (bytes32)",
  "function MAX_FEE() external view returns (uint256)",
  "function POOL_ADMIN_ROLE() external view returns (bytes32)",
  "function hasRole(bytes32 role, address account) external view returns (bool)",
];

function getPoolManagerContract(providerOrSigner) {
  const address = env.POOL_MANAGER_ADDRESS();
  return new ethers.Contract(address, POOL_MANAGER_ABI, providerOrSigner);
}

/**
 * Surfaces a readable message for the common on-chain revert reasons
 * createPool can hit, instead of ethers' raw "execution reverted" text.
 */
function describePoolTxError(err) {
  const raw =
    err?.shortMessage ||
    err?.reason ||
    err?.error?.message ||
    err?.message ||
    "";
  if (/AccessControl/i.test(raw) || /missing role/i.test(raw)) {
    return "This wallet doesn't have POOL_ADMIN_ROLE, so it can't create pools on-chain.";
  }
  if (/Fee too high/i.test(raw))
    return "Swap fee exceeds the pool manager's MAX_FEE.";
  if (/length mismatch/i.test(raw)) {
    return "Assets, weights, oracles, and heartbeats must all be the same length.";
  }
  if (/Minimum 2 assets/i.test(raw)) return "A pool needs at least 2 assets.";
  if (/user rejected/i.test(raw) || err?.code === "ACTION_REJECTED") {
    return "Transaction rejected in wallet.";
  }
  return raw || "Transaction failed.";
}

const Web3Context = createContext(null);

export function Web3Provider({ children }) {
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  const [account, setAccount] = useState(null);
  const [contracts, setContracts] = useState({});
  const [pools, setPools] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [chainId, setChainId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const initializeContracts = useCallback((prov) => {
    try {
      const poolManager = getPoolManagerContract(prov);
      // "factory" kept as an alias for the same pool manager contract for
      // backward compatibility with any existing callers; there is only one
      // real contract here (LiquidityPoolManager.sol) - SyntheticAssetFactory
      // integration lives separately in pages/synthetics.js since it has an
      // entirely different ABI and isn't a pool manager.
      setContracts({ poolManager, factory: poolManager });
    } catch (err) {
      console.error("Error initializing contracts:", err);
    }
  }, []);

  const fetchPools = useCallback(async (address, prov) => {
    if (!address || !prov) return;
    setIsLoading(true);
    try {
      const poolManager = getPoolManagerContract(prov);
      const count = await poolManager.getUserPoolCount(address);
      const poolIds = await Promise.all(
        Array.from({ length: Number(count) }, (_, i) =>
          poolManager.getUserPoolAtIndex(address, i),
        ),
      );
      const details = await Promise.all(
        poolIds.map(async (poolId) => {
          const [assets, weights, fee, amplification, active, totalLiquidity] =
            await poolManager.getPool(poolId);
          return {
            id: poolId,
            assets: [...assets],
            weights: weights.map((w) => w.toString()),
            fee: fee.toString(),
            amplification: amplification.toString(),
            active,
            totalLiquidity: totalLiquidity.toString(),
          };
        }),
      );
      setPools(details);
    } catch (err) {
      console.error("Error fetching pools:", err);
      setError(describePoolTxError(err));
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleAccountsChanged = useCallback(
    async (accounts, currentProvider) => {
      if (!accounts || accounts.length === 0) {
        setAccount(null);
        setSigner(null);
        setIsConnected(false);
        setPools([]);
      } else {
        const addr =
          typeof accounts[0] === "string" ? accounts[0] : accounts[0]?.address;
        if (!addr) return;
        setAccount(addr);
        try {
          const prov = currentProvider;
          if (prov) {
            const s = await prov.getSigner();
            setSigner(s);
          }
          setIsConnected(true);
          fetchPools(addr, prov);
        } catch (err) {
          console.error("Error setting signer:", err);
        }
      }
    },
    [fetchPools],
  );

  useEffect(() => {
    let mounted = true;
    const eth = typeof window !== "undefined" ? window.ethereum : undefined;
    const onAccountsChangedRef = { current: null };
    const onChainChanged = () => window.location.reload();

    const init = async () => {
      if (!eth) {
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const prov = new ethers.BrowserProvider(eth);
        if (!mounted) return;
        setProvider(prov);

        const network = await prov.getNetwork();
        if (!mounted) return;
        setChainId(network.chainId);

        initializeContracts(prov);

        const onAccountsChanged = (accs) => handleAccountsChanged(accs, prov);
        onAccountsChangedRef.current = onAccountsChanged;
        eth.on("accountsChanged", onAccountsChanged);
        eth.on("chainChanged", onChainChanged);

        const accounts = await prov.listAccounts();
        if (!mounted) return;
        if (accounts.length > 0) {
          handleAccountsChanged(accounts, prov);
        }
      } catch (err) {
        console.error("Error initializing web3:", err);
        if (mounted)
          setError("Failed to initialize Web3. Please check your wallet.");
      } finally {
        if (mounted) setIsLoading(false);
      }
    };

    init();
    return () => {
      mounted = false;
      // Remove only the handlers this effect registered, so multiple
      // mounts don't clobber each other's listeners (removeAllListeners
      // would do exactly that).
      try {
        if (eth?.removeListener) {
          if (onAccountsChangedRef.current) {
            eth.removeListener("accountsChanged", onAccountsChangedRef.current);
          }
          eth.removeListener("chainChanged", onChainChanged);
        }
      } catch (err) {
        console.error("Error removing wallet listeners:", err);
      }
    };
  }, [handleAccountsChanged, initializeContracts]);

  const connectWallet = async () => {
    setIsLoading(true);
    setError(null);
    if (typeof window === "undefined" || !window.ethereum) {
      setError("No Ethereum wallet detected. Please install MetaMask.");
      setIsLoading(false);
      return;
    }
    try {
      const accounts = await window.ethereum.request({
        method: "eth_requestAccounts",
      });
      const prov = provider || new ethers.BrowserProvider(window.ethereum);
      if (!provider) setProvider(prov);
      handleAccountsChanged(accounts, prov);
    } catch (err) {
      console.error("Error connecting wallet:", err);
      setError("Failed to connect wallet. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Create a pool on-chain via LiquidityPoolManager.createPool.
   *
   * Requires the connected wallet to hold POOL_ADMIN_ROLE - this is an
   * admin-gated operation on-chain, not something any connected wallet can
   * do, so callers should expect and surface the revert this throws for a
   * non-admin wallet.
   *
   * @param {{assets: string[], weights: (string|bigint)[], fee: string|bigint, amplification: string|bigint, oracles: string[], heartbeats: (string|bigint)[]}} poolData
   *   All addresses are real on-chain ERC-20/oracle addresses (not symbols);
   *   fee/weights/heartbeats are raw values matching the contract's units
   *   (fee/weights are 18-decimal fixed point, heartbeats are seconds).
   */
  const createPool = async (poolData) => {
    if (!isConnected || !signer) {
      setError("Please connect your wallet first");
      return null;
    }
    setIsLoading(true);
    setError(null);
    try {
      const poolManager = getPoolManagerContract(signer);
      const tx = await poolManager.createPool(
        poolData.assets,
        poolData.weights,
        poolData.fee,
        poolData.amplification,
        poolData.oracles,
        poolData.heartbeats,
      );
      const receipt = await tx.wait();

      const createdEvent = receipt.logs
        .map((log) => {
          try {
            return poolManager.interface.parseLog(log);
          } catch {
            return null;
          }
        })
        .find((parsed) => parsed?.name === "PoolCreated");
      const poolId = createdEvent?.args?.poolId ?? null;

      await fetchPools(account, provider);
      return poolId;
    } catch (err) {
      console.error("Error creating pool:", err);
      setError(describePoolTxError(err));
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    provider,
    signer,
    account,
    contracts,
    pools,
    isConnected,
    chainId,
    isLoading,
    error,
    connectWallet,
    fetchPools,
    createPool,
  };

  return <Web3Context.Provider value={value}>{children}</Web3Context.Provider>;
}

export function useWeb3() {
  const context = useContext(Web3Context);
  if (!context) {
    throw new Error("useWeb3 must be used within a Web3Provider");
  }
  return context;
}
