jest.mock("axios", () => {
  const mockInstance = {
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
    get: jest.fn(),
    post: jest.fn(),
  };
  return {
    __esModule: true,
    default: { create: jest.fn(() => mockInstance) },
    create: jest.fn(() => mockInstance),
  };
});
jest.mock("@react-native-async-storage/async-storage", () => ({
  setItem: jest.fn(() => Promise.resolve()),
  getItem: jest.fn(() => Promise.resolve(null)),
  removeItem: jest.fn(() => Promise.resolve()),
  multiRemove: jest.fn(() => Promise.resolve()),
}));
jest.mock("expo-constants", () => ({
  default: { expoConfig: null, manifest: null },
}));

import apiClient, {
  fetchPoolForecast,
  fetchPoolRisk,
  fetchRiskOverview,
} from "../api/client";

describe("ML API client", () => {
  let errorSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    errorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    errorSpy.mockRestore();
  });

  it("fetchRiskOverview unwraps the data payload", async () => {
    apiClient.get.mockResolvedValue({
      data: {
        success: true,
        data: { overall_risk: 0.4, risk_level: "medium" },
      },
    });
    const result = await fetchRiskOverview();
    expect(apiClient.get).toHaveBeenCalledWith("/ml/risk/overview");
    expect(result.risk_level).toBe("medium");
  });

  it("fetchPoolRisk encodes the pool id", async () => {
    apiClient.get.mockResolvedValue({ data: { data: { entity_id: "a/b" } } });
    await fetchPoolRisk("a/b");
    expect(apiClient.get).toHaveBeenCalledWith("/ml/pools/a%2Fb/risk");
  });

  it("fetchPoolForecast passes the horizon", async () => {
    apiClient.get.mockResolvedValue({
      data: { data: { predicted_liquidity: [1, 2, 3] } },
    });
    const result = await fetchPoolForecast("pool-1", 3);
    expect(apiClient.get).toHaveBeenCalledWith("/ml/pools/pool-1/forecast", {
      params: { horizon: 3 },
    });
    expect(result.predicted_liquidity).toHaveLength(3);
  });

  it("surfaces the backend detail message on failure", async () => {
    jest.useFakeTimers();
    apiClient.get.mockRejectedValue({
      response: { data: { detail: "No active risk model" } },
    });
    const pending = fetchRiskOverview();
    const assertion = expect(pending).rejects.toThrow("No active risk model");
    await jest.advanceTimersByTimeAsync(2000);
    await assertion;
    expect(apiClient.get).toHaveBeenCalledTimes(2);
    jest.useRealTimers();
  });

  it("falls back to a generic message without a response body", async () => {
    jest.useFakeTimers();
    apiClient.get.mockRejectedValue(new Error("Network error"));
    const pending = fetchPoolForecast("pool-1");
    const assertion = expect(pending).rejects.toThrow(
      "Failed to fetch liquidity forecast",
    );
    await jest.advanceTimersByTimeAsync(2000);
    await assertion;
    jest.useRealTimers();
  });
});
