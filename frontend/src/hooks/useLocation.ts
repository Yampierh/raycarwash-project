import * as Location from "expo-location";
import { useEffect, useState } from "react";

interface LocationData {
  city: string | null;
  region: string | null;
  zipcode: string | null;
  lat: number | null;
  lng: number | null;
  loading: boolean;
  permissionDenied: boolean;
}

export function useLocation(): LocationData {
  const [data, setData] = useState<LocationData>({
    city: null,
    region: null,
    zipcode: null,
    lat: null,
    lng: null,
    loading: true,
    permissionDenied: false,
  });

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();

        if (status !== "granted") {
          if (!cancelled) {
            setData((prev) => ({ ...prev, loading: false, permissionDenied: true }));
          }
          return;
        }

        const position = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });

        const [geocode] = await Location.reverseGeocodeAsync({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });

        if (!cancelled) {
          setData({
            city: geocode?.city ?? geocode?.subregion ?? null,
            region: geocode?.region ?? null,
            zipcode: geocode?.postalCode ?? null,
            lat: position.coords.latitude,
            lng: position.coords.longitude,
            loading: false,
            permissionDenied: false,
          });
        }
      } catch {
        if (!cancelled) {
          setData((prev) => ({ ...prev, loading: false }));
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return data;
}
