import { act, renderHook, waitFor } from "@testing-library/react";
import { Web3Provider, useWeb3 } from "../lib/web3-config.jsx";

// Mock ethers.Contract so we can assert exactly which on-chain functions
// createPool/fetchPools call and with what arguments, without needing a
// real chain. ethers.BrowserProvider is left real (constructible against
// the mocked window.ethereum from setupTests.js).
const mockCreatePool = jest.fn();
const mockGetUserPoolCount = jest.fn();
const mockGetUserPoolAtIndex = jest.fn();
const mockGetPool = jest.fn();
const mockParseLog = jest.fn();
const mockAddress = "0x000000000000000000000000000000000000AA";
const mockSigner = { getAddress: async () => mockAddress };

jest.mock("ethers", () => {
  const actual = jest.requireActual("ethers");
  const MockContract = jest.fn().mockImplementation(() => ({
    createPool: mockCreatePool,
    getUserPoolCount: mockGetUserPoolCount,
    getUserPoolAtIndex: mockGetUserPoolAtIndex,
    getPool: mockGetPool,
    interface: { parseLog: mockParseLog },
  }));
  const MockBrowserProvider = jest.fn().mockImplementation(() => ({
    getNetwork: async () => ({ chainId: 1n }),
    listAccounts: async () => [],
    getSigner: async () => mockSigner,
  }));
  return {
    ...actual,
    // web3-config.jsx does `import { ethers } from "ethers"` and calls
    // `ethers.Contract` / `ethers.BrowserProvider` off that namespace
    // object, not the package's top-level named exports - both need
    // overriding for the mock to actually take effect.
    Contract: MockContract,
    BrowserProvider: MockBrowserProvider,
    ethers: {
      ...actual.ethers,
      Contract: MockContract,
      BrowserProvider: MockBrowserProvider,
    },
  };
});

const TEST_ADDRESS = mockAddress;
const TEST_POOL_ID =
  "0x1111111111111111111111111111111111111111111111111111111111111a";

function wrapper({ children }) {
  return <Web3Provider>{children}</Web3Provider>;
}

async function connectAndWait(result) {
  await act(async () => {
    window.ethereum.request.mockResolvedValueOnce([TEST_ADDRESS]);
    await result.current.connectWallet();
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  window.ethereum.request.mockReset();
  mockGetUserPoolCount.mockResolvedValue(0n);
});

describe("useWeb3", () => {
  it("throws when used outside a Web3Provider", () => {
    const { result } = renderHook(() => {
      try {
        return useWeb3();
      } catch (e) {
        return e;
      }
    });
    expect(result.current).toBeInstanceOf(Error);
  });

  it("createPool calls the real contract with the exact 6 createPool args, in order", async () => {
    const { result } = renderHook(() => useWeb3(), { wrapper });
    await connectAndWait(result);

    mockCreatePool.mockResolvedValue({
      wait: jest.fn().mockResolvedValue({ logs: [] }),
    });

    const poolData = {
      assets: ["0xAsset1", "0xAsset2"],
      weights: [500000000000000000n, 500000000000000000n],
      fee: 3000000000000000n,
      amplification: 100n,
      oracles: ["0xOracle1", "0xOracle2"],
      heartbeats: [3600n, 3600n],
    };

    await act(async () => {
      await result.current.createPool(poolData);
    });

    expect(mockCreatePool).toHaveBeenCalledWith(
      poolData.assets,
      poolData.weights,
      poolData.fee,
      poolData.amplification,
      poolData.oracles,
      poolData.heartbeats,
    );
  });

  it("createPool parses the PoolCreated event to return the real poolId", async () => {
    const { result } = renderHook(() => useWeb3(), { wrapper });
    await connectAndWait(result);

    mockCreatePool.mockResolvedValue({
      wait: jest.fn().mockResolvedValue({ logs: [{ fake: "log" }] }),
    });
    mockParseLog.mockReturnValue({
      name: "PoolCreated",
      args: { poolId: TEST_POOL_ID },
    });

    let returnedId;
    await act(async () => {
      returnedId = await result.current.createPool({
        assets: ["0xA", "0xB"],
        weights: [1n, 1n],
        fee: 1n,
        amplification: 1n,
        oracles: ["0xO1", "0xO2"],
        heartbeats: [1n, 1n],
      });
    });

    expect(returnedId).toBe(TEST_POOL_ID);
  });

  it("createPool surfaces a readable error for a POOL_ADMIN_ROLE revert", async () => {
    const { result } = renderHook(() => useWeb3(), { wrapper });
    await connectAndWait(result);

    mockCreatePool.mockRejectedValue({
      shortMessage:
        "execution reverted: AccessControl: account 0x... is missing role",
    });

    await act(async () => {
      await result.current.createPool({
        assets: ["0xA", "0xB"],
        weights: [1n, 1n],
        fee: 1n,
        amplification: 1n,
        oracles: ["0xO1", "0xO2"],
        heartbeats: [1n, 1n],
      });
    });

    expect(result.current.error).toMatch(/POOL_ADMIN_ROLE/);
  });

  it("createPool refuses to run without a connected wallet", async () => {
    const { result } = renderHook(() => useWeb3(), { wrapper });

    let returned;
    await act(async () => {
      returned = await result.current.createPool({ assets: [], weights: [] });
    });

    expect(returned).toBeNull();
    expect(mockCreatePool).not.toHaveBeenCalled();
    expect(result.current.error).toMatch(/connect your wallet/i);
  });

  it("fetchPools enumerates the user's real pools via getUserPoolCount/getUserPoolAtIndex/getPool", async () => {
    mockGetUserPoolCount.mockResolvedValue(2n);
    mockGetUserPoolAtIndex.mockImplementation((_addr, i) =>
      Promise.resolve(`0xpool${i}`),
    );
    mockGetPool.mockImplementation((poolId) =>
      Promise.resolve([
        ["0xAsset1", "0xAsset2"],
        [500000000000000000n, 500000000000000000n],
        3000000000000000n,
        100n,
        true,
        0n,
      ]),
    );

    const { result } = renderHook(() => useWeb3(), { wrapper });
    await connectAndWait(result);

    await waitFor(() => expect(result.current.pools).toHaveLength(2));
    expect(mockGetUserPoolAtIndex).toHaveBeenCalledWith(TEST_ADDRESS, 0);
    expect(mockGetUserPoolAtIndex).toHaveBeenCalledWith(TEST_ADDRESS, 1);
    expect(result.current.pools[0].assets).toEqual(["0xAsset1", "0xAsset2"]);
    expect(result.current.pools[0].active).toBe(true);
  });
});
