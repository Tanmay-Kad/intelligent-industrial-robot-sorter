import { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = `http://${window.location.hostname}:8000`;
const WS_URL = `ws://${window.location.hostname}:8000/ws/telemetry`;

export function useFactorySocket() {
  const [connected, setConnected] = useState(false);
  const [telemetry, setTelemetry] = useState({
    stats: {
      connected: false,
      sim_state: "STOPPED",
      factory_state: "IDLE",
      current_operation: "Connecting...",
      total_spawned: 0,
      total_sorted: 0,
      total_failed: 0,
      pending_objects: 0,
      color_counts: { red: 0, green: 0, blue: 0 },
      success_rate: 100.0,
      avg_cycle_time_s: 0.0,
      throughput_bpm: 0.0,
      uptime_seconds: 0.0,
    },
    vision: {
      has_frame: false,
      detected: false,
      color: "none",
      confidence: 0.0,
      center: null,
      bbox: null,
      contour_area: 0.0,
      image_base64: null,
    },
    recent_logs: [],
  });

  const [loadingAction, setLoadingAction] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        setErrorMsg(null);
      };

      ws.onmessage = (event) => {
        try {
          const packet = JSON.parse(event.data);
          setTelemetry((prev) => ({
            ...prev,
            stats: packet.stats || prev.stats,
            vision: packet.vision || prev.vision,
            recent_logs: packet.recent_logs || prev.recent_logs,
          }));
        } catch (e) {
          console.error("JSON parse error:", e);
        }
      };

      ws.onclose = () => {
        setConnected(false);
        // Retry connection in 1.5 seconds
        reconnectTimeoutRef.current = setTimeout(connect, 1500);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch (e) {
      setConnected(false);
      reconnectTimeoutRef.current = setTimeout(connect, 2000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (socketRef.current) socketRef.current.close();
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
    };
  }, [connect]);

  // REST API Actions
  const sendControl = async (endpoint, payload = null) => {
    setLoadingAction(endpoint);
    setErrorMsg(null);
    try {
      const opts = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      };
      if (payload) {
        opts.body = JSON.stringify(payload);
      }
      const res = await fetch(`${API_BASE}/api/control/${endpoint}`, opts);
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.message || "Command failed");
      }
      return data;
    } catch (err) {
      setErrorMsg(err.message);
      throw err;
    } finally {
      setLoadingAction(null);
    }
  };

  const startSorting = (config) => sendControl("start", config);
  const pauseSorting = () => sendControl("pause");
  const resumeSorting = () => sendControl("resume");
  const stopSorting = () => sendControl("stop");
  const resetFactory = () => sendControl("reset");
  const updateConfig = (config) => sendControl("config", config);

  return {
    connected,
    stats: telemetry.stats,
    vision: telemetry.vision,
    logs: telemetry.recent_logs,
    loadingAction,
    errorMsg,
    startSorting,
    pauseSorting,
    resumeSorting,
    stopSorting,
    resetFactory,
    updateConfig,
  };
}
