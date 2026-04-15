import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";

const DataContext = createContext(null);

export const DataProvider = ({ children }) => {
  const [marketData, setMarketData] = useState({
    tvl: "$142.5M",
    volume24h: "$28.4M",
    activePools: 247,
    avgApy: "8.74%",
  });
  const [poolsData, setPoolsData] = useState([]);
  const [analyticsData, setAnalyticsData] = useState({
    volumeData: [],
    tvlData: [],
    poolDistribution: [],
  });
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchMarketData = useCallback(async () => {
    try {
      setIsLoading(true);
      await new Promise((resolve) => setTimeout(resolve, 500));
      setMarketData({
        tvl: "$142.5M",
        volume24h: "$28.4M",
        activePools: 247,
        avgApy: "8.74%",
      });
    } catch (err) {
      console.error("Error fetching market data:", err);
      setError("Failed to fetch market data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchPoolsData = useCallback(async () => {
    try {
      setIsLoading(true);
      await new Promise((resolve) => setTimeout(resolve, 500));
      setPoolsData([
        {
          id: "ETH-USDC",
          tvl: "$2.4M",
          volume24h: "$340K",
          apy: "5.2%",
          risk: "Low",
          assets: ["ETH", "USDC"],
          weights: [50, 50],
          utilization: 78,
        },
        {
          id: "BTC-ETH",
          tvl: "$1.8M",
          volume24h: "$220K",
          apy: "4.8%",
          risk: "Medium",
          assets: ["BTC", "ETH"],
          weights: [60, 40],
          utilization: 65,
        },
        {
          id: "LINK-ETH",
          tvl: "$950K",
          volume24h: "$120K",
          apy: "7.3%",
          risk: "Medium",
          assets: ["LINK", "ETH"],
          weights: [30, 70],
          utilization: 82,
        },
      ]);
    } catch (err) {
      console.error("Error fetching pools data:", err);
      setError("Failed to fetch pools data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const fetchAnalyticsData = useCallback(async () => {
    try {
      setIsLoading(true);
      await new Promise((resolve) => setTimeout(resolve, 500));
      setAnalyticsData({
        volumeData: [
          { name: "Jan", volume: 2400 },
          { name: "Feb", volume: 1398 },
          { name: "Mar", volume: 9800 },
          { name: "Apr", volume: 3908 },
          { name: "May", volume: 4800 },
          { name: "Jun", volume: 3800 },
          { name: "Jul", volume: 4300 },
        ],
        tvlData: [
          { name: "Jan", tvl: 4000 },
          { name: "Feb", tvl: 3000 },
          { name: "Mar", tvl: 2000 },
          { name: "Apr", tvl: 2780 },
          { name: "May", tvl: 1890 },
          { name: "Jun", tvl: 2390 },
          { name: "Jul", tvl: 3490 },
        ],
        poolDistribution: [
          { name: "ETH-USDC", value: 2400 },
          { name: "BTC-ETH", value: 1800 },
          { name: "LINK-ETH", value: 950 },
          { name: "UNI-USDT", value: 750 },
          { name: "Others", value: 1200 },
        ],
      });
    } catch (err) {
      console.error("Error fetching analytics data:", err);
      setError("Failed to fetch analytics data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchMarketData();
    fetchPoolsData();
    fetchAnalyticsData();
  }, [fetchMarketData, fetchPoolsData, fetchAnalyticsData]);

  const value = {
    marketData,
    poolsData,
    analyticsData,
    isLoading,
    error,
    fetchMarketData,
    fetchPoolsData,
    fetchAnalyticsData,
  };

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
};

export const useData = () => {
  const context = useContext(DataContext);
  if (!context) throw new Error("useData must be used within a DataProvider");
  return context;
};

export default useData;
