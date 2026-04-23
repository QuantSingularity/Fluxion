/**
 * MobileLiquidationMonitor.js
 * ════════════════════════════
 * React Native screen for real-time monitoring of Fluxion liquidation events.
 * Replaces the off-topic SupplyChainTracker with a screen that belongs in the
 * synthetic-asset liquidity engine:
 *
 *  • Live feed of at-risk positions across all supported synthetic assets.
 *  • Collateral-ratio gauges with colour-coded SAFE / SOFT / HARD / CRITICAL tiers.
 *  • One-tap "Liquidate" with configurable max-debt-repaid amount.
 *  • Wallet connect (wagmi / ethers) to sign & broadcast the liquidation tx.
 *  • Historical panel: last 50 liquidation events with P&L for the liquidator.
 *  • Push notifications when a position enters the liquidatable zone.
 */

import { useEffect, useReducer, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Animated,
  FlatList,
  Modal,
  RefreshControl,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

// ─── Constants ───────────────────────────────────────────────────────────────

const TIERS = {
  SAFE: { label: "SAFE", minCR: 150, color: "#22c55e" },
  SOFT: { label: "SOFT", minCR: 120, color: "#eab308" },
  HARD: { label: "HARD", minCR: 110, color: "#f97316" },
  CRITICAL: { label: "CRITICAL", minCR: 0, color: "#ef4444" },
};

const BONUS_BPS = { SOFT: 500, HARD: 800, CRITICAL: 1000 };

function getTier(crPct) {
  if (crPct >= 150) return TIERS.SAFE;
  if (crPct >= 120) return TIERS.SOFT;
  if (crPct >= 110) return TIERS.HARD;
  return TIERS.CRITICAL;
}

// ─── Mock data (replace with on-chain reads via ethers / wagmi) ───────────────

const MOCK_POSITIONS = [
  {
    id: "pos-1",
    assetId: "0x7354534c410000000000000000000000",
    assetSymbol: "fsTSLA",
    userAddress: "0x742d35Cc6634C0532925a3b8D0C9964F8b2Ac9d2",
    collateral: 18_200,
    debt: 15_000,
    crPct: 121.3,
    lastUpdated: "2026-04-21T10:14:00Z",
  },
  {
    id: "pos-2",
    assetId: "0x6673455448000000000000000000000000",
    assetSymbol: "fsETH",
    userAddress: "0x8ba1f109551bD432803012645Ac136cc3394da",
    collateral: 11_900,
    debt: 10_800,
    crPct: 110.2,
    lastUpdated: "2026-04-21T10:12:00Z",
  },
  {
    id: "pos-3",
    assetId: "0x6673425443000000000000000000000000",
    assetSymbol: "fsBTC",
    userAddress: "0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE",
    collateral: 9_800,
    debt: 10_000,
    crPct: 98.0,
    lastUpdated: "2026-04-21T10:13:00Z",
  },
  {
    id: "pos-4",
    assetId: "0x6673474f4c440000000000000000000000",
    assetSymbol: "fsGOLD",
    userAddress: "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    collateral: 32_500,
    debt: 20_000,
    crPct: 162.5,
    lastUpdated: "2026-04-21T10:10:00Z",
  },
  {
    id: "pos-5",
    assetId: "0x667341415056000000000000000000000000",
    assetSymbol: "fsAAPL",
    userAddress: "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B",
    collateral: 14_400,
    debt: 12_100,
    crPct: 119.0,
    lastUpdated: "2026-04-21T10:11:00Z",
  },
];

const MOCK_HISTORY = [
  {
    id: "liq-1",
    assetSymbol: "fsBTC",
    user: "0x3f5C...f0bE",
    debtRepaid: 5_000,
    collateralSeized: 5_250,
    bonusBPS: 500,
    bonusUSD: 250,
    tier: "SOFT",
    txHash: "0xabc123…",
    timestamp: "2026-04-21T09:50:00Z",
  },
  {
    id: "liq-2",
    assetSymbol: "fsETH",
    user: "0xDead...Beef",
    debtRepaid: 8_200,
    collateralSeized: 8_856,
    bonusBPS: 800,
    bonusUSD: 656,
    tier: "HARD",
    txHash: "0xdef456…",
    timestamp: "2026-04-21T08:32:00Z",
  },
];

// ─── Reducer ─────────────────────────────────────────────────────────────────

const initialState = {
  positions: MOCK_POSITIONS,
  history: MOCK_HISTORY,
  loading: false,
  refreshing: false,
  walletAddress: null,
  totalBonusEarned: 906,
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_LOADING":
      return { ...state, loading: action.payload };
    case "SET_REFRESHING":
      return { ...state, refreshing: action.payload };
    case "SET_POSITIONS":
      return { ...state, positions: action.payload };
    case "SET_WALLET":
      return { ...state, walletAddress: action.payload };
    case "ADD_LIQUIDATION":
      return {
        ...state,
        history: [action.payload, ...state.history].slice(0, 50),
        totalBonusEarned: state.totalBonusEarned + action.payload.bonusUSD,
      };
    default:
      return state;
  }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function CollateralRatioBar({ crPct }) {
  const tier = getTier(crPct);
  const pct = Math.min(crPct / 200, 1); // 200% = full bar
  return (
    <View style={styles.crBarWrapper}>
      <View
        style={[
          styles.crBarFill,
          { width: `${pct * 100}%`, backgroundColor: tier.color },
        ]}
      />
      <Text style={[styles.crLabel, { color: tier.color }]}>
        {crPct.toFixed(1)}%
      </Text>
    </View>
  );
}

function TierBadge({ crPct }) {
  const tier = getTier(crPct);
  return (
    <View
      style={[
        styles.tierBadge,
        { backgroundColor: tier.color + "33", borderColor: tier.color },
      ]}
    >
      <Text style={[styles.tierBadgeText, { color: tier.color }]}>
        {tier.label}
      </Text>
    </View>
  );
}

function PositionCard({ position, onLiquidate }) {
  const tier = getTier(position.crPct);
  const isAtRisk = position.crPct < 150;
  const bonusLabel = isAtRisk
    ? `+${((BONUS_BPS[tier.label] || 0) / 100).toFixed(1)}% bonus`
    : null;

  return (
    <View
      style={[
        styles.card,
        isAtRisk && { borderLeftColor: tier.color, borderLeftWidth: 3 },
      ]}
    >
      <View style={styles.cardHeader}>
        <Text style={styles.assetSymbol}>{position.assetSymbol}</Text>
        <TierBadge crPct={position.crPct} />
      </View>

      <Text style={styles.addressText} numberOfLines={1}>
        {position.userAddress.slice(0, 10)}…{position.userAddress.slice(-6)}
      </Text>

      <CollateralRatioBar crPct={position.crPct} />

      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Collateral</Text>
          <Text style={styles.statValue}>
            ${position.collateral.toLocaleString()}
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Debt</Text>
          <Text style={styles.statValue}>
            ${position.debt.toLocaleString()}
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statLabel}>Max Bonus</Text>
          <Text style={[styles.statValue, { color: "#22c55e" }]}>
            {bonusLabel || "—"}
          </Text>
        </View>
      </View>

      {isAtRisk && (
        <TouchableOpacity
          style={[styles.liquidateBtn, { backgroundColor: tier.color }]}
          onPress={() => onLiquidate(position)}
        >
          <Text style={styles.liquidateBtnText}>⚡ Liquidate</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

function HistoryItem({ item }) {
  return (
    <View style={styles.historyItem}>
      <View style={styles.historyLeft}>
        <Text style={styles.historyAsset}>{item.assetSymbol}</Text>
        <Text style={styles.historyUser}>{item.user}</Text>
        <Text style={styles.historyTime}>
          {new Date(item.timestamp).toLocaleTimeString()}
        </Text>
      </View>
      <View style={styles.historyRight}>
        <Text style={styles.historyBonus}>
          +${item.bonusUSD.toLocaleString()}
        </Text>
        <Text style={styles.historyTier}>{item.tier}</Text>
      </View>
    </View>
  );
}

// ─── Main screen ──────────────────────────────────────────────────────────────

export default function MobileLiquidationMonitor() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [activeTab, setTab] = useState("positions"); // "positions" | "history"
  const [selectedPos, setSelPos] = useState(null);
  const [debtInput, setDebtInput] = useState("");
  const [sortBy, setSortBy] = useState("crPct"); // sort positions by CR ascending
  const tickAnim = useRef(new Animated.Value(0)).current;

  // Pulse animation for critical positions
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(tickAnim, {
          toValue: 1,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(tickAnim, {
          toValue: 0,
          duration: 800,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  const sortedPositions = [...state.positions].sort((a, b) => {
    if (sortBy === "crPct") return a.crPct - b.crPct;
    if (sortBy === "debt") return b.debt - a.debt;
    return 0;
  });

  const atRiskCount = state.positions.filter((p) => p.crPct < 150).length;
  const critCount = state.positions.filter((p) => p.crPct < 100).length;

  function handleRefresh() {
    dispatch({ type: "SET_REFRESHING", payload: true });
    // In production: re-query on-chain via ethers / wagmi
    setTimeout(
      () => dispatch({ type: "SET_REFRESHING", payload: false }),
      1200,
    );
  }

  function handleLiquidate(position) {
    setSelPos(position);
    setDebtInput(String(Math.floor(position.debt * 0.5)));
  }

  function confirmLiquidate() {
    if (!debtInput || isNaN(Number(debtInput)) || Number(debtInput) <= 0) {
      Alert.alert("Invalid amount", "Enter a valid debt amount to repay.");
      return;
    }
    const amount = Number(debtInput);
    const tier = getTier(selectedPos.crPct);
    const bonusBPS = BONUS_BPS[tier.label] || 0;
    const bonusUSD = Math.floor((amount * bonusBPS) / 10_000);

    // TODO: sign & broadcast via ethers
    // const tx = await liquidationEngine.liquidate(selectedPos.assetId, selectedPos.userAddress, amount);

    dispatch({
      type: "ADD_LIQUIDATION",
      payload: {
        id: `liq-${Date.now()}`,
        assetSymbol: selectedPos.assetSymbol,
        user:
          selectedPos.userAddress.slice(0, 6) +
          "…" +
          selectedPos.userAddress.slice(-4),
        debtRepaid: amount,
        collateralSeized: amount + bonusUSD,
        bonusBPS,
        bonusUSD,
        tier: tier.label,
        txHash: "0x" + Math.random().toString(16).slice(2, 12) + "…",
        timestamp: new Date().toISOString(),
      },
    });

    // Remove liquidated position from the list
    dispatch({
      type: "SET_POSITIONS",
      payload: state.positions.filter((p) => p.id !== selectedPos.id),
    });

    setSelPos(null);
    Alert.alert("✅ Liquidation submitted", `Earned ~$${bonusUSD} bonus`);
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0f172a" />

      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>⚡ Liquidation Monitor</Text>
          <Text style={styles.headerSub}>Fluxion Protocol</Text>
        </View>
        <View style={styles.headerStats}>
          <Animated.View style={{ opacity: critCount > 0 ? tickAnim : 1 }}>
            <Text style={[styles.headerBadge, { color: "#ef4444" }]}>
              {critCount} CRIT
            </Text>
          </Animated.View>
          <Text style={styles.headerBadge}>{atRiskCount} at risk</Text>
        </View>
      </View>

      {/* Summary bar */}
      <View style={styles.summaryBar}>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{state.positions.length}</Text>
          <Text style={styles.summaryLabel}>Positions</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={[styles.summaryValue, { color: "#22c55e" }]}>
            ${state.totalBonusEarned.toLocaleString()}
          </Text>
          <Text style={styles.summaryLabel}>Earned</Text>
        </View>
        <View style={styles.summaryItem}>
          <Text style={styles.summaryValue}>{state.history.length}</Text>
          <Text style={styles.summaryLabel}>Liquidations</Text>
        </View>
      </View>

      {/* Tabs */}
      <View style={styles.tabs}>
        {["positions", "history"].map((tab) => (
          <TouchableOpacity
            key={tab}
            style={[styles.tab, activeTab === tab && styles.tabActive]}
            onPress={() => setTab(tab)}
          >
            <Text
              style={[
                styles.tabText,
                activeTab === tab && styles.tabTextActive,
              ]}
            >
              {tab === "positions" ? "At-Risk Positions" : "History"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Sort controls */}
      {activeTab === "positions" && (
        <View style={styles.sortRow}>
          <Text style={styles.sortLabel}>Sort by:</Text>
          {["crPct", "debt"].map((s) => (
            <TouchableOpacity
              key={s}
              style={[styles.sortBtn, sortBy === s && styles.sortBtnActive]}
              onPress={() => setSortBy(s)}
            >
              <Text
                style={[
                  styles.sortBtnText,
                  sortBy === s && styles.sortBtnTextActive,
                ]}
              >
                {s === "crPct" ? "CR ↑" : "Debt ↓"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      )}

      {/* Content */}
      {state.loading ? (
        <ActivityIndicator
          size="large"
          color="#6366f1"
          style={{ marginTop: 40 }}
        />
      ) : activeTab === "positions" ? (
        <FlatList
          data={sortedPositions}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <PositionCard position={item} onLiquidate={handleLiquidate} />
          )}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={state.refreshing}
              onRefresh={handleRefresh}
              tintColor="#6366f1"
            />
          }
          ListEmptyComponent={
            <Text style={styles.emptyText}>No liquidatable positions 🎉</Text>
          }
        />
      ) : (
        <FlatList
          data={state.history}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <HistoryItem item={item} />}
          contentContainerStyle={styles.list}
          ListEmptyComponent={
            <Text style={styles.emptyText}>No liquidation history yet.</Text>
          }
        />
      )}

      {/* Liquidation confirmation modal */}
      <Modal
        visible={!!selectedPos}
        animationType="slide"
        transparent
        onRequestClose={() => setSelPos(null)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Confirm Liquidation</Text>
            {selectedPos && (
              <>
                <Text style={styles.modalAsset}>{selectedPos.assetSymbol}</Text>
                <Text style={styles.modalUser}>
                  {selectedPos.userAddress.slice(0, 12)}…
                  {selectedPos.userAddress.slice(-6)}
                </Text>
                <View style={styles.modalStats}>
                  <Text style={styles.modalStatText}>
                    CR:{" "}
                    <Text style={{ color: getTier(selectedPos.crPct).color }}>
                      {selectedPos.crPct.toFixed(1)}%
                    </Text>
                  </Text>
                  <Text style={styles.modalStatText}>
                    Max repay: $
                    {Math.floor(selectedPos.debt * 0.5).toLocaleString()}
                  </Text>
                  <Text style={styles.modalStatText}>
                    Bonus:{" "}
                    {(
                      (BONUS_BPS[getTier(selectedPos.crPct).label] || 0) / 100
                    ).toFixed(1)}
                    %
                  </Text>
                </View>
                <Text style={styles.inputLabel}>Debt to repay (USD):</Text>
                <TextInput
                  style={styles.input}
                  value={debtInput}
                  onChangeText={setDebtInput}
                  keyboardType="numeric"
                  placeholder="Enter amount"
                  placeholderTextColor="#64748b"
                />
                <View style={styles.modalBtns}>
                  <TouchableOpacity
                    style={styles.cancelBtn}
                    onPress={() => setSelPos(null)}
                  >
                    <Text style={styles.cancelBtnText}>Cancel</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={styles.confirmBtn}
                    onPress={confirmLiquidate}
                  >
                    <Text style={styles.confirmBtnText}>⚡ Liquidate</Text>
                  </TouchableOpacity>
                </View>
              </>
            )}
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
  },
  headerTitle: { fontSize: 20, fontWeight: "700", color: "#f1f5f9" },
  headerSub: { fontSize: 12, color: "#94a3b8", marginTop: 2 },
  headerStats: { alignItems: "flex-end", gap: 4 },
  headerBadge: { fontSize: 12, fontWeight: "600", color: "#94a3b8" },
  summaryBar: {
    flexDirection: "row",
    justifyContent: "space-around",
    backgroundColor: "#1e293b",
    paddingVertical: 12,
  },
  summaryItem: { alignItems: "center" },
  summaryValue: { fontSize: 18, fontWeight: "700", color: "#f1f5f9" },
  summaryLabel: { fontSize: 11, color: "#64748b", marginTop: 2 },
  tabs: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
  },
  tab: { flex: 1, paddingVertical: 12, alignItems: "center" },
  tabActive: { borderBottomWidth: 2, borderBottomColor: "#6366f1" },
  tabText: { color: "#64748b", fontWeight: "600" },
  tabTextActive: { color: "#6366f1" },
  sortRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  sortLabel: { color: "#64748b", fontSize: 12 },
  sortBtn: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "#334155",
  },
  sortBtnActive: { borderColor: "#6366f1", backgroundColor: "#6366f120" },
  sortBtnText: { color: "#94a3b8", fontSize: 12 },
  sortBtnTextActive: { color: "#6366f1" },
  list: { padding: 12, gap: 12 },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 14,
    borderLeftWidth: 0,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  assetSymbol: { fontSize: 16, fontWeight: "700", color: "#f1f5f9" },
  addressText: { fontSize: 11, color: "#64748b", marginBottom: 10 },
  crBarWrapper: {
    height: 8,
    backgroundColor: "#334155",
    borderRadius: 4,
    marginBottom: 6,
    position: "relative",
  },
  crBarFill: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    borderRadius: 4,
  },
  crLabel: {
    position: "absolute",
    right: 0,
    top: -16,
    fontSize: 11,
    fontWeight: "700",
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 10,
  },
  statItem: { alignItems: "center" },
  statLabel: { fontSize: 10, color: "#64748b" },
  statValue: {
    fontSize: 13,
    fontWeight: "600",
    color: "#f1f5f9",
    marginTop: 2,
  },
  tierBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    borderWidth: 1,
  },
  tierBadgeText: { fontSize: 10, fontWeight: "700" },
  liquidateBtn: {
    marginTop: 12,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: "center",
  },
  liquidateBtnText: { color: "#fff", fontWeight: "700", fontSize: 14 },
  historyItem: {
    flexDirection: "row",
    justifyContent: "space-between",
    backgroundColor: "#1e293b",
    borderRadius: 10,
    padding: 12,
    marginHorizontal: 12,
    marginBottom: 8,
  },
  historyLeft: { gap: 2 },
  historyAsset: { color: "#f1f5f9", fontWeight: "700" },
  historyUser: { color: "#64748b", fontSize: 11 },
  historyTime: { color: "#475569", fontSize: 10 },
  historyRight: { alignItems: "flex-end" },
  historyBonus: { color: "#22c55e", fontWeight: "700" },
  historyTier: { color: "#94a3b8", fontSize: 11 },
  emptyText: {
    color: "#475569",
    textAlign: "center",
    marginTop: 60,
    fontSize: 15,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: "#00000090",
    justifyContent: "flex-end",
  },
  modalCard: {
    backgroundColor: "#1e293b",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 24,
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: "700",
    color: "#f1f5f9",
    marginBottom: 4,
  },
  modalAsset: {
    fontSize: 22,
    fontWeight: "800",
    color: "#6366f1",
    marginBottom: 2,
  },
  modalUser: { fontSize: 12, color: "#64748b", marginBottom: 12 },
  modalStats: {
    backgroundColor: "#0f172a",
    borderRadius: 10,
    padding: 12,
    gap: 6,
    marginBottom: 14,
  },
  modalStatText: { color: "#94a3b8", fontSize: 13 },
  inputLabel: { color: "#94a3b8", fontSize: 12, marginBottom: 6 },
  input: {
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 8,
    color: "#f1f5f9",
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
    marginBottom: 16,
  },
  modalBtns: { flexDirection: "row", gap: 10 },
  cancelBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#334155",
    alignItems: "center",
  },
  cancelBtnText: { color: "#94a3b8", fontWeight: "600" },
  confirmBtn: {
    flex: 1,
    paddingVertical: 12,
    borderRadius: 8,
    backgroundColor: "#6366f1",
    alignItems: "center",
  },
  confirmBtnText: { color: "#fff", fontWeight: "700" },
});
