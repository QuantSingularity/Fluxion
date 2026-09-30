import {
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Flex,
  FormControl,
  FormLabel,
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
  NumberInput,
  NumberInputField,
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
  Tr,
  useColorModeValue,
  useDisclosure,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { ethers } from "ethers";
import { useEffect, useState } from "react";
import {
  FiAlertTriangle,
  FiDollarSign,
  FiPlus,
  FiTrendingUp,
} from "react-icons/fi";
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
import {
  getSyntheticPosition,
  listSyntheticAssets,
  mintSynthetic,
} from "../synthetics.js";

// Illustrative-only chart data: there's no on-chain price/volume history
// indexer (subgraph) wired up anywhere in this project, so these trend
// lines can't be real. Shown only as a demo of what the chart will look
// like once a real indexer is connected.
const priceData = [
  { name: "Jan", price: 100 },
  { name: "Feb", price: 120 },
  { name: "Mar", price: 110 },
  { name: "Apr", price: 140 },
  { name: "May", price: 130 },
  { name: "Jun", price: 160 },
  { name: "Jul", price: 170 },
];

const volumeData = [
  { name: "Jan", volume: 2400 },
  { name: "Feb", volume: 1398 },
  { name: "Mar", volume: 9800 },
  { name: "Apr", volume: 3908 },
  { name: "May", volume: 4800 },
  { name: "Jun", volume: 3800 },
  { name: "Jul", volume: 4300 },
];

// Demo synthetics shown until real ones load (or if none are registered /
// the read fails) so the page isn't empty on a fresh deployment.
const DEMO_SYNTHETICS = [
  {
    id: "synth-1",
    name: "sETH",
    baseAsset: "ETH",
    price: "$1,720.45",
    priceChange: "+2.4%",
    isUp: true,
    tvl: "$42.5M",
    volume24h: "$8.2M",
    collateralization: "150%",
    description:
      "Synthetic Ethereum that tracks the price of ETH through oracle price feeds.",
    isDemo: true,
  },
  {
    id: "synth-2",
    name: "sBTC",
    baseAsset: "BTC",
    price: "$42,350.78",
    priceChange: "+1.8%",
    isUp: true,
    tvl: "$68.3M",
    volume24h: "$12.5M",
    collateralization: "150%",
    description:
      "Synthetic Bitcoin that tracks the price of BTC through oracle price feeds.",
    isDemo: true,
  },
  {
    id: "synth-3",
    name: "sGOLD",
    baseAsset: "GOLD",
    price: "$1,845.20",
    priceChange: "-0.5%",
    isUp: false,
    tvl: "$15.7M",
    volume24h: "$3.2M",
    collateralization: "175%",
    description:
      "Synthetic Gold that tracks the price of gold through oracle price feeds.",
    isDemo: true,
  },
  {
    id: "synth-4",
    name: "sEUR",
    baseAsset: "EUR",
    price: "$1.08",
    priceChange: "+0.2%",
    isUp: true,
    tvl: "$22.1M",
    volume24h: "$5.4M",
    collateralization: "120%",
    description:
      "Synthetic Euro that tracks the price of EUR through oracle price feeds.",
    isDemo: true,
  },
  {
    id: "synth-5",
    name: "sTSLA",
    baseAsset: "TSLA",
    price: "$248.50",
    priceChange: "-1.2%",
    isUp: false,
    tvl: "$8.9M",
    volume24h: "$2.1M",
    collateralization: "200%",
    description:
      "Synthetic Tesla stock that tracks the price of TSLA through oracle price feeds.",
    isDemo: true,
  },
];

// Demo positions shown when there's no live wallet position data (not
// connected, no live assets, or nothing minted yet), clearly distinguished
// via isDemo so the UI can label them.
const DEMO_POSITIONS = [
  {
    id: "position-1",
    synthetic: "sETH",
    amountLabel: "5.2 sETH",
    collateralLabel: "$13,419.51",
    cRatioLabel: "150%",
    health: 85,
    isDemo: true,
  },
  {
    id: "position-2",
    synthetic: "sBTC",
    amountLabel: "0.25 sBTC",
    collateralLabel: "$15,881.55",
    cRatioLabel: "150%",
    health: 92,
    isDemo: true,
  },
];
// the existing cards/table expect. Fields with no on-chain source (TVL,
// 24h volume/change, collateralization ratio at the asset level rather
// than per-position) are shown as "-" rather than fabricated, since
// getting them for real needs a subgraph indexer this project doesn't have
// wired up yet.
function normalizeOnChainAsset(asset) {
  const priceNum = Number(ethers.formatUnits(asset.price18, 18));
  return {
    id: asset.assetId,
    assetId: asset.assetId,
    name: asset.label,
    baseAsset: asset.label.replace(/^s/, ""),
    price: `$${priceNum.toLocaleString(undefined, { maximumFractionDigits: 2 })}`,
    priceChange: "-",
    isUp: true,
    tvl: "-",
    volume24h: "-",
    collateralization: "-",
    description: `Synthetic asset tracked via Chainlink oracle. Collateral token: ${asset.collateralToken.slice(0, 10)}...`,
    active: asset.active,
    isDemo: false,
  };
}

const Synthetics = () => {
  const { isConnected, provider, account } = useWeb3();
  const cardBg = useColorModeValue("gray.800", "gray.700");
  const borderColor = useColorModeValue("gray.700", "gray.600");
  const subTextColor = useColorModeValue("gray.400", "gray.400");
  const toast = useToast();

  // Modal state
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selectedSynthetic, setSelectedSynthetic] = useState(null);

  // Mint modal state
  const {
    isOpen: isMintOpen,
    onOpen: onMintOpen,
    onClose: onMintClose,
  } = useDisclosure();
  const [mintTarget, setMintTarget] = useState(null);
  const [mintCollateral, setMintCollateral] = useState("");
  const [mintSyntheticAmount, setMintSyntheticAmount] = useState("");
  const [isMinting, setIsMinting] = useState(false);

  // State for active tab
  const [activeTab, setActiveTab] = useState(0);

  // Real on-chain synthetics, loaded via listSyntheticAssets. Falls back to
  // demo data (clearly labeled below) if none are registered yet, or if
  // the read fails (e.g. no provider/RPC available).
  const [synthetics, setSynthetics] = useState(DEMO_SYNTHETICS);
  const [isLiveData, setIsLiveData] = useState(false);
  const [isLoadingAssets, setIsLoadingAssets] = useState(false);

  // Real positions for the connected wallet, one getPosition call per
  // listed synthetic asset - this works from live contract reads alone, no
  // subgraph needed, unlike TVL/volume history or a holders list.
  const [userPositions, setUserPositions] = useState([]);
  const [isLoadingPositions, setIsLoadingPositions] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function loadAssets() {
      if (!provider) return;
      setIsLoadingAssets(true);
      try {
        const onChainAssets = await listSyntheticAssets(provider);
        if (cancelled) return;
        if (onChainAssets.length > 0) {
          setSynthetics(onChainAssets.map(normalizeOnChainAsset));
          setIsLiveData(true);
        } else {
          setSynthetics(DEMO_SYNTHETICS);
          setIsLiveData(false);
        }
      } catch (err) {
        console.error("Error loading synthetic assets:", err);
        if (!cancelled) {
          setSynthetics(DEMO_SYNTHETICS);
          setIsLiveData(false);
        }
      } finally {
        if (!cancelled) setIsLoadingAssets(false);
      }
    }
    loadAssets();
    return () => {
      cancelled = true;
    };
  }, [provider]);

  useEffect(() => {
    let cancelled = false;
    async function loadPositions() {
      if (!provider || !account || !isLiveData) {
        setUserPositions(DEMO_POSITIONS);
        return;
      }
      setIsLoadingPositions(true);
      try {
        const results = await Promise.all(
          synthetics.map(async (s) => {
            try {
              const pos = await getSyntheticPosition(
                provider,
                s.assetId,
                account,
              );
              if (pos.debt === 0n) return null;
              const collateralStr = ethers.formatUnits(pos.collateral, 18);
              return {
                id: s.assetId,
                synthetic: s.name,
                amountLabel: `${ethers.formatUnits(pos.debt, 18)} ${s.name}`,
                collateralLabel: `${collateralStr} ${s.collateralToken.slice(0, 8)}...`,
                cRatioLabel: `${(Number(pos.ratioBPS) / 100).toFixed(1)}%`,
                health: Math.min(100, Math.round(Number(pos.ratioBPS) / 150)),
                isLiquidatable: pos.isLiquidatable,
                isDemo: false,
              };
            } catch {
              return null;
            }
          }),
        );
        if (!cancelled) {
          const real = results.filter(Boolean);
          setUserPositions(real.length > 0 ? real : []);
        }
      } finally {
        if (!cancelled) setIsLoadingPositions(false);
      }
    }
    loadPositions();
    return () => {
      cancelled = true;
    };
  }, [provider, account, isLiveData, synthetics]);

  // Handle synthetic click
  const handleSyntheticClick = (synthetic) => {
    setSelectedSynthetic(synthetic);
    onOpen();
  };

  const handleTradeClick = (synthetic) => {
    toast({
      title: "Trading not yet available",
      description:
        `${synthetic.name} can be minted against collateral, but there's ` +
        "no on-chain swap function for synthetic assets in this protocol " +
        "yet - only isolated mint/burn/liquidate.",
      status: "info",
      duration: 6000,
      isClosable: true,
    });
  };

  const handleMintClick = (synthetic) => {
    if (synthetic.isDemo) {
      toast({
        title: "Demo asset",
        description:
          "This is placeholder data - no real synthetic asset is " +
          "registered for it on-chain yet.",
        status: "warning",
        duration: 5000,
        isClosable: true,
      });
      return;
    }
    setMintTarget(synthetic);
    setMintCollateral("");
    setMintSyntheticAmount("");
    onMintOpen();
  };

  const submitMint = async () => {
    if (!isConnected) {
      toast({
        title: "Connect your wallet",
        description: "Connect a wallet to mint synthetic assets.",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
      return;
    }
    if (!mintCollateral || !mintSyntheticAmount) {
      toast({
        title: "Missing amounts",
        description: "Enter both a collateral and synthetic amount.",
        status: "error",
        duration: 4000,
        isClosable: true,
      });
      return;
    }
    setIsMinting(true);
    try {
      const collateralAmount = ethers.parseUnits(mintCollateral, 18);
      const syntheticAmount = ethers.parseUnits(mintSyntheticAmount, 18);
      await mintSynthetic(
        provider,
        mintTarget.assetId,
        collateralAmount,
        syntheticAmount,
      );
      toast({
        title: "Mint successful",
        description: `Minted ${mintSyntheticAmount} ${mintTarget.name}.`,
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      onMintClose();
    } catch (err) {
      console.error("Error minting synthetic:", err);
      const message =
        err?.shortMessage || err?.reason || err?.message || "Mint failed.";
      toast({
        title: "Mint failed",
        description: message,
        status: "error",
        duration: 8000,
        isClosable: true,
      });
    } finally {
      setIsMinting(false);
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
              Synthetic Assets
            </Heading>
            <Text fontSize="lg" color={subTextColor} maxW="600px">
              Trade synthetic assets that track the price of real-world assets
              without owning the underlying asset. Access global markets 24/7.
            </Text>
          </Box>

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
            onClick={() => {
              const target = synthetics.find((s) => !s.isDemo);
              if (target) {
                handleMintClick(target);
              } else {
                toast({
                  title: "No live synthetic assets yet",
                  description:
                    "Pick an asset from the table below once real ones are registered on-chain.",
                  status: "info",
                  duration: 5000,
                  isClosable: true,
                });
              }
            }}
          >
            Mint Synthetic
          </Button>
        </Flex>
      </Box>

      {!isLiveData && (
        <Box
          mb={4}
          px={4}
          py={2}
          borderRadius="md"
          bg="yellow.900"
          border="1px solid"
          borderColor="yellow.600"
        >
          <Text fontSize="sm" color="yellow.200">
            {isLoadingAssets
              ? "Loading assets from chain..."
              : "Showing demo data - connect a wallet or check the RPC connection to see real registered synthetic assets."}
          </Text>
        </Box>
      )}

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
            $157.5M
          </Heading>
          <HStack>
            <Icon as={FiTrendingUp} color="green.400" />
            <Text color="green.400">+12.8% (24h)</Text>
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
          <Heading size="2xl" mb={2}>
            $31.4M
          </Heading>
          <HStack>
            <Icon as={FiTrendingUp} color="green.400" />
            <Text color="green.400">+8.5% (24h)</Text>
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
            Active Synthetics
          </Heading>
          <Heading size="2xl" mb={2}>
            15
          </Heading>
          <HStack>
            <Icon as={FiTrendingUp} color="green.400" />
            <Text color="green.400">+2 new</Text>
          </HStack>
        </Box>
      </SimpleGrid>

      {/* Charts Section */}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8} mb={8}>
        <Box
          bg={cardBg}
          p={6}
          borderRadius="lg"
          boxShadow="md"
          border="1px solid"
          borderColor={borderColor}
        >
          <Heading size="md" mb={6}>
            Price Performance
          </Heading>
          <Box h="300px">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={priceData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
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
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#0080ff"
                  strokeWidth={2}
                  dot={{ r: 4 }}
                />
              </LineChart>
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
          <Heading size="md" mb={6}>
            Trading Volume
          </Heading>
          <Box h="300px">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={volumeData}
                margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
              >
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
                <Bar dataKey="volume" fill="#ff7000" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Box>
        </Box>
      </SimpleGrid>

      {/* Synthetics Table */}
      <Box
        bg={cardBg}
        p={6}
        borderRadius="lg"
        boxShadow="md"
        border="1px solid"
        borderColor={borderColor}
        mb={8}
      >
        <Heading size="md" mb={6}>
          Available Synthetics
        </Heading>

        <Box overflowX="auto">
          <Table variant="simple">
            <Thead>
              <Tr>
                <Th>Asset</Th>
                <Th isNumeric>Price</Th>
                <Th isNumeric>24h Change</Th>
                <Th isNumeric>TVL</Th>
                <Th isNumeric>Volume (24h)</Th>
                <Th>Collateralization</Th>
                <Th></Th>
              </Tr>
            </Thead>
            <Tbody>
              {synthetics.map((synthetic) => (
                <Tr
                  key={synthetic.id}
                  _hover={{
                    bg: "gray.700",
                    cursor: "pointer",
                    transition: "all 0.2s ease",
                  }}
                  onClick={() => handleSyntheticClick(synthetic)}
                >
                  <Td>
                    <HStack>
                      <Box
                        bg={
                          synthetic.name === "sETH"
                            ? "blue.500"
                            : synthetic.name === "sBTC"
                              ? "orange.500"
                              : synthetic.name === "sGOLD"
                                ? "yellow.500"
                                : synthetic.name === "sEUR"
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
                        border="2px solid"
                        borderColor="gray.800"
                      >
                        {synthetic.name.charAt(1)}
                      </Box>
                      <VStack align="start" spacing={0}>
                        <Text fontWeight="bold">{synthetic.name}</Text>
                        <Text fontSize="xs" color={subTextColor}>
                          {synthetic.baseAsset}
                        </Text>
                      </VStack>
                    </HStack>
                  </Td>
                  <Td isNumeric fontWeight="medium">
                    {synthetic.price}
                  </Td>
                  <Td isNumeric>
                    <Text
                      fontWeight="bold"
                      color={synthetic.isUp ? "green.400" : "red.400"}
                    >
                      {synthetic.priceChange}
                    </Text>
                  </Td>
                  <Td isNumeric>{synthetic.tvl}</Td>
                  <Td isNumeric>{synthetic.volume24h}</Td>
                  <Td>{synthetic.collateralization}</Td>
                  <Td>
                    <HStack spacing={2}>
                      <Button
                        size="sm"
                        colorScheme="brand"
                        variant="solid"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleTradeClick(synthetic);
                        }}
                      >
                        Trade
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMintClick(synthetic);
                        }}
                      >
                        Mint
                      </Button>
                    </HStack>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      </Box>

      {/* User Dashboard or Connect Wallet */}
      {isConnected ? (
        <Box
          bg={cardBg}
          p={6}
          borderRadius="lg"
          boxShadow="md"
          border="1px solid"
          borderColor={borderColor}
        >
          <Tabs
            variant="soft-rounded"
            colorScheme="brand"
            index={activeTab}
            onChange={(index) => setActiveTab(index)}
          >
            <TabList mb={6}>
              <Tab>My Positions</Tab>
              <Tab>Transaction History</Tab>
            </TabList>

            <TabPanels>
              <TabPanel px={0}>
                {!isLiveData && userPositions.length > 0 && (
                  <Text fontSize="sm" color="yellow.300" mb={4}>
                    Showing demo positions - connect a wallet on a network with
                    real registered synthetic assets to see your actual
                    positions.
                  </Text>
                )}
                {userPositions.length === 0 && !isLoadingPositions ? (
                  <Text color={subTextColor}>
                    No open positions. Mint a synthetic asset above to get
                    started.
                  </Text>
                ) : (
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6}>
                    {userPositions.map((position) => (
                      <Box
                        key={position.id}
                        p={4}
                        borderRadius="md"
                        bg="gray.700"
                        border="1px solid"
                        borderColor="gray.600"
                        _hover={{
                          borderColor: "brand.500",
                          transform: "translateY(-2px)",
                          transition: "all 0.3s ease",
                        }}
                      >
                        <Flex justify="space-between" mb={3}>
                          <Heading size="md">{position.synthetic}</Heading>
                          <Badge
                            colorScheme={
                              position.isLiquidatable
                                ? "red"
                                : position.health > 90
                                  ? "green"
                                  : position.health > 70
                                    ? "yellow"
                                    : "red"
                            }
                            px={2}
                            py={1}
                          >
                            {position.isLiquidatable
                              ? "Liquidatable"
                              : `Health: ${position.health}%`}
                          </Badge>
                        </Flex>

                        <SimpleGrid columns={2} spacing={4} mb={4}>
                          <Box>
                            <Text color={subTextColor}>Amount</Text>
                            <Text fontWeight="bold">
                              {position.amountLabel}
                            </Text>
                          </Box>
                          <Box>
                            <Text color={subTextColor}>Collateral</Text>
                            <Text fontWeight="bold">
                              {position.collateralLabel}
                            </Text>
                          </Box>
                          <Box>
                            <Text color={subTextColor}>C-Ratio</Text>
                            <Text fontWeight="bold">
                              {position.cRatioLabel}
                            </Text>
                          </Box>
                        </SimpleGrid>

                        <Progress
                          value={position.health}
                          colorScheme={
                            position.isLiquidatable
                              ? "red"
                              : position.health > 90
                                ? "green"
                                : position.health > 70
                                  ? "yellow"
                                  : "red"
                          }
                          size="sm"
                          borderRadius="full"
                          mb={4}
                        />

                        <HStack spacing={2}>
                          <Button size="sm" colorScheme="brand" flex="1">
                            Manage
                          </Button>
                          <Button size="sm" variant="outline" flex="1">
                            Add Collateral
                          </Button>
                          <Button
                            size="sm"
                            colorScheme="red"
                            variant="outline"
                            flex="1"
                          >
                            Close
                          </Button>
                        </HStack>
                      </Box>
                    ))}
                  </SimpleGrid>
                )}
              </TabPanel>

              <TabPanel px={0}>
                <VStack spacing={4} align="stretch">
                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <Flex justify="space-between" align="center">
                        <HStack>
                          <Badge colorScheme="green" px={2} py={1}>
                            Mint
                          </Badge>
                          <VStack align="start" spacing={0}>
                            <Text fontWeight="bold">5.0 sETH</Text>
                            <Text fontSize="sm" color={subTextColor}>
                              Today, 10:23 AM
                            </Text>
                          </VStack>
                        </HStack>
                        <Text>$8,602.25</Text>
                      </Flex>
                    </CardBody>
                  </Card>

                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <Flex justify="space-between" align="center">
                        <HStack>
                          <Badge colorScheme="blue" px={2} py={1}>
                            Trade
                          </Badge>
                          <VStack align="start" spacing={0}>
                            <Text fontWeight="bold">0.25 sBTC → 6.2 sETH</Text>
                            <Text fontSize="sm" color={subTextColor}>
                              Yesterday, 3:45 PM
                            </Text>
                          </VStack>
                        </HStack>
                        <Text>$10,587.70</Text>
                      </Flex>
                    </CardBody>
                  </Card>

                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <Flex justify="space-between" align="center">
                        <HStack>
                          <Badge colorScheme="purple" px={2} py={1}>
                            Add Collateral
                          </Badge>
                          <VStack align="start" spacing={0}>
                            <Text fontWeight="bold">
                              +2.5 ETH to sETH position
                            </Text>
                            <Text fontSize="sm" color={subTextColor}>
                              Apr 10, 2025, 11:32 AM
                            </Text>
                          </VStack>
                        </HStack>
                        <Text>$4,301.13</Text>
                      </Flex>
                    </CardBody>
                  </Card>

                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <Flex justify="space-between" align="center">
                        <HStack>
                          <Badge colorScheme="red" px={2} py={1}>
                            Burn
                          </Badge>
                          <VStack align="start" spacing={0}>
                            <Text fontWeight="bold">1.0 sETH</Text>
                            <Text fontSize="sm" color={subTextColor}>
                              Apr 8, 2025, 9:15 AM
                            </Text>
                          </VStack>
                        </HStack>
                        <Text>$1,720.45</Text>
                      </Flex>
                    </CardBody>
                  </Card>
                </VStack>
              </TabPanel>
            </TabPanels>
          </Tabs>
        </Box>
      ) : (
        <Box
          bg={cardBg}
          p={8}
          borderRadius="lg"
          boxShadow="md"
          border="1px solid"
          borderColor={borderColor}
          textAlign="center"
        >
          <Icon as={FiDollarSign} boxSize={12} color="brand.500" mb={4} />
          <Heading size="lg" mb={4}>
            Connect Your Wallet
          </Heading>
          <Text color={subTextColor} maxW="600px" mx="auto" mb={6}>
            Connect your wallet to mint synthetic assets, manage your positions,
            and trade on the Fluxion platform.
          </Text>
          <Button
            size="lg"
            colorScheme="brand"
            bgGradient="linear(to-r, brand.500, accent.500)"
            _hover={{
              bgGradient: "linear(to-r, brand.600, accent.600)",
              transform: "translateY(-2px)",
              boxShadow: "lg",
            }}
          >
            Connect Wallet
          </Button>
        </Box>
      )}

      {/* Synthetic Detail Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="xl">
        <ModalOverlay backdropFilter="blur(4px)" />
        <ModalContent bg="gray.800" color="white">
          <ModalHeader>
            <HStack>
              <Box
                bg={
                  selectedSynthetic?.name === "sETH"
                    ? "blue.500"
                    : selectedSynthetic?.name === "sBTC"
                      ? "orange.500"
                      : selectedSynthetic?.name === "sGOLD"
                        ? "yellow.500"
                        : selectedSynthetic?.name === "sEUR"
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
                border="2px solid"
                borderColor="gray.800"
              >
                {selectedSynthetic?.name.charAt(1)}
              </Box>
              <Text>{selectedSynthetic?.name}</Text>
            </HStack>
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <Tabs variant="soft-rounded" colorScheme="brand" mb={4}>
              <TabList mb={4}>
                <Tab>Overview</Tab>
                <Tab>Stats</Tab>
                <Tab>How It Works</Tab>
              </TabList>

              <TabPanels>
                <TabPanel px={0}>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} mb={6}>
                    <Stat>
                      <StatLabel>Current Price</StatLabel>
                      <StatNumber>{selectedSynthetic?.price}</StatNumber>
                      <StatHelpText>
                        <StatArrow
                          type={
                            selectedSynthetic?.isUp ? "increase" : "decrease"
                          }
                        />
                        {selectedSynthetic?.priceChange} (24h)
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>Total Value Locked</StatLabel>
                      <StatNumber>{selectedSynthetic?.tvl}</StatNumber>
                      <StatHelpText>
                        <StatArrow type="increase" />
                        12.5% (24h)
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>24h Volume</StatLabel>
                      <StatNumber>{selectedSynthetic?.volume24h}</StatNumber>
                      <StatHelpText>
                        <StatArrow type="increase" />
                        8.3% (24h)
                      </StatHelpText>
                    </Stat>

                    <Stat>
                      <StatLabel>Collateralization Ratio</StatLabel>
                      <StatNumber>
                        {selectedSynthetic?.collateralization}
                      </StatNumber>
                      <StatHelpText>Minimum required</StatHelpText>
                    </Stat>
                  </SimpleGrid>

                  <Box mb={6}>
                    <Heading size="sm" mb={2}>
                      Description
                    </Heading>
                    <Text>{selectedSynthetic?.description}</Text>
                  </Box>

                  <Box mb={6}>
                    <Heading size="sm" mb={2}>
                      Price Performance
                    </Heading>
                    <Box h="200px">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart
                          data={[
                            { date: "Apr 5", price: 1650 },
                            { date: "Apr 6", price: 1680 },
                            { date: "Apr 7", price: 1700 },
                            { date: "Apr 8", price: 1690 },
                            { date: "Apr 9", price: 1710 },
                            { date: "Apr 10", price: 1715 },
                            { date: "Apr 11", price: 1720 },
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
                              `$${value.toFixed(2)}`,
                              "Price",
                            ]}
                          />
                          <Line
                            type="monotone"
                            dataKey="price"
                            stroke="#0080ff"
                            strokeWidth={2}
                            dot={{ r: 4 }}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    </Box>
                  </Box>
                </TabPanel>

                <TabPanel px={0}>
                  <SimpleGrid columns={{ base: 1, md: 2 }} spacing={6} mb={6}>
                    <Box>
                      <Heading size="sm" mb={4}>
                        Market Stats
                      </Heading>
                      <VStack spacing={4} align="stretch">
                        <Flex justify="space-between">
                          <Text color={subTextColor}>Market Cap</Text>
                          <Text fontWeight="bold">$124.5M</Text>
                        </Flex>
                        <Flex justify="space-between">
                          <Text color={subTextColor}>Circulating Supply</Text>
                          <Text fontWeight="bold">
                            72,365 {selectedSynthetic?.name}
                          </Text>
                        </Flex>
                        <Flex justify="space-between">
                          <Text color={subTextColor}>All-Time High</Text>
                          <Text fontWeight="bold">$1,845.20</Text>
                        </Flex>
                        <Flex justify="space-between">
                          <Text color={subTextColor}>All-Time Low</Text>
                          <Text fontWeight="bold">$890.45</Text>
                        </Flex>
                      </VStack>
                    </Box>

                    <Box>
                      <Heading size="sm" mb={4}>
                        Protocol Stats
                      </Heading>
                      <VStack spacing={4} align="stretch">
                        <Flex justify="space-between">
                          <Text color={subTextColor}>Oracle Provider</Text>
                          <Text fontWeight="bold">Chainlink</Text>
                        </Flex>
                        <Flex justify="space-between">
                          <Text color={subTextColor}>
                            Liquidation Threshold
                          </Text>
                          <Text fontWeight="bold">120%</Text>
                        </Flex>
                        <Flex justify="space-between">
                          <Text color={subTextColor}>Minting Fee</Text>
                          <Text fontWeight="bold">0.3%</Text>
                        </Flex>
                        <Flex justify="space-between">
                          <Text color={subTextColor}>Burning Fee</Text>
                          <Text fontWeight="bold">0.3%</Text>
                        </Flex>
                      </VStack>
                    </Box>
                  </SimpleGrid>

                  <Box mb={6}>
                    <Heading size="sm" mb={4}>
                      Top Holders
                    </Heading>
                    <Table variant="simple" size="sm">
                      <Thead>
                        <Tr>
                          <Th>Address</Th>
                          <Th isNumeric>Amount</Th>
                          <Th isNumeric>% of Supply</Th>
                        </Tr>
                      </Thead>
                      <Tbody>
                        <Tr>
                          <Td>0x1234...5678</Td>
                          <Td isNumeric>5,240 {selectedSynthetic?.name}</Td>
                          <Td isNumeric>7.24%</Td>
                        </Tr>
                        <Tr>
                          <Td>0x8765...4321</Td>
                          <Td isNumeric>3,850 {selectedSynthetic?.name}</Td>
                          <Td isNumeric>5.32%</Td>
                        </Tr>
                        <Tr>
                          <Td>0x5432...1234</Td>
                          <Td isNumeric>2,760 {selectedSynthetic?.name}</Td>
                          <Td isNumeric>3.81%</Td>
                        </Tr>
                        <Tr>
                          <Td>0x9876...5432</Td>
                          <Td isNumeric>2,150 {selectedSynthetic?.name}</Td>
                          <Td isNumeric>2.97%</Td>
                        </Tr>
                        <Tr>
                          <Td>0x2468...1357</Td>
                          <Td isNumeric>1,980 {selectedSynthetic?.name}</Td>
                          <Td isNumeric>2.74%</Td>
                        </Tr>
                      </Tbody>
                    </Table>
                  </Box>
                </TabPanel>

                <TabPanel px={0}>
                  <Box mb={6}>
                    <Heading size="sm" mb={4}>
                      How Synthetic Assets Work
                    </Heading>
                    <Text mb={4}>
                      Synthetic assets are tokenized derivatives that provide
                      exposure to the price movement of the underlying asset
                      without requiring you to hold the actual asset.
                    </Text>

                    <VStack spacing={4} align="stretch">
                      <Card bg="gray.700" variant="outline">
                        <CardBody>
                          <HStack align="start" spacing={4}>
                            <Box
                              bg="brand.500"
                              borderRadius="full"
                              w="30px"
                              h="30px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                              fontWeight="bold"
                              fontSize="md"
                              flexShrink={0}
                            >
                              1
                            </Box>
                            <Box>
                              <Heading size="sm" mb={2}>
                                Collateralization
                              </Heading>
                              <Text fontSize="sm">
                                To mint synthetic assets, users must provide
                                collateral in excess of the value of the
                                synthetic assets they wish to create. This
                                over-collateralization ensures the stability of
                                the system.
                              </Text>
                            </Box>
                          </HStack>
                        </CardBody>
                      </Card>

                      <Card bg="gray.700" variant="outline">
                        <CardBody>
                          <HStack align="start" spacing={4}>
                            <Box
                              bg="brand.500"
                              borderRadius="full"
                              w="30px"
                              h="30px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                              fontWeight="bold"
                              fontSize="md"
                              flexShrink={0}
                            >
                              2
                            </Box>
                            <Box>
                              <Heading size="sm" mb={2}>
                                Price Oracles
                              </Heading>
                              <Text fontSize="sm">
                                Price feeds from trusted oracles (like
                                Chainlink) provide real-time price data for the
                                underlying assets, ensuring that synthetic
                                assets accurately track their real-world
                                counterparts.
                              </Text>
                            </Box>
                          </HStack>
                        </CardBody>
                      </Card>

                      <Card bg="gray.700" variant="outline">
                        <CardBody>
                          <HStack align="start" spacing={4}>
                            <Box
                              bg="brand.500"
                              borderRadius="full"
                              w="30px"
                              h="30px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                              fontWeight="bold"
                              fontSize="md"
                              flexShrink={0}
                            >
                              3
                            </Box>
                            <Box>
                              <Heading size="sm" mb={2}>
                                Liquidation
                              </Heading>
                              <Text fontSize="sm">
                                If the value of your collateral falls below the
                                required ratio, your position may be liquidated.
                                This means your collateral will be sold to repay
                                the synthetic assets you&rsquo;ve minted.
                              </Text>
                            </Box>
                          </HStack>
                        </CardBody>
                      </Card>

                      <Card bg="gray.700" variant="outline">
                        <CardBody>
                          <HStack align="start" spacing={4}>
                            <Box
                              bg="brand.500"
                              borderRadius="full"
                              w="30px"
                              h="30px"
                              display="flex"
                              alignItems="center"
                              justifyContent="center"
                              fontWeight="bold"
                              fontSize="md"
                              flexShrink={0}
                            >
                              4
                            </Box>
                            <Box>
                              <Heading size="sm" mb={2}>
                                Trading
                              </Heading>
                              <Text fontSize="sm">
                                Once minted, synthetic assets can be freely
                                traded on decentralized exchanges or used in
                                other DeFi protocols, just like any other token.
                              </Text>
                            </Box>
                          </HStack>
                        </CardBody>
                      </Card>
                    </VStack>
                  </Box>

                  <Box
                    p={4}
                    bg="gray.700"
                    borderRadius="md"
                    borderLeft="4px solid"
                    borderLeftColor="yellow.400"
                  >
                    <Flex>
                      <Icon
                        as={FiAlertTriangle}
                        color="yellow.400"
                        boxSize={6}
                        mr={3}
                        mt={1}
                      />
                      <Box>
                        <Text fontWeight="bold">Risk Warning</Text>
                        <Text fontSize="sm">
                          Synthetic assets involve risk. Price volatility of the
                          underlying asset can lead to liquidations if
                          collateral ratios are not maintained. Always monitor
                          your positions and maintain healthy collateralization
                          ratios.
                        </Text>
                      </Box>
                    </Flex>
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
                onClick={() => handleTradeClick(selectedSynthetic)}
              >
                Trade
              </Button>
              <Button
                variant="outline"
                onClick={() => handleMintClick(selectedSynthetic)}
              >
                Mint
              </Button>
              <Button variant="outline">Add to Watchlist</Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* Mint modal */}
      <Modal isOpen={isMintOpen} onClose={onMintClose} size="md" isCentered>
        <ModalOverlay />
        <ModalContent bg="gray.800">
          <ModalHeader>Mint {mintTarget?.name}</ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4} align="stretch">
              <Text fontSize="sm" color={subTextColor}>
                Deposits collateral and mints synthetic tokens against it via
                SyntheticAssetFactory.mintSynthetic. Requires at least 150%
                collateralization.
              </Text>
              <FormControl>
                <FormLabel fontSize="sm">Collateral amount</FormLabel>
                <NumberInput
                  value={mintCollateral}
                  onChange={(v) => setMintCollateral(v)}
                  min={0}
                >
                  <NumberInputField placeholder="0.0" />
                </NumberInput>
              </FormControl>
              <FormControl>
                <FormLabel fontSize="sm">Synthetic amount to mint</FormLabel>
                <NumberInput
                  value={mintSyntheticAmount}
                  onChange={(v) => setMintSyntheticAmount(v)}
                  min={0}
                >
                  <NumberInputField placeholder="0.0" />
                </NumberInput>
              </FormControl>
            </VStack>
          </ModalBody>
          <ModalFooter>
            <Button variant="outline" mr={3} onClick={onMintClose}>
              Cancel
            </Button>
            <Button
              colorScheme="brand"
              bgGradient="linear(to-r, brand.500, accent.500)"
              isLoading={isMinting}
              loadingText="Minting..."
              onClick={submitMint}
            >
              Mint
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
};

export default Synthetics;
