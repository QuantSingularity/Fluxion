import {
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
  NumberDecrementStepper,
  NumberIncrementStepper,
  NumberInput,
  NumberInputField,
  NumberInputStepper,
  Select,
  SimpleGrid,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  Tooltip,
  useColorModeValue,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import { FiAlertTriangle, FiInfo, FiPlus } from "react-icons/fi";
import {
  Cell,
  Pie,
  PieChart,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";
import { useWeb3 } from "../../lib/web3-config.jsx";

const CreatePool = () => {
  const { isConnected } = useWeb3();
  const cardBg = useColorModeValue("gray.800", "gray.700");
  const borderColor = useColorModeValue("gray.700", "gray.600");
  const subTextColor = useColorModeValue("gray.400", "gray.400");
  const toast = useToast();

  // State for pool creation
  const [poolType, setPoolType] = useState("weighted");
  const [assets, setAssets] = useState([
    { token: "ETH", weight: 50, amount: 0 },
    { token: "USDC", weight: 50, amount: 0 },
  ]);
  const [swapFee, setSwapFee] = useState(0.3);
  const [showTooltip, setShowTooltip] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  // Colors for pie chart
  const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884D8"];

  // Handle weight change - redistribute remaining weight proportionally
  const handleWeightChange = (index, value) => {
    const clamped = Math.max(1, Math.min(99, value));
    const newAssets = [...assets];
    newAssets[index].weight = clamped;

    const otherIndices = newAssets.map((_, i) => i).filter((i) => i !== index);
    const totalOther = otherIndices.reduce(
      (s, i) => s + newAssets[i].weight,
      0,
    );
    const remaining = 100 - clamped;

    if (otherIndices.length > 0 && totalOther > 0) {
      // Distribute proportionally
      let assigned = 0;
      otherIndices.forEach((i, pos) => {
        if (pos === otherIndices.length - 1) {
          // Last item gets the remainder to avoid rounding drift
          newAssets[i].weight = Math.max(1, remaining - assigned);
        } else {
          const w = Math.max(
            1,
            Math.round((newAssets[i].weight / totalOther) * remaining),
          );
          newAssets[i].weight = w;
          assigned += w;
        }
      });
    } else if (otherIndices.length > 0) {
      // Edge case: spread evenly
      const each = Math.floor(remaining / otherIndices.length);
      const extra = remaining - each * otherIndices.length;
      otherIndices.forEach((i, pos) => {
        newAssets[i].weight = each + (pos === 0 ? extra : 0);
      });
    }

    setAssets(newAssets);
  };

  // Handle amount change - parse safely
  const handleAmountChange = (index, _strVal, numVal) => {
    const newAssets = [...assets];
    newAssets[index].amount = isNaN(numVal) ? 0 : numVal;
    setAssets(newAssets);
  };

  // Handle token change
  const handleTokenChange = (index, value) => {
    const newAssets = [...assets];
    newAssets[index].token = value;
    setAssets(newAssets);
  };

  // Add new asset
  const addAsset = () => {
    if (assets.length >= 8) {
      toast({
        title: "Maximum assets reached",
        description: "You can add up to 8 assets in a pool.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const newWeight = Math.floor(100 / (assets.length + 1));
    const remainingWeight = 100 - newWeight * (assets.length + 1);

    const newAssets = assets.map((asset, index) => ({
      ...asset,
      weight: newWeight + (index === 0 ? remainingWeight : 0),
    }));

    newAssets.push({
      token: getNextAvailableToken(),
      weight: newWeight,
      amount: 0,
    });

    setAssets(newAssets);
  };

  // Remove asset
  const removeAsset = (index) => {
    if (assets.length <= 2) {
      toast({
        title: "Minimum assets required",
        description: "A pool must have at least 2 assets.",
        status: "warning",
        duration: 3000,
        isClosable: true,
      });
      return;
    }

    const removedWeight = assets[index].weight;
    const newAssets = assets.filter((_, i) => i !== index);

    // Redistribute weight
    const weightPerAsset = Math.floor(removedWeight / newAssets.length);
    const remainingWeight = removedWeight - weightPerAsset * newAssets.length;

    newAssets.forEach((asset, i) => {
      asset.weight += weightPerAsset + (i === 0 ? remainingWeight : 0);
    });

    setAssets(newAssets);
  };

  // Get next available token
  const getNextAvailableToken = () => {
    const usedTokens = assets.map((a) => a.token);
    const allTokens = [
      "ETH",
      "WBTC",
      "USDC",
      "DAI",
      "LINK",
      "UNI",
      "AAVE",
      "SNX",
    ];
    return allTokens.find((token) => !usedTokens.includes(token)) || "ETH";
  };

  // Create pool
  const createPool = () => {
    toast({
      title: "Pool created successfully!",
      description: "Your liquidity pool has been created and is now active.",
      status: "success",
      duration: 5000,
      isClosable: true,
    });
  };

  // Calculate total value
  const calculateTotalValue = () => {
    const tokenPrices = {
      ETH: 1700,
      WBTC: 42000,
      USDC: 1,
      DAI: 1,
      LINK: 15,
      UNI: 8,
      AAVE: 80,
      SNX: 3,
    };

    return assets.reduce((total, asset) => {
      return total + asset.amount * tokenPrices[asset.token];
    }, 0);
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

        <Heading as="h1" size="xl" mb={4}>
          Create Liquidity Pool
        </Heading>
        <Text fontSize="lg" color={subTextColor} maxW="800px">
          Design your custom liquidity pool by selecting assets, setting
          weights, and configuring parameters.
        </Text>
      </Box>

      {/* Pool Creation Form */}
      <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
        <Box>
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
              Pool Type
            </Heading>

            <Tabs
              variant="soft-rounded"
              colorScheme="brand"
              mb={6}
              onChange={(index) =>
                setPoolType(index === 0 ? "weighted" : "stable")
              }
            >
              <TabList>
                <Tab>Weighted Pool</Tab>
                <Tab>Stable Pool</Tab>
              </TabList>
              <TabPanels>
                <TabPanel px={0} pt={4}>
                  <Text>
                    Weighted pools allow for custom weight allocations between
                    different tokens. Ideal for creating index funds or
                    expressing specific market views.
                  </Text>
                </TabPanel>
                <TabPanel px={0} pt={4}>
                  <Text>
                    Stable pools are optimized for assets that are expected to
                    trade at similar values. Perfect for stablecoins or
                    synthetic assets pegged to the same value.
                  </Text>
                </TabPanel>
              </TabPanels>
            </Tabs>

            <FormControl mb={6}>
              <FormLabel>Swap Fee</FormLabel>
              <Flex align="center">
                <Slider
                  flex="1"
                  min={0.1}
                  max={1}
                  step={0.05}
                  value={swapFee}
                  onChange={(val) => setSwapFee(val)}
                  onMouseEnter={() => setShowTooltip(true)}
                  onMouseLeave={() => setShowTooltip(false)}
                  mr={4}
                >
                  <SliderTrack bg="gray.600">
                    <SliderFilledTrack bg="brand.500" />
                  </SliderTrack>
                  <Tooltip
                    hasArrow
                    bg="brand.500"
                    color="white"
                    placement="top"
                    isOpen={showTooltip}
                    label={`${swapFee.toFixed(2)}%`}
                  >
                    <SliderThumb boxSize={6} />
                  </Tooltip>
                </Slider>
                <Text fontWeight="bold" minW="60px" textAlign="right">
                  {swapFee.toFixed(2)}%
                </Text>
              </Flex>
              <Text fontSize="xs" color={subTextColor} mt={1}>
                Fee earned by liquidity providers on every swap.
              </Text>
            </FormControl>

            <Box
              p={4}
              bg="gray.700"
              borderRadius="md"
              borderLeft="4px solid"
              borderLeftColor="brand.500"
            >
              <Flex>
                <Icon as={FiInfo} color="brand.500" boxSize={6} mr={3} mt={1} />
                <Box>
                  <Text fontWeight="bold">Pool Creation Fee</Text>
                  <Text fontSize="sm">
                    Creating a new pool requires a one-time fee of 0.01 ETH to
                    prevent spam.
                  </Text>
                </Box>
              </Flex>
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
            <Flex justify="space-between" align="center" mb={6}>
              <Heading size="md">Pool Assets</Heading>
              <Button
                leftIcon={<FiPlus />}
                size="sm"
                onClick={addAsset}
                colorScheme="brand"
              >
                Add Asset
              </Button>
            </Flex>

            <VStack spacing={6} align="stretch">
              {assets.map((asset, index) => (
                <Card key={index} bg="gray.700" variant="outline">
                  <CardBody>
                    <SimpleGrid columns={{ base: 1, md: 2 }} spacing={4} mb={4}>
                      <FormControl>
                        <FormLabel>Token</FormLabel>
                        <Select
                          value={asset.token}
                          onChange={(e) =>
                            handleTokenChange(index, e.target.value)
                          }
                        >
                          <option value="ETH">ETH</option>
                          <option value="WBTC">WBTC</option>
                          <option value="USDC">USDC</option>
                          <option value="DAI">DAI</option>
                          <option value="LINK">LINK</option>
                          <option value="UNI">UNI</option>
                          <option value="AAVE">AAVE</option>
                          <option value="SNX">SNX</option>
                        </Select>
                      </FormControl>

                      <FormControl>
                        <FormLabel>
                          Weight{" "}
                          {poolType === "weighted" ? `(${asset.weight}%)` : ""}
                        </FormLabel>
                        {poolType === "weighted" ? (
                          <Slider
                            min={1}
                            max={99}
                            value={asset.weight}
                            onChange={(val) => handleWeightChange(index, val)}
                            isDisabled={poolType !== "weighted"}
                          >
                            <SliderTrack bg="gray.600">
                              <SliderFilledTrack
                                bg={COLORS[index % COLORS.length]}
                              />
                            </SliderTrack>
                            <SliderThumb boxSize={6} />
                          </Slider>
                        ) : (
                          <Text>Equal (Stable Pool)</Text>
                        )}
                      </FormControl>
                    </SimpleGrid>

                    <FormControl mb={4}>
                      <FormLabel>Amount</FormLabel>
                      <NumberInput
                        min={0}
                        value={asset.amount}
                        onChange={(strVal, numVal) =>
                          handleAmountChange(index, strVal, numVal)
                        }
                      >
                        <NumberInputField />
                        <NumberInputStepper>
                          <NumberIncrementStepper />
                          <NumberDecrementStepper />
                        </NumberInputStepper>
                      </NumberInput>
                    </FormControl>

                    <Flex justify="flex-end">
                      <Button
                        size="sm"
                        colorScheme="red"
                        variant="ghost"
                        onClick={() => removeAsset(index)}
                        isDisabled={assets.length <= 2}
                      >
                        Remove
                      </Button>
                    </Flex>
                  </CardBody>
                </Card>
              ))}
            </VStack>
          </Box>
        </Box>

        <Box>
          <Box
            bg={cardBg}
            p={6}
            borderRadius="lg"
            boxShadow="md"
            border="1px solid"
            borderColor={borderColor}
            mb={8}
            position="sticky"
            top="80px"
          >
            <Heading size="md" mb={6}>
              Pool Preview
            </Heading>

            <Tabs
              variant="soft-rounded"
              colorScheme="brand"
              mb={6}
              index={activeTab}
              onChange={(index) => setActiveTab(index)}
            >
              <TabList>
                <Tab>Composition</Tab>
                <Tab>Details</Tab>
              </TabList>
              <TabPanels>
                <TabPanel px={0} pt={4}>
                  <Box h="300px" mb={6}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={assets}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          outerRadius={120}
                          fill="#8884d8"
                          dataKey="weight"
                          label={({ token, weight }) => `${token} ${weight}%`}
                        >
                          {assets.map((_, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={COLORS[index % COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <RechartsTooltip
                          contentStyle={{
                            backgroundColor: "rgba(23, 25, 35, 0.9)",
                            border: "1px solid #333",
                            borderRadius: "4px",
                            color: "white",
                          }}
                          formatter={(value, _name, props) => [
                            `${value}%`,
                            props.payload.token,
                          ]}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </Box>

                  <VStack spacing={4} align="stretch">
                    {assets.map((asset, index) => (
                      <Flex key={index} justify="space-between" align="center">
                        <HStack>
                          <Box
                            bg={COLORS[index % COLORS.length]}
                            borderRadius="md"
                            w="12px"
                            h="12px"
                          />
                          <Text fontWeight="bold">{asset.token}</Text>
                        </HStack>
                        <Text>{asset.weight}%</Text>
                      </Flex>
                    ))}
                  </VStack>
                </TabPanel>

                <TabPanel px={0} pt={4}>
                  <VStack spacing={4} align="stretch" mb={6}>
                    <Flex justify="space-between">
                      <Text color={subTextColor}>Pool Type</Text>
                      <Text fontWeight="bold" textTransform="capitalize">
                        {poolType}
                      </Text>
                    </Flex>

                    <Flex justify="space-between">
                      <Text color={subTextColor}>Swap Fee</Text>
                      <Text fontWeight="bold">{swapFee.toFixed(2)}%</Text>
                    </Flex>

                    <Flex justify="space-between">
                      <Text color={subTextColor}>Number of Assets</Text>
                      <Text fontWeight="bold">{assets.length}</Text>
                    </Flex>

                    <Flex justify="space-between">
                      <Text color={subTextColor}>Total Value</Text>
                      <Text fontWeight="bold">
                        ${calculateTotalValue().toLocaleString()}
                      </Text>
                    </Flex>

                    <Flex justify="space-between">
                      <Text color={subTextColor}>Estimated APY</Text>
                      <Text fontWeight="bold" color="green.400">
                        7.2% - 12.5%
                      </Text>
                    </Flex>
                  </VStack>

                  <Box
                    p={4}
                    bg="gray.700"
                    borderRadius="md"
                    borderLeft="4px solid"
                    borderLeftColor="yellow.400"
                    mb={6}
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
                        <Text fontWeight="bold">Important Note</Text>
                        <Text fontSize="sm">
                          APY is an estimate based on current market conditions
                          and may vary. Past performance is not indicative of
                          future results.
                        </Text>
                      </Box>
                    </Flex>
                  </Box>
                </TabPanel>
              </TabPanels>
            </Tabs>

            <Button
              width="full"
              size="lg"
              colorScheme="brand"
              bgGradient="linear(to-r, brand.500, accent.500)"
              _hover={{
                bgGradient: "linear(to-r, brand.600, accent.600)",
                transform: "translateY(-2px)",
                boxShadow: "lg",
              }}
              onClick={createPool}
              isDisabled={
                !isConnected || assets.some((a) => !a.amount || a.amount <= 0)
              }
            >
              Create Pool
            </Button>

            {!isConnected && (
              <Text fontSize="sm" color="red.300" textAlign="center" mt={2}>
                Please connect your wallet to create a pool
              </Text>
            )}

            {assets.some((a) => !a.amount || a.amount <= 0) && (
              <Text fontSize="sm" color="yellow.300" textAlign="center" mt={2}>
                All assets must have an amount greater than zero
              </Text>
            )}
          </Box>
        </Box>
      </SimpleGrid>
    </Box>
  );
};

export default CreatePool;
