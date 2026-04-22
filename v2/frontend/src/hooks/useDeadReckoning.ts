import { useEffect, useRef, useState } from 'react';
import { KalmanFilter } from '../utils/kalman';

export interface GpsPosition {
  lat: number;
  lng: number;
  heading: number; // degrees clockwise from North (0–360)
  speedMps: number; // meters per second
  timestamp: number; // Date.now()
}

/**
 * Dead Reckoning hook — smooth 60fps map marker animation.
 *
 * Between GPS updates (every 5s from the server), this hook interpolates
 * the detailer's expected position based on last known speed and heading.
 * When a new GPS fix arrives, a Kalman filter blends the real measurement
 * with the predicted position to avoid sudden jumps (teleportation).
 *
 * Usage:
 *   const position = useDeadReckoning(lastKnownGps);
 *   // position.lat / position.lng update at 60fps
 */
export function useDeadReckoning(lastKnown: GpsPosition | null) {
  const [position, setPosition] = useState<{ lat: number; lng: number } | null>(
    lastKnown ? { lat: lastKnown.lat, lng: lastKnown.lng } : null
  );

  const kalmanLat = useRef<KalmanFilter | null>(null);
  const kalmanLng = useRef<KalmanFilter | null>(null);
  const lastKnownRef = useRef<GpsPosition | null>(lastKnown);

  // Initialize or update Kalman filters when a new GPS fix arrives
  useEffect(() => {
    if (!lastKnown) return;

    if (!kalmanLat.current) {
      kalmanLat.current = new KalmanFilter(lastKnown.lat);
      kalmanLng.current = new KalmanFilter(lastKnown.lng);
    } else {
      // Blend the new GPS measurement with the current estimate
      const smoothLat = kalmanLat.current.update(lastKnown.lat);
      const smoothLng = kalmanLng.current!.update(lastKnown.lng);
      setPosition({ lat: smoothLat, lng: smoothLng });
    }

    lastKnownRef.current = lastKnown;
  }, [lastKnown]);

  // Dead Reckoning loop at 60fps
  useEffect(() => {
    const frameId = { current: 0 };

    const tick = () => {
      const last = lastKnownRef.current;
      if (last && kalmanLat.current && kalmanLng.current) {
        const elapsedSec = (Date.now() - last.timestamp) / 1000;
        const distanceM = last.speedMps * elapsedSec;

        // Move along bearing (heading) by estimated distance
        const projected = moveAlongBearing(last.lat, last.lng, distanceM, last.heading);

        setPosition({ lat: projected.lat, lng: projected.lng });
      }
      frameId.current = requestAnimationFrame(tick);
    };

    frameId.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frameId.current);
  }, []);

  return position;
}

// ------------------------------------------------------------------ //
//  Geo math                                                           //
// ------------------------------------------------------------------ //

function moveAlongBearing(
  lat: number,
  lng: number,
  distanceM: number,
  headingDeg: number
): { lat: number; lng: number } {
  const R = 6_371_000; // Earth radius in meters
  const d = distanceM / R; // angular distance in radians
  const heading = (headingDeg * Math.PI) / 180;

  const lat1 = (lat * Math.PI) / 180;
  const lng1 = (lng * Math.PI) / 180;

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(d) + Math.cos(lat1) * Math.sin(d) * Math.cos(heading)
  );
  const lng2 =
    lng1 +
    Math.atan2(
      Math.sin(heading) * Math.sin(d) * Math.cos(lat1),
      Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
    );

  return {
    lat: (lat2 * 180) / Math.PI,
    lng: (lng2 * 180) / Math.PI,
  };
}
