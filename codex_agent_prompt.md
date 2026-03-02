# Codex Agent Implementation Prompt

## Task Overview

You are tasked with implementing critical missing functionality in an AI Commodity Predictor web application. The application currently has basic commodity tracking and prediction features, but lacks essential user personalization and alerting capabilities.

## Current Application State

The application is a full-stack web app with:

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Authentication**: Auth0 integration
- **Features**: Live commodity prices, historical data, AI predictions, basic alert system

## Missing Requirements to Implement

### 1. Region-Based Default Dashboard

**Requirement**: After login, the dashboard should automatically show commodity prices for the user's region as default.

**Current State**: Dashboard shows US region by default regardless of user location.

**Implementation Details**:

- Add user region preference to the database (extend user profile)
- Modify the DashboardPage component to detect user's region on load
- Set the region dropdown to user's preferred region by default
- Ensure all charts and data reflect the user's region automatically
- Add API endpoints to manage user region preferences

**Files to Modify**:

- `frontend/src/pages/dashboard.tsx` - Update default region logic
- `app/models/` - Add user profile model with region preference
- `app/api/routes.py` - Add endpoints for user preferences
- `frontend/src/api/client.ts` - Add client methods for user preferences

### 2. Enhanced Dashboard with Candle Charts and Trending Charts

**Requirement**: Dashboard should display candle charts and trending charts for the user's region market.

**Current State**: Dashboard only shows basic price cards and summary statistics.

**Implementation Details**:

- Add candlestick chart component to dashboard (reuse existing CommodityChart)
- Display trending commodities for the user's region
- Show price movement trends (up/down indicators)
- Add market overview section with key metrics
- Implement real-time updates for dashboard charts

**Files to Modify**:

- `frontend/src/pages/dashboard.tsx` - Add candle charts and trending sections
- `frontend/src/components/` - Create new chart components if needed
- `app/services/` - Add trending data calculation service

### 3. Predicted Prices Display on Dashboard

**Requirement**: Dashboard should show predicted prices alongside current prices.

**Current State**: Predictions are only available in the commodity detail pages.

**Implementation Details**:

- Fetch prediction data for all commodities in user's region
- Display predicted prices in dashboard price cards
- Show prediction confidence intervals
- Add prediction trend indicators (bullish/bearish)
- Implement caching for prediction data

**Files to Modify**:

- `frontend/src/pages/dashboard.tsx` - Add prediction data fetching and display
- `app/services/commodity_service.py` - Add batch prediction methods

### 4. Complete Smart Price Alerts System

**Requirement**: Implement a fully functional alert system with email notifications.

**Current State**: Basic alert creation exists but email functionality is incomplete.

**Implementation Details**:

#### Alert Types to Support:

- **Price crosses above/below**: Trigger when price exceeds threshold
- **% change in 24h**: Trigger on significant daily movements
- **Sudden spike/drop**: Detect rapid price changes

#### Alert Configuration:

- Support all commodities: Gold, Silver, Crude Oil, Natural Gas, Copper
- Multiple threshold types (absolute price, percentage change)
- User-configurable alert frequency and debounce (30-minute cooldown)
- Enable/disable individual alerts

#### Email Notifications:

- Use SendGrid or Resend.com (free tier)
- Professional email templates
- Include alert details and current market context
- Handle email delivery failures gracefully

#### Alert History:

- Comprehensive logging in user profile
- Filterable by date, commodity, alert type
- Export functionality for alert history
- Visual indicators for triggered vs. pending alerts

**Files to Modify**:

- `app/services/alert_service.py` - Complete alert evaluation logic
- `app/services/email_service.py` - Implement email templates and delivery
- `app/models/alert_history.py` - Enhance history tracking
- `frontend/src/pages/commodity.tsx` - Improve alert UI
- `frontend/src/pages/profile.tsx` - Add comprehensive alert history
- `frontend/src/types/api.ts` - Update alert schemas

### 5. User Profile Management

**Requirement**: Complete user profile functionality with region preferences and alert history.

**Current State**: Basic profile exists but lacks region management and comprehensive alert history.

**Implementation Details**:

- Region preference management
- Alert history with filtering and search
- Email notification settings
- Profile picture and basic user info
- Security settings (change password, connected accounts)

**Files to Modify**:

- `frontend/src/pages/profile.tsx` - Complete profile page
- `app/models/` - Extend user profile model
- `app/api/routes.py` - Add profile management endpoints

## Technical Requirements

### Database Schema Updates

- Add user profile table with region preferences
- Enhance alert history with more detailed logging
- Add email notification tracking

### API Endpoints to Add

- `GET/POST /user/profile` - User profile management
- `GET /user/region` - Get user's preferred region
- `POST /user/region` - Set user's preferred region
- `GET /market/trending/{region}` - Get trending commodities
- `GET /predictions/batch/{region}` - Get predictions for all commodities

### Frontend Components to Create/Modify

- Enhanced dashboard with charts and trends
- User profile management interface
- Alert configuration wizard
- Email notification preferences

### Email Service Implementation

- Professional email templates
- Template engine integration
- Email delivery tracking
- Bounce handling and retry logic

## Implementation Priority

1. **High Priority**: Region-based dashboard defaults and user profile
2. **High Priority**: Complete alert system with email notifications
3. **Medium Priority**: Dashboard candle charts and trending data
4. **Medium Priority**: Predicted prices on dashboard
5. **Low Priority**: Advanced profile features and export functionality

## Testing Requirements

- Unit tests for all new backend services
- Integration tests for alert system
- Frontend component tests for new UI elements
- End-to-end tests for complete user workflows
- Email delivery testing (use test mode)

## Configuration

- Use environment variables for email service credentials
- Implement proper error handling and logging
- Ensure all new features respect user authentication
- Maintain backward compatibility with existing API

## Success Criteria

1. Users can set and persist their region preference
2. Dashboard automatically shows user's region data after login
3. All alert types work with email notifications
4. Alert history is comprehensive and searchable
5. Dashboard shows candle charts and trending data
6. Predicted prices are visible on dashboard
7. All features work end-to-end without errors

## Notes

- Maintain existing code patterns and architecture
- Use TypeScript strictly for type safety
- Follow existing naming conventions
- Ensure mobile responsiveness for new components
- Implement proper loading states and error handling
- Use existing charting libraries where possible
