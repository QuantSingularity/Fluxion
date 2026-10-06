import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import useMlRisk from "../../hooks/useMlRisk";
import { colors, spacing } from "../../theme/theme";
import AppCard from "../ui/AppCard";
import Pill from "../ui/Pill";

const LEVEL_TONES = {
  low: "success",
  medium: "warning",
  high: "danger",
  critical: "danger",
};

const FACTOR_LABELS = {
  market_risk: "Market",
  credit_risk: "Credit",
  liquidity_risk: "Liquidity",
  operational_risk: "Operational",
  compliance_risk: "Compliance",
};

const levelOf = (score) => {
  if (score >= 0.85) return "critical";
  if (score >= 0.66) return "high";
  if (score >= 0.33) return "medium";
  return "low";
};

const percent = (value) => `${(value * 100).toFixed(1)}%`;

export const MlRiskView = ({ loading, error, data, onRetry }) => {
  if (loading) {
    return (
      <AppCard style={styles.card}>
        <ActivityIndicator color={colors.brand[300]} testID="ml-risk-loading" />
      </AppCard>
    );
  }

  if (error || !data) {
    return (
      <AppCard style={styles.card}>
        <Text style={styles.muted} testID="ml-risk-error">
          {error || "Risk models are currently unavailable"}
        </Text>
        {onRetry ? (
          <Pressable onPress={onRetry} accessibilityRole="button">
            <Text style={styles.retry}>Retry</Text>
          </Pressable>
        ) : null}
      </AppCard>
    );
  }

  return (
    <AppCard style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.overallLabel}>Overall risk</Text>
        <Pill
          label={`${data.risk_level} ${percent(data.overall_risk)}`}
          tone={LEVEL_TONES[data.risk_level] || "neutral"}
        />
      </View>

      {Object.entries(data.factors).map(([key, score]) => {
        const level = levelOf(score);
        return (
          <View key={key} style={styles.factorRow} testID={`ml-factor-${key}`}>
            <Text style={styles.factorLabel}>{FACTOR_LABELS[key] || key}</Text>
            <View style={styles.track}>
              <View
                style={[
                  styles.fill,
                  {
                    width: `${Math.round(score * 100)}%`,
                    backgroundColor:
                      level === "low"
                        ? colors.success
                        : level === "medium"
                          ? colors.warning
                          : colors.danger,
                  },
                ]}
              />
            </View>
            <Text style={styles.factorValue}>{percent(score)}</Text>
          </View>
        );
      })}

      <Text style={styles.subTitle}>By market</Text>
      {data.items.map((item) => (
        <View
          key={`${item.entity_type}-${item.entity_id}`}
          style={styles.itemRow}
        >
          <Text style={styles.itemName}>{item.name || item.entity_id}</Text>
          <Pill
            label={item.risk_level}
            tone={LEVEL_TONES[item.risk_level] || "neutral"}
          />
        </View>
      ))}
    </AppCard>
  );
};

const MlRiskSection = () => {
  const state = useMlRisk();
  return (
    <>
      <Text style={styles.blockTitle}>Model Risk Assessment</Text>
      <MlRiskView
        loading={state.loading}
        error={state.error}
        data={state.data}
        onRetry={state.reload}
      />
    </>
  );
};

const styles = StyleSheet.create({
  blockTitle: {
    color: colors.text,
    fontSize: 18,
    fontWeight: "700",
    marginTop: spacing.sm,
    marginBottom: spacing.md,
  },
  card: { marginBottom: spacing.md },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.md,
  },
  overallLabel: { color: colors.textSecondary, fontSize: 13 },
  factorRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: spacing.sm,
  },
  factorLabel: { color: colors.textSecondary, fontSize: 12, width: 84 },
  track: {
    flex: 1,
    height: 6,
    borderRadius: 3,
    backgroundColor: "rgba(148,163,184,0.2)",
    marginHorizontal: spacing.sm,
    overflow: "hidden",
  },
  fill: { height: 6, borderRadius: 3 },
  factorValue: {
    color: colors.text,
    fontSize: 12,
    width: 46,
    textAlign: "right",
  },
  subTitle: {
    color: colors.text,
    fontSize: 14,
    fontWeight: "700",
    marginTop: spacing.md,
    marginBottom: spacing.sm,
  },
  itemRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: spacing.xs,
  },
  itemName: { color: colors.textSecondary, fontSize: 13 },
  muted: { color: colors.textSecondary, fontSize: 13 },
  retry: {
    color: colors.brand[300],
    fontSize: 13,
    fontWeight: "700",
    marginTop: spacing.sm,
  },
});

export default MlRiskSection;
