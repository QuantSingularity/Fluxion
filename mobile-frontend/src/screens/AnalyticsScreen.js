import { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import MlRiskSection from "../components/ml/MlRiskSection";
import AppCard from "../components/ui/AppCard";
import {
  AreaChartMini,
  BarChartMini,
  DonutChart,
} from "../components/ui/Charts";
import Pill from "../components/ui/Pill";
import Screen from "../components/ui/Screen";
import StatCard from "../components/ui/StatCard";
import {
  marketStats,
  poolDistribution,
  riskMetrics,
  tvlHistory,
  volumeHistory,
} from "../data/mockData";
import { colors, spacing } from "../theme/theme";

const ranges = ["7D", "1M", "3M", "1Y"];

const AnalyticsScreen = () => {
  const [range, setRange] = useState("1M");
  const totalDistribution = poolDistribution.reduce(
    (sum, d) => sum + d.value,
    0,
  );

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.title}>Analytics</Text>
        <Text style={styles.subtitle}>
          Protocol-wide performance and risk metrics.
        </Text>
      </View>

      {/* Range selector */}
      <View style={styles.rangeRow}>
        {ranges.map((r) => {
          const active = r === range;
          return (
            <Pressable
              key={r}
              onPress={() => setRange(r)}
              style={[styles.rangeChip, active && styles.rangeChipActive]}
            >
              <Text
                style={[styles.rangeText, active && styles.rangeTextActive]}
              >
                {r}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* Key stats */}
      <View style={styles.statsGrid}>
        <StatCard
          label="Total TVL"
          value={marketStats.tvl}
          change="+12.4%"
          up
          icon="dollar-sign"
          style={styles.statHalf}
        />
        <StatCard
          label="24h Volume"
          value={marketStats.volume24h}
          change="+5.1%"
          up
          icon="activity"
          style={styles.statHalf}
        />
      </View>

      {/* TVL chart */}
      <AppCard style={styles.chartCard}>
        <View style={styles.chartHeader}>
          <Text style={styles.chartTitle}>Total Value Locked</Text>
          <Pill label="+67.5%" tone="success" />
        </View>
        <AreaChartMini data={tvlHistory} height={150} />
      </AppCard>

      {/* Volume chart */}
      <AppCard style={styles.chartCard}>
        <View style={styles.chartHeader}>
          <Text style={styles.chartTitle}>Weekly Volume</Text>
          <Text style={styles.chartHint}>in $M</Text>
        </View>
        <BarChartMini
          data={volumeHistory}
          height={170}
          color={colors.accent[500]}
        />
      </AppCard>

      {/* Pool distribution */}
      <AppCard style={styles.chartCard}>
        <Text style={styles.chartTitle}>Pool Distribution</Text>
        <View style={styles.distRow}>
          <DonutChart data={poolDistribution} size={140} />
          <View style={styles.legend}>
            {poolDistribution.map((item) => (
              <View key={item.name} style={styles.legendRow}>
                <View
                  style={[styles.legendDot, { backgroundColor: item.color }]}
                />
                <Text style={styles.legendLabel}>{item.name}</Text>
                <Text style={styles.legendValue}>
                  {Math.round((item.value / totalDistribution) * 100)}%
                </Text>
              </View>
            ))}
          </View>
        </View>
      </AppCard>

      {/* Risk metrics */}
      <Text style={styles.blockTitle}>Risk Metrics</Text>
      <View style={styles.riskGrid}>
        {riskMetrics.map((metric) => (
          <AppCard key={metric.label} style={styles.riskCard}>
            <Text style={styles.riskLabel}>{metric.label}</Text>
            <Text
              style={[
                styles.riskValue,
                {
                  color:
                    metric.tone === "success"
                      ? colors.success
                      : metric.tone === "danger"
                        ? colors.danger
                        : metric.tone === "warning"
                          ? colors.warning
                          : colors.text,
                },
              ]}
            >
              {metric.value}
            </Text>
          </AppCard>
        ))}
      </View>

      <MlRiskSection />
    </Screen>
  );
};

const styles = StyleSheet.create({
  header: { marginTop: spacing.md, marginBottom: spacing.lg },
  title: { color: colors.text, fontSize: 24, fontWeight: "800" },
  subtitle: { color: colors.textSecondary, fontSize: 14, marginTop: 2 },
  rangeRow: { flexDirection: "row", gap: spacing.sm, marginBottom: spacing.lg },
  rangeChip: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: colors.card,
    borderWidth: 1,
    borderColor: colors.border,
  },
  rangeChipActive: {
    backgroundColor: colors.brand[500],
    borderColor: colors.brand[500],
  },
  rangeText: { color: colors.textSecondary, fontWeight: "700", fontSize: 13 },
  rangeTextActive: { color: colors.text },
  statsGrid: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: spacing.xs,
  },
  statHalf: { width: "48.5%", marginBottom: spacing.md },
  chartCard: { marginBottom: spacing.md },
  chartHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  chartTitle: { color: colors.text, fontSize: 16, fontWeight: "700" },
  chartHint: { color: colors.textMuted, fontSize: 12 },
  distRow: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: spacing.md,
    gap: spacing.lg,
  },
  legend: { flex: 1, gap: spacing.sm },
  legendRow: { flexDirection: "row", alignItems: "center" },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: spacing.sm,
  },
  legendLabel: { color: colors.textSecondary, fontSize: 13, flex: 1 },
  legendValue: { color: colors.text, fontSize: 13, fontWeight: "600" },
  blockTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  riskGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "space-between",
  },
  riskCard: { width: "48.5%", marginBottom: spacing.md },
  riskLabel: { color: colors.textSecondary, fontSize: 12 },
  riskValue: { fontSize: 20, fontWeight: "800", marginTop: 4 },
});

export default AnalyticsScreen;
