# Cash Flow Dashboard

A comprehensive Streamlit-based cash flow management application with clean architecture, featuring sales tracking, cost management, payment scheduling, and external integrations.

## 🏗️ Architecture

This application follows **Clean Architecture** principles with clear separation of concerns:

```
src/
├── models/          # Domain entities and business logic
├── repositories/    # Data access layer with connection pooling
├── services/        # Business services and orchestration
├── config/          # Configuration management
└── utils/           # Utility functions and helpers

components/          # 💰 Cash Flow Dashboard

A comprehensive financial management dashboard built with Streamlit for tracking business cash flow, costs, and financial analytics with enterprise-grade performance optimizations and professional deployment pipeline.

## ✨ Features

### **Core Financial Management**
- **📊 Dashboard Overview**: Real-time financial metrics, KPIs, and interactive charts
- **📈 Sales & Cash Flow Analysis**: Revenue tracking, forecasting, and trend analysis
- **💸 Cost Management**: Expense tracking, categorization, and budget monitoring
- **🧮 Scenario Planning**: Financial modeling and what-if analysis
- **🏦 Loan Management**: Payment tracking, amortization schedules, and interest calculations
- **🗓️ Payment Scheduling**: Recurring payment management and due date tracking

### **Advanced Features**
- **🔌 Integrations**: Stripe, Airtable, and external API connectivity
- **🔐 Security**: End-to-end encryption, secure authentication, and data protection
- **⚡ Performance**: Redis caching, database optimization, and async processing
- **📱 PWA Support**: Offline capabilities and mobile-responsive design
- **🔍 Analytics**: Advanced reporting, data visualization, and business intelligence

## 🌐 API Endpoints

The application provides a RESTful API for programmatic access to financial data and operations. The API is built with FastAPI and includes interactive documentation.

### Base URL
```
http://localhost:8000/api/v1
```

### Available Endpoints

#### Test Webhook Endpoints
These endpoints simulate various webhook events for testing:

1. **Simulate Stripe Payout**
   ```
   POST /zapier/test/stripe_payout
   ```
   Simulates an incoming Stripe payment with random data.

2. **Simulate Incoming Wire Transfer**
   ```
   POST /zapier/test/incoming_wire
   ```
   Simulates an incoming wire transfer with random data.

3. **Simulate Outgoing Payment**
   ```
   POST /zapier/test/outgoing_ocbc
   ```
   Simulates an outgoing payment to a random vendor.

### Interactive API Documentation
- **Swagger UI**: Visit `/docs` (e.g., http://localhost:8000/docs)
- **ReDoc**: Visit `/redoc` (e.g., http://localhost:8000/redoc)

### Running the API Server
```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
uvicorn fastapi_app:app --reload
```

## 🚀 Quick Start

### **Prerequisites**
- Python 3.11 or higher
- Git

### **Installation**

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cash-flow-app
   ```

2. **Set up environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   **⚠️ IMPORTANT**: Edit `.env` and add your actual API keys and secrets:
   - **Stripe Keys**: Get from your Stripe Dashboard
   - **Airtable Keys**: Get from your Airtable account settings
   - **Encryption Key**: Generate a secure 32-character key
   - **Database URL**: Set your database connection string

4. **Initialize the database**
   ```bash
   python -c "from src.utils.db_init import initialize_database; initialize_database()"
   ```

5. **Create admin user (Optional)**
   ```bash
   # Option 1: Use the command-line script
   python scripts/create_admin.py
   
   # Option 2: Set environment variables in .env
   ADMIN_EMAIL=admin@yourdomain.com
   ADMIN_PASSWORD=your-secure-password
   
   # Option 3: Use the setup wizard on first launch (no action needed)
   ```

6. **Run the application**
   ```bash
   streamlit run app.py
   ```

### **🔐 Security Setup**

**Generate new API keys immediately:**
- **Stripe**: Go to Stripe Dashboard → Developers → API Keys → Create new keys
- **Airtable**: Go to Airtable → Account → Generate API Key
- **Encryption Key**: Use `python -c "import secrets; print(secrets.token_urlsafe(32))"`

**Never commit sensitive data:**
- All `.env` files are gitignored
- Database files (`.db`) are excluded from version control
- Use `.env.example` as a template only

## 🚀 Technology Stack

