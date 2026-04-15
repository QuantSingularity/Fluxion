import {
  Box,
  Button,
  Flex,
  Icon,
  Image,
  Text,
  useColorModeValue,
  VStack,
} from "@chakra-ui/react";
import {
  FiBarChart2,
  FiDollarSign,
  FiDroplet,
  FiExternalLink,
  FiGrid,
  FiHome,
  FiSettings,
} from "react-icons/fi";
import { NavLink, useLocation } from "react-router-dom";
import logo from "../../assets/images/fluxion-logo.svg";

const NavItem = ({ icon, children, to }) => {
  const location = useLocation();
  // exact match for home, prefix match for others
  const isActive =
    to === "/" ? location.pathname === "/" : location.pathname.startsWith(to);

  return (
    <Box
      as={NavLink}
      to={to}
      style={{ textDecoration: "none" }}
      _focus={{ boxShadow: "none" }}
      display="block"
    >
      <Flex
        align="center"
        p="3"
        mx="3"
        borderRadius="lg"
        role="group"
        cursor="pointer"
        bg={isActive ? "brand.500" : "transparent"}
        color={isActive ? "white" : "gray.300"}
        _hover={{
          bg: isActive ? "brand.500" : "gray.700",
          color: "white",
          transform: "translateX(2px)",
        }}
        transition="all 0.2s ease"
        fontSize="sm"
        fontWeight={isActive ? "semibold" : "normal"}
      >
        <Icon
          mr="3"
          fontSize="16"
          as={icon}
          color={isActive ? "white" : "gray.400"}
          _groupHover={{ color: "white" }}
        />
        {children}
      </Flex>
    </Box>
  );
};

const Sidebar = () => {
  const borderColor = useColorModeValue("gray.800", "gray.700");

  return (
    <Box
      bg="gray.900"
      borderRight="1px"
      borderRightColor={borderColor}
      w="full"
      h="full"
      overflowY="auto"
      py={4}
    >
      {/* Logo */}
      <Flex h="14" alignItems="center" px="6" mb={4}>
        <Image src={logo} alt="Fluxion Logo" h="8" mr={3} />
        <Text
          fontSize="lg"
          fontWeight="bold"
          color="white"
          letterSpacing="tight"
        >
          Fluxion
        </Text>
      </Flex>

      {/* Nav links */}
      <VStack spacing={1} align="stretch">
        <NavItem icon={FiHome} to="/">
          Home
        </NavItem>
        <NavItem icon={FiGrid} to="/dashboard">
          Dashboard
        </NavItem>
        <NavItem icon={FiDroplet} to="/pools">
          Liquidity Pools
        </NavItem>
        <NavItem icon={FiDollarSign} to="/synthetics">
          Synthetic Assets
        </NavItem>
        <NavItem icon={FiBarChart2} to="/analytics">
          Analytics
        </NavItem>
        <NavItem icon={FiSettings} to="/settings">
          Settings
        </NavItem>
      </VStack>

      {/* Bottom doc button */}
      <Box position="absolute" bottom={5} left={0} right={0} px={4}>
        <Button
          as="a"
          href="https://docs.fluxion.finance"
          target="_blank"
          rel="noopener noreferrer"
          leftIcon={<FiExternalLink />}
          colorScheme="brand"
          variant="outline"
          size="sm"
          width="full"
          _hover={{ bg: "brand.500", color: "white", borderColor: "brand.500" }}
        >
          Documentation
        </Button>
        <Text fontSize="xs" color="gray.500" textAlign="center" mt={3}>
          Fluxion v1.0.0
        </Text>
      </Box>
    </Box>
  );
};

export default Sidebar;
