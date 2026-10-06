import { fireEvent, screen, waitFor } from "@testing-library/react-native";
import { fetchRiskOverview } from "../api/client";
import MlRiskSection, { MlRiskView } from "../components/ml/MlRiskSection";
import { render } from "../test-utils";

jest.mock("../api/client", () => ({
  fetchRiskOverview: jest.fn(),
}));

const overview = {
  overall_risk: 0.52,
  risk_level: "medium",
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
    },
    {
      entity_type: "synthetic",
      entity_id: "syn-eth",
      name: "Synthetic Ethereum",
      risk_level: "low",
    },
  ],
};

describe("MlRiskView", () => {
  it("shows a spinner while loading", () => {
    render(<MlRiskView loading error={null} data={null} />);
    expect(screen.getByTestId("ml-risk-loading")).toBeTruthy();
  });

  it("shows the error and a retry action", () => {
    const onRetry = jest.fn();
    render(
      <MlRiskView
        loading={false}
        error="No active risk model"
        data={null}
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText("No active risk model")).toBeTruthy();
    fireEvent.press(screen.getByText("Retry"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders every factor and market", () => {
    render(<MlRiskView loading={false} error={null} data={overview} />);
    [
      "market_risk",
      "credit_risk",
      "liquidity_risk",
      "operational_risk",
      "compliance_risk",
    ].forEach((key) => {
      expect(screen.getByTestId(`ml-factor-${key}`)).toBeTruthy();
    });
    expect(screen.getByText("90.0%")).toBeTruthy();
    expect(screen.getByText("synBTC/synUSD")).toBeTruthy();
    expect(screen.getByText("medium 52.0%")).toBeTruthy();
  });
});

describe("MlRiskSection", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("loads the overview on mount", async () => {
    fetchRiskOverview.mockResolvedValue(overview);
    render(<MlRiskSection />);
    expect(await screen.findByText("Overall risk")).toBeTruthy();
    expect(fetchRiskOverview).toHaveBeenCalledTimes(1);
  });

  it("shows the error and reloads on retry", async () => {
    fetchRiskOverview
      .mockRejectedValueOnce(new Error("Risk models unavailable"))
      .mockResolvedValueOnce(overview);
    render(<MlRiskSection />);
    expect(await screen.findByText("Risk models unavailable")).toBeTruthy();
    fireEvent.press(screen.getByText("Retry"));
    await waitFor(() => expect(screen.getByText("Overall risk")).toBeTruthy());
    expect(fetchRiskOverview).toHaveBeenCalledTimes(2);
  });
});
