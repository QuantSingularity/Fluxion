import { ChakraProvider } from "@chakra-ui/react";
import { fireEvent, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import Analytics from "../pages/analytics/Analytics";

jest.mock("../services/api", () => ({
  mlAPI: {
    getRiskOverview: jest.fn(() => new Promise(() => {})),
    getPoolForecast: jest.fn(() => new Promise(() => {})),
  },
}));

// Mock the recharts components
jest.mock("recharts", () => ({
  LineChart: ({ children }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  AreaChart: ({ children }) => <div data-testid="area-chart">{children}</div>,
  Area: () => null,
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  ResponsiveContainer: ({ children }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => null,
  Cell: () => null,
}));

const renderAnalytics = () => {
  return render(
    <BrowserRouter>
      <ChakraProvider>
        <Analytics />
      </ChakraProvider>
    </BrowserRouter>,
  );
};

describe("Analytics Component", () => {
  it("renders the page heading", () => {
    renderAnalytics();
    expect(screen.getByText("Analytics Dashboard")).toBeInTheDocument();
  });

  it("renders the stats overview labels", () => {
    renderAnalytics();
    expect(screen.getAllByText("Total Value Locked").length).toBeGreaterThan(0);
    expect(screen.getAllByText("24h Volume").length).toBeGreaterThan(0);
    expect(screen.getByText("Active Pools")).toBeInTheDocument();
    expect(screen.getByText("Average APY")).toBeInTheDocument();
  });

  it("displays the stat values", () => {
    renderAnalytics();
    expect(screen.getAllByText("$142.5M").length).toBeGreaterThan(0);
    expect(screen.getByText("8.74%")).toBeInTheDocument();
  });

  it("renders the analytics tabs", () => {
    renderAnalytics();
    const tabs = screen.getAllByRole("tab");
    expect(tabs.length).toBe(4);
    expect(screen.getByText("Historical")).toBeInTheDocument();
  });

  it("renders charts on the overview tab", () => {
    renderAnalytics();
    // At least one mocked recharts container should be present.
    expect(
      screen.getAllByTestId("responsive-container").length,
    ).toBeGreaterThan(0);
  });

  it("switches to the Pools tab and shows top pools", () => {
    renderAnalytics();
    const tabs = screen.getAllByRole("tab");
    fireEvent.click(tabs[1]);
    expect(screen.getByText("Top Performing Pools")).toBeInTheDocument();
  });
});
