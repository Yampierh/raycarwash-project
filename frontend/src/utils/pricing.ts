// src/utils/pricing.ts

/**
 * Derives the display price (in dollars) for a service based on a vehicle's body class.
 * Mirrors the backend SIZE_MULTIPLIERS logic.
 *
 * @param vehicle - Vehicle object containing body_class
 * @param service - Service object with price_small/medium/large/xl fields (in cents)
 * @returns Price in dollars as a float
 */
export const getServicePrice = (vehicle: any, service: any): number => {
  if (!service) return 0;
  const body = vehicle.body_class?.toLowerCase() ?? "";
  let priceCents: number;

  if (body.includes("sedan") || body.includes("coupe")) {
    priceCents = service.price_small;
  } else if (body.includes("suv") || body.includes("hatchback")) {
    priceCents = service.price_medium;
  } else if (body.includes("pickup") || body.includes("truck")) {
    priceCents = service.price_large;
  } else if (body.includes("van")) {
    priceCents = service.price_xl;
  } else {
    priceCents = service.price_medium; // Safe default
  }

  return priceCents / 100;
};
