import AsyncStorage from "@react-native-async-storage/async-storage";
import axios from "axios";
import Constants from "expo-constants";

// API version prefix - the backend mounts all routes under /api/v1.
const API_VERSION_PREFIX = "/api/v1";

// Get API configuration from environment or use defaults
const getApiBaseUrl = () => {
  // Try to get from expo constants first (for managed workflow)
  const expoConfig = Constants.expoConfig || Constants.manifest;
  const root =
    expoConfig?.extra?.apiBaseUrl ||
    (__DEV__ ? "http://localhost:8000" : "https://api.fluxion.io");

  // Avoid double-prefixing if the configured URL already includes the version.
  const trimmed = root.replace(/\/+$/, "");
  return trimmed.endsWith(API_VERSION_PREFIX)
    ? trimmed
    : `${trimmed}${API_VERSION_PREFIX}`;
};

const API_BASE_URL = getApiBaseUrl();
const API_TIMEOUT = 30000; // 30 seconds

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: API_TIMEOUT,
});

// Token storage keys
const AUTH_TOKEN_KEY = "@fluxion_auth_token";
const REFRESH_TOKEN_KEY = "@fluxion_refresh_token";
const TOKEN_EXPIRY_KEY = "@fluxion_token_expiry";
const USER_KEY = "@fluxion_user";

// Token management functions
export const setAuthToken = async (token, expiryMinutes = 30) => {
  try {
    await AsyncStorage.setItem(AUTH_TOKEN_KEY, token);
    const expiryTime = Date.now() + expiryMinutes * 60 * 1000;
    await AsyncStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
  } catch (error) {
    console.error("Error saving auth token:", error);
  }
};

export const getAuthToken = async () => {
  try {
    const token = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
    const expiry = await AsyncStorage.getItem(TOKEN_EXPIRY_KEY);

    if (!token || !expiry) {
      return null;
    }

    // Check if token is expired
    if (Date.now() > parseInt(expiry, 10)) {
      await clearAuthToken();
      return null;
    }

    return token;
  } catch (error) {
    console.error("Error getting auth token:", error);
    return null;
  }
};

export const clearAuthToken = async () => {
  try {
    await AsyncStorage.multiRemove([
      AUTH_TOKEN_KEY,
      REFRESH_TOKEN_KEY,
      TOKEN_EXPIRY_KEY,
      USER_KEY,
    ]);
  } catch (error) {
    console.error("Error clearing auth token:", error);
  }
};

// Persist the full token pair returned by the backend auth endpoints.
export const setAuthTokens = async ({
  accessToken,
  refreshToken,
  expiresIn = 1800,
}) => {
  try {
    if (accessToken) await AsyncStorage.setItem(AUTH_TOKEN_KEY, accessToken);
    if (refreshToken)
      await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    const expiryTime = Date.now() + expiresIn * 1000;
    await AsyncStorage.setItem(TOKEN_EXPIRY_KEY, expiryTime.toString());
  } catch (error) {
    console.error("Error saving auth tokens:", error);
  }
};

export const getRefreshToken = () => AsyncStorage.getItem(REFRESH_TOKEN_KEY);

// Cache the authenticated user so the session can be restored instantly on
// cold start without a network round-trip.
export const setStoredUser = async (user) => {
  try {
    if (user) await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
  } catch (error) {
    console.error("Error saving user:", error);
  }
};

export const getStoredUser = async () => {
  try {
    const raw = await AsyncStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const isAuthenticated = async () => {
  const token = await getAuthToken();
  return !!token;
};

// Request interceptor for adding auth token
apiClient.interceptors.request.use(
  async (config) => {
    const token = await getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle session expiration
    if (error.response && error.response.status === 401) {
      await clearAuthToken();
      // You can dispatch a navigation event here if needed
      // For now, we just clear the token
    }

    // Handle network errors
    if (!error.response) {
      error.message = "Network error. Please check your connection.";
    }

    return Promise.reject(error);
  },
);

// Retry logic for failed requests
const retryRequest = async (requestFn, retries = 3, delay = 1000) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await requestFn();
    } catch (error) {
      if (i === retries - 1) throw error;
      await new Promise((resolve) => setTimeout(resolve, delay * (i + 1)));
    }
  }
};

