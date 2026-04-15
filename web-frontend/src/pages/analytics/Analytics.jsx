import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Divider,
  Flex,
  Heading,
  HStack,
  Icon,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  SimpleGrid,
  Stat,
  StatArrow,
  StatHelpText,
  StatLabel,
  StatNumber,
  Tab,
  TabList,
  Table,
  TabPanel,
  TabPanels,
  Tabs,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tooltip,
  Tr,
  useColorModeValue,
  useDisclosure,
} from "@chakra-ui/react";
import { useState } from "react";
import {
  FiActivity,
  FiBarChart2,
  FiDollarSign,
  FiDownload,
  FiExternalLink,
  FiShare2,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi";
import { Link as RouterLink } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";

const tvlData = [
  { name: "Jan", tvl: 85 },
  { name: "Feb", tvl: 92 },
  { name: "Mar", tvl: 105 },
  { name: "Apr", tvl: 120 },
  { name: "May", tvl: 132 },
  { name: "Jun", tvl: 142 },
  { name: "Jul", tvl: 138 },
];

const volumeData = [
  { name: "Jan", volume: 12 },
  { name: "Feb", volume: 18 },
  { name: "Mar", volume: 15 },
  { name: "Apr", volume: 21 },
  { name: "May", volume: 24 },
  { name: "Jun", volume: 28 },
  { name: "Jul", volume: 26 },
];

const weeklyVolumeData = [
  { name: "Mon", volume: 3.2 },
  { name: "Tue", volume: 4.8 },
  { name: "Wed", volume: 4.1 },
  { name: "Thu", volume: 5.7 },
  { name: "Fri", volume: 6.2 },
  { name: "Sat", volume: 3.9 },
  { name: "Sun", volume: 2.8 },
];

const poolTypeData = [
  { name: "Weighted", value: 65 },
  { name: "Stable", value: 25 },
  { name: "Boosted", value: 10 },
];

const historicalTVL = [
  { name: "Q1 2024", tvl: 28, volume: 6 },
  { name: "Q2 2024", tvl: 52, volume: 14 },
  { name: "Q3 2024", tvl: 79, volume: 22 },
  { name: "Q4 2024", tvl: 105, volume: 31 },
  { name: "Q1 2025", tvl: 128, volume: 38 },
  { name: "Q2 2025", tvl: 142.5, volume: 28 },
];

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042"];

const topPools = [
  {
    name: "ETH-USDC",
    tvl: "$42.5M",
    volume: "$8.2M",
    apy: "8.4%",
    trend: "up",
  },
  {
    name: "WBTC-ETH",
    tvl: "$38.7M",
    volume: "$7.5M",
    apy: "7.2%",
    trend: "down",
  },
  {
    name: "USDC-DAI-USDT",
    tvl: "$32.5M",
    volume: "$5.8M",
    apy: "4.5%",
    trend: "up",
  },
  {
    name: "ETH-LINK",
    tvl: "$12.8M",
    volume: "$3.2M",
    apy: "9.7%",
    trend: "up",
  },
];

const tooltipStyle = {
  contentStyle: {
    backgroundColor: "rgba(15,20,30,0.95)",
    border: "1px solid #333",
    borderRadius: "8px",
    color: "white",
  },
};

const Analytics = () => {
  const cardBg = useColorModeValue("gray.800", "gray.700");
  const borderColor = useColorModeValue("gray.700", "gray.600");
  const subTextColor = "gray.400";

  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedChart, setSelectedChart] = useState(null);

  const handleExpandChart = (chartType) => {
    setSelectedChart(chartType);
    onOpen();
  };

  return (
    <Box>
      {/* Hero */}
      <Box
        p={8}
        borderRadius="xl"
        mb={8}
        bgGradient="linear(to-br, gray.900, gray.800)"
        boxShadow="xl"
        border="1px solid"
        borderColor={borderColor}
        position="relative"
        overflow="hidden"
      >
        <Box
          position="absolute"
          top="-50px"
          right="-50px"
          w="200px"
          h="200px"
          borderRadius="full"
          bg="brand.500"
          opacity="0.08"
          filter="blur(30px)"
        />
        <Heading as="h1" size="xl" mb={3}>
          Analytics Dashboard
        </Heading>
        <Text fontSize="md" color={subTextColor} maxW="700px">
          Comprehensive analytics and insights for the Fluxion ecosystem.
          Monitor performance, track trends, and make data-driven decisions.
        </Text>
      </Box>

      {/* Stats */}
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={5} mb={8}>
        {[
          {
            label: "Total Value Locked",
            value: "$142.5M",
            change: "23.36%",
            up: true,
            icon: FiDollarSign,
            color: "brand.400",
          },
          {
            label: "24h Volume",
            value: "$28.4M",
            change: "5.14%",
            up: false,
            icon: FiBarChart2,
            color: "accent.400",
          },
          {
            label: "Active Pools",
            value: "247",
            change: "12.05%",
            up: true,
            icon: FiActivity,
            color: "green.400",
          },
          {
            label: "Average APY",
            value: "8.74%",
            change: "2.31%",
            up: true,
            icon: FiTrendingUp,
            color: "purple.400",
          },
        ].map((s, i) => (
          <Stat
            key={i}
            px={5}
            py={4}
            bg={cardBg}
            borderRadius="lg"
            border="1px solid"
            borderColor={borderColor}
            _hover={{ transform: "translateY(-3px)", boxShadow: "lg" }}
            transition="all 0.2s"
          >
            <HStack mb={1}>
              <Icon as={s.icon} color={s.color} />
              <StatLabel fontSize="xs" color={subTextColor}>
                {s.label}
              </StatLabel>
            </HStack>
            <StatNumber fontSize="2xl" fontWeight="bold">
              {s.value}
            </StatNumber>
            <StatHelpText mb={0}>
              <StatArrow type={s.up ? "increase" : "decrease"} />
              {s.change}
            </StatHelpText>
          </Stat>
        ))}
      </SimpleGrid>

      {/* Main Tabs */}
      <Tabs variant="soft-rounded" colorScheme="brand" mb={8}>
        <TabList mb={6} flexWrap="wrap" gap={2}>
          <Tab>Overview</Tab>
          <Tab>Pools</Tab>
          <Tab>Volume</Tab>
          <Tab>Historical</Tab>
        </TabList>

        <TabPanels>
          {/* ── Overview ── */}
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8} mb={8}>
              {/* TVL Chart */}
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <Heading size="md">TVL Trend (Millions $)</Heading>
                  <HStack>
                    <Tooltip label="Expand Chart">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleExpandChart("tvl")}
                      >
                        <Icon as={FiExternalLink} />
                      </Button>
                    </Tooltip>
                    <Tooltip label="Download Data">
                      <Button size="sm" variant="ghost">
                        <Icon as={FiDownload} />
                      </Button>
                    </Tooltip>
                  </HStack>
                </Flex>
                <Box h="280px">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={tvlData}
                      margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient
                          id="colorTvl"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor="#0080ff"
                            stopOpacity={0.7}
                          />
                          <stop
                            offset="95%"
                            stopColor="#0080ff"
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="name" stroke="#666" />
                      <YAxis stroke="#666" />
                      <RechartsTooltip
                        {...tooltipStyle}
                        formatter={(v) => [`$${v}M`, "TVL"]}
                      />
                      <Area
                        type="monotone"
                        dataKey="tvl"
                        stroke="#0080ff"
                        strokeWidth={2}
                        fillOpacity={1}
                        fill="url(#colorTvl)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </Box>
                <HStack mt={3} justify="space-between">
                  <Text color={subTextColor} fontSize="sm">
                    Last 6 months
                  </Text>
                  <Badge colorScheme="green" px={2}>
                    +67.5%
                  </Badge>
                </HStack>
              </Box>

              {/* Volume Chart */}
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <Heading size="md">Volume Trend (Millions $)</Heading>
                  <HStack>
                    <Tooltip label="Expand Chart">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleExpandChart("volume")}
                      >
                        <Icon as={FiExternalLink} />
                      </Button>
                    </Tooltip>
                    <Tooltip label="Download Data">
                      <Button size="sm" variant="ghost">
                        <Icon as={FiDownload} />
                      </Button>
                    </Tooltip>
                  </HStack>
                </Flex>
                <Box h="280px">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={volumeData}
                      margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="name" stroke="#666" />
                      <YAxis stroke="#666" />
                      <RechartsTooltip
                        {...tooltipStyle}
                        formatter={(v) => [`$${v}M`, "Volume"]}
                      />
                      <Bar
                        dataKey="volume"
                        fill="#ff7000"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
                <HStack mt={3} justify="space-between">
                  <Text color={subTextColor} fontSize="sm">
                    Last 6 months
                  </Text>
                  <Badge colorScheme="green" px={2}>
                    +116.7%
                  </Badge>
                </HStack>
              </Box>
            </SimpleGrid>

            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
              {/* Distribution */}
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <Heading size="md">Pool Type Distribution</Heading>
                  <Tooltip label="Expand">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleExpandChart("distribution")}
                    >
                      <Icon as={FiExternalLink} />
                    </Button>
                  </Tooltip>
                </Flex>
                <Box h="260px">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={poolTypeData}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        outerRadius={100}
                        dataKey="value"
                        label={({ name, percent }) =>
                          `${name} ${(percent * 100).toFixed(0)}%`
                        }
                      >
                        {poolTypeData.map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <RechartsTooltip {...tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </Box>
                <SimpleGrid columns={3} spacing={4} mt={4}>
                  {poolTypeData.map((t, i) => (
                    <Box key={i}>
                      <HStack>
                        <Box w="3" h="3" borderRadius="full" bg={COLORS[i]} />
                        <Text fontSize="sm">{t.name}</Text>
                      </HStack>
                      <Text fontWeight="bold">{t.value}%</Text>
                    </Box>
                  ))}
                </SimpleGrid>
              </Box>

              {/* Top Pools */}
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Flex justify="space-between" align="center" mb={4}>
                  <Heading size="md">Top Performing Pools</Heading>
                  <Button
                    as={RouterLink}
                    to="/pools"
                    size="sm"
                    variant="outline"
                    rightIcon={<FiExternalLink />}
                  >
                    View All
                  </Button>
                </Flex>
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Pool</Th>
                      <Th isNumeric>TVL</Th>
                      <Th isNumeric>Volume</Th>
                      <Th isNumeric>APY</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {topPools.map((pool, i) => (
                      <Tr key={i}>
                        <Td fontWeight="medium">{pool.name}</Td>
                        <Td isNumeric>{pool.tvl}</Td>
                        <Td isNumeric>{pool.volume}</Td>
                        <Td isNumeric>
                          <HStack justify="flex-end">
                            <Text
                              fontWeight="bold"
                              color={
                                pool.trend === "up" ? "green.400" : "red.400"
                              }
                            >
                              {pool.apy}
                            </Text>
                            <Icon
                              as={
                                pool.trend === "up"
                                  ? FiTrendingUp
                                  : FiTrendingDown
                              }
                              color={
                                pool.trend === "up" ? "green.400" : "red.400"
                              }
                            />
                          </HStack>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
                <Divider my={4} />
                <SimpleGrid columns={2} spacing={4}>
                  <Card bg="gray.700" variant="outline">
                    <CardBody py={3}>
                      <Text fontSize="sm" color={subTextColor}>
                        Highest APY
                      </Text>
                      <Text fontWeight="bold">ETH-LINK</Text>
                      <HStack>
                        <Text color="green.400" fontWeight="bold">
                          9.7%
                        </Text>
                        <Icon as={FiTrendingUp} color="green.400" />
                      </HStack>
                    </CardBody>
                  </Card>
                  <Card bg="gray.700" variant="outline">
                    <CardBody py={3}>
                      <Text fontSize="sm" color={subTextColor}>
                        Highest Volume
                      </Text>
                      <Text fontWeight="bold">ETH-USDC</Text>
                      <Text fontWeight="bold">$8.2M (24h)</Text>
                    </CardBody>
                  </Card>
                </SimpleGrid>
              </Box>
            </SimpleGrid>
          </TabPanel>

          {/* ── Pools Analytics ── */}
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={5} mb={8}>
              {[
                { label: "Top TVL Pool", value: "ETH-USDC", sub: "$42.5M" },
                { label: "Highest APY", value: "ETH-LINK", sub: "9.7% APY" },
                { label: "Most Active", value: "WBTC-ETH", sub: "$7.5M vol" },
                {
                  label: "Newest Pool",
                  value: "ETH-AAVE",
                  sub: "Created today",
                },
              ].map((s, i) => (
                <Box
                  key={i}
                  bg={cardBg}
                  p={5}
                  borderRadius="lg"
                  border="1px solid"
                  borderColor={borderColor}
                >
                  <Text fontSize="xs" color={subTextColor} mb={1}>
                    {s.label}
                  </Text>
                  <Text fontWeight="bold" fontSize="lg">
                    {s.value}
                  </Text>
                  <Text fontSize="sm" color="brand.400">
                    {s.sub}
                  </Text>
                </Box>
              ))}
            </SimpleGrid>

            <Box
              bg={cardBg}
              p={6}
              borderRadius="lg"
              border="1px solid"
              borderColor={borderColor}
              mb={8}
            >
              <Heading size="md" mb={6}>
                Pool Performance Comparison
              </Heading>
              <Box h="320px">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={topPools.map((p) => ({
                      name: p.name,
                      apy: parseFloat(p.apy),
                      tvl: parseFloat(p.tvl.replace(/[$M]/g, "")),
                    }))}
                    margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="name" stroke="#666" />
                    <YAxis stroke="#666" />
                    <RechartsTooltip {...tooltipStyle} />
                    <Legend />
                    <Bar
                      dataKey="apy"
                      fill="#0080ff"
                      name="APY %"
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="tvl"
                      fill="#ff7000"
                      name="TVL ($M)"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </Box>

            <Box
              bg={cardBg}
              p={6}
              borderRadius="lg"
              border="1px solid"
              borderColor={borderColor}
            >
              <Heading size="md" mb={4}>
                All Pools Overview
              </Heading>
              <Box overflowX="auto">
                <Table variant="simple" size="sm">
                  <Thead>
                    <Tr>
                      <Th>Pool</Th>
                      <Th isNumeric>TVL</Th>
                      <Th isNumeric>24h Volume</Th>
                      <Th isNumeric>APY</Th>
                      <Th>Trend</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {topPools.map((p, i) => (
                      <Tr key={i} _hover={{ bg: "gray.700" }}>
                        <Td fontWeight="medium">{p.name}</Td>
                        <Td isNumeric>{p.tvl}</Td>
                        <Td isNumeric>{p.volume}</Td>
                        <Td isNumeric>
                          <Text color="green.400" fontWeight="bold">
                            {p.apy}
                          </Text>
                        </Td>
                        <Td>
                          <Icon
                            as={
                              p.trend === "up" ? FiTrendingUp : FiTrendingDown
                            }
                            color={p.trend === "up" ? "green.400" : "red.400"}
                          />
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </Box>
          </TabPanel>

          {/* ── Volume Analytics ── */}
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8} mb={8}>
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Heading size="md" mb={6}>
                  Weekly Volume (Millions $)
                </Heading>
                <Box h="300px">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={weeklyVolumeData}
                      margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="name" stroke="#666" />
                      <YAxis stroke="#666" />
                      <RechartsTooltip
                        {...tooltipStyle}
                        formatter={(v) => [`$${v}M`, "Volume"]}
                      />
                      <Bar
                        dataKey="volume"
                        fill="#0080ff"
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </Box>
              </Box>

              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Heading size="md" mb={6}>
                  Monthly Volume Trend
                </Heading>
                <Box h="300px">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart
                      data={volumeData}
                      margin={{ top: 10, right: 20, left: 0, bottom: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                      <XAxis dataKey="name" stroke="#666" />
                      <YAxis stroke="#666" />
                      <RechartsTooltip
                        {...tooltipStyle}
                        formatter={(v) => [`$${v}M`, "Volume"]}
                      />
                      <Line
                        type="monotone"
                        dataKey="volume"
                        stroke="#ff7000"
                        strokeWidth={2}
                        dot={{ r: 5 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              </Box>
            </SimpleGrid>

            <Box
              bg={cardBg}
              p={6}
              borderRadius="lg"
              border="1px solid"
              borderColor={borderColor}
            >
              <Heading size="md" mb={4}>
                Volume Breakdown by Pool
              </Heading>
              <Table variant="simple" size="sm">
                <Thead>
                  <Tr>
                    <Th>Pool</Th>
                    <Th isNumeric>24h Volume</Th>
                    <Th isNumeric>7d Volume</Th>
                    <Th isNumeric>Share</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {[
                    {
                      pool: "ETH-USDC",
                      d1: "$8.2M",
                      d7: "$52.4M",
                      share: "28.9%",
                    },
                    {
                      pool: "WBTC-ETH",
                      d1: "$7.5M",
                      d7: "$48.1M",
                      share: "26.4%",
                    },
                    {
                      pool: "USDC-DAI-USDT",
                      d1: "$5.8M",
                      d7: "$38.7M",
                      share: "21.3%",
                    },
                    {
                      pool: "ETH-LINK",
                      d1: "$3.2M",
                      d7: "$21.5M",
                      share: "11.8%",
                    },
                    {
                      pool: "Others",
                      d1: "$3.7M",
                      d7: "$21.1M",
                      share: "11.6%",
                    },
                  ].map((r, i) => (
                    <Tr key={i} _hover={{ bg: "gray.700" }}>
                      <Td fontWeight="medium">{r.pool}</Td>
                      <Td isNumeric>{r.d1}</Td>
                      <Td isNumeric>{r.d7}</Td>
                      <Td isNumeric>
                        <Badge colorScheme="brand">{r.share}</Badge>
                      </Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </TabPanel>

          {/* ── Historical ── */}
          <TabPanel px={0}>
            <Box
              bg={cardBg}
              p={6}
              borderRadius="lg"
              border="1px solid"
              borderColor={borderColor}
              mb={8}
            >
              <Heading size="md" mb={6}>
                Quarterly TVL & Volume History
              </Heading>
              <Box h="360px">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={historicalTVL}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="histTvl" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="5%"
                          stopColor="#0080ff"
                          stopOpacity={0.6}
                        />
                        <stop
                          offset="95%"
                          stopColor="#0080ff"
                          stopOpacity={0}
                        />
                      </linearGradient>
                      <linearGradient id="histVol" x1="0" y1="0" x2="0" y2="1">
                        <stop
                          offset="5%"
                          stopColor="#ff7000"
                          stopOpacity={0.6}
                        />
                        <stop
                          offset="95%"
                          stopColor="#ff7000"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="name" stroke="#666" />
                    <YAxis stroke="#666" />
                    <RechartsTooltip
                      {...tooltipStyle}
                      formatter={(v, n) => [
                        `$${v}M`,
                        n === "tvl" ? "TVL" : "Volume",
                      ]}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="tvl"
                      name="TVL ($M)"
                      stroke="#0080ff"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#histTvl)"
                    />
                    <Area
                      type="monotone"
                      dataKey="volume"
                      name="Volume ($M)"
                      stroke="#ff7000"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#histVol)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </Box>
            </Box>

            <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8}>
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Heading size="sm" mb={4}>
                  Key Milestones
                </Heading>
                <Box>
                  {[
                    {
                      date: "Q1 2024",
                      event: "Protocol launch",
                      value: "$5M TVL",
                    },
                    {
                      date: "Q2 2024",
                      event: "Synthetics launch",
                      value: "$52M TVL",
                    },
                    {
                      date: "Q3 2024",
                      event: "100 pools milestone",
                      value: "$79M TVL",
                    },
                    {
                      date: "Q4 2024",
                      event: "Analytics dashboard",
                      value: "$105M TVL",
                    },
                    {
                      date: "Q1 2025",
                      event: "Multi-chain expansion",
                      value: "$128M TVL",
                    },
                  ].map((m, i) => (
                    <Flex
                      key={i}
                      py={3}
                      borderBottom={i < 4 ? "1px solid" : "none"}
                      borderColor="gray.700"
                      align="center"
                    >
                      <Box
                        w="2"
                        h="2"
                        borderRadius="full"
                        bg="brand.500"
                        mr={4}
                        flexShrink={0}
                      />
                      <Box flex={1}>
                        <Text fontWeight="bold" fontSize="sm">
                          {m.event}
                        </Text>
                        <Text fontSize="xs" color={subTextColor}>
                          {m.date}
                        </Text>
                      </Box>
                      <Badge colorScheme="brand" fontSize="xs">
                        {m.value}
                      </Badge>
                    </Flex>
                  ))}
                </Box>
              </Box>

              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                border="1px solid"
                borderColor={borderColor}
              >
                <Heading size="sm" mb={4}>
                  All-Time Stats
                </Heading>
                {[
                  { label: "All-Time High TVL", value: "$142.5M" },
                  { label: "Total Volume Traded", value: "$1.2B" },
                  { label: "Unique Wallets", value: "18,420" },
                  { label: "Total Pools Created", value: "312" },
                  { label: "Total Fees Collected", value: "$3.6M" },
                  { label: "Avg. APY (all-time)", value: "7.8%" },
                ].map((s, i) => (
                  <Flex
                    key={i}
                    justify="space-between"
                    py={2}
                    borderBottom={i < 5 ? "1px solid" : "none"}
                    borderColor="gray.700"
                  >
                    <Text fontSize="sm" color={subTextColor}>
                      {s.label}
                    </Text>
                    <Text fontWeight="bold" fontSize="sm">
                      {s.value}
                    </Text>
                  </Flex>
                ))}
              </Box>
            </SimpleGrid>
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Expand Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="4xl">
        <ModalOverlay backdropFilter="blur(10px)" />
        <ModalContent bg="gray.800" color="white">
          <ModalHeader>
            {selectedChart === "tvl" && "TVL Trend"}
            {selectedChart === "volume" && "Volume Trend"}
            {selectedChart === "distribution" && "Pool Type Distribution"}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <Box h="480px">
              {selectedChart === "tvl" && (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={tvlData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient
                        id="colorTvlM"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="#0080ff"
                          stopOpacity={0.8}
                        />
                        <stop
                          offset="95%"
                          stopColor="#0080ff"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                    <XAxis dataKey="name" stroke="#888" />
                    <YAxis stroke="#888" />
                    <RechartsTooltip
                      {...tooltipStyle}
                      formatter={(v) => [`$${v}M`, "TVL"]}
                    />
                    <Legend />
                    <Area
                      type="monotone"
                      dataKey="tvl"
                      stroke="#0080ff"
                      fillOpacity={1}
                      fill="url(#colorTvlM)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              )}
              {selectedChart === "volume" && (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={volumeData}
                    margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                    <XAxis dataKey="name" stroke="#888" />
                    <YAxis stroke="#888" />
                    <RechartsTooltip
                      {...tooltipStyle}
                      formatter={(v) => [`$${v}M`, "Volume"]}
                    />
                    <Legend />
                    <Bar
                      dataKey="volume"
                      fill="#ff7000"
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              )}
              {selectedChart === "distribution" && (
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={poolTypeData}
                      cx="50%"
                      cy="50%"
                      labelLine
                      outerRadius={180}
                      dataKey="value"
                      label={({ name, percent }) =>
                        `${name} ${(percent * 100).toFixed(0)}%`
                      }
                    >
                      {poolTypeData.map((_, i) => (
                        <Cell key={i} fill={COLORS[i % COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip {...tooltipStyle} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              )}
            </Box>
          </ModalBody>
          <ModalFooter>
            <Button leftIcon={<FiDownload />} colorScheme="brand" mr={3}>
              Download Data
            </Button>
            <Button leftIcon={<FiShare2 />} variant="outline">
              Share
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default Analytics;
