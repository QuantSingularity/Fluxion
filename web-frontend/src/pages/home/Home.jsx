import {
  Badge,
  Box,
  Button,
  Flex,
  Grid,
  Heading,
  HStack,
  Icon,
  SimpleGrid,
  Stat,
  StatArrow,
  StatHelpText,
  StatLabel,
  StatNumber,
  Text,
  useColorModeValue,
  VStack,
} from "@chakra-ui/react";
import {
  FiActivity,
  FiArrowRight,
  FiBarChart2,
  FiDollarSign,
  FiDroplet,
  FiLock,
  FiShield,
  FiTrendingUp,
  FiZap,
} from "react-icons/fi";
import { Link as RouterLink } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useWeb3 } from "../../lib/web3-config.jsx";

const tvlHistory = [
  { name: "Jan", tvl: 45 },
  { name: "Feb", tvl: 62 },
  { name: "Mar", tvl: 78 },
  { name: "Apr", tvl: 95 },
  { name: "May", tvl: 115 },
  { name: "Jun", tvl: 132 },
  { name: "Jul", tvl: 142.5 },
];

const featuredPools = [
  { name: "ETH-USDC", apy: "8.4%", tvl: "$4.2M", type: "Weighted" },
  { name: "WBTC-ETH", apy: "7.2%", tvl: "$8.7M", type: "Weighted" },
  { name: "USDC-DAI", apy: "4.5%", tvl: "$2.5M", type: "Stable" },
];

const features = [
  {
    icon: FiDroplet,
    title: "Flexible Liquidity",
    description:
      "Create custom-weighted pools with up to 8 tokens. Set your own weights and fees to match your strategy.",
    color: "brand.500",
  },
  {
    icon: FiDollarSign,
    title: "Synthetic Assets",
    description:
      "Trade real-world assets on-chain without custody risk. Access stocks, commodities and forex 24/7.",
    color: "accent.500",
  },
  {
    icon: FiBarChart2,
    title: "Deep Analytics",
    description:
      "Comprehensive charts, APY tracking and risk metrics to help you make data-driven decisions.",
    color: "green.400",
  },
  {
    icon: FiShield,
    title: "Non-Custodial",
    description:
      "Your keys, your assets. All operations are executed directly on-chain with full transparency.",
    color: "purple.400",
  },
  {
    icon: FiZap,
    title: "Low Fees",
    description:
      "Optimized smart contracts keep gas costs low and swap fees competitive across all pools.",
    color: "yellow.400",
  },
  {
    icon: FiLock,
    title: "Battle-Tested",
    description:
      "Audited contracts and real-time risk monitoring protect your liquidity positions at all times.",
    color: "red.400",
  },
];

