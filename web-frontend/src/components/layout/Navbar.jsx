import {
  Avatar,
  Box,
  Button,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  HStack,
  Icon,
  IconButton,
  Image,
  Menu,
  MenuButton,
  MenuDivider,
  MenuItem,
  MenuList,
  Text,
  useColorModeValue,
  useDisclosure,
  VStack,
} from "@chakra-ui/react";
import {
  FiBarChart2,
  FiBell,
  FiChevronDown,
  FiCopy,
  FiDollarSign,
  FiDroplet,
  FiGrid,
  FiHome,
  FiLogOut,
  FiMenu,
  FiSettings,
  FiUser,
} from "react-icons/fi";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import logo from "../../assets/images/fluxion-logo.svg";
import { useWeb3 } from "../../lib/web3-config.jsx";

const MobileNavItem = ({ icon, label, to, onClose }) => (
  <Box
    as={RouterLink}
    to={to}
    onClick={onClose}
    display="flex"
    alignItems="center"
    p={3}
    borderRadius="lg"
    _hover={{ bg: "gray.700", color: "white" }}
    color="gray.300"
    textDecoration="none"
    gap={3}
  >
    <Icon as={icon} boxSize={5} />
    <Text fontWeight="medium">{label}</Text>
  </Box>
);

const Navbar = () => {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { account, isConnected, connectWallet } = useWeb3();
  const navigate = useNavigate();

  const formatAddress = (address) => {
    if (!address) return "";
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  const copyAddress = () => {
    if (account) navigator.clipboard.writeText(account);
  };

  return (
    <Box>
      <Flex
        bg={useColorModeValue("gray.900", "gray.900")}
        color="white"
        minH="60px"
        py={2}
        px={4}
        borderBottom="1px solid"
        borderColor={useColorModeValue("gray.800", "gray.700")}
        align="center"
        position="fixed"
        top="0"
        width="100%"
        zIndex={1000}
        boxShadow="0 1px 20px rgba(0,0,0,0.3)"
      >
        {/* Mobile hamburger */}
        <IconButton
          display={{ base: "flex", md: "none" }}
          onClick={onOpen}
          icon={<FiMenu />}
          variant="ghost"
          aria-label="Toggle Navigation"
          mr={2}
        />

        {/* Logo */}
        <Flex flex={1} justify={{ base: "center", md: "start" }}>
          <RouterLink to="/">
            <Image src={logo} alt="Fluxion Logo" h="8" />
          </RouterLink>
        </Flex>

        {/* Right actions */}
        <HStack spacing={3}>
          <IconButton
            size="md"
            variant="ghost"
            aria-label="Notifications"
            icon={<FiBell />}
            _hover={{ bg: "gray.700" }}
          />

          {isConnected ? (
            <Menu>
              <MenuButton
                as={Button}
                variant="outline"
                borderColor="gray.700"
                _hover={{ borderColor: "brand.500" }}
                size="sm"
                cursor="pointer"
              >
                <HStack spacing={2}>
                  <Avatar
                    size="xs"
                    bgGradient="linear(to-r, brand.500, accent.500)"
                  />
                  <Text display={{ base: "none", md: "flex" }} fontSize="sm">
                    {formatAddress(account)}
                  </Text>
                  <Icon
                    as={FiChevronDown}
                    boxSize={3}
                    display={{ base: "none", md: "flex" }}
                  />
                </HStack>
              </MenuButton>
              <MenuList bg="gray.800" borderColor="gray.700">
                <MenuItem
                  icon={<FiUser />}
                  bg="gray.800"
                  _hover={{ bg: "gray.700" }}
                  onClick={() => navigate("/settings")}
                >
                  Profile
                </MenuItem>
                <MenuItem
                  icon={<FiCopy />}
                  bg="gray.800"
                  _hover={{ bg: "gray.700" }}
                  onClick={copyAddress}
                >
                  Copy Address
                </MenuItem>
                <MenuItem
                  icon={<FiSettings />}
                  bg="gray.800"
                  _hover={{ bg: "gray.700" }}
                  onClick={() => navigate("/settings")}
                >
                  Settings
                </MenuItem>
                <MenuDivider borderColor="gray.700" />
                <MenuItem
                  icon={<FiLogOut />}
                  bg="gray.800"
                  _hover={{ bg: "red.700" }}
                  color="red.300"
                >
                  Disconnect
                </MenuItem>
              </MenuList>
            </Menu>
          ) : (
            <Button
              size="sm"
              colorScheme="brand"
              bgGradient="linear(to-r, brand.500, accent.500)"
              _hover={{
                bgGradient: "linear(to-r, brand.600, accent.600)",
                transform: "translateY(-1px)",
              }}
              onClick={connectWallet}
            >
              Connect Wallet
            </Button>
          )}
        </HStack>
      </Flex>

      {/* Mobile nav drawer */}
      <Drawer isOpen={isOpen} placement="left" onClose={onClose} size="xs">
        <DrawerOverlay />
        <DrawerContent bg="gray.900" color="white">
          <DrawerCloseButton />
          <DrawerHeader borderBottomWidth="1px" borderColor="gray.700">
            <Image src={logo} alt="Fluxion" h="7" />
          </DrawerHeader>
          <DrawerBody py={4}>
            <VStack spacing={1} align="stretch">
              <MobileNavItem
                icon={FiHome}
                label="Home"
                to="/"
                onClose={onClose}
              />
              <MobileNavItem
                icon={FiGrid}
                label="Dashboard"
                to="/dashboard"
                onClose={onClose}
              />
              <MobileNavItem
                icon={FiDroplet}
                label="Liquidity Pools"
                to="/pools"
                onClose={onClose}
              />
              <MobileNavItem
                icon={FiDollarSign}
                label="Synthetic Assets"
                to="/synthetics"
                onClose={onClose}
              />
              <MobileNavItem
                icon={FiBarChart2}
                label="Analytics"
                to="/analytics"
                onClose={onClose}
              />
              <MobileNavItem
                icon={FiSettings}
                label="Settings"
                to="/settings"
                onClose={onClose}
              />
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>
    </Box>
  );
};

export default Navbar;
