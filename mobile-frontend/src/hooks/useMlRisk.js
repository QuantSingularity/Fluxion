import { useCallback, useEffect, useRef, useState } from "react";
import { fetchRiskOverview } from "../api/client";

const useMlRisk = () => {
  const [state, setState] = useState({
    loading: true,
    error: null,
    data: null,
  });
  const mounted = useRef(true);

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const data = await fetchRiskOverview();
      if (mounted.current) setState({ loading: false, error: null, data });
    } catch (error) {
      if (mounted.current) {
        setState({
          loading: false,
          error: error.message || "Risk models are currently unavailable",
          data: null,
        });
      }
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    load();
    return () => {
      mounted.current = false;
    };
  }, [load]);

  return { ...state, reload: load };
};

export default useMlRisk;
