# 🚀 Deployment Guide

This guide provides comprehensive instructions for deploying the Cash Flow Dashboard application across different environments.

## 📋 Prerequisites

### **System Requirements**
- **Docker**: 20.10+ with Docker Compose
- **Python**: 3.11+ (for local development)
- **Node.js**: 16+ (for build tools)
- **Git**: Latest version

### **Cloud Requirements (AWS)**
- **AWS CLI**: Configured with appropriate permissions
- **Terraform**: 1.0+ for infrastructure provisioning
- **kubectl**: For Kubernetes deployments (optional)

## 🏠 Local Development

### **Quick Start**
```bash
# Clone and setup
git clone <repository-url>
cd cash-flow-app
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database
python -c "from services.storage import init_db; init_db()"

# Start application
streamlit run app.py
```

### **Docker Development**
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

## 🧪 Staging Environment

### **Docker Compose Staging**
```bash
# Build and deploy
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Health check
curl -f http://localhost:8501/health

# Monitor logs
docker-compose -f docker-compose.prod.yml logs -f
```

### **Environment Variables**
```bash
# Create .env file
cat > .env << EOF
ENVIRONMENT=staging
ENCRYPTION_MASTER_KEY=$(openssl rand -hex 32)
STRIPE_SECRET_KEY=sk_test_...
AIRTABLE_API_KEY=key...
REDIS_URL=redis://redis:6379/0
GRAFANA_ADMIN_PASSWORD=staging-password
EOF
```

## 🌐 Production Deployment

### **AWS ECS with Terraform**

#### **1. Infrastructure Setup**
```bash
cd terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan -var-file="production.tfvars"

# Deploy infrastructure
terraform apply -var-file="production.tfvars"
```

#### **2. Production Variables (production.tfvars)**
```hcl
project_name = "cash-flow-app"
environment = "production"
aws_region = "us-west-2"

# Container configuration
docker_image = "your-dockerhub/cash-flow-app"
image_tag = "v1.0.0"
task_cpu = "1024"
task_memory = "2048"

# Scaling configuration
desired_count = 3
min_capacity = 2
max_capacity = 10

# Secrets (use AWS Secrets Manager in production)
encryption_master_key = "your-production-encryption-key"
stripe_secret_key = "sk_live_..."
```

#### **3. Deploy Application**
```bash
# Build and push Docker image
docker build -t your-dockerhub/cash-flow-app:v1.0.0 .
docker push your-dockerhub/cash-flow-app:v1.0.0

# Update ECS service
aws ecs update-service \
  --cluster cash-flow-app-cluster \
  --service cash-flow-app-service \
  --force-new-deployment
```

### **Docker Swarm Production**
```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml cashflow

# Scale services
docker service scale cashflow_app=3

# Monitor services
docker service ls
docker service logs cashflow_app
```

## 🔐 Security Configuration

### **SSL/TLS Setup**
```bash
# Generate SSL certificates (Let's Encrypt)
certbot certonly --webroot -w /var/www/html -d yourdomain.com

# Update nginx configuration
cp ssl/yourdomain.com.crt /etc/nginx/ssl/
cp ssl/yourdomain.com.key /etc/nginx/ssl/
```

### **Secrets Management**
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name "cash-flow-app/encryption-key" \
  --secret-string "your-encryption-key"

# Docker Secrets
echo "your-secret" | docker secret create encryption_key -
```

## 📊 Monitoring Setup

### **Prometheus Configuration**
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'cash-flow-app'
    static_configs:
      - targets: ['app:8501']
    metrics_path: /metrics
```

### **Grafana Dashboards**
```bash
# Import pre-built dashboards
curl -X POST \
  http://admin:password@localhost:3000/api/dashboards/db \
  -H 'Content-Type: application/json' \
  -d @monitoring/grafana/dashboards/app-dashboard.json
```

## 🔄 CI/CD Pipeline

