import { useEffect, useRef, useState } from "react";

export interface KnownPosition {
  lat: number;
  lng: number;
  heading: number;  // degrees 0–360
  timestamp: number; // ms epoch
}

export interface EstimatedPosition {
  lat: number;
  lng: number;
}

const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;
const EARTH_RADIUS_M = 6_371_000;
const FRAME_MS = 16; // ~60 fps

function moveAlongBearing(
  lat: number,
  lng: number,
  bearingDeg: number,
  distanceM: number,
): EstimatedPosition {
  const d = distanceM / EARTH_RADIUS_M;
  const θ = bearingDeg * DEG_TO_RAD;
  const φ1 = lat * DEG_TO_RAD;
  const λ1 = lng * DEG_TO_RAD;

  const φ2 = Math.asin(
    Math.sin(φ1) * Math.cos(d) + Math.cos(φ1) * Math.sin(d) * Math.cos(θ),
  );
  const λ2 =
    λ1 +
    Math.atan2(
      Math.sin(θ) * Math.sin(d) * Math.cos(φ1),
      Math.cos(d) - Math.sin(φ1) * Math.sin(φ2),
    );

  return { lat: φ2 * RAD_TO_DEG, lng: λ2 * RAD_TO_DEG };
}

/**
 * Dead-reckoning hook.
 * Interpolates the detailer's position at 60 fps between real GPS updates,
 * eliminating the teleportation effect when a new WS location_update arrives.
 */
export function useDeadReckoning(
  lastKnown: KnownPosition | null,
  speedMps: number = 8, // ~30 km/h default
): EstimatedPosition | null {
  const [estimated, setEstimated] = useState<EstimatedPosition | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!lastKnown) {
      setEstimated(null);
      return;
    }

    // Immediately set to last known so there's no delay on first position
    setEstimated({ lat: lastKnown.lat, lng: lastKnown.lng });

    if (intervalRef.current) clearInterval(intervalRef.current);

    intervalRef.current = setInterval(() => {
      const elapsedMs = Date.now() - lastKnown.timestamp;
      const distanceM = (elapsedMs / 1000) * speedMps;
      const next = moveAlongBearing(
        lastKnown.lat,
        lastKnown.lng,
        lastKnown.heading,
        distanceM,
      );
      setEstimated(next);
    }, FRAME_MS);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [lastKnown, speedMps]);

  return estimated;
}
