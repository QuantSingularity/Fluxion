import {
  Avatar,
  AvatarBadge,
  Badge,
  Box,
  Button,
  Card,
  CardBody,
  Divider,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Icon,
  IconButton,
  Input,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Select,
  SimpleGrid,
  Slider,
  SliderFilledTrack,
  SliderThumb,
  SliderTrack,
  Switch,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Text,
  Tooltip,
  useColorModeValue,
  VStack,
} from "@chakra-ui/react";
import { useState } from "react";
import {
  FiAlertTriangle,
  FiBell,
  FiCheck,
  FiChevronDown,
  FiGlobe,
  FiInfo,
  FiLogOut,
  FiMoon,
  FiSettings,
  FiShield,
  FiSun,
  FiUser,
  FiX,
} from "react-icons/fi";
import { useWeb3 } from "../../lib/web3-config.jsx";

const Settings = () => {
  const { isConnected, account } = useWeb3();
  const cardBg = useColorModeValue("gray.800", "gray.700");
  const borderColor = useColorModeValue("gray.700", "gray.600");
  const subTextColor = useColorModeValue("gray.400", "gray.400");

  // State for settings
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [slippageTolerance, setSlippageTolerance] = useState(0.5);
  const [gasPreference, setGasPreference] = useState("standard");
  const [showTooltip, setShowTooltip] = useState(false);
  const [language, setLanguage] = useState("en");
  const [currency, setCurrency] = useState("usd");

  // Format account address for display
  const formatAddress = (address) => {
    if (!address) return "";
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
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
          Settings
        </Heading>
        <Text fontSize="lg" color={subTextColor} maxW="800px">
          Customize your Fluxion experience and manage your account preferences.
        </Text>
      </Box>

      {/* Settings Tabs */}
      <Tabs variant="soft-rounded" colorScheme="brand" mb={8}>
        <TabList mb={6}>
          <Tab>
            <Icon as={FiUser} mr={2} /> Account
          </Tab>
          <Tab>
            <Icon as={FiSettings} mr={2} /> Preferences
          </Tab>
          <Tab>
            <Icon as={FiShield} mr={2} /> Security
          </Tab>
          <Tab>
            <Icon as={FiGlobe} mr={2} /> Network
          </Tab>
        </TabList>

        <TabPanels>
          {/* Account Tab */}
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                boxShadow="md"
                border="1px solid"
                borderColor={borderColor}
              >
                <Heading size="md" mb={6}>
                  Profile Information
                </Heading>

                <Flex
                  direction={{ base: "column", md: "row" }}
                  mb={6}
                  align="center"
                  gap={6}
                >
                  <Avatar
                    size="xl"
                    bgGradient="linear(to-r, brand.500, accent.500)"
                    icon={<Icon as={FiUser} fontSize="3rem" />}
                  >
                    <AvatarBadge boxSize="1.25em" bg="green.500" />
                  </Avatar>

                  <VStack align="flex-start" flex="1">
                    <Text fontSize="sm" color={subTextColor}>
                      Connected Wallet
                    </Text>
                    <HStack>
                      <Text fontSize="xl" fontWeight="bold">
                        {isConnected ? formatAddress(account) : "Not Connected"}
                      </Text>
                      {isConnected && (
                        <Badge colorScheme="green">Connected</Badge>
                      )}
                    </HStack>

                    <HStack mt={2}>
                      <Button size="sm" variant="outline" colorScheme="brand">
                        Copy Address
                      </Button>
                      <Menu>
                        <MenuButton
                          as={IconButton}
                          aria-label="Options"
                          icon={<FiChevronDown />}
                          variant="outline"
                          size="sm"
                        />
                        <MenuList bg="gray.800" borderColor="gray.700">
                          <MenuItem
                            icon={<FiLogOut />}
                            bg="gray.800"
                            _hover={{ bg: "gray.700" }}
                          >
                            Disconnect
                          </MenuItem>
                        </MenuList>
                      </Menu>
                    </HStack>
                  </VStack>
                </Flex>

                <Divider mb={6} />

                <VStack spacing={4} align="stretch">
                  <FormControl>
                    <FormLabel>Display Name</FormLabel>
                    <Input placeholder="Enter a display name" />
                  </FormControl>

                  <FormControl>
                    <FormLabel>Email Address</FormLabel>
                    <Input placeholder="Enter your email (optional)" />
                    <Text fontSize="xs" color={subTextColor} mt={1}>
                      Used for notifications and alerts only. We'll never share
                      your email.
                    </Text>
                  </FormControl>
                </VStack>

                <Button
                  mt={6}
                  colorScheme="brand"
                  bgGradient="linear(to-r, brand.500, accent.500)"
                  _hover={{
                    bgGradient: "linear(to-r, brand.600, accent.600)",
                    transform: "translateY(-2px)",
                    boxShadow: "lg",
                  }}
                >
                  Save Changes
                </Button>
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
                  Account Activity
                </Heading>

                <VStack spacing={4} align="stretch" mb={6}>
                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">Wallet Connected</Text>
                          <Text fontSize="sm" color={subTextColor}>
                            Today, 10:23 AM
                          </Text>
                        </VStack>
                        <Icon as={FiCheck} color="green.400" boxSize={5} />
                      </HStack>
                    </CardBody>
                  </Card>

                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">
                            Added Liquidity to ETH-USDC
                          </Text>
                          <Text fontSize="sm" color={subTextColor}>
                            Yesterday, 3:45 PM
                          </Text>
                        </VStack>
                        <Icon as={FiCheck} color="green.400" boxSize={5} />
                      </HStack>
                    </CardBody>
                  </Card>

                  <Card bg="gray.700" variant="outline">
                    <CardBody>
                      <HStack justify="space-between">
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">Created New Pool</Text>
                          <Text fontSize="sm" color={subTextColor}>
                            Apr 10, 2025, 11:32 AM
                          </Text>
                        </VStack>
                        <Icon as={FiCheck} color="green.400" boxSize={5} />
                      </HStack>
                    </CardBody>
                  </Card>
                </VStack>

                <Button variant="outline" width="full">
                  View All Activity
                </Button>
              </Box>
            </SimpleGrid>
          </TabPanel>

          {/* Preferences Tab */}
          <TabPanel px={0}>
            <SimpleGrid columns={{ base: 1, lg: 2 }} spacing={8}>
              <Box
                bg={cardBg}
                p={6}
                borderRadius="lg"
                boxShadow="md"
                border="1px solid"
                borderColor={borderColor}
              >
                <Heading size="md" mb={6}>
                  Appearance & Localization
                </Heading>

                <VStack spacing={6} align="stretch">
                  <FormControl
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                  >
                    <FormLabel mb={0} display="flex" alignItems="center">
                      <Icon as={isDarkMode ? FiMoon : FiSun} mr={2} />
                      Dark Mode
                    </FormLabel>
                    <Switch
                      colorScheme="brand"
                      isChecked={isDarkMode}
                      onChange={() => setIsDarkMode(!isDarkMode)}
                    />
                  </FormControl>

                  <Divider />

                  <FormControl>
                    <FormLabel>Language</FormLabel>
                    <Select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      <option value="en">English</option>
                      <option value="es">Español</option>
                      <option value="fr">Français</option>
                      <option value="de">Deutsch</option>
                      <option value="zh">中文</option>
                      <option value="ja">日本語</option>
                    </Select>
                  </FormControl>

                  <FormControl>
                    <FormLabel>Currency</FormLabel>
                    <Select
                      value={currency}
                      onChange={(e) => setCurrency(e.target.value)}
                    >
                      <option value="usd">USD ($)</option>
                      <option value="eur">EUR (€)</option>
                      <option value="gbp">GBP (£)</option>
                      <option value="jpy">JPY (¥)</option>
                      <option value="cny">CNY (¥)</option>
                    </Select>
                  </FormControl>

                  <FormControl
                    display="flex"
                    alignItems="center"
                    justifyContent="space-between"
                  >
                    <FormLabel mb={0} display="flex" alignItems="center">
                      <Icon as={FiBell} mr={2} />
                      Notifications
                    </FormLabel>
                    <Switch
                      colorScheme="brand"
                      isChecked={notificationsEnabled}
                      onChange={() =>
                        setNotificationsEnabled(!notificationsEnabled)
                      }
                    />
                  </FormControl>
                </VStack>
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
                  Trading Preferences
                </Heading>

                <VStack spacing={6} align="stretch">
                  <FormControl>
                    <FormLabel>Slippage Tolerance</FormLabel>
                    <Flex align="center">
                      <Slider
                        flex="1"
                        min={0.1}
                        max={5}
                        step={0.1}
                        value={slippageTolerance}
                        onChange={(val) => setSlippageTolerance(val)}
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
                          label={`${slippageTolerance.toFixed(1)}%`}
                        >
                          <SliderThumb boxSize={6} />
                        </Tooltip>
                      </Slider>
                      <Text fontWeight="bold" minW="60px" textAlign="right">
                        {slippageTolerance.toFixed(1)}%
                      </Text>
                    </Flex>
                    <Text fontSize="xs" color={subTextColor} mt={1}>
                      Your transaction will revert if the price changes
                      unfavorably by more than this percentage.
                    </Text>
                  </FormControl>

                  <Divider />

                  <FormControl>
                    <FormLabel>Gas Price Preference</FormLabel>
                    <Select
                      value={gasPreference}
                      onChange={(e) => setGasPreference(e.target.value)}
                    >
                      <option value="standard">Standard</option>
                      <option value="fast">Fast</option>
                      <option value="instant">Instant</option>
                      <option value="custom">Custom</option>
                    </Select>
                    <Text fontSize="xs" color={subTextColor} mt={1}>
                      Higher gas prices result in faster transaction
                      confirmations but cost more.
                    </Text>
                  </FormControl>

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
                        <Text fontWeight="bold">Advanced Settings</Text>
                        <Text fontSize="sm">
                          These settings are for advanced users. Incorrect
                          values can result in failed transactions or unexpected
                          behavior.
                        </Text>
                      </Box>
                    </Flex>
                  </Box>
                </VStack>
              </Box>
            </SimpleGrid>
          </TabPanel>

          {/* Security Tab */}
          <TabPanel px={0}>
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
                Security Settings
              </Heading>

              <VStack spacing={6} align="stretch">
                <FormControl
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Box>
                    <FormLabel mb={0}>Transaction Signing</FormLabel>
                    <Text fontSize="sm" color={subTextColor}>
                      Require confirmation for all transactions
                    </Text>
                  </Box>
                  <Switch colorScheme="brand" defaultChecked />
                </FormControl>

                <Divider />

                <FormControl
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Box>
                    <FormLabel mb={0}>Contract Interaction Warning</FormLabel>
                    <Text fontSize="sm" color={subTextColor}>
                      Show warning when interacting with new contracts
                    </Text>
                  </Box>
                  <Switch colorScheme="brand" defaultChecked />
                </FormControl>

                <Divider />

                <FormControl
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Box>
                    <FormLabel mb={0}>Spending Limits</FormLabel>
                    <Text fontSize="sm" color={subTextColor}>
                      Set maximum transaction amount
                    </Text>
                  </Box>
                  <Switch colorScheme="brand" />
                </FormControl>

                <Box
                  p={4}
                  bg="gray.700"
                  borderRadius="md"
                  borderLeft="4px solid"
                  borderLeftColor="red.400"
                >
                  <Flex>
                    <Icon
                      as={FiAlertTriangle}
                      color="red.400"
                      boxSize={6}
                      mr={3}
                      mt={1}
                    />
                    <Box>
                      <Text fontWeight="bold">Security Reminder</Text>
                      <Text fontSize="sm">
                        Never share your private keys or seed phrases with
                        anyone. Fluxion will never ask for this information.
                      </Text>
                    </Box>
                  </Flex>
                </Box>
              </VStack>
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
                Connected Applications
              </Heading>

              <VStack spacing={4} align="stretch" mb={6}>
                <Card bg="gray.700" variant="outline">
                  <CardBody>
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Avatar size="sm" name="MetaMask" bg="orange.500" />
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">MetaMask</Text>
                          <Text fontSize="xs" color={subTextColor}>
                            Connected Apr 10, 2025
                          </Text>
                        </VStack>
                      </HStack>
                      <Button size="sm" colorScheme="red" variant="ghost">
                        Disconnect
                      </Button>
                    </Flex>
                  </CardBody>
                </Card>

                <Card bg="gray.700" variant="outline">
                  <CardBody>
                    <Flex justify="space-between" align="center">
                      <HStack>
                        <Avatar size="sm" name="WalletConnect" bg="blue.500" />
                        <VStack align="start" spacing={0}>
                          <Text fontWeight="bold">WalletConnect</Text>
                          <Text fontSize="xs" color={subTextColor}>
                            Connected Apr 8, 2025
                          </Text>
                        </VStack>
                      </HStack>
                      <Button size="sm" colorScheme="red" variant="ghost">
                        Disconnect
                      </Button>
                    </Flex>
                  </CardBody>
                </Card>
              </VStack>

              <Button leftIcon={<FiX />} colorScheme="red" variant="outline">
                Disconnect All Applications
              </Button>
            </Box>
          </TabPanel>

          {/* Network Tab */}
          <TabPanel px={0}>
            <Box
              bg={cardBg}
              p={6}
              borderRadius="lg"
              boxShadow="md"
              border="1px solid"
              borderColor={borderColor}
            >
              <Heading size="md" mb={6}>
                Network Settings
              </Heading>

              <VStack spacing={6} align="stretch">
                <FormControl>
                  <FormLabel>Current Network</FormLabel>
                  <Select defaultValue="ethereum">
                    <option value="ethereum">Ethereum Mainnet</option>
                    <option value="arbitrum">Arbitrum</option>
                    <option value="optimism">Optimism</option>
                    <option value="polygon">Polygon</option>
                    <option value="bsc">Binance Smart Chain</option>
                  </Select>
                </FormControl>

                <Divider />

                <FormControl>
                  <FormLabel>RPC Endpoint</FormLabel>
                  <Input placeholder="https://mainnet.infura.io/v3/your-api-key" />
                  <Text fontSize="xs" color={subTextColor} mt={1}>
                    Custom RPC endpoint for advanced users
                  </Text>
                </FormControl>

                <Divider />

                <FormControl
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Box>
                    <FormLabel mb={0}>Auto-detect Network</FormLabel>
                    <Text fontSize="sm" color={subTextColor}>
                      Automatically switch to the network requested by dApps
                    </Text>
                  </Box>
                  <Switch colorScheme="brand" defaultChecked />
                </FormControl>

                <Box
                  p={4}
                  bg="gray.700"
                  borderRadius="md"
                  borderLeft="4px solid"
                  borderLeftColor="brand.500"
                >
                  <Flex>
                    <Icon
                      as={FiInfo}
                      color="brand.500"
                      boxSize={6}
                      mr={3}
                      mt={1}
                    />
                    <Box>
                      <Text fontWeight="bold">Network Information</Text>
                      <Text fontSize="sm">
                        Ethereum Mainnet: Chain ID 1, Currency ETH
                      </Text>
                      <Text fontSize="sm">Gas Price: 25 Gwei (Standard)</Text>
                    </Box>
                  </Flex>
                </Box>
              </VStack>
            </Box>
          </TabPanel>
        </TabPanels>
      </Tabs>
    </Box>
  );
};

export default Settings;
