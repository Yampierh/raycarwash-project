export type JwtPayload = {
  sub?: string;
  role?: string | string[];
  scope?: string;
  exp?: number;
  iat?: number;
  email?: string;
};

function decode(token: string): JwtPayload | null {
  try {
    const b64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(b64)) as JwtPayload;
  } catch {
    return null;
  }
}

export function extractRole(token: string): string | null {
  const payload = decode(token);
  if (!payload) return null;
  if (typeof payload.role === "string") return payload.role;
  if (Array.isArray(payload.role) && typeof payload.role[0] === "string") {
    return payload.role[0];
  }
  return null;
}

export function isTokenExpired(token: string): boolean {
  const payload = decode(token);
  if (!payload?.exp) return false;
  return Date.now() >= payload.exp * 1000;
}

export function getJwtPayload(token: string): JwtPayload | null {
  return decode(token);
}
