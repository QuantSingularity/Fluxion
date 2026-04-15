import { ethers } from "ethers";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

const POOL_MANAGER_ABI = [
  {
    anonymous: false,
    inputs: [
      {
        indexed: true,
        internalType: "bytes32",
        name: "poolId",
        type: "bytes32",
      },
      {
        indexed: false,
        internalType: "address[]",
        name: "assets",
        type: "address[]",
      },
      {
        indexed: false,
        internalType: "uint256[]",
        name: "weights",
        type: "uint256[]",
      },
    ],
    name: "PoolCreated",
    type: "event",
  },
];

const FACTORY_ABI = [
  {
    inputs: [
      { internalType: "address[]", name: "assets", type: "address[]" },
      { internalType: "uint256[]", name: "weights", type: "uint256[]" },
      { internalType: "uint256", name: "swapFee", type: "uint256" },
      {
        internalType: "uint256",
        name: "amplificationParameter",
        type: "uint256",
      },
    ],
    name: "createPool",
    outputs: [{ internalType: "bytes32", name: "", type: "bytes32" }],
    stateMutability: "nonpayable",
    type: "function",
  },
];

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
      const poolManagerAddress =
        (typeof import.meta !== "undefined" &&
          import.meta.env?.VITE_POOL_MANAGER_ADDRESS) ||
        "0x0000000000000000000000000000000000000000";
      const factoryAddress =
        (typeof import.meta !== "undefined" &&
          import.meta.env?.VITE_FACTORY_ADDRESS) ||
        "0x0000000000000000000000000000000000000000";
      const poolManager = new ethers.Contract(
        poolManagerAddress,
        POOL_MANAGER_ABI,
        prov,
      );
      const factory = new ethers.Contract(factoryAddress, FACTORY_ABI, prov);
      setContracts({ poolManager, factory });
    } catch (err) {
      console.error("Error initializing contracts:", err);
    }
  }, []);

  const fetchPools = useCallback(async (address) => {
    if (!address) return;
    setIsLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 500));
      const mockPools = [
        {
          id: `pool-${address.substring(0, 8)}-1`,
          assets: ["ETH", "USDC"],
          weights: [50, 50],
          fee: 0.3,
          amplification: 100,
          tvl: "$1.2M",
          apy: "4.5%",
        },
        {
          id: `pool-${address.substring(0, 8)}-2`,
          assets: ["ETH", "WBTC"],
          weights: [40, 60],
          fee: 0.25,
          amplification: 85,
          tvl: "$850K",
          apy: "5.2%",
        },
      ];
      setPools(mockPools);
    } catch (err) {
      console.error("Error fetching pools:", err);
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
          fetchPools(addr);
        } catch (err) {
          console.error("Error setting signer:", err);
        }
      }
    },
    [fetchPools],
  );

  useEffect(() => {
    let mounted = true;
    const init = async () => {
      if (typeof window === "undefined" || !window.ethereum) {
        return;
      }
      setIsLoading(true);
      setError(null);
      try {
        const prov = new ethers.BrowserProvider(window.ethereum);
        if (!mounted) return;
        setProvider(prov);

        const network = await prov.getNetwork();
        if (!mounted) return;
        setChainId(network.chainId);

        initializeContracts(prov);

        const onAccountsChanged = (accs) => handleAccountsChanged(accs, prov);
        window.ethereum.on("accountsChanged", onAccountsChanged);
        window.ethereum.on("chainChanged", () => window.location.reload());

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
      try {
        if (window.ethereum?.removeAllListeners) {
          window.ethereum.removeAllListeners("accountsChanged");
        }
      } catch (_) {}
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

  const createPool = async (poolData) => {
    if (!isConnected || !signer) {
      setError("Please connect your wallet first");
      return null;
    }
    setIsLoading(true);
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      const newPool = {
        id: `pool-${account.substring(0, 8)}-${pools.length + 1}`,
        assets: poolData.assets,
        weights: poolData.weights,
        fee: poolData.fee,
        amplification: poolData.amplification,
        tvl: "$0",
        apy: "0%",
      };
      setPools((prev) => [...prev, newPool]);
      return newPool.id;
    } catch (err) {
      console.error("Error creating pool:", err);
      setError("Failed to create pool. Please try again.");
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
