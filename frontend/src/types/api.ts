export type Commodity = 'gold' | 'silver' | 'crude_oil';
export type Region = 'india' | 'us' | 'europe';
export type AlertCommodity = Commodity | 'natural_gas' | 'copper';
export type AlertType = 'above' | 'below' | 'pct_change_24h' | 'spike' | 'drop';
export type AlertDirection = 'above' | 'below';

export interface RegionDefinition {
  id: Region;
  currency: 'INR' | 'USD' | 'EUR';
  unit: string;
}

export interface CommodityDefinition {
  id: Commodity;
}

export interface LivePrice {
  commodity: Commodity;
  region: Region;
  unit: string;
  currency: string;
  live_price: number;
  source: string;
  timestamp: string;
}

export interface HistoricalPoint {
  date: string;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number;
  volume: number | null;
}

export interface HistoricalResponse {
  commodity: Commodity;
  region: Region;
  currency: string;
  unit: string;
  rows: number;
  data: HistoricalPoint[];
}

export interface PredictionResponse {
  commodity: Commodity;
  region: Region;
  unit: string;
  currency: string;
  forecast_horizon: string;
  point_forecast: number;
  confidence_interval: [number, number];
  scenario: 'bull' | 'base' | 'bear';
  scenario_forecasts: Record<'bull' | 'base' | 'bear', number>;
  model_used: string;
}

export interface DataProvenance {
  data_type: 'live_price' | 'historical' | 'forecast' | 'news' | 'features' | 'signal';
  provider: string;
  detail?: string | null;
  observed_at?: string | null;
}

export interface EngineeredFeatureSnapshot {
  returns_1d: number;
  returns_5d: number;
  returns_20d: number;
  realized_volatility_20d: number;
  momentum_20d: number;
  price_vs_ma20_pct: number;
  drawdown_20d_pct: number;
  fx_rate?: number | null;
  fx_volatility?: number | null;
  inflation_proxy?: number | null;
  rate_proxy?: number | null;
  calendar_month: number;
}

export interface MarketSignalSummary {
  label: 'bullish' | 'bearish' | 'neutral' | 'cautious';
  score: number;
  confidence: number;
  scenario: 'bull' | 'base' | 'bear';
  rationale: string;
  thresholds_applied: string[];
}

export interface MarketIntelligence {
  commodity: Commodity;
  region: Region;
  currency: string;
  unit: string;
  horizon_days: number;
  as_of: string;
  live_price: number;
  forecast_point: number;
  forecast_range: [number, number];
  scenario_forecasts: Record<'bull' | 'base' | 'bear', number>;
  signal: MarketSignalSummary;
  features: EngineeredFeatureSnapshot;
  news_sentiment?: 'bullish' | 'bearish' | 'neutral' | null;
  news_summary?: string | null;
  provenance: DataProvenance[];
}

export interface NormalizedLiveQuote {
  commodity: Commodity;
  price_usd_per_troy_oz: number;
  observed_at: string;
  provenance: DataProvenance;
}

export interface NormalizedHistoricalBar {
  date: string;
  open_usd_per_troy_oz: number;
  high_usd_per_troy_oz: number;
  low_usd_per_troy_oz: number;
  close_usd_per_troy_oz: number;
  volume?: number | null;
}

export interface NormalizedHistoricalSeries {
  commodity: Commodity;
  region: Region;
  rows: number;
  provenance: DataProvenance;
  data: NormalizedHistoricalBar[];
}

export interface FeatureSnapshot {
  commodity: Commodity;
  region: Region;
  period: string;
  features: EngineeredFeatureSnapshot;
  provenance: DataProvenance[];
}

export interface MarketSignal {
  commodity: Commodity;
  region: Region;
  horizon_days: number;
  live_price: number;
  forecast_point: number;
  forecast_range: [number, number];
  scenario_forecasts: Record<'bull' | 'base' | 'bear', number>;
  signal: MarketSignalSummary;
  features: EngineeredFeatureSnapshot;
  provenance: DataProvenance[];
}

export interface TrainResponse {
  commodity: Commodity;
  region: Region;
  best_model: string;
  model_version: string;
  rmse: number;
  mape: number;
}

export interface PriceAlert {
  id: number;
  commodity: AlertCommodity;
  region: Region;
  currency: string;
  unit: string;
  alert_type: AlertType;
  threshold: number;
  enabled: boolean;
  cooldown_minutes: number;
  email_notifications_enabled: boolean;
  last_triggered_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface WhatsAppAlert {
  id: number;
  user_id: string;
  commodity: AlertCommodity;
  region: Region;
  target_price: number;
  direction: AlertDirection;
  whatsapp_number: string;
  is_active: boolean;
  is_triggered: boolean;
  created_at: string;
  triggered_at?: string | null;
}

export interface AlertHistoryItem {
  id: number;
  alert_id: number;
  commodity: AlertCommodity;
  region: Region;
  currency: string;
  alert_type: AlertType;
  threshold: number;
  observed_value: number;
  message: string;
  email_status: string;
  delivery_provider?: string | null;
  delivery_error?: string | null;
  delivery_attempts: number;
  triggered_at: string;
}

export interface AlertEvaluation {
  checked: number;
  triggered: number;
  events: AlertHistoryItem[];
}

export interface NewsHeadline {
  title: string;
  source: string;
  url: string;
  published_at: string;
}

export interface CommodityNewsSummary {
  commodity: AlertCommodity;
  sentiment: 'bullish' | 'bearish' | 'neutral';
  summary: string;
  headlines: NewsHeadline[];
  updated_at: string;
}

export interface UserProfile {
  user_sub: string;
  email?: string | null;
  name?: string | null;
  picture_url?: string | null;
  preferred_region: Region;
  email_notifications_enabled: boolean;
  alert_cooldown_minutes: number;
  created_at: string;
  updated_at: string;
}

export interface UserSettings {
  id: number;
  user_id: string;
  default_region: Region;
  default_commodity: Commodity;
  prediction_horizon: number;
  email_notifications: boolean;
  alert_cooldown_minutes: number;
  alerts_enabled: boolean;
  enable_chronos_bolt: boolean;
  enable_xgboost: boolean;
  auto_retrain: boolean;
  theme_preference: 'light' | 'dark' | 'system';
  created_at: string;
  updated_at: string;
}

export interface AlertHistoryFilters {
  commodity?: AlertCommodity;
  alert_type?: AlertType;
  email_status?: string;
  start_at?: string;
  end_at?: string;
  search?: string;
  limit?: number;
}

export interface AIChatResponse {
  answer: string;
  intent:
    | 'market_summary'
    | 'price_forecast'
    | 'historical_trend_analysis'
    | 'commodity_comparison'
    | 'region_comparison'
    | 'trading_outlook'
    | 'volatility_explanation';
  region: Region;
  commodity?: AlertCommodity | null;
  horizon_days: number;
  generated_at: string;
}

export interface AIProviderStatus {
  provider: 'openrouter' | 'disabled';
  openrouter_model: string;
  openrouter_api_key_present: boolean;
  openrouter_cooldown_seconds_remaining: number;
  last_openrouter_error?: string | null;
}
