import { ChakraProvider } from "@chakra-ui/react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import MlRiskPanel from "../components/analytics/MlRiskPanel";
import { mlAPI } from "../services/api";

jest.mock("../services/api", () => ({
  mlAPI: {
    getRiskOverview: jest.fn(),
    getPoolForecast: jest.fn(),
  },
}));

const overview = {
  overall_risk: 0.52,
  risk_level: "medium",
  data_source: "simulated_market_snapshot",
  factors: {
    market_risk: 0.4,
    credit_risk: 0.7,
    liquidity_risk: 0.2,
    operational_risk: 0.1,
    compliance_risk: 0.9,
  },
  items: [
    {
      entity_type: "pool",
      entity_id: "pool-a",
      name: "synBTC/synUSD",
      risk_level: "high",
      primary_driver: "credit_risk",
    },
    {
      entity_type: "pool",
      entity_id: "pool-b",
      name: "synETH/synUSD",
      risk_level: "low",
      primary_driver: "market_risk",
    },
    {
      entity_type: "synthetic",
      entity_id: "syn-eth",
      name: "Synthetic Ethereum",
      risk_level: "medium",
      primary_driver: "market_risk",
    },
  ],
};

const forecast = (id) => ({
  current_liquidity: 1000000,
  predicted_liquidity: [1010000, 1020000, id === "pool-b" ? 900000 : 1030000],
  predicted_change_pct: [1, 2, id === "pool-b" ? -10 : 3],
  lower_bound: [990000, 980000, 850000],
  upper_bound: [1030000, 1050000, 1100000],
  confidence_level: 0.9,
});

const renderPanel = () =>
  render(
    <ChakraProvider>
      <MlRiskPanel />
    </ChakraProvider>,
  );

describe("MlRiskPanel", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mlAPI.getRiskOverview.mockResolvedValue({
      data: { success: true, data: overview },
    });
    mlAPI.getPoolForecast.mockImplementation((id) =>
      Promise.resolve({ data: { success: true, data: forecast(id) } }),
    );
  });

  it("renders overall risk and every factor", async () => {
    renderPanel();
    expect(await screen.findByText(/Overall medium/)).toBeInTheDocument();
    ["Market", "Credit", "Liquidity", "Operational", "Compliance"].forEach(
      (label) => {
        expect(screen.getByTestId(`risk-factor-${label}`)).toBeInTheDocument();
      },
    );
    expect(screen.getByText("Synthetic Ethereum")).toBeInTheDocument();
  });

  it("loads the forecast for the first pool and switches pools", async () => {
    renderPanel();
    await waitFor(() =>
      expect(mlAPI.getPoolForecast).toHaveBeenCalledWith("pool-a", 3),
    );
    expect(await screen.findByTestId("forecast-value")).toHaveTextContent(
      "$1.03M",
    );

    fireEvent.change(screen.getByLabelText("Select pool"), {
      target: { value: "pool-b" },
    });
    await waitFor(() =>
      expect(mlAPI.getPoolForecast).toHaveBeenCalledWith("pool-b", 3),
    );
    await waitFor(() =>
      expect(screen.getByTestId("forecast-value")).toHaveTextContent("$900K"),
    );
  });

  it("shows the API error detail when risk models are unavailable", async () => {
    mlAPI.getRiskOverview.mockRejectedValue({
      response: { data: { detail: "No active risk model" } },
    });
    renderPanel();
    expect(await screen.findByText("No active risk model")).toBeInTheDocument();
    expect(mlAPI.getPoolForecast).not.toHaveBeenCalled();
  });

  it("falls back to a generic message on network failure", async () => {
    mlAPI.getRiskOverview.mockRejectedValue(new Error("Network Error"));
    renderPanel();
    expect(
      await screen.findByText("Risk models are currently unavailable"),
    ).toBeInTheDocument();
  });
});
