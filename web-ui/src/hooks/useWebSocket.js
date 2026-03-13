import { useEffect, useRef, useState, useCallback } from 'react';
import { WS_URL } from '../api/client';

export default function useWebSocket(jobId) {
  const [logs, setLogs] = useState([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;
    const ws = new WebSocket(`${WS_URL}/ws/logs/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (e) => {
      const entry = JSON.parse(e.data);
      setLogs((prev) => [...prev, entry]);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [jobId]);

  const clear = useCallback(() => setLogs([]), []);

  return { logs, connected, clear };
}
