# Fluxion – DeFi Supply Chain Platform

Production-ready DeFi supply chain backend with enterprise-grade security, compliance, and blockchain integration.

## Stack

- **Backend**: FastAPI (Python 3.12) with async SQLAlchemy
- **Database**: PostgreSQL 16 with asyncpg
- **Cache / Session**: Redis 7
- **Auth**: PyJWT + bcrypt + pyotp (MFA)
- **Blockchain**: Web3.py (Ethereum, Polygon, BSC)
- **ML**: scikit-learn, pandas, numpy
- **Containerisation**: Docker + Docker Compose

---

## Quick Start (Development)

### Prerequisites

- Docker ≥ 24 and Docker Compose ≥ 2.20
- Python 3.12 (for local development without Docker)

### 1. Clone & configure

```bash
git clone https://github.com/quantsingularity/Fluxion.git
cd Fluxion/code
cp backend/.env.example backend/.env
# Edit backend/.env – at minimum change SECRET_KEY
```

### 2. Start services

```bash
docker compose up --build
```

API is available at **http://localhost:8000**  
Swagger docs at **http://localhost:8000/docs**

### 3. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

---

## Development (without Docker)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Start PostgreSQL and Redis locally, then:
uvicorn app.main:app --reload --port 8000
```

---

## Production Deployment

```bash
# Set required secrets
export POSTGRES_PASSWORD=<strong-password>
export REDIS_PASSWORD=<strong-password>

# Deployment is managed from the top-level infrastructure/ directory
cd ../infrastructure
docker compose up -d --build

# Run migrations
docker compose exec api alembic upgrade head
```

### Key Production Checklist

- [ ] Set `SECRET_KEY` to a cryptographically random 64+ character string
- [ ] Set strong `POSTGRES_PASSWORD` and `REDIS_PASSWORD`
- [ ] Set `ENVIRONMENT=production` and `DEBUG=false`
- [ ] Configure `ALLOWED_ORIGINS` to your frontend domain(s)
- [ ] Enable `FIELD_ENCRYPTION_ENABLED=true` and set `ENCRYPTION_KEY`
- [ ] Configure `SENTRY_DSN` for error tracking
- [ ] Set up TLS termination (nginx/Traefik) in front of the API

---

## API Overview

| Method | Path                            | Auth | Description                 |
| ------ | ------------------------------- | ---- | --------------------------- |
| GET    | `/health`                       | No   | Basic health check          |
| GET    | `/api/v1/health/detailed`       | No   | Detailed health + DB status |
| GET    | `/api/v1/health/ready`          | No   | Readiness probe (k8s)       |
| GET    | `/api/v1/health/live`           | No   | Liveness probe (k8s)        |
| POST   | `/api/v1/auth/register`         | No   | Register new user           |
| POST   | `/api/v1/auth/login`            | No   | Authenticate & get tokens   |
| POST   | `/api/v1/auth/refresh`          | No   | Refresh access token        |
| GET    | `/api/v1/auth/verify-email`     | No   | Verify email address        |
| POST   | `/api/v1/auth/logout`           | JWT  | Revoke tokens               |
| GET    | `/api/v1/auth/me`               | JWT  | Get current user            |
| POST   | `/api/v1/auth/change-password`  | JWT  | Change password             |
| POST   | `/api/v1/auth/enable-mfa`       | JWT  | Setup MFA (TOTP)            |
| POST   | `/api/v1/auth/verify-mfa-setup` | JWT  | Confirm MFA setup           |
| GET    | `/api/v1/users/me`              | JWT  | Full user profile           |
| PATCH  | `/api/v1/users/me`              | JWT  | Update profile              |
| GET    | `/api/v1/portfolio/`            | JWT  | List portfolios             |
| GET    | `/api/v1/transactions/`         | JWT  | List transactions           |
| POST   | `/api/v1/transactions/`         | JWT  | Create transaction          |
| GET    | `/api/v1/analytics/overview`    | JWT  | Analytics overview          |

---

## Running Tests

```bash
cd backend
pytest tests/ -v --cov=. --cov-report=term-missing
```

---

## Optional Profiles

```bash
# Start with Celery workers
docker compose --profile celery up -d

# Start with monitoring (Prometheus + Grafana)
docker compose --profile monitoring up -d

# Start everything
docker compose --profile celery --profile monitoring up -d
```

Grafana: http://localhost:3001 (admin / fluxion_grafana)  
Prometheus: http://localhost:9090  
Flower (Celery): http://localhost:5555

---

## Project Structure

```
code/
├── backend/
│   ├── api/
│   │   ├── routes/          # Route handlers (auth, users, portfolio, ...)
│   │   └── v1/router.py     # API v1 aggregated router
│   ├── app/
│   │   └── main.py          # FastAPI app factory & lifespan
│   ├── config/
│   │   ├── database.py      # Async SQLAlchemy setup
│   │   └── settings.py      # Pydantic-settings configuration
│   ├── middleware/           # Security, rate-limiting, audit, compliance
│   ├── migrations/           # Alembic migrations
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── services/             # Business logic services
│   │   ├── auth/            # JWT, MFA, session management
│   │   ├── compliance/      # KYC, AML, transaction monitoring
│   │   ├── security/        # Encryption, threat detection
│   │   └── ...
│   ├── tests/                # pytest test suite
│   ├── Dockerfile
│   └── requirements.txt
├── blockchain/               # Solidity contracts & tests
├── ml_models/                # ML models, training CLI and inference service (see ml_models/README.md)
└── README.md
```

> Deployment manifests (docker-compose, Kubernetes, Terraform, Ansible) and
> database init scripts live in the top-level `infrastructure/` directory.
