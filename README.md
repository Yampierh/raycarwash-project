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
│   ├── scripts/       # Setup scripts
│   └── package.json
│
└── backend/           # FastAPI Python backend
    ├── app/
    │   ├── routers/   # API endpoints
    │   ├── services/  # Business logic
    │   ├── repositories/ # Data access
    │   ├── models/    # SQLAlchemy models
    │   ├── schemas/   # Pydantic schemas
    │   ├── core/      # Config & utilities
    │   └── db/        # Database & seeds
    ├── scripts/       # Setup scripts
    ├── main.py        # App entry point
    └── requirements.txt
```

## Prerequisites

- **Frontend**: Node.js 18+, npm
- **Backend**: Python 3.11+, PostgreSQL

## Quick Start

### Backend Setup

```bash
cd backend
.\scripts\setup.bat
```

Edit `.env` with your configuration:
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Generate with `openssl rand -hex 32`

Start the backend:
```bash
.\scripts\start.bat
```

API available at http://localhost:8000

### Frontend Setup

```bash
cd frontend
npm install
```

Copy `.env.example` to `.env.local` and configure:
- `EXPO_PUBLIC_API_URL`: Backend URL (use your local IP for mobile testing)

Start the frontend:
```bash
npm start
```

## Environment Variables

### Backend (.env)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | JWT secret key (32+ chars) | Required |
| `DEBUG` | Enable debug mode | true |
| `STRIPE_SECRET_KEY` | Stripe API key | sk_test_placeholder |

### Frontend (.env.local)

| Variable | Description | Default |
|----------|-------------|---------|
| `EXPO_PUBLIC_API_URL` | Backend API URL | http://192.168.0.10:8000 |

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

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

Private - All rights reserved