// API Functions

// The backend wraps list/detail responses as { success, data, total }. This
// returns the inner `data` payload so screens receive the array/object they
// expect (and still works if a raw payload is returned instead).
const unwrap = (payload) => {
  if (payload && typeof payload === "object" && "data" in payload) {
    return payload.data;
  }
  return payload;
};

/**
 * Fetch all synthetic assets
 * @param {Object} params - Query parameters (limit, offset, search, etc.)
 * @returns {Promise<Object>} Assets data
 */
export const fetchAssets = async (params = {}) => {
  try {
    const response = await retryRequest(() =>
      apiClient.get("/markets/assets", { params }),
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchAssets):",
      error.response?.data || error.message,
    );
    throw new Error(error.response?.data?.detail || "Failed to fetch assets");
  }
};

/**
 * Fetch single asset by ID
 * @param {string} assetId - Asset ID
 * @returns {Promise<Object>} Asset data
 */
export const fetchAssetById = async (assetId) => {
  try {
    const response = await retryRequest(() =>
      apiClient.get(`/markets/assets/${assetId}`),
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchAssetById):",
      error.response?.data || error.message,
    );
    throw new Error(
      error.response?.data?.detail || "Failed to fetch asset data",
    );
  }
};

/**
 * Fetch all liquidity pools
 * @param {Object} params - Query parameters (limit, offset, search, etc.)
 * @returns {Promise<Object>} Pools data
 */
export const fetchPools = async (params = {}) => {
  try {
    const response = await retryRequest(() =>
      apiClient.get("/markets/pools", { params }),
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchPools):",
      error.response?.data || error.message,
    );
    throw new Error(error.response?.data?.detail || "Failed to fetch pools");
  }
};

/**
 * Fetch single pool by ID
 * @param {string} poolId - Pool ID
 * @returns {Promise<Object>} Pool data
 */
export const fetchPoolById = async (poolId) => {
  try {
    const response = await retryRequest(() =>
      apiClient.get(`/markets/pools/${poolId}`),
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchPoolById):",
      error.response?.data || error.message,
    );
    throw new Error(
      error.response?.data?.detail || "Failed to fetch pool data",
    );
  }
};

const mlError = (error, fallback) =>
  new Error(error.response?.data?.detail || fallback);

export const fetchRiskOverview = async () => {
  try {
    const response = await retryRequest(
      () => apiClient.get("/ml/risk/overview"),
      2,
      500,
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchRiskOverview):",
      error.response?.data || error.message,
    );
    throw mlError(error, "Failed to fetch risk overview");
  }
};

export const fetchPoolRisk = async (poolId) => {
  try {
    const response = await retryRequest(
      () => apiClient.get(`/ml/pools/${encodeURIComponent(poolId)}/risk`),
      2,
      500,
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchPoolRisk):",
      error.response?.data || error.message,
    );
    throw mlError(error, "Failed to fetch pool risk");
  }
};

export const fetchPoolForecast = async (poolId, horizon = 3) => {
  try {
    const response = await retryRequest(
      () =>
        apiClient.get(`/ml/pools/${encodeURIComponent(poolId)}/forecast`, {
          params: { horizon },
        }),
      2,
      500,
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchPoolForecast):",
      error.response?.data || error.message,
    );
    throw mlError(error, "Failed to fetch liquidity forecast");
  }
};

/**
 * Fetch asset price history
 * @param {string} assetId - Asset ID
 * @param {string} timeframe - Timeframe (1h, 24h, 7d, 30d, 1y)
 * @returns {Promise<Object>} Price history data
 */
export const fetchAssetPriceHistory = async (assetId, timeframe = "24h") => {
  try {
    const response = await retryRequest(() =>
      apiClient.get(`/markets/assets/${assetId}/price-history`, {
        params: { timeframe },
      }),
    );
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchAssetPriceHistory):",
      error.response?.data || error.message,
    );
    throw new Error(
      error.response?.data?.detail || "Failed to fetch price history",
    );
  }
};

/**
 * Create a new trade order
 * @param {Object} orderData - Order data (asset_id, type, amount, price, etc.)
 * @returns {Promise<Object>} Order confirmation
 */
