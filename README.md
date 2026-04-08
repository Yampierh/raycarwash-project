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
- **Backend**: Python 3.11+, PostgreSQL

## Quick Start

### 1. Install all dependencies

```bash
npm run install
```

This will:
- Install Node.js dependencies (concurrently)
- Create Python virtual environment
- Install Python dependencies
- Create `.env` files from examples

### 2. Configure environment variables

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

> **Tip**: For mobile testing, use your computer's IP instead of localhost (e.g., `http://192.168.0.10:8000`)

### 3. Start both projects

```bash
npm start
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
| `npm start` | Start both backend and frontend |
| `npm run install` | Install all dependencies |
| `npm run backend` | Start only backend |
| `npm run frontend` | Start only frontend |

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
- Axios
- AsyncStorage

### Backend
- FastAPI
- SQLAlchemy (async)
- PostgreSQL (asyncpg)
- Pydantic

## License

Private - All rights reserved
