import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Card,
  CardBody,
  Flex,
  Heading,
  HStack,
  Progress,
  Select,
  SimpleGrid,
  Skeleton,
  Stat,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  VStack,
} from "@chakra-ui/react";
import { useEffect, useRef, useState } from "react";
import { mlAPI } from "../../services/api";

const LEVEL_COLORS = {
  low: "green",
  medium: "yellow",
  high: "orange",
  critical: "red",
};

const FACTOR_LABELS = {
  market_risk: "Market",
  credit_risk: "Credit",
  liquidity_risk: "Liquidity",
  operational_risk: "Operational",
  compliance_risk: "Compliance",
};

const unwrap = (response) => response?.data?.data ?? null;

const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;

const formatMoney = (value) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(value);

const levelOf = (score) => {
  if (score >= 0.85) return "critical";
  if (score >= 0.66) return "high";
  if (score >= 0.33) return "medium";
  return "low";
};

function useMlData(loader, key) {
  const loaderRef = useRef(loader);
  loaderRef.current = loader;
  const enabled = Boolean(loader);
  const [state, setState] = useState({
    loading: true,
    error: null,
    data: null,
  });

  useEffect(() => {
    if (!enabled) {
      setState({ loading: false, error: null, data: null });
      return undefined;
    }
    let active = true;
    setState((prev) => ({ ...prev, loading: true, error: null }));
    loaderRef
      .current()
      .then((response) => {
        if (active) {
          setState({ loading: false, error: null, data: unwrap(response) });
        }
      })
      .catch((error) => {
        if (active) {
          const detail =
            error?.response?.data?.detail ||
            error?.response?.data?.message ||
            "Risk models are currently unavailable";
          setState({ loading: false, error: String(detail), data: null });
        }
      });
    return () => {
      active = false;
    };
  }, [enabled, key]);

  return state;
}

function RiskBar({ label, score }) {
  const level = levelOf(score);
  return (
    <Box data-testid={`risk-factor-${label}`}>
      <Flex justify="space-between" mb={1}>
        <Text fontSize="sm">{label}</Text>
        <Badge colorScheme={LEVEL_COLORS[level]}>
          {formatPercent(score)} {level}
        </Badge>
      </Flex>
      <Progress
        value={score * 100}
        size="sm"
        borderRadius="md"
        colorScheme={LEVEL_COLORS[level]}
        aria-label={`${label} risk`}
      />
    </Box>
  );
}

function LiquidityOutlook({ pools }) {
  const [poolId, setPoolId] = useState(pools[0]?.entity_id ?? "");
  const horizon = 3;
  const { loading, error, data } = useMlData(
    poolId ? () => mlAPI.getPoolForecast(poolId, horizon) : null,
    poolId,
  );

  if (!pools.length) return null;

  const last = data
    ? data.predicted_liquidity[data.predicted_liquidity.length - 1]
    : null;
  const lastChange = data
    ? data.predicted_change_pct[data.predicted_change_pct.length - 1]
    : null;
  const lower = data ? data.lower_bound[data.lower_bound.length - 1] : null;
  const upper = data ? data.upper_bound[data.upper_bound.length - 1] : null;

  return (
    <Box mt={6}>
      <Flex justify="space-between" align="center" mb={3} wrap="wrap" gap={2}>
        <Heading size="sm">Liquidity outlook (next {horizon} periods)</Heading>
        <Select
          size="sm"
          maxW="260px"
          value={poolId}
          onChange={(event) => setPoolId(event.target.value)}
          aria-label="Select pool"
        >
          {pools.map((pool) => (
            <option key={pool.entity_id} value={pool.entity_id}>
              {pool.name}
            </option>
          ))}
        </Select>
      </Flex>
      {loading && <Skeleton height="60px" />}
      {error && !loading && (
        <Alert status="warning" borderRadius="md">
          <AlertIcon />
          {error}
        </Alert>
      )}
      {data && !loading && (
        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={4}>
          <Stat>
            <StatLabel>Current liquidity</StatLabel>
            <StatNumber>{formatMoney(data.current_liquidity)}</StatNumber>
          </Stat>
          <Stat>
            <StatLabel>Forecast</StatLabel>
            <StatNumber data-testid="forecast-value">
              {formatMoney(last)}
            </StatNumber>
            <StatHelpText>
              {lastChange >= 0 ? "+" : ""}
              {lastChange.toFixed(2)}%
            </StatHelpText>
          </Stat>
          <Stat>
            <StatLabel>
              {Math.round(data.confidence_level * 100)}% interval
            </StatLabel>
            <StatNumber fontSize="lg">
              {formatMoney(lower)} to {formatMoney(upper)}
            </StatNumber>
          </Stat>
        </SimpleGrid>
      )}
    </Box>
  );
}

export default function MlRiskPanel() {
  const { loading, error, data } = useMlData(
    () => mlAPI.getRiskOverview(),
    "overview",
  );

  const pools = data
    ? data.items.filter((item) => item.entity_type === "pool")
    : [];

  return (
    <Card mb={8} variant="outline" data-testid="ml-risk-panel">
      <CardBody>
        <Flex justify="space-between" align="center" mb={4} wrap="wrap" gap={2}>
          <Heading size="md">ML Risk Assessment</Heading>
          {data && (
            <Badge
              colorScheme={LEVEL_COLORS[data.risk_level]}
              fontSize="sm"
              px={3}
              py={1}
            >
              Overall {data.risk_level} ({formatPercent(data.overall_risk)})
            </Badge>
          )}
        </Flex>

        {loading && (
          <VStack align="stretch" spacing={3}>
            <Skeleton height="20px" />
            <Skeleton height="20px" />
            <Skeleton height="20px" />
          </VStack>
        )}

        {error && !loading && (
          <Alert status="warning" borderRadius="md">
            <AlertIcon />
            {error}
          </Alert>
        )}

        {data && !loading && (
          <>
            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
              {Object.entries(data.factors).map(([key, score]) => (
                <RiskBar
                  key={key}
                  label={FACTOR_LABELS[key] ?? key}
                  score={score}
                />
              ))}
            </SimpleGrid>

            <Box mt={6}>
              <Heading size="sm" mb={3}>
                Risk by market
              </Heading>
              <VStack align="stretch" spacing={2}>
                {data.items.map((item) => (
                  <Flex
                    key={`${item.entity_type}-${item.entity_id}`}
                    justify="space-between"
                    align="center"
                  >
                    <Text fontSize="sm">{item.name ?? item.entity_id}</Text>
                    <HStack>
                      <Text fontSize="xs" color="gray.500">
                        {FACTOR_LABELS[item.primary_driver] ??
                          item.primary_driver}
                      </Text>
                      <Badge colorScheme={LEVEL_COLORS[item.risk_level]}>
                        {item.risk_level}
                      </Badge>
                    </HStack>
                  </Flex>
                ))}
              </VStack>
            </Box>

            <LiquidityOutlook pools={pools} />

            <Text fontSize="xs" color="gray.500" mt={4}>
              Scores come from the Fluxion ML service using{" "}
              {data.data_source === "simulated_market_snapshot"
                ? "simulated market history"
                : "supplied market history"}
              .
            </Text>
          </>
        )}
      </CardBody>
    </Card>
  );
}
