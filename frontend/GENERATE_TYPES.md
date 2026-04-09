# Generate TypeScript Types from OpenAPI

This script generates TypeScript types from the backend OpenAPI schema.

## Prerequisites

```bash
# Install openapi-typescript
npm install -D openapi-typescript
```

## Usage

1. Start the backend:
```bash
cd backend
uvicorn main:app --reload --port 8000
```

2. In another terminal, generate types:
```bash
npm run generate:types
```

## Output

Types are generated in:
```
frontend/src/types/api.generated.ts
```

## Manual Types (Additional)

Some types need manual definition because they include helper methods:

```typescript
// frontend/src/types/api.extensions.ts

import type { User as GeneratedUser } from './api.generated';

export interface UserProfile extends GeneratedUser {
  isClient: boolean;
  isDetailer: boolean;
  isAdmin: boolean;
  hasRole: (role: string) => boolean;
}

export interface AppointmentWithVehicles extends GeneratedAppointment {
  totalPrice: number; // helper: price_cents / 100
  totalDuration: number;
}
```

## Regenerate When

- New endpoints are added
- Response schemas change
- New fields are added to models

## Alternative: swagger-typescript-api

If openapi-typescript doesn't work well, try:

```bash
npx swagger-typescript-api -p http://localhost:8000/openapi.json -o ./src/types --axios
```