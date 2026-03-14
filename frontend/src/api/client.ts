import axios from 'axios';
import { z } from 'zod';
import type {
  AlertCommodity,
  AlertDirection,
  AlertEvaluation,
  AlertHistoryItem,
  AlertHistoryFilters,
  AlertType,
  AIProviderStatus,
  AIChatResponse,
  CommodityNewsSummary,
  Commodity,
  CommodityDefinition,
  FeatureSnapshot,
  HistoricalResponse,
  LivePrice,
  MarketIntelligence,
  MarketSignal,
  NormalizedHistoricalSeries,
  NormalizedLiveQuote,
  PriceAlert,
  PredictionResponse,
  Region,
  RegionDefinition,
  TrainResponse,
  UserProfile,
  UserSettings,
  WhatsAppAlert,
} from '../types/api';

const envBaseURL = import.meta.env.VITE_API_BASE_URL?.trim();
const baseURL = envBaseURL && envBaseURL.length > 0 ? envBaseURL : '/api';
const api = axios.create({ baseURL });
let tokenGetter: (() => Promise<string | undefined>) | null = null;

export function setAccessTokenGetter(getter: () => Promise<string | undefined>): void {
  tokenGetter = getter;
}

api.interceptors.request.use(async (config) => {
  if (tokenGetter) {
    const token = await tokenGetter();
    if (token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

const regionSchema = z.object({
  id: z.enum(['india', 'us', 'europe']),
  currency: z.enum(['INR', 'USD', 'EUR']),
  unit: z.string(),
});

const commoditySchema = z.object({
  id: z.enum(['gold', 'silver', 'crude_oil']),
});

export const livePriceSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  unit: z.string(),
  currency: z.string(),
  live_price: z.number(),
  source: z.string(),
  timestamp: z.string(),
});

const liveEnvelopeSchema = z.object({ items: z.array(livePriceSchema) });

const historicalPointSchema = z.object({
  date: z.string(),
  open: z.number().nullable(),
  high: z.number().nullable(),
  low: z.number().nullable(),
  close: z.number(),
  volume: z.number().nullable(),
});

export const historicalSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  unit: z.string(),
  rows: z.number(),
  data: z.array(historicalPointSchema),
});

export const predictionSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  unit: z.string(),
  currency: z.string(),
  forecast_horizon: z.string(),
  current_spot_price: z.number(),
  spot_timestamp: z.string(),
  point_forecast: z.number(),
  forecast_vs_spot_pct: z.number(),
  confidence_interval: z.tuple([z.number(), z.number()]),
  confidence_method: z.string(),
  scenario: z.enum(['bull', 'base', 'bear']),
  scenario_forecasts: z.object({
    bull: z.number(),
    base: z.number(),
    bear: z.number(),
  }),
  forecast_basis_label: z.string(),
  macro_sensitivity_tags: z.array(z.string()),
  last_calibrated_at: z.string().nullable().optional(),
  model_used: z.string(),
});

const trainSchema = z.object({
  message: z.string(),
  status: z.enum(['processing']),
});

const dataProvenanceSchema = z.object({
  data_type: z.enum(['live_price', 'historical', 'forecast', 'news', 'features', 'signal']),
  provider: z.string(),
  detail: z.string().nullable().optional(),
  observed_at: z.string().nullable().optional(),
});

const engineeredFeatureSnapshotSchema = z.object({
  returns_1d: z.number(),
  returns_5d: z.number(),
  returns_20d: z.number(),
  realized_volatility_20d: z.number(),
  momentum_20d: z.number(),
  price_vs_ma20_pct: z.number(),
  drawdown_20d_pct: z.number(),
  fx_rate: z.number().nullable().optional(),
  fx_volatility: z.number().nullable().optional(),
  inflation_proxy: z.number().nullable().optional(),
  rate_proxy: z.number().nullable().optional(),
  calendar_month: z.number().int(),
});

const marketSignalSummarySchema = z.object({
  label: z.enum(['bullish', 'bearish', 'neutral', 'cautious']),
  score: z.number(),
  confidence: z.number(),
  scenario: z.enum(['bull', 'base', 'bear']),
  rationale: z.string(),
  thresholds_applied: z.array(z.string()),
});

const marketIntelligenceSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  unit: z.string(),
  horizon_days: z.number().int().min(1).max(90),
  as_of: z.string(),
  live_price: z.number(),
  forecast_point: z.number(),
  forecast_range: z.tuple([z.number(), z.number()]),
  scenario_forecasts: z.object({
    bull: z.number(),
    base: z.number(),
    bear: z.number(),
  }),
  signal: marketSignalSummarySchema,
  features: engineeredFeatureSnapshotSchema,
  news_sentiment: z.enum(['bullish', 'bearish', 'neutral']).nullable().optional(),
  news_summary: z.string().nullable().optional(),
  provenance: z.array(dataProvenanceSchema),
});

const normalizedLiveQuoteSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  price_usd_per_troy_oz: z.number(),
  observed_at: z.string(),
  provenance: dataProvenanceSchema,
});

const normalizedHistoricalBarSchema = z.object({
  date: z.string(),
  open_usd_per_troy_oz: z.number(),
  high_usd_per_troy_oz: z.number(),
  low_usd_per_troy_oz: z.number(),
  close_usd_per_troy_oz: z.number(),
  volume: z.number().nullable().optional(),
});

const normalizedHistoricalSeriesSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  rows: z.number(),
  provenance: dataProvenanceSchema,
  data: z.array(normalizedHistoricalBarSchema),
});

const featureSnapshotSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  period: z.string(),
  features: engineeredFeatureSnapshotSchema,
  provenance: z.array(dataProvenanceSchema),
});

const marketSignalSchema = z.object({
  commodity: z.enum(['gold', 'silver', 'crude_oil']),
  region: z.enum(['india', 'us', 'europe']),
  horizon_days: z.number().int().min(1).max(90),
  live_price: z.number(),
  forecast_point: z.number(),
  forecast_range: z.tuple([z.number(), z.number()]),
  scenario_forecasts: z.object({
    bull: z.number(),
    base: z.number(),
    bear: z.number(),
  }),
  signal: marketSignalSummarySchema,
  features: engineeredFeatureSnapshotSchema,
  provenance: z.array(dataProvenanceSchema),
});

export const trainStatusSchema = z.object({
  status: z.enum(['none', 'queued', 'processing', 'completed', 'failed']),
  message: z.string(),
  result: z
    .object({
      rmse: z.number(),
      mape: z.number(),
      best_model: z.string(),
      model_version: z.string(),
    })
    .optional(),
  error: z.record(z.unknown()).optional(),
  created_at: z.string().optional(),
  started_at: z.string().optional(),
  completed_at: z.string().optional(),
});

const alertCommoditySchema = z.enum(['gold', 'silver', 'crude_oil', 'natural_gas', 'copper']);
const alertTypeSchema = z.enum(['above', 'below', 'pct_change_24h', 'spike', 'drop']);
const alertDirectionSchema = z.enum(['above', 'below']);

