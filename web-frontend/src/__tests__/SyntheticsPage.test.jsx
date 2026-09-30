import { ChakraProvider } from "@chakra-ui/react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import Synthetics from "../pages/synthetics/Synthetics";

const mockListSyntheticAssets = jest.fn();
const mockGetSyntheticPosition = jest.fn();
const mockMintSynthetic = jest.fn();

jest.mock("../pages/synthetics.js", () => ({
  listSyntheticAssets: (...args) => mockListSyntheticAssets(...args),
  getSyntheticPosition: (...args) => mockGetSyntheticPosition(...args),
  mintSynthetic: (...args) => mockMintSynthetic(...args),
}));

const mockProvider = {};
const mockAccount = "0x000000000000000000000000000000000000AA";

jest.mock("../lib/web3-config.jsx", () => ({
  useWeb3: () => ({
    isConnected: true,
    provider: mockProvider,
    account: mockAccount,
  }),
}));

jest.mock("recharts", () => ({
  LineChart: ({ children }) => <div>{children}</div>,
  Line: () => null,
  BarChart: ({ children }) => <div>{children}</div>,
  Bar: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }) => <div>{children}</div>,
}));

const REAL_ASSET = {
  assetId: "0x7345544800000000000000000000000000000000000000000000000000000",
  label: "sETH",
  syntheticToken: "0xSynthETH0000000000000000000000000000000",
  collateralToken: "0xCollateralAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
  price18: 1700000000000000000000n,
  priceTimestamp: 1710000000n,
  active: true,
};

const renderPage = () =>
  render(
    <ChakraProvider>
      <Synthetics />
    </ChakraProvider>,
  );

beforeEach(() => {
  jest.clearAllMocks();
  mockGetSyntheticPosition.mockResolvedValue({
    collateral: 0n,
    debt: 0n,
    ratioBPS: 0n,
    isLiquidatable: false,
  });
});

describe("Synthetics page", () => {
  it("shows demo data and a banner when listSyntheticAssets fails", async () => {
    mockListSyntheticAssets.mockRejectedValue(new Error("no provider"));

    renderPage();

    await waitFor(() => expect(mockListSyntheticAssets).toHaveBeenCalled());
    expect(await screen.findByText(/Showing demo data/i)).toBeInTheDocument();
    expect(screen.getAllByText("sETH").length).toBeGreaterThan(0); // demo asset
  });

  it("shows real assets from listSyntheticAssets and hides the demo banner", async () => {
    mockListSyntheticAssets.mockResolvedValue([REAL_ASSET]);

    renderPage();

    await waitFor(() =>
      expect(screen.queryByText(/Showing demo data - connect/i)).toBeNull(),
    );
    expect(screen.getAllByText("sETH").length).toBeGreaterThan(0);
    expect(screen.getByText("$1,700")).toBeInTheDocument();
  });

  it("Trade shows an honest message instead of doing nothing", async () => {
    mockListSyntheticAssets.mockResolvedValue([REAL_ASSET]);
    renderPage();
    await waitFor(() => expect(mockListSyntheticAssets).toHaveBeenCalled());

    const tradeButtons = await screen.findAllByText("Trade");
    fireEvent.click(tradeButtons[0]);

    expect(
      await screen.findByText(/Trading not yet available/i),
    ).toBeInTheDocument();
  });

  it("Mint opens the mint modal and calls the real mintSynthetic on submit", async () => {
    mockListSyntheticAssets.mockResolvedValue([REAL_ASSET]);
    mockMintSynthetic.mockResolvedValue({});

    renderPage();
    await waitFor(() => expect(mockListSyntheticAssets).toHaveBeenCalled());

    const mintButtons = await screen.findAllByText("Mint");
    fireEvent.click(mintButtons[0]);

    const inputs = await screen.findAllByRole("spinbutton");
    // Last two spinbuttons in the DOM belong to the mint modal (collateral,
    // then synthetic amount).
    fireEvent.change(inputs[inputs.length - 2], { target: { value: "300" } });
    fireEvent.change(inputs[inputs.length - 1], { target: { value: "100" } });

    fireEvent.click(screen.getByRole("button", { name: "Mint" }));

    await waitFor(() => expect(mockMintSynthetic).toHaveBeenCalled());
    expect(mockMintSynthetic).toHaveBeenCalledWith(
      mockProvider,
      REAL_ASSET.assetId,
      300000000000000000000n,
      100000000000000000000n,
    );
  });
});