### **GitHub Actions Secrets**
```bash
# Required secrets in GitHub repository
DOCKER_USERNAME=your-dockerhub-username
DOCKER_PASSWORD=your-dockerhub-password
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
ENCRYPTION_MASTER_KEY=your-encryption-key
STRIPE_SECRET_KEY=your-stripe-key
```

### **Deployment Workflow**
1. **Push to main branch** triggers production deployment
2. **Push to develop branch** triggers staging deployment
3. **Pull requests** run full test suite
4. **Failed deployments** automatically rollback

## 🔧 Troubleshooting

### **Common Issues**

#### **Database Connection Issues**
```bash
# Check database file permissions
ls -la cashflow.db

# Recreate database
rm cashflow.db
python -c "from services.storage import init_db; init_db()"
```

#### **Redis Connection Issues**
```bash
# Check Redis connectivity
redis-cli ping

# Restart Redis
docker-compose restart redis
```

#### **High Memory Usage**
```bash
# Monitor memory usage
docker stats

# Optimize cache settings
export REDIS_MAXMEMORY=256mb
export REDIS_MAXMEMORY_POLICY=allkeys-lru
```

### **Performance Tuning**

#### **Database Optimization**
```sql
-- Add indexes for better query performance
CREATE INDEX idx_costs_date_category ON costs(date, category);
CREATE INDEX idx_sales_date_status ON sales_orders(date, status);

-- Vacuum database
VACUUM;
ANALYZE;
```

#### **Cache Optimization**
```python
# Adjust cache TTL based on data freshness requirements
FINANCIAL_DATA_TTL = 300  # 5 minutes
REPORTS_TTL = 1800        # 30 minutes
METRICS_TTL = 600         # 10 minutes
```

## 📈 Scaling Strategies

### **Horizontal Scaling**
```bash
# Scale ECS service
aws ecs update-service \
  --cluster cash-flow-app-cluster \
  --service cash-flow-app-service \
  --desired-count 5

# Scale Docker Swarm
docker service scale cashflow_app=5
```

### **Vertical Scaling**
```hcl
# Update Terraform configuration
task_cpu = "2048"    # 2 vCPUs
task_memory = "4096" # 4GB RAM
```

### **Database Scaling**
```bash
# Enable WAL mode for better concurrency
sqlite3 cashflow.db "PRAGMA journal_mode=WAL;"

# Consider PostgreSQL for high-scale deployments
export DATABASE_URL=postgresql://user:pass@localhost/cashflow
```

## 🔄 Backup & Recovery

### **Database Backup**
```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp cashflow.db "backups/cashflow_${DATE}.db"
aws s3 cp "backups/cashflow_${DATE}.db" s3://your-backup-bucket/
```

### **Disaster Recovery**
```bash
# Restore from backup
aws s3 cp s3://your-backup-bucket/cashflow_20240117.db ./cashflow.db

# Verify data integrity
python -c "
import sqlite3
conn = sqlite3.connect('cashflow.db')
print('Tables:', [row[0] for row in conn.execute('SELECT name FROM sqlite_master WHERE type=\"table\"')])
conn.close()
"
```

## 📋 Deployment Checklist

### **Pre-Deployment**
- [ ] All tests passing
- [ ] Security scan completed
- [ ] Performance benchmarks met
- [ ] Database migrations applied
- [ ] Secrets configured
- [ ] SSL certificates valid

### **Post-Deployment**
- [ ] Health checks passing
- [ ] Monitoring alerts configured
- [ ] Performance metrics normal
- [ ] User acceptance testing
- [ ] Backup verification
- [ ] Documentation updated

## 🆘 Support & Maintenance

### **Log Analysis**
```bash
# Application logs
docker-compose logs -f app

# System logs
journalctl -u docker -f

# Performance logs
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### **Health Monitoring**
```bash
# Application health
curl -f http://localhost:8501/health

# Database health
sqlite3 cashflow.db "PRAGMA integrity_check;"

# Redis health
redis-cli ping
```

---

**For additional support, consult the [Performance Optimization Guide](PERFORMANCE_OPTIMIZATION_GUIDE.md) and project documentation.**