### **Frontend & Backend**
- **Framework**: Streamlit 1.28+ with custom components
- **Language**: Python 3.11+ with type hints
- **Database**: SQLite with connection pooling and indexing
- **Caching**: Redis with memory fallback
- **Charts**: Plotly with lazy loading and optimization

### **Performance & Scalability**
- **Async Processing**: Background tasks with asyncio and ThreadPoolExecutor
- **Caching Strategy**: Multi-tier caching (Redis → Memory → Database)
- **Database Optimization**: Query optimization, indexing, and bulk operations
- **UI Optimization**: Lazy loading, pagination, and virtual scrolling

### **Security & Monitoring**
- **Authentication**: JWT-based with role-based access control
- **Encryption**: AES-256 encryption for sensitive data
- **Monitoring**: Prometheus metrics, Grafana dashboards, and alerting
- **Logging**: Structured logging with correlation IDs

## 🛠️ Installation & Setup

### **Quick Start (Docker)**
```bash
# Clone repository
git clone <repository-url>
cd cash-flow-app

# Start with Docker Compose
docker-compose up -d

# Access application
open http://localhost:8501
```

### **Local Development**
```bash
# 1. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python -c "from services.storage import init_db; init_db()"

# 4. Start application
streamlit run app.py
```

### **Production Deployment**
```bash
# Using Docker Compose (Production)
docker-compose -f docker-compose.prod.yml up -d

# Using Terraform (AWS ECS)
cd terraform
terraform init
terraform plan
terraform apply
```

## ⚙️ Configuration

### **Environment Variables**
```bash
# Security
ENCRYPTION_MASTER_KEY=your-256-bit-encryption-key
JWT_SECRET_KEY=your-jwt-secret-key

# External APIs
STRIPE_SECRET_KEY=sk_live_...
AIRTABLE_API_KEY=key...
AIRTABLE_BASE_ID=app...

# Database & Caching
DATABASE_URL=sqlite:///app/data/cashflow.db
REDIS_URL=redis://localhost:6379/0

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ADMIN_PASSWORD=secure-password
- **🔐 Authentication**: Secure user management with bcrypt
- **🌍 Multi-Currency**: USD/CRC support with FX rates
- **📊 Analytics**: Business intelligence and forecasting
- **⚡ Performance**: Caching and connection pooling
- **🎨 Modern UI**: Clean, responsive Streamlit interface

## 🔌 Integrations

### Stripe
- Payment processing
- Transaction synchronization
- Revenue tracking

### Airtable
- CRM data integration
- Lead management
- Custom field mapping

### Webhooks
- Real-time event processing
- Custom payload handling
- Integration testing tools

## 🛠️ Development

### Project Structure
```
├── src/                    # Clean architecture implementation
│   ├── models/            # Domain entities
│   ├── repositories/      # Data access layer
│   ├── services/          # Business logic
│   ├── config/            # Configuration management
│   └── utils/             # Utility functions
├── components/            # Reusable UI components
├── pages/                 # Streamlit pages
├── data/                  # Sample data files
├── tests/                 # Test files
├── .streamlit/            # Streamlit configuration
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── app.py                # Application entry point
```

### Code Quality
- Type hints throughout codebase
- Comprehensive error handling
- Input validation and sanitization
- Security best practices
- Performance optimization

### Testing
```bash
# Run tests (when implemented)
python -m pytest tests/

# Run with coverage
python -m pytest --cov=src tests/
```

## 🚀 Deployment

### Streamlit Cloud
1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Set `app.py` as entry point
4. Configure secrets in Streamlit dashboard

### Docker (Recommended)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
```

### Traditional Server
```bash
# Install dependencies
pip install -r requirements.txt

# Set production environment
export ENV=production
export SECRET_KEY=your-production-secret

# Run with gunicorn (if using custom WSGI)
# Or use systemd service for streamlit
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## 🔒 Security

- **Authentication**: Session-based with secure password hashing
- **Environment Variables**: Sensitive data stored in `.env`
- **Input Validation**: Comprehensive data sanitization
- **SQL Injection Prevention**: Parameterized queries
- **HTTPS Ready**: Production deployment support

## 📈 Performance

- **Connection Pooling**: Efficient database connections
- **Caching**: TTL-based in-memory cache
- **Lazy Loading**: On-demand data fetching
- **Query Optimization**: Indexed database queries

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the development team
- Check the documentation in `/docs`