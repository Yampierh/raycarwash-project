import axios from "axios";
import { useEffect, useState } from "react";

interface WeatherData {
  temperature: number | null;
  condition: string;
  icon: string;
  isGoodForDetailing: boolean;
  loading: boolean;
}

// WMO Weather Interpretation Codes → Open-Meteo standard
const WMO: Record<number, { condition: string; icon: string; good: boolean }> = {
  0:  { condition: "Clear sky",          icon: "weather-sunny",           good: true  },
  1:  { condition: "Mainly clear",       icon: "weather-partly-cloudy",   good: true  },
  2:  { condition: "Partly cloudy",      icon: "weather-partly-cloudy",   good: true  },
  3:  { condition: "Overcast",           icon: "weather-cloudy",          good: true  },
  45: { condition: "Foggy",              icon: "weather-fog",             good: false },
  48: { condition: "Icy fog",            icon: "weather-fog",             good: false },
  51: { condition: "Light drizzle",      icon: "weather-rainy",           good: false },
  53: { condition: "Drizzle",            icon: "weather-rainy",           good: false },
  55: { condition: "Heavy drizzle",      icon: "weather-pouring",         good: false },
  61: { condition: "Light rain",         icon: "weather-rainy",           good: false },
  63: { condition: "Rain",               icon: "weather-rainy",           good: false },
  65: { condition: "Heavy rain",         icon: "weather-pouring",         good: false },
  71: { condition: "Light snow",         icon: "weather-snowy",           good: false },
  73: { condition: "Snow",               icon: "weather-snowy",           good: false },
  75: { condition: "Heavy snow",         icon: "weather-snowy-heavy",     good: false },
  77: { condition: "Snow grains",        icon: "weather-snowy",           good: false },
  80: { condition: "Rain showers",       icon: "weather-rainy",           good: false },
  81: { condition: "Rain showers",       icon: "weather-pouring",         good: false },
  82: { condition: "Violent showers",    icon: "weather-pouring",         good: false },
  85: { condition: "Snow showers",       icon: "weather-snowy",           good: false },
  86: { condition: "Heavy snow showers", icon: "weather-snowy-heavy",     good: false },
  95: { condition: "Thunderstorm",       icon: "weather-lightning",       good: false },
  96: { condition: "Thunderstorm",       icon: "weather-lightning-rainy", good: false },
  99: { condition: "Thunderstorm",       icon: "weather-lightning-rainy", good: false },
};

export function useWeather(lat: number | null, lng: number | null): WeatherData {
  const [data, setData] = useState<WeatherData>({
    temperature: null,
    condition: "",
    icon: "weather-partly-cloudy",
    isGoodForDetailing: true,
    loading: true,
  });

  useEffect(() => {
    if (lat === null || lng === null) return;

    let cancelled = false;

    (async () => {
      try {
        const { data: res } = await axios.get(
          `https://api.open-meteo.com/v1/forecast` +
          `?latitude=${lat.toFixed(4)}&longitude=${lng.toFixed(4)}` +
          `&current_weather=true&temperature_unit=fahrenheit`,
          { timeout: 8000 },
        );
        if (cancelled) return;
        const cw = res?.current_weather;
        if (!cw) throw new Error("No weather data");
        const wmo = WMO[cw.weathercode] ?? WMO[0];
        setData({
          temperature: Math.round(cw.temperature),
          condition: wmo.condition,
          icon: wmo.icon,
          isGoodForDetailing: wmo.good,
          loading: false,
        });
      } catch {
        if (!cancelled) setData((p) => ({ ...p, loading: false }));
      }
    })();

    return () => { cancelled = true; };
  }, [lat, lng]);

  return data;
}
