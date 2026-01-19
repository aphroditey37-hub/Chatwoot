# 🚀 Gaming Platform - Production Deployment Guide

## Quick Start (Local Development)

```bash
# 1. Clone repository
git clone <repository-url>
cd gaming-platform

# 2. Copy environment file
cp .env.example .env

# 3. Edit .env and fill in your values
nano .env

# 4. Start services with Docker Compose
docker-compose up -d

# 5. Run database migrations
docker-compose exec backend alembic upgrade head

# 6. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8001
# API Docs: http://localhost:8001/docs
```

## Architecture Overview

```
┌─────────────┐      ┌──────────────┐      ┌───────────────┐
│   Nginx     │─────▶│   Frontend   │      │   Telegram    │
│ (Load Bal.) │      │   (React)    │      │     Bot       │
└─────────────┘      └──────────────┘      └───────┬───────┘
       │                     │                      │
       │                     ▼                      │
       │             ┌──────────────┐               │
       └────────────▶│   Backend    │◀──────────────┘
                     │  (FastAPI)   │
                     └──────┬───────┘
                            │
                     ┌──────▼───────┐
                     │  PostgreSQL  │
                     │   Database   │
                     └──────────────┘
```

## Production Deployment

### Option 1: Docker Compose (Single Server)

**Best for**: Small to medium deployments, staging environments

```bash
# 1. Set up production environment
export ENVIRONMENT=production
cp .env.example .env.production
# Edit .env.production with production values

# 2. Build production images
docker-compose -f docker-compose.prod.yml build

# 3. Deploy
docker-compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker-compose exec backend alembic upgrade head

# 5. Verify health
curl http://your-domain.com/api/health
```

### Option 2: Kubernetes (Scalable)

**Best for**: Large deployments, high availability

```bash
# 1. Create namespace
kubectl create namespace gaming-platform

# 2. Create secrets
kubectl create secret generic app-secrets \
  --from-env-file=.env.production \
  -n gaming-platform

# 3. Deploy database
kubectl apply -f k8s/postgres.yaml -n gaming-platform

# 4. Deploy backend
kubectl apply -f k8s/backend.yaml -n gaming-platform

# 5. Deploy frontend
kubectl apply -f k8s/frontend.yaml -n gaming-platform

# 6. Verify deployment
kubectl get pods -n gaming-platform
```

### Option 3: AWS ECS/Fargate

**Best for**: AWS-native deployments, serverless

```bash
# 1. Build and push images to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker tag gaming-platform-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/gaming-platform-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/gaming-platform-backend:latest

# 2. Deploy with terraform
cd terraform/aws
terraform init
terraform plan -var-file=production.tfvars
terraform apply -var-file=production.tfvars
```

## Environment Variables

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `JWT_SECRET_KEY` | Secret key for JWT tokens (min 32 chars) | `your-super-secret-key-here` |
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token | `123456:ABC-DEF...` |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for notifications | `1234567890` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GAMES_API_TOKEN` | Games API authentication token | `DEMO_TOKEN` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `*` |
| `ENVIRONMENT` | Environment name | `development` |
| `DEBUG` | Enable debug mode | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Database Migrations

### Create New Migration

```bash
# Auto-generate migration from model changes
docker-compose exec backend alembic revision --autogenerate -m "Description of changes"

# Manual migration
docker-compose exec backend alembic revision -m "Description of changes"
```

### Apply Migrations

```bash
# Upgrade to latest
docker-compose exec backend alembic upgrade head

# Upgrade one version
docker-compose exec backend alembic upgrade +1

# Downgrade one version
docker-compose exec backend alembic downgrade -1

# Check current version
docker-compose exec backend alembic current
```

## Monitoring & Observability

### Health Checks

```bash
# Application health
curl http://localhost:8001/api/health

# Database health
curl http://localhost:8001/api/health/db

# Ready check
curl http://localhost:8001/api/health/ready
```

### Logs

```bash
# View backend logs
docker-compose logs -f backend

# View frontend logs
docker-compose logs -f frontend

# View database logs
docker-compose logs -f postgres

# All logs
docker-compose logs -f
```

### Metrics

Application exposes metrics at `/metrics` endpoint (Prometheus format):

- Request count
- Response times
- Error rates
- Active connections
- Database query performance

## Security

### SSL/TLS Configuration

Use Let's Encrypt with Certbot:

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Secrets Management

**Never commit secrets to git!**

Use environment variables or secrets managers:
- AWS Secrets Manager
- HashiCorp Vault
- Google Secret Manager
- Azure Key Vault

### Security Headers

Configured in `nginx.conf`:
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block
- Content-Security-Policy (configure per needs)

## Backup & Recovery

### Database Backup

```bash
# Manual backup
docker-compose exec postgres pg_dump -U postgres portal_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup (add to cron)
0 2 * * * /path/to/backup-script.sh
```

### Restore from Backup

```bash
# Restore database
docker-compose exec -T postgres psql -U postgres portal_db < backup.sql
```

## Troubleshooting

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Database not ready - wait for postgres to be healthy
# 2. Missing environment variables - check .env
# 3. Port conflict - change port in docker-compose.yml
```

### Frontend Build Fails

```bash
# Check Node version (requires 18+)
node --version

# Clear cache and rebuild
rm -rf node_modules package-lock.json
yarn install
yarn build
```

### Database Connection Errors

```bash
# Verify postgres is running
docker-compose ps postgres

# Check connection from backend
docker-compose exec backend psql $DATABASE_URL -c "SELECT 1"

# Check firewall rules
telnet postgres 5432
```

## Performance Optimization

### Database

```sql
-- Create indexes
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_user_id ON orders(user_id);

-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM orders WHERE status = 'pending';
```

### Caching

Add Redis for caching:

```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

### CDN

Use CloudFront/CloudFlare for static assets:
- Cache static files (JS, CSS, images)
- Enable compression
- Use appropriate cache headers

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.yml
backend:
  deploy:
    replicas: 3
```

### Load Balancing

```nginx
# nginx.conf
upstream backend {
    server backend1:8001;
    server backend2:8001;
    server backend3:8001;
}
```

## CI/CD Integration

GitHub Actions workflow included at `.github/workflows/ci-cd.yml`

Triggers on:
- Push to `main` (deploy to production)
- Push to `develop` (deploy to staging)
- Pull requests (run tests)

## Support

For issues and questions:
1. Check logs first
2. Review this documentation
3. Check GitHub issues
4. Contact: support@yourdomain.com

## License

[Your License Here]
