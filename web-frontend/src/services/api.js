import axios from "axios";
import { env } from "../lib/env";

// Create an axios instance with default config
const api = axios.create({
  baseURL: env.API_BASE_URL(),
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("fluxion_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Add response interceptor for error handling and one-shot token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response) {
      // On 401, try a single refresh-and-retry before giving up.
      if (error.response.status === 401 && original && !original._retried) {
        original._retried = true;
        const refreshToken = localStorage.getItem("fluxion_refresh_token");
        if (refreshToken) {
          try {
            const resp = await api.post("/auth/refresh", {
              refresh_token: refreshToken,
            });
            const data = resp.data?.data ?? resp.data ?? {};
            const newAccess = data.access_token;
            const newRefresh = data.refresh_token;
            if (newAccess) {
              localStorage.setItem("fluxion_token", newAccess);
              if (newRefresh)
                localStorage.setItem("fluxion_refresh_token", newRefresh);
              original.headers.Authorization = `Bearer ${newAccess}`;
              return api(original);
            }
          } catch {
            // fall through to clearing tokens
          }
        }
        localStorage.removeItem("fluxion_token");
        localStorage.removeItem("fluxion_refresh_token");
      }
    } else if (error.request) {
      console.error("Network error, no response received");
    } else {
      console.error("Error setting up request:", error.message);
    }
    return Promise.reject(error);
  },
);

// API endpoints
//
// baseURL is "/api/v1" (see env.API_BASE_URL), so paths below are relative to
// the backend's versioned mount point. These mirror the routes the backend
// actually serves (api/v1/router.py).

export const authAPI = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
  logout: () => api.post("/auth/logout"),
  refresh: (refreshToken) =>
    api.post("/auth/refresh", { refresh_token: refreshToken }),
  me: () => api.get("/auth/me"),
  verifyEmail: (token) => api.post("/auth/verify-email", { token }),
  requestPasswordReset: (email) => api.post("/auth/password-reset", { email }),
};

export const userAPI = {
  getProfile: () => api.get("/users/me"),
  updateProfile: (data) => api.patch("/users/me", data),
  getPreferences: () => api.get("/users/me/preferences"),
  updatePreferences: (data) => api.patch("/users/me/preferences", data),
  getSessions: () => api.get("/users/me/sessions"),
};

export const portfolioAPI = {
  getPortfolios: () => api.get("/portfolio/"),
  getPortfolio: (id) => api.get(`/portfolio/${id}`),
  getPerformance: (id, params) =>
    api.get(`/portfolio/${id}/performance`, { params }),
  getAssets: (id) => api.get(`/portfolio/${id}/assets`),
};

export const transactionsAPI = {
  list: (params) => api.get("/transactions/", { params }),
  create: (data) => api.post("/transactions/", data),
  getById: (id) => api.get(`/transactions/${id}`),
  cancel: (id) => api.post(`/transactions/${id}/cancel`),
};

export const analyticsAPI = {
  getOverview: () => api.get("/analytics/overview"),
  getRisk: () => api.get("/analytics/risk"),
  getCompliance: () => api.get("/analytics/compliance"),
};

export const poolsAPI = {
  getAllPools: (params) => api.get("/markets/pools", { params }),
  getPoolById: (id) => api.get(`/markets/pools/${id}`),
};

export const syntheticsAPI = {
  getAllSynthetics: (params) => api.get("/markets/synthetics", { params }),
  getSyntheticById: (id) => api.get(`/markets/synthetics/${id}`),
};

export const mlAPI = {
  getRiskOverview: () => api.get("/ml/risk/overview", { timeout: 30000 }),
  getPoolRisk: (id) => api.get(`/ml/pools/${encodeURIComponent(id)}/risk`),
  getAssetRisk: (id) => api.get(`/ml/assets/${encodeURIComponent(id)}/risk`),
  getPoolForecast: (id, horizon = 3) =>
    api.get(`/ml/pools/${encodeURIComponent(id)}/forecast`, {
      params: { horizon },
      timeout: 30000,
    }),
  getStatus: () => api.get("/ml/status"),
};

export const healthAPI = {
  check: () => api.get("/health/"),
};

// Fallback to mock data when API is not available
const mockData = {
  market: {
    tvl: "$142.5M",
    volume24h: "$28.4M",
    activePools: 247,
    averageApy: "8.74%",
  },
  pools: [
    {
      id: "pool-1",
      name: "ETH-USDC",
      assets: ["ETH", "USDC"],
      weights: [50, 50],
      tvl: "$4.2M",
      volume24h: "$1.2M",
      apy: "8.4%",
      fee: "0.3%",
    },
    {
      id: "pool-2",
      name: "WBTC-ETH",
      assets: ["WBTC", "ETH"],
      weights: [60, 40],
      tvl: "$8.7M",
      volume24h: "$3.5M",
      apy: "7.2%",
      fee: "0.3%",
    },
  ],
};

// Helper function to get mock data when API fails
export const getMockData = (type) => {
  return mockData[type] || null;
};

export default api;
