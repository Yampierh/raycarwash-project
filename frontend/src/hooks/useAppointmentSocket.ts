/**
 * useAppointmentSocket — Sprint 6
 *
 * Room-based WebSocket hook for a single appointment.
 *
 * Features:
 *   - Auto-connects when appointmentId and token are available
 *   - Exponential backoff reconnection (max 30 s between attempts)
 *   - Heartbeat ping every 30 s to keep the connection alive through proxies
 *   - Dispatches onStatusChange / onLocationUpdate callbacks
 *   - sendLocationUpdate() for detailer to push GPS coordinates
 *
 * Usage (client — status only):
 *   const { status: socketStatus } = useAppointmentSocket({
 *     appointmentId,
 *     onStatusChange: (newStatus) => setAppointmentStatus(newStatus),
 *   });
 *
 * Usage (detailer — location + status):
 *   const { sendLocationUpdate } = useAppointmentSocket({
 *     appointmentId,
 *     onStatusChange: ...,
 *     onLocationUpdate: ({ lat, lng }) => ...,
 *   });
 *   // Call sendLocationUpdate(lat, lng) every 5 s when job is active
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_BASE_URL } from "../services/api";
import { useAuthStore } from "../store/authStore";

// ------------------------------------------------------------------ //

export type SocketStatus = "connecting" | "open" | "closed" | "error";

export interface LocationPayload {
  lat: number;
  lng: number;
  ts: string;
}

export interface UseAppointmentSocketOptions {
  /** UUID of the appointment room to join. Pass null/undefined to skip. */
  appointmentId: string | null | undefined;
  /** Called whenever the server broadcasts a status_change event. */
  onStatusChange?: (newStatus: string) => void;
  /** Called whenever the server broadcasts a location_update event. */
  onLocationUpdate?: (payload: LocationPayload) => void;
}

export interface UseAppointmentSocketReturn {
  /** Current WebSocket connection state. */
  socketStatus: SocketStatus;
  /** Send the detailer's current GPS coordinates to the room. */
  sendLocationUpdate: (lat: number, lng: number) => void;
}

// ------------------------------------------------------------------ //

const HEARTBEAT_INTERVAL_MS  = 30_000;
const INITIAL_BACKOFF_MS      = 1_000;
const MAX_BACKOFF_MS          = 30_000;

export function useAppointmentSocket({
  appointmentId,
  onStatusChange,
  onLocationUpdate,
}: UseAppointmentSocketOptions): UseAppointmentSocketReturn {
  const token = useAuthStore((s) => s.token);

  const [socketStatus, setSocketStatus] = useState<SocketStatus>("closed");

  const wsRef          = useRef<WebSocket | null>(null);
  const backoffRef     = useRef<number>(INITIAL_BACKOFF_MS);
  const retryTimerRef  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef     = useRef(true);

  // Keep callbacks in refs so reconnect closure always sees the latest version
  const onStatusChangeRef  = useRef(onStatusChange);
  const onLocationUpdateRef = useRef(onLocationUpdate);
  useEffect(() => { onStatusChangeRef.current  = onStatusChange; }, [onStatusChange]);
  useEffect(() => { onLocationUpdateRef.current = onLocationUpdate; }, [onLocationUpdate]);

  const cleanup = useCallback(() => {
    if (heartbeatRef.current) {
      clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    if (wsRef.current) {
      // Remove handlers before close to prevent reconnect loop on intentional close
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (!appointmentId || !token || !mountedRef.current) return;

    cleanup();
    setSocketStatus("connecting");

    const url = `${WS_BASE_URL}/ws/appointments/${appointmentId}?token=${token}`;
    const ws  = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (!mountedRef.current) { ws.close(); return; }
      backoffRef.current = INITIAL_BACKOFF_MS;
      setSocketStatus("open");

      // Heartbeat to keep the connection alive through load balancers
      heartbeatRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "ping" }));
        }
      }, HEARTBEAT_INTERVAL_MS);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as Record<string, unknown>;
        const type = msg["type"];

        if (type === "status_change" && typeof msg["status"] === "string") {
          onStatusChangeRef.current?.(msg["status"]);
        } else if (type === "location_update") {
          const lat = msg["lat"];
          const lng = msg["lng"];
          const ts  = msg["ts"];
          if (
            typeof lat === "number" &&
            typeof lng === "number" &&
            typeof ts  === "string"
          ) {
            onLocationUpdateRef.current?.({ lat, lng, ts });
          }
        }
        // "pong" messages are silently ignored
      } catch {
        // Malformed JSON — ignore
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      setSocketStatus("error");
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      if (heartbeatRef.current) {
        clearInterval(heartbeatRef.current);
        heartbeatRef.current = null;
      }
      // Auth / not-found close codes — don't reconnect
      if (event.code === 4001 || event.code === 4003 || event.code === 4004) {
        setSocketStatus("closed");
        return;
      }
      setSocketStatus("closed");
      // Exponential backoff reconnect
      const delay = backoffRef.current;
      backoffRef.current = Math.min(backoffRef.current * 2, MAX_BACKOFF_MS);
      retryTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connect();
      }, delay);
    };
  }, [appointmentId, token, cleanup]);

  // Connect / disconnect when appointmentId or token changes
  useEffect(() => {
    mountedRef.current = true;
    if (appointmentId && token) {
      connect();
    }
    return () => {
      mountedRef.current = false;
      cleanup();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appointmentId, token]);

  const sendLocationUpdate = useCallback(
    (lat: number, lng: number) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "location_update", lat, lng }));
      }
    },
    [],
  );

  return { socketStatus, sendLocationUpdate };
}
