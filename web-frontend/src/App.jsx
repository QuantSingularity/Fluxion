import { Box, Container, Flex, useColorModeValue } from "@chakra-ui/react";
import { Navigate, Route, Routes } from "react-router-dom";
import Footer from "./components/layout/Footer";
import Navbar from "./components/layout/Navbar";
import Sidebar from "./components/layout/Sidebar";
import Analytics from "./pages/analytics/Analytics";
import Dashboard from "./pages/dashboard/Dashboard";
import Home from "./pages/home/Home";
import CreatePool from "./pages/pools/CreatePool";
import Pools from "./pages/pools/Pools";
import Settings from "./pages/settings/Settings";
import Synthetics from "./pages/synthetics/Synthetics";

function App() {
  const bgColor = useColorModeValue("gray.950", "gray.900");
  return (
    <Box minH="100vh" bg={bgColor}>
      <Navbar />
      <Flex>
        {/* Fixed sidebar, hidden on mobile */}
        <Box
          display={{ base: "none", md: "block" }}
          w="60"
          position="fixed"
          h="calc(100vh - 60px)"
          top="60px"
          zIndex={100}
        >
          <Sidebar />
        </Box>

        {/* Main content area, offset by sidebar width */}
        <Box
          ml={{ base: 0, md: 60 }}
          w="full"
          mt="60px"
          minH="calc(100vh - 60px)"
          display="flex"
          flexDirection="column"
        >
          <Container maxW="container.xl" py={8} flex="1">
            <Routes>
              {/* Homepage is the entry point */}
              <Route path="/" element={<Home />} />
              {/* Dashboard at /dashboard */}
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/pools" element={<Pools />} />
              <Route path="/pools/create" element={<CreatePool />} />
              <Route path="/synthetics" element={<Synthetics />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/settings" element={<Settings />} />
              {/* Catch-all redirect to home */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Container>
          <Footer />
        </Box>
      </Flex>
    </Box>
  );
}

export default App;
