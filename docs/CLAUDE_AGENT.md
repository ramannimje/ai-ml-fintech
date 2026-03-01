# Claude Agent Documentation: AI-ML-Fintech Platform

## Overview

This document provides a comprehensive guide for Claude agents to understand and work with the AI-ML-Fintech platform - a sophisticated financial technology system that combines machine learning, real-time data processing, and multi-currency commodity trading capabilities.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Core Components](#core-components)
3. [Data Flow](#data-flow)
4. [Machine Learning Pipeline](#machine-learning-pipeline)
5. [API Endpoints](#api-endpoints)
6. [Database Schema](#database-schema)
7. [Configuration](#configuration)
8. [Deployment](#deployment)
9. [Monitoring](#monitoring)
10. [Development Guidelines](#development-guidelines)

## Architecture Overview

The AI-ML-Fintech platform follows a microservices architecture with the following key characteristics:

- **Multi-Region Deployment**: Supports deployment across multiple AWS regions with automatic failover
- **Containerized Services**: All components run in Docker containers orchestrated by ECS
- **Event-Driven Architecture**: Uses message queues and event streaming for real-time data processing
- **ML Pipeline Integration**: Seamless integration of machine learning models with trading operations
- **Multi-Currency Support**: Real-time FX rate conversion and currency management

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Gateway   │    │   ML Services   │
│   (React/Vite)  │◄──►│   (FastAPI)     │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Database      │    │   Cache Layer   │    │   Monitoring    │
│   (PostgreSQL)  │◄──►│   (Redis)       │◄──►│   (Prometheus)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Core Components

### 1. Frontend Application (`frontend/`)

**Technology Stack:**

- React 19 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- TanStack Query for data fetching
- Recharts for data visualization

**Key Features:**

- Real-time commodity price charts
- Multi-currency display support
- Dark/light theme switching
- Responsive design for mobile and desktop

**Main Files:**

- `src/App.tsx` - Main application component
- `src/components/chart.tsx` - Price visualization component
- `src/api/client.ts` - API communication layer

### 2. Backend API (`app/`)

**Technology Stack:**

- FastAPI for REST API
- SQLAlchemy for ORM
- Alembic for database migrations
- Pydantic for data validation

**Key Features:**

- RESTful API endpoints for commodity data
- Multi-currency price conversion
- Authentication and authorization
- Comprehensive error handling

**Main Files:**

- `app/main.py` - API entry point
- `app/api/routes.py` - Route definitions
- `app/services/commodity_service.py` - Business logic
- `app/models/price_record.py` - Database models

### 3. Machine Learning Services (`ml/`)

**Technology Stack:**

- Python with scikit-learn
- MLflow for model tracking
- Pandas for data manipulation
- NumPy for numerical computations

**Key Features:**

- Time series forecasting models
- Feature engineering pipeline
- Model training and evaluation
- Real-time inference capabilities

**Main Files:**

- `ml/training/models.py` - ML model definitions
- `ml/features/engineer.py` - Feature engineering
- `ml/data/data_fetcher.py` - Data collection
- `ml/inference/artifacts.py` - Model deployment

### 4. Database Layer

**Technology:**

- PostgreSQL for primary data storage
- Redis for caching and session management
- Alembic for schema migrations

**Key Features:**

- Relational data modeling
- Automatic schema versioning
- Connection pooling and optimization
- Data integrity constraints

## Data Flow

### 1. Data Ingestion

```mermaid
graph TD
    A[External Data Sources] --> B[Data Fetcher]
    B --> C[Data Validation]
    C --> D[Feature Engineering]
    D --> E[Database Storage]
    E --> F[Cache Layer]
```

### 2. API Request Flow

```mermaid
graph TD
    A[Frontend Request] --> B[API Gateway]
    B --> C[Authentication]
    C --> D[Business Logic]
    D --> E[Database Query]
    E --> F[Response Formatting]
    F --> G[Frontend Response]
```

### 3. ML Pipeline Flow

```mermaid
graph TD
    A[Historical Data] --> B[Feature Engineering]
    B --> C[Model Training]
    C --> D[Model Evaluation]
    D --> E[Model Deployment]
    E --> F[Real-time Inference]
```

## Machine Learning Pipeline

### 1. Data Processing

**Feature Engineering:**

- Time-based features (hour, day of week, seasonality)
- Lag features for time series analysis
- Moving averages and technical indicators
- Currency conversion features

**Data Validation:**

- Outlier detection and handling
- Missing value imputation
- Data quality checks
- Schema validation

### 2. Model Training

**Available Models:**

- Linear Regression with regularization
- Random Forest for ensemble learning
- Gradient Boosting for complex patterns
- Time series specific models (ARIMA, Prophet)

**Training Process:**

1. Data splitting (train/validation/test)
2. Hyperparameter tuning with cross-validation
3. Model evaluation with multiple metrics
4. Model serialization and storage

### 3. Model Deployment

**Deployment Strategy:**

- Containerized model serving
- A/B testing capabilities
- Automatic model versioning
- Performance monitoring

## API Endpoints

### Core Endpoints

#### Commodity Data

- `GET /api/commodities` - List all commodities
- `GET /api/commodities/{symbol}/prices` - Get price history
- `GET /api/commodities/{symbol}/forecast` - Get ML predictions
- `POST /api/commodities/{symbol}/predict` - Real-time prediction

#### Currency Management

- `GET /api/currencies` - List supported currencies
- `GET /api/currencies/rates` - Get current FX rates
- `GET /api/currencies/convert` - Currency conversion

#### ML Models

- `GET /api/models` - List available models
- `POST /api/models/train` - Trigger model training
- `GET /api/models/{model_id}/metrics` - Get model performance

### Authentication

The API uses JWT-based authentication with the following endpoints:

- `POST /api/auth/login` - User authentication
- `POST /api/auth/logout` - Session termination
- `GET /api/auth/me` - Get current user info

## Database Schema

### Core Tables

#### Price Records

```sql
CREATE TABLE price_records (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) NOT NULL,
    price DECIMAL(10,2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Training Runs

```sql
CREATE TABLE training_runs (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(20) NOT NULL,
    metrics JSONB,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT
);
```

### Relationships

- Price records are linked to commodities via symbol
- Training runs track ML model performance over time
- Currency rates are cached for performance optimization

## Configuration

### Environment Variables

#### Database Configuration

```bash
DATABASE_URL=postgresql://user:password@host:port/database
REDIS_URL=redis://host:port
```

#### ML Configuration

```bash
MLFLOW_TRACKING_URI=http://mlflow-server:5000
MODEL_REGISTRY_URL=http://model-registry:8080
```

#### API Configuration

```bash
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=true
```

### Configuration Files

- `app/core/config.py` - Application configuration
- `ml/config.py` - ML pipeline configuration
- `docker-compose.yml` - Local development setup

## Deployment

### Local Development

1. **Prerequisites:**

   - Docker and Docker Compose
   - Python 3.9+
   - Node.js 18+

2. **Setup:**

   ```bash
   # Clone and setup
   git clone <repository-url>
   cd ai-ml-fintech

   # Install dependencies
   make install

   # Start services
   make up
   ```

3. **Development Commands:**
   ```bash
   make dev          # Start development servers
   make test         # Run tests
   make lint         # Code quality checks
   make migrate      # Database migrations
   ```

### Production Deployment

**Infrastructure as Code:**

- Terraform for AWS resource management
- ECS for container orchestration
- RDS for managed database
- CloudWatch for monitoring

**Deployment Pipeline:**

1. Code commit triggers CI/CD
2. Automated testing and linting
3. Docker image building and registry
4. ECS service deployment
5. Health checks and monitoring

## Monitoring

### Metrics Collection

**Application Metrics:**

- API response times and throughput
- Database connection pool usage
- Cache hit/miss ratios
- ML model prediction latency

**Business Metrics:**

- Commodity price volatility
- Trading volume and frequency
- Model prediction accuracy
- Currency conversion usage

### Alerting

**Critical Alerts:**

- API response time > 1 second
- Database connection failures
- ML model prediction failures
- High error rates in trading operations

**Warning Alerts:**

- Cache hit ratio < 80%
- Model accuracy degradation
- Unusual trading patterns
- Currency rate anomalies

## Development Guidelines

### Code Style

**Python:**

- Use Black for code formatting
- Follow PEP 8 guidelines
- Type hints for all functions
- Comprehensive docstrings

**JavaScript/TypeScript:**

- ESLint for code quality
- Prettier for formatting
- TypeScript for type safety
- Component-based architecture

### Testing Strategy

**Unit Tests:**

- All business logic functions
- Data validation and transformation
- ML model training and inference

**Integration Tests:**

- API endpoint functionality
- Database operations
- External service integrations

**End-to-End Tests:**

- Complete user workflows
- ML pipeline integration
- Multi-currency scenarios

### Security Considerations

**Data Protection:**

- Encryption at rest and in transit
- Secure API authentication
- Input validation and sanitization
- Rate limiting and DDoS protection

**Compliance:**

- GDPR compliance for user data
- Financial data protection standards
- Audit logging for all operations
- Secure deployment practices

## Troubleshooting

### Common Issues

**Database Connection Problems:**

- Check connection string format
- Verify database service availability
- Review connection pool settings

**ML Model Performance:**

- Monitor training data quality
- Check feature engineering pipeline
- Validate model deployment configuration

**API Performance:**

- Review query optimization
- Check cache configuration
- Monitor resource utilization

### Debug Commands

```bash
# Check service health
make health

# View logs
docker-compose logs -f

# Database migration status
alembic current

# ML model status
mlflow models list
```

## User Guide: Functional Description

### Getting Started

#### 1. Accessing the Platform

**Web Interface:**

- Navigate to the deployed frontend URL (e.g., `https://ai-ml-fintech.example.com`)
- The application loads with a dashboard showing current commodity prices
- Users can immediately view real-time price data without authentication

**API Access:**

- API endpoints are available at `/api/` path
- Authentication required for most operations
- API documentation available at `/docs` endpoint

#### 2. Dashboard Overview

**Main Dashboard Features:**

- **Commodity Price Ticker**: Real-time scrolling display of major commodity prices
- **Interactive Charts**: Click any commodity to view detailed price history
- **Currency Selector**: Switch between supported currencies (USD, EUR, GBP, JPY)
- **Theme Toggle**: Switch between light and dark themes

**Chart Interface:**

- **Time Range Selection**: View data from 1 hour to 1 year
- **Technical Indicators**: Toggle moving averages, RSI, MACD
- **Prediction Overlay**: View ML model forecasts alongside historical data
- **Export Options**: Download chart data as CSV or PNG

#### 3. Commodity Analysis

**Price History:**

1. Click on any commodity from the main list
2. View interactive price chart with zoom and pan capabilities
3. Select time range (1H, 6H, 1D, 1W, 1M, 3M, 1Y)
4. Toggle between different chart types (line, candlestick, area)

**ML Predictions:**

1. Navigate to the "Forecast" tab for any commodity
2. View short-term (24h) and medium-term (7d) predictions
3. See confidence intervals and prediction accuracy metrics
4. Compare model predictions with actual price movements

**Multi-Currency View:**

1. Use the currency selector in the top navigation
2. All prices automatically convert to selected currency
3. View FX rate history and volatility
4. Monitor currency-specific trading volumes

#### 4. Trading Interface

**Price Alerts:**

1. Click "Set Alert" on any commodity page
2. Configure price thresholds (upper/lower bounds)
3. Select notification method (email, SMS, push)
4. Set alert frequency and duration

**Portfolio Tracking:**

1. Navigate to "Portfolio" section (requires authentication)
2. Add commodities to watchlist
3. Track performance across different time periods
4. View portfolio value in preferred currency

**Historical Analysis:**

1. Use the "Analysis" tab for detailed historical data
2. Apply custom date ranges and filters
3. Export data for external analysis
4. Generate custom reports

#### 5. Advanced Features

**Custom Indicators:**

1. Navigate to "Indicators" section
2. Select from available technical indicators
3. Customize parameters (periods, thresholds)
4. Save custom indicator configurations

**Bulk Operations:**

1. Use "Bulk Actions" for multiple commodities
2. Export price data for multiple symbols
3. Set alerts for multiple commodities simultaneously
4. Generate comparative analysis reports

**API Integration:**

1. Obtain API key from user settings
2. Use provided API endpoints for programmatic access
3. Integrate with external trading platforms
4. Set up automated data feeds

### User Workflows

#### Daily Trading Routine

**Morning Market Analysis:**

1. Check overnight price movements on dashboard
2. Review ML predictions for the day
3. Analyze technical indicators for key commodities
4. Set price alerts for expected movements

**Mid-Day Monitoring:**

1. Monitor real-time price changes
2. Check alert notifications
3. Update positions based on new information
4. Review portfolio performance

**End-of-Day Review:**

1. Analyze daily performance vs. predictions
2. Review trading volume and volatility
3. Update watchlists and alerts
4. Prepare for next trading session

#### Research and Analysis

**Commodity Research:**

1. Select commodity for detailed analysis
2. Review historical price patterns
3. Analyze correlation with other commodities
4. Study impact of external factors (news, events)

**Strategy Development:**

1. Use historical data to test trading strategies
2. Backtest against ML predictions
3. Analyze performance across different timeframes
4. Optimize strategy parameters

**Risk Management:**

1. Monitor portfolio exposure across commodities
2. Set stop-loss and take-profit levels
3. Analyze volatility and risk metrics
4. Diversify across different asset classes

### Troubleshooting Common Issues

#### Data Display Problems

**Missing Price Data:**

- Check internet connection
- Refresh the page
- Verify commodity symbol is correct
- Contact support if issue persists

**Chart Not Loading:**

- Clear browser cache
- Try different time range
- Check browser console for errors
- Use different browser if needed

**Currency Conversion Issues:**

- Verify selected currency is supported
- Check if FX rates are up to date
- Refresh currency data
- Contact support for rate issues

#### Performance Issues

**Slow Loading:**

- Reduce chart time range
- Limit number of displayed indicators
- Clear browser cache and cookies
- Check internet connection speed

**API Rate Limits:**

- Reduce API call frequency
- Implement caching for frequently accessed data
- Use bulk endpoints when possible
- Contact support for higher limits

#### Authentication Problems

**Login Issues:**

- Verify username/password
- Check if account is active
- Reset password if needed
- Contact administrator for access

**API Key Problems:**

- Regenerate API key from settings
- Verify key has proper permissions
- Check key expiration date
- Contact support for key issues

### Best Practices

#### Data Analysis

- Always cross-reference ML predictions with technical analysis
- Consider multiple timeframes for comprehensive analysis
- Use alerts to monitor key price levels
- Keep detailed trading journals

#### Risk Management

- Never invest more than you can afford to lose
- Use stop-loss orders to limit downside
- Diversify across different commodities
- Monitor position sizes relative to portfolio

#### Platform Usage

- Regularly update browser and plugins
- Use strong, unique passwords
- Enable two-factor authentication
- Keep API keys secure and confidential

## Conclusion

This AI-ML-Fintech platform represents a sophisticated integration of financial technology, machine learning, and modern software architecture. The system is designed for scalability, reliability, and maintainability while providing real-time commodity trading capabilities with multi-currency support.

For further assistance or specific implementation details, refer to the individual component documentation or consult the development team.

```

```
