import {
  Badge,
  Box,
  Button,
  Flex,
  Heading,
  HStack,
  Icon,
  IconButton,
  Input,
  InputGroup,
  InputLeftElement,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Progress,
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
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import {
  FiChevronDown,
  FiExternalLink,
  FiFilter,
  FiInfo,
  FiPlus,
  FiSearch,
  FiStar,
  FiTrendingDown,
  FiTrendingUp,
} from "react-icons/fi";
import { Link as RouterLink } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import { useWeb3 } from "../../lib/web3-config.jsx";

// Mock data for charts
const volumeData = [
  { name: "Mon", volume: 1200 },
  { name: "Tue", volume: 1800 },
  { name: "Wed", volume: 1500 },
  { name: "Thu", volume: 2100 },
  { name: "Fri", volume: 2400 },
  { name: "Sat", volume: 1700 },
  { name: "Sun", volume: 1300 },
];

const apyData = [
  { name: "ETH-USDC", apy: 8.4 },
  { name: "WBTC-ETH", apy: 7.2 },
  { name: "ETH-DAI", apy: 6.8 },
  { name: "USDC-DAI", apy: 4.5 },
  { name: "WBTC-USDC", apy: 9.1 },
];

const Pools = () => {
  const { isConnected } = useWeb3();
  const cardBg = useColorModeValue("gray.800", "gray.700");
  const borderColor = useColorModeValue("gray.700", "gray.600");
  const subTextColor = useColorModeValue("gray.400", "gray.400");

  // State for filtering and sorting
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("tvl");
  const [sortOrder, setSortOrder] = useState("desc");
  const [filterType, setFilterType] = useState("all");

  // Modal state
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedPool, setSelectedPool] = useState(null);

  // Mock pools data
  const mockPools = [
    {
      id: "pool-1",
      name: "ETH-USDC",
      assets: ["ETH", "USDC"],
      weights: [50, 50],
      tvl: "$4.2M",
      tvlValue: 4200000,
      volume24h: "$1.2M",
      volumeValue: 1200000,
      apy: "8.4%",
      apyValue: 8.4,
      fee: "0.3%",
      type: "weighted",
      creator: "0x1234...5678",
      myLiquidity: "$25,000",
      hasStaked: true,
    },
    {
      id: "pool-2",
      name: "WBTC-ETH",
      assets: ["WBTC", "ETH"],
      weights: [60, 40],
      tvl: "$8.7M",
      tvlValue: 8700000,
      volume24h: "$3.5M",
      volumeValue: 3500000,
      apy: "7.2%",
      apyValue: 7.2,
      fee: "0.3%",
      type: "weighted",
      creator: "0x9876...5432",
      myLiquidity: "$0",
      hasStaked: false,
    },
    {
      id: "pool-3",
      name: "ETH-DAI",
      assets: ["ETH", "DAI"],
      weights: [50, 50],
      tvl: "$3.1M",
      tvlValue: 3100000,
      volume24h: "$980K",
      volumeValue: 980000,
      apy: "6.8%",
      apyValue: 6.8,
      fee: "0.25%",
      type: "weighted",
      creator: "0x2468...1357",
      myLiquidity: "$12,500",
      hasStaked: true,
    },
    {
      id: "pool-4",
      name: "USDC-DAI",
      assets: ["USDC", "DAI"],
      weights: [50, 50],
      tvl: "$2.5M",
      tvlValue: 2500000,
      volume24h: "$750K",
      volumeValue: 750000,
      apy: "4.5%",
      apyValue: 4.5,
      fee: "0.1%",
      type: "stable",
      creator: "0x1357...2468",
      myLiquidity: "$0",
      hasStaked: false,
    },
    {
      id: "pool-5",
      name: "WBTC-USDC",
      assets: ["WBTC", "USDC"],
      weights: [70, 30],
      tvl: "$6.8M",
      tvlValue: 6800000,
      volume24h: "$2.1M",
      volumeValue: 2100000,
      apy: "9.1%",
      apyValue: 9.1,
      fee: "0.4%",
      type: "weighted",
      creator: "0x3579...8642",
      myLiquidity: "$8,000",
      hasStaked: true,
    },
  ];

  // Filter and sort pools
  const filteredPools = mockPools
    .filter((pool) => {
      // Filter by search query
      if (
        searchQuery &&
        !pool.name.toLowerCase().includes(searchQuery.toLowerCase())
      ) {
        return false;
      }

      // Filter by type (skip the "my-pools" virtual filter here)
      if (
        filterType !== "all" &&
        filterType !== "my-pools" &&
        pool.type !== filterType
      ) {
        return false;
      }

      // Filter by user's pools
      if (
        filterType === "my-pools" &&
        (pool.myLiquidity === "$0" || pool.myLiquidity === "")
      ) {
        return false;
      }

      return true;
    })
    .sort((a, b) => {
      // Sort by selected field
      let valueA, valueB;

      switch (sortBy) {
        case "tvl":
          valueA = a.tvlValue;
          valueB = b.tvlValue;
          break;
        case "volume":
          valueA = a.volumeValue;
          valueB = b.volumeValue;
          break;
        case "apy":
          valueA = a.apyValue;
          valueB = b.apyValue;
          break;
        default:
          valueA = a.tvlValue;
          valueB = b.tvlValue;
      }

      // Apply sort order
      return sortOrder === "desc" ? valueB - valueA : valueA - valueB;
    });

  // Handle pool click
  const handlePoolClick = (pool) => {
    setSelectedPool(pool);
    onOpen();
  };

  // Toggle sort order
  const toggleSortOrder = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("desc");
    }
  };

  return (
    <Box>
      {/* Hero Section */}
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
        {/* Decorative elements */}
        <Box
          position="absolute"
          top="-50px"
          right="-50px"
          w="200px"
          h="200px"
          borderRadius="full"
          bg="brand.500"
          opacity="0.1"
        />
        <Box
          position="absolute"
          bottom="-30px"
          left="30%"
          w="100px"
          h="100px"
          borderRadius="full"
          bg="accent.500"
          opacity="0.1"
        />

        <Flex
          direction={{ base: "column", md: "row" }}
          justify="space-between"
          align={{ base: "flex-start", md: "center" }}
        >
          <Box mb={{ base: 6, md: 0 }}>
            <Heading as="h1" size="xl" mb={4}>
              Liquidity Pools
            </Heading>
            <Text fontSize="lg" color={subTextColor} maxW="600px">
              Provide liquidity to earn fees and participate in the Fluxion
              ecosystem. Explore existing pools or create your own.
            </Text>
          </Box>

          <RouterLink to="/pools/create">
            <Button
              leftIcon={<FiPlus />}
              colorScheme="brand"
              size="lg"
              bgGradient="linear(to-r, brand.500, accent.500)"
              _hover={{
                bgGradient: "linear(to-r, brand.600, accent.600)",
                transform: "translateY(-2px)",
                boxShadow: "lg",
              }}
            >
              Create New Pool
            </Button>
          </RouterLink>
        </Flex>
      </Box>

      {/* Stats Overview */}
      <SimpleGrid columns={{ base: 1, md: 3 }} spacing={6} mb={8}>
        <Box
          bg={cardBg}
          p={6}
          borderRadius="lg"
          boxShadow="md"
          border="1px solid"
          borderColor={borderColor}
        >
          <Heading size="md" mb={4}>
            Total Value Locked
          </Heading>
          <Heading size="2xl" mb={2}>
            $25.3M
          </Heading>
          <HStack>
            <Icon as={FiTrendingUp} color="green.400" />
            <Text color="green.400">+5.2% (24h)</Text>
          </HStack>
        </Box>

        <Box
          bg={cardBg}
          p={6}
          borderRadius="lg"
          boxShadow="md"
          border="1px solid"
          borderColor={borderColor}
        >
          <Heading size="md" mb={4}>
            24h Trading Volume
          </Heading>
          <Box h="150px">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={volumeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis dataKey="name" stroke="#888" />
                <YAxis stroke="#888" />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "rgba(23, 25, 35, 0.9)",
                    border: "1px solid #333",
                    borderRadius: "4px",
                    color: "white",
                  }}
                />
                <Bar dataKey="volume" fill="#0080ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Box>

        <Box
          bg={cardBg}
          p={6}
          borderRadius="lg"
          boxShadow="md"
          border="1px solid"
          borderColor={borderColor}
        >
          <Heading size="md" mb={4}>
            Top APY Pools
          </Heading>
          <Box h="150px">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                layout="vertical"
                data={apyData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                <XAxis type="number" stroke="#888" />
                <YAxis
                  dataKey="name"
                  type="category"
                  stroke="#888"
                  width={80}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "rgba(23, 25, 35, 0.9)",
                    border: "1px solid #333",
                    borderRadius: "4px",
                    color: "white",
                  }}
                  formatter={(value) => [`${value}%`, "APY"]}
                />
                <Bar dataKey="apy" fill="#ff7000" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Box>
      </SimpleGrid>

      {/* Pools Table */}
      <Box
        bg={cardBg}
        p={6}
        borderRadius="lg"
        boxShadow="md"
        border="1px solid"
        borderColor={borderColor}
        mb={8}
      >
        <Flex
          direction={{ base: "column", md: "row" }}
          justify="space-between"
          align={{ base: "flex-start", md: "center" }}
          mb={6}
          gap={4}
        >
          <Heading size="md">Available Pools</Heading>

          <HStack spacing={4}>
            <InputGroup maxW="300px">
              <InputLeftElement pointerEvents="none">
                <Icon as={FiSearch} color="gray.400" />
              </InputLeftElement>
              <Input
                placeholder="Search pools..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </InputGroup>

            <Menu>
              <MenuButton
                as={Button}
                rightIcon={<FiChevronDown />}
                variant="outline"
              >
                <HStack>
                  <Icon as={FiFilter} />
                  <Text>Filter</Text>
                </HStack>
              </MenuButton>
              <MenuList bg="gray.800" borderColor="gray.700">
                <MenuItem
                  onClick={() => setFilterType("all")}
                  bg={filterType === "all" ? "gray.700" : "gray.800"}
                  _hover={{ bg: "gray.700" }}
                >
                  All Pools
                </MenuItem>
                <MenuItem
                  onClick={() => setFilterType("weighted")}
                  bg={filterType === "weighted" ? "gray.700" : "gray.800"}
                  _hover={{ bg: "gray.700" }}
                >
                  Weighted Pools
                </MenuItem>
                <MenuItem
                  onClick={() => setFilterType("stable")}
                  bg={filterType === "stable" ? "gray.700" : "gray.800"}
                  _hover={{ bg: "gray.700" }}
                >
                  Stable Pools
                </MenuItem>
                <MenuItem
                  onClick={() => setFilterType("my-pools")}
                  bg={filterType === "my-pools" ? "gray.700" : "gray.800"}
                  _hover={{ bg: "gray.700" }}
                >
                  My Pools
                </MenuItem>
              </MenuList>
            </Menu>
          </HStack>
        </Flex>

        <Box overflowX="auto">
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>Pool</Th>
                <Th isNumeric>
                  <HStack
                    justify="flex-end"
                    spacing={1}
                    cursor="pointer"
                    onClick={() => toggleSortOrder("tvl")}
                  >
                    <Text>TVL</Text>
                    <Icon
                      as={
                        sortBy === "tvl"
                          ? sortOrder === "asc"
                            ? FiTrendingUp
                            : FiTrendingDown
                          : FiChevronDown
                      }
                      boxSize={4}
                    />
                  </HStack>
                </Th>
                <Th isNumeric>
                  <HStack
                    justify="flex-end"
                    spacing={1}
                    cursor="pointer"
                    onClick={() => toggleSortOrder("volume")}
                  >
                    <Text>Volume (24h)</Text>
                    <Icon
                      as={
                        sortBy === "volume"
                          ? sortOrder === "asc"
                            ? FiTrendingUp
                            : FiTrendingDown
                          : FiChevronDown
                      }
                      boxSize={4}
                    />
                  </HStack>
                </Th>
                <Th isNumeric>
                  <HStack
                    justify="flex-end"
                    spacing={1}
                    cursor="pointer"
                    onClick={() => toggleSortOrder("apy")}
                  >
                    <Text>APY</Text>
                    <Icon
                      as={
                        sortBy === "apy"
                          ? sortOrder === "asc"
                            ? FiTrendingUp
                            : FiTrendingDown
                          : FiChevronDown
                      }
                      boxSize={4}
                    />
                  </HStack>
                </Th>
                <Th>Fee</Th>
                <Th>My Liquidity</Th>
                <Th></Th>
              </Tr>
            </Thead>
            <Tbody>
              {filteredPools.map((pool) => (
                <Tr
                  key={pool.id}
                  _hover={{
                    bg: "gray.700",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                  onClick={() => handlePoolClick(pool)}
                >
                  <Td>
                    <HStack>
                      <HStack spacing={-1}>
                        {pool.assets.map((asset, index) => (
                          <Box
                            key={index}
                            bg={
                              asset === "ETH"
                                ? "blue.500"
                                : asset === "WBTC"
                                  ? "orange.500"
                                  : asset === "USDC"
                                    ? "green.500"
                                    : "purple.500"
                            }
                            borderRadius="full"
                            w="30px"
                            h="30px"
                            display="flex"
                            alignItems="center"
                            justifyContent="center"
                            fontWeight="bold"
                            fontSize="xs"
                            ml={index > 0 ? "-2" : "0"}
                            border="2px solid"
                            borderColor="gray.800"
                          >
                            {asset.charAt(0)}
                          </Box>
                        ))}
                      </HStack>
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="bold">{pool.name}</Text>
                        <Text fontSize="xs" color={subTextColor}>
                          {pool.weights
                            .map((w, i) => `${w}% ${pool.assets[i]}`)
                            .join(" / ")}
                        </Text>
                      </VStack>
                      {pool.type === "stable" && (
                        <Badge colorScheme="purple" ml={2}>
                          Stable
                        </Badge>
                      )}
                    </HStack>
                  </Td>
                  <Td isNumeric fontWeight="medium">
                    {pool.tvl}
                  </Td>
                  <Td isNumeric>{pool.volume24h}</Td>
                  <Td isNumeric>
                    <Text fontWeight="bold" color="green.400">
                      {pool.apy}
                    </Text>
                  </Td>
                  <Td>{pool.fee}</Td>
                  <Td>
                    <HStack>
                      <Text>{pool.myLiquidity}</Text>
                      {pool.hasStaked && (
                        <Tooltip label="Earning rewards">
                          <Icon as={FiStar} color="yellow.400" />
                        </Tooltip>
                      )}
                    </HStack>
                  </Td>
                  <Td>
                    <IconButton
                      aria-label="View pool details"
                      icon={<FiExternalLink />}
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handlePoolClick(pool);
                      }}
                    />
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* Pool Detail Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay backdropFilter="blur(4px)" />
        <ModalContent bg="gray.800" color="white">
          <ModalHeader>
            <HStack>
              <HStack spacing={-1}>
                {selectedPool?.assets.map((asset, index) => (
                  <Box
                    key={index}
                    bg={
                      asset === "ETH"
                        ? "blue.500"
                        : asset === "WBTC"
                          ? "orange.500"
                          : asset === "USDC"
                            ? "green.500"
                            : "purple.500"
                    }
                    borderRadius="full"
                    w="30px"
                    h="30px"
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    fontWeight="bold"
                    fontSize="xs"
                    ml={index > 0 ? "-2" : "0"}
                    border="2px solid"
                    borderColor="gray.800"
                  >
                    {asset.charAt(0)}
                  </Box>
                ))}
              </HStack>
              <Text>{selectedPool?.name} Pool</Text>
              {selectedPool?.type === "stable" && (
                <Badge colorScheme="purple">Stable</Badge>
              )}
            </HStack>
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <Tabs variant="soft-rounded" colorScheme="brand" mb={4}>
              <TabList mb={4}>
                <Tab>Overview</Tab>
                <Tab>Composition</Tab>
                <Tab>Activity</Tab>
              </TabList>

              <TabPanels>
                <TabPanel px={0}>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} mb={6}>
                    <Stat>
                      <StatLabel>Total Value Locked</StatLabel>
                      <StatNumber>{selectedPool?.tvl}</StatNumber>
                      <StatHelpText>
                        <StatArrow type="increase" />
                        5.2% (24h)
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>Volume (24h)</StatLabel>
                      <StatNumber>{selectedPool?.volume24h}</StatNumber>
                      <StatHelpText>
                        <StatArrow type="increase" />
                        12.5% (24h)
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>APY</StatLabel>
                      <StatNumber color="green.400">
                        {selectedPool?.apy}
                      </StatNumber>
                      <StatHelpText>
                        <HStack>
                          <Text>Swap Fee: {selectedPool?.fee}</Text>
                          <Tooltip label="APY includes swap fees and liquidity mining rewards">
                            <Icon as={FiInfo} />
                          </Tooltip>
                        </HStack>
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>My Liquidity</StatLabel>
                      <StatNumber>{selectedPool?.myLiquidity}</StatNumber>
                      <StatHelpText>
                        {selectedPool?.hasStaked ? (
                          <HStack>
                            <Icon as={FiStar} color="yellow.400" />
                            <Text>Earning rewards</Text>
                          </HStack>
                        ) : (
                          <Text color="gray.400">Not staked</Text>
                        )}
                      </StatHelpText>
                    </Stat>
                  </SimpleGrid>

                  <Box mb={6}>
                    <Heading size="sm" mb={2}>
                      Pool Performance
                    </Heading>
                    <Box h="200px">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={[
                            { date: "Apr 5", tvl: 3800000 },
                            { date: "Apr 6", tvl: 3900000 },
                            { date: "Apr 7", tvl: 4000000 },
                            { date: "Apr 8", tvl: 4100000 },
                            { date: "Apr 9", tvl: 4050000 },
                            { date: "Apr 10", tvl: 4150000 },
                            { date: "Apr 11", tvl: 4200000 },
                          ]}
                        >
                          <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                          <XAxis dataKey="date" stroke="#888" />
                          <YAxis stroke="#888" />
                          <RechartsTooltip
                            contentStyle={{
                              backgroundColor: "rgba(23, 25, 35, 0.9)",
                              border: "1px solid #333",
                              borderRadius: "4px",
                              color: "white",
                            }}
                            formatter={(value) => [
                              `$${(value / 1000000).toFixed(2)}M`,
                              "TVL",
                            ]}
                          />
                          <Line
                            type="monotone"
                            dataKey="tvl"
                            stroke="#0080ff"
                            strokeWidth={2}
                            dot={{ r: 4 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </Box>
                  </Box>

                  <Box>
                    <Heading size="sm" mb={2}>
                      Pool Information
                    </Heading>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4}>
                      <Box>
                        <Text color={subTextColor}>Pool ID</Text>
                        <Text fontWeight="medium">{selectedPool?.id}</Text>
                      </Box>
                      <Box>
                        <Text color={subTextColor}>Creator</Text>
                        <Text fontWeight="medium">{selectedPool?.creator}</Text>
                      </Box>
                      <Box>
                        <Text color={subTextColor}>Pool Type</Text>
                        <Text fontWeight="medium" textTransform="capitalize">
                          {selectedPool?.type}
                        </Text>
                      </Box>
                      <Box>
                        <Text color={subTextColor}>Creation Date</Text>
                        <Text fontWeight="medium">Apr 5, 2025</Text>
                      </Box>
                    </SimpleGrid>
                  </Box>
                </TabPanel>

                <TabPanel px={0}>
                  <Box mb={6}>
                    <Heading size="sm" mb={4}>
                      Asset Weights
                    </Heading>
                    {selectedPool?.assets.map((asset, index) => (
                      <Box key={index} mb={3}>
                        <Flex justify="space-between" mb={1}>
                          <HStack>
                            <Box
                              bg={
                                asset === "ETH"
                                  ? "blue.500"
                                  : asset === "WBTC"
                                    ? "orange.500"
                                    : asset === "USDC"
                                      ? "green.500"
                                      : "purple.500"
                              }
                              borderRadius="full"
                              w="24px"
                              h="24px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                              fontWeight="bold"
                              fontSize="xs"
                            >
                              {asset.charAt(0)}
                            </Box>
                            <Text>{asset}</Text>
                          </HStack>
                          <Text fontWeight="bold">
                            {selectedPool?.weights[index]}%
                          </Text>
                        </Flex>
                        <Progress
                          value={selectedPool?.weights[index]}
                          size="sm"
                          colorScheme={
                            asset === "ETH"
                              ? "blue"
                              : asset === "WBTC"
                                ? "orange"
                                : asset === "USDC"
                                  ? "green"
                                  : "purple"
                          }
                          borderRadius="full"
                          bg="gray.600"
                        />
                      </Box>
                    ))}
                  </Box>

                  <Box mb={6}>
                    <Heading size="sm" mb={4}>
                      Pool Composition
                    </Heading>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                      {selectedPool?.assets.map((asset, index) => (
                        <Box
                          key={index}
                          p={4}
                          borderRadius="md"
                          bg="gray.700"
                          border="1px solid"
                          borderColor="gray.600"
                        >
                          <HStack mb={3}>
                            <Box
                              bg={
                                asset === "ETH"
                                  ? "blue.500"
                                  : asset === "WBTC"
                                    ? "orange.500"
                                    : asset === "USDC"
                                      ? "green.500"
                                      : "purple.500"
                              }
                              borderRadius="full"
                              w="36px"
                              h="36px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                              fontWeight="bold"
                              fontSize="sm"
                            >
                              {asset.charAt(0)}
                            </Box>
                            <VStack align="start" spacing={0}>
                              <Text fontWeight="bold">{asset}</Text>
                              <Text fontSize="sm" color={subTextColor}>
                                {asset === "ETH"
                                  ? "Ethereum"
                                  : asset === "WBTC"
                                    ? "Wrapped Bitcoin"
                                    : asset === "USDC"
                                      ? "USD Coin"
                                      : "Dai Stablecoin"}
                              </Text>
                            </VStack>
                          </HStack>

                          <SimpleGrid columns={2} spacing={4}>
                            <Box>
                              <Text color={subTextColor}>Amount</Text>
                              <Text fontWeight="bold">
                                {asset === "ETH"
                                  ? "1,250"
                                  : asset === "WBTC"
                                    ? "42"
                                    : asset === "USDC"
                                      ? "2,100,000"
                                      : "2,050,000"}
                              </Text>
                            </Box>
                            <Box>
                              <Text color={subTextColor}>Value</Text>
                              <Text fontWeight="bold">
                                {asset === "ETH"
                                  ? "$2.1M"
                                  : asset === "WBTC"
                                    ? "$2.1M"
                                    : asset === "USDC"
                                      ? "$2.1M"
                                      : "$2.05M"}
                              </Text>
                            </Box>
                          </SimpleGrid>
                        </Box>
                      ))}
                    </SimpleGrid>
                  </Box>
                </TabPanel>

                <TabPanel px={0}>
                  <Box mb={6}>
                    <Heading size="sm" mb={4}>
                      Recent Transactions
                    </Heading>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Type</Th>
                          <Th>Amount</Th>
                          <Th>Address</Th>
                          <Th>Time</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        <Tr>
                          <Td>
                            <Badge colorScheme="green">Add Liquidity</Badge>
                          </Td>
                          <Td>$25,000</Td>
                          <Td>0x1234...5678</Td>
                          <Td>2 hours ago</Td>
                        </Tr>
                        <Tr>
                          <Td>
                            <Badge colorScheme="blue">Swap</Badge>
                          </Td>
                          <Td>5 ETH → 10,000 USDC</Td>
                          <Td>0x8765...4321</Td>
                          <Td>3 hours ago</Td>
                        </Tr>
                        <Tr>
                          <Td>
                            <Badge colorScheme="red">Remove Liquidity</Badge>
                          </Td>
                          <Td>$12,500</Td>
                          <Td>0x5432...1234</Td>
                          <Td>5 hours ago</Td>
                        </Tr>
                        <Tr>
                          <Td>
                            <Badge colorScheme="blue">Swap</Badge>
                          </Td>
                          <Td>15,000 USDC → 7.5 ETH</Td>
                          <Td>0x9876...5432</Td>
                          <Td>6 hours ago</Td>
                        </Tr>
                        <Tr>
                          <Td>
                            <Badge colorScheme="green">Add Liquidity</Badge>
                          </Td>
                          <Td>$50,000</Td>
                          <Td>0x2468...1357</Td>
                          <Td>8 hours ago</Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </Box>
                </TabPanel>
              </TabPanels>
            </Tabs>
          </ModalBody>

          <ModalFooter>
            <HStack spacing={4}>
              <Button
                colorScheme="brand"
                bgGradient="linear(to-r, brand.500, accent.500)"
                _hover={{
                  bgGradient: "linear(to-r, brand.600, accent.600)",
                  transform: "translateY(-2px)",
                  boxShadow: "lg",
                }}
              >
                Add Liquidity
              </Button>
              <Button variant="outline">Swap</Button>
              {selectedPool?.myLiquidity !== "$0" && (
                <Button variant="outline" colorScheme="red">
                  Remove Liquidity
                </Button>
              )}
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default Pools;