const priceAlertSchema = z.object({
  id: z.number(),
  commodity: alertCommoditySchema,
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  unit: z.string(),
  alert_type: alertTypeSchema,
  threshold: z.number(),
  enabled: z.boolean(),
  cooldown_minutes: z.number(),
  email_notifications_enabled: z.boolean(),
  last_triggered_at: z.string().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

const alertHistorySchema = z.object({
  id: z.number(),
  alert_id: z.number(),
  commodity: alertCommoditySchema,
  region: z.enum(['india', 'us', 'europe']),
  currency: z.string(),
  alert_type: alertTypeSchema,
  threshold: z.number(),
  observed_value: z.number(),
  message: z.string(),
  email_status: z.string(),
  delivery_provider: z.string().nullable().optional(),
  delivery_error: z.string().nullable().optional(),
  delivery_attempts: z.number(),
  triggered_at: z.string(),
});

const whatsappAlertSchema = z.object({
  id: z.number(),
  user_id: z.string(),
  commodity: alertCommoditySchema,
  region: z.enum(['india', 'us', 'europe']),
  target_price: z.number(),
  direction: alertDirectionSchema,
  whatsapp_number: z.string(),
  is_active: z.boolean(),
  is_triggered: z.boolean(),
  created_at: z.string(),
  triggered_at: z.string().nullable().optional(),
});

const alertEvaluationSchema = z.object({
  checked: z.number(),
  triggered: z.number(),
  events: z.array(alertHistorySchema),
});

const newsHeadlineSchema = z.object({
  title: z.string(),
  source: z.string(),
  url: z.string(),
  published_at: z.string(),
});

const newsSummarySchema = z.object({
  commodity: alertCommoditySchema,
  sentiment: z.enum(['bullish', 'bearish', 'neutral']),
  summary: z.string(),
  headlines: z.array(newsHeadlineSchema),
  updated_at: z.string(),
});

const userProfileSchema = z.object({
  user_sub: z.string(),
  email: z.string().nullable().optional(),
  name: z.string().nullable().optional(),
  picture_url: z.string().nullable().optional(),
  preferred_region: z.enum(['india', 'us', 'europe']),
  email_notifications_enabled: z.boolean(),
  alert_cooldown_minutes: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

const userSettingsSchema = z.object({
  id: z.number(),
  user_id: z.string(),
  default_region: z.enum(['india', 'us', 'europe']),
  default_commodity: z.enum(['gold', 'silver', 'crude_oil']),
  prediction_horizon: z.number().int().min(1).max(90),
  email_notifications: z.boolean(),
  alert_cooldown_minutes: z.number().int().min(5).max(1440),
  alerts_enabled: z.boolean(),
  enable_chronos_bolt: z.boolean(),
  enable_xgboost: z.boolean(),
  auto_retrain: z.boolean(),
  theme_preference: z.enum(['light', 'dark', 'system']),
  created_at: z.string(),
  updated_at: z.string(),
});

const aiChatResponseSchema = z.object({
  answer: z.string(),
  intent: z.enum([
    'market_summary',
    'price_forecast',
    'historical_trend_analysis',
    'commodity_comparison',
    'region_comparison',
    'trading_outlook',
    'volatility_explanation',
  ]),
  region: z.enum(['india', 'us', 'europe']),
  commodity: z.enum(['gold', 'silver', 'crude_oil', 'natural_gas', 'copper']).nullable().optional(),
  horizon_days: z.number().int().min(1).max(1095),
  generated_at: z.string(),
});

const aiProviderStatusSchema = z.object({
  provider: z.enum(['openrouter', 'disabled']),
  openrouter_model: z.string(),
  openrouter_api_key_present: z.boolean(),
  openrouter_cooldown_seconds_remaining: z.number().int().min(0),
  last_openrouter_error: z.string().nullable().optional(),
});

function withQuery(path: string, filters: AlertHistoryFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.commodity) params.set('commodity', filters.commodity);
  if (filters.alert_type) params.set('alert_type', filters.alert_type);
  if (filters.email_status) params.set('email_status', filters.email_status);
  if (filters.start_at) params.set('start_at', filters.start_at);
  if (filters.end_at) params.set('end_at', filters.end_at);
  if (filters.search) params.set('search', filters.search);
  if (filters.limit) params.set('limit', String(filters.limit));
  const q = params.toString();
  return q ? `${path}?${q}` : path;
}

export const client = {
  regions: async () => z.array(regionSchema).parse((await api.get('/regions')).data) as RegionDefinition[],
  commodities: async () => z.array(commoditySchema).parse((await api.get('/commodities')).data) as CommodityDefinition[],
  livePrices: async () => liveEnvelopeSchema.parse((await api.get('/live-prices')).data).items as LivePrice[],
  livePricesByRegion: async (region: Region) =>
    liveEnvelopeSchema.parse((await api.get(`/live-prices/${region}`)).data).items as LivePrice[],
  publicLivePricesByRegion: async (region: Region) =>
    liveEnvelopeSchema.parse((await api.get(`/public/live-prices/${region}`)).data).items as LivePrice[],
  historical: async (commodity: Commodity, region: Region, range: '1m' | '6m' | '1y' | '5y' | 'max') =>
    historicalSchema.parse((await api.get(`/historical/${commodity}/${region}?range=${range}`)).data) as HistoricalResponse,
  train: async (commodity: Commodity, region: Region, horizon: number) =>
    trainSchema.parse((await api.post(`/train/${commodity}/${region}?horizon=${horizon}`)).data),
  trainStatus: async (commodity: Commodity, region: Region) =>
    trainStatusSchema.parse((await api.get(`/train/${commodity}/${region}/status`)).data),
  marketIntelligence: async (commodity: Commodity, region: Region, horizon: number) =>
    marketIntelligenceSchema.parse((await api.get(`/intelligence/${commodity}/${region}?horizon=${horizon}`)).data) as MarketIntelligence,
  normalizedLiveQuote: async (commodity: Commodity, region: Region) =>
    normalizedLiveQuoteSchema.parse((await api.get(`/normalized/live/${commodity}/${region}`)).data) as NormalizedLiveQuote,
  normalizedHistorical: async (commodity: Commodity, region: Region, range: '1m' | '6m' | '1y' | '5y' | 'max') =>
    normalizedHistoricalSeriesSchema.parse((await api.get(`/normalized/historical/${commodity}/${region}?range=${range}`)).data) as NormalizedHistoricalSeries,
  featureSnapshot: async (commodity: Commodity, region: Region, range: '1m' | '6m' | '1y' | '5y' | 'max') =>
    featureSnapshotSchema.parse((await api.get(`/features/${commodity}/${region}?range=${range}`)).data) as FeatureSnapshot,
  signalSnapshot: async (commodity: Commodity, region: Region, horizon: number) =>
    marketSignalSchema.parse((await api.get(`/signals/${commodity}/${region}?horizon=${horizon}`)).data) as MarketSignal,
  forecastSnapshot: async (commodity: Commodity, region: Region, horizon: number) =>
    predictionSchema.parse((await api.get(`/forecasts/${commodity}/${region}?horizon=${horizon}`)).data) as PredictionResponse,
  predict: async (commodity: Commodity, region: Region, horizon: number) =>
    predictionSchema.parse((await api.get(`/predict/${commodity}/${region}?horizon=${horizon}`)).data) as PredictionResponse,
  createAlert: async (input: {
    commodity: AlertCommodity;
    region: Region;
    alert_type: AlertType;
    threshold: number;
    enabled?: boolean;
    cooldown_minutes?: number;
    email_notifications_enabled?: boolean;
  }) =>
    priceAlertSchema.parse((await api.post('/alerts', input)).data) as PriceAlert,
  createWhatsAppAlert: async (input: {
    commodity: AlertCommodity;
    region: Region;
    target_price: number;
    direction: AlertDirection;
    whatsapp_number: string;
  }) =>
    whatsappAlertSchema.parse((await api.post('/alerts/whatsapp', input)).data) as WhatsAppAlert,
  listAlerts: async () => z.array(priceAlertSchema).parse((await api.get('/alerts')).data) as PriceAlert[],
  updateAlert: async (
    alertId: number,
    input: { threshold?: number; enabled?: boolean; cooldown_minutes?: number; email_notifications_enabled?: boolean },
  ) => priceAlertSchema.parse((await api.patch(`/alerts/${alertId}`, input)).data) as PriceAlert,
  deleteAlert: async (alertId: number) => api.delete(`/alerts/${alertId}`),
  evaluateAlerts: async () => alertEvaluationSchema.parse((await api.post('/alerts/evaluate')).data) as AlertEvaluation,
  alertHistory: async (filters: AlertHistoryFilters = {}) =>
    z.array(alertHistorySchema).parse((await api.get(withQuery('/alerts/history', filters))).data) as AlertHistoryItem[],
  exportAlertHistory: async (filters: AlertHistoryFilters = {}) =>
    api.get(withQuery('/alerts/history/export', filters), { responseType: 'blob' }),
  commodityNewsSummary: async (commodity: AlertCommodity) =>
    newsSummarySchema.parse((await api.get(`/news-summary/${commodity}`)).data) as CommodityNewsSummary,
  profile: async () => userProfileSchema.parse((await api.get('/profile')).data) as UserProfile,
  updateProfile: async (input: {
    name?: string;
    picture_url?: string;
    preferred_region?: Region;
    email_notifications_enabled?: boolean;
    alert_cooldown_minutes?: number;
  }) => userProfileSchema.parse((await api.put('/profile', input)).data) as UserProfile,
  getUserSettings: async () =>
    userSettingsSchema.parse((await api.get('/settings')).data) as UserSettings,
  updateUserSettings: async (input: {
    default_region?: Region;
    default_commodity?: Commodity;
    prediction_horizon?: number;
    email_notifications?: boolean;
    alert_cooldown_minutes?: number;
    alerts_enabled?: boolean;
    enable_chronos_bolt?: boolean;
    enable_xgboost?: boolean;
    auto_retrain?: boolean;
    theme_preference?: 'light' | 'dark' | 'system';
  }) => userSettingsSchema.parse((await api.post('/settings', input)).data) as UserSettings,
  sendChatMessage: async (message: string) =>
    aiChatResponseSchema.parse((await api.post('/ai/chat', { message })).data) as AIChatResponse,
  aiProviderStatus: async () =>
    aiProviderStatusSchema.parse((await api.get('/ai/provider-status')).data) as AIProviderStatus,
  sendChatMessageStream: async (
    message: string,
    handlers: {
      onToken: (chunk: string) => void;
      onDone: (response: AIChatResponse) => void;
    },
  ) => {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (tokenGetter) {
      const token = await tokenGetter();
      if (token) headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(`${baseURL}/ai/chat/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message }),
      credentials: 'include',
    });
    if (!response.ok || !response.body) {
      const errText = await response.text().catch(() => '');
      throw new Error(errText || `Streaming request failed with status ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';
      for (const rawEvent of events) {
        const lines = rawEvent.split('\n');
        const eventName = lines.find((line) => line.startsWith('event:'))?.replace('event:', '').trim() ?? 'message';
        const dataLine = lines.find((line) => line.startsWith('data:'))?.replace('data:', '').trim() ?? '{}';
        const parsed = JSON.parse(dataLine) as { delta?: string } | AIChatResponse | { error?: string };
        if (eventName === 'token' && 'delta' in parsed && typeof parsed.delta === 'string') {
          handlers.onToken(parsed.delta);
        } else if (eventName === 'done') {
          handlers.onDone(aiChatResponseSchema.parse(parsed));
        } else if (eventName === 'error') {
          throw new Error(typeof (parsed as { error?: string }).error === 'string' ? (parsed as { error: string }).error : 'Unknown streaming error');
        }
      }
    }
  },
};
