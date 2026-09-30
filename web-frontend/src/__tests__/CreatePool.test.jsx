import { ChakraProvider } from "@chakra-ui/react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import CreatePool from "../pages/pools/CreatePool";

const mockCreatePoolOnChain = jest.fn();

jest.mock("../lib/web3-config.jsx", () => ({
  useWeb3: () => ({
    isConnected: true,
    createPool: mockCreatePoolOnChain,
    isLoading: false,
    error: null,
  }),
}));

jest.mock("../lib/assets", () => ({
  getAssetRegistry: () => ({
    isMainnetReference: true,
    assets: [
      {
        symbol: "WETH",
        address: "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        decimals: 18,
        oracle: "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
        oracleHeartbeatSeconds: 3600,
      },
      {
        symbol: "WBTC",
        address: "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",
        decimals: 8,
        oracle: "0xF4030086522a5beEa4988F8ca5B36dbC97BeE88c",
        oracleHeartbeatSeconds: 3600,
      },
      {
        // No verified oracle - should be excluded from the dropdown
        // entirely, since createPool requires one oracle per asset.
        symbol: "USDC",
        address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        decimals: 6,
        oracle: null,
        oracleHeartbeatSeconds: null,
      },
    ],
  }),
}));

jest.mock("recharts", () => ({
  PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
}));

const renderCreatePool = () => {
  return render(
    <BrowserRouter>
      <ChakraProvider>
        <CreatePool />
      </ChakraProvider>
    </BrowserRouter>,
  );
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe("CreatePool", () => {
  it("only offers tokens with a verified oracle in the dropdown", () => {
    renderCreatePool();
    const options = screen
      .getAllByRole("option")
      .map((o) => o.getAttribute("value"));
    expect(options).toContain("WETH");
    expect(options).toContain("WBTC");
    expect(options).not.toContain("USDC");
  });

  it("shows the mainnet-reference disclosure banner", () => {
    renderCreatePool();
    expect(
      screen.getByText(/Ethereum Mainnet reference token\/oracle addresses/i),
    ).toBeInTheDocument();
  });

  it("calls the real on-chain createPool with resolved addresses, fee, and oracles", async () => {
    mockCreatePoolOnChain.mockResolvedValue(
      "0x1111111111111111111111111111111111111111111111111111111111111a",
    );

    renderCreatePool();

    // Give both default assets a nonzero amount so the button isn't disabled.
    const amountInputs = screen.getAllByRole("spinbutton");
    fireEvent.change(amountInputs[0], { target: { value: "1" } });
    fireEvent.change(amountInputs[1], { target: { value: "1000" } });

    fireEvent.click(screen.getByRole("button", { name: /create pool/i }));

    await waitFor(() => expect(mockCreatePoolOnChain).toHaveBeenCalledTimes(1));

    const callArg = mockCreatePoolOnChain.mock.calls[0][0];
    // Component seeds its default two assets from availableTokens[0] and
    // [1], which given the mocked registry (oracle-less USDC filtered out)
    // are WETH and WBTC.
    expect(callArg.assets).toEqual([
      "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", // WETH
      "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", // WBTC
    ]);
    expect(callArg.oracles).toEqual([
      "0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419",
      "0xF4030086522a5beEa4988F8ca5B36dbC97BeE88c",
    ]);
    expect(callArg.heartbeats).toEqual([3600n, 3600n]);
    expect(callArg.weights).toHaveLength(2);
    expect(typeof callArg.fee).toBe("bigint");
    expect(typeof callArg.amplification).toBe("bigint");
  });
});
