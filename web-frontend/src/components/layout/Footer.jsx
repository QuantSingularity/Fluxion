import { Box, Flex, HStack, Link, Text } from "@chakra-ui/react";

const Footer = () => {
  return (
    <Box
      as="footer"
      bg="gray.900"
      borderTop="1px solid"
      borderColor="gray.800"
      py={4}
      px={6}
    >
      <Flex
        justify="space-between"
        align="center"
        direction={{ base: "column", md: "row" }}
        gap={{ base: 2, md: 0 }}
      >
        <Text fontSize="sm" color="gray.500">
          © {new Date().getFullYear()} Fluxion. All rights reserved.
        </Text>
        <HStack spacing={6}>
          <Link
            fontSize="sm"
            color="gray.500"
            _hover={{ color: "brand.400" }}
            href="#"
          >
            Terms
          </Link>
          <Link
            fontSize="sm"
            color="gray.500"
            _hover={{ color: "brand.400" }}
            href="#"
          >
            Privacy
          </Link>
          <Link
            fontSize="sm"
            color="gray.500"
            _hover={{ color: "brand.400" }}
            href="#"
          >
            Documentation
          </Link>
        </HStack>
      </Flex>
    </Box>
  );
};

export default Footer;
