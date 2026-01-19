# 🎮 Gaming Platform

[![CI/CD](https://github.com/yourusername/gaming-platform/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/yourusername/gaming-platform/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)

A production-ready gaming platform with wallet management, game integrations, and admin dashboard.

## ✨ Features

### User Features
- 🔐 **Secure Authentication** - JWT-based auth with role-based access control
- 💰 **Wallet Management** - Deposits, withdrawals, and transaction history
- 🎮 **Game Integration** - Load credits to games, redeem winnings
- 🎁 **Welcome Bonus** - $50 one-time credit for new users
- 🎟️ **Promo Codes** - Redeem promotional credits
- 👥 **Referral System** - Earn rewards by referring friends

### Admin Features
- 📊 **Dashboard** - Real-time metrics and analytics
- 🔍 **Order Management** - Approve/reject deposits and withdrawals
- 💳 **Balance Control** - Manual balance adjustments with audit trail
- 🎫 **Promo Code Creation** - Generate promotional codes with expiry
- 👤 **User Management** - View and manage user accounts
- 📱 **Telegram Integration** - Approve orders via Telegram bot

### Business Rules
- ✅ **$5 Load Limit** - Cannot load if game balance exceeds $5
- ✅ **3x Wagering** - Must meet 3x wagering before cashout
- ✅ **5x Maximum** - Excess over 5x loaded amount is voided

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                  │
│  - Material-UI components                          │
│  - JWT authentication                              │
│  - Real-time updates                               │
└──────────────────┬──────────────────────────────────┘
                   │ HTTPS/REST API
┌──────────────────▼──────────────────────────────────┐
│                Backend (FastAPI)                    │
│  - RESTful API                                     │
│  - JWT validation                                  │
│  - Business logic & rules                          │
│  - Telegram webhook                                │
└──────────────────┬──────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────┐
│              PostgreSQL Database                    │
│  - User accounts                                   │
│  - Transactions                                    │
│  - Game accounts                                   │
│  - Orders                                          │
└─────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- PostgreSQL 15+
- Node.js 18+
- Python 3.11+

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/gaming-platform.git
cd gaming-platform

# 2. Copy environment file
cp .env.example .env

# 3. Update .env with your values
nano .env

# 4. Start services
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend alembic upgrade head

# 6. Create admin user (optional)
docker-compose exec backend python scripts/create_admin.py
```

### Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Admin Panel**: http://localhost:3000/admin/login

### Default Credentials

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**Test Client:**
- Username: `testclient`
- Password: `test12345`

⚠️ **Change these in production!**

## 📚 Documentation

- [Deployment Guide](DEPLOYMENT.md) - Production deployment instructions
- [Deployment Checklist](DEPLOYMENT_CHECKLIST.md) - Pre-launch checklist
- [API Documentation](http://localhost:8001/docs) - Interactive API docs
- [Architecture](docs/ARCHITECTURE.md) - System design details

## 🧪 Testing

### Run All Tests

```bash
# Backend tests
cd backend
pytest --cov=. --cov-report=html

# Frontend tests
cd frontend
yarn test --coverage
```

### Run Specific Tests

```bash
# Backend unit tests
pytest tests/unit/

# Backend integration tests
pytest tests/integration/

# Frontend component tests
yarn test src/components/
```

### Test Business Rules

```bash
# Run business rule validation tests
bash tests/test_game_operations.sh
```

## 🔧 Development

### Backend Development

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn server:app --reload --host 0.0.0.0 --port 8001

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

### Frontend Development

```bash
cd frontend

# Install dependencies
yarn install

# Start development server
yarn start

# Build for production
yarn build

# Run linter
yarn lint
```

## 📦 Tech Stack

### Backend
- **Framework**: FastAPI 0.100+
- **Database**: PostgreSQL 15
- **ORM**: AsyncPG (raw SQL for performance)
- **Authentication**: JWT
- **Validation**: Pydantic
- **Testing**: pytest

### Frontend
- **Framework**: React 18
- **Styling**: Tailwind CSS
- **State Management**: React Context
- **HTTP Client**: Axios
- **Routing**: React Router v6
- **Icons**: Lucide React

### Infrastructure
- **Containerization**: Docker
- **Orchestration**: Docker Compose / Kubernetes
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana (optional)

## 🔐 Security

- ✅ JWT authentication with secure secret keys
- ✅ Password hashing with bcrypt
- ✅ Rate limiting on API endpoints
- ✅ CORS protection
- ✅ SQL injection prevention
- ✅ XSS protection
- ✅ HTTPS enforcement in production
- ✅ Security headers (CSP, HSTS, X-Frame-Options)

## 📊 Monitoring

### Health Checks

```bash
# Application health
curl http://localhost:8001/api/health

# Database health
curl http://localhost:8001/api/health/db
```

### Metrics

Metrics available at `/metrics` (Prometheus format):
- Request count & latency
- Error rates
- Active connections
- Database query performance

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Backend: Follow PEP 8, use `ruff` for linting
- Frontend: Follow Airbnb style guide, use ESLint
- Write tests for new features
- Update documentation

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- 📧 Email: support@yourdomain.com
- 💬 Discord: [Join our server](https://discord.gg/yourinvite)
- 🐛 Issues: [GitHub Issues](https://github.com/yourusername/gaming-platform/issues)

## 🙏 Acknowledgments

- FastAPI team for the amazing framework
- React team for the robust library
- All contributors and testers

---

**Made with ❤️ by Your Team**