const Home = () => {
  const { isConnected, connectWallet } = useWeb3();
  const cardBg = useColorModeValue("gray.800", "gray.700");
  const borderColor = useColorModeValue("gray.700", "gray.600");
  const subTextColor = "gray.400";

  return (
    <Box>
      {/* ─── Hero ─────────────────────────────────────────── */}
      <Box
        position="relative"
        overflow="hidden"
        borderRadius="2xl"
        mb={12}
        p={{ base: 10, md: 16 }}
        bgGradient="linear(135deg, gray.900 0%, gray.800 50%, gray.900 100%)"
        border="1px solid"
        borderColor={borderColor}
        boxShadow="2xl"
      >
        {/* Background blobs */}
        <Box
          position="absolute"
          top="-80px"
          right="-80px"
          w="350px"
          h="350px"
          borderRadius="full"
          bg="brand.500"
          opacity="0.08"
          filter="blur(40px)"
        />
        <Box
          position="absolute"
          bottom="-60px"
          left="20%"
          w="250px"
          h="250px"
          borderRadius="full"
          bg="accent.500"
          opacity="0.08"
          filter="blur(40px)"
        />

        <Flex
          direction={{ base: "column", lg: "row" }}
          align="center"
          justify="space-between"
          gap={10}
        >
          <Box maxW="600px" zIndex={1}>
            <Badge
              colorScheme="brand"
              mb={4}
              px={3}
              py={1}
              borderRadius="full"
              fontSize="sm"
            >
              🚀 Next-Gen DeFi Protocol
            </Badge>
            <Heading
              as="h1"
              fontSize={{ base: "3xl", md: "5xl" }}
              fontWeight="extrabold"
              lineHeight="1.1"
              mb={6}
              bgGradient="linear(to-r, white, gray.300)"
              bgClip="text"
            >
              The Future of
              <br />
              <Box
                as="span"
                bgGradient="linear(to-r, brand.400, accent.400)"
                bgClip="text"
              >
                Decentralised Liquidity
              </Box>
            </Heading>
            <Text
              fontSize={{ base: "md", md: "lg" }}
              color={subTextColor}
              mb={8}
              lineHeight="1.8"
            >
              Provide liquidity with custom-weighted pools, mint synthetic
              assets, and earn competitive yields — all in one non-custodial
              platform secured by Ethereum.
            </Text>

            <HStack spacing={4} flexWrap="wrap">
              <RouterLink to="/pools">
                <Button
                  size="lg"
                  colorScheme="brand"
                  bgGradient="linear(to-r, brand.500, accent.500)"
                  _hover={{
                    bgGradient: "linear(to-r, brand.600, accent.600)",
                    transform: "translateY(-2px)",
                    boxShadow: "0 0 30px rgba(0,128,255,0.4)",
                  }}
                  rightIcon={<FiArrowRight />}
                  transition="all 0.2s"
                >
                  Explore Pools
                </Button>
              </RouterLink>

              {!isConnected && (
                <Button
                  size="lg"
                  variant="outline"
                  borderColor="brand.500"
                  color="brand.300"
                  _hover={{
                    bg: "brand.500",
                    color: "white",
                    transform: "translateY(-2px)",
                  }}
                  onClick={connectWallet}
                  transition="all 0.2s"
                >
                  Connect Wallet
                </Button>
              )}
            </HStack>
          </Box>

          {/* Mini TVL chart */}
          <Box
            flex="1"
            minW={{ base: "100%", lg: "340px" }}
            maxW="420px"
            bg={cardBg}
            p={6}
            borderRadius="xl"
            border="1px solid"
            borderColor={borderColor}
            zIndex={1}
          >
            <Flex justify="space-between" align="center" mb={4}>
              <Text fontWeight="bold" color="gray.300">
                Total Value Locked
              </Text>
              <Badge colorScheme="green" px={2} py={1} borderRadius="full">
                +67.5%
              </Badge>
            </Flex>
            <Heading
              size="xl"
              mb={4}
              bgGradient="linear(to-r, brand.400, accent.400)"
              bgClip="text"
            >
              $142.5M
            </Heading>
            <Box h="140px">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={tvlHistory}>
                  <defs>
                    <linearGradient id="heroTvl" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0080ff" stopOpacity={0.6} />
                      <stop offset="95%" stopColor="#0080ff" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                  <XAxis dataKey="name" stroke="#666" tick={{ fontSize: 11 }} />
                  <YAxis stroke="#666" tick={{ fontSize: 11 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "rgba(15,20,30,0.95)",
                      border: "1px solid #333",
                      borderRadius: "8px",
                      color: "white",
                    }}
                    formatter={(v) => [`$${v}M`, "TVL"]}
                  />
                  <Area
                    type="monotone"
                    dataKey="tvl"
                    stroke="#0080ff"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#heroTvl)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </Box>
          </Box>
        </Flex>
      </Box>

      {/* ─── Protocol Stats ─────────────────────────────────── */}
      <SimpleGrid columns={{ base: 2, md: 4 }} spacing={5} mb={12}>
        {[
          {
            label: "Total Value Locked",
            value: "$142.5M",
            change: "+23.36%",
            up: true,
            icon: FiDollarSign,
          },
          {
            label: "24h Volume",
            value: "$28.4M",
            change: "+12.05%",
            up: true,
            icon: FiBarChart2,
          },
          {
            label: "Active Pools",
            value: "247",
            change: "+8 today",
            up: true,
            icon: FiDroplet,
          },
          {
            label: "Average APY",
            value: "8.74%",
            change: "-0.42%",
            up: false,
            icon: FiTrendingUp,
          },
        ].map((stat, i) => (
          <Box
            key={i}
            bg={cardBg}
            p={5}
            borderRadius="lg"
            border="1px solid"
            borderColor={borderColor}
            _hover={{
              borderColor: "brand.600",
              transform: "translateY(-2px)",
              transition: "all 0.2s",
            }}
            transition="all 0.2s"
          >
            <Stat>
              <HStack mb={1}>
                <Icon as={stat.icon} color="brand.400" boxSize={4} />
                <StatLabel fontSize="xs" color={subTextColor}>
                  {stat.label}
                </StatLabel>
              </HStack>
              <StatNumber fontSize="xl" fontWeight="bold">
                {stat.value}
              </StatNumber>
              <StatHelpText mb={0}>
                <StatArrow type={stat.up ? "increase" : "decrease"} />
                {stat.change}
              </StatHelpText>
            </Stat>
          </Box>
        ))}
      </SimpleGrid>

      {/* ─── Featured Pools ─────────────────────────────────── */}
      <Box mb={12}>
        <Flex justify="space-between" align="center" mb={6}>
          <Heading size="lg">Featured Pools</Heading>
          <RouterLink to="/pools">
            <Button
              size="sm"
              variant="ghost"
              color="brand.400"
              rightIcon={<FiArrowRight />}
            >
              View all
            </Button>
          </RouterLink>
        </Flex>

        <SimpleGrid columns={{ base: 1, md: 3 }} spacing={5}>
          {featuredPools.map((pool, i) => (
            <Box
              key={i}
              bg={cardBg}
              p={6}
              borderRadius="lg"
              border="1px solid"
              borderColor={borderColor}
              _hover={{
                borderColor: "brand.500",
                transform: "translateY(-3px)",
                boxShadow: "0 8px 30px rgba(0,128,255,0.15)",
              }}
              transition="all 0.25s"
              cursor="pointer"
              as={RouterLink}
              to="/pools"
            >
              <Flex justify="space-between" align="start" mb={4}>
                <HStack spacing={-1}>
                  {pool.name.split("-").map((token, idx) => (
                    <Box
                      key={idx}
                      bg={idx === 0 ? "brand.500" : "accent.500"}
                      borderRadius="full"
                      w="32px"
                      h="32px"
                      display="flex"
                      alignItems="center"
                      justifyContent="center"
                      fontWeight="bold"
                      fontSize="xs"
                      ml={idx > 0 ? "-2" : "0"}
                      border="2px solid"
                      borderColor={cardBg}
                    >
                      {token.charAt(0)}
                    </Box>
                  ))}
                </HStack>
                <Badge
                  colorScheme={pool.type === "Stable" ? "purple" : "blue"}
                  px={2}
                >
                  {pool.type}
                </Badge>
              </Flex>

              <Heading size="md" mb={1}>
                {pool.name}
              </Heading>
              <Text color={subTextColor} fontSize="sm" mb={4}>
                TVL: {pool.tvl}
              </Text>

              <Flex justify="space-between" align="center">
                <Box>
                  <Text fontSize="xs" color={subTextColor}>
                    APY
                  </Text>
                  <Text fontSize="xl" fontWeight="bold" color="green.400">
                    {pool.apy}
                  </Text>
                </Box>
                <Button size="sm" colorScheme="brand" variant="outline">
                  Add Liquidity
                </Button>
              </Flex>
            </Box>
          ))}
        </SimpleGrid>
      </Box>

      {/* ─── Features ───────────────────────────────────────── */}
      <Box mb={12}>
        <Heading size="lg" mb={2} textAlign="center">
          Why Fluxion?
        </Heading>
        <Text color={subTextColor} textAlign="center" mb={8}>
          Everything you need to participate in the next generation of DeFi.
        </Text>

        <Grid
          templateColumns={{
            base: "1fr",
            md: "repeat(2, 1fr)",
            lg: "repeat(3, 1fr)",
          }}
          gap={5}
        >
          {features.map((feat, i) => (
            <Box
              key={i}
              bg={cardBg}
              p={6}
              borderRadius="lg"
              border="1px solid"
              borderColor={borderColor}
              _hover={{
                borderColor: feat.color,
                transform: "translateY(-2px)",
              }}
              transition="all 0.2s"
            >
              <Box
                w="44px"
                h="44px"
                borderRadius="lg"
                bg={`${feat.color}22`}
                display="flex"
                alignItems="center"
                justifyContent="center"
                mb={4}
              >
                <Icon as={feat.icon} color={feat.color} boxSize={5} />
              </Box>
              <Heading size="sm" mb={2}>
                {feat.title}
              </Heading>
              <Text color={subTextColor} fontSize="sm" lineHeight="1.7">
                {feat.description}
              </Text>
            </Box>
          ))}
        </Grid>
      </Box>

      {/* ─── CTA Banner ─────────────────────────────────────── */}
      <Box
        p={{ base: 8, md: 12 }}
        borderRadius="2xl"
        bgGradient="linear(135deg, brand.900 0%, gray.800 100%)"
        border="1px solid"
        borderColor="brand.700"
        textAlign="center"
        position="relative"
        overflow="hidden"
      >
        <Box
          position="absolute"
          top="-40px"
          left="50%"
          transform="translateX(-50%)"
          w="300px"
          h="300px"
          borderRadius="full"
          bg="brand.500"
          opacity="0.06"
          filter="blur(50px)"
        />
        <Icon as={FiActivity} boxSize={10} color="brand.400" mb={4} />
        <Heading size="lg" mb={4}>
          Start earning today
        </Heading>
        <Text color={subTextColor} maxW="500px" mx="auto" mb={8}>
          Join thousands of liquidity providers earning competitive yields on
          the Fluxion protocol. No minimums, no lock-ups.
        </Text>
        <HStack spacing={4} justify="center" flexWrap="wrap">
          <RouterLink to="/pools/create">
            <Button
              size="lg"
              colorScheme="brand"
              bgGradient="linear(to-r, brand.500, accent.500)"
              _hover={{
                bgGradient: "linear(to-r, brand.600, accent.600)",
                transform: "translateY(-2px)",
                boxShadow: "0 0 30px rgba(0,128,255,0.3)",
              }}
              transition="all 0.2s"
            >
              Create a Pool
            </Button>
          </RouterLink>
          <RouterLink to="/analytics">
            <Button
              size="lg"
              variant="outline"
              borderColor="gray.600"
              _hover={{ borderColor: "brand.500", color: "brand.300" }}
              transition="all 0.2s"
            >
              View Analytics
            </Button>
          </RouterLink>
        </HStack>
      </Box>
    </Box>
  );
};

export default Home;
