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
