# RayCarwash

Mobile car detailing marketplace - Fort Wayne, IN

## Project Structure

```
raycarwash-project/
├── frontend/          # React Native (Expo) mobile app
│   ├── src/
│   │   ├── screens/   # App screens
│   │   ├── services/  # API services
│   │   ├── navigation/# Navigation config
│   │   ├── hooks/     # Custom hooks
│   │   ├── config/    # App configuration
│   │   ├── theme/     # Theme/colors
│   │   └── utils/     # Utilities
│   └── package.json
│
├── backend/           # FastAPI Python backend
│   ├── app/
│   │   ├── routers/   # API endpoints
│   │   ├── services/  # Business logic
│   │   ├── repositories/ # Data access
│   │   ├── models/    # SQLAlchemy models
│   │   ├── schemas/   # Pydantic schemas
│   │   ├── core/      # Config & utilities
│   │   └── db/        # Database & seeds
│   ├── main.py        # App entry point
│   └── requirements.txt
│
└── package.json       # Root scripts for both projects
```

## Prerequisites

- **Frontend**: Node.js 18+, npm
- **Backend**: Python 3.11+, PostgreSQL, greenlet

## Quick Start

### 1. Install npm dependencies

```bash
npm run install
```

### 2. Install Python dependencies

```bash
npm run install-deps
```

This will:
- Create Python virtual environment
- Install Python dependencies from requirements.txt

### 3. Configure environment variables

Edit the following files:

**Backend** (`backend/.env`):
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/raycarwash
SECRET_KEY=your-secret-key-here
DEBUG=true
```

**Frontend** (`frontend/.env.local`):
```env
EXPO_PUBLIC_API_URL=http://localhost:8000
```

> **Tip**: For mobile testing, use your computer's IP instead of localhost (e.g., `http://192.168.0.1:8000`)

### 3. Start both projects

```bash
npm run dev
```

This opens:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:8081 (Expo)

### 4. Open API documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Available Scripts

| Command | Description |
|---------|-------------|
| `npm run install` | Install npm dependencies (frontend + backend) |
| `npm run install-deps` | Create Python venv and install dependencies |
| `npm run dev` | Start both backend and frontend in parallel |
| `npm run dev:backend` | Start only the backend |
| `npm run dev:frontend` | Start only the frontend |

## Environment Variables

### Backend (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | JWT secret (32+ chars) | Yes |
| `DEBUG` | Enable debug mode | No |
| `STRIPE_SECRET_KEY` | Stripe API key | No |

### Frontend (.env.local)

| Variable | Description | Default |
|----------|-------------|---------|
| `EXPO_PUBLIC_API_URL` | Backend API URL | http://localhost:8000 |

## Tech Stack

### Frontend
- React Native (Expo)
- React Navigation
- Axios + WebSocket (native)
- Zustand (auth store)
- expo-secure-store

### Backend
- FastAPI (REST + WebSocket)
- SQLAlchemy (async)
- PostgreSQL (asyncpg)
- Pydantic
- Stripe SDK v11 + Stripe Identity
- webauthn (passkeys)

## License

Private - All rights reserved
