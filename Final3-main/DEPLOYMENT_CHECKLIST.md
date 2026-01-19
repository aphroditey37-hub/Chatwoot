# Production Deployment Checklist

## Pre-Deployment

### Environment Setup
- [ ] `.env` file created from `.env.example`
- [ ] All secrets rotated (JWT_SECRET_KEY, database passwords)
- [ ] Database credentials secured
- [ ] Telegram bot token configured
- [ ] Games API token obtained and configured
- [ ] CORS origins set to production domains only

### Database
- [ ] PostgreSQL instance provisioned
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] Database backups configured
- [ ] Connection pooling configured
- [ ] Read replicas set up (if needed)

### Security
- [ ] Rate limiting enabled
- [ ] HTTPS/TLS certificates configured
- [ ] Security headers verified (CSP, HSTS, X-Frame-Options)
- [ ] Secrets stored in secrets manager (AWS Secrets Manager / Vault)
- [ ] Environment variables never committed to git
- [ ] SQL injection protection verified
- [ ] XSS protection verified
- [ ] CSRF protection enabled

### Infrastructure
- [ ] Docker images built and tagged
- [ ] Container orchestration configured (K8s/ECS/Docker Swarm)
- [ ] Load balancer configured
- [ ] Auto-scaling policies set
- [ ] Health checks configured
- [ ] Resource limits set (CPU/Memory)

### Monitoring & Logging
- [ ] Application logging configured
- [ ] Log aggregation set up (ELK/CloudWatch/Datadog)
- [ ] Error tracking configured (Sentry/Rollbar)
- [ ] Performance monitoring (APM)
- [ ] Uptime monitoring (Pingdom/UptimeRobot)
- [ ] Alerts configured for critical errors
- [ ] Dashboard created for key metrics

### Testing
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] End-to-end tests passing
- [ ] Load testing completed
- [ ] Security scanning passed
- [ ] Penetration testing completed

## Deployment

### Initial Deployment
- [ ] Database migrations applied
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] Health checks passing
- [ ] Smoke tests passing

### Post-Deployment
- [ ] Monitor error rates
- [ ] Check application logs
- [ ] Verify critical user flows
- [ ] Test Telegram webhook
- [ ] Test payment flows
- [ ] Monitor database performance

### Rollback Plan
- [ ] Previous version tagged
- [ ] Rollback procedure documented
- [ ] Database rollback strategy defined
- [ ] Rollback tested in staging

## Production Hardening

### Application
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] Detailed error messages disabled in API responses
- [ ] Admin routes protected
- [ ] File upload size limits configured
- [ ] Request timeout configured
- [ ] Graceful shutdown implemented

### Network
- [ ] Firewall rules configured
- [ ] DDoS protection enabled
- [ ] WAF configured (if applicable)
- [ ] Private subnets for database
- [ ] VPC peering configured (if multi-region)

### Compliance
- [ ] GDPR compliance verified (if EU users)
- [ ] Data retention policy implemented
- [ ] Terms of service deployed
- [ ] Privacy policy deployed
- [ ] Cookie consent implemented

## Ongoing Operations

### Daily
- [ ] Check error logs
- [ ] Monitor uptime
- [ ] Review performance metrics

### Weekly
- [ ] Review security alerts
- [ ] Check database performance
- [ ] Review user feedback
- [ ] Update dependencies (security patches)

### Monthly
- [ ] Review and rotate secrets
- [ ] Security audit
- [ ] Backup restoration test
- [ ] Disaster recovery drill
- [ ] Performance optimization review

## Emergency Procedures

### Incident Response
- [ ] On-call rotation defined
- [ ] Incident response playbook created
- [ ] Communication channels established
- [ ] Status page configured
- [ ] Post-mortem template ready

### Disaster Recovery
- [ ] RTO (Recovery Time Objective) defined
- [ ] RPO (Recovery Point Objective) defined
- [ ] Backup restoration procedure tested
- [ ] Failover procedure documented
- [ ] Multi-region strategy (if applicable)