export const createOrder = async (orderData) => {
  try {
    const response = await apiClient.post("/transactions/", orderData);
    return response.data;
  } catch (error) {
    console.error(
      "API Error (createOrder):",
      error.response?.data || error.message,
    );
    throw new Error(error.response?.data?.detail || "Failed to create order");
  }
};

/**
 * Fetch user's orders
 * @param {Object} params - Query parameters (status, limit, offset)
 * @returns {Promise<Object>} Orders data
 */
export const fetchUserOrders = async (params = {}) => {
  try {
    const response = await retryRequest(() =>
      apiClient.get("/transactions/", { params }),
    );
    return response.data;
  } catch (error) {
    console.error(
      "API Error (fetchUserOrders):",
      error.response?.data || error.message,
    );
    throw new Error(error.response?.data?.detail || "Failed to fetch orders");
  }
};

/**
 * Fetch user's portfolio
 * @returns {Promise<Object>} Portfolio data
 */
export const fetchPortfolio = async () => {
  try {
    const response = await retryRequest(() => apiClient.get("/portfolio/"));
    return unwrap(response.data);
  } catch (error) {
    console.error(
      "API Error (fetchPortfolio):",
      error.response?.data || error.message,
    );
    throw new Error(
      error.response?.data?.detail || "Failed to fetch portfolio",
    );
  }
};

/**
 * Authenticate user
 * @param {string} address - Wallet address
 * @param {string} signature - Signed message
 * @returns {Promise<Object>} Authentication response with token
 */
export const authenticateUser = async (address, signature) => {
  try {
    const response = await apiClient.post("/auth/login", {
      address,
      signature,
    });

    // Store the token
    if (response.data.access_token) {
      await setAuthToken(response.data.access_token);
    }

    return response.data;
  } catch (error) {
    console.error(
      "API Error (authenticateUser):",
      error.response?.data || error.message,
    );
    throw new Error(error.response?.data?.detail || "Authentication failed");
  }
};

/**
 * Get health status of the API
 * @returns {Promise<Object>} Health status
 */
export const getHealthStatus = async () => {
  try {
    const response = await apiClient.get("/health/");
    return response.data;
  } catch (error) {
    console.error(
      "API Error (getHealthStatus):",
      error.response?.data || error.message,
    );
    throw new Error("API health check failed");
  }
};

// --- Email / password authentication -------------------------------------

const extractTokens = (payload) => {
  const d = payload?.data ?? payload ?? {};
  return {
    accessToken: d.access_token || d.accessToken,
    refreshToken: d.refresh_token || d.refreshToken,
    expiresIn: d.expires_in || d.expiresIn || 1800,
  };
};

/**
 * Register a new account with email + password.
 * @param {Object} payload - { email, password, first_name, last_name, ... }
 */
export const registerUser = async (payload) => {
  const body = {
    user_type: "individual",
    confirm_password: payload.confirm_password ?? payload.password,
    terms_accepted: payload.terms_accepted ?? true,
    privacy_accepted: payload.privacy_accepted ?? true,
    ...payload,
  };
  const response = await apiClient.post("/auth/register", body);
  const tokens = extractTokens(response.data);
  if (tokens.accessToken) await setAuthTokens(tokens);
  return response.data?.data ?? response.data;
};

/**
 * Sign in with email + password.
 * @param {string} email
 * @param {string} password
 */
export const loginUser = async (email, password) => {
  const response = await apiClient.post("/auth/login", { email, password });
  const tokens = extractTokens(response.data);
  if (tokens.accessToken) await setAuthTokens(tokens);
  return response.data?.data ?? response.data;
};

/**
 * Fetch the currently authenticated user.
 */
export const getCurrentUser = async () => {
  const response = await apiClient.get("/auth/me");
  return response.data?.data ?? response.data;
};

/**
 * Sign out: notify the backend (best effort) then clear local tokens.
 */
export const logoutUser = async () => {
  try {
    await apiClient.post("/auth/logout");
  } catch {
    // Ignore network/auth errors on logout; tokens are cleared regardless.
  }
  await clearAuthToken();
};

/**
 * Request a password reset email.
 * @param {string} email
 */
export const requestPasswordReset = async (email) => {
  const response = await apiClient.post("/auth/password-reset", { email });
  return response.data;
};

export default apiClient;
